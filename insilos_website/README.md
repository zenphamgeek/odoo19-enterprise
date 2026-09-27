# Insilos Website — Insilos 19 / QWeb / Owl

Module website production-ready cho **Insilos — Intelligent Operations**.

## Phạm vi website

### Trang public

- `/insilos` — Trang chủ.
- `/insilos/platform` — Nền tảng Operational AI.
- `/insilos/solutions` — Solution hub.
- `/insilos/solutions/<slug>` — 6 trang giải pháp.
- `/insilos/industries` — Industry hub.
- `/insilos/industries/<slug>` — FSM, Logistics, Energy, Pharmaceutical Manufacturing.
- `/insilos/resources` — Resource hub.
- `/insilos/resources/<slug>` — 3 bài hướng dẫn nền tảng.
- `/insilos/about` — Company page.
- `/insilos/request-demo` — Form yêu cầu demo.
- `/insilos/thank-you` — Trang xác nhận.
- `/insilos/media-credits` — Attribution và media sources.

### Backend

Sau khi thêm người dùng vào nhóm **Insilos Demo Request Manager**, menu **Insilos Website → Yêu cầu demo** cung cấp:

- Danh sách và tìm kiếm yêu cầu.
- Group theo trạng thái, ngành, use case và thời gian.
- Phân công người phụ trách.
- Chuyển trạng thái New → Contacted → Qualified → Closed.
- Chatter và activities.
- Internal notes.

## Kiến trúc

- **QWeb**: SEO, server-rendered page content và form.
- **Owl public components**: Industry Explorer và Agent Workflow.
- **SCSS**: scoped design system dưới `.insilos-site`.
- **Python model/controller**: dynamic catalog, demo lead capture và email notification queue.
- **Local media**: Pexels images được lưu trong module, có card variants 960×640.

## Cài đặt

```bash
# Copy thư mục insilos_website vào addons_path
./insilos-bin -d YOUR_DATABASE -i insilos_website --stop-after-init
```

Sau đó khởi động Insilos và mở:

```text
https://YOUR_DOMAIN/insilos
```

Xem hướng dẫn triển khai đầy đủ trong `INSTALL.md`.

## Email notification

Khi có demo request, module tạo một `mail.mail` gửi tới email của công ty đang gắn với website. Cần cấu hình:

1. **Settings → Companies → Email**.
2. Outgoing Mail Server hoặc email provider của Insilos.
3. Mail queue / scheduled actions đang hoạt động.

Nếu chưa có email công ty, request vẫn được lưu trong backend nhưng không tạo notification mail.

## Tùy biến nội dung

- Industry/solution/article data: `controllers/main.py`.
- QWeb pages: `views/*.xml`.
- Design system và responsive: `static/src/scss/insilos.scss`.
- Owl components: `static/src/components/`.
- Media: `static/src/img/` và `MEDIA_SOURCES.md`.

## Lưu ý production

- Các KPI trên website là capability statements; không có claim định lượng chưa được xác minh.
- Dashboard SVG là mockup, cần thay bằng screenshot sản phẩm thật khi sẵn sàng.
- Cần cập nhật domain, company email, privacy policy và legal footer trước go-live.
- Stock images không được dùng để ngụ ý người trong ảnh chứng thực Insilos.

## Kiểm thử đã thực hiện

- XML well-formed validation.
- Python compile và manifest/data path validation.
- JavaScript syntax check bằng Node.
- Image dimension/format validation.
- Route/template/link consistency checks.

Môi trường build không có Insilos runtime, vì vậy vẫn cần thực hiện installation test trên một instance Insilos 19 trước go-live.
