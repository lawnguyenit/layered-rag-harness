# Adapter mô hình (và các lớp bọc)

- Giai đoạn thêm vào: 0
- Làm gì: giữ một hợp đồng duy nhất giữa lõi và nhà cung cấp mô hình, để đổi mô hình hoặc hãng chỉ là đổi cấu hình. Ba lớp bọc quanh adapter: bộ nhớ đệm, bộ giới hạn tốc độ (RPM/TPM/RPD), trần chi tiêu.
- Nhận gì: `GenerateRequest` (messages, temperature, max_output_tokens, tools tùy chọn); `embed(texts, task)`.
- Trả gì: `GenerateResult` (text, tool_calls, usage, model_id, provider, latency_ms, cache_hit, retries, rate_limited); `EmbedResult`.
- Phụ thuộc vào: pydantic, `google-genai` (adapter Gemini, `adapters/gemini.py`), `python-dotenv` (`config.py`). Bảng hạn mức từng mô hình ở `limits_table.py`; `factory.py` dựng Cached(Throttled(Gemini)).
- Có thể hỏng thế nào (và hậu quả):
  - Hệ số ước lượng token (`CHARS_PER_TOKEN = 3.0`) là phỏng đoán chưa hiệu chỉnh cho tiếng Việt: ước thấp thì vượt TPM thật và bị 429; ước cao thì chạy chậm hơn cần thiết. Bước 0.6 thay bằng số đo.
  - Bộ giới hạn chỉ đếm trong một tiến trình: chạy hai bộ chạy cùng lúc sẽ cùng tiêu hạn mức project mà không biết nhau.
  - Mỗi lần thử lại tính là một lượt RPD (thận trọng); nếu nhà cung cấp không đếm lượt lỗi thì ta tiêu hao quá tay.
  - Bộ đệm chỉ áp dụng khi temperature = 0; thay đổi system prompt đổi khóa đệm (đúng), nhưng đổi hành vi phía nhà cung cấp mà giữ nguyên tên mô hình thì đệm cũ vẫn trả kết quả cũ.
  - Mốc reset RPD theo giờ Thái Bình Dương là suy từ tài liệu Google (chưa quan sát thực tế).
- Quyền được kiểm ở đâu: không kiểm ở đây. Adapter mô hình không biết người dùng; quyền do lớp truy xuất (giai đoạn 1) và guardrails (giai đoạn 3).
- Kiểm tra bằng cách nào (test nào): `tests/test_gemini_adapter.py` (client giả dùng kiểu dữ liệu SDK thật: ánh xạ vai trò, đếm token, phản hồi rỗng, 429 RetryInfo/PerDay, bẫy vector gộp của embedding-2); `tests/test_live.py` (gọi thật, mặc định bỏ qua: `LRH_LIVE=1 uv run pytest -m live -s`); `tests/test_adapter_contract.py` (mọi adapter), `test_cache.py`, `test_limiter.py`, `test_throttled.py`, `test_results_cli.py`. Chạy: `uv run pytest`. Các test này do cùng agent viết mã viết nên chưa phải kiểm thử độc lập (xem AGENTS.md).
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): chưa có (giai đoạn 0 là điểm gốc, chưa sửa lỗi nào).
- Chưa quyết định / chưa biết: lời gọi mạng thật chưa từng chạy (chỉ kiểm bằng client giả); việc nhận diện hết lượt ngày dựa vào chuỗi "PerDay" trong quotaId là suy đoán; `thinking_level` chưa đặt cho Gemma; token embedding là ước lượng; hành vi thật của Gemma khi một yêu cầu vượt 16K token/phút (bị từ chối hay chờ); cách Gemini API báo `retry_after`; có tính lượt lỗi vào RPD hay không.
