# Part of Insilos. See LICENSE file for full copyright and licensing details.

import datetime
import io
import json
import zipfile
from xml.sax.saxutils import escape

from insilos import http
from insilos.http import request


CANONICAL_DGM_EMPLOYEES = [
    {
        "reg": "DGM-001",
        "name": "Lê Xuân Hoàng",
        "id_card_name": "089094016917",
        "job_title": "Chủ tịch HĐQT & Tổng Giám đốc",
        "department_name": "Ban Giám Đốc & Quản Trị (Executive Board)",
        "manager_name": "Hội đồng Quản trị DGM",
        "work_email": "hoang.le@inno.ai.vn",
        "work_phone": "0903881001",
        "bank_name": "VIETCOMBANK",
        "bank_bic": "BFTVVNVX",
        "bank_branch": "CN TP.HCM",
        "bank_acc_number": "1373068161",
        "gross_wage": 45000000,
        "join_date": "01/01/2024",
    },
    {
        "reg": "DGM-002",
        "name": "Nguyễn Hoài Ân",
        "id_card_name": "096095006609",
        "job_title": "Cổ đông sáng lập & CTO",
        "department_name": "Khối Công Nghệ & AI (AI & Engineering — Mojo AI / ERP)",
        "manager_name": "Lê Xuân Hoàng",
        "work_email": "an.nguyen@inno.ai.vn",
        "work_phone": "0903881002",
        "bank_name": "VIETCOMBANK",
        "bank_bic": "BFTVVNVX",
        "bank_branch": "CN TP.HCM",
        "bank_acc_number": "1901014028",
        "gross_wage": 42000000,
        "join_date": "01/01/2024",
    },
    {
        "reg": "DGM-003",
        "name": "Mai Thị Hồng Thắm",
        "id_card_name": "093197003049",
        "job_title": "Cổ đông sáng lập & CFO/HR Lead",
        "department_name": "Khối Tài Chính - Kế Toán - Nhân Sự (Finance, Accounting & HR)",
        "manager_name": "Lê Xuân Hoàng",
        "work_email": "tham.mai@inno.ai.vn",
        "work_phone": "0903881003",
        "bank_name": "VIETCOMBANK",
        "bank_bic": "BFTVVNVX",
        "bank_branch": "CN Nam Sài Gòn",
        "bank_acc_number": "0111000287863",
        "gross_wage": 35000000,
        "join_date": "01/01/2024",
    },
    {
        "reg": "DGM-004",
        "name": "Bùi Hữu Tài",
        "id_card_name": "365931521",
        "job_title": "Kỹ sư Phần mềm Senior (MTI Onsite)",
        "department_name": "Khối Dịch Vụ Kỹ Sư Onsite B2B (Enterprise B2B & MTI Delivery)",
        "manager_name": "Lê Xuân Hoàng",
        "work_email": "tai.bui@inno.ai.vn",
        "work_phone": "0903881004",
        "bank_name": "VIETCOMBANK",
        "bank_bic": "BFTVVNVX",
        "bank_branch": "CN Tân Bình",
        "bank_acc_number": "1045246615",
        "gross_wage": 32000000,
        "join_date": "01/01/2024",
    },
    {
        "reg": "DGM-005",
        "name": "Huỳnh Trần Quang Khánh",
        "id_card_name": "089085004243",
        "job_title": "Kỹ sư Phần mềm Senior / Tech Lead",
        "department_name": "Khối Công Nghệ & AI (AI & Engineering — Mojo AI / ERP)",
        "manager_name": "Nguyễn Hoài Ân",
        "work_email": "khanh.huynh@inno.ai.vn",
        "work_phone": "0903881005",
        "bank_name": "ACB",
        "bank_bic": "ASCBVNVX",
        "bank_branch": "CN Sài Gòn",
        "bank_acc_number": "12154887",
        "gross_wage": 34000000,
        "join_date": "01/02/2024",
    },
    {
        "reg": "DGM-006",
        "name": "Ngô Thanh Lộc",
        "id_card_name": "079096011234",
        "job_title": "Kỹ sư Phần mềm Senior (MTI Onsite)",
        "department_name": "Khối Dịch Vụ Kỹ Sư Onsite B2B (Enterprise B2B & MTI Delivery)",
        "manager_name": "Bùi Hữu Tài",
        "work_email": "loc.ngo@inno.ai.vn",
        "work_phone": "0903881006",
        "bank_name": "ACB",
        "bank_bic": "ASCBVNVX",
        "bank_branch": "CN Cộng Hòa",
        "bank_acc_number": "12154937",
        "gross_wage": 28000000,
        "join_date": "01/02/2024",
    },
    {
        "reg": "DGM-007",
        "name": "Lê Cao Bảo Phúc",
        "id_card_name": "079097022345",
        "job_title": "Kỹ sư Phần mềm (MTI Onsite)",
        "department_name": "Khối Dịch Vụ Kỹ Sư Onsite B2B (Enterprise B2B & MTI Delivery)",
        "manager_name": "Bùi Hữu Tài",
        "work_email": "phuc.le@inno.ai.vn",
        "work_phone": "0903881007",
        "bank_name": "ACB",
        "bank_bic": "ASCBVNVX",
        "bank_branch": "CN Cộng Hòa",
        "bank_acc_number": "12154917",
        "gross_wage": 25000000,
        "join_date": "01/03/2024",
    },
    {
        "reg": "DGM-008",
        "name": "Thái Nguyễn Đăng Khoa",
        "id_card_name": "079099033456",
        "job_title": "Kỹ sư Phần mềm / Junior Developer",
        "department_name": "Khối Công Nghệ & AI (AI & Engineering — Mojo AI / ERP)",
        "manager_name": "Nguyễn Hoài Ân",
        "work_email": "khoa.thai@inno.ai.vn",
        "work_phone": "0903881008",
        "bank_name": "ACB",
        "bank_bic": "ASCBVNVX",
        "bank_branch": "CN Tân Thuận",
        "bank_acc_number": "47070467",
        "gross_wage": 18000000,
        "join_date": "01/06/2024",
    },
]


def _compute_vn_payroll(gross):
    bhxh = round(gross * 0.08)
    bhyt = round(gross * 0.015)
    bhtn = round(gross * 0.01)
    total_ins = bhxh + bhyt + bhtn
    taxable = max(0, gross - total_ins - 11000000)
    if taxable <= 0:
        pit = 0
    elif taxable <= 5000000:
        pit = round(taxable * 0.05)
    elif taxable <= 10000000:
        pit = round(taxable * 0.10 - 250000)
    elif taxable <= 18000000:
        pit = round(taxable * 0.15 - 750000)
    elif taxable <= 32000000:
        pit = round(taxable * 0.20 - 1650000)
    elif taxable <= 52000000:
        pit = round(taxable * 0.25 - 3250000)
    else:
        pit = round(taxable * 0.30 - 5850000)
    net = gross - total_ins - pit
    return {
        "gross_wage": gross,
        "bhxh_amount": bhxh,
        "bhyt_amount": bhyt,
        "bhtn_amount": bhtn,
        "total_insurance": total_ins,
        "taxable_income": taxable,
        "pit_amount": pit,
        "net_wage": net,
    }


def _default_lifecycle(emp_dict):
    return {
        "onboarding": {
            "status": "in_progress",
            "steps": [
                {
                    "id": "onb_1",
                    "code": "SOP-DGM-04.1",
                    "title": "Hồ sơ Pháp lý, CCCD & Định danh Thuế TNCN",
                    "description": "Thu thập CCCD gắn chip, MST cá nhân, đăng ký giảm trừ gia cảnh và hồ sơ nhân sự gốc.",
                    "owner": "HR & Legal (Mai Thị Hồng Thắm)",
                    "sla": "Ngày 1",
                    "done": True,
                    "completed_at": "2024-01-02",
                },
                {
                    "id": "onb_2",
                    "code": "SOP-DGM-04.2",
                    "title": "Ký Hợp đồng Lao động 12 Điều Chuẩn DGM & Cam kết NDA/SHTT",
                    "description": "Ký HĐLĐ mẫu chuẩn 12 điều, thỏa thuận bảo mật NDA và quyền sở hữu trí tuệ mã nguồn.",
                    "owner": "Ban Giám Đốc & Pháp chế",
                    "sla": "Ngày 1",
                    "done": True,
                    "completed_at": "2024-01-02",
                },
                {
                    "id": "onb_3",
                    "code": "SOP-DGM-04.3",
                    "title": "Báo tăng BHXH Quận 7 (Mã ĐV: TZ0857G) & Xác thực Tài khoản Lương",
                    "description": f"Đăng ký BHXH/BHYT/BHTN tại BHXH Quận 7 và liên kết TK {emp_dict.get('bank_name', 'VCB')} ({emp_dict.get('bank_acc_number', '')}) trên VCB DigiBiz.",
                    "owner": "Kế toán Tiền lương (FIN-HR)",
                    "sla": "Trong 15 ngày đầu",
                    "done": True,
                    "completed_at": "2024-01-10",
                },
                {
                    "id": "onb_4",
                    "code": "SOP-DGM-04.4",
                    "title": "Cấp phát Tài khoản Innoria ERP, Email @inno.ai.vn, GitHub & VPN",
                    "description": f"Khởi tạo định danh SSO ({emp_dict.get('work_email', '')}), phân quyền kho tài liệu Documents (5 phân vùng) & môi trường Dev.",
                    "owner": "IT & SecOps (Nguyễn Hoài Ân)",
                    "sla": "Ngày 1",
                    "done": True,
                    "completed_at": "2024-01-02",
                },
                {
                    "id": "onb_5",
                    "code": "SOP-DGM-04.5",
                    "title": "Đánh giá Hội nhập 60 Ngày & Bàn giao KPI Quý",
                    "description": "Hoàn tất đánh giá thử việc/hội nhập kỹ thuật cùng Quản lý trực tiếp và xác nhận mục tiêu OKR/KPI.",
                    "owner": "Trưởng bộ phận & HR",
                    "sla": "Ngày 60",
                    "done": False,
                    "completed_at": None,
                },
            ],
        },
        "leaving": {
            "status": "active_employment",
            "notice_date": "",
            "expected_last_day": "",
            "handover_assignee": "Nguyễn Hoài Ân (CTO)",
            "reason": "",
            "steps": [
                {
                    "id": "off_1",
                    "code": "SOP-DGM-03.1",
                    "title": "Tiếp nhận Đơn xin nghỉ việc & Phê duyệt Thời hạn Báo trước",
                    "description": "Kiểm tra thời hạn báo trước theo Bộ luật Lao động (30/45 ngày) và xác nhận ngày làm việc cuối cùng.",
                    "owner": "Trưởng bộ phận & HR",
                    "sla": "T-30 ngày",
                    "done": False,
                    "completed_at": None,
                },
                {
                    "id": "off_2",
                    "code": "SOP-DGM-03.2",
                    "title": "Bàn giao Mã nguồn (Git/PR), Tài liệu Kỹ thuật & Dự án MTI/Mojo AI",
                    "description": "Nghiệm thu toàn bộ PR, tài liệu kiến trúc, khóa API và chuyển giao quyền sở hữu trên kho Documents.",
                    "owner": "CTO / Tech Lead",
                    "sla": "T-7 ngày",
                    "done": False,
                    "completed_at": None,
                },
                {
                    "id": "off_3",
                    "code": "SOP-DGM-03.3",
                    "title": "Thu hồi Thiết bị (Laptop/Thẻ từ) & Đóng quyền Truy cập SSO/GitHub/VPN",
                    "description": "Thu hồi tài sản vật lý và vô hiệu hóa token truy cập hệ thống sản xuất, Cloud, VPN, Email.",
                    "owner": "IT & SecOps",
                    "sla": "Ngày cuối (T-0)",
                    "done": False,
                    "completed_at": None,
                },
                {
                    "id": "off_4",
                    "code": "SOP-DGM-04.4",
                    "title": "Đối soát Công nợ Tạm ứng (TK 141) & Quyết toán Lương / Thuế TNCN",
                    "description": "Tính lương ngày công thực tế, phép năm tồn, khấu trừ thuế TNCN và tất toán qua VCB DigiBiz.",
                    "owner": "Kế toán Trưởng (Mai Thị Hồng Thắm)",
                    "sla": "T+7 ngày",
                    "done": False,
                    "completed_at": None,
                },
                {
                    "id": "off_5",
                    "code": "SOP-DGM-04.5",
                    "title": "Báo giảm BHXH Quận 7 (TZ0857G), Chốt sổ BHXH & Ban hành Quyết định Thôi việc",
                    "description": "Nộp hồ sơ báo giảm điện tử lên BHXH Quận 7, bàn giao tờ rời sổ BHXH và chứng từ khấu trừ thuế TNCN.",
                    "owner": "HR & Pháp chế",
                    "sla": "T+14 ngày",
                    "done": False,
                    "completed_at": None,
                },
            ],
        },
    }


def _enrich_workflow(wf_block):
    steps = wf_block.get("steps", [])
    total = len(steps) or 1
    completed = sum(1 for s in steps if s.get("done"))
    pct = round((completed / total) * 100)
    out = dict(wf_block)
    out["completed_count"] = completed
    out["total_count"] = total
    out["progress_pct"] = pct
    if completed == total:
        out["status"] = "completed"
    elif completed > 0 and out.get("status") not in ("notice_submitted",):
        out["status"] = "in_progress"
    return out


def _build_minimal_xlsx(headers, rows):
    """Pure-Python OpenXML (.xlsx) generator that preserves all cells as inline strings (`t="inlineStr"`)."""
    try:
        import xlsxwriter

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        ws = workbook.add_worksheet("VCB_DigiBiz_T10_2026")
        hdr_fmt = workbook.add_format({"bold": True, "bg_color": "#0F172A", "font_color": "#FFFFFF", "border": 1})
        txt_fmt = workbook.add_format({"num_format": "@", "border": 1})
        num_fmt = workbook.add_format({"num_format": "#,##0", "border": 1})

        for col_idx, h in enumerate(headers):
            ws.write_string(0, col_idx, str(h), hdr_fmt)
            ws.set_column(col_idx, col_idx, max(16, len(str(h)) + 4))

        for row_idx, r in enumerate(rows, start=1):
            for col_idx, val in enumerate(r):
                if isinstance(val, (int, float)) and col_idx == 2:
                    ws.write_number(row_idx, col_idx, val, num_fmt)
                else:
                    ws.write_string(row_idx, col_idx, str(val if val is not None else ""), txt_fmt)
        workbook.close()
        return output.getvalue()
    except Exception:
        pass

    def col_letter(n):
        string = ""
        while n >= 0:
            string = chr(n % 26 + 65) + string
            n = n // 26 - 1
        return string

    sheet_rows_xml = []
    all_rows = [headers] + rows
    for r_idx, r in enumerate(all_rows, start=1):
        cells_xml = []
        for c_idx, val in enumerate(r):
            ref = f"{col_letter(c_idx)}{r_idx}"
            text_val = escape(str(val if val is not None else ""))
            cells_xml.append(f'<c r="{ref}" t="inlineStr"><is><t>{text_val}</t></is></c>')
        sheet_rows_xml.append(f'<row r="{r_idx}">{"".join(cells_xml)}</row>')

    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows_xml)}</sheetData>'
        "</worksheet>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="VCB_DigiBiz_T10_2026" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    wb_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("xl/workbook.xml", wb_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
    return buf.getvalue()


class InsilosEmployeeDashboardController(http.Controller):

    def _get_registry_and_employees(self):
        IrConfig = request.env["ir.config_parameter"].sudo()
        raw_reg = IrConfig.get_param("dgm.hr.master_registry")
        if raw_reg:
            try:
                parsed = json.loads(raw_reg)
                if parsed.get("employees"):
                    return parsed
            except Exception:
                pass

        # Fallback: build dynamically from CANONICAL_DGM_EMPLOYEES + hr.employee if present
        emp_rows = []
        for idx, item in enumerate(CANONICAL_DGM_EMPLOYEES, start=1):
            calc = _compute_vn_payroll(item["gross_wage"])
            emp_id = idx
            try:
                rec = (
                    request.env["hr.employee"]
                    .sudo()
                    .search([("registration_number", "=", item["reg"])], limit=1)
                )
                if rec:
                    emp_id = rec.id
            except Exception:
                pass
            emp_rows.append(
                {
                    "id": emp_id,
                    "registration_number": item["reg"],
                    "name": item["name"],
                    "job_title": item["job_title"],
                    "department_name": item["department_name"],
                    "manager_name": item["manager_name"],
                    "work_email": item["work_email"],
                    "work_phone": item["work_phone"],
                    "identification_id": item["id_card_name"],
                    "bank_name": item["bank_name"],
                    "bank_bic": item["bank_bic"],
                    "bank_branch": item["bank_branch"],
                    "bank_acc_number": item["bank_acc_number"],
                    "bhxh_unit": "TZ0857G (BHXH Quận 7)",
                    "contract_name": "HĐLĐ Chuẩn Digimate 2026 (12 Điều)",
                    "join_date": item["join_date"],
                    **calc,
                    "latest_payslip_id": idx,
                    "latest_payslip_name": f"SLIP/202610/{idx:03d}",
                    "latest_payslip_state": "Đã duyệt — Chuẩn VCB DigiBiz (Tháng 10/2026)",
                    "documents_folder_id": None,
                }
            )
        return {
            "company_name": "CÔNG TY CỔ PHẦN DIGIMATE (INNORIA)",
            "tax_id": "0318201249",
            "bhxh_unit": "TZ0857G (BHXH Quận 7)",
            "payslip_run_id": 1,
            "month_label": "Tháng 10/2026",
            "employees": emp_rows,
        }

    def _get_or_init_lifecycle(self, emp_dict):
        IrConfig = request.env["ir.config_parameter"].sudo()
        key = f"dgm.hr.lifecycle.{emp_dict['id']}"
        raw = IrConfig.get_param(key)
        state = None
        if raw:
            try:
                state = json.loads(raw)
            except Exception:
                state = None
        if not state or "onboarding" not in state or "leaving" not in state:
            state = _default_lifecycle(emp_dict)
            IrConfig.set_param(key, json.dumps(state, ensure_ascii=False))
        return state

    def _build_dashboard_payload(self, employee_id=None):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]

        selected = None
        if employee_id:
            try:
                target_id = int(employee_id)
                selected = next((e for e in employees if int(e["id"]) == target_id), None)
            except Exception:
                selected = next((e for e in employees if e["registration_number"] == str(employee_id)), None)

        if not selected:
            # Try current user's linked employee
            try:
                emp_rec = (
                    request.env["hr.employee"]
                    .sudo()
                    .search([("user_id", "=", request.env.uid), ("active", "=", True)], limit=1)
                )
                if emp_rec:
                    selected = next((e for e in employees if int(e["id"]) == emp_rec.id), None)
            except Exception:
                pass

        if not selected:
            selected = employees[0]

        lifecycle = self._get_or_init_lifecycle(selected)
        onboarding = _enrich_workflow(lifecycle["onboarding"])
        leaving = _enrich_workflow(lifecycle["leaving"])

        total_gross = sum(e["gross_wage"] for e in employees)
        total_ins = sum(e["total_insurance"] for e in employees)
        total_pit = sum(e["pit_amount"] for e in employees)
        total_net = sum(e["net_wage"] for e in employees)

        return {
            "company_name": registry.get("company_name", "CÔNG TY CỔ PHẦN DIGIMATE (INNORIA)"),
            "tax_id": registry.get("tax_id", "0318201249"),
            "bhxh_unit": registry.get("bhxh_unit", "TZ0857G (BHXH Quận 7)"),
            "current_employee": selected,
            "all_employees": employees,
            "payroll_summary": {
                "month_label": registry.get("month_label", "Tháng 10/2026"),
                "headcount": len(employees),
                "total_gross": total_gross,
                "total_insurance": total_ins,
                "total_pit": total_pit,
                "total_net": total_net,
                "payslip_run_id": registry.get("payslip_run_id"),
                "vcb_export_url": "/insilos/employee_dashboard/export_vcb_digibiz",
            },
            "onboarding": onboarding,
            "leaving": leaving,
        }

    @http.route("/insilos/employee_dashboard/data", type="jsonrpc", auth="user")
    def get_employee_dashboard_data(self, employee_id=None, **kwargs):
        return self._build_dashboard_payload(employee_id=employee_id)

    @http.route("/insilos/employee_dashboard/toggle_step", type="jsonrpc", auth="user")
    def toggle_lifecycle_step(
        self,
        employee_id=None,
        workflow="onboarding",
        step_id=None,
        done=None,
        action=None,
        notice_date=None,
        expected_last_day=None,
        handover_assignee=None,
        reason=None,
        **kwargs,
    ):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]
        selected = None
        if employee_id:
            try:
                target_id = int(employee_id)
                selected = next((e for e in employees if int(e["id"]) == target_id), None)
            except Exception:
                pass
        if not selected:
            selected = employees[0]

        lifecycle = self._get_or_init_lifecycle(selected)
        today_str = datetime.date.today().isoformat()

        if action == "initiate_leaving":
            lv = lifecycle["leaving"]
            lv["status"] = "notice_submitted"
            lv["notice_date"] = notice_date or today_str
            lv["expected_last_day"] = expected_last_day or (
                (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
            )
            if handover_assignee is not None:
                lv["handover_assignee"] = handover_assignee
            if reason is not None:
                lv["reason"] = reason
            if lv.get("steps"):
                lv["steps"][0]["done"] = True
                lv["steps"][0]["completed_at"] = today_str
        elif workflow in ("onboarding", "leaving") and step_id:
            wf = lifecycle[workflow]
            for s in wf.get("steps", []):
                if s.get("id") == step_id:
                    new_done = bool(done) if done is not None else (not bool(s.get("done")))
                    s["done"] = new_done
                    s["completed_at"] = today_str if new_done else None
                    break

        IrConfig = request.env["ir.config_parameter"].sudo()
        IrConfig.set_param(f"dgm.hr.lifecycle.{selected['id']}", json.dumps(lifecycle, ensure_ascii=False))
        return self._build_dashboard_payload(employee_id=selected["id"])

    @http.route("/insilos/employee_dashboard/export_vcb_digibiz", type="http", auth="user", methods=["GET"])
    def export_vcb_digibiz(self, **kwargs):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]

        headers = [
            "STT",
            "Số tài khoản thụ hưởng",
            "Số tiền chuyển khoản (VND)",
            "Loại tiền",
            "Tên người thụ hưởng",
            "Địa chỉ người thụ hưởng",
            "Ngân hàng thụ hưởng",
            "Mã ngân hàng (CITAD/BIC)",
            "Chi nhánh ngân hàng",
            "Nội dung thanh toán",
            "Phí chuyển khoản (OUR/BEN)",
        ]
        rows = []
        for idx, emp in enumerate(employees, start=1):
            rows.append(
                [
                    str(idx),
                    str(emp["bank_acc_number"]),  # Preserves leading zero on 0111000287863!
                    int(emp["net_wage"]),
                    "VND",
                    emp["name"],
                    "TP. Hồ Chí Minh, Việt Nam",
                    emp["bank_name"],
                    emp["bank_bic"],
                    emp.get("bank_branch", "CN TP.HCM"),
                    f"DIGIMATE THANH TOAN LUONG T10 2026 {emp['registration_number']} {emp['name']}",
                    "OUR",
                ]
            )

        xlsx_bytes = _build_minimal_xlsx(headers, rows)
        filename = "VCB_DigiBiz_Luong_DGM_Thang_10_2026.xlsx"
        return request.make_response(
            xlsx_bytes,
            headers=[
                ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
                ("Content-Length", str(len(xlsx_bytes))),
            ],
        )
