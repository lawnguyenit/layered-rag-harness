"""Production-shaped ASGI entry point; all secrets and issuer values come from environment."""
from __future__ import annotations

import os
from lrh.config import load_settings
from lrh.factory import build_generator
from lrh.api import create_app
from lrh.conversation_store import ConversationStore
from lrh.oidc import OIDCConfig, OIDCTokenVerifier
from lrh.routing import ModelIntentParser, RouteCatalog


def _build_app():
    settings = load_settings()
    oidc = OIDCConfig.from_env()
    catalog_path = os.getenv("LRH_ROUTE_CATALOG", "").strip()
    if not catalog_path:
        raise RuntimeError("LRH_ROUTE_CATALOG must point to a domain route catalog")
    catalog = RouteCatalog.load(catalog_path)
    generator = build_generator(settings.model_id, settings, use_cache=False)
    parser = ModelIntentParser(generator, catalog)
    store = ConversationStore(os.getenv("LRH_CONVERSATION_DB", "data/private/conversations.sqlite3"))
    return create_app(
        token_verifier=OIDCTokenVerifier(oidc),
        parser=parser,
        catalog=catalog,
        conversations=store,
        max_body_bytes=int(os.getenv("LRH_API_MAX_BODY_BYTES", "16384")),
        max_question_chars=int(os.getenv("LRH_API_MAX_QUESTION_CHARS", "8000")),
        requests_per_minute=int(os.getenv("LRH_API_RATE_LIMIT_PER_MINUTE", "30")),
    )


app = _build_app()
