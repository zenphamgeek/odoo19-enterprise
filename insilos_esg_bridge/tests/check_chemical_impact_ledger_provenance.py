"""Run without an ORM or database: python3 <this file>."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


class ValidationError(Exception):
    pass


class ChemicalImpactLedgerProvenanceTest(unittest.TestCase):
    def test_unverified_chemical_impact_never_posts_or_overwrites_ledger(self):
        path = Path(__file__).resolve().parents[1] / 'models/is_esg_chemical_impact.py'
        model = next(node for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef))
        method = next(node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == 'action_post_to_esg_scope1')
        method.decorator_list = []
        namespace = {'ValidationError': ValidationError, '_': lambda value: value}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        for existing_entry in (False, 42):
            record = SimpleNamespace(esg_other_emission_id=existing_entry)
            with self.subTest(existing_entry=existing_entry), self.assertRaisesRegex(ValidationError, 'verified factors'):
                namespace['action_post_to_esg_scope1'](record)
            self.assertEqual(record.esg_other_emission_id, existing_entry)


if __name__ == '__main__':
    unittest.main()
