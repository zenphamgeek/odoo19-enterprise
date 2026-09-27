# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import MagicMock, patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'insilos_pubsub_bridge')
class TestPubSubEnterpriseWorkflows(TransactionCase):

    def setUp(self):
        super(TestPubSubEnterpriseWorkflows, self).setUp()
        self.EventLog = self.env['is.pubsub.event.log']
        self.Rule = self.env['is.pubsub.automation.rule']
        self.OutboundRule = self.env['is.pubsub.outbound.rule']
        self.OutboundEvent = self.env['is.pubsub.outbound.event']
        self.CronHelper = self.env['is.pubsub.scheduled.action']
        self.Partner = self.env['res.partner']
        self.Move = self.env['account.move']

    def test_rpc_credentials_are_manager_only(self):
        user = new_test_user(
            self.env, login='pubsub_regular',
            groups='insilos_pubsub_bridge.group_pubsub_user',
        )
        credentials = {
            'is.pubsub.channel': 'webhook_secret',
            'is.pubsub.automation.rule': 'forward_auth_header',
            'is.pubsub.outbound.rule': 'auth_header',
        }
        for model_name, field_name in credentials.items():
            with self.assertRaises(AccessError):
                self.env[model_name].with_user(user).search_read([], [field_name], limit=1)
        with self.assertRaises(AccessError):
            self.Rule.with_user(user).search_read([], ['telegram_bot_token'], limit=1)

        manager = new_test_user(
            self.env, login='pubsub_manager',
            groups='insilos_pubsub_bridge.group_pubsub_manager',
        )
        for model_name, field_name in credentials.items():
            self.env[model_name].with_user(manager).search_read([], [field_name], limit=1)
        self.Rule.with_user(manager).search_read([], ['telegram_bot_token'], limit=1)

    def test_01_invoicing_vendor_bill_workflow(self):
        """Test Inbound Invoice workflow creating account.move vendor bill."""
        partner = self.Partner.create({
            'name': 'BASF Vietnam Co., Ltd',
            'email': 'billing@basf.com',
            'supplier_rank': 1,
        })

        event_payload = {
            'event_type': 'finance.inbound.invoice',
            'payload': {
                'ai_analysis': {
                    'summary': 'Chemical raw materials bill for Toluene 20MT',
                    'entities': {
                        'invoice_number': 'BASF-2026-INV-001',
                        'amount': 15600.0,
                    }
                }
            }
        }

        log = self.EventLog.create({
            'event_id': 'evt-test-invoice-001',
            'event_type': 'finance.inbound.invoice',
            'sender_email': 'billing@basf.com',
            'sender_name': 'BASF Vietnam',
            'subject': 'E-Invoice #BASF-2026-INV-001',
            'ai_summary': 'Chemical raw materials bill for Toluene 20MT',
            'payload': json.dumps(event_payload),
            'ai_entities_json': json.dumps(event_payload['payload']['ai_analysis']['entities']),
            'state': 'received',
        })
        requeued = log.with_context(requeue_reason='Focused test retry').action_requeue_event()
        self.assertEqual(log.state, 'requeued')
        self.assertEqual(requeued.state, 'processed')
        self.assertEqual(requeued.target_model, 'account.move')
        self.assertTrue(requeued.target_res_id)

        bill = self.Move.browse(requeued.target_res_id)
        self.assertEqual(bill.move_type, 'in_invoice')
        self.assertEqual(bill.partner_id.id, partner.id)

    def test_02_payment_advice_workflow(self):
        """Test Inbound Payment Advice workflow creating account.payment voucher."""
        partner = self.Partner.create({
            'name': 'PetroVietnam Gas Treasury',
            'email': 'treasury@petrovietnam.vn',
            'customer_rank': 1,
        })

        event_payload = {
            'event_type': 'finance.inbound.payment_advice',
            'payload': {
                'ai_analysis': {
                    'summary': 'Wire transfer received for Gas contract',
                    'entities': {
                        'amount': 50000.0,
                        'transaction_ref': 'TXN-998822',
                    }
                }
            }
        }

        log = self.EventLog.create({
            'event_id': 'evt-test-payment-002',
            'event_type': 'finance.inbound.payment_advice',
            'sender_email': 'treasury@petrovietnam.vn',
            'sender_name': 'PetroVietnam Gas',
            'subject': 'Payment Advice Ref TXN-998822',
            'ai_summary': 'Wire transfer received $50,000 USD',
            'payload': json.dumps(event_payload),
            'ai_entities_json': json.dumps(event_payload['payload']['ai_analysis']['entities']),
            'state': 'received',
        })

        requeued = log.with_context(requeue_reason='Focused test retry').action_requeue_event()
        self.assertEqual(log.state, 'requeued')
        self.assertEqual(requeued.state, 'processed')
        self.assertEqual(requeued.target_model, 'account.payment')
        self.assertTrue(requeued.target_res_id)

    def test_03_outbound_event_publishing(self):
        """Test publishing outbound events via is.pubsub.outbound.event."""
        event = self.OutboundEvent.create({
            'event_type': 'record.created',
            'source_model': 'crm.lead',
            'source_res_id': 99,
            'payload': json.dumps({'name': 'Test Lead', 'amount': 10000}),
            'target_url': 'https://example.com/api/mock/outbound',
            'state': 'pending',
        })
        self.assertTrue(event.id)
        self.assertEqual(event.state, 'pending')

        # Test retry action
        event.write({'state': 'retrying'})
        event.action_retry()
        self.assertEqual(event.state, 'pending')
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_outbound_event.requests.request') as request:
            request.return_value.status_code = 202
            request.return_value.text = 'accepted'
            event.action_publish()
        self.assertEqual(event.state, 'sent')

    def test_03a_outbound_delivery_classification_and_observability(self):
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_outbound_event.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 443))]):
            event = self.OutboundEvent.publish_event(
                'custom', 'res.partner', 42,
                {'correlation_id': 'corr-1', 'causation_id': 'cause-1', 'trace_id': 'trace-1'},
                'https://example.test/events',
            )
        self.assertEqual((event.destination, event.correlation_id, event.causation_id, event.trace_id), ('example.test', 'corr-1', 'cause-1', 'trace-1'))

        responses = [(409, {}), (400, {}), (429, {'Retry-After': '120'}), (503, {})]
        expected = [('sent', False), ('dead', 'terminal_http'), ('retrying', 'retryable_http'), ('retrying', 'retryable_http')]
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_outbound_event.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 443))]):
            for index, ((status, headers), outcome) in enumerate(zip(responses, expected)):
                current = event if not index else event.copy({'name': f'OUT-FAKE-{index}', 'state': 'pending', 'retry_count': 0})
                response = MagicMock(status_code=status, text='fake', headers=headers)
                with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_outbound_event.requests.request', return_value=response):
                    current.action_publish()
                self.assertEqual((current.state, current.error_class or False), outcome)
        self.assertGreaterEqual((current.next_retry_at - fields.Datetime.now()).total_seconds(), 29)

    def test_03aa_canonical_envelope_and_destination_ledger(self):
        payload = {
            'event_id': 'canonical-1', 'aggregate_id': 'partner-42', 'aggregate_version': 2,
            'correlation_id': 'corr-1', 'causation_id': 'cause-1', 'trace_id': 'trace-1',
            'schema_name': 'partner.changed', 'schema_hash': 'sha256:abc',
            'classification': 'internal', 'payload': {'name': 'Canonical Partner'},
        }
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_outbound_event.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 443))]):
            event = self.OutboundEvent.publish_event('custom', 'res.partner', 42, payload, 'https://example.test/events')
            other_destination = self.OutboundEvent.publish_event('custom', 'res.partner', 42, payload, 'https://other.example.test/events')
            with self.assertRaises(Exception):
                self.OutboundEvent.publish_event('custom', 'res.partner', 42, payload, 'https://example.test/events')
        envelope = json.loads(event.payload)
        self.assertEqual(envelope['spec_version'], '1.0')
        self.assertEqual(envelope['payload'], {'name': 'Canonical Partner'})
        self.assertEqual((event.event_id, event.aggregate_id, event.aggregate_version), ('canonical-1', 'partner-42', 2))
        self.assertEqual(other_destination.event_id, event.event_id)

    def test_03ab_timeout_retries_and_expired_worker_lease_is_reclaimed(self):
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_outbound_event.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 443))]):
            event = self.OutboundEvent.create({
                'event_type': 'custom', 'source_model': 'res.partner', 'payload': '{}',
                'target_url': 'https://example.test/timeout', 'state': 'processing',
                'lease_expires_at': fields.Datetime.subtract(fields.Datetime.now(), minutes=1),
            })
        timeout = __import__('requests').exceptions.Timeout('deterministic timeout')
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_outbound_event.requests.request', side_effect=timeout):
            self.OutboundEvent._cron_dispatch_outbox()
        self.assertEqual((event.state, event.retry_count, event.error_class), ('retrying', 1, 'network'))
        self.assertFalse(event.lease_expires_at)

    def test_03b_outbound_audit_is_immutable(self):
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_outbound_event.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 443))]):
            event = self.OutboundEvent.create({'event_type': 'custom', 'source_model': 'res.partner', 'payload': '{}', 'target_url': 'https://example.test/events'})
        with self.assertRaises(AccessError):
            event.write({'payload': '{"changed": true}'})

    def test_03c_outbound_rule_event_type_mapping(self):
        rule = self.OutboundRule.create({
            'name': 'Map update event',
            'model_name': 'res.partner',
            'trigger_action': 'write',
            'target_url': 'https://example.test/events',
            'include_full_record': False,
        })
        partner = self.Partner.create({'name': 'Mapped Partner'})
        with patch.object(type(self.OutboundEvent), 'publish_event', autospec=True) as publish:
            rule.fire_rule(partner, action='write')
        self.assertEqual(publish.call_args.kwargs['event_type'], 'record.updated')
        self.assertEqual(publish.call_args.kwargs['payload_dict']['event_type'], 'record.updated')

    def test_03c_forward_failure_propagates_and_updates_counters(self):
        rule = self.Rule.create({
            'name': 'Failing forward',
            'event_type_filter': 'all',
            'call_forward_enabled': True,
            'forward_url': 'https://example.test/fail',
        })
        log = self.EventLog.create({'event_id': 'evt-forward-fail', 'event_type': 'general.event'})
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_automation_rule.requests.request') as request:
            request.return_value.status_code = 500
            request.return_value.text = 'failure'
            self.assertFalse(rule.execute_rule(log))
        self.assertEqual(rule.success_count, 0)
        self.assertEqual(rule.failed_count, 1)
        self.assertEqual(rule.forward_log_ids.state, 'failed')

    def test_03d_native_notification_routing_is_durable(self):
        event = self.EventLog.create({
            'event_id': 'evt-action-required-001',
            'event_type': 'general.event',
            'priority': 'URGENT',
            'subject': 'Review deterministic event',
        })
        message_count = len(event.message_ids)
        event.action_route_notification()
        self.assertEqual(len(event.message_ids), message_count + 1)
        self.assertEqual(len(event.activity_ids), 1)
        self.assertEqual(event.activity_ids.summary, 'Review deterministic event')

    def test_04_rule_filtering_precision(self):
        """Test regex sender filter and keyword filtering on automation rules."""
        rule = self.Rule.create({
            'name': 'Filter Hapag-Lloyd Logistics Only',
            'event_type_filter': 'email.inbound.logistics_idp',
            'sender_filter': r'@hapag-lloyd\.com$',
            'keyword_filter': 'Bill of Lading, 40HC, Container',
            'action_type': 'call_forward',
            'call_forward_enabled': False,
            'state': 'active',
        })

        # Test Matching Event
        matching_log = self.EventLog.create({
            'event_id': 'evt-match-001',
            'event_type': 'email.inbound.logistics_idp',
            'sender_email': 'docs@hapag-lloyd.com',
            'subject': 'Bill of Lading HLBU1234567',
            'ai_summary': '40HC Container shipment',
        })
        self.assertTrue(rule.matches_event(matching_log))

        # Test Non-matching Sender
        non_match_sender = self.EventLog.create({
            'event_id': 'evt-nonmatch-002',
            'event_type': 'email.inbound.logistics_idp',
            'sender_email': 'docs@maersk.com',
            'subject': 'Bill of Lading MAEU1234567',
            'ai_summary': '40HC Container shipment',
        })
        self.assertFalse(rule.matches_event(non_match_sender))

        # Test Non-matching Keyword
        non_match_keyword = self.EventLog.create({
            'event_id': 'evt-nonmatch-003',
            'event_type': 'email.inbound.logistics_idp',
            'sender_email': 'docs@hapag-lloyd.com',
            'subject': 'General Inquiry Meeting',
            'ai_summary': 'Request for coffee chat',
        })
        self.assertFalse(rule.matches_event(non_match_keyword))

    def test_05_dead_letter_queue_and_crons(self):
        """Test DLQ retry cron and channel health check."""
        failed_log = self.EventLog.create({
            'event_id': 'evt-failed-dlq-001',
            'event_type': 'email.inbound.crm_lead',
            'sender_email': 'lead@example.com',
            'subject': 'DLQ Test Lead',
            'state': 'failed',
            'retry_count': 0,
            'payload': json.dumps({'event_type': 'email.inbound.crm_lead'}),
        })

        # Run DLQ cron
        self.CronHelper._cron_retry_dead_letters()
        self.assertEqual(failed_log.state, 'requeued')
        self.assertEqual(failed_log.requeue_generation, 0)
        self.assertEqual(self.EventLog.search_count([('requeued_from_id', '=', failed_log.id)]), 1)

        # Run Channel health check
        self.CronHelper._cron_channel_health_check()
        # Run Stats aggregation
        self.CronHelper._cron_stats_aggregate()


@tagged('post_install', '-at_install', 'insilos_pubsub_bridge', 'security_negative')
class TestPubSubCompanySecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'PubSub Foreign Company'})
        cls.user = new_test_user(
            cls.env,
            login='pubsub-company-user',
            groups='insilos_pubsub_bridge.group_pubsub_manager',
            company_id=cls.company_a.id,
            company_ids=[(6, 0, cls.company_a.ids)],
        )
        cls.channel_b = cls.env['is.pubsub.channel'].create({
            'name': 'Foreign Channel',
            'company_id': cls.company_b.id,
        })
        cls.rule_b = cls.env['is.pubsub.automation.rule'].create({
            'name': 'Foreign Rule',
            'company_id': cls.company_b.id,
        })
        cls.event_b = cls.env['is.pubsub.event.log'].create({
            'event_id': 'evt-company-foreign',
            'event_type': 'general.event',
            'company_id': cls.company_b.id,
        })
        cls.outbound_rule_b = cls.env['is.pubsub.outbound.rule'].create({
            'name': 'Foreign Outbound Rule',
            'model_name': 'res.partner',
            'target_url': 'https://example.test/events',
            'company_id': cls.company_b.id,
        })
        with patch('odoo.addons.insilos_pubsub_bridge.models.is_pubsub_outbound_event.socket.getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 443))]):
            cls.outbound_b = cls.env['is.pubsub.outbound.event'].create({
                'event_type': 'custom',
                'source_model': 'res.partner',
                'payload': '{}',
                'target_url': 'https://example.test/events',
                'company_id': cls.company_b.id,
            })
        cls.forward_b = cls.env['is.pubsub.forward.log'].create({
            'rule_id': cls.rule_b.id,
            'event_log_id': cls.event_b.id,
            'forward_url': 'https://example.test/forward',
        })

    def test_foreign_company_records_are_hidden(self):
        records = (
            self.channel_b,
            self.rule_b,
            self.event_b,
            self.forward_b,
            self.outbound_rule_b,
            self.outbound_b,
        )
        for record in records:
            self.assertFalse(record.with_user(self.user).search([('id', '=', record.id)]))
            with self.assertRaises(AccessError):
                record.with_user(self.user).check_access('write')

    def test_outbound_records_require_company(self):
        for model, values in (
            (self.env['is.pubsub.outbound.rule'], {
                'name': 'Companyless Rule',
                'model_name': 'res.partner',
                'target_url': 'https://example.test/rule',
            }),
            (self.env['is.pubsub.outbound.event'], {
                'event_type': 'custom',
                'source_model': 'res.partner',
                'payload': '{}',
                'target_url': 'https://example.test/event',
            }),
        ):
            with self.assertRaises(Exception):
                model.create(dict(values, company_id=False))
