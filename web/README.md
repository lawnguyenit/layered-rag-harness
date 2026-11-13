# web: giao diện của hệ thống chủ

React 18 + TypeScript + Vite. Đăng nhập Keycloak (Authorization Code + PKCE), tra cứu theo mã, tìm tài liệu. Giao diện không lọc dữ liệu: mọi quyết định quyền nằm ở host. Xem docs/components/host-web.md.

## Chạy
```bash
cd web
npm ci
VITE_OIDC_AUTHORITY=http://localhost:18080/realms/bepmay-e2e VITE_HOST_URL=http://127.0.0.1:8020 npm run dev   # http://localhost:5173
npm run typecheck && npm test && npm run build
```

## Ca trình duyệt (Chrome có sẵn, không tải thêm)
Cách nhanh nhất là `python scripts/demo.py up` ở thư mục gốc repo. Để chạy tay, cần ba thứ đang chạy: Keycloak dev realm, host API, `npm run dev`. Realm thử dựng bằng `scripts/kc_dev_realm.py` (cần `KC_URL`, `KC_ADMIN_PASSWORD` và một `DEV_USER_PASSWORD` tùy bạn đặt cho các người dùng tổng hợp). Host phải chạy với `HOST_CORS_ORIGINS=http://localhost:5173`, và `HOST_OIDC_ISSUER` phải trùng tên máy với `VITE_OIDC_AUTHORITY` (`localhost` khác `127.0.0.1` ở claim `iss`).
```bash
DEV_USER_PASSWORD=... HOST_TRACE_FILE=/đường/dẫn/tệp/host chạy ghi vết npm run e2e
```
