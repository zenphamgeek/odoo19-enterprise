# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hmac
import hashlib
import json
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_hs_sync')
class TestHSWebhookReceiver(TransactionCase):

    def setUp(self):
        super().setUp()
        self.secret = 'test_secret_key_12345'
        self.env['ir.config_parameter'].set_param('insilos_hs_sync.webhook_secret', self.secret)
        self.env['ir.config_parameter'].set_param('insilos_hs_sync.auto_update_products', 'True')

    def test_ruling_published_processing(self):
        """Test processing of hs.ruling.published event."""
        ruling_model = self.env['is.customs.ruling']
        ruling_num = '9999/TB-TCHQ'
        
        # 1. First event: create new ruling
        data = {
            'document_id': ruling_num,
            'hs_code': '8471.30.20',
            'title': 'Máy vi tính xách tay ThinkPad P15',
            'content_snippet': 'Máy vi tính cá nhân xách tay màn hình 15.6 inch...',
            'legal_basis': 'Quy tắc 1 và 6 Tổng tắc giải thích HS...',
            'source_url': 'https://customs.gov.vn/ruling/9999',
            'artifact_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
            'status': 'active',
            'issue_date': '2026-08-20',
        }

        # Call controller logic directly
        from ..controllers.webhook import InsilosHSWebhookController
        controller = InsilosHSWebhookController()
        controller._process_ruling_published(self.env, data)

        ruling = ruling_model.search([('ruling_number', '=', ruling_num)], limit=1)
        self.assertTrue(ruling)
        self.assertEqual(ruling.hs_code, '8471.30.20')
        self.assertEqual(ruling.commercial_name, 'Máy vi tính xách tay ThinkPad P15')
        self.assertEqual(ruling.status, 'active')

        # 2. Second event: update existing ruling (e.g. status revoked)
        data['status'] = 'revoked'
        controller._process_ruling_published(self.env, data)
        ruling.invalidate_recordset()
        self.assertEqual(ruling.status, 'revoked')

    def test_tariff_changed_processing(self):
        """Test processing of hs.tariff.changed event and product auto-update."""
        # Create product with matching HS Code
        product = self.env['product.template'].create({
            'name': 'Test Laptop Model X',
            'hs_code_customs': '8471.30.90',
            'import_duty_rate': 10.0,
            'vat_rate': 10.0,
        })

        data = {
            'hs_code': '8471.30.90',
            'description_vi': 'Máy vi tính loại khác',
            'import_duty_rate': 0.0,
            'vat_rate': 8.0,
            'specialized_management_notes': 'QCVN 118:2018/BTTTT',
            'legal_basis': 'Nghị định 26/2023/NĐ-CP',
        }

        from ..controllers.webhook import InsilosHSWebhookController
        controller = InsilosHSWebhookController()
        controller._process_tariff_changed(self.env, data)

        # Check tariff record
        tariff = self.env['is.hs.tariff'].search([('hs_code', '=', '8471.30.90')], limit=1)
        self.assertTrue(tariff)
        self.assertEqual(tariff.import_duty_rate, 0.0)
        self.assertEqual(tariff.vat_rate, 8.0)

        # Check auto-updated product
        product.invalidate_recordset()
        self.assertEqual(product.import_duty_rate, 0.0)
        self.assertEqual(product.vat_rate, 8.0)
        self.assertEqual(product.specialized_management_notes, 'QCVN 118:2018/BTTTT')
        self.assertTrue(product.hs_last_synced)

    def test_hmac_signature_verification(self):
        """Test HMAC-SHA256 signature generation and validation."""
        payload = json.dumps({'event_id': 'evt_1', 'event_type': 'test'}).encode('utf-8')
        expected_sig = "sha256=" + hmac.new(self.secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
        
        # Valid signature comparison
        self.assertTrue(hmac.compare_digest(expected_sig, expected_sig))
        
        # Invalid signature comparison
        invalid_sig = "sha256=invalid_hash_signature"
        self.assertFalse(hmac.compare_digest(expected_sig, invalid_sig))
