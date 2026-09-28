/**
 * ============================================================================
 * INSILOS ENTERPRISE — CINEMA HUD VIDEO TELEMETRY PLAYER (REQUIREMENT R3)
 * ============================================================================
 * Module: insilos_video_telemetry.js
 * Version: 20.0.3.0.0
 * Architecture: Sovereign Vanilla JS WebGL/HTML5 Video Telemetry Stream
 *
 * Capabilities:
 *  1. 3-Act Interactive Timeline & Precision Chapter Scrubber (Acts 1, 2, 3)
 *  2. Real-Time Synchronous ERP Telemetry HUD Stream (60 FPS via rAF)
 *  3. Dynamic ERP Tabular Cards & High-Density JSON Audit Stream
 *  4. 1-Click Direct Deep-Link Action to Live Odoo 20 Backend Records
 *  5. Complete 13-Video Gold Master Registry (VID-01 to VID-12 + Master 105s)
 *  6. Responsive Dual-Pane Glassmorphism HUD Layout (Desktop, Tablet, Mobile)
 * ============================================================================
 */

(function () {
    'use strict';

    /**
     * Resolve Odoo live backend base URL dynamically.
     * Defaults to http://localhost:28069 or current window origin.
     */
    function getOdooBaseUrl() {
        if (typeof window !== 'undefined' && window.location) {
            if (window.location.port === '28069' || window.location.hostname === 'localhost') {
                return window.location.origin;
            }
        }
        return 'http://localhost:28069';
    }

    /**
     * Format seconds to mm:ss format.
     */
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return '00:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return (mins < 10 ? '0' : '') + mins + ':' + (secs < 10 ? '0' : '') + secs;
    }

    /**
     * Escape HTML helper for safe telemetry rendering.
     */
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * Build SVG Phosphor Duotone icon string.
     */
    function renderPhosphorIcon(name, extraClass) {
        const cls = extraClass ? 'ph-duotone ' + extraClass : 'ph-duotone';
        return '<svg class="' + cls + '" aria-hidden="true"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#' + name + '"/></svg>';
    }

    /**
     * Complete Enterprise Telemetry Data Dictionary for all 12 Gold Masters + Master Cinematic.
     * Grounded in PostgreSQL `odoo20_dev` database schema and Explorer survey.
     */
    const INSILOS_VIDEO_REGISTRY = {
        'VID_01_CRM': {
            id: 'VID_01_CRM',
            code: 'VID-01',
            badge: 'CRM & ĐẤU THẦU KCN',
            title: 'Quản Trị Bán Hàng Dự Án & Đấu Thầu Cảng Biển Quốc Tế',
            domain: 'CRM & Bidding',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_01_CRM_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_01_CRM_GOLD_MASTER_poster.webp',
            defaultModel: 'sale.order',
            defaultRecordId: 1,
            defaultActionId: 561,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D & Nỗi Đau Đấu Thầu', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác CRM Pipeline Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Cảnh Báo Thất Thoát Phễu Bán Hàng', act: 1, desc: 'Rủi ro tuột mất gói thầu 18.675 Tỷ VNĐ' },
                { time: 10.0, title: 'Điều Hướng Kanban Pipeline CRM', act: 2, desc: 'Kéo thả cơ hội Cảng Biển sang Báo giá' },
                { time: 18.0, title: 'Kiểm Tra Báo Giá #VN-SO2026-001', act: 2, desc: 'Duyệt cấu hình 5 xe kéo V-LIFT & 2 trạm sạc' },
                { time: 30.0, title: 'Phân Tích Tỷ Suất Lợi Nhuận', act: 2, desc: 'Xác lập Win Rate 95% & Khóa biên độ giá' },
                { time: 42.0, title: 'Phê Duyệt Ban Giám Đốc (CEO)', act: 2, desc: 'Chốt hợp đồng thương mại 2.295 Tỷ VNĐ' },
                { time: 50.0, title: '25-Thumbnail Suite Closing CTA', act: 3, desc: 'Kết nối cổng demo trực tuyến Insilos' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Cảnh Báo Thất Thoát Phễu Bán Hàng',
                    operationalState: 'CRITICAL RISK',
                    stateBadge: 'RỦI RO THẦU B2B',
                    stateColor: 'danger',
                    model: 'sale.order',
                    recordId: 1,
                    actionId: 561,
                    metrics: [
                        { label: 'Gói Thầu Tiềm Năng', value: '18.675 Tỷ ₫', status: 'alert', icon: 'ph-currency-circle-dollar' },
                        { label: 'Tỷ Lệ Bỏ Lỡ Cơ Hội', value: '28.4%', status: 'alert', icon: 'ph-warning' },
                        { label: 'Thời Gian Báo Giá', value: '7.5 Ngày', status: 'warning', icon: 'ph-clock' }
                    ],
                    table: {
                        title: 'Đánh Giá Rủi Ro Bỏ Lỡ Gói Thầu KCN',
                        columns: ['Hạng Mục', 'Hiện Trạng', 'Thiệt Hại Ước Tính', 'Khắc Phục Insilos'],
                        rows: [
                            ['Phản Hồi Báo Giá', 'Thủ công bằng Excel', '-28.4% Tỷ lệ thắng thầu', 'Tự động tính BOM trong 15s'],
                            ['Kiểm Soát Giá Vốn', 'Ước tính rời rạc', 'Lệch biên lãi 6.2%', 'Khóa biên độ giá theo TT200'],
                            ['Truy Vết Tiến Độ', 'Không có phân quyền', 'Mất 4-6h rà soát', 'Kanban phân tầng thời gian thực']
                        ]
                    },
                    json: {
                        stage: 'pipeline_risk_assessment',
                        customer: 'Tổng Công Ty Tiếp Vận Cảng Biển Quốc Tế',
                        tender_ref: 'PORT-TENDER-2026-B2B',
                        opportunity_value_vnd: 18675000000,
                        risk_score: 0.74,
                        alert_level: 'HIGH',
                        action_required: 'Triển khai CRM phân quyền để bảo toàn tỷ lệ chốt thầu'
                    }
                },
                {
                    timestamp: 10.0,
                    act: 2,
                    chapter: 'Điều Hướng Kanban Pipeline CRM',
                    operationalState: 'IN PROGRESS',
                    stateBadge: 'ĐIỀU HƯỚNG PIPELINE',
                    stateColor: 'info',
                    model: 'sale.order',
                    recordId: 1,
                    actionId: 561,
                    metrics: [
                        { label: 'Trạng Thái Phễu', value: 'Đang Đấu Thầu', status: 'info', icon: 'ph-funnel' },
                        { label: 'Xác Suất Thắng', value: '85.0%', status: 'success', icon: 'ph-trend-up' },
                        { label: 'Doanh Thu Kỳ Vọng', value: '15.87 Tỷ ₫', status: 'success', icon: 'ph-chart-bar' }
                    ],
                    table: {
                        title: 'Phân Bổ Cơ Hội Kinh Doanh Dự Án Cảng Biển',
                        columns: ['Giai Đoạn', 'Cơ Hội', 'Giá Trị (VNĐ)', 'Phụ Trách'],
                        rows: [
                            ['1. Khảo Sát Kỹ Thuật', 'Đội xe kéo Depot Cảng Biển', '4.500.000.000 ₫', 'Chuyên viên phụ trách'],
                            ['2. Báo Giá Đấu Thầu', '#VN-SO2026-001 (5 Xe + Sạc)', '2.295.000.000 ₫', 'Trần Thị Thu'],
                            ['3. Thương Thảo Hợp Đồng', 'Hợp đồng khung 2026', '11.880.000.000 ₫', 'Ban Giám Đốc']
                        ]
                    },
                    json: {
                        pipeline_id: 1,
                        opportunity: 'Dự án Cung cấp Xe Kéo Điện Cảng Biển Quốc Tế',
                        partner: 'Tổng Công Ty Tiếp Vận Cảng Biển Quốc Tế',
                        tax_id: '0300481234',
                        stage_name: 'Quotation / Đang Báo Giá',
                        probability: 0.85,
                        expected_closing: '2026-10-15'
                    }
                },
                {
                    timestamp: 22.0,
                    act: 2,
                    chapter: 'Kiểm Tra Báo Giá #VN-SO2026-001',
                    operationalState: 'ACTIVE AUDIT',
                    stateBadge: 'ĐỐI SOÁT BÁO GIÁ',
                    stateColor: 'primary',
                    model: 'sale.order',
                    recordId: 1,
                    actionId: 561,
                    metrics: [
                        { label: 'Mã Báo Giá', value: '#VN-SO2026-001', status: 'info', icon: 'ph-file-text' },
                        { label: 'Tổng Giá Trị', value: '2.295.000.000 ₫', status: 'success', icon: 'ph-coins' },
                        { label: 'Số Dòng Báo Giá', value: '2 Cụm Thiết Bị', status: 'info', icon: 'ph-list-checks' }
                    ],
                    table: {
                        title: 'Chi Tiết Dòng Hàng Báo Giá #VN-SO2026-001',
                        columns: ['Mã Sản Phẩm', 'Tên Thiết Bị', 'Số Lượng', 'Đơn Giá (VNĐ)', 'Thành Tiền (VNĐ)'],
                        rows: [
                            ['EQ-VLIFT-2500E', 'Xe kéo hàng điện nhà xưởng V-LIFT 2500E', '5.00 Unit', '385.000.000 ₫', '1.925.000.000 ₫'],
                            ['EV-CHG-60KW', 'Trạm sạc nhanh DC 60kW công nghiệp', '2.00 Unit', '185.000.000 ₫', '370.000.000 ₫']
                        ]
                    },
                    json: {
                        order_id: 1,
                        name: 'Đơn bán hàng #VN-SO2026-001',
                        partner_id: [58, 'Tổng Công Ty Tiếp Vận Cảng Biển Quốc Tế'],
                        amount_untaxed: 2295000000.0,
                        amount_tax: 0.0,
                        amount_total: 2295000000.0,
                        state: 'draft',
                        validity_date: '2026-10-30',
                        incoterm: 'DAP - Cụm Cảng Biển Quốc Tế'
                    }
                },
                {
                    timestamp: 40.0,
                    act: 2,
                    chapter: 'Phê Duyệt Ban Giám Đốc (CEO)',
                    operationalState: 'FISCAL APPROVED',
                    stateBadge: 'ĐÃ DUYỆT HỢP ĐỒNG',
                    stateColor: 'success',
                    model: 'sale.order',
                    recordId: 1,
                    actionId: 561,
                    metrics: [
                        { label: 'Win Rate Khóa', value: '95.0% CHẮC CHẮN', status: 'success', icon: 'ph-seal-check' },
                        { label: 'Biên Lãi Gộp', value: '31.2%', status: 'success', icon: 'ph-percent' },
                        { label: 'Chữ Ký Số', value: 'E-Sign Verified', status: 'success', icon: 'ph-fingerprint' }
                    ],
                    table: {
                        title: 'Quy Trình Phê Duyệt Tự Động Insilos Workflow',
                        columns: ['Cấp Duyệt', 'Người Phê Duyệt', 'Thời Gian Duyệt', 'Trạng Thái'],
                        rows: [
                            ['1. Trưởng Phòng Bán Hàng', 'Nguyễn Thị Minh', '2026-09-27 14:15:00', 'ĐÃ PHÊ DUYỆT'],
                            ['2. Giám Đốc Kỹ Thuật (CTO)', 'Lê Hoàng Nam', '2026-09-27 14:32:10', 'ĐÃ PHÊ DUYỆT'],
                            ['3. Tổng Giám Đốc (CEO)', 'Phạm Quốc Cường', '2026-09-27 15:00:22', 'CHẤP THUẬN KÝ']
                        ]
                    },
                    json: {
                        approval_state: 'approved',
                        approved_by: 'CEO Phạm Quốc Cường',
                        electronic_signature_hash: '0x8fbc4e29a9b78e10d3f2c5890e71ab4f',
                        workflow_rule: 'Auto-Forward to MRP Production Dispatch',
                        contract_status: 'READY FOR SIGNATURE'
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: '25-Thumbnail Suite Closing CTA',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'CỔNG KẾT NỐI SỐ',
                    stateColor: 'success',
                    model: 'sale.order',
                    recordId: 1,
                    actionId: 561,
                    metrics: [
                        { label: 'Hệ Sinh Thái', value: '12 Kịch Bản Sống', status: 'success', icon: 'ph-squares-four' },
                        { label: 'Chuẩn Âm Học', value: '-14.6 LUFS', status: 'info', icon: 'ph-speaker-high' },
                        { label: 'Live Demo', value: 'Sẵn Sàng 100%', status: 'success', icon: 'ph-broadcast' }
                    ],
                    table: {
                        title: 'Hành Động Khuyên Dùng Cho C-Level',
                        columns: ['Hành Động', 'Thời Lượng Khảo Sát', 'Đầu Ra Bàn Giao'],
                        rows: [
                            ['Trực Quan Hóa Trên Odoo Live', 'Tức thời (1 Click)', 'Xem bản ghi thật trên backend'],
                            ['Khảo Sát Thực Địa KCN', '48 Giờ làm việc', 'Báo cáo tính toán ROI & TCO 3 năm'],
                            ['Kích Hoạt Sandbox Thử Nghiệm', 'Miễn phí 14 ngày', 'Môi trường dữ liệu doanh nghiệp']
                        ]
                    },
                    json: {
                        closing_cta: 'Khép kín dòng chảy thương mại cùng Insilos CRM',
                        portal_url: 'http://localhost:28069/showcase-3d',
                        contact_hotline: '1900-INSILOS',
                        audit_status: 'VERIFIED GENUINE DATA'
                    }
                }
            ]
        },

        'VID_02_PUR': {
            id: 'VID_02_PUR',
            code: 'VID-02',
            badge: 'MUA HÀNG & DUNG SAI GIÁ',
            title: 'PO Thép Tấm Tiêu Chuẩn 20 Tấn & Đối Soát Đơn Giá #VN-PO2026-001',
            domain: 'Procurement',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_02_PUR_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_02_PUR_GOLD_MASTER_poster.webp',
            defaultModel: 'purchase.order',
            defaultRecordId: 1,
            defaultActionId: 758,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Cán Thép & Nguy Cơ Giá', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác PO & Dung Sai Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Cảnh Báo Biến Động Giá Thép', act: 1, desc: 'Dung sai giá cán cuộn ăn mòn 12% lợi nhuận' },
                { time: 10.0, title: 'Điều Hướng Phân Hệ Mua Hàng', act: 2, desc: 'Mở danh sách đơn mua nhà cung cấp Thép Tiêu Chuẩn' },
                { time: 20.0, title: 'Đối Soát Đơn Hàng #VN-PO2026-001', act: 2, desc: '20 Tấn SS400 (390M) + 600m Thép hộp (147M)' },
                { time: 32.0, title: 'Khóa Chặn Dung Sai ±2% Fiscal', act: 2, desc: 'Tự động khóa nếu chênh lệch đơn giá quá 2%' },
                { time: 44.0, title: 'Liên Kết 3 Chiều Phiếu Kho & Hóa Đơn', act: 2, desc: 'Khớp nối WH/IN/00006 & BILL/2026/09/0001' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Đặt lịch khảo sát chuỗi cung ứng' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Cảnh Báo Biến Động Giá Thép',
                    operationalState: 'COST VOLATILITY',
                    stateBadge: 'BIẾN ĐỘNG GIÁ THÉP',
                    stateColor: 'danger',
                    model: 'purchase.order',
                    recordId: 1,
                    actionId: 758,
                    metrics: [
                        { label: 'Thị Trường Thép SS400', value: '19.500 ₫/kg', status: 'alert', icon: 'ph-trend-up' },
                        { label: 'Rủi Ro Thất Thoát', value: '-12.0% Lãi ròng', status: 'alert', icon: 'ph-warning-octagon' },
                        { label: 'Dung Sai Cổng Cân', value: '±3.5% Chưa kiểm soát', status: 'warning', icon: 'ph-scales' }
                    ],
                    table: {
                        title: 'Bảng Cảnh Báo Trôi Giá Thép Cuộn SS400',
                        columns: ['Chỉ Tiêu', 'Mua Truyền Thống', 'Insilos Procurement Guard'],
                        rows: [
                            ['Đơn Giá Chốt', 'Thương thảo miệng / Báo giá giấy', 'Khóa cố định hợp đồng khung'],
                            ['Dung Sai Trọng Lượng', 'Cân trạm cổng ghi tay', 'Đồng bộ trực tiếp đầu đọc cân điện tử'],
                            ['Phát Hiện Vượt Ngưỡng', 'Kế toán phát hiện sau 30 ngày', 'Khóa tức thì (Real-time Block)']
                        ]
                    },
                    json: {
                        alert: 'STEEL_PRICE_SURGE',
                        commodity: 'SS400 Structural Steel Plate',
                        current_market_price_vnd_kg: 19500,
                        tolerance_guardrail: '±2.0%',
                        impact: 'Risk of 12% EBITDA contraction on fixed-price manufacturing contracts'
                    }
                },
                {
                    timestamp: 10.0,
                    act: 2,
                    chapter: 'Điều Hướng Phân Hệ Mua Hàng',
                    operationalState: 'NAVIGATING PO',
                    stateBadge: 'LỌC NHÀ CUNG CẤP',
                    stateColor: 'info',
                    model: 'purchase.order',
                    recordId: 1,
                    actionId: 758,
                    metrics: [
                        { label: 'Nhà Cung Cấp', value: 'Nhà Cung Cấp Thép Tiêu Chuẩn', status: 'info', icon: 'ph-factory' },
                        { label: 'Mã Số Thuế', value: '0900234567', status: 'info', icon: 'ph-identification-badge' },
                        { label: 'Tổng PO Năm 2026', value: '14.2 Tỷ ₫', status: 'success', icon: 'ph-vault' }
                    ],
                    table: {
                        title: 'Hồ Sơ Năng Lực Nhà Cung Cấp Thép Tiêu Chuẩn',
                        columns: ['Thông Tin Đối Tác', 'Giá Trị Chi Tiết'],
                        rows: [
                            ['Tên Pháp Nhân', 'Tập Đoàn Thép Công Nghiệp Tiêu Chuẩn'],
                            ['Địa Chỉ Nhà Máy', 'KCN Phố Nối A, Xã Giai Phạm, Yên Mỹ, Hưng Yên'],
                            ['Hạn Mức Tín Dụng', '10.000.000.000 ₫ (Thời hạn thanh toán: 30 ngày)'],
                            ['Đánh Giá Chất Lượng', '99.2% Đạt chuẩn kiểm định JIS G3101']
                        ]
                    },
                    json: {
                        partner_id: 60,
                        partner_name: 'Tập Đoàn Thép Công Nghiệp Tiêu Chuẩn',
                        tax_id: '0900234567',
                        rating: 'TIER-1 STRATEGIC SUPPLIER',
                        active_pos_count: 4
                    }
                },
                {
                    timestamp: 22.0,
                    act: 2,
                    chapter: 'Đối Soát Đơn Hàng #VN-PO2026-001',
                    operationalState: 'INSPECTION',
                    stateBadge: 'ĐỐI SOÁT ĐƠN HÀNG',
                    stateColor: 'primary',
                    model: 'purchase.order',
                    recordId: 1,
                    actionId: 758,
                    metrics: [
                        { label: 'Mã Đơn Mua', value: '#VN-PO2026-001', status: 'info', icon: 'ph-receipt' },
                        { label: 'Tổng Giá Trị', value: '537.000.000 ₫', status: 'success', icon: 'ph-money' },
                        { label: 'Ngày Duyệt Đơn', value: '2026-09-27 15:44', status: 'success', icon: 'ph-calendar-check' }
                    ],
                    table: {
                        title: 'Đơn Đặt Hàng Thép Tiêu Chuẩn #VN-PO2026-001',
                        columns: ['Mã Vật Tư', 'Mô Tả Vật Liệu', 'Số Lượng', 'Đơn Giá (₫)', 'Thành Tiền (₫)'],
                        rows: [
                            ['RM-STEEL-SS400-12', 'Thép tấm SS400 (Dày 12mm x Khổ 1.5x6m)', '20.000 kg (20 Tấn)', '19.500 ₫', '390.000.000 ₫'],
                            ['RM-STEEL-BOX100', 'Thép hộp mạ kẽm nhúng nóng 100x100x4mm (6m)', '600 m (100 Cây)', '245.000 ₫', '147.000.000 ₫']
                        ]
                    },
                    json: {
                        po_id: 1,
                        name: 'Đơn mua hàng #VN-PO2026-001',
                        vendor: 'Tập Đoàn Thép Công Nghiệp Tiêu Chuẩn',
                        date_order: '2026-09-13',
                        date_approve: '2026-09-27 15:44:12',
                        amount_total: 537000000.0,
                        tolerance_limit_percent: 2.0,
                        receipt_picking: 'WH/IN/00006'
                    }
                },
                {
                    timestamp: 42.0,
                    act: 2,
                    chapter: 'Liên Kết 3 Chiều Phiếu Kho & Hóa Đơn',
                    operationalState: '3-WAY MATCHED',
                    stateBadge: '3-WAY MATCH 100%',
                    stateColor: 'success',
                    model: 'purchase.order',
                    recordId: 1,
                    actionId: 758,
                    metrics: [
                        { label: 'Phiếu Nhập Kho', value: 'WH/IN/00006 Đã gán', status: 'success', icon: 'ph-package' },
                        { label: 'Hóa Đơn Đã Khớp', value: 'BILL/2026/09/0001', status: 'success', icon: 'ph-file-check' },
                        { label: 'Sai Lệch Giá & Lượng', value: '0.00 ₫ (Khớp 100%)', status: 'success', icon: 'ph-shield-check' }
                    ],
                    table: {
                        title: 'Bảng Đối Soát 3 Chiều (3-Way Matching Proof)',
                        columns: ['Chứng Từ Đối Chiếu', 'Mã Hiệu', 'Giá Trị', 'Trạng Thái Khớp'],
                        rows: [
                            ['1. Đơn Mua Hàng (PO)', '#VN-PO2026-001', '537.000.000 ₫', 'ĐÃ DUYỆT (Approved)'],
                            ['2. Phiếu Nhập Kho (GRN)', 'WH/IN/00006', '20.000 kg + 600m', 'ĐÃ KIỂM ĐỊNH (Assigned)'],
                            ['3. Hóa Đơn Người Bán', 'BILL/2026/09/0001', '429.550.000 ₫ (Đợt 1)', 'ĐÃ VÀO SỔ (Posted)']
                        ]
                    },
                    json: {
                        po_reference: '#VN-PO2026-001',
                        three_way_match: 'PASSED',
                        price_discrepancy_vnd: 0,
                        qty_discrepancy_kg: 0,
                        journal_entry: 'BILL/2026/09/0001',
                        compliance: 'VAS 200 / TT 200'
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'TRẢI NGHIỆM THỰC TẾ',
                    stateColor: 'success',
                    model: 'purchase.order',
                    recordId: 1,
                    actionId: 758,
                    metrics: [
                        { label: 'Chống Lãng Phí', value: '-100% Sai Lệch Giá', status: 'success', icon: 'ph-check-circle' },
                        { label: 'Thời Gian Đối Soát', value: '< 3.5 Giây', status: 'success', icon: 'ph-lightning' },
                        { label: 'Tuân Thủ Pháp Lý', value: 'Thông Tư 78/200', status: 'info', icon: 'ph-scales' }
                    ],
                    table: {
                        title: 'Lộ Trình Triển Khai Kiểm Soát Mua Hàng Insilos',
                        columns: ['Giai Đoạn', 'Thời Gian', 'Mục Tiêu Đạt Được'],
                        rows: [
                            ['W1: Cấu Hình Nhà Cung Cấp', 'Ngày 1 - 7', 'Chuẩn hóa danh mục NCC thép, cáp, linh kiện'],
                            ['W2: Khóa Chốt Dung Sai', 'Ngày 8 - 14', 'Kích hoạt bộ lọc giá và hạn ngạch cổng cân'],
                            ['W3: Vận Hành Tự Động', 'Ngày 15+', '100% PO được đối soát 3 chiều tự động']
                        ]
                    },
                    json: {
                        action: 'Schedule Procurement Live Demo',
                        target_route: '/request-demo'
                    }
                }
            ]
        },

        'VID_03_INV': {
            id: 'VID_03_INV',
            code: 'VID-03',
            badge: 'KHO BÃI & BARCODE CÁP',
            title: 'Kiểm Kê Cáp Điện Tiêu Chuẩn 3.500m & Quét Barcode Truy Vết Lô',
            domain: 'Inventory & Barcode',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_03_INV_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_03_INV_GOLD_MASTER_poster.webp',
            defaultModel: 'stock.picking',
            defaultRecordId: 2,
            defaultActionId: 258,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Cuộn Cáp & Thất Thoát', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác Quét Barcode Kho Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Cảnh Báo Tồn Kho Ảo Cáp Đồng', act: 1, desc: 'Gian lận cắt xén cáp và thất thoát mẩu thừa' },
                { time: 10.0, title: 'Khởi Động Thiết Bị Quét Barcode Kho', act: 2, desc: 'Tần số quét 1760Hz nhận diện mã vạch tức thời' },
                { time: 22.0, title: 'Truy Vết Số Lô LOT-CABLE-3X16', act: 2, desc: 'Nhập kho 3.500m cáp đồng mềm 3x16+1x10mm²' },
                { time: 35.0, title: 'Phân Loại Tự Động Mẩu Cắt Dưới 1.5m', act: 2, desc: 'Chống gian lận hao hụt cơ điện phân xưởng' },
                { time: 45.0, title: 'Hạch Toán Tự Động Giá Vốn Vật Tư', act: 2, desc: 'Cập nhật thẻ kho và bút toán Nợ 152' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Trải nghiệm số hóa kho bãi công nghiệp' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Cảnh Báo Tồn Kho Ảo Cáp Đồng',
                    operationalState: 'INVENTORY RISK',
                    stateBadge: 'RỦI RO THẤT THOÁT',
                    stateColor: 'danger',
                    model: 'stock.picking',
                    recordId: 2,
                    actionId: 258,
                    metrics: [
                        { label: 'Tỷ Lệ Hao Hụt Cáp', value: '8.5% Hàng năm', status: 'alert', icon: 'ph-warning' },
                        { label: 'Giá Trị Thất Thoát', value: '185 Triệu ₫/kho', status: 'alert', icon: 'ph-trend-down' },
                        { label: 'Độ Trễ Thẻ Kho', value: '48 Giờ ghi tay', status: 'warning', icon: 'ph-clock-countdown' }
                    ],
                    table: {
                        title: 'Hiện Trạng Quản Lý Cáp Điện Nhà Xưởng Truyền Thống',
                        columns: ['Điểm Đau Vận Hành', 'Nguyên Nhân Cốt Lõi', 'Hậu Quả Tài Chính'],
                        rows: [
                            ['Cắt lẻ không ghi nhận', 'Không có máy quét di động', 'Thất thoát mẩu vụn 1.5m - 3m'],
                            ['Tồn kho ảo trên sổ sách', 'Nhập liệu thủ công cuối ngày', 'Đứt gãy tiến độ lắp ráp V-LIFT'],
                            ['Mất dấu xuất xứ số lô', 'Tem nhãn giấy bị rách/ẩm ướt', 'Trượt tiêu chuẩn nghiệm thu PDI']
                        ]
                    },
                    json: {
                        warehouse_risk: 'CABLE_SCRAP_FRAUD',
                        material_code: 'RM-CABLE-STD',
                        annual_loss_vnd: 185000000,
                        lot_tracking_status: 'UNAUTOMATED'
                    }
                },
                {
                    timestamp: 10.0,
                    act: 2,
                    chapter: 'Khởi Động Thiết Bị Quét Barcode Kho',
                    operationalState: 'SCANNER ONLINE',
                    stateBadge: 'MÁY QUÉT 1760HZ',
                    stateColor: 'info',
                    model: 'stock.picking',
                    recordId: 2,
                    actionId: 258,
                    metrics: [
                        { label: 'Tần Số Âm Học Bíp', value: '1.760 Hz Chuẩn', status: 'success', icon: 'ph-speaker-high' },
                        { label: 'Tốc Độ Quét', value: '< 0.25 Giây/Mã', status: 'success', icon: 'ph-barcode' },
                        { label: 'Độ Chính Xác STP', value: '100.0%', status: 'success', icon: 'ph-check-circle' }
                    ],
                    table: {
                        title: 'Phiếu Nhập Kho Cáp Điện Tiêu Chuẩn (WH/IN/00002)',
                        columns: ['Mã Vạch Quét', 'Sản Phẩm', 'Số Lượng', 'Kho Đích', 'Trạng Thái'],
                        rows: [
                            ['BC-CABLE-3X16-01', 'Cáp Điện Tiêu Chuẩn 3x16+1x10mm²', '1.500 m', 'WH/Stock/Rack-C01', 'ĐÃ XÁC NHẬN'],
                            ['BC-CABLE-3X16-02', 'Cáp Điện Tiêu Chuẩn 3x16+1x10mm²', '2.000 m', 'WH/Stock/Rack-C02', 'ĐÃ XÁC NHẬN']
                        ]
                    },
                    json: {
                        picking_name: 'WH/IN/00002',
                        scanner_device: 'Zebra TC26 Industrial Terminal',
                        scan_beep_frequency_hz: 1760,
                        operator: 'Thủ kho Nguyễn Tuấn Kiệt',
                        verified_barcode: '8935001245892'
                    }
                },
                {
                    timestamp: 25.0,
                    act: 2,
                    chapter: 'Truy Vết Số Lô LOT-CABLE-3X16',
                    operationalState: 'LOT TRACING ACTIVE',
                    stateBadge: 'TRUY VẾT SỐ LÔ',
                    stateColor: 'primary',
                    model: 'stock.picking',
                    recordId: 2,
                    actionId: 258,
                    metrics: [
                        { label: 'Số Lô Vật Tư', value: 'LOT-CABLE-2026-01', status: 'success', icon: 'ph-tag' },
                        { label: 'Tổng Khối Lượng', value: '3.500 Mét', status: 'info', icon: 'ph-ruler' },
                        { label: 'Giá Trị Lô Hàng', value: '507.500.000 ₫', status: 'success', icon: 'ph-currency-circle-dollar' }
                    ],
                    table: {
                        title: 'Phả Hệ Dữ Liệu Lô Cáp Điện Tiêu Chuẩn 3x16+1x10mm²',
                        columns: ['Thông Số Kiểm Tra', 'Số Liệu Đo Kiểm', 'Tiêu Chuẩn Công Bố'],
                        rows: [
                            ['Điện trở ruột dẫn 20°C', '1.15 Ω/km', 'TCVN 5935-1 / IEC 60502-1'],
                            ['Độ dày cách điện PVC', '1.0 mm', 'Đạt chuẩn kiểm định Quatest 3'],
                            ['Khả năng chịu tải dòng điện', '82 Ampe', 'Đạt điều kiện an toàn V-LIFT 2500E']
                        ]
                    },
                    json: {
                        lot_name: 'LOT-CABLE-2026-01',
                        product_id: 139,
                        product_code: 'RM-CABLE-STD',
                        quantity: 3500.0,
                        uom: 'm',
                        unit_cost_vnd: 145000.0,
                        quality_test_result: 'PASSED'
                    }
                },
                {
                    timestamp: 40.0,
                    act: 2,
                    chapter: 'Phân Loại Tự Động Mẩu Cắt Dưới 1.5m',
                    operationalState: 'SCRAP AVOIDANCE',
                    stateBadge: 'CHỐNG PHẾ LIỆU',
                    stateColor: 'success',
                    model: 'stock.picking',
                    recordId: 2,
                    actionId: 258,
                    metrics: [
                        { label: 'Mẩu Thừa < 1.5m', value: '0.0 Mét Thất Thoát', status: 'success', icon: 'ph-shield-check' },
                        { label: 'Đoạn Tái Sử Dụng', value: '100% Gán Cụm Batery', status: 'success', icon: 'ph-recycle' },
                        { label: 'Tiết Kiệm Vật Tư', value: '+42.5 Triệu ₫/tháng', status: 'success', icon: 'ph-chart-line-up' }
                    ],
                    table: {
                        title: 'Quy Chuẩn Tái Phân Bổ Mẩu Dây Cáp Cắt Thừa',
                        columns: ['Chiều Dài Cắt', 'Số Lượng', 'Mục Đích Sử Dụng', 'Hiệu Quả'],
                        rows: [
                            ['Đoạn dài 15.0m', '100 Đoạn', 'Lắp cụm Chassis tới Trụ nâng', 'Khớp 100% BOM xe kéo'],
                            ['Đoạn ngắn 1.2m', '40 Đoạn', 'Dây nối tiếp các Pack pin Lithium', 'Tận dụng 100% mẩu ngắn'],
                            ['Phế liệu đồng thực tế', '0.00 kg', 'Không thải loại mẩu thừa', 'Tiết kiệm 8.5% chi phí cáp']
                        ]
                    },
                    json: {
                        cut_optimization_algorithm: '1D Bin-Packing Knapsack',
                        scrap_percentage: 0.0,
                        recycled_segments_count: 40,
                        monthly_cost_reduction_vnd: 42500000
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'KHO THÔNG MINH',
                    stateColor: 'success',
                    model: 'stock.picking',
                    recordId: 2,
                    actionId: 258,
                    metrics: [
                        { label: 'Tốc Độ Kiểm Kê', value: 'Nhanh Hơn 8x', status: 'success', icon: 'ph-gauge' },
                        { label: 'Sai Lệch Tồn Kho', value: '0.00% Tuyệt Đối', status: 'success', icon: 'ph-check-circle' }
                    ],
                    table: {
                        title: 'Chuyển Đổi Quản Trị Kho Toàn Diện Cùng Insilos Barcode',
                        columns: ['Hạng Mục', 'Cam Kết Insilos'],
                        rows: [
                            ['Phần Cứng Tương Thích', 'Zebra, Honeywell, Datalogic, Điện thoại Android'],
                            ['Triển Khai Kho', '7 Ngày Go-Live tại nhà máy cơ khí'],
                            ['Hiệu Quả Hoàn Vốn', 'Hoàn vốn đầu tư sau 45 ngày']
                        ]
                    },
                    json: {
                        cta: 'Book Warehouse Audit Session',
                        url: '/showcase-3d#insilos-gold-suite'
                    }
                }
            ]
        },

        'VID_04_BOM': {
            id: 'VID_04_BOM',
            code: 'VID-04',
            badge: 'BOM ĐA CẤP & LASER CNC',
            title: 'BOM Đa Tầng Xe Kéo V-LIFT 2500E & Lệnh Cắt Laser WH/MO/00010',
            domain: 'Manufacturing & BOM',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_04_BOM_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_04_BOM_GOLD_MASTER_poster.webp',
            defaultModel: 'mrp.production',
            defaultRecordId: 10,
            defaultActionId: 367,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Cắt Laser & Rủi Ro BOM', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác MO & Laser CNC Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Cảnh Báo Lệch Định Mức Cơ Khí', act: 1, desc: 'Lãng phí 18% thép tấm & đứt tiến độ V-LIFT' },
                { time: 10.0, title: 'Điều Hướng Lệnh Sản Xuất MO', act: 2, desc: 'Mở Form View lệnh sản xuất WH/MO/00010' },
                { time: 22.0, title: 'Phân Rã BOM 2 Cấp (Chassis Sub-BOM)', act: 2, desc: 'Kiểm kê thép SS400, thép hộp & sơn Epoxy' },
                { time: 35.0, title: 'Trạm Máy WC-CUT-01 Fiber Laser 12kW', act: 2, desc: 'Kích hoạt công đoạn cắt phôi thép dày 12mm' },
                { time: 44.0, title: 'Đo Lường OEE Phân Xưởng 92.5%', act: 2, desc: 'Đồng bộ SCADA thời gian thực trạm máy' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Trải nghiệm số hóa sản xuất Insilos MES' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Cảnh Báo Lệch Định Mức Cơ Khí',
                    operationalState: 'CRITICAL RISK',
                    stateBadge: 'LÃNG PHÍ VẬT TƯ',
                    stateColor: 'danger',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Lệch Định Mức Thép', value: '18.4% Thất thoát', status: 'alert', icon: 'ph-warning' },
                        { label: 'Phế Liệu Khung Gầm', value: '450 kg/xe', status: 'alert', icon: 'ph-trash' },
                        { label: 'Trễ Hạn Giao Hàng', value: '14 Ngày trì hoãn', status: 'alert', icon: 'ph-alarm' }
                    ],
                    table: {
                        title: 'Tổn Thất Do Sai Lệch BOM Sản Xuất Truyền Thống',
                        columns: ['Công Đoạn Gia Công', 'Sai Lệch Định Mức', 'Thiệt Hại / 4 Xe'],
                        rows: [
                            ['Cắt Phôi Laser CNC', 'Xếp hình phôi thủ công (Nesting)', 'Tốn thêm 1.800 kg thép tấm SS400 (35.1 Triệu ₫)'],
                            ['Chấn Gấp Định Hình', 'Sai bán kính chấn R', 'Phế phẩm 3 cụm dầm chịu lực'],
                            ['Hàn Robot Yaskawa', 'Lệch khe hở mối hàn > 2mm', 'Dừng dây chuyền hàn tự động 6.5 giờ']
                        ]
                    },
                    json: {
                        risk_type: 'BOM_DISCREPANCY_SCRAP',
                        product_id: 148,
                        product_code: 'EQ-VLIFT-2500E',
                        assembly_name: 'Xe kéo hàng điện nhà xưởng V-LIFT 2500E',
                        bom_levels: 2,
                        scrap_cost_vnd: 35100000
                    }
                },
                {
                    timestamp: 10.0,
                    act: 2,
                    chapter: 'Điều Hướng Lệnh Sản Xuất MO',
                    operationalState: 'NAVIGATING MO',
                    stateBadge: 'LỆNH SẢN XUẤT LIVE',
                    stateColor: 'info',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Lệnh Sản Xuất', value: 'WH/MO/00010', status: 'info', icon: 'ph-gear-six' },
                        { label: 'Trạng Thái', value: 'Đang Sản Xuất (Progress)', status: 'info', icon: 'ph-play-circle' },
                        { label: 'Số Lượng Sản Xuất', value: '4.00 Chiếc Cụm', status: 'success', icon: 'ph-stack' }
                    ],
                    table: {
                        title: 'Thông Tin Lệnh Sản Xuất WH/MO/00010',
                        columns: ['Thuộc Tính', 'Giá Trị Hệ Thống Odoo 20 Live'],
                        rows: [
                            ['Thành Phẩm Sản Xuất', 'SF-CHASSIS-25E: Cụm Khung gầm Chassis hàn gia công'],
                            ['Định Mức Sử Dụng', 'BOM ID 11: BOM-CHASSIS-25E-V1'],
                            ['Thời Gian Bắt Đầu', '2026-09-27 02:18:19 (Theo tiến độ KCN)'],
                            ['Thời Lượng Dự Kiến', '1.080 Phút (18 Giờ gia công liên hoàn)']
                        ]
                    },
                    json: {
                        mo_id: 10,
                        name: 'WH/MO/00010',
                        product_code: 'SF-CHASSIS-25E',
                        product_qty: 4.0,
                        qty_producing: 4.0,
                        date_start: '2026-09-27 02:18:19',
                        date_finished_scheduled: '2026-09-30 12:30:00'
                    }
                },
                {
                    timestamp: 22.0,
                    act: 2,
                    chapter: 'Phân Rã BOM 2 Cấp (Chassis Sub-BOM)',
                    operationalState: 'BOM EXPLOSION',
                    stateBadge: 'PHÂN RÃ BOM 2 CẤP',
                    stateColor: 'primary',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Vật Tư Đã Giữ Chỗ', value: '100% Assigned', status: 'success', icon: 'ph-check-circle' },
                        { label: 'Thép SS400 Giữ Chỗ', value: '1.800 kg Đủ', status: 'success', icon: 'ph-package' },
                        { label: 'Thép Hộp 100x100', value: '96.0 Mét Đủ', status: 'success', icon: 'ph-cube' }
                    ],
                    table: {
                        title: 'Định Mức Cấu Thành Sub-BOM Khung Gầm (BOM-CHASSIS-25E-V1)',
                        columns: ['Mã Linh Kiện', 'Tên Nguyên Vật Liệu', 'Định Mức 1 Xe', 'Tổng Nhu Cầu (4 Xe)', 'Đơn Giá (₫)'],
                        rows: [
                            ['RM-STEEL-SS400-12', 'Thép tấm cán nóng kết cấu SS400 12mm', '450.0 kg', '1.800.0 kg', '19.500 ₫/kg'],
                            ['RM-STEEL-BOX100', 'Thép hộp mạ kẽm 100x100x4.0mm (Cây 6m)', '24.0 m', '96.0 m', '245.000 ₫/m'],
                            ['RM-PAINT-JOTUN-EP', 'Sơn tĩnh điện công nghiệp Epoxy Jotun', '18.0 kg', '72.0 kg', '135.000 ₫/kg']
                        ]
                    },
                    json: {
                        bom_code: 'BOM-CHASSIS-25E-V1',
                        parent_bom_code: 'BOM-VLIFT-2500E-V1',
                        components: [
                            { code: 'RM-STEEL-SS400-12', qty_required: 1800.0, uom: 'kg', stock_move_id: 204, state: 'assigned' },
                            { code: 'RM-STEEL-BOX100', qty_required: 96.0, uom: 'm', stock_move_id: 205, state: 'assigned' },
                            { code: 'RM-PAINT-JOTUN-EP', qty_required: 72.0, uom: 'kg', stock_move_id: 206, state: 'assigned' }
                        ]
                    }
                },
                {
                    timestamp: 35.0,
                    act: 2,
                    chapter: 'Trạm Máy WC-CUT-01 Fiber Laser 12kW',
                    operationalState: 'WO IN PROGRESS',
                    stateBadge: 'FIBER LASER 12KW',
                    stateColor: 'warning',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Công Đoạn WO 40', value: 'Cắt Laser & Đột Lỗ', status: 'warning', icon: 'ph-fire' },
                        { label: 'Phân Xưởng', value: 'WC-CUT-01 Trumpf', status: 'info', icon: 'ph-cpu' },
                        { label: 'Thời Gian Chu Kỳ', value: '300 Phút (5 Giờ)', status: 'info', icon: 'ph-timer' }
                    ],
                    table: {
                        title: 'Tiến Trình 4 Công Đoạn Gia Công Phân Xưởng',
                        columns: ['Mã WO', 'Tên Công Đoạn', 'Trạm Máy', 'Thời Lượng', 'Trạng Thái'],
                        rows: [
                            ['WO ID 40', 'Cắt phôi thép SS400 bằng máy Laser CNC', 'WC-CUT-01 (Laser 12kW)', '300 min', 'ĐANG CHẠY (Progress)'],
                            ['WO ID 41', 'Chấn gấp định hình góc chữ U', 'WC-BEND-01 (Chấn 250T)', '180 min', 'CHỜ PHÔI (Blocked)'],
                            ['WO ID 42', 'Gá đồ gá & Hàn liên kết Robot Yaskawa', 'WC-WELD-01 (Robot hàn)', '360 min', 'CHỜ HÀN (Blocked)'],
                            ['WO ID 43', 'Tẩy dầu nano & Phun sơn sấy tĩnh điện', 'WC-PAINT-01 (Buồng sơn)', '240 min', 'CHỜ SƠN (Blocked)']
                        ]
                    },
                    json: {
                        active_workorder_id: 40,
                        workcenter: 'Phân xưởng Cắt Fiber Laser & Đột dập CNC (WC-CUT-01)',
                        laser_power_kw: 12.0,
                        gas_assist: 'Nitrogen High-Pressure 18 bar',
                        nesting_efficiency: '94.2%',
                        cutting_speed_m_min: 4.8
                    }
                },
                {
                    timestamp: 44.0,
                    act: 2,
                    chapter: 'Đo Lường OEE Phân Xưởng 92.5%',
                    operationalState: 'OEE PEAK',
                    stateBadge: 'OEE ĐẠT 92.5%',
                    stateColor: 'success',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Chỉ Số OEE Máy Cắt', value: '92.5% WORLD-CLASS', status: 'success', icon: 'ph-gauge' },
                        { label: 'Tính Khả Dụng (A)', value: '96.2%', status: 'success', icon: 'ph-chart-pie' },
                        { label: 'Hiệu Suất (P)', value: '98.1%', status: 'success', icon: 'ph-lightning' }
                    ],
                    table: {
                        title: 'Bảng Phân Tích 3 Trụ Cột OEE Thiết Bị Laser CNC',
                        columns: ['Trụ Cột OEE', 'Chỉ Số Đo Được', 'Ngưỡng Chuẩn Công Nghiệp', 'Đánh Giá'],
                        rows: [
                            ['Tính Khả Dụng (Availability)', '96.2%', '>= 90.0%', 'XUẤT SẮC (Dừng máy < 15p)'],
                            ['Hiệu Suất Tốc Độ (Performance)', '98.1%', '>= 95.0%', 'TỐI ƯU (Tốc độ cắt 4.8m/p)'],
                            ['Tỷ Lệ Chất Lượng (Quality)', '98.2%', '>= 98.0%', 'CHUẨN XÁC (0 phôi lỗi PDI)'],
                            ['Chỉ Số OEE Tổng Hợp', '92.5%', '>= 85.0% World Class', 'ĐẠT HUY CHƯƠNG VÀNG']
                        ]
                    },
                    json: {
                        oee_overall: 0.925,
                        availability: 0.962,
                        performance: 0.981,
                        quality: 0.982,
                        iot_sensor_bus: 'MQTT / OPC-UA Active',
                        vibration_mms: 0.84,
                        spindle_temp_c: 41.5
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'KẾT THÚC HOÀN HẢO',
                    stateColor: 'success',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Sản Lượng Hoàn Thành', value: '4/4 Xe V-LIFT', status: 'success', icon: 'ph-check-circle' },
                        { label: 'Thời Gian Gia Công', value: 'Đúng Hạn 100%', status: 'success', icon: 'ph-calendar-check' }
                    ],
                    table: {
                        title: 'Đăng Ký Khảo Sát Tự Động Hóa Phân Xưởng Cơ Khí',
                        columns: ['Thông Tin Hỗ Trợ', 'Cam Kết Insilos'],
                        rows: [
                            ['Đào Tạo Kỹ Sư Vận Hành', 'Trực tiếp tại phân xưởng trong 3 ngày'],
                            ['Tích Hợp PLC / CNC', 'Kết nối Trumpf, Amada, Yaskawa qua OPC-UA'],
                            ['Bảo Hành Nền Tảng', '24/7 SLA phản hồi sự cố < 15 phút']
                        ]
                    },
                    json: {
                        cta: 'Trực quan hóa trên Odoo Live',
                        deep_link: 'http://localhost:28069/web#id=10&model=mrp.production&view_type=form&action=367'
                    }
                }
            ]
        },

        'VID_05_PLN': {
            id: 'VID_05_PLN',
            code: 'VID-05',
            badge: 'ĐIỀU ĐỘ KẾ HOẠCH GANTT',
            title: 'Điều Độ Kế Hoạch Sản Xuất Gantt & Cân Bằng Phụ Tải Máy',
            domain: 'Planning & Gantt',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_05_PLN_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_05_PLN_GOLD_MASTER_poster.webp',
            defaultModel: 'mrp.production',
            defaultRecordId: 10,
            defaultActionId: 367,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Nhà Máy & Nút Thắt Cổ Chai', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác Biểu Đồ Gantt Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Nút Thắt Cổ Chai Phân Xưởng', act: 1, desc: 'Máy chấn quá tải làm trễ đơn giao hàng' },
                { time: 10.0, title: 'Mở Biểu Đồ Gantt Điều Độ Phân Xưởng', act: 2, desc: 'Trực quan hóa công suất 4 trạm máy CNC' },
                { time: 22.0, title: 'Cân Bằng Phụ Tải Trumpf & Yaskawa', act: 2, desc: 'Chia tải tự động giữa máy chấn và robot hàn' },
                { time: 35.0, title: 'Kéo Thả Giải Quyết Xung Đột Lịch', act: 2, desc: 'Tái sắp xếp lệnh gấp không gây thời gian chết' },
                { time: 45.0, title: 'Xuất Lệnh Đến Tablet Phân Xưởng', act: 2, desc: 'Đồng bộ tức thời bảng tin ca kíp' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Tối ưu công suất sản xuất cùng Insilos' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Nút Thắt Cổ Chai Phân Xưởng',
                    operationalState: 'BOTTLENECK WARNING',
                    stateBadge: 'QUÁ TẢI TRẠM MÁY',
                    stateColor: 'danger',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Phụ Tải Máy Chấn', value: '142.0% Quá tải', status: 'alert', icon: 'ph-warning' },
                        { label: 'Thời Gian Chờ Đợi', value: '18 Giờ chết', status: 'alert', icon: 'ph-hourglass' },
                        { label: 'Lệnh MO Bị Nghẽn', value: '6 Lệnh dồn ứ', status: 'alert', icon: 'ph-traffic-cone' }
                    ],
                    table: {
                        title: 'Phân Tích Nút Thắt Cổ Chai Thiết Bị Gia Công',
                        columns: ['Trạm Máy', 'Công Suất Thiết Kế', 'Phụ Tải Thực Tế', 'Tình Trạng'],
                        rows: [
                            ['WC-CUT-01 Laser CNC', '16h/ngày', '14.5h/ngày (90.6%)', 'HOẠT ĐỘNG TỐT'],
                            ['WC-BEND-01 Chấn 250T', '16h/ngày', '22.7h/ngày (142%)', 'NGHẼN CỔ CHAI NẶNG'],
                            ['WC-WELD-01 Robot Hàn', '16h/ngày', '9.2h/ngày (57.5%)', 'THIẾU VIỆC (Đang chờ)']
                        ]
                    },
                    json: {
                        bottleneck_detected: true,
                        critical_station: 'WC-BEND-01',
                        utilization_rate: 1.42,
                        recommended_action: 'Re-balance sub-components to auxiliary stations'
                    }
                },
                {
                    timestamp: 22.0,
                    act: 2,
                    chapter: 'Cân Bằng Phụ Tải Trumpf & Yaskawa',
                    operationalState: 'GANTT BALANCING',
                    stateBadge: 'ĐIỀU ĐỘ GANTT CÂN BẰNG',
                    stateColor: 'success',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Phụ Tải Sau Cân Bằng', value: '88.5% Đồng đều', status: 'success', icon: 'ph-scales' },
                        { label: 'Thời Gian Chết Máy', value: 'Giảm 94.0%', status: 'success', icon: 'ph-clock-countdown' },
                        { label: 'Năng Suất Xuất Xưởng', value: '+35.0% Lô/tuần', status: 'success', icon: 'ph-chart-line-up' }
                    ],
                    table: {
                        title: 'Biểu Đồ Cân Bằng Năng Lực Trạm Máy (Workcenter Load)',
                        columns: ['Trạm Máy', 'Phụ Tải Trước', 'Phụ Tải Sau Cân Bằng', 'Thời Gian Hoàn Tất'],
                        rows: [
                            ['Laser CNC (WC-CUT-01)', '90.6%', '92.0%', '28/09 13:00'],
                            ['Máy Chấn (WC-BEND-01)', '142.0%', '88.0%', '29/09 10:30'],
                            ['Robot Hàn (WC-WELD-01)', '57.5%', '89.5%', '30/09 08:30'],
                            ['Buồng Sơn (WC-PAINT-01)', '70.0%', '86.0%', '30/09 12:30']
                        ]
                    },
                    json: {
                        gantt_algorithm: 'Critical Chain Path & Capacity Heuristics',
                        conflict_resolved: true,
                        total_cycle_saved_hours: 18.5,
                        scheduled_delivery: '2026-09-30 12:30:00 (On-Time 100%)'
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'ĐIỀU HÀNH THÔNG MINH',
                    stateColor: 'success',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Giao Hàng Đúng Hạn', value: '99.4% SLA', status: 'success', icon: 'ph-check-circle' },
                        { label: 'Giảm Lead Time', value: '-3.5 Ngày', status: 'success', icon: 'ph-timer' }
                    ],
                    table: {
                        title: 'Giải Pháp Điều Độ Sản Xuất Tức Thời Insilos MRP',
                        columns: ['Lợi Ích Doanh Nghiệp', 'Chỉ Số Định Lượng'],
                        rows: [
                            ['Cân Bằng Tự Động', 'Tính toán biểu đồ Gantt trong < 2.0 giây'],
                            ['Phản Ứng Sự Cố', 'Tự động dời lịch khi máy báo hỏng sau 5s'],
                            ['Khả Năng Mở Rộng', 'Quản lý đồng thời 200+ máy CNC phân tán']
                        ]
                    },
                    json: {
                        cta: 'Khai mở tiềm năng nhà máy',
                        action_url: 'http://localhost:28069/web#id=10&model=mrp.production&view_type=form&action=367'
                    }
                }
            ]
        },

        'VID_06_SFL': {
            id: 'VID_06_SFL',
            code: 'VID-06',
            badge: 'SHOP FLOOR TABLET MES',
            title: 'Shop Floor Tablet Xưởng Cơ Khí & Đo OEE Thời Gian Thực',
            domain: 'MES & Shop Floor',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_06_SFL_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_06_SFL_GOLD_MASTER_poster.webp',
            defaultModel: 'mrp.production',
            defaultRecordId: 10,
            defaultActionId: 367,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Tablet & Bụi Xưởng Cơ Khí', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác Chạm Tablet Xưởng Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Rủi Ro Thất Lạc Lệnh Giấy', act: 1, desc: 'Phiếu giao việc bị rách, sai phiên bản bản vẽ' },
                { time: 10.0, title: 'Đăng Nhập Tablet Chống Bụi IP65', act: 2, desc: 'Giao diện nút bấm lớn phù hợp găng tay bảo hộ' },
                { time: 22.0, title: 'Kích Hoạt Công Đoạn WO 40', act: 2, desc: 'Bấm Bắt đầu công đoạn, đồng hồ đo thời gian chạy' },
                { time: 35.0, title: 'Bảng Điều Khiển OEE Trạm Máy', act: 2, desc: 'OEE 92.5%, phụ tải 96.2%, không phế phẩm' },
                { time: 45.0, title: 'Nghiệm Thu PDI Khung Chassis', act: 2, desc: 'Quét mã xác nhận hoàn thành 4 khung gầm' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Xóa bỏ 100% giấy tờ tại phân xưởng' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Rủi Ro Thất Lạc Lệnh Giấy',
                    operationalState: 'PAPER OPERATIONAL RISK',
                    stateBadge: 'LỆNH GIẤY THẤT LẠC',
                    stateColor: 'danger',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Thất Lạc Phiếu Việc', value: '12 Phiếu/tháng', status: 'alert', icon: 'ph-file-x' },
                        { label: 'Gia Công Nhầm Bản Vẽ', value: '4 Mẻ phế phẩm', status: 'alert', icon: 'ph-warning' },
                        { label: 'Thời Gian Báo Cáo', value: 'Cuối ngày (Trễ 8h)', status: 'warning', icon: 'ph-clock' }
                    ],
                    table: {
                        title: 'So Sánh Quản Lý Xưởng Cơ Khí: Giấy Tờ vs Tablet Insilos',
                        columns: ['Tiêu Chí', 'Lệnh Giấy Truyền Thống', 'Insilos Shop Floor Tablet'],
                        rows: [
                            ['Cập Nhật Bản Vẽ', 'In lại giấy, nguy cơ nhầm bản cũ', 'Tự động đồng bộ CAD 3D mới nhất'],
                            ['Bắt Đầu / Dừng Máy', 'Ghi tay sổ ca kíp', 'Chạm 1 nút trên màn hình cảm ứng'],
                            ['Phát Hiện Sự Cố', 'Gọi điện thoại hoặc tìm quản đốc', 'Nhấn nút cảnh báo Andon trên máy']
                        ]
                    },
                    json: {
                        shop_floor_audit: 'PAPERLESS_TRANSITION',
                        workcenter: 'WC-CUT-01',
                        tablet_model: 'Samsung Galaxy Tab Active4 Pro Rugged',
                        ip_rating: 'IP68 & MIL-STD-810H'
                    }
                },
                {
                    timestamp: 25.0,
                    act: 2,
                    chapter: 'Bảng Điều Khiển OEE Trạm Máy',
                    operationalState: 'MES TOUCH ONLINE',
                    stateBadge: 'MES TABLET REAL-TIME',
                    stateColor: 'success',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'OEE Trạm Laser', value: '92.5% VƯỢT CHUẨN', status: 'success', icon: 'ph-gauge' },
                        { label: 'Sản Lượng Hoàn Thành', value: '4/4 Khung Chassis', status: 'success', icon: 'ph-check-square' },
                        { label: 'Cảnh Báo Andon', value: '0 Sự Cố (Bình thường)', status: 'success', icon: 'ph-shield-check' }
                    ],
                    table: {
                        title: 'Nhật Trình Vận Hành Ca Trạm Máy Cắt Fiber Laser',
                        columns: ['Mốc Thời Gian', 'Thao Tác Công Nhân', 'Thời Lượng Ghi Nhận', 'Trạng Thái'],
                        rows: [
                            ['07:30 - 07:45', 'Bảo trì đầu ca, vệ sinh bép cắt', '15 phút', 'HOÀN TẤT'],
                            ['07:45 - 11:45', 'Gia công phôi tấm SS400 12mm', '240 phút', 'ĐANG CHẠY'],
                            ['11:45 - 12:45', 'Nghỉ trưa theo quy định', '60 phút', 'KẾ HOẠCH'],
                            ['12:45 - 13:45', 'Đột dập lỗ định vị bu lông', '60 phút', 'HOÀN THÀNH']
                        ]
                    },
                    json: {
                        tablet_session_id: 'SFL-SESSION-2026-0927-01',
                        operator_badge: 'OP-782 (Trần Đình Trọng)',
                        oee_score: 0.925,
                        parts_completed: 4,
                        rejection_count: 0
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'MINH BẠCH PHÂN XƯỞNG',
                    stateColor: 'success',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Tỷ Lệ Giấy Tờ', value: '0% Giấy tờ (Paperless)', status: 'success', icon: 'ph-tree' },
                        { label: 'Độ Trễ Dữ Liệu', value: '< 100 Milliseconds', status: 'success', icon: 'ph-broadcast' }
                    ],
                    table: {
                        title: 'Lợi Ích Khi Trang Bị Tablet Cho 100% Công Nhân Xưởng',
                        columns: ['Chỉ Số', 'Trước Insilos', 'Sau Insilos'],
                        rows: [
                            ['Thời gian nhập liệu', '45 phút / ca', '0 phút (Tự động)'],
                            ['Tỷ lệ sai sót phiếu', '6.8%', '0.0% Tuyệt đối'],
                            ['Thời gian phản hồi sự cố', '2.5 Giờ', '< 3 Phút']
                        ]
                    },
                    json: {
                        deep_link: 'http://localhost:28069/web#id=10&model=mrp.production&view_type=form&action=367'
                    }
                }
            ]
        },

        'VID_07_FLT': {
            id: 'VID_07_FLT',
            code: 'VID-07',
            badge: 'QUẢN TRỊ ĐỘI XE VẬN TẢI',
            title: 'Giám Sát Đầu Kéo 51C-982.45, ODO 142.500km & Định Mức Dầu PVOIL',
            domain: 'Fleet & Fuel',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_07_FLT_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_07_FLT_GOLD_MASTER_poster.webp',
            defaultModel: 'fleet.vehicle',
            defaultRecordId: 6,
            defaultActionId: 738,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Đường Cao Tốc & Gian Lận Dầu', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác Hồ Sơ Đội Xe Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Cảnh Báo Thất Thoát Dầu DO & ODO', act: 1, desc: 'Gian lận hút trộm dầu và làm sai lệch đồng hồ ODO' },
                { time: 10.0, title: 'Mở Danh Mục Xe Tải Nặng Container', act: 2, desc: 'Hồ sơ đầu kéo 51C-982.45 Hyundai Xcient GT 440PS' },
                { time: 22.0, title: 'Đối Soát Km ODO 142.500km Tuyến Cảng', act: 2, desc: 'Tăng trưởng +24.500km trên hành lang Cảng Biển Quốc Tế' },
                { time: 34.0, title: 'Kiểm Tra Phiếu Xăng Dầu PVOIL 7.525.000₫', act: 2, desc: 'Đối chiếu hóa đơn PTX-CL-98245-01 và trạm bơm' },
                { time: 44.0, title: 'Định Mức Nhiên Liệu Giảm -18.4%', act: 2, desc: 'Đạt 34L/100km so với định mức 42L/100km cũ' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Khóa cứng chi phí đội xe vận tải' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Cảnh Báo Thất Thoát Dầu DO & ODO',
                    operationalState: 'FLEET FUEL RISK',
                    stateBadge: 'THẤT THOÁT DẦU DO',
                    stateColor: 'danger',
                    model: 'fleet.vehicle',
                    recordId: 6,
                    actionId: 738,
                    metrics: [
                        { label: 'Thất Thoát Dầu Ước Tính', value: '18.4% / Đội xe', status: 'alert', icon: 'ph-drop' },
                        { label: 'Chi Phí Lãng Phí', value: '45 Triệu ₫/đầu xe/năm', status: 'alert', icon: 'ph-warning' },
                        { label: 'Rủi Ro Tua Đồng Hồ', value: 'Lệch ODO 12.000km', status: 'alert', icon: 'ph-speedometer' }
                    ],
                    table: {
                        title: 'Các Lỗ Hổng Quản Trị Đội Xe Container Cảng Biển',
                        columns: ['Điểm Đau', 'Phương Thức Gian Lận', 'Biện Pháp Chặn Đứng Insilos'],
                        rows: [
                            ['Hút trộm dầu dọc đường', 'Mua bán hóa đơn khống cây xăng', 'Tích hợp cảm biến siêu âm đáy bình dầu'],
                            ['Chạy sai tuyến đường', 'Nhận hàng ngoài giờ hợp đồng', 'GPS Geofencing cảnh báo lệch hành lang'],
                            ['Khai man chi phí sửa chữa', 'Lập chứng từ bảo dưỡng ảo', 'Khóa đối chiếu 3 chiều hóa đơn PVOIL']
                        ]
                    },
                    json: {
                        fleet_audit: 'FUEL_THEFT_PREVENTION',
                        vehicle_plate: '51C-982.45',
                        model: 'Hyundai Xcient GT 440PS',
                        fuel_type: 'Diesel 0.05S',
                        estimated_leakage_pct: 18.4
                    }
                },
                {
                    timestamp: 22.0,
                    act: 2,
                    chapter: 'Đối Soát Km ODO 142.500km Tuyến Cảng',
                    operationalState: 'TELEMATICS AUDIT',
                    stateBadge: 'ODO XÁC THỰC 142.500KM',
                    stateColor: 'success',
                    model: 'fleet.vehicle',
                    recordId: 6,
                    actionId: 738,
                    metrics: [
                        { label: 'Chỉ Số ODO Hiện Tại', value: '142.500 km', status: 'success', icon: 'ph-gauge' },
                        { label: 'Km Chạy Trong Tháng', value: '+24.500 km', status: 'info', icon: 'ph-road-horizon' },
                        { label: 'Đơn Vị Vận Hành', value: 'Depot Cảng Biển Quốc Tế', status: 'info', icon: 'ph-buildings' }
                    ],
                    table: {
                        title: 'Lịch Sử Đoạn Đường & Nhật Trình Xe 51C-982.45',
                        columns: ['Ngày Ghi Nhận', 'Chỉ Số ODO', 'Chênh Lệch', 'Tuyến Đường', 'Trạng Thái'],
                        rows: [
                            ['2026-05-30', '118.000 km', 'Gốc ban đầu', 'Cảng Biển - KCN VSIP 1', 'ĐÃ KIỂM ĐỊNH'],
                            ['2026-08-15', '132.400 km', '+14.400 km', 'Liên cảng quốc tế', 'ĐÃ KIỂM ĐỊNH'],
                            ['2026-09-25', '142.500 km', '+10.100 km', 'Liên cảng quốc tế', 'XÁC THỰC GPS']
                        ]
                    },
                    json: {
                        vehicle_id: 6,
                        license_plate: '51C-982.45',
                        vin_number: 'KMHFB18WPMA012456',
                        odometer_km: 142500.0,
                        last_reading_date: '2026-09-25',
                        gps_odometer_delta_pct: 0.02
                    }
                },
                {
                    timestamp: 38.0,
                    act: 2,
                    chapter: 'Kiểm Tra Phiếu Xăng Dầu PVOIL 7.525.000₫',
                    operationalState: 'PVOIL INTEGRATION',
                    stateBadge: 'HÓA ĐƠN PVOIL KHỚP',
                    stateColor: 'success',
                    model: 'fleet.vehicle',
                    recordId: 6,
                    actionId: 738,
                    metrics: [
                        { label: 'Số Hóa Đơn Dầu', value: 'PTX-CL-98245-01', status: 'success', icon: 'ph-receipt' },
                        { label: 'Tiền Dầu Thực Tế', value: '7.525.000 ₫', status: 'success', icon: 'ph-currency-circle-dollar' },
                        { label: 'Tiêu Hao Đo Được', value: '34 L/100km (-18.4%)', status: 'success', icon: 'ph-trend-down' }
                    ],
                    table: {
                        title: 'Nhật Trình Cấp Phát Dầu & Dịch Vụ PVOIL / Petrolimex',
                        columns: ['Mã Chứng Từ', 'Ngày Thực Hiện', 'Số Lít Dầu DO', 'Đơn Giá', 'Tổng Tiền (₫)'],
                        rows: [
                            ['PTX-CL-98245-01', '2026-09-24', '334.4 L', '22.500 ₫/L', '7.525.000 ₫'],
                            ['HD-BD-2026-0982', '2026-09-12', 'Thay lọc dầu & mỡ', 'Trọn gói', '6.800.000 ₫']
                        ]
                    },
                    json: {
                        fuel_service_log_id: 5,
                        vendor: 'Tổng Công ty Dầu Việt Nam - CTCP (PVOIL)',
                        inv_ref: 'PTX-CL-98245-01',
                        cost_vnd: 7525000.0,
                        fuel_rate_l_per_100km: 34.0,
                        rate_benchmark: 42.0,
                        savings_pct: 18.4
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'ĐỘI XE THÔNG MINH',
                    stateColor: 'success',
                    model: 'fleet.vehicle',
                    recordId: 6,
                    actionId: 738,
                    metrics: [
                        { label: 'Đầu Xe Quản Lý', value: '10 - 200+ Xe', status: 'success', icon: 'ph-truck' },
                        { label: 'Tiết Kiệm Dầu/Năm', value: '1.2 Tỷ ₫ / 25 Xe', status: 'success', icon: 'ph-piggy-bank' }
                    ],
                    table: {
                        title: 'Cam Kết Nền Tảng Insilos Fleet Management',
                        columns: ['Hạng Mục', 'Cam Kết', 'Khả Năng Tích Hợp'],
                        rows: [
                            ['Cảm Biến Đáy Bình', 'Đo dung tích dầu chính xác 99.5%', 'Gắn trực tiếp bình dầu 400L'],
                            ['API Cây Xăng', 'Tự động tải hóa đơn điện tử PVOIL', 'Không cần lái xe giữ hóa đơn giấy'],
                            ['Bảo Hành Cảm Biến', 'Bảo hành 1 đổi 1 trong 24 tháng', 'Đạt chuẩn phòng nổ ATEX']
                        ]
                    },
                    json: {
                        deep_link: 'http://localhost:28069/web#id=6&model=fleet.vehicle&view_type=form&action=738'
                    }
                }
            ]
        },

        'VID_08_FUL': {
            id: 'VID_08_FUL',
            code: 'VID-08',
            badge: 'AN TOÀN & ĐĂNG KIỂM',
            title: 'Khóa Chốt An Toàn Đăng Kiểm Rơ-moóc 51R-089.34 & Tự Động Phê Duyệt',
            domain: 'Safety & Compliance',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_08_FUL_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_08_FUL_GOLD_MASTER_poster.webp',
            defaultModel: 'fleet.vehicle',
            defaultRecordId: 8,
            defaultActionId: 738,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Trạm Cân & Phạt Kiểm Định', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác Khóa An Toàn Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Nguy Cơ Phạt Đăng Kiểm Rơ-moóc', act: 1, desc: 'Bỏ lỡ hạn kiểm định tại cổng cảng biển' },
                { time: 10.0, title: 'Mở Hồ Sơ Rơ-moóc 51R-089.34', act: 2, desc: 'Sơ mi rơ moóc CIMC 40ft (VIN CIMC40HC20240981)' },
                { time: 22.0, title: 'Cảnh Báo Khóa Chốt An Toàn Tự Động', act: 2, desc: 'Khóa điều xe nếu quá hạn kiểm định QCVN 11' },
                { time: 35.0, title: 'Quy Trình Duyệt Gia Hạn Đăng Kiểm', act: 2, desc: 'Đính kèm chứng nhận và kích hoạt lại xe' },
                { time: 46.0, title: 'Xác Nhận Hợp Chuẩn Bộ Giao Thông', act: 2, desc: 'Tái cấp phép điều xe ra vào cổng cảng' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Không còn rủi ro phạt kiểm định vận tải' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Nguy Cơ Phạt Đăng Kiểm Rơ-moóc',
                    operationalState: 'SAFETY COMPLIANCE RISK',
                    stateBadge: 'RỦI RO KIỂM ĐỊNH',
                    stateColor: 'danger',
                    model: 'fleet.vehicle',
                    recordId: 8,
                    actionId: 738,
                    metrics: [
                        { label: 'Mức Phạt Quá Hạn', value: '16-22 Triệu ₫/xe', status: 'alert', icon: 'ph-warning-octagon' },
                        { label: 'Tước Phù Hiệu Xe', value: '1 - 3 Tháng', status: 'alert', icon: 'ph-hand' },
                        { label: 'Đình Trệ Hàng Hóa', value: '40ft Bị giữ cảng', status: 'alert', icon: 'ph-lock' }
                    ],
                    table: {
                        title: 'Rủi Ro Pháp Lý Vận Tải Theo Nghị Định 100/2019/NĐ-CP',
                        columns: ['Hành Vi Vi Phạm', 'Mức Phạt Doanh Nghiệp', 'Hệ Lụy Vận Hành'],
                        rows: [
                            ['Rơ-moóc quá hạn kiểm định', '14.000.000 ₫ - 20.000.000 ₫', 'Giam xe tại bãi, đình trệ vỏ container'],
                            ['Không có phù hiệu xe tải', '10.000.000 ₫ - 12.000.000 ₫', 'Cảng biển từ chối cấp lệnh hạ bãi'],
                            ['Lốp mòn dưới rãnh an toàn', '2.000.000 ₫ - 4.000.000 ₫', 'Nguy cơ nổ lốp trên cầu vành đai']
                        ]
                    },
                    json: {
                        regulatory_code: 'QCVN 11:2015/BGTVT',
                        target_unit: '51R-089.34',
                        chassis_type: 'CIMC 3-Axle 40ft Skeleton Trailer',
                        compliance_state: 'EXPIRED_WARNING'
                    }
                },
                {
                    timestamp: 25.0,
                    act: 2,
                    chapter: 'Cảnh Báo Khóa Chốt An Toàn Tự Động',
                    operationalState: 'SAFETY LOCK ENGAGED',
                    stateBadge: 'KHÓA ĐIỀU XE TỰ ĐỘNG',
                    stateColor: 'warning',
                    model: 'fleet.vehicle',
                    recordId: 8,
                    actionId: 738,
                    metrics: [
                        { label: 'Trạng Thái Khóa Chốt', value: 'LOCKED / DISALLOW', status: 'alert', icon: 'ph-lock-key' },
                        { label: 'Lệnh Điều Xe Bị Chặn', value: 'Tự động ngăn xuất bến', status: 'warning', icon: 'ph-prohibit' },
                        { label: 'Thông Báo Tới', value: 'Quản đốc & Đăng kiểm viên', status: 'info', icon: 'ph-bell-ringing' }
                    ],
                    table: {
                        title: 'Cơ Chế Khóa Chốt An Toàn Insilos Safety Gate',
                        columns: ['Thông Số Kiểm Tra', 'Kết Quả Quét', 'Hành Động Hệ Thống'],
                        rows: [
                            ['Hạn đăng kiểm rơ-moóc', '2026-09-26 (Đã quá 24h)', 'KÍCH HOẠT KHÓA KHẨN CẤP'],
                            ['Phần mềm điều độ drayage', 'Nhận tín hiệu Lock từ Odoo Fleet', 'Ẩn xe khỏi danh sách gán cuốc'],
                            ['Cổng bảo vệ xuất xưởng', 'Quét biển số camera OCR', 'Đèn đỏ, không mở thanh chắn barie']
                        ]
                    },
                    json: {
                        safety_interlock_active: true,
                        lock_reason: 'MANDATORY_INSPECTION_OVERDUE',
                        vehicle_id: 8,
                        plate: '51R-089.34',
                        interlock_policy: 'ZERO_DEFECT_DISPATCH'
                    }
                },
                {
                    timestamp: 45.0,
                    act: 2,
                    chapter: 'Xác Nhận Hợp Chuẩn Bộ Giao Thông',
                    operationalState: 'REGISTERED VERIFIED',
                    stateBadge: 'ĐĂNG KIỂM HỢP CHUẨN',
                    stateColor: 'success',
                    model: 'fleet.vehicle',
                    recordId: 8,
                    actionId: 738,
                    metrics: [
                        { label: 'Giấy Chứng Nhận Mới', value: 'KD-2026-98104 Đã duyệt', status: 'success', icon: 'ph-certificate' },
                        { label: 'Thời Hạn Mới', value: 'Đến 2027-09-25 (12T)', status: 'success', icon: 'ph-calendar' },
                        { label: 'Mở Khóa Điều Xe', value: 'UNLOCKED / ACTIVE', status: 'success', icon: 'ph-lock-key-open' }
                    ],
                    table: {
                        title: 'Hồ Sơ Đăng Kiểm Điện Tử Đã Được Xác Thực',
                        columns: ['Mục Kiểm Định', 'Kết Quả Kiểm Tra', 'Cơ Quan Đăng Kiểm'],
                        rows: [
                            ['Hệ thống phanh khí nén', 'Đạt hiệu quả phanh 64.5%', 'Trung tâm Đăng kiểm 50-03V'],
                            ['Khung xương chassi', 'Không nứt vỡ rỉ sét', 'Trung tâm Đăng kiểm 50-03V'],
                            ['Hệ thống đèn tín hiệu', 'Đèn LED đạt độ rọi chuẩn', 'Trung tâm Đăng kiểm 50-03V']
                        ]
                    },
                    json: {
                        inspection_cert: 'KD-2026-98104',
                        valid_until: '2027-09-25',
                        state: 'Registered',
                        dispatch_allowed: true
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'AN TOÀN TUYỆT ĐỐI',
                    stateColor: 'success',
                    model: 'fleet.vehicle',
                    recordId: 8,
                    actionId: 738,
                    metrics: [
                        { label: 'Tỷ Lệ Bị Phạt', value: '0 Đồng (100% An toàn)', status: 'success', icon: 'ph-shield-check' }
                    ],
                    table: {
                        title: 'Chuẩn Hóa An Toàn Đội Xe Cùng Insilos Fleet',
                        columns: ['Tiêu Chuẩn', 'Ứng Dụng Thực Tiễn'],
                        rows: [
                            ['Nhắc hạn tự động', 'Gửi email & SMS trước 30 ngày, 15 ngày, 7 ngày'],
                            ['Lưu trữ hồ sơ', 'Lưu trữ đám mây Sovereign chuẩn Nghị định 13']
                        ]
                    },
                    json: {
                        deep_link: 'http://localhost:28069/web#id=8&model=fleet.vehicle&view_type=form&action=738'
                    }
                }
            ]
        },

        'VID_09_LOG': {
            id: 'VID_09_LOG',
            code: 'VID-09',
            badge: 'LOGISTICS & PHÍ DET/DEM',
            title: 'Điều Xe Drayage Liên Cảng Liên cảng quốc tế & Cảnh Báo DET/DEM',
            domain: 'Port Logistics',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_09_LOG_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_09_LOG_GOLD_MASTER_poster.webp',
            defaultModel: 'sale.order',
            defaultRecordId: 2,
            defaultActionId: 561,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Cẩu Bờ Cảng Biển & Tắc Cảng', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác Cảnh Báo DET/DEM Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Khủng Hoảng Phí Lưu Bãi DET/DEM', act: 1, desc: '120 USD/container/ngày khi trễ hạn cảng' },
                { time: 10.0, title: 'Hợp Đồng Kéo Hàng Gemadept #VN-SO2026-002', act: 2, desc: '50 Chuyến kéo container Cảng Biển - VSIP Bình Dương' },
                { time: 22.0, title: 'Lệnh Xuất Bến WH/OUT/00001 & Container TCLU', act: 2, desc: 'Xe 51C-982.45 nhận vỏ container TCLU-582194-0' },
                { time: 35.0, title: 'Radar Giám Sát Free Time DET/DEM', act: 2, desc: 'Còn 36.2 giờ / 48 giờ miễn phí lưu bãi' },
                { time: 45.0, title: 'Tiết Kiệm -88% Phí Phạt Lưu Bãi', act: 2, desc: 'Hạ bãi an toàn trước mốc cảnh báo 12 giờ' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Giải phóng container tức thời cùng Insilos' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Khủng Hoảng Phí Lưu Bãi DET/DEM',
                    operationalState: 'DET/DEM RISK',
                    stateBadge: 'CẢNH BÁO DET/DEM',
                    stateColor: 'danger',
                    model: 'sale.order',
                    recordId: 2,
                    actionId: 561,
                    metrics: [
                        { label: 'Phí Phạt DEM/Ngày', value: '$120 USD / Container', status: 'alert', icon: 'ph-warning' },
                        { label: 'Tỷ Lệ Trễ Hạn Cảng', value: '23.5% Mùa cao điểm', status: 'alert', icon: 'ph-clock-countdown' },
                        { label: 'Tắc Nghẽn Cổng Cảng Biển', value: '3.5 - 6 Giờ chờ đợi', status: 'alert', icon: 'ph-traffic-signal' }
                    ],
                    table: {
                        title: 'Biểu Phí Phạt Lưu Bãi Hãng Tàu (Maersk, ONE, CMA CGM)',
                        columns: ['Số Ngày Quá Hạn', 'Đơn Giá / Ngày (20ft)', 'Đơn Giá / Ngày (40ft)', 'Tổng Phạt (Lô 10 Cont)'],
                        rows: [
                            ['Ngày 1 - 3', '$45 USD', '$85 USD', '21.250.000 ₫/ngày'],
                            ['Ngày 4 - 7', '$75 USD', '$120 USD', '30.000.000 ₫/ngày'],
                            ['Ngày 8 trở đi', '$110 USD', '$180 USD', '45.000.000 ₫/ngày']
                        ]
                    },
                    json: {
                        shipping_line: 'ONE / Ocean Network Express',
                        terminal: 'Cụm Cảng Biển CY04',
                        dem_rate_usd: 120.0,
                        free_time_limit_hours: 48.0
                    }
                },
                {
                    timestamp: 22.0,
                    act: 2,
                    chapter: 'Hợp Đồng Kéo Hàng Gemadept #VN-SO2026-002',
                    operationalState: 'DRAYAGE DISPATCH',
                    stateBadge: 'HỢP ĐỒNG GEMADEPT',
                    stateColor: 'info',
                    model: 'sale.order',
                    recordId: 2,
                    actionId: 561,
                    metrics: [
                        { label: 'Tổng Giá Trị Hợp Đồng', value: '1.4525 Tỷ ₫', status: 'success', icon: 'ph-coins' },
                        { label: 'Số Lượng Chuyến', value: '50 Chuyến Cont 40ft', status: 'info', icon: 'ph-truck' },
                        { label: 'Đơn Giá Cước', value: '3.850.000 ₫/Chuyến', status: 'info', icon: 'ph-receipt' }
                    ],
                    table: {
                        title: 'Đơn Bán Hàng #VN-SO2026-002 (Gemadept Logistics)',
                        columns: ['Mã Dịch Vụ', 'Nội Dung Tuyến Vận Tải', 'Số Lượng', 'Đơn Giá', 'Thành Tiền (₫)'],
                        rows: [
                            ['TR-TRAIL-40HC', 'Sơ mi rơ moóc tải nặng chuyên dụng 40ft', '3 Unit', '420.000.000 ₫', '1.260.000.000 ₫'],
                            ['SRV-TRUCK-CL-VSIP', 'Dịch vụ Kéo Container Tuyến Cảng Biển - VSIP', '50 Chuyến', '3.850.000 ₫', '192.500.000 ₫']
                        ]
                    },
                    json: {
                        so_id: 2,
                        partner: 'Công ty CP Gemadept Logistics',
                        tax_id: '0303126789',
                        amount_total: 1452500000.0,
                        picking_id: 3,
                        picking_name: 'WH/OUT/00001'
                    }
                },
                {
                    timestamp: 35.0,
                    act: 2,
                    chapter: 'Radar Giám Sát Free Time DET/DEM',
                    operationalState: 'RADAR ACTIVE',
                    stateBadge: 'RADAR FREE TIME AN TOÀN',
                    stateColor: 'success',
                    model: 'sale.order',
                    recordId: 2,
                    actionId: 561,
                    metrics: [
                        { label: 'Thời Gian Free Time', value: '36.2h / 48.0h (75%)', status: 'success', icon: 'ph-timer' },
                        { label: 'Vị Trí Xe 51C-982.45', value: 'Xa lộ Hà Nội (Đúng tiến độ)', status: 'success', icon: 'ph-navigation-arrow' },
                        { label: 'Tiết Kiệm Phí Phạt', value: '-88.0% Phí DET/DEM', status: 'success', icon: 'ph-shield-check' }
                    ],
                    table: {
                        title: 'Hành Lang Điều Xe Drayage Tránh Phạt Lưu Bãi',
                        columns: ['Số Container', 'Hành Trình', 'Free Time Còn Lại', 'Đánh Giá Rủi Ro'],
                        rows: [
                            ['TCLU-582194-0', 'Cảng Biển -> KCN VSIP 1', '36.2 Giờ', 'AN TOÀN (Vùng Xanh)'],
                            ['TEMU-841920-3', 'Cảng Biển -> KCN VSIP 2', '41.0 Giờ', 'AN TOÀN (Vùng Xanh)'],
                            ['CMAU-190284-9', 'Cái Mép -> KCN VSIP 1', '44.5 Giờ', 'AN TOÀN (Vùng Xanh)']
                        ]
                    },
                    json: {
                        container_no: 'TCLU-582194-0',
                        free_time_remaining_hours: 36.2,
                        free_time_total_hours: 48.0,
                        risk_level: 'SAFE',
                        penalty_avoided_usd: 240.0
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'TỐI ƯU CẢNG BIỂN',
                    stateColor: 'success',
                    model: 'sale.order',
                    recordId: 2,
                    actionId: 561,
                    metrics: [
                        { label: 'Tốc Độ Hạ Bãi', value: 'Nhanh Hơn 45%', status: 'success', icon: 'ph-lightning' },
                        { label: 'Phí Phạt Hãng Tàu', value: '0.00 ₫ (Triệt để)', status: 'success', icon: 'ph-check-circle' }
                    ],
                    table: {
                        title: 'Liên Kết Vận Hành Cảng Liên cảng quốc tế Cùng Insilos',
                        columns: ['Tuyến Hành Lang', 'Thời Gian Vận Chuyển', 'Cam Kết Tiết Kiệm'],
                        rows: [
                            ['Cảng Biển - VSIP 1', '1h45p (Tối ưu hóa tránh giờ cấm tải)', 'Tiết kiệm 240.000 ₫ tiền dầu/chuyến'],
                            ['Cái Mép - VSIP 2', '2h30p (Qua đường Vành đai 3)', 'Giảm 100% rủi ro trễ closing time tàu']
                        ]
                    },
                    json: {
                        deep_link: 'http://localhost:28069/web#id=2&model=sale.order&view_type=form&action=561'
                    }
                }
            ]
        },

        'VID_10_SAL': {
            id: 'VID_10_SAL',
            code: 'VID-10',
            badge: 'HÓA ĐƠN ĐIỆN TỬ TT 78',
            title: 'Phát Hành Hóa Đơn Điện Tử Viettel S-Invoice Thông Tư 78 Tức Thì',
            domain: 'E-Invoice Circular 78',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_10_SAL_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_10_SAL_GOLD_MASTER_poster.webp',
            defaultModel: 'account.move',
            defaultRecordId: 12,
            defaultActionId: 476,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Sổ Kế Toán & Rủi Ro Thuế', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác Ký Điện Tử S-Invoice Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Rủi Ro Sai Lệch Hóa Đơn TT 78', act: 1, desc: 'Lệch phiếu xuất kho và hóa đơn bị phạt thuế nặng' },
                { time: 10.0, title: 'Mở Phân Hệ Hóa Đơn & Kế Toán', act: 2, desc: 'Hóa đơn khách hàng INV/2026/00001 (Tiếp Vận Cảng Biển)' },
                { time: 22.0, title: 'Đối Soát Chi Tiết 1.050.500.000₫', act: 2, desc: 'Doanh thu 955M + Thuế GTGT 10% (95.5M)' },
                { time: 34.0, title: 'Ký Số XML & Gửi Cơ Quan Thuế CQT', act: 2, desc: 'Tích hợp cổng Viettel S-Invoice cấp mã tức thời' },
                { time: 45.0, title: 'Đồng Bộ Sổ Nhật Ký Kế Toán TT 200', act: 2, desc: 'Nợ 131 / Có 5112 / Có 33311 cân đối tuyệt đối' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Tuân thủ thuế trọn gói cùng Insilos' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Rủi Ro Sai Lệch Hóa Đơn TT 78',
                    operationalState: 'TAX COMPLIANCE RISK',
                    stateBadge: 'RỦI RO PHẠT THUẾ',
                    stateColor: 'danger',
                    model: 'account.move',
                    recordId: 12,
                    actionId: 476,
                    metrics: [
                        { label: 'Khung Phạt Xuất Trễ', value: '4 - 8 Triệu ₫ / HĐ', status: 'alert', icon: 'ph-warning' },
                        { label: 'Từ Chối Khấu Trừ VAT', value: '100% Giá trị thuế', status: 'alert', icon: 'ph-x-circle' },
                        { label: 'Sai Lệch Thời Điểm', value: 'Xuất sau giao hàng', status: 'alert', icon: 'ph-clock' }
                    ],
                    table: {
                        title: 'Quy Định Bắt Buộc Theo Nghị Định 123/2020 & Thông Tư 78/2021',
                        columns: ['Tiêu Chuẩn', 'Yêu Cầu Pháp Lý', 'Xử Lý Của Insilos'],
                        rows: [
                            ['Thời điểm lập hóa đơn', 'Cùng ngày chuyển giao quyền sở hữu', 'Tự động kích hoạt khi ký phiếu giao nhận'],
                            ['Mã của Cơ quan Thuế', 'Bắt buộc cấp mã trước khi gửi khách', 'Kết nối trực tiếp API Tổng Cục Thuế'],
                            ['Định dạng dữ liệu', 'Chuẩn dữ liệu XML Thông tư 78', 'Ký số HSM Cloud tốc độ < 1.2 giây']
                        ]
                    },
                    json: {
                        regulation: 'Circular 78/2021/TT-BTC & Decree 123/2020/ND-CP',
                        risk_scenario: 'LATE_INVOICING_PENALTY',
                        compliance_target: 'AUTOMATIC_INVOICING_ON_DELIVERY'
                    }
                },
                {
                    timestamp: 22.0,
                    act: 2,
                    chapter: 'Đối Soát Chi Tiết 1.050.500.000₫',
                    operationalState: 'INVOICE FORM REVIEW',
                    stateBadge: 'HÓA ĐƠN INV/2026/00001',
                    stateColor: 'primary',
                    model: 'account.move',
                    recordId: 12,
                    actionId: 476,
                    metrics: [
                        { label: 'Số Tiền Chưa Thuế', value: '955.000.000 ₫', status: 'info', icon: 'ph-money' },
                        { label: 'Thuế GTGT 10%', value: '95.500.000 ₫', status: 'info', icon: 'ph-percent' },
                        { label: 'Tổng Tiền Thanh Toán', value: '1.050.500.000 ₫', status: 'success', icon: 'ph-currency-circle-dollar' }
                    ],
                    table: {
                        title: 'Nội Dung Hóa Đơn Điện Tử Bán Thành Phẩm Cảng Biển',
                        columns: ['Sản Phẩm Nghiệp Vụ', 'Số Lượng', 'Đơn Giá (₫)', 'Thuế Suất', 'Tổng Tiền (₫)'],
                        rows: [
                            ['Xe kéo điện V-LIFT 2500E', '2.0 Unit', '385.000.000 ₫', '10%', '847.000.000 ₫'],
                            ['Trạm sạc nhanh DC 60kW', '1.0 Unit', '185.000.000 ₫', '10%', '203.500.000 ₫']
                        ]
                    },
                    json: {
                        invoice_id: 12,
                        name: 'INV/2026/00001',
                        partner_name: 'Tổng Công Ty Tiếp Vận Cảng Biển Quốc Tế',
                        tax_id: '0300481234',
                        move_type: 'out_invoice',
                        state: 'posted',
                        amount_untaxed: 955000000.0,
                        amount_tax: 95500000.0,
                        amount_total: 1050500000.0
                    }
                },
                {
                    timestamp: 35.0,
                    act: 2,
                    chapter: 'Ký Số XML & Gửi Cơ Quan Thuế CQT',
                    operationalState: 'CQT SIGNED',
                    stateBadge: 'CQT CẤP MÃ HỢP LỆ',
                    stateColor: 'success',
                    model: 'account.move',
                    recordId: 12,
                    actionId: 476,
                    metrics: [
                        { label: 'Cổng Hóa Đơn', value: 'Viettel S-Invoice API', status: 'success', icon: 'ph-shield-check' },
                        { label: 'Mã Cơ Quan Thuế', value: '002348910248921', status: 'success', icon: 'ph-barcode' },
                        { label: 'Thời Gian Cấp Mã', value: '< 1.2 Giây', status: 'success', icon: 'ph-lightning' }
                    ],
                    table: {
                        title: 'Thông Tin Ký Số HSM & Cấp Mã Cơ Quan Thuế',
                        columns: ['Thuộc Tính Ký Số', 'Giá Trị Kỹ Thuật'],
                        rows: [
                            ['Chứng Thư Số Nhà Cung Cấp', 'Viettel-CA Cloud HSM Server'],
                            ['Thuật Toán Băm Chữ Ký', 'SHA-256 with RSA Encryption 2048-bit'],
                            ['Mã Nhận Hóa Đơn Thuế', '002348910248921 (Tổng Cục Thuế tiếp nhận hợp lệ)'],
                            ['Email Gửi Tự Động Khách Hàng', 'ketoan@saigonnewport.com.vn (Đã gửi link tra cứu)']
                        ]
                    },
                    json: {
                        e_invoice_provider: 'Viettel S-Invoice',
                        tax_authority_code: '002348910248921',
                        digital_signature: 'VALID_VERIFIED',
                        transmission_status: 'SUCCESS'
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'KẾ TOÁN SỐ HOÀN HẢO',
                    stateColor: 'success',
                    model: 'account.move',
                    recordId: 12,
                    actionId: 476,
                    metrics: [
                        { label: 'Rủi Ro Sai Hóa Đơn', value: '0.00% Tuyệt Đối', status: 'success', icon: 'ph-check-circle' }
                    ],
                    table: {
                        title: 'Chuẩn Hóa Thuế & Hóa Đơn Doanh Nghiệp',
                        columns: ['Tính Năng', 'Lợi Ích Thực Chứng'],
                        rows: [
                            ['Tự động phát hành', 'Giảm 100% thời gian kế toán gõ lại số liệu'],
                            ['Đồng bộ thuế Thông tư 78', 'An tâm tuyệt đối khi quyết toán thuế cuối năm']
                        ]
                    },
                    json: {
                        deep_link: 'http://localhost:28069/web#id=12&model=account.move&view_type=form&action=476'
                    }
                }
            ]
        },

        'VID_11_ACC': {
            id: 'VID_11_ACC',
            code: 'VID-11',
            badge: 'KẾ TOÁN CHI PHÍ TT 200',
            title: 'Đối Soát 3 Chiều & Hạch Toán Chi Phí Phân Xưởng Thông Tư 200',
            domain: 'Cost Accounting TT 200',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_11_ACC_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_11_ACC_GOLD_MASTER_poster.webp',
            defaultModel: 'account.move',
            defaultRecordId: 15,
            defaultActionId: 479,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Dòng Tiền & Rủi Ro Lệch Sổ', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác Kế Toán TT 200 Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Cảnh Báo Lệch Giá Thành Phân Xưởng', act: 1, desc: 'Lệch chi phí dở dang TK 154 và giá vốn TK 632' },
                { time: 10.0, title: 'Kiểm Tra Hóa Đơn Mua Thép BILL/2026/09/0001', act: 2, desc: 'Số tiền 429.550.000 ₫ mua thép cán nóng' },
                { time: 22.0, title: 'Đối Soát Tự Động 3 Chiều (3-Way Matching)', act: 2, desc: 'Khớp PO #VN-PO2026-001, phiếu kho & hóa đơn' },
                { time: 34.0, title: 'Hạch Toán Sổ Kép Thông Tư 200', act: 2, desc: 'Nợ 152 (390.5M), Nợ 1331 (39.05M), Có 331 (429.55M)' },
                { time: 45.0, title: 'Tập Hợp Chi Phí TK 621/622/627 Sang TK 154', act: 2, desc: 'Kết chuyển tự động giá thành sản xuất V-LIFT' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Minh bạch sổ sách kế toán chuẩn mực' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Cảnh Báo Lệch Giá Thành Phân Xưởng',
                    operationalState: 'ACCOUNTING RISK',
                    stateBadge: 'SAI LỆCH GIÁ THÀNH',
                    stateColor: 'danger',
                    model: 'account.move',
                    recordId: 15,
                    actionId: 479,
                    metrics: [
                        { label: 'Rủi Ro Loại Chi Phí Thuế', value: 'Hàng trăm triệu ₫', status: 'alert', icon: 'ph-warning' },
                        { label: 'Sai Lệch Giá Thành', value: 'Lệch 7.8% Biên lãi', status: 'alert', icon: 'ph-trend-down' },
                        { label: 'Thời Gian Lập BCTC', value: 'Chậm 25 ngày', status: 'warning', icon: 'ph-clock' }
                    ],
                    table: {
                        title: 'Nỗi Đau Kế Toán Giá Thành Cơ Khí Chế Tạo Tại Việt Nam',
                        columns: ['Tài Khoản Kế Toán', 'Sai Lệch Phổ Biến', 'Giải Pháp Insilos TT 200'],
                        rows: [
                            ['TK 621 (Nguyên vật liệu)', 'Không phân bổ được theo từng lệnh MO', 'Tự động trích xuất từ phiếu xuất kho MO'],
                            ['TK 622 (Nhân công)', 'Chấm công giấy, tính lương trễ hạn', 'Đồng bộ giờ máy từ Shop Floor Tablet'],
                            ['TK 154 (Chi phí dở dang)', 'Không kiểm kê được sản phẩm dở dang', 'Đo lường OEE và tỷ lệ % hoàn thành trạm']
                        ]
                    },
                    json: {
                        accounting_standard: 'Circular 200/2014/TT-BTC',
                        costing_method: 'Per-Job Manufacturing Order Costing',
                        risk_area: 'WIP_INVENTORY_VALUATION'
                    }
                },
                {
                    timestamp: 22.0,
                    act: 2,
                    chapter: 'Đối Soát Tự Động 3 Chiều (3-Way Matching)',
                    operationalState: '3-WAY MATCHING',
                    stateBadge: 'ĐỐI SOÁT 3 CHIỀU',
                    stateColor: 'info',
                    model: 'account.move',
                    recordId: 15,
                    actionId: 479,
                    metrics: [
                        { label: 'Trạng Thái 3-Way Match', value: '100% MATCHED', status: 'success', icon: 'ph-check-circle' },
                        { label: 'Hóa Đơn Mua Thép', value: '429.550.000 ₫', status: 'success', icon: 'ph-receipt' },
                        { label: 'Chênh Lệch Đối Soát', value: '0.00 ₫ Tuyệt đối', status: 'success', icon: 'ph-shield-check' }
                    ],
                    table: {
                        title: 'Đối Soát 3 Chiều Đơn Mua Thép Tiêu Chuẩn',
                        columns: ['Hồ Sơ Chứng Từ', 'Mã Tham Chiếu', 'Số Lượng', 'Giá Trị Đơn Hàng'],
                        rows: [
                            ['Đơn Mua Hàng (PO)', '#VN-PO2026-001', '15.000 kg SS400 + 400m', '390.500.000 ₫ (Chưa thuế)'],
                            ['Phiếu Nhập Kho (GRN)', 'WH/IN/00006', '15.000 kg SS400 + 400m', 'Đã nghiệm thu cổng cân'],
                            ['Hóa Đơn NCC (Bill)', 'BILL/2026/09/0001', '15.000 kg SS400 + 400m', '429.550.000 ₫ (Có thuế VAT)']
                        ]
                    },
                    json: {
                        bill_id: 15,
                        bill_name: 'BILL/2026/09/0001',
                        vendor_name: 'Tập Đoàn Thép Công Nghiệp Tiêu Chuẩn',
                        three_way_match_status: 'PASSED',
                        variance_amount: 0.0
                    }
                },
                {
                    timestamp: 35.0,
                    act: 2,
                    chapter: 'Hạch Toán Sổ Kép Thông Tư 200',
                    operationalState: 'DOUBLE ENTRY POSTED',
                    stateBadge: 'SỔ CÁI TT 200',
                    stateColor: 'success',
                    model: 'account.move',
                    recordId: 15,
                    actionId: 479,
                    metrics: [
                        { label: 'Bút Toán Vào Sổ', value: 'POSTED / UNALTERABLE', status: 'success', icon: 'ph-lock' },
                        { label: 'Tài Khoản Ghi Nợ', value: 'TK 152 / TK 1331', status: 'info', icon: 'ph-arrow-down-right' },
                        { label: 'Tài Khoản Ghi Có', value: 'TK 331 (Phải trả NCC)', status: 'info', icon: 'ph-arrow-up-right' }
                    ],
                    table: {
                        title: 'Bút Toán Sổ Kép Thông Tư 200/2014/TT-BTC',
                        columns: ['Số Hiệu TK', 'Tên Tài Khoản Kế Toán', 'Phát Sinh Nợ (₫)', 'Phát Sinh Có (₫)'],
                        rows: [
                            ['TK 152', 'Nguyên liệu, vật liệu (15T Thép SS400 + 400m hộp)', '390.500.000 ₫', '0 ₫'],
                            ['TK 1331', 'Thuế GTGT được khấu trừ 10%', '39.050.000 ₫', '0 ₫'],
                            ['TK 331', 'Phải trả cho người bán (Nhà Cung Cấp Thép)', '0 ₫', '429.550.000 ₫']
                        ]
                    },
                    json: {
                        journal_id: 'Vendor Bills',
                        posted_date: '2026-09-17',
                        total_debit: 429550000.0,
                        total_credit: 429550000.0,
                        balance: 0.0,
                        ledger_compliance: 'CIRCULAR_200_VALID'
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'KẾ TOÁN CHUẨN MỰC',
                    stateColor: 'success',
                    model: 'account.move',
                    recordId: 15,
                    actionId: 479,
                    metrics: [
                        { label: 'Thời Gian Lập BCTC', value: 'Rút Ngắn 80%', status: 'success', icon: 'ph-clock-countdown' }
                    ],
                    table: {
                        title: 'Đăng Ký Tư Vấn Hệ Thống Kế Toán Quản Trị Insilos',
                        columns: ['Dịch Vụ Chuyên Sâu', 'Quy Chuẩn Áp Dụng'],
                        rows: [
                            ['Tự động hóa giá thành phân xưởng', 'Chuẩn mực kế toán VAS 200'],
                            ['Đối soát tự động ngân hàng & NCC', 'STP 99.8% không cần nhân viên gõ tay']
                        ]
                    },
                    json: {
                        deep_link: 'http://localhost:28069/web#id=15&model=account.move&view_type=form&action=479'
                    }
                }
            ]
        },

        'VID_12_MKT': {
            id: 'VID_12_MKT',
            code: 'VID-12',
            badge: 'BCTC & C-LEVEL DASHBOARD',
            title: 'Bảng Cân Đối B01-DN, Báo Cáo KQKD B02-DN & C-Level EBITDA',
            domain: 'Executive Financials',
            duration: 60,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_12_MKT_GOLD_MASTER.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_VID_12_MKT_GOLD_MASTER_poster.webp',
            defaultModel: 'account.move',
            defaultRecordId: 12,
            defaultActionId: 476,
            acts: [
                { id: 1, start: 0, end: 10, name: 'Hồi 1: B-Roll 3D Glass Cockpit & Điểm Mù Quản Trị', color: 'info' },
                { id: 2, start: 10, end: 50, name: 'Hồi 2: Thao Tác BCTC B01 & EBITDA Live', color: 'warning' },
                { id: 3, start: 50, end: 60, name: 'Hồi 3: 25-Thumbnail Mosaic Closing CTA', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Điểm Mù Quản Trị C-Suite', act: 1, desc: 'Báo cáo chậm 15 ngày khiến lãnh đạo mất cơ hội' },
                { time: 10.0, title: 'Bảng Cân Đối Kế Toán B01-DN Live', act: 2, desc: 'Tổng tài sản và nguồn vốn cập nhật thời gian thực' },
                { time: 22.0, title: 'Báo Cáo Kết Quả Kinh Doanh B02-DN', act: 2, desc: 'Doanh thu thuần 18.675 Tỷ & Biên lợi nhuận 24.8%' },
                { time: 35.0, title: 'Cockpit EBITDA & Dòng Tiền Hoạt Động', act: 2, desc: 'Dự báo dòng tiền 90 ngày không gián đoạn' },
                { time: 46.0, title: 'Xác Thực Dấu Vết Kiểm Toán Merkle DAG', act: 2, desc: 'Bảo mật bất biến chống can thiệp số liệu' },
                { time: 50.0, title: 'Closing CTA Suite', act: 3, desc: 'Nâng tầm năng lực điều hành C-Level' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Điểm Mù Quản Trị C-Suite',
                    operationalState: 'EXECUTIVE BLINDSPOT',
                    stateBadge: 'ĐIỂM MÙ ĐIỀU HÀNH',
                    stateColor: 'danger',
                    model: 'account.move',
                    recordId: 12,
                    actionId: 476,
                    metrics: [
                        { label: 'Độ Trễ Báo Cáo', value: '15 - 20 Ngày', status: 'alert', icon: 'ph-clock' },
                        { label: 'Rủi Ro Số Liệu Ảo', value: 'Số liệu không khớp ERP', status: 'alert', icon: 'ph-warning' },
                        { label: 'Khó Khăn Ra Quyết Định', value: 'Phụ thuộc Excel rời rạc', status: 'warning', icon: 'ph-file-x' }
                    ],
                    table: {
                        title: 'Khoảng Cách Ra Quyết Định Giữa Báo Cáo Excel và Insilos Cockpit',
                        columns: ['Tiêu Chí So Sánh', 'Báo Cáo Thủ Công Truyền Thống', 'Insilos Real-Time Executive Cockpit'],
                        rows: [
                            ['Thời gian chốt số liệu', 'Ngày 20 tháng sau', 'Tức thời theo thời gian thực (0 giây)'],
                            ['Nguồn gốc số liệu', 'Gõ tay tổng hợp từ phòng ban', 'Truy vết trực tiếp đến từng chứng từ gốc'],
                            ['Mô phỏng kịch bản What-If', 'Mất 1 tuần viết lại công thức', 'Kéo thanh trượt mô phỏng trong 3 giây']
                        ]
                    },
                    json: {
                        executive_dashboard: 'C_SUITE_REAL_TIME_COCKPIT',
                        status: 'BLINDSPOT_RESOLVED',
                        latency_ms: 12.5
                    }
                },
                {
                    timestamp: 22.0,
                    act: 2,
                    chapter: 'Báo Cáo Kết Quả Kinh Doanh B02-DN',
                    operationalState: 'P&L REAL-TIME AUDIT',
                    stateBadge: 'KQKD B02-DN LIVE',
                    stateColor: 'success',
                    model: 'account.move',
                    recordId: 12,
                    actionId: 476,
                    metrics: [
                        { label: 'Doanh Thu Thuần', value: '18.675 Tỷ ₫', status: 'success', icon: 'ph-trend-up' },
                        { label: 'Biên Lợi Nhuận Gộp', value: '24.8% Vượt Kế Hoạch', status: 'success', icon: 'ph-chart-pie' },
                        { label: 'Chỉ Số EBITDA', value: '4.63 Tỷ ₫', status: 'success', icon: 'ph-coins' }
                    ],
                    table: {
                        title: 'Báo Cáo Kết Quả Hoạt Động Kinh Doanh (Mẫu B02-DN)',
                        columns: ['Mã Số', 'Chỉ Tiêu Tài Chính', 'Kỳ Thực Hiện (VNĐ)', 'Tăng Trưởng'],
                        rows: [
                            ['01', '1. Doanh thu bán hàng và cung cấp dịch vụ', '18.675.000.000 ₫', '+28.4% YoY'],
                            ['11', '2. Giá vốn hàng bán (COGS)', '14.043.600.000 ₫', 'Kiểm soát tốt'],
                            ['20', '3. Lợi nhuận gộp về bán hàng', '4.631.400.000 ₫ (24.8%)', '+4.6% vs Kế hoạch'],
                            ['50', '4. Tổng lợi nhuận kế toán trước thuế', '3.892.000.000 ₫', '+31.2% YoY']
                        ]
                    },
                    json: {
                        report_template: 'B02-DN Circular 200',
                        gross_revenue_vnd: 18675000000,
                        cogs_vnd: 14043600000,
                        gross_profit_vnd: 4631400000,
                        ebitda_vnd: 4631400000,
                        margin_pct: 24.8
                    }
                },
                {
                    timestamp: 50.0,
                    act: 3,
                    chapter: 'Closing CTA Suite',
                    operationalState: 'CLOSING CTA',
                    stateBadge: 'BẢO TOÀN GIÁ TRỊ',
                    stateColor: 'success',
                    model: 'account.move',
                    recordId: 12,
                    actionId: 476,
                    metrics: [
                        { label: 'Bảo Toàn Lợi Nhuận', value: '+18.4% ROI Hàng Năm', status: 'success', icon: 'ph-check-circle' }
                    ],
                    table: {
                        title: 'Đăng Ký Tư Vấn Xây Dựng Dashboard C-Level',
                        columns: ['Khối Doanh Nghiệp', 'Gói Triển Khai'],
                        rows: [
                            ['Sản xuất cơ khí 100-300 công nhân', 'Bàn giao hệ thống Cockpit trong 14 ngày'],
                            ['Vận tải logistics 50-200 đầu kéo', 'Khóa cứng chi phí dầu và dòng tiền sau 7 ngày']
                        ]
                    },
                    json: {
                        deep_link: 'http://localhost:28069/web#id=12&model=account.move&view_type=form&action=476'
                    }
                }
            ]
        },

        'MASTER_CINEMATIC': {
            id: 'MASTER_CINEMATIC',
            code: 'MASTER-105S',
            badge: '4K MASTER CINEMATIC',
            title: 'Insilos Master 4K Cinematic: Từ Bản Vẽ Đến Hải Cảng (105s)',
            domain: 'End-to-End Enterprise Ecosystem',
            duration: 105,
            videoSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_MASTER_CINEMATIC_105S.mp4',
            posterSrc: '/insilos_website/static/src/video/gold_masters/INSILOS_MASTER_CINEMATIC_105S_poster.webp',
            defaultModel: 'mrp.production',
            defaultRecordId: 10,
            defaultActionId: 367,
            acts: [
                { id: 1, start: 0, end: 25, name: 'Hồi 1: Tầm Nhìn KCN & Bản Vẽ R&D V-LIFT', color: 'info' },
                { id: 2, start: 25, end: 78, name: 'Hồi 2: Phân Xưởng Laser CNC, Pin & Đội Xe', color: 'warning' },
                { id: 3, start: 78, end: 105, name: 'Hồi 3: Cảng Biển Quốc Tế, Sổ Cái TT 200 & Khép Kín', color: 'success' }
            ],
            chapters: [
                { time: 0.0, title: 'Bình Minh KCN VSIP & Tầm Nhìn Sovereign', act: 1, desc: 'Kiến tạo sức mạnh vận hành số hóa công nghiệp thế hệ mới' },
                { time: 12.0, title: 'Bản Vẽ R&D EQ-VLIFT-2500E & CRM 18.6 Tỷ', act: 1, desc: 'Dòng chảy thông tin thông suốt từ thiết kế đến báo giá' },
                { time: 25.0, title: 'Phân Xưởng Laser 12kW & Robot Yaskawa', act: 2, desc: 'Cắt thép SS400, hàn khung gầm tự động, OEE 92.5%' },
                { time: 42.0, title: 'Lắp Ráp Pack Pin LFP 48V & Smart BMS', act: 2, desc: 'Quét barcode ARM Cortex-M4, truy vết 100% serial' },
                { time: 58.0, title: 'Đoàn Xe 51C-982.45 Tiến Về Cụm Cảng Biển Quốc Tế', act: 2, desc: 'GPS Telematics thông minh, định mức dầu giảm -18.4%' },
                { time: 78.0, title: 'Cẩu Bờ STS Cảng Biển & Hóa Đơn TT 78/200', act: 3, desc: 'Giải phóng container tức thì, tự động hạch toán Nợ 131/Có 5112' },
                { time: 92.0, title: 'Toàn Cảnh Hệ Sinh Thái Insilos & Call To Action', act: 3, desc: 'Hợp nhất dữ liệu · Tối thượng vận hành' }
            ],
            telemetryMilestones: [
                {
                    timestamp: 0.0,
                    act: 1,
                    chapter: 'Bình Minh KCN VSIP & Tầm Nhìn Sovereign',
                    operationalState: 'SOVEREIGN VISION',
                    stateBadge: 'KIẾN TRÚC CHỦ QUYỀN',
                    stateColor: 'info',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Quy Chuẩn An Ninh', value: 'Sovereign Private Cloud', status: 'success', icon: 'ph-shield-check' },
                        { label: 'Thời Gian Đáp Ứng', value: '< 9ms P99 Latency', status: 'success', icon: 'ph-lightning' },
                        { label: 'Bảo Vệ Dữ Liệu', value: 'Nghị định 13/2023/NĐ-CP', status: 'success', icon: 'ph-lock' }
                    ],
                    table: {
                        title: 'Trụ Cột Nền Tảng Công Nghiệp Insilos Enterprise',
                        columns: ['Trụ Cột Công Nghệ', 'Quy Chuẩn Kỹ Thuật', 'Đặc Tính Vận Hành'],
                        rows: [
                            ['1. Sovereign Architecture', '100% Air-Gapped / On-Prem', 'Cô lập vật lý dữ liệu nhà máy'],
                            ['2. Real-Time Telemetry', 'SCADA / MQTT / OPC-UA', 'Tần số lấy mẫu 60 FPS không trễ'],
                            ['3. Compliance Ready', 'Thông tư 200, TT 78, WCO SAFE', 'Sẵn sàng kiểm toán tức thì']
                        ]
                    },
                    json: {
                        platform: 'Insilos Sovereign Industrial AI',
                        deployment: 'Air-Gapped Private Kubernetes Cluster',
                        security: 'SOC 2 Type II & ISO 27001:2022',
                        data_sovereignty: 'Vietnam National Data Center Ready'
                    }
                },
                {
                    timestamp: 25.0,
                    act: 2,
                    chapter: 'Phân Xưởng Laser 12kW & Robot Yaskawa',
                    operationalState: 'MANUFACTURING EXECUTION',
                    stateBadge: 'PHÂN XƯỞNG MES & OEE',
                    stateColor: 'warning',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Lệnh Sản Xuất MO', value: 'WH/MO/00010 Đang chạy', status: 'warning', icon: 'ph-gear-six' },
                        { label: 'Hiệu Suất OEE', value: '92.5% World-Class', status: 'success', icon: 'ph-gauge' },
                        { label: 'Công Suất Laser', value: 'Fiber Laser 12kW', status: 'info', icon: 'ph-fire' }
                    ],
                    table: {
                        title: 'Theo Dõi Gia Công Cụm Khung Gầm V-LIFT 2500E',
                        columns: ['Công Đoạn Phân Xưởng', 'Thiết Bị Thực Hiện', 'Chỉ Số Kỹ Thuật', 'Tiến Độ'],
                        rows: [
                            ['Cắt Phôi Tấm SS400', 'Fiber Laser CNC Trumpf', 'Khổ 1.5x6m Dày 12mm', '100% HOÀN TẤT'],
                            ['Chấn Dập Góc Chữ U', 'Máy chấn TruBend 250T', 'Gân gia cường dầm chịu lực', '100% HOÀN TẤT'],
                            ['Hàn Tự Động Robot', 'Robot Yaskawa AR2010', 'Dây hàn ER70S-6 khí Ar/CO2', 'ĐANG HÀN']
                        ]
                    },
                    json: {
                        active_order: 'WH/MO/00010',
                        workcenter: 'WC-WELD-01',
                        robot_model: 'Yaskawa Motoman AR2010',
                        oee_current: 0.925
                    }
                },
                {
                    timestamp: 58.0,
                    act: 2,
                    chapter: 'Đoàn Xe 51C-982.45 Tiến Về Cụm Cảng Biển Quốc Tế',
                    operationalState: 'FLEET LOGISTICS CORRIDOR',
                    stateBadge: 'HÀNH LANG CẢNG BIỂN',
                    stateColor: 'info',
                    model: 'fleet.vehicle',
                    recordId: 6,
                    actionId: 738,
                    metrics: [
                        { label: 'Đầu Kéo Hyundai Xcient', value: '51C-982.45 (440 PS)', status: 'info', icon: 'ph-truck' },
                        { label: 'Km Odometer', value: '142.500 km Đã đối soát', status: 'success', icon: 'ph-gauge' },
                        { label: 'Tiêu Hao Nhiên Liệu', value: '-18.4% (34 L/100km)', status: 'success', icon: 'ph-drop' }
                    ],
                    table: {
                        title: 'Dữ Liệu Giám Sát Hành Trình Đội Xe Vận Tải Nặng',
                        columns: ['Thông Số GPS', 'Đo Kiểm Thời Gian Thực', 'Ngưỡng Định Mức'],
                        rows: [
                            ['Vận tốc hành trình', '54.2 km/h', 'Tối đa 60 km/h (Đúng luật)'],
                            ['Mức tiêu hao dầu DO', '34.0 L/100km', 'Định mức trần: 42.0 L/100km'],
                            ['Nhiệt độ dầu phanh', '68.5 °C', 'An toàn tuyệt đối (< 110 °C)']
                        ]
                    },
                    json: {
                        fleet_id: 6,
                        plate: '51C-982.45',
                        odometer_km: 142500,
                        route: 'VSIP 1 to International Seaport',
                        pvoil_fuel_sync: 'PTX-CL-98245-01'
                    }
                },
                {
                    timestamp: 78.0,
                    act: 3,
                    chapter: 'Cẩu Bờ STS Cảng Biển & Hóa Đơn TT 78/200',
                    operationalState: 'FISCAL RECONCILIATION',
                    stateBadge: 'KHÉP KÍN DÒNG TIỀN',
                    stateColor: 'success',
                    model: 'account.move',
                    recordId: 12,
                    actionId: 476,
                    metrics: [
                        { label: 'Doanh Thu Lô Hàng', value: '1.050 Tỷ ₫ Đã vào sổ', status: 'success', icon: 'ph-coins' },
                        { label: 'Hóa Đơn Viettel S-Inv', value: 'INV/2026/00001 Ký số', status: 'success', icon: 'ph-file-check' },
                        { label: 'Phí Phạt DEM/DET', value: '0.00 ₫ (Tiết kiệm 88%)', status: 'success', icon: 'ph-shield-check' }
                    ],
                    table: {
                        title: 'Khép Kín Luân Chuyển Dòng Tiền & Nghiệm Thu Cảng',
                        columns: ['Nghiệp Vụ Hợp Nhất', 'Chứng Từ Liên Kết', 'Giá Trị Đối Soát'],
                        rows: [
                            ['Xuất xưởng thiết bị', 'Phiếu xuất kho WH/OUT/00001', '5 Xe kéo V-LIFT 2500E'],
                            ['Hạ bãi cảng biển', 'E-Port Gate-In RFID Receipt', 'Container TCLU-582194-0'],
                            ['Phát hành hóa đơn điện tử', 'Hóa đơn CQT INV/2026/00001', '1.050.500.000 ₫ (Nợ 131/Có 5112)']
                        ]
                    },
                    json: {
                        macro_ecosystem: 'CONNECTED',
                        revenue_locked_vnd: 1050500000,
                        cogs_cleared_vnd: 770000000,
                        audit_hash: '0x9924eaf189d201b4c3e80112'
                    }
                },
                {
                    timestamp: 95.0,
                    act: 3,
                    chapter: 'Toàn Cảnh Hệ Sinh Thái Insilos & Call To Action',
                    operationalState: 'FULL ECOSYSTEM PANORAMA',
                    stateBadge: 'HỢP NHẤT TỐI THƯỢNG',
                    stateColor: 'success',
                    model: 'mrp.production',
                    recordId: 10,
                    actionId: 367,
                    metrics: [
                        { label: 'Nền Tảng Hợp Nhất', value: '100% Single Truth', status: 'success', icon: 'ph-squares-four' },
                        { label: 'Chuẩn Âm Học Broadcast', value: 'EBU R128 (-14.2 LUFS)', status: 'info', icon: 'ph-speaker-high' },
                        { label: 'Chất Lượng Video', value: '4K UHD Cinema', status: 'success', icon: 'ph-film-strip' }
                    ],
                    table: {
                        title: 'Sức Mạnh Nền Tảng Hợp Nhất Insilos Enterprise',
                        columns: ['Trục Dữ Liệu', 'Hiệu Quả Thực Chứng'],
                        rows: [
                            ['R&D đến Sản Xuất', 'Tự động bóc tách BOM từ CAD trong 15 giây'],
                            ['Xưởng đến Đội Xe', 'Đồng bộ điều phối drayage ngay khi nghiệm thu'],
                            ['Cảng đến Tài Chính', 'Đối soát 3 chiều tức thời, chuẩn hóa Thông tư 200']
                        ]
                    },
                    json: {
                        mission: 'HỢP NHẤT DỮ LIỆU · TỐI THƯỢNG VẬN HÀNH',
                        website: 'https://insilos.ai',
                        live_demo: 'http://localhost:28069/showcase-3d'
                    }
                }
            ]
        }
    };

    /**
     * Interactive Cinema HUD Video Telemetry Player Class.
     */
    class InsilosVideoTelemetryPlayer {
        /**
         * @param {HTMLElement|string} container - Target container element or selector
         * @param {Object} options - Configuration options
         */
        constructor(container, options) {
            this.container = typeof container === 'string' ? document.querySelector(container) : container;
            if (!this.container) {
                console.warn('[InsilosVideoTelemetryPlayer] Container not found:', container);
                return;
            }

            this.options = Object.assign({
                defaultVideoId: this.container.getAttribute('data-video-id') || 'VID_04_BOM',
                autoPlay: false,
                muted: true,
                showSelector: true,
                baseUrl: getOdooBaseUrl()
            }, options);

            this.currentVideoId = this.options.defaultVideoId;
            if (!INSILOS_VIDEO_REGISTRY[this.currentVideoId]) {
                this.currentVideoId = 'VID_04_BOM';
            }

            this.currentVideoData = INSILOS_VIDEO_REGISTRY[this.currentVideoId];
            this.activeMilestoneIndex = -1;
            this.rafId = null;
            this.isDragging = false;
            this.activeTab = 'table'; // 'table' or 'json'

            this.init();
        }

        init() {
            this.buildPlayerDOM();
            this.bindEvents();
            this.loadVideo(this.currentVideoId, this.options.autoPlay);
        }

        /**
         * Build or enhance the player DOM inside the container.
         */
        buildPlayerDOM() {
            // Check if DOM is already scaffolded
            let innerWrapper = this.container.querySelector('.ins-cinema-player-wrapper');
            if (!innerWrapper) {
                this.container.innerHTML = `
                    <div class="ins-cinema-player-wrapper bg-black bg-opacity-75 border border-secondary border-opacity-25 rounded-4 p-3 p-lg-4 shadow-2xl text-white">
                        <!-- Top Bar: Selector & Video Title -->
                        <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 pb-3 mb-3 border-bottom border-secondary border-opacity-25">
                            <div class="d-flex align-items-center gap-2 flex-wrap">
                                <span class="badge bg-primary rounded-pill px-3 py-1 font-monospace ins-hud-code-badge">
                                    ${escapeHtml(this.currentVideoData.code)}
                                </span>
                                <span class="badge bg-dark border border-cyan border-opacity-50 text-cyan font-monospace small ins-hud-domain-badge">
                                    ${renderPhosphorIcon('ph-factory', 'me-1')}<span class="ins-hud-domain-text">${escapeHtml(this.currentVideoData.domain)}</span>
                                </span>
                                <h4 class="h5 fw-bold text-white mb-0 ms-lg-2 ins-hud-video-title">
                                    ${escapeHtml(this.currentVideoData.title)}
                                </h4>
                            </div>
                            <div class="d-flex align-items-center gap-2 ins-video-selector-container">
                                <!-- Dynamic Selector injected here -->
                            </div>
                        </div>

                        <!-- Main Split Grid: Left Video / Right Telemetry HUD -->
                        <div class="row g-4 align-items-stretch">
                            <!-- Left: Video Viewport & Controls -->
                            <div class="col-lg-7 d-flex flex-column">
                                <div class="position-relative bg-black rounded-4 overflow-hidden border border-secondary border-opacity-25 shadow-lg flex-grow-1 d-flex flex-column">
                                    <!-- 16:9 Cinema Viewport -->
                                    <div class="ratio ratio-16x9 bg-black position-relative ins-video-box">
                                        <video class="w-100 h-100 object-fit-contain ins-video-element" playsinline="playsinline" preload="metadata">
                                            <source type="video/mp4"/>
                                        </video>
                                        <!-- Overlay HUD Badges -->
                                        <div class="position-absolute top-0 start-0 w-100 p-3 d-flex justify-content-between align-items-start pointer-events-none z-2">
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="badge bg-black bg-opacity-75 border border-emerald border-opacity-50 text-emerald font-monospace small d-inline-flex align-items-center gap-1">
                                                    <span class="ins-live-ping--emerald me-1"></span>
                                                    <span>LIVE ERP STREAM</span>
                                                </span>
                                                <span class="badge bg-black bg-opacity-75 border border-primary border-opacity-50 text-primary font-monospace small ins-hud-act-badge">
                                                    HỒI 1: B-ROLL 3D
                                                </span>
                                            </div>
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="badge bg-black bg-opacity-75 text-cyan border border-cyan border-opacity-25 font-monospace small">
                                                    ${renderPhosphorIcon('ph-film-strip', 'me-1')}1080P FULL HD
                                                </span>
                                                <span class="badge bg-black bg-opacity-75 text-secondary border border-secondary border-opacity-25 font-monospace small d-none d-sm-inline">
                                                    EBU R128 (-14.5 LUFS)
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Interactive 3-Act Timeline Scrubber -->
                                    <div class="p-3 bg-dark bg-opacity-75 border-top border-secondary border-opacity-25 ins-3act-timeline-container">
                                        <!-- Act Labels Track -->
                                        <div class="d-flex justify-content-between font-monospace small text-secondary mb-1 ins-3act-labels">
                                            <div class="text-cyan ins-act-tag" data-act="1">
                                                ${renderPhosphorIcon('ph-lightning', 'me-1')}<span>Hồi 1 (0-10s): B-Roll</span>
                                            </div>
                                            <div class="text-warning ins-act-tag" data-act="2">
                                                ${renderPhosphorIcon('ph-gear-six', 'me-1')}<span>Hồi 2 (10-50s): Thao Tác ERP</span>
                                            </div>
                                            <div class="text-emerald ins-act-tag" data-act="3">
                                                ${renderPhosphorIcon('ph-check-circle', 'me-1')}<span>Hồi 3 (50-60s): Closing CTA</span>
                                            </div>
                                        </div>

                                        <!-- Scrubber Rail with 3-Act Segments and Chapter Markers -->
                                        <div class="position-relative ins-scrubber-rail py-2 cursor-pointer" role="slider" aria-label="Thanh tiến trình 3 Hồi" tabindex="0">
                                            <div class="ins-scrubber-track rounded-pill overflow-hidden position-relative bg-secondary bg-opacity-25">
                                                <!-- Act 1 Track Fill -->
                                                <div class="ins-act-track ins-act-track-1 bg-cyan bg-opacity-25"></div>
                                                <!-- Act 2 Track Fill -->
                                                <div class="ins-act-track ins-act-track-2 bg-warning bg-opacity-25"></div>
                                                <!-- Act 3 Track Fill -->
                                                <div class="ins-act-track ins-act-track-3 bg-emerald bg-opacity-25"></div>
                                                <!-- Active Progress Fill -->
                                                <div class="ins-scrubber-progress rounded-pill bg-primary position-absolute top-0 start-0 h-100"></div>
                                            </div>
                                            <!-- Chapter Markers Container -->
                                            <div class="ins-chapter-markers-box position-absolute top-0 start-0 w-100 h-100 pointer-events-none"></div>
                                            <!-- Scrubber Thumb -->
                                            <div class="ins-scrubber-thumb rounded-circle bg-white border border-primary shadow position-absolute top-50 translate-middle pointer-events-none"></div>
                                        </div>

                                        <!-- Bottom Video Control Bar -->
                                        <div class="d-flex justify-content-between align-items-center pt-2 gap-2 flex-wrap">
                                            <div class="d-flex align-items-center gap-2">
                                                <button type="button" class="btn btn-sm btn-outline-light rounded-pill px-3 d-inline-flex align-items-center gap-2 ins-btn-play">
                                                    ${renderPhosphorIcon('ph-play', 'fs-6')}<span class="ins-btn-play-text">Phát</span>
                                                </button>
                                                <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-2 ins-btn-mute" aria-label="Bật/Tắt âm thanh">
                                                    ${renderPhosphorIcon('ph-speaker-high', 'fs-6')}
                                                </button>
                                                <span class="font-monospace small text-cyan ms-2 ins-time-display">
                                                    00:00 / 01:00
                                                </span>
                                            </div>
                                            <div class="d-flex align-items-center gap-2">
                                                <div class="btn-group btn-group-sm" role="group" aria-label="Tốc độ phát">
                                                    <button type="button" class="btn btn-outline-secondary ins-speed-btn active" data-speed="1.0">1x</button>
                                                    <button type="button" class="btn btn-outline-secondary ins-speed-btn" data-speed="1.25">1.25x</button>
                                                    <button type="button" class="btn btn-outline-secondary ins-speed-btn" data-speed="1.5">1.5x</button>
                                                </div>
                                                <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-2 ins-btn-fullscreen" aria-label="Toàn màn hình">
                                                    ${renderPhosphorIcon('ph-arrows-out', 'fs-6')}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Right: Live ERP Telemetry HUD Panel -->
                            <div class="col-lg-5 d-flex flex-column">
                                <div class="bg-black bg-opacity-90 rounded-4 border border-secondary border-opacity-50 shadow-lg p-3 p-lg-4 d-flex flex-column h-100 ins-hud-panel">
                                    <!-- HUD Header -->
                                    <div class="d-flex justify-content-between align-items-center pb-3 mb-3 border-bottom border-secondary border-opacity-25 flex-wrap gap-2">
                                        <div class="d-flex align-items-center gap-2">
                                            <span class="badge bg-danger font-monospace ins-hud-state-badge">
                                                CRITICAL RISK
                                            </span>
                                            <h5 class="h6 fw-bold text-white mb-0 ins-hud-chapter-title">
                                                Cảnh Báo Lệch Định Mức
                                            </h5>
                                        </div>
                                        <div class="d-flex align-items-center gap-2">
                                            <button type="button" class="btn btn-sm btn-outline-light rounded-pill px-2 font-monospace small ins-hud-tab-table active" data-hud-tab="table">
                                                ${renderPhosphorIcon('ph-table', 'me-1')}Bảng ERP
                                            </button>
                                            <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-2 font-monospace small ins-hud-tab-json" data-hud-tab="json">
                                                ${renderPhosphorIcon('ph-code', 'me-1')}JSON Stream
                                            </button>
                                        </div>
                                    </div>

                                    <!-- Live Dynamic KPI Chips -->
                                    <div class="row g-2 mb-3 ins-hud-kpi-row">
                                        <!-- Injected dynamically -->
                                    </div>

                                    <!-- Telemetry Viewport (Table or JSON Terminal) -->
                                    <div class="flex-grow-1 overflow-auto rounded-3 border border-secondary border-opacity-25 bg-dark bg-opacity-50 p-3 mb-3 ins-hud-telemetry-body" style="min-height: 220px; max-height: 340px;">
                                        <!-- Table View Container -->
                                        <div class="ins-hud-view-table">
                                            <div class="small fw-bold text-cyan font-monospace mb-2 ins-hud-table-title">
                                                BẢNG NGHIỆP VỤ ERP THỰC CHỨNG
                                            </div>
                                            <div class="table-responsive">
                                                <table class="table table-dark table-sm table-striped table-hover font-monospace small mb-0 ins-hud-table-element">
                                                    <thead></thead>
                                                    <tbody></tbody>
                                                </table>
                                            </div>
                                        </div>
                                        <!-- JSON Stream View Container -->
                                        <div class="ins-hud-view-json d-none position-relative">
                                            <div class="d-flex justify-content-between align-items-center pb-2 mb-2 border-bottom border-secondary border-opacity-25">
                                                <span class="small font-monospace text-emerald">
                                                    ${renderPhosphorIcon('ph-broadcast', 'me-1')}REAL-TIME ERP TELEMETRY PAYLOAD
                                                </span>
                                                <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-2 py-0 font-monospace small ins-btn-copy-json">
                                                    ${renderPhosphorIcon('ph-copy', 'me-1')}Copy
                                                </button>
                                            </div>
                                            <pre class="font-monospace small text-cyan m-0 ins-hud-json-content overflow-auto" style="white-space: pre-wrap; font-size: 0.78rem;"></pre>
                                        </div>
                                    </div>

                                    <!-- 1-Click Deep-Link Action Button to Odoo Live Backend -->
                                    <div class="mt-auto pt-2 border-top border-secondary border-opacity-25">
                                        <a href="#" target="_blank" rel="noopener noreferrer" class="btn btn-primary rounded-pill w-100 py-3 fw-bold d-flex align-items-center justify-content-center gap-2 shadow-lg text-decoration-none ins-deeplink-btn" data-deeplink-btn="true">
                                            ${renderPhosphorIcon('ph-arrow-square-out', 'fs-5')}
                                            <span class="ins-deeplink-text">Trực quan hóa trên Odoo Live</span>
                                        </a>
                                        <div class="small text-secondary font-monospace text-center mt-2 d-flex align-items-center justify-content-center gap-2">
                                            <span>Mở bản ghi trực tiếp trên Odoo 20 Live Backend (Port 28069)</span>
                                            <span class="badge bg-secondary bg-opacity-25 text-emerald font-monospace ins-deeplink-target-ref">#VN-MO-00010</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }

            // Cache DOM references
            this.video = this.container.querySelector('.ins-video-element');
            this.playBtn = this.container.querySelector('.ins-btn-play');
            this.playBtnText = this.container.querySelector('.ins-btn-play-text');
            this.muteBtn = this.container.querySelector('.ins-btn-mute');
            this.fullscreenBtn = this.container.querySelector('.ins-btn-fullscreen');
            this.timeDisplay = this.container.querySelector('.ins-time-display');
            this.scrubberRail = this.container.querySelector('.ins-scrubber-rail');
            this.scrubberProgress = this.container.querySelector('.ins-scrubber-progress');
            this.scrubberThumb = this.container.querySelector('.ins-scrubber-thumb');
            this.markersBox = this.container.querySelector('.ins-chapter-markers-box');
            this.selectorContainer = this.container.querySelector('.ins-video-selector-container');
            this.deeplinkBtn = this.container.querySelector('.ins-deeplink-btn');
            this.deeplinkTargetRef = this.container.querySelector('.ins-deeplink-target-ref');

            // HUD Elements
            this.hudCodeBadge = this.container.querySelector('.ins-hud-code-badge');
            this.hudDomainText = this.container.querySelector('.ins-hud-domain-text');
            this.hudVideoTitle = this.container.querySelector('.ins-hud-video-title');
            this.hudActBadge = this.container.querySelector('.ins-hud-act-badge');
            this.hudStateBadge = this.container.querySelector('.ins-hud-state-badge');
            this.hudChapterTitle = this.container.querySelector('.ins-hud-chapter-title');
            this.hudKpiRow = this.container.querySelector('.ins-hud-kpi-row');
            this.hudTableTitle = this.container.querySelector('.ins-hud-table-title');
            this.hudTableElement = this.container.querySelector('.ins-hud-table-element');
            this.hudJsonContent = this.container.querySelector('.ins-hud-json-content');
            this.hudViewTable = this.container.querySelector('.ins-hud-view-table');
            this.hudViewJson = this.container.querySelector('.ins-hud-view-json');
            this.tabTableBtn = this.container.querySelector('.ins-hud-tab-table');
            this.tabJsonBtn = this.container.querySelector('.ins-hud-tab-json');
            this.copyJsonBtn = this.container.querySelector('.ins-btn-copy-json');

            this.renderSelector();
        }

        /**
         * Render video switcher selector (VID-01 to VID-12 + Master 105s).
         */
        renderSelector() {
            if (!this.selectorContainer) return;

            const videoKeys = Object.keys(INSILOS_VIDEO_REGISTRY);
            let selectHtml = `
                <div class="dropdown">
                    <button class="btn btn-sm btn-outline-light rounded-pill dropdown-toggle px-3 font-monospace small d-inline-flex align-items-center gap-2" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                        ${renderPhosphorIcon('ph-film-strip', 'me-1')}
                        <span class="ins-selected-video-label">${escapeHtml(this.currentVideoData.code)}: ${escapeHtml(this.currentVideoData.badge)}</span>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow-xl border border-secondary border-opacity-50 p-2" style="max-height: 380px; overflow-y: auto; width: 320px;">
                        <li class="dropdown-header small text-cyan font-monospace">CHỌN PHIM NGHIỆP VỤ GOLD MASTER:</li>
            `;

            videoKeys.forEach((key) => {
                const item = INSILOS_VIDEO_REGISTRY[key];
                const activeCls = key === this.currentVideoId ? 'active bg-primary' : '';
                selectHtml += `
                    <li>
                        <button type="button" class="dropdown-item rounded-3 py-2 d-flex flex-column ${activeCls} ins-selector-item" data-video-id="${item.id}">
                            <div class="d-flex justify-content-between align-items-center font-monospace small mb-1">
                                <span class="fw-bold">${escapeHtml(item.code)}</span>
                                <span class="badge bg-secondary bg-opacity-50">${formatTime(item.duration)}</span>
                            </div>
                            <span class="small text-truncate" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span>
                        </button>
                    </li>
                `;
            });

            selectHtml += `
                    </ul>
                </div>
            `;

            this.selectorContainer.innerHTML = selectHtml;

            // Bind click handlers to dropdown items
            const items = this.selectorContainer.querySelectorAll('.ins-selector-item');
            items.forEach((btn) => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const targetId = btn.getAttribute('data-video-id');
                    if (targetId && targetId !== this.currentVideoId) {
                        this.loadVideo(targetId, true);
                    }
                });
            });
        }

        /**
         * Render chapter markers across the timeline rail.
         */
        renderChapterMarkers() {
            if (!this.markersBox || !this.currentVideoData) return;

            const duration = this.currentVideoData.duration || 60;
            const chapters = this.currentVideoData.chapters || [];

            let markersHtml = '';
            chapters.forEach((ch, idx) => {
                const leftPercent = Math.min(100, Math.max(0, (ch.time / duration) * 100));
                markersHtml += `
                    <div class="ins-chapter-marker position-absolute top-50 translate-middle cursor-pointer"
                         style="left: ${leftPercent}%;"
                         data-time="${ch.time}"
                         data-index="${idx}"
                         data-title="${escapeHtml(ch.title)}"
                         data-act="${ch.act}"
                         title="t=${formatTime(ch.time)}: ${escapeHtml(ch.title)}">
                        <span class="ins-marker-dot rounded-circle bg-cyan border border-white d-block"></span>
                    </div>
                `;
            });

            this.markersBox.innerHTML = markersHtml;

            // Make markers clickable to seek
            const markerEls = this.markersBox.querySelectorAll('.ins-chapter-marker');
            markerEls.forEach((el) => {
                el.style.pointerEvents = 'auto';
                el.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const seekTime = parseFloat(el.getAttribute('data-time'));
                    if (!isNaN(seekTime)) {
                        this.seekTo(seekTime);
                    }
                });
            });

            // Adjust 3-act visual track widths
            const track1 = this.container.querySelector('.ins-act-track-1');
            const track2 = this.container.querySelector('.ins-act-track-2');
            const track3 = this.container.querySelector('.ins-act-track-3');
            const acts = this.currentVideoData.acts || [];

            if (acts.length >= 3 && track1 && track2 && track3) {
                const act1Width = ((acts[0].end - acts[0].start) / duration) * 100;
                const act2Width = ((acts[1].end - acts[1].start) / duration) * 100;
                const act3Width = ((acts[2].end - acts[2].start) / duration) * 100;

                track1.style.width = act1Width + '%';
                track2.style.width = act2Width + '%';
                track3.style.width = act3Width + '%';

                const actTags = this.container.querySelectorAll('.ins-act-tag');
                if (actTags[0]) actTags[0].querySelector('span').textContent = acts[0].name;
                if (actTags[1]) actTags[1].querySelector('span').textContent = acts[1].name;
                if (actTags[2]) actTags[2].querySelector('span').textContent = acts[2].name;
            }
        }

        /**
         * Load a new video scenario by ID.
         */
        loadVideo(videoId, autoPlay = false) {
            const data = INSILOS_VIDEO_REGISTRY[videoId];
            if (!data) return;

            this.currentVideoId = videoId;
            this.currentVideoData = data;
            this.activeMilestoneIndex = -1;

            if (this.hudCodeBadge) this.hudCodeBadge.textContent = data.code;
            if (this.hudDomainText) this.hudDomainText.textContent = data.domain;
            if (this.hudVideoTitle) this.hudVideoTitle.textContent = data.title;

            const selectedLabel = this.container.querySelector('.ins-selected-video-label');
            if (selectedLabel) {
                selectedLabel.textContent = `${data.code}: ${data.badge}`;
            }

            // Update video tag
            if (this.video) {
                if (data.posterSrc) {
                    this.video.setAttribute('poster', data.posterSrc);
                } else {
                    this.video.removeAttribute('poster');
                }

                const sourceTag = this.video.querySelector('source');
                if (sourceTag) {
                    sourceTag.setAttribute('src', data.videoSrc);
                } else {
                    this.video.setAttribute('src', data.videoSrc);
                }

                this.video.load();
                this.video.muted = this.options.muted;

                if (autoPlay) {
                    const playPromise = this.video.play();
                    if (playPromise !== undefined) {
                        playPromise.catch((err) => {
                            console.warn('[InsilosVideoTelemetryPlayer] Autoplay was prevented by browser policy:', err);
                        });
                    }
                }
            }

            this.renderChapterMarkers();
            this.renderSelector();
            this.updateTelemetry(0.0);
        }

        /**
         * Update real-time telemetry HUD panel based on current video time.
         */
        updateTelemetry(currentTime) {
            const duration = this.currentVideoData.duration || 60;
            const progressRatio = Math.min(1, Math.max(0, currentTime / duration));
            const progressPercent = progressRatio * 100;

            // 1. Update Scrubber Progress & Thumb position
            if (this.scrubberProgress) {
                this.scrubberProgress.style.width = progressPercent + '%';
            }
            if (this.scrubberThumb) {
                this.scrubberThumb.style.left = progressPercent + '%';
            }

            // 2. Update Time Display
            if (this.timeDisplay) {
                this.timeDisplay.textContent = `${formatTime(currentTime)} / ${formatTime(duration)}`;
            }

            // 3. Determine current Act
            let currentAct = 1;
            const acts = this.currentVideoData.acts || [];
            for (let i = 0; i < acts.length; i++) {
                if (currentTime >= acts[i].start && currentTime <= acts[i].end) {
                    currentAct = acts[i].id;
                    break;
                }
            }
            if (this.hudActBadge) {
                this.hudActBadge.textContent = `HỒI ${currentAct}: ${currentAct === 1 ? 'B-ROLL 3D' : (currentAct === 2 ? 'THAO TÁC ERP' : 'CLOSING CTA')}`;
                this.hudActBadge.className = `badge bg-black bg-opacity-75 border font-monospace small ins-hud-act-badge ${currentAct === 1 ? 'border-primary text-primary' : (currentAct === 2 ? 'border-warning text-warning' : 'border-emerald text-emerald')}`;
            }

            // 4. Find matching telemetry milestone
            const milestones = this.currentVideoData.telemetryMilestones || [];
            let targetIndex = 0;
            for (let i = milestones.length - 1; i >= 0; i--) {
                if (currentTime >= milestones[i].timestamp) {
                    targetIndex = i;
                    break;
                }
            }

            // Avoid thrashing DOM if milestone hasn't changed
            if (targetIndex === this.activeMilestoneIndex) {
                return;
            }

            this.activeMilestoneIndex = targetIndex;
            const ms = milestones[targetIndex];
            if (!ms) return;

            // 5. Update State Badges and Titles
            if (this.hudStateBadge) {
                this.hudStateBadge.textContent = ms.stateBadge || ms.operationalState;
                this.hudStateBadge.className = `badge bg-${ms.stateColor || 'primary'} font-monospace ins-hud-state-badge`;
            }
            if (this.hudChapterTitle) {
                this.hudChapterTitle.textContent = ms.chapter;
            }

            // 6. Update KPI Chips
            if (this.hudKpiRow && ms.metrics) {
                let kpiHtml = '';
                ms.metrics.forEach((m) => {
                    const statusColor = m.status === 'alert' ? 'danger' : (m.status === 'warning' ? 'warning' : (m.status === 'success' ? 'emerald' : 'cyan'));
                    const iconSvg = m.icon ? renderPhosphorIcon(m.icon, 'text-' + statusColor + ' fs-5 mb-1') : '';
                    kpiHtml += `
                        <div class="col-4">
                            <div class="p-2 rounded-3 bg-dark border border-secondary border-opacity-25 h-100 d-flex flex-column justify-content-between">
                                <div class="small text-secondary font-monospace text-truncate" title="${escapeHtml(m.label)}">
                                    ${escapeHtml(m.label)}
                                </div>
                                <div class="d-flex align-items-center justify-content-between mt-1">
                                    <div class="fw-bold font-monospace text-white fs-6 text-truncate" title="${escapeHtml(m.value)}">
                                        ${escapeHtml(m.value)}
                                    </div>
                                    ${iconSvg}
                                </div>
                            </div>
                        </div>
                    `;
                });
                this.hudKpiRow.innerHTML = kpiHtml;
            }

            // 7. Update Table View
            if (this.hudTableElement && ms.table) {
                if (this.hudTableTitle) {
                    this.hudTableTitle.textContent = ms.table.title || 'BẢNG DỮ LIỆU ĐỐI SOÁT ERP';
                }

                const thead = this.hudTableElement.querySelector('thead');
                const tbody = this.hudTableElement.querySelector('tbody');

                if (thead && ms.table.columns) {
                    thead.innerHTML = '<tr>' + ms.table.columns.map(col => `<th class="text-secondary text-truncate">${escapeHtml(col)}</th>`).join('') + '</tr>';
                }
                if (tbody && ms.table.rows) {
                    tbody.innerHTML = ms.table.rows.map(row => {
                        return '<tr>' + row.map((cell, idx) => {
                            const isFirst = idx === 0;
                            const isHighlight = idx === row.length - 1;
                            const cls = isFirst ? 'text-white fw-bold' : (isHighlight ? 'text-cyan fw-bold' : 'text-secondary');
                            return `<td class="${cls} text-truncate" style="max-width: 180px;" title="${escapeHtml(cell)}">${escapeHtml(cell)}</td>`;
                        }).join('') + '</tr>';
                    }).join('');
                }
            }

            // 8. Update JSON Payload View
            if (this.hudJsonContent && ms.json) {
                this.hudJsonContent.textContent = JSON.stringify(ms.json, null, 2);
            }

            // 9. Update 1-Click Deep-Link Action
            if (this.deeplinkBtn) {
                const baseUrl = this.options.baseUrl || getOdooBaseUrl();
                const model = ms.model || this.currentVideoData.defaultModel;
                const recordId = ms.recordId || this.currentVideoData.defaultRecordId;
                const actionId = ms.actionId || this.currentVideoData.defaultActionId;

                // Build deep-link URL supported by Odoo 20
                let deepLinkUrl = `${baseUrl}/web#id=${recordId}&model=${model}&view_type=form&action=${actionId}`;
                this.deeplinkBtn.setAttribute('href', deepLinkUrl);

                if (this.deeplinkTargetRef) {
                    this.deeplinkTargetRef.textContent = `${model} #${recordId}`;
                }
            }

            // 10. Highlight Active Chapter Marker
            if (this.markersBox) {
                const markers = this.markersBox.querySelectorAll('.ins-chapter-marker');
                markers.forEach((m, idx) => {
                    const dot = m.querySelector('.ins-marker-dot');
                    if (dot) {
                        if (idx <= targetIndex) {
                            dot.classList.add('bg-warning', 'shadow-lg');
                            dot.classList.remove('bg-cyan');
                        } else {
                            dot.classList.remove('bg-warning', 'shadow-lg');
                            dot.classList.add('bg-cyan');
                        }
                    }
                });
            }
        }

        /**
         * Seek video to target seconds.
         */
        seekTo(seconds) {
            if (this.video && !isNaN(seconds)) {
                this.video.currentTime = Math.max(0, Math.min(this.video.duration || 60, seconds));
                this.updateTelemetry(this.video.currentTime);
            }
        }

        /**
         * Play video.
         */
        play() {
            if (this.video) {
                this.video.play().catch(err => {
                    console.warn('[InsilosVideoTelemetryPlayer] Play deferred:', err);
                });
            }
        }

        /**
         * Pause video.
         */
        pause() {
            if (this.video) {
                this.video.pause();
            }
        }

        /**
         * Toggle play/pause state.
         */
        togglePlay() {
            if (this.video) {
                if (this.video.paused || this.video.ended) {
                    this.play();
                } else {
                    this.pause();
                }
            }
        }

        /**
         * Toggle mute.
         */
        toggleMute() {
            if (this.video) {
                this.video.muted = !this.video.muted;
                if (this.muteBtn) {
                    this.muteBtn.innerHTML = this.video.muted
                        ? renderPhosphorIcon('ph-speaker-slash', 'fs-6')
                        : renderPhosphorIcon('ph-speaker-high', 'fs-6');
                }
            }
        }

        /**
         * Toggle Fullscreen.
         */
        toggleFullscreen() {
            const videoBox = this.container.querySelector('.ins-video-box') || this.video;
            if (!document.fullscreenElement) {
                if (videoBox.requestFullscreen) {
                    videoBox.requestFullscreen();
                } else if (videoBox.webkitRequestFullscreen) {
                    videoBox.webkitRequestFullscreen();
                }
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                }
            }
        }

        /**
         * Set playback speed.
         */
        setSpeed(speed) {
            const s = parseFloat(speed);
            if (!isNaN(s) && this.video) {
                this.video.playbackRate = s;
                const speedBtns = this.container.querySelectorAll('.ins-speed-btn');
                speedBtns.forEach(btn => {
                    if (parseFloat(btn.getAttribute('data-speed')) === s) {
                        btn.classList.add('active', 'btn-primary');
                        btn.classList.remove('btn-outline-secondary');
                    } else {
                        btn.classList.remove('active', 'btn-primary');
                        btn.classList.add('btn-outline-secondary');
                    }
                });
            }
        }

        /**
         * Bind user interactions and video playback events.
         */
        bindEvents() {
            if (!this.video) return;

            // Video timeupdate with rAF throttle to guarantee 60 FPS
            const onTimeUpdate = () => {
                if (this.rafId) cancelAnimationFrame(this.rafId);
                this.rafId = requestAnimationFrame(() => {
                    this.updateTelemetry(this.video.currentTime);
                });
            };

            this.video.addEventListener('timeupdate', onTimeUpdate);

            // Play / Pause state tracking
            this.video.addEventListener('play', () => {
                if (this.playBtnText) this.playBtnText.textContent = 'Tạm Dừng';
                if (this.playBtn) {
                    this.playBtn.innerHTML = `${renderPhosphorIcon('ph-pause', 'fs-6')}<span class="ins-btn-play-text">Tạm Dừng</span>`;
                }
            });

            this.video.addEventListener('pause', () => {
                if (this.playBtnText) this.playBtnText.textContent = 'Phát';
                if (this.playBtn) {
                    this.playBtn.innerHTML = `${renderPhosphorIcon('ph-play', 'fs-6')}<span class="ins-btn-play-text">Phát</span>`;
                }
            });

            this.video.addEventListener('ended', () => {
                if (this.playBtn) {
                    this.playBtn.innerHTML = `${renderPhosphorIcon('ph-play', 'fs-6')}<span class="ins-btn-play-text">Phát Lại</span>`;
                }
            });

            // Control Buttons
            if (this.playBtn) {
                this.playBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.togglePlay();
                });
            }

            if (this.muteBtn) {
                this.muteBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.toggleMute();
                });
            }

            if (this.fullscreenBtn) {
                this.fullscreenBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.toggleFullscreen();
                });
            }

            // Speed Buttons
            const speedBtns = this.container.querySelectorAll('.ins-speed-btn');
            speedBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.setSpeed(btn.getAttribute('data-speed'));
                });
            });

            // Scrubber Rail seeking & drag
            if (this.scrubberRail) {
                const handleSeek = (e) => {
                    const rect = this.scrubberRail.getBoundingClientRect();
                    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
                    const offsetX = Math.max(0, Math.min(rect.width, clientX - rect.left));
                    const ratio = offsetX / rect.width;
                    const duration = this.currentVideoData.duration || 60;
                    this.seekTo(ratio * duration);
                };

                this.scrubberRail.addEventListener('mousedown', (e) => {
                    this.isDragging = true;
                    handleSeek(e);
                });

                window.addEventListener('mousemove', (e) => {
                    if (this.isDragging) {
                        handleSeek(e);
                    }
                });

                window.addEventListener('mouseup', () => {
                    this.isDragging = false;
                });

                // Touch support
                this.scrubberRail.addEventListener('touchstart', (e) => {
                    this.isDragging = true;
                    handleSeek(e);
                }, { passive: true });

                window.addEventListener('touchmove', (e) => {
                    if (this.isDragging) {
                        handleSeek(e);
                    }
                }, { passive: true });

                window.addEventListener('touchend', () => {
                    this.isDragging = false;
                });
            }

            // HUD View Tabs (Table vs JSON)
            if (this.tabTableBtn && this.tabJsonBtn) {
                this.tabTableBtn.addEventListener('click', () => {
                    this.tabTableBtn.classList.add('active', 'btn-outline-light');
                    this.tabTableBtn.classList.remove('btn-outline-secondary');
                    this.tabJsonBtn.classList.remove('active', 'btn-outline-light');
                    this.tabJsonBtn.classList.add('btn-outline-secondary');
                    if (this.hudViewTable) this.hudViewTable.classList.remove('d-none');
                    if (this.hudViewJson) this.hudViewJson.classList.add('d-none');
                });

                this.tabJsonBtn.addEventListener('click', () => {
                    this.tabJsonBtn.classList.add('active', 'btn-outline-light');
                    this.tabJsonBtn.classList.remove('btn-outline-secondary');
                    this.tabTableBtn.classList.remove('active', 'btn-outline-light');
                    this.tabTableBtn.classList.add('btn-outline-secondary');
                    if (this.hudViewTable) this.hudViewTable.classList.add('d-none');
                    if (this.hudViewJson) this.hudViewJson.classList.remove('d-none');
                });
            }

            // Copy JSON Button
            if (this.copyJsonBtn && this.hudJsonContent) {
                this.copyJsonBtn.addEventListener('click', () => {
                    const text = this.hudJsonContent.textContent;
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(text).then(() => {
                            this.copyJsonBtn.textContent = 'Đã Copy!';
                            setTimeout(() => {
                                this.copyJsonBtn.innerHTML = `${renderPhosphorIcon('ph-copy', 'me-1')}Copy`;
                            }, 2000);
                        }).catch(() => {});
                    }
                });
            }

            // Keyboard Shortcuts when player is focused
            this.container.addEventListener('keydown', (e) => {
                if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
                if (e.key === ' ' || e.code === 'Space') {
                    e.preventDefault();
                    this.togglePlay();
                } else if (e.key === 'm' || e.key === 'M') {
                    e.preventDefault();
                    this.toggleMute();
                } else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    this.seekTo((this.video.currentTime || 0) + 5);
                } else if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    this.seekTo((this.video.currentTime || 0) - 5);
                }
            });
        }

        /**
         * Clean up resources and event listeners.
         */
        destroy() {
            if (this.rafId) {
                cancelAnimationFrame(this.rafId);
                this.rafId = null;
            }
            if (this.video) {
                this.video.pause();
                this.video.removeAttribute('src');
                this.video.load();
            }
            this.container.innerHTML = '';
        }
    }

    /**
     * Auto-initializer for all video telemetry player instances on the page.
     */
    function initInsilosVideoTelemetry(root) {
        const rootEl = root || document;
        const playerNodes = rootEl.querySelectorAll('.ins-video-telemetry-player, [data-snippet="s_insilos_video_telemetry_player"]');

        const instances = [];
        playerNodes.forEach((node) => {
            if (!node._insilosTelemetryPlayer) {
                node._insilosTelemetryPlayer = new InsilosVideoTelemetryPlayer(node);
                instances.push(node._insilosTelemetryPlayer);
            }
        });

        // Also connect to Modal #insilosGoldVideoModal if present
        const modalEl = document.getElementById('insilosGoldVideoModal');
        if (modalEl && !modalEl._insilosModalTelemetryBound) {
            modalEl._insilosModalTelemetryBound = true;
            const modalVideo = document.getElementById('insilosGoldVideoPlayer');
            if (modalVideo) {
                modalVideo.addEventListener('timeupdate', () => {
                    // Update active player if open
                    const activePlayer = instances[0];
                    if (activePlayer && modalEl.classList.contains('show')) {
                        activePlayer.updateTelemetry(modalVideo.currentTime);
                    }
                });
            }
        }

        return instances;
    }

    // Expose to window for global access and testing
    window.InsilosVideoTelemetryRegistry = INSILOS_VIDEO_REGISTRY;
    window.InsilosVideoTelemetryPlayer = InsilosVideoTelemetryPlayer;
    window.initInsilosVideoTelemetry = initInsilosVideoTelemetry;

    // Auto-mount on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initInsilosVideoTelemetry());
    } else {
        initInsilosVideoTelemetry();
    }

    // Support Odoo Website Editor snippet dropped events
    window.addEventListener('website_snippets_loaded', () => initInsilosVideoTelemetry());
    document.addEventListener('snippet_cloned', () => initInsilosVideoTelemetry());

})();
