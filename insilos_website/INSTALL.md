# Installation & Deployment Guide

## 1. Yêu cầu

- Insilos 19 Community hoặc Enterprise.
- Module `website` và `mail`.
- Quyền truy cập server/addons path.
- Reverse proxy HTTPS cho production.

## 2. Cài module

1. Giải nén ZIP.
2. Copy thư mục `insilos_website` vào một thư mục trong `addons_path`.
3. Khởi động lại Insilos.
4. Bật Developer Mode.
5. Apps → Update Apps List.
6. Cài **Insilos Intelligent Operations Website**.

Hoặc CLI:

```bash
./insilos-bin -c /etc/insilos.conf -d DATABASE -i insilos_website --stop-after-init
```

Nâng cấp module:

```bash
./insilos-bin -c /etc/insilos.conf -d DATABASE -u insilos_website --stop-after-init
```

## 3. Phân quyền quản lý yêu cầu demo

Trong Settings → Users, thêm người phụ trách vào nhóm **Insilos Demo Request Manager**. System administrators luôn có quyền quản trị.

## 4. Thiết lập website

- Mở `/insilos`.
- Website → Configuration → Settings:
  - Domain.
  - Website name.
  - Language.
  - Favicon/social image.
- Company:
  - Email dùng để nhận thông báo demo.
  - Phone, address và legal information.

Module không tự thay homepage `/` để tránh ảnh hưởng website đang tồn tại. Có thể:

- Link `/insilos` từ menu chính; hoặc
- Cấu hình redirect `/` → `/insilos` ở reverse proxy; hoặc
- Chủ động thay homepage trong Insilos sau khi kiểm thử.

## 5. Email

Cấu hình outgoing email. Demo request được lưu ngay cả khi email chưa hoạt động.

## 6. Bảo mật

- Public user không có quyền đọc model `insilos.demo.request`.
- Controller chỉ dùng `sudo()` cho thao tác tạo record đã validate.
- CSRF được bật.
- Honeypot và session cooldown hạn chế spam cơ bản.
- Production nên bổ sung CAPTCHA/WAF nếu traffic cao.

## 7. Cache và assets

Sau khi thay SCSS/JS:

```bash
./insilos-bin -d DATABASE -u insilos_website --stop-after-init
```

Trong môi trường dev có thể dùng `?debug=assets` để kiểm tra asset source.

## 8. Go-live checklist

Xem `QA_CHECKLIST.md`.
