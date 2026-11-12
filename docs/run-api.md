# Local Tier 1–2 API

This is a local development route-planning API. It needs a real OIDC token and a Gemini API key for semantic intent parsing. The endpoint stops at a route plan: it does not retrieve documents, run tools, or generate a customer answer.

## Start local Keycloak

1. Copy `.env.example` to `.env` and set local-only Keycloak bootstrap credentials. Keep `.env` untracked.
2. Run `docker compose -f compose.auth.yaml up -d`.
3. Open `http://localhost:8080`, create realm `lrh`, and create one application role per user such as `customer` or `support`. The API rejects a token carrying zero or multiple recognized application roles; it does not infer role hierarchy.
4. Create an OIDC client for the API. Configure an access-token audience mapper that emits `lrh-api` as `aud`. Add a user-attribute mapper for `customer_id` if testing customer-owned records. Use an Authorization Code + PKCE client flow for a real interactive client; do not build a password-collection flow into the harness.
5. Set the local environment values for `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL`, `LRH_ROUTE_CATALOG`, and `GEMINI_API_KEY`. Local Keycloak URLs are `http://localhost:8080/realms/lrh` and `http://localhost:8080/realms/lrh/protocol/openid-connect/certs`; audience is `lrh-api`; current fixture catalog is `eval/intent/catalog-bm-v1.json`.
6. Start from the repository root with `uv run uvicorn lrh.server:app --host 127.0.0.1 --port 8010`.

Request `POST /v1/route` with JSON `{"question":"Đơn BM-1001 giao khi nào?"}` and an `Authorization: Bearer <access token>` header. The response contains a decision and zero or more route tasks. The HTTP body cannot set `role`, `customer_id`, `actor`, or `access_scope`.

## Boundaries and limits

- `compose.auth.yaml` runs Keycloak in `start-dev`, bound to loopback; it is not a production deployment.
- The API validates JWT signature (`RS256`), issuer, audience, expiration and required claims. It reads role and customer identity from token claims. Production can use another OIDC issuer by changing issuer/audience/JWKS configuration.
- The SQLite conversation store is local and private under `data/private/`; every read/write uses the authenticated subject. Replace it through the same storage contract before multi-instance production.
- The sliding-window request limiter is process-local. It protects a single dev process; a horizontally scaled service needs a shared limiter.
- Ingress checks body size, field shape and request rate. It is not a semantic toxicity classifier. A live probe on 2026-11-12 set Gemini safety thresholds to `BLOCK_ONLY_HIGH` on the configured Gemma 4 parser call; three direct harmful requests still received `NEGLIGIBLE` ratings and were not blocked. Treat provider settings as defense in depth, not the semantic ingress gate. See `docs/lab/input-safety-probe-2026-11-12.md`.
- API TLS, proxy trust, account provisioning, token revocation strategy, retention/deletion, production rate limiting and deployment are not implemented or verified.
