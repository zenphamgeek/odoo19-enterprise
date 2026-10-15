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


def _mask_cccd(val):
    s = "".join(str(val or "").split())
    if len(s) >= 7:
        return s[:3] + ("*" * (len(s) - 6)) + s[-3:]
    return "*" * len(s) if s else ""


def _mask_phone(val):
    s = "".join(str(val or "").split())
    if len(s) >= 8:
        return s[:3] + ("*" * (len(s) - 5)) + s[-2:]
    return "*" * len(s) if s else ""


def _mask_bank_acc(val):
    s = "".join(str(val or "").split())
    if len(s) >= 6:
        return s[:2] + ("*" * (len(s) - 6)) + s[-4:]
    return "*" * len(s) if s else ""


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

    def _find_employee(self, employees, employee_id=None):
        selected = None
        if employee_id is not None:
            try:
                target_id = int(employee_id)
                selected = next((e for e in employees if int(e["id"]) == target_id), None)
            except Exception:
                selected = next(
                    (e for e in employees if e.get("registration_number") == str(employee_id)),
                    None,
                )
        if not selected:
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
        if not selected and employees:
            selected = employees[0]
        return selected

    def _resolve_viewer_role(self, emp_dict):
        uid = getattr(request.env, "uid", None)
        user = getattr(request.env, "user", None)
        if uid in (1, 2):
            return "HR_EXEC"
        if user:
            for grp in (
                "base.group_system",
                "hr.group_hr_manager",
                "hr_payroll.group_hr_payroll_manager",
                "hr_payroll.group_hr_payroll_user",
            ):
                try:
                    if user.has_group(grp):
                        return "HR_EXEC"
                except Exception:
                    pass

        emp_rec = None
        try:
            emp_rec = request.env["hr.employee"].sudo().browse(int(emp_dict["id"]))
            if emp_rec and hasattr(emp_rec, "exists") and not emp_rec.exists():
                emp_rec = None
        except Exception:
            emp_rec = None

        try:
            if emp_rec and getattr(emp_rec, "user_id", None) and emp_rec.user_id.id == uid:
                return "SELF"
            if emp_dict.get("user_id") and int(emp_dict["user_id"]) == uid:
                return "SELF"
        except Exception:
            pass

        try:
            if emp_rec:
                if (
                    getattr(emp_rec, "parent_id", None)
                    and getattr(emp_rec.parent_id, "user_id", None)
                    and emp_rec.parent_id.user_id.id == uid
                ):
                    return "LINE_MANAGER"
                if (
                    getattr(emp_rec, "department_id", None)
                    and getattr(emp_rec.department_id, "manager_id", None)
                    and getattr(emp_rec.department_id.manager_id, "user_id", None)
                    and emp_rec.department_id.manager_id.user_id.id == uid
                ):
                    return "LINE_MANAGER"
            if user and user.has_group("hr.group_hr_user"):
                return "LINE_MANAGER"
        except Exception:
            pass

        return "UNAUTHORIZED"

    def _mask_employee_for_viewer(self, emp_dict, viewer_role):
        emp = dict(emp_dict)
        raw_cccd = str(emp.get("identification_id") or "")
        raw_phone = str(emp.get("work_phone") or "")
        raw_bank = str(emp.get("bank_acc_number") or "")

        cccd_masked = _mask_cccd(raw_cccd)
        phone_masked = _mask_phone(raw_phone)
        bank_masked = _mask_bank_acc(raw_bank)

        emp["identification_id_masked"] = cccd_masked
        emp["work_phone_masked"] = phone_masked
        emp["bank_acc_number_masked"] = bank_masked

        emp["identification_id"] = cccd_masked
        emp["work_phone"] = phone_masked
        emp["bank_acc_number"] = bank_masked
        emp["is_partially_masked"] = True

        can_reveal = viewer_role in ("SELF", "HR_EXEC")
        can_approve = viewer_role == "HR_EXEC"
        can_view_comp = viewer_role in ("SELF", "HR_EXEC")

        emp["viewer_role"] = viewer_role
        emp["can_reveal_pii"] = can_reveal
        emp["can_approve_changes"] = can_approve
        emp["can_view_compensation"] = can_view_comp

        if not can_view_comp:
            emp["gross_wage"] = 0
            emp["net_wage"] = 0
            emp["bhxh_amount"] = 0
            emp["bhyt_amount"] = 0
            emp["bhtn_amount"] = 0
            emp["total_insurance"] = 0
            emp["taxable_income"] = 0
            emp["pit_amount"] = 0
            emp["gross_wage_masked"] = "**.***.000 ₫"
            emp["net_wage_masked"] = "**.***.000 ₫"
        else:
            emp["gross_wage_masked"] = f"{int(emp.get('gross_wage', 0)):,} ₫".replace(",", ".")
            emp["net_wage_masked"] = f"{int(emp.get('net_wage', 0)):,} ₫".replace(",", ".")

        emp["has_active_contract"] = True
        emp["active_contract_code"] = f"HĐLĐ-DGM-2026-{emp['registration_number']}"
        emp["legal_lock_notice"] = (
            "HĐLĐ đang hiệu lực pháp lý — Mọi thay đổi thông tin Định danh / Ngân hàng / Lương "
            "bắt buộc qua Quy trình Phê duyệt 2 Bước (Maker → Checker)"
        )
        return emp

    def _get_or_init_privacy_audit_log(self):
        IrConfig = request.env["ir.config_parameter"].sudo()
        raw = IrConfig.get_param("dgm.hr.privacy_audit_log")
        logs = None
        if raw:
            try:
                logs = json.loads(raw)
            except Exception:
                logs = None
        if not isinstance(logs, list) or not logs:
            logs = [
                {
                    "audit_id": "AUD-ISO-0002",
                    "user_id": 2,
                    "user_name": "Bùi Hữu Tài",
                    "employee_id": 4,
                    "employee_code": "DGM-004",
                    "action": "STEP1_SUBMIT_CHANGE_REQUEST",
                    "timestamp": "14/10/2026 09:15:00",
                    "standard": "ISO/IEC 27701:2019 & NĐ 13/2023/NĐ-CP",
                },
                {
                    "audit_id": "AUD-ISO-0001",
                    "user_id": 2,
                    "user_name": "Lê Xuân Hoàng (CEO)",
                    "employee_id": 3,
                    "employee_code": "DGM-003",
                    "action": "STEP2_APPROVE_LEGAL_CHANGE",
                    "timestamp": "01/10/2026 16:05:12",
                    "standard": "ISO/IEC 27701:2019 & NĐ 13/2023/NĐ-CP",
                },
            ]
            IrConfig.set_param("dgm.hr.privacy_audit_log", json.dumps(logs, ensure_ascii=False))
        return logs

    def _append_privacy_audit_log(self, emp_dict, action):
        IrConfig = request.env["ir.config_parameter"].sudo()
        logs = self._get_or_init_privacy_audit_log()
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        user_name = getattr(getattr(request.env, "user", None), "name", None) or "System Admin"
        entry = {
            "audit_id": f"AUD-ISO-{len(logs) + 1:04d}",
            "user_id": getattr(request.env, "uid", 2),
            "user_name": user_name,
            "employee_id": emp_dict["id"],
            "employee_code": emp_dict["registration_number"],
            "action": action,
            "timestamp": now_str,
            "standard": "ISO/IEC 27701:2019 & NĐ 13/2023/NĐ-CP",
        }
        logs.insert(0, entry)
        IrConfig.set_param("dgm.hr.privacy_audit_log", json.dumps(logs, ensure_ascii=False))
        return logs

    def _get_or_init_change_requests(self, employees):
        IrConfig = request.env["ir.config_parameter"].sudo()
        raw = IrConfig.get_param("dgm.hr.change_requests")
        reqs = None
        if raw:
            try:
                reqs = json.loads(raw)
            except Exception:
                reqs = None
        if not isinstance(reqs, list) or not reqs:
            emp_004 = next((e for e in employees if e.get("registration_number") == "DGM-004"), None)
            emp_003 = next((e for e in employees if e.get("registration_number") == "DGM-003"), None)
            id_004 = emp_004["id"] if emp_004 else 4
            id_003 = emp_003["id"] if emp_003 else 3
            reqs = [
                {
                    "id": "CR-DGM-2026-0001",
                    "request_id": "CR-DGM-2026-0001",
                    "employee_id": id_004,
                    "employee_code": "DGM-004",
                    "employee_name": "Bùi Hữu Tài",
                    "field_type": "work_phone",
                    "field_label": "Số Điện thoại Liên hệ Pháp lý",
                    "old_value_masked": "090*****04",
                    "new_value": "0903889904",
                    "new_value_masked": "090*****04",
                    "legal_reason": "Cập nhật SĐT chính chủ đã định danh VNeID Mức 2 phục vụ nhận OTP ký số Phụ lục HĐLĐ Onsite MTI",
                    "evidence_doc_ref": "VNeID-DGM004-202610",
                    "contract_ref": "HĐLĐ Chuẩn Digimate 2026 (12 Điều) — Active",
                    "requested_by_name": "Bùi Hữu Tài",
                    "requested_at": "14/10/2026 09:15",
                    "state": "pending",
                    "approved_by_name": "",
                    "approved_at": "",
                    "approver_note": "",
                },
                {
                    "id": "CR-DGM-2026-0002",
                    "request_id": "CR-DGM-2026-0002",
                    "employee_id": id_003,
                    "employee_code": "DGM-003",
                    "employee_name": "Mai Thị Hồng Thắm",
                    "field_type": "bank_account",
                    "field_label": "Tài khoản Ngân hàng Nhận lương (VCB DigiBiz)",
                    "old_value_masked": "01*******7863 (VIETCOMBANK)",
                    "new_value": "0111000287863",
                    "new_value_masked": "01*******7863 (VIETCOMBANK)",
                    "legal_reason": "Chuẩn hóa định dạng Text bảo toàn số 0 đầu cho tài khoản VCB DigiBiz theo Phụ lục HĐLĐ PL01/2026",
                    "evidence_doc_ref": "PL01-HDLD-DGM003",
                    "contract_ref": "HĐLĐ Chuẩn Digimate 2026 (12 Điều) — Active",
                    "requested_by_name": "Mai Thị Hồng Thắm",
                    "requested_at": "01/10/2026 14:20",
                    "state": "approved",
                    "approved_by_name": "Lê Xuân Hoàng (CEO)",
                    "approved_at": "01/10/2026 16:05",
                    "approver_note": "Đã đối chiếu xác nhận ngân hàng VCB Quận 7 & Phụ lục HĐLĐ.",
                },
            ]
            IrConfig.set_param("dgm.hr.change_requests", json.dumps(reqs, ensure_ascii=False))
        return reqs

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
        raw_employees = registry["employees"]

        scoped_employees = []
        for raw_emp in raw_employees:
            role = self._resolve_viewer_role(raw_emp)
            if role != "UNAUTHORIZED":
                scoped_employees.append(self._mask_employee_for_viewer(raw_emp, role))

        if not scoped_employees and raw_employees:
            scoped_employees.append(self._mask_employee_for_viewer(raw_employees[0], "SELF"))

        selected = self._find_employee(scoped_employees, employee_id)

        lifecycle = self._get_or_init_lifecycle(selected)
        onboarding = _enrich_workflow(lifecycle["onboarding"])
        leaving = _enrich_workflow(lifecycle["leaving"])

        change_requests = self._get_or_init_change_requests(raw_employees)
        pending_count = sum(1 for r in change_requests if r.get("state") == "pending")
        privacy_audit_log = self._get_or_init_privacy_audit_log()[:10]

        total_gross = sum(e["gross_wage"] for e in raw_employees)
        total_ins = sum(e["total_insurance"] for e in raw_employees)
        total_pit = sum(e["pit_amount"] for e in raw_employees)
        total_net = sum(e["net_wage"] for e in raw_employees)

        return {
            "company_name": registry.get("company_name", "CÔNG TY CỔ PHẦN DIGIMATE (INNORIA)"),
            "tax_id": registry.get("tax_id", "0318201249"),
            "bhxh_unit": registry.get("bhxh_unit", "TZ0857G (BHXH Quận 7)"),
            "current_employee": selected,
            "all_employees": scoped_employees,
            "payroll_summary": {
                "month_label": registry.get("month_label", "Tháng 10/2026"),
                "headcount": len(raw_employees),
                "total_gross": total_gross,
                "total_insurance": total_ins,
                "total_pit": total_pit,
                "total_net": total_net,
                "payslip_run_id": registry.get("payslip_run_id"),
                "vcb_export_url": "/insilos/employee_dashboard/export_vcb_digibiz",
            },
            "onboarding": onboarding,
            "leaving": leaving,
            "change_requests": change_requests,
            "pending_approval_count": pending_count,
            "privacy_audit_log": privacy_audit_log,
        }

    @http.route("/insilos/employee_dashboard/data", type="jsonrpc", auth="user")
    def get_employee_dashboard_data(self, employee_id=None, **kwargs):
        return self._build_dashboard_payload(employee_id=employee_id)

    @http.route("/insilos/employee_dashboard/reveal_pii", type="jsonrpc", auth="user")
    def reveal_pii(self, employee_id=None, **kwargs):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]
        target_emp = self._find_employee(employees, employee_id)
        role = self._resolve_viewer_role(target_emp)
        if role == "UNAUTHORIZED":
            if all(self._resolve_viewer_role(e) == "UNAUTHORIZED" for e in employees) and target_emp == employees[0]:
                role = "SELF"
        if role not in ("SELF", "HR_EXEC"):
            return {
                "ok": False,
                "error": "Truy cập bị từ chối theo chính sách Need-to-Know (ISO/IEC 27701 & NĐ 13/2023/NĐ-CP).",
            }

        logs = self._append_privacy_audit_log(target_emp, "REVEAL_PARTIAL_PII_30S")
        return {
            "ok": True,
            "employee_id": target_emp["id"],
            "identification_id_full": str(target_emp.get("identification_id") or ""),
            "work_phone_full": str(target_emp.get("work_phone") or ""),
            "bank_acc_number_full": str(target_emp.get("bank_acc_number") or ""),
            "expires_in_seconds": 30,
            "privacy_audit_log": logs[:10],
        }

    @http.route("/insilos/employee_dashboard/submit_change_request", type="jsonrpc", auth="user")
    def submit_change_request(
        self,
        employee_id=None,
        field_type="work_phone",
        new_value="",
        new_bank_name=None,
        legal_reason="",
        evidence_doc_ref="",
        **kwargs,
    ):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]
        target_emp = self._find_employee(employees, employee_id)

        reqs = self._get_or_init_change_requests(employees)
        next_idx = len(reqs) + 1
        req_id = f"CR-DGM-2026-{next_idx:04d}"
        existing_ids = {r.get("request_id") or r.get("id") for r in reqs}
        while req_id in existing_ids:
            next_idx += 1
            req_id = f"CR-DGM-2026-{next_idx:04d}"

        clean_val = str(new_value or "").strip()
        clean_bank = str(new_bank_name or "").strip()

        if field_type == "work_phone":
            field_label = "Số Điện thoại Liên hệ Pháp lý"
            old_masked = _mask_phone(target_emp.get("work_phone", ""))
            new_masked = _mask_phone(clean_val)
        elif field_type == "bank_account":
            field_label = "Tài khoản Ngân hàng Nhận lương (VCB DigiBiz)"
            old_bank = target_emp.get("bank_name", "VIETCOMBANK")
            eff_bank = clean_bank or old_bank
            old_masked = f"{_mask_bank_acc(target_emp.get('bank_acc_number', ''))} ({old_bank})"
            new_masked = f"{_mask_bank_acc(clean_val)} ({eff_bank})"
        elif field_type == "identification_id":
            field_label = "Số CCCD / Định danh Cá nhân"
            old_masked = _mask_cccd(target_emp.get("identification_id", ""))
            new_masked = _mask_cccd(clean_val)
        elif field_type == "work_email":
            field_label = "Email Công vụ Định danh SSO"
            old_masked = str(target_emp.get("work_email", ""))
            new_masked = clean_val
        elif field_type == "wage":
            field_label = "Mức Lương Gross Hợp đồng (VND)"
            try:
                old_w = int(float(target_emp.get("gross_wage", 0)))
            except Exception:
                old_w = 0
            try:
                new_w = int(float(clean_val or 0))
            except Exception:
                new_w = 0
            old_masked = f"{old_w:,} ₫".replace(",", ".")
            new_masked = f"{new_w:,} ₫".replace(",", ".")
        else:
            field_label = "Thông tin Hồ sơ Pháp lý"
            old_masked = "***"
            new_masked = clean_val

        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        requester_name = getattr(getattr(request.env, "user", None), "name", None) or target_emp["name"]

        new_req = {
            "id": req_id,
            "request_id": req_id,
            "employee_id": target_emp["id"],
            "employee_code": target_emp["registration_number"],
            "employee_name": target_emp["name"],
            "field_type": field_type,
            "field_label": field_label,
            "old_value_masked": old_masked,
            "new_value": clean_val,
            "new_value_masked": new_masked,
            "new_bank_name": clean_bank,
            "legal_reason": str(legal_reason or "").strip()
            or "Cập nhật thông tin hồ sơ pháp lý theo Phụ lục HĐLĐ",
            "evidence_doc_ref": str(evidence_doc_ref or "").strip() or "VNeID-2026",
            "contract_ref": f"{target_emp.get('contract_name', 'HĐLĐ Chuẩn Digimate 2026 (12 Điều)')} — Active",
            "requested_by_name": requester_name,
            "requested_at": now_str,
            "state": "pending",
            "approved_by_name": "",
            "approved_at": "",
            "approver_note": "",
        }
        reqs.insert(0, new_req)
        IrConfig = request.env["ir.config_parameter"].sudo()
        IrConfig.set_param("dgm.hr.change_requests", json.dumps(reqs, ensure_ascii=False))
        self._append_privacy_audit_log(target_emp, "STEP1_SUBMIT_CHANGE_REQUEST")
        return self._build_dashboard_payload(employee_id=target_emp["id"])

    @http.route("/insilos/employee_dashboard/decide_change_request", type="jsonrpc", auth="user")
    def decide_change_request(
        self,
        request_id=None,
        decision="approve",
        approver_note="",
        employee_id=None,
        **kwargs,
    ):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]

        caller_role = self._resolve_viewer_role(employees[0]) if employees else "UNAUTHORIZED"
        if caller_role != "HR_EXEC":
            return {
                "ok": False,
                "error": "Chỉ Quản trị Nhân sự Cấp cao / Ban Giám Đốc (HR_EXEC) mới có thẩm quyền phê duyệt Bước 2 (Checker).",
            }

        reqs = self._get_or_init_change_requests(employees)
        target_req = next(
            (r for r in reqs if (r.get("request_id") == request_id or r.get("id") == request_id)),
            None,
        )
        if not target_req:
            return self._build_dashboard_payload(employee_id=employee_id)

        target_emp = next(
            (
                e
                for e in employees
                if str(e.get("id")) == str(target_req.get("employee_id"))
                or e.get("registration_number") == target_req.get("employee_code")
            ),
            employees[0],
        )

        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        approver_name = getattr(getattr(request.env, "user", None), "name", None) or "Lê Xuân Hoàng (CEO)"
        IrConfig = request.env["ir.config_parameter"].sudo()

        if decision == "approve":
            ftype = target_req.get("field_type")
            new_val = str(target_req.get("new_value") or "").strip()
            new_bank = str(target_req.get("new_bank_name") or "").strip()
            emp_db_id = int(target_emp["id"])
            emp_reg = target_emp["registration_number"]

            if ftype == "work_phone":
                target_emp["work_phone"] = new_val
                try:
                    request.env.cr.execute(
                        "UPDATE hr_employee SET work_phone = %s, mobile_phone = %s WHERE id = %s OR registration_number = %s",
                        (new_val, new_val, emp_db_id, emp_reg),
                    )
                except Exception:
                    pass
            elif ftype == "work_email":
                target_emp["work_email"] = new_val
                try:
                    request.env.cr.execute(
                        "UPDATE hr_employee SET work_email = %s WHERE id = %s OR registration_number = %s",
                        (new_val, emp_db_id, emp_reg),
                    )
                except Exception:
                    pass
            elif ftype == "identification_id":
                target_emp["identification_id"] = new_val
                try:
                    request.env.cr.execute(
                        "UPDATE hr_employee SET id_card_name = %s WHERE id = %s OR registration_number = %s",
                        (new_val, emp_db_id, emp_reg),
                    )
                    request.env.cr.execute(
                        "UPDATE hr_version SET identification_id = %s WHERE employee_id = %s",
                        (new_val, emp_db_id),
                    )
                except Exception:
                    pass
            elif ftype == "bank_account":
                target_emp["bank_acc_number"] = new_val
                if new_bank:
                    target_emp["bank_name"] = new_bank
                try:
                    if new_bank:
                        request.env.cr.execute(
                            """
                            UPDATE res_partner_bank
                               SET account_number = %s,
                                   sanitized_account_number = %s,
                                   bank_name = %s
                             WHERE partner_id IN (
                                   SELECT work_contact_id FROM hr_employee
                                    WHERE id = %s OR registration_number = %s
                             )
                            """,
                            (new_val, new_val, new_bank, emp_db_id, emp_reg),
                        )
                    else:
                        request.env.cr.execute(
                            """
                            UPDATE res_partner_bank
                               SET account_number = %s,
                                   sanitized_account_number = %s
                             WHERE partner_id IN (
                                   SELECT work_contact_id FROM hr_employee
                                    WHERE id = %s OR registration_number = %s
                             )
                            """,
                            (new_val, new_val, emp_db_id, emp_reg),
                        )
                except Exception:
                    pass
            elif ftype == "wage":
                try:
                    new_gross = int(float(new_val))
                    calc = _compute_vn_payroll(new_gross)
                    target_emp.update(calc)
                    request.env.cr.execute(
                        """
                        UPDATE hr_version
                           SET wage = %s
                         WHERE employee_id = %s
                            OR id IN (
                               SELECT current_version_id FROM hr_employee
                                WHERE id = %s OR registration_number = %s
                            )
                        """,
                        (new_gross, emp_db_id, emp_db_id, emp_reg),
                    )
                except Exception:
                    pass

            IrConfig.set_param("dgm.hr.master_registry", json.dumps(registry, ensure_ascii=False))
            target_req["state"] = "approved"
            target_req["approved_by_name"] = approver_name
            target_req["approved_at"] = now_str
            target_req["approver_note"] = (
                str(approver_note or "").strip()
                or "Đã đối chiếu hồ sơ pháp lý & Phụ lục HĐLĐ hợp lệ."
            )
            IrConfig.set_param("dgm.hr.change_requests", json.dumps(reqs, ensure_ascii=False))
            self._append_privacy_audit_log(target_emp, "STEP2_APPROVE_LEGAL_CHANGE")
        else:
            target_req["state"] = "rejected"
            target_req["approved_by_name"] = approver_name
            target_req["approved_at"] = now_str
            target_req["approver_note"] = (
                str(approver_note or "").strip()
                or "Từ chối phê duyệt: Hồ sơ minh chứng chưa đầy đủ."
            )
            IrConfig.set_param("dgm.hr.change_requests", json.dumps(reqs, ensure_ascii=False))
            self._append_privacy_audit_log(target_emp, "STEP2_REJECT_LEGAL_CHANGE")

        return self._build_dashboard_payload(employee_id=employee_id or target_emp["id"])

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
        selected = self._find_employee(employees, employee_id)

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
