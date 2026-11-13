# Host: business store và API (exact-ID records)

- Giai đoạn thêm vào: H1 (kho) và H2 (RLS) trong docs/HOST-SYSTEM-PLAN.md (nhánh C1 của sơ đồ). Nằm trong `host/`, một dự án riêng với harness (`src/lrh`).
- Làm gì: trả một đơn, phiếu hoặc hóa đơn theo mã định danh, chỉ khi người hỏi được phép xem.
- Nhận gì: `Actor` đã xác thực, `kind` (order|ticket|invoice), `ref_id`.
- Trả gì: `BusinessRecord` hoặc `None`. Không có quyền và không tồn tại cho cùng kết quả `None`.
- Phụ thuộc vào: adapter `memory` (tham chiếu, lọc bằng Python) và `postgres` (bảng `records`, Alembic `0001`, RLS `0002`, `host/compose.yaml`). Dữ liệu nạp từ `data/corpus` bằng `python -m bepmay_host.seed` (chạy trong `host/`).
- Có thể hỏng thế nào (và hậu quả): nếu server kết nối bằng role chủ bảng hoặc superuser thì RLS bị bỏ qua và truy vấn không còn WHERE quyền nên rò toàn bộ; nếu quên `set_config` thì policy đóng kín (0 dòng, lỗi dễ thấy). Cấp thêm quyền ghi cho role app cũng làm test đỏ.
- Quyền được kiểm ở đâu: policy `records_visible` trong host/migrations/versions/0002_rls.py (Postgres), `is_visible` trong access.py cho adapter memory. Adapter chỉ đặt `app.role` và `app.customer_id` bằng `set_config(..., true)` trong transaction. Harness không áp lại quy tắc này.
- Kiểm tra bằng cách nào (test nào): host/tests/test_store_contract.py (hai adapter; Postgres chạy bằng role app), host/tests/test_rls.py (14 ca chạy SQL thô không WHERE bằng role không bypass: không đặt chủ thể, đoán mã, ghi trái quyền, rò giữa các transaction), host/tests/test_api.py. Đã thử phá policy (bỏ điều kiện chủ sở hữu: 6 test đỏ; policy luôn đúng: 14 đỏ).
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): chưa có. Nhánh C1 chưa nối vào API và chưa có bộ đo cho nó; ghi rõ để không tính là đã sửa lỗi nào.
- Chưa quyết định / chưa biết: pool 1–8 kết nối chưa đo tải; chưa có role riêng cho seed ngoài chủ bảng; chưa kiểm hiệu năng RLS; RLS không bảo vệ theo cột (nếu sau này có cột nhạy cảm cần view hoặc GRANT theo cột).
- Token: harness chuyển tiếp nguyên bearer token của người dùng tới host (`src/lrh/business.py`). Host kiểm audience riêng (`HOST_OIDC_AUDIENCE`), nên token phải mang cả hai audience hoặc phải đổi token. Chuyển tiếp token là cách đơn giản nhưng nới quyền của token; cách chuẩn hơn là token exchange [kiến thức chung, chưa kiểm nguồn]. Chưa kiểm với Keycloak thật.
