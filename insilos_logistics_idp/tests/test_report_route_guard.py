from pathlib import Path
import re
from xml.etree import ElementTree


MODULE = Path(__file__).resolve().parents[1]


def test_qweb_pdf_report_routes_enforce_read_access():
    root = ElementTree.parse(MODULE / 'reports' / 'is_logistics_idp_report_actions.xml').getroot()
    reports = [
        {
            field.attrib['name']: (field.text or '').strip()
            for field in record.findall('field')
        }
        for record in root.findall("record[@model='ir.actions.report']")
        if record.findtext("field[@name='report_type']") == 'qweb-pdf'
    ]
    assert reports
    source = (MODULE / 'controllers' / 'report.py').read_text(encoding='utf-8')
    for report in reports:
        guard = re.compile(
            rf"reportname == {re.escape(repr(report['report_name']))}[\s\S]*?"
            rf"request\.env\[{re.escape(repr(report['model']))}\]\.browse[\s\S]*?"
            r"records\.check_access\('read'\)[\s\S]*?"
            r"records\.check_access_rule\('read'\)",
        )
        assert guard.search(source)
    assert (MODULE / 'controllers' / '__init__.py').read_text(encoding='utf-8') == 'from . import report\n'
    assert 'from . import controllers' in (MODULE / '__init__.py').read_text(encoding='utf-8')


def test_release_ready_report_requires_activated_immutable_screening_or_approved_override():
    controller = (MODULE / 'controllers' / 'report.py').read_text(encoding='utf-8')
    model = (MODULE / 'models' / 'logistics_idp.py').read_text(encoding='utf-8')
    assert "case.state in ('ready', 'completed') or case.verdict == 'pass'" in controller
    assert "_has_governed_screening_result(require_release=True)" in controller
    guard = re.compile(
        r"def _has_governed_screening_result[\s\S]*?"
        r"item\.code == 'RESTRICTED_PARTY_SCREENING' and item\.audit_input_hash[\s\S]*?"
        r"self\._screening_source_is_activated\(item\.policy_source_id\)[\s\S]*?"
        r"item\.state == 'approved'[\s\S]*?"
        r"item\.verdict == 'pass' or item in approved",
    )
    assert guard.search(model)
