# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import inspect
import json
from pathlib import Path
import threading
import urllib.request
import uuid
from unittest.mock import MagicMock, patch

from odoo.addons.insilos_pubsub_bridge.controllers.pubsub_webhook import _validate_envelope
from odoo.tests.common import HttpCase, TransactionCase, tagged


@tagged('at_install', 'insilos_pubsub_bridge')
class TestCompanyMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = Path(__file__).parents[1] / "migrations/19.0.2.0.1/pre-migrate.py"
        spec = importlib.util.spec_from_file_location("pubsub_company_migration", path)
        cls.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.migration)

    def test_preserves_known_company_and_creates_all_columns_before_validation(self):
        cr = MagicMock()
        cr.fetchall.side_effect = [[(7,)], [], [], []]
        with self.assertRaisesRegex(RuntimeError, r"is_pubsub_event_log.*IDs: \[7\].*backup"):
            self.migration.migrate(cr, None)
        sql = [call.args[0] for call in cr.execute.call_args_list]
        add_positions = [i for i, statement in enumerate(sql) if "ADD COLUMN IF NOT EXISTS" in statement]
        self.assertEqual(len(add_positions), len(self.migration.TABLES))
        self.assertLess(max(add_positions), next(i for i, statement in enumerate(sql) if "SELECT id" in statement))
        self.assertFalse(any("UPDATE" in statement.upper() for statement in sql))

    def test_known_companies_become_required_and_indexed(self):
        cr = MagicMock()
        cr.fetchall.side_effect = [[] for _table in self.migration.TABLES]
        self.migration.migrate(cr, None)
        sql = "\n".join(call.args[0] for call in cr.execute.call_args_list)
        for table in self.migration.TABLES:
            self.assertIn(f"ALTER TABLE {table} ALTER COLUMN company_id SET NOT NULL", sql)
            self.assertIn(f"CREATE INDEX IF NOT EXISTS {table}_company_id_idx", sql)


@tagged('post_install', '-at_install', 'insilos_pubsub_bridge')
class TestPubSubIngest(TransactionCase):

    def setUp(self):
        super(TestPubSubIngest, self).setUp()
        self.EventLog = self.env['is.pubsub.event.log']
        self.Lead = self.env['crm.lead']
        self.PO = self.env['purchase.order']

    def test_00_strict_envelope_boundary(self):
        envelope = {
            'spec_version': '1.0',
            'event_id': 'evt-1',
            'event_type': 'general.event',
            'source': 'test.source',
            'producer': 'test-producer',
            'company_id': self.env.company.id,
            'payload': {},
        }
        self.assertIs(_validate_envelope(envelope), envelope)
        for invalid in (
            {},
            {**envelope, 'event_id': '../unsafe'},
            {**envelope, 'company_id': str(self.env.company.id)},
            {**envelope, 'payload': []},
            {**envelope, 'payload': {'sender': 'not-an-object'}},
            {**envelope, 'metadata': []},
        ):
            with self.assertRaises(ValueError):
                _validate_envelope(invalid)

    def test_01_ingress_claims_before_business_effect(self):
        from odoo.addons.insilos_pubsub_bridge.controllers.pubsub_webhook import PubSubERPController

        source = inspect.getsource(PubSubERPController.ingest_pubsub_event)
        self.assertIn('event_log = EventLog.create', source)
        self.assertIn('event_log._process_claimed_event()', source)
        self.assertNotIn("request.env['crm.lead']", source)
        self.assertIn('except IntegrityError:', source)

    def test_01_dispatch_capabilities_are_explicit_dependencies(self):
        from odoo.addons.insilos_pubsub_bridge.models.is_pubsub_event_log import PubSubEventLog

        manifest = (Path(__file__).parents[1] / '__manifest__.py').read_text()
        handlers = inspect.getsource(PubSubEventLog)
        for module, model in (('crm', 'crm.lead'), ('purchase', 'purchase.order'),
                              ('account', 'account.move'), ('project', 'project.task')):
            self.assertIn(f"'{module}'", manifest)
            self.assertIn(f"self.env['{model}']", handlers)

    def test_01_event_log_company_schema(self):
        field = self.EventLog._fields['company_id']
        self.assertTrue(field.required)
        self.assertTrue(field.index)
        self.env.cr.execute("""
            SELECT is_nullable
              FROM information_schema.columns
             WHERE table_name = 'is_pubsub_event_log' AND column_name = 'company_id'
        """)
        self.assertEqual(self.env.cr.fetchone(), ('NO',))
        self.env.cr.execute("""
            SELECT 1
              FROM pg_indexes
             WHERE tablename = 'is_pubsub_event_log'
               AND indexdef LIKE '%(company_id)%'
        """)
        self.assertTrue(self.env.cr.fetchone())

    def test_02_event_log_creation_and_idempotency(self):
        """Test event log creation and unique event_id constraint."""
        log = self.EventLog.create({
            'event_id': 'evt-test-unique-01',
            'event_type': 'email.inbound.crm_lead',
            'sender_email': 'customer@example.com',
            'sender_name': 'Nguyen Van A',
            'subject': 'Request for Quotation Toluene 50 Tons',
            'state': 'processed',
        })
        self.assertEqual(log.event_id, 'evt-test-unique-01')
        self.assertEqual(log.state, 'processed')

        # Test duplicate event_id triggers uniqueness error
        with self.assertRaises(Exception):
            self.EventLog.create({
                'event_id': 'evt-test-unique-01',
                'event_type': 'email.inbound.crm_lead',
            })

    def test_02_per_consumer_ledger_and_ordering_gap(self):
        common = {
            'event_id': 'evt-consumer-order', 'event_type': 'email.inbound.crm_lead',
            'aggregate_id': 'lead-stream-1', 'aggregate_version': 2,
            'subject': 'Ordered lead', 'state': 'received',
        }
        first_consumer = self.EventLog.create(dict(common, consumer='crm'))
        second_consumer = self.EventLog.create(dict(common, consumer='audit'))
        first_consumer._process_claimed_event()
        self.assertEqual(first_consumer.state, 'received')
        self.assertIn('version 1', first_consumer.error_message)
        previous = self.EventLog.create(dict(common, event_id='evt-consumer-order-v1', consumer='crm', aggregate_version=1))
        previous._process_claimed_event()
        first_consumer._process_claimed_event()
        self.assertEqual((previous.state, first_consumer.state), ('processed', 'processed'))
        self.assertEqual(second_consumer.state, 'received')

    def test_02_crm_lead_dispatch_simulation(self):
        """Test creating CRM Lead from AI analysis payload."""
        entities = {
            'chemical_name': 'Toluene',
            'cas_number': '108-88-3',
            'quantity': 50,
            'unit': 'Tons',
            'delivery_location': 'Cảng Cát Lái',
        }
        lead = self.Lead.create({
            'name': '[AI Inbound] Yêu cầu báo giá Toluene',
            'contact_name': 'Tran Van B',
            'email_from': 'tran.b@chemical-importer.vn',
            'description': f"Extracted Entities:\n{json.dumps(entities, indent=2)}",
            'priority': '3',
        })
        self.assertTrue(lead.id)
        self.assertIn('108-88-3', lead.description)

        # Log link
        log = self.EventLog.create({
            'event_id': 'evt-test-lead-02',
            'event_type': 'email.inbound.crm_lead',
            'target_model': 'crm.lead',
            'target_res_id': lead.id,
            'state': 'processed',
        })
        self.assertEqual(log.target_record_ref, f"crm.lead,{lead.id}")
        action = log.action_open_target_record()
        self.assertEqual(action.get('res_model'), 'crm.lead')
        self.assertEqual(action.get('res_id'), lead.id)

    def test_03_pubsub_channel_ping_and_renew(self):
        """Test channel creation, health ping and watch renewal."""
        channel = self.env['is.pubsub.channel'].create({
            'name': 'Test Gmail Notifications Hub',
            'channel_type': 'gmail_push',
            'topic_name': 'gmail-notifications',
            'monitored_email': 'inteligentsilos@gmail.com',
        })
        self.assertEqual(channel.state, 'active')
        self.assertIn('/google_gmail/pubsub/push', channel.endpoint_url)

        # Test ping action
        ping_res = channel.action_test_ping()
        self.assertEqual(ping_res.get('type'), 'ir.actions.client')

        # Test renew watch action
        renew_res = channel.action_renew_watch()
        self.assertEqual(renew_res.get('type'), 'ir.actions.client')

    def test_04_automation_rule_execution(self):
        """Test automation rule configuration and execution."""
        rule = self.env['is.pubsub.automation.rule'].create({
            'name': 'Forward Logistics Manifest',
            'event_type_filter': 'email.inbound.crm_lead',
            'action_type': 'multi_action',
            'target_model': 'crm.lead',
            'call_forward_enabled': True,
            'forward_url': 'http://127.0.0.1:8000/api/mock/forward',
            'telegram_alert_enabled': False,
        })
        self.assertTrue(rule.id)

        # Trigger test rule action
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_automation_rule.requests.request') as request:
            request.return_value.status_code = 202
            request.return_value.text = 'accepted'
            res = rule.action_test_rule()
        self.assertEqual(res.get('type'), 'ir.actions.client')
        self.assertGreaterEqual(rule.execution_count, 1)


@tagged('post_install', '-at_install', 'insilos_pubsub_bridge')
class TestPubSubIngestSecurity(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'PubSub Company B'})
        cls.env['is.pubsub.channel'].create({
            'name': 'Company A Hermes',
            'channel_type': 'hermes_event_bus',
            'company_id': cls.company_a.id,
            'webhook_secret': 'company-a-secret',
        })
        cls.env['is.pubsub.channel'].create({
            'name': 'Company B Hermes',
            'channel_type': 'hermes_event_bus',
            'company_id': cls.company_b.id,
            'webhook_secret': 'company-b-secret',
        })

    def _post(self, company, secret, event_type='general.event', event_id=None):
        event_id = event_id or f'evt-{uuid.uuid4()}'
        response = self.url_open('/api/v1/pubsub/ingest', data=json.dumps({
            'event_id': event_id,
            'event_type': event_type,
            'source': 'test.source',
            'producer': 'test-producer',
            'company_id': company.id,
            'payload': {'subject': 'Security test'},
            'spec_version': '1.0',
        }), headers={'Content-Type': 'application/json', 'X-ERP-API-Key': secret})
        return event_id, response

    def test_concurrent_duplicate_http_creates_one_business_effect(self):
        event_id = f'evt-concurrent-{uuid.uuid4()}'
        subject = f'Concurrent HTTP {event_id}'
        barrier = threading.Barrier(2)
        secret = f'concurrent-secret-{uuid.uuid4()}'
        company_id = self.company_a.id

        with self.registry.cursor() as cr:
            env = self.env(cr=cr)
            channel = env['is.pubsub.channel'].search([
                ('company_id', '=', company_id),
                ('channel_type', '=', 'hermes_event_bus'),
            ], limit=1)
            channel_id = channel.id
            original_secret = channel.webhook_secret
            channel.webhook_secret = secret
            cr.commit()
        body = json.dumps({
            'spec_version': '1.0',
            'event_id': event_id,
            'event_type': 'email.inbound.crm_lead',
            'source': 'test.source',
            'producer': 'test-producer',
            'company_id': company_id,
            'payload': {'subject': subject},
        }).encode()

        def post():
            request = urllib.request.Request(
                f'{self.base_url()}/api/v1/pubsub/ingest', body,
                {'Content-Type': 'application/json', 'X-ERP-API-Key': secret},
            )
            barrier.wait(timeout=5)
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.load(response)['status']

        try:
            with self.allow_requests(all_requests=True), ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = [future.result(timeout=15) for future in (executor.submit(post), executor.submit(post))]

            self.assertEqual(sorted(outcomes), [(200, 'ignored'), (200, 'success')])
            self.env.invalidate_all()
            self.assertEqual(self.env['is.pubsub.event.log'].search_count([('event_id', '=', event_id)]), 1)
            self.assertEqual(self.env['crm.lead'].search_count([('name', '=', f'[AI Inbound] {subject}')]), 1)
        finally:
            with self.registry.cursor() as cr:
                cr.execute("DELETE FROM crm_lead WHERE name = %s", [f'[AI Inbound] {subject}'])
                cr.execute("DELETE FROM is_pubsub_event_log WHERE event_id = %s", [event_id])
                cr.execute("UPDATE is_pubsub_channel SET webhook_secret = %s WHERE id = %s", [original_secret, channel_id])
                cr.commit()

    def test_credentials_are_bound_to_envelope_company(self):
        event_id, response = self._post(self.company_b, 'company-a-secret')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.env['is.pubsub.event.log'].search([('event_id', '=', event_id)]))

        event_id, response = self._post(self.company_b, 'company-b-secret')
        self.assertEqual(response.status_code, 200)
        log = self.env['is.pubsub.event.log'].search([('event_id', '=', event_id)])
        self.assertEqual(log.company_id, self.company_b)

    def test_same_event_id_is_isolated_by_company(self):
        event_id = f'evt-shared-{uuid.uuid4()}'
        _, response_a = self._post(self.company_a, 'company-a-secret', event_id=event_id)
        _, response_b = self._post(self.company_b, 'company-b-secret', event_id=event_id)

        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)
        logs = self.env['is.pubsub.event.log'].search([('event_id', '=', event_id)])
        self.assertEqual(set(logs.company_id.ids), {self.company_a.id, self.company_b.id})

    def test_automation_rules_are_isolated_by_company(self):
        rule_a = self.env['is.pubsub.automation.rule'].create({
            'name': 'Company A rule',
            'company_id': self.company_a.id,
        })
        rule_b = self.env['is.pubsub.automation.rule'].create({
            'name': 'Company B rule',
            'company_id': self.company_b.id,
        })

        _, response = self._post(self.company_a, 'company-a-secret')

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()['rules_triggered'], 1)
        rule_a.invalidate_recordset()
        rule_b.invalidate_recordset()
        self.assertEqual(rule_a.execution_count, 1)
        self.assertEqual(rule_b.execution_count, 0)

    def test_exception_rolls_back_business_record(self):
        Lead = self.env.registry['crm.lead']
        original_create = Lead.create

        def create_then_fail(records, vals):
            original_create(records, vals)
            raise RuntimeError('forced failure after business create')

        with patch.object(Lead, 'create', create_then_fail):
            event_id, response = self._post(self.company_a, 'company-a-secret', 'email.inbound.crm_lead')

        self.assertEqual(response.status_code, 500)
        self.assertFalse(self.env['crm.lead'].search([('name', '=', '[AI Inbound] Security test')]))
        self.assertFalse(self.env['is.pubsub.event.log'].search([('event_id', '=', event_id)]))
