#!/usr/bin/env python3
"""
Upgrade Left Column Hero sections across all routes into 4-Act Storyboard Panes
and interactive 4-Pill Selectors that bind 2-way with the 3D Cockpit Deck.

Routes upgraded:
1. views/platform_solutions.xml:
   - /solutions/enterprise-knowledge-graph
   - /solutions/vertical-idp
   - /solutions/trade-compliance
   - /solutions/field-service-intelligence
2. views/industries.xml:
   - /industries/logistics
   - /industries/pharma
   - /industries/energy
   - /industries/fsm
3. views/resources_about_demo.xml:
   - /resources
   - /pricing
   - /about
   - /request-demo
"""
import re
import os

VIEWS_DIR = "/home/zen/O20/enterprise/insilos_website/views"

PAGES_DATA = {
    # ── SOLUTIONS SUBPAGES ──
    "graph": {
        "file": "platform_solutions.xml",
        "cockpit_title": "LIVING KNOWLEDGE MESH // FABRIC",
        "eyebrow": "ONTOLOGY &amp; SEMANTIC REASONING ENGINE",
        "badge1": "2.8M TRIPLES",
        "badge2": "W3C OWL/RDF",
        "back_link": "/solutions",
        "back_text": "← Xem tất cả giải pháp",
        "pills": [
            ("01", "Multi-Source Ingestion"),
            ("02", "Entity Resolution"),
            ("03", "Domino Risk GNN"),
            ("04", "Closed-Loop Action"),
        ],
        "acts": [
            {
                "headline": 'Thu Nạp <span class="text-cyan">45+ Nguồn Dữ Liệu</span> Phân Tán<br class="d-none d-md-inline"/> Kết Nối Trực Tiếp <span class="ins-gradient-headline">Real-Time CDC Stream</span>',
                "desc": "Hợp nhất tức thì dữ liệu ERP (SAP, Oracle), mạng lưới cảm biến SCADA/OPC-UA và hàng triệu trang tài liệu logistics phi cấu trúc. Cơ chế Change Data Capture (CDC) đảm bảo phản ánh trạng thái vật lý vào đồ thị với độ trễ &lt; 50ms.",
                "cta_primary": ("Khám Phá Ingestion Stream", "#graph-pillars", "arrow-down"),
                "cta_secondary": ("Tư Vấn Kết Nối ERP", "/request-demo", "plugs-connected", "cyan")
            },
            {
                "headline": 'Đồng Nhất Thực Thể <span class="text-mint">99.4% Chuẩn Xác</span><br class="d-none d-md-inline"/> Truy Vấn SPARQL <span class="ins-gradient-headline">&lt; 12ms Traversal</span>',
                "desc": "Thuật toán Entity Resolution tự động ánh xạ nhà cung cấp, lô hàng, mã vật tư và hợp đồng thành một mạng lưới quan hệ W3C RDF Mesh. Truy vết phả hệ dữ liệu Merkle DAG ngăn ngừa xung đột và sai lệch thông tin đa chi nhánh.",
                "cta_primary": ("Xem Cấu Trúc Ontology", "#graph-pillars", "arrow-right"),
                "cta_secondary": ("Thử Nghiệm SPARQL Query", "/request-demo", "tree-structure", "mint")
            },
            {
                "headline": 'Mạng Nơ-ron Đồ Thị <span class="text-warning">GNN Domino Predictor</span><br class="d-none d-md-inline"/> Cảnh Báo Đứt Gãy <span class="ins-gradient-headline">Trước 72 Giờ</span>',
                "desc": "Mô hình hóa tác động lan truyền (Ripple Effect) khi có sự cố tại một mắt xích cung ứng hay thiết bị trọng yếu. Cảnh báo sớm 72 giờ giúp ban lãnh đạo chủ động điều chỉnh nguồn cung ứng thay thế trước khi xảy ra đình trệ dây chuyền.",
                "cta_primary": ("Mô Phỏng Domino Risk", "#graph-pillars", "arrow-right"),
                "cta_secondary": ("Xem Thuật Toán GNN", "/request-demo", "lightning", "warning")
            },
            {
                "headline": 'Kích Hoạt Tự Động <span class="text-cyan">Sub-Second SLA</span><br class="d-none d-md-inline"/> Bảo Chứng Sổ Cái <span class="ins-gradient-headline">100% Traceable Ledger</span>',
                "desc": "Tự động kích hoạt đơn hàng thay thế, định tuyến lại dòng logistics và gửi cảnh báo điều phối kỹ sư ngay khi chỉ số rủi ro vượt ngưỡng. Mọi hành động được ký số mật mã và lưu trữ bất biến phục vụ công tác thanh kiểm tra.",
                "cta_primary": ("Trải Nghiệm Graph Demo", "/request-demo", "arrow-right"),
                "cta_secondary": ("Xem Lộ Trình Triển Khai", "#graph-pillars", "shield-check", "cyan")
            },
        ],
        "lineage": [
            ("Ontology Standards:", "W3C OWL/RDF", "Neo4j TripleStore", "Merkle DAG", "Air-Gapped Ready")
        ]
    },

    "idp": {
        "file": "platform_solutions.xml",
        "cockpit_title": "DOCUMENT INTELLIGENCE FABRIC",
        "eyebrow": "MULTIMODAL DOCUMENT PROCESSING ENGINE",
        "badge1": "0.38S STP",
        "badge2": "99.8% PRECISION",
        "back_link": "/solutions",
        "back_text": "← Xem tất cả giải pháp",
        "pills": [
            ("01", "Multi-Stream Ingestion"),
            ("02", "Dual-Engine OCR"),
            ("03", "3-Way Match"),
            ("04", "Direct Write-Back"),
        ],
        "acts": [
            {
                "headline": 'Thu Nạp Đa Luồng <span class="text-cyan">1,420 Chứng Từ/Giờ</span><br class="d-none d-md-inline"/> Xử Lý Tự Động Qua <span class="ins-gradient-headline">Kafka Event Queue</span>',
                "desc": "Tiếp nhận liên tục file PDF scan chất lượng thấp, ảnh chụp container từ hiện trường, dữ liệu EDIFACT hàng hải và XML tờ khai hải quan. Hệ thống tự động phân loại, khử nhiễu và định tuyến tài liệu vào pipeline bóc tách.",
                "cta_primary": ("Khám Phá Pipeline Thu Nạp", "#idp-capabilities", "arrow-down"),
                "cta_secondary": ("Gửi Mẫu Chứng Từ Thử Nghiệm", "/request-demo", "file-arrow-up", "cyan")
            },
            {
                "headline": 'Nhận Diện Kép <span class="text-mint">Dual-Engine OCR &amp; Vision LM</span><br class="d-none d-md-inline"/> Bóc Tách Bảng Biểu <span class="ins-gradient-headline">99.8% Chính Xác</span>',
                "desc": "Kết hợp mô hình OCR quang học với Large Vision Model chuyên ngành thương mại. Trích xuất chính xác 100% bảng biểu phức tạp, con dấu hải quan đa quốc gia và chữ viết tay trên Bill of Lading, Packing List mà không ảo giác.",
                "cta_primary": ("Xem Độ Chính Xác Bóc Tách", "#idp-capabilities", "arrow-right"),
                "cta_secondary": ("Live Sandbox IDP Demo", "/request-demo", "scan", "mint")
            },
            {
                "headline": 'Đối Soát 3 Bên <span class="text-emerald">Cross-Validation</span><br class="d-none d-md-inline"/> Khóa Chặt Sai Lệch <span class="ins-gradient-headline">0 Variance Budget</span>',
                "desc": "Tự động so khớp đối chiếu chéo số liệu giữa Hóa đơn thương mại, Bảng kê chi tiết (Packing List) và Vận đơn đường biển. Phát hiện tức thì sai lệch số lượng kiện, trọng lượng gross/net và đơn giá trước khi nộp hải quan.",
                "cta_primary": ("Xem Cơ Chế Đối Soát", "#idp-capabilities", "arrow-right"),
                "cta_secondary": ("Kiểm Tra Đối Soát Live", "/request-demo", "check-square-offset", "emerald")
            },
            {
                "headline": 'Ghi Trực Tiếp <span class="text-cyan">&lt; 2.1s E2E</span> Vào ERP<br class="d-none d-md-inline"/> Tuân Thủ Chuẩn <span class="ins-gradient-headline">Thông Tư 78 &amp; VAS 200</span>',
                "desc": "Đồng bộ dữ liệu trực tiếp vào hệ thống hải quan điện tử VNACCS/VCIS và ghi nhận sổ cái tài khoản kế toán SAP, Oracle. Hoàn tất toàn bộ chu trình xử lý chứng từ trong chưa đầy 2.1 giây với chứng từ số hợp pháp.",
                "cta_primary": ("Yêu Cầu Demo Tự Động Hóa", "/request-demo", "arrow-right"),
                "cta_secondary": ("Xem Khung Tích Hợp ERP", "#idp-capabilities", "database", "cyan")
            },
        ],
        "lineage": [
            ("Regulatory &amp; Compliance:", "VNACCS / VCIS", "Thông tư 78", "VAS 200/133", "ISO 27001")
        ]
    },

    "trade": {
        "file": "platform_solutions.xml",
        "cockpit_title": "AUTONOMOUS TRADE GOVERNANCE",
        "eyebrow": "CROSS-BORDER TRADE &amp; TARIFF ENGINE",
        "badge1": "WCO SAFE READY",
        "badge2": "-98% PENALTIES",
        "back_link": "/solutions",
        "back_text": "← Xem tất cả giải pháp",
        "pills": [
            ("01", "Trade Stream Ingestion"),
            ("02", "HS Code 8-10 Digit"),
            ("03", "FTA &amp; Origin Optimizer"),
            ("04", "Sanction Dossier Sign-Off"),
        ],
        "acts": [
            {
                "headline": 'Giám Sát Thời Gian Thực <span class="text-cyan">100% Hồ Sơ Hải Quan</span><br class="d-none d-md-inline"/> Kiểm Soát Trước Thông Quan <span class="ins-gradient-headline">Pre-Clearance Audit</span>',
                "desc": "Thu nạp và phân tích tức thì tờ khai hải quan điện tử, hợp đồng ngoại thương và chứng nhận xuất xứ C/O Form E, D, EUR.1. Phát hiện sớm nguy cơ luồng vàng, luồng đỏ và rủi ro truy thu thuế trước khi truyền tờ khai.",
                "cta_primary": ("Khám Phá Khung Quản Trị", "#compliance-pillars", "arrow-down"),
                "cta_secondary": ("Tư Vấn Hồ Sơ Xuất Nhập Khẩu", "/request-demo", "file-text", "cyan")
            },
            {
                "headline": 'Áp Mã Tự Động <span class="text-mint">HS Code 8-10 Số</span><br class="d-none d-md-inline"/> Độ Chính Xác Thuế <span class="ins-gradient-headline">99.4% Tax Precision</span>',
                "desc": "Công nghệ AI chuyên sâu phân tích thành phần kỹ thuật, công năng sản phẩm để áp mã HS chính xác theo Biểu thuế xuất nhập khẩu Việt Nam 2026. Loại bỏ hoàn toàn nguy cơ phạt vi phạm phân loại và truy thu thuế hồi tố.",
                "cta_primary": ("Xem Công Nghệ Áp Mã HS", "#compliance-pillars", "arrow-right"),
                "cta_secondary": ("Thử Nghiệm Áp Mã HS Live", "/request-demo", "barcode", "mint")
            },
            {
                "headline": 'Tối Ưu Ưu Đãi Thuế <span class="text-emerald">0% Duty Rate Target</span><br class="d-none d-md-inline"/> Tận Dụng Toàn Diện <span class="ins-gradient-headline">EVFTA, CPTPP &amp; RCEP</span>',
                "desc": "Tự động rà soát quy tắc xuất xứ cụ thể mặt hàng (PSR), tỷ lệ hàm lượng giá trị khu vực (RVC) và chuyển đổi mã số hàng hóa (CTC). Đảm bảo doanh nghiệp hưởng tối đa mức thuế suất ưu đãi đặc biệt trong mọi hiệp định FTA.",
                "cta_primary": ("Xem Ma Trận Quy Tắc Xuất Xứ", "#compliance-pillars", "arrow-right"),
                "cta_secondary": ("Tối Ưu Thuế FTA Của Bạn", "/request-demo", "globe", "emerald")
            },
            {
                "headline": 'Bảo Lãnh Kiểm Toán <span class="text-cyan">100% Audit Ready</span><br class="d-none d-md-inline"/> Rà Quét Trừng Phạt <span class="ins-gradient-headline">OFAC &amp; Bút Phê Mật Mã</span>',
                "desc": "Tự động rà quét đối tác và tàu vận chuyển qua danh sách trừng phạt quốc tế OFAC/EU. Xuất hồ sơ pháp lý kèm chữ ký số và bằng chứng giải trình phân loại thuế, sẵn sàng bảo vệ doanh nghiệp trong các đợt kiểm tra sau thông quan.",
                "cta_primary": ("Yêu Cầu Demo Trade Compliance", "/request-demo", "arrow-right"),
                "cta_secondary": ("Xem Hồ Sơ Kiểm Toán Mẫu", "#compliance-pillars", "certificate", "cyan")
            },
        ],
        "lineage": [
            ("Trade Standards:", "WCO SAFE Framework", "EVFTA / CPTPP / RCEP", "VNACCS / VCIS", "OFAC Sanction Guard")
        ]
    },

    "fsm": {
        "file": "platform_solutions.xml",
        "cockpit_title": "PREDICTIVE FSM DISPATCH FABRIC",
        "eyebrow": "IOT SCADA &amp; FIELD SERVICE INTELLIGENCE",
        "badge1": "&lt; 45S DISPATCH",
        "badge2": "94.8% FTFR",
        "back_link": "/solutions",
        "back_text": "← Xem tất cả giải pháp",
        "pills": [
            ("01", "SCADA Telemetry"),
            ("02", "Bearing Fatigue FFT"),
            ("03", "Technician Dispatch"),
            ("04", "Offline 3D SOP"),
        ],
        "acts": [
            {
                "headline": 'Thu Nạp Cảm Biến <span class="text-cyan">12.4k Điểm/Giây</span><br class="d-none d-md-inline"/> Tần Số Lấy Mẫu <span class="ins-gradient-headline">50.02 Hz SCADA / OPC-UA</span>',
                "desc": "Kết nối trực tiếp PLC/SCADA thu nạp phổ rung động, biến thiên nhiệt độ và áp suất dầu của tuabin, máy nén khí, cẩu trục cảng biển. Tín hiệu được truyền theo chuẩn công nghiệp IEC 61850 không làm trễ điều khiển thời gian thực.",
                "cta_primary": ("Khám Phá Tầng Thu Nạp SCADA", "#fsm-capabilities", "arrow-down"),
                "cta_secondary": ("Tư Vấn Kết Nối IoT", "/request-demo", "gauge", "cyan")
            },
            {
                "headline": 'Dự Báo Suy Hao <span class="text-mint">Trước 14 Ngày</span><br class="d-none d-md-inline"/> Phân Tích Phổ Rung Động <span class="ins-gradient-headline">FFT Spectral Analytics</span>',
                "desc": "Thuật toán AI phân tích phổ tần số FFT phát hiện sớm hiện tượng mỏi cơ khí, lệch trục và mòn rãnh vòng bi trước 14 ngày. Dự báo tuổi thọ hữu dụng còn lại (RUL), ngăn chặn hoàn toàn các sự cố dừng máy khẩn cấp ngoài kế hoạch.",
                "cta_primary": ("Xem Mô Hình Dự Báo RUL", "#fsm-capabilities", "arrow-right"),
                "cta_secondary": ("Thử Nghiệm Phân Tích Rung Động", "/request-demo", "chart-line-up", "mint")
            },
            {
                "headline": 'Điều Phối Tự Động <span class="text-warning">SLA &lt; 45 Giây</span><br class="d-none d-md-inline"/> Tỷ Lệ Sửa Chữa Lần Đầu <span class="ins-gradient-headline">94.8% FTFR</span>',
                "desc": "Thuật toán tối ưu hóa lộ trình GPS đa điểm, đối chiếu năng lực tay nghề kỹ sư và tự động dự giữ phụ tùng trong kho ERP. Đảm bảo kỹ thuật viên luôn mang đúng linh kiện ngay lần đầu tiên tới hiện trường.",
                "cta_primary": ("Xem Thuật Toán Điều Phối", "#fsm-capabilities", "arrow-right"),
                "cta_secondary": ("Mô Phỏng Lộ Trình Kỹ Sư", "/request-demo", "users-three", "warning")
            },
            {
                "headline": 'Chỉ Dẫn Bảo Trì <span class="text-cyan">Offline 3D SOP</span><br class="d-none d-md-inline"/> Nghiệm Thu Tức Thì <span class="ins-gradient-headline">Zero Downtime Sync</span>',
                "desc": "Ứng dụng di động cung cấp mô hình 3D tháo lắp từng bước hoạt động hoàn toàn ngoại tuyến tại hầm mỏ, giàn khoan. Nghiệm thu điện tử bằng hình ảnh và chữ ký số tự động đồng bộ về sổ cái bảo trì Odoo/SAP khi có mạng.",
                "cta_primary": ("Trải Nghiệm Live FSM Demo", "/request-demo", "arrow-right"),
                "cta_secondary": ("Xem Giao Diện Di Động", "#fsm-capabilities", "device-mobile-camera", "cyan")
            },
        ],
        "lineage": [
            ("Technical Protocols:", "IEC 61850 &amp; OPC-UA", "ISO 55000 Asset Mgmt", "FFT Vibration Spectrum", "Offline Mobile Sync")
        ]
    },

    # ── INDUSTRIES SUBPAGES ──
    "logistics": {
        "file": "industries.xml",
        "cockpit_title": "PORT TERMINAL CONTROL FABRIC",
        "eyebrow": "PORT TERMINAL &amp; MARITIME LOGISTICS",
        "badge1": "14,200 TEU CAPACITY",
        "badge2": "WCO SAFE CERTIFIED",
        "back_link": "/industries",
        "back_text": "← Xem tất cả ngành công nghiệp",
        "pills": [
            ("01", "Quay Crane Telemetry"),
            ("02", "TOS &amp; VNACCS"),
            ("03", "Multimodal Gate"),
            ("04", "Demurrage Shield"),
        ],
        "acts": [
            {
                "headline": 'Giám Sát Cẩu Giàn <span class="text-cyan">32 Moves/Giờ</span><br class="d-none d-md-inline"/> Định Vị Hàng Hải <span class="ins-gradient-headline">Real-Time AIS Tracking</span>',
                "desc": "Thu nạp thời gian thực dữ liệu vận hành từ hệ thống cẩu giàn bờ STS và cẩu bãi RTG tại cụm cảng Cái Mép - Thị Vải. Tích hợp hải trình AIS theo dõi tàu cập cầu, tối ưu hóa biểu đồ phân bổ bến bãi theo giờ.",
                "cta_primary": ("Xem Sơ Đồ Cảng Biển", "#logistics-architecture", "arrow-down"),
                "cta_secondary": ("Tư Vấn Tích Hợp TOS", "/request-demo", "anchor", "cyan")
            },
            {
                "headline": 'Khớp Nối Tức Thì <span class="text-mint">99.8% Match</span><br class="d-none d-md-inline"/> Đồng Bộ Thông Quan <span class="ins-gradient-headline">0 Inline Bottleneck</span>',
                "desc": "Tự động đối chiếu thông tin manifest hãng tàu với hệ thống thông quan điện tử VNACCS và phần mềm điều hành cảng TOS. Giải phóng container khỏi bãi chỉ trong vài phút thay vì xếp hàng chờ duyệt giấy tờ thủ công.",
                "cta_primary": ("Xem Quy Trình Đối Chiếu", "#logistics-architecture", "arrow-right"),
                "cta_secondary": ("Demo Đối Soát Manifest", "/request-demo", "receipt", "mint")
            },
            {
                "headline": 'Tối Ưu Cổng Cảng <span class="text-warning">&lt; 18 Phút/Xe</span><br class="d-none d-md-inline"/> Nhận Diện Tự Động <span class="ins-gradient-headline">OCR &amp; Smart Queueing</span>',
                "desc": "Camera AI nhận diện biển số đầu kéo và mã số container tự động tại cổng. Phân làn thông minh và chỉ định chính xác tọa độ vị trí bãi hạ hàng, giảm 40% thời gian ùn tắc xe container tại khu vực cảng.",
                "cta_primary": ("Xem Giải Pháp Cổng Cảng", "#logistics-architecture", "arrow-right"),
                "cta_secondary": ("Khảo Sát Hiện Trường", "/request-demo", "truck", "warning")
            },
            {
                "headline": 'Xóa Bỏ Rủi Ro <span class="text-emerald">-88% Phí Lưu Bãi</span><br class="d-none d-md-inline"/> Tối Ưu Toàn Diện <span class="ins-gradient-headline">Green Port 2026</span>',
                "desc": "Hệ thống cảnh báo sớm thời hạn lưu bãi miễn phí (Free Time) và tự động đề xuất phương án rút hàng tối ưu chi phí. Giúp các doanh nghiệp chủ hàng và hãng tàu tiết kiệm hàng triệu USD chi phí Demurrage &amp; Detention mỗi năm.",
                "cta_primary": ("Đăng Ký Khảo Sát Cảng Biển", "/request-demo", "arrow-right"),
                "cta_secondary": ("Tải Báo Cáo ROI Logistics", "#logistics-architecture", "shield-check", "emerald")
            },
        ],
        "lineage": [
            ("Maritime Standards:", "WCO SAFE Framework", "AIS Maritime Tracking", "TOS Integration", "Green Port 2026")
        ]
    },

    "pharma": {
        "file": "industries.xml",
        "cockpit_title": "PHARMA CLEANROOM CONTROL FABRIC",
        "eyebrow": "PHARMACEUTICAL &amp; CLEANROOM MANUFACTURING",
        "badge1": "GAMP 5 COMPLIANT",
        "badge2": "21 CFR PART 11",
        "back_link": "/industries",
        "back_text": "← Xem tất cả ngành công nghiệp",
        "pills": [
            ("01", "Bioreactor Telemetry"),
            ("02", "Golden Batch SPC"),
            ("03", "OOS Deviation Lock"),
            ("04", "21 CFR Part 11 EBR"),
        ],
        "acts": [
            {
                "headline": 'Thu Nạp Cleanroom <span class="text-cyan">0.1s Sampling</span><br class="d-none d-md-inline"/> Giám Sát Lên Men <span class="ins-gradient-headline">PAT Real-Time Sensors</span>',
                "desc": "Giám sát liên tục nhiệt độ, áp suất, độ pH, oxy hòa tan DO và nồng độ sinh khối trong bồn lên men sinh học. Thu nạp dữ liệu phân tích quy trình (PAT) với tần suất 0.1 giây, đảm bảo môi trường nuôi cấy vô trùng tuyệt đối.",
                "cta_primary": ("Xem Sơ Đồ Cleanroom", "#pharma-architecture", "arrow-down"),
                "cta_secondary": ("Tư Vấn Thiết Kế PAT", "/request-demo", "flask", "cyan")
            },
            {
                "headline": 'Phân Tích Đa Biến <span class="text-mint">+14.2% Yield Tăng Trưởng</span><br class="d-none d-md-inline"/> Mô Hình Mẻ Mẫu <span class="ins-gradient-headline">Golden Batch Trajectory</span>',
                "desc": "Mô hình hóa đường cong mẻ thuốc lý tưởng theo thời gian thực bằng thuật toán SPC đa biến. So sánh quỹ đạo mẻ hiện tại với mẻ chuẩn để kịp thời điều chỉnh vi lượng dưỡng chất, gia tăng 14.2% sản lượng hoạt chất đầu ra.",
                "cta_primary": ("Khám Phá Golden Batch", "#pharma-architecture", "arrow-right"),
                "cta_secondary": ("Demo Mô Phỏng Mẻ Lên Men", "/request-demo", "chart-polar", "mint")
            },
            {
                "headline": 'Khóa Chặt Sai Lệch <span class="text-warning">-70% Sự Cố OOS/OOT</span><br class="d-none d-md-inline"/> Bảo Vệ Mẻ Thuốc <span class="ins-gradient-headline">Zero Discarded Batches</span>',
                "desc": "Tự động phát hiện xu hướng chệch chuẩn (Out of Trend - OOT) trước khi vi phạm giới hạn tiêu chuẩn chất lượng (Out of Specification - OOS). Khóa cứng tham số van điều khiển để cứu vãn mẻ thuốc giá trị hàng trăm nghìn USD.",
                "cta_primary": ("Xem Cơ Chế Khóa OOS", "#pharma-architecture", "arrow-right"),
                "cta_secondary": ("Đánh Giá Rủi Ro Dược Phẩm", "/request-demo", "warning-octagon", "warning")
            },
            {
                "headline": 'Hồ Sơ Lô Điện Tử <span class="text-emerald">100% Audit Proof</span><br class="d-none d-md-inline"/> Tuân Thủ Nghiêm Ngặt <span class="ins-gradient-headline">FDA 21 CFR Part 11</span>',
                "desc": "Tự động tạo hồ sơ mẻ thuốc điện tử (Electronic Batch Record - EBR) kèm chữ ký số hai lớp và nhật ký kiểm toán Audit Trail không thể thay đổi. Sẵn sàng vượt qua mọi đợt thanh tra gắt gao của Cục Quản lý Dược và WHO/FDA.",
                "cta_primary": ("Yêu Cầu Demo Pharma EBR", "/request-demo", "arrow-right"),
                "cta_secondary": ("Tải Khung Chuẩn GAMP 5", "#pharma-architecture", "signature", "emerald")
            },
        ],
        "lineage": [
            ("Pharma Standards:", "FDA 21 CFR Part 11", "GAMP 5 Guidelines", "GMP-WHO Validated", "Multi-Variate SPC")
        ]
    },

    "energy": {
        "file": "industries.xml",
        "cockpit_title": "SMART GRID &amp; WIND FABRIC",
        "eyebrow": "RENEWABLE ENERGY &amp; SMART TRANSMISSION",
        "badge1": "500KV ONLINE",
        "badge2": "IEC 61850 COMPLIANT",
        "back_link": "/industries",
        "back_text": "← Xem tất cả ngành công nghiệp",
        "pills": [
            ("01", "500kV Substation"),
            ("02", "Wind Digital Twin"),
            ("03", "Frequency Balancer"),
            ("04", "Blackout Interlock"),
        ],
        "acts": [
            {
                "headline": 'Giám Sát Trạm Biến Áp <span class="text-cyan">10ms Tốc Độ Bắt Gói</span><br class="d-none d-md-inline"/> Truyền Dẫn Điện Lực <span class="ins-gradient-headline">500kV IEC 61850 Stream</span>',
                "desc": "Kết nối trực tiếp hệ thống đo lường quang học CT/PT tại các trạm biến áp truyền tải 500kV và đường dây liên kết Bắc - Nam. Bắt gói tin vi sai với chu kỳ 10 mili-giây, cung cấp bức tranh vận hành siêu chính xác cho trung tâm điều độ.",
                "cta_primary": ("Xem Sơ Đồ Lưới Điện", "#energy-architecture", "arrow-down"),
                "cta_secondary": ("Tư Vấn Tích Hợp SCADA Năng Lượng", "/request-demo", "lightning", "cyan")
            },
            {
                "headline": 'Bản Sao Số Hóa <span class="text-mint">98.6% Sức Khỏe Tuabin</span><br class="d-none d-md-inline"/> Dự Báo Hộp Số <span class="ins-gradient-headline">Offshore Turbine Twin</span>',
                "desc": "Mô phỏng khí động học cánh quạt và tải trọng cơ khí trên hộp số tuabin gió ngoài khơi. Thuật toán phân tích ứng suất kết cấu dự báo chính xác độ mòn vòng bi chính trước 21 ngày trong điều kiện bão biển khắc nghiệt.",
                "cta_primary": ("Xem Bản Sao Số Tuabin", "#energy-architecture", "arrow-right"),
                "cta_secondary": ("Demo Giám Sát Tuabin Gió", "/request-demo", "wind", "mint")
            },
            {
                "headline": 'Cân Bằng Tần Số <span class="text-emerald">Mục Tiêu 50.02 Hz</span><br class="d-none d-md-inline"/> Điều Độ Tự Trị <span class="ins-gradient-headline">Active Inertia Control</span>',
                "desc": "Tự động tính toán và điều tiết công suất phát điện gió/mặt trời kết hợp hệ thống pin lưu trữ BESS. Bù quán tính lưới điện thời gian thực, duy trì tần số ổn định 50.02 Hz chống lại sự trồi sụt đột ngột của năng lượng tái tạo.",
                "cta_primary": ("Xem Cơ Chế Cân Bằng Phụ Tải", "#energy-architecture", "arrow-right"),
                "cta_secondary": ("Tư Vấn Lưu Trữ Năng Lượng", "/request-demo", "sliders-horizontal", "emerald")
            },
            {
                "headline": 'Khóa Chống Rã Lưới <span class="text-cyan">0s Major Outage</span><br class="d-none d-md-inline"/> Cô Lập Sự Cố <span class="ins-gradient-headline">40ms Fault Isolation</span>',
                "desc": "Thuật toán phát hiện sự cố phóng điện hoặc đứt pha tự động cô lập phân đoạn đường dây trong 40 mili-giây, ngăn chặn hiệu ứng sụp đổ dây chuyền dẫn đến rã lưới diện rộng. Giải pháp đã kiểm chứng tại các nhà máy điện các nhà máy phát điện quốc gia.",
                "cta_primary": ("Đăng Ký Tư Vấn Năng Lượng", "/request-demo", "arrow-right"),
                "cta_secondary": ("Xem Hồ Sơ Ngành Năng Lượng", "#energy-architecture", "shield-check", "cyan")
            },
        ],
        "lineage": [
            ("Grid Standards:", "IEC 61850 Architecture", "500kV Transmission Ready", "Grid Proven", "Sub-40ms Protection")
        ]
    },

    "fsm_ind": {
        "file": "industries.xml",
        "cockpit_title": "TELECOM FIELD MOBILITY FABRIC",
        "eyebrow": "TELECOMMUNICATIONS &amp; HEAVY FLEET",
        "badge1": "&lt; 45S SLA DISPATCH",
        "badge2": "FIRST-TIME-FIX READY",
        "back_link": "/industries",
        "back_text": "← Xem tất cả ngành công nghiệp",
        "pills": [
            ("01", "BTS IoT Telemetry"),
            ("02", "Traffic GPS Routing"),
            ("03", "Spare Parts Ready"),
            ("04", "Mobile Sign-Off"),
        ],
        "acts": [
            {
                "headline": 'Giám Sát Trạm Thu Phát <span class="text-cyan">Hàng Nghìn Trạm BTS</span><br class="d-none d-md-inline"/> Tín Hiệu Nguồn Phụ <span class="ins-gradient-headline">Battery Health Stream</span>',
                "desc": "Thu nạp dữ liệu IoT từ tủ nguồn, dung lượng ắc quy dự phòng và mức dầu máy phát điện tại các trạm BTS viễn thông vùng sâu vùng xa. Phát hiện sớm nguy cơ mất nguồn để kích hoạt kỹ sư ứng cứu trước khi mất liên lạc.",
                "cta_primary": ("Xem Kiến Trúc Hạ Tầng BTS", "#fsm-architecture", "arrow-down"),
                "cta_secondary": ("Tư Vấn Quản Lý Hạ Tầng Viễn Thông", "/request-demo", "broadcast", "cyan")
            },
            {
                "headline": 'Tối Ưu Tuyến Đường <span class="text-mint">-35% Thời Gian Di Chuyển</span><br class="d-none d-md-inline"/> Thuật Toán Giao Thông <span class="ins-gradient-headline">Traffic-Aware GPS Solver</span>',
                "desc": "Tính toán lộ trình di chuyển tối ưu theo dữ liệu mật độ giao thông thực tế. Nhóm các phiếu công tác cùng khu vực địa lý, giảm 35% thời gian di chuyển và cắt giảm đáng kể chi phí nhiên liệu đội xe kỹ thuật.",
                "cta_primary": ("Xem Thuật Toán Định Tuyến", "#fsm-architecture", "arrow-right"),
                "cta_secondary": ("Demo Lộ Trình Kỹ Sư Hiện Trường", "/request-demo", "navigation-arrow", "mint")
            },
            {
                "headline": 'Sẵn Sàng Linh Kiện <span class="text-warning">100% Parts Ready</span><br class="d-none d-md-inline"/> Dự Giữ Tự Động <span class="ins-gradient-headline">Inventory Auto-Reserve</span>',
                "desc": "Hệ thống tự động liên kết mã lỗi trạm viễn thông với danh mục vật tư phụ tùng cần thiết trên kho ERP. Tự động xuất phiếu kho sẵn sàng tại cốp xe kỹ thuật viên, đảm bảo xử lý dứt điểm sự cố ngay lần đầu tiên tới trạm.",
                "cta_primary": ("Xem Quản Lý Phụ Tùng Tự Động", "#fsm-architecture", "arrow-right"),
                "cta_secondary": ("Khảo Sát Năng Lực FTFR", "/request-demo", "wrench", "warning")
            },
            {
                "headline": 'Nghiệm Thu Di Động <span class="text-emerald">Instant Cloud Sync</span><br class="d-none d-md-inline"/> Hoạt Động Ngoại Tuyến <span class="ins-gradient-headline">Mobile Acceptance App</span>',
                "desc": "Kỹ thuật viên chụp ảnh hiện trường, quét mã vạch thiết bị thay thế và ký nghiệm thu điện tử trực tiếp trên ứng dụng di động ngay cả khi mất sóng 4G/5G. Dữ liệu tự động đồng bộ về hệ thống trung tâm ngay khi có kết nối.",
                "cta_primary": ("Trải Nghiệm Giải Pháp Viễn Thông", "/request-demo", "arrow-right"),
                "cta_secondary": ("Xem Hệ Sinh Thái Viễn Thông", "#fsm-architecture", "check-circle", "emerald")
            },
        ],
        "lineage": [
            ("Mobility Standards:", "Telecom Tower IoT", "GPS Multi-Stop Solver", "Telco Proven", "Offline Native Sync")
        ]
    },

    # ── GROWTH ROUTES ──
    "pricing": {
        "file": "resources_about_demo.xml",
        "cockpit_title": "SOVEREIGN TCO LEDGER FABRIC",
        "eyebrow": "TRANSPARENT ENTERPRISE PRICING",
        "badge1": "AUDIT VERIFIED",
        "badge2": "FIXED TCO GUARANTEE",
        "back_link": None,
        "back_text": None,
        "pills": [
            ("01", "Sovereign Core"),
            ("02", "Micro-Ledger Metering"),
            ("03", "Zero Egress Surprise"),
            ("04", "SLA Refund Guarantee"),
        ],
        "acts": [
            {
                "headline": 'Lõi Tự Chủ Dữ Liệu <span class="text-cyan">Sovereign Core</span><br class="d-none d-md-inline"/> Triển Khai Hoàn Toàn <span class="ins-gradient-headline">Air-Gapped &amp; On-Premises</span>',
                "desc": "Toàn quyền sở hữu và kiểm soát mã nguồn, mô hình AI và dữ liệu công nghiệp nhạy cảm. Triển khai linh hoạt trên Private Cloud hoặc hệ thống máy chủ nội bộ On-Premises, triệt tiêu hoàn toàn rủi ro rò rỉ dữ liệu xuyên biên giới.",
                "cta_primary": ("Xem Chi Tiết 3 Gói Dịch Vụ", "#pricing-plans", "arrow-down"),
                "cta_secondary": ("Tư Vấn Kiến Trúc Sovereign", "/request-demo", "lock-key", "cyan")
            },
            {
                "headline": 'Định Lượng Minh Bạch <span class="text-mint">Micro-Ledger Metering</span><br class="d-none d-md-inline"/> Tính Phí Chính Xác <span class="ins-gradient-headline">Pay-As-You-Operate</span>',
                "desc": "Sổ cái tiêu thụ tín chỉ ghi nhận minh bạch từng tác vụ bóc tách tài liệu, truy vấn đồ thị hay giờ giám sát cảm biến SCADA theo thời gian thực. Báo cáo kiểm toán chi phí chi tiết đến từng mili-giây, không tính phí theo đầu người sử dụng.",
                "cta_primary": ("Ước Tính Chi Phí Vận Hành", "#pricing-plans", "arrow-right"),
                "cta_secondary": ("Dùng Thử Credit Ledger", "/request-demo", "receipt", "mint")
            },
            {
                "headline": 'Cam Kết Chi Phí <span class="text-emerald">0 VNĐ Phí Ẩn</span><br class="d-none d-md-inline"/> Không Phát Sinh <span class="ins-gradient-headline">Zero Cloud Egress Surprise</span>',
                "desc": "Xóa bỏ hoàn toàn nỗi lo hóa đơn truyền dữ liệu đám mây (Egress Fees) leo thang khó lường hay phí bản quyền nâng cấp đột xuất. Đảm bảo tổng chi phí sở hữu (TCO) cố định và có thể dự báo chính xác trong suốt vòng đời dự án.",
                "cta_primary": ("Xem Bảng So Sánh Chi Phí TCO", "#pricing-plans", "arrow-right"),
                "cta_secondary": ("Tính Toán Điểm Hòa Vốn ROI", "/request-demo", "currency-circle-dollar", "emerald")
            },
            {
                "headline": 'Cam Kết Khắt Khe <span class="text-cyan">99.95% SLA Uptime</span><br class="d-none d-md-inline"/> Chính Sách Hoàn Tiền <span class="ins-gradient-headline">Enterprise SLA Refund</span>',
                "desc": "Hợp đồng pháp lý ký kết trực tiếp tại Việt Nam với điều khoản hoàn tiền phạt rõ ràng nếu hệ thống không đạt chỉ số sẵn sàng và thời gian đáp ứng đã cam kết. Bảo lãnh chất lượng dịch vụ vận hành ở mức cao nhất.",
                "cta_primary": ("Kích Hoạt Chương Trình Pilot", "/request-demo", "arrow-right"),
                "cta_secondary": ("Tải Bản Mẫu Hợp Đồng SLA", "#pricing-plans", "seal-check", "cyan")
            },
        ],
        "lineage": [
            ("Sovereign TCO:", "0 VNĐ Cloud Egress", "100% On-Premises", "Micro-Ledger Billing", "Audit SLA Guarantee")
        ]
    },

    "about": {
        "file": "resources_about_demo.xml",
        "cockpit_title": "INSILOS R&amp;D INNOVATION FABRIC",
        "eyebrow": "ENGINEERING DNA &amp; R&amp;D VISION",
        "badge1": "SOVEREIGN OPERATIONAL AI",
        "badge2": "ISO 27001 CERTIFIED",
        "back_link": None,
        "back_text": None,
        "pills": [
            ("01", "Domain Research"),
            ("02", "Sovereign AI Core"),
            ("03", "Reliability Gates"),
            ("04", "Co-Innovation Labs"),
        ],
        "acts": [
            {
                "headline": 'Nghiên Cứu Chuyên Sâu <span class="text-cyan">15+ Năm Lĩnh Vực</span><br class="d-none d-md-inline"/> Thấu Hiểu Bản Địa <span class="ins-gradient-headline">Domain-First Engineering</span>',
                "desc": "Đội ngũ kỹ sư trưởng và chuyên gia hàng đầu tập trung giải quyết bài toán vận hành công nghiệp phức tạp: từ chuẩn kế toán VAS 200, thông quan VNACCS, lưới điện 500kV đến tiêu chuẩn dược phẩm sạch của Bộ Y Tế.",
                "cta_primary": ("Tìm Hiểu Đội Ngũ &amp; Sứ Mệnh", "#about-pillars", "arrow-down"),
                "cta_secondary": ("Liên Hệ Ban Cố Vấn Kỹ Thuật", "/request-demo", "atom", "cyan")
            },
            {
                "headline": 'Kiến Trúc Lõi Độc Lập <span class="text-mint">Sovereign AI Core</span><br class="d-none d-md-inline"/> Tự Chủ Công Nghệ <span class="ins-gradient-headline">Zero Vendor Lock-In</span>',
                "desc": "Xây dựng toàn diện từ tầng lõi xử lý dữ liệu đến mô hình tác tử AI tự trị không phụ thuộc vào hạ tầng đám mây nước ngoài. Giúp các doanh nghiệp trọng yếu hoàn toàn tự chủ tài sản trí tuệ và an ninh số quốc gia.",
                "cta_primary": ("Xem Kiến Trúc Độc Lập", "#about-pillars", "arrow-right"),
                "cta_secondary": ("Tư Vấn Tự Chủ Hạ Tầng", "/request-demo", "cpu", "mint")
            },
            {
                "headline": 'Chuẩn Mực Mã Nguồn <span class="text-warning">100% Strict Tested</span><br class="d-none d-md-inline"/> Tiêu Chuẩn Khắt Khe <span class="ins-gradient-headline">Strict Quality Gates</span>',
                "desc": "Mọi dòng mã nguồn được kiểm thử tự động qua 7 tầng cổng chất lượng, mô phỏng tải hàng triệu thông điệp và quét lỗ hổng an ninh mạng thường trực. Đảm bảo độ ổn định tuyệt đối cho các hạ tầng kỹ thuật huyết mạch.",
                "cta_primary": ("Xem Bộ Tiêu Chuẩn Kỹ Thuật", "#about-pillars", "arrow-right"),
                "cta_secondary": ("Khám Phá Quality Gates", "/resources", "code", "warning")
            },
            {
                "headline": 'Đồng Sáng Tạo Giá Trị <span class="text-emerald">Co-Innovation Labs</span><br class="d-none d-md-inline"/> Đồng Hành Sản Xuất <span class="ins-gradient-headline">Proven APAC Track</span>',
                "desc": "Không chỉ cung cấp phần mềm, chúng tôi sát cánh cùng ban lãnh đạo và kỹ sư vận hành tại hiện trường nhà máy, trạm phát điện và bến cảng để biến dữ liệu thô thành lợi nhuận và năng suất đo lường được.",
                "cta_primary": ("Hợp Tác Đồng Sáng Tạo", "/request-demo", "arrow-right"),
                "cta_secondary": ("Xem Dự Án Tiêu Biểu", "#about-pillars", "handshake", "emerald")
            },
        ],
        "lineage": [
            ("Engineering DNA:", "Sovereign Architecture", "Zero Lock-in", "ISO 27001 Certified", "15+ Years Domain R&amp;D")
        ]
    },

    "resources": {
        "file": "resources_about_demo.xml",
        "cockpit_title": "ARCHITECTURE REPOSITORY",
        "eyebrow": "KNOWLEDGE &amp; GOVERNANCE HUB",
        "badge1": "40+ BLUEPRINTS",
        "badge2": "UPDATED 2026",
        "back_link": None,
        "back_text": None,
        "pills": [
            ("01", "Reference Blueprints"),
            ("02", "Research Whitepapers"),
            ("03", "Compliance Guides"),
            ("04", "ROI Calculators"),
        ],
        "acts": [
            {
                "headline": 'Sơ Đồ Kiến Trúc <span class="text-cyan">Reference Blueprints</span><br class="d-none d-md-inline"/> Triển Khai Thực Chiến <span class="ins-gradient-headline">Production-Ready Designs</span>',
                "desc": "Thư viện sơ đồ kiến trúc mẫu chi tiết cho tích hợp SAP ECC/S4HANA, Oracle EBS, hệ thống điều khiển SCADA và mạng lưới dữ liệu Air-Gapped. Được thiết kế chuẩn hóa cho các Kỹ Sư Trưởng và Giám Đốc Công Nghệ.",
                "cta_primary": ("Khám Phá 40+ Blueprints", "#resources-grid", "arrow-down"),
                "cta_secondary": ("Yêu Cầu Blueprint Chuyên Biệt", "/request-demo", "blueprint", "cyan")
            },
            {
                "headline": 'Báo Cáo Nghiên Cứu <span class="text-mint">Whitepapers Thực Tế</span><br class="d-none d-md-inline"/> Dữ Liệu Thực Nghiệm <span class="ins-gradient-headline">Empirical ROI Studies</span>',
                "desc": "Các công trình nghiên cứu sâu sắc về hiệu quả tự động hóa bóc tách chứng từ logistics, mô hình hóa đồ thị tri thức chống đứt gãy cung ứng và giảm thiểu thời gian dừng máy phát điện tại thị trường Việt Nam.",
                "cta_primary": ("Tải Các Bản Whitepapers", "#resources-grid", "arrow-right"),
                "cta_secondary": ("Đăng Ký Nhận Nghiên Cứu Mới", "/request-demo", "book-bookmark", "mint")
            },
            {
                "headline": 'Hướng Dẫn Pháp Lý <span class="text-emerald">Compliance Guides</span><br class="d-none d-md-inline"/> Chuẩn Bị Kiểm Toán <span class="ins-gradient-headline">WCO · FDA · IEC Standards</span>',
                "desc": "Bộ tài liệu hướng dẫn kỹ thuật chi tiết giúp doanh nghiệp chuẩn bị hồ sơ tuân thủ theo chuẩn hải quan WCO SAFE, quy định hồ sơ điện tử FDA 21 CFR Part 11 và tiêu chuẩn truyền thông điện lực IEC 61850.",
                "cta_primary": ("Xem Hướng Dẫn Tuân Thủ", "#resources-grid", "arrow-right"),
                "cta_secondary": ("Tư Vấn Khung Tiêu Chuẩn", "/request-demo", "shield-check", "emerald")
            },
            {
                "headline": 'Công Cụ Tương Tác <span class="text-cyan">Interactive ROI Calculators</span><br class="d-none d-md-inline"/> Tính Toán Chi Phí <span class="ins-gradient-headline">Dynamic TCO Formulas</span>',
                "desc": "Bộ công cụ trực tuyến cho phép các nhà quản trị ước tính chính xác thời gian hoàn vốn đầu tư (Payback Period), chi phí tiết kiệm từ việc xóa bỏ gõ tay chứng từ và giá trị giảm thiểu rủi ro vi phạm thuế.",
                "cta_primary": ("Sử Dụng ROI Calculator", "#resources-grid", "arrow-right"),
                "cta_secondary": ("Yêu Cầu Báo Cáo TCO Riêng", "/request-demo", "calculator", "cyan")
            },
        ],
        "lineage": [
            ("Repository Topics:", "IDP Blueprint", "Graph Architecture", "FDA &amp; IEC Guides", "Interactive Calculators")
        ]
    },

    "demo": {
        "file": "resources_about_demo.xml",
        "cockpit_title": "MISSION CONTROL LIVE SCHEDULING",
        "eyebrow": "TAILORED OPERATIONAL AI WALKTHROUGH",
        "badge1": "48H SANDBOX TURNAROUND",
        "badge2": "NDA PROTECTED",
        "back_link": None,
        "back_text": None,
        "pills": [
            ("01", "Needs Assessment"),
            ("02", "Live Sandbox PoC"),
            ("03", "Custom Blueprint &amp; ROI"),
            ("04", "Executive Briefing"),
        ],
        "acts": [
            {
                "headline": 'Khảo Sát Hiện Trạng <span class="text-cyan">Needs Assessment</span><br class="d-none d-md-inline"/> Phản Hồi Chuyên Gia Trong <span class="ins-gradient-headline">&lt; 15 Phút</span>',
                "desc": "Đội ngũ kỹ sư trưởng tiếp nhận và phân tích hiện trạng các ốc đảo dữ liệu, luồng chứng từ thủ công và rủi ro vận hành cụ thể của doanh nghiệp. Cam kết bảo mật thông tin tuyệt đối với thỏa thuận NDA ngay từ đầu.",
                "cta_primary": ("Điền Form Yêu Cầu Demo", "#demo-form-anchor", "arrow-down"),
                "cta_secondary": ("Gọi Trực Tiếp Kỹ Sư Trưởng", "tel:+84944311811", "phone", "cyan")
            },
            {
                "headline": 'Môi Trường Thử Nghiệm <span class="text-mint">Live Sandbox PoC</span><br class="d-none d-md-inline"/> Sẵn Sàng Vận Hành <span class="ins-gradient-headline">48 Giờ Khởi Tạo</span>',
                "desc": "Khởi tạo môi trường Sandbox bảo mật riêng biệt với dữ liệu mẫu tổng hợp (Synthetic Data) sát thực tế ngành của bạn. Trực tiếp trải nghiệm tốc độ bóc tách tài liệu 0.38s và khả năng truy vấn đồ thị tri thức &lt; 15ms.",
                "cta_primary": ("Xem Quy Trình Sandbox PoC", "#demo-form-anchor", "arrow-right"),
                "cta_secondary": ("Đăng Ký Sandbox 48h", "#demo-form-anchor", "database", "mint")
            },
            {
                "headline": 'Bản Thiết Kế May Đo <span class="text-warning">Custom Solution Blueprint</span><br class="d-none d-md-inline"/> Dự Toán Kinh Tế <span class="ins-gradient-headline">100% Customized TCO</span>',
                "desc": "Cung cấp bản thiết kế kiến trúc kỹ thuật chi tiết phù hợp với hệ thống ERP/SCADA sẵn có, kèm mô hình phân tích chi phí đầu tư và lộ trình hoàn vốn rõ ràng dành cho Hội Đồng Quản Trị và Ban Điều Hành.",
                "cta_primary": ("Xem Khung Thiết Kế May Đo", "#demo-form-anchor", "arrow-right"),
                "cta_secondary": ("Yêu Cầu Mô Hình TCO", "#demo-form-anchor", "chart-line-up", "warning")
            },
            {
                "headline": 'Buổi Trình Bày Cấp Cao <span class="text-emerald">Executive Briefing</span><br class="d-none d-md-inline"/> Tư Vấn Trực Tiếp Bởi <span class="ins-gradient-headline">Chief Solutions Architect</span>',
                "desc": "Buổi làm việc chuyên sâu trực tiếp giữa Kỹ Sư Trưởng Insilos và Ban Lãnh Đạo doanh nghiệp. Thảo luận chiến lược tự chủ dữ liệu, an ninh mạng cấp độ cao và lộ trình triển khai tăng tốc 7-14 ngày.",
                "cta_primary": ("Đặt Lịch Briefing Trực Tiếp", "#demo-form-anchor", "arrow-right"),
                "cta_secondary": ("Tải Hồ Sơ Năng Lực Insilos", "/resources", "presentation", "emerald")
            },
        ],
        "lineage": [
            ("POC Highlights:", "48h Sandbox Turnaround", "NDA Protected", "Chief Architect Consultation", "Zero Cloud Egress")
        ]
    }
}

def render_left_column(data):
    # Back link if present
    back_html = ""
    if data["back_link"]:
        back_html = f"""                                <div class="mb-3">
                                    <a href="{data['back_link']}" class="text-white-70 text-decoration-none small fw-bold">{data['back_text']}</a>
                                </div>\n"""

    # Top badges
    top_badge_html = f"""                                <div class="d-flex align-items-center flex-wrap gap-2 mb-3">
                                    <div class="ins-pill-badge">
                                        <span class="ins-live-ping"/>
                                        <span>{data['cockpit_title']}</span>
                                    </div>
                                    <span class="badge bg-white-10 text-cyan border border-white-10 small font-monospace">{data['badge1']}</span>
                                    <span class="badge bg-white-10 text-mint border border-white-10 small font-monospace">{data['badge2']}</span>
                                </div>"""

    # Pills
    pill_items = []
    for idx, (num, label) in enumerate(data["pills"], 1):
        active_cls = " active" if idx == 1 else ""
        pill_items.append(f"""                                    <button type="button" class="ins-hero-pill{active_cls}" data-layer-target="{idx}">
                                        <span class="ins-hero-pill-num">{num}</span>
                                        <span>{label}</span>
                                    </button>""")
    pills_html = """                                <!-- 4-Tier Interactive Selector Pills -->
                                <div class="ins-hero-pill-nav d-flex flex-wrap gap-2 mb-4">
""" + "\n".join(pill_items) + "\n                                </div>"

    # Act Panes
    act_panes = []
    for idx, act in enumerate(data["acts"], 1):
        active_cls = " active" if idx == 1 else ""
        p_text, p_href, p_icon = act["cta_primary"]
        s_text, s_href, s_icon, s_color = act["cta_secondary"]

        act_panes.append(f"""                                <!-- Act {idx}: {data['pills'][idx-1][1]} -->
                                <div class="ins-hero-act-pane{active_cls}" data-act="{idx}">
                                    <h1 class="display-3 fw-bold text-white mb-3 ins-title-balance">
                                        {act['headline']}
                                    </h1>
                                    <p class="lead text-secondary mb-4 col-lg-11 p-0">
                                        {act['desc']}
                                    </p>
                                    <div class="d-flex flex-column flex-sm-row flex-wrap gap-3 mb-4">
                                        <a href="{p_href}" class="btn btn-primary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                            <span>{p_text}</span>
                                            <svg class="ph-duotone ph-{p_icon} ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-{p_icon}"/></svg>
                                        </a>
                                        <a href="{s_href}" class="btn btn-outline-secondary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                            <svg class="ph-duotone ph-{s_icon} ph-sm text-{s_color}"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-{s_icon}"/></svg>
                                            <span>{s_text}</span>
                                        </a>
                                    </div>
                                </div>""")
    acts_html = "\n\n".join(act_panes)

    # Lineage / Footer badges
    lineage_items = []
    for title, *badges in data["lineage"]:
        lineage_items.append(f'<span class="font-monospace small text-secondary text-uppercase">{title}</span>')
        for b in badges:
            lineage_items.append(f'<span class="badge bg-secondary bg-opacity-25 text-white">{b}</span>')
    lineage_html = """                                <div class="d-flex flex-wrap align-items-center gap-2 pt-3 border-top border-secondary border-opacity-25">
                                    """ + "\n                                    ".join(lineage_items) + "\n                                </div>"

    return f"""                            <div class="col-lg-6">
{back_html}{top_badge_html}

{pills_html}

{acts_html}

{lineage_html}
                            </div>"""

def upgrade_file(filename, pages_keys):
    filepath = os.path.join(VIEWS_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    modified_count = 0
    for key in pages_keys:
        data = PAGES_DATA[key]
        marker = f"<!-- Right Column: Sovereign Enterprise 3D Cockpit UI ({data['cockpit_title']}) -->"
        pos = content.find(marker)
        if pos == -1:
            print(f"[-] Marker not found for {key} in {filename}: {marker}")
            continue

        # Find the preceding <div class="col-lg-6"> (or col-lg-7 if old)
        col_start = content.rfind('<div class="col-lg-6">', 0, pos)
        if col_start == -1:
            col_start = content.rfind('<div class="col-lg-7">', 0, pos)
        if col_start == -1:
            print(f"[-] col_start not found for {key} in {filename}")
            continue

        # Find the closing </div> right before the marker
        col_end = content.rfind('</div>', col_start, pos)
        if col_end == -1:
            print(f"[-] col_end not found for {key} in {filename}")
            continue
        col_end += len('</div>')

        old_left = content[col_start:col_end]
        new_left = render_left_column(data).strip()

        content = content[:col_start] + new_left + content[col_end:]
        print(f"[+] Upgraded {key} in {filename}")
        modified_count += 1

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved {filename} ({modified_count} pages updated)\n")

if __name__ == "__main__":
    print("Upgrading Left Columns for all 12 remaining heroes...")
    upgrade_file("platform_solutions.xml", ["graph", "idp", "trade", "fsm"])
    upgrade_file("industries.xml", ["logistics", "pharma", "energy", "fsm_ind"])
    upgrade_file("resources_about_demo.xml", ["resources", "pricing", "about", "demo"])
    print("All 12 heroes successfully upgraded with 4-Act Storyboard Panes & Pill Navigators!")
