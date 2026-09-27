# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install', 'insilos_hs_sync')
class TestHSReportsAndOnboarding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ruling = cls.env['is.customs.ruling'].create({
            'ruling_number': 'TEST-9999/TB-TCHQ',
            'issuing_authority': 'Tổng cục Hải quan Test',
            'hs_code': '8471.30.20',
            'commercial_name': 'Máy tính xách tay Laptop Model X',
            'technical_description': 'Máy xử lý dữ liệu tự động kỹ thuật số loại xách tay, khối lượng dưới 10kg.',
            'status': 'active',
        })

        cls.tariff = cls.env['is.hs.tariff'].create({
            'hs_code': '8471.30.20',
            'description_vi': 'Máy tính xách tay, kể cả loại mini (notebook và subnotebook)',
            'import_duty_rate': 0.0,
            'vat_rate': 10.0,
            'unit': 'Cái',
        })

    def test_01_hs_report_actions_exist(self):
        """Verify QWeb action reports for Customs Ruling and HS Tariff are loaded."""
        rep_ruling = self.env.ref('insilos_hs_sync.action_report_hs_customs_ruling')
        self.assertTrue(rep_ruling)
        self.assertEqual(rep_ruling.report_type, 'qweb-pdf')

        rep_tariff = self.env.ref('insilos_hs_sync.action_report_hs_tariff_item')
        self.assertTrue(rep_tariff)
        self.assertEqual(rep_tariff.report_type, 'qweb-pdf')

    def test_02_hs_onboarding_hub_action(self):
        """Verify HS Onboarding Hub action and view."""
        hub = self.env.ref('insilos_hs_sync.action_is_hs_onboarding_hub')
        self.assertTrue(hub)
        self.assertEqual(hub.res_model, 'res.config.settings')
        self.assertEqual(hub.view_mode, 'form')
