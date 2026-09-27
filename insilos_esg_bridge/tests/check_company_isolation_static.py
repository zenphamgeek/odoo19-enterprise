from pathlib import Path
import xml.etree.ElementTree as ET


MODULE = Path(__file__).resolve().parents[1]
RULES = {
    'model_is_esg_chemical_impact': "[('company_id', 'in', company_ids + [False])]",
    'model_is_esg_freight_carbon': "[('company_id', 'in', company_ids + [False])]",
    'model_is_esg_cbam_advisor': "[('company_id', 'in', company_ids)]",
}


def test_company_bound_bridge_records_have_company_rules():
    root = ET.parse(MODULE / 'security' / 'security_groups.xml').getroot()
    found = {
        record.find("field[@name='model_id']").attrib['ref']:
        record.find("field[@name='domain_force']").text
        for record in root.findall("record[@model='ir.rule']")
        if record.attrib['id'] in {
            'is_esg_chemical_impact_company_rule',
            'is_esg_freight_carbon_company_rule',
            'is_esg_cbam_advisor_company_rule',
        }
    }
    assert found == RULES
    cbam_model = (MODULE / 'models' / 'is_esg_cbam_advisor.py').read_text(encoding='utf-8')
    assert "company_id = fields.Many2one('res.company', required=True" in cbam_model
