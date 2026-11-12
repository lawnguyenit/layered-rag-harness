# Conversation history store

- Giai đoạn thêm vào: Runtime Tier 1 context loading
- Làm gì: lưu và nạp các lượt trước theo cặp `(conversation_id, authenticated subject)` để parser chỉ thấy lịch sử thuộc actor.
- Nhận gì: conversation ID và actor subject từ token đã xác thực; utterance hiện tại.
- Trả gì: tối đa 8 lượt trước hoặc trạng thái không tồn tại/không thuộc actor.
- Phụ thuộc vào: SQLite adapter, file dưới `data/private/`.
- Có thể hỏng thế nào (và hậu quả): mất file làm mất hội thoại; SQLite local không phù hợp nhiều instance; giữ prompt có yêu cầu retention/deletion và bảo vệ dữ liệu.
- Quyền được kiểm ở đâu: mọi SELECT/INSERT gắn cả conversation ID và authenticated subject; không nhận `history` từ request body.
- Kiểm tra bằng cách nào (test nào): ownership isolation trong `tests/test_api_ingress.py`; production DB adapter cần cùng contract tests.
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): `I-023`–`I-026` tham chiếu ngữ cảnh, chưa có điểm đo thật.
- Chưa quyết định / chưa biết: retention/deletion, production store, có cần lưu lượt assistant sau này không.
