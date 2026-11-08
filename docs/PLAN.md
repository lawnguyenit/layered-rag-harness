# Kế hoạch layered-rag-harness

Cập nhật: 2026-11-08. Trạng thái: giai đoạn 0 chưa bắt đầu. Nguồn: các phiên trao đổi giữa chủ repo và Claude ngày 2026-11-08, cộng mẫu job Upwork cùng ngày.
Ký hiệu: [đã chốt] chủ repo xác nhận; [đề xuất] chờ chủ repo xác nhận; [chưa kiểm] chưa đối chiếu nguồn.

## 1. Mục tiêu: hai đường
- **Đường 1, sản phẩm (portfolio)**: một ngăn xếp, đi sâu, có số đo. Chứng minh được lớp nào sửa lỗi nào.
- **Đường 2, phòng thí nghiệm (để hiểu toàn bộ production)**: thay mảnh trong cùng repo (adapter), mỗi thí nghiệm một trang ghi trong docs/lab/. Không chặn đường 1. [đã chốt: chủ repo muốn thử nhiều loại để hiểu cái toàn vẹn của production, không phải để apply vào từng mảng]
- Không phải mục tiêu: train LLM từ đầu (chỉ là thí nghiệm riêng ở đường 2); đưa lên mạng công khai ở giai đoạn đầu.

## 2. Bằng chứng chọn ngăn xếp (mẫu Upwork 2026-11-08)
Đếm tay trên khoảng 17 mô tả job (3 truy vấn: RAG; LLM + vector + knowledge base; agent + tool + MCP; kết quả truy vấn thứ ba chưa đếm). Số gần đúng, mẫu thiên về từ khóa tìm, không đại diện cả thị trường. [chưa kiểm ở quy mô lớn]

| Yêu cầu | Số job nhắc tới (xấp xỉ /17) |
|---|---|
| Python | ~11 |
| Đánh giá chất lượng (test set, LLM-as-judge, "đưa số đo") | ~10 |
| FastAPI | ~7 |
| PostgreSQL / pgvector (Qdrant ~2, Pinecone ~3, Elasticsearch/OpenSearch ~1) | ~7 |
| LangChain / LangGraph / LlamaIndex | ~6 |
| Cô lập tenant, kiểm soát truy cập, nhật ký kiểm toán | ~5 |
| Docker | ~5 |
| React / Next.js / TypeScript | ~4 |
| Prompt injection, guardrails | ~3-4 |
| MCP | ~3 |

Tín hiệu đáng chú ý (đọc trực tiếp):
- Một job RAG hỏi thẳng khi apply: "làm sao ngăn trợ lý truy cập dữ liệu của khách khác?", "đánh giá độ chính xác truy xuất và giảm ảo giác thế nào?".
- Một job đòi "chúng tôi sẽ hỏi số đo của bạn" và "cho xem repo cùng cách bạn đo".
- Một job mời làm bài test có trả tiền: 5-10 câu hỏi trên tài liệu mẫu, có xử lý ca thông tin không có trong tài liệu.
- Nhiều job yêu cầu 3-7+ năm kinh nghiệm, số lượng đề xuất cạnh tranh từ 20 tới hơn 400. Repo này không thay thế kinh nghiệm triển khai thật; nó là bằng chứng kỹ năng.

Suy ra [đề xuất]: Python + FastAPI + PostgreSQL/pgvector + Docker làm đường 1; giao diện web tối thiểu (CLI trước); LangGraph làm một adapter bộ điều phối ở đường 2, sau khi vòng lặp tự viết đã chạy.

## 3. Kiến trúc: các lớp
Harness là phần điều phối quanh mô hình, không phải bản thân LLM, RAG hay MCP.

| Lớp | Trách nhiệm | Giai đoạn |
|---|---|---|
| L0 Giao diện | Nhập câu hỏi, nhận trả lời có nguồn | 0 (CLI) |
| L1 API và danh tính | Nhận yêu cầu, xác thực, giới hạn tần suất | 3 |
| L2 Harness | Ghép chỉ dẫn, điều phối RAG/mô hình/công cụ, giới hạn số bước | 0 |
| L3a Tri thức (RAG) | Nạp tài liệu, trích văn bản, chia đoạn, tìm đoạn phù hợp kèm nguồn | 1 |
| L3b Công cụ (MCP) | Công cụ chỉ đọc qua giao diện chuẩn | 2 |
| L3c Adapter mô hình | Chuyển yêu cầu sang định dạng của nhà cung cấp, chuẩn hóa phản hồi | 0 |
| L4 Hạ tầng | Chạy dịch vụ, lưu dữ liệu, quản lý khóa | 0 (máy local) |
| Xuyên suốt | Phân quyền, guardrails, theo dõi, đánh giá, giới hạn chi phí | 3-4 |

Luồng nạp tài liệu và luồng người dùng hỏi tách riêng:
```
Nạp:  tài liệu -> trích văn bản/OCR -> chia đoạn + metadata (gồm quyền) -> chỉ mục -> kho
Hỏi:  người dùng -> xác thực -> lọc theo quyền (trước khi tìm) -> tìm -> [LLM <-> công cụ] -> kiểm đầu ra -> trả lời có nguồn
```
Vòng lặp công cụ (đã đối chiếu spec MCP 2026-07-28 và tài liệu tool use của Claude API): host đưa danh sách công cụ (`tools/list`) vào lời gọi mô hình; mô hình trả khối `tool_use` rồi dừng; host xin phép, gửi `tools/call` tới server; kết quả quay về dưới dạng `tool_result`; lặp tới khi có câu trả lời cuối. Mô hình không tự kết nối tới server nào.

**Adapter (mảnh thay được).** Hợp đồng đặt ở mức việc cần làm, ví dụ `tìm(câu hỏi, phạm vi quyền) -> các đoạn kèm mã nguồn`. Mỗi adapter qua cùng bộ test hợp đồng, kể cả ca không có quyền.
- Mô hình: nhà cung cấp và tên mô hình là cấu hình. Dev bằng mô hình rẻ, đo chốt bằng mô hình mạnh. [đề xuất]
- Kho tìm kiếm: PostgreSQL+pgvector (đường 1); lab: CSDL vector chuyên dụng, Elasticsearch/OpenSearch, MongoDB. MySQL Community không có `DISTANCE()` (chỉ HeatWave/MySQL AI), nên chỉ lưu metadata. SQL Server 2025: kiểu và hàm vector GA, chỉ mục DiskANN preview vào 11/2025, trạng thái hiện tại [chưa kiểm].
- Bộ điều phối: vòng lặp tự viết (đường 1); LangGraph (lab).
- Vận chuyển MCP: stdio và Streamable HTTP, cùng một server (lab).
- Embedding: tên mô hình là cấu hình; chất lượng tiếng Việt [chưa kiểm].

## 4. Giai đoạn
Cổng, số đo và việc production của từng giai đoạn: docs/GATES.md. Bộ câu hỏi: docs/EVAL-SET-DESIGN.md.

| Giai đoạn | Thêm gì | Xong khi |
|---|---|---|
| 0 | Gọi mô hình qua adapter, system prompt, CLI, bộ câu hỏi đo + điểm gốc | Chạy bằng một lệnh, có điểm gốc chấm tay, chi phí và độ trễ mỗi lượt |
| 1 | RAG trên tài liệu công khai/tổng hợp | Điểm so với bản 0, ghi lỗi nào sửa được |
| Điểm dừng 1 | Nhìn lại: số giờ thật, kết quả, đi tiếp không. Là cổng đánh giá, không phải hạn chót | Quyết định có chủ đích, ghi vào mục Quyết định |
| 2 | Một công cụ MCP chỉ đọc (viết bằng hàm thường trước, rồi đưa ra MCP) | Đúng công cụ, đúng tham số; xử lý lỗi và timeout |
| 3 | Phân quyền, guardrails, giới hạn tần suất, log kiểm toán | Tỉ lệ lộ dữ liệu bằng 0 trên bộ ca tấn công |
| 4 | Đánh giá chạy tự động (CI), giám sát, chi phí, sao lưu/khôi phục thử thật | Số đo theo thời gian, khôi phục thành công |

## 5. Quyết định
| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Hướng RAG, tên repo `layered-rag-harness` | [đã chốt] 2026-11-08 | Chủ repo tạo thư mục theo tên này |
| Ngăn xếp đường 1: Python, FastAPI, PostgreSQL+pgvector, Docker | [đề xuất] | Dựa trên mẫu job mục 2 |
| Mô hình: dev rẻ, đo chốt mạnh, đổi qua cấu hình | [đề xuất] | Giá tại 2026-11-08: Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50 mỗi triệu token (input/output) |
| Thời gian và thu nhập | [đã chốt] không dùng làm tiêu chí | Chủ repo đã tự cân nhắc. Không đặt hạn chót cứng; điểm dừng 1 là cổng đánh giá |
| Bảo trì | [đã chốt] là tiêu chí chính khi thêm mảnh | |
| Ai viết lõi | [đề xuất] chủ repo tự gõ vòng lặp lõi và lọc quyền | Để giải thích được khi bị hỏi |
| Số đo | [đã chốt] không dồn hết từ đầu, nhắc đúng giai đoạn | Gắn vào cổng từng giai đoạn trong docs/GATES.md |
| Frontend | [đề xuất] CLI trước, web tối thiểu sau | Framework chọn theo bằng chứng job, không theo cảm tính |

## 6. Rủi ro và điểm mù chưa xử lý
- **Trùng với repo cũ**: ai-customer-support-email-rag (n8n, mới đọc README). Repo này phải khác rõ: mã Python, có số đo, có phân quyền.
- **Tiếng Việt**: truy xuất và trả lời chưa kiểm. Đưa câu tiếng Việt vào bộ đo từ giai đoạn 0.
- **Dữ liệu**: chỉ dùng dữ liệu tổng hợp hoặc công khai có ghi giấy phép.
- **Môi trường chạy thật**: sandbox của agent không gọi được API ngoài danh sách cho phép; lời gọi mô hình và dịch vụ CSDL chạy trên máy chủ repo. Máy có Docker hay không [chưa kiểm].
- **Production**: "chạy bình thường" nghĩa là gì sau khi deploy (kiểm sức khỏe, cảnh báo, log, sao lưu và khôi phục thử thật); khóa API chỉ ở phía server; trần chi tiêu; hạn mức dịch vụ miễn phí năm 2026 [chưa kiểm]; bản vá phụ thuộc.
- **Trung thực**: ghi rõ có dùng AI hỗ trợ viết mã; chỉ nêu số đo đã đo.
- **Phình phạm vi**: mỗi lớp thêm vào phải sửa một lỗi có trong bộ đo.

## 7. Chưa biết
- Số giờ thật cho từng giai đoạn (ghi vào Nhật ký giờ).
- Framework web nào nên dùng cho giao diện (ngoài CLI).
- Chất lượng tiếng Việt của embedding và mô hình.
- Trạng thái DiskANN của SQL Server 2025 hiện tại.
- Máy chủ repo có Docker và đủ RAM cho PostgreSQL local hay không.

## 8. Nhật ký giờ
| Giai đoạn | Giờ thật | Ghi chú |
|---|---|---|
| (chưa bắt đầu) | | |
