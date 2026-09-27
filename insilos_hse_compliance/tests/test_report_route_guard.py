from pathlib import Path
import xml.etree.ElementTree as ET


MODULE = Path(__file__).resolve().parents[1]
REPORT_NAMES = {
    'insilos_hse_compliance.report_hse_product_permit_doc',
    'insilos_hse_compliance.report_hse_chemical_safety_sop_doc',
    'insilos_hse_compliance.report_hse_legal_compliance_audit_doc',
    'insilos_hse_compliance.report_hse_safety_data_sheet_doc',
}


def test_hse_qweb_pdf_generic_route_enforces_read_access():
    actions = ET.parse(MODULE / 'reports' / 'is_hse_report_actions.xml').getroot()
    report_names = {
        record.find("field[@name='report_name']").text
        for record in actions.findall("record[@model='ir.actions.report']")
        if record.find("field[@name='report_type']").text == 'qweb-pdf'
    }
    source = (MODULE / 'controllers' / 'report.py').read_text(encoding='utf-8')
    assert report_names == REPORT_NAMES
    assert all(repr(report_name) in source for report_name in report_names)
    assert "all(id_.isdigit() for id_ in ids)" in source
    assert "_get_report_from_name(reportname).model" in source
    assert "records.check_access('read')" in source
    assert "records.check_access_rule('read')" in source
    permit_template = (MODULE / 'reports' / 'is_hse_report_templates.xml').read_text(encoding='utf-8')
    assert 'Trạng thái bản ghi nội bộ:' in permit_template
    sop_template = permit_template
    assert 'BẢN DỰ THẢO NỘI BỘ — KHÔNG DÙNG THAY THẾ SDS HOẶC QUY TRÌNH KHẨN CẤP ĐƯỢC PHÊ DUYỆT.' in sop_template
    assert 'theo SDS và quy trình khẩn cấp đã được phê duyệt cho đúng hóa chất này.' in sop_template
    assert 'BẢN RÀ SOÁT NỘI BỘ — KHÔNG PHẢI KẾT LUẬN TUÂN THỦ PHÁP LÝ' in permit_template
    assert 'Nguồn:' in permit_template
    assert 'Bằng chứng nội bộ:' in permit_template
    assert 'Găng tay chuyên dụng chống hóa chất (Nitrile/Butyl).' not in sop_template
    assert 'Sử dụng bình bọt Foam, bột khô ABC hoặc CO2.' not in sop_template
    assert 'from . import report' in (MODULE / 'controllers' / '__init__.py').read_text(encoding='utf-8')


def test_non_draft_legal_register_report_requires_governed_checked_sources():
    source = (MODULE / 'controllers' / 'report.py').read_text(encoding='utf-8')
    assert "reportname == 'insilos_hse_compliance.report_hse_legal_compliance_audit_doc'" in source
    assert "record.state != 'draft'" in source
    assert "not obligation.provision_id" in source
    assert "not obligation.document_id.has_governed_provenance()" in source
    assert "obligation.compliance_status == 'compliant'" in source
    assert "not obligation.compliance_approved_by_id" in source
    assert "not register.obligation_ids or unsupported" in source
    assert 'Non-draft internal HSE reviews require governed sources and approved compliance assessments.' in source
    assert 'SDS export is unavailable until supplier source, version, immutable content hash' in source


def test_hse_onboarding_and_review_views_are_internal_only():
    onboarding = (MODULE / 'views' / 'is_hse_onboarding_views.xml').read_text(encoding='utf-8')
    legal_register = (MODULE / 'views' / 'is_hse_legal_register_views.xml').read_text(encoding='utf-8')
    permits = (MODULE / 'views' / 'is_hse_product_permit_views.xml').read_text(encoding='utf-8')
    assert 'Không gian theo dõi nội bộ' in onboarding
    assert 'đối chiếu SDS nguồn trước khi sử dụng' in onboarding
    assert 'không thay thế kết luận tuân thủ hoặc hồ sơ nộp cơ quan' in onboarding
    assert 'Enterprise Ready' not in onboarding
    assert 'lập biên bản kiểm toán phục vụ thanh tra' not in onboarding
    assert 'Print Internal HSE Review' in legal_register
    assert 'Mark Internal Review Complete' in legal_register
    assert 'Print HSE Evaluation Report' not in legal_register
    assert 'Print Internal Permit Record' in permits
    assert 'Internal Permit &amp; Certificate Metadata' in permits
    assert 'Draft-only records; no validation or authority confirmation.' in permits
    assert 'Manage Operating Licenses &amp; Compliance Certificates' not in permits
    assert 'Register and manage regulatory licenses' not in permits
    assert 'Internal Record Status' in permits
    assert 'Recorded Issue &amp; Expiry Metadata' in permits
    assert 'filter_valid' not in permits
    assert 'filter_expiring_soon' not in permits
    assert 'filter_expired' not in permits
    assert 'search_default_filter_valid' not in permits
    assert "state == 'valid'" not in permits
    assert "state == 'expiring_soon'" not in permits
    assert "state == 'expired'" not in permits
    assert 'statusbar_visible' not in permits
    assert 'default_group_by="state"' not in permits
    assert 'Print Permit Certificate' not in permits
