"""Run directly with Python; synthetic fixtures, no ORM or DB."""
import ast
from copy import deepcopy
from datetime import date
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nsw_builder', ROOT / 'services/nsw_payload_builder.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Builder = module.NSWChemicalPayloadBuilder


def fixture():
    return NS(
        name='TEST-1', dossier_type='nsw_declaration', jurisdiction='VN',
        nsw_procedure_code='TEST-PROCEDURE', invoice_number='TEST-INVOICE',
        invoice_date=date(2026, 1, 2), customs_office_code='TEST-OFFICE',
        port_of_loading='Test loading', port_of_discharge='Test discharge',
        importer_company_id=NS(vat='TEST-TAX', name='Test importer', street='Test address', phone=False, email=False),
        partner_id=NS(name='Test exporter', street='Test exporter address', country_id=NS(code='SG')),
        line_ids=[NS(trade_name='Test chemical', chemical_substance_id=False, cas_number='108-88-3',
                     hs_code='29023000', concentration_percentage=99.0, net_weight_kg=200.0,
                     package_type='Test container', quantity=2, intended_use='Test use',
                     regulatory_status='nsw_required', permit_id=False)],
    )


class TestNSW(unittest.TestCase):
    def test_valid_json_xml(self):
        dossier = fixture()
        payload = Builder.build_json_payload(dossier)
        self.assertEqual(payload['header']['importer']['tax_code'], 'TEST-TAX')
        self.assertEqual(payload['header']['total_net_weight_kg'], 200)
        self.assertEqual(payload['chemical_items'][0]['package_quantity'], 2)
        xml = ET.fromstring(Builder.build_xml_payload(dossier))
        self.assertEqual(xml.findtext('Header/importer/address'), 'Test address')

    def test_missing_inputs_block_both_formats(self):
        paths = ['nsw_procedure_code', 'invoice_number', 'invoice_date', 'jurisdiction',
                 'customs_office_code', 'port_of_loading', 'port_of_discharge',
                 'importer_company_id', 'partner_id', 'line_ids',
                 'importer_company_id.vat', 'importer_company_id.street',
                 'partner_id.name', 'partner_id.street', 'partner_id.country_id',
                 'line.trade_name', 'line.cas_number', 'line.hs_code',
                 'line.package_type', 'line.intended_use']
        for path in paths:
            for missing in (False, '', '   '):
                if path in ('importer_company_id', 'partner_id', 'line_ids', 'partner_id.country_id') and missing:
                    continue
                dossier = fixture()
                target = dossier
                parts = path.split('.')
                if parts[0] == 'line':
                    target = dossier.line_ids[0]
                elif len(parts) > 1:
                    target = getattr(dossier, parts[0])
                setattr(target, parts[-1], missing)
                for build in (Builder.build_json_payload, Builder.build_xml_payload):
                    with self.subTest(path=path, missing=missing, build=build.__name__):
                        with self.assertRaises(ValueError):
                            build(dossier)

    def test_numeric_boundaries(self):
        for field in ('quantity', 'net_weight_kg', 'concentration_percentage'):
            for value in (0, -1, float('nan'), float('inf'), True, '1'):
                dossier = fixture()
                setattr(dossier.line_ids[0], field, value)
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    Builder.build_json_payload(dossier)
        dossier = fixture()
        dossier.line_ids[0].concentration_percentage = 101
        with self.assertRaises(ValueError):
            Builder.build_json_payload(dossier)

    def test_compliance_data_check_has_workflow_guard(self):
        tree = ast.parse((ROOT / 'models/is_chemical_compliance_dossier.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'action_run_compliance_data_check')
        call = method.body[1].value
        self.assertEqual(call.func.attr, '_check_transition')
        self.assertEqual(call.args[0].elts[0].value, 'draft')
        self.assertEqual(call.args[0].elts[1].value, 'evaluating')
        self.assertEqual(call.args[0].elts[2].value, 'dossier_ready')

    def test_dossier_has_no_unverified_official_transitions(self):
        source = (ROOT / 'models/is_chemical_compliance_dossier.py').read_text()
        tree = ast.parse(source)
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ChemicalComplianceDossier')
        method_names = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
        self.assertFalse({'action_submit_nsw', 'action_approve_dossier', 'action_customs_clearance'} & method_names)
        states = next(node for node in cls.body if isinstance(node, ast.Assign) and node.targets[0].id == 'state')
        values = {item.elts[0].value for item in states.value.args[0].elts}
        self.assertFalse({'submitted_nsw', 'approved', 'customs_cleared'} & values)

    def test_evaluation_context_and_stale_procedure(self):
        tree = ast.parse((ROOT / 'models/is_chemical_compliance_dossier.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        method = deepcopy(next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'action_evaluate_obligations'))
        method.decorator_list = []
        namespace = {
            'ValidationError': ValueError, '_': lambda text: text,
            'ChemicalComplianceDossier': object,
            'ChemicalComplianceDossierLine': object,
            'super': lambda cls, rec: NS(write=lambda vals: rec.__dict__.update(vals)),
        }
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<dossier-method>', 'exec'), namespace)
        calls = []

        class Rules(list):
            ids = []
            def filtered(self, predicate):
                return self
            def mapped(self, field):
                return []

        class Lines(list):
            def mapped(self, field):
                return Rules()

        def evaluate(**kwargs):
            calls.append(kwargs)
            return Rules()

        dossier = fixture()
        dossier.line_ids = Lines(dossier.line_ids)
        dossier.env = {'is.chemical.regulatory.rule': NS(evaluate_chemical_obligations=evaluate)}
        dossier._check_transition = lambda states: None
        dossier._compute_risk_flags = lambda: None
        dossier.jurisdiction = 'SG'
        run = namespace['action_evaluate_obligations']
        run(dossier)
        self.assertEqual(calls[0]['jurisdiction'], 'SG')
        self.assertEqual(calls[0]['effective_date'], date(2026, 1, 2))
        self.assertFalse(dossier.nsw_procedure_code)
        dossier.invoice_date = False
        with self.assertRaises(ValueError):
            run(dossier)
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
