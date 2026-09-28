#!/usr/bin/env python3
"""
Upgrade 3D Cockpit Heroes for all pages across:
1. enterprise/insilos_website/views/platform_solutions.xml
2. enterprise/insilos_website/views/industries.xml
3. enterprise/insilos_website/views/resources_about_demo.xml

Replaces the single-column / flat right-column Hero layouts with the
canonical 2-column layout (col-lg-6 copy + col-lg-6 ins-3d-cockpit-viewport).
Preserves the high-resolution Video Hero background and cybernetic overlays.
"""
import re
import os

BASE_DIR = "/home/zen/O20/enterprise/insilos_website/views"

def make_cockpit_markup(cfg):
    """
    cfg keys:
    - prefix: str (for unique IDs)
    - title: str
    - badge: str
    - layers: list of 4 dicts:
        - num: "L1".."L4"
        - icon: Phosphor icon name
        - title: str
        - badge_text: str
        - badge_color: "mint" | "cyan" | "warning" | "emerald"
        - desc: str
        - metric: str
        - meter_class: "ins-meter-w98" etc.
    - footer_proof: str
    - footer_cert: str
    """
    grad_id = f"insBusGrad_{cfg['prefix']}"
    glow_id = f"insBusGlow_{cfg['prefix']}"
    
    layer_cards_html = []
    for idx, l in enumerate(cfg['layers'], 1):
        active_cls = " ins-act-highlight" if idx == 1 else ""
        badge_cls = f"text-{l['badge_color']} border-{l['badge_color']}-subtle"
        card_html = f"""                                                <!-- Layer {idx} -->
                                                <div class="ins-cockpit-card{active_cls}" data-layer="{idx}">
                                                    <div class="d-flex justify-content-between align-items-center mb-1">
                                                        <div class="d-flex align-items-center gap-2">
                                                            <span class="badge bg-white-10 text-white font-monospace small px-2 py-0 border border-white-10 ins-layer-num">{l['num']}</span>
                                                            <div class="ins-card-pictogram ins-pictogram-md flex-shrink-0">
                                                                <svg class="ph-duotone ph-{l['icon']} ph-lg"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-{l['icon']}"/></svg>
                                                            </div>
                                                            <span class="ins-cockpit-title">{l['title']}</span>
                                                        </div>
                                                        <span class="badge bg-primary-subtle {badge_cls} ins-cockpit-badge">{l['badge_text']}</span>
                                                    </div>
                                                    <div class="d-flex justify-content-between align-items-center text-secondary small">
                                                        <span>{l['desc']}</span>
                                                        <span class="text-{l['badge_color']} fw-medium font-monospace small">{l['metric']}</span>
                                                    </div>
                                                    <div class="ins-cockpit-meter">
                                                        <div class="ins-cockpit-meter-bar {l['meter_class']}"/>
                                                    </div>
                                                </div>"""
        layer_cards_html.append(card_html)
        
    deck_body = "\n".join(layer_cards_html)
    
    return f"""                            <!-- Right Column: Sovereign Enterprise 3D Cockpit UI ({cfg['title']}) -->
                            <div class="col-lg-6">
                                <div class="ins-3d-cockpit-viewport">
                                    <div class="ins-cloud-cockpit">
                                        <!-- Cockpit Header: Mode Toggles & Telemetry Status -->
                                        <div class="ins-cockpit-header">
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="ins-live-ping ins-live-ping--emerald"/>
                                                <span class="ins-cockpit-title fw-bold text-white font-monospace small">{cfg['title']}</span>
                                            </div>
                                            <div class="d-flex align-items-center gap-2">
                                                <div class="btn-group btn-group-sm ins-3d-mode-toggles me-1" role="group">
                                                    <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2 active ins-btn-3d-isometric" title="3D Isometric Architecture View">3D ISO</button>
                                                    <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2 ins-btn-3d-exploded" title="Exploded Architecture Stack">EXPLODED</button>
                                                </div>
                                                <span class="badge bg-secondary bg-opacity-25 text-white font-monospace small">{cfg['badge']}</span>
                                            </div>
                                        </div>

                                        <!-- Cockpit Deck Wrapper with Animated SVG Signal Bus -->
                                        <div class="ins-cockpit-deck-wrapper position-relative">
                                            <svg class="ins-cockpit-bus-svg position-absolute start-0 top-0 h-100 o_not_editable" viewBox="0 0 50 380" preserveAspectRatio="none" style="width: 50px; pointer-events: none; z-index: 5;">
                                                <defs>
                                                    <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="0%" y2="100%">
                                                        <stop offset="0%" stop-color="#FF8000" stop-opacity="0.95"/>
                                                        <stop offset="33%" stop-color="#42E6C3" stop-opacity="0.95"/>
                                                        <stop offset="66%" stop-color="#00E5FF" stop-opacity="0.95"/>
                                                        <stop offset="100%" stop-color="#F59E0B" stop-opacity="0.95"/>
                                                    </linearGradient>
                                                    <filter id="{glow_id}" x="-50%" y="-50%" width="200%" height="200%">
                                                        <feGaussianBlur stdDeviation="3" result="blur"/>
                                                        <feMerge>
                                                            <feMergeNode in="blur"/>
                                                            <feMergeNode in="SourceGraphic"/>
                                                        </feMerge>
                                                    </filter>
                                                </defs>
                                                <path d="M 16 20 L 16 360" stroke="rgba(255,255,255,0.12)" stroke-width="2" fill="none"/>
                                                <path class="ins-bus-pulse-path" d="M 16 20 L 16 360" stroke="url(#{grad_id})" stroke-width="2.5" stroke-dasharray="16 32" fill="none" filter="url(#{glow_id})"/>
                                                <path class="ins-bus-branch ins-bus-branch-1 active" d="M 16 55 L 44 55" stroke="#FF8000" stroke-width="2" fill="none"/>
                                                <path class="ins-bus-branch ins-bus-branch-2" d="M 16 145 L 44 145" stroke="#42E6C3" stroke-width="2" fill="none"/>
                                                <path class="ins-bus-branch ins-bus-branch-3" d="M 16 235 L 44 235" stroke="#00E5FF" stroke-width="2" fill="none"/>
                                                <path class="ins-bus-branch ins-bus-branch-4" d="M 16 325 L 44 325" stroke="#F59E0B" stroke-width="2" fill="none"/>
                                                <circle class="ins-bus-tap ins-bus-tap-1 active" cx="16" cy="55" r="4.5" fill="#FF8000" filter="url(#{glow_id})"/>
                                                <circle class="ins-bus-dock ins-bus-dock-1 active" cx="44" cy="55" r="3.5" fill="#FF8000"/>
                                                <circle class="ins-bus-tap ins-bus-tap-2" cx="16" cy="145" r="4.5" fill="#42E6C3" filter="url(#{glow_id})"/>
                                                <circle class="ins-bus-dock ins-bus-dock-2" cx="44" cy="145" r="3.5" fill="#42E6C3"/>
                                                <circle class="ins-bus-tap ins-bus-tap-3" cx="16" cy="235" r="4.5" fill="#00E5FF" filter="url(#{glow_id})"/>
                                                <circle class="ins-bus-dock ins-bus-dock-3" cx="44" cy="235" r="3.5" fill="#00E5FF"/>
                                                <circle class="ins-bus-tap ins-bus-tap-4" cx="16" cy="325" r="4.5" fill="#F59E0B" filter="url(#{glow_id})"/>
                                                <circle class="ins-bus-dock ins-bus-dock-4" cx="44" cy="325" r="3.5" fill="#F59E0B"/>
                                            </svg>

                                            <!-- Cockpit Body: 4 Mission-Critical Control Layers Stacked in 3D -->
                                            <div class="ins-cockpit-body">
{deck_body}
                                            </div>
                                        </div>

                                        <!-- Cockpit Footer: Mission-Critical Deployment Ready -->
                                        <div class="ins-cockpit-footer">
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="ins-live-ping"/>
                                                <span>{cfg['footer_proof']}</span>
                                            </div>
                                            <span class="badge bg-white-10 text-cyan border border-white-10">{cfg['footer_cert']}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>"""

# Configuration for all 15 heroes
CONFIGS = {
    "platform": {
        "prefix": "platform",
        "title": "PLATFORM ARCHITECTURE // 4 TIERS",
        "badge": "SOC 2 TYPE II",
        "layers": [
            {"num": "L1", "icon": "plugs-connected", "title": "Ingestion &amp; IDP Streaming", "badge_text": "100+ Connectors", "badge_color": "cyan", "desc": "SAP, Oracle, Kafka Stream, IoT OPC-UA &amp; Scanned PDFs", "metric": "50.02 Hz · 12.4k pts/s", "meter_class": "ins-meter-w98"},
            {"num": "L2", "icon": "graph", "title": "Knowledge Graph &amp; Digital Twin", "badge_text": "&lt; 15ms Query", "badge_color": "emerald", "desc": "Entity Resolution, W3C OWL/RDF &amp; 1.4M Enterprise Triples", "metric": "1.4M Triples · Real-Time", "meter_class": "ins-meter-w95"},
            {"num": "L3", "icon": "robot", "title": "Autonomous Operational Agents", "badge_text": "97.4% STP", "badge_color": "cyan", "desc": "HS Classifier, FTA Matrix, 3D Packing &amp; Predictive FSM", "metric": "Sub-45s SLA Execution", "meter_class": "ins-meter-w97"},
            {"num": "L4", "icon": "check-circle", "title": "Closed-Loop Execution &amp; Write-Back", "badge_text": "AUDIT VERIFIED", "badge_color": "mint", "desc": "ERP Write-Back, Cryptographic Dossier &amp; Human Gatekeeper", "metric": "Zero Drift Protection", "meter_class": "ins-meter-w99"}
        ],
        "footer_proof": "Triển khai thực chiến: <strong class=\"text-white\">Năng Lượng Quốc Gia • Viễn Thông • FDI</strong>",
        "footer_cert": "ISO 27001 &amp; SOC 2 Type II"
    },
    "solutions": {
        "prefix": "solutions",
        "title": "SOLUTIONS MATRIX // 4 PILLARS",
        "badge": "100% WRITE-BACK",
        "layers": [
            {"num": "L1", "icon": "file-text", "title": "Vertical IDP Logistics Automation", "badge_text": "99.8% Precision", "badge_color": "cyan", "desc": "Bóc tách B/L, Commercial Invoice &amp; Tờ khai hải quan", "metric": "STP 0.38s · 1,420 docs/h", "meter_class": "ins-meter-w99"},
            {"num": "L2", "icon": "tree-structure", "title": "Enterprise Knowledge Graph &amp; Twin", "badge_text": "&lt; 15ms Query", "badge_color": "cyan", "desc": "Hợp nhất Data Silos &amp; Dự báo rủi ro Domino chuỗi cung ứng", "metric": "2.8M Triples · OWL/RDF", "meter_class": "ins-meter-w96"},
            {"num": "L3", "icon": "scales", "title": "Autonomous Trade Compliance", "badge_text": "-98% Penalties", "badge_color": "emerald", "desc": "Phân loại mã HS 8-10 số &amp; Kiểm soát FTA EVFTA/CPTPP", "metric": "WCO SAFE Framework", "meter_class": "ins-meter-w98"},
            {"num": "L4", "icon": "wrench", "title": "Field Service Intelligence", "badge_text": "94.8% FTFR", "badge_color": "warning", "desc": "Bảo trì dự đoán SCADA &amp; Điều phối kỹ thuật viên SLA &lt; 45s", "metric": "0h Downtime · IEC 61850", "meter_class": "ins-meter-w95"}
        ],
        "footer_proof": "Sẵn sàng cho: <strong class=\"text-white\">101+ Ngành Công Nghiệp</strong>",
        "footer_cert": "Enterprise Mesh 2026"
    },
    "idp": {
        "prefix": "idp",
        "title": "DOCUMENT INTELLIGENCE FABRIC",
        "badge": "0.38S STP",
        "layers": [
            {"num": "L1", "icon": "arrows-in", "title": "Multi-Stream Document Ingestion", "badge_text": "1,420 docs/h", "badge_color": "cyan", "desc": "PDF Scan, Ảnh chụp Container, EDIFACT &amp; XML Manifest", "metric": "Kafka Event Queue", "meter_class": "ins-meter-w97"},
            {"num": "L2", "icon": "scan", "title": "Dual-Engine OCR &amp; Vision LM", "badge_text": "99.8% Match", "badge_color": "mint", "desc": "Bóc tách bảng biểu phức tạp &amp; Con dấu hải quan đa quốc gia", "metric": "Zero Hallucination", "meter_class": "ins-meter-w99"},
            {"num": "L3", "icon": "check-square-offset", "title": "Cross-Validation &amp; 3-Way Match", "badge_text": "0 Variance", "badge_color": "emerald", "desc": "Đối soát Invoice vs Packing List vs Bill of Lading", "metric": "Merkle Audit Hash", "meter_class": "ins-meter-w98"},
            {"num": "L4", "icon": "database", "title": "Direct VNACCS &amp; ERP Write-Back", "badge_text": "&lt; 2.1s E2E", "badge_color": "cyan", "desc": "Tự động đẩy dữ liệu vào phân hệ Kế toán SAP / Oracle", "metric": "Thông tư 78 / VAS 200", "meter_class": "ins-meter-w100"}
        ],
        "footer_proof": "Bảo mật tài liệu: <strong class=\"text-white\">On-Premises / Air-Gapped</strong>",
        "footer_cert": "ISO 27001 &amp; VAS 200"
    },
    "graph": {
        "prefix": "graph",
        "title": "LIVING KNOWLEDGE MESH // FABRIC",
        "badge": "2.8M TRIPLES",
        "layers": [
            {"num": "L1", "icon": "database", "title": "Multi-Source Data Silo Ingestion", "badge_text": "45+ Sources", "badge_color": "cyan", "desc": "SAP, Oracle, SCADA, IoT Sensors &amp; Unstructured PDFs", "metric": "Real-Time CDC Stream", "meter_class": "ins-meter-w96"},
            {"num": "L2", "icon": "tree-structure", "title": "Entity Resolution &amp; W3C RDF Mesh", "badge_text": "&lt; 12ms Traversal", "badge_color": "mint", "desc": "Đồng nhất thực thể Nhà cung cấp, Lô hàng &amp; Thiết bị", "metric": "Entity Resolution 99.4%", "meter_class": "ins-meter-w98"},
            {"num": "L3", "icon": "lightning", "title": "Graph Neural Domino Risk Predictor", "badge_text": "96.4% Early Warning", "badge_color": "warning", "desc": "Mô phỏng đứt gãy chuỗi cung ứng trước 72 giờ", "metric": "GNN Multi-Hop Inference", "meter_class": "ins-meter-w95"},
            {"num": "L4", "icon": "shield-check", "title": "Closed-Loop Action Trigger", "badge_text": "Sub-Second SLA", "badge_color": "cyan", "desc": "Tự động kích hoạt đơn hàng thay thế &amp; tuyến vận tải dự phòng", "metric": "100% Traceable Ledger", "meter_class": "ins-meter-w97"}
        ],
        "footer_proof": "Chuẩn đồ thị: <strong class=\"text-white\">W3C OWL/RDF &amp; Neo4j TripleStore</strong>",
        "footer_cert": "W3C Compliant"
    },
    "trade": {
        "prefix": "trade",
        "title": "AUTONOMOUS TRADE GOVERNANCE",
        "badge": "WCO SAFE READY",
        "layers": [
            {"num": "L1", "icon": "file-text", "title": "Trade Document Stream Ingestion", "badge_text": "Real-Time Audit", "badge_color": "cyan", "desc": "Tờ khai hải quan điện tử, Hóa đơn thương mại, C/O Form E/D", "metric": "100% Pre-Clearance", "meter_class": "ins-meter-w98"},
            {"num": "L2", "icon": "barcode", "title": "HS Code 8-10 Digit Engine", "badge_text": "99.4% Tax Precision", "badge_color": "mint", "desc": "Gán mã HS chính xác theo biểu thuế hiện hành 2026", "metric": "Zero Tariff Penalty", "meter_class": "ins-meter-w99"},
            {"num": "L3", "icon": "globe", "title": "FTA &amp; Origin Optimizer (PSR)", "badge_text": "0% Duty Rate", "badge_color": "emerald", "desc": "Tận dụng tối đa ưu đãi thuế quan EVFTA, CPTPP, RCEP", "metric": "Value Add Verification", "meter_class": "ins-meter-w97"},
            {"num": "L4", "icon": "certificate", "title": "Sanction &amp; Legal Dossier Sign-Off", "badge_text": "100% Audit Ready", "badge_color": "cyan", "desc": "Rà quét danh sách trừng phạt OFAC &amp; Bút phê điện tử", "metric": "Bảo Lãnh Kiểm Toán", "meter_class": "ins-meter-w100"}
        ],
        "footer_proof": "Khung an ninh: <strong class=\"text-white\">WCO SAFE Framework &amp; VNACCS</strong>",
        "footer_cert": "Legal Audit Proof"
    },
    "fsm": {
        "prefix": "fsm",
        "title": "PREDICTIVE FSM DISPATCH FABRIC",
        "badge": "&lt; 45S DISPATCH",
        "layers": [
            {"num": "L1", "icon": "gauge", "title": "SCADA &amp; OPC-UA Telemetry Ingestion", "badge_text": "12.4k pts/s", "badge_color": "cyan", "desc": "Cảm biến rung động, nhiệt độ &amp; áp suất thời gian thực", "metric": "50.02 Hz Sampling", "meter_class": "ins-meter-w98"},
            {"num": "L2", "icon": "chart-line-up", "title": "Bearing Fatigue &amp; RUL Degradation", "badge_text": "14 Days Lead Time", "badge_color": "mint", "desc": "Dự báo suy hao linh kiện trước khi phát sinh sự cố", "metric": "FFT Spectral Analysis", "meter_class": "ins-meter-w96"},
            {"num": "L3", "icon": "users-three", "title": "Intelligent Technician Dispatch", "badge_text": "94.8% FTFR", "badge_color": "warning", "desc": "Tối ưu lộ trình GPS, phụ tùng và năng lực kỹ sư", "metric": "Routing SLA &lt; 45s", "meter_class": "ins-meter-w95"},
            {"num": "L4", "icon": "device-mobile-camera", "title": "Offline 3D SOP &amp; Digital Sign-Off", "badge_text": "Zero Downtime", "badge_color": "cyan", "desc": "Hướng dẫn tháo lắp AR/3D không cần kết nối mạng", "metric": "Odoo / SAP FSM Sync", "meter_class": "ins-meter-w98"}
        ],
        "footer_proof": "Tiêu chuẩn kỹ thuật: <strong class=\"text-white\">IEC 61850 &amp; OPC-UA</strong>",
        "footer_cert": "Field Mobility 2026"
    },
    "industries": {
        "prefix": "industries",
        "title": "101+ INDUSTRIAL PACKS ENGINE",
        "badge": "101 PACKAGES",
        "layers": [
            {"num": "L1", "icon": "buildings", "title": "Pre-Configured Sector Ontologies", "badge_text": "101+ Sectors", "badge_color": "cyan", "desc": "Sản xuất nặng, Cảng biển, Dược phẩm, Năng lượng &amp; Bán lẻ", "metric": "Out-of-the-Box Schemas", "meter_class": "ins-meter-w98"},
            {"num": "L2", "icon": "flow-arrow", "title": "Industry-Specific SOP Workflows", "badge_text": "500+ Standard SOPs", "badge_color": "mint", "desc": "Quy trình kiểm soát chất lượng &amp; bảo trì chuẩn ngành", "metric": "Best-Practice Baked In", "meter_class": "ins-meter-w96"},
            {"num": "L3", "icon": "shield-check", "title": "Regulatory Compliance Engines", "badge_text": "100% Localized", "badge_color": "emerald", "desc": "FDA 21 CFR Part 11, GAMP 5, IEC 61850 &amp; VAS 200", "metric": "Strict Governance", "meter_class": "ins-meter-w99"},
            {"num": "L4", "icon": "rocket-launch", "title": "Rapid Go-Live Acceleration Pack", "badge_text": "7-14 Days Live", "badge_color": "cyan", "desc": "Đưa vào vận hành sản xuất thực tế trong 2 tuần", "metric": "Zero Disruption", "meter_class": "ins-meter-w97"}
        ],
        "footer_proof": "Bảo chứng thực tế: <strong class=\"text-white\">Hơn 50+ Doanh nghiệp FDI</strong>",
        "footer_cert": "Sovereign Air-Gapped"
    },
    "logistics": {
        "prefix": "logistics",
        "title": "PORT TERMINAL CONTROL FABRIC",
        "badge": "14,200 TEU",
        "layers": [
            {"num": "L1", "icon": "anchor", "title": "Berth &amp; STS Quay Crane Telemetry", "badge_text": "32 Moves/Hour", "badge_color": "cyan", "desc": "Giám sát thời gian thực cẩu giàn cảng Cái Mép - Thị Vải", "metric": "AIS Live Tracking", "meter_class": "ins-meter-w97"},
            {"num": "L2", "icon": "receipt", "title": "TOS &amp; VNACCS Reconciliation", "badge_text": "99.8% Match", "badge_color": "mint", "desc": "Khớp nối thông quan điện tử &amp; manifest xếp dỡ container", "metric": "0 Inline Bottleneck", "meter_class": "ins-meter-w99"},
            {"num": "L3", "icon": "truck", "title": "Multimodal Gate Turnaround", "badge_text": "&lt; 18 Mins Gate", "badge_color": "warning", "desc": "Nhận diện biển số OCR &amp; điều phối luồng xe tại cổng", "metric": "Automated Queueing", "meter_class": "ins-meter-w96"},
            {"num": "L4", "icon": "shield-check", "title": "Demurrage Elimination Shield", "badge_text": "-88% Lưu Bãi", "badge_color": "emerald", "desc": "Cảnh báo sớm hạn lưu bãi &amp; tối ưu chi phí hạ tầng cảng", "metric": "Tối ưu 100% Phí", "meter_class": "ins-meter-w98"}
        ],
        "footer_proof": "Chuẩn cảng biển: <strong class=\"text-white\">WCO SAFE &amp; Cảng Cái Mép</strong>",
        "footer_cert": "Green Port 2026"
    },
    "pharma": {
        "prefix": "pharma",
        "title": "PHARMA CLEANROOM CONTROL FABRIC",
        "badge": "GAMP 5 READY",
        "layers": [
            {"num": "L1", "icon": "flask", "title": "PAT &amp; Cleanroom Bioreactor Telemetry", "badge_text": "0.1s Sampling", "badge_color": "cyan", "desc": "Nhiệt độ, áp suất, pH &amp; oxy hòa tan bồn lên men sinh học", "metric": "Cleanroom Sensors", "meter_class": "ins-meter-w99"},
            {"num": "L2", "icon": "chart-polar", "title": "Golden Batch Trajectory Analytics", "badge_text": "+14.2% Yield", "badge_color": "mint", "desc": "Mô hình hóa đường cong mẻ thuốc lý tưởng theo thời gian thực", "metric": "Multi-Variate SPC", "meter_class": "ins-meter-w97"},
            {"num": "L3", "icon": "warning-octagon", "title": "Real-Time OOS / OOT Deviation Lock", "badge_text": "-70% Sai Lệch", "badge_color": "warning", "desc": "Ngăn chặn tức thì nguy cơ hỏng mẻ và cảnh báo sớm", "metric": "Zero Discarded Batches", "meter_class": "ins-meter-w98"},
            {"num": "L4", "icon": "signature", "title": "21 CFR Part 11 Electronic Batch Record", "badge_text": "100% Audit Proof", "badge_color": "emerald", "desc": "Chữ ký số, nhật ký kiểm toán không thể chỉnh sửa", "metric": "FDA / WHO Inspection", "meter_class": "ins-meter-w100"}
        ],
        "footer_proof": "Tuân thủ tiêu chuẩn: <strong class=\"text-white\">FDA 21 CFR Part 11 &amp; GAMP 5</strong>",
        "footer_cert": "GMP-WHO Validated"
    },
    "energy": {
        "prefix": "energy",
        "title": "SMART GRID &amp; WIND FABRIC",
        "badge": "500KV ONLINE",
        "layers": [
            {"num": "L1", "icon": "lightning", "title": "Substation IEC 61850 Stream", "badge_text": "10ms Capture", "badge_color": "cyan", "desc": "Giám sát trạm biến áp 500kV &amp; đường dây truyền tải điện", "metric": "Optical CT/PT Stream", "meter_class": "ins-meter-w99"},
            {"num": "L2", "icon": "wind", "title": "Offshore Turbine Digital Twin", "badge_text": "98.6% Health", "badge_color": "mint", "desc": "Mô phỏng khí động học và độ mòn hộp số tua-bin gió", "metric": "Predictive Bearing RUL", "meter_class": "ins-meter-w96"},
            {"num": "L3", "icon": "sliders-horizontal", "title": "Frequency &amp; Reactive Balancer", "badge_text": "50.02 Hz Target", "badge_color": "emerald", "desc": "Cân bằng phụ tải lưới điện tự động theo thời gian thực", "metric": "Active Inertia Control", "meter_class": "ins-meter-w98"},
            {"num": "L4", "icon": "shield-check", "title": "Blackout Prevention Interlock", "badge_text": "0s Major Outage", "badge_color": "cyan", "desc": "Tự động cô lập sự cố trong 40 mili-giây bảo vệ hệ thống", "metric": "Grid Proven", "meter_class": "ins-meter-w100"}
        ],
        "footer_proof": "Tiêu chuẩn quốc tế: <strong class=\"text-white\">IEC 61850 Grid Architecture</strong>",
        "footer_cert": "Grid Proven"
    },
    "fsm_ind": {
        "prefix": "fsm_ind",
        "title": "TELECOM FIELD MOBILITY FABRIC",
        "badge": "&lt; 45S SLA",
        "layers": [
            {"num": "L1", "icon": "broadcast", "title": "BTS Tower IoT Telemetry", "badge_text": "Real-Time Telemetry", "badge_color": "cyan", "desc": "Giám sát trạm viễn thông &amp; tủ nguồn dự phòng máy nổ", "metric": "Battery Health Stream", "meter_class": "ins-meter-w98"},
            {"num": "L2", "icon": "navigation-arrow", "title": "Traffic-Aware Fleet Routing", "badge_text": "-35% Di Chuyển", "badge_color": "mint", "desc": "Tối ưu lộ trình di chuyển của kỹ thuật viên hiện trường", "metric": "GPS Multi-Stop Solver", "meter_class": "ins-meter-w95"},
            {"num": "L3", "icon": "wrench", "title": "Automated Tooling &amp; Spare Parts", "badge_text": "100% Parts Ready", "badge_color": "warning", "desc": "Đảm bảo kỹ sư mang đúng linh kiện ngay lần đầu tiên", "metric": "Inventory Auto-Reserve", "meter_class": "ins-meter-w98"},
            {"num": "L4", "icon": "check-circle", "title": "Mobile Acceptance Sign-Off", "badge_text": "Instant Sync", "badge_color": "emerald", "desc": "Nghiệm thu điện tử và cập nhật trực tiếp vào hệ thống", "metric": "Offline Mobile App", "meter_class": "ins-meter-w99"}
        ],
        "footer_proof": "Hệ sinh thái viễn thông: <strong class=\"text-white\">National Telco &amp; Enterprise Ecosystem</strong>",
        "footer_cert": "Field Mobility"
    },
    "pricing": {
        "prefix": "pricing",
        "title": "SOVEREIGN TCO LEDGER FABRIC",
        "badge": "AUDIT VERIFIED",
        "layers": [
            {"num": "L1", "icon": "lock-key", "title": "Sovereign Core Deployment", "badge_text": "Air-Gapped Ready", "badge_color": "cyan", "desc": "Toàn quyền kiểm soát mã nguồn và dữ liệu công nghiệp", "metric": "On-Premises / Private", "meter_class": "ins-meter-w100"},
            {"num": "L2", "icon": "receipt", "title": "Micro-Ledger Usage Metering", "badge_text": "Transparent Ledger", "badge_color": "mint", "desc": "Tính phí minh bạch theo dung lượng vận hành thực tế", "metric": "Real-Time Audit Proof", "meter_class": "ins-meter-w97"},
            {"num": "L3", "icon": "currency-circle-dollar", "title": "Zero Cloud Egress Surprise Fees", "badge_text": "0 VNĐ Phí Ẩn", "badge_color": "emerald", "desc": "Không phát sinh chi phí truyền tải hay phí bản quyền bất ngờ", "metric": "Fixed TCO Guarantee", "meter_class": "ins-meter-w100"},
            {"num": "L4", "icon": "seal-check", "title": "Enterprise SLA Refund Policy", "badge_text": "99.95% SLA Uptime", "badge_color": "cyan", "desc": "Cam kết hoàn tiền nếu không đạt chỉ số SLA thỏa thuận", "metric": "Hợp Đồng Pháp Lý VN", "meter_class": "ins-meter-w99"}
        ],
        "footer_proof": "Chính sách tài chính: <strong class=\"text-white\">Minh bạch 100% chi phí sở hữu TCO</strong>",
        "footer_cert": "Sovereign SLA"
    },
    "about": {
        "prefix": "about",
        "title": "INSILOS R&amp;D INNOVATION FABRIC",
        "badge": "SOVEREIGN AI",
        "layers": [
            {"num": "L1", "icon": "atom", "title": "Deep Industrial Domain Research", "badge_text": "15+ Năm Kinh Nghiệm", "badge_color": "cyan", "desc": "Nghiên cứu chuyên sâu giải pháp công nghiệp đặc thù", "metric": "Domain-First Research", "meter_class": "ins-meter-w97"},
            {"num": "L2", "icon": "cpu", "title": "Sovereign AI Core Architecture", "badge_text": "Air-Gapped Ready", "badge_color": "mint", "desc": "Kiến trúc độc lập, không phụ thuộc nhà cung cấp nước ngoài", "metric": "Zero Vendor Lock-in", "meter_class": "ins-meter-w99"},
            {"num": "L3", "icon": "code", "title": "High Reliability Code Standard", "badge_text": "100% Tested", "badge_color": "warning", "desc": "Tiêu chuẩn mã nguồn khắt khe dành cho hạ tầng trọng yếu", "metric": "Strict Quality Gates", "meter_class": "ins-meter-w98"},
            {"num": "L4", "icon": "handshake", "title": "Customer Co-Innovation Labs", "badge_text": "7-14 Days Go-Live", "badge_color": "emerald", "desc": "Đồng hành cùng khách hàng từ PoC đến quy mô lớn", "metric": "Proven APAC Track", "meter_class": "ins-meter-w98"}
        ],
        "footer_proof": "Đội ngũ phát triển: <strong class=\"text-white\">Kỹ sư Việt Nam tinh hoa</strong>",
        "footer_cert": "ISO 27001"
    },
    "resources": {
        "prefix": "resources",
        "title": "ARCHITECTURE REPOSITORY",
        "badge": "40+ BLUEPRINTS",
        "layers": [
            {"num": "L1", "icon": "blueprint", "title": "Enterprise Reference Blueprints", "badge_text": "Production Ready", "badge_color": "cyan", "desc": "Sơ đồ kiến trúc mẫu cho SAP, Oracle &amp; SCADA", "metric": "System Architecture", "meter_class": "ins-meter-w98"},
            {"num": "L2", "icon": "book-bookmark", "title": "Industrial AI Research Whitepapers", "badge_text": "Peer-Reviewed Data", "badge_color": "mint", "desc": "Báo cáo nghiên cứu thực tế về hiệu quả vận hành tự động", "metric": "Empirical ROI Studies", "meter_class": "ins-meter-w96"},
            {"num": "L3", "icon": "shield-check", "title": "Regulatory &amp; Compliance Guides", "badge_text": "WCO · FDA · IEC", "badge_color": "emerald", "desc": "Tài liệu hướng dẫn tuân thủ pháp lý &amp; quy chuẩn kỹ thuật", "metric": "Audit Preparedness", "meter_class": "ins-meter-w99"},
            {"num": "L4", "icon": "calculator", "title": "Interactive ROI Calculators", "badge_text": "Real-Time Tools", "badge_color": "cyan", "desc": "Công cụ tính toán hiệu quả kinh tế và thư viện mẫu tích hợp", "metric": "Dynamic Formulas", "meter_class": "ins-meter-w97"}
        ],
        "footer_proof": "Kho tri thức: <strong class=\"text-white\">Cẩm nang thiết kế cho Kỹ Sư Trưởng</strong>",
        "footer_cert": "Updated 2026"
    },
    "demo": {
        "prefix": "demo",
        "title": "MISSION CONTROL LIVE SCHEDULING",
        "badge": "ACTIVE SLOT",
        "layers": [
            {"num": "L1", "icon": "magnifying-glass", "title": "Architectural Needs Assessment", "badge_text": "&lt; 15 Mins Response", "badge_color": "cyan", "desc": "Phân tích hiện trạng hạ tầng và yêu cầu nghiệp vụ thực tế", "metric": "Zero Commitment", "meter_class": "ins-meter-w98"},
            {"num": "L2", "icon": "database", "title": "Live Sandbox &amp; Synthetic Data PoC", "badge_text": "48 Hours Turnaround", "badge_color": "mint", "desc": "Trải nghiệm trực tiếp trên môi trường thử nghiệm chuyên biệt", "metric": "Sample Pipeline Ready", "meter_class": "ins-meter-w96"},
            {"num": "L3", "icon": "chart-line-up", "title": "Custom Solution Blueprint &amp; ROI", "badge_text": "100% Customized", "badge_color": "warning", "desc": "Bản thiết kế giải pháp chi tiết kèm mô hình dự toán chi phí", "metric": "TCO Optimization", "meter_class": "ins-meter-w98"},
            {"num": "L4", "icon": "presentation", "title": "Executive Briefing Session", "badge_text": "Architect Directed", "badge_color": "emerald", "desc": "Buổi trình bày giải pháp với ban lãnh đạo doanh nghiệp", "metric": "Kỹ sư trưởng tư vấn", "meter_class": "ins-meter-w100"}
        ],
        "footer_proof": "Cam kết bảo mật: <strong class=\"text-white\">NDA Bảo mật thông tin 100%</strong>",
        "footer_cert": "Direct Consulting"
    }
}

print("Loaded 3D Cockpit configurations for 15 heroes!")

def update_platform_solutions():
    bak_path = os.path.join(BASE_DIR, "platform_solutions.xml.bak")
    path = os.path.join(BASE_DIR, "platform_solutions.xml")
    source_file = bak_path if os.path.exists(bak_path) else path
    with open(source_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. /platform
    pattern_plat = r'(<section[^>]*data-name="Platform Hero"[^>]*>[\s\S]*?<div class="ins-hero-scanlines[^>]*/>\s*)<div class="container[^\"]*"[^>]*>([\s\S]*?</div>\s*</div>\s*</div>)\s*(</section>)'
    m_plat = re.search(pattern_plat, content)
    if m_plat:
        m_left = re.search(r'<div class="col-lg-7">([\s\S]*?)</div>\s*<!-- Right:', m_plat.group(2))
        if m_left:
            left_html = m_left.group(1)
            new_platform_container = f"""<div class="container py-lg-4 position-relative ins-hero-content-layer">
                        <div class="row align-items-center g-5">
                            <div class="col-lg-6">{left_html}</div>
{make_cockpit_markup(CONFIGS['platform'])}
                        </div>
                    </div>"""
            content = content[:m_plat.start(1)] + m_plat.group(1) + new_platform_container + '\n                ' + m_plat.group(3) + content[m_plat.end():]
            print("Updated /platform 3D Cockpit!")
        else:
            print("Could not match /platform left column!")
    else:
        print("Could not match /platform container!")

    # 2. /solutions (Directory)
    pattern_sol = r'(<section class="s_cover[^>]*data-name="Solutions Hero"[^>]*>[\s\S]*?<div class="ins-hero-scanlines[^>]*/>\s*)<div class="container py-lg-4 text-center[^>]*>[\s\S]*?</div>\s*(</section>)'
    m_sol = re.search(pattern_sol, content)
    if m_sol:
        sol_left = """<div class="col-lg-6">
                                <div class="ins-pill-badge mb-3">
                                    <svg class="ph-duotone ph-diamonds-four ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-diamonds-four"/></svg>
                                    <span>Enterprise AI Solutions</span>
                                </div>
                                <h1 class="display-3 fw-bold text-white mb-3 ins-title-balance">Hệ Thống Giải Pháp Trí Tuệ Vận Hành Công Nghiệp:<br class="d-none d-md-inline"/> Tự Động Hóa Đa Phân Hệ &amp; Khóa Cứng Rủi Ro</h1>
                                <p class="lead text-secondary mb-4 col-lg-11 p-0">
                                    Chuyển đổi các tác vụ vận hành phức tạp, tốn kém và dễ sai sót thành quy trình tự động hóa có kiểm soát, tối ưu hóa chi phí và đảm bảo tuân thủ pháp lý 100%.
                                </p>
                                <div class="d-flex flex-column flex-sm-row flex-wrap gap-3 mb-4">
                                    <a href="#solutions-grid" class="btn btn-primary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <span>Khám Phá 4 Bộ Giải Pháp</span>
                                        <svg class="ph-duotone ph-arrow-down ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-arrow-down"/></svg>
                                    </a>
                                    <a href="/request-demo" class="btn btn-outline-secondary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <svg class="ph-duotone ph-headset ph-sm text-cyan"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-headset"/></svg>
                                        <span>Tư Vấn Kiến Trúc Trực Tiếp</span>
                                    </a>
                                </div>
                                <div class="d-flex flex-wrap align-items-center gap-2 pt-3 border-top border-secondary border-opacity-25">
                                    <span class="font-monospace small text-secondary text-uppercase">Enterprise Matrix:</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Vertical IDP</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Knowledge Graph</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Trade Compliance</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Predictive FSM</span>
                                </div>
                            </div>"""
        new_sol_container = f"""<div class="container py-lg-4 position-relative ins-hero-content-layer">
                        <div class="row align-items-center g-5">
                            {sol_left}
{make_cockpit_markup(CONFIGS['solutions'])}
                        </div>
                    </div>"""
        content = content[:m_sol.start(1)] + m_sol.group(1) + new_sol_container + '\n                ' + m_sol.group(2) + content[m_sol.end():]
        print("Updated /solutions 3D Cockpit!")
    else:
        print("Could not match /solutions!")

    # 3, 4, 5, 6. Subpages
    for tmpl, cfg_key, log_name in [
        ('insilos_solution_enterprise_knowledge_graph_page', 'graph', '/solutions/enterprise-knowledge-graph'),
        ('insilos_solution_vertical_idp_page', 'idp', '/solutions/vertical-idp'),
        ('insilos_solution_trade_compliance_page', 'trade', '/solutions/trade-compliance'),
        ('insilos_solution_field_service_intelligence_page', 'fsm', '/solutions/field-service-intelligence')
    ]:
        pattern_sub = rf'(<template id="{tmpl}"[\s\S]*?<section[^>]*>[\s\S]*?<div class="ins-hero-scanlines[^>]*/>\s*)<div class="container[^\"]*"[^>]*>([\s\S]*?)</div>\s*</div>\s*</div>\s*(</section>)'
        m_sub = re.search(pattern_sub, content)
        if m_sub:
            m_sub_left = re.search(r'<div class="col-lg-7">([\s\S]*?)</div>\s*<div class="col-lg-5">', m_sub.group(2))
            if m_sub_left:
                sub_left_html = m_sub_left.group(1).replace('col-lg-10', 'col-lg-11')
                new_sub_container = f"""<div class="container s_allow_columns position-relative ins-hero-content-layer py-lg-4">
                        <div class="row align-items-center g-5">
                            <div class="col-lg-6">{sub_left_html}</div>
{make_cockpit_markup(CONFIGS[cfg_key])}
                        </div>
                    </div>"""
                content = content[:m_sub.start(1)] + m_sub.group(1) + new_sub_container + '\n                ' + m_sub.group(3) + content[m_sub.end():]
                print(f"Updated {log_name} 3D Cockpit!")
            else:
                print(f"Could not match left col for {log_name}!")
        else:
            print(f"Could not match container for {log_name}!")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Saved platform_solutions.xml!")

def update_industries():
    path = os.path.join(BASE_DIR, "industries.xml")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. /industries
    pattern_ind = r'(<section class="s_cover[^>]*data-name="Industries Hero"[^>]*>[\s\S]*?<div class="ins-hero-scanlines[^>]*/>\s*)<div class="container py-lg-4 text-center[^>]*>[\s\S]*?</div>\s*(</section>)'
    m_ind = re.search(pattern_ind, content)
    if m_ind:
        ind_markup = f"""<div class="container py-lg-4 position-relative ins-hero-content-layer">
                        <div class="row align-items-center g-5">
                            <div class="col-lg-6">
                                <div class="ins-pill-badge mb-3">
                                    <svg class="ph-duotone ph-buildings ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-buildings"/></svg>
                                    <span>101+ Industrial Packages</span>
                                </div>
                                <h1 class="display-3 fw-bold text-white mb-3 ins-title-balance">Gói Ứng Dụng AI Theo Ngành: Sẵn Sàng Vận Hành Ngay Từ Ngày Đầu Tiên</h1>
                                <p class="lead text-secondary mb-4 col-lg-11 p-0">
                                    Insilos cung cấp 101+ gói mô hình hóa dữ liệu (Ontology), quy trình SOP và giải pháp AI đóng gói sẵn cho từng ngành công nghiệp đặc thù. Triển khai trong 7–14 ngày.
                                </p>
                                <div class="d-flex flex-column flex-sm-row flex-wrap gap-3 mb-4">
                                    <a href="#cluster-filters" class="btn btn-primary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <span>Khám Phá Các Cụm Ngành</span>
                                        <svg class="ph-duotone ph-arrow-down ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-arrow-down"/></svg>
                                    </a>
                                    <a href="/request-demo" class="btn btn-outline-secondary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <svg class="ph-duotone ph-headset ph-sm text-cyan"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-headset"/></svg>
                                        <span>Tư Vấn Gói Phù Hợp</span>
                                    </a>
                                </div>
                                <div class="d-flex flex-wrap align-items-center gap-2 pt-3 border-top border-secondary border-opacity-25">
                                    <span class="font-monospace small text-secondary text-uppercase">Sector Clusters:</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Logistics &amp; Port</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Pharma &amp; GxP</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Energy &amp; Grid</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Telecom &amp; FSM</span>
                                </div>
                            </div>
{make_cockpit_markup(CONFIGS['industries'])}
                        </div>
                    </div>\n                """
        content = content[:m_ind.start(1)] + m_ind.group(1) + ind_markup + m_ind.group(2) + content[m_ind.end():]
        print("Updated /industries 3D Cockpit!")
    else:
        print("Could not match /industries!")

    # Helper for industry sub-pages
    def wrap_subpage_hero(template_id, cfg_key):
        nonlocal content
        pattern = rf'(<template id="{template_id}"[\s\S]*?<section[^>]*data-name="Cover"[^>]*>[\s\S]*?<div class="ins-hero-scanlines[^>]*/>\s*)<div class="container s_allow_columns position-relative ins-hero-content-layer">([\s\S]*?)</div>\s*(</section>)'
        m = re.search(pattern, content)
        if m:
            inner_copy = m.group(2).strip()
            # If inner_copy contains col-lg-10, change to col-lg-11
            inner_copy = inner_copy.replace('col-lg-10', 'col-lg-11')
            new_container = f"""<div class="container s_allow_columns position-relative ins-hero-content-layer py-lg-4">
                        <div class="row align-items-center g-5">
                            <div class="col-lg-6">
                                {inner_copy}
                            </div>
{make_cockpit_markup(CONFIGS[cfg_key])}
                        </div>
                    </div>\n                """
            content = content[:m.start(1)] + m.group(1) + new_container + m.group(3) + content[m.end():]
            print(f"Updated {template_id} 3D Cockpit!")
        else:
            print(f"Could not match {template_id}!")

    wrap_subpage_hero("insilos_industry_logistics_page", "logistics")
    wrap_subpage_hero("insilos_industry_pharma_page", "pharma")
    wrap_subpage_hero("insilos_industry_energy_page", "energy")
    wrap_subpage_hero("insilos_industry_fsm_page", "fsm_ind")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Saved industries.xml!")

def update_resources_about_demo():
    path = os.path.join(BASE_DIR, "resources_about_demo.xml")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. /pricing
    pattern_pricing = r'(<template id="insilos_pricing_page"[\s\S]*?<section[^>]*data-name="Pricing Hero"[^>]*>[\s\S]*?<div class="ins-hero-scanlines[^>]*/>\s*)<div class="container py-lg-4 position-relative ins-hero-content-layer">([\s\S]*?)</div>\s*(</section>)'
    m_pr = re.search(pattern_pricing, content)
    if m_pr:
        pricing_markup = f"""<div class="container py-lg-4 position-relative ins-hero-content-layer">
                        <div class="row align-items-center g-5">
                            <div class="col-lg-6">
                                <div class="ins-pill-badge mb-3">
                                    <span class="ins-live-ping"/>
                                    <span>Transparent Enterprise Pricing</span>
                                </div>
                                <h1 class="display-3 fw-bold text-white mb-3">Mô Hình Giá Linh Hoạt &amp; Minh Bạch Theo Giá Trị Vận Hành</h1>
                                <p class="lead text-secondary mb-4 col-lg-11 p-0">
                                    Khởi đầu với chương trình Pilot 4 tuần và mở rộng theo quy mô doanh nghiệp với cơ chế AI Credit Ledger thời gian thực, cam kết không phát sinh chi phí ẩn.
                                </p>
                                <div class="d-flex flex-column flex-sm-row flex-wrap gap-3 mb-4">
                                    <a href="#pricing-plans" class="btn btn-primary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <span>Xem Chi Tiết 3 Gói Dịch Vụ</span>
                                        <svg class="ph-duotone ph-arrow-down ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-arrow-down"/></svg>
                                    </a>
                                    <a href="/request-demo" class="btn btn-outline-secondary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <svg class="ph-duotone ph-calculator ph-sm text-cyan"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-calculator"/></svg>
                                        <span>Ước Tính Chi Phí Pilot</span>
                                    </a>
                                </div>
                                <div class="d-flex flex-wrap align-items-center gap-2 pt-3 border-top border-secondary border-opacity-25">
                                    <span class="font-monospace small text-secondary text-uppercase">Sovereign TCO:</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">0 VNĐ Cloud Egress</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">100% On-Premises</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Audit SLA Guarantee</span>
                                </div>
                            </div>
{make_cockpit_markup(CONFIGS['pricing'])}
                        </div>
                    </div>\n                """
        content = content[:m_pr.start(1)] + m_pr.group(1) + pricing_markup + m_pr.group(3) + content[m_pr.end():]
        print("Updated /pricing 3D Cockpit!")
    else:
        print("Could not match /pricing!")

    # 2. /about
    pattern_about = r'(<template id="insilos_about_page"[\s\S]*?<section[^>]*data-name="About Hero"[^>]*>[\s\S]*?<div class="ins-hero-scanlines[^>]*/>\s*)<div class="container py-lg-4 position-relative ins-hero-content-layer">[\s\S]*?</div>\s*</div>\s*(</section>)'
    m_ab = re.search(pattern_about, content)
    if m_ab:
        about_markup = f"""<div class="container py-lg-4 position-relative ins-hero-content-layer">
                        <div class="row align-items-center g-5">
                            <div class="col-lg-6">
                                <div class="ins-pill-badge mb-3">
                                    <span class="ins-live-ping"/>
                                    <span>Company Mission &amp; DNA</span>
                                </div>
                                <h1 class="display-3 fw-bold text-white mb-3">Xây Dựng Lớp Trí Tuệ Cho Những Hoạt Động Vận Hành Quan Trọng</h1>
                                <p class="lead text-secondary mb-4 col-lg-11 p-0">
                                    Insilos được sinh ra để kết nối dữ liệu phân mảnh, mô hình hóa bối cảnh vận hành và trao quyền ra quyết định tự động có thể kiểm toán cho các ngành công nghiệp trọng yếu.
                                </p>
                                <div class="d-flex flex-column flex-sm-row flex-wrap gap-3 mb-4">
                                    <a href="#about-pillars" class="btn btn-primary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <span>Tìm Hiểu Đội Ngũ &amp; Sứ Mệnh</span>
                                        <svg class="ph-duotone ph-arrow-down ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-arrow-down"/></svg>
                                    </a>
                                    <a href="/request-demo" class="btn btn-outline-secondary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <svg class="ph-duotone ph-handshake ph-sm text-cyan"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-handshake"/></svg>
                                        <span>Hợp Tác Đồng Sáng Tạo</span>
                                    </a>
                                </div>
                                <div class="d-flex flex-wrap align-items-center gap-2 pt-3 border-top border-secondary border-opacity-25">
                                    <span class="font-monospace small text-secondary text-uppercase">Engineering DNA:</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Sovereign Architecture</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Zero Lock-in</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">ISO 27001 Certified</span>
                                </div>
                            </div>
{make_cockpit_markup(CONFIGS['about'])}
                        </div>
                    </div>\n                """
        content = content[:m_ab.start(1)] + m_ab.group(1) + about_markup + m_ab.group(2) + content[m_ab.end():]
        print("Updated /about 3D Cockpit!")
    else:
        print("Could not match /about!")

    # 3. /resources
    pattern_res = r'(<template id="insilos_resources_page"[\s\S]*?<section[^>]*data-name="Resources Hero"[^>]*>[\s\S]*?<div class="ins-hero-scanlines[^>]*/>\s*)<div class="container py-lg-4 position-relative ins-hero-content-layer">[\s\S]*?</div>\s*(</section>)'
    m_res = re.search(pattern_res, content)
    if m_res:
        res_markup = f"""<div class="container py-lg-4 position-relative ins-hero-content-layer">
                        <div class="row align-items-center g-5">
                            <div class="col-lg-6">
                                <div class="ins-pill-badge mb-3">
                                    <span class="ins-live-ping"/>
                                    <span>Knowledge &amp; Governance Hub</span>
                                </div>
                                <h1 class="display-3 fw-bold text-white mb-3">Tài Nguyên Vận Hành &amp; Khung Thiết Kế Operational AI</h1>
                                <p class="lead text-secondary mb-4 col-lg-11 p-0">
                                    Hướng dẫn thực tiễn, tiêu chuẩn kiểm toán và phương pháp luận chuyển đổi dữ liệu phân mảnh thành quyết định tự động có thể đo lường cho các kỹ sư trưởng.
                                </p>
                                <div class="d-flex flex-column flex-sm-row flex-wrap gap-3 mb-4">
                                    <a href="#resources-grid" class="btn btn-primary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <span>Khám Phá 40+ Whitepapers</span>
                                        <svg class="ph-duotone ph-arrow-down ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-arrow-down"/></svg>
                                    </a>
                                    <a href="/request-demo" class="btn btn-outline-secondary rounded-pill px-4 py-2 d-inline-flex align-items-center gap-2">
                                        <svg class="ph-duotone ph-headset ph-sm text-cyan"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-headset"/></svg>
                                        <span>Yêu Cầu Tài Liệu Riêng</span>
                                    </a>
                                </div>
                                <div class="d-flex flex-wrap align-items-center gap-2 pt-3 border-top border-secondary border-opacity-25">
                                    <span class="font-monospace small text-secondary text-uppercase">Repository Topics:</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">IDP Blueprint</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Graph Architecture</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">FDA &amp; IEC Guides</span>
                                </div>
                            </div>
{make_cockpit_markup(CONFIGS['resources'])}
                        </div>
                    </div>\n                """
        content = content[:m_res.start(1)] + m_res.group(1) + res_markup + m_res.group(2) + content[m_res.end():]
        print("Updated /resources 3D Cockpit!")
    else:
        print("Could not match /resources!")

    # 4. /request-demo
    pattern_demo = r'(<template id="insilos_request_demo_page"[\s\S]*?<section[^>]*data-name="Title"[^>]*>[\s\S]*?<div class="ins-hero-scanlines[^>]*/>\s*)<div class="container s_allow_columns position-relative ins-hero-content-layer">[\s\S]*?</div>\s*</div>\s*</div>\s*(</section>)'
    m_demo = re.search(pattern_demo, content)
    if m_demo:
        demo_markup = f"""<div class="container s_allow_columns position-relative ins-hero-content-layer py-lg-4">
                        <div class="row align-items-center g-5">
                            <div class="col-lg-6">
                                <div class="d-inline-flex align-items-center gap-2 px-3 py-1 mb-3 rounded-pill bg-white-10 border border-white-20 text-white small">
                                    <span class="ins-pulse-dot"/>
                                    <span class="text-uppercase fw-bold font-monospace">Tailored Operational AI Walkthrough</span>
                                </div>
                                <h1 class="display-3 fw-bold text-white mb-2">Thiết Kế Demo Quanh Dữ Liệu &amp; Quy Trình Của Bạn</h1>
                                <p class="lead text-white-80 mb-4 fs-5 col-lg-11 p-0">Chúng tôi tập trung vào use case cụ thể, KPI cần cải thiện, nguồn dữ liệu và cách nhân sự vận hành thực hiện hành động.</p>
                                <div class="d-flex flex-wrap align-items-center gap-2 pt-3 border-top border-secondary border-opacity-25">
                                    <span class="font-monospace small text-secondary text-uppercase">POC Highlights:</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">48h Sandbox Turnaround</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">NDA Protected</span>
                                    <span class="badge bg-secondary bg-opacity-25 text-white">Chief Architect Consultation</span>
                                </div>
                            </div>
{make_cockpit_markup(CONFIGS['demo'])}
                        </div>
                    </div>\n                """
        content = content[:m_demo.start(1)] + m_demo.group(1) + demo_markup + m_demo.group(2) + content[m_demo.end():]
        print("Updated /request-demo 3D Cockpit!")
    else:
        print("Could not match /request-demo!")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Saved resources_about_demo.xml!")

if __name__ == "__main__":
    update_platform_solutions()
    update_industries()
    update_resources_about_demo()
