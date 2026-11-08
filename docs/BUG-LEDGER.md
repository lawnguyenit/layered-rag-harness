# Sổ lỗi

Mỗi lỗi một dòng. Cột đúng theo yêu cầu của chủ repo: sinh ra khi nào, xảy ra khi nào, sửa được không, ảnh hưởng.

| ID | Phát hiện bởi | Sinh ra khi nào (giai đoạn/commit) | Xảy ra khi nào (điều kiện) | Sửa được không | Ảnh hưởng | Trạng thái |
|---|---|---|---|---|---|---|
| B-001 | test (tests/test_throttled.py::test_spend_guard_free_tier_never_blocks) | 2026-11-08, khi viết SpendGuard (src/lrh/limiter.py) | SPEND_CAP_USD=0 với mô hình giá 0: mọi lượt gọi bị chặn vì kiểm `spent >= cap` | có, đã sửa: kiểm chi phí dự kiến của lượt trước khi gọi | nếu không bắt thì cấu hình miễn phí hợp lý nhất làm hệ thống không chạy được | đã sửa, có test hồi quy |

