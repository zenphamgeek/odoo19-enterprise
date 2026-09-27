"""Run without an ORM or database: python3 <this file>."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


class ValidationError(Exception):
    pass


class OrchestrationEvidenceTest(unittest.TestCase):
    def test_refusal_preserves_existing_state_without_model_access(self):
        path = Path(__file__).resolve().parents[1] / 'models/logistics_idp_case_esg.py'
        tree = ast.parse(path.read_text())
        model = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        method = next(node for node in model.body
                      if isinstance(node, ast.FunctionDef)
                      and node.name == 'action_execute_enterprise_orchestration')
        namespace = {'ValidationError': ValidationError, '_': lambda value: value}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        for existing in (False, 42):
            with self.subTest(existing=existing):
                # No env: any cross-app access fails instead of silently passing.
                record = SimpleNamespace(
                    ensure_one=lambda: None,
                    is_orchestrated=bool(existing),
                    orchestrated_po_id=existing,
                    orchestrated_nsw_dossier_id=existing,
                    orchestrated_treasury_task_id=existing,
                )
                before = vars(record).copy()
                with self.assertRaisesRegex(ValidationError, 'source evidence'):
                    namespace['action_execute_enterprise_orchestration'](record)
                self.assertEqual(vars(record), before)


if __name__ == '__main__':
    unittest.main()
