# Intent parser and route planner

- Giai đoạn thêm vào: Runtime Tier 2 (implementation in progress; project gate not closed)
- Làm gì: lấy parse ứng viên intent/task, slot, polarity, negation và tham chiếu; kiểm tra deterministic theo route catalog; trả `route`, `clarify`, `unsupported`, hoặc `no_action`.
- Nhận gì: câu hỏi hiện tại, lịch sử do server nạp theo actor, route catalog có phiên bản.
- Trả gì: parser candidates plus 0..N validated route tasks; non-route decisions have no dispatchable tasks. It does not call RAG/tools or grant permissions.
- Phụ thuộc vào: `IntentParser` port; `ModelIntentParser` dùng `ModelAdapter` và schema Pydantic; `RoutePlanner` kiểm ID/slot bắt buộc/polarity.
- Có thể hỏng thế nào (và hậu quả): LLM hiểu sai phủ định hoặc tham chiếu; schema hợp lệ vẫn có thể sai ngữ nghĩa; lỗi provider không được biến thành route.
- Quyền được kiểm ở đâu: role/customer scope chỉ từ `Actor`; actor text trong prompt không thay đổi scope. Bộ lọc quyền dữ liệu phải chạy ở bước truy xuất sau này.
- Kiểm tra bằng cách nào (test nào): contract cases in `tests/test_api_ingress.py` pass independently; semantic benchmark in `eval/intent/` awaits gold approval and a live model run; latency/cost/load remain separate.
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): draft `I-001`–`I-030`; chưa có kết quả parser đo thật.
- Chưa quyết định / chưa biết: gold labels và taxonomy cuối cùng; operating point; chất lượng thật của model cho tiếng Việt; chi phí/latency thực nghiệm.
