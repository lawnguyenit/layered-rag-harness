# Cổng giai đoạn

Agent đọc file này ở đầu mỗi phiên. Trước khi đóng giai đoạn N, nêu các mục chưa xong của giai đoạn N. Mục được đánh dấu xong chỉ khi có bằng chứng trong repo (kết quả chạy, trang thành phần, test).
Định nghĩa chỉ số là kiến thức chung, chưa đối chiếu từng nguồn [chưa kiểm]. Nếu dùng mô hình làm giám khảo để chấm, phải đối chiếu một mẫu chấm tay.

## Giai đoạn 0: mô hình + system prompt
Trước khi viết corpus và bộ câu hỏi:
- [ ] docs/DATA-CONTRACT.md được chủ repo duyệt (vai trò, quy ước nhóm E, định dạng bản ghi)
Số đo:
- [ ] Tỉ lệ đúng trên bộ câu hỏi cố định (chấm tay) = điểm gốc
- [ ] Độ trễ và chi phí mỗi lượt
Production:
- [ ] Khóa API chỉ ở phía server, đọc từ .env
- [ ] Trần chi tiêu (SPEND_CAP_USD) được thực thi trong code
- [ ] Chạy bằng một lệnh, phụ thuộc ghim phiên bản
- [ ] Trang thành phần: adapter mô hình, harness

## Giai đoạn 1: RAG
Số đo:
- [ ] Đoạn đúng có nằm trong top-k khi truy xuất không
- [ ] Câu trả lời bám nguồn, trích dẫn đúng
- [ ] Biết nói "không có thông tin" khi tài liệu không có (nhóm C)
- [ ] So với điểm gốc: lớp này sửa lỗi nào (ID câu hỏi)
Production:
- [ ] Cập nhật tài liệu phản ánh vào chỉ mục
- [ ] Xóa tài liệu thì xóa khỏi chỉ mục (kiểm bằng test)
- [ ] Giấy phép và nguồn của dữ liệu thử được ghi
- [ ] Trang thành phần: nạp tài liệu, truy xuất, kho

## Điểm dừng 1 (cổng đánh giá, không phải hạn chót)
- [ ] Số giờ thật của giai đoạn 0-1 đã ghi trong docs/PLAN.md
- [ ] Quyết định có chủ đích: đi tiếp / chỉnh phạm vi / dừng

## Giai đoạn 2: công cụ
Số đo:
- [ ] Gọi đúng công cụ, đúng tham số; tỉ lệ lỗi và thử lại
Production:
- [ ] Timeout cho mỗi lần gọi công cụ
- [ ] Công cụ chỉ đọc; quyền ghi chưa mở
- [ ] Viết bằng hàm thường trước, rồi đưa ra MCP; hai bản cho cùng kết quả
- [ ] Trang thành phần: công cụ, MCP server/client

## Giai đoạn 3: phân quyền, guardrails
Số đo:
- [ ] Tỉ lệ lộ dữ liệu = 0 trên nhóm E (quyền) và F (tấn công prompt injection)
- [ ] Tỉ lệ từ chối nhầm (người có quyền bị chặn)
Production:
- [ ] Giới hạn tần suất; không trả điểm tương đồng ra ngoài
- [ ] Log kiểm toán (ai hỏi, đoạn nào được dùng, công cụ nào gọi)
- [ ] Cache (nếu có) tách theo người dùng hoặc quyền
- [ ] Kiểm quyền cả ở từng lần gọi công cụ, không chỉ ở cửa vào
- [ ] Xoay khóa; ghi cách xoay

## Giai đoạn 4: vận hành
Số đo:
- [ ] Độ trễ p50/p95, chi phí mỗi lượt, tỉ lệ lỗi
- [ ] Điểm trên bộ câu hỏi theo thời gian (phát hiện suy giảm)
Production:
- [ ] Đánh giá chạy tự động (CI) kèm ca không có quyền
- [ ] Kiểm sức khỏe và cảnh báo: biết dịch vụ chạy bình thường khi không ai nhìn
- [ ] Sao lưu và khôi phục thử thật (khôi phục thành công mới tính)
- [ ] Quy trình nâng cấp phụ thuộc; hạn mức dịch vụ miễn phí đã kiểm (nếu dùng)
- [ ] Trang dự phòng tĩnh nếu có demo công khai
