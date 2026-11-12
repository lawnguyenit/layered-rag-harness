# Cổng giai đoạn

Agent đọc file này ở đầu mỗi phiên. Trước khi đóng giai đoạn N, nêu các mục chưa xong của giai đoạn N. Mục được đánh dấu xong chỉ khi có bằng chứng trong repo (kết quả chạy, trang thành phần, test).
Định nghĩa chỉ số là kiến thức chung, chưa đối chiếu từng nguồn [chưa kiểm]. Nếu dùng mô hình làm giám khảo để chấm, phải đối chiếu một mẫu chấm tay.

## Giai đoạn 0: mô hình + system prompt
Trước khi viết corpus và bộ câu hỏi:
- [ ] docs/DATA-CONTRACT.md được chủ repo duyệt (vai trò, quy ước nhóm E, định dạng bản ghi)
Số đo:
- [ ] Tỉ lệ đúng trên bộ câu hỏi cố định (chấm tay) = điểm gốc. Trước khi chạy: sửa key_fact sai của A-007, B-005, B-006 (docs/lab/thinking-level.md), vì sửa sau thì phải chạy lại mọi bản đo
- [ ] Độ trễ và chi phí mỗi lượt
Production:
- [ ] Khóa API chỉ ở phía server, đọc từ .env
- [x] Trần chi tiêu (SPEND_CAP_USD) được thực thi trong code (SpendGuard, tests/test_throttled.py; chưa nối vào cấu hình .env)
- [ ] Chạy bằng một lệnh, phụ thuộc ghim phiên bản (`uv sync` và live smoke test chạy được trên máy chủ repo 2026-11-08; uv.lock cũ thiếu gói, đã tạo lại: B-002; còn thiếu lệnh chạy điểm gốc)
- [ ] Trang thành phần: adapter mô hình, harness

## Runtime Tier 1–2 (lộ trình request, song song với G0 trước RAG)

Đây là các lớp trong một lượt request runtime, không đổi tên các project gate G0–G4. HTTP/Auth được kéo sớm theo quyết định chủ repo 2026-11-12; data authorization/filter vẫn chỉ đóng khi gate phân quyền G3 đạt đủ bằng chứng.

### Tier 1 — ingress, identity, actor/access scope
- [x] HTTP body/field limits, whitespace handling, rate limiting, safe errors and body spoofing covered by tests
- [x] OIDC signature, issuer, audience, expiry, role claim and secure URL policy covered with synthetic RSA/JWKS tests
- [ ] End-to-end token acquisition and verification against local Keycloak realm/client
- [x] Actor/customer identity comes only from validated token claims; conversation history is scoped by subject
- [x] Rate-limit behavior is tested; single-process limitation is documented
- [x] Component pages and local API setup instructions exist
- [ ] Define and measure semantic input-safety policy (e.g. harmful-content moderation); current gate is deterministic limits/rate only

### Tier 2 — intent and route planning
- [x] Versioned parser port and replaceable catalog exist; Bếp Mây is only a fixture
- [x] Required slots, ID formats, negation, references and multiple route tasks covered by contract tests
- [x] `clarify`, `unsupported`, `no_action` return no dispatchable tasks
- [x] v0 and v1 draft schema/split keys independently reviewed; owner approval of v1 gold labels remains pending
- [x] Scoring tool reports counts, false dispatch beside coverage, groups, error categories, latency/tokens/retries
- [ ] Run semantic parser against owner-approved gold and record a measured held-out score

### Unfinished project gates still in force
- G0 baseline remains open: DATA-CONTRACT review/corpus/questions approval, fix A-007/B-005/B-006, run baseline, cost/latency, runnable single command, component pages.
- Runtime T1–T2 remain open for live Keycloak check, semantic input safety policy, owner-approved gold, and a live parser evaluation.
- RAG G1, tool G2, data permission/guardrail G3, and operations G4 remain open as listed below.

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
