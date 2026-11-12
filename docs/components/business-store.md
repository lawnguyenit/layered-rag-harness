# Business store (exact-ID records)

- Giai đoạn thêm vào: H1 trong docs/HOST-SYSTEM-PLAN.md (nhánh C1 của sơ đồ).
- Làm gì: trả một đơn, phiếu hoặc hóa đơn theo mã định danh, chỉ khi người hỏi được phép xem.
- Nhận gì: `Actor` đã xác thực, `kind` (order|ticket|invoice), `ref_id`.
- Trả gì: `BusinessRecord` hoặc `None`. Không có quyền và không tồn tại cho cùng kết quả `None`.
- Phụ thuộc vào: adapter `memory` (tham chiếu, lọc bằng Python) và `postgres` (bảng `records`, Alembic `0001`, `compose.db.yaml`). Dữ liệu nạp từ `data/corpus` bằng `python -m lrh.datastore.seed`.
- Có thể hỏng thế nào (và hậu quả): ở H1 quyền được áp bằng mệnh đề WHERE trong từng truy vấn, nên một truy vấn viết mới quên mệnh đề đó sẽ rò rỉ. H2 chuyển sang RLS với role không bypass để lỗi kiểu này không còn phụ thuộc người viết truy vấn.
- Quyền được kiểm ở đâu: `is_visible` (contracts.py) cho adapter memory; mệnh đề WHERE trong postgres.py. Cùng quy tắc DATA-CONTRACT mục 3.
- Kiểm tra bằng cách nào (test nào): tests/test_datastore_contract.py, chạy trên cả hai adapter; adapter Postgres chỉ chạy khi có `LRH_TEST_DATABASE_URL`. Đã thử phá điều kiện chủ sở hữu trong SQL: 3 test báo lỗi.
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): chưa có. Nhánh C1 chưa nối vào API và chưa có bộ đo cho nó; ghi rõ để không tính là đã sửa lỗi nào.
- Chưa quyết định / chưa biết: kết nối mỗi lần gọi (chưa có pool); chưa có role app tách khỏi chủ DB (H2); chưa kiểm hiệu năng.
