from pathlib import Path
import xml.etree.ElementTree as ET


MODULE = Path(__file__).resolve().parents[1]
MODELS = {
    'model_is_hse_facility',
    'model_is_hse_legal_register',
    'model_is_hse_obligation',
    'model_is_hse_product_permit',
}


def test_company_bound_hse_models_are_isolated():
    rules = ET.parse(MODULE / 'security' / 'hse_company_rules.xml').getroot()
    isolated = {
        record.find("field[@name='model_id']").attrib['ref']
        for record in rules.findall("record[@model='ir.rule']")
        if record.find("field[@name='global']").attrib.get('eval') == 'True'
        and record.find("field[@name='domain_force']").text == "[('company_id', 'in', company_ids)]"
    }
    assert isolated == MODELS


def test_company_rules_are_loaded_and_register_rejects_cross_company_facility():
    manifest = (MODULE / '__manifest__.py').read_text(encoding='utf-8')
    assert "'security/hse_company_rules.xml'" in manifest
    register = (MODULE / 'models' / 'is_hse_legal_register.py').read_text(encoding='utf-8')
    assert 'def _check_facility_company(self):' in register
    assert 'register.facility_id.company_id != register.company_id' in register
    events = (MODULE / 'models' / 'is_hse_compliance_event.py').read_text(encoding='utf-8')
    assert "related='affected_facility_id.company_id', store=True" in events
    assert 'model_is_hse_compliance_event' in (MODULE / 'security' / 'hse_company_rules.xml').read_text(encoding='utf-8')
    obligations = (MODULE / 'models' / 'is_hse_legal_register.py').read_text(encoding='utf-8')
    assert "@api.constrains('company_id', 'evidence_attachment_ids')" in obligations
    assert 'Evidence attachments must belong to the obligation company.' in obligations
    permits = (MODULE / 'models' / 'is_hse_product_permit.py').read_text(encoding='utf-8')
    assert "@api.constrains('company_id', 'attachment_ids')" in permits
    assert 'Permit attachments must belong to the permit company.' in permits
