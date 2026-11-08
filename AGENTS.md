# AGENTS.md — quy tắc cho agent làm việc trong repo layered-rag-harness

Nguồn quy tắc duy nhất của repo. CLAUDE.md và GEMINI.md chỉ trỏ về file này.

## Dự án là gì
Ứng dụng hỏi đáp trên tài liệu (RAG) có phân quyền, gọi công cụ qua MCP, dựng theo từng lớp; sau mỗi lớp đo lại trên một bộ câu hỏi cố định để biết lớp đó sửa được lỗi nào. Hai mục đích: (1) portfolio có số đo, (2) chủ repo hiểu toàn bộ đường từ máy cá nhân tới production và bảo trì.
Kế hoạch đầy đủ: docs/PLAN.md. Cổng giai đoạn: docs/GATES.md.

## Bắt đầu phiên
1. Quy tắc vault của chủ repo (D:\Project\Brain\AGENTS.md) vẫn áp dụng: đọc vault rồi ghi dòng đầu "Đã đọc từ vault: ..." hoặc "Chưa đọc vault: <lý do>".
2. Đọc docs/PLAN.md (mục Quyết định) và docs/GATES.md. Trước khi đóng bất kỳ giai đoạn nào, nêu những mục chưa xong trong GATES.md.
3. Chủ repo không nhớ hết ngữ cảnh giữa các phiên và agent cũng không nhớ: mọi điều cần nhớ phải nằm trong file của repo.

## Cách làm việc
- Phản biện và nhắc điểm mù theo vault Me/Blind-Spot-Rule.md: tối đa ba điểm mỗi câu trả lời, chỉ khi ảnh hưởng quyết định hiện tại. Điểm chủ repo đã cân nhắc và gạt đi (thời gian, thu nhập của dự án này) không nhắc lại. Bảo trì vẫn xét.
- Mỗi lớp mới phải sửa một lỗi cụ thể có trong bộ câu hỏi đo. Không có lỗi để sửa thì không thêm lớp.
- Thêm hoặc đổi một mảnh (cơ sở dữ liệu, mô hình, kiểu vận chuyển, bộ điều phối) chỉ qua adapter; lõi không được sửa theo từng mảnh. Hợp đồng đặt ở mức việc cần làm, không đặt ở mức lệnh của cơ sở dữ liệu. Mỗi adapter phải qua cùng bộ test hợp đồng, gồm ca "người không có quyền".
- Ghi số giờ thật của mỗi giai đoạn vào docs/PLAN.md (mục Nhật ký giờ). Đây không phải hạn chót.
- Mọi dữ kiện kiểm chứng được (giá, phiên bản, giới hạn dịch vụ) phải có nguồn và ngày kiểm. Chưa kiểm thì ghi "chưa kiểm", không đoán.
- Mỗi thành phần có một trang trong docs/components/ theo mẫu _TEMPLATE.md.

## Kiểm thử
- Agent viết code không tự chấm code đó. Việc kiểm thử do một agent riêng chạy, đọc yêu cầu từ docs và test, không đọc lý lẽ của agent viết code.
- Lỗi ghi vào docs/BUG-LEDGER.md: sinh ra khi nào, xảy ra khi nào, sửa được không, ảnh hưởng.
- Số đo chỉ có giá trị khi chạy trên bộ câu hỏi cố định (docs/EVAL-SET-DESIGN.md). Đổi bộ câu hỏi thì ghi lại và chạy lại các bản trước.

## Bí mật và dữ liệu
- Không ghi khóa API, token, mật khẩu vào repo hoặc chat. Chỉ .env trên máy chủ repo; .env.example chỉ có tên biến.
- Dữ liệu thử là dữ liệu công khai hoặc tổng hợp, có ghi nguồn và giấy phép. Không đưa dữ liệu của khách vào repo.
- Gặp .env, *.pem, file credential: dừng và hỏi.

## Nói về dự án một cách trung thực
- Ghi rõ mã có dùng công cụ AI hỗ trợ. Chủ repo phải giải thích được từng quyết định trong lõi; phần lõi (vòng lặp gọi công cụ, lọc quyền) nên do chủ repo tự gõ với agent hướng dẫn (đề xuất, chờ chủ repo xác nhận).
- Chỉ ghi số đo đã đo thật, kèm điều kiện đo.

## Git
- Chỉ commit khi chủ repo yêu cầu hoặc cuối một đợt làm có chủ đề. Không force push, không viết lại lịch sử. Không commit .env hay dữ liệu riêng.
