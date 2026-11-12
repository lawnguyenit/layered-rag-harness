# User intent and approved decisions

Updated 2026-11-12. This record captures the current conversation; earlier project docs may still describe the previous schedule.

## User intent

| ID | Request | Normalized meaning | Status | Source/date |
|---|---|---|---|---|
| REQ-RUNTIME-T1T2 | Implement runtime Tier 1 and Tier 2; specifically measure uncertainty in 5a (intent, slots, negation, references), error types, and accuracy. | Add an API request path up to a scoped route plan, plus a fixed, reviewable parser evaluation suite. Do not imply RAG/tool execution is part of these tiers. | requested | Conversation, 2026-11-12 |
| REQ-GENERIC | The process is generic; Bếp Mây is only a concrete example. | Keep ingress, identity, parsing and route contracts domain-neutral; put example intents in a replaceable fixture/catalog. | approved | Conversation, 2026-11-12 |
| REQ-AUTH | Include a real HTTP API and authentication in scope now. | No unauthenticated production request path; actor identity comes from validated credentials, never question/body claims. | approved | User response, 2026-11-12 |

## Approved decisions

| ID | Decision | Alternatives rejected | Scope | Evidence |
|---|---|---|---|---|
| DEC-OIDC | Use OIDC; Keycloak is the local dev/test issuer. Production remains provider-configurable using issuer/audience/JWKS configuration. | Hard-coding a production identity vendor; trusting caller-supplied actor fields. | HTTP auth adapter/config | User response, 2026-11-12 |
| DEC-CANCEL-V0 | Parse cancellation intent. If no cancellation handler exists, mark `unsupported`; if required target data is missing, clarify first. | Treat a recognized unsupported action as an unknown intent. | 5a decision contract | User response, 2026-11-12 |
| DEC-MULTI-ROUTE | A compound utterance or multiple targets produce a list of route tasks, one per intent/target. | Silently dropping facets or forcing one task. | T2 route planning | User response, 2026-11-12 |
| DEC-REFERENCE-RECENCY | Resolve “that order” to the most recently mentioned compatible entity; clarify if none or if the parser cannot identify a compatible antecedent. | Always clarify whenever more than one entity exists in history. | 5a context resolution | User response, 2026-11-12 |
| DEC-NEGATION-NO-ACTION | “Đừng hủy đơn” means `no_action`; never create a route for the negated cancellation. | Confirming or dispatching the negated action. | 5a polarity/dispatch boundary | User response, 2026-11-12 |

## Superseded plan timing

`docs/PLAN.md` previously placed HTTP identity in project stage 3. The current request moves API and authentication into runtime Tiers 1–2. This changes delivery order, not the separate project gate labels G0–G4. Reconcile `docs/PLAN.md` and `docs/GATES.md` before declaring a gate complete.
