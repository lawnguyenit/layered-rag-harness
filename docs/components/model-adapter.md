# Adapter mô hình (và các lớp bọc)

- Giai đoạn thêm vào: 0
- Làm gì: giữ một hợp đồng duy nhất giữa lõi và nhà cung cấp mô hình, để đổi mô hình hoặc hãng chỉ là đổi cấu hình. Ba lớp bọc quanh adapter: bộ nhớ đệm, bộ giới hạn tốc độ (RPM/TPM/RPD), trần chi tiêu.
- Nhận gì: `GenerateRequest` (messages, temperature, max_output_tokens, tools tùy chọn); `embed(texts, task)`.
- Trả gì: `GenerateResult` (text, tool_calls, usage, model_id, provider, latency_ms, cache_hit, retries, rate_limited); `EmbedResult`.
- Phụ thuộc vào: pydantic, `google-genai` (adapter Gemini, `adapters/gemini.py`), `python-dotenv` (`config.py`). Bảng hạn mức từng mô hình ở `limits_table.py`; `factory.py` dựng Cached(Throttled(Gemini)).
- Có thể hỏng thế nào (và hậu quả):
  - Hệ số ước lượng token `CHARS_PER_TOKEN = 2.0` (bước 0.6, đo bằng countTokens 2026-11-08, `eval/results/token-profile-2026-11-08.json`): cố ý ước cao khoảng 35% trên corpus hiện tại; văn bản nhiều chữ số (hóa đơn) đặc token hơn, 3/63 mục vẫn bị ước thấp tới 11%. Corpus đo nhỏ (5.231 ký tự), chưa đại diện cho prompt RAG dài; đo lại khi có system prompt và ngữ cảnh truy xuất. Hệ số cũ 3.0 ước thấp 36/63 mục.
  - Bộ giới hạn chỉ đếm trong một tiến trình: chạy hai bộ chạy cùng lúc sẽ cùng tiêu hạn mức project mà không biết nhau.
  - Mỗi lần thử lại tính là một lượt RPD (thận trọng); nếu nhà cung cấp không đếm lượt lỗi thì ta tiêu hao quá tay.
  - Bộ đệm chỉ áp dụng khi temperature = 0; thay đổi system prompt đổi khóa đệm (đúng), nhưng đổi hành vi phía nhà cung cấp mà giữ nguyên tên mô hình thì đệm cũ vẫn trả kết quả cũ.
  - Mốc reset RPD theo giờ Thái Bình Dương là suy từ tài liệu Google (chưa quan sát thực tế).
- Quyền được kiểm ở đâu: không kiểm ở đây. Adapter mô hình không biết người dùng; quyền do lớp truy xuất (giai đoạn 1) và guardrails (giai đoạn 3).
- Kiểm tra bằng cách nào (test nào): `tests/test_gemini_adapter.py` (client giả dùng kiểu dữ liệu SDK thật: ánh xạ vai trò, đếm token, phản hồi rỗng, 429 RetryInfo/PerDay, bẫy vector gộp của embedding-2); `tests/test_live.py` (gọi thật, mặc định bỏ qua: `LRH_LIVE=1 uv run pytest -m live -s`); `tests/test_adapter_contract.py` (mọi adapter), `test_cache.py`, `test_limiter.py`, `test_throttled.py`, `test_results_cli.py`. Chạy: `uv run pytest`. Các test này do cùng agent viết mã viết nên chưa phải kiểm thử độc lập (xem AGENTS.md).
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): chưa có (giai đoạn 0 là điểm gốc, chưa sửa lỗi nào).
- Đã quan sát (live smoke test, 2026-11-08, google-genai 2.34.0, một lần chạy): `gemma-4-31b-it` trả "Hello" sau 48 s, `prompt_tokens=13`, `output_tokens=155` (gồm token suy nghĩ) với `max_output_tokens=256`; embedding 2 văn bản ra 2 vector. countTokens chạy được cho cả Gemma và gemini-embedding-2, và số của nó (13) khớp `prompt_token_count` của lời gọi sinh, tức không có token phụ của khuôn chat. Một lần đo, chưa phải p50.
- Chưa quyết định / chưa biết: vì sao độ trễ 48 s (suy nghĩ mặc định của Gemma? hàng đợi tầng Free?) và token suy nghĩ có ăn hết `max_output_tokens` ở câu dài hơn không, phải kiểm trước khi chạy điểm gốc; countTokens có tính vào RPM/RPD không; việc nhận diện hết lượt ngày dựa vào chuỗi "PerDay" trong quotaId là suy đoán; `thinking_level` chưa đặt cho Gemma; token embedding là ước lượng; hành vi thật của Gemma khi một yêu cầu vượt 16K token/phút (bị từ chối hay chờ); cách Gemini API báo `retry_after`; có tính lượt lỗi vào RPD hay không.
