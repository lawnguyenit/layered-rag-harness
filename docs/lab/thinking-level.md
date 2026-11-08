# Thí nghiệm: mức suy nghĩ của Gemma 4 31B (HIGH và MINIMAL)

- Ngày: 2026-11-08
- Câu hỏi muốn trả lời: điểm gốc nên chạy ở mức suy nghĩ nào? Hai mức khác nhau ở chất lượng, độ trễ, token ra như thế nào trên đúng bộ 40 câu?
- Thay mảnh nào, giữ nguyên phần còn lại: chỉ `thinking_level` của `GeminiModel` (HIGH = mặc định của mô hình; MINIMAL). Cùng mô hình `gemma-4-31b-it`, temperature 0, `max_output_tokens` 1024, cùng system prompt bản nháp, cùng ngữ cảnh. LOW và `thinking_budget` mô hình không nhận (400), xem `docs/components/model-adapter.md`.
- Điều kiện: mỗi câu kèm **toàn bộ tài liệu người hỏi được đọc** (mô phỏng truy xuất hoàn hảo và lọc quyền tầng 1). Đây **không** phải điểm gốc giai đoạn 0 (điểm gốc không có tài liệu) và system prompt chỉ là bản nháp.
- Cách chạy lại: `uv run python eval/compare_thinking.py` (khoảng 40 phút cho cả hai mức chạy song song; chạy tiếp được nếu bị ngắt), rồi `uv run python eval/summarize_compare.py --date 2026-11-08`. Kết quả: `eval/results/thinking-compare-{high,minimal}-2026-11-08.jsonl`, báo cáo `eval/results/thinking-compare-2026-11-08.md`.

## Kết quả (một lần chạy mỗi mức)
| Chỉ số | HIGH | MINIMAL |
|---|---|---|
| Đạt theo luật | 32/40 | 32/40 |
| Đạt khi đọc tay (agent đọc, chủ repo chưa đối chiếu) | 38/40 | 36/40 |
| Rò rỉ (`must_not_contain`) | 0 | 0 |
| Lỗi 500 còn lại sau 3 lần thử lại | 1 (E-004) | 1 (F-001) |
| Độ trễ trung vị / p90 | 27,3 s / 55,8 s | 18,2 s / 28,6 s |
| Token ra trung bình / tối đa (gồm suy nghĩ) | 417 / 967 | 22 / 74 |
| Tổng token vào + ra (40 câu) | 72.267 | 56.312 |
| Số lần thử lại (429 hoặc 5xx, không tách) | 31 | 18 |

Đọc tay các câu luật chấm trượt:
- **Giống nhau ở cả hai mức, lỗi nằm ở bộ câu hỏi, không ở mô hình:** A-007 (tài liệu ghi "300.001đ", key_fact đòi "300.000"), B-005 (trả lời "Có, vì lần khiếu nại thứ 3" là đúng; key_fact "quản lý ca" nằm sẵn trong câu hỏi), B-006 (trả lời đúng "2 lần"; key_fact "23/11" không cần cho câu hỏi). E-009: cả hai chỉ đọc đúng dòng "Nội dung:" của phiếu, bỏ "đã hoàn 45.000đ"; tính là trả lời thiếu.
- **Khác nhau thật:**
  - C-005 (support hỏi quy trình dị ứng đậu phộng, tài liệu không có): HIGH trả câu cố định "không tìm thấy"; **MINIMAL trả một câu lạc đề lấy từ FAQ** ("công thức có đậu phộng được đánh dấu..."), tức không nhận ra tài liệu không trả lời câu hỏi. Đây đúng là loại lỗi nhóm C đo.
  - G-003 (câu tiếng Anh "Can I change it?"): HIGH hỏi lại bằng tiếng Anh; MINIMAL hỏi lại bằng tiếng Việt, trái chỉ dẫn "trả lời bằng ngôn ngữ của câu hỏi".
  - B-004: HIGH kết luận đúng "cần finance duyệt" nhưng không nêu số tiền 629.000đ làm căn cứ; MINIMAL nêu cả hai. Tính đúng cho cả hai khi đọc tay.

## Diễn giải
- Với ngữ cảnh đủ và đúng quyền, hai mức gần như ngang nhau. HIGH hơn ở hai chỗ, và cả hai đều là chỗ sản phẩm cần (biết nói "không có", theo đúng chỉ dẫn ngôn ngữ). MINIMAL hơn ở chi phí: ít hơn 19 lần token ra, nhanh hơn khoảng 1,5 lần ở trung vị và 2 lần ở p90, dùng ít hơn 22% TPM.
- Mẫu nhỏ: một lần chạy, 40 câu, khác nhau 2 câu. Không đủ để nói HIGH tốt hơn có ý nghĩa thống kê; đủ để thấy loại lỗi MINIMAL dễ mắc.
- Ở tầng Free, độ trễ không phải chi phí tiền; TPM 16K là ràng buộc thật. Với prompt RAG ~2K token, HIGH vẫn vừa (khoảng 4-5 câu mỗi phút theo TPM; thực tế bị chặn bởi độ trễ trước).

## Điều học được về production
- Lỗi 500 xảy ra thường xuyên ở tầng Free: mỗi mức mất 1/40 câu dù đã thử lại 3 lần với backoff 2-4-8 s. Cần thử lại lâu hơn cho 5xx, hoặc bộ chạy đo đánh dấu câu lỗi và chạy lại riêng.
- Bản ghi chưa tách thử lại do 429 hay do 5xx; cần tách để biết đang chạm hạn mức hay máy chủ lỗi.
- Bộ câu hỏi có ít nhất 3 key_fact sai hoặc thừa (A-007, B-005, B-006): luật chấm trượt câu đúng. Phải sửa trước khi chạy điểm gốc, vì sửa bộ câu hỏi sau đó buộc chạy lại mọi bản (AGENTS.md).

## Điều chưa hiểu
- Lỗi C-005 của MINIMAL có lặp lại ổn định không (temperature 0 nhưng chưa chạy lại).
- Ở điều kiện điểm gốc thật (không có tài liệu) hai mức khác nhau thế nào: chưa đo.
- Đánh giá tay ở đây do agent viết thí nghiệm làm; chủ repo chưa đối chiếu.

## Có đưa vào đường 1 không
Chờ chủ repo quyết. Đề xuất của agent: **HIGH (mặc định)** cho điểm gốc và các giai đoạn sau, vì hai lỗi của MINIMAL rơi đúng vào điều dự án đo (nhóm C, theo chỉ dẫn), còn cái giá của HIGH (độ trễ, token) không tốn tiền ở tầng Free và vẫn nằm trong TPM. Nếu chọn MINIMAL thì phải giữ nguyên cho mọi giai đoạn, và mức suy nghĩ phải vào khóa đệm.
