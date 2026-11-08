# Kế hoạch nhà cung cấp API (chỉ API, không chạy mô hình cục bộ)

Cập nhật: 2026-11-08. Nguồn: trang giá và tài liệu Gemini API (ai.google.dev, đọc 2026-11-08), bảng giá Anthropic đã tra cùng ngày. Trang giá Gemini không ghi ngày cập nhật. Mọi giá có thể đổi: ghi ID mô hình và ngày vào từng lần đo.

## 1. Quyết định
- **Chỉ dùng tầng miễn phí (chủ repo quyết 2026-11-08).** Cột giá ở mục 2 là giá gói trả phí, chỉ để biết chi phí nếu sau này bật thanh toán; ở tầng miễn phí chi phí là $0. Claude không có trong kế hoạch vì bảng giá Anthropic đã tra không có tầng miễn phí API (chưa kiểm tín dụng thử).
- Bỏ AI cục bộ (chủ repo quyết 2026-11-08). Không còn mục lab "mô hình tự chạy" và "train". Mục 6b trong PLAN.md giữ làm bối cảnh máy, không dùng cho kế hoạch.
- Một lớp adapter nhà cung cấp; hiện chỉ có Gemini. Đổi mô hình qua cấu hình, không sửa mã lõi. Kiểm adapter đổi hãng cần nhà cung cấp thứ hai miễn phí [chưa tra].
- Mô hình sinh và mô hình chấm là hai mô hình khác nhau (ví dụ 3.1 Flash-Lite sinh, 3.5 Flash chấm). Cùng hãng vẫn có thể chung điểm yếu: chấm tay một mẫu để đối chiếu. Lý do tách là kiến thức chung, chưa kiểm nguồn.

## 2. Bảng mô hình (cột giá = giá gói TRẢ PHÍ cho 1 triệu token, đầu vào / đầu ra; tầng miễn phí = $0)
Dòng Claude chỉ để tham khảo, không dùng trong kế hoạch miễn phí.
| Vai trò | Mô hình | Miễn phí? | Giá |
|---|---|---|---|
| Phát triển hằng ngày | Gemini 3.1 Flash-Lite | Có | $0,25 / $1,50 |
| Dự phòng rẻ | Gemini 2.5 Flash-Lite | Có | $0,10 / $0,40 |
| Mức giữa để so | Gemini 3.5 Flash | Có | $1,50 / $9,00 |
| Đo cuối, rẻ | Claude Haiku 5.5 | Không | $0,10 / $0,50 (prompt ≤100K) |
| Đo cuối, mạnh | Claude Sonnet 5.5 | Không | $2 / $10 |
| Embedding | gemini-embedding-2 | Có (không có batch) | $0,20 (batch $0,10) |
| Embedding dự phòng | gemini-embedding-001 | Có | $0,15 (batch $0,075) |

Về tên mô hình (sửa 2026-11-08): bản đọc trang giá lúc đầu chỉ phủ 100.000/106.069 ký tự và không thấy "3.8 Flash" hay "3.5 Flash-Lite", nên kết luận "trang giá không có" là chưa đủ căn cứ. Trang rate-limits (bản chủ repo đính kèm) liệt kê Gemini 3.8 Flash, 3.6 Flash, 3.5 Flash-Lite, 3.1 Flash Lite trong bảng Batch, tức các mô hình này tồn tại. Chúng có tầng miễn phí hay không, và giá, vẫn **chưa xác nhận**: kiểm trong AI Studio. Mặc định dùng 3.1 Flash-Lite.
Trang rate-limits cũng ghi: tầng Free không có hạn mức chi tiêu; số RPM/TPM/RPD chỉ xem được trong AI Studio (trang cá nhân, cần đăng nhập); "hạn mức không được đảm bảo"; mô hình preview/thử nghiệm bị giới hạn chặt hơn; Tier 1 cần liên kết tài khoản thanh toán.

## 3. Ước lượng chi phí một lần chạy bộ đo (40 câu)
Giả định, không phải số đo: mỗi câu 4.000 token vào (đoạn truy xuất), 500 token ra; chưa tính lần gọi chấm điểm (nhân khoảng 2 nếu chấm bằng mô hình).
| Mô hình | Chi phí/lần |
|---|---|
| Gemini 3.1 Flash-Lite | ≈ $0,07 |
| Claude Haiku 5.5 | ≈ $0,03 |
| Gemini 3.5 Flash | ≈ $0,42 |
| Claude Sonnet 5.5 | ≈ $0,52 |
Embedding một corpus 200K token ≈ $0,04. Kết luận: chi phí không phải ràng buộc ở quy mô này; ràng buộc là quyền riêng tư và hạn mức. Thay giả định bằng số đo thật ở giai đoạn 0.

## 4. Rủi ro có căn cứ
1. **Tầng miễn phí dùng nội dung để cải thiện sản phẩm Google** (trang giá). Chỉ gửi dữ liệu tổng hợp hoặc công khai có giấy phép. Dữ liệu khách hàng thật không đi qua tầng miễn phí. Gói trả phí không dùng nội dung cho mục đích đó (cùng nguồn).
2. **Hạn mức không công bố trên trang tài liệu**: chỉ xem được trong AI Studio, tính theo project chứ không theo khóa API; hạn mức theo ngày reset lúc nửa đêm giờ Thái Bình Dương (trang rate-limits). Tier 1 có giới hạn chi tiêu $10 mỗi cửa sổ 10 phút. Hệ quả: bộ chạy đo phải có retry/backoff và ghi lại lần bị giới hạn; không giả định số RPM.
3. **Mô hình bị tắt**: Gemini 2.0 Flash và Flash-Lite đã ngừng 2026-06-01. Cố định ID trong cấu hình, kiểm trang deprecations mỗi tháng, ghi ID vào mọi kết quả đo.
4. **Embedding không tương thích giữa các phiên bản**: `gemini-embedding-001` và `-2` có không gian vector khác nhau; đổi mô hình là phải nhúng lại toàn bộ. Lưu `embedding_model_id` và số chiều cùng mỗi vector; đổi mô hình = chạy lại ingestion, so sánh bằng recall@k. `-2` hỗ trợ 128-3072 chiều (khuyến nghị 768/1536/3072), giới hạn 8.192 token vào; không dùng `task_type`, thêm tiền tố vào văn bản. Hỗ trợ tiếng Việt: tài liệu nói "hơn 100 ngôn ngữ", không nêu riêng tiếng Việt, **chưa xác nhận**; đo bằng nhóm câu VI.
5. **Khóa API và chi tiêu**: khóa chỉ trong `.env` trên server; đặt trần chi tiêu phía nhà cung cấp nếu có tùy chọn (tính năng và vị trí cấu hình của Anthropic/Google chưa kiểm) và trần phía mã (`SPEND_CAP_USD`, dừng khi vượt).
6. **Lệch hành vi giữa hai nhà cung cấp** (định dạng gọi công cụ, mã lỗi, độ dài ngữ cảnh): adapter chuẩn hóa về một hợp đồng; bộ kiểm hợp đồng chạy trên cả hai.
7. **Chỉ một nhà cung cấp**: bộ kiểm hợp đồng adapter không kiểm được việc đổi hãng.

## 5. Phát hiện công cụ (MCP) qua API
- **Đường mặc định (A): phía ứng dụng.** App là MCP client: gọi `tools/list`, đổi `inputSchema` thành khai báo hàm của nhà cung cấp, chạy vòng lặp `tool_use`/`function_call` → `tools/call` → trả `tool_result`/`function_result`. Chạy được với cả Gemini và Claude, server MCP chỉ cần ở máy local, tập công cụ trả về có thể thay đổi theo quyền (spec 2026-07-28).
- **Đường lab (B): MCP từ xa phía nhà cung cấp** (Gemini Interactions API nhận `{"type":"mcp_server","url":...}`, chỉ Streamable HTTP). Suy luận: phía Google gọi nên server phải công khai được; khi đó bài toán xác thực và dữ liệu rời máy. Làm sau giai đoạn 3, chỉ với dữ liệu tổng hợp.

## 6. Cấu hình (.env, chỉ tên biến)
`MODEL_PROVIDER` (gemini|anthropic), `MODEL_ID`, `JUDGE_PROVIDER`, `JUDGE_MODEL_ID`, `EMBEDDING_MODEL_ID`, `EMBEDDING_DIM`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, `SPEND_CAP_USD`.

## 7. Giai đoạn 0 làm gì với phần này
1. Hợp đồng adapter: `generate(messages, tools?) → {text, tool_calls, usage, model_id, latency}` và `embed(texts) → vectors + model_id`.
2. Cài hai adapter (Gemini, Claude), cùng bộ kiểm hợp đồng.
3. Mỗi lần chạy ghi: ngày, ID mô hình, token vào/ra, độ trễ, lần bị giới hạn.
4. Đo nền (chưa RAG) trên 40 câu bằng 3.1 Flash-Lite và 3.5 Flash; so sánh.

## 8. Chưa biết (đánh dấu, không đoán)
- Gemini 3.8 Flash: có trong bảng giá miễn phí không.
- Số RPM/TPM/RPD thật của mô hình chọn (xem AI Studio).
- Embedding `-2` với tiếng Việt.
- Có nhà cung cấp thứ hai miễn phí đủ dùng để kiểm adapter đổi hãng không.
- Chỗ đặt trần chi tiêu phía nhà cung cấp.
