# Kế hoạch hệ thống chủ (host) để gắn harness vào

Soạn: 2026-11-13, thay bản "PIVOT-PLAN" trước đó (hiểu sai ý chủ repo). Trạng thái: [đề xuất], chờ chủ repo xác nhận. Chưa làm mục nào.

## 1. Ý định
- Không đổi dự án, không làm lại theo job Upwork nào. Job chỉ là tín hiệu về công nghệ thị trường hay hỏi (Python/FastAPI, PostgreSQL, React/TypeScript, Docker Compose; xem PLAN.md mục 2).
- Vấn đề thật: harness tự xây chưa gắn vào hệ thống nào để thử. Cần một **hệ thống chủ** nhỏ, tổng hợp, mà harness cắm vào, đúng như sơ đồ docs/architecture.
- Hệ thống chủ **chính là Bếp Mây** đang dùng làm fixture (đơn, ticket, hóa đơn, tài liệu). Không thêm miền thứ hai.
- docs/architecture là nơi demo. Hệ thống chủ phải cho ra vết chạy thật để thay các kịch bản mô phỏng trong viewer.

## 2. Công nghệ nằm ở đâu trong sơ đồ
| Công nghệ | Nút trong sơ đồ | Hiện trạng |
|---|---|---|
| Python/FastAPI | Tầng 1 Ingress, Auth, route plan | Đã có, test pass |
| OIDC/Keycloak + Docker | Nút 3 Auth | Đã thử cục bộ (compose chỉ có Keycloak) |
| PostgreSQL (dữ liệu nghiệp vụ: đơn, ticket, hóa đơn) | Nhánh C1 tra theo mã định danh + nút 4 `access_scope` | Chưa có |
| PostgreSQL + pgvector (đoạn tài liệu) | A4 kho/chỉ mục, nhánh C2 | Chưa có (kế hoạch G1) |
| React/TypeScript | Nút 1 người dùng nhập, hiển thị trả lời, route plan, trích nguồn | Chưa có |
| Docker Compose cả hệ thống | Hạ tầng L4 | Chưa có, chỉ Keycloak |

Postgres vì thế có hai vai: dữ liệu đơn/ticket/hóa đơn cho C1, và đoạn tài liệu cho C2. Cả hai đứng sau adapter, qua cùng test hợp đồng gồm ca "người không có quyền".

## 2b. Tách đôi (làm 2026-11-13)
Host nằm trong `host/` như dự án riêng (pyproject, compose, migration, API, test riêng); harness chỉ có cổng `BusinessLookup` và client HTTP. Mỗi hệ thống tự kiểm token và tự giữ quy tắc của mình. Hệ quả cho các bước dưới: H2 (RLS) và dữ liệu thuộc host; H3 là phần harness gọi host.

## 2c. Tiến độ host (2026-11-13)
Đã có: Postgres + Alembic + seed, API chỉ đọc có kiểm token, connection pool, Dockerfile và `docker compose --profile api` (dựng từ trạng thái sạch, `/healthz` ok, thiếu token trả 401). Đã xong H2 (RLS), kiểm Keycloak thật và chốt chặn khởi động, H4 (pgvector: `POST /v1/search`, `chunks` dưới RLS, ingest idempotent; embedder Gemini chưa kiểm thật, chất lượng chưa đo). Còn lại phía host: quyết cách một token dùng cho cả hai hệ thống (pgvector). React (H5) và vết chạy (H6) là phần sau.

## 2d. H2 — RLS (làm 2026-11-13, agent viết theo yêu cầu chủ repo)
Xong: migration `0002`, adapter dùng `set_config`, hai URL (chủ/app), `provision`. Thiết kế ban đầu, giữ để đối chiếu. Test nghiệm thu: `host/tests/test_rls.py`, cần `HOST_TEST_DATABASE_URL` (chủ bảng) và `HOST_TEST_APP_DATABASE_URL` (role `bepmay_app`). Các việc cần viết:
1. Migration `0002`: tạo role `bepmay_app` NOSUPERUSER NOBYPASSRLS, chỉ `GRANT SELECT ON records` (mật khẩu đặt ngoài migration); `ENABLE` + `FORCE ROW LEVEL SECURITY`; một policy `FOR SELECT TO bepmay_app`.
2. Policy đọc chủ thể từ `current_setting('app.role', true)` và `app.customer_id` (tham số `true` để thiếu thì ra NULL, đóng kín; chuỗi rỗng coi là không có customer).
3. Adapter: bỏ WHERE quyền, mở transaction, `set_config('app.role', ..., true)` và `app.customer_id` (tham số thứ ba `true` = chỉ trong transaction, tương đương SET LOCAL nhưng nhận tham số bind). Server kết nối bằng role app; seed/migration dùng role chủ.
4. Compose/Dockerfile: hai URL (`DATABASE_URL` cho role app, `MIGRATE_DATABASE_URL` cho chủ).
Xong khi cả `test_rls.py` và `test_store_contract.py` đều xanh với role app.

## 2e. Hoàn tất host (2026-11-13)
H5 (web/: PKCE, tra cứu, tìm kiếm, 7 ca Chrome khách A/B), H6 (vết có cấu trúc, kiểm sao lưu/khôi phục thật, CI, vết thật trong viewer) và token exchange (harness đổi token người dùng lấy token cho host, 29/29 e2e) đã làm. Quyết định token: **token exchange** (RFC 8693), vì mỗi hệ thống chỉ nhận token gửi cho nó và `azp` cho host biết harness là bên gọi. Chưa làm ở host: ô hỏi đáp qua harness trong giao diện (chờ harness), CI chưa chạy trên GitHub, embedder Gemini thật chưa gọi, HTTPS, đo tải.

## 3. Bước
Phần intent (Tầng 2, 5a) giữ như hiện tại: chờ chủ repo duyệt gold và đo held-out. Các bước dưới là phần đứng sau route plan.

| Bước | Nội dung | Bằng chứng xong | Giờ ước [chưa đo] |
|---|---|---|---|
| H0 | Điều kiện G0: sửa key_fact A-007/B-005/B-006, chạy baseline, lệnh chạy một phát, `.gitignore` cho `output/` và `.playwright-cli/` | Điểm gốc trong repo | 6–10 |
| H1 | Dữ liệu chủ: schema Postgres cho đơn/ticket/hóa đơn có `customer_id`, seed từ fixture tổng hợp, Alembic, compose `api + postgres + keycloak`, cổng khác 8000. Adapter `DataStore` | `docker compose up` từ clone sạch; hợp đồng đạt | 8–12 |
| H2 | `access_scope` thành thật: RLS, role app không bypass (không superuser, không chủ bảng), chủ thể đặt bằng `SET LOCAL` từ actor đã xác thực. **Lõi, chủ repo tự gõ** | Nhóm E: tra đơn của khách khác, ID đoán mò, ghi trái quyền đều 0 dòng; test chứng minh role chủ bảng sẽ bypass | 10–14 |
| H3 | Điều phối C1: route task `exact_id_lookup` thành truy vấn chỉ đọc có timeout, dưới scope của actor | Đúng công cụ, đúng tham số; so với intent gold | 6–10 |
| H4 | C2: nạp tài liệu (A1–A4), pgvector, lọc quyền trước khi tìm, trích nguồn | G1: điểm so với baseline, lỗi nào sửa được | 10–14 |
| H5 | React/TS mỏng (Vite): đăng nhập PKCE, chat, bảng route plan và vết chạy. Mọi quyết định quyền nằm ở server | Ca Playwright: khách A không thấy đơn khách B | 10–14 |
| H6 | Xuất vết chạy thật vào viewer docs/architecture thay kịch bản mô phỏng; CI (pytest với postgres, `uv lock --check`, build frontend); sao lưu/khôi phục thật | CI xanh; khôi phục xong thì role, policy, dữ liệu còn nguyên | 8–12 |

Bẫy H6: `pg_dump` mặc định không kèm role và grant ở mức cụm; chứng minh bằng một lần khôi phục thật vào DB trống.

## 4. Cổng
- H2 không đóng khi chưa có test chạy bằng role không bypass.
- H4 chỉ ghi điểm so với baseline H0; chưa có baseline thì ghi "chưa đo".
- Mỗi bước: mục PROCESS-LOG, trang docs/components/, lỗi vào BUG-LEDGER, kiểm thử do agent khác chạy. Dữ liệu chỉ tổng hợp.
- Viewer phải ghi rõ nút nào đã chạy thật, nút nào còn là thiết kế (như hiện nay).

## 5. Chờ chủ repo quyết
1. Dùng Bếp Mây làm hệ thống chủ duy nhất.
2. Thứ tự H0 → H1 → H2 → H3 trước React, hay React sớm để có demo nhìn được.
