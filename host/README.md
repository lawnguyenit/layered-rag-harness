# bepmay-host: hệ thống chủ tổng hợp

Hệ thống nghiệp vụ giả (Bếp Mây: đơn, phiếu hỗ trợ, hóa đơn) mà harness cắm vào. Nó **sở hữu** dữ liệu, xác thực và quy tắc quyền; harness không có quyền truy cập trực tiếp vào cơ sở dữ liệu của nó. Chỉ dùng dữ liệu tổng hợp từ `../data/corpus`.

Ranh giới với harness: harness gọi `GET /v1/{orders|tickets|invoices}/{mã}` kèm bearer token của người dùng (`src/lrh/business.py`). Host tự kiểm token, tự lọc quyền, trả 404 như nhau cho "không có quyền" và "không tồn tại".

## Chạy
```bash
cd host
export POSTGRES_PASSWORD=<giá trị cục bộ>   # chỉ trong .env cục bộ, không commit
docker compose up -d --wait                  # postgres:16-alpine, 127.0.0.1:55432
export DATABASE_URL=postgresql://lrh:$POSTGRES_PASSWORD@127.0.0.1:55432/lrh
uv sync && uv run alembic upgrade head && uv run python -m bepmay_host.seed
uv run pytest                                # thêm HOST_TEST_DATABASE_URL=$DATABASE_URL để chạy cả adapter Postgres
uv run uvicorn bepmay_host.server:app --port 8020   # cần HOST_OIDC_ISSUER, HOST_OIDC_AUDIENCE, HOST_OIDC_JWKS_URL
```

## Chưa có
Row-level security với role không bypass (H2); connection pool; chạy cả hai hệ thống trong một compose; kiểm với Keycloak thật.
