"""ASGI entry point: `uvicorn bepmay_host.server:app --port 8020` (env: DATABASE_URL, HOST_OIDC_*)."""
from __future__ import annotations

import os

from bepmay_host.api import create_app
from bepmay_host.auth import AuthConfig, OIDCTokenVerifier
from bepmay_host.postgres_store import PostgresBusinessStore


def _build():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    store = PostgresBusinessStore(url)
    try:
        store.assert_least_privilege()  # fail at boot, not silently at request time
    except Exception:
        store.close()
        raise
    return create_app(token_verifier=OIDCTokenVerifier(AuthConfig.from_env()), store=store)


app = _build()
