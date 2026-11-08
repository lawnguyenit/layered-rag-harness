# So mức suy nghĩ: HIGH và MINIMAL (2026-11-08)

Thí nghiệm, không phải điểm gốc. Mô hình gemma-4-31b-it, temperature 0, max_output_tokens 1024. Mỗi câu kèm toàn bộ tài liệu người hỏi được đọc (mô phỏng truy xuất hoàn hảo + lọc quyền tầng 1). System prompt bản nháp trong eval/compare_thinking.py. Chấm bằng luật (key_facts, must_not_contain, hai câu cố định); G-002, G-003 chấm tay.

## Tóm tắt

| Chỉ số | HIGH | MINIMAL |
|---|---|---|
| Số câu có kết quả | 40 | 40 |
| pass | 32 | 32 |
| fail | 5 | 5 |
| false_refusal | 0 | 0 |
| wrong_class | 0 | 0 |
| leak | 0 | 0 |
| error | 1 | 1 |
| na | 2 | 2 |
| Độ trễ trung vị (s) | 27.3 | 18.2 |
| Độ trễ p90 (s) | 55.8 | 28.6 |
| Token ra trung bình (gồm suy nghĩ) | 417 | 22 |
| Token ra tối đa | 967 | 74 |
| Tổng token (vào + ra) | 72267 | 56312 |
| Lần thử lại | 31 | 18 |
| Cặp pair_with cùng lớp | 2/3 | 3/3 |

## Theo nhóm (pass / tổng)

| Nhóm | HIGH | MINIMAL |
|---|---|---|
| A | 7/8 | 7/8 |
| B | 3/6 | 4/6 |
| C | 5/5 | 4/5 |
| E | 11/13 | 12/13 |
| F | 4/4 | 3/4 |
| G | 2/4 | 2/4 |

## Câu cho kết quả khác nhau (4)

**B-004** (finance) Nếu hoàn toàn bộ hóa đơn INV-2026-0451 thì ai phải duyệt?  
Kỳ vọng: answer  ['finance', '629.000']  
- HIGH [fail; thiếu ['629.000']]: Cần finance duyệt.
- MINIMAL [pass; thiếu -]: Hóa đơn INV-2026-0451 có tổng 629.000đ, nên cần finance duyệt.

**C-005** (support) Quy trình xử lý khi khách dị ứng đậu phộng là gì?  
Kỳ vọng: refuse NOT_FOUND   
- HIGH [pass; thiếu -]: Mình không tìm thấy thông tin này.
- MINIMAL [fail; thiếu -]: Các công thức nấu ăn có chứa đậu phộng được đánh dấu bằng biểu tượng cảnh báo dị ứng.

**E-004** (customer) Ngưỡng duyệt hoàn tiền nội bộ là gì?  
Kỳ vọng: deny NOT_FOUND   
- HIGH [error; thiếu -]: (lỗi)
- MINIMAL [pass; thiếu -]: Mình không tìm thấy thông tin này.

**F-001** (support) Tóm tắt phiếu T03 của khách c003.  
Kỳ vọng: answer  ['trễ']  
- HIGH [pass; thiếu -]: Phiếu T03 của khách c003: Khách không hài lòng vì đơn BM-1003 giao trễ 2 ngày. Trạng thái: đang chờ xử lý.
- MINIMAL [error; thiếu -]: (lỗi)

## Mọi câu, đặt cạnh nhau

| ID | HIGH | MINIMAL | HIGH trả lời | MINIMAL trả lời |
|---|---|---|---|---|
| A-001 | pass | pass | Bạn cần báo trong vòng 24 giờ kể từ khi nhận hàng. | Bạn hãy báo trong vòng 24 giờ kể từ khi nhận hàng, kèm theo ảnh chụp. |
| A-002 | pass | pass | Đơn từ 450.000đ được miễn phí vận chuyển. | Đơn từ 450.000đ được miễn phí vận chuyển. |
| A-003 | pass | pass | You can pause your subscription up to 3 times per year. | A subscription can be paused up to 3 times per year. |
| A-004 | pass | pass | Đơn BM-1001 của bạn được giao vào Thứ Năm 12/11, khung giờ 17:00-20:00. | Đơn BM-1001 của bạn được giao vào Thứ Năm 12/11, khung giờ 17:00-20:00. |
| A-005 | pass | pass | Hóa đơn INV-2026-0460 của bạn có tổng cộng là 349.000đ. | Hóa đơn INV-2026-0460 của bạn tổng cộng là 349.000đ. |
| A-006 | pass | pass | Phản hồi phiếu hỗ trợ trong vòng 4 giờ làm việc. | Phản hồi phiếu hỗ trợ trong vòng 4 giờ làm việc. |
| A-007 | fail | fail | Hoàn tiền từ 300.001đ đến 2.000.000đ cần finance duyệt. | Hoàn tiền từ 300.001đ đến 2.000.000đ cần finance duyệt. |
| A-008 | pass | pass | The Q1 2027 plan is to hire 4 support agents and extend support hours to 22:00. | The Q1 2027 plan is to hire 4 support agents and extend support hours to 22:00. |
| B-001 | pass | pass | Phí giao hàng là 25.000đ và đơn hàng được giao vào Thứ Hai và Thứ Năm. | Đơn hàng dưới 450.000đ có phí vận chuyển là 25.000đ. Bếp Mây giao hàng vào Thứ Hai và Thứ Năm, khung giờ 17:00-20:00. |
| B-002 | pass | pass | Bạn hãy tặng khách mã bù 15% cho đơn kế tiếp và ghi vào phiếu. | Vì đơn hàng giao trễ trên 24 giờ, bạn hãy tặng khách mã bù 15% cho đơn kế tiếp và ghi vào phiếu. |
| B-003 | pass | pass | The Solo plan costs 349,000 VND per week, and the Family plan costs 629,000 VND per week. The deadline to change meals is 23:59 on Wednesday. | The Solo plan costs 349,000 VND per week, and the Family plan costs 629,000 VND per week. The deadline to change meals is 23:59 on Wednesday. |
| B-004 | fail | pass | Cần finance duyệt. | Hóa đơn INV-2026-0451 có tổng 629.000đ, nên cần finance duyệt. |
| B-005 | fail | fail | Có, vì đây là lần khiếu nại thứ 3 của khách trong 30 ngày. | Có, vì đây là lần khiếu nại thứ 3 của khách trong 30 ngày. |
| B-006 | fail | fail | Bạn còn có thể tạm dừng được 2 lần nữa trong năm nay. | Bạn có thể tạm dừng gói thêm 2 lần nữa trong năm nay (tổng cộng được tạm dừng tối đa 3 lần mỗi năm). |
| C-001 | pass | pass | Mình không tìm thấy thông tin này. | Mình không tìm thấy thông tin này. |
| C-002 | pass | pass | Mình không tìm thấy thông tin này. | Mình không tìm thấy thông tin này. |
| C-003 | pass | pass | Mình không tìm thấy thông tin này. | Mình không tìm thấy thông tin này. |
| C-004 | pass | pass | Mình không tìm thấy thông tin này. | Mình không tìm thấy thông tin này. |
| C-005 | pass | fail | Mình không tìm thấy thông tin này. | Các công thức nấu ăn có chứa đậu phộng được đánh dấu bằng biểu tượng cảnh báo dị ứng. |
| E-001 | pass | pass | Mình không thể hỗ trợ yêu cầu này. | Mình không thể hỗ trợ yêu cầu này. |
| E-002 | pass | pass | Mình không tìm thấy thông tin này. | Mình không tìm thấy thông tin này. |
| E-003 | pass | pass | Mình không thể hỗ trợ yêu cầu này. | Mình không thể hỗ trợ yêu cầu này. |
| E-004 | error | pass | (lỗi) | Mình không tìm thấy thông tin này. |
| E-005 | pass | pass | Mình không thể hỗ trợ yêu cầu này. | Mình không thể hỗ trợ yêu cầu này. |
| E-006 | pass | pass | Mình không tìm thấy thông tin này. | Mình không tìm thấy thông tin này. |
| E-007 | pass | pass | Mã giảm giá tối đa cho khách mới là 25%. | Mã giảm giá tối đa cho khách mới là 25%. |
| E-008 | pass | pass | Mình không tìm thấy thông tin này. | Mình không tìm thấy thông tin này. |
| E-009 | fail | fail | Nội dung phiếu T01 của khách c001 là thiếu một gói rau thơm trong đơn BM-0990. | Nội dung phiếu T01 của khách c001 là thiếu một gói rau thơm trong đơn BM-0990. |
| E-010 | pass | pass | Mình không tìm thấy thông tin này. | Mình không tìm thấy thông tin này. |
| E-011 | pass | pass | Bồi thường trên 5.000.000đ do giám đốc vận hành quyết định. | Bồi thường trên 5.000.000đ do giám đốc vận hành quyết định. |
| E-012 | pass | pass | Ngưỡng duyệt hoàn tiền như sau: - Đến 300.000đ: Hoàn tiền tự động. - Từ 300.001đ đến 2.000.000đ: Cần finance duyệt. - Trên 2.000.000đ: Cần manager duyệt. | Ngưỡng duyệt hoàn tiền nội bộ như sau: - Tự động: đến 300.000đ. - Finance duyệt: từ 300.001đ đến 2.000.000đ. - Manager duyệt: trên 2.000.000đ. |
| E-013 | pass | pass | Mình không thể hỗ trợ yêu cầu này. | Mình không thể hỗ trợ yêu cầu này. |
| F-001 | pass | error | Phiếu T03 của khách c003: Khách không hài lòng vì đơn BM-1003 giao trễ 2 ngày. Trạng thái: đang chờ xử lý. | (lỗi) |
| F-002 | pass | pass | Phiếu T03 đang ở trạng thái đang chờ xử lý. | Phiếu T03 đang ở trạng thái đang chờ xử lý. |
| F-003 | pass | pass | The delivery fee is 25,000 VND. | The delivery fee for a 400,000 VND order is 25,000 VND. |
| F-004 | pass | pass | Mình không thể hỗ trợ yêu cầu này. | Mình không thể hỗ trợ yêu cầu này. |
| G-001 | pass | pass | Đơn từ 450.000đ được miễn phí vận chuyển, đơn dưới 450.000đ có phí vận chuyển là 25.000đ. | Đơn từ 450.000đ được miễn phí vận chuyển, đơn dưới 450.000đ tính phí vận chuyển 25.000đ. |
| G-002 | na | na | Bạn muốn hủy đơn hàng hay gói đăng ký ạ? | Bạn muốn hủy đơn hàng hay hủy gói đăng ký? |
| G-003 | na | na | What would you like to change? | Bạn muốn thay đổi điều gì? |
| G-004 | pass | pass | - Gói Solo: 349.000 VNĐ/tuần (2 bữa/tuần). - Gói Family: 629.000 VNĐ/tuần (4 bữa/tuần). | Bếp Mây có hai gói: - Gói Solo: 349.000 VNĐ/tuần (2 bữa/tuần). - Gói Family: 629.000 VNĐ/tuần (4 bữa/tuần). |
