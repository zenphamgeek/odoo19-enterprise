# Part of Insilos. See LICENSE file for full copyright and licensing details.

from hashlib import sha256
import json
from pathlib import Path
import runpy

from odoo.tests.common import TransactionCase, tagged


SERVICE = runpy.run_path(
    Path(__file__).parents[1] / 'services' / 'reconciliation_evidence.py')
envelope = SERVICE['envelope']
authorize = SERVICE['authorize']
replay = SERVICE['replay']


@tagged('post_install', '-at_install', 'finance_agent_os', 'rec_01')
class TestReconciliationEvidence(TransactionCase):
    def test_owner_boundaries_and_immutable_payload(self):
        finance = envelope('finance', 'ledger', 'account.move.line,7',
                           {'amount': '12.00', 'dimensions': ['USD']})
        logistics = envelope('logistics', 'document', 'logistics.idp.document,9',
                             {'type': 'invoice'})
        self.assertEqual(finance.payload['dimensions'], ('USD',))
        with self.assertRaises(TypeError):
            finance.payload['amount'] = '0'
        with self.assertRaises(ValueError):
            envelope('finance', 'document', 'doc,9', {})
        with self.assertRaises(ValueError):
            envelope('logistics', 'position', 'capital.position,7', {})
        self.assertIs(authorize('logistics', finance, 'reconcile'), finance)
        self.assertIs(authorize('finance', logistics, 'read'), logistics)

    def test_canonical_sha256_and_replay_idempotency(self):
        first = envelope('finance', 'position', 'capital.position,3', {'b': 2, 'a': 1})
        same = envelope('finance', 'position', 'capital.position,3', {'a': 1, 'b': 2})
        canonical = json.dumps({
            'owner': 'finance', 'kind': 'position', 'reference': 'capital.position,3',
            'payload': {'a': 1, 'b': 2},
        }, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
        self.assertEqual(first.evidence_hash, sha256(canonical.encode()).hexdigest())
        self.assertEqual(first, same)
        self.assertIs(replay(first, same), first)

    def test_rejections_leave_existing_evidence_and_inputs_unchanged(self):
        payload = {'amount': '12.00'}
        current = envelope('finance', 'ledger', 'account.move.line,7', payload)
        conflict = envelope('finance', 'ledger', 'account.move.line,7', {'amount': '13.00'})
        before = current.evidence_hash
        with self.assertRaises(PermissionError):
            authorize('logistics', current, 'mutate')
        with self.assertRaises(ValueError):
            replay(current, conflict)
        self.assertEqual(current.evidence_hash, before)
        self.assertEqual(payload, {'amount': '12.00'})

