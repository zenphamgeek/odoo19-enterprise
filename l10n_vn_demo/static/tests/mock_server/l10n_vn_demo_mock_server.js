/** @insilos-module **/

import { serverState } from '@web/../tests/web_test_helpers';
import { ServerModel } from '@web/../tests/_framework/mock_server/mock_model';
import { defineModels } from '@web/../tests/_framework/mock_server/mock_server';
import * as fields from '@web/../tests/_framework/mock_server/mock_fields';

// ---------------------------------------------------------------------------
// Vietnamese Partner (rs.partner) — khách hàng và nhà cung cấp tiếng Việt
// ---------------------------------------------------------------------------
const viPartners = [
    { id: 1001, name: "Công ty TNHH An Phát", display_name: "Công ty TNHH An Phát",
      phone: "028 1234 5678", email: "anphat@example.com", is_company: true,
      street: "123 Nguyễn Thị Minh Khai", city: "TP. Hồ Chí Minh", country_id: 243 },
    { id: 1002, name: "Công ty CP Đầu tư Mai Linh", display_name: "Công ty CP Đầu tư Mai Linh",
      phone: "028 2222 3333", email: "info@mailinh.vn", is_company: true,
      street: "456 Lê Lợi", city: "TP. Hồ Chí Minh", country_id: 243 },
    { id: 1003, name: "Doanh nghiệp tư nhân Hoàng Gia", display_name: "Doanh nghiệp tư nhân Hoàng Gia",
      phone: "024 5555 6666", email: "hoanggia@example.com", is_company: true,
      street: "789 Trần Hưng Đạo", city: "Hà Nội", country_id: 243 },
    { id: 1004, name: "Hợp tác xã Nông sản Đà Lạt", display_name: "Hợp tác xã Nông sản Đà Lạt",
      phone: "0263 888 999", email: "dalat@htxnongsan.vn", is_company: true,
      street: "12 Quang Trung", city: "Đà Lạt", country_id: 243 },
    { id: 1005, name: "Cửa hàng Tạp hóa Minh Tâm", display_name: "Cửa hàng Tạp hóa Minh Tâm",
      phone: "028 777 8888", email: "minhtam@shop.vn", is_company: true,
      street: "34 Hai Bà Trưng", city: "TP. Hồ Chí Minh", country_id: 243 },
    // Suppliers
    { id: 1101, name: "Nhà máy Giấy Bình Dương", display_name: "Nhà máy Giấy Bình Dương",
      phone: "0274 999 111", email: "sales@binhduongpaper.vn", is_company: true,
      street: "KCN Sóng Thần", city: "Bình Dương", country_id: 243 },
    { id: 1102, name: "Công ty TNHH SX Nguyên Liệu Việt", display_name: "Công ty TNHH SX Nguyên Liệu Việt",
      phone: "0251 222 333", email: "info@nguyenlieu.vn", is_company: true,
      street: "KCN Biên Hòa 2", city: "Đồng Nai", country_id: 243 },
    { id: 1103, name: "Trang trại Rau Sạch Củ Chi", display_name: "Trang trại Rau Sạch Củ Chi",
      phone: "028 345 6789", email: "rausach@cuchi.vn", is_company: true,
      street: "Ấp Bến Đình", city: "TP. Hồ Chí Minh", country_id: 243 },
];

// ---------------------------------------------------------------------------
// Vietnamese Employee (hr.employee) — nhân viên mẫu tiếng Việt
// ---------------------------------------------------------------------------
const viEmployees = [
    { id: 2001, name: "Nguyễn Văn Hùng", display_name: "Nguyễn Văn Hùng",
      job_title: "Tổng Giám đốc", work_email: "hungnv@mycompany.vn",
      mobile_phone: "0912 345 678", department_id: 3001 },
    { id: 2002, name: "Trần Thị Mai", display_name: "Trần Thị Mai",
      job_title: "Giám đốc Nhân sự", work_email: "maitt@mycompany.vn",
      mobile_phone: "0913 456 789", department_id: 3002, parent_id: 2001 },
    { id: 2003, name: "Lê Văn Tuấn", display_name: "Lê Văn Tuấn",
      job_title: "Giám đốc Kinh doanh", work_email: "tuanlv@mycompany.vn",
      mobile_phone: "0914 567 890", department_id: 3003, parent_id: 2001 },
    { id: 2004, name: "Phạm Thị Hồng", display_name: "Phạm Thị Hồng",
      job_title: "Kế toán trưởng", work_email: "hongpt@mycompany.vn",
      mobile_phone: "0915 678 901", department_id: 3004, parent_id: 2001 },
    { id: 2005, name: "Hoàng Minh Đức", display_name: "Hoàng Minh Đức",
      job_title: "Trưởng phòng Mua hàng", work_email: "duchm@mycompany.vn",
      mobile_phone: "0916 789 012", department_id: 3005, parent_id: 2001 },
    { id: 2006, name: "Vũ Đình Nam", display_name: "Vũ Đình Nam",
      job_title: "Quản lý Kho", work_email: "namvd@mycompany.vn",
      mobile_phone: "0917 890 123", department_id: 3006, parent_id: 2001 },
    { id: 2007, name: "Đỗ Thị Hoa", display_name: "Đỗ Thị Hoa",
      job_title: "Nhân viên Kinh doanh", work_email: "hoadt@mycompany.vn",
      mobile_phone: "0918 901 234", department_id: 3003, parent_id: 2003 },
    { id: 2008, name: "Ngô Thanh Tùng", display_name: "Ngô Thanh Tùng",
      job_title: "Nhân viên Kinh doanh", work_email: "tungnt@mycompany.vn",
      mobile_phone: "0919 012 345", department_id: 3003, parent_id: 2003 },
    { id: 2009, name: "Lý Hoàng Anh", display_name: "Lý Hoàng Anh",
      job_title: "Lập trình viên", work_email: "anhlh@mycompany.vn",
      mobile_phone: "0920 123 456", department_id: 3007, parent_id: 2001 },
    { id: 2010, name: "Đặng Thu Thảo", display_name: "Đặng Thu Thảo",
      job_title: "Lập trình viên", work_email: "thaodt@mycompany.vn",
      mobile_phone: "0921 234 567", department_id: 3007, parent_id: 2001 },
];

// ---------------------------------------------------------------------------
// Vietnamese Departments (hr.department) — phòng ban tiếng Việt
// ---------------------------------------------------------------------------
class HrDepartmentVN extends ServerModel {
    _name = "hr.department";
    parent_id = fields.Many2one({ relation: "hr.department" });
    manager_id = fields.Many2one({ relation: "hr.employee" });
    _records = [
        { id: 3001, name: "Ban Giám đốc", complete_name: "Ban Giám đốc" },
        { id: 3002, name: "Nhân sự", complete_name: "Nhân sự", parent_id: 3001 },
        { id: 3003, name: "Kinh doanh", complete_name: "Kinh doanh", parent_id: 3001 },
        { id: 3004, name: "Tài chính - Kế toán", complete_name: "Tài chính - Kế toán", parent_id: 3001 },
        { id: 3005, name: "Mua hàng", complete_name: "Mua hàng", parent_id: 3001 },
        { id: 3006, name: "Kho vận", complete_name: "Kho vận", parent_id: 3001 },
        { id: 3007, name: "R&D", complete_name: "R&D", parent_id: 3001 },
    ];
}

// ---------------------------------------------------------------------------
// Vietnamese Partner Model
// ---------------------------------------------------------------------------
class ResPartnerVN extends ServerModel {
    _name = "rs.partner";
    phone = fields.Char();
    email = fields.Char();
    vat = fields.Char();
    street = fields.Char();
    city = fields.Char();
    country_id = fields.Many2one({ relation: "rs.country" });
    is_company = fields.Boolean({ default: false });

    _records = viPartners;
}

// ---------------------------------------------------------------------------
// Vietnamese Employee Model
// ---------------------------------------------------------------------------
class HrEmployeeVN extends ServerModel {
    _name = "hr.employee";
    job_title = fields.Char();
    work_email = fields.Char();
    mobile_phone = fields.Char();
    department_id = fields.Many2one({ relation: "hr.department" });
    parent_id = fields.Many2one({ relation: "hr.employee" });
    company_id = fields.Many2one({ relation: "rs.company" });

    _records = viEmployees;
}

// ---------------------------------------------------------------------------
// Vietnamese CRM Lead Model
// ---------------------------------------------------------------------------
class CrmLeadVN extends ServerModel {
    _name = "crm.lead";
    partner_id = fields.Many2one({ relation: "rs.partner" });
    user_id = fields.Many2one({ relation: "rs.users" });
    team_id = fields.Many2one({ relation: "crm.team" });
    stage_id = fields.Many2one({ relation: "crm.stage" });
    type = fields.Selection({ selection: [["lead", "Lead"], ["opportunity", "Opportunity"]] });
    priority = fields.Selection({ selection: [["0", "Low"], ["1", "Normal"], ["2", "High"], ["3", "Very High"]] });
    expected_revenue = fields.Monetary({ currency_field: "company_currency" });

    _records = [
        { id: 4001, name: "Tư vấn giải pháp ERP", display_name: "Tư vấn giải pháp ERP",
          partner_id: 1001, type: "opportunity", priority: "2",
          expected_revenue: 150000000, user_id: 7 },
        { id: 4002, name: "Báo giá máy lọc nước công nghiệp", display_name: "Báo giá máy lọc nước công nghiệp",
          partner_id: 1002, type: "opportunity", priority: "1",
          expected_revenue: 50000000, user_id: 7 },
        { id: 4003, name: "Liên hệ mua sỉ cà phê", display_name: "Liên hệ mua sỉ cà phê",
          partner_id: 1003, type: "lead", priority: "0",
          expected_revenue: 20000000, user_id: 7 },
        { id: 4004, name: "Hợp tác phân phối nông sản", display_name: "Hợp tác phân phối nông sản",
          partner_id: 1004, type: "opportunity", priority: "3",
          expected_revenue: 300000000, user_id: 7 },
    ];
}

// ---------------------------------------------------------------------------
// Vietnamese Product Model
// ---------------------------------------------------------------------------
class ProductTemplateVN extends ServerModel {
    _name = "product.template";
    type = fields.Selection({ selection: [["consu", "Consumable"], ["service", "Service"], ["product", "Storable"]] });
    list_price = fields.Float();
    default_code = fields.Char();
    uom_id = fields.Many2one({ relation: "uom.uom" });
    uom_po_id = fields.Many2one({ relation: "uom.uom" });
    categ_id = fields.Many2one({ relation: "product.category" });

    _records = [
        { id: 5001, name: "Cà phê Arabica Đà Lạt", default_code: "CF001",
          type: "product", list_price: 180000 },
        { id: 5002, name: "Trà Ô Long Tân Cương", default_code: "TR001",
          type: "product", list_price: 250000 },
        { id: 5003, name: "Nước mắm Phú Quốc 500ml", default_code: "NM001",
          type: "product", list_price: 85000 },
        { id: 5004, name: "Bàn gỗ sồi tự nhiên", default_code: "BG001",
          type: "product", list_price: 3200000 },
        { id: 5005, name: "Gạo ST25 Sóc Trăng 10kg", default_code: "GA001",
          type: "product", list_price: 220000 },
        { id: 5006, name: "Máy lọc nước RO Karofi", default_code: "ML001",
          type: "product", list_price: 4500000 },
        { id: 5007, name: "Áo sơ mi nam cao cấp", default_code: "AS001",
          type: "product", list_price: 550000 },
        { id: 5008, name: "Dịch vụ vận chuyển nội thành", default_code: "DV001",
          type: "service", list_price: 50000 },
    ];
}

// ---------------------------------------------------------------------------
// Vietnamese Country + State
// ---------------------------------------------------------------------------
class ResCountryVN extends ServerModel {
    _name = "rs.country";
    _records = [
        { id: 243, name: "Vietnam", code: "VN" },
    ];
}

// ---------------------------------------------------------------------------
// Register all models
// ---------------------------------------------------------------------------
defineModels([
    ResCountryVN,
    HrDepartmentVN,
    ResPartnerVN,
    HrEmployeeVN,
    CrmLeadVN,
    ProductTemplateVN,
]);

// ---------------------------------------------------------------------------
// Configure serverState for Vietnamese locale
// ---------------------------------------------------------------------------
serverState.lang = "vi_VN";
serverState.multiLang = true;
serverState.partnerName = "Nguyễn Văn Admin";
