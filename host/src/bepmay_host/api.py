"""Read-only HTTP API of the host. Denied and nonexistent records both return the same 404."""
from __future__ import annotations

import re
from typing import Protocol

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from bepmay_host.access import Actor, BusinessRecord
from bepmay_host.auth import AuthenticationError, AuthenticationUnavailable, TokenVerifier
from bepmay_host.embeddings import Embedder, EmbeddingUnavailable
from bepmay_host.search_store import SearchStore

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
) -> FastAPI:
    app = FastAPI(title="Bếp Mây host (synthetic)", version="0.0.1")
    bearer = HTTPBearer(auto_error=False)

    def actor_dep(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Actor:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(401, "authentication_required", headers={"WWW-Authenticate": "Bearer"})
        try:
            return token_verifier.actor_for(credentials.credentials)
        except AuthenticationUnavailable as exc:
            raise HTTPException(503, "identity_provider_unavailable") from exc
        except AuthenticationError as exc:
            raise HTTPException(401, "invalid_bearer_token", headers={"WWW-Authenticate": "Bearer"}) from exc

    def lookup(kind: str, ref_id: str, actor: Actor) -> dict:
        record = store.get(actor, kind, ref_id) if _REF[kind].match(ref_id) else None
        if record is None:
            raise HTTPException(404, "not_found")
        return {"kind": record.kind, "ref_id": record.ref_id, "title": record.title, "body": record.body}

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/v1/orders/{ref_id}")
    def order(ref_id: str, actor: Actor = Depends(actor_dep)):
        return lookup("order", ref_id, actor)

    @app.get("/v1/tickets/{ref_id}")
    def ticket(ref_id: str, actor: Actor = Depends(actor_dep)):
        return lookup("ticket", ref_id, actor)

    @app.get("/v1/invoices/{ref_id}")
    def invoice(ref_id: str, actor: Actor = Depends(actor_dep)):
        return lookup("invoice", ref_id, actor)

    if search_store is not None and embedder is not None:
        @app.post("/v1/search")
        def search(body: SearchRequest, actor: Actor = Depends(actor_dep)):
            """Semantic search over document chunks the actor may see. Ranking never sees other chunks."""
            try:
                qvec = embedder.embed_query(body.query)
            except EmbeddingUnavailable as exc:
                raise HTTPException(503, "embedding_unavailable") from exc
            hits = search_store.search(actor, embedder.model_id, qvec, body.top_k)
            return {"results": [
                {"chunk_id": h.chunk_id, "doc_id": h.doc_id, "title": h.title, "kind": h.kind,
                 "text": h.text, "score": round(h.score, 6)} for h in hits
            ]}

    return app
