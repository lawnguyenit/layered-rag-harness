# Impact map: runtime Tiers 1–2

| Capability | UI / CLI | HTTP / handler / domain | Storage / external | Errors and logs | Tests / deploy |
|---|---|---|---|---|---|
| Request ingress | CLI remains existing G0 path | New API app and request envelope; validate body before parsing | None required | Safe 4xx response; correlation ID; do not log raw sensitive prompts by default | API contract, oversize, empty, content-type, rate-limit checks; local API launch |
| OIDC auth | Not applicable | Bearer-token verification adapter; actor constructed from validated claims | Discovery/JWKS from configured issuer; Keycloak local dev/test | 401 invalid/missing token; avoid token or PII logging | Valid, expired, wrong issuer/audience/algorithm, missing/unknown role, JWKS failure; Keycloak dev setup |
| Actor and access scope | Not user-controlled | Principal claims map to allowlisted role and optional customer ID; scope policy consumes actor only | No database lookup yet unless the chosen account/session mapping requires one | 403 / not-found policy remains distinct from parser result | Spoofed body role/customer, untrusted role strings, positive-control actor/scope cases |
| 5a parse | No UI required | Domain-neutral parser port; replaceable route catalog fixture; parse intent/slots/polarity/references | Model provider behind adapter; local deterministic stub for contract tests | Parse/schema failure abstains to clarify; record safe category and timings | Fixed semantic benchmark; split by paraphrase family/conversation; separate latency/cost/load runs |
| T2 plan | Existing CLI is unaffected | Combine validated parse candidates with trusted actor scope into route tasks; no execution | No RAG/tool/database call at this stage | `route`, `clarify`, `unsupported`, `no_action`; preserve parser and policy outcomes separately | Contract tests ensure no dispatch on missing/negative/unsupported or malformed output |

## Adjacent surfaces to reconcile

- `src/lrh/cli.py` and provider `GenerateRequest` remain a separate G0 execution route.
- `docs/architecture/` currently illustrates future ACL, RAG, model, and MCP paths; label each as design or implemented according to source evidence.
- `docs/PLAN.md`, `docs/GATES.md`, `docs/DATA-CONTRACT.md` currently put auth later and behavioral refusal in G3. Update these records without erasing the prior rationale.
- `eval/questions.jsonl` is answer-level and remains unchanged; the new 5a set is separately versioned.
