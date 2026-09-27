import json
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user as _new_test_user, tagged

from .common import new_logistics_test_user, unique_fixture


@tagged('post_install', '-at_install', 'logistics_idp')
class TestLogisticsIdpOperationalHealth(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_logistics_test_user(
            _new_test_user, cls.env, login=unique_fixture('health-manager'),
            groups='insilos_logistics_idp.group_logistics_manager')
        cls.operator = new_logistics_test_user(
            _new_test_user, cls.env, login=unique_fixture('health-operator'),
            groups='insilos_logistics_idp.group_logistics_operator')

    def _job(self, state, **values):
        return self.env['logistics.idp.inbound.job'].with_user(self.manager).create({
            'profile_code': 'health', 'source_system': 'health-fixture',
            'source_key': unique_fixture(state), 'source_version': '1',
            'payload': json.dumps({'name': 'health', 'provenance': 'fixture',
                                   'effective_date': '2026-01-01'}),
            'state': state, **values,
        })

    def test_health_reports_queue_dead_stale_policy_and_provider_without_pii(self):
        model = self.env['logistics.idp.inbound.job'].with_user(self.manager)
        before = model.operational_health(stale_minutes=30)
        self._job('pending', next_attempt_at=fields.Datetime.now() - timedelta(minutes=10))
        self._job('dead')
        self._job('processing', last_attempt_at=fields.Datetime.now() - timedelta(hours=1))

        health = model.operational_health(stale_minutes=30)

        self.assertEqual(health['schema_version'], '1.0')
        self.assertEqual(health['queue']['queued_count'], before['queue']['queued_count'] + 1)
        self.assertGreaterEqual(health['queue']['oldest_age_seconds'], 600)
        self.assertEqual(health['queue']['dead_count'], before['queue']['dead_count'] + 1)
        self.assertEqual(health['queue']['stale_processing_count'], before['queue']['stale_processing_count'] + 1)
        self.assertEqual(health['queue']['stale_after_seconds'], 1800)
        self.assertEqual(set(health['policy']), {'active', 'active_count', 'fresh_count'})
        self.assertEqual(set(health['provider']), {'active', 'provider', 'capable_model_count'})
        serialized = json.dumps(health).lower()
        for pii_key in ('name', 'email', 'sender', 'subject', 'source_key', 'payload', 'last_error'):
            self.assertNotIn('"%s"' % pii_key, serialized)

    def test_health_is_rbac_guarded_and_validates_threshold(self):
        model = self.env['logistics.idp.inbound.job']
        with self.assertRaises(AccessError):
            model.with_user(self.operator).operational_health()
        with self.assertRaises(ValidationError):
            model.with_user(self.manager).operational_health(stale_minutes=0)
