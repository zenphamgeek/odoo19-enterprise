# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase, tagged
from ..services.hse_client import HSEKnowledgeClient


@tagged('post_install', '-at_install', 'insilos_hse_compliance')
class TestHSEClient(TransactionCase):

    def setUp(self):
        super(TestHSEClient, self).setUp()
        self.client = HSEKnowledgeClient(self.env)

    @patch('urllib.request.urlopen')
    def test_01_get_substance_by_cas(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'cas_number': '67-64-1',
            'name': 'Acetone',
            'formula': 'C3H6O',
            'hazard_classification': 'conditional',
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = self.client.get_substance_by_cas('67-64-1')
        self.assertEqual(res.get('cas_number'), '67-64-1')
        self.assertEqual(res.get('name'), 'Acetone')

    @patch('urllib.request.urlopen')
    def test_02_trigger_on_demand_crawl(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'task_id': 'task_crawl_001',
            'status': 'dispatched',
            'topic': 'QCVN 05:2023/BTNMT',
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = self.client.trigger_on_demand_crawl('QCVN 05:2023/BTNMT')
        self.assertEqual(res.get('status'), 'dispatched')
        self.assertEqual(res.get('task_id'), 'task_crawl_001')

    @patch('urllib.request.urlopen')
    def test_03_evaluate_facility_applicability(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'facility_id': 'FAC-01',
            'applicable_laws_count': 12,
            'obligations': [
                {'title': 'Quan trắc môi trường định kỳ', 'frequency': 'quarterly'}
            ]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = self.client.evaluate_facility_applicability({'facility_code': 'FAC-01', 'industry': 'chemical'})
        self.assertEqual(res.get('applicable_laws_count'), 12)
        self.assertEqual(len(res.get('obligations', [])), 1)
