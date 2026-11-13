# Host: business store và API (exact-ID records)

- Giai đoạn thêm vào: H1 trong docs/HOST-SYSTEM-PLAN.md (nhánh C1 của sơ đồ). Nằm trong `host/`, một dự án riêng với harness (`src/lrh`).
- Làm gì: trả một đơn, phiếu hoặc hóa đơn theo mã định danh, chỉ khi người hỏi được phép xem.
- Nhận gì: `Actor` đã xác thực, `kind` (order|ticket|invoice), `ref_id`.
- Trả gì: `BusinessRecord` hoặc `None`. Không có quyền và không tồn tại cho cùng kết quả `None`.
- Phụ thuộc vào: adapter `memory` (tham chiếu, lọc bằng Python) và `postgres` (bảng `records`, Alembic `0001`, `compose.db.yaml`). Dữ liệu nạp từ `data/corpus` bằng `python -m bepmay_host.seed` (chạy trong `host/`).
- Có thể hỏng thế nào (và hậu quả): ở H1 quyền được áp bằng mệnh đề WHERE trong từng truy vấn, nên một truy vấn viết mới quên mệnh đề đó sẽ rò rỉ. H2 chuyển sang RLS với role không bypass để lỗi kiểu này không còn phụ thuộc người viết truy vấn.
- Quyền được kiểm ở đâu: `is_visible` (host/src/bepmay_host/access.py) cho adapter memory; mệnh đề WHERE trong postgres_store.py. Harness không áp lại quy tắc này, chỉ chuyển tiếp token và nhận kết quả. Cùng quy tắc DATA-CONTRACT mục 3.
- Kiểm tra bằng cách nào (test nào): host/tests/test_store_contract.py (cả hai adapter; Postgres cần `HOST_TEST_DATABASE_URL`) và host/tests/test_api.py (401, 404 giống nhau cho bị chặn và không tồn tại, mã tham chiếu sai định dạng, audience sai). Phía harness: tests/test_business_lookup.py kiểm adapter HTTP bằng máy chủ giả. Đã thử phá điều kiện chủ sở hữu trong SQL: 3 test báo lỗi.
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): chưa có. Nhánh C1 chưa nối vào API và chưa có bộ đo cho nó; ghi rõ để không tính là đã sửa lỗi nào.
- Chưa quyết định / chưa biết: đã có pool (`psycopg_pool`, 1–8 kết nối, mỗi lần gọi một transaction); chưa có role app tách khỏi chủ DB (H2); chưa kiểm hiệu năng.
- Token: harness chuyển tiếp nguyên bearer token của người dùng tới host (`src/lrh/business.py`). Host kiểm audience riêng (`HOST_OIDC_AUDIENCE`), nên token phải mang cả hai audience hoặc phải đổi token. Chuyển tiếp token là cách đơn giản nhưng nới quyền của token; cách chuẩn hơn là token exchange [kiến thức chung, chưa kiểm nguồn]. Chưa kiểm với Keycloak thật.
