# Go-live QA Checklist

## Functional

- [ ] Cài mới module trên database test không lỗi.
- [ ] Upgrade module không mất demo requests.
- [ ] Tất cả public routes trả HTTP 200.
- [ ] Industry Explorer chuyển tab đúng trên desktop/mobile.
- [ ] Agent Workflow chạy, pause và chọn step đúng.
- [ ] Form demo báo lỗi field đúng.
- [ ] Form hợp lệ tạo record backend.
- [ ] Email notification vào queue khi company email được cấu hình.
- [ ] Thank-you page không xuất hiện trong sitemap.

## Content

- [ ] Tên thương hiệu, domain, email và legal entity đã đúng.
- [ ] Thay mọi KPI placeholder/claim chưa xác minh.
- [ ] Screenshot dashboard phản ánh sản phẩm thật.
- [ ] Nội dung pharma đã được compliance/legal review.
- [ ] Privacy policy và cookie policy đã được link trong footer.

## Responsive & browser

- [ ] Chrome, Edge, Firefox, Safari.
- [ ] iPhone/Android viewport.
- [ ] Keyboard navigation và visible focus.
- [ ] Reduced motion.
- [ ] Không có horizontal scroll ngoài ý muốn.

## Performance

- [ ] Hero LCP dưới mục tiêu dự án.
- [ ] Không hotlink media.
- [ ] WebP và dimensions đúng.
- [ ] Insilos assets minified trong production.
- [ ] CDN/proxy cache được cấu hình phù hợp.

## SEO

- [ ] Page titles và meta descriptions.
- [ ] Canonical domain đúng.
- [ ] Sitemap chứa pages/solutions/industries/articles.
- [ ] Open Graph image và favicon theo brand.
- [ ] Search Console/Bing Webmaster đã được xác minh.

## Security

- [ ] HTTPS và HSTS.
- [ ] Outgoing email/domain SPF, DKIM, DMARC.
- [ ] WAF/rate limiting cho public form nếu cần.
- [ ] Internal access tới demo requests đúng nhóm.
- [ ] Backup và restore test.
