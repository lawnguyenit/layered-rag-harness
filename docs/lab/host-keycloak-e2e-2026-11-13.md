# Host end-to-end with a real Keycloak token

Date: 2026-11-13. Environment: Keycloak 26.8.2 (`start-dev`, loopback port 18080), PostgreSQL 16 (throwaway container), the host API run from `host/` as the non-bypass role `bepmay_app`, and the harness client `lrh.business.HostHttpBusinessLookup` over real HTTP. Synthetic realm and users only; all containers and credentials were temporary and are not in Git. Reproduce with `scripts/e2e_host_keycloak.py`.

## Result
17 of 17 checks passed: five users (two customers, support, finance, manager) read exactly what the access matrix allows, a customer reading another customer's order and a nonexistent order both got "none", a token addressed to another API, a tampered signature and a garbage string were all answered 401 by the host.

## What it found
- **Keycloak only issued the host audience once the host was registered as a client.** The audience mapper was configured correctly but the token still carried `aud=account`. Registering `bepmay-host` (and `lrh-api`) as bearer-only clients fixed it. Any real IdP setup needs the API registered as a resource server.
- **Open design problem, not solved here:** the token that passes the host has `aud=bepmay-host` only, so the harness's own verifier (audience `lrh-api`) would reject it. A single user token cannot satisfy both services unless it carries both audiences. Options: (a) put both audiences in one token, which is simple but lets either service replay the token at the other; (b) token exchange (OAuth 2.0 RFC 8693) so the harness trades the user token for one addressed to the host [general knowledge, not yet verified against Keycloak 26.8 docs]. Option (b) is the production pattern; it is not built.

## Limits
Password grant and a username-free random password were used only to obtain tokens in a script; the earlier PKCE smoke covers the interactive flow. The `customer_id` claim comes from a user attribute (a test mapping). Keycloak ran in dev mode over HTTP on loopback; production needs HTTPS. This does not test the harness `/v1/route` endpoint calling the host, because the harness does not dispatch C1 yet (H3).
