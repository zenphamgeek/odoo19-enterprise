# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase, tagged
from ..services.hermes_client import HermesHSClient


@tagged('post_install', '-at_install', 'insilos_hs_sync')
class TestHermesHSClient(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].set_param('insilos_hs_sync.hermes_api_url', 'http://127.0.0.1:8000')
        self.client = HermesHSClient(self.env)

    @patch('urllib.request.urlopen')
    def test_search_hs_codes_mock(self, mock_urlopen):
        """Test searching HS codes via mocked Hermes API."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"results": [{"hs_code": "8471.30.20", "description": "ThinkPad"}]}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = self.client.search_hs_codes("ThinkPad", limit=5)
        self.assertEqual(res.get('status'), 'success')
        self.assertEqual(res.get('code'), 200)
        self.assertIn('results', res.get('data', {}))

        # Verify audit log was recorded
        log = self.env['is.hs.sync.log'].search([('direction', '=', 'outbound_api')], order='id desc', limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, 'success')

    @patch('urllib.request.urlopen')
    def test_classify_product_mock(self, mock_urlopen):
        """Test AI product classification via mocked Hermes API."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"candidates": [{"hs_code": "8471.30.20", "confidence": 0.95}]}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = self.client.classify_product(
            title="Dell Precision 5570 Laptop",
            description="Intel Core i7, 32GB RAM, 15.6 inch screen",
            technical_specs="Laptop computer with portable power source"
        )
        self.assertEqual(res.get('status'), 'success')
        self.assertIn('candidates', res.get('data', {}))
