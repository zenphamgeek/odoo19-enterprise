from odoo import fields, models


class InsilosDemoRequest(models.Model):
    _name = "insilos.demo.request"
    _description = "Insilos Demo Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Họ và tên", required=True, tracking=True)
    email = fields.Char(string="Email công việc", required=True, tracking=True)
    phone = fields.Char(string="Số điện thoại")
    company = fields.Char(string="Doanh nghiệp", required=True, tracking=True)
    job_title = fields.Char(string="Chức danh")
    industry = fields.Selection(
        [
            ("fsm", "Field Service & Asset Operations"),
            ("logistics", "Logistics & Supply Chain"),
            ("energy", "Energy & Utilities"),
            ("pharma", "Pharmaceutical Manufacturing"),
            ("other", "Ngành khác"),
        ],
        string="Ngành",
        required=True,
        tracking=True,
    )
    use_case = fields.Selection(
        [
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
        ],
        string="Use case ưu tiên",
        required=True,
        tracking=True,
    )
    company_size = fields.Selection(
        [
            ("1_49", "1–49"),
            ("50_249", "50–249"),
            ("250_999", "250–999"),
            ("1000_plus", "1.000+"),
        ],
        string="Quy mô nhân sự",
    )
    message = fields.Text(string="Bối cảnh / nhu cầu")
    consent = fields.Boolean(string="Đồng ý được liên hệ", required=True)
    state = fields.Selection(
        [
            ("new", "Mới"),
            ("contacted", "Đã liên hệ"),
            ("qualified", "Đủ điều kiện"),
            ("closed", "Đã đóng"),
        ],
        default="new",
        required=True,
        tracking=True,
    )
    assigned_user_id = fields.Many2one("res.users", string="Người phụ trách", tracking=True)
    website_id = fields.Many2one("website", string="Website", readonly=True)
    source_url = fields.Char(string="Trang gửi yêu cầu", readonly=True)
    language_code = fields.Char(string="Ngôn ngữ", readonly=True)
    internal_notes = fields.Html(string="Ghi chú nội bộ")
    active = fields.Boolean(default=True)

    def action_mark_contacted(self):
        self.write({"state": "contacted"})

    def action_mark_qualified(self):
        self.write({"state": "qualified"})

    def action_close(self):
        self.write({"state": "closed"})
