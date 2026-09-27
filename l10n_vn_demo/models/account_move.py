# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _l10n_vn_demo_sync_demo_accounting(self):
        """Ensure Vietnamese Dong (VND) exchange rate is configured and demo
        accounting moves, sales orders, and purchase orders are properly synchronized
        with accurate multicurrency balances under Circular 200/2014/TT-BTC.
        """
        # 1. Ensure VND is active and has an official exchange rate against USD (25,400 VND/USD)
        vnd = self.env.ref('base.VND', raise_if_not_found=False)
        main_company = self.env.ref('base.main_company', raise_if_not_found=False)
        if vnd and main_company:
            if not vnd.active:
                vnd.active = True
            rate = self.env['res.currency.rate'].search([
                ('currency_id', '=', vnd.id),
                ('company_id', '=', main_company.id),
            ], limit=1)
            if not rate:
                rate = self.env['res.currency.rate'].create({
                    'name': '2026-01-01',
                    'rate': 25400.0,
                    'currency_id': vnd.id,
                    'company_id': main_company.id,
                })
            elif rate.rate != 25400.0:
                rate.write({'rate': 25400.0})

        # 2. Sync demo invoices: ensure invoice_currency_rate is 25400 and balances are recalculated
        inv_xmlids = [
            'l10n_vn_demo.invoice_vn_customer_1',
            'l10n_vn_demo.invoice_vn_customer_2',
            'l10n_vn_demo.invoice_vn_customer_3',
            'l10n_vn_demo.invoice_vn_supplier_1',
            'l10n_vn_demo.invoice_vn_supplier_2',
            'l10n_vn_demo.invoice_vn_supplier_3',
        ]
        for xmlid in inv_xmlids:
            inv = self.env.ref(xmlid, raise_if_not_found=False)
            if inv:
                receivable_payable = inv.line_ids.filtered(lambda l: l.display_type == 'payment_term')
                needs_sync = (
                    inv.invoice_currency_rate != 25400.0
                    or any(abs(l.balance) > 100000.0 for l in receivable_payable)
                )
                if needs_sync:
                    if inv.state == 'posted':
                        inv.button_draft()
                    inv.write({'invoice_currency_rate': 25400.0})
                    inv.action_post()

        # 3. Sync demo sales orders to VND pricelist
        pricelist = self.env.ref('l10n_vn_demo.pricelist_vn_industrial_vnd', raise_if_not_found=False)
        if not pricelist and vnd:
            pricelist = self.env['product.pricelist'].search([('currency_id', '=', vnd.id)], limit=1)
        if pricelist:
            for so_xmlid in ['l10n_vn_demo.sale_order_vn_1', 'l10n_vn_demo.sale_order_vn_2']:
                so = self.env.ref(so_xmlid, raise_if_not_found=False)
                if so and so.pricelist_id != pricelist:
                    so.write({'pricelist_id': pricelist.id})

        # 4. Sync demo purchase orders to VND currency
        if vnd:
            for po_xmlid in [
                'l10n_vn_demo.purchase_order_vn_1',
                'l10n_vn_demo.purchase_order_vn_2',
                'l10n_vn_demo.purchase_order_vn_3',
            ]:
                po = self.env.ref(po_xmlid, raise_if_not_found=False)
                if po and po.currency_id != vnd:
                    po.write({'currency_id': vnd.id})
