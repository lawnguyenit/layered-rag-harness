"""ASGI entry point: `uvicorn bepmay_host.server:app --port 8020` (env: DATABASE_URL, HOST_OIDC_*, HOST_EMBEDDER)."""
from __future__ import annotations

import os

from bepmay_host.api import create_app
from bepmay_host.auth import AuthConfig, OIDCTokenVerifier
from bepmay_host.embeddings import embedder_from_env
from bepmay_host.postgres_search import PostgresSearchStore
from bepmay_host.postgres_store import PostgresBusinessStore


def _build():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    store, search = PostgresBusinessStore(url), PostgresSearchStore(url)
    try:
        # Fail at boot, not silently at request time.
        store.assert_least_privilege()
        search.assert_least_privilege()
        embedder = embedder_from_env()
    except Exception:
        store.close()
        search.close()
        raise
    return create_app(token_verifier=OIDCTokenVerifier(AuthConfig.from_env()), store=store,
                      search_store=search, embedder=embedder)


app = _build()
