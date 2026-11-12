# Local OIDC Authorization Code + PKCE smoke

Date: 2026-11-12. Environment: temporary Keycloak 26.8.2 and Uvicorn, both bound to loopback; synthetic user/client only.

## Observed flow

The smoke used the Authorization Code flow with PKCE `S256`, checked the returned state, exchanged the code with its verifier, and called the running `/v1/route` endpoint over HTTP. The public client had direct access grants disabled. Its test-only Keycloak mapper derived the `customer_id` claim from the authenticated user's `username` property; the token also carried the `customer` realm role and `lrh-api` audience.

Observed result: authorization code + PKCE succeeded; state matched; the access token contained `customer_id=c001`, role `customer`, and audience `lrh-api`; the API returned HTTP 200 with `access_scope.owner_customer_id=c001`.

## Scope and limitations

- The HTTP test client manually allowed Keycloak's `Secure` loopback cookies over local HTTP because `httpx` does not apply browser localhost trust behavior. This is a local test-client accommodation, not a change to the application and not evidence for browser cookie behavior over HTTP. Production interactive OIDC must use HTTPS.
- The username-to-customer claim mapper is only a test mapping. A production identity provider must supply a stable, controlled customer identifier; usernames can change and must not be treated as the production identity contract without an explicit design decision.
- This verifies claim-derived actor/scope construction only. It does not verify a data-store ACL, retrieval filter, tool authorization, or production deployment.
- The user's owner gold review, semantic input-safety policy, held-out 5a score, and remaining project gates are still open.

The smoke account, Keycloak container, API process, credentials and raw tokens are temporary local test material and are not included in Git.
