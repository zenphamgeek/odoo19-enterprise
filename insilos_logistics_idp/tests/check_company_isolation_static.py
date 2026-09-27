from pathlib import Path
import xml.etree.ElementTree as ET


MODULE = Path(__file__).resolve().parents[1]
RULES = {
    'model_logistics_idp_inbound_job': "[('company_id', 'in', company_ids)]",
    'model_logistics_idp_mes_reference': "[('case_id.company_id', 'in', company_ids)]",
    'model_logistics_idp_extracted_line': "[('company_id', 'in', company_ids)]",
}


def test_late_added_logistics_company_rules_are_global_and_exact():
    root = ET.parse(MODULE / 'security' / 'logistics_idp_security.xml').getroot()
    found = {
        record.find("field[@name='model_id']").attrib['ref']:
        record.find("field[@name='domain_force']").text
        for record in root.findall("record[@model='ir.rule']")
        if record.attrib['id'] in {
            'rule_inbound_job_company', 'rule_mes_reference_company', 'rule_extracted_line_company',
        }
        and record.find("field[@name='global']").attrib.get('eval') == 'True'
    }
    assert found == RULES
