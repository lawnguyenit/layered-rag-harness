# Host: vết chạy, sao lưu/khôi phục, CI

- Giai đoạn thêm vào: H6 trong docs/HOST-SYSTEM-PLAN.md.
- Làm gì: (1) ghi một dòng JSON có cấu trúc cho mỗi request; (2) chứng minh một bản sao lưu khôi phục được cả dữ liệu lẫn quy tắc quyền; (3) chạy test tự động trên mỗi push; (4) đưa vết thật vào viewer docs/architecture.
- Nhận gì: request HTTP vào host; `HOST_TRACE_FILE` (tùy chọn) để ghi JSONL; Docker cho bản kiểm sao lưu.
- Trả gì: dòng vết (`request_id`, route mẫu, status, outcome, latency, role, mã định danh người dùng đã băm 8 ký tự, kind, ref hợp lệ, `result_count`); header `x-request-id`; `docs/architecture/host-traces.js` do `scripts/record_host_traces.py` sinh ra.
- Phụ thuộc vào: `host/src/bepmay_host/trace.py`, `scripts/backup_restore_check.py`, `.github/workflows/ci.yml`, `scripts/record_host_traces.py`.
- Có thể hỏng thế nào (và hậu quả):
  - Vết không bao giờ ghi token, nội dung câu hỏi, thân bản ghi, hay mã không hợp lệ (có test). Nếu sau này thêm trường mới, phải qua cùng bộ test đó.
  - `pg_dump` mặc định **không mang role**: khôi phục chỉ dump cơ sở dữ liệu cho ra DB không còn role `bepmay_app` và không còn policy RLS (đã chứng minh bằng ca đối chứng). Phải dump role riêng (`pg_dumpall --roles-only`); lệnh này mang cả băm mật khẩu nên file role là bí mật.
  - Lệch đồng hồ giữa Keycloak và host làm token vừa cấp bị từ chối vì `iat` ở tương lai (đo được 0,4–0,6 s). Host có `leeway` 30 giây (cấu hình `HOST_OIDC_LEEWAY_SECONDS`, tối đa 120).
- Quyền được kiểm ở đâu: không thêm quy tắc quyền mới. Bản kiểm khôi phục chạy lại 89 test RLS/hợp đồng/search của host trên cơ sở dữ liệu đã khôi phục, bằng role app với mật khẩu cũ.
- Kiểm tra bằng cách nào (test nào): host/tests/test_trace.py (9 test: trường, mã vết khớp header, denied và missing giống nhau, không lộ truy vấn/token/đầu vào lạ, request id lạ bị thay, tệp JSONL, CORS đúng danh sách); host/tests/test_api.py (leeway); `scripts/backup_restore_check.py` (3 container tạm, 4 kiểm tra cấu trúc, 89 test, 1 ca đối chứng).
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): chưa có.
- Chưa quyết định / chưa biết:
  - **CI chưa chạy trên GitHub**: workflow mới được viết và kiểm cú pháp YAML, các bước tương đương đã chạy cục bộ. Phiên bản action (`checkout@v4`, `setup-uv@v5`, `setup-node@v4`) chưa kiểm nguồn hôm nay.
  - Vết chỉ ghi ra tệp/logger; chưa có thu thập tập trung, chưa có cảnh báo, chưa có xoay vòng tệp.
  - Viewer đọc `host-traces.js` đã sinh sẵn (ảnh chụp tại một thời điểm), không phải luồng trực tiếp; cần chạy lại `record_host_traces.py` để làm mới.
  - Bản kiểm sao lưu dùng dữ liệu tổng hợp nhỏ; chưa đo thời gian khôi phục, chưa thử sao lưu liên tục (PITR).
