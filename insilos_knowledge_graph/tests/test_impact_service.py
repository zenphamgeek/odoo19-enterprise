from datetime import datetime, timedelta, timezone

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..services.impact_service import ImpactService


@tagged('post_install', '-at_install')
class TestImpactService(TransactionCase):
    def setUp(self):
        super().setUp()
        self.service = ImpactService()
        self.event_at = datetime(2026, 8, 14, 1, 0, tzinfo=timezone.utc)
        self.event = {
            'reference': 'operations.event:7',
            'domain': 'OPERATIONS',
            'canonical': True,
            'verified': True,
            'timestamp': self.event_at,
            'action_proposal': {'type': 'REVIEW_ROUTE'},
        }
        self.verified_path = [{
            'edge_hash': 'b', 'from': 'urn:a', 'to': 'urn:b',
            'provenance': {
                'verified': True, 'state': 'VERIFIED',
                'evidence_reference': 'evidence:7',
            },
        }]

    def test_measures_supplied_verified_timestamps_deterministically(self):
        observed_at = self.event_at + timedelta(seconds=125)
        first = self.service.measure(
            self.event, observed_at=observed_at, paths=[self.verified_path])
        second = self.service.measure(
            self.event, observed_at=observed_at, paths=[self.verified_path])
        self.assertEqual(first, second)
        self.assertEqual(first['measured_mtti_seconds'], 125.0)
        self.assertEqual(first['event_timestamp'], self.event_at)
        self.assertEqual(first['observed_at'], observed_at)
        self.assertEqual(first['affected_entities'], ['urn:a', 'urn:b'])
        self.assertEqual(first['evidence_references'], ['evidence:7'])
        self.assertEqual(first['action_proposal'], {'type': 'REVIEW_ROUTE'})
        self.assertFalse(first['execution'])

    def test_only_verified_paths_affect_result(self):
        candidate = [{
            'edge_hash': 'a', 'from': 'urn:a', 'to': 'urn:hidden',
            'provenance': {
                'verified': False, 'state': 'CANDIDATE',
                'evidence_reference': 'evidence:hidden',
            },
        }]
        missing_state = [{
            'edge_hash': 'c', 'from': 'urn:a', 'to': 'urn:hidden-state',
            'provenance': {'verified': True, 'evidence_reference': 'evidence:c'},
        }]
        missing_evidence = [{
            'edge_hash': 'd', 'from': 'urn:a', 'to': 'urn:hidden-evidence',
            'provenance': {'verified': True, 'state': 'VERIFIED'},
        }]
        bare_verified = [{'edge_hash': 'e', 'verified': True, 'from': 'urn:a', 'to': 'urn:bare'}]
        result = self.service.measure(
            self.event, observed_at=self.event_at,
            paths=[candidate, missing_state, missing_evidence, bare_verified, self.verified_path])
        self.assertEqual(result['affected_paths'], [self.verified_path])
        self.assertNotIn('urn:hidden', result['affected_entities'])
        self.assertNotIn('evidence:hidden', result['evidence_references'])

    def test_missing_timestamp_never_invents_mtti(self):
        event = dict(self.event)
        event.pop('timestamp')
        result = self.service.measure(event, paths=[self.verified_path])
        self.assertIsNone(result['event_timestamp'])
        self.assertIsNone(result['observed_at'])
        self.assertIsNone(result['measured_mtti_seconds'])

    def test_trade_and_legal_impact_blocked(self):
        for event in (
            dict(self.event, domain='TRADE'),
            dict(self.event, domain='REGULATORY'),
            dict(self.event, legal=True),
        ):
            with self.subTest(event=event), self.assertRaisesRegex(
                    ValidationError, 'disabled until TRADE gates pass'):
                self.service.measure(event, observed_at=self.event_at)
