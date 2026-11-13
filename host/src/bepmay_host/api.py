"""Read-only HTTP API of the host. Denied and nonexistent records both return the same 404."""
from __future__ import annotations

import re
from typing import Protocol

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from bepmay_host.access import Actor, BusinessRecord
from bepmay_host.auth import AuthenticationError, AuthenticationUnavailable, TokenVerifier

_REF = {
    "order": re.compile(r"^BM-\d{4}$"),
    "ticket": re.compile(r"^T\d{2}$"),
    "invoice": re.compile(r"^INV-\d{4}-\d{4}$"),
}


class Store(Protocol):
    def get(self, actor: Actor, kind: str, ref_id: str) -> BusinessRecord | None: ...


def create_app(*, token_verifier: TokenVerifier, store: Store) -> FastAPI:
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

    return app
