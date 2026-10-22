/**
 * ============================================================================
 * INNORIA ENTERPRISE SOVEREIGN I18N UNIFIED FRAMEWORK & PRIORITY QUOTE ENGINE
 * Asset: enterprise/insilos_website/static/src/js/innoria_i18n_unified.js
 * Scope: innoria.com Public Website, AI Concierge & Customer Portal
 *
 * Architecture:
 * - Unified Semantic Phrase & Block Translation Engine (Zero word-by-word translation)
 * - Attribute-driven translation ([data-i18n-en], [data-i18n-vi], [data-i18n-placeholder-en/vi])
 * - Whitespace-normalized block phrase dictionary (VI <-> EN) with 240+ executive phrases
 * - Real-time DOM MutationObserver for OWL & dynamic components
 * - Live Priority File Attachment feedback for Quote Request / RFP / SRS / BoQ uploads
 * ============================================================================
 */

(function (window, document) {
    "use strict";

    // ------------------------------------------------------------------------
    // 1. COMPREHENSIVE ENTERPRISE SEMANTIC PHRASE DICTIONARY (VI -> EN)
    //    Strictly phrase/sentence-level semantic translation — NEVER word-by-word
    // ------------------------------------------------------------------------
    const INNORIA_SEMANTIC_PHRASES = {
        // --- NAVBAR & TOPBAR ---
        "Sản Phẩm": "Products",
        "Nền Tảng": "Platform",
        "Giải Pháp": "Solutions",
        "Ngành Nghề": "Industries",
        "Về Innoria": "About Innoria",
        "Tài Nguyên": "Resources",
        "Bảng Giá": "Pricing",
        "Liên Hệ": "Contact",
        "Liên hệ": "Contact us",
        "Đăng Nhập": "Sign in",
        "Đăng nhập": "Sign in",
        "Đăng Xuất": "Sign Out",
        "Tài khoản": "Account",
        "Hồ sơ & Cổng Portal": "Profile & Customer Portal",
        "Hệ thống ERP / Apps": "ERP System / Apps",
        "Cổng Khách Hàng": "Customer Portal",
        "Yêu Cầu Demo": "Request Demo",
        "Yêu Cầu Live Demo": "Request Live Demo",
        "Tham Vấn Kiến Trúc 3 Giờ": "3-Hour Architecture Advisory",
        "Đặt Lịch Tham Vấn": "Schedule Advisory",
        "Trung Tâm Điều Hành": "Operations Center",
        "Tìm kiếm giải pháp, tài liệu...": "Search solutions, documentation...",

        // --- MEGAMENU: PRODUCTS, PLATFORM & SOLUTIONS ---
        "Xuất Nhập Khẩu & Hải Quan": "Import-Export & Customs",
        "Đối Chiếu Chứng Từ XNK": "Trade Document Reconciliation",
        "Đối chiếu PO, Invoice, Packing List và Tờ khai hải quan": "Automated 4-way matching across PO, Invoice, Packing List, and Customs Declarations",
        "Quản Trị Xuất Xứ C/O": "Certificate of Origin (C/O) Governance",
        "Kiểm soát quy tắc xuất xứ BOM và cấp bộ hồ sơ C/O chuẩn": "Verify BOM regional value content (RVC/CTC) and generate compliant C/O dossiers",
        "Thương Mại Hóa Chất": "Chemical Trade Compliance",
        "Chuẩn hóa mã định danh CAS và giấy phép tiền chất tự động": "Automated CAS registry verification and chemical precursor import licensing",
        "Vận Hành & An Toàn Kỹ Thuật": "Operations & Technical Safety",
        "Giấy Phép e-PTW & LOTO": "Digital e-PTW & LOTO Isolation",
        "Cô lập nguồn năng lượng van điện LOTO và ký duyệt số e-PTW": "Zero-energy LOTO valve isolation verification and digital Permit-to-Work sign-off",
        "Nhật Ký & Bàn Giao Ca": "Operations Logbook & Shift Handover",
        "Nhật ký ca vận hành tự động và ký nhận bàn giao việc ca": "Structured digital shift logbooks and accountable shift-to-shift handover sign-offs",
        "Quản Trị An Toàn EHS": "EHS Safety & CAPA Governance",
        "Quản trị rủi ro HSE hiện trường và hành động phòng ngừa CAPA": "Field HSE hazard tracking and closed-loop Corrective & Preventive Action (CAPA)",
        "Forwarder & Chuỗi Cung Ứng Liền Kề": "Freight Forwarding & Adjacent Supply Chain",
        "Kiểm Soát Forwarder": "Freight Forwarder Cost Control",
        "Tự động sinh Jobfile từ B/L và đối soát biểu phí forwarder": "Auto-generate Jobfiles from B/L and audit freight forwarder tariff surcharges",
        "Chuỗi Cung Ứng Ngành": "Industrial Supply Chain Orchestration",
        "Hợp nhất chuỗi cung ứng công nghiệp và điều phối liên bến cảng": "Unify industrial supply chain execution and multi-terminal port dispatch",
        "Tài Chính Kế Toán": "Financial & Statutory Accounting",
        "Hệ thống tài khoản Thông tư 200, quyết toán thuế minh bạch": "Circular 200/2014 chart of accounts, IFRS mapping, and transparent tax reconciliation",
        "Mua Hàng & Đấu Thầu": "Procurement & Strategic Sourcing",
        "Khóa Biên Lãi": "Margin Lock",
        "Đối soát PO, hóa đơn và biên bản giao hàng 3 chiều chuẩn": "Strict 3-way matching across Purchase Orders, GRNs, and E-Invoices",
        "Công Nghệ Tích Hợp Thông Minh": "Smart Industrial Integrations",
        "Bảo Trì RCM Dự Đoán": "RCM Predictive Maintenance",
        "Cảnh báo rung động trục quay trước 14 ngày xảy ra sự cố": "Detect rotary shaft harmonic anomalies 14 days prior to mechanical failure",
        "Tháp Vận Tải Logistics": "Logistics Fleet & Depot Control Tower",
        "Điều phối xe rơ-moóc liên cảng, kiểm soát mức tiêu hao dầu": "Inter-port prime mover dispatch, container depot telemetry, and fuel consumption audit",
        "Hải Quan & Chứng Từ XNK": "Customs & Trade Documentation AI",
        "AI-OCR chứng từ đa thể thức, đối soát luồng tờ khai VNACCS": "Multimodal AI-OCR document extraction and automated VNACCS declaration cross-check",
        "An Toàn Lao Động HSE": "Workplace HSE Vision AI",
        "Thị giác máy tính phát hiện vi phạm mũ bảo hộ, giấy phép e-PTW": "Real-time computer vision PPE compliance detection and digital e-PTW enforcement",
        "Quản Trị Sản Xuất MES & BOM Đa Tầng": "MES Shopfloor Execution & Multi-Level BOM",
        "Hệ thống điều độ phân xưởng MES trực quan, cân bằng phụ tải máy cắt Laser Fiber CNC và theo dõi chi phí lệnh sản xuất.": "Visual MES shopfloor scheduling, CNC Fiber Laser load balancing, and real-time work order costing.",
        "Khám Phá Giải Pháp": "Explore Solutions",
        "Khám Phá Nền Tảng": "Explore The Platform",

        // --- HERO SLIDE 0: GRC & COMPLIANCE INTELLIGENCE ---
        "Công Nghệ Cho Vận Hành Được Kiểm Soát & Tuân Thủ.": "Technology for Controlled & Compliant Enterprise Operations.",
        "Công Nghệ Cho Vận Hành Được Kiểm Soát & Tuân Thủ. Technology for Controlled, Compliant Operations": "Technology for Controlled & Compliant Enterprise Operations",
        "Lớp kiểm soát độc lập nằm giữa dữ liệu vận hành và các nghĩa vụ thực tế của doanh nghiệp: Kết nối dữ liệu · Kiểm tra theo quy tắc · Xử lý ngoại lệ · Điều phối hành động · Lưu vết bằng chứng pháp lý.": "An independent governance layer bridging operational data and statutory enterprise obligations: Data Ingestion · Deterministic Rule Validation · Exception Handling · Action Orchestration · Tamper-Evident Audit Trails.",
        "Đủ Chứng Từ": "Complete Dossiers",
        "Đúng Nội Dung": "Verified Content",
        "Đúng Quy Định": "Statutory Compliance",
        "Đúng Bên Liên Quan": "Authorized Stakeholders",
        "Đúng Thời Điểm": "Real-Time SLA",
        "Bất Biến Audit Trail": "Immutable Audit Trail",
        "Trải Nghiệm Live Proof-of-Concept 3 Giờ": "Experience 3-Hour Live Proof-of-Concept",
        "Khám Phá Data Fabric Studio": "Explore Data Fabric Studio",
        "TỐC ĐỘ TRIỂN KHAI": "DEPLOYMENT VELOCITY",
        "Nhanh Gấp 10x": "10x Faster Rollout",
        "NỢ KỸ THUẬT": "TECHNICAL DEBT",
        "Triệt Tiêu Nợ Kỹ Thuật": "Zero Legacy Bloat",
        "CHUẨN KẾT NỐI": "INTEGRATION STANDARD",
        "UPTIME CAM KẾT": "GUARANTEED UPTIME",

        // --- HERO SLIDE 1: AUTONOMOUS AI SWARM ---
        "Mạng Lưới Tác Nhân AI Doanh Nghiệp": "Enterprise Autonomous AI Agent Swarm",
        "Cụm Tác Nhân AI Đa Luồng Tự Chủ Cấp Doanh Nghiệp": "Enterprise Multi-Agent Autonomous Intelligence",
        "Mạng Lưới Tác Nhân Nhận Thức & Thực Thi Quy Trình": "Cognitive Agent Swarm & Workflow Execution Fabric",
        "Chuyển dịch từ phần mềm thụ động sang Trí tuệ Vận hành Tự động (Autonomous Enterprise Operations): Mạng lưới 16 tác nhân AI nhận thức Clef DAG kết hợp thị giác máy tính VLM See-Detect-Analyze-Adapt với độ trễ suy luận dưới 180ms.": "Transition from passive software to Autonomous Enterprise Operations: A 16-node cognitive Clef DAG agent swarm paired with real-time See-Detect-Analyze-Adapt VLM vision under 180ms p95 latency.",
        "16 Tác Nhân AI Tự Trị": "16 Autonomous AI Agents",
        "Hệ Thống Thị Giác VLM Thời Gian Thực": "Real-Time VLM Computer Vision",
        "Chu Trình Nhận Thức Clef DAG": "Clef DAG Cognitive Graph",
        "Cổng Kiểm Soát Chống Ảo Giác AI": "Zero-Hallucination Entailment Gate",
        "Xem Thực Nghiệm AI Swarm": "View AI Swarm Live Benchmarks",
        "ĐỘ CHÍNH XÁC VLM": "VLM ACCURACY",
        "99.8% Nhận Diện": "99.8% Precision",
        "ĐỘ TRỄ SUY LUẬN P95": "P95 INFERENCE LATENCY",
        "AGENT TỰ HÀNH": "AUTONOMOUS AGENTS",
        "16 Nút Tự Trị (Nodes)": "16 Sovereign Nodes",
        "BẢO MẬT HẠ TẦNG": "INFRASTRUCTURE SECURITY",
        "AI Cục Bộ Biệt Lập (Air-Gapped)": "Air-Gapped On-Premise AI",

        // --- HERO SLIDE 2: INSILOS ERP ---
        "Lõi Vận Hành Doanh Nghiệp Tự Hành": "Autonomous Enterprise Core ERP",
        "Hệ Thống Điều Hành Doanh Nghiệp Tự Trị Toàn Diện": "Comprehensive Autonomous Enterprise Operating System",
        "Lõi Vận Hành INSILOS ERP Chuẩn Quốc Tế": "Global-Grade INSILOS ERP Operational Core",
        "Chuyển dịch từ phần mềm thụ động sang Trí tuệ Vận hành Tự động (Autonomous Enterprise Operations): Lõi ERP hợp nhất chuỗi cung ứng SD-MM-PP-FI/CO, tối ưu chi phí sở hữu -50% TCO, tự động hóa khớp chứng từ 3 chiều chuẩn Thông tư 200 và Nghị định 123.": "Transition from passive software to Autonomous Enterprise Operations: Unified SD-MM-PP-FI/CO ERP core cutting 3-year TCO by 50% with automated 3-way matching compliant with Circular 200 and Decree 70/2025 (1C26TAA).",
        "Quản Trị Chuỗi Toàn Diện SD - MM - PP - FI/CO": "End-to-End SD - MM - PP - FI/CO Core",
        "Đối Chiếu Chứng Từ 3 Chiều Tự Động": "Automated 3-Way Document Matching",
        "Điều Độ Xưởng CNC (MES) & Đa Định Mức BOM": "CNC Shopfloor MES & Multi-Level BOM",
        "Chuẩn Hóa NĐ 70/2025 (1C26TAA) & VAS 200": "Decree 70/2025 (1C26TAA) & VAS 200 Compliant",
        "Khám Phá Lõi INSILOS ERP": "Explore INSILOS ERP Core",
        "THỜI GIAN TRIỂN KHAI": "TIME TO GO-LIVE",
        "30 Ngày Go-Live": "30-Day Rapid Go-Live",
        "CHI PHÍ SỞ HỮU TCO": "TOTAL COST OF OWNERSHIP",
        "-50% So Với Cũ": "-50% vs. Legacy ERP",
        "TUÂN THỦ PHÁP LÝ": "STATUTORY COMPLIANCE",
        "TT 200 & NĐ 123": "VAS 200 & E-Invoice",
        "CƠ SỞ DỮ LIỆU": "DATABASE ENGINE",
        "PostgreSQL Tự Chủ": "Sovereign PostgreSQL",

        // --- HERO SLIDE 3: ENTERPRISE TRUST & SECURITY ---
        "An Toàn & Phòng Thủ Chủ Quyền": "Sovereign Security & Cryptographic Defense",
        "Hạ Tầng Mật Mã & Phòng Thủ Cấp Chủ Quyền": "Sovereign Cryptographic Infrastructure & Cyber Defense",
        "Sổ Cái Bất Biến & Bảo Mật Dữ Liệu Cấp Tập Đoàn": "Immutable Audit Ledger & Enterprise Data Sovereignty",
        "Chuyển dịch từ phần mềm thụ động sang Trí tuệ Vận hành Tự động (Autonomous Enterprise Operations): Mạng lưới chuỗi giá trị phi tập trung, định danh số DID, sổ cái bất biến chống giả mạo và chứng minh không tiết lộ tri thức (Mã Hóa Zero-Knowledge Proofs).": "Transition from passive software to Autonomous Enterprise Operations: Decentralized value verification, sovereign DID identity, tamper-evident Merkle ledgers, and Zero-Knowledge Proof cryptographic attestation.",
        "Hệ Lõi Biệt Lập Mạng Air-Gapped": "Air-Gapped Sovereign Core",

        // --- HOMEPAGE & /CONTACTUS QUOTE REQUEST + PRIORITY FILE UPLOAD ---
        "Hội Đồng Kiến Trúc Sư Trưởng": "Principal Solutions Architecture Council",
        "Khởi Tạo Đánh Giá Kiến Trúc & Yêu Cầu Báo Giá Cấp Điều Hành (180 Phút)": "Initiate Executive Architecture Review & Custom Quote Request (180 Minutes)",
        "Phiên thẩm định kỹ thuật chuyên sâu trực tiếp cùng Giám Đốc Công Nghệ & Kiến Trúc Sư Trưởng Innoria: Phân tích kiến trúc hiện hữu, bóc tách dự toán chi phí và xác lập bản thiết kế mục tiêu khả thi trong 72 giờ.": "In-depth technical evaluation directly with Innoria's CTO & Chief Solutions Architect: Assess current architecture, break down project cost estimation, and deliver an actionable target blueprint within 72 hours.",
        "Tham vấn kiến trúc 1:1 trực tiếp cùng CTO & Solution Architect": "1-on-1 architecture consultation directly with CTO & Solution Architect",
        "Đính kèm hồ sơ dự án (RFP/SRS/BoQ) nhận Báo Giá Ưu Tiên trong 2 giờ": "Attach project dossiers (RFP/SRS/BoQ) for Fast-Track Priority Quote within 2 hours",
        "Ký kết thỏa thuận bảo mật NDA song phương tự động": "Automated bilateral Non-Disclosure Agreement (NDA) execution",
        "Phiếu Yêu Cầu Báo Giá & Đánh Giá Kiến Trúc": "Executive Quote Request & Architecture Assessment",
        "✓ Đã Tiếp Nhận Yêu Cầu Báo Giá & Hồ Sơ Dự Án Thành Công!": "✓ Quote Request & Project Dossier Successfully Received!",
        "⚡ ƯU TIÊN CAO (SLA < 2 GIỜ · ĐÃ ĐÍNH KÈM FILE)": "⚡ FAST-TRACK PRIORITY (SLA < 2H · FILE ATTACHED)",
        "Họ và tên & Chức danh điều hành *": "Full Name & Executive Title *",
        "Tên doanh nghiệp / Tổ chức": "Company / Organization Name",
        "Email doanh nghiệp chính thức *": "Official Corporate Email *",
        "Số điện thoại liên hệ trực tiếp *": "Direct Contact Phone *",
        "Hiện trạng hạ tầng & Điểm nghẽn cấp bách cần giải quyết": "Current Infrastructure & Critical Bottlenecks to Resolve",
        "📎 Đính Kèm Tài Liệu Dự Án (RFP / SRS / BoQ / Sơ Đồ Kiến Trúc)": "📎 Attach Project Documents (RFP / SRS / BoQ / Architecture Specs)",
        "⚡ ƯU TIÊN BÁO GIÁ NHANH (< 2 GIỜ)": "⚡ FAST-TRACK QUOTE PRIORITY (< 2H SLA)",
        "Gửi Yêu Cầu Báo Giá & Đánh Giá Kiến Trúc": "Submit Quote Request & Architecture Review",
        "Yêu Cầu Báo Giá & Đặt Lịch Tham Vấn Kiến Trúc": "Request a Custom Quote & Executive Architecture Consultation",
        "Đính kèm tài liệu dự án (RFP, SRS, BoQ, Sơ đồ kiến trúc) để được kích hoạt luồng Báo Giá Ưu Tiên (Fast-Track Priority SLA < 2 giờ làm việc) từ Hội đồng Kiến trúc sư Giải pháp Innoria.": "Attach your project documents (RFP, SRS, BoQ, Architecture Blueprint) to activate our Fast-Track Priority Quote Desk (SLA < 2 business hours) with Innoria Principal Solutions Architects.",
        "📎 Đính Kèm Hồ Sơ Dự Án (RFP, SRS, BoQ, Bảng Khối Lượng, Sơ Đồ Kiến Trúc)": "📎 Attach Project Dossier (RFP, SRS, BoQ, Bill of Quantities, Architecture Specs)",
        "Đính kèm file giúp đội ngũ Kiến trúc sư Giải pháp bóc tách khối lượng chính xác và gửi Báo Giá Nhanh trong vòng 2 giờ làm việc (Hỗ trợ PDF, Word, Excel, PowerPoint, ZIP, Ảnh tối đa 25MB/file).": "Uploading your project files enables our Solutions Architects to size your scope accurately and deliver a Fast-Track Quote within 2 business hours (Supports PDF, DOCX, XLSX, PPTX, ZIP, Images up to 25MB/file).",
        "Gửi Yêu Cầu Báo Giá & Tham Vấn Kiến Trúc (SLA < 2h Khi Đính Kèm File)": "Submit Quote Request & Architecture Consultation (Fast-Track < 2h SLA with File)",

        // --- /REQUEST-DEMO WIZARD ---
        "BƯỚC 1: THÔNG TIN DOANH NGHIỆP & LIÊN HỆ": "STEP 1: ENTERPRISE PROFILE & CONTACT",
        "Họ và tên *": "Full Name *",
        "Email công việc *": "Work Email *",
        "Tên doanh nghiệp *": "Company Name *",
        "Chức danh": "Job Title",
        "Số điện thoại": "Phone Number",
        "Tiếp Theo: Trọng Tâm Vận Hành (Bước 2/3)": "Next: Operational Focus (Step 2/3)",
        "BƯỚC 2: TRỌNG TÂM VẬN HÀNH & HỆ THỐNG HIỆN HỮU": "STEP 2: OPERATIONAL FOCUS & EXISTING SYSTEMS",
        "Ngành *": "Industry *",
        "Use case ưu tiên *": "Priority Use Case *",
        "Quy mô nhân sự": "Company Size",
        "Hệ thống Core ERP": "Core ERP System",
        "Tiến độ triển khai": "Deployment Timeline",
        "Quay Lại": "Back",
        "Tiếp Theo: Đặt Lịch 1-1 & Đính Kèm Hồ Sơ (Bước 3/3)": "Next: 1-on-1 Scheduling & File Upload (Step 3/3)",
        "BƯỚC 3: BỐI CẢNH DỰ ÁN, ĐÍNH KÈM TÀI LIỆU & XÁC NHẬN": "STEP 3: PROJECT CONTEXT, PRIORITY FILE ATTACHMENT & CONFIRMATION",
        "Bối cảnh hoặc bài toán cần giải quyết": "Project Context or Business Challenge",
        "📎 Đính Kèm Hồ Sơ Yêu Cầu Báo Giá (RFP / SRS / BoQ / Sơ Đồ Kiến Trúc)": "📎 Attach Quote Request Documents (RFP / SRS / BoQ / Architecture Specs)",
        "⚡ ƯU TIÊN PHẢN HỒI NHANH (< 2 GIỜ)": "⚡ FAST-TRACK PRIORITY (< 2H SLA)",
        "Gửi Yêu Cầu Demo & Nhận Báo Giá": "Submit Demo & Quote Request",
        "Cam kết bảo mật dữ liệu doanh nghiệp. Không chia sẻ cho bên thứ ba. Tuân thủ tuyệt đối Nghị định 13/2023/NĐ-CP.": "Enterprise data confidentiality guaranteed. Zero third-party sharing. Strict compliance with Decree 13/2023/ND-CP.",

        // --- AI CONCIERGE & CUSTOMER PORTAL ---
        "📎 Đính kèm Tài liệu Dự án (RFP / SRS / BoQ)": "📎 Attach Project Documents (RFP / SRS / BoQ)",
        "⚡ ƯU TIÊN BÁO GIÁ < 2 GIỜ": "⚡ FAST-TRACK QUOTE < 2H SLA",
        "Dịch vụ & Giải pháp quan tâm": "Target Solution & Service Scope",
        "Yêu cầu kỹ thuật, phạm vi tích hợp hoặc lộ trình dự kiến": "Technical Scope, Integration Requirements & Target Timeline",
        "Cổng Bảo Mật Chống Spam, Fake Contact & Tấn Công": "Anti-Spam, Contact Verification & WAF Security Shield",
        "1. Báo giá & SOW": "1. Quotations & SOW",
        "2. Chấm công Kỹ sư": "2. Engineer Timesheets",
        "3. Hóa đơn Nháp & 1C26TAA": "3. Draft & 1C26TAA E-Invoices",
        "4. Trợ lý AI & Customer Care SLA": "4. AI Copilot & Customer Care SLA",
        "Gửi Yêu Cầu Giải Trình": "Ask AI Copilot",
        "Gửi Yêu Cầu Hỗ Trợ Kỹ Thuật SLA & Đối Soát AL2C-INV-103": "Submit Technical SLA Support & AL2C-INV-103 Reconciliation Request",
        "Gửi Yêu Cầu Hỗ Trợ & Cấp Mã Theo Dõi SLA": "Submit Support Request & Issue SLA Tracking Code",

        // --- MERGED FULL-PAGE SEMANTIC PHRASE CORPUS (SWARM PARALLEL SYNTHESIS) ---
        "Vận Hành & Kỹ Thuật": "Operations & Engineering",
        "Forwarder & Chuỗi Cung Ứng": "Freight Forwarding & Supply Chain",
        "Jobfile Tự Động": "Automated Freight Jobfile",
        "MES Xưởng Cơ Khí": "Precision Mechanical MES",
        "Kho Vận Thông Minh WMS": "Intelligent Warehouse Management (WMS)",
        "Kế Toán Tài Chính TT200": "Circular 200 Financial Accounting",
        "Phiên Tham Vấn Kiến Trúc Chiến Lược 3 Giờ Miễn Phí": "Complimentary 3-Hour Strategic Architecture Consultation",
        "Khởi Tạo Đánh Giá Kiến Trúc": "Initiate Architecture Assessment",
        "Cấp Điều Hành 180 Phút": "180-Minute Executive Session",
        "Phiên thẩm định kỹ thuật chuyên sâu độc lập kéo dài 180 phút giữa Ban Lãnh Đạo Kỹ Thuật của quý doanh nghiệp và Hội Đồng Kiến Trúc Sư Trưởng Innoria. Không bán hàng. Không slide quảng cáo. Trực diện vào điểm nghẽn và giải pháp.": "An intensive, independent 180-minute technical evaluation between your engineering leadership and the INNORIA Chief Architecture Council. Zero sales pitches. No marketing slides. Direct focus on bottlenecks and actionable solutions.",
        "Phiên tư vấn kiến trúc ban đầu hoàn toàn miễn phí. Các Kiến trúc sư Giải pháp Trưởng của chúng tôi làm việc trực tiếp cùng ban lãnh đạo doanh nghiệp nhằm loại bỏ rủi ro đầu tư công nghệ, thiết lập hàng rào chủ quyền dữ liệu và xây dựng lộ trình thực thi khả thi trong 90 ngày.": "Initial architecture consultation is completely complimentary. Our Principal Solution Architects work directly with enterprise executives to de-risk technology investments, establish sovereign data boundaries, and chart an actionable 90-day execution roadmap.",
        "Đặt Lịch Phiên Làm Việc Chiến Lược": "Schedule Strategic Working Session",
        "Cam Kết Phản Hồi Trong 2 Giờ": "2-Hour SLA Response Guarantee",
        "Bảo Mật Thỏa Thuận NDA Song Phương": "Bilateral NDA Confidentiality",
        "100% Chủ Quyền Mã Nguồn & Dữ Liệu": "100% Data & Source Code Sovereignty",
        "TIẾP NHẬN TRỰC TIẾP": "DIRECT EXECUTIVE INTAKE",
        "Bàn Tiếp Nhận Kiến Trúc Doanh Nghiệp": "Enterprise Architecture Intake Desk",
        "Cam Kết Phản Hồi SLA Trong 2 Giờ": "Guaranteed 2-Hour SLA Response",
        "Mọi yêu cầu từ doanh nghiệp đều được chuyển giao tới Kiến trúc sư Trưởng trong vòng 120 phút trong giờ làm việc.": "Every enterprise inquiry is escalated directly to a Chief Architect within 120 business minutes.",
        "Thỏa Thuận Bảo Mật NDA Trước Khi Khảo Sát Kỹ Thuật": "Mutual NDA Executed Prior to Technical Discovery",
        "Thỏa thuận bảo mật song phương (Bilateral NDA) được ký kết trước khi bất kỳ dữ liệu, mã nguồn hoặc hạ tầng nội bộ nào được chia sẻ.": "A bilateral non-disclosure agreement (NDA) is executed before any internal data, source code, or infrastructure topology is shared.",
        "Cam Kết Không Ràng Buộc Nhà Cung Cấp (Zero Vendor Lock-In)": "Zero Vendor Lock-In Commitment",
        "Toàn quyền chủ quyền. Doanh nghiệp nắm giữ 100% quyền sở hữu logic nghiệp vụ, lược đồ dữ liệu, mô hình tùy biến và mã nguồn tài sản.": "Absolute sovereignty. Enterprises retain 100% proprietary ownership of business logic, database schemas, custom models, and source code assets.",
        "Bàn Làm Việc Doanh Nghiệp:": "Enterprise Working Desk:",
        "BẢN VẼ THIẾT KẾ KIẾN TRÚC": "ENTERPRISE ARCHITECTURE BLUEPRINT",
        "Ba Giờ. Một Lộ Trình Ra Quyết Định Kiến Trúc Rõ Ràng.": "Three Hours. One Decisive Architectural Roadmap.",
        "Phiên làm việc chiến lược chuyên sâu, nhịp độ cao được thiết kế riêng cho các CIO, CTO, Giám đốc Chuyển đổi số và Hội đồng Đổi mới Doanh nghiệp.": "A high-velocity, deep-dive strategic session purpose-built for CIOs, CTOs, Chief Digital Officers, and Enterprise Innovation Boards.",
        "Sprint Toàn Diện 180 Phút": "Comprehensive 180-Minute Sprint",
        "01 / 45 PHÚT": "01 / 45 MIN",
        "CHẨN ĐOÁN": "DIAGNOSTIC",
        "Xác Định Bài Toán & Thống Nhất Mục Tiêu": "Problem Formulation & Strategic Alignment",
        "Bóc tách các điểm nghẽn vận hành, thao tác thủ công, rào cản tuân thủ pháp lý, sự ma sát liên phòng ban và các chỉ số chuyển đổi cấp Hội đồng Quản trị.": "Deconstruct operational bottlenecks, manual friction, regulatory compliance barriers, cross-departmental silos, and Board-level transformation metrics.",
        "Kết Quả Bàn Giao:": "Deliverables:",
        "• Ma Trận Điểm Nghẽn & Luận Điểm Giá Trị": "• Bottleneck Matrix & Value Realization Thesis",
        "02 / 45 PHÚT": "02 / 45 MIN",
        "KHẢ THI": "FEASIBILITY",
        "Tính Khả Thi Kỹ Thuật & Kiểm Toán Hệ Thống": "Technical Feasibility & Systems Audit",
        "Đánh giá cấu trúc ERP/CRM hiện hữu (Legacy ERP, Monolithic ERP, Hệ CSDL & ERP Truyền Thống), nợ kỹ thuật lược đồ dữ liệu, mức độ sẵn sàng API, vùng an ninh on-premise và nghĩa vụ lưu trữ dữ liệu nội địa.": "Audit existing ERP/CRM topologies (Legacy ERP, Monolithic ERP, relational databases & legacy ERP systems), schema technical debt, API readiness, on-premise security enclaves, and sovereign data residency compliance.",
        "• Bảng Đánh Giá Khoảng Trống Tích Hợp & An Toàn": "• Integration Gap Analysis & Security Posture Assessment",
        "03 / 45 PHÚT": "03 / 45 MIN",
        "KIẾN TRÚC": "ARCHITECTURE",
        "Lộ Trình Kiến Trúc & Định Hình Tầm Nhìn": "Architecture Roadmap & Target Vision Formulation",
        "Tổng hợp kiến trúc mục tiêu theo phân hệ: Điều phối DIGIFORCE, cụm tác nhân MOJO AI, sổ cái bất biến MOJOVERSE và các đường ống dữ liệu phân tán với quyền kiểm soát chủ quyền.": "Synthesize target architecture modules: DIGIFORCE orchestration, MOJO AI agent swarms, MOJOVERSE immutable ledgers, and sovereign-controlled distributed data pipelines.",
        "• Sơ Đồ Cấu Trúc Kiến Trúc Cấp Cao": "• High-Level Architectural Topology Diagram",
        "04 / 45 PHÚT": "04 / 45 MIN",
        "THỰC THI": "EXECUTION",
        "Phạm Vi Thử Nghiệm & Cổng Ra Quyết Định": "Proof-of-Concept Scoping & Decision Gates",
        "Thiết lập ranh giới thử nghiệm khả thi MVP (Proof-of-Concept) tinh gọn từ 6 đến 8 tuần với tiêu chí nghiệm thu rõ ràng, ma trận phân bổ nguồn lực, nhịp độ sprint và chỉ số đo lường ROI.": "Define an agile 6-to-8-week Proof-of-Concept (PoC) boundary with definitive acceptance criteria, resource allocation matrices, sprint cadences, and measurable ROI benchmarks.",
        "• Kế Hoạch Sprint & Bản Thiết Kế PoC An Toàn": "• Sprint Execution Plan & Hardened PoC Blueprint",
        "TIẾP NHẬN DOANH NGHIỆP TRỰC TIẾP": "DIRECT ENTERPRISE INTAKE",
        "Đặt Lịch Phiên Tư Vấn Kiến Trúc 3 Giờ Miễn Phí.": "Book Your Complimentary 3-Hour Architecture Session.",
        "Hội đồng Giải pháp Kỹ thuật phân bổ trực tiếp Kiến trúc sư Trưởng chuyên ngành trước phiên làm việc.": "Our Principal Solutions Council assigns a dedicated Lead Domain Architect prior to your working session.",
        "Gửi thông tin chiến lược của quý doanh nghiệp bên dưới. Hội đồng giải pháp kỹ thuật của chúng tôi sẽ phân bổ đúng kiến trúc sư chuyên ngành trước khi tiến hành phiên làm việc.": "Submit your enterprise briefing below. Our Solutions Council will assign the appropriate domain architect prior to convening the working session.",
        "Quy Trình Tiếp Theo:": "Subsequent Engagement Workflow:",
        "Quy Trình Thẩm Định & Báo Giá 3 Bước:": "3-Step Architectural Appraisal & Quotation Workflow:",
        "Sàng Lọc Ngay Lập Tức:": "Immediate Triage & Intake:",
        "Xác nhận tiếp nhận và ký kết thỏa thuận bảo mật song phương NDA trong vòng 2 giờ làm việc.": "Intake confirmation and bilateral NDA execution finalized within 2 business hours.",
        "Khảo Sát Định Hướng:": "Discovery Alignment Call:",
        "Cuộc gọi ngắn 15 phút cùng Kiến trúc sư Trưởng để định hình chính xác phạm vi phiên tư vấn.": "A targeted 15-minute alignment call with a Principal Architect to delineate session scope.",
        "Cuộc gọi ngắn 15 phút cùng Kiến trúc sư Trưởng để định hình chính xác phạm vi phiên tư vấn & BoQ.": "A targeted 15-minute alignment call with a Principal Architect to delineate session scope and BoQ.",
        "Họp & Bàn Giao Kế Hoạch:": "Deep-Dive Session & Roadmap Delivery:",
        "Phiên làm việc chuyên sâu 3 giờ tổ chức trực tiếp (TP.HCM / Hà Nội / Đà Nẵng) hoặc qua phòng họp trực tuyến bảo mật quốc tế.": "A 3-hour deep-dive workshop hosted on-site (HCMC / Hanoi / Da Nang) or via secure virtual briefing suites.",
        "CAM KẾT SLA BÁO GIÁ": "QUOTATION SLA GUARANTEE",
        "< 2 Giờ Làm Việc": "< 2 Business Hours",
        "Khi đính kèm RFP / SRS / BoQ": "When RFP / SRS / BoQ attached",
        "CHỦ QUYỀN & AN NINH": "SOVEREIGNTY & SECURITY",
        "PHƯƠNG PHÁP LUẬN": "DELIVERY METHODOLOGY",
        "TUÂN THỦ ĐỊNH CHẾ": "STATUTORY COMPLIANCE",
        "Nghị định 70/2025 & 13/2023": "Decree 70/2025 & 13/2023",
        "Trao đổi trực tiếp với Hội đồng Chuyên gia:": "Direct correspondence with our Advisory Council:",
        "Quý đối tác muốn trao đổi trực tiếp qua thư điện tử? Vui lòng gửi email đến hội đồng chuyên gia tại": "Prefer direct executive correspondence? Reach our advisory council at",
        "ĐỊA ĐIỂM & HẠ TẦNG VẬN HÀNH CHỦ QUYỀN": "SOVEREIGN INFRASTRUCTURE & GLOBAL OPERATIONS",
        "Trụ Sở Kỹ Nghệ Tại Việt Nam. Triển Khai Đa Quốc Gia.": "Vietnam Engineering HQ. Multi-National Deployment.",
        "Vận hành từ trung tâm R&D tại TP. Hồ Chí Minh kết hợp hạ tầng đám mây chủ quyền Tier-3 và cổng hợp tác kỹ thuật trực tuyến cho khách hàng doanh nghiệp trong và ngoài nước.": "Operating from our flagship R&D Center in Ho Chi Minh City, backed by Tier-3 sovereign cloud infrastructure and secure online engineering portals for enterprise clients worldwide.",
        "TRỤ SỞ CHÍNH & TRUNG TÂM R&D": "HEADQUARTERS & R&D CENTER",
        "HOẠT ĐỘNG · 08:30 - 18:00 (GMT+7)": "OPERATIONS · 08:30 - 18:00 (GMT+7)",
        "TP. Hồ Chí Minh, Việt Nam": "Ho Chi Minh City, Vietnam",
        "Pháp nhân thương hiệu: INNORIA GROUP": "Brand Legal Entity: INNORIA GROUP",
        "Địa chỉ Tiếng Anh:": "Address (English):",
        "Địa chỉ Tiếng Việt:": "Address (Vietnamese):",
        "45 đường số 3, KDC Trung Sơn, Xã Bình Hưng, Huyện Bình Chánh, TP. Hồ Chí Minh.": "45 Street 3, Trung Son Residential Area, Binh Hung Commune, Binh Chanh District, Ho Chi Minh City.",
        "Định danh Hệ sinh thái:": "Ecosystem Identifier:",
        "Mở Bản Đồ Chỉ Đường": "Open Driving Directions",
        "TRUNG TÂM TƯ VẤN": "ADVISORY CENTER",
        "Hà Nội": "Hanoi",
        "Tư vấn Chuyển đổi số, Kiến trúc GRC & Chủ quyền Dữ liệu Doanh nghiệp phía Bắc.": "Enterprise Digital Transformation, GRC Architecture & Northern Sovereign Data Practice.",
        "Trọng tâm:": "Core Focus:",
        "ERP Doanh Nghiệp & Đám Mây Chủ Quyền": "Enterprise ERP & Sovereign Cloud",
        "KỸ NGHỆ & EDGE AI": "ENGINEERING & EDGE AI",
        "Đà Nẵng": "Da Nang",
        "Triển khai Hạ tầng Công nghiệp Miền Trung, Tích hợp PLC/SCADA & Thị giác Máy tính tại Biên.": "Central Vietnam Industrial Infrastructure Deployment, PLC/SCADA Integration & Edge Computer Vision.",
        "CỔNG B2B QUỐC TẾ": "INTERNATIONAL B2B PORTAL",
        "Cổng Hợp tác Kỹ thuật Quốc tế & Không gian Khách hàng B2B trực tuyến (/my) cho đối tác Nhật Bản & ASEAN.": "International Engineering Collaboration Portal & Dedicated B2B Client Space (/my) for Japan & ASEAN Enterprise Partners.",
        "Pháp nhân đăng ký hợp pháp:": "Registered Legal Entity:",
        "Mã số thuế:": "Tax ID / Corporate Registration:",
        "Email chính thức:": "Official Inquiries:",
        "Thành lập từ năm:": "Established:",
        "BẢO CHỨNG & QUẢN TRỊ DOANH NGHIỆP": "ENTERPRISE ASSURANCE & GOVERNANCE",
        "Cam Kết Không Ràng Buộc Công Nghệ Độc Quyền. Chủ Quyền Dữ Liệu Tối Cao.": "Zero Proprietary Lock-In Guarantee. Absolute Data Sovereignty.",
        "Tuân thủ nghiêm ngặt chuẩn mực kiểm soát thể chế, đáp ứng toàn diện tiêu chuẩn kiểm toán quốc tế cho các ngân hàng thương mại, tập đoàn công nghiệp và chuỗi cung ứng đa quốc gia.": "Rigorous institutional compliance adhering to international audit mandates for commercial banks, industrial conglomerates, and global supply chains.",
        "Tuân Thủ ISO 27001": "ISO 27001 Certified Compliance",
        "Hệ thống Quản lý An toàn Thông tin (ISMS) nghiêm ngặt quản trị kho mã nguồn, dữ liệu vận hành và các đường ống truyền dẫn.": "Strict Information Security Management System (ISMS) governing source repositories, operational data stores, and transmission pipelines.",
        "Kiểm Soát SOC 2 Type II": "SOC 2 Type II Attestation",
        "Nhật ký kiểm toán liên tục (Audit Trail), cơ chế cô lập môi trường thuê (Tenant Isolation) và phân quyền vai trò chuyên sâu, tự động quét lỗ hổng bảo mật cùng quy trình khắc phục sự cố sau thảm họa (Disaster Recovery).": "Continuous audit trails, strict multi-tenant isolation, granular role-based access controls, automated vulnerability scanning, and disaster recovery orchestration.",
        "Thỏa Thuận Bảo Mật Song Phương (NDA)": "Bilateral Non-Disclosure Agreement (NDA)",
        "Cam kết bảo mật pháp lý nghiêm ngặt được ký kết trước bất kỳ hoạt động khảo sát kỹ thuật, đánh giá kiến trúc hay thu nạp dữ liệu nào.": "Legally binding confidentiality agreements executed prior to any technical assessment, architectural discovery, or data ingestion.",
        "100% yêu cầu tư vấn từ ban lãnh đạo doanh nghiệp đều nhận được phản hồi phân tích sơ bộ từ Kiến trúc sư Trưởng trong vòng 2 giờ làm việc.": "100% of executive inquiries receive a preliminary architectural appraisal from a Principal Architect within 2 business hours.",
        "CHUẨN BỊ TRƯỚC PHIÊN LÀM VIỆC": "PRE-SESSION EXECUTIVE BRIEFING GUIDE",
        "Danh Mục Chuẩn Bị Cho Lãnh Đạo": "Executive Preparation Checklist",
        "Quý vị không cần phải chuẩn bị một tập hồ sơ yêu cầu (RFQ) dày 50 trang. Để đạt hiệu quả tối đa từ phiên làm việc 3 giờ, việc làm rõ 5 khía cạnh cốt lõi sau sẽ giúp định hình kiến trúc kỹ thuật chuẩn xác và nhanh chóng:": "You do not need a 50-page RFQ. To maximize executive ROI from the 3-hour session, clarifying these 5 strategic dimensions ensures precision architectural alignment:",
        "Những Thông Tin Cần Mang Đến:": "Recommended Discussion Inputs:",
        "Mục Tiêu Vận Hành Cốt Lõi:": "Core Strategic & Operational Mandates:",
        "1-2 điểm nghẽn vận hành lớn nhất hoặc mục tiêu tăng trưởng doanh thu thúc đẩy sáng kiến này.": "Top 1-2 critical operational bottlenecks or revenue growth objectives underwriting this initiative.",
        "Cấu Trúc Hệ Thống Hiện Hữu:": "Current Systems Architecture:",
        "Tổng quan về các hệ thống cốt lõi hiện có (Legacy ERP, Monolithic ERP, vi dịch vụ tự phát triển, nhà cung cấp đám mây).": "High-level inventory of mission-critical systems (Legacy ERP, Monolithic ERP, custom microservices, primary cloud/infra providers).",
        "Quy Chuẩn Quản Trị & Chủ Quyền:": "Governance, Risk & Sovereignty Mandates:",
        "Các tiêu chuẩn tuân thủ cụ thể (Quy định của Ngân hàng Nhà nước, Nghị định 13/2023/NĐ-CP, GDPR, HIPAA).": "Target compliance frameworks (State Bank of Vietnam regulations, Decree 13/2023/ND-CP, GDPR, HIPAA).",
        "Khung Thời Gian & Ngân Sách Dự Kiến:": "Target Timeline & Capital Horizon:",
        "Mốc thời gian mục tiêu triển khai thử nghiệm MVP và kỳ vọng mở rộng quy mô vận hành chính thức.": "Target milestones for MVP validation and full-scale operational production rollout.",
        "Đại Diện Ra Quyết Định:": "Executive Stakeholder Representation:",
        "Sự hiện diện của lãnh đạo công nghệ (CTO/Phó Giám đốc Kỹ thuật) và lãnh đạo điều hành (CIO/CEO/COO).": "Presence of technology leadership (CTO / VP of Engineering) alongside executive sponsors (CIO / CEO / COO).",
        "HỎI & ĐÁP DÀNH CHO LÃNH ĐẠO": "EXECUTIVE FAQ",
        "Các Câu Hỏi Thường Gặp": "Frequently Asked Questions",
        "1. Phiên làm việc chiến lược 3 giờ có thực sự hoàn toàn miễn phí và không ràng buộc?": "1. Is the 3-hour strategic consultation genuinely complimentary and non-binding?",
        "Hoàn toàn miễn phí và không đi kèm bất kỳ ràng buộc thương mại hay hợp đồng ràng buộc nào. Tại INNORIA, niềm tin của các nhà lãnh đạo doanh nghiệp bắt nguồn từ chất lượng phân tích kiến trúc thực chứng, thay vì những cam kết tiếp thị chung chung. Toàn bộ sơ đồ kiến trúc và lộ trình chuyển đổi số được xây dựng trong phiên làm việc sẽ hoàn toàn thuộc quyền sở hữu của quý doanh nghiệp.": "Completely complimentary and free of commercial obligations. At INNORIA, enterprise executive trust is earned through verifiable architectural rigor rather than generic marketing pledges. All architecture blueprints and digital transformation roadmaps produced during the session remain 100% proprietary to your enterprise.",
        "2. Thỏa thuận bảo mật thông tin (NDA) được ký kết như thế nào và vào thời điểm nào?": "2. How and when is the Non-Disclosure Agreement (NDA) executed?",
        "Thỏa thuận bảo mật thông tin song phương (Bilateral NDA) chuẩn doanh nghiệp của chúng tôi sẽ được ký số và gửi đến quý vị trong vòng 2 giờ làm việc sau khi tiếp nhận thông tin đăng ký. Chúng tôi cũng hoàn toàn sẵn sàng thẩm định và ký kết trên mẫu thỏa thuận NDA nội bộ của quý doanh nghiệp. Toàn bộ các cuộc thảo luận chiến lược, sơ đồ kiến trúc hiện tại và dữ liệu kinh doanh được chia sẻ trong phiên làm việc đều được pháp luật Việt Nam và quốc tế bảo hộ nghiêm ngặt theo diện bí mật kinh doanh.": "Our enterprise-standard bilateral NDA is digitally signed and dispatched within 2 business hours of intake. We are equally prepared to review and execute your corporate legal counsel's NDA template. All strategic discussions, architectural topologies, and proprietary business data disclosed during the engagement are strictly protected as trade secrets under Vietnamese and international law.",
        "3. INNORIA bảo đảm nguyên tắc không bị phụ thuộc nhà cung cấp (Zero Vendor Lock-In) như thế nào?": "3. How does INNORIA guarantee Zero Vendor Lock-In?",
        "Loại bỏ hoàn toàn rủi ro phụ thuộc nhà cung cấp (Zero Lock-In) là nguyên tắc kiến trúc bất biến cốt lõi của INNORIA. Mọi giải pháp xây dựng trên DIGIFORCE, MOJO AI, MOJOVERSE hay các vi dịch vụ tùy biến đều được đóng gói dưới dạng container tiêu chuẩn (Docker / Kubernetes / lược đồ PostgreSQL tiêu chuẩn). Quý doanh nghiệp sở hữu 100% logic nghiệp vụ, các mô hình AI tinh chỉnh riêng và lược đồ cơ sở dữ liệu. Quý vị có thể tự vận hành trên máy chủ vật lý on-premise, triển khai trên đám mây chủ quyền trong nước (Tier-3 Quốc Gia & Cloud Nội Địa), hoặc vận hành trên AWS/GCP/Azure với khả năng chuyển đổi mã nguồn linh hoạt tuyệt đối.": "Eliminating proprietary lock-in is a non-negotiable architectural invariant at INNORIA. Every solution built on DIGIFORCE, MOJO AI, MOJOVERSE, or custom microservices is packaged into open-standard containers (Docker / Kubernetes / standard PostgreSQL schemas). Enterprises retain 100% ownership of business logic, fine-tuned proprietary AI models, and database schemas. You maintain complete freedom to run on-premise on bare metal, deploy across national Tier-3 sovereign clouds, or host on AWS/GCP/Azure with seamless source portability.",
        "4. Quý doanh nghiệp sẽ nhận được những tài liệu bàn giao cụ thể nào sau phiên làm việc?": "4. What formal deliverables will our enterprise receive following the session?",
        "Trong vòng 48 giờ sau phiên làm việc 3 giờ, ban lãnh đạo doanh nghiệp sẽ nhận được Bộ Hồ Sơ Tóm Lược Kiến Trúc Doanh Nghiệp (Executive Architecture Briefing Pack) chính thức bao gồm:": "Within 48 hours of the 3-hour session, enterprise leadership receives a formal Executive Architecture Briefing Pack containing:",
        "Bảng Đánh Giá Khả Thi Kỹ Thuật & Khoảng Trống Hệ Thống:": "Technical Feasibility Assessment & Systems Gap Analysis:",
        "Đánh giá có hệ thống về khả năng tích hợp hệ thống hiện hữu (Legacy Systems), các điểm nghẽn cơ sở dữ liệu và mức độ sẵn sàng của dữ liệu.": "Systematic audit of legacy system integration boundaries, database bottlenecks, and data estate readiness.",
        "Bản Vẽ Kiến Trúc Mục Tiêu:": "Target Architecture Topology:",
        "Sơ đồ phân rã microservices đề xuất, luồng dữ liệu tác nhân AI và hạ tầng hợp nhất dữ liệu (Data Fabric).": "Modular microservices decomposition blueprint, AI agent swarming flows, and enterprise Data Fabric architecture.",
        "Bản Đặc Tả Phạm Vi Thử Nghiệm MVP:": "Proof-of-Concept (MVP) Scope Specification:",
        "Kế hoạch triển khai Sprint linh hoạt trọn gói từ 6 đến 8 tuần với phân bổ nguồn lực chi tiết, tiến độ thực hiện và các mốc đánh giá hoàn vốn ROI rõ ràng.": "Turnkey 6-to-8-week agile sprint delivery plan complete with resource allocation, delivery milestones, and definitive ROI realization metrics.",
        "Doanh nghiệp có nhu cầu triển khai theo thời hạn mua sắm khẩn cấp?": "Facing an accelerated procurement deadline?",
        "Yêu cầu phiên làm việc trực tiếp 60 phút với Kiến trúc sư Trưởng của chúng tôi.": "Request an expedited 60-minute direct briefing with our Chief Architect.",
        "Đặt Lịch Ưu Tiên Nhanh": "Expedited Priority Booking",
        "Hạ tầng công nghệ cấp chủ quyền cho doanh nghiệp lớn. Chúng tôi cung cấp nền tảng tự hành toàn diện dựa trên dữ liệu hợp nhất, quy trình vận hành tự động và bảo mật đa tầng, tuân thủ nghiêm ngặt các chuẩn mực quản trị rủi ro quốc tế ISO/IEC 27001 và SOC-2.": "Sovereign Enterprise Infrastructure for Leading Enterprises. Delivering an autonomous digital platform powered by unified data, cognitive automation, and defense-in-depth security strictly aligned with ISO/IEC 27001 and SOC-2 risk governance.",
        "Ultra AI Vision Công Nghiệp": "Ultra Industrial AI Vision",
        "Quản Trị ERP & Hóa Đơn Tự Động": "Enterprise ERP & Automated Invoicing",
        "Permit to Work & EHS Số": "Digital Permit to Work & EHS",
        "Chứng Nhận Xuất Xứ Số (e-CO)": "Digital Certificate of Origin (e-CO)",
        "Lịch Sử Phát Triển & Năng Lực 18 Năm": "18-Year Engineering Heritage & Capability",
        "KẾT NỐI": "CONNECT",
        "Liên hệ": "Contact us",
        "Đăng nhập": "Sign in",
        "Mã số DN (Tax ID): INNORIA-GROUP": "Enterprise Tax ID: INNORIA-GROUP",
        "45 đường số 3, KDC Trung Sơn, Xã Bình Hưng, Huyện Bình Chánh, TP. Hồ Chí Minh": "45 Street 3, Trung Son Residential Area, Binh Hung Commune, Binh Chanh District, Ho Chi Minh City",
        "Bản quyền © 2026 INNORIA | Hạ Tầng Công Nghệ Cấp Chủ Quyền Cho Doanh Nghiệp": "Copyright © 2026 INNORIA | Sovereign Enterprise Technology Infrastructure",
        "Định Danh Số Phi Tập Trung (DID)": "Decentralized Digital Identity (DID)",
        "Sổ Cái Bất Biến Truy Xuất Toàn Trình": "End-to-End Immutable Traceability Ledger",
        "Chứng Nhận Quốc Tế ISO/IEC 27001": "ISO/IEC 27001 International Certification",
        "Kiểm Tra Tiêu Chuẩn Bảo Mật": "Security Standards Compliance Audit",
        "TOÀN VẸN DỮ LIỆU": "DATA INTEGRITY",
        "100% Bất Biến (Invariance)": "100% Invariance & Immutability",
        "THỜI GIAN FINALITY": "SETTLEMENT FINALITY",
        "< 0.8s Chốt Khối": "< 0.8s Block Finality",
        "BẢO MẬT GIAO DỊCH": "TRANSACTION SECURITY",
        "Mã Hóa Zero-Knowledge": "Zero-Knowledge Cryptography",
        "TIÊU CHUẨN AN NINH": "SECURITY STANDARDS",
        "CHẾ ĐỘ 01 · FABRIC": "MODE 01 · FABRIC",
        "Kiến Trúc Dữ Liệu": "Data Architecture",
        "[Nền Tảng Đám Mây & Dữ Liệu]": "[Cloud Infrastructure & Data Platform]",
        "CHẾ ĐỘ 02 · NHẬN THỨC": "MODE 02 · COGNITIVE",
        "Thị Giác VLM & 16 Tác Nhân": "VLM Computer Vision & 16-Agent Swarm",
        "[Mạng Lưới AI Đa Tác Nhân]": "[Multi-Agent AI Network]",
        "CHẾ ĐỘ 03 · LÕI VẬN HÀNH": "MODE 03 · OPERATIONAL CORE",
        "ERP Tự Trị Toàn Chuỗi": "Autonomous End-to-End ERP",
        "[Hệ Thống INSILOS ERP]": "[INSILOS ERP Platform]",
        "CHẾ ĐỘ 04 · TÍN NHIỆM": "MODE 04 · TRUST",
        "Zero-Trust & Chuẩn DID": "Zero-Trust & DID Architecture",
        "[Bảo Mật & Tín Nhiệm]": "[Security & Enterprise Trust]",
        "HẠ TẦNG TIN CẬY · ĐƯỢC VẬN HÀNH BỞI CÁC TẬP ĐOÀN TÀI CHÍNH & CÔNG NGHIỆP TRỌNG YẾU": "TRUSTED INFRASTRUCTURE · POWERED BY LEADING FINANCIAL & INDUSTRIAL ENTERPRISES",
        "100 Quy Tắc Fit-to-Standard (Class A/B/C)": "100 Fit-to-Standard Governance Rules (Class A/B/C)",
        "7,886 Tài Liệu Data Room 9 Tầng Bảo Chứng SHA-256": "7,886 Data Room Documents with 9-Tier SHA-256 Attestation",
        "Kiến Trúc Đa Tầng": "Multi-Tier Enterprise Architecture",
        "Nền Tảng No-Code": "No-Code Application Platform",
        "App Studio · Thiết Kế Luồng Tự Động Hoá": "App Studio · Visual Workflow Automation",
        "Dịch Vụ Nền Tảng": "Core Platform Services",
        "Kiến Trúc Microservices · Bảo Mật Zero-Trust · CI/CD": "Microservices Architecture · Zero-Trust Security · CI/CD",
        "Trí Tuệ Nhân Tạo": "Enterprise Artificial Intelligence",
        "Generative AI · Explainable AI · Tương Tác Người-Máy": "Generative AI · Explainable AI · Human-Machine Teaming",
        "Kho Dữ Liệu & ERP Cốt Lõi": "Data Warehouse & Core ERP",
        "Lõi ERP · Quản Trị Rủi Ro GRC · Cảm Biến IIoT": "Core ERP · Enterprise GRC · Industrial IoT",
        "LỚP 1": "LAYER 1",
        "Xây dựng ứng dụng doanh nghiệp tốc độ cao qua giao diện kéo thả trực quan, tự sinh API REST/GraphQL chuẩn mực.": "Rapidly build enterprise applications via visual drag-and-drop interfaces with automated, standardized REST/GraphQL API generation.",
        "LỚP 2": "LAYER 2",
        "Kiến trúc Microservices độc lập, Quản trị bảo mật Zero-Trust, phân quyền RBAC/ABAC đa cấp và CI/CD tự động hoá.": "Autonomous Microservices Architecture, Zero-Trust Security Governance, Multi-Level RBAC/ABAC Access Control, and Automated CI/CD.",
        "Trí Tuệ Nhân Tạo (Enterprise AI)": "Artificial Intelligence (Enterprise AI)",
        "LỚP 3": "LAYER 3",
        "Generative AI, Explainable AI và Human-Machine Understanding hỗ trợ ra quyết định thời gian thực và tự động hoá.": "Generative AI, Explainable AI, and Human-Machine Understanding driving real-time decision intelligence and operational automation.",
        "LỚP 4": "LAYER 4",
        "Đồng bộ hoá nguồn dữ liệu đa dạng: ERP, GRC (Quản trị rủi ro), IIoT cảm biến và sổ cái phi tập trung hợp nhất.": "Synchronizing heterogeneous enterprise data sources: ERP, GRC, Industrial IoT sensors, and a unified decentralized ledger.",
        "LỚP 01 · APPLICATION DEVELOPMENT": "LAYER 01 · APPLICATION DEVELOPMENT",
        "Tổng Quan": "Overview",
        "Trao quyền cho các nhóm nghiệp vụ và kỹ sư phát triển phần mềm kiến tạo ứng dụng chuẩn doanh nghiệp với tốc độ gấp 10 lần. Nền tảng hỗ trợ kéo thả thiết kế biểu mẫu, mô hình dữ liệu động, quy trình phê duyệt đa cấp và tự động tạo REST / GraphQL APIs.": "Empowering business teams and software engineers to build enterprise-grade applications at 10x speed. The platform delivers drag-and-drop form builders, dynamic data modeling, multi-tier approval workflows, and automated REST / GraphQL API generation.",
        "App Studio Kéo Thả": "Visual Drag-and-Drop App Studio",
        "Tạo giao diện Web & Mobile Responsive, custom views không cần code lại.": "Design responsive Web & Mobile interfaces and custom views without rewriting code.",
        "Chuẩn hóa luồng BPMN 2.0, tự động hoá phê duyệt và kích hoạt Webhook.": "Standardize BPMN 2.0 workflows, automate multi-level approvals, and trigger real-time Webhooks.",
        "Tự sinh OpenAPI / Swagger 3.0, bảo mật token JWT phân quyền chi tiết.": "Auto-generate OpenAPI / Swagger 3.0 specs with granular JWT token-based authorization.",
        "Xuất bản 1 chạm trên Web Browser, iOS, Android và Tablet công nghiệp.": "Single-click deployment across Web Browsers, iOS, Android, and Industrial Rugged Tablets.",
        "TỐC ĐỘ DEV": "DEVELOPMENT VELOCITY",
        "CHUẨN TƯƠNG THÍCH": "COMPATIBILITY STANDARD",
        "100% Sạch Sẽ": "100% Clean Code",
        "Lớp 1: No-Code": "Layer 1: No-Code Platform",
        "Lớp 2: Services": "Layer 2: Core Services",
        "Lớp 3: AI": "Layer 3: Enterprise AI",
        "Lớp 4: Data ERP": "Layer 4: ERP & Big Data",
        "LỚP 02 · INFRASTRUCTURE & SECURITY": "LAYER 02 · INFRASTRUCTURE & SECURITY",
        "Tầng dịch vụ nền tảng cung cấp hạ tầng Microservices chịu tải cao, cơ chế bảo mật Zero-Trust toàn diện, quản lý định danh IAM/SSO, và quy trình CI/CD GitOps tự động hoá giúp hệ thống hoạt động liên tục 24/7 với 99.99% Enterprise Uptime.": "The core platform layer provides high-throughput microservices infrastructure, end-to-end Zero-Trust security, enterprise IAM/SSO identity federation, and automated GitOps CI/CD pipelines—ensuring 24/7 continuous resilience with 99.99% enterprise uptime.",
        "Mã hóa TLS 1.3 và mTLS giữa mọi microservices, kiểm tra quyền từng request.": "TLS 1.3 in-transit encryption and service-to-service mTLS with per-request policy authorization.",
        "Cô lập dữ liệu tuyệt đối giữa các tenant ở tầng database và runtime.": "Absolute multi-tenant data isolation enforced across both database and runtime layers.",
        "Tự động mở rộng pod theo phụ tải CPU/RAM trong vòng 15 giây.": "Autonomous horizontal pod autoscaling based on CPU/RAM metrics within 15 seconds.",
        "Thu thập chỉ số APM, OpenTelemetry, và giám sát lỗi tập trung thời gian thực.": "Centralized telemetry ingestion, OpenTelemetry APM instrumentation, and real-time observability.",
        "BẢO MẬT": "ENTERPRISE SECURITY",
        "ĐỘ TRỄ NỘI BỘ": "INTERNAL LATENCY",
        "LỚP 03 · INTELLIGENCE & AGENT SWARMS": "LAYER 03 · INTELLIGENCE & AGENT SWARMS",
        "Tích hợp trí tuệ nhân tạo chuyên sâu vào từng mắt xích vận hành doanh nghiệp. Kết hợp Generative AI, Explainable AI (XAI), thị giác máy tính VLM và cụm tác nhân AI tự chủ (Multi-Agent Swarms) giúp tối ưu hóa chuỗi cung ứng, dự báo tồn kho và ra quyết định chính xác.": "Embedding domain-specialized artificial intelligence across enterprise operations. Combining Generative AI, Explainable AI (XAI), VLM computer vision, and autonomous Multi-Agent Swarms to optimize supply chains, forecast inventory, and execute precision decisions.",
        "Điều phối các Agent tự hành kiểm tra chứng từ, đối soát tài chính và mua sắm.": "Orchestrate autonomous agent swarms to audit trade documentation, reconcile finances, and streamline procurement.",
        "Giải thích minh bạch mọi đề xuất giá bán, cảnh báo rủi ro tín dụng đối tác.": "Provide transparent reasoning for dynamic pricing proposals and partner credit risk scoring.",
        "Thị giác AI nhận diện tem mác, quét lỗi phôi SS400 trên trạm cắt Laser CNC.": "Vision AI inspects labels and detects surface defects on SS400 billets across CNC laser cutting cells.",
        "Truy vấn tri thức nội bộ từ hàng triệu trang tài liệu quy trình, tiêu chuẩn ISO.": "Enterprise semantic RAG across millions of pages of standard operating procedures and ISO specifications.",
        "ĐỘ CHÍNH XÁC": "INFERENCE ACCURACY",
        "MÔ HÌNH HỖ TRỢ": "SUPPORTED FOUNDATION MODELS",
        "THỜI GIAN PHẢN HỒI": "RESPONSE LATENCY",
        "LỚP 04 · CORE ENGINE & LEDGER": "LAYER 04 · CORE ENGINE & LEDGER",
        "Tầng gốc rễ hội tụ toàn bộ nguồn lực doanh nghiệp: Hệ thống ERP toàn diện (Bán hàng, Mua hàng, Kho vận, Sản xuất, Kế toán Thông tư 200/78), Data Lake hồ dữ liệu lớn, luồng cảm biến IIoT từ nhà máy và bộ máy quản trị rủi ro & tuân thủ (GRC).": "The enterprise foundation unifying all operational resources: Full-suite ERP (Sales, Procurement, Warehouse Logistics, Manufacturing, Circular 200/78 Financials), Enterprise Data Lake, Shop-Floor IIoT Streams, and Integrated GRC (Governance, Risk, and Compliance).",
        "Quy trình liên kết xuyên suốt SD-MM-PP-FI/CO, chuẩn hóa Legacy ERP Lexicon.": "Seamless end-to-end SD-MM-PP-FI/CO process orchestration mapped to legacy ERP lexicons.",
        "Kết nối máy cắt Laser CNC, Robot hàn và cảm biến qua MQTT / OPC-UA.": "Real-time connectivity for CNC laser cutters, robotic welding arms, and industrial sensors via MQTT / OPC-UA.",
        "Kiểm soát rủi ro gian lận, truy vết Audit Trail chuẩn mực ngân hàng.": "Continuous fraud mitigation and bank-grade immutable audit trails.",
        "Cơ sở dữ liệu PostgreSQL Enterprise tự chủ, bất biến và sao lưu đa vùng.": "Sovereign PostgreSQL Enterprise database with multi-region disaster recovery and point-in-time recovery.",
        "DỮ LIỆU BẤT BIẾN": "DATA IMMUTABILITY",
        "XỬ LÝ IIOT": "IIOT STREAM INGESTION",
        "Kết nối dữ liệu từ PO, Invoice, Packing List, tờ khai, BOM, nguyên vật liệu và hồ sơ pháp lý để doanh nghiệp kiểm tra giao dịch, xử lý ngoại lệ và chuẩn bị bằng chứng tuân thủ trong một luồng xuyên suốt.": "Unifying data across POs, Commercial Invoices, Packing Lists, Customs Declarations, BOMs, raw materials, and statutory records—enabling enterprises to audit transactions, resolve exceptions, and establish audit-ready compliance in a seamless workflow.",
        "GIAO DỊCH · #TX-2026-8942": "TRANSACTION · #TX-2026-8942",
        "Nhập Khẩu Phôi Thép Inox 304 & Vòng Bi Chính Xác": "Importation of SUS304 Stainless Steel Billets & Precision Bearings",
        "Nguồn: PO Legacy ERP (ERP) · Invoice PDF (Email) · Packing List Excel · Tờ Khai ECUS VNACCS · Sea Waybill B/L": "Sources: PO Legacy ERP (ERP) · Invoice PDF (Email) · Packing List Excel · ECUS VNACCS Customs Declaration · Sea Waybill B/L",
        "Chờ Kiểm Tra Rule": "Awaiting Rule Validation",
        "Quét Đối Chiếu Tự Động": "Automated Reconciliation Scan",
        "Dòng Hàng": "Line Item",
        "PO Mua Hàng": "Purchase Order (PO)",
        "Tờ Khai ECUS": "ECUS Customs Declaration",
        "Vận Đơn B/L": "Bill of Lading (B/L)",
        "Trạng Thái & Ngoại Lệ": "Status & Exceptions",
        "Trị giá: $35,625": "Value: $35,625",
        "⚠️ Lệch UOM Quy Đổi (±0.1kg)": "⚠️ UOM Conversion Variance (±0.1kg)",
        "Thuế NK lệch +3.2%": "Import Duty Variance +3.2%",
        "⚠️ Lệch Mã HS 6 Số": "⚠️ 6-Digit HS Code Discrepancy",
        "✅ Khớp 100%": "✅ 100% Matched",
        "ℹ️ Tách Dòng Hợp Lệ": "ℹ️ Valid Line Split",
        "Tổng kết đối soát:": "Reconciliation Summary:",
        "Chưa đối chiếu": "Pending Reconciliation",
        "Ký Số & Lưu Bằng Chứng Audit Trail": "Digital Sign & Commit Audit Trail Evidence",
        "AUDIT TRAIL · LỊCH SỬ KIỂM TRA & QUYẾT ĐỊNH NGHIỆP VỤ": "AUDIT TRAIL · TRANSACTION INSPECTION & BUSINESS DECISION LEDGER",
        "Tháp Thẩm Quyền Phân Giải Pháp Lý & Kiểm Soát Áp Mã HS": "Hierarchy of Legal Authority & HS Code Classification Governance",
        "Quy tắc bất biến: Diễn giải nội bộ (P4/P5) tuyệt đối không được phép ghi đè văn bản quy phạm pháp luật (P0/P1).": "Immutable Invariant: Internal interpretations (P4/P5) strictly shall not override statutory legislation or regulatory decrees (P0/P1).",
        "Mô Phỏng Né Thuế (P4 Override)": "Simulate Tax Evasion (P4 Override)",
        "Đặt Lại Trạng Thái Chuẩn": "Reset to Standard Compliant Baseline",
        "HỆ THỐNG PHÁT HIỆN HÀNH VI ÁP MÃ THẤP NÉ THUẾ (-3.2%)": "SYSTEM DETECTED TARIFF EVASION VIA ARTIFICIAL DOWN-CLASSIFICATION (-3.2%)",
        "Quy tắc thẩm quyền cấp cao chặn cưỡng bức: Diễn giải tư vấn P4 (HS 7219.33.00 thuế suất 3.2%) vi phạm trực tiếp Biểu thuế quy định tại Nghị định Chính phủ P1 (HS 7219.34 thuế suất 12%). Hệ thống tự động ghi nhật ký vi phạm và bảo vệ tính tuân thủ pháp lý cho doanh nghiệp.": "Authoritative Precedence Enforced: Advisory interpretation P4 (HS 7219.33.00 at 3.2% tariff) directly violates the statutory tariff schedule decreed under Government Decree P1 (HS 7219.34 at 12% tariff). The system automatically recorded the violation in the immutable compliance log, safeguarding enterprise legal integrity.",
        "P0 · TỐI CAO": "P0 · SUPREME AUTHORITY",
        "Hiệp Ước & Công Ước Quốc Tế": "International Treaties & Conventions",
        "Công ước HS WCO 6 số, Hiệp định EVFTA Protocol 1, RCEP, CPTPP.": "WCO 6-Digit HS Convention, EVFTA Protocol 1, RCEP, and CPTPP Agreements.",
        "P1 · PHÁP ĐỊNH": "P1 · STATUTORY LAW",
        "LUẬT HQ · NGHỊ ĐỊNH": "CUSTOMS LAW & GOVERNMENT DECREES",
        "Luật Hải Quan & Nghị Định Chính Phủ": "Customs Law & Government Decrees",
        "Luật HQ 54/2014/QH13, Nghị định 08/2015/NĐ-CP & Nghị định 35/2020/NĐ-CP.": "Customs Law 54/2014/QH13, Decree 08/2015/ND-CP & Decree 35/2020/ND-CP.",
        "P2 · THÔNG TƯ": "P2 · MINISTERIAL CIRCULARS",
        "BỘ TÀI CHÍNH · BCT": "MINISTRY OF FINANCE · MOIT",
        "Thông Tư & Biểu Thuế Xuất Nhập Khẩu": "Ministerial Circulars & Import-Export Tariff Schedules",
        "Thông tư 38/2015/TT-BTC, 39/2018/TT-BTC & Biểu thuế XNK hiện hành 2026.": "Circular 38/2015/TT-BTC, Circular 39/2018/TT-BTC & 2026 Import-Export Tariff Schedule.",
        "P3 · TỔNG CỤC HQ": "P3 · GENERAL DEPARTMENT OF CUSTOMS",
        "RULING NGHIỆP VỤ": "ADVANCE TARIFF RULINGS",
        "Quyết Định Phân Loại Tổng Cục Hải Quan": "Customs Directorate Classification Decisions & Formal Rulings",
        "Văn bản hướng dẫn phân loại mã hàng, công bố kết quả giám định mẫu.": "Official classification guidance and certified laboratory test rulings.",
        "P4 · THAM VẤN": "P4 · ADVISORY OPINION",
        "BIG 4 · TƯ VẤN THUẾ": "BIG 4 · TAX COUNSEL",
        "Ý Kiến Tư Vấn Của Hãng Kiểm Toán": "Audit & Tax Advisory Firm Memoranda",
        "Báo cáo rà soát thuế, khuyến nghị áp mã (chỉ có giá trị tham khảo nội bộ).": "Tax review memoranda and classification recommendations (internal advisory only).",
        "P5 · NỘI BỘ": "P5 · INTERNAL NOTES",
        "Ghi Chú Cá Nhân Của Nhân Viên Khai Báo": "Customs Broker & Staff Informal Notes",
        "Lịch sử khai báo của forwarder/nhân viên, không có giá trị pháp lý hải quan.": "Historical forwarding logs and staff notes (no statutory customs validity).",
        "Từ Dữ Liệu Nguyên Vật Liệu Đến Hồ Sơ Xuất Xứ Có Thể Truy Xuất": "From Raw Material Telemetry to Fully Traceable Rules of Origin Dossiers",
        "Kết nối tờ khai nhập, Master nguyên vật liệu, định mức BOM từ Legacy ERP, tỷ lệ hao hụt sản xuất và lô hàng xuất khẩu để tính toán tự động tiêu chí RVC/CTC và lưu bằng chứng giải trình.": "Connecting import customs declarations, raw material master data, ERP BOM consumption standards, production yield scrap factors, and export shipments to automatically calculate RVC/CTC origin criteria and preserve auditable substantiation.",
        "1. Tờ Khai Nhập ECUS": "1. ECUS Import Declaration",
        "2. Legacy ERP BOM & Hao Hụt": "2. Legacy ERP BOM & Scrap Factor",
        "3. Lô Hàng Xuất Khẩu": "3. Outbound Export Consignment",
        "4. Kiểm Tra Tiêu Chí C/O": "4. C/O Qualification Audit",
        "ĐỘNG CƠ TÍNH TIÊU CHÍ RVC %": "RVC % ORIGIN CALCULATION ENGINE",
        "Trị Giá FOB (USD):": "FOB Value (USD):",
        "Vật Liệu Non-Origin VNM ($):": "Non-Originating Materials VNM ($):",
        "HÀM LƯỢNG RVC % TÍNH TOÁN:": "CALCULATED RVC % CONTENT:",
        "✅ ĐẠT TIÊU CHÍ RVC (≥ 40%)": "✅ MEETS RVC ORIGIN THRESHOLD (≥ 40%)",
        "Xem Dự Thảo Biểu Mẫu C/O & Khấu Trừ BOM": "Review Draft C/O Form & BOM Depletion Ledger",
        "DỰ THẢO DỮ LIỆU C/O FORM D · ATIGA CERTIFICATE OF ORIGIN": "DRAFT C/O FORM D DATASET · ATIGA CERTIFICATE OF ORIGIN",
        "Hệ thống đã tự động khấu trừ định mức 5,670 KG Inox 304 vào Sổ Nhập-Xuất-Tồn Tờ Khai Nhập ECUS tương ứng. Lịch sử trừ lùi đã sẵn sàng cho cơ quan hải quan hậu kiểm.": "The system automatically depleted 5,670 kg of SUS304 stainless steel from the corresponding ECUS Import Declaration customs stock ledger. The audit trail is fully reconciled for post-clearance customs audits.",
        "Từ Hàng Nghìn Mã Hàng Đến Đúng Dữ Liệu & Hồ Sơ Hóa Chất Cần Xử Lý": "From Thousands of SKUs to Precision Hazardous Chemical Records",
        "Chuẩn hóa và liên kết Material ↔ Hóa chất ↔ Mã CAS ↔ Mục đích sử dụng để xác định nghĩa vụ giấy phép và khai báo hải quan một cửa.": "Standardizing and correlating Materials ↔ Chemicals ↔ CAS Registry Numbers ↔ End Uses to identify regulatory licensing obligations and National Single Window customs declarations.",
        "Sinh Bộ Dataset Khai Báo Cổng Một Cửa": "Generate National Single Window Regulatory Dataset",
        "Tất cả danh mục pháp lý": "All Statutory Categories",
        "Hóa chất kinh doanh có điều kiện (NĐ 113)": "Conditional Commercial Chemicals (Decree 113)",
        "Tiền chất công nghiệp": "Industrial Chemical Precursors",
        "Hóa chất hạn chế sản xuất/kinh doanh": "Restricted Production/Commercial Chemicals",
        "Mã Vật Tư & Tên Hóa Chất": "Material SKU & Chemical Name",
        "Mã CAS": "CAS Registry Number",
        "Mục Đích Sử Dụng": "Intended Industrial Use",
        "Phân Loại Pháp Lý": "Statutory Classification",
        "Hạn Mức Quota": "Allocated Import Quota",
        "Nghĩa Vụ Giấy Phép": "Licensing Obligation",
        "Tẩy rửa thụ động hóa bề mặt Inox 304": "Surface pickling and passivation for SUS304 stainless steel",
        "Hóa Chất Có Điều Kiện (NĐ 113)": "Conditional Chemical (Decree 113)",
        "✅ Giấy Phép Còn Hạn (2027)": "✅ Valid Regulatory License (Exp: 2027)",
        "Dung môi pha chế sơn tĩnh điện xưởng cơ khí": "Powder coating solvent formulation in precision fabrication shop",
        "Tiền Chất Công Nghiệp Nhóm 2": "Group 2 Industrial Precursor",
        "⚠️ Khai Báo Nhập Khẩu Một Cửa": "⚠️ National Single Window Import Declaration Required",
        "Bể xử lý điện phân mạ bề mặt cơ khí chính xác": "Electrolytic surface plating bath for precision components",
        "Hóa Chất Hạn Chế Kinh Doanh": "Restricted Commercial Chemical",
        "⚠️ Sắp Chạm Trần Quota Giấy Phép": "⚠️ Nearing Licensed Import Quota Ceiling",
        "Kiểm soát hoạt động theo": "Operational governance enforcing",
        "quy định, phân quyền & an toàn": "compliance, segregation of duties & zero-harm safety",
        "Khóa hãm năng lượng LOTO, quản trị giấy phép công việc nguy hiểm e-PTW và nhật ký bàn giao ca số hóa không thể sửa xóa.": "Digital Lockout/Tagout (LOTO), electronic Permit to Work (e-PTW) hazardous governance, and tamper-proof shift handover logbooks.",
        "Đúng quy trình": "Process Adherence",
        "Đúng thẩm quyền": "Delegated Authority",
        "Đủ an toàn": "Fail-Safe Hazard Controls",
        "Lưu vết bằng chứng": "Immutable Evidentiary Trail",
        "Permit to Work & LOTO (Khóa Nguồn Năng Lượng)": "Permit to Work & LOTO (Lockout/Tagout)",
        "Operations Logbook & Shift Handover (Giao Nhận Ca)": "Operations Logbook & Digital Shift Handover",
        "GIẤY PHÉP · e-PTW-2026-0412": "PERMIT · e-PTW-2026-0412",
        "Hàn Cắt & Làm Việc Trong Không Gian Kín Bồn Phản Ứng R-201": "Hot Work & Confined Space Entry: Chemical Reactor Vessel R-201",
        "Khu vực: Phân Xưởng Hóa Nhuộm 02 · Nhân lực: Đội Cơ Điện 5 người · Thời hạn: 08 Giờ": "Zone: Dyeing & Chemical Plant 02 · Crew: 5-Member Electromechanical Team · Duration: 08 Hours",
        "⚠️ Đang Chờ Cô Lập Điểm LOTO Số 04": "⚠️ Awaiting Isolation at LOTO Point #04",
        "⏱️ Ca Hiệu Lực: 07:59:45": "⏱️ Valid Shift Window: 07:59:45",
        "YÊU CẦU AN TOÀN BẮT BUỘC:": "MANDATORY SAFETY PROTOCOL:",
        "Giấy phép làm việc chỉ được phép ký duyệt số khi tất cả 4 điểm cô lập nguồn năng lượng (van khí, van xả, cầu dao điện) đã được gắn Khóa LOTO và Thẻ Cảnh Báo An Toàn.": "Permit approval can only be digitally authorized once all four energy isolation points (gas valve, drain valve, electrical circuit breaker) are verified with physical LOTO locks and hazard warning tags.",
        "Giải Phẫu 3D Bồn Phản Ứng Hóa Chất R-201 & Mạng Cô Lập LOTO": "3D Spatial Anatomy of Chemical Reactor R-201 & LOTO Isolation Network",
        "Cắt Lớp X-Ray": "X-Ray Cross Section",
        "Đỉnh Bồn 90°": "90° Vessel Dome",
        "Trạng Thái Cách Ly:": "Isolation Status:",
        "3/4 CÔ LẬP · CÒN NGUY HIỂM": "3/4 ISOLATED · HAZARD ACTIVE",
        "Kéo xoay 360° · Bấm trực tiếp vào Van #04 (V-109) trên mô hình 3D để khóa cô lập LOTO": "Rotate 360° · Click Valve #04 (V-109) directly on the 3D model to engage LOTO isolation",
        "NGUỒN CẤP AXIT ĐẬM ĐẶC": "CONCENTRATED ACID FEED LINE",
        "Van Bi Axit 3\": Đã Khóa Cơ Học": "3\" Acid Ball Valve: Mechanically Locked",
        "NGUỒN ĐIỆN ĐỘNG CƠ 380V/45kW": "380V / 45kW AGITATOR MOTOR POWER",
        "Aptomat Khuấy: Đã Ngắt Nguồn": "Agitator Circuit Breaker: Tripped & De-energized",
        "ĐƯỜNG XẢ CẶN VÀ NƯỚC RỬA": "EFFLUENT SLUDGE & RINSE WATER DRAIN",
        "Van Xả Đáy: Đã Xả Áp Hoàn Toàn": "Bottom Drain Valve: Depressurized to Zero",
        "KHÍ TRƠ N2 ÁP SUẤT CAO 10 BAR": "10-BAR HIGH-PRESSURE N2 INERT GAS LINE",
        "⚠️ V-109 (CHƯA KHÓA)": "⚠️ V-109 (UNLOCKED / ACTIVE)",
        "Bấm Để Gắn Khóa LOTO #L-8824": "Click to Affix LOTO Lock #L-8824",
        "Chuẩn: 19.5% - 23.5%": "Standard: 19.5% - 23.5%",
        "Ngưỡng an toàn: 0.0%": "Safe Threshold: 0.0%",
        "Giới hạn: < 10 ppm": "Exposure Limit: < 10 ppm",
        "Ngưỡng an toàn: 0.00 bar": "Safe Threshold: 0.00 bar",
        "ĐÃ KHÓA (#L-8821)": "LOCKED (#L-8821)",
        "Van Nạp Liệu Chính V-101": "Main Feed Valve V-101",
        "Van bi cấp axit 3-inch, đã khóa xích cơ học và kẹp tag đỏ.": "3-inch acid feed ball valve: Mechanically chained, padlocked, and red safety tagged.",
        "Mở Khóa": "Unlock",
        "ĐÃ KHÓA (#L-8822)": "LOCKED (#L-8822)",
        "Cầu Dao Động Cơ CB-201": "Motor Breaker CB-201",
        "Aptomat nguồn động cơ cánh khuấy 45kW, đã ngắt và gắn hasp khóa.": "45kW agitator motor breaker: Switched off, verified dead, and locked with lockout hasp.",
        "ĐÃ KHÓA (#L-8823)": "LOCKED (#L-8823)",
        "Van Xả Đáy Bồn V-105": "Vessel Bottom Drain Valve V-105",
        "Van xả cặn đáy, đã xả áp dư về 0 bar và khóa tay quay.": "Bottom sludge blowdown valve: Residual pressure bled to 0 bar and handwheel locked.",
        "CHƯA KHÓA HÃM": "PENDING LOTO LOCKOUT",
        "Van Khí Trơ Nitơ V-109": "Nitrogen Inert Gas Valve V-109",
        "Van cấp khí nitơ làm trơ, chưa gắn khóa cơ và thẻ cảnh báo.": "Inert nitrogen feed valve, pending mechanical lockout and danger tag.",
        "Gắn Khóa LOTO": "Apply LOTO Lockout",
        "Thẩm quyền phê duyệt:": "Approval Authority:",
        "Kỹ Sư An Toàn EHS": "EHS Safety Engineer",
        "Quản Đốc Phân Xưởng": "Plant Superintendent",
        "Ký Duyệt e-PTW Số & Cấp Phép Thi Công": "Digitally Authorize e-PTW & Work Permit",
        "CHỮ KÝ SỐ #1 · SAFETY LEAD": "DIGITAL SIGNATURE #1 · SAFETY LEAD",
        "Trần Quốc Bảo - Kỹ Sư An Toàn EHS Cấp Cao": "Tran Quoc Bao - Senior EHS Safety Engineer",
        "CHỮ KÝ SỐ #2 · PLANT MANAGER": "DIGITAL SIGNATURE #2 · PLANT MANAGER",
        "Lê Hoàng Nam - Quản Đốc Phân Xưởng Cơ Điện": "Le Hoang Nam - Electromechanical Plant Superintendent",
        "GIAO NHẬN CA · BÀN GIAO SONG PHƯƠNG": "SHIFT HANDOVER · BILATERAL SIGNOFF",
        "Ca Trưởng Ca 1: Nguyễn Văn Thắng · Ca Trưởng Ca 2: Trần Đình Trọng · Dây Chuyền Cơ Khí CNC": "Shift 1 Lead: Nguyen Van Thang · Shift 2 Lead: Tran Dinh Trong · CNC Machining Line",
        "Đang Chờ Ký Giao Ca": "Pending Shift Handover Signature",
        "Tất Cả Sự Kiện": "All Events",
        "🔴 P1 Khẩn Cấp (1)": "🔴 P1 Critical (1)",
        "🟡 P2 Cảnh Báo (1)": "🟡 P2 Warning (1)",
        "🔵 P3 Thông Tin (1)": "🔵 P3 Informational (1)",
        "[10:14 UTC] ALARM-P1: Máy Ép Thủy Lực P-02 Quá Nhiệt Dầu Bôi Trơn": "[10:14 UTC] ALARM-P1: Hydraulic Press P-02 Lube Oil Overheating",
        "P1 ĐÃ XỬ LÝ": "P1 RESOLVED",
        "Nhiệt độ đạt 78°C. Đã dừng khẩn cấp, vệ sinh bộ sinh hàn dầu, thay 20L dầu ISO VG 68. Máy chạy thử ổn định ở 52°C.": "Temperature reached 78°C. Triggered emergency stop, cleaned oil heat exchanger, and replaced 20L of ISO VG 68 lubricant. Test run stabilized at 52°C.",
        "[11:45 UTC] WARN-P2: Rò Rỉ Hơi Nhẹ Tại Mặt Bích Van Hơi V-33": "[11:45 UTC] WARN-P2: Minor Steam Leak at Steam Valve Flange V-33",
        "P2 CẦN THEO DÕI": "P2 MONITORING REQUIRED",
        "Rò rỉ hơi áp 4 bar tại gioăng amiăng. Đã siết đều bulông và đưa vào danh sách việc tồn bàn giao ca cho Ca 2 thay thế gioăng graphit.": "4-bar steam leak at asbestos gasket. Flange bolts retorqued; logged into shift handover backlog for Shift 2 graphite gasket replacement.",
        "[13:00 UTC] INFO-P3: Tiếp Nhận 2 Xe Tải Phôi Thép Tấm SS400 (32 Tấn)": "[13:00 UTC] INFO-P3: Received 2 Truckloads of SS400 Steel Plates (32 Tons)",
        "P3 HOÀN TẤT": "P3 COMPLETED",
        "Đã quét Barcode QR nhập kho WMS, lưu vị trí ô kệ A-04 và đối soát phiếu cân điện tử 100% khớp.": "WMS inbound QR barcode scanned, assigned to rack location A-04, and electronic weighbridge tickets 100% reconciled.",
        "DANH MỤC VIỆC TỒN ĐỌNG BÀN GIAO CA (HANDOVER CHECKLIST):": "SHIFT HANDOVER BACKLOG (HANDOVER CHECKLIST):",
        "Xác nhận thông số máy ép P-02 sau 2 giờ chạy thử (Dầu: 52°C, Áp suất: 180 bar).": "Verify hydraulic press P-02 operating parameters post-2-hour test run (Oil: 52°C, Pressure: 180 bar).",
        "Bàn giao vật tư thay thế gioăng van hơi V-33 cho ca 2 trong giờ bảo trì giữa ca (16:30).": "Hand over replacement gasket materials for steam valve V-33 to Shift 2 during mid-shift maintenance window (16:30).",
        "Ca Trưởng Ca 1 Ký Giao": "Shift 1 Lead Sign-off",
        "Ca Trưởng Ca 2 Ký Nhận": "Shift 2 Lead Sign-off",
        "Đọc hiểu chứng từ vận tải (B/L, Booking, D/O), tự động tạo Jobfile nghiệp vụ và đối soát chi phí thực tế với biểu phí hợp đồng trước khi thanh toán.": "Ingests freight documents (B/L, Booking, D/O), auto-generates operational Jobfiles, and audits actual billing against contracted tariffs prior to settlement.",
        "Bóc tách B/L tự động": "Automated B/L Extraction",
        "Jobfile xuyên suốt": "End-to-End Operational Jobfiles",
        "Khóa chênh lệch cước": "Freight Discrepancy Lock",
        "Vận Chuyển Container Cảng Cửa Ngõ Phía Nam (VNCLI) ➔ Los Angeles (USLAX)": "Container Freight: Southern Gateway Port (VNCLI) ➔ Los Angeles (USLAX)",
        "Tuyến Vận Tải: Tuyến Container Viễn Dương Quốc Tế · Tàu: M/V PACIFIC SOVEREIGN · 2x40' HC (": "Trade Route: Deep-Sea International Container Line · Vessel: M/V PACIFIC SOVEREIGN · 2x40' HC (",
        "Sinh Thư Kháng Nghị Chi Phí Bất Thường": "Generate Freight Dispute Notice",
        "KHOẢN MỤC CHI PHÍ (LOCAL CHARGES & FREIGHT)": "LINE ITEM CHARGES (LOCAL CHARGES & FREIGHT)",
        "BIỂU PHÍ THỎA THUẬN (CONTRACT TARIFF)": "AGREED CONTRACT TARIFF",
        "HÓA ĐƠN THỰC TẾ (CARRIER INVOICE)": "ACTUAL CARRIER INVOICE",
        "CHÊNH LỆCH": "VARIANCE",
        "ĐÁNH GIÁ ĐỐI SOÁT": "AUDIT RECONCILIATION",
        "Cước Biển (Ocean Freight - O/F)": "Ocean Freight (O/F)",
        "✓ Khớp 100%": "✓ 100% Matched",
        "Phí Xếp Dỡ Tại Cảng (THC)": "Terminal Handling Charges (THC)",
        "Terminal Handling - Cảng Container Cửa Ngõ Phía Nam": "Terminal Handling - Southern Gateway Container Port",
        "Phí Chì & Chứng Từ (Seal & Doc Fee)": "Seal & Documentation Fee",
        "Hóa đơn phát hành hãng tàu": "Carrier-issued invoice",
        "Phí Phạt Lưu Vỏ & Lưu Bãi (DEM/DET)": "Demurrage & Detention Penalties (DEM/DET)",
        "Quy định hợp đồng: 14 Ngày Miễn Phí": "Contract terms: 14 Free Days",
        "4,600,000 VND (+2 Ngày Phạt)": "4,600,000 VND (+2 Penalty Days)",
        "⚠️ Thu Sai Điều Khoản Hợp Đồng": "⚠️ Billed in Violation of Contract Terms",
        "VĂN BẢN KHÁNG NGHỊ CHI PHÍ CƯỚC VẬN TẢI · DISPUTE NOTICE": "FREIGHT CHARGE DISPUTE NOTICE",
        "Hợp Đồng Khung: #CONTRACT-OCEAN-2026-V1": "Master Agreement: #CONTRACT-OCEAN-2026-V1",
        "Kính gửi Đơn vị Vận tải Container Quốc tế: Căn cứ Điều khoản 14.2 Phụ lục Biểu phí Miễn phí DEM/DET ký ngày 01/01/2026, lô hàng B/L #BL8841920 được hưởng trọn vẹn": "Attention International Container Carrier: Pursuant to Clause 14.2 of the DEM/DET Free Time Addendum dated January 1, 2026, consignment B/L #BL8841920 is entitled to full",
        "14 ngày miễn phí lưu bãi/lưu vỏ": "14 free days of demurrage/detention",
        "tại Cảng Container Quốc Tế Trọng Điểm. Container CONT4918230 được kéo hạ bãi vào ngày thứ 13 kể từ ngày dỡ tàu. Do đó, khoản thu 4,600,000 VND tiền phạt phát sinh ngày 15-16 là không phù hợp với thỏa thuận.": "at Key International Container Terminal. Container CONT4918230 was gated in on Day 13 post-discharge. Consequently, the 4,600,000 VND penalty assessed for Days 15–16 contradicts contractual terms.",
        "Trạng thái:": "Status:",
        "Đã xuất PDF & đính kèm lịch sử GPS kéo container từ depot": "PDF exported with depot-to-gate GPS telematics audit trail attached",
        "TIẾT KIỆM TỨC THÌ: 4,600,000 VND": "IMMEDIATE RECOVERED SAVINGS: 4,600,000 VND",
        "Tính Toán Chi Phí Đổ Cảng Thực Tế & Lợi Ích Hiệp Định FTA": "Landed Cost Calculation & FTA Tariff Optimization",
        "MÃ TRA CỨU HẢI QUAN · ECUS-EVFTA-2026-0988 · TỰ ĐỘNG KHỚP C/O FORM EUR.1": "CUSTOMS REFERENCE · ECUS-EVFTA-2026-0988 · AUTOMATED C/O FORM EUR.1 MATCH",
        "Đã Khớp EVFTA (0%)": "EVFTA Tariff Matched (0%)",
        "TIẾT KIỆM $480": "SAVINGS $480",
        "Biểu Phí MFN (10%)": "MFN Tariff (10%)",
        "CHƯA KHỚP C/O": "UNMATCHED C/O",
        "Giá Mua FOB Cơ Sở": "Base FOB Procurement Price",
        "Gốc Hóa Đơn": "Commercial Invoice Origin",
        "Cước Vận Tải Biển Quốc Tế": "International Ocean Freight",
        "Hãng Tàu Quốc Tế Hàng Đầu B/L #MSKU8841": "Tier-1 Ocean Carrier B/L #MSKU8841",
        "Xếp Dỡ & Phí Cảng Tổng Công Ty Khai Thác Cảng": "Terminal Handling & Port Authority Charges",
        "Thuế Nhập Khẩu Tiêu Chuẩn MFN (10%)": "Standard MFN Import Duty (10%)",
        "Áp khi thiếu C/O": "Assessed without C/O",
        "Không Ưu Đãi": "Non-Preferential",
        "Ưu Đãi Thuế Quan EVFTA (0%)": "EVFTA Preferential Tariff (0%)",
        "C/O Form EUR.1 Hợp Lệ": "Valid C/O Form EUR.1",
        "Tiết Kiệm -$480": "Savings -$480",
        "Chi Phí Đổ Cảng Cuối Cùng": "Net Final Landed Cost",
        "Biên Lãi +8.4%": "Gross Margin +8.4%",
        "Phân Bổ Tỷ Trọng Chi Phí Đổ Cảng (Landed Cost Structure)": "Landed Cost Structure Breakdown",
        "CƯỚC 10.0%": "FREIGHT 10.0%",
        "TIẾT KIỆM THUẾ EVFTA -$480": "EVFTA TARIFF SAVINGS -$480",
        "THUẾ MFN +$480": "MFN DUTY +$480",
        "Giá FOB ($3,700)": "FOB Price ($3,700)",
        "Cước Biển ($420)": "Ocean Freight ($420)",
        "Phí Cảng THC ($100)": "Port THC Fee ($100)",
        "Tiết Kiệm Thuế EVFTA ($480 / Cont)": "EVFTA Tariff Savings ($480 / Container)",
        "HIỆP ĐỊNH THƯƠNG MẠI TỰ DO EVFTA · PROTOCOL 1": "EVFTA FREE TRADE AGREEMENT · PROTOCOL 1",
        "TIÊU CHÍ RVC = 48.6% > 40.0% (CTC ĐẠT)": "RVC CRITERIA = 48.6% > 40.0% (CTC COMPLIANT)",
        "XÁC THỰC PHÁP LÝ TỰ ĐỘNG BẰNG RULE ENGINE": "AUTOMATED STATUTORY VERIFICATION VIA RULE ENGINE",
        "Căn cứ pháp lý: Khoản 2 Điều 3.2 Thông tư 11/2020/TT-BCT & Nghị định 35/2020/NĐ-CP": "Statutory Basis: Clause 2, Article 3.2, Circular 11/2020/TT-BCT & Decree 35/2020/ND-CP",
        "Hàng hóa đã được đối soát 100% dòng nguyên phụ liệu nhập khẩu với định mức tiêu hao thực tế (BOM Legacy ERP vs Sàn sản xuất). Tỷ lệ hàm lượng giá trị gia tăng khu vực đạt": "Consignment verified with 100% reconciliation of imported raw material line items against actual production BOM (Legacy ERP vs Shop Floor). Regional Value Content (RVC) achieved",
        ", vượt ngưỡng tiêu chuẩn 40.0%. Áp dụng thuế suất ưu đãi đặc biệt": ", exceeding the 40.0% statutory threshold. Eligible for preferential tariff",
        "(Tiết kiệm tức thời ₫148,200,000 / Lô hàng).": "(Immediate savings: ₫148,200,000 / shipment).",
        "· KHÓA DỮ LIỆU TỜ KHAI ECUS5-VNACCS": "· ECUS5-VNACCS DECLARATION DATA LOCK",
        "🛡️ Hồ Sơ Sẵn Sàng Thanh Tra Hải Quan": "🛡️ Customs Audit-Ready Documentation Dossier",
        "QUY TRÌNH KỸ NGHỆ · ENTERPRISE PIPELINE": "ENGINEERING LIFECYCLE · ENTERPRISE PIPELINE",
        "Quy Trình Triển Khai Cấp Tập Đoàn": "Enterprise-Grade Deployment Framework",
        "4 Giai Đoạn": "4 Phases",
        "Phương thức chuyển đổi số cấp chủ quyền: Kiểm toán kiến trúc độc lập, chứng minh năng lực thực nghiệm nhanh và triển khai tự chủ không gián đoạn vận hành.": "Sovereign digital transformation methodology: Independent architectural audit, rapid empirical proof-of-value, and autonomous, zero-downtime production rollout.",
        "Giai Đoạn 1": "Phase 1",
        "Phiên Tham Vấn Cấp Chiến Lược (Executive Briefing)": "Executive Strategy Briefing",
        "Khảo sát chuyên sâu cùng ban lãnh đạo, định vị điểm nghẽn vận hành và xác lập khung giải pháp khả thi ngay trong buổi làm việc đầu tiên.": "Executive deep-dive session to pinpoint operational bottlenecks and define an actionable solution roadmap from Day One.",
        "Phân tích Phạm Vi & Điểm Nghẽn Vận Hành": "Scope Definition & Operational Bottleneck Analysis",
        "Phác thảo Hành Trình Trải Nghiệm Người Dùng": "End-to-End User Experience Journey Mapping",
        "Giai Đoạn 2": "Phase 2",
        "Thẩm Định Kỹ Thuật & Thực Nghiệm POC": "Technical Validation & Empirical POC",
        "Đánh giá hạ tầng kỹ thuật, dựng mô hình tương tác mẫu (POC) và kiểm chứng mức độ tương thích dữ liệu thực tế của doanh nghiệp.": "Audit technical infrastructure, construct interactive POC prototypes, and validate empirical data interoperability with enterprise systems.",
        "Khung Thiết Kế & Nguyên Mẫu Thử Nghiệm": "Design Architecture & Interactive Prototypes",
        "Kiểm chứng kiến trúc bảo mật": "Security Architecture & Cryptographic Verification",
        "Giai Đoạn 3": "Phase 3",
        "Thử Nghiệm Môi Trường Thực Tế (MVP)": "Production Pilot & MVP Deployment",
        "Hoàn thiện phiên bản MVP với đầy đủ luồng nghiệp vụ cốt lõi, chạy thử nghiệm trên môi trường sandbox độc lập cùng người dùng thực tế.": "Finalize production MVP encompassing core business workflows, piloting in an isolated sandbox with real enterprise operators.",
        "Thử Nghiệm Sandbox với Dữ Liệu Thực": "Sandbox Pilot with Real-World Production Data",
        "Đo lường phản hồi vận hành": "Operational Feedback & SLA Telemetry Benchmarking",
        "Giai Đoạn 4": "Phase 4",
        "Vận Hành Thực Chiến Toàn Doanh Nghiệp": "Enterprise-Wide Production Go-Live",
        "Mở rộng quy mô giải pháp trên toàn bộ phòng ban hoặc nhà máy, chuyển giao mã nguồn và kích hoạt hệ thống bảo mật Sovereign Cloud.": "Scale seamlessly across all business units and plants, deliver full source code ownership, and activate Sovereign Cloud security safeguards.",
        "Vận hành chính thức (Go-Live)": "Official Production Go-Live",
        "SLA Hỗ trợ kỹ thuật 24/7": "24/7/365 Dedicated SLA Support",
        "HỆ SINH THÁI CÔNG NGHỆ · CORE PLATFORMS": "TECHNOLOGY ECOSYSTEM · CORE PLATFORMS",
        "4 Trụ Cột Công Nghệ Độc Lập": "4 Autonomous Technology Pillars",
        "Các giải pháp của Innoria được xây dựng trên kiến trúc module hoá cao cấp, đồng nhất chuẩn giao tiếp, sẵn sàng tích hợp hoặc vận hành độc lập theo quy mô doanh nghiệp.": "Innoria platforms are engineered on high-grade modular architecture with unified interface standards, ready for turnkey integration or standalone sovereign operation across enterprise scale.",
        "NỀN TẢNG NO-CODE / LOW-CODE": "NO-CODE / LOW-CODE PLATFORM",
        "Nền tảng phát triển ứng dụng siêu tốc. Giúp đội ngũ nghiệp vụ và chuyên gia CNTT hợp tác kiến tạo phần mềm doanh nghiệp trên giao diện kéo thả trực quan.": "High-velocity application development platform empowering business teams and IT leaders to co-create enterprise software via an intuitive visual builder.",
        "Điểm nổi bật": "Key Highlights",
        "Rút ngắn 70% thời gian code": "Reduces custom engineering time by 70%",
        "Tự động sinh REST/GraphQL API": "Auto-generates REST & GraphQL APIs",
        "Khám Phá DIGIFORCE": "Explore DIGIFORCE",
        "⚡ Tư Vấn & Dự Toán AI": "⚡ AI Architecture Consultation & Sizing",
        "CỤM TÁC NHÂN AI ĐA LUỒNG": "MULTI-AGENT AI CLUSTERS",
        "Nền tảng phát triển tác nhân AI tự trị: Tích hợp thị giác máy tính VLM công nghiệp (See-Detect-Analyze-Adapt) và mạng lưới suy luận logic đa tầng (Reason-Solve-Plan-Execute).": "Autonomous AI agent development platform integrating industrial VLM computer vision (See-Detect-Analyze-Adapt) with multi-echelon reasoning engines (Reason-Solve-Plan-Execute).",
        "Độ trễ suy luận < 200ms": "Inference Latency < 200ms",
        "Chống ảo giác dữ liệu 100%": "100% Hallucination-Resistant Grounding",
        "Khám Phá MOJO AI": "Explore MOJO AI",
        "KỸ NGHỆ PHẦN MỀM TỰ TRỊ": "AUTONOMOUS SOFTWARE ENGINEERING",
        "Hệ điều hành kỹ nghệ tự trị cho ngân hàng, fintech và doanh nghiệp chủ quyền. Tự động hóa vòng đời phần mềm khép kín Swarm PDCA, cô lập Zero-Telemetry và hiện đại hóa Core Banking.": "Autonomous software engineering operating system for tier-1 banking, fintech, and sovereign enterprises. Automates closed-loop Swarm PDCA, isolates Zero-Telemetry pipelines, and modernizes Core Banking systems.",
        "Swarm PDCA & Binary Veto (5 vai trò)": "Swarm PDCA & Binary Veto (5 roles)",
        "Khám Phá ZENCODE-ENT": "Explore ZENCODE-ENT",
        "HỆ THỐNG VẬN HÀNH TỰ TRỊ": "AUTONOMOUS OPERATING SYSTEM",
        "Nền tảng ERP tự hành hợp nhất chuỗi cung ứng, sản xuất cơ khí chính xác và tài chính. Tự động hóa chuẩn mực kế toán Việt Nam (Thông tư 200, Hóa đơn điện tử Nghị định 70/2025/NĐ-CP), điều phối logistics cảng biển và MES trạm xưởng.": "Autonomous ERP platform unifying supply chain, precision engineering manufacturing, and finance. Automates Vietnamese Accounting Standards (VAS 200, Decree 70/2025/ND-CP e-Invoicing), maritime port logistics, and shop-floor MES.",
        "Chuẩn hóa VAS TT 200 & HĐĐT NĐ 70/2025": "Compliant with VAS Circular 200 & Decree 70/2025 e-Invoices",
        "Giảm 85% vận hành thủ công · OEE ≥ 95%": "85% Manual Workload Reduction · OEE ≥ 95%",
        "Khám Phá INSILOS": "Explore INSILOS",
        "SYSTEMS ANATOMY // CỖ MÁY GIẢI PHẪU KIẾN TRÚC TỰ HÀNH": "SYSTEMS ANATOMY // AUTONOMOUS ARCHITECTURE ENGINE",
        "Kiến Trúc Hệ Thống Cấp Chủ Quyền": "Sovereign-Grade System Architecture",
        "Mỗi cấu kiện cơ khí trên mô hình đẳng cự (Isometric Rig) phản ánh chính xác một cơ chế vận hành thực chứng: từ phân luồng chứng từ hải quan, thị giác biên 120 FPS ngắt mạch rơ-le an toàn, đến buồng mật mã kế toán cô lập vật lý.": "Every mechanical assembly on the isometric rig mirrors a verified operational mechanism: from customs document routing and 120 FPS edge-vision safety interlocks to air-gapped cryptographic accounting vaults.",
        "CHỌN CHẾ ĐỘ VẬN HÀNH THỰC CHỨNG (3 REGIMES)": "SELECT VERIFIED OPERATING REGIME (3 REGIMES)",
        "Chế Độ 01 · Đối Soát XNK & Khóa Xuất Xứ e-CO (RVC 48.6%)": "Regime 01 · Customs Clearance & Origin Lock e-CO (RVC 48.6%)",
        "Chế Độ 02 · Thị Giác Biên 120 FPS & Liên Động e-PTW HSE": "Regime 02 · 120 FPS Edge Vision & HSE e-PTW Interlock",
        "VisionX Optical Turret · Ngắt Mạch PLC < 12ms": "VisionX Optical Turret · PLC Circuit Trip < 12ms",
        "Chế Độ 03 · Hạch Toán Tự Động VAS 200 & Buồng Mật Mã Air-Gapped": "Regime 03 · Automated VAS 200 Accounting & Air-Gapped Cryptographic Vault",
        "EXECUTIVE HOOK // CHẾ ĐỘ 01": "EXECUTIVE HOOK // REGIME 01",
        "Khóa cứng rủi ro xuất xứ trong 3 giây.": "Eliminate origin compliance exposure in 3 seconds.",
        "RVC 48.6%, đối soát 5 luồng ECUS5-VNACCS hoàn tất dưới 3.2 giây.": "RVC 48.6%, 5-way ECUS5-VNACCS cross-reconciliation finalized under 3.2 seconds.",
        "Cụm van phân phối 5 cổng (Manifold Distributor) tiếp nhận song song 5 luồng tài liệu: PO, Invoice, Packing List, Tờ khai hải quan và B/L. Con trượt quang học (Vernier Slider) cân đo hàm lượng nội địa hóa RVC và kích hoạt van chốt cơ khí (Solenoid Interlock) khóa tờ khai khi lệch mã HS hoặc BOM vượt 0.5%.": "The 5-port manifold distributor ingests 5 parallel document streams: PO, Invoice, Packing List, Customs Declaration, and B/L. The optical vernier slider calculates RVC regional content and triggers a solenoid interlock to halt filing if HS code or BOM drift exceeds 0.5%.",
        "CHUẨN PHÁP LÝ:": "STATUTORY COMPLIANCE:",
        "Thông tư 11/2020/TT-BCT · Nghị định 35/2020/NĐ-CP · EVFTA Protocol 1 & CPTPP · ECUS5-VNACCS": "Circular 11/2020/TT-BCT · Decree 35/2020/ND-CP · EVFTA Protocol 1 & CPTPP · ECUS5-VNACCS",
        "EXECUTIVE HOOK // CHẾ ĐỘ 02": "EXECUTIVE HOOK // REGIME 02",
        "Ngắt nguồn tức thì khi vi phạm an toàn.": "Instant fail-safe trip on safety perimeter breach.",
        "Độ trễ biên < 12ms, nhận diện 99.8%, duy trì OEE > 98.5%.": "Edge latency < 12ms, 99.8% precision, maintaining OEE > 98.5%.",
        "Thấu kính quang học viễn tâm kép (Dual Telecentric Lens) quét liên tục 120 FPS nhận diện hành lang an toàn và PPE, nối cứng vào rơ-le cách ly quang (Galvanic Safety Relay) ngắt mạch PLC trong 12ms độc lập đám mây, kết hợp cảm biến áp điện RCM FFT phân tích phổ rung động trục quay.": "Dual telecentric lenses scan continuously at 120 FPS to monitor safety perimeters and PPE compliance, hardwired to a galvanic safety relay that trips PLC circuitry in 12ms without cloud dependencies, paired with piezoelectric RCM FFT sensors for real-time spindle vibration spectral analysis.",
        "ISO 45001:2018 (Khoản 8.1.2) · ISO 13849-1:2023 (PL e, Cat 4) · RCM FFT ISO 10816-3": "ISO 45001:2018 (Clause 8.1.2) · ISO 13849-1:2023 (PL e, Cat 4) · RCM FFT ISO 10816-3",
        "EXECUTIVE HOOK // CHẾ ĐỘ 03": "EXECUTIVE HOOK // REGIME 03",
        "Xóa bỏ 80% thời gian nhập liệu kế toán.": "Eliminate 80% of manual accounting data entry.",
        "Giảm 80% giờ nhập liệu, SLA 99.999%, cắt giảm 50% TCO.": "80% data entry hours eliminated, 99.999% SLA uptime, 50% TCO reduction.",
        "Buồng mật mã Faraday cô lập mạng vật lý qua công tắc ngắt quang (Air-Gapped Optical Switch). Trụ pittông Zero-Knowledge (ZK Plunger) dập dấu băm SHA-256 / Ed25519 và bánh răng vi sai cơ khí đồng bộ đối ứng Nợ - Có chuẩn VAS 200 với 0 sai số.": "Faraday cryptographic cage physically air-gapped via optical cutoff switch. Zero-Knowledge plunger seals SHA-256 / Ed25519 cryptographic hashes, while mechanical differential gears synchronize double-entry debit-credit ledger under VAS 200 with zero discrepancies.",
        "Thông tư 200/2014/TT-BTC · Luật Kế toán 88/2015/QH13 · Nghị định 13/2023/NĐ-CP · ISO/IEC 27001:2022": "Circular 200/2014/TT-BTC · Accounting Law 88/2015/QH13 · Decree 13/2023/ND-CP · ISO/IEC 27001:2022",
        "TẦN SUẤT GIAO DỊCH & XUNG LƯỢNG HỆ THỐNG": "TRANSACTION FREQUENCY & SYSTEM VELOCITY",
        "Độ Trễ Biên": "Edge Latency",
        "Tỷ Lệ Tự Động Hóa": "Automation Ratio",
        "Tiết Kiệm TCO": "TCO Savings",
        "-80% Giờ Nhập Liệu VAS 200": "-80% VAS 200 Data Entry Hours",
        "Chuẩn Tuân Thủ & Bảo Chứng SHA-256": "Statutory Compliance & SHA-256 Attestation",
        "Nhấp trực tiếp vào từng cụm cơ khí trên bản vẽ hoặc thanh chọn để tách lớp trục Z": "Click directly on any mechanical assembly in the schematic or selector to isolate Z-axis layers",
        "Cụm van 5 cổng đối soát PO · Invoice · Packing List · Tờ khai VNACCS · B/L (< 3.2s)": "5-port manifold reconciling PO · Invoice · Packing List · VNACCS Declaration · B/L (< 3.2s)",
        "DỊCH VỤ CÔNG NGHỆ CHUYÊN SÂU · EXECUTIVE ENGINEERING SERVICES": "ADVANCED TECHNOLOGY SERVICES · EXECUTIVE ENGINEERING SERVICES",
        "Đội Ngũ Kỹ Sư Cấp Cao": "Senior Principal Engineering Team",
        "Đồng Hành Cùng Doanh Nghiệp": "Strategic Enterprise Partnership",
        "Không dừng lại ở việc chuyển giao phần mềm, Innoria đồng hành cùng doanh nghiệp bằng đội ngũ chuyên gia kiến trúc giải pháp giàu kinh nghiệm trong toàn bộ tiến trình số hóa.": "Beyond turnkey software delivery, Innoria partners with enterprises through seasoned solution architects guiding every milestone of your digital transformation journey.",
        "Cam Kết Sẵn Sàng 99.98% SLA": "Guaranteed 99.98% Uptime SLA",
        "Suy Luận Thời Gian Thực < 14ms": "Real-Time Inference < 14ms",
        "Kỷ Luật ISO 27001 & CMMI Cấp 5": "ISO 27001 Security & CMMI Level 5 Rigor",
        "Vận Hành Tự Trị 24/7/365": "24/7/365 Autonomous Operations",
        "01 · DỊCH VỤ AI & 4-LAYER SOP-RAG (MOJO AIaaS)": "01 · AI SERVICES & 4-LAYER SOP-RAG (MOJO AIaaS)",
        "Dịch Vụ AI & 4-Layer Grounded SOP-RAG (Mojo AIaaS)": "AI Services & 4-Layer Grounded SOP-RAG (Mojo AIaaS)",
        "Truy xuất kết hợp Hybrid RRF (BM25 + Dense Vector, k=60) trên 20 quy trình KMS & 160 phân đoạn SOP, kiểm định Entailment >= 0.85 kèm trích dẫn mật mã SHA-256. Hoàn vốn 4.3 tháng (ROI 5.25x).": "Hybrid RRF retrieval (BM25 + Dense Vector, k=60) across 20 KMS processes & 160 SOP chunks, audited with Entailment >= 0.85 and SHA-256 cryptographic citations. 4.3-month payback period (5.25x ROI).",
        "ROI 5.25x (4.3 Tháng)": "5.25x ROI (4.3 Months)",
        "02 · CLEAN-CORE ERP & BÁO GIÁ CPQ < 5 PHÚT (AL2C)": "02 · CLEAN-CORE ERP & CPQ ESTIMATION < 5 MIN (AL2C)",
        "Chuyển Đổi Số Clean-Core ERP & Chu Trình AL2C 7 Bước": "Clean-Core ERP Digital Transformation & 7-Step AL2C Lifecycle",
        "Chuẩn hóa 100 danh mục Fit-to-Standard (68 Class A, 24 Class B, 8 Class C), kế toán VAS TT 200, Hóa đơn điện tử 2 bước 1C26TAA (NĐ 70/2025/NĐ-CP) và động cơ báo giá CPQ < 5 phút.": "Standardizes 100 Fit-to-Standard workflows (68 Class A, 24 Class B, 8 Class C), VAS Circular 200 accounting, 2-step 1C26TAA e-Invoicing (Decree 70/2025/ND-CP), and CPQ quote engine in < 5 minutes.",
        "HĐĐT 1C26TAA 2 Bước": "2-Step 1C26TAA e-Invoicing",
        "03 · PHẦN MỀM TRỌN GÓI & DATA ROOM 9 TẦNG": "03 · TURNKEY SOFTWARE SUITE & 9-TIER DATA ROOM",
        "Phát Triển Phần Mềm Trọn Gói & Sovereign Data Room": "Turnkey Software Engineering & Sovereign Data Room",
        "Kiến trúc Cloud-Native Kubernetes kết hợp Kho dữ liệu doanh nghiệp 9 tầng (978 thư mục, 7,886 tài liệu thực chứng, 11 cấu hình phân quyền RBAC và 28 biểu mẫu quản trị song ngữ).": "Cloud-Native Kubernetes architecture paired with a 9-tier enterprise Data Room (978 directories, 7,886 verified artifacts, 11 granular RBAC access tiers, and 28 bilingual governance templates).",
        "28 Biểu Mẫu Song Ngữ": "28 Bilingual Governance Templates",
        "ROI 5.20x (4.1 Tháng)": "5.20x ROI (4.1 Months)",
        "04 · BIỆT ĐỘI KỸ SƯ CO-ENGINEERING & PORTAL (/my)": "04 · CO-ENGINEERING TASK FORCE & CLIENT PORTAL (/my)",
        "Đội Ngũ Kỹ Sư Đồng Phát Triển & Cổng Khách Hàng (/my)": "Co-Engineering Task Force & Client Portal (/my)",
        "Vận hành biệt đội kỹ sư theo quy trình 7 bước TT 13/2020/TT-BTTTT (thuế KCT Luật 48/2024/QH15), nghiệm thu Timesheet song phương (100% chuẩn / 150% OT) niêm phong SHA-256 trên cổng /my.": "Deploys engineering squads following the 7-step Circular 13/2020/TT-BTTTT protocol (VAT exempt under Law 48/2024/QH15), with bilateral timesheet acceptance (100% standard / 150% OT) cryptographically sealed with SHA-256 on the /my portal.",
        "Portal /my Tự Phục Vụ": "Self-Service /my Portal",
        "ROI 4.06x (3.4 Tháng)": "4.06x ROI (3.4 Months)",
        "MÔ PHỎNG THỰC THỜI": "REAL-TIME SIMULATION",
        "CHẾ ĐỘ 01 · CỔNG KẾT NỐI AI ĐANG KÍCH HOẠT (SUY LUẬN: 11.4ms)": "REGIME 01 · AI GATEWAY ACTIVE (INFERENCE: 11.4ms)",
        "CHỌN KỊCH BẢN KIỂM THỬ THỜI GIAN THỰC:": "SELECT REAL-TIME BENCHMARK SCENARIO:",
        "OCR & Đối Soát HĐĐT NĐ 70/2025": "OCR & Reconciliation for Decree 70/2025 e-Invoicing",
        "AI Agent Điều Độ Xưởng CNC": "AI Agent CNC Shop-Floor Dispatching",
        "YOLO Giám Sát PPE Camera": "YOLO Real-Time PPE Camera Vision",
        "ĐỘ TRỄ P99:": "P99 LATENCY:",
        "TỐC ĐỘ XỬ LÝ:": "THROUGHPUT VELOCITY:",
        "SO SÁNH HIỆU NĂNG VẬN HÀNH TRƯỚC & SAU:": "OPERATIONAL PERFORMANCE BENCHMARK (BEFORE VS. AFTER):",
        "Thủ Công (Cũ)": "Manual Legacy (Before)",
        "Innoria DX (Mới)": "Innoria DX (Modern)",
        "Thời Gian Xử Lý / Đơn": "Processing Time per Order",
        "2.8 Giây (Giảm 98.4%)": "2.8 Seconds (98.4% Reduction)",
        "Tỷ Lệ Sai Sót Nhập Liệu": "Data Entry Error Rate",
        "0.00% (Khử Triệt Để)": "0.00% (Zero-Error Elimination)",
        "Chi Phí Vận Hành / Tháng": "Monthly Operating Expenditure (OPEX)",
        "18,500,000 đ (Tiết kiệm 85%)": "VND 18,500,000 (85% Cost Savings)",
        "LUỒNG TỰ ĐỘNG HÓA ROBUST COGNITIVE PIPELINE": "ROBUST COGNITIVE PIPELINE AUTOMATION WORKFLOW",
        "1. Quét Hóa Đơn Email / Barcode": "1. Email / Barcode Invoice Ingestion & OCR",
        "2. RPA Bóc Tách B01 / B02": "2. RPA Extraction for B01 / B02 Forms",
        "3. Khớp Lệnh Mua PO": "3. Automated PO 3-Way Matching",
        "4. Tự Động Định Khoản 154/621/632": "4. Automated General Ledger Posting (Accounts 154/621/632)",
        "✓ Đã kiểm chứng trên 5 Archetype Doanh nghiệp: Hoàn vốn 3.4 - 6.2 tháng · Tỷ suất ROI 3 năm đạt 4.06x - 5.25x · Báo giá CPQ < 5 phút": "✓ Proven Across 5 Enterprise Archetypes: 3.4 - 6.2 Month Payback · 3-Year ROI 4.06x - 5.25x · Instant CPQ Quotation < 5 Mins",
        "KIẾN TRÚC MICROSERVICES CLUSTER TRÊN KUBERNETES": "KUBERNETES-NATIVE MICROSERVICES CLUSTER ARCHITECTURE",
        "LƯU LƯỢNG TRUY CẬP:": "TRAFFIC THROUGHPUT:",
        "ĐỘ TRỄ VẬN HÀNH:": "OPERATIONAL LATENCY:",
        "KÍCH HOẠT PHỤ TẢI ĐỈNH 50,000 RPS": "BURST CAPACITY ACTIVATION: 50,000 RPS",
        "✓ Công Nghệ: Docker · Kubernetes · Kafka · Go/Python · Postgres Sharding": "✓ Technology Stack: Docker · Kubernetes · Kafka · Go/Python · Postgres Sharding",
        "MẠNG LƯỚI TRUNG TÂM PHÁT TRIỂN PHẦN MỀM CHUYÊN TRÁCH:": "SPECIALIZED SOFTWARE DEVELOPMENT CENTER NETWORK:",
        "TIÊU CHUẨN QUỐC TẾ": "GLOBAL INDUSTRY STANDARDS",
        "Hà Nội (AI Lab)": "Hanoi (AI Lab)",
        "Đà Nẵng (Cloud Hub)": "Da Nang (Cloud Hub)",
        "Quy mô nhân sự chuyên trách:": "Dedicated Engineering Headcount:",
        "Lĩnh vực chuyên môn trọng tâm:": "Core Technical Competencies:",
        "Lãnh đạo kỹ thuật (Squad Lead):": "Technical Leadership (Squad Lead):",
        "Mô hình biệt đội (Squad Architecture):": "Squad Team Architecture:",
        "Cam kết khởi động dự án & cử chuyên gia trong 72 giờ": "Guaranteed 72-Hour Project Kickoff & SME Mobilization",
        "⚡ Dự Toán & Cấu Hình Trực Tiếp Với AI Concierge": "⚡ Interactive Estimation & Scoping with AI Concierge",
        "Tham Vấn Kiến Trúc Sư Cấp Cao": "Consult Enterprise Solutions Architect",
        "GIẢI PHÁP CHUYÊN SÂU · SOLUTIONS": "ENTERPRISE SOLUTIONS & INDUSTRY VERTICALS",
        "Ứng Dụng Thực Chiến Cho Từng Ngành Công Nghiệp": "Mission-Critical Implementations Tailored for Vertical Industries",
        "Được bảo chứng qua hàng trăm dự án sản xuất, kho vận và chuỗi cung ứng với các yêu cầu tuân thủ khắt khe nhất.": "Validated across hundreds of manufacturing, logistics, and supply chain deployments with mission-critical compliance rigor.",
        "AN TOÀN HSE": "HSE & OCCUPATIONAL SAFETY",
        "Permit to Work Điện Tử": "Electronic Permit to Work (e-PTW)",
        "Số hóa toàn diện giấy phép làm việc nguy hiểm (hàn cắt, làm việc trên cao, không gian kín). Tích hợp chữ ký số và cảnh báo tự động khi phát hiện công nhân không mang đồ bảo hộ.": "End-to-end digital transformation of hazardous work permits (hot work, working at heights, confined spaces). Integrated with digital signatures and automated alerts upon PPE non-compliance detection.",
        "100% Không dùng giấy": "100% Paperless Operations",
        "0 Tai nạn vi phạm": "Zero Safety Non-Compliance Incidents",
        "BẢO TRÌ DỰ BÁO": "PREDICTIVE MAINTENANCE (PdM)",
        "Quản Trị Độ Tin Cậy Thiết Bị": "Asset Reliability & Uptime Management",
        "Thu thập dữ liệu cảm biến rung động, nhiệt độ vòng bi động cơ và áp suất thủy lực. Mô hình AI phân tích phổ tần FFT để cảnh báo hỏng hóc trước 14 ngày.": "Continuous telemetry ingestion of vibration, bearing thermal dynamics, and hydraulic pressure. AI models perform FFT spectral analysis to detect impending equipment failures up to 14 days in advance.",
        "OEE Thiết Bị > 98.5%": "Equipment OEE > 98.5%",
        "Giảm 40% dừng máy": "40% Unplanned Downtime Reduction",
        "XUẤT NHẬP KHẨU": "GLOBAL TRADE & CUSTOMS",
        "Hệ thống bóc tách định mức BOM sản phẩm, đối soát tiêu chuẩn xuất xứ (RVC, CTC) theo các hiệp định thương mại EVFTA, CPTPP và kết nối trực tiếp cổng dịch vụ công.": "Automated BOM explosion, multi-tier origin qualification auditing (RVC, CTC) across EVFTA and CPTPP frameworks, integrated directly with national single-window customs portals.",
        "Thông quan < 2 giờ": "Customs Clearance < 2 Hours",
        "Khớp chuẩn 100% FTA": "100% FTA Tariff Compliance",
        "AI THỊ GIÁC": "INDUSTRIAL COMPUTER VISION",
        "Kiểm tra lỗi sản phẩm cơ khí chính xác, mối hàn và bề mặt vật liệu ngay trên dây chuyền với camera công nghiệp FPS cao. Phát hiện lỗi micro không thể thấy bằng mắt thường.": "High-speed in-line optical inspection for precision engineering, weld integrity, and surface defect detection using high-FPS industrial cameras. Detects microscopic anomalies imperceptible to the human eye.",
        "99.8% Chuẩn xác": "99.8% Defect Classification Accuracy",
        "Tốc độ < 50ms/khung": "Latency < 50ms/Frame",
        "BÁN LẺ & FMCG": "RETAIL & FMCG",
        "CPG Visualytics & Quầy Kệ": "CPG Shelf Visualytics & Execution",
        "Nhận diện tỷ lệ diện tích trưng bày (Share of Shelf), tự động phát hiện hàng cận date, hết hạn sử dụng hoặc đứt gãy nguồn cung trên quầy kệ thông qua ảnh chụp thực tế.": "Automated Share-of-Shelf recognition, real-time auditing of near-expiry SKUs, out-of-stock scenarios, and on-shelf availability via field computer vision.",
        "Đối soát trong 3 giây": "3-Second Store Shelf Audit",
        "Tăng 18% doanh số kệ": "18% On-Shelf Revenue Uplift",
        "TÀI CHÍNH": "FINANCE & CONTROLLING",
        "TT 200 · NĐ 70/2025": "Circular 200 · Decree 70/2025",
        "Quản Trị Tài Chính VAS 200": "VAS 200 Financial Governance & Compliance",
        "Tự động kết nối hóa đơn điện tử Tổng Cục Thuế, tự động đối chiếu hóa đơn đầu vào với phiếu nhập kho và định khoản kế toán không cần gõ tay chứng từ.": "Native integration with General Department of Taxation e-invoicing portals, automated 3-way matching between vendor invoices and goods receipts with zero-touch ledger posting.",
        "Tiết kiệm 80% giờ làm": "80% Time Reduction in Bookkeeping",
        "Không sai sót số liệu": "Zero Data Discrepancies",
        "Thị Giác Máy Tính Giám Sát An Toàn HSE": "Computer Vision HSE Safety Surveillance",
        "Giám Sát Hiện Trường An Toàn Lao Động": "On-Site Occupational Safety & HSE Surveillance",
        "Bằng": "Powered by",
        "Camera Trí Tuệ Nhân Tạo (AI Vision)": "Artificial Intelligence Vision (AI Vision)",
        "Nhận diện trang bị BHLĐ (Mũ bảo hộ, Áo phản quang), ranh giới vùng nguy hiểm và tự động kích hoạt còi hú hiện trường, khóa liên động máy cơ khí và đẩy hồ sơ sự cố lên Insilos ERP và Vertical GRC thời gian thực.": "Automated PPE detection (Safety Helmets, Hi-Vis Vests), hazardous boundary monitoring, real-time audio-visual field alarms, machine safety interlocks, and incident streaming to Insilos ERP and Vertical GRC.",
        "PHIM CHUYÊN ĐỀ HSE": "HSE FEATURETTE",
        "Video Toàn Cảnh: Giám Sát An Toàn Lao Động HSE & PPE Bằng AI Vision": "Overview Showcase: HSE & PPE Workplace Safety Monitoring via Industrial AI Vision",
        "Trải nghiệm video điện ảnh 75 giây mô phỏng quy trình AI nhận diện trang bị BHLĐ, còi hú hiện trường và đối soát 2 chiều Insilos ERP & Vertical GRC.": "Experience a 75-second cinematic simulation showcasing real-time AI PPE detection, on-site alarm triggering, and bi-directional reconciliation with Insilos ERP & Vertical GRC.",
        "Phát Phim HSE 75s": "Play 75s HSE Featurette",
        "Angle 1: Hiện Trường & Tháp Cẩu": "Angle 1: Field Site & Tower Crane",
        "Angle 2: Hàn Tự Động SS400": "Angle 2: Automated SS400 Welding",
        "Angle 3: Cổng Kiểm Soát PPE Gate": "Angle 3: PPE Access Control Gate",
        "Angle 4: Kỹ Sư Phân Xưởng PPE": "Angle 4: Workshop PPE Engineers",
        "Xem Phim HSE 75s (4K Thuyết Minh)": "Watch 75s HSE Featurette (4K Narration)",
        "CAM-01 // Giám Sát An Toàn Hiện Trường & Tháp Cẩu": "CAM-01 // Field Site & Tower Crane Safety Monitoring",
        "Trạng Thái: Chuẩn Vận Hành": "Status: Operational Standard",
        "GIÁM SÁT VIÊN #01 // 99.4%": "SUPERVISOR #01 // 99.4%",
        "MŨ BẢO HỘ TIÊU CHUẨN // 99.7%": "CERTIFIED SAFETY HELMET // 99.7%",
        "KÍNH BẢO HỘ TIA UV // 98.6%": "UV SAFETY GLASSES // 98.6%",
        "GĂNG TAY & BỘ ĐÀM // 98.9%": "SAFETY GLOVES & TWO-WAY RADIO // 98.9%",
        "BÁN KÍNH QUAY THÁP CẨU // DROP ZONE // 100.0%": "TOWER CRANE SLEWING RADIUS // DROP ZONE // 100.0%",
        "MŨ BẢO HỘ TIÊU CHUẨN": "CERTIFIED SAFETY HELMET",
        "ĐỘ TRỄ:": "LATENCY:",
        "VỊ TRÍ:": "LOCATION:",
        "Khu Thi Công Công Trình Trọng Điểm // Tháp Cẩu & Giàn Giáo Thép": "Critical Construction Zone // Tower Crane & Steel Scaffolding",
        "ĐỘ PHÂN GIẢI:": "RESOLUTION:",
        "ĐỘ TRỄ AI:": "AI INFERENCE LATENCY:",
        "GIAO THỨC:": "PROTOCOL:",
        "LỚP LỌC THỊ GIÁC AI": "AI VISION OVERLAY FILTERS",
        "Bật / Tắt Lớp Lọc AI Vision": "Toggle AI Vision Overlays",
        "Tùy biến hiển thị các lớp nơ-ron nhận diện mũ bảo hộ, áo phản quang và ranh giới vùng nguy hiểm với độ chính xác trên 99%.": "Customize neural detection overlays for safety helmets, hi-vis vests, and hazardous zone perimeters with >99% precision.",
        "Mũ Bảo Hộ (Safety Helmet)": "Safety Helmet",
        "Áo Phản Quang (Hi-Vis Vest)": "Hi-Vis Vest",
        "Ranh Giới Vùng Nguy Hiểm": "Hazardous Zone Perimeter",
        "Lớp lọc tự động kích hoạt theo ca làm việc": "Overlays automatically activate according to operating shifts",
        "TƯƠNG TÁC HIỆN TRƯỜNG": "FIELD-LEVEL INTERACTION",
        "CÒI HÚ ĐANG PHÁT": "ALARM ACTIVE",
        "Mô Phỏng Vi Phạm & Cảnh Báo": "Violation & Alert Simulation",
        "Kích hoạt còi hú âm học kép FM (880Hz - 1240Hz), viền cảnh báo đỏ rực và bật cửa sổ khẩn cấp chuẩn ISO 45001.": "Triggers dual-frequency FM acoustic siren (880Hz - 1240Hz), vivid red alert strobe, and ISO 45001 emergency incident modal.",
        "Mô Phỏng Vi Phạm PPE Hiện Trường": "Simulate Field PPE Non-Compliance",
        "Đặt Lại Trạng Thái": "Reset State",
        "Bật/Tắt Còi": "Mute / Unmute Siren",
        "Còi hú ứng dụng Web Audio API không phụ thuộc file âm thanh ngoài": "Synthesized siren powered by Web Audio API without external audio dependencies",
        "LIÊN THÔNG HỆ THỐNG": "ENTERPRISE INTEROPERABILITY",
        "Dữ Liệu Đối Soát ERP & GRC": "ERP & GRC Reconciliation Data",
        "Đồng bộ hai chiều giữa lệnh bảo trì, lệnh sản xuất trên Insilos ERP và hồ sơ cấp phép an toàn e-PTW trên Vertical GRC.": "Bi-directional synchronization between maintenance work orders, production routing in Insilos ERP, and e-PTW safety permits in Vertical GRC.",
        "Lệnh công tác:": "Work Order:",
        "Kiểm định xe cẩu chuyên dụng & thiết bị nâng (51C-982.45)": "Heavy Crane & Rigging Equipment Inspection (51C-982.45)",
        "Hiệu suất OEE:": "Equipment OEE:",
        "Cảm biến:": "Sensor Telemetry:",
        "Mở Lệnh Công Tác Trên Insilos ERP": "Open Work Order in Insilos ERP",
        "Mở Hồ Sơ Cấp Phép Vertical GRC": "Open Safety Permit in Vertical GRC",
        "Cảnh Báo Khẩn Cấp: Phát Hiện Vi Phạm BHLĐ (AI PPE Detection)": "Critical Alarm: PPE Non-Compliance Detected (AI PPE Detection)",
        "Mã Vi Phạm:": "Incident ID:",
        "Phát hiện Kỹ thuật viên không đội Mũ bảo hộ bước vào Ranh giới Vùng Nguy hiểm Máy Cắt Laser CNC 12kW!": "Technician detected without Safety Helmet entering 12kW CNC Laser Cutter Hazardous Exclusion Zone!",
        "Thời gian ghi nhận:": "Timestamp:",
        "Góc quan sát:": "Camera Angle:",
        "CAM-01. Xưởng Cắt Laser CNC SS400": "CAM-01. SS400 CNC Laser Cutting Workshop",
        "Vị trí hiện trường:": "Field Location:",
        "Khu A3 · Trạm Cắt Laser Trumpf TruLaser 5030": "Zone A3 · Trumpf TruLaser 5030 Laser Station",
        "Khung pháp lý:": "Regulatory Standard:",
        "Liên động máy móc:": "Machine Interlock:",
        "Mở Hồ Sơ GRC": "Open GRC Incident File",
        "Mở Lệnh Insilos ERP": "Open Insilos ERP Order",
        "Tắt Còi & Đặt Lại Trạng Thái": "Silence Alarm & Reset State",
        "Trình duyệt không hỗ trợ phát trực tiếp định dạng video MP4.": "Your browser does not support inline MP4 video playback.",
        "Độ Phân Giải:": "Resolution:",
        "Âm Thanh:": "Audio Format:",
        "Thuyết Minh:": "Voiceover:",
        "Tiếng Việt (Executive)": "Vietnamese (Executive)",
        "Tải 4 SOPs & 6 Biểu Mẫu HSE": "Download 4 HSE SOPs & 6 Form Templates",
        "Đóng": "Close",
        "Tỷ Suất ROI Định Lượng 3 Năm (SOP-DGM-15)": "Quantitative 3-Year ROI (SOP-DGM-15)",
        "< 5 Phút": "< 5 Mins",
        "Báo Giá Rapid CPQ & 100 Quy Tắc FTS": "Rapid CPQ Quotation & 100 FTS Business Rules",
        "Tài Liệu Data Room 9 Tầng · 11 RBAC": "9-Tier Data Room Repository · 11 RBAC Profiles",
        "3.4-6.2 Tháng": "3.4-6.2 Months",
        "Chu Kỳ Hoàn Vốn Thực Nghiệm (Payback)": "Empirical Payback Period",
        "ROI 4.06x · Hoàn vốn 3.4 tháng": "4.06x ROI · 3.4-Month Payback",
        "Gói 384M VNĐ → Lợi ích ròng 1,176M VNĐ. Nghiệm thu Timesheet song phương (100% chuẩn / 150% OT) ký số SHA-256 trên cổng /my.": "Package VND 384M → Net Financial Return VND 1,176M. Bi-lateral timesheet sign-off (100% standard / 150% OT) with SHA-256 digital attestation on /my portal.",
        "02 · THUẾ, HĐĐT 1C26TAA & LƯƠNG": "02 · TAX, 1C26TAA E-INVOICE & PAYROLL",
        "ROI 4.51x · Hoàn vốn 4.8 tháng": "4.51x ROI · 4.8-Month Payback",
        "Gói 165M VNĐ → Lợi ích ròng 579M VNĐ. Kế toán VAS TT 200, HĐĐT 2 bước NĐ 70/2025/NĐ-CP và BHXH 8% / BHYT 1.5% / BHTN 1%.": "Package VND 165M → Net Financial Return VND 579M. Accounting compliant with VAS Circular 200, 2-step e-invoicing under Decree 70/2025/ND-CP, and statutory social insurance (SI 8% / HI 1.5% / UI 1%).",
        "03 · CLEAN-CORE ERP TỰ HÀNH": "03 · AUTONOMOUS CLEAN-CORE ERP",
        "ROI 4.07x · Hoàn vốn 6.2 tháng": "4.07x ROI · 6.2-Month Payback",
        "Gói 450M VNĐ → Lợi ích ròng 1,380M VNĐ. Hợp nhất Lead-to-Cash (O2C), Procure-to-Pay (P2P), WMS/MES và Data Room 9 tầng.": "Package VND 450M → Net Financial Return VND 1,380M. Seamlessly unifies Lead-to-Cash (O2C), Procure-to-Pay (P2P), WMS/MES, and 9-Tier Data Room.",
        "04 · GRC, EHS & BẢO MẬT DỮ LIỆU": "04 · GRC, EHS & DATA PRIVACY",
        "ROI 5.20x · Hoàn vốn 4.1 tháng": "5.20x ROI · 4.1-Month Payback",
        "Gói 225M VNĐ → Lợi ích ròng 945M VNĐ. Tuân thủ ISO/IEC 27001:2022, ISO/IEC 27701, Nghị định 13/2023/NĐ-CP và rào cản e-PTW/LOTO.": "Package VND 225M → Net Financial Return VND 945M. Fully compliant with ISO/IEC 27001:2022, ISO/IEC 27701, Decree 13/2023/ND-CP, and e-PTW/LOTO digital guardrails.",
        "ROI 5.25x · Hoàn vốn 4.3 tháng": "5.25x ROI · 4.3-Month Payback",
        "Gói 180M VNĐ → Lợi ích ròng 765M VNĐ. Hybrid RRF (k=60) trên 20 quy trình KMS & 160 phân đoạn SOP, Entailment >= 0.85.": "Package VND 180M → Net Financial Return VND 765M. Hybrid RRF (k=60) indexing across 20 KMS workflows & 160 SOP chunks, Entailment >= 0.85.",
        "AI Dự Toán": "AI Scoping & Estimation",
        "Dự toán phần mềm & Thuê Squad Kỹ sư AI/ERP": "Software Estimation & AI/ERP Dedicated Co-Dev Squads",
        "Báo Giá": "Quotation",
        "💬 Hội Thoại AI": "💬 AI Consultation",
        "🧮 Dịch Vụ & Dự Toán": "🧮 Services & Cost Estimation",
        "📅 Nhận Báo Giá": "📅 Request Quotation",
        "Hội Thoại AI": "AI Consultation",
        "Dịch Vụ & Dự Toán": "Services & Cost Estimation",
        "Nhận Báo Giá": "Request Quotation",
        "Kính chào Quý khách! Tôi là": "Welcome! I am your",
        "Executive AI Concierge & Kiến trúc sư Dự toán": "Executive AI Concierge & Scoping Architect",
        "của Innoria.": "at Innoria.",
        "Tôi hỗ trợ tư vấn kiến trúc, cấu hình đội ngũ kỹ sư phần mềm (Dedicated Co-Dev Squad theo": "I provide enterprise architectural advisory, engineering squad scoping (Dedicated Co-Dev Squad pursuant to",
        "Thông tư 13/2020/TT-BTTTT": "Circular 13/2020/TT-BTTTT",
        "), phát triển phần mềm trọn gói (": "), turnkey custom software development (",
        ") và báo giá dự toán tức thì cho:": ") and real-time scoping quotations for:",
        "Squad Kỹ Sư Đồng Phát Triển & Turnkey Software:": "Dedicated Co-Dev Engineering Squads & Turnkey Software:",
        "Xây dựng hệ thống may đo, Web/Mobile App & tích hợp AI/ERP.": "Custom enterprise architectures, Web/Mobile engineering & AI/ERP integration.",
        "Quản trị tài chính kế toán VAS (TT 200/133), WMS & Hóa đơn điện tử": "Financial governance under VAS (Circular 200/133), WMS & e-Invoicing",
        "(Nghị định 70/2025/NĐ-CP).": "(Decree 70/2025/ND-CP).",
        "Quản trị rủi ro GRC, bảo vệ dữ liệu": "Vertical GRC risk governance, data protection under",
        "ISO 27701 / Nghị định 13/2023": "ISO 27701 / Decree 13/2023/ND-CP",
        "& truy xuất e-CO.": "& e-CO origin traceability.",
        "Tác tử AL2C Swarm, Grounded RAG triệt tiêu ảo giác & Hiện đại hóa mã nguồn kế thừa.": "AL2C Swarm Agents, Hallucination-free Grounded RAG & Legacy Modernization.",
        "Quý khách có thể chọn trực tiếp gói dịch vụ bên dưới để": "You can select a service package below to",
        "Cấu hình & Xem dự toán tự động": "Configure & View Automated Estimation",
        "hoặc đặt câu hỏi cho AI!": "or consult the AI directly!",
        "Từ 84.000.000 ₫ / tháng": "From VND 84,000,000 / month",
        "Squad Kỹ Sư Đồng Phát Triển (Dedicated Co-Dev Squad)": "Dedicated Co-Dev Engineering Squad",
        "Cung cấp đội ngũ Kỹ sư Phần mềm, Solution Architect & QA/SecOps chuyên trách theo chuẩn Agile/Scrum, tích hợp giám sát năng suất AGY Telemetry và định mức quy trình phần mềm Thông tư 13/2020/TT-BTTTT.": "Dedicated team of Senior Software Engineers, Solution Architects & QA/SecOps operating under Agile/Scrum, integrated with AGY Telemetry productivity telemetry and software process norms under Circular 13/2020/TT-BTTTT.",
        "⚙️ Dự Toán & Cấu Hình": "⚙️ Configure & Estimate",
        "📅 Nhận Báo Giá Gói Này": "📅 Request Quote for this Package",
        "Dự Toán & Cấu Hình": "Configure & Estimate",
        "Nhận Báo Giá Gói Này": "Request Quote for this Package",
        "Từ 144.000.000 ₫ / giai đoạn": "From VND 144,000,000 / milestone",
        "Phát Triển Phần Mềm Trọn Gói (Turnkey Custom Software)": "Turnkey Custom Software Development",
        "Thiết kế kiến trúc, phát triển trọn gói hệ thống phần mềm doanh nghiệp, cổng giao dịch B2B/B2C, Web/Mobile App đặc thù theo phương pháp luận 5-Gate Enterprise (Prepare → Explore → Realize → Deploy → Run).": "Architecture design and turnkey delivery of enterprise platforms, B2B/B2C transactional portals, and specialized Web/Mobile apps executed under the 5-Gate Enterprise Methodology (Prepare → Explore → Realize → Deploy → Run).",
        "VAS 200/133 • NĐ 70/2025": "VAS 200/133 • Decree 70/2025",
        "Từ 140.000.000 ₫ / gói": "From VND 140,000,000 / package",
        "Insilos Clean-Core ERP & HĐĐT 1C26TAA": "Insilos Clean-Core ERP & 1C26TAA E-Invoicing",
        "Nền tảng ERP thế hệ mới hợp nhất Kế toán chuẩn VAS (Thông tư 200/133) & IFRS, Chuỗi cung ứng WMS, Sản xuất MRP, Nhân sự Tiền lương BHXH/PIT 2026 và Hóa đơn điện tử 1C26TAA.": "Next-generation ERP platform unifying VAS (Circular 200/133) & IFRS accounting, WMS supply chain, MRP manufacturing, 2026 HR/Payroll (SI/PIT), and 1C26TAA e-invoicing.",
        "ISO 27701 • NĐ 13/2023": "ISO 27701 • Decree 13/2023/ND-CP",
        "Từ 76.000.000 ₫ / khung": "From VND 76,000,000 / scope",
        "Hệ thống Quản trị Rủi ro Doanh nghiệp (ERM), Ma trận Kiểm soát Nội bộ (RCM), bảo vệ dữ liệu cá nhân Nghị định 13/2023/NĐ-CP (ISO 27701), truy xuất nguồn gốc xuất xứ e-CO và kiểm kê ESG/CSRD.": "Enterprise Risk Management (ERM), Risk & Control Matrix (RCM), Decree 13/2023/ND-CP personal data protection (ISO 27701), digital e-CO origin traceability, and ESG/CSRD reporting.",
        "Grounded RAG • Điểm xác thực:": "Grounded RAG • Attestation Score:",
        "Trích dẫn kiểm chứng KMS (": "KMS Verified Citations (",
        "nguồn)": "sources)",
        "🧮 Mở Công Cụ Dự Toán Dịch Vụ Phần Mềm": "🧮 Open Software Scoping & Estimation Tool",
        "👨‍💻 Tư vấn thuê Squad Kỹ sư (TT 13/2020)": "👨‍💻 Dedicated Squad Advisory (Circular 13/2020)",
        "🏗️ Quy trình Phần mềm Trọn gói (Turnkey)": "🏗️ Turnkey Software Lifecycle",
        "📅 Nhận Báo Giá & Hồ Sơ Năng Lực": "📅 Request Quote & Capability Statement",
        "Mở Công Cụ Dự Toán Dịch Vụ Phần Mềm": "Open Software Scoping & Estimation Tool",
        "Tư vấn thuê Squad Kỹ sư (TT 13/2020)": "Dedicated Squad Advisory (Circular 13/2020)",
        "Quy trình Phần mềm Trọn gói (Turnkey)": "Turnkey Software Lifecycle",
        "Nhận Báo Giá & Hồ Sơ Năng Lực": "Request Quote & Capability Statement",
        "Khám phá nhanh Dịch vụ Phần mềm & Giải pháp:": "Quick Explore Software Services & Solutions:",
        "👨‍💻 Thuê Squad Kỹ sư Đồng phát triển (TT 13/2020)": "👨‍💻 Dedicated Co-Dev Engineering Squad (Circular 13/2020)",
        "🏗️ Phát triển Phần mềm Trọn gói (Turnkey)": "🏗️ Turnkey Software Development",
        "📊 Báo giá Clean-Core ERP & HĐĐT 1C26TAA": "📊 Clean-Core ERP & 1C26TAA E-Invoice Pricing",
        "🛡️ Tuân thủ ISO 27701 / GRC / e-CO": "🛡️ ISO 27701 / GRC / e-CO Compliance",
        "Thuê Squad Kỹ sư Đồng phát triển (TT 13/2020)": "Dedicated Co-Dev Engineering Squad (Circular 13/2020)",
        "Phát triển Phần mềm Trọn gói (Turnkey)": "Turnkey Software Development",
        "Báo giá Clean-Core ERP & HĐĐT 1C26TAA": "Clean-Core ERP & 1C26TAA E-Invoice Pricing",
        "Tuân thủ ISO 27701 / GRC / e-CO": "ISO 27701 / GRC / e-CO Compliance",
        "WAF Anti-Spam & Anti-Harassment · TT 13/2020/TT-BTTTT · ISO/IEC 27701 & NĐ 13/2023/NĐ-CP": "WAF Anti-Spam & Anti-Harassment · Circular 13/2020/TT-BTTTT · ISO/IEC 27701 & Decree 13/2023/ND-CP",
    };

    /**
     * Normalize whitespace (including NBSP \u00A0 and multi-line breaks) for deterministic phrase lookup.
     * @param {string} str
     * @returns {string}
     */
    function normalizePhraseKey(str) {
        return String(str || "")
            .replace(/[\u00A0\s]+/g, " ")
            .trim()
            .toLowerCase();
    }

    const INNORIA_NORMALIZED_VI = {};
    const INNORIA_REVERSE_PHRASES = {};
    for (const [viPhrase, enPhrase] of Object.entries(INNORIA_SEMANTIC_PHRASES)) {
        INNORIA_NORMALIZED_VI[normalizePhraseKey(viPhrase)] = enPhrase;
        INNORIA_REVERSE_PHRASES[normalizePhraseKey(enPhrase)] = viPhrase;
    }

    class InnoriaI18nEngine {
        constructor() {
            this.currentLang = "vi";
            this.observer = null;
            this.isMutating = false;
            this.mutationDebounceTimer = null;
            this.boundInit = this.init.bind(this);
            this.boundMutations = this.handleMutations.bind(this);
        }

        /**
         * Detect active language with URL path (/en or /en/...) taking highest priority.
         */
        detectLanguage() {
            try {
                const pathname = window.location.pathname || "";
                const searchParams = new URLSearchParams(window.location.search);
                const queryLang = searchParams.get("lang");
                if (pathname === "/en" || pathname.startsWith("/en/")) {
                    localStorage.setItem("innoria_lang", "en");
                    return "en";
                }
                if (pathname === "/vi" || pathname.startsWith("/vi/")) {
                    localStorage.setItem("innoria_lang", "vi");
                    return "vi";
                }
                if (queryLang === "en" || queryLang === "vi") {
                    localStorage.setItem("innoria_lang", queryLang);
                    return queryLang;
                }
                // On root or non-/en path, if user explicitly navigated to VN URL via #lang_toggle_vi, keep vi
                const storedLang = localStorage.getItem("innoria_lang");
                if (storedLang === "en" && searchParams.get("keep_lang") === "1") {
                    return "en";
                }
            } catch (_e) {
                // Ignore storage errors
            }
            return "vi";
        }

        init() {
            this.currentLang = this.detectLanguage();
            this.updateHtmlLangAttribute();
            this.wireLanguageToggles();
            this.wirePriorityFileDropzones();
            this.translatePage(this.currentLang);
            this.initObserver();

            window.dispatchEvent(
                new CustomEvent("innoria:i18n:ready", {
                    detail: { lang: this.currentLang },
                })
            );
        }

        updateHtmlLangAttribute() {
            document.documentElement.setAttribute("lang", this.currentLang);
            document.documentElement.classList.toggle("innoria-lang-en", this.currentLang === "en");
            document.documentElement.classList.toggle("innoria-lang-vi", this.currentLang === "vi");
        }

        wireLanguageToggles() {
            const toggleEn = document.getElementById("lang_toggle_en");
            const toggleVi = document.getElementById("lang_toggle_vi");

            if (toggleEn && !toggleEn.dataset.i18nWired) {
                toggleEn.dataset.i18nWired = "1";
                toggleEn.addEventListener("click", () => {
                    try {
                        localStorage.setItem("innoria_lang", "en");
                    } catch (_e) {}
                });
            }

            if (toggleVi && !toggleVi.dataset.i18nWired) {
                toggleVi.dataset.i18nWired = "1";
                toggleVi.addEventListener("click", () => {
                    try {
                        localStorage.setItem("innoria_lang", "vi");
                    } catch (_e) {}
                });
            }

            document.querySelectorAll("[data-innoria-lang-switch]").forEach((btn) => {
                if (btn.dataset.i18nWired) return;
                btn.dataset.i18nWired = "1";
                btn.addEventListener("click", (ev) => {
                    ev.preventDefault();
                    const targetLang = btn.getAttribute("data-innoria-lang-switch");
                    if (targetLang === "en" || targetLang === "vi") {
                        this.setLanguage(targetLang);
                    }
                });
            });

            this.updateToggleUiState();
        }

        updateToggleUiState() {
            const toggleEn = document.getElementById("lang_toggle_en");
            const toggleVi = document.getElementById("lang_toggle_vi");
            if (toggleEn) {
                toggleEn.classList.toggle("active", this.currentLang === "en");
                toggleEn.classList.toggle("is-active", this.currentLang === "en");
                toggleEn.setAttribute("aria-pressed", this.currentLang === "en" ? "true" : "false");
            }
            if (toggleVi) {
                toggleVi.classList.toggle("active", this.currentLang === "vi");
                toggleVi.classList.toggle("is-active", this.currentLang === "vi");
                toggleVi.setAttribute("aria-pressed", this.currentLang === "vi" ? "true" : "false");
            }
        }

        /**
         * Wire interactive feedback on all Priority File Attachment inputs (.innoria-file-input).
         * When user selects files, immediately display file count, names, total size, and Fast-Track Priority SLA badge.
         */
        wirePriorityFileDropzones(root = document) {
            const inputs = root.querySelectorAll(".innoria-file-input, input[type='file'][name='quote_attachments']");
            inputs.forEach((input) => {
                if (input.dataset.priorityDropzoneWired === "1") {
                    return;
                }
                input.dataset.priorityDropzoneWired = "1";
                input.addEventListener("change", () => {
                    const files = input.files ? Array.from(input.files) : [];
                    const dropzone = input.closest(".innoria-priority-dropzone") || input.parentElement;
                    if (!dropzone) return;
                    const summaryEl = dropzone.querySelector(".innoria-attached-files-summary");
                    const badgeEl = dropzone.querySelector(".innoria-dropzone-status-badge");
                    const isEn = this.currentLang === "en";

                    if (files.length > 0) {
                        const totalKb = Math.max(
                            1,
                            Math.round(files.reduce((acc, f) => acc + (f.size || 0), 0) / 1024)
                        );
                        const names = files
                            .slice(0, 3)
                            .map((f) => f.name)
                            .join(", ");
                        if (summaryEl) {
                            summaryEl.classList.remove("d-none");
                            summaryEl.classList.add("d-inline-flex", "align-items-center", "justify-content-end", "gap-1", "w-100");
                            const summaryText = isEn
                                ? `Attached ${files.length} file(s) (${names} · ${totalKb} KB) — Fast-Track Priority Quote (< 2h SLA) Activated!`
                                : `Đã đính kèm ${files.length} tệp (${names} · ${totalKb} KB) — Đã kích hoạt Báo Giá Ưu Tiên (< 2 giờ)!`;
                            summaryEl.innerHTML = `<svg class="ph-duotone ph-check-circle" style="width:13px;height:13px;flex-shrink:0;" aria-hidden="true"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-check-circle"/></svg><span></span>`;
                            summaryEl.querySelector("span").textContent = summaryText;
                        }
                        if (badgeEl) {
                            badgeEl.style.background = "#005F73";
                            badgeEl.style.color = "#FFFFFF";
                            const badgeText = isEn
                                ? `PRIORITY ACTIVE (${files.length} FILE${files.length > 1 ? "S" : ""})`
                                : `ĐÃ KÍCH HOẠT ƯU TIÊN (${files.length} FILE)`;
                            badgeEl.innerHTML = `<svg class="ph-duotone ph-check-circle" style="width:12px;height:12px;flex-shrink:0;" aria-hidden="true"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-check-circle"/></svg><span></span>`;
                            badgeEl.querySelector("span").textContent = badgeText;
                        }
                    } else {
                        if (summaryEl) {
                            summaryEl.classList.add("d-none");
                            summaryEl.textContent = "";
                        }
                        if (badgeEl) {
                            badgeEl.style.background = "#FF8000";
                            badgeEl.style.color = "#FFFFFF";
                            const badgeText = isEn
                                ? "FAST-TRACK PRIORITY (< 2H SLA)"
                                : "ƯU TIÊN BÁO GIÁ NHANH (< 2 GIỜ)";
                            badgeEl.innerHTML = `<svg class="ph-duotone ph-lightning" style="width:12px;height:12px;flex-shrink:0;" aria-hidden="true"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-lightning"/></svg><span></span>`;
                            badgeEl.querySelector("span").textContent = badgeText;
                        }
                    }
                });
            });
        }

        setLanguage(lang) {
            if (lang !== "en" && lang !== "vi") return;
            this.currentLang = lang;
            try {
                localStorage.setItem("innoria_lang", lang);
            } catch (_e) {}

            this.updateHtmlLangAttribute();
            this.updateToggleUiState();

            if (this.observer) {
                this.observer.disconnect();
            }
            this.translatePage(this.currentLang);
            this.initObserver();

            window.dispatchEvent(
                new CustomEvent("innoria:i18n:switched", {
                    detail: { lang: this.currentLang },
                })
            );
        }

        translatePage(lang, root = document.body) {
            if (!root) return;
            this.isMutating = true;
            try {
                this.translateDataAttributes(lang, root);
                this.translateElementAttributes(lang, root);
                this.translateTextBlocks(lang, root);
            } finally {
                this.isMutating = false;
            }
        }

        translateDataAttributes(lang, root) {
            const isEn = lang === "en";
            const attrName = isEn ? "data-i18n-en" : "data-i18n-vi";
            root.querySelectorAll(`[${attrName}]`).forEach((el) => {
                const val = el.getAttribute(attrName);
                if (val && val.trim()) {
                    el.textContent = val.trim();
                }
            });

            const phAttr = isEn ? "data-i18n-placeholder-en" : "data-i18n-placeholder-vi";
            root.querySelectorAll(`[${phAttr}]`).forEach((el) => {
                const val = el.getAttribute(phAttr);
                if (val && val.trim()) {
                    el.setAttribute("placeholder", val.trim());
                }
            });
        }

        translateElementAttributes(lang, root) {
            const isEn = lang === "en";
            const targets = root.querySelectorAll("input, textarea, select, option, button, a, [title], [aria-label]");
            targets.forEach((el) => {
                const placeholder = el.getAttribute("placeholder");
                if (placeholder && !el.hasAttribute(isEn ? "data-i18n-placeholder-en" : "data-i18n-placeholder-vi")) {
                    const match = this.lookupSemantic(placeholder, isEn);
                    if (match) el.setAttribute("placeholder", match);
                }

                const title = el.getAttribute("title");
                if (title) {
                    const match = this.lookupSemantic(title, isEn);
                    if (match) el.setAttribute("title", match);
                }

                const ariaLabel = el.getAttribute("aria-label");
                if (ariaLabel) {
                    const match = this.lookupSemantic(ariaLabel, isEn);
                    if (match) el.setAttribute("aria-label", match);
                }

                if (el.tagName === "OPTION") {
                    const match = this.lookupSemantic(el.textContent, isEn);
                    if (match) el.textContent = match;
                }
            });
        }

        translateTextBlocks(lang, root) {
            const isEn = lang === "en";
            const walker = document.createTreeWalker(
                root,
                NodeFilter.SHOW_TEXT,
                {
                    acceptNode(node) {
                        if (!node.nodeValue || !node.nodeValue.trim()) {
                            return NodeFilter.FILTER_REJECT;
                        }
                        const parent = node.parentElement;
                        if (!parent) return NodeFilter.FILTER_REJECT;
                        if (["SCRIPT", "STYLE", "CODE", "PRE", "NOSCRIPT", "TEXTAREA"].includes(parent.tagName)) {
                            return NodeFilter.FILTER_REJECT;
                        }
                        if (
                            parent.hasAttribute("data-i18n-en") ||
                            parent.hasAttribute("data-i18n-vi") ||
                            parent.closest("[data-no-i18n]") ||
                            parent.isContentEditable
                        ) {
                            return NodeFilter.FILTER_REJECT;
                        }
                        return NodeFilter.FILTER_ACCEPT;
                    },
                },
                false
            );

            const nodesToTranslate = [];
            while (walker.nextNode()) {
                nodesToTranslate.push(walker.currentNode);
            }

            nodesToTranslate.forEach((textNode) => {
                const raw = textNode.nodeValue;
                const match = this.lookupSemantic(raw, isEn);
                if (match) {
                    const lead = (raw.match(/^\s*/) || [""])[0];
                    const trail = (raw.match(/\s*$/) || [""])[0];
                    textNode.nodeValue = lead + match + trail;
                }
            });
        }

        lookupSemantic(text, isToEn) {
            if (!text) return null;
            const norm = normalizePhraseKey(text);
            if (!norm) return null;
            if (isToEn) {
                return INNORIA_SEMANTIC_PHRASES[text.trim()] || INNORIA_NORMALIZED_VI[norm] || null;
            }
            return INNORIA_REVERSE_PHRASES[norm] || null;
        }

        initObserver() {
            if (this.observer) {
                this.observer.disconnect();
            }
            if (!document.body) return;
            this.observer = new MutationObserver(this.boundMutations);
            this.observer.observe(document.body, {
                childList: true,
                subtree: true,
            });
        }

        handleMutations(mutationsList) {
            if (this.isMutating) return;
            let hasNewElements = false;
            for (const m of mutationsList) {
                if (m.type === "childList" && m.addedNodes.length > 0) {
                    for (const n of m.addedNodes) {
                        if (n.nodeType === Node.ELEMENT_NODE) {
                            hasNewElements = true;
                            break;
                        }
                    }
                }
                if (hasNewElements) break;
            }
            if (!hasNewElements) return;

            if (this.mutationDebounceTimer) {
                clearTimeout(this.mutationDebounceTimer);
            }
            this.mutationDebounceTimer = setTimeout(() => {
                if (this.observer) this.observer.disconnect();
                this.wirePriorityFileDropzones();
                if (this.currentLang === "en") {
                    this.translatePage("en");
                }
                this.initObserver();
            }, 60);
        }
    }

    const engine = new InnoriaI18nEngine();
    window.InnoriaI18nFramework = engine;
    window.innoriaI18n = engine;
    window.INNORIA_SEMANTIC_PHRASES = INNORIA_SEMANTIC_PHRASES;
    window.INNORIA_REVERSE_PHRASES = INNORIA_REVERSE_PHRASES;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", engine.boundInit);
    } else {
        engine.init();
    }
})(window, document);
