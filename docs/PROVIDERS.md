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

## 2b. Hạn mức tầng Free của tài khoản chủ repo (ảnh chụp AI Studio, 2026-11-08 ~20:30 giờ VN)
Nguồn: ảnh chủ repo gửi. Số có thể đổi, Google ghi hạn mức "không được đảm bảo". Chưa thấy các dòng gemini-3.1-flash-lite và gemini-3.5-flash (nằm giữa hai ảnh, chưa chụp). Dòng Gemini 4 Argon: 0/0/0.
| Mô hình | RPM | TPM | RPD |
|---|---|---|---|
| Gemini 3.8 Flash | 5 | 250K | 20 |
| Gemini 3 Flash | 5 | 250K | 20 |
| Gemini 2.5 Flash | 5 | 250K | 20 |
| Gemini 2.5 Flash Lite | 10 | 250K | 20 |
| Gemini 2.5 Flash TTS | 3 | 10K | 10 |
| Gemma 4 31B (`gemma-4-31b-it`) | 30 | 16K | 14.400 |
| Gemma 4 26B (`gemma-4-26b-a4b-it`) | 30 | 16K | 14.400 |
| Gemini Embedding 1 và Gemini Embedding 2 (ảnh thứ hai, cùng ngày) | 100 | 30K | 1.000 |
| Gemini 2.5 Pro, 3.1 Pro, 2 Flash, 2 Flash Lite | 0 | 0 | 0 (không dùng được ở Free) |
Hạn mức theo từng mô hình. RPD reset 00:00 giờ Thái Bình Dương = 15:00 giờ VN khi PST (UTC-8, tức mùa đông), 14:00 khi PDT; đây là phép tính múi giờ, không có trong trang.
Gemini 3.8 Flash có tầng Free (đã xác nhận bằng ảnh).

**Gemma 4 qua Gemini API (ảnh thứ ba): đây là API chạy trên máy chủ Google, không phải AI cục bộ.** ID mô hình và hỗ trợ gọi hàm, system instruction, thinking: trang Google (ghi "tài liệu này đã lỗi thời, xem gemma.ai") và một bài blog bên thứ ba; context 256K chỉ từ bài blog. Chưa kiểm: JSON schema, cách trả kết quả hàm về mô hình, chính sách dữ liệu của tầng Free cho Gemma (giả định giống tầng Free chung: Google dùng nội dung để cải thiện sản phẩm), chất lượng tiếng Việt, chất lượng so với 3.8 Flash.
Giới hạn thật là **16K token/phút**: một câu RAG ~4K token vào thì tối đa ~4 câu/phút, 40 câu ≈ 10 phút; một yêu cầu vượt 16K token có thể bị từ chối (suy luận). Ngân sách ngữ cảnh RAG mỗi câu đặt ≤ ~8K token.

**Phân vai đề xuất (chờ chủ repo xác nhận):** mô hình đo chính và chạy phát triển = `gemma-4-31b-it` (14.400 lượt/ngày giải quyết điểm nghẽn); Gemini 3.8 Flash = đường tham chiếu, chạy tập con câu hỏi (20 lượt/ngày) để so chất lượng. Mỗi kết quả ghi rõ mô hình; hai đường không gộp số.

**Embedding:** 30K token/phút nghĩa là nhập 200K token tối thiểu ≈ 7 phút (phép tính, chưa đo); 1.000 lượt/ngày đủ cho vài trăm đoạn nếu không gộp, mỗi câu hỏi truy vấn tốn 1 lượt. Chưa biết một lượt gọi gộp nhiều đoạn có tính là 1 RPD không [chưa kiểm]. Nhập tài liệu phải theo lô có giới hạn tốc độ theo TPM.

**Hệ quả sinh văn bản:** 20 lượt/ngày/mô hình. Bộ 40 câu cần ≥2 ngày cho MỘT lần chạy sinh, chưa tính lần chấm; vòng lặp công cụ tốn 1 lượt cho mỗi bước. Quy tắc bắt buộc cho giai đoạn 0:
1. Adapter giả (stub) xác định để kiểm đường ống và bộ kiểm hợp đồng, không tốn lượt thật.
2. Bộ nhớ đệm phản hồi theo (model_id, hash prompt); chạy lại không gọi lại.
3. Chạy đo có checkpoint và tiếp tục qua nhiều ngày; không tính 429 là câu trả lời.
4. Ưu tiên chấm bằng luật xác định (chuỗi bị cấm xuất hiện = rò rỉ, mẫu từ chối) và chấm tay mẫu; LLM chấm chỉ dùng khi cần và tốn lượt riêng.
5. Không trộn mô hình trong một lần đo để "lấy thêm hạn mức": kết quả không so sánh được. Với Gemma 4 là mô hình đo chính, nhu cầu này không còn.
6. Bộ chạy đo giới hạn tốc độ theo cả RPM và TPM (token ước lượng trước khi gửi), không chỉ theo số lượt.

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
