# Host: giao diện web (React/TypeScript)

- Giai đoạn thêm vào: H5 trong docs/HOST-SYSTEM-PLAN.md. Nằm trong `web/` (Vite, React 18, TypeScript, `oidc-client-ts`).
- Làm gì: cho người dùng đăng nhập bằng Keycloak, tra một đơn/phiếu/hóa đơn theo mã, tìm tài liệu, và hiện mã vết của từng lần gọi. Chỉ làm những việc host làm được thật.
- Nhận gì: người dùng nhập mã hoặc câu hỏi. Cấu hình: `VITE_OIDC_AUTHORITY`, `VITE_OIDC_CLIENT_ID` (mặc định `bepmay-spa`), `VITE_HOST_URL`.
- Trả gì: bản ghi hoặc đoạn tài liệu do host trả; thông báo "không tìm thấy hoặc không có quyền" giống nhau cho hai trường hợp; mã vết `x-request-id`.
- Phụ thuộc vào: Keycloak (Authorization Code + PKCE S256, client công khai), host API (cần `HOST_CORS_ORIGINS` chứa origin của giao diện).
- Chạy demo: `python scripts/demo.py up` (cần Docker và Python; compose.demo.yaml, web/Dockerfile, web/nginx.conf.template). Bản demo phục vụ bản build production qua nginx với Content-Security-Policy (`script-src 'self'`, `connect-src` chỉ tới Keycloak và host), nên 6 trong 7 ca trình duyệt đã chạy trên đúng bản đó (ca thứ 7 cần tệp vết của host nên chỉ chạy ở cấu hình cục bộ).
- Có thể hỏng thế nào (và hậu quả):
  - Token nằm trong `sessionStorage` (mất khi đóng tab) nên mọi script chạy trên cùng origin đọc được; không có refresh token, hết hạn là đăng nhập lại. Chấp nhận cho bản thử; production cần CSP chặt và xem xét mô hình BFF.
  - Giao diện **không lọc gì**: nếu host quên lọc thì giao diện sẽ hiện ra. Đó là chủ ý, để test trình duyệt đo đúng host.
  - Mã đăng nhập chỉ dùng được một lần; React StrictMode (dev) từng làm đổi mã hai lần (xem BUG-LEDGER B-012).
- Quyền được kiểm ở đâu: không ở giao diện. `describeToken` chỉ đọc claim để hiển thị "bạn là ai"; host kiểm token và lọc bằng RLS.
- Kiểm tra bằng cách nào (test nào): `web/src/api.test.ts` (6 test đơn vị: header bearer, mã hóa tham chiếu, 404/401/5xx, đọc claim), `web/e2e/isolation.spec.ts` (7 ca Chrome thật: chưa đăng nhập, PKCE S256 và token không nằm trong localStorage, khách A/B đọc đơn của nhau, tìm kiếm không trả tài liệu người khác hay nội bộ, quản lý thấy cái hỗ trợ không thấy, mã vết khớp dòng log của host và log không chứa câu hỏi hay token). Phá RLS giữa chừng: 4 ca đỏ; khôi phục: 7/7 xanh; chạy 3 lần liên tiếp đều 7/7. CI chạy typecheck, test đơn vị, build, `npm audit` ở mức production; ca trình duyệt chạy cục bộ.
- Lỗi nó sửa trong bộ câu hỏi đo (ID câu hỏi): chưa có. Không liên quan bộ câu hỏi đo.
- Chưa quyết định / chưa biết: **ô "Hỏi đáp qua harness" chưa nối** (câu hỏi → route plan → công cụ thuộc giai đoạn harness); chưa kiểm trên trình duyệt ngoài Chrome; chưa kiểm thiết bị di động thật (CSS có điểm gãy ở 480px nhưng chưa xem trên máy thật); Keycloak chạy HTTP trên loopback (production bắt buộc HTTPS).
