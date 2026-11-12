# HTTP ingress and OIDC authentication

- Giai đoạn thêm vào: Runtime Tier 1 (implemented; bounded local HTTP smoke verified; project gate remains open for semantic safety and production concerns)
- Làm gì: nhận HTTP request có giới hạn kích thước, xác thực bearer JWT theo issuer/audience/JWKS, dựng actor tin cậy, giới hạn request theo subject và trả mã lỗi an toàn.
- Nhận gì: `UserRequest` + `Authorization: Bearer`; cấu hình `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL`.
- Trả gì: actor context nội bộ hoặc HTTP 4xx; `/v1/route` trả route plan, không sinh câu trả lời.
- Phụ thuộc vào: FastAPI, PyJWT, OIDC discovery/JWKS của issuer; Keycloak 26.8.2 cho local dev/test. Keycloak image/version checked 2026-11-12: https://www.keycloak.org/downloads and https://www.keycloak.org/getting-started/getting-started-docker. PyJWT JWKS usage checked 2026-11-12: https://pyjwt.readthedocs.io/en/latest/usage.html.
- Có thể hỏng thế nào (và hậu quả): cấu hình issuer/audience sai làm chặn người dùng thật; JWKS outage làm auth không xác thực được; thiếu distributed rate limiting không đủ khi chạy nhiều worker/replica; Keycloak `start-dev` chỉ dành local.
- Quyền được kiểm ở đâu: token signature/issuer/audience/expiry in `lrh.oidc`; exactly one application role is required from the allowlist; `customer_id` is read from a token claim for customers. Authorization filtering over protected data is not implemented here.
- Kiểm tra bằng cách nào (test nào): `tests/test_api_ingress.py` passes in the independent focused/full runs recorded in `docs/project-state/verification.md`; local Keycloak 26.8.2 + Uvicorn loopback smoke verified 401 without bearer, 422 for body role spoof, and 200 with a valid claim-derived customer actor. The smoke used a direct access grant and hardcoded `customer_id`; Authorization Code + PKCE and per-user attribute mapping remain unverified.
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): chưa đo câu trả lời; auth/access-scope contract có bộ test riêng, bao gồm claim giả trong body và owner khác.
- Chưa quyết định / chưa biết: semantic input-safety policy; production issuer, TLS/reverse proxy, distributed limiter, refresh/session UX, retention policy cho hội thoại.
