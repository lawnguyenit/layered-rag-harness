# bepmay-host: hệ thống chủ tổng hợp

Quyền đọc do chính Postgres thực thi (row-level security, role không bypass), không nằm trong câu truy vấn.

Hệ thống nghiệp vụ giả (Bếp Mây: đơn, phiếu hỗ trợ, hóa đơn) mà harness cắm vào. Nó **sở hữu** dữ liệu, xác thực và quy tắc quyền; harness không có quyền truy cập trực tiếp vào cơ sở dữ liệu của nó. Chỉ dùng dữ liệu tổng hợp từ `../data/corpus`.

Ranh giới với harness: harness gọi `GET /v1/{orders|tickets|invoices}/{mã}` kèm bearer token của người dùng (`src/lrh/business.py`). Host tự kiểm token, tự lọc quyền, trả 404 như nhau cho "không có quyền" và "không tồn tại".

## Chạy
```bash
cd host
export POSTGRES_PASSWORD=<giá trị cục bộ>   # chỉ trong .env cục bộ, không commit
docker compose up -d --wait                  # postgres:16-alpine, 127.0.0.1:55432
# Hai role: chủ bảng (migrate, seed) và role app không bypass (server, chỉ SELECT, chịu RLS).
export MIGRATE_DATABASE_URL=postgresql://lrh:$POSTGRES_PASSWORD@127.0.0.1:55432/lrh
export HOST_APP_PASSWORD=<giá trị cục bộ khác>   # không commit
export DATABASE_URL=postgresql://bepmay_app:$HOST_APP_PASSWORD@127.0.0.1:55432/lrh
uv sync && uv run alembic upgrade head && uv run python -m bepmay_host.provision && uv run python -m bepmay_host.seed && uv run python -m bepmay_host.ingest
uv run pytest        # thêm HOST_TEST_DATABASE_URL=$MIGRATE_DATABASE_URL HOST_TEST_APP_DATABASE_URL=$DATABASE_URL để chạy adapter Postgres và test RLS
uv run uvicorn bepmay_host.server:app --port 8020   # cần HOST_OIDC_ISSUER, HOST_OIDC_AUDIENCE, HOST_OIDC_JWKS_URL
```

## Chạy cả API trong container
```bash
export HOST_APP_PASSWORD=... HOST_OIDC_ISSUER=... HOST_OIDC_AUDIENCE=... HOST_OIDC_JWKS_URL=...   # Keycloak của bạn
docker compose --profile api up -d --build --wait   # postgres + host-api trên 127.0.0.1:8020
```
Container tự `alembic upgrade head`, đặt mật khẩu role app, seed và ingest chunk (idempotent), rồi chạy uvicorn bằng user không phải root và kết nối bằng role app. Context build là gốc repo vì seed đọc `data/corpus`. `docker compose up` không kèm profile vẫn chỉ chạy postgres.

## Kiểm đầu-cuối với Keycloak
`scripts/e2e_host_keycloak.py` (chạy từ gốc repo) dựng realm thử, lấy token thật và gọi host bằng client của harness: 17/17 đạt, xem docs/lab/host-keycloak-e2e-2026-11-13.md. Server từ chối khởi động nếu kết nối bằng role chủ bảng/superuser hoặc bảng chưa bật RLS.

## Tìm kiếm (H4)
`POST /v1/search {"query": "...", "top_k": 5}` với bearer token. Mặc định `HOST_EMBEDDER=hash` (xác định, không cần khóa, chỉ để thử đường ống và quyền). Embedding thật: `HOST_EMBEDDER=gemini` và `HOST_EMBEDDING_API_KEY` (khóa chỉ trong .env cục bộ), rồi chạy lại `ingest`. Xem docs/components/host-search.md.

## Chưa có
Một token dùng được cho cả harness và host (cần token exchange hoặc hai audience); chạy harness cùng compose; harness thực thi nhánh C1 (H3).
