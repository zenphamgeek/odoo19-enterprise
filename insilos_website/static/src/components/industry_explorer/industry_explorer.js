import { Component, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';

export class IndustryExplorer extends Component {
    static template = "insilos_website.IndustryExplorer";
    static props = {};

    setup() {
        this.state = useState({ active: "fsm" });
        this.industries = [
            {
                key: "fsm",
                short: "Field Service",
                name: "Field Service & Asset Operations",
                headline: "Xử lý đúng công việc, với đúng kỹ thuật viên, ngay lần đầu.",
                description:
                    "Kết nối tình trạng tài sản, yêu cầu dịch vụ, kỹ năng, vị trí và phụ tùng để chủ động điều phối công việc hiện trường.",
                image: "/insilos_website/static/src/img/fsm-960.webp",
                alt: "Nhóm kỹ sư sử dụng máy tính bảng trong nhà máy",
                url: "/industries/fsm",
                label: "FIRST-TIME FIX",
                metric: "Asset → Case → Dispatch",
                applications: ["Predictive service", "Scheduling & dispatch", "Technician assistant"],
            },
            {
                key: "logistics",
                short: "Logistics",
                name: "Logistics & Supply Chain",
                headline: "Một bức tranh vận hành cho tồn kho, shipment và ngoại lệ.",
                description:
                    "Hợp nhất ERP, WMS, TMS, telematics và tín hiệu bên ngoài để dự báo ETA, ưu tiên exception và tối ưu mạng lưới.",
                image: "/insilos_website/static/src/img/logistics-960.webp",
                alt: "Trung tâm logistics với container và xe vận chuyển",
                url: "/industries/logistics",
                label: "NETWORK VISIBILITY",
                metric: "Demand → Inventory → Delivery",
                applications: ["Control tower", "ETA prediction", "Inventory optimization"],
            },
            {
                key: "energy",
                short: "Năng lượng",
                name: "Energy & Utilities",
                headline: "Tăng độ tin cậy tài sản và tối ưu sản lượng trong giới hạn an toàn.",
                description:
                    "Kết nối SCADA, historian, EAM, GIS, thời tiết và thị trường để dự báo rủi ro, tải, sản lượng và tổn thất.",
                image: "/insilos_website/static/src/img/energy-960.webp",
                alt: "Trang trại điện mặt trời và điện gió tại Việt Nam",
                url: "/industries/energy",
                label: "RELIABLE ENERGY",
                metric: "Sense → Predict → Optimize",
                applications: ["Asset reliability", "Load forecasting", "Process optimization"],
            },
            {
                key: "pharma",
                short: "Sản xuất dược",
                name: "Pharmaceutical Manufacturing",
                headline: "Cải thiện hiệu suất lô với AI có nguồn dẫn và kiểm soát.",
                description:
                    "Kết nối MES, historian, LIMS, QMS, EAM và SOP để phát hiện biến thiên, hỗ trợ điều tra và bảo vệ data integrity.",
                image: "/insilos_website/static/src/img/pharma-960.webp",
                alt: "Nhân viên trong phòng sạch công nghệ cao",
                url: "/industries/pharma",
                label: "GOVERNED AI",
                metric: "Batch → Evidence → Decision",
                applications: ["Batch intelligence", "Deviation investigation", "SOP assistant"],
            },
        ];
    }

    get activeIndustry() {
        return this.industries.find((industry) => industry.key === this.state.active) || this.industries[0];
    }

    selectIndustry(key) {
        this.state.active = key;
    }
}

registry.category("public_components").add("insilos_website.IndustryExplorer", IndustryExplorer);
