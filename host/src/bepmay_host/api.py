"""HTTP API of the host (read-only). Denied and nonexistent records both return the same 404."""
from __future__ import annotations

import re
import time
import uuid
from typing import Protocol

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from bepmay_host.access import Actor, BusinessRecord
from bepmay_host.auth import AuthenticationError, AuthenticationUnavailable, TokenVerifier
from bepmay_host.embeddings import Embedder, EmbeddingUnavailable
from bepmay_host.search_store import SearchStore
from bepmay_host.trace import REQUEST_ID, TraceRecorder, outcome_for, subject_tag

_REF = {
    "order": re.compile(r"^BM-\d{4}$"),
    "ticket": re.compile(r"^T\d{2}$"),
    "invoice": re.compile(r"^INV-\d{4}-\d{4}$"),
}


class Store(Protocol):
    def get(self, actor: Actor, kind: str, ref_id: str) -> BusinessRecord | None: ...


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


def create_app(
    *, token_verifier: TokenVerifier, store: Store,
    search_store: SearchStore | None = None, embedder: Embedder | None = None,
    trace: TraceRecorder | None = None, cors_origins: list[str] | None = None,
) -> FastAPI:
    app = FastAPI(title="Bếp Mây host (synthetic)", version="0.0.1")
    recorder = trace or TraceRecorder()
    bearer = HTTPBearer(auto_error=False)

    @app.middleware("http")
    async def trace_requests(request: Request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if REQUEST_ID.match(supplied) else uuid.uuid4().hex
        request.state.trace = {}
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            info = request.state.trace
            route = request.scope.get("route")
            recorder.emit({
                "request_id": request_id, "method": request.method,
                "route": getattr(route, "path", "unmatched"), "status": status,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "outcome": outcome_for(status, "authorization" in request.headers, info.pop("outcome", None)),
                **info,
            })

    if cors_origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=cors_origins, allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "X-Request-Id"], expose_headers=["X-Request-Id"],
        )

    def actor_dep(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Actor:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(401, "authentication_required", headers={"WWW-Authenticate": "Bearer"})
        try:
            actor = token_verifier.actor_for(credentials.credentials)
        except AuthenticationUnavailable as exc:
            raise HTTPException(503, "identity_provider_unavailable") from exc
        except AuthenticationError as exc:
            raise HTTPException(401, "invalid_bearer_token", headers={"WWW-Authenticate": "Bearer"}) from exc
        request.state.trace.update(actor_role=actor.role, actor=subject_tag(actor.subject))
        return actor

    def lookup(request: Request, kind: str, ref_id: str, actor: Actor) -> dict:
        valid = bool(_REF[kind].match(ref_id))
        request.state.trace.update(kind=kind, ref=ref_id if valid else None)  # never echo unvalidated input into the log
        record = store.get(actor, kind, ref_id) if valid else None
        if record is None:
            raise HTTPException(404, "not_found")
        return {"kind": record.kind, "ref_id": record.ref_id, "title": record.title, "body": record.body}

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/v1/orders/{ref_id}")
    def order(request: Request, ref_id: str, actor: Actor = Depends(actor_dep)):
        return lookup(request, "order", ref_id, actor)

    @app.get("/v1/tickets/{ref_id}")
    def ticket(request: Request, ref_id: str, actor: Actor = Depends(actor_dep)):
        return lookup(request, "ticket", ref_id, actor)

    @app.get("/v1/invoices/{ref_id}")
    def invoice(request: Request, ref_id: str, actor: Actor = Depends(actor_dep)):
        return lookup(request, "invoice", ref_id, actor)

    if search_store is not None and embedder is not None:
        @app.post("/v1/search")
        def search(request: Request, body: SearchRequest, actor: Actor = Depends(actor_dep)):
            """Semantic search over document chunks the actor may see. Ranking never sees other chunks."""
            request.state.trace.update(kind="search", top_k=body.top_k)  # the query text is not logged
            try:
                qvec = embedder.embed_query(body.query)
            except EmbeddingUnavailable as exc:
                request.state.trace["outcome"] = "embedding_unavailable"
                raise HTTPException(503, "embedding_unavailable") from exc
            hits = search_store.search(actor, embedder.model_id, qvec, body.top_k)
            request.state.trace["result_count"] = len(hits)
            return {"results": [
                {"chunk_id": h.chunk_id, "doc_id": h.doc_id, "title": h.title, "kind": h.kind,
                 "text": h.text, "score": round(h.score, 6)} for h in hits
            ]}

    return app
