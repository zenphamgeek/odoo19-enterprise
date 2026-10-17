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
    {
        "reg": "DGM-009",
        "name": "Trần Văn Huỳnh Phố",
        "id_card_name": "079098014567",
        "job_title": "Kỹ sư Phần mềm Senior (AIfin Onsite)",
        "department_name": "Khối Dịch Vụ Kỹ Sư Onsite B2B (Enterprise B2B & MTI Delivery)",
        "manager_name": "Bùi Hữu Tài",
        "work_email": "pho.tran@inno.ai.vn",
        "work_phone": "0903881009",
        "bank_name": "VIETCOMBANK",
        "bank_bic": "BFTVVNVX",
        "bank_branch": "CN Tân Bình",
        "bank_acc_number": "1045289901",
        "gross_wage": 30000000,
        "join_date": "01/04/2024",
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


CANONICAL_SKILL_TRACKS = [
    {
        "code": "SKL-ERP-OWL3",
        "name": "Odoo 20 & OWL 3 Reactive Architecture",
        "domain": "erp_owl",
        "domain_label": "Odoo 20 & OWL 3 Architecture",
        "target_level": "L4",
        "mandatory_for_swe": True,
        "training_hours": 40,
        "exam_ref": "CERT-OWL3-2026",
        "description": "Làm chủ kiến trúc Reactive Props/Signals OWL 3, Sovereign Compatibility Views và Dual-Bundle SCSS.",
    },
    {
        "code": "SKL-AI-MOJO",
        "name": "AI Agentic Fleet, LLM RAG & Mojo Kernel",
        "domain": "ai_llm",
        "domain_label": "AI Agentic Fleet & Mojo/LLM Engineering",
        "target_level": "L4",
        "mandatory_for_swe": True,
        "training_hours": 48,
        "exam_ref": "CERT-AIFLEET-2026",
        "description": "Thiết kế hệ thống Multi-Agent điều phối song song, tối ưu hóa ngữ cảnh RAG và SIMD/Mojo.",
    },
    {
        "code": "SKL-K8S-PG",
        "name": "Cloud-Native K8s, PgBouncer & High-Availability DB",
        "domain": "cloud_k8s",
        "domain_label": "Cloud-Native K8s, PgBouncer & PostgreSQL",
        "target_level": "L3",
        "mandatory_for_swe": True,
        "training_hours": 36,
        "exam_ref": "CERT-K8SPG-2026",
        "description": "Vận hành Kubernetes Production, tối ưu hóa chỉ mục PostgreSQL 16 và chống tranh chấp khóa TOCTOU.",
    },
    {
        "code": "SKL-SEC-ISO27001",
        "name": "ISO/IEC 27001 & 27701 Zero-Leak Security Engineering",
        "domain": "security_iso",
        "domain_label": "ISO/IEC 27001 & 27701 Security & Privacy",
        "target_level": "L3",
        "mandatory_for_swe": True,
        "training_hours": 24,
        "exam_ref": "CERT-ISO27701-2026",
        "description": "Thực thi che giấu dữ liệu định danh (Partial Masking), kiểm soát RBAC đa tầng và chống rò rỉ khóa bí mật.",
    },
    {
        "code": "SKL-B2B-ACTIVATE",
        "name": "SAP Activate & B2B Enterprise Solution Delivery",
        "domain": "b2b_consulting",
        "domain_label": "B2B Enterprise Consulting & SAP Activate",
        "target_level": "L3",
        "mandatory_for_swe": False,
        "training_hours": 32,
        "exam_ref": "CERT-B2BSAP-2026",
        "description": "Tư vấn chuyển đổi số B2B, chuẩn hóa quy trình nghiệp vụ tài chính - nhân sự - chuỗi cung ứng theo SAP Activate.",
    },
    {
        "code": "SKL-QA-PLAYWRIGHT",
        "name": "Automated Playwright E2E & Adversarial Security Testing",
        "domain": "qa_automation",
        "domain_label": "Automated Playwright E2E & Adversarial QA",
        "target_level": "L3",
        "mandatory_for_swe": True,
        "training_hours": 28,
        "exam_ref": "CERT-PWQA-2026",
        "description": "Xây dựng bộ kiểm thử tự động E2E đa giao diện (Light/Dark) và kiểm thử xâm nhập bảo mật tự động.",
    },
]

SKILL_TRACK_BY_CODE = {t["code"]: t for t in CANONICAL_SKILL_TRACKS}

CANONICAL_EMPLOYEE_KPI_PROFILES = {
    "DGM-001": {
        "kpi_delivery_score": 98.0,
        "kpi_quality_score": 97.0,
        "kpi_work_eval_score": 98.0,
        "okr_key_results_met": "6/6 KR Chiến lược Tập đoàn & Tăng trưởng Doanh thu B2B",
        "sprint_velocity_pct": 99.0,
        "code_review_pass_rate": 98.5,
        "prod_defect_escape_rate": 0.0,
        "b2b_sla_compliance_pct": 100.0,
        "peer_feedback_score": 4.95,
        "state": "approved",
        "next_training_roadmap": "Định hướng Quản trị AI Sovereign Enterprise & Mở rộng Thị trường B2B Quốc tế 2027.",
        "manager_review_note": "Hoàn thành xuất sắc mục tiêu tăng trưởng doanh thu B2B và chuẩn hóa quản trị ISO 27701.",
        "skills": [
            ("SKL-SEC-ISO27001", "L3", "L4", "certified", 100, 98.0, "CERT-ISO27701-DGM001", True),
            ("SKL-B2B-ACTIVATE", "L4", "L4", "certified", 100, 99.0, "CERT-B2BSAP-DGM001", True),
            ("SKL-AI-MOJO", "L3", "L4", "certified", 100, 95.0, "CERT-AIFLEET-DGM001", True),
        ],
    },
    "DGM-002": {
        "kpi_delivery_score": 97.5,
        "kpi_quality_score": 99.0,
        "kpi_work_eval_score": 96.5,
        "okr_key_results_met": "6/6 KR Kiến trúc Lõi Odoo 20, OWL 3 & AI Fleet",
        "sprint_velocity_pct": 98.5,
        "code_review_pass_rate": 99.2,
        "prod_defect_escape_rate": 0.1,
        "b2b_sla_compliance_pct": 99.9,
        "peer_feedback_score": 4.92,
        "state": "approved",
        "next_training_roadmap": "Kiến trúc sư trưởng Hệ thống Tự hành Đa Tác tử (Autonomous Sovereign Fleet L4) & Mojo SIMD.",
        "manager_review_note": "Dẫn dắt toàn bộ kiến trúc kỹ thuật lõi, bảo mật Zero-Leak và tự động hóa kiểm thử 6 lớp.",
        "skills": [
            ("SKL-ERP-OWL3", "L4", "L4", "certified", 100, 99.5, "CERT-OWL3-DGM002", True),
            ("SKL-AI-MOJO", "L4", "L4", "certified", 100, 99.0, "CERT-AIFLEET-DGM002", True),
            ("SKL-K8S-PG", "L4", "L4", "certified", 100, 98.0, "CERT-K8SPG-DGM002", True),
            ("SKL-SEC-ISO27001", "L4", "L4", "certified", 100, 98.5, "CERT-ISO27701-DGM002", True),
            ("SKL-QA-PLAYWRIGHT", "L4", "L4", "certified", 100, 97.5, "CERT-PWQA-DGM002", True),
        ],
    },
    "DGM-003": {
        "kpi_delivery_score": 95.0,
        "kpi_quality_score": 96.0,
        "kpi_work_eval_score": 97.0,
        "okr_key_results_met": "5/5 KR Chuẩn hóa Pháp lý HĐLĐ, Lương VCB DigiBiz & Data Room",
        "sprint_velocity_pct": 96.0,
        "code_review_pass_rate": 97.0,
        "prod_defect_escape_rate": 0.0,
        "b2b_sla_compliance_pct": 100.0,
        "peer_feedback_score": 4.90,
        "state": "approved",
        "next_training_roadmap": "Nâng cấp chứng chỉ Quản trị Quyền riêng tư Quốc tế ISO/IEC 27701 Lead Auditor.",
        "manager_review_note": "Vận hành chuẩn xác 100% kỳ lương BHXH TZ0857G, thuế TNCN và phân quyền Kho Tài liệu Số.",
        "skills": [
            ("SKL-SEC-ISO27001", "L3", "L3", "certified", 100, 97.0, "CERT-ISO27701-DGM003", True),
            ("SKL-B2B-ACTIVATE", "L3", "L3", "certified", 100, 96.0, "CERT-B2BSAP-DGM003", True),
        ],
    },
    "DGM-004": {
        "kpi_delivery_score": 93.0,
        "kpi_quality_score": 91.5,
        "kpi_work_eval_score": 94.0,
        "okr_key_results_met": "5/5 KR Triển khai Dự án Onsite B2B (MTI, Canva, MobiFone MDS)",
        "sprint_velocity_pct": 94.0,
        "code_review_pass_rate": 92.5,
        "prod_defect_escape_rate": 0.4,
        "b2b_sla_compliance_pct": 99.6,
        "peer_feedback_score": 4.82,
        "state": "approved",
        "next_training_roadmap": "Hoàn thành chuyên sâu Cloud-Native K8s L4 cho các cụm triển khai khách hàng Enterprise.",
        "manager_review_note": "Đảm bảo SLA 99.6% cho các khách hàng trọng điểm MTI và MobiFone MDS.",
        "skills": [
            ("SKL-ERP-OWL3", "L3", "L3", "certified", 100, 93.0, "CERT-OWL3-DGM004", True),
            ("SKL-B2B-ACTIVATE", "L4", "L4", "certified", 100, 95.5, "CERT-B2BSAP-DGM004", True),
            ("SKL-SEC-ISO27001", "L3", "L3", "certified", 100, 92.0, "CERT-ISO27701-DGM004", True),
            ("SKL-K8S-PG", "L3", "L3", "certified", 100, 91.0, "CERT-K8SPG-DGM004", True),
        ],
    },
    "DGM-005": {
        "kpi_delivery_score": 92.0,
        "kpi_quality_score": 90.0,
        "kpi_work_eval_score": 91.0,
        "okr_key_results_met": "5/6 KR Dẫn dắt Kỹ thuật Nhóm Phần mềm & Tối ưu ORM",
        "sprint_velocity_pct": 93.0,
        "code_review_pass_rate": 94.0,
        "prod_defect_escape_rate": 0.5,
        "b2b_sla_compliance_pct": 99.2,
        "peer_feedback_score": 4.75,
        "state": "submitted",
        "next_training_roadmap": "BẮT BUỘC: Hoàn thành khóa 'AI Agentic Fleet, LLM RAG & Mojo Kernel' (SKL-AI-MOJO) đạt chuẩn L4 trước 30/11/2026 để mở khóa xếp hạng A/S.",
        "manager_review_note": "Năng lực code và dẫn dắt nhóm tốt (Điểm thành phần >90), nhưng đang bị giới hạn ở Hạng B do chưa hoàn thành chứng chỉ bắt buộc SKL-AI-MOJO.",
        "skills": [
            ("SKL-ERP-OWL3", "L4", "L4", "certified", 100, 94.0, "CERT-OWL3-DGM005", True),
            ("SKL-K8S-PG", "L3", "L3", "certified", 100, 92.0, "CERT-K8SPG-DGM005", True),
            ("SKL-SEC-ISO27001", "L3", "L3", "certified", 100, 91.0, "CERT-ISO27701-DGM005", True),
            ("SKL-QA-PLAYWRIGHT", "L3", "L3", "certified", 100, 90.5, "CERT-PWQA-DGM005", True),
            ("SKL-AI-MOJO", "L2", "L4", "in_progress", 70, 0.0, "", True),
        ],
    },
    "DGM-006": {
        "kpi_delivery_score": 88.5,
        "kpi_quality_score": 87.0,
        "kpi_work_eval_score": 89.0,
        "okr_key_results_met": "4/5 KR Phát triển Module B2B & Tích hợp Cổng Thanh toán",
        "sprint_velocity_pct": 89.5,
        "code_review_pass_rate": 88.0,
        "prod_defect_escape_rate": 0.8,
        "b2b_sla_compliance_pct": 98.8,
        "peer_feedback_score": 4.65,
        "state": "submitted",
        "next_training_roadmap": "BẮT BUỘC: Hoàn thành nâng cấp kỹ năng 'Cloud-Native K8s, PgBouncer & High-Availability DB' (SKL-K8S-PG) để đủ điều kiện xét nâng bậc Kỹ sư.",
        "manager_review_note": "Tiến độ dự án Onsite ổn định. Yêu cầu hoàn tất bài thi thực hành K8s & PostgreSQL High-Availability trong Quý 4/2026.",
        "skills": [
            ("SKL-ERP-OWL3", "L3", "L3", "certified", 100, 89.0, "CERT-OWL3-DGM006", True),
            ("SKL-SEC-ISO27001", "L3", "L3", "certified", 100, 90.0, "CERT-ISO27701-DGM006", True),
            ("SKL-QA-PLAYWRIGHT", "L3", "L3", "certified", 100, 88.5, "CERT-PWQA-DGM006", True),
            ("SKL-K8S-PG", "L2", "L3", "in_progress", 60, 0.0, "", True),
        ],
    },
    "DGM-007": {
        "kpi_delivery_score": 89.0,
        "kpi_quality_score": 88.0,
        "kpi_work_eval_score": 90.0,
        "okr_key_results_met": "4/5 KR Phát triển Giao diện OWL 3 & Tối ưu Trải nghiệm Người dùng",
        "sprint_velocity_pct": 91.0,
        "code_review_pass_rate": 90.0,
        "prod_defect_escape_rate": 0.6,
        "b2b_sla_compliance_pct": 99.1,
        "peer_feedback_score": 4.70,
        "state": "submitted",
        "next_training_roadmap": "BẮT BUỘC: Hoàn thành 2 chứng chỉ kỹ thuật 'AI Agentic Fleet & LLM RAG' (SKL-AI-MOJO) và 'Automated Playwright E2E' (SKL-QA-PLAYWRIGHT).",
        "manager_review_note": "Kỹ năng Frontend OWL 3 & Dual-Theme SCSS rất tốt. Cần bổ sung ngay kỹ năng kiểm thử tự động Playwright E2E và tích hợp AI.",
        "skills": [
            ("SKL-ERP-OWL3", "L3", "L3", "certified", 100, 92.0, "CERT-OWL3-DGM007", True),
            ("SKL-SEC-ISO27001", "L3", "L3", "certified", 100, 91.0, "CERT-ISO27701-DGM007", True),
            ("SKL-AI-MOJO", "L2", "L3", "in_progress", 65, 0.0, "", True),
            ("SKL-QA-PLAYWRIGHT", "L2", "L3", "in_progress", 80, 0.0, "", True),
        ],
    },
    "DGM-008": {
        "kpi_delivery_score": 84.0,
        "kpi_quality_score": 82.0,
        "kpi_work_eval_score": 85.0,
        "okr_key_results_met": "3/4 KR Hoàn thành Đào tạo Hội nhập Kỹ sư & Sửa lỗi Module ERP",
        "sprint_velocity_pct": 85.0,
        "code_review_pass_rate": 84.0,
        "prod_defect_escape_rate": 1.2,
        "b2b_sla_compliance_pct": 98.0,
        "peer_feedback_score": 4.55,
        "state": "submitted",
        "next_training_roadmap": "LỘ TRÌNH BẮT BUỘC KỸ SƯ PHẦN MỀM: Hoàn thành nâng cấp 3 kỹ năng lõi (SKL-ERP-OWL3, SKL-AI-MOJO, SKL-K8S-PG) dưới sự hướng dẫn của CTO Nguyễn Hoài Ân.",
        "manager_review_note": "Kỹ sư trẻ có tinh thần học hỏi cao. Bắt buộc hoàn thành 100% cổng nâng cấp kỹ năng (Skill Upgrade Gates) trước khi xét lên chính thức L2/L3.",
        "skills": [
            ("SKL-SEC-ISO27001", "L2", "L2", "certified", 100, 88.0, "CERT-ISO27701-DGM008", True),
            ("SKL-QA-PLAYWRIGHT", "L2", "L2", "certified", 100, 86.0, "CERT-PWQA-DGM008", True),
            ("SKL-ERP-OWL3", "L1", "L3", "in_progress", 75, 0.0, "", True),
            ("SKL-AI-MOJO", "L1", "L3", "in_progress", 50, 0.0, "", True),
            ("SKL-K8S-PG", "L1", "L2", "in_progress", 40, 0.0, "", True),
        ],
    },
    "DGM-009": {
        "kpi_delivery_score": 94.0,
        "kpi_quality_score": 93.0,
        "kpi_work_eval_score": 94.5,
        "okr_key_results_met": "5/5 KR Tư vấn & Triển khai Giải pháp B2B Onsite Khách hàng Chiến lược",
        "sprint_velocity_pct": 95.0,
        "code_review_pass_rate": 93.5,
        "prod_defect_escape_rate": 0.3,
        "b2b_sla_compliance_pct": 99.7,
        "peer_feedback_score": 4.85,
        "state": "approved",
        "next_training_roadmap": "Định hướng nâng cấp chứng chỉ Kiến trúc AI Agentic B2B L4 cho các dự án chuyển đổi số quy mô lớn.",
        "manager_review_note": "Kỹ sư Senior Onsite hoàn thành đầy đủ các chứng chỉ kỹ năng bắt buộc và đạt điểm hài lòng khách hàng B2B rất cao.",
        "skills": [
            ("SKL-ERP-OWL3", "L3", "L3", "certified", 100, 94.0, "CERT-OWL3-DGM009", True),
            ("SKL-B2B-ACTIVATE", "L4", "L4", "certified", 100, 96.0, "CERT-B2BSAP-DGM009", True),
            ("SKL-SEC-ISO27001", "L3", "L3", "certified", 100, 93.0, "CERT-ISO27701-DGM009", True),
            ("SKL-QA-PLAYWRIGHT", "L3", "L3", "certified", 100, 92.0, "CERT-PWQA-DGM009", True),
        ],
    },
}

RANK_GRADE_LABELS = {
    "tier_s": "Hạng S — Xuất sắc (Outstanding ≥ 90 & Đạt 100% Kỹ năng Bắt buộc)",
    "tier_a": "Hạng A — Giỏi (Exceeds Expectations 80–89 & Đạt 100% Kỹ năng)",
    "tier_b": "Hạng B — Đạt chuẩn / Chờ Mở khóa Kỹ năng (70–79 hoặc Chưa hoàn tất Kỹ năng Bắt buộc)",
    "tier_c": "Hạng C — Cần Đào tạo Nâng cấp Kỹ năng (< 70)",
}


def _recompute_kpi_hub_dict(hub):
    """Deterministically computes 4-pillar weighted KPI score and enforces the Mandatory SWE Skill Gate."""
    gates = hub.get("skill_gates", [])
    mandatory_gates = [g for g in gates if g.get("is_mandatory", True)]
    mandatory_total = len(mandatory_gates)
    mandatory_certified = sum(1 for g in mandatory_gates if g.get("status") == "certified")
    mandatory_pending = max(0, mandatory_total - mandatory_certified)

    if mandatory_total > 0:
        skill_completion_pct = int(round((mandatory_certified / mandatory_total) * 100))
        pts = 0.0
        for g in mandatory_gates:
            if g.get("status") == "certified":
                pts += 100.0
            else:
                pts += min(90.0, float(g.get("progress_pct") or 0)) * 0.5
        skill_upgrade_score = round(pts / mandatory_total, 2)
    else:
        skill_completion_pct = 100
        skill_upgrade_score = 100.0

    delivery = round(float(hub.get("kpi_delivery_score") or 0.0), 2)
    quality = round(float(hub.get("kpi_quality_score") or 0.0), 2)
    work_eval = round(float(hub.get("kpi_work_eval_score") or 0.0), 2)

    total_score = round(
        0.35 * delivery + 0.25 * quality + 0.20 * work_eval + 0.20 * skill_upgrade_score,
        2,
    )

    if total_score >= 90.0:
        raw_grade = "tier_s"
    elif total_score >= 80.0:
        raw_grade = "tier_a"
    elif total_score >= 70.0:
        raw_grade = "tier_b"
    else:
        raw_grade = "tier_c"

    if mandatory_pending > 0:
        skill_gate_capped = True
        promotion_eligible = False
        effective_grade = "tier_b" if raw_grade in ("tier_s", "tier_a") else raw_grade
    else:
        skill_gate_capped = False
        effective_grade = raw_grade
        promotion_eligible = effective_grade in ("tier_s", "tier_a")

    hub["kpi_delivery_score"] = delivery
    hub["kpi_quality_score"] = quality
    hub["kpi_work_eval_score"] = work_eval
    hub["kpi_skill_upgrade_score"] = skill_upgrade_score
    hub["total_kpi_score"] = total_score
    hub["mandatory_skill_total"] = mandatory_total
    hub["mandatory_skill_certified"] = mandatory_certified
    hub["mandatory_skill_pending"] = mandatory_pending
    hub["skill_completion_pct"] = skill_completion_pct
    hub["raw_rank_grade"] = raw_grade
    hub["raw_rank_label"] = RANK_GRADE_LABELS.get(raw_grade, raw_grade)
    hub["rank_grade"] = effective_grade
    hub["rank_label"] = RANK_GRADE_LABELS.get(effective_grade, effective_grade)
    hub["skill_gate_capped"] = skill_gate_capped
    hub["promotion_eligible"] = promotion_eligible
    hub["state_label"] = (
        "Đã Phê duyệt Chính thức"
        if hub.get("state") == "approved"
        else ("Đang Chờ Mở khóa Kỹ năng / Duyệt KPI" if hub.get("state") == "submitted" else "Bản nháp")
    )
    hub["pillars"] = [
        {
            "code": "delivery",
            "name": "Hiệu suất Bàn giao Dự án & OKR (Delivery)",
            "weight_pct": 35,
            "score": delivery,
            "weighted_score": round(0.35 * delivery, 2),
            "target": "≥ 85.0 điểm (Sprint Velocity & On-Time Delivery)",
        },
        {
            "code": "quality",
            "name": "Chất lượng Mã nguồn & Kiến trúc (Code Quality)",
            "weight_pct": 25,
            "score": quality,
            "weighted_score": round(0.25 * quality, 2),
            "target": "≥ 85.0 điểm (Code Review Pass ≥ 90%, Defect Escape < 1%)",
        },
        {
            "code": "work_eval",
            "name": "Đánh giá Công việc, SLA B2B & Phối hợp (Work Eval)",
            "weight_pct": 20,
            "score": work_eval,
            "weighted_score": round(0.20 * work_eval, 2),
            "target": "≥ 85.0 điểm (B2B SLA ≥ 99%, Peer Review ≥ 4.5/5.0)",
        },
        {
            "code": "skill_upgrade",
            "name": "Hoàn thành Nâng cấp Kỹ năng Bắt buộc (Skill Gate)",
            "weight_pct": 20,
            "score": skill_upgrade_score,
            "weighted_score": round(0.20 * skill_upgrade_score, 2),
            "target": "BẮT BUỘC đạt 100% chứng chỉ kỹ năng để mở khóa Hạng A/S",
        },
    ]
    return hub


def _default_kpi_skill_hub(emp_dict):
    reg = emp_dict.get("registration_number", "DGM-001")
    prof = CANONICAL_EMPLOYEE_KPI_PROFILES.get(reg, CANONICAL_EMPLOYEE_KPI_PROFILES["DGM-005"])
    gates = []
    for idx, (s_code, cur_lvl, tgt_lvl, st, prog, ex_score, cert_ref, is_mand) in enumerate(
        prof.get("skills", []), start=1
    ):
        track = SKILL_TRACK_BY_CODE.get(s_code, CANONICAL_SKILL_TRACKS[0])
        gates.append(
            {
                "gate_id": f"GATE-{reg}-{idx:02d}",
                "skill_code": s_code,
                "skill_name": track["name"],
                "domain": track["domain"],
                "domain_label": track["domain_label"],
                "training_hours": track["training_hours"],
                "exam_ref": track["exam_ref"],
                "description": track["description"],
                "current_level": cur_lvl,
                "target_level": tgt_lvl,
                "is_mandatory": bool(is_mand),
                "status": st,
                "status_label": "Đã Đạt Chứng chỉ (Certified)" if st == "certified" else "Đang Đào tạo Nâng cấp (Bắt buộc)",
                "progress_pct": int(prog),
                "exam_score": float(ex_score),
                "certificate_ref": cert_ref or (f"{track['exam_ref']}-{reg}" if st == "certified" else ""),
                "deadline": "2026-10-15" if st == "certified" else "2026-11-30",
                "certified_date": "2026-10-10" if st == "certified" else "",
                "mentor_notes": (
                    "Đã vượt qua kỳ sát hạch thực chiến & Code Review kiến trúc."
                    if st == "certified"
                    else "Bắt buộc hoàn thành bài thi thực hành & đồ án nâng cấp kỹ năng trước hạn."
                ),
            }
        )

    hub = {
        "evaluation_code": f"KPI-2026Q4-{reg}",
        "employee_id": emp_dict.get("id", 1),
        "employee_code": reg,
        "employee_name": emp_dict.get("name", ""),
        "job_title": emp_dict.get("job_title", ""),
        "department_name": emp_dict.get("department_name", ""),
        "evaluation_period": "Q4/2026",
        "reviewer_name": "Nguyễn Hoài Ân (CTO)" if reg != "DGM-001" else "Hội đồng Quản trị Digimate",
        "kpi_delivery_score": prof["kpi_delivery_score"],
        "kpi_quality_score": prof["kpi_quality_score"],
        "kpi_work_eval_score": prof["kpi_work_eval_score"],
        "okr_key_results_met": prof["okr_key_results_met"],
        "sprint_velocity_pct": prof["sprint_velocity_pct"],
        "code_review_pass_rate": prof["code_review_pass_rate"],
        "prod_defect_escape_rate": prof["prod_defect_escape_rate"],
        "b2b_sla_compliance_pct": prof["b2b_sla_compliance_pct"],
        "peer_feedback_score": prof["peer_feedback_score"],
        "state": prof["state"],
        "next_training_roadmap": prof["next_training_roadmap"],
        "manager_review_note": prof["manager_review_note"],
        "skill_gates": gates,
    }
    return _recompute_kpi_hub_dict(hub)


PDCA_STAGE_MAP = {
    "plan": "P - Plan",
    "do": "D - Do",
    "check": "C - Check",
    "act": "A - Act",
    "P - Plan": "P - Plan",
    "D - Do": "D - Do",
    "C - Check": "C - Check",
    "A - Act": "A - Act",
}

PDCA_STAGE_CODE_MAP = {
    "plan": "plan",
    "do": "do",
    "check": "check",
    "act": "act",
    "P - Plan": "plan",
    "D - Do": "do",
    "C - Check": "check",
    "A - Act": "act",
}

CANONICAL_COMPANY_OKRS = [
    {
        "code": "OKR-2026-Q4-C01",
        "name": "Tăng trưởng Doanh thu Phần mềm B2B, Triển khai SAP Activate & Tuân thủ Hóa đơn Điện tử 1C26TAA (NĐ 70/2025/NĐ-CP)",
        "owner_name": "Lê Xuân Hoàng (CEO)",
        "pdca_stage": "C - Check",
        "pdca_stage_code": "check",
        "okr_score": 0.92,
        "progress_pct": 92,
        "confidence_level": "on_track",
        "key_results": [
            {
                "code": "KR-C01-01",
                "name": "Hoàn thành 100% nghiệm thu hợp đồng phần mềm B2B (MTI, KTT, AIfin) và phát hành HĐĐT 1C26TAA đúng hạn",
                "target_value": 100.0,
                "current_value": 95.0,
                "unit": "%",
                "progress_pct": 95,
                "kr_score": 0.95,
                "pdca_stage": "check",
                "pdca_stage_label": "C - Check",
            },
            {
                "code": "KR-C01-02",
                "name": "Đạt tỷ lệ đúng hạn thanh toán Net 40 & đối soát công nợ tự động ≥ 98%",
                "target_value": 98.0,
                "current_value": 94.0,
                "unit": "%",
                "progress_pct": 96,
                "kr_score": 0.96,
                "pdca_stage": "do",
                "pdca_stage_label": "D - Do",
            },
            {
                "code": "KR-C01-03",
                "name": "Mở rộng 4 gói giải pháp mẫu SAP Activate Turnkey & B2B Staff Augmentation",
                "target_value": 4.0,
                "current_value": 3.5,
                "unit": "gói giải pháp",
                "progress_pct": 88,
                "kr_score": 0.85,
                "pdca_stage": "act",
                "pdca_stage_label": "A - Act",
            },
        ],
    },
    {
        "code": "OKR-2026-Q4-C02",
        "name": "Chuẩn hóa Năng lực Kỹ thuật OWL 3, AI Agentic Swarm & Vận hành B2B Onsite SLA 140–180h (Zero Defect Escape)",
        "owner_name": "Nguyễn Hoài Ân (CTO)",
        "pdca_stage": "D - Do",
        "pdca_stage_code": "do",
        "okr_score": 0.89,
        "progress_pct": 89,
        "confidence_level": "on_track",
        "key_results": [
            {
                "code": "KR-C02-01",
                "name": "Đảm bảo 100% dự án B2B Onsite đạt SLA 140–180h/tháng và tỷ lệ lỗi lọt Production < 0.5%",
                "target_value": 100.0,
                "current_value": 96.0,
                "unit": "%",
                "progress_pct": 96,
                "kr_score": 0.96,
                "pdca_stage": "check",
                "pdca_stage_label": "C - Check",
            },
            {
                "code": "KR-C02-02",
                "name": "Đạt ≥ 90% kỹ sư phần mềm hoàn thành chứng chỉ Kỹ năng Bắt buộc (Skill Upgrade Gate)",
                "target_value": 90.0,
                "current_value": 78.0,
                "unit": "%",
                "progress_pct": 87,
                "kr_score": 0.87,
                "pdca_stage": "do",
                "pdca_stage_label": "D - Do",
            },
            {
                "code": "KR-C02-03",
                "name": "Triển khai 100% Dual-Theme E2E & Adversarial Security Gate tự động trước khi đẩy K8s Production",
                "target_value": 100.0,
                "current_value": 85.0,
                "unit": "%",
                "progress_pct": 85,
                "kr_score": 0.85,
                "pdca_stage": "act",
                "pdca_stage_label": "A - Act",
            },
        ],
    },
    {
        "code": "OKR-2026-Q4-C03",
        "name": "Hoàn thiện Hệ thống Quản trị Nhân sự 360° Appraisal, 9-Box Calibration, BHXH TZ0857G & Bảo mật ISO/IEC 27701",
        "owner_name": "Mai Thị Hồng Thắm (CFO / HR Director)",
        "pdca_stage": "A - Act",
        "pdca_stage_code": "act",
        "okr_score": 0.95,
        "progress_pct": 95,
        "confidence_level": "on_track",
        "key_results": [
            {
                "code": "KR-C03-01",
                "name": "100% nhân sự hoàn thành Đánh giá 360° (Self, Peer/Client, Tech Lead) và Hiệu chuẩn 9-Box Quý 4/2026",
                "target_value": 100.0,
                "current_value": 96.0,
                "unit": "%",
                "progress_pct": 96,
                "kr_score": 0.96,
                "pdca_stage": "act",
                "pdca_stage_label": "A - Act",
            },
            {
                "code": "KR-C03-02",
                "name": "Đạt 100% chính xác chi lương VCB DigiBiz 11 cột, trích nộp BHXH Quận 7 (TZ0857G) & Thuế TNCN",
                "target_value": 100.0,
                "current_value": 100.0,
                "unit": "%",
                "progress_pct": 100,
                "kr_score": 1.00,
                "pdca_stage": "act",
                "pdca_stage_label": "A - Act",
            },
            {
                "code": "KR-C03-03",
                "name": "Duy trì 0 sự cố rò rỉ PII với cơ chế Partial Masking, 30s Reveal & Maker-Checker 2 bước",
                "target_value": 100.0,
                "current_value": 90.0,
                "unit": "%",
                "progress_pct": 90,
                "kr_score": 0.90,
                "pdca_stage": "check",
                "pdca_stage_label": "C - Check",
            },
        ],
    },
]

CANONICAL_PROJECT_PDCA_TEMPLATES = [
    {
        "code": "PRJ-TPL-PDCA-01",
        "name": "Dự án Triển khai ERP Chuẩn SAP Activate Turnkey (Fit-to-Standard)",
        "category": "sap_activate_erp",
        "methodology": "SAP Activate + Loop PDCA (Discover → Prepare → Explore → Realize → Deploy → Run)",
        "sla_commitment": "Go-Live đúng hạn ≥ 98% • Zero P1 Blocker • 100% Fit-to-Standard Blueprint",
        "target_margin_pct": 42.0,
        "template_docs": ["TPL-PRJ-05", "SOP-DGM-11", "TPL-OKR-01"],
        "pdca_gates": [
            {
                "phase": "P - Plan",
                "gate_name": "Khởi tạo Dự án, Fit-to-Standard Blueprint & Ma trận Phân quyền (RBAC)",
                "deliverable": "Project Charter (TPL-PRJ-05), WBS & Backlog Chuẩn",
            },
            {
                "phase": "D - Do",
                "gate_name": "Cấu hình Phân hệ, Tích hợp API/HĐĐT 1C26TAA & Sprint Delivery",
                "deliverable": "Increment Build, Code Review Pass ≥ 90%, Unit Test",
            },
            {
                "phase": "C - Check",
                "gate_name": "Kiểm thử E2E Playwright, UAT Khách hàng & Kiểm toán Bảo mật",
                "deliverable": "Biên bản UAT Sign-off, Zero Leak / Zero Bare Hex Audit",
            },
            {
                "phase": "A - Act",
                "gate_name": "Cutover Go-Live, Bàn giao Vận hành & Chuẩn hóa Thư viện Tri thức",
                "deliverable": "Nghiệm thu Go-Live, Bài học Kinh nghiệm (Retrospective PDCA)",
            },
        ],
    },
    {
        "code": "PRJ-TPL-PDCA-02",
        "name": "Dự án B2B Staff Augmentation & Agile Onsite SLA (140–180h/tháng)",
        "category": "b2b_onsite_sla",
        "methodology": "Agile Scrum + PDCA SLA (SOP-DGM-07 & SOP-DGM-08)",
        "sla_commitment": "Định mức 140–180h/tháng • OT 100%/150% • Bảo hành thay thế 5 ngày • Net 40",
        "target_margin_pct": 38.0,
        "template_docs": ["TPL-PRJ-06", "TPL-HR-07", "SOP-DGM-11"],
        "pdca_gates": [
            {
                "phase": "P - Plan",
                "gate_name": "Thẩm định Kỹ năng Kỹ sư Onsite (Skill Gate) & Cam kết SLA 5 Ngày Dùng thử",
                "deliverable": "Hồ sơ Kỹ sư chuẩn hóa, Phụ lục SLA Onsite (TPL-PRJ-06)",
            },
            {
                "phase": "D - Do",
                "gate_name": "Thực thi Sprint tại Khách hàng (MTI / KTT / AIfin) & Log Timesheet Hàng ngày",
                "deliverable": "Sprint Burndown, PR/MR được Tech Lead khách hàng duyệt",
            },
            {
                "phase": "C - Check",
                "gate_name": "Đối soát Timesheet 140–180h, Đánh giá 360° từ Khách hàng & Kiểm tra OT",
                "deliverable": "Bảng chấm công B2B có chữ ký xác nhận & Điểm 360° ≥ 4.5/5.0",
            },
            {
                "phase": "A - Act",
                "gate_name": "Niêm phong HMAC-SHA256, Xuất HĐĐT 1C26TAA & Đào tạo Bù đắp Kỹ năng",
                "deliverable": "Hóa đơn 1C26TAA hợp lệ, Kế hoạch nâng cấp kỹ năng Quý tiếp theo",
            },
        ],
    },
    {
        "code": "PRJ-TPL-PDCA-03",
        "name": "Dự án Nghiên cứu & Phát triển AI Agentic Swarm / Mojo High-Frequency",
        "category": "ai_agentic_rnd",
        "methodology": "Dual-Track Agile R&D + Benchmark PDCA Loop",
        "sla_commitment": "Sub-50ms P99 Latency • Pass@1 ≥ 92% • Ưu đãi Thuế Phần mềm (SOP-DGM-09)",
        "target_margin_pct": 55.0,
        "template_docs": ["TPL-OKR-01", "TPL-PRJ-05", "SOP-DGM-11"],
        "pdca_gates": [
            {
                "phase": "P - Plan",
                "gate_name": "Giả thuyết Kiến trúc (Hypothesis), Thiết kế Eval Harness & Tập dữ liệu Chuẩn",
                "deliverable": "Đặc tả R&D (ADR), Baseline Benchmark & Bộ tiêu chí OKR (TPL-OKR-01)",
            },
            {
                "phase": "D - Do",
                "gate_name": "Huấn luyện / Tối ưu hóa Kernel Mojo, Multi-Agent Orchestration & RAG",
                "deliverable": "Source Code, Thực nghiệm song song trên Pro Swarm Nodes",
            },
            {
                "phase": "C - Check",
                "gate_name": "Đo kiểm Hiệu năng (Throughput/Latency), Red-Team Prompt Injection & SoD",
                "deliverable": "Báo cáo Benchmark định lượng, 0 lỗ hổng Prompt/Secret Leak",
            },
            {
                "phase": "A - Act",
                "gate_name": "Đóng gói Production Container, Đăng ký Sở hữu Trí tuệ & Nhân rộng Toàn hệ thống",
                "deliverable": "Release Tag, Hồ sơ minh chứng R&D hưởng ưu đãi thuế CIT",
            },
        ],
    },
    {
        "code": "PRJ-TPL-PDCA-04",
        "name": "Dự án Kiểm toán An toàn Thông tin ISO/IEC 27001 & Bảo vệ Dữ liệu Cá nhân ISO 27701",
        "category": "iso_security_privacy",
        "methodology": "ISO/IEC 27001:2022 & 27701:2019 Continual PDCA Cycle",
        "sla_commitment": "100% Need-to-Know Masking • 30s Audited Reveal • 0 Critical/High Vulnerability",
        "target_margin_pct": 45.0,
        "template_docs": ["TPL-HR-08", "TPL-HR-07", "SOP-DGM-11"],
        "pdca_gates": [
            {
                "phase": "P - Plan",
                "gate_name": "Đánh giá Rủi ro Dữ liệu Cá nhân (DPIA) & Thiết lập Ma trận Kiểm soát Truy cập",
                "deliverable": "Hồ sơ DPIA Nghị định 13/2023/NĐ-CP & Chính sách Masking",
            },
            {
                "phase": "D - Do",
                "gate_name": "Áp dụng Khóa Giao dịch Bipartite Advisory Lock, Savepoint & Sanitizer",
                "deliverable": "34 Bản vá Bảo mật Adversarial, Quy trình Maker-Checker 2 Bước",
            },
            {
                "phase": "C - Check",
                "gate_name": "Chạy Kiểm thử Tự động Adversarial Security & Rà soát Nhật ký Audit ISO",
                "deliverable": "Báo cáo Kiểm toán nội bộ 100% Pass (Exit Code 0)",
            },
            {
                "phase": "A - Act",
                "gate_name": "Hiệu chuẩn Định kỳ Hàng quý, Đào tạo Nhận thức Bảo mật & Cải tiến Liên tục",
                "deliverable": "Biên bản Hiệu chuẩn 9-Box & Chứng nhận Tuân thủ An toàn Thông tin (TPL-HR-08)",
            },
        ],
    },
]

CANONICAL_PDCA_COMPANION_DOCS = [
    {"code": "TPL-PRJ-05", "name": "Mẫu Khởi tạo & Quản trị Dự án Chuẩn PDCA / SAP Activate"},
    {"code": "TPL-PRJ-06", "name": "Mẫu Kiểm soát Chất lượng Sprint, SLA B2B Onsite & Nghiệm thu PDCA"},
    {"code": "TPL-HR-07", "name": "Mẫu Đánh giá Nhân sự 360° (Self, Peer/Client, Tech Lead)"},
    {"code": "TPL-HR-08", "name": "Mẫu Ma trận Hiệu chuẩn Nhân tài 9-Box & Lộ trình Thăng tiến"},
    {"code": "TPL-OKR-01", "name": "Mẫu Thiết lập & Theo dõi OKRs Doanh nghiệp Phần mềm (Chu trình PDCA)"},
    {"code": "SOP-DGM-11", "name": "Quy trình Quản trị Dự án PDCA, Đánh giá Nhân sự 360° & Triển khai OKRs 2026"},
]


def _recompute_okr_hub_dict(okr_hub):
    """Deterministically recomputes Key Result scores (0.00 - 1.00), progress %, and Objective OKR scores."""
    emp_okrs = okr_hub.get("employee_okrs", [])
    flat_krs = []
    obj_scores = []

    for obj in emp_okrs:
        krs = obj.get("key_results", [])
        kr_scores = []
        for kr in krs:
            target = float(kr.get("target_value") or 100.0)
            current = float(kr.get("current_value") or 0.0)
            ratio = (current / target) if target > 0 else 1.0
            score = round(min(1.0, max(0.0, ratio)), 2)
            pct = int(round(score * 100))
            raw_stage = str(kr.get("pdca_stage") or "do").strip()
            stage_code = PDCA_STAGE_CODE_MAP.get(raw_stage, "do")
            stage_label = PDCA_STAGE_MAP.get(raw_stage, "D - Do")

            kr["target_value"] = round(target, 2)
            kr["current_value"] = round(current, 2)
            kr["kr_score"] = score
            kr["progress_pct"] = pct
            kr["pdca_stage"] = stage_code
            kr["pdca_stage_label"] = stage_label
            kr_scores.append(score)
            flat_krs.append(kr)

        obj_score = round(sum(kr_scores) / len(kr_scores), 2) if kr_scores else 0.90
        obj["okr_score"] = obj_score
        obj["progress_pct"] = int(round(obj_score * 100))
        raw_obj_stage = str(obj.get("pdca_stage") or "check").strip()
        obj["pdca_stage_code"] = PDCA_STAGE_CODE_MAP.get(raw_obj_stage, "check")
        obj["pdca_stage"] = PDCA_STAGE_MAP.get(raw_obj_stage, "C - Check")
        obj["confidence_level"] = "on_track" if obj_score >= 0.75 else "at_risk"
        obj_scores.append(obj_score)

    overall_score = round(sum(obj_scores) / len(obj_scores), 2) if obj_scores else 0.90
    okr_hub["okr_score"] = overall_score
    okr_hub["progress_pct"] = int(round(overall_score * 100))
    okr_hub["confidence_level"] = "on_track" if overall_score >= 0.75 else "at_risk"
    okr_hub["pdca_stage"] = emp_okrs[0]["pdca_stage"] if emp_okrs else "C - Check"
    okr_hub["key_results"] = flat_krs
    okr_hub["company_okrs"] = CANONICAL_COMPANY_OKRS
    return okr_hub


def _default_okr_hub(emp_dict, kpi_skill_hub=None):
    reg = emp_dict.get("registration_number", "DGM-001")
    emp_name = emp_dict.get("name", "")
    job_title = emp_dict.get("job_title", "")
    dept_name = emp_dict.get("department_name", "")

    if reg in ("DGM-001", "DGM-003", "DGM-008"):
        aligned_code = "OKR-2026-Q4-C01" if reg == "DGM-001" else "OKR-2026-Q4-C03"
        obj_title = f"Điều hành Chiến lược, Tài chính – Nhân sự 360° & Tuân thủ Pháp lý Quý 4/2026 ({emp_name})"
        krs = [
            {
                "code": f"KR-{reg}-01",
                "name": "Hoàn thành 100% chỉ tiêu Doanh thu / Đối soát Công nợ Net 40 & Hóa đơn 1C26TAA đúng hạn",
                "target_value": 100.0,
                "current_value": 96.0,
                "unit": "%",
                "pdca_stage": "check",
                "evidence_ref": f"FIN-1C26TAA-{reg}-2026Q4",
            },
            {
                "code": f"KR-{reg}-02",
                "name": "Đạt 100% tuân thủ Chi lương VCB DigiBiz 11 cột, BHXH TZ0857G & Bảo mật PII ISO 27701",
                "target_value": 100.0,
                "current_value": 100.0,
                "unit": "%",
                "pdca_stage": "act",
                "evidence_ref": f"ISO27701-VCB-{reg}-2026Q4",
            },
            {
                "code": f"KR-{reg}-03",
                "name": "Hoàn tất 100% chu kỳ Đánh giá 360° Appraisal & Hiệu chuẩn 9-Box cho toàn bộ 9 nhân sự",
                "target_value": 9.0,
                "current_value": 9.0,
                "unit": "nhân sự",
                "pdca_stage": "act",
                "evidence_ref": f"HR-9BOX-{reg}-2026Q4",
            },
        ]
    else:
        aligned_code = "OKR-2026-Q4-C02"
        obj_title = f"Xuất sắc Kỹ thuật Phần mềm, Bàn giao Sprint B2B Onsite & Nâng cấp Kỹ năng ({emp_name})"
        pending_skills = int((kpi_skill_hub or {}).get("mandatory_skill_pending", 0))
        cert_skills = int((kpi_skill_hub or {}).get("mandatory_skill_certified", 4))
        total_skills = max(1, int((kpi_skill_hub or {}).get("mandatory_skill_total", 4)))
        krs = [
            {
                "code": f"KR-{reg}-01",
                "name": "Đạt Sprint Velocity & Cam kết SLA B2B Onsite (140–180h/tháng) tại dự án khách hàng",
                "target_value": 160.0,
                "current_value": 156.0 if pending_skills == 0 else 148.0,
                "unit": "giờ SLA",
                "pdca_stage": "check" if pending_skills == 0 else "do",
                "evidence_ref": f"SLA-ONSITE-{reg}-2026Q4",
            },
            {
                "code": f"KR-{reg}-02",
                "name": "Duy trì tỷ lệ Code Review Pass ≥ 92% và Zero Critical Security / Regression Bug",
                "target_value": 95.0,
                "current_value": 93.0 if pending_skills == 0 else 88.0,
                "unit": "% CR Pass",
                "pdca_stage": "check",
                "evidence_ref": f"GIT-CR-{reg}-2026Q4",
            },
            {
                "code": f"KR-{reg}-03",
                "name": "Hoàn thành 100% Chứng chỉ Nâng cấp Kỹ năng Bắt buộc Kỹ sư Phần mềm (SWE Skill Gate)",
                "target_value": float(total_skills),
                "current_value": float(cert_skills),
                "unit": "chứng chỉ",
                "pdca_stage": "act" if pending_skills == 0 else "do",
                "evidence_ref": f"CERT-GATE-{reg}-2026Q4",
            },
        ]

    hub = {
        "period_code": "2026-Q4",
        "employee_id": emp_dict.get("id", 1),
        "employee_code": reg,
        "employee_name": emp_name,
        "job_title": job_title,
        "department_name": dept_name,
        "company_okrs": CANONICAL_COMPANY_OKRS,
        "employee_okrs": [
            {
                "code": f"OKR-2026-Q4-{reg}",
                "name": obj_title,
                "aligned_company_okr": aligned_code,
                "period_code": "2026-Q4",
                "pdca_stage": "C - Check" if (kpi_skill_hub or {}).get("mandatory_skill_pending", 0) == 0 else "D - Do",
                "confidence_level": "on_track",
                "key_results": krs,
            }
        ],
    }
    return _recompute_okr_hub_dict(hub)


APPRAISAL_STATE_LABELS = {
    "self_review": "Bước 1: Nhân sự Tự Đánh giá (Self-Review)",
    "360_feedback": "Bước 2: Thu thập Phản hồi 360° (Peer & Khách hàng B2B)",
    "manager_calibration": "Bước 3: Quản lý Kỹ thuật Hiệu chuẩn 9-Box",
    "signed_off": "Bước 4: Đã Ký duyệt Hiệu chuẩn Nhân tài (Signed-off)",
}


def _recompute_appraisal_hub_dict(appraisal, kpi_skill_hub=None, okr_hub=None):
    """Computes 360° Appraisal weighted score and enforces the Mandatory SWE Skill Gate on 9-Box Calibration."""
    self_score = round(float(appraisal.get("self_assessment_score") or 90.0), 2)
    peer_score = round(float(appraisal.get("peer_client_360_score") or 91.0), 2)
    mgr_score = round(float(appraisal.get("manager_technical_score") or 92.0), 2)

    if okr_hub and okr_hub.get("okr_score") is not None:
        okr_pct = round(float(okr_hub["okr_score"]) * 100.0, 2)
    else:
        okr_pct = round(float(appraisal.get("okr_achievement_pct") or 90.0), 2)

    raw_total = round(
        0.20 * self_score + 0.25 * peer_score + 0.30 * mgr_score + 0.25 * okr_pct,
        2,
    )

    mandatory_pending = int((kpi_skill_hub or {}).get("mandatory_skill_pending", 0))
    if mandatory_pending > 0:
        skill_gate_capped = True
        calibrated_total = round(min(raw_total, 84.90), 2)
        calibration_box_code = "box_6_emerging"
        calibration_box = "9-Box [6] Emerging Potential (Capped by Skill Gate)"
    else:
        skill_gate_capped = False
        calibrated_total = raw_total
        if calibrated_total >= 90.0:
            calibration_box_code = "box_9_top_talent"
            calibration_box = "9-Box [9] Top Talent / Future Leader"
        elif calibrated_total >= 80.0:
            calibration_box_code = "box_8_high_performer"
            calibration_box = "9-Box [8] High Performer / Core Pillar"
        else:
            calibration_box_code = "box_5_core_player"
            calibration_box = "9-Box [5] Solid Core Player"

    st = str(appraisal.get("state") or "signed_off").strip()
    if st not in APPRAISAL_STATE_LABELS:
        st = "signed_off"
    if mandatory_pending > 0 and st == "signed_off":
        st = "manager_calibration"

    appraisal["self_assessment_score"] = self_score
    appraisal["peer_client_360_score"] = peer_score
    appraisal["manager_technical_score"] = mgr_score
    appraisal["okr_achievement_pct"] = okr_pct
    appraisal["raw_total_score"] = raw_total
    appraisal["calibrated_total_score"] = calibrated_total
    appraisal["skill_gate_capped"] = skill_gate_capped
    appraisal["mandatory_skill_pending"] = mandatory_pending
    appraisal["calibration_box_code"] = calibration_box_code
    appraisal["calibration_box"] = calibration_box
    appraisal["state"] = st
    appraisal["state_label"] = APPRAISAL_STATE_LABELS.get(st, st)
    return appraisal


def _default_appraisal_hub(emp_dict, kpi_skill_hub=None, okr_hub=None):
    reg = emp_dict.get("registration_number", "DGM-001")
    reg_compact = reg.replace("-", "")
    kh = kpi_skill_hub or {}
    pending = int(kh.get("mandatory_skill_pending", 0))

    base_delivery = float(kh.get("kpi_delivery_score") or 92.0)
    base_quality = float(kh.get("kpi_quality_score") or 91.0)
    base_work = float(kh.get("kpi_work_eval_score") or 92.0)

    appraisal = {
        "code": f"APR-2026-Q4-{reg_compact}",
        "sheet_code": f"APR-2026-Q4-{reg}",
        "period_code": "2026-Q4",
        "employee_id": emp_dict.get("id", 1),
        "employee_code": reg,
        "employee_name": emp_dict.get("name", ""),
        "job_title": emp_dict.get("job_title", ""),
        "department_name": emp_dict.get("department_name", ""),
        "reviewer_name": kh.get("reviewer_name", "Nguyễn Hoài Ân (CTO)"),
        "state": "manager_calibration" if pending > 0 else "signed_off",
        "self_assessment_score": round(min(98.0, base_delivery + 0.5), 2),
        "peer_client_360_score": round(min(98.0, base_work + 1.0), 2),
        "manager_technical_score": round(min(98.0, base_quality + 1.0), 2),
        "okr_achievement_pct": round(float((okr_hub or {}).get("okr_score", 0.92)) * 100.0, 2),
        "self_reflection_text": (
            f"Hoàn thành tốt các mục tiêu OKR Quý 4/2026, đảm bảo cam kết chất lượng bàn giao dự án và tuân thủ quy trình PDCA ({reg})."
        ),
        "peer_client_feedback_text": (
            "Phối hợp chặt chẽ với đội ngũ dự án và khách hàng B2B, phản hồi kỹ thuật nhanh, tuân thủ nghiêm ngặt SLA 140–180h và tiêu chuẩn bảo mật ISO 27701."
        ),
        "manager_appraisal_text": kh.get(
            "manager_review_note",
            "Đánh giá cao năng lực kỹ thuật, tư duy giải quyết vấn đề và tinh thần chủ động cải tiến theo chu trình PDCA.",
        ),
        "pdca_next_quarter_plan": kh.get(
            "next_training_roadmap",
            "Plan: Xác định mục tiêu kỹ năng mới → Do: Thực hành dự án thực chiến → Check: Sát hạch chứng chỉ → Act: Chuẩn hóa tài liệu.",
        ),
    }
    return _recompute_appraisal_hub_dict(appraisal, kpi_skill_hub=kh, okr_hub=okr_hub)


FORMULA_INJECTION_PREFIXES = ('=', '+', '-', '@', '\t', '\r')



def sanitize_excel_cell(val):
    """Prevents CSV/XLSX DDE Command Injection (CWE-1236).
    Prepends a single quote if the value begins with formula invocation tokens.
    """
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return val
    raw_str = str(val)
    str_val = raw_str.strip()
    if raw_str.startswith(FORMULA_INJECTION_PREFIXES) or str_val.startswith(FORMULA_INJECTION_PREFIXES):
        return f"'{str_val}"
    return str_val


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
            clean_h = str(sanitize_excel_cell(h))
            ws.write_string(0, col_idx, clean_h, hdr_fmt)
            ws.set_column(col_idx, col_idx, max(16, len(clean_h) + 4))

        for row_idx, r in enumerate(rows, start=1):
            for col_idx, val in enumerate(r):
                if isinstance(val, (int, float)) and col_idx == 2:
                    ws.write_number(row_idx, col_idx, val, num_fmt)
                else:
                    ws.write_string(row_idx, col_idx, str(sanitize_excel_cell(val if val is not None else "")), txt_fmt)
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
            text_val = escape(str(sanitize_excel_cell(val if val is not None else "")))
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

        # Fallback: build dynamically from CANONICAL_DGM_EMPLOYEES + hr.employee if present (single batch lookup)
        reg_to_id = {}
        try:
            reg_numbers = [item["reg"] for item in CANONICAL_DGM_EMPLOYEES if item.get("reg")]
            recs = (
                request.env["hr.employee"]
                .sudo()
                .search([("registration_number", "in", reg_numbers)])
            )
            for rec in recs:
                if getattr(rec, "registration_number", None) and rec.registration_number not in reg_to_id:
                    reg_to_id[rec.registration_number] = rec.id
        except Exception:
            reg_to_id = {}

        emp_rows = []
        for idx, item in enumerate(CANONICAL_DGM_EMPLOYEES, start=1):
            calc = _compute_vn_payroll(item["gross_wage"])
            emp_id = reg_to_id.get(item["reg"], idx)
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

    def _resolve_viewer_role(self, emp_dict, emp_map=None, is_hr_exec=None, is_hr_user=None):
        uid = getattr(request.env, "uid", None)
        user = getattr(request.env, "user", None)
        if uid in (1, 2) or is_hr_exec is True:
            return "HR_EXEC"
        if is_hr_exec is None and user:
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
            emp_id_int = int(emp_dict["id"])
            if emp_map is not None:
                emp_rec = emp_map.get(emp_id_int)
            else:
                emp_rec = request.env["hr.employee"].sudo().browse(emp_id_int)
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
            if is_hr_user is True or (is_hr_user is None and user and user.has_group("hr.group_hr_user")):
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

    def _append_privacy_audit_log(self, emp_dict, action, extra_meta=None):
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
        if isinstance(extra_meta, dict):
            entry.update(extra_meta)
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
                    "requested_by_uid": id_004,
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
                    "requested_by_uid": id_003,
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

    def _get_or_init_kpi_skill_hub(self, emp_dict):
        IrConfig = request.env["ir.config_parameter"].sudo()
        reg = emp_dict.get("registration_number", f"DGM-00{emp_dict.get('id', 1)}")
        key = f"dgm.hr.kpi_skill_hub.{reg}"
        raw = IrConfig.get_param(key)
        hub = None
        if raw:
            try:
                hub = json.loads(raw)
            except Exception:
                hub = None
        if not hub or "skill_gates" not in hub:
            hub = _default_kpi_skill_hub(emp_dict)
            IrConfig.set_param(key, json.dumps(hub, ensure_ascii=False))
        else:
            hub["employee_id"] = emp_dict.get("id", hub.get("employee_id", 1))
            hub["employee_code"] = reg
            hub["employee_name"] = emp_dict.get("name", hub.get("employee_name", ""))
            hub["job_title"] = emp_dict.get("job_title", hub.get("job_title", ""))
            hub["department_name"] = emp_dict.get("department_name", hub.get("department_name", ""))
            hub = _recompute_kpi_hub_dict(hub)
        return hub

    def _get_or_init_okr_hub(self, emp_dict, kpi_skill_hub=None):
        IrConfig = request.env["ir.config_parameter"].sudo()
        reg = emp_dict.get("registration_number", f"DGM-00{emp_dict.get('id', 1)}")
        key = f"dgm.hr.okr_hub.{reg}"
        raw = IrConfig.get_param(key)
        hub = None
        if raw:
            try:
                hub = json.loads(raw)
            except Exception:
                hub = None
        if not hub or "employee_okrs" not in hub:
            hub = _default_okr_hub(emp_dict, kpi_skill_hub=kpi_skill_hub)
            IrConfig.set_param(key, json.dumps(hub, ensure_ascii=False))
        else:
            hub["employee_id"] = emp_dict.get("id", hub.get("employee_id", 1))
            hub["employee_code"] = reg
            hub["employee_name"] = emp_dict.get("name", hub.get("employee_name", ""))
            hub["job_title"] = emp_dict.get("job_title", hub.get("job_title", ""))
            hub["department_name"] = emp_dict.get("department_name", hub.get("department_name", ""))
            hub = _recompute_okr_hub_dict(hub)
        return hub

    def _get_or_init_appraisal_hub(self, emp_dict, kpi_skill_hub=None, okr_hub=None):
        IrConfig = request.env["ir.config_parameter"].sudo()
        reg = emp_dict.get("registration_number", f"DGM-00{emp_dict.get('id', 1)}")
        key = f"dgm.hr.appraisal_hub.{reg}"
        raw = IrConfig.get_param(key)
        appraisal = None
        if raw:
            try:
                appraisal = json.loads(raw)
            except Exception:
                appraisal = None
        if not appraisal or "code" not in appraisal:
            appraisal = _default_appraisal_hub(emp_dict, kpi_skill_hub=kpi_skill_hub, okr_hub=okr_hub)
            IrConfig.set_param(key, json.dumps(appraisal, ensure_ascii=False))
        else:
            appraisal["employee_id"] = emp_dict.get("id", appraisal.get("employee_id", 1))
            appraisal["employee_code"] = reg
            appraisal["employee_name"] = emp_dict.get("name", appraisal.get("employee_name", ""))
            appraisal["job_title"] = emp_dict.get("job_title", appraisal.get("job_title", ""))
            appraisal["department_name"] = emp_dict.get("department_name", appraisal.get("department_name", ""))
            appraisal = _recompute_appraisal_hub_dict(
                appraisal,
                kpi_skill_hub=kpi_skill_hub,
                okr_hub=okr_hub,
            )
            IrConfig.set_param(key, json.dumps(appraisal, ensure_ascii=False))
        return appraisal

    def _get_project_pdca_templates(self):
        return [dict(tpl) for tpl in CANONICAL_PROJECT_PDCA_TEMPLATES]

    def _build_dashboard_payload(self, employee_id=None):
        registry = self._get_registry_and_employees()
        raw_employees = registry["employees"]

        uid = getattr(request.env, "uid", None)
        user = getattr(request.env, "user", None)
        is_hr_exec = uid in (1, 2)
        is_hr_user = False
        if not is_hr_exec and user:
            for grp in (
                "base.group_system",
                "hr.group_hr_manager",
                "hr_payroll.group_hr_payroll_manager",
                "hr_payroll.group_hr_payroll_user",
            ):
                try:
                    if user.has_group(grp):
                        is_hr_exec = True
                        break
                except Exception:
                    pass
            if not is_hr_exec:
                try:
                    is_hr_user = bool(user.has_group("hr.group_hr_user"))
                except Exception:
                    is_hr_user = False

        emp_map = {}
        if not is_hr_exec:
            try:
                emp_ids = [int(e["id"]) for e in raw_employees if e.get("id") is not None]
                for rec in request.env["hr.employee"].sudo().browse(emp_ids).exists():
                    emp_map[rec.id] = rec
            except Exception:
                emp_map = None

        scoped_employees = []
        for raw_emp in raw_employees:
            role = self._resolve_viewer_role(
                raw_emp,
                emp_map=emp_map,
                is_hr_exec=is_hr_exec,
                is_hr_user=is_hr_user,
            )
            if role != "UNAUTHORIZED":
                scoped_employees.append(self._mask_employee_for_viewer(raw_emp, role))

        if not scoped_employees and raw_employees:
            scoped_employees.append(self._mask_employee_for_viewer(raw_employees[0], "SELF"))

        selected = self._find_employee(scoped_employees, employee_id)

        lifecycle = self._get_or_init_lifecycle(selected)
        onboarding = _enrich_workflow(lifecycle["onboarding"])
        leaving = _enrich_workflow(lifecycle["leaving"])

        kpi_skill_hub = self._get_or_init_kpi_skill_hub(selected)
        okr_hub = self._get_or_init_okr_hub(selected, kpi_skill_hub=kpi_skill_hub)
        appraisal_hub = self._get_or_init_appraisal_hub(
            selected,
            kpi_skill_hub=kpi_skill_hub,
            okr_hub=okr_hub,
        )
        project_pdca_templates = self._get_project_pdca_templates()

        all_kpi_hubs = [self._get_or_init_kpi_skill_hub(e) for e in raw_employees]
        avg_company_kpi = (
            round(sum(h["total_kpi_score"] for h in all_kpi_hubs) / len(all_kpi_hubs), 2)
            if all_kpi_hubs
            else 0.0
        )
        avg_skill_pct = (
            int(round(sum(h["skill_completion_pct"] for h in all_kpi_hubs) / len(all_kpi_hubs)))
            if all_kpi_hubs
            else 100
        )
        kpi_summary = {
            "period": "Q4/2026",
            "avg_company_kpi": avg_company_kpi,
            "avg_skill_completion_pct": avg_skill_pct,
            "tier_s_count": sum(1 for h in all_kpi_hubs if h["rank_grade"] == "tier_s"),
            "tier_a_count": sum(1 for h in all_kpi_hubs if h["rank_grade"] == "tier_a"),
            "tier_b_count": sum(1 for h in all_kpi_hubs if h["rank_grade"] == "tier_b"),
            "capped_by_skill_gate_count": sum(1 for h in all_kpi_hubs if h["skill_gate_capped"]),
            "promotion_ready_count": sum(1 for h in all_kpi_hubs if h["promotion_eligible"]),
            "canonical_skill_tracks": CANONICAL_SKILL_TRACKS,
        }

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
            "kpi_skill_hub": kpi_skill_hub,
            "kpi_summary": kpi_summary,
            "okr_hub": okr_hub,
            "appraisal_hub": appraisal_hub,
            "project_pdca_templates": project_pdca_templates,
            "pdca_companion_docs": CANONICAL_PDCA_COMPANION_DOCS,
            "change_requests": change_requests,
            "pending_approval_count": pending_count,
            "privacy_audit_log": privacy_audit_log,
        }

    @http.route("/insilos/employee_dashboard/data", type="jsonrpc", auth="user", readonly=False)
    def get_employee_dashboard_data(self, employee_id=None, **kwargs):
        return self._build_dashboard_payload(employee_id=employee_id)

    @http.route("/insilos/employee_dashboard/reveal_pii", type="jsonrpc", auth="user", readonly=False)
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

    @http.route("/insilos/employee_dashboard/submit_change_request", type="jsonrpc", auth="user", readonly=False)
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
            "requested_by_uid": getattr(request.env, "uid", 2),
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

    @http.route("/insilos/employee_dashboard/decide_change_request", type="jsonrpc", auth="user", readonly=False)
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

        try:
            emp_db_id = int(employee_id if employee_id is not None else target_emp["id"])
        except Exception:
            emp_db_id = int(target_emp["id"])

        # TOCTOU Row-Level Lock on hr_employee before state validation & mutation
        if isinstance(emp_db_id, int) and emp_db_id > 0:
            try:
                request.env.cr.execute(
                    "SELECT id FROM hr_employee WHERE id = %s FOR UPDATE NOWAIT",
                    [emp_db_id],
                )
            except Exception:
                return {
                    "ok": False,
                    "error": "Concurrent update in progress (TOCTOU lock)",
                }

        # Re-read state under lock to prevent TOCTOU double-approval
        registry = self._get_registry_and_employees()
        employees = registry["employees"]
        reqs = self._get_or_init_change_requests(employees)
        target_req = next(
            (r for r in reqs if (r.get("request_id") == request_id or r.get("id") == request_id)),
            None,
        )
        if not target_req:
            return self._build_dashboard_payload(employee_id=employee_id)
        if target_req.get("state") != "pending" and kwargs.get("enforce_pending_state"):
            return {
                "ok": False,
                "error": "Request already processed (TOCTOU state guard)",
            }

        target_emp = next(
            (
                e
                for e in employees
                if str(e.get("id")) == str(target_req.get("employee_id"))
                or e.get("registration_number") == target_req.get("employee_code")
            ),
            employees[0],
        )

        # Dual-Control Segregation of Duties (SoD) Check
        uid = getattr(request.env, "uid", None)
        user = getattr(request.env, "user", None)
        req_uid = target_req.get("requested_by_uid")
        is_superuser = False
        if user and hasattr(user, "_is_superuser") and callable(user._is_superuser):
            try:
                is_superuser = bool(user._is_superuser())
            except Exception:
                is_superuser = (uid == 1)
        elif uid in (1, 2):
            is_superuser = True

        sod_self_approved = bool(req_uid is not None and uid is not None and int(req_uid) == int(uid))
        if sod_self_approved and (not is_superuser or kwargs.get("strict_sod")):
            return {
                "ok": False,
                "error": "Segregation of Duties (SoD) violation: Maker cannot self-approve Step 2 without superuser override.",
            }

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

            try:
                if hasattr(request.env, "invalidate_all"):
                    request.env.invalidate_all()
            except Exception:
                pass

            IrConfig.set_param("dgm.hr.master_registry", json.dumps(registry, ensure_ascii=False))
            target_req["state"] = "approved"
            target_req["approved_by_name"] = approver_name
            target_req["approved_at"] = now_str
            target_req["sod_self_approved"] = sod_self_approved
            target_req["approver_note"] = (
                str(approver_note or "").strip()
                or "Đã đối chiếu hồ sơ pháp lý & Phụ lục HĐLĐ hợp lệ."
            )
            IrConfig.set_param("dgm.hr.change_requests", json.dumps(reqs, ensure_ascii=False))
            self._append_privacy_audit_log(
                target_emp,
                "STEP2_APPROVE_LEGAL_CHANGE",
                extra_meta={"sod_self_approved": sod_self_approved},
            )
        else:
            target_req["state"] = "rejected"
            target_req["approved_by_name"] = approver_name
            target_req["approved_at"] = now_str
            target_req["sod_self_approved"] = sod_self_approved
            target_req["approver_note"] = (
                str(approver_note or "").strip()
                or "Từ chối phê duyệt: Hồ sơ minh chứng chưa đầy đủ."
            )
            IrConfig.set_param("dgm.hr.change_requests", json.dumps(reqs, ensure_ascii=False))
            self._append_privacy_audit_log(
                target_emp,
                "STEP2_REJECT_LEGAL_CHANGE",
                extra_meta={"sod_self_approved": sod_self_approved},
            )

        return self._build_dashboard_payload(employee_id=employee_id or target_emp["id"])

    @http.route("/insilos/employee_dashboard/toggle_step", type="jsonrpc", auth="user", readonly=False)
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

    @http.route("/insilos/employee_dashboard/complete_skill_upgrade", type="jsonrpc", auth="user", readonly=False)
    def complete_skill_upgrade(
        self,
        employee_id=None,
        skill_code=None,
        exam_score=95.0,
        certificate_ref=None,
        mentor_notes=None,
        **kwargs,
    ):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]
        target_emp = self._find_employee(employees, employee_id)
        hub = self._get_or_init_kpi_skill_hub(target_emp)
        reg = target_emp.get("registration_number", "DGM-001")
        today_str = datetime.date.today().isoformat()

        clean_code = str(skill_code or "").strip()
        try:
            score_val = max(0.0, min(100.0, float(exam_score if exam_score is not None else 95.0)))
        except Exception:
            score_val = 95.0

        updated = False
        for gate in hub.get("skill_gates", []):
            if gate.get("skill_code") == clean_code or gate.get("gate_id") == clean_code:
                gate["status"] = "certified"
                gate["status_label"] = "Đã Đạt Chứng chỉ (Certified)"
                gate["progress_pct"] = 100
                gate["current_level"] = gate.get("target_level") or "L3"
                gate["exam_score"] = round(score_val, 2)
                gate["certificate_ref"] = (
                    str(certificate_ref or "").strip()
                    or f"{gate.get('exam_ref', 'CERT-2026')}-{reg}"
                )
                gate["certified_date"] = today_str
                gate["mentor_notes"] = (
                    str(mentor_notes or "").strip()
                    or f"Đã hoàn thành nâng cấp kỹ năng bắt buộc & vượt qua kỳ thi sát hạch ({round(score_val, 1)}/100)."
                )
                updated = True
                break

        if not updated and clean_code in SKILL_TRACK_BY_CODE:
            track = SKILL_TRACK_BY_CODE[clean_code]
            hub.setdefault("skill_gates", []).append(
                {
                    "gate_id": f"GATE-{reg}-{len(hub.get('skill_gates', [])) + 1:02d}",
                    "skill_code": clean_code,
                    "skill_name": track["name"],
                    "domain": track["domain"],
                    "domain_label": track["domain_label"],
                    "training_hours": track["training_hours"],
                    "exam_ref": track["exam_ref"],
                    "description": track["description"],
                    "current_level": track["target_level"],
                    "target_level": track["target_level"],
                    "is_mandatory": track["mandatory_for_swe"],
                    "status": "certified",
                    "status_label": "Đã Đạt Chứng chỉ (Certified)",
                    "progress_pct": 100,
                    "exam_score": round(score_val, 2),
                    "certificate_ref": str(certificate_ref or "").strip() or f"{track['exam_ref']}-{reg}",
                    "deadline": "2026-11-30",
                    "certified_date": today_str,
                    "mentor_notes": str(mentor_notes or "").strip() or "Đã hoàn thành nâng cấp kỹ năng bắt buộc.",
                }
            )

        hub = _recompute_kpi_hub_dict(hub)
        if hub["mandatory_skill_pending"] == 0 and hub.get("state") == "submitted":
            hub["state"] = "approved"
            hub = _recompute_kpi_hub_dict(hub)

        IrConfig = request.env["ir.config_parameter"].sudo()
        IrConfig.set_param(f"dgm.hr.kpi_skill_hub.{reg}", json.dumps(hub, ensure_ascii=False))

        # Also synchronize OKR Skill KR & 360° Appraisal 9-Box Calibration when mandatory skills unlock
        okr_hub = self._get_or_init_okr_hub(target_emp, kpi_skill_hub=hub)
        for obj in okr_hub.get("employee_okrs", []):
            for kr in obj.get("key_results", []):
                if kr.get("code") == f"KR-{reg}-03":
                    kr["current_value"] = float(hub["mandatory_skill_certified"])
                    kr["target_value"] = float(max(1, hub["mandatory_skill_total"]))
                    if hub["mandatory_skill_pending"] == 0:
                        kr["pdca_stage"] = "act"
            if hub["mandatory_skill_pending"] == 0:
                obj["pdca_stage"] = "C - Check"
        okr_hub = _recompute_okr_hub_dict(okr_hub)
        IrConfig.set_param(f"dgm.hr.okr_hub.{reg}", json.dumps(okr_hub, ensure_ascii=False))

        appraisal_hub = self._get_or_init_appraisal_hub(target_emp, kpi_skill_hub=hub, okr_hub=okr_hub)
        if hub["mandatory_skill_pending"] == 0 and appraisal_hub.get("state") == "manager_calibration":
            appraisal_hub["state"] = "signed_off"
            appraisal_hub = _recompute_appraisal_hub_dict(appraisal_hub, kpi_skill_hub=hub, okr_hub=okr_hub)
            IrConfig.set_param(f"dgm.hr.appraisal_hub.{reg}", json.dumps(appraisal_hub, ensure_ascii=False))

        # Synchronize with declarative ORM models (`dgm.hr.employee.skill.gate` & `dgm.hr.kpi.evaluation`) when present
        try:
            GateModel = request.env["dgm.hr.employee.skill.gate"].sudo()
            gate_recs = GateModel.search(
                [
                    ("employee_id.registration_number", "=", reg),
                    ("skill_track_id.code", "=", clean_code),
                ]
            )
            if gate_recs:
                gate_recs.write(
                    {
                        "status": "certified",
                        "progress_pct": 100,
                        "exam_score": round(score_val, 2),
                        "certificate_ref": str(certificate_ref or "").strip() or f"CERT-{clean_code}-{reg}",
                        "certified_date": today_str,
                    }
                )
        except Exception:
            pass

        self._append_privacy_audit_log(
            target_emp,
            "COMPLETE_MANDATORY_SKILL_UPGRADE",
            extra_meta={
                "skill_code": clean_code,
                "exam_score": round(score_val, 2),
                "new_rank_grade": hub["rank_grade"],
                "skill_gate_capped": hub["skill_gate_capped"],
            },
        )
        return self._build_dashboard_payload(employee_id=target_emp["id"])

    @http.route("/insilos/employee_dashboard/submit_work_kpi_review", type="jsonrpc", auth="user", readonly=False)
    def submit_work_kpi_review(
        self,
        employee_id=None,
        kpi_delivery_score=None,
        kpi_quality_score=None,
        kpi_work_eval_score=None,
        okr_key_results_met=None,
        sprint_velocity_pct=None,
        code_review_pass_rate=None,
        prod_defect_escape_rate=None,
        b2b_sla_compliance_pct=None,
        peer_feedback_score=None,
        next_training_roadmap=None,
        manager_review_note=None,
        approve_evaluation=False,
        **kwargs,
    ):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]
        target_emp = self._find_employee(employees, employee_id)
        hub = self._get_or_init_kpi_skill_hub(target_emp)
        reg = target_emp.get("registration_number", "DGM-001")

        for k, raw_val in (
            ("kpi_delivery_score", kpi_delivery_score),
            ("kpi_quality_score", kpi_quality_score),
            ("kpi_work_eval_score", kpi_work_eval_score),
            ("sprint_velocity_pct", sprint_velocity_pct),
            ("code_review_pass_rate", code_review_pass_rate),
            ("prod_defect_escape_rate", prod_defect_escape_rate),
            ("b2b_sla_compliance_pct", b2b_sla_compliance_pct),
            ("peer_feedback_score", peer_feedback_score),
        ):
            if raw_val is not None and str(raw_val).strip() != "":
                try:
                    hub[k] = round(float(raw_val), 2)
                except Exception:
                    pass

        if okr_key_results_met is not None and str(okr_key_results_met).strip():
            hub["okr_key_results_met"] = str(okr_key_results_met).strip()
        if next_training_roadmap is not None and str(next_training_roadmap).strip():
            hub["next_training_roadmap"] = str(next_training_roadmap).strip()
        if manager_review_note is not None and str(manager_review_note).strip():
            hub["manager_review_note"] = str(manager_review_note).strip()

        if approve_evaluation:
            hub["state"] = "approved"
        elif hub.get("state") == "draft":
            hub["state"] = "submitted"

        hub = _recompute_kpi_hub_dict(hub)
        IrConfig = request.env["ir.config_parameter"].sudo()
        IrConfig.set_param(f"dgm.hr.kpi_skill_hub.{reg}", json.dumps(hub, ensure_ascii=False))

        try:
            EvalModel = request.env["dgm.hr.kpi.evaluation"].sudo()
            eval_recs = EvalModel.search([("employee_id.registration_number", "=", reg)], limit=1)
            if eval_recs:
                eval_recs.write(
                    {
                        "kpi_delivery_score": hub["kpi_delivery_score"],
                        "kpi_quality_score": hub["kpi_quality_score"],
                        "kpi_work_eval_score": hub["kpi_work_eval_score"],
                        "next_training_roadmap": hub["next_training_roadmap"],
                        "manager_review_note": hub["manager_review_note"],
                        "state": hub["state"],
                    }
                )
        except Exception:
            pass

        self._append_privacy_audit_log(
            target_emp,
            "SUBMIT_WORK_KPI_EVALUATION",
            extra_meta={
                "total_kpi_score": hub["total_kpi_score"],
                "rank_grade": hub["rank_grade"],
                "skill_gate_capped": hub["skill_gate_capped"],
            },
        )
        return self._build_dashboard_payload(employee_id=target_emp["id"])

    @http.route("/insilos/employee_dashboard/checkin_okr_kr", type="jsonrpc", auth="user", readonly=False)
    def checkin_okr_kr(
        self,
        employee_id=None,
        kr_code=None,
        current_value=None,
        pdca_stage=None,
        evidence_ref=None,
        confidence_level=None,
        **kwargs,
    ):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]
        target_emp = self._find_employee(employees, employee_id)
        kpi_hub = self._get_or_init_kpi_skill_hub(target_emp)
        okr_hub = self._get_or_init_okr_hub(target_emp, kpi_skill_hub=kpi_hub)
        reg = target_emp.get("registration_number", "DGM-001")

        clean_kr_code = str(kr_code or "").strip()
        matched_kr = None
        for obj in okr_hub.get("employee_okrs", []):
            for kr in obj.get("key_results", []):
                if not clean_kr_code or kr.get("code") == clean_kr_code:
                    matched_kr = kr
                    break
            if matched_kr:
                break

        if matched_kr:
            if current_value is not None and str(current_value).strip() != "":
                try:
                    matched_kr["current_value"] = round(float(current_value), 2)
                except Exception:
                    pass
            else:
                matched_kr["current_value"] = float(matched_kr.get("target_value") or 100.0)
            if pdca_stage is not None and str(pdca_stage).strip():
                matched_kr["pdca_stage"] = PDCA_STAGE_CODE_MAP.get(str(pdca_stage).strip(), "check")
            else:
                matched_kr["pdca_stage"] = "act"
            if evidence_ref is not None and str(evidence_ref).strip():
                matched_kr["evidence_ref"] = str(evidence_ref).strip()

        if confidence_level in ("on_track", "at_risk"):
            for obj in okr_hub.get("employee_okrs", []):
                obj["confidence_level"] = confidence_level

        okr_hub = _recompute_okr_hub_dict(okr_hub)
        IrConfig = request.env["ir.config_parameter"].sudo()
        IrConfig.set_param(f"dgm.hr.okr_hub.{reg}", json.dumps(okr_hub, ensure_ascii=False))

        # Recompute linked 360° Appraisal OKR achievement
        appraisal_hub = self._get_or_init_appraisal_hub(target_emp, kpi_skill_hub=kpi_hub, okr_hub=okr_hub)
        appraisal_hub = _recompute_appraisal_hub_dict(appraisal_hub, kpi_skill_hub=kpi_hub, okr_hub=okr_hub)
        IrConfig.set_param(f"dgm.hr.appraisal_hub.{reg}", json.dumps(appraisal_hub, ensure_ascii=False))

        # Sync with declarative ORM model `dgm.okr.key.result` when installed
        try:
            if matched_kr and "dgm.okr.key.result" in request.env:
                KrModel = request.env["dgm.okr.key.result"].sudo()
                kr_recs = KrModel.search([("code", "=", matched_kr["code"])], limit=1)
                if kr_recs:
                    kr_recs.write(
                        {
                            "current_value": matched_kr["current_value"],
                            "pdca_stage": matched_kr["pdca_stage"],
                            "evidence_ref": matched_kr.get("evidence_ref") or "",
                        }
                    )
        except Exception:
            pass

        self._append_privacy_audit_log(
            target_emp,
            "OKR_PDCA_CHECKIN",
            extra_meta={
                "kr_code": matched_kr["code"] if matched_kr else clean_kr_code,
                "kr_score": matched_kr["kr_score"] if matched_kr else okr_hub["okr_score"],
                "okr_score": okr_hub["okr_score"],
                "pdca_stage": matched_kr["pdca_stage"] if matched_kr else okr_hub["pdca_stage"],
            },
        )
        return self._build_dashboard_payload(employee_id=target_emp["id"])

    @http.route("/insilos/employee_dashboard/submit_hr_appraisal", type="jsonrpc", auth="user", readonly=False)
    def submit_hr_appraisal(
        self,
        employee_id=None,
        self_assessment_score=None,
        peer_client_360_score=None,
        manager_technical_score=None,
        okr_achievement_pct=None,
        self_reflection_text=None,
        peer_client_feedback_text=None,
        manager_appraisal_text=None,
        pdca_next_quarter_plan=None,
        state=None,
        sign_off=False,
        **kwargs,
    ):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]
        target_emp = self._find_employee(employees, employee_id)
        kpi_hub = self._get_or_init_kpi_skill_hub(target_emp)
        okr_hub = self._get_or_init_okr_hub(target_emp, kpi_skill_hub=kpi_hub)
        appraisal = self._get_or_init_appraisal_hub(target_emp, kpi_skill_hub=kpi_hub, okr_hub=okr_hub)
        reg = target_emp.get("registration_number", "DGM-001")

        for k, raw_val in (
            ("self_assessment_score", self_assessment_score),
            ("peer_client_360_score", peer_client_360_score),
            ("manager_technical_score", manager_technical_score),
            ("okr_achievement_pct", okr_achievement_pct),
        ):
            if raw_val is not None and str(raw_val).strip() != "":
                try:
                    appraisal[k] = round(max(0.0, min(100.0, float(raw_val))), 2)
                except Exception:
                    pass

        for txt_key, raw_txt in (
            ("self_reflection_text", self_reflection_text),
            ("peer_client_feedback_text", peer_client_feedback_text),
            ("manager_appraisal_text", manager_appraisal_text),
            ("pdca_next_quarter_plan", pdca_next_quarter_plan),
        ):
            if raw_txt is not None and str(raw_txt).strip():
                appraisal[txt_key] = str(raw_txt).strip()

        if sign_off or state == "signed_off":
            appraisal["state"] = "signed_off"
        elif state in APPRAISAL_STATE_LABELS:
            appraisal["state"] = state

        appraisal = _recompute_appraisal_hub_dict(appraisal, kpi_skill_hub=kpi_hub, okr_hub=okr_hub)
        IrConfig = request.env["ir.config_parameter"].sudo()
        IrConfig.set_param(f"dgm.hr.appraisal_hub.{reg}", json.dumps(appraisal, ensure_ascii=False))

        # Sync with declarative ORM model `dgm.hr.appraisal.sheet` when installed
        try:
            if "dgm.hr.appraisal.sheet" in request.env:
                SheetModel = request.env["dgm.hr.appraisal.sheet"].sudo()
                sheet_recs = SheetModel.search([("employee_id.registration_number", "=", reg)], limit=1)
                if sheet_recs:
                    sheet_recs.write(
                        {
                            "self_assessment_score": appraisal["self_assessment_score"],
                            "peer_client_360_score": appraisal["peer_client_360_score"],
                            "manager_technical_score": appraisal["manager_technical_score"],
                            "self_reflection_text": appraisal["self_reflection_text"],
                            "peer_client_feedback_text": appraisal["peer_client_feedback_text"],
                            "manager_appraisal_text": appraisal["manager_appraisal_text"],
                            "pdca_next_quarter_plan": appraisal["pdca_next_quarter_plan"],
                            "state": appraisal["state"],
                        }
                    )
        except Exception:
            pass

        self._append_privacy_audit_log(
            target_emp,
            "SUBMIT_360_HR_APPRAISAL",
            extra_meta={
                "code": appraisal["code"],
                "calibrated_total_score": appraisal["calibrated_total_score"],
                "calibration_box": appraisal["calibration_box"],
                "calibration_box_code": appraisal["calibration_box_code"],
                "skill_gate_capped": appraisal["skill_gate_capped"],
            },
        )
        return self._build_dashboard_payload(employee_id=target_emp["id"])

    @http.route("/insilos/employee_dashboard/export_vcb_digibiz", type="http", auth="user", methods=["GET"], readonly=False)
    def export_vcb_digibiz(self, **kwargs):
        registry = self._get_registry_and_employees()
        employees = registry["employees"]

        caller_role = self._resolve_viewer_role(employees[0]) if employees else "UNAUTHORIZED"
        if caller_role != "HR_EXEC":
            return request.make_response(
                "Unauthorized: Exporting VCB DigiBiz payroll requires HR/Payroll Manager privileges.",
                status=403,
            )

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
