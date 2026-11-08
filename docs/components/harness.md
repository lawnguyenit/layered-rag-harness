# Harness (bộ chạy đo)

- Giai đoạn thêm vào: 0 (khung); phần chạy bộ câu hỏi ở bước 0.7
- Làm gì: đọc `eval/questions.jsonl`, gọi mô hình qua adapter (đã bọc đệm và giới hạn), chấm bằng luật xác định, ghi `eval/results/<run_id>.jsonl` theo DATA-CONTRACT mục 7.
- Hiện có: `lrh.results` (bản ghi kết quả, người ghi), `lrh.cli` (`python -m lrh ask`, chỉ adapter giả).
- Chưa có: bộ chạy bộ câu hỏi, bộ chấm theo luật, adapter Gemini, hồ sơ token.
- Chưa quyết định / chưa biết: system prompt gốc của giai đoạn 0 (cần chứa canary `CANARY-SP-4410`).
