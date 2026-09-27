"""Run without an ORM or database: python3 <this file>."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


class ValidationError(Exception):
    pass


class FreightLedgerProvenanceTest(unittest.TestCase):
    def load_method(self, name):
        path = Path(__file__).resolve().parents[1] / 'models/is_esg_freight_carbon.py'
        tree = ast.parse(path.read_text())
        model = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        method = next(node for node in model.body
                      if isinstance(node, ast.FunctionDef) and node.name == name)
        method.decorator_list = []
        namespace = {'ValidationError': ValidationError, '_': lambda value: value}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        return namespace[name]

    def test_rpc_and_sudo_cannot_link_draft_estimates_to_a_ledger(self):
        path = Path(__file__).resolve().parents[1] / 'models/is_esg_freight_carbon.py'
        model = next(node for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef))
        methods = {node.name: node for node in model.body if isinstance(node, ast.FunctionDef)}
        for name in ('create', 'write'):
            with self.subTest(method=name):
                source = ast.unparse(methods[name])
                self.assertIn("'esg_other_emission_id'", source)
                self.assertIn('raise ValidationError', source)

    def test_unverified_estimates_never_access_or_modify_ledger(self):
        post = self.load_method('action_post_to_esg_ledger')
        for existing_entry in (False, 42):
            with self.subTest(existing_entry=existing_entry):
                # No env: any ledger access fails instead of silently passing.
                record = SimpleNamespace(ensure_one=lambda: None,
                                         esg_other_emission_id=existing_entry)
                with self.assertRaisesRegex(ValidationError, 'provenance'):
                    post(record)
                self.assertEqual(record.esg_other_emission_id, existing_entry)

    def test_fractional_activity_and_paperless_estimates_remain_local(self):
        compute = self.load_method('_compute_carbon_metrics')
        post = self.load_method('action_post_to_esg_ledger')
        for pages in (0, 10, 100000):
            with self.subTest(pages=pages):
                record = SimpleNamespace(
                    ensure_one=lambda: None,
                    esg_other_emission_id=False,
                    cargo_weight_ton=2.5,
                    estimated_distance_km=10.25,
                    emission_factor_kg_per_tkm=0.015,
                    paperless_pages_processed=pages,
                )
                compute([record])
                # Existing local estimate, not a verified posting factor.
                self.assertAlmostEqual(record.gross_freight_emissions_kg_co2e, 0.384375)
                self.assertAlmostEqual(record.gross_freight_emissions_t_co2e, 0.000384375)
                self.assertAlmostEqual(record.paperless_carbon_offset_kg, pages * 0.009)
                self.assertAlmostEqual(record.net_logistics_carbon_kg_co2e,
                                       max(0.0, 0.384375 - pages * 0.009))
                with self.assertRaisesRegex(ValidationError, 'provenance'):
                    post(record)
                self.assertFalse(record.esg_other_emission_id)


if __name__ == '__main__':
    unittest.main()
