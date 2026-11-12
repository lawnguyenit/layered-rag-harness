# Verification and gaps

Updated 2026-11-12.

| ID | Check | Result | Evidence | Next action |
|---|---|---|---|---|
| CHK-STATE-001 | Inspect source for HTTP/auth/parser/access-scope implementation | pass | Current source verified independently; route plan stops before retrieval and execution. | Live service and owner acceptance remain separate. |
| CHK-API-001 | Tier 1–2 focused and full test suites | pass | Independent run 2026-11-12: focused scorer/ingress tests = 14 passed; `uv run pytest -q` = 69 passed, 2 skipped. One Starlette/httpx deprecation warning. | Re-run as code changes. |
| CHK-EVAL-001 | Draft benchmark structural validation | pass | Independent run: v1 = 35 valid draft rows; preserved v0 = 30 valid draft rows. Both validators pass. | Keep v1 gold draft until owner approves; do not report accuracy. |
| CHK-EVAL-002 | Gold label review | partial/open | Independent blind review found no blocking v1 artifact inconsistency and considers it ready for owner review as a draft; gold labels are not approved, test is non-blind, and coverage is thin. | Owner review before freezing test split. |
| CHK-AUTH-UNIT | Token signature/issuer/audience/expiry/role validation | pass (unit only) | Synthetic RSA key with fake JWKS in `tests/test_api_ingress.py`; does not prove live Keycloak. | Run local Keycloak end-to-end token check. |
| CHK-AUTH-LIVE | OIDC issuer/audience/JWKS against local Keycloak | not-run | `compose.auth.yaml` and setup guide exist; no live realm/client/token run. | Start local issuer and verify real access token. |
| CHK-5A-001 | Parser accuracy, uncertainty and serving cost | not-run | Parser and `eval/intent/run.py`/`score.py` exist. No live Gemini request or approved gold set. | Approve labels; run fixed test split; measure accuracy, false dispatch/coverage, latency/tokens/provider errors. |
| GAP-CORE-OWNER | Core permission filter and tool loop should be typed by repository owner with agent guidance. | open | `AGENTS.md` owner-workflow rule. | Tier 1–2 do not query protected data or execute tools. The actual data filter/tool loop remains for owner-guided implementation later. |
| GAP-SEMANTIC-GOLD | Some fixture labels (intent taxonomy, slot grammar, context limits) require final gold review. | open | Draft benchmark, owner decisions, independent reviewer report. | Reviewer plus owner review before declaring measured accuracy. |
| GAP-PRODUCTION | Production issuer, TLS/reverse proxy, secret/session handling, distributed rate limiting and deployment are not specified. | open | Owner approved provider-neutral production config; no target deployment context yet. | Keep production issuer configurable; document operational requirements; do not claim production readiness. |
| GAP-INPUT-SAFETY | Semantic harmful-content moderation is not implemented. | open | Current ingress gate checks deterministic limits and request rate; no threat taxonomy/eval cases exist. | Define policy and fixed cases before selecting a classifier; do not substitute keyword scanning as a general semantic solution. |

The independent test agent ran the commands recorded above. No live Keycloak or live Gemini parser benchmark was run. Docker Desktop's user application was started and the daemon connected, but Keycloak bootstrap requires local credentials; repo `AGENTS.md` requires asking before accessing `.env` or credential files. No production service was run.
