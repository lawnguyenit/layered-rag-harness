# Project state records

These files separate user intent, approved decisions, code that exists, impact, verification, and acceptance. Status words are not interchangeable. Update them alongside any non-trivial change.

- `user-intent.md`: requested behavior and approved scope.
- `implementation-state.md`: repository facts checked against source.
- `impact-map.md`: affected boundaries and owners.
- `verification.md`: evidence, unrun checks, and remaining gates.

Current scope extension: implement runtime Tier 1 (HTTP ingress, input limits, OIDC identity, actor/access scope) and Tier 2 (intent/slot/polarity/reference parsing, clarify/unsupported decisions, route planning) before the existing RAG generation path. The Bếp Mây scenario remains a fixture; core contracts must be domain-neutral.
