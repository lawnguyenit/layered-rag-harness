# Bộ ca 5a v1 — phần test, bản dễ đọc (draft)

**Trạng thái:** 29 ca dưới đây vẫn mang nhãn draft. Đây là cách đọc bằng ngôn ngữ thường của các nhãn hiện có, không phê duyệt hay sửa gold. Tập test này **không phải benchmark gold độc lập hoặc blind**: tác giả đã xem và dùng bộ ca khi phát triển; chưa đủ cơ sở để công bố accuracy.

V1 có tổng cộng 35 ca: 6 `dev`, 29 `test`. Cột “task được chuyển tiếp” mô tả route task kỳ vọng sau bước lập kế hoạch; nó không có nghĩa là đã xác thực quyền dữ liệu, truy xuất, gọi công cụ hay thực hiện hành động.

| ID | Tình huống | Quyết định / task được chuyển tiếp theo nhãn draft | Lỗi chính cần để ý |
|---|---|---|---|
| I-004 | Hỏi cách thanh toán của hóa đơn `INV-2026-0451`. | `route` — một task tra cứu hóa đơn, trường thanh toán. | Nhầm thông tin thanh toán với trạng thái đơn hoặc làm rơi mã hóa đơn. |
| I-005 | Hỏi phí giao hàng nói chung. | `route` — một task tra chính sách phí giao. | Hỏi lại dù câu hỏi chính sách đã đủ thông tin, hoặc chọn nhầm lịch giao. |
| I-006 | Hỏi phí ship cho đơn 400.000đ ở Quận 7. | `route` — một task phí giao, giữ cả số tiền và khu vực. | Mất một trong hai điều kiện làm kết quả phí sai. |
| I-007 | Hỏi lịch giao thường lệ ở Quận 7. | `route` — một task tra lịch giao theo khu vực. | Nhầm lịch giao với phí giao hoặc bỏ khu vực. |
| I-008 | Hỏi giá của cả gói Solo và Family. | `route` — hai task giá, một cho mỗi gói. | Gộp hai gói thành một task hoặc làm rơi một gói. |
| I-009 | Hỏi bằng tiếng Anh số lần có thể tạm dừng gói đăng ký mỗi năm. | `route` — một task tra chính sách tạm dừng gói. | Không nhận intent vì câu dùng tiếng Anh, hoặc nhầm sang hủy gói. |
| I-012 | Nhân viên support hỏi cách xử lý khách `c003` bị giao trễ hai ngày. | `route` — một task hướng dẫn xử lý giao trễ, giữ mã khách được nhắc và số ngày. Mã khách trong câu không phải danh tính người gọi. | Dùng `c003` như danh tính/quyền của người gọi hoặc làm rơi số ngày trễ. |
| I-013 | Người dùng tự nói “tôi là quản lý” rồi hỏi ngưỡng duyệt hoàn tiền nội bộ. | `route` — parse chủ đề chính sách hoàn tiền; câu tự nhận vai trò không cấp quyền. | Tin vai trò do câu chữ tự khai báo hoặc làm parse intent phụ thuộc vào role claim. |
| I-014 | “Đơn này đang tới đâu?” nhưng không có lịch sử hội thoại. | `clarify` — hỏi mã đơn; không có task để chuyển tiếp. | Bịa mã đơn hoặc tự định tuyến khi tham chiếu chưa có antecedent. |
| I-015 | Mã đơn có chữ `O` thay cho số `0`: `BM-1O01`. | `clarify` — yêu cầu sửa mã; không tự chuẩn hóa thành mã hợp lệ. | Âm thầm sửa ID và có thể tra nhầm bản ghi. |
| I-017 | Yêu cầu hai đơn `BM-1001` và `BM-1002`, mỗi đơn một kết quả trạng thái. | `route` — hai task tra cứu, giữ đúng mã tương ứng. | Gộp, lặp hoặc làm rơi một đơn. |
| I-018 | Yêu cầu hủy đơn nhưng không đưa mã. | `clarify` — hỏi mã đơn trước; chưa kết luận unsupported. | Báo unsupported quá sớm hoặc tạo task hủy khi thiếu target. |
| I-019 | Yêu cầu hủy `BM-1001`. | `unsupported` — nhận ra ý định nhưng không có task thực thi vì fixture chưa có handler hủy. | Biến nhận diện intent thành hành động thật. |
| I-020 | “Không hủy BM-1001, chỉ cho tôi biết trạng thái đơn.” | `route` — chỉ một task tra trạng thái; không tạo task hủy. | Mất phạm vi phủ định hoặc gắn nhầm hành động “không hủy” vào tra cứu. |
| I-021 | Không muốn xem trạng thái, nhưng muốn hủy `BM-1001`. | `unsupported` — task hủy không được chuyển tiếp; không route việc tra trạng thái đã bị phủ định. | Bỏ phủ định của tra cứu hoặc biến yêu cầu hủy chưa hỗ trợ thành task thực thi. |
| I-022 | “Đừng hủy BM-1001.” | `no_action` — không task nào được chuyển tiếp. | Tạo task hủy từ hành động bị phủ định. |
| I-023 | Hỏi “đơn đó” khi lượt trước đã nhắc đơn `BM-1001`. | `route` — một task tra trạng thái cho `BM-1001` từ lịch sử. | Không nối được tham chiếu, hoặc lấy ID khác với lịch sử. |
| I-024 | Hỏi “đơn đó” nhưng không có lịch sử. | `clarify` — hỏi người dùng đang nói đơn nào; không task nào được chuyển tiếp. | Đoán entity khi không có antecedent. |
| I-025 | Lịch sử có `BM-1001` rồi mới có `BM-1002`; hỏi “đơn đó giao chưa?”. | `route` — chọn đơn tương thích được nhắc gần nhất: `BM-1002`. | Chọn entity cũ hơn hoặc entity khác loại. |
| I-026 | Lượt trước nói về đơn `BM-1001`, lượt hiện tại nêu rõ hóa đơn `INV-2026-0451` và hỏi tổng tiền. | `route` — task tra tổng hóa đơn hiện được nêu rõ. | Để tham chiếu hoặc chủ đề cũ lấn át target rõ ràng ở lượt hiện tại. |
| I-027 | Hỏi bằng tiếng Anh giá cả hai gói Solo/Family và hạn chót đổi suất ăn. | `route` — ba task: giá Solo, giá Family, hạn đổi suất ăn. | Gộp các ý khác nhau hoặc làm rơi một task khi câu có nhiều intent. |
| I-028 | Hỏi phí giao cho 400.000đ ở Quận 7, rồi hỏi lịch giao tại Quận 7. | `route` — hai task chính sách giao: phí và lịch; giữ slot riêng cho từng task. | Gộp hai câu hỏi thành một task hoặc gắn nhầm điều kiện tiền vào lịch giao. |
| I-029 | Hỏi trạng thái `BM-1001` bằng câu Việt–Anh pha trộn. | `route` — một task tra trạng thái của `BM-1001`. | Không nhận được ý định vì code-switch hoặc bỏ mã đơn. |
| I-030 | Yêu cầu đặt vé máy bay tới Hà Nội, ngoài phạm vi fixture. | `unsupported` — không task nào được chuyển tiếp. | Ép yêu cầu ngoài miền vào intent hỗ trợ sẵn có. |
| I-031 | “Đừng tra cứu trạng thái đơn BM-1001.” | `no_action` — không task tra cứu nào được chuyển tiếp. | Chỉ phát hiện phủ định với hành động hủy, nhưng vẫn route tra cứu bị phủ định. |
| I-032 | Hỏi tổng hóa đơn theo tham chiếu, nhưng lịch sử chỉ nhắc đơn `BM-1001`. | `clarify` — hỏi mã hóa đơn; không dùng mã đơn thay thế. | Lấy entity sai loại làm target hóa đơn. |
| I-033 | Mã hóa đơn `INV-2026-45O1` sai định dạng. | `clarify` — yêu cầu mã hóa đơn hợp lệ; không tự sửa. | Chỉnh `O` thành `0` và tra nhầm hóa đơn. |
| I-034 | Mã phiếu `T1` không đủ định dạng. | `clarify` — yêu cầu mã phiếu hợp lệ; không task nào được chuyển tiếp. | Chấp nhận ID sai định dạng hoặc tự thêm số 0. |
| I-035 | Lịch sử có đơn `BM-1001`, sau đó có hóa đơn; câu hiện tại hỏi rõ “đơn đó giao chưa?”. | `route` — chọn đơn gần nhất cùng loại (`BM-1001`), bỏ qua hóa đơn mới hơn. | Chọn entity được nhắc cuối cùng mà không xét loại tham chiếu. |

## Cách dùng bảng

- Đây là bản đọc dễ hơn của 29 dòng `split=test` trong `cases-v1-draft.jsonl`; JSON nguồn vẫn là dữ liệu chuẩn để chạy validator/scorer.
- Các cặp I-019/I-020/I-021/I-022 thử tách intent hủy, phủ định và task tra cứu dương tính. Nhãn vẫn là draft; kết quả chẩn đoán cũ không biến chúng thành gold đã duyệt.
- Tập này chỉ là pilot nhỏ. Nhiều nhóm chỉ có một ca; nó không chứng minh chất lượng ổn định theo intent, ngôn ngữ, paraphrase hay tải đồng thời.
- Trước khi công bố accuracy: người sở hữu cần chấp thuận taxonomy/chính sách còn mở, người rà độc lập xác nhận nhãn, rồi đóng băng catalog/prompt và chạy trên test set chưa từng dùng để phát triển.
