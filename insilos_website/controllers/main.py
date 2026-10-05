import os
import re
import time
from html import escape

from odoo import http
from odoo.http import request

from .industry_registry import INDUSTRY_101_REGISTRY


INDUSTRIES = {
    "fsm": {
        "name": "Field Service & Asset Operations",
        "short_name": "Field Service",
        "eyebrow": "FIELD SERVICE INTELLIGENCE",
        "title": "Điều phối đúng kỹ thuật viên trước khi sự cố trở thành thời gian dừng máy.",
        "summary": (
            "Kết nối tình trạng tài sản, yêu cầu dịch vụ, kỹ năng, vị trí, phụ tùng "
            "và tri thức kỹ thuật để tối ưu từng quyết định ngoài hiện trường."
        ),
        "image": "/insilos_website/static/src/img/fsm.webp",
        "image_card": "/insilos_website/static/src/img/fsm-960.webp",
        "image_width": 1920,
        "image_height": 1277,
        "image_alt": "Nhóm kỹ sư công nghiệp làm việc với máy tính bảng trong nhà máy",
        "outcomes": [
            ("First-time fix", "Tăng khả năng xử lý dứt điểm ngay trong lần đầu."),
            ("Faster dispatch", "Ưu tiên và điều phối theo rủi ro tài sản và SLA."),
            ("Lower service cost", "Giảm quãng đường, lượt quay lại và thời gian chờ phụ tùng."),
            ("More uptime", "Chuyển cảnh báo dự báo thành hành động bảo trì."),
        ],
        "problems": [
            ("Điều phối phản ứng", "Công việc chỉ bắt đầu sau khi người dùng hoặc vận hành báo hỏng."),
            ("Lịch sử tài sản phân mảnh", "Kỹ thuật viên thiếu cảnh báo, sửa chữa và tài liệu liên quan."),
            ("Sai kỹ năng hoặc phụ tùng", "Người gần nhất chưa chắc là người phù hợp nhất cho công việc."),
            ("Tri thức khó truy cập", "Manual, kinh nghiệm và hướng dẫn xử lý nằm ở nhiều hệ thống khác nhau."),
        ],
        "applications": [
            "Intelligent Scheduling & Dispatch",
            "Predictive Service Cases",
            "Technician AI Assistant",
            "Remote Diagnosis",
            "Service Parts Optimization",
            "SLA & Escalation Intelligence",
        ],
        "workflow": [
            "Phát hiện rủi ro hoặc tiếp nhận yêu cầu dịch vụ",
            "Đánh giá ảnh hưởng tới SLA, an toàn và hoạt động",
            "Ghép kỹ thuật viên theo kỹ năng, vị trí và lịch",
            "Xác nhận phụ tùng, procedure và work package",
            "Ghi nhận bằng chứng và cập nhật lịch sử tài sản",
        ],
        "systems": ["CRM", "EAM / CMMS", "IoT", "ERP", "GIS", "Mobile Workforce"],
        "pdf_filename": "INSILOS_SOLUTION_022_hvac.pdf",
    },
    "logistics": {
        "name": "Logistics & Supply Chain",
        "short_name": "Logistics",
        "eyebrow": "LOGISTICS INTELLIGENCE",
        "title": "Quan sát mọi vị trí tồn kho, chuyến hàng và rủi ro mạng lưới — Hành lang Hàng hải Bắc - Nam & Điều phối Đa phương thức.",
        "summary": (
            "Hợp nhất nhu cầu, tồn kho, kho vận, vận tải biển và drayage đường bộ: kết nối đồng bộ Cụm cảng nước sâu "
            "Phía Bắc (Lạch Huyện HICT, Đình Vũ, Nam Đình Vũ, Tân Vũ, Hải Phòng, ICD Bắc Ninh) và Cụm cảng Phía Nam "
            "(Cát Lái, Cái Mép - Thị Vải, ICD Phước Long) với hệ thống telematics đội xe drayage và phân luồng thông quan VNACCS/VCIS."
        ),
        "image": "/insilos_website/static/src/img/logistics.webp",
        "image_card": "/insilos_website/static/src/img/logistics-960.webp",
        "image_width": 1920,
        "image_height": 1281,
        "image_alt": "Toàn cảnh trung tâm logistics với container và xe vận chuyển",
        "outcomes": [
            ("Hành lang hàng hải toàn diện", "Kết nối liên thông luồng hàng Lạch Huyện HICT - Đình Vũ (Bắc) và Cát Lái - Cái Mép (Nam)."),
            ("Telematics đội xe drayage", "Giám sát thời gian thực xe đầu kéo Hyundai Xcient, rơ-moóc CIMC và định mức nhiên liệu PVOIL."),
            ("Phân luồng VNACCS/VCIS tự động", "Phân luồng Xanh/Vàng/Đỏ tức thì < 3.2s, giải phóng container khỏi bãi cảng."),
            ("Kiểm soát Demurrage & Detention", "Cảnh báo sớm 48h Free Time: giảm -88% vi phạm quá hạn và cắt -18.4% chi phí phạt ròng."),
        ],
        "problems": [
            ("Ách tắc hai đầu hành lang", "Thiếu kết nối đồng bộ giữa cảng nước sâu Lạch Huyện HICT, Đình Vũ với mạng lưới ICD công nghiệp nội địa."),
            ("Quản lý đội xe drayage thủ công", "Không kiểm soát được định mức tiêu hao nhiên liệu PVOIL và lộ trình xe đầu kéo container."),
            ("Chậm trễ phân luồng hải quan", "Chuyển luồng Vàng/Đỏ do sai lệch chứng từ và mã HS, gây ách tắc tại cổng kiểm hóa."),
            ("Quá tải ngoại lệ Demurrage", "Đội control tower nhận nhiều cảnh báo trễ hạn Free Time hơn khả năng xử lý thủ công."),
        ],
        "applications": [
            "Northern Maritime Corridor (Lạch Huyện HICT - Đình Vũ - Hải Phòng)",
            "Southern Maritime Gateway (Cát Lái - Cái Mép - Thị Vải)",
            "Drayage Fleet Telematics & Fuel Quota (Hyundai Xcient & CIMC)",
            "VNACCS/VCIS Automated Routing (Luồng Xanh / Vàng / Đỏ)",
            "Demurrage & Detention Elimination Shield",
            "Multimodal Feeder Barge & Yard Intelligence",
        ],
        "workflow": [
            "Hợp nhất tín hiệu AIS tàu biển, camera AI cổng cảng và GPS đội xe drayage",
            "Bóc tách tự động chứng từ B/L, C/O, Packing List và đối soát 3 chiều 99.8%",
            "Tự động phân luồng thông quan VNACCS (Luồng Xanh tự động giải phóng < 3.2s)",
            "Điều phối đội xe drayage và tuyến sà lan trung chuyển feeder kết nối ICD nội địa",
            "Cảnh báo sớm 48h hạn Free Time bãi container và đối soát cước vận tải",
        ],
        "systems": ["TOS (Navis N4, Cosmos)", "VNACCS/VCIS", "Telematics (GPS/PVOIL)", "WMS / TMS", "ERP", "AIS Satellite"],
        "pdf_filename": "INSILOS_SOLUTION_051_freight.pdf",
    },
    "energy": {
        "name": "Energy & Utilities",
        "short_name": "Năng lượng",
        "eyebrow": "ENERGY OPERATIONS AI",
        "title": "Dự báo rủi ro và tối ưu từng tài sản năng lượng.",
        "summary": (
            "Kết nối dữ liệu vận hành, kỹ thuật, thị trường và môi trường để nâng cao "
            "độ tin cậy, sản lượng, hiệu suất hiện trường và hiệu quả năng lượng."
        ),
        "image": "/insilos_website/static/src/img/energy.webp",
        "image_card": "/insilos_website/static/src/img/energy-960.webp",
        "image_width": 1920,
        "image_height": 1113,
        "image_alt": "Trang trại điện mặt trời và điện gió tại Việt Nam",
        "outcomes": [
            ("Maximum uptime", "Phát hiện hư hỏng đang hình thành trước khi mất điện."),
            ("Optimized production", "Khuyến nghị điều kiện vận hành trong giới hạn an toàn."),
            ("Better forecasting", "Dự báo tải, phát điện và phơi nhiễm thị trường."),
            ("Lower energy loss", "Nhận diện tiêu thụ, tổn thất và điểm kém hiệu quả."),
        ],
        "problems": [
            ("Tài sản phân tán", "Khó phát hiện tín hiệu sớm trên đội tài sản quy mô lớn."),
            ("Nguồn và tải biến động", "Thời tiết, giá và nguồn phân tán thay đổi cân bằng hệ thống."),
            ("Hệ thống vận hành tách rời", "SCADA, historian, GIS, EMS và EAM không cùng ngữ cảnh."),
            ("Quyết định vận hành thủ công", "Operator phải diễn giải hàng nghìn biến số thay đổi liên tục."),
        ],
        "applications": [
            "Energy Asset Reliability",
            "Generation & Load Forecasting",
            "Process Optimization",
            "Field Service Intelligence",
            "Energy & Emissions Intelligence",
            "Intelligent Operations Center",
        ],
        "workflow": [
            "Thu nhận tín hiệu SCADA, historian và sự kiện tài sản",
            "Phát hiện drift, anomaly và dấu hiệu xuống cấp",
            "Đánh giá ảnh hưởng tới sản lượng, an toàn và thị trường",
            "Đề xuất setpoint, inspection hoặc work order",
            "Theo dõi kết quả và cập nhật mô hình",
        ],
        "systems": ["SCADA", "Historian", "EMS / DMS", "GIS", "EAM", "Weather & Market"],
        "pdf_filename": "INSILOS_SOLUTION_021_electrical.pdf",
    },
    "pharma": {
        "name": "Pharmaceutical Manufacturing",
        "short_name": "Sản xuất dược",
        "eyebrow": "GOVERNED MANUFACTURING AI",
        "title": "Cải thiện hiệu suất lô mà không đánh đổi chất lượng và kiểm soát.",
        "summary": (
            "Kết nối dữ liệu lô, quy trình, phòng thí nghiệm, thiết bị và chất lượng để "
            "phát hiện biến thiên, tăng tốc điều tra và cải thiện hiệu suất sản xuất."
        ),
        "image": "/insilos_website/static/src/img/pharma.webp",
        "image_card": "/insilos_website/static/src/img/pharma-960.webp",
        "image_width": 1920,
        "image_height": 1281,
        "image_alt": "Nhân viên trong môi trường phòng sạch công nghệ cao",
        "outcomes": [
            ("Batch consistency", "Nhận diện biến số liên quan tới yield và chất lượng."),
            ("Faster investigation", "Tập hợp bằng chứng quy trình, lab và bảo trì nhanh hơn."),
            ("Equipment availability", "Phát hiện rủi ro thiết bị sản xuất và utility quan trọng."),
            ("Governed decisions", "Duy trì nguồn, lineage, audit và phê duyệt của con người."),
        ],
        "problems": [
            ("Dữ liệu lô phân mảnh", "MES, historian, LIMS, QMS và thiết bị khó phân tích cùng nhau."),
            ("Điều tra nguyên nhân chậm", "Kỹ sư phải ghép trend, alarm, deviation và kết quả lab thủ công."),
            ("Biến thiên quy trình", "Nguyên liệu, thiết bị và điều kiện quy trình tương tác phức tạp."),
            ("Rủi ro toàn vẹn dữ liệu", "Đầu ra AI thiếu nguồn dẫn, phiên bản hoặc quy trình duyệt."),
        ],
        "applications": [
            "Batch Process Intelligence",
            "Golden Batch Analysis",
            "Equipment Reliability",
            "Deviation Investigation Assistant",
            "Yield Forecasting",
            "SOP & Manufacturing Assistant",
        ],
        "workflow": [
            "Hợp nhất batch, process, lab, quality và maintenance data",
            "So sánh lô với baseline hoặc golden batch",
            "Xếp hạng biến số có khả năng đóng góp vào deviation",
            "Cung cấp bằng chứng, lineage và nguồn dẫn",
            "Đưa kết quả vào review với human approval",
        ],
        "systems": ["MES", "LIMS", "QMS", "Historian", "DCS / SCADA", "EAM"],
        "pdf_filename": "INSILOS_SOLUTION_044_clinic.pdf",
    },
}

INDUSTRY_CLUSTERS = [
    {"id": "all", "name": "Tất Cả Các Ngành", "count": "40+", "icon": "ph-squares-four"},
    {"id": "logistics_trade", "name": "Logistics & Chuỗi Cung Ứng", "icon": "ph-boat"},
    {"id": "finance_banking", "name": "Tài Chính & Thị Trường Vốn", "icon": "ph-chart-line-up"},
    {"id": "manufacturing_industrial", "name": "Sản Xuất & Chế Tạo", "icon": "ph-factory"},
    {"id": "energy_infrastructure", "name": "Năng Lượng & Xây Dựng", "icon": "ph-lightning"},
    {"id": "healthcare_pharma", "name": "Y Tế & Dược Phẩm", "icon": "ph-first-aid"},
    {"id": "fsm_facility", "name": "Dịch Vụ Hiện Trường & Tòa Nhà", "icon": "ph-wrench"},
    {"id": "tech_telecom", "name": "Công Nghệ & Viễn Thông", "icon": "ph-hard-drives"},
    {"id": "retail_consumer", "name": "Bán Lẻ & Hàng Tiêu Dùng", "icon": "ph-shopping-cart"},
    {"id": "hospitality_food", "name": "F&B & Khách Sạn", "icon": "ph-fork-knife"},
    {"id": "public_services", "name": "Chính Phủ & Dịch Vụ Công", "icon": "ph-buildings"},
]

EXTENDED_INDUSTRIES = [
    # 1. Logistics, Trade & Transportation
    {
        "id": "freight",
        "cluster": "logistics_trade",
        "name": "Vận Tải Quốc Tế & Giao Nhận Freight Forwarding",
        "eyebrow": "GLOBAL FREIGHT & MARITIME",
        "summary": "Tự động hóa bóc tách Vận đơn (Bill of Lading), chứng từ hải quan VNACCS/VCIS (Luồng Xanh/Vàng/Đỏ) và đối soát 3 chiều cước cảng Hải Phòng, Lạch Huyện HICT, Cát Lái và Cái Mép.",
        "image_card": "/insilos_website/static/src/img/industries/freight/1.webp",
        "tags": ["IDP 3-Way Match", "B/L OCR", "Lạch Huyện & Cái Mép", "VNACCS Routing", "WCO SAFE"],
        "url": "/industries/logistics",
    },
    {
        "id": "cold_chain",
        "cluster": "logistics_trade",
        "name": "Chuỗi Cung Ứng Lạnh Cold Chain Logistics",
        "eyebrow": "TEMPERATURE-CONTROLLED LOGISTICS & PHARMA GxP",
        "summary": "Giám sát chuỗi cung ứng lạnh dược phẩm & thực phẩm theo chuẩn GDP/GSP. Telemetry nhiệt độ reefer container -20°C và giám sát IoT cold box liên tục.",
        "image_card": "/insilos_website/static/src/img/industries/cold_chain/1.webp",
        "tags": ["GDP/GSP Pharma", "Reefer Telemetry -20°C", "IoT Cold Box", "WHO-GMP Temp SLA"],
        "url": "/industries/cold_chain",
    },
    {
        "id": "warehouse",
        "cluster": "logistics_trade",
        "name": "Kho Bãi Thông Minh & Trung Tâm Phân Phối DC",
        "eyebrow": "SMART WAREHOUSING & YARD",
        "summary": "Tối ưu hóa vị trí lưu kho 3D, điều phối xe tại bãi (Yard Management) và đồng bộ tồn kho thời gian thực với ERP/WMS.",
        "image_card": "/insilos_website/static/src/img/industries/warehouse/1.webp",
        "tags": ["3D Bin Packing", "WMS Ingestion", "Yard Management", "Cycle Counting"],
        "url": "/industries/logistics",
    },
    {
        "id": "import_export",
        "cluster": "logistics_trade",
        "name": "Xuất Nhập Khẩu & Thủ Tục Hải Quan",
        "eyebrow": "TRADE COMPLIANCE & CUSTOMS",
        "summary": "Tự động phân loại mã HS 8-10 số, thẩm định quy tắc xuất xứ FTA (EVFTA, CPTPP) và tích hợp cổng hải quan VNACCS/VCIS luồng Xanh, Vàng, Đỏ.",
        "image_card": "/insilos_website/static/src/img/industries/import_export/1.webp",
        "tags": ["HS Classification", "C/O FTA Form", "VNACCS Luồng Xanh", "Customs Dossier"],
        "url": "/solutions/trade-compliance",
    },
    {
        "id": "courier",
        "cluster": "logistics_trade",
        "name": "Chuyển Phát Nhanh & Giao Hàng Last-Mile",
        "eyebrow": "EXPRESS & LAST-MILE DISPATCH",
        "summary": "Định tuyến động đa điểm, tối ưu hóa cung đường giao hàng theo thời gian thực và quản lý COD tự động.",
        "image_card": "/insilos_website/static/src/img/industries/courier/1.webp",
        "tags": ["Dynamic Routing", "COD Ledger", "Driver AI Assistant", "On-Time SLA"],
        "url": "/industries/logistics",
    },

    # 2. Finance, Banking & Capital Markets
    {
        "id": "fintech",
        "cluster": "finance_banking",
        "name": "Công Nghệ Tài Chính & Thanh Toán Số",
        "eyebrow": "FINANCIAL TECHNOLOGY & PAYMENTS",
        "summary": "Phát hiện gian lận giao dịch mili-giây, đối soát sổ cái micro-ledger và tự động hóa thẩm định tín dụng.",
        "image_card": "/insilos_website/static/src/img/industries/fintech/1.webp",
        "tags": ["Fraud Detection", "Micro-Ledger", "eKYC IDP", "Real-Time Refund"],
        "url": "/solutions/trade-compliance",
    },
    {
        "id": "bank",
        "cluster": "finance_banking",
        "name": "Ngân Hàng Thương Mại & Đối Soát Sổ Cái",
        "eyebrow": "COMMERCIAL BANKING OPERATIONS",
        "summary": "Xử lý khối lượng lớn giao dịch liên ngân hàng, tự động đối soát sao kê và rà soát cấm vận AML/CFT.",
        "image_card": "/insilos_website/static/src/img/industries/bank/1.webp",
        "tags": ["AML Screening", "Statement OCR", "ISO 20022", "GL Reconciliation"],
        "url": "/solutions/trade-compliance",
    },
    {
        "id": "investment",
        "cluster": "finance_banking",
        "name": "Quỹ Đầu Tư & Quản Trị Rủi Ro Danh Mục",
        "eyebrow": "CAPITAL MARKETS & ASSET MANAGEMENT",
        "summary": "Đo lường Value at Risk (VaR 99%), mô phỏng kịch bản stress-test thị trường và tự động hóa phòng hộ rủi ro tỷ giá.",
        "image_card": "/insilos_website/static/src/img/industries/investment/1.webp",
        "tags": ["VaR 99%", "Stress Testing", "FX Hedging", "Portfolio Graph"],
        "url": "/solutions/trade-compliance",
    },
    {
        "id": "insurance",
        "cluster": "finance_banking",
        "name": "Bảo Hiểm Doanh Nghiệp & Giám Định Bồi Thường",
        "eyebrow": "INSURTECH & CLAIMS PROCESSING",
        "summary": "Bóc tách hồ sơ yêu cầu bồi thường (Claims IDP), phát hiện gian lận bảo hiểm và rút ngắn thời gian chi trả.",
        "image_card": "/insilos_website/static/src/img/industries/insurance/1.webp",
        "tags": ["Claims IDP", "Damage Assessment", "Policy Rules", "Fast Settlement"],
        "url": "/solutions/vertical-idp",
    },
    {
        "id": "accounting_firm",
        "cluster": "finance_banking",
        "name": "Kế Toán, Kiểm Toán & Hạch Toán Tự Động",
        "eyebrow": "ACCOUNTING & AUDIT AUTOMATION",
        "summary": "Tự động khớp hóa đơn điện tử với đơn đặt hàng và phiếu nhập kho, tự động định khoản và chuẩn bị báo cáo tài chính.",
        "image_card": "/insilos_website/static/src/img/industries/accounting_firm/1.webp",
        "tags": ["e-Invoice IDP", "3-Way Match", "Tax Audit Trail", "ERP Integration"],
        "url": "/solutions/vertical-idp",
    },

    # 3. Manufacturing & Precision Engineering
    {
        "id": "general_manufacturing",
        "cluster": "manufacturing_industrial",
        "name": "Sản Xuất Chế Tạo & Quản Trị OEE",
        "eyebrow": "DISCRETE & PROCESS MANUFACTURING",
        "summary": "Theo dõi hiệu suất thiết bị tổng thể (OEE), cân bằng dây chuyền sản xuất và dự báo bảo trì máy móc công nghiệp.",
        "image_card": "/insilos_website/static/src/img/industries/general_manufacturing/1.webp",
        "tags": ["OEE Analytics", "Predictive Maintenance", "BOM Management", "Digital Twin"],
        "url": "/industries/fsm",
    },
    {
        "id": "food_manufacturing",
        "cluster": "manufacturing_industrial",
        "name": "Chế Biến Thực Phẩm & Tiêu Chuẩn HACCP",
        "eyebrow": "FOOD & BEVERAGE PRODUCTION",
        "summary": "Quản lý công thức định lượng, kiểm soát điểm tới hạn HACCP và truy xuất phả hệ nguồn gốc nguyên liệu từng mẻ.",
        "image_card": "/insilos_website/static/src/img/industries/food_manufacturing/1.webp",
        "tags": ["HACCP Compliance", "Recipe Control", "Lot Traceability", "Cold Storage"],
        "url": "/industries/pharma",
    },
    {
        "id": "metalwork",
        "cluster": "manufacturing_industrial",
        "name": "Cơ Khí Chính Xác & Gia Công Kim Loại CNC",
        "eyebrow": "PRECISION METALWORKING & CNC",
        "summary": "Tối ưu hóa lịch gá đặt máy CNC, kiểm soát mài mòn dao cụ và tự động hóa kiểm tra kích thước quang học AI.",
        "image_card": "/insilos_website/static/src/img/industries/metalwork/1.webp",
        "tags": ["Tool Wear AI", "CNC Scheduling", "Quality Vision", "Scrap Reduction"],
        "url": "/industries/fsm",
    },
    {
        "id": "chemical",
        "cluster": "manufacturing_industrial",
        "name": "Công Nghiệp Hóa Chất & An Toàn MSDS",
        "eyebrow": "SPECIALTY CHEMICALS & PROCESS AI",
        "summary": "Giám sát thông số phản ứng hóa học (áp suất, nhiệt độ), quản trị tài liệu an toàn hóa chất MSDS và giảm khí thải.",
        "image_card": "/insilos_website/static/src/img/industries/chemical/1.webp",
        "tags": ["Process Safety", "MSDS IDP", "Reaction AI", "Emission Control"],
        "url": "/industries/energy",
    },
    {
        "id": "textile",
        "cluster": "manufacturing_industrial",
        "name": "Dệt May & Thời Trang Xuất Khẩu (FOB/OEM)",
        "eyebrow": "TEXTILE & APPAREL MANUFACTURING",
        "summary": "Quản lý đơn hàng đa mã hàng (Style/Color/Size), tối ưu hóa sơ đồ cắt vải và kiểm soát tiến độ giao hàng xuất khẩu.",
        "image_card": "/insilos_website/static/src/img/industries/textile/1.webp",
        "tags": ["Cutting Optimization", "FOB Planning", "Quality Inspection", "OTIF Tracking"],
        "url": "/industries/logistics",
    },
    {
        "id": "3d_printing",
        "cluster": "manufacturing_industrial",
        "name": "Sản Xuất Bồi Đắp & In 3D Công Nghiệp",
        "eyebrow": "ADDITIVE MANUFACTURING & 3D PRINT",
        "summary": "Tối ưu hóa buồng in, theo dõi khuyết tật lớp in bằng thị giác máy tính và quản lý kho linh kiện số (Digital Inventory).",
        "image_card": "/insilos_website/static/src/img/industries/3d_printing/1.webp",
        "tags": ["Layer Inspection", "Digital Inventory", "Material Usage", "On-Demand Spares"],
        "url": "/industries/fsm",
    },

    # 4. Energy, Utilities & Infrastructure
    {
        "id": "electrical",
        "cluster": "energy_infrastructure",
        "name": "Lưới Điện & Trạm Biến Áp Số IEC 61850",
        "eyebrow": "SMART GRID & SUBSTATION SCADA",
        "summary": "Giám sát thông số SCADA thời gian thực, phân tích khí hòa tan máy biến áp (DGA) và giảm tổn thất truyền tải.",
        "image_card": "/insilos_website/static/src/img/industries/electrical/1.webp",
        "tags": ["IEC 61850", "DGA Transformer", "Grid Balance", "Outage Prediction"],
        "url": "/industries/energy",
    },
    {
        "id": "environmental",
        "cluster": "energy_infrastructure",
        "name": "Năng Lượng Tái Tạo & Giám Sát ESG",
        "eyebrow": "RENEWABLES & ESG INTELLIGENCE",
        "summary": "Dự báo công suất phát điện mặt trời và điện gió với độ chính xác 98.4%, tự động lập báo cáo kiểm kê phát thải carbon.",
        "image_card": "/insilos_website/static/src/img/industries/environmental/1.webp",
        "tags": ["Solar/Wind Forecast", "Carbon Accounting", "ESG Audit Trail", "AGC Dispatch"],
        "url": "/industries/energy",
    },
    {
        "id": "general_contractor",
        "cluster": "energy_infrastructure",
        "name": "Tổng Thầu Xây Dựng & Dự Án EPC",
        "eyebrow": "CONSTRUCTION & EPC MANAGEMENT",
        "summary": "Đối chiếu tiến độ thi công thực tế với mô hình BIM, quản lý hồ sơ nghiệm thu thanh toán và kiểm soát an toàn lao động.",
        "image_card": "/insilos_website/static/src/img/industries/general_contractor/1.webp",
        "tags": ["BIM Integration", "EPC Budgeting", "Safety Compliance", "Subcontractor SLA"],
        "url": "/industries/fsm",
    },

    # 5. Healthcare & Life Sciences
    {
        "id": "hospital",
        "cluster": "healthcare_pharma",
        "name": "Bệnh Viện Đa Khoa & Quản Trị Thiết Bị Y Tế",
        "eyebrow": "HOSPITAL OPERATIONS & MEDTECH",
        "summary": "Quản lý vòng đời trang thiết bị y tế (MRI, CT Scanner), tối ưu hóa thời gian phòng mổ và đối soát hồ sơ bảo hiểm BHYT.",
        "image_card": "/insilos_website/static/src/img/industries/hospital/1.webp",
        "tags": ["Medical Asset EAM", "OR Scheduling", "BHYT Reconciliation", "HL7/FHIR"],
        "url": "/industries/pharma",
    },
    {
        "id": "clinic",
        "cluster": "healthcare_pharma",
        "name": "Phòng Khám Chuyên Khoa & Điều Phối Bác Sĩ",
        "eyebrow": "SPECIALTY CLINIC OPERATIONS",
        "summary": "Tự động hóa tiếp nhận bệnh nhân, xếp lịch khám thông minh theo chuyên khoa và quản lý bệnh án điện tử EMR an toàn.",
        "image_card": "/insilos_website/static/src/img/industries/clinic/1.webp",
        "tags": ["EMR Integration", "Smart Triage", "Doctor Dispatch", "HIPAA Ready"],
        "url": "/industries/pharma",
    },
    {
        "id": "pharmacy_retail",
        "cluster": "healthcare_pharma",
        "name": "Chuỗi Nhà Thuốc Bán Lẻ & Chuẩn GPP",
        "eyebrow": "RETAIL PHARMACY & GPP COMPLIANCE",
        "summary": "Quản lý hạn dùng từng lô thuốc, tự động liên thông dữ liệu Dược Quốc Gia và cảnh báo tương tác thuốc tự động.",
        "image_card": "/insilos_website/static/src/img/industries/pharmacy_retail/1.webp",
        "tags": ["GPP Compliance", "National Drug Sync", "Expiry FEFO", "Prescription IDP"],
        "url": "/industries/pharma",
    },

    # 6. Field Service & Facility Management
    {
        "id": "hvac",
        "cluster": "fsm_facility",
        "name": "Bảo Trì Điện Lạnh Công Nghiệp HVAC",
        "eyebrow": "COMMERCIAL HVAC & REFRIGERATION",
        "summary": "Điều phối kỹ thuật viên theo chứng chỉ tay nghề và vị trí GPS, chẩn đoán từ xa lỗi máy nén chiller qua IoT.",
        "image_card": "/insilos_website/static/src/img/industries/hvac/1.webp",
        "tags": ["FTFR 94.8%", "Compressor IoT", "Skills Routing", "Mobile Work Order"],
        "url": "/industries/fsm",
    },
    {
        "id": "plumbing",
        "cluster": "fsm_facility",
        "name": "Cơ Điện Nước M&E & Hệ Thống Đường Ống",
        "eyebrow": "MECHANICAL & PLUMBING SERVICE",
        "summary": "Xử lý khẩn cấp sự cố rò rỉ, phân tích áp lực đường ống và quản lý kho vật tư phụ tùng trên từng xe kỹ thuật.",
        "image_card": "/insilos_website/static/src/img/industries/plumbing/1.webp",
        "tags": ["Emergency Dispatch", "Van Inventory", "Pressure Telemetry", "SLA Tracking"],
        "url": "/industries/fsm",
    },
    {
        "id": "auto_repair",
        "cluster": "fsm_facility",
        "name": "Trạm Dịch Vụ & Bảo Dưỡng Ô Tô",
        "eyebrow": "AUTOMOTIVE AFTERMARKET & FLEET",
        "summary": "Quản lý quy trình tiếp nhận xe (Check-in), báo giá phụ tùng tự động và nhắc lịch bảo dưỡng định kỳ cho đội xe.",
        "image_card": "/insilos_website/static/src/img/industries/auto_repair/1.webp",
        "tags": ["VIN Reader", "Parts Catalog", "Bay Utilization", "Fleet Maintenance"],
        "url": "/industries/fsm",
    },
    {
        "id": "security_service",
        "cluster": "fsm_facility",
        "name": "Dịch Vụ An Ninh & Giám Sát Tuần Tra",
        "eyebrow": "PHYSICAL SECURITY & PATROL OPS",
        "summary": "Giám sát lộ trình tuần tra bảo vệ theo thời gian thực (NFC/GPS), ghi nhận sự cố bằng hình ảnh và báo cáo số tức thì.",
        "image_card": "/insilos_website/static/src/img/industries/security_service/1.webp",
        "tags": ["GPS Guard Tour", "Incident Logging", "Checkpoint Audit", "Real-Time SOS"],
        "url": "/industries/fsm",
    },

    # 7. Technology, Telecom & Cybersecurity
    {
        "id": "telecom",
        "cluster": "tech_telecom",
        "name": "Viễn Thông & Hạ Tầng Trạm Thu Phát BTS",
        "eyebrow": "TELECOMMUNICATIONS INFRASTRUCTURE",
        "summary": "Giám sát nguồn điện dự phòng, ắc quy và nhiệt độ trạm viễn thông, điều phối kỹ sư ứng cứu thông tin 24/7.",
        "image_card": "/insilos_website/static/src/img/industries/telecom/1.webp",
        "tags": ["BTS Telemetry", "Emergency Dispatch", "Battery Health", "Network Uptime"],
        "url": "/industries/fsm",
    },
    {
        "id": "cybersecurity",
        "cluster": "tech_telecom",
        "name": "An Ninh Mạng & Trung Tâm SOC Zero-Trust",
        "eyebrow": "MANAGED DETECTION & RESPONSE (MDR)",
        "summary": "Tự động tương quan sự kiện bảo mật (SIEM), phát hiện hành vi xâm nhập bất thường và lưu vết kiểm toán pháp lý.",
        "image_card": "/insilos_website/static/src/img/industries/cybersecurity/1.webp",
        "tags": ["SOC 2 Type II", "Zero-Trust Mesh", "Threat Hunting", "ISO 27001"],
        "url": "/about",
    },
    {
        "id": "data_analytics",
        "cluster": "tech_telecom",
        "name": "Xử Lý Dữ Liệu Lớn & Nền Tảng Lakehouse",
        "eyebrow": "BIG DATA & DECISION INTELLIGENCE",
        "summary": "Hợp nhất hàng tỷ bản ghi dữ liệu vận hành phân tán thành đồ thị tri thức sống phục vụ suy luận thời gian thực.",
        "image_card": "/insilos_website/static/src/img/industries/data_analytics/1.webp",
        "tags": ["Knowledge Graph", "Sub-Second SQL", "Feature Store", "Semantic Layer"],
        "url": "/solutions/enterprise-knowledge-graph",
    },
    {
        "id": "software_company",
        "cluster": "tech_telecom",
        "name": "Phát Triển Phần Mềm & Doanh Nghiệp SaaS",
        "eyebrow": "ENTERPRISE SOFTWARE & DEVOPS",
        "summary": "Tích hợp sẵn các API AI bóc tách chứng từ, đồ thị quan hệ và quản lý quyền người dùng đa tầng an toàn.",
        "image_card": "/insilos_website/static/src/img/industries/software_company/1.webp",
        "tags": ["REST & GraphQL", "Multi-Tenant DB", "Sovereign Cloud", "API Quota"],
        "url": "/platform",
    },

    # 8. Retail, Consumer & Luxury Goods
    {
        "id": "grocery_store",
        "cluster": "retail_consumer",
        "name": "Chuỗi Siêu Thị Thực Phẩm & Bán Lẻ FMCG",
        "eyebrow": "SUPERMARKET & GROCERY RETAIL",
        "summary": "Dự báo nhu cầu hàng ngày từng cửa hàng, giảm tỷ lệ hư hỏng hàng tươi sống và tối ưu hóa diện tích kệ hàng (Planogram).",
        "image_card": "/insilos_website/static/src/img/industries/grocery_store/1.webp",
        "tags": ["Demand Forecast", "Waste Reduction", "FEFO Rotation", "Planogram AI"],
        "url": "/industries/logistics",
    },
    {
        "id": "fashion_store",
        "cluster": "retail_consumer",
        "name": "Bán Lẻ Thời Trang & Chuỗi Cửa Hàng",
        "eyebrow": "APPAREL RETAIL & OMNICHANNEL",
        "summary": "Phân bổ tồn kho theo kích cỡ và màu sắc (SKU), điều chuyển hàng liên cửa hàng và cá nhân hóa trải nghiệm mua sắm.",
        "image_card": "/insilos_website/static/src/img/industries/fashion_store/1.webp",
        "tags": ["Size/Color Matrix", "Inter-Store Transfer", "Loyalty CRM", "Omnichannel"],
        "url": "/industries/logistics",
    },
    {
        "id": "electronics_store",
        "cluster": "retail_consumer",
        "name": "Bán Lẻ Điện Máy & Thiết Bị Công Nghệ",
        "eyebrow": "CONSUMER ELECTRONICS & APPLIANCES",
        "summary": "Quản lý bảo hành theo Serial/IMEI, tự động hóa điều phối nhân viên lắp đặt tận nhà và thu hồi hàng cũ.",
        "image_card": "/insilos_website/static/src/img/industries/electronics_store/1.webp",
        "tags": ["Serial/IMEI Tracking", "Home Installation", "Warranty Claims", "Trade-in Ops"],
        "url": "/industries/fsm",
    },
    {
        "id": "jewelry_store",
        "cluster": "retail_consumer",
        "name": "Trang Sức Cao Cấp & Kim Hoàn",
        "eyebrow": "LUXURY JEWELRY & GEMOLOGY",
        "summary": "Quản lý chứng thư giám định đá quý (GIA), theo dõi phả hệ kim loại quý và kiểm soát an ninh từng món hàng giá trị cao.",
        "image_card": "/insilos_website/static/src/img/industries/jewelry_store/1.webp",
        "tags": ["GIA Certificate IDP", "Gem Genealogy", "High-Security RFID", "Bespoke Orders"],
        "url": "/industries/pharma",
    },
    {
        "id": "cosmetics",
        "cluster": "retail_consumer",
        "name": "Mỹ Phẩm & Chăm Sóc Sắc Đẹp",
        "eyebrow": "BEAUTY & COSMETICS BRANDING",
        "summary": "Quản trị phiếu công bố sản phẩm, kiểm soát số lô sản xuất và tự động hóa hồ sơ pháp lý kiểm định an toàn.",
        "image_card": "/insilos_website/static/src/img/industries/cosmetics/1.webp",
        "tags": ["Formula Management", "Batch Dossier", "FDA Approval", "Counterfeit Guard"],
        "url": "/industries/pharma",
    },

    # 9. Hospitality, Food & Beverage
    {
        "id": "hotel",
        "cluster": "hospitality_food",
        "name": "Khách Sạn, Resort & Khu Nghỉ Dưỡng",
        "eyebrow": "HOSPITALITY & PROPERTY MANAGEMENT",
        "summary": "Định giá phòng động theo nhu cầu (Dynamic Pricing), tối ưu hóa lịch bảo trì buồng phòng và cá nhân hóa dịch vụ khách VIP.",
        "image_card": "/insilos_website/static/src/img/industries/hotel/1.webp",
        "tags": ["Dynamic Pricing", "Housekeeping Dispatch", "Guest Profile Graph", "Energy Saving"],
        "url": "/industries/fsm",
    },
    {
        "id": "restaurant",
        "cluster": "hospitality_food",
        "name": "Chuỗi Nhà Hàng & Dịch Vụ Ẩm Thực F&B",
        "eyebrow": "CHAIN RESTAURANT & CENTRAL KITCHEN",
        "summary": "Quản lý bếp trung tâm (Central Kitchen), trừ tồn kho nguyên liệu theo định lượng món và dự báo lượng khách từng khung giờ.",
        "image_card": "/insilos_website/static/src/img/industries/restaurant/1.webp",
        "tags": ["Central Kitchen", "Auto Recipe Depletion", "Footfall Forecast", "Supplier SLA"],
        "url": "/industries/logistics",
    },

    # 10. Public Sector, Legal & Real Estate
    {
        "id": "government",
        "cluster": "public_services",
        "name": "Cơ Quan Hành Chính Công & Dịch Vụ Đô Thị",
        "eyebrow": "GOVTECH & PUBLIC SECTOR EXCELLENCE",
        "summary": "Số hóa và bóc tách hồ sơ hành chính công dân, tự động phân luồng thụ lý và giám sát thời gian giải quyết đúng hạn.",
        "image_card": "/insilos_website/static/src/img/industries/government/1.webp",
        "tags": ["Public Service IDP", "Citizen Portal", "SLA Escalation", "Open Data Graph"],
        "url": "/about",
    },
    {
        "id": "law_firm",
        "cluster": "public_services",
        "name": "Công Ty Luật & Dịch Vụ Pháp Lý Doanh Nghiệp",
        "eyebrow": "LEGALTECH & CONTRACT INTELLIGENCE",
        "summary": "Đối soát hợp đồng kinh tế đa ngôn ngữ, phát hiện điều khoản rủi ro tiềm ẩn và tra cứu án lệ thông minh theo ngữ cảnh.",
        "image_card": "/insilos_website/static/src/img/industries/law_firm/1.webp",
        "tags": ["Contract Analysis", "Clause Comparison", "Precedent Search", "Legal Dossier"],
        "url": "/solutions/trade-compliance",
    },
    {
        "id": "real_estate_agency",
        "cluster": "public_services",
        "name": "Sàn Bất Động Sản & Quản Lý Dự Án",
        "eyebrow": "PROPTECH & REAL ESTATE BROKERAGE",
        "summary": "Quản trị giỏ hàng bất động sản theo thời gian thực, tự động bóc tách hồ sơ pháp lý dự án và khớp nối khách hàng tiềm năng.",
        "image_card": "/insilos_website/static/src/img/industries/real_estate_agency/1.webp",
        "tags": ["Property Graph", "Title Deed IDP", "Lead Matching", "Escrow Ledger"],
        "url": "/solutions/enterprise-knowledge-graph",
    },
]

SOLUTIONS = {
    "vertical-idp": {
        "name": "Vertical Intelligent Document Processing (IDP)",
        "eyebrow": "MULTI-MODAL LOGISTICS OCR & EXTRACTION",
        "title": "Tự động hóa bóc tách và đối soát 100% chứng từ vận tải, logistics và xuất nhập khẩu.",
        "summary": "Kết hợp OCR nhận diện chuyên sâu, IAP AI Router, và bộ kiểm toán Tier 1/2/3 Policy để chuyển đổi Bill of Lading, Invoice, Packing List, C/O và tờ khai hải quan thành dữ liệu có cấu trúc chuẩn xác.",
        "icon": "IDP",
        "industry_keys": ["logistics", "pharma", "fsm"],
        "capabilities": [
            ("Multi-modal OCR & Table Extraction", "Bóc tách chính xác các bảng biểu phức tạp, hóa đơn nhiều trang, chứng từ mờ/nghiêng."),
            ("Governed Policy & Trade Packs", "Tự động áp dụng bộ quy tắc nghiệp vụ 2026.3 theo từng loại chứng từ vận tải."),
            ("Autonomous Preflight & Reconciliation", "Đối soát 3 chiều giữa B/L, Invoice và Packing List để phát hiện sai lệch số lượng/trọng lượng."),
            ("Audit Lineage & Provenance", "Lưu vết bằng chứng trích xuất, mức độ tự tin (confidence score) và căn cứ pháp lý bất biến."),
        ],
        "steps": ["Upload document", "Multi-modal OCR", "Policy extraction", "3-way reconciliation", "ERP/WMS integration"],
        "systems": ["ERP", "WMS", "TMS", "Customs Gateways", "Carrier Portals", "Document Repositories"],
    },
    "enterprise-knowledge-graph": {
        "name": "Enterprise Knowledge Graph",
        "eyebrow": "ONTOLOGY & SEMANTIC REASONING",
        "title": "Hợp nhất mọi thực thể, tài sản, lô hàng và quy trình thành mạng lưới tri thức sống.",
        "summary": "Xóa bỏ rào cản dữ liệu giữa các phòng ban (Data Silos), xây dựng Digital Twins và liên kết ngữ cảnh vận hành theo chuẩn Ontology mở.",
        "icon": "KG",
        "industry_keys": ["fsm", "logistics", "energy", "pharma"],
        "capabilities": [
            ("Cross-silo Entity Resolution", "Tự động nhận diện và hợp nhất các định danh trùng lặp giữa ERP, WMS, CRM và SCADA."),
            ("Operational Ontology & Graph", "Mô hình hóa quan hệ giữa nhà máy, thiết bị, linh kiện, tuyến đường, lô hàng và nhân sự."),
            ("Semantic Search & Reasoning", "Truy vấn dữ liệu vận hành bằng ngôn ngữ tự nhiên với suy luận logic đa tầng."),
            ("Impact & Root-Cause Analysis", "Mô phỏng hiệu ứng domino khi một mắt xích trong chuỗi cung ứng hoặc thiết bị gặp sự cố."),
        ],
        "steps": ["Ingest data sources", "Entity resolution", "Graph construction", "Semantic reasoning", "Actionable insights"],
        "systems": ["ERP", "EAM", "MES", "IoT", "WMS", "Graph Databases"],
    },
    "trade-compliance": {
        "name": "Trade Compliance & Customs Intelligence",
        "eyebrow": "REGULATORY & TARIFF AUTOMATION",
        "title": "Phân loại mã HS tự động, kiểm soát quy tắc xuất xứ C/O và thẩm định hồ sơ hải quan.",
        "summary": "Tích hợp biểu thuế xuất nhập khẩu, hiệp định thương mại tự do (FTA) và cơ chế Legal-Policy Dossier để phòng ngừa rủi ro phạt thuế và chậm thông quan.",
        "icon": "TC",
        "industry_keys": ["logistics", "pharma"],
        "capabilities": [
            ("Automated HS Code Classification", "Đề xuất mã HS 8-10 số kèm căn cứ giải trình pháp lý và mức thuế suất ưu đãi."),
            ("Rules of Origin (C/O) Verification", "Tự động kiểm tra tiêu chí xuất xứ hàng hóa (PSR, RVC, CTC) theo từng FTA (EVFTA, CPTPP, RCEP)."),
            ("Sanctions & Denied Party Screening", "Rà soát đối tác, tàu vận chuyển và cảng biển theo danh sách trừng phạt quốc tế thời gian thực."),
            ("Legal Dossier & Audit Trails", "Lưu trữ hồ sơ chứng minh tuân thủ sẵn sàng cho thanh tra sau thông quan."),
        ],
        "steps": ["Analyze product specs", "Classify HS code", "Verify origin rules", "Screen compliance", "Issue declaration ready pack"],
        "systems": ["Customs Portals", "ERP", "WMS", "Legal Tariff DB", "Trade Compliance Repositories"],
    },
    "field-service-intelligence": {
        "name": "Field Service & Intelligent Asset Operations",
        "eyebrow": "WORKFORCE & PREDICTIVE ASSET OPERATIONS",
        "title": "Điều phối đúng kỹ thuật viên với đầy đủ phụ tùng và tri thức trước khi sự cố xảy ra.",
        "summary": "Kết nối tín hiệu telemetry IoT, lịch sử tài sản, kỹ năng chứng chỉ, vị trí GPS và tài liệu kỹ thuật để nâng cao tỷ lệ xử lý dứt điểm ngay lần đầu (First-Time Fix Rate).",
        "icon": "FSM",
        "industry_keys": ["fsm", "energy", "pharma"],
        "capabilities": [
            ("Predictive Service Cases & IoT Telemetry", "Tự động phát hiện bất thường từ cảm biến rung/nhiệt và khởi tạo lệnh sửa chữa trước khi hỏng máy."),
            ("Dynamic Skills & Route Dispatch", "Tối ưu hóa lộ trình di chuyển và ghép kỹ thuật viên theo chứng chỉ chuyên môn và vị trí thời gian thực."),
            ("Technician Digital Briefing Pack", "Cung cấp sơ đồ kỹ thuật, danh mục phụ tùng cần mang theo và checklist quy trình an toàn ngay trên thiết bị di động."),
            ("Closed-Loop Asset Intelligence", "Ghi nhận kết quả hiện trường, âm thanh máy chạy và hình ảnh sau sửa chữa để tự động cập nhật độ tin cậy tài sản."),
        ],
        "steps": ["Detect asset risk", "Prioritize service", "Match technician", "Prepare work", "Close the loop"],
        "systems": ["CRM", "EAM / CMMS", "ERP", "IoT", "GIS", "Mobile Workforce"],
    },
    "asset-reliability": {
        "name": "Asset Reliability",
        "eyebrow": "PREDICTIVE MAINTENANCE",
        "title": "Phát hiện hư hỏng đang hình thành trước khi hoạt động bị gián đoạn.",
        "summary": "Kết hợp time-series, sự kiện, work order và bối cảnh vận hành để xếp hạng rủi ro thiết bị và đề xuất hành động.",
        "icon": "AR",
        "industry_keys": ["fsm", "energy", "pharma", "logistics"],
        "capabilities": [
            ("Condition monitoring", "Theo dõi condition indicator và anomaly theo tài sản."),
            ("Failure risk ranking", "Ưu tiên tài sản theo xác suất, tác động và thời gian hành động."),
            ("Evidence & explainability", "Hiển thị signal, trend và lịch sử hỗ trợ cảnh báo."),
            ("Maintenance workflow", "Kết nối khuyến nghị với inspection và work order."),
        ],
        "steps": ["Collect signals", "Detect drift", "Assess impact", "Recommend action", "Track outcome"],
        "systems": ["SCADA", "Historian", "IoT", "EAM / CMMS", "ERP", "Engineering data"],
    },
    "logistics-control-tower": {
        "name": "Logistics Control Tower",
        "eyebrow": "SUPPLY NETWORK INTELLIGENCE",
        "title": "Một operating view cho demand, inventory, shipment và network exception.",
        "summary": "Dự báo gián đoạn, xếp hạng tác động và điều phối hành động recovery trên toàn mạng lưới logistics Bắc - Nam.",
        "icon": "LC",
        "industry_keys": ["logistics", "pharma"],
        "capabilities": [
            ("Hành lang Bắc - Nam", "Kết nối toàn diện cụm cảng Lạch Huyện HICT - Đình Vũ (Bắc) và Cát Lái - Cái Mép (Nam)."),
            ("Telematics đội xe drayage", "Giám sát thời gian thực xe đầu kéo Hyundai Xcient, rơ-moóc CIMC và định mức xăng dầu PVOIL."),
            ("Phân luồng VNACCS/VCIS", "Tự động phân luồng hải quan Luồng Xanh, Vàng, Đỏ và đối soát manifest điện tử."),
            ("Scenario recovery & Demurrage", "Mô phỏng reroute sà lan feeder, chuyển bãi container và cảnh báo sớm 48h hạn Free Time."),
        ],
        "steps": ["Sense network", "Predict exception", "Rank impact", "Simulate recovery", "Orchestrate action"],
        "systems": ["ERP", "OMS", "WMS", "TMS", "Telematics (GPS/PVOIL)", "TOS (Navis/Cosmos)", "VNACCS/VCIS", "External risk"],
    },
    "process-optimization": {
        "name": "Process Optimization",
        "eyebrow": "CONSTRAINED OPTIMIZATION",
        "title": "Khuyến nghị điều kiện vận hành tốt hơn trong giới hạn kỹ thuật và an toàn.",
        "summary": "Kết hợp process data, engineering constraints và mục tiêu kinh doanh để đề xuất setpoint hoặc operating window có giải thích.",
        "icon": "PO",
        "industry_keys": ["energy", "pharma"],
        "capabilities": [
            ("Multivariate models", "Nhận diện tương tác giữa nhiều biến quy trình."),
            ("Constrained recommendations", "Tôn trọng operating envelope và rule vận hành."),
            ("What-if simulation", "So sánh tác động trước khi áp dụng thay đổi."),
            ("Operator feedback", "Ghi nhận phê duyệt, từ chối và kết quả thực tế."),
        ],
        "steps": ["Model process", "Detect opportunity", "Apply constraints", "Recommend setpoint", "Measure value"],
        "systems": ["DCS / SCADA", "Historian", "MES", "Lab", "Energy market", "Engineering models"],
    },
    "operations-assistant": {
        "name": "Operations AI Assistant",
        "eyebrow": "ENTERPRISE KNOWLEDGE & AGENTS",
        "title": "Hỏi bằng ngôn ngữ tự nhiên. Nhận câu trả lời có nguồn dẫn từ dữ liệu vận hành.",
        "summary": "Kết nối tài liệu, sự kiện, work order, KPI và time-series để hỗ trợ điều tra, briefing và ra quyết định.",
        "icon": "OA",
        "industry_keys": ["fsm", "logistics", "energy", "pharma"],
        "capabilities": [
            ("Cited answers", "Mỗi câu trả lời gắn với nguồn dữ liệu hoặc tài liệu liên quan."),
            ("Role-aware context", "Giới hạn thông tin và hành động theo vai trò người dùng."),
            ("Investigation agents", "Tự động thu thập evidence và xếp hạng giả thuyết."),
            ("Workflow actions", "Tạo draft work order, case, briefing hoặc escalation."),
        ],
        "steps": ["Ask", "Retrieve context", "Analyze evidence", "Explain", "Propose action"],
        "systems": ["Documents", "EAM", "ERP", "MES", "Historian", "Data warehouse"],
    },
    "governed-manufacturing-ai": {
        "name": "Governed Manufacturing AI",
        "eyebrow": "PHARMA & CONTROLLED OPERATIONS",
        "title": "AI có lineage, nguồn dẫn, phân quyền và phê duyệt cho môi trường sản xuất được kiểm soát.",
        "summary": "Hỗ trợ batch review, deviation investigation và process intelligence mà không loại bỏ trách nhiệm của con người.",
        "icon": "GA",
        "industry_keys": ["pharma"],
        "capabilities": [
            ("Data lineage", "Theo dõi nguồn, thời điểm, phiên bản và phép biến đổi dữ liệu."),
            ("Human approval", "Thiết kế điểm duyệt rõ ràng trước hành động quan trọng."),
            ("Auditability", "Ghi lại prompt, evidence, output và quyết định của người dùng."),
            ("Controlled deployment", "Hỗ trợ môi trường customer-controlled và policy theo vai trò."),
        ],
        "steps": ["Connect governed data", "Investigate", "Cite evidence", "Review", "Approve & record"],
        "systems": ["MES", "LIMS", "QMS", "Historian", "SOP repository", "Identity & access"],
    },
}


ARTICLES = {
    "operational-ai": {
        "title": "Operational AI là gì?",
        "eyebrow": "FOUNDATION GUIDE",
        "summary": "Một cách tiếp cận kết nối dữ liệu, mô hình, bối cảnh và workflow để cải thiện quyết định vận hành.",
        "sections": [
            ("Từ dashboard đến hệ thống hành động", "Dashboard mô tả điều đã xảy ra. Operational AI bổ sung dự báo, bằng chứng, ràng buộc và workflow để người dùng quyết định điều nên làm tiếp theo."),
            ("Bối cảnh là thành phần cốt lõi", "Một tín hiệu chỉ có ý nghĩa khi được liên kết với tài sản, vị trí, quy trình, đơn hàng, lô sản xuất, SLA và lịch sử hoạt động."),
            ("Đo giá trị bằng kết quả", "Use case nên gắn với uptime, first-time fix, OTIF, yield, cycle time, năng lượng hoặc thời gian điều tra thay vì chỉ số sử dụng AI."),
        ],
    },
    "industrial-ai-agents": {
        "title": "AI agent trong vận hành công nghiệp",
        "eyebrow": "AGENTIC WORKFLOWS",
        "summary": "Agent hữu ích khi có thể thu thập evidence, tuân thủ quyền hạn và chuyển đề xuất vào quy trình thực thi.",
        "sections": [
            ("Agent không chỉ là chat", "Một agent vận hành cần kết nối tool, data, policy và workflow; câu trả lời chỉ là một phần của trải nghiệm."),
            ("Human-in-the-loop", "Các quyết định có ảnh hưởng tới an toàn, chất lượng hoặc cam kết khách hàng cần điểm duyệt rõ ràng và khả năng truy vết."),
            ("Bắt đầu từ workflow hẹp", "Nên khởi đầu với một nhiệm vụ có trigger, dữ liệu, KPI và owner rõ ràng; sau đó mở rộng khi đã đo được kết quả."),
        ],
    },
    "governed-ai-pharma": {
        "title": "Thiết kế AI có kiểm soát cho sản xuất dược",
        "eyebrow": "PHARMACEUTICAL MANUFACTURING",
        "summary": "Các nguyên tắc kỹ thuật và vận hành để dùng AI hỗ trợ mà vẫn duy trì traceability và trách nhiệm con người.",
        "sections": [
            ("Nguồn dữ liệu và lineage", "Mỗi insight cần chỉ ra dữ liệu nguồn, thời điểm, phiên bản và các phép biến đổi quan trọng."),
            ("Phân tách hỗ trợ và phê duyệt", "AI có thể chuẩn bị evidence, gợi ý contributor và tạo draft; phê duyệt cuối vẫn thuộc quy trình được kiểm soát."),
            ("Quản lý thay đổi", "Model, prompt, retrieval source và workflow cần versioning, test và release control phù hợp với mức độ rủi ro."),
        ],
    },
    "vertical-idp-logistics-roi": {
        "title": "Mô hình đo lường ROI khi tự động hóa chứng từ logistics",
        "eyebrow": "LOGISTICS & SUPPLY CHAIN ROI",
        "summary": "Khung đánh giá hiệu quả kinh tế khi triển khai OCR đa phương thức và đối soát 3 chiều cho Bill of Lading, Invoice và Packing List.",
        "sections": [
            ("Tiết kiệm chi phí nhập liệu trực tiếp", "Giảm 75-85% giờ làm việc thủ công của đội ngũ chứng từ xuất nhập khẩu và loại bỏ 98% lỗi sai số liệu."),
            ("Ngăn ngừa chi phí Demurrage & Detention", "Phát hiện sớm sai lệch chứng từ trước khi tàu cập cảng giúp hàng hóa thông quan ngay trong ngày, tiết kiệm hàng chục nghìn USD tiền lưu kho bãi."),
            ("Thời gian hoàn vốn (Payback Period)", "Hầu hết các doanh nghiệp logistics và xuất nhập khẩu đạt điểm hòa vốn và sinh lời chỉ sau 3.5 đến 4.2 tháng vận hành."),
        ],
    },
    "trade-compliance-handbook": {
        "title": "Sổ tay tự động hóa phân loại HS và quy tắc xuất xứ FTA",
        "eyebrow": "CUSTOMS & TRADE REGULATION",
        "summary": "Hướng dẫn ứng dụng AI để tra cứu mã HS 8-10 số, tối ưu hóa C/O ưu đãi theo EVFTA, CPTPP và chuẩn bị hồ sơ thanh tra sau thông quan.",
        "sections": [
            ("Phân loại mã HS chính xác theo 6 quy tắc GIR", "Sử dụng mô hình ngôn ngữ chuyên sâu kết hợp biểu thuế WCO để xác định đúng mã số hàng hóa kèm căn cứ pháp lý rõ ràng."),
            ("Tự động hóa tính toán chuyển đổi phân nhóm (CTC) và RVC", "Đánh giá tỷ lệ hàm lượng giá trị khu vực từ định mức BOM để chọn hiệp định thương mại có thuế suất ưu đãi nhất."),
            ("Xây dựng Legal-Policy Dossier bất biến", "Lưu trữ toàn bộ lịch sử tra cứu, chứng từ gốc và dữ liệu tính toán sẵn sàng phục vụ thanh tra hải quan sau 5 năm."),
        ],
    },
}

INDUSTRY_SELECTIONS = [
    ("", "Chọn ngành"),
    ("fsm", "Field Service & Asset Operations"),
    ("logistics", "Logistics & Supply Chain"),
    ("energy", "Energy & Utilities"),
    ("pharma", "Pharmaceutical Manufacturing"),
    ("other", "Ngành khác"),
]

USE_CASE_SELECTIONS = [
    ("", "Chọn use case"),
    ("vertical_idp", "Vertical Intelligent Document Processing (IDP)"),
    ("knowledge_graph", "Enterprise Knowledge Graph"),
    ("trade_compliance", "Trade Compliance & Customs Intelligence"),
    ("field_service", "Field Service & Intelligent Asset Operations"),
    ("reliability", "Asset Reliability"),
    ("control_tower", "Logistics Control Tower"),
    ("process", "Process Optimization"),
    ("assistant", "Operations AI Assistant"),
    ("governed_ai", "Governed Manufacturing AI"),
    ("discovery", "Chưa xác định — cần tư vấn"),
]

COMPANY_SIZE_SELECTIONS = [
    ("", "Chọn quy mô"),
    ("1_49", "1–49"),
    ("50_249", "50–249"),
    ("250_999", "250–999"),
    ("1000_plus", "1.000+"),
]

CORE_ERP_SELECTIONS = [
    ("", "Chọn hệ thống Core ERP"),
    ("sap_s4", "SAP S/4HANA"),
    ("sap_ecc", "SAP ECC 6.0"),
    ("oracle", "Oracle Fusion / EBS"),
    ("odoo", "Insilos ERP"),
    ("inhouse", "Hệ thống nội bộ (In-house / Legacy)"),
    ("other", "Khác"),
]

PROJECT_TIMELINE_SELECTIONS = [
    ("", "Chọn tiến độ dự kiến"),
    ("immediate", "Triển khai ngay (< 1 tháng)"),
    ("1_3_mo", "1 – 3 tháng"),
    ("3_6_mo", "3 – 6 tháng"),
    ("explore", "Nghiên cứu khả thi / Khảo sát"),
]

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
STATIC_PAGE_PATHS = {
    "/",
    "/platform",
    "/solutions",
    "/industries",
    "/resources",
    "/pricing",
    "/about",
    "/media-credits",
    "/request-demo",
    "/privacy",
    "/thank-you",
    "/trust",
    "/compliance",
    "/sandbox",
    "/showcase-3d",
    "/interactive-3d",
}
DEDICATED_SOLUTION_SLUGS = {
    "trade-compliance",
    "vertical-idp",
    "enterprise-knowledge-graph",
    "field-service-intelligence",
}
DEDICATED_INDUSTRY_SLUGS = {"logistics", "pharma", "energy", "fsm"}


def _is_valid_slug(slug: str) -> bool:
    if not slug or not isinstance(slug, str):
        return False
    if ".." in slug or "/" in slug or "\\" in slug:
        return False
    return bool(SLUG_RE.match(slug))


STATIC_URLS = [
    "/",
    "/platform",
    "/solutions",
    "/industries",
    "/resources",
    "/pricing",
    "/about",
    "/request-demo",
    "/privacy",
    "/privacy-policy",
    "/media-credits",
    "/trust",
    "/compliance",
    "/sandbox",
    "/showcase-3d",
    "/interactive-3d",
]


def sitemap_static(env, rule, qs):
    for loc in STATIC_URLS:
        if not qs or qs.lower() in loc.lower():
            yield {"loc": loc}


def sitemap_industries(env, rule, qs):
    all_keys = set(INDUSTRIES.keys()).union(INDUSTRY_101_REGISTRY.keys())
    for key in sorted(all_keys):
        loc = f"/industries/{key}"
        if not qs or qs.lower() in loc.lower():
            yield {"loc": loc}


def sitemap_solutions(env, rule, qs):
    for key in SOLUTIONS:
        loc = f"/solutions/{key}"
        if not qs or qs.lower() in loc.lower():
            yield {"loc": loc}


def sitemap_articles(env, rule, qs):
    for key in ARTICLES:
        loc = f"/resources/{key}"
        if not qs or qs.lower() in loc.lower():
            yield {"loc": loc}


_SHOWCASE_HTML_CACHE = {}
_SHOWCASE_CACHE_TTL = 300.0


class InsilosWebsite(http.Controller):
    def _base_values(self, **extra):
        values = {
            "industries": INDUSTRIES,
            "solutions": SOLUTIONS,
            "articles": ARTICLES,
            "industry_clusters": INDUSTRY_CLUSTERS,
            "extended_industries": EXTENDED_INDUSTRIES,
            "industry_101_registry": INDUSTRY_101_REGISTRY,
        }
        # Website Designer chỉ gắn branding (data-oe-model) khi main_object là
        # website.page (xem website/models/is_qweb.py:50-55). Route Python tự
        # render thì main_object mặc định là chính view, nên block bị khoá.
        # Only query website.page for registered top-level static pages to avoid redundant DB roundtrips
        current_path = request.httprequest.path
        if current_path in STATIC_PAGE_PATHS:
            page = request.env["website.page"].sudo().search(
                [("url", "=", current_path)], limit=1
            )
            if page:
                values["main_object"] = page
        if request and hasattr(request, "website") and request.website and request.website.custom_code_head:
            if "insilos.com" in request.website.custom_code_head:
                cleaned_head = re.sub(r'<link\s+rel=["\']canonical["\']\s+href=["\']https://insilos\.com/?["\']\s*/?>', '', request.website.custom_code_head)
                if cleaned_head != request.website.custom_code_head:
                    request.website.custom_code_head = cleaned_head
        values.update(extra)
        return values

    @http.route("/", type="http", auth="public", website=True, sitemap=True)
    def home(self, **kwargs):
        host = (request.httprequest.host or "").lower()
        website_name = (request.website.name or "").lower() if getattr(request, "website", None) else ""
        if "innoria" in host or "innoria" in website_name:
            if request.env["ir.ui.view"].sudo().search([("key", "=", "insilos_website.innoria_homepage_template")], limit=1):
                return request.render("insilos_website.innoria_homepage_template", self._base_values())
        return request.render("insilos_website.insilos_homepage", self._base_values())

    @http.route(["/platform", "/artificial-intelligence-platform", "/vi/platform", "/vi/artificial-intelligence-platform"], type="http", auth="public", website=True, sitemap=True)
    def platform(self, **kwargs):
        return request.render("insilos_website.insilos_platform_page", self._base_values())

    @http.route(["/no-code-platform", "/vi/no-code-platform"], type="http", auth="public", website=True, sitemap=True)
    def no_code_platform(self, **kwargs):
        return request.render("insilos_website.innoria_digiforce_page", self._base_values())

    @http.route(["/blockchain", "/vi/blockchain"], type="http", auth="public", website=True, sitemap=True)
    def blockchain(self, **kwargs):
        return request.render("insilos_website.innoria_blockchain_page", self._base_values())

    @http.route(["/solutions", "/erp-combine-with-ai", "/vi/solutions", "/vi/erp-combine-with-ai"], type="http", auth="public", website=True, sitemap=True)
    def solutions(self, **kwargs):
        return request.render("insilos_website.insilos_solutions_page", self._base_values())

    @http.route(
        ["/solutions/<string:solution>", "/solutions/<path:solution>"],
        type="http",
        auth="public",
        website=True,
        sitemap=sitemap_solutions,
    )
    def solution_detail(self, solution, **kwargs):
        if not _is_valid_slug(solution):
            return request.not_found()

        solution_aliases = {
            "autonomous-trade-compliance": "/solutions/trade-compliance",
            "fsm": "/solutions/field-service-intelligence",
            "field-service": "/solutions/field-service-intelligence",
            "logistics": "/solutions/logistics-control-tower",
            "idp": "/solutions/vertical-idp",
            "knowledge-graph": "/solutions/enterprise-knowledge-graph",
            "customs": "/solutions/trade-compliance",
            "predictive-maintenance": "/solutions/asset-reliability",
            "energy": "/industries/energy",
            "pharma": "/industries/pharma",
            "capital-markets": "/solutions/trade-compliance",
        }
        if solution in solution_aliases:
            return request.redirect(solution_aliases[solution])
        solution_data = SOLUTIONS.get(solution)
        if not solution_data:
            return request.not_found()
        related_industries = [(key, INDUSTRIES.get(key, INDUSTRY_101_REGISTRY.get(key))) for key in solution_data["industry_keys"] if key in INDUSTRIES or key in INDUSTRY_101_REGISTRY]
        if solution in DEDICATED_SOLUTION_SLUGS:
            template_name = f"insilos_website.insilos_solution_{solution.replace('-', '_')}_page"
            return request.render(
                template_name,
                self._base_values(solution=solution_data, solution_key=solution, related_industries=related_industries),
            )
        return request.render(
            "insilos_website.insilos_solution_page",
            self._base_values(solution=solution_data, solution_key=solution, related_industries=related_industries),
        )

    @http.route(["/industries", "/industry", "/ultra-ai-vision", "/vi/industries", "/vi/ultra-ai-vision"], type="http", auth="public", website=True, sitemap=True)
    def industries(self, **kwargs):
        return request.render("insilos_website.insilos_industries_page", self._base_values())

    @http.route(
        [
            "/industries/<string:industry>",
            "/industry/<string:industry>",
            "/industries/<path:industry>",
            "/industry/<path:industry>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=sitemap_industries,
    )
    def industry(self, industry, **kwargs):
        if not _is_valid_slug(industry):
            return request.not_found()

        industry_data = INDUSTRY_101_REGISTRY.get(industry) or INDUSTRIES.get(industry)
        if not industry_data:
            return request.not_found()
        if industry == "cold_chain":
            industry_data = dict(industry_data)
            industry_data.update({
                "summary": (
                    "Hệ thống giám sát chuỗi cung ứng lạnh dược phẩm & thực phẩm theo chuẩn "
                    "GDP/GSP/WHO. Thu thập telemetry nhiệt độ thời gian thực từ container lạnh "
                    "Reefer (-20°C đến +8°C), IoT Cold Box và cảnh báo tức thì nguy cơ đứt gãy dải nhiệt."
                ),
                "philosophy": (
                    "Bảo toàn 100% chất lượng dược phẩm, sinh phẩm y tế và nông sản xuất khẩu thông "
                    "qua mạng lưới cảm biến IoT không dây và nhật trình kiểm soát nhiệt độ tự động."
                ),
                "tags": [
                    "GDP/GSP Pharma",
                    "Reefer -20°C Telemetry",
                    "IoT Cold Box",
                    "VAS 200/133",
                ],
                "pain_points": [
                    {
                        "manual": "Ghi chép nhiệt độ container thủ công hoặc chỉ đọc data logger sau khi hàng về kho, không thể cứu vãn khi nhiệt độ âm sâu (-20°C) bị gián đoạn.",
                        "insilos": "Telemetry thời gian thực từ trạm Reefer và IoT Cold Box truyền liên tục 60s/lần, tự động kích hoạt cảnh báo vượt ngưỡng trước khi hỏng lô hàng."
                    },
                    {
                        "manual": "Hồ sơ đối soát nhiệt độ theo chuẩn GDP/GSP và FDA 21 CFR Part 11 phân mảnh, mất 3-5 ngày tổng hợp biên bản khi thanh tra.",
                        "insilos": "Xuất báo cáo Audit Trail nhiệt độ tức thì có chữ ký số Merkle DAG bất biến, chứng minh chuỗi bảo quản lạnh liên tục 100% hành trình."
                    },
                    {
                        "manual": "Chi phí bồi thường hư hỏng hàng nhạy nhiệt và phụ phí cắm điện container lạnh tại bãi cảng (Plug-in fees) tăng cao do điều phối chậm.",
                        "insilos": "AI dự báo điểm lệch nhiệt và tối ưu lộ trình xe lạnh, giảm 85% rủi ro hủy lô hàng sinh phẩm và cắt giảm chi phí cắm điện bãi cảng."
                    }
                ],
            })
        related_solutions = [
            (key, solution)
            for key, solution in SOLUTIONS.items()
            if industry in solution.get("industry_keys", [])
        ]
        if industry in DEDICATED_INDUSTRY_SLUGS:
            template_name = f"insilos_website.insilos_industry_{industry.replace('-', '_')}_page"
            return request.render(
                template_name,
                self._base_values(
                    industry=industry_data,
                    industry_key=industry,
                    related_solutions=related_solutions,
                ),
            )
        return request.render(
            "insilos_website.insilos_industry_page",
            self._base_values(
                industry=industry_data,
                industry_key=industry,
                related_solutions=related_solutions,
            ),
        )

    @http.route(
        [
            "/industry/<string:industry>/brochure",
            "/industries/<string:industry>/brochure",
            "/industry/<path:industry>/brochure",
            "/industries/<path:industry>/brochure",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def industry_brochure(self, industry, **kwargs):
        if not _is_valid_slug(industry):
            return request.not_found()
        ind_data = INDUSTRY_101_REGISTRY.get(industry) or INDUSTRIES.get(industry)
        if not ind_data:
            return request.not_found()
        pdf_filename = ind_data.get("pdf_filename")
        if not pdf_filename:
            import glob
            for cand_dir in ["/home/zen/insilos_ee/pdf_standalone", "/app/pdf_standalone", "pdf_standalone"]:
                if os.path.exists(cand_dir):
                    matches = glob.glob(os.path.join(cand_dir, f"INSILOS_SOLUTION_*_{industry}.pdf"))
                    if matches:
                        pdf_filename = os.path.basename(matches[0])
                        break
        if not pdf_filename:
            return request.not_found()

        # 1. Check local candidates
        candidate_paths = [
            os.path.join("/home/zen/insilos_ee/pdf_standalone", pdf_filename),
            os.path.join("/app/pdf_standalone", pdf_filename),
            os.path.join("/home/insilos/.local/share/Insilos/pdf_standalone", pdf_filename),
            os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")), "pdf_standalone", pdf_filename),
            os.path.join(os.getcwd(), "pdf_standalone", pdf_filename),
        ]
        for cp in candidate_paths:
            if os.path.exists(cp):
                with open(cp, "rb") as f:
                    pdf_data = f.read()
                return request.make_response(
                    pdf_data,
                    headers=[
                        ("Content-Type", "application/pdf"),
                        ("Content-Disposition", f"inline; filename=\"{pdf_filename}\""),
                        ("Cache-Control", "public, max-age=86400"),
                    ],
                )

        # 2. Check MinIO / Internal S3
        import urllib.request
        minio_url = f"http://10.123.214.249:9000/insilos-templates/pdf_standalone/{pdf_filename}"
        try:
            req = urllib.request.Request(minio_url, headers={"User-Agent": "InsilosSaaS/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    pdf_data = resp.read()
                    return request.make_response(
                        pdf_data,
                        headers=[
                            ("Content-Type", "application/pdf"),
                            ("Content-Disposition", f"inline; filename=\"{pdf_filename}\""),
                            ("Cache-Control", "public, max-age=86400"),
                        ],
                    )
        except Exception:
            pass

        # 3. Check Public S3 Fallback
        s3_url = f"https://s3.iz.io.vn/insilos-filestore/pdf_standalone/{pdf_filename}"
        try:
            req = urllib.request.Request(s3_url, headers={"User-Agent": "InsilosSaaS/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    pdf_data = resp.read()
                    return request.make_response(
                        pdf_data,
                        headers=[
                            ("Content-Type", "application/pdf"),
                            ("Content-Disposition", f"inline; filename=\"{pdf_filename}\""),
                            ("Cache-Control", "public, max-age=86400"),
                        ],
                    )
        except Exception:
            pass

        return request.not_found()

    @http.route("/resources", type="http", auth="public", website=True, sitemap=True)
    def resources(self, **kwargs):
        return request.render("insilos_website.insilos_resources_page", self._base_values())

    @http.route(
        ["/resources/<string:article>", "/resources/<path:article>"],
        type="http",
        auth="public",
        website=True,
        sitemap=sitemap_articles,
    )
    def resource_article(self, article, **kwargs):
        if not _is_valid_slug(article):
            return request.not_found()
        article_aliases = {
            "predictive-maintenance-whitepaper": "/resources/operational-ai",
            "whitepaper": "/resources/operational-ai",
            "idp-roi": "/resources/vertical-idp-logistics-roi",
            "trade-compliance": "/resources/trade-compliance-handbook",
        }
        if article in article_aliases:
            return request.redirect(article_aliases[article])
        article_data = ARTICLES.get(article)
        if not article_data:
            return request.not_found()
        return request.render(
            "insilos_website.insilos_article_page",
            self._base_values(article=article_data, article_key=article),
        )

    @http.route("/pricing", type="http", auth="public", website=True, sitemap=True)
    def pricing(self, **kwargs):
        return request.render("insilos_website.insilos_pricing_page", self._base_values())

    @http.route(["/about", "/company", "/vi/about", "/vi/company"], type="http", auth="public", website=True, sitemap=True)
    def about(self, **kwargs):
        return request.render("insilos_website.insilos_about_page", self._base_values())

    @http.route(["/contactus", "/contactus-1", "/vi/contactus", "/vi/contactus-1"], type="http", auth="public", website=True, sitemap=True)
    def contactus(self, **kwargs):
        host = (request.httprequest.host or "").lower()
        website_name = (request.website.name or "").lower() if getattr(request, "website", None) else ""
        if "innoria" in host or "innoria" in website_name:
            if request.env["ir.ui.view"].sudo().search([("key", "=", "insilos_website.innoria_contactus")], limit=1):
                return request.render("insilos_website.innoria_contactus", self._base_values())
        return request.render("website.contactus", self._base_values())

    @http.route("/media-credits", type="http", auth="public", website=True, sitemap=True)
    def media_credits(self, **kwargs):
        return request.render("insilos_website.insilos_media_credits", self._base_values())

    @http.route(["/trust", "/vi/trust"], type="http", auth="public", website=True, sitemap=True)
    def trust(self, **kwargs):
        return request.render("insilos_website.insilos_trust_page", self._base_values(**kwargs))

    @http.route(["/compliance", "/vi/compliance"], type="http", auth="public", website=True, sitemap=True)
    def compliance(self, **kwargs):
        return request.render("insilos_website.insilos_compliance_page", self._base_values(**kwargs))

    @http.route(["/sandbox", "/vi/sandbox"], type="http", auth="public", website=True, sitemap=True)
    def sandbox(self, **kwargs):
        return request.render("insilos_website.insilos_sandbox_page", self._base_values(**kwargs))

    @http.route(["/privacy", "/privacy-policy", "/vi/privacy", "/vi/privacy-policy"], type="http", auth="public", website=True, sitemap=True)
    def privacy(self, **kwargs):
        return request.render("insilos_website.insilos_privacy_page", self._base_values(**kwargs))

    @http.route(
        "/request-demo",
        type="http",
        auth="public",
        website=True,
        methods=["GET", "POST"],
        csrf=True,
        sitemap=True,
    )
    def request_demo(self, **post):
        form_data = {
            "name": (post.get("name") or "").strip()[:120],
            "email": (post.get("email") or "").strip().lower()[:254],
            "phone": (post.get("phone") or "").strip()[:64],
            "company": (post.get("company") or "").strip()[:160],
            "job_title": (post.get("job_title") or "").strip()[:120],
            "industry": (post.get("industry") or "").strip(),
            "use_case": (post.get("use_case") or "").strip(),
            "company_size": (post.get("company_size") or "").strip(),
            "core_erp": (post.get("core_erp") or "").strip(),
            "project_timeline": (post.get("project_timeline") or "").strip(),
            "message": (post.get("message") or "").strip()[:5000],
            "consent": post.get("consent") == "on" or post.get("consent_decree13") == "on",
            "consent_decree13": post.get("consent_decree13") == "on" or post.get("consent") == "on",
            "website_url": (post.get("website_url") or "").strip(),
        }
        errors = {}

        if request.httprequest.method == "POST":
            if form_data["website_url"]:
                return request.redirect("/thank-you")

            last_submit = float(request.session.get("insilos_demo_last_submit", 0) or 0)
            if time.time() - last_submit < 20:
                errors["general"] = "Yêu cầu vừa được gửi. Vui lòng đợi một chút trước khi gửi lại."

            if len(form_data["name"]) < 2:
                errors["name"] = "Vui lòng nhập họ và tên."
            if not EMAIL_RE.match(form_data["email"]):
                errors["email"] = "Vui lòng nhập email hợp lệ."
            if len(form_data["company"]) < 2:
                errors["company"] = "Vui lòng nhập tên doanh nghiệp."
            if not form_data["industry"] or form_data["industry"] not in dict(INDUSTRY_SELECTIONS):
                errors["industry"] = "Vui lòng chọn ngành."
            if not form_data["use_case"] or form_data["use_case"] not in dict(USE_CASE_SELECTIONS):
                errors["use_case"] = "Vui lòng chọn use case."
            if form_data["company_size"] and form_data["company_size"] not in dict(COMPANY_SIZE_SELECTIONS):
                errors["company_size"] = "Quy mô không hợp lệ."
            if form_data["core_erp"] and form_data["core_erp"] not in dict(CORE_ERP_SELECTIONS):
                errors["core_erp"] = "Hệ thống Core ERP không hợp lệ."
            if form_data["project_timeline"] and form_data["project_timeline"] not in dict(PROJECT_TIMELINE_SELECTIONS):
                errors["project_timeline"] = "Tiến độ dự kiến không hợp lệ."
            if not form_data["consent_decree13"]:
                errors["consent"] = "Cần xác nhận đồng ý xử lý dữ liệu theo Nghị định 13/2023/NĐ-CP để Insilos có thể liên hệ."

            if not errors:
                current_website = request.env["website"].get_current_website(fallback=True)
                website_id = current_website.id if current_website else False
                record = request.env["insilos.demo.request"].sudo().create(
                    {
                        "name": form_data["name"],
                        "email": form_data["email"],
                        "phone": form_data["phone"],
                        "company": form_data["company"],
                        "job_title": form_data["job_title"],
                        "industry": form_data["industry"],
                        "use_case": form_data["use_case"],
                        "company_size": form_data["company_size"] or False,
                        "core_erp": form_data["core_erp"] or False,
                        "project_timeline": form_data["project_timeline"] or False,
                        "message": form_data["message"],
                        "consent": True,
                        "consent_decree13": True,
                        "website_id": website_id,
                        "source_url": (request.httprequest.referrer or "/request-demo")[:1024],
                        "language_code": request.env.lang or "",
                    }
                )
                self._queue_notification(record)
                request.session["insilos_demo_last_submit"] = time.time()
                request.session["insilos_demo_request_id"] = record.id
                return request.redirect("/thank-you")

        return request.render(
            "insilos_website.insilos_request_demo_page",
            self._base_values(
                form_data=form_data,
                errors=errors,
                industry_selections=INDUSTRY_SELECTIONS,
                use_case_selections=USE_CASE_SELECTIONS,
                company_size_selections=COMPANY_SIZE_SELECTIONS,
                core_erp_selections=CORE_ERP_SELECTIONS,
                project_timeline_selections=PROJECT_TIMELINE_SELECTIONS,
            ),
        )

    def _queue_notification(self, record):
        current_website = request.env["website"].get_current_website(fallback=True)
        company = current_website.company_id if current_website and current_website.company_id else request.env.company
        email_to = company.email
        if not email_to:
            return
        body = "".join(
            [
                "<h2>Yêu cầu demo mới từ website Insilos</h2>",
                f"<p><strong>Họ tên:</strong> {escape(record.name)}</p>",
                f"<p><strong>Email:</strong> {escape(record.email)}</p>",
                f"<p><strong>Doanh nghiệp:</strong> {escape(record.company)}</p>",
                f"<p><strong>Ngành:</strong> {escape(dict(record._fields['industry'].selection).get(record.industry, record.industry))}</p>",
                f"<p><strong>Use case:</strong> {escape(dict(record._fields['use_case'].selection).get(record.use_case, record.use_case))}</p>",
                f"<p><strong>Nhu cầu:</strong><br/>{escape(record.message or '').replace(chr(10), '<br/>')}</p>",
            ]
        )
        request.env["mail.mail"].sudo().create(
            {
                "subject": f"[Insilos] Yêu cầu demo — {record.company}",
                "body_html": body,
                "email_from": company.partner_id.email_formatted or email_to,
                "email_to": email_to,
                "reply_to": record.email,
                "auto_delete": True,
            }
        )

    @http.route("/thank-you", type="http", auth="public", website=True, sitemap=False)
    def thank_you(self, **kwargs):
        return request.render("insilos_website.insilos_thank_you_page", self._base_values())

    @http.route(["/showcase-3d", "/vi/showcase-3d", "/solutions/industrial-showcase"], type="http", auth="public", website=True, sitemap=True)
    def showcase_3d(self, **kwargs):
        submitted = bool(kwargs.get("submitted"))
        now = time.time()
        is_public = request.env.user._is_public() if hasattr(request.env, "user") else True
        if is_public and submitted in _SHOWCASE_HTML_CACHE:
            cached_html, cache_time = _SHOWCASE_HTML_CACHE[submitted]
            if now - cache_time < _SHOWCASE_CACHE_TTL:
                csrf_token = request.csrf_token() if hasattr(request, "csrf_token") else ""
                html = re.sub(
                    r'(name="csrf_token"\s+value=")[^"]*(")',
                    r'\g<1>' + csrf_token + r'\g<2>',
                    cached_html,
                )
                return request.make_response(html, [("Content-Type", "text/html; charset=utf-8")])

        values = self._base_values(submitted=submitted)
        response = request.render("insilos_website.insilos_showcase_3d_page", values)
        if is_public:
            try:
                rendered_content = response.render()
                if isinstance(rendered_content, bytes):
                    rendered_html = rendered_content.decode("utf-8")
                else:
                    rendered_html = str(rendered_content)
                _SHOWCASE_HTML_CACHE[submitted] = (rendered_html, now)
            except Exception:
                pass
        return response

    @http.route(["/interactive-3d", "/vi/interactive-3d"], type="http", auth="public", website=True, sitemap=True)
    def interactive_3d(self, **kwargs):
        values = self._base_values()
        return request.render("insilos_website.insilos_interactive_3d_page", values)

    @http.route("/insilos/lead-submit", type="http", auth="public", methods=["POST"], website=True, csrf=True)
    def lead_submit(self, **post):
        contact_name = (post.get("contact_name") or "").strip()
        email_from = (post.get("email_from") or "").strip()
        phone = (post.get("phone") or "").strip()
        partner_name = (post.get("partner_name") or "").strip()
        focus_area = post.get("focus_area", "full")
        campaign_tag = post.get("campaign_tag", "3D Showcase")

        tag = request.env["crm.tag"].sudo().search([("name", "=", campaign_tag)], limit=1)
        if not tag:
            tag = request.env["crm.tag"].sudo().create({"name": campaign_tag, "color": 4})

        lead = request.env["crm.lead"].sudo().create({
            "name": f"Yêu cầu Tư vấn 3D Showcase — {partner_name or contact_name}",
            "contact_name": contact_name,
            "email_from": email_from,
            "phone": phone,
            "partner_name": partner_name,
            "description": f"Phân hệ quan tâm: {focus_area}\nNguồn: Website 3D Showcase Landing Page",
            "type": "opportunity",
            "tag_ids": [(4, tag.id)],
        })

        # Sync participants for marketing automation campaign if running
        campaign = request.env["marketing.campaign"].sudo().search([
            ("name", "ilike", "3D Showcase"),
            ("state", "=", "running")
        ], limit=1)
        if campaign:
            try:
                campaign.sync_participants()
            except Exception:
                pass

        return request.redirect("/showcase-3d?submitted=1")
