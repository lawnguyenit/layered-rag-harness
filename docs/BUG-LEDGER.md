# Sổ lỗi

Mỗi lỗi một dòng. Cột đúng theo yêu cầu của chủ repo: sinh ra khi nào, xảy ra khi nào, sửa được không, ảnh hưởng.

| ID | Phát hiện bởi | Sinh ra khi nào (giai đoạn/commit) | Xảy ra khi nào (điều kiện) | Sửa được không | Ảnh hưởng | Trạng thái |
|---|---|---|---|---|---|---|
| B-001 | test (tests/test_throttled.py::test_spend_guard_free_tier_never_blocks) | 2026-11-08, khi viết SpendGuard (src/lrh/limiter.py) | SPEND_CAP_USD=0 với mô hình giá 0: mọi lượt gọi bị chặn vì kiểm `spent >= cap` | có, đã sửa: kiểm chi phí dự kiến của lượt trước khi gọi | nếu không bắt thì cấu hình miễn phí hợp lý nhất làm hệ thống không chạy được | đã sửa, có test hồi quy |
| B-002 | `uv sync` trên máy chủ repo (2026-11-08, bước 0.6) | commit af07368 (bước 0.5): thêm google-genai, python-dotenv vào pyproject.toml nhưng không tạo lại uv.lock | mọi lần cài từ commit đó: uv phải giải lại phụ thuộc (thêm 21 gói, google-genai ra 2.34.0 trong khi mã được kiểm trên 2.33.0) | có: uv.lock tạo lại bằng uv 0.10.6 trên máy chủ repo và commit cùng bước 0.6 | lock không ghim gói mạng nào, nên "phụ thuộc ghim phiên bản" ở GATES.md là sai cho tới khi sửa; chưa có kiểm tự động lock khớp pyproject (`uv lock --check` trong CI, giai đoạn 4) | đã sửa, chưa có kiểm hồi quy |

