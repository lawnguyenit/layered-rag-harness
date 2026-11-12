# Implementation state (checked 2026-11-12)

## Existing code

| ID | Behavior | Status | User accepted? | Source evidence | Runtime/test evidence | Last checked |
|---|---|---|---|---|---|---|
| IMP-GENERATE | CLI sends one question as a provider `GenerateRequest`; model chain includes cache/throttle/spend guard. | implemented | unknown | `src/lrh/cli.py`, `src/lrh/contracts.py`, `src/lrh/factory.py` | Existing G0 tests; no runtime HTTP path. | 2026-11-12 |
| IMP-HTTP | HTTP `POST /v1/route` and `/healthz`. | implemented and independently unit-verified | no | `src/lrh/api.py`, `src/lrh/server.py`, `src/lrh/request_contracts.py`. | 68 passed/2 skipped in full suite; no live service run. | 2026-11-12 |
| IMP-AUTH | Validated OIDC identity / actor context. | implemented; synthetic-token tests pass; live issuer pending | no | `src/lrh/oidc.py`; `compose.auth.yaml`; environment contracts in `.env.example`. | RSA/JWKS fake tests pass; local Keycloak integration not run. | 2026-11-12 |
| IMP-INPUT-GATE | Request-size, question-size, whitespace, and per-subject caller-rate gate. | implemented and independently unit-verified | no | `src/lrh/api.py`, `src/lrh/ingress.py`. | Covered by focused tests; semantic harmful-content moderation is not implemented. | 2026-11-12 |
| IMP-ACCESS-SCOPE | Trusted route access scope derived from verified actor. | implemented and independently unit-verified | no | `src/lrh/request_contracts.py`, `src/lrh/routing.py`; body fields are forbidden. | Tests cover claim-derived role/scope; this scope is not yet an ACL filter over data. | 2026-11-12 |
| IMP-HISTORY | Per-subject local SQLite conversation context. | implemented and independently unit-verified | no | `src/lrh/conversation_store.py`; default path under `data/private/`. | Ownership isolation test passes; multi-instance production store not implemented. | 2026-11-12 |
| IMP-5A | Intent, slots, polarity, negation, references and route-plan validation. | implemented; contract tests pass; semantic score not measured | no | `src/lrh/routing.py`; model behind `IntentParser`/`ModelIntentParser`; catalog is external config. | Focused and full tests pass; live Gemini 5a benchmark not run. | 2026-11-12 |
| IMP-EVAL-5A | Labeled 5a benchmark draft. | draft, structurally validated | no | `eval/intent/README.md`, `eval/intent/catalog-bm-v0.json`, `eval/intent/cases-v0-draft.jsonl`. | Validator passes; independent reviewer cleared schema blockers but gold approval remains open. | 2026-11-12 |

## Approved design boundary

Tiers 1–2 end at a validated route plan containing one or more tasks, actor identity/access scope, and a route decision. They do not query protected records, retrieve documents, call tools, assemble the final answer prompt, or call the answer-generation LLM. Those are later runtime tiers.

`GenerateRequest` remains the provider-facing model contract. The user-facing HTTP envelope must be a separate contract and must not accept a caller-defined system prompt, role, actor ID, tenant ID, or access scope.
