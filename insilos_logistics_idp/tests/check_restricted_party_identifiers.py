"""Run locally: python3 insilos/apps/insilos_logistics_idp/tests/check_restricted_party_identifiers.py"""
import ast
import importlib.util
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


spec = importlib.util.spec_from_file_location(
    'restricted_party', Path(__file__).resolve().parents[1] / 'services/restricted_party.py')
screening = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screening)


class RestrictedPartyIdentifiers(unittest.TestCase):
    def test_incomplete_datasets_and_reconciliation_callers(self):
        model = Path(__file__).resolve().parents[1] / 'models/logistics_idp.py'
        tree = ast.parse(model.read_text())
        case = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and any(isinstance(item, ast.FunctionDef) and item.name == '_restricted_party_screening'
                            for item in node.body))
        method = next(node for node in case.body if isinstance(node, ast.FunctionDef)
                      and node.name == '_restricted_party_screening')
        namespace = {'json': json, 'canonical_party_evidence': screening.canonical_party_evidence,
                     'normalize_party': screening.normalize_party, 'screen_parties': screening.screen_parties,
                     'hashlib': hashlib, 'tools': SimpleNamespace(config={'test_enable': True}),
                     '_canonical_json': lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'))}
        sources_method = next(node for node in case.body if isinstance(node, ast.FunctionDef)
                              and node.name == '_restricted_party_sources')
        activation_method = next(node for node in case.body if isinstance(node, ast.FunctionDef)
                                 and node.name == '_screening_source_is_activated')
        exec(compile(ast.Module(body=[sources_method, activation_method, method], type_ignores=[]), str(model), 'exec'), namespace)
        reconcile = next(node for node in case.body if isinstance(node, ast.FunctionDef)
                         and node.name == 'reconcile_documents')
        start = next(index for index, node in enumerate(reconcile.body)
                     if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                         and target.id == 'restricted_party' for target in node.targets))
        propagation = compile(ast.Module(body=reconcile.body[start:start + 2], type_ignores=[]), str(model), 'exec')
        valid = {'entries': [{'name': 'Listed Party'}]}
        invalid = [None, [], {}, 'bad', [None], [{'entries': []}],
                   [{'entries': [{'name': ''}]}], [{'entries': [{'name': 'Listed', 'aliases': None}]}],
                   [valid, {'entries': []}], [dict(valid, complete=False)],
                   [{'entries': [{'name': 'Listed', 'id_numbers': [123]}]}]]
        for dataset in invalid:
            with self.subTest(dataset=dataset):
                result = screening.screen_parties(['Clean Supplier'], dataset)
                self.assertEqual(result['verdict'], 'review')
                self.assertEqual(result['reason'], 'restricted_party_screening_incomplete')
                source = SimpleNamespace(payload=json.dumps({'overlays': {'restricted_parties': dataset}}),
                                         id=1, code='fixture', version='1', payload_hash='fixture',
                                         source_tier='authoritative_tier_1', citation='fixture',
                                         legal_authority=True, verification_status='verified', freshness_status='fresh',
                                         audit_service='test_fixture', company_id=SimpleNamespace(id=1))
                env = Mock()
                env.search.return_value = [source]
                checks = Mock()
                checks.search.return_value = SimpleNamespace(id=42)
                activations = Mock()
                activations.sudo.return_value.search.return_value = False
                env_models = {'logistics.idp.policy.source': env, 'logistics.idp.check.result': checks,
                              'logistics.idp.policy.activation': activations}
                stub = SimpleNamespace(ensure_one=lambda: None, supplier_reference='Clean Supplier',
                                       company_id=SimpleNamespace(id=1), effective_date='2026-09-08', id=1,
                                       env=env_models)
                stub._restricted_party_sources = lambda: namespace['_restricted_party_sources'](stub)
                stub._screening_source_is_activated = lambda item: namespace['_screening_source_is_activated'](stub, item)
                stub._restricted_party_screening = lambda po, invoice, binding: namespace['_restricted_party_screening'](stub, po, invoice, binding)
                source.audit_service = 'forged'
                self.assertFalse(stub._screening_source_is_activated(source))
                source.audit_service = 'test_fixture'
                result = stub._restricted_party_screening({}, {}, 'fixture')
                self.assertEqual((result['verdict'], result['performed']), ('review', False))
                for original, expected in [('pass', 'review'), ('review', 'review'), ('block', 'block')]:
                    scope = {'self': stub, 'po': {}, 'invoice': {}, 'binding_hash': 'fixture', 'verdict': original}
                    exec(propagation, scope)
                    self.assertEqual(scope['verdict'], expected)
        for payloads in [[], ['not-json'], ['null'], ['{}'], ['{"overlays": null}'],
                         ['{"overlays": {}}']]:
            env.search.return_value = [SimpleNamespace(
                payload=payload, id=index, payload_hash='invalid-%s' % index,
                audit_service='test_fixture', company_id=SimpleNamespace(id=1))
                for index, payload in enumerate(payloads, 1)]
            result = stub._restricted_party_screening({}, {}, 'fixture')
            self.assertEqual((result['verdict'], result['performed']), ('review', False))
        env.search.return_value = []
        checks.search.return_value = False
        result = stub._restricted_party_screening({}, {}, 'no-source')
        self.assertEqual((result['verdict'], result['performed'], result['lists_consulted']), ('review', False, 0))
        created, runner = checks._create_from_check_runner.call_args.args
        self.assertEqual(runner, 'restricted_party_screening')
        self.assertEqual(created['verdict'], 'review')
        self.assertFalse(created['policy_source_id'])
        self.assertEqual(created['payload']['hits'], [])
        self.assertEqual(screening.screen_parties(['Clean Supplier'], [valid])['verdict'], 'pass')
        sources = [SimpleNamespace(
            payload=json.dumps({'overlays': {'restricted_parties': [valid]}}),
            id=index, code='fixture', version='1', payload_hash='fixture-%s' % index,
            source_tier='authoritative_tier_1', citation='fixture', legal_authority=True,
            verification_status='verified', freshness_status='fresh', audit_service='test_fixture',
            company_id=SimpleNamespace(id=1))
            for index in (1, 2)]
        env.search.return_value = sources
        result = stub._restricted_party_screening({}, {}, 'fixture')
        self.assertEqual((result['verdict'], result['lists_consulted']), ('pass', 2))
        sources[0].audit_service = 'forged'
        result = stub._restricted_party_screening({}, {}, 'unactivated-source')
        self.assertEqual((result['verdict'], result['performed'], result['lists_consulted']), ('review', False, 1))
        sources[0].audit_service = 'test_fixture'
        sources[0].freshness_status = 'review'
        checks.search.return_value = False
        result = stub._restricted_party_screening({}, {}, 'stale-source')
        self.assertEqual((result['verdict'], result['performed'], result['lists_consulted']), ('review', False, 1))
        created, runner = checks._create_from_check_runner.call_args.args
        self.assertEqual(runner, 'restricted_party_screening')
        self.assertEqual(created['actual'], 'no match')
        self.assertEqual(created['payload']['hits'], [])
        sources[0].freshness_status = 'fresh'
        domain = env.search.call_args.args[0]
        self.assertIn(('effective_from', '<=', stub.effective_date), domain)
        self.assertEqual(domain[-3:], ['|', ('effective_to', '=', False),
                                     ('effective_to', '>=', stub.effective_date)])
        first_hash = checks.search.call_args.args[0][-1][2]
        sources[1].payload_hash = 'changed-no-hit-dataset'
        stub._restricted_party_screening({}, {}, 'fixture')
        second_hash = checks.search.call_args.args[0][-1][2]
        self.assertNotEqual(first_hash, second_hash)
        env.search.return_value = list(reversed(sources))
        stub._restricted_party_screening({}, {}, 'fixture')
        self.assertEqual(second_hash, checks.search.call_args.args[0][-1][2])

    def test_identifier_match_requires_review_even_when_name_differs(self):
        result = screening.screen_parties(['Different Name', ' VAT-123 '], [{
            'entries': [{'name': 'Listed Party', 'id_numbers': ['vat-123']}],
        }])
        self.assertEqual(result['verdict'], 'review')
        self.assertEqual(result['hits'][0]['matched'], 'vat-123')

    def test_identifier_only_entry_is_consulted(self):
        result = screening.screen_parties(['IMO-123'], [{
            'entries': [{'id_numbers': ['imo-123']}],
        }])
        self.assertEqual(result['lists_consulted'], 1)
        self.assertEqual(result['verdict'], 'review')

    def test_identifier_matching_is_exact(self):
        result = screening.screen_parties(['1234567890124'], [{
            'entries': [{'name': 'Listed Party', 'id_numbers': ['1234567890123']}],
        }])
        self.assertEqual(result['verdict'], 'pass')

    def test_name_alias_fuzzy_match_still_requires_review(self):
        result = screening.screen_parties(['Acme Trading Compan'], [{
            'entries': [{'name': 'Other Name', 'aliases': ['Acme Trading Company']}],
        }])
        self.assertEqual(result['verdict'], 'review')


if __name__ == '__main__':
    unittest.main()
