# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    has_chemical_items = fields.Boolean(string='Contains Chemical Items', compute='_compute_has_chemical_items', store=True)
    chemical_dossier_ids = fields.One2many('is.chemical.compliance.dossier', 'purchase_order_id', string='Chemical Compliance Dossiers')
    chemical_dossier_count = fields.Integer(string='Dossiers Count', compute='_compute_chemical_dossier_count')

    @api.depends('order_line.product_id')
    def _compute_has_chemical_items(self):
        for po in self:
            po.has_chemical_items = any(
                line.product_id.product_tmpl_id.is_hazardous_chemical or bool(line.product_id.product_tmpl_id.chemical_substance_id)
                for line in po.order_line if line.product_id
            )

    @api.depends('chemical_dossier_ids')
    def _compute_chemical_dossier_count(self):
        for po in self:
            po.chemical_dossier_count = len(po.chemical_dossier_ids)

    def action_create_chemical_dossier(self):
        """
        Creates a new Chemical Compliance Dossier from this purchase order lines.
        """
        self.ensure_one()
        Dossier = self.env['is.chemical.compliance.dossier']
        dossier_lines = []

        for line in self.order_line:
            prod = line.product_id
            tmpl = prod.product_tmpl_id if prod else False
            if tmpl and (tmpl.is_hazardous_chemical or tmpl.chemical_substance_id):
                dossier_lines.append((0, 0, {
                    'product_id': prod.id,
                    'chemical_substance_id': tmpl.chemical_substance_id.id if tmpl.chemical_substance_id else False,
                    'trade_name': prod.name,
                    'cas_number': tmpl.cas_number,
                    'hs_code': getattr(tmpl, 'hs_code', '') or '',
                    'quantity': line.product_qty,
                    'net_weight_kg': line.product_qty,  # Default 1:1 if unit is kg or estimated
                    'intended_use': 'Nguyên liệu sản xuất công nghiệp theo Đơn hàng ' + (self.name or ''),
                    'permit_id': tmpl.permit_ids[0].id if tmpl.permit_ids else False,
                }))

        if not dossier_lines:
            # Fallback for all lines if no specific chemical flag is set
            for line in self.order_line:
                if line.product_id:
                    dossier_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'trade_name': line.product_id.name,
                        'quantity': line.product_qty,
                        'net_weight_kg': line.product_qty,
                        'intended_use': 'Nguyên liệu sản xuất theo PO ' + (self.name or ''),
                    }))

        dossier = Dossier.create({
            'dossier_type': 'nsw_declaration',
            'partner_id': self.partner_id.id,
            'purchase_order_id': self.id,
            'importer_company_id': self.company_id.id,
            'line_ids': dossier_lines,
        })
        dossier.action_evaluate_obligations()

        action = self.env['ir.actions.act_window']._for_xml_id('insilos_chemical_trade_compliance.action_is_chemical_compliance_dossier')
        action['views'] = [(self.env.ref('insilos_chemical_trade_compliance.view_is_chemical_compliance_dossier_form').id, 'form')]
        action['res_id'] = dossier.id
        return action
