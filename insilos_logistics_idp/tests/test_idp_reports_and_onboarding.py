# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install', 'insilos_logistics_idp')
class TestIDPReportsAndOnboarding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.case = cls.env['logistics.idp.case'].create({
            'name': 'CASE-LOG-2026-TEST-REP-01',
            'po_reference': 'PO-2026-0099',
            'supplier_reference': 'ABC Chemical Supplies Ltd',
            'shipment_reference': 'BL-SGN-2026-88',
        })

    def test_01_idp_report_action_exists(self):
        """Verify QWeb action report for Logistics IDP Case Dossier."""
        rep = self.env.ref('insilos_logistics_idp.action_report_logistics_idp_case_dossier')
        self.assertTrue(rep)
        self.assertEqual(rep.report_type, 'qweb-pdf')

    def test_02_idp_report_is_internal_review_only(self):
        template = self.env.ref('insilos_logistics_idp.report_logistics_idp_case_dossier_doc')
        self.assertIn('HỒ SƠ NỘI BỘ — CHỜ RÀ SOÁT:', template.arch)
        self.assertIn('không phải thông quan hải quan, phê duyệt, chứng nhận hoặc kết quả sàng lọc có thẩm quyền', template.arch)
        self.assertIn('Kết quả sàng lọc nội bộ tự động:', template.arch)

    def test_03_idp_onboarding_hub_action(self):
        """Verify Logistics IDP Onboarding Hub action and view."""
        hub = self.env.ref('insilos_logistics_idp.action_is_logistics_idp_onboarding_hub')
        self.assertTrue(hub)
        self.assertEqual(hub.res_model, 'res.config.settings')
        self.assertEqual(hub.view_mode, 'form')
