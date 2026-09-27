from unittest.mock import patch

from requests import RequestException

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAiVisionActionDispatch(TransactionCase):

    def setUp(self):
        super().setUp()
        self.move = self.env['account.move'].create({'move_type': 'in_invoice'})
        self.env['ir.attachment'].create({
            'name': 'invoice.png',
            'res_model': 'account.move',
            'res_id': self.move.id,
            'mimetype': 'image/png',
            'datas': 'eA==',
        })
        self.params = self.env['ir.config_parameter'].sudo()
        self.params.set_param(
            'ai_vision.trigger_url',
            'https://trigger.test/api/v1/tasks/insilos-ai-vision-extract/trigger')
        self.params.set_param('ai_vision.trigger_secret', 'trigger-secret-test')
        self.params.set_param('ai.iap_endpoint', 'http://127.0.0.1:3099/openrouter/v1/proxy')
        self.params.set_param('ai_vision.model', 'vision/model-configured')
        account = self.env['iap.account'].get('ai_llm')
        self.wallet = self.env['iap.wallet'].get_wallet(self.move.company_id, iap_account=account)
        self.env['iap.ledger'].create_entry(
            self.wallet, 'topup', 10, 'ai_vision_action_test_topup')

    @patch('odoo.addons.ai_vision_iap.models.account_move.requests.post')
    def test_success_payload_uses_delegated_held_charge(self, post):
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {'id': 'run_123'}

        self.move.action_trigger_ai_extraction()

        post.assert_called_once()
        self.assertEqual(
            post.call_args.args[0],
            'https://trigger.test/api/v1/tasks/insilos-ai-vision-extract/trigger')
        self.assertEqual(post.call_args.kwargs['headers'], {
            'Authorization': 'Bearer trigger-secret-test',
            'Content-Type': 'application/json',
            'Idempotency-Key': f'ai_vision_account.move_{self.move.id}',
        })
        self.assertEqual(post.call_args.kwargs['timeout'], 5)
        envelope = post.call_args.kwargs['json']
        self.assertEqual(set(envelope), {'payload'})
        payload = envelope['payload']
        self.assertNotIn('trigger-secret-test', str(payload))
        charge = self.env['iap.charge'].search([
            ('wallet_id', '=', self.wallet.id),
            ('operation_id', '=', f'ai_vision_account.move_{self.move.id}'),
        ], order='id desc', limit=1)
        self.assertEqual(payload['schema_version'], '1.0')
        self.assertEqual(payload['company_id'], self.move.company_id.id)
        self.assertEqual(payload['record_model'], 'account.move')
        self.assertEqual(payload['record_id'], self.move.id)
        self.assertEqual(payload['operation_id'], charge.operation_id)
        self.assertEqual(payload['correlation_id'], charge.operation_id)
        self.assertEqual(payload['extraction_run_id'], charge.operation_id)
        self.assertEqual(payload['service_name'], 'ai_vision')
        self.assertEqual(payload['iap_endpoint'], 'http://127.0.0.1:3099/openrouter/v1/proxy')
        self.assertEqual(payload['model_hint'], 'vision/model-configured')
        self.assertEqual(payload['credit_metadata'], {'held_amount': charge.amount})
        self.assertTrue(payload['delegation_token'].startswith('iapd1.'))
        self.assertNotIn('account_token', payload)
        self.assertEqual(charge.wallet_id, self.wallet)
        self.assertEqual(charge.state, 'held')
        self.assertEqual(self.move.ai_trigger_run_id, 'run_123')
        self.assertEqual(self.move.ai_operation_id, charge.operation_id)

    @patch('odoo.addons.ai_vision_iap.models.account_move.requests.post', side_effect=RequestException)
    def test_dispatch_failure_rolls_back_hold(self, post):
        before = self.env['iap.charge'].search_count([])
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self.move.action_trigger_ai_extraction()
        self.env.invalidate_all()
        self.assertEqual(self.env['iap.charge'].search_count([]), before)

    @patch('odoo.addons.ai_vision_iap.models.account_move.requests.post')
    def test_response_without_run_id_rolls_back_hold(self, post):
        post.return_value.json.return_value = {}
        before = self.env['iap.charge'].search_count([])
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self.move.action_trigger_ai_extraction()
        self.env.invalidate_all()
        self.assertEqual(self.env['iap.charge'].search_count([]), before)

    def test_missing_urls_fail_before_hold(self):
        before = self.env['iap.charge'].search_count([])
        for key in (
                'ai_vision.trigger_url', 'ai_vision.trigger_secret', 'ai.iap_endpoint'):
            old = self.params.get_param(key)
            self.params.set_param(key, False)
            with self.assertRaises(UserError):
                self.move.action_trigger_ai_extraction()
            self.assertEqual(self.env['iap.charge'].search_count([]), before)
            self.params.set_param(key, old)
