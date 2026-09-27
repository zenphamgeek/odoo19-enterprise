import time
import uuid
from unittest.mock import patch

from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError
from odoo.modules.registry import Registry
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'openrouter_ai')
class TestOpenRouterDurableLog(TransactionCase):
    def setUp(self):
        super().setUp()
        self.operations = []

    def tearDown(self):
        with Registry(self.env.cr.dbname).cursor() as cr:
            cr.execute('DELETE FROM openrouter_log WHERE operation_id = ANY(%s)', [self.operations])
            cr.commit()
        super().tearDown()

    def _vals(self, status, error_message=None):
        operation = f'test-durable-{uuid.uuid4().hex}:model:0'
        self.operations.append(operation)
        return {
            'operation_id': operation, 'tenant_id': 'test-tenant',
            'company_id': self.env.company.id, 'policy_version': 'test',
            'credit_budget': 1, 'used_model_name': 'test/model',
            'status': status, 'error_message': error_message,
        }

    def _durable_logs(self, operation):
        with Registry(self.env.cr.dbname).cursor(readonly=True) as cr:
            env = api.Environment(cr, SUPERUSER_ID, {'allowed_company_ids': [self.env.company.id]})
            return env['openrouter.log'].search([('operation_id', '=', operation)]).read()

    def test_failed_provider_user_error_survives_outer_rollback(self):
        vals = self._vals('failed', 'HTTP 500')
        with self.env.cr.savepoint() as savepoint:
            self.env['openrouter.router']._create_durable_log(vals)
            with self.assertRaises(UserError):
                raise UserError('Provider failed')
            savepoint.rollback()
        logs = self._durable_logs(vals['operation_id'])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['error_message'], 'HTTP 500')

    def test_success_survives_outer_rollback_without_business_leak(self):
        vals = self._vals('success')
        with self.env.cr.savepoint() as savepoint:
            leaked = self.env['openrouter.model'].create({'name': 'Must Roll Back', 'model_id': vals['operation_id']})
            self.env['openrouter.router']._create_durable_log(vals)
            savepoint.rollback()
        logs = self._durable_logs(vals['operation_id'])
        self.assertEqual(len(logs), 1)
        self.assertFalse(self.env['openrouter.model'].search([('id', '=', leaked.id)]))
        self.assertNotIn('secret', str(logs))

    def test_duplicate_operation_is_idempotent(self):
        vals = self._vals('success')
        router = self.env['openrouter.router']
        router._create_durable_log(vals)
        router._create_durable_log(vals)
        self.assertEqual(len(self._durable_logs(vals['operation_id'])), 1)

    def test_uncommitted_fk_does_not_block_provider_result(self):
        vals = self._vals('success')
        vals['model_id'] = self.env['openrouter.model'].create({
            'name': 'Uncommitted', 'model_id': vals['operation_id'],
        }).id
        started = time.monotonic()
        self.env['openrouter.router']._create_durable_log(vals)
        self.assertLess(time.monotonic() - started, 3)
        self.assertFalse(self._durable_logs(vals['operation_id']))

    def test_catalog_token_destination_requires_exact_trusted_iap_endpoint(self):
        model = self.env['openrouter.model']
        with patch.dict('os.environ', {'INSILOS_TRUSTED_IAP_URL': 'https://iap.example.com'}, clear=True):
            for endpoint in ('https://iap.example.com', 'https://iap.example.com/', 'https://iap.example.com/jsonrpc'):
                self.assertEqual(model._iap_catalog_url(endpoint), 'https://iap.example.com/openrouter/v1/models')
            for endpoint in ('http://iap.example.com/jsonrpc', 'https://evil.example/jsonrpc',
                             'https://iap.example.com/other', 'https://iap.example.com/jsonrpc?redirect=evil',
                             'https://attacker@iap.example.com/jsonrpc'):
                with self.assertRaises(UserError):
                    model._iap_catalog_url(endpoint)
        with patch.dict('os.environ', {'INSILOS_TRUSTED_IAP_URL': ' https://iap.example.com:443/jsonrpc '}, clear=True):
            self.assertEqual(model._iap_catalog_url(' https://iap.example.com/ '), 'https://iap.example.com:443/openrouter/v1/models')
        with patch.dict('os.environ', {'INSILOS_LOCAL_DEV': 'true'}, clear=True):
            self.assertEqual(model._iap_catalog_url('http://127.0.0.1:3099/jsonrpc'), 'http://127.0.0.1:3099/openrouter/v1/models')
            with self.assertRaises(UserError):
                model._iap_catalog_url('http://localhost:3099/jsonrpc')
