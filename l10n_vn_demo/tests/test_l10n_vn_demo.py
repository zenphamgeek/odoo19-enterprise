# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestL10nVnDemo(TransactionCase):

    def test_01_partners_and_accounts(self):
        """Verify Vietnamese industrial partners and Circular 200/2014 accounts."""
        vinfast = self.env.ref('l10n_vn_demo.res_partner_customer_vn_1')
        self.assertTrue(vinfast.exists())
        self.assertEqual(vinfast.property_account_receivable_id.code, '131')

        tancang = self.env.ref('l10n_vn_demo.res_partner_customer_vn_4')
        self.assertTrue(tancang.exists())
        self.assertEqual(tancang.property_account_receivable_id.code, '131')

        hoaphat = self.env.ref('l10n_vn_demo.res_partner_supplier_vn_1')
        self.assertTrue(hoaphat.exists())
        self.assertEqual(hoaphat.property_account_payable_id.code, '331')

        cadivi = self.env.ref('l10n_vn_demo.res_partner_supplier_vn_2')
        self.assertTrue(cadivi.exists())
        self.assertEqual(cadivi.property_account_payable_id.code, '331')

    def test_02_products_and_boms(self):
        """Verify products, workcenters, and multi-level BOMs."""
        vlift = self.env.ref('l10n_vn_demo.product_vn_1')
        semitrailer = self.env.ref('l10n_vn_demo.product_vn_2')
        chassis = self.env.ref('l10n_vn_demo.product_vn_4')
        pcb = self.env.ref('l10n_vn_demo.product_vn_14')

        self.assertEqual(vlift.default_code, 'EQ-VLIFT-2500E')
        self.assertEqual(vlift.tracking, 'serial')
        self.assertEqual(semitrailer.default_code, 'TR-TRAIL-40HC')
        self.assertEqual(chassis.default_code, 'SF-CHASSIS-25E')
        self.assertEqual(pcb.tracking, 'serial')

        bom_vlift = self.env.ref('l10n_vn_demo.mrp_bom_vlift')
        self.assertEqual(bom_vlift.product_tmpl_id, vlift.product_tmpl_id)
        self.assertGreaterEqual(len(bom_vlift.bom_line_ids), 4)
        self.assertGreaterEqual(len(bom_vlift.operation_ids), 4)

        bom_chassis = self.env.ref('l10n_vn_demo.mrp_bom_chassis')
        self.assertEqual(bom_chassis.product_tmpl_id, chassis.product_tmpl_id)
        self.assertGreaterEqual(len(bom_chassis.bom_line_ids), 3)

    def test_03_stock_quants_and_inventory(self):
        """Verify initial stock quants, lots, and serial tracking."""
        steel = self.env.ref('l10n_vn_demo.product_vn_9')
        self.assertGreater(steel.qty_available, 0)
        cable = self.env.ref('l10n_vn_demo.product_vn_12')
        self.assertGreater(cable.qty_available, 0)

        # Serial number tracking: ARM Cortex-M4 PCB should have individual serials
        pcb = self.env.ref('l10n_vn_demo.product_vn_14')
        self.assertGreaterEqual(pcb.qty_available, 8.0)
        sn1 = self.env.ref('l10n_vn_demo.sn_raw_pcb_01')
        self.assertTrue(sn1.exists())
        self.assertEqual(sn1.product_id, pcb)

    def test_04_mrp_productions(self):
        """Verify MOs are confirmed and scheduled on Gantt / Shop floor."""
        mo1 = self.env.ref('l10n_vn_demo.mrp_production_vn_1')
        self.assertIn(mo1.state, ['confirmed', 'progress', 'to_close', 'done'])
        self.assertGreaterEqual(len(mo1.workorder_ids), 4)

        mo2 = self.env.ref('l10n_vn_demo.mrp_production_vn_2')
        self.assertIn(mo2.state, ['confirmed', 'progress', 'to_close', 'done'])

        mo3 = self.env.ref('l10n_vn_demo.mrp_production_vn_3')
        self.assertIn(mo3.state, ['confirmed', 'progress', 'to_close', 'done'])
        self.assertTrue(any(wo.state == 'progress' for wo in mo3.workorder_ids))

    def test_05_account_moves_and_multicurrency(self):
        """Verify posted customer invoices, vendor bills, VND rate, and GL balances."""
        vnd = self.env.ref('base.VND')
        main_company = self.env.ref('base.main_company')
        rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', vnd.id),
            ('company_id', '=', main_company.id),
        ], limit=1)
        self.assertTrue(rate.exists(), "VND exchange rate record must exist")
        self.assertEqual(rate.rate, 25400.0)

        inv1 = self.env.ref('l10n_vn_demo.invoice_vn_customer_1')
        bill1 = self.env.ref('l10n_vn_demo.invoice_vn_supplier_1')

        self.assertEqual(inv1.state, 'posted')
        self.assertEqual(bill1.state, 'posted')
        self.assertEqual(inv1.currency_id.name, 'VND')
        self.assertEqual(bill1.currency_id.name, 'VND')

        # Multi-currency exchange rate check
        self.assertEqual(inv1.invoice_currency_rate, 25400.0)
        self.assertEqual(bill1.invoice_currency_rate, 25400.0)

        # General Ledger company currency (USD) balances must be realistic and scaled
        inv1_term = inv1.line_ids.filtered(lambda l: l.display_type == 'payment_term')
        self.assertEqual(round(inv1_term.balance, 2), 41358.27)

        bill1_term = bill1.line_ids.filtered(lambda l: l.display_type == 'payment_term')
        self.assertEqual(round(bill1_term.balance, 2), -16911.42)

        # GL debits and credits must be balanced
        for inv_xmlid in [
            'l10n_vn_demo.invoice_vn_customer_1',
            'l10n_vn_demo.invoice_vn_customer_2',
            'l10n_vn_demo.invoice_vn_customer_3',
            'l10n_vn_demo.invoice_vn_supplier_1',
            'l10n_vn_demo.invoice_vn_supplier_2',
            'l10n_vn_demo.invoice_vn_supplier_3',
        ]:
            move = self.env.ref(inv_xmlid)
            total_balance = sum(move.line_ids.mapped('balance'))
            self.assertAlmostEqual(total_balance, 0.0, places=2, msg=f"Move {inv_xmlid} GL lines not balanced")

    def test_06_sales_and_purchases(self):
        """Verify Sales Orders and Purchase Orders in VND currency."""
        so1 = self.env.ref('l10n_vn_demo.sale_order_vn_1')
        self.assertEqual(so1.currency_id.name, 'VND')
        self.assertEqual(so1.pricelist_id.currency_id.name, 'VND')
        self.assertEqual(so1.amount_total, 2295000000.0)

        so2 = self.env.ref('l10n_vn_demo.sale_order_vn_2')
        self.assertEqual(so2.currency_id.name, 'VND')

        po1 = self.env.ref('l10n_vn_demo.purchase_order_vn_1')
        self.assertEqual(po1.currency_id.name, 'VND')
        self.assertEqual(po1.amount_total, 537000000.0)

        po2 = self.env.ref('l10n_vn_demo.purchase_order_vn_2')
        self.assertEqual(po2.currency_id.name, 'VND')

    def test_07_fleet_and_crm(self):
        """Verify fleet vehicles and calibrated CRM industrial pipeline."""
        truck1 = self.env.ref('l10n_vn_demo.vehicle_vn_tractor_1')
        self.assertTrue(truck1.license_plate)
        self.assertEqual(truck1.model_id.name, 'Xcient GT 440PS Prime Mover (Đầu kéo 6x4)')

        lead1 = self.env.ref('l10n_vn_demo.crm_lead_vn_1')
        self.assertGreater(lead1.expected_revenue, 0)
        self.assertLess(lead1.expected_revenue, 1000000.0, "Expected revenue must be calibrated in company USD")
        self.assertEqual(lead1.probability, 80.0)
