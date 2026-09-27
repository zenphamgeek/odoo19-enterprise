from pathlib import Path
import xml.etree.ElementTree as ET


MODULE = Path(__file__).resolve().parents[1]
RULES = {
    'model_is_chemical_compliance_dossier': "[('importer_company_id', 'in', company_ids)]",
    'model_is_chemical_compliance_dossier_line': "[('dossier_id.importer_company_id', 'in', company_ids)]",
    'model_is_chemical_compliance_exception': "[('dossier_id.importer_company_id', 'in', company_ids)]",
    'model_is_chemical_material_mapping': "[('company_id', 'in', company_ids)]",
    'model_is_chemical_permit_quota': "[('company_id', 'in', company_ids)]",
    'model_is_chemical_permit_quota_line': "[('quota_id.company_id', 'in', company_ids)]",
    'model_is_chemical_purpose_of_use': "[('company_id', 'in', company_ids)]",
    'model_is_chemical_usage_tracking': "[('company_id', 'in', company_ids)]",
    'model_is_chemical_usage_tracking_line': "[('tracking_id.company_id', 'in', company_ids)]",
}


def test_chemical_company_bound_records_have_global_rules():
    root = ET.parse(MODULE / 'security' / 'chemical_company_rules.xml').getroot()
    found = {
        record.find("field[@name='model_id']").attrib['ref']:
        record.find("field[@name='domain_force']").text
        for record in root.findall("record[@model='ir.rule']")
        if record.find("field[@name='global']").attrib.get('eval') == 'True'
    }
    assert found == RULES


def test_company_rules_are_loaded_and_stock_sync_is_explicitly_scoped():
    manifest = (MODULE / '__manifest__.py').read_text(encoding='utf-8')
    assert "'security/chemical_company_rules.xml'" in manifest
    usage = (MODULE / 'models' / 'is_chemical_usage_tracking.py').read_text(encoding='utf-8')
    assert usage.count("('company_id', '=', self.company_id.id)") == 2
    quota = (MODULE / 'models' / 'is_chemical_permit_quota.py').read_text(encoding='utf-8')
    assert 'dossier.importer_company_id != self.company_id' in quota
    assert 'dossier_line.dossier_id != dossier' in quota


def test_cross_company_relationships_are_rejected_or_explicitly_scoped():
    dossier = (MODULE / 'models' / 'is_chemical_compliance_dossier.py').read_text(encoding='utf-8')
    assert "@api.constrains('importer_company_id', 'purchase_order_id', 'case_id', 'picking_id', 'usage_tracking_id')" in dossier
    assert "@api.constrains('dossier_id', 'purpose_of_use_id', 'permit_id')" in dossier
    usage = (MODULE / 'models' / 'is_chemical_usage_tracking.py').read_text(encoding='utf-8')
    assert "@api.constrains('company_id', 'facility_id', 'purpose_of_use_ids')" in usage
    assert "@api.constrains('tracking_id', 'purpose_of_use_id')" in usage
    purpose = (MODULE / 'models' / 'is_chemical_purpose_of_use.py').read_text(encoding='utf-8')
    assert "@api.constrains('company_id', 'facility_id')" in purpose
    mapping = (MODULE / 'models' / 'is_chemical_material_mapping.py').read_text(encoding='utf-8')
    assert "@api.constrains('company_id', 'purpose_of_use_id')" in mapping
    bridge = (MODULE / 'models' / 'logistics_idp_bridge.py').read_text(encoding='utf-8')
    assert "('company_id', '=', self.company_id.id)" in bridge
    assert "('company_id', '=', dossier.importer_company_id.id)" in bridge


def test_verified_mapping_and_erp_usage_sources_are_immutable():
    mapping = (MODULE / 'models' / 'is_chemical_material_mapping.py').read_text(encoding='utf-8')
    assert '_MAPPING_VERIFICATION_CAPABILITY = object()' in mapping
    assert 'A different Chemical Compliance Manager must review this mapping.' in mapping
    assert '_chemical_mapping_verification=_MAPPING_VERIFICATION_CAPABILITY' in mapping
    assert 'Verified mappings are immutable' in mapping
    usage = (MODULE / 'models' / 'is_chemical_usage_tracking.py').read_text(encoding='utf-8')
    assert "source_stock_move_id = fields.Many2one('stock.move'" in usage
    assert "('chemical_usage_source_stock_move_unique', 'unique(source_stock_move_id)'" in usage
    assert '_chemical_usage_sync=_USAGE_SYNC_CAPABILITY' in usage
    assert "'source_stock_move_id': move.id" in usage
    assert 'ERP-synchronized usage lines are immutable' in usage
    dossier = (MODULE / 'models' / 'is_chemical_compliance_dossier.py').read_text(encoding='utf-8')
    assert 'NSW payload generation is unavailable until governed legal sources' in dossier
