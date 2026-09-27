# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    chemical_dossier_id = fields.Many2one('is.chemical.compliance.dossier', string='Chemical Compliance Dossier',
                                          copy=False, tracking=True)
    has_chemical_items = fields.Boolean(string='Contains Chemical Items', compute='_compute_chemical_status', store=True)
    is_chemical_compliance_cleared = fields.Boolean(string='Chemical Trade Compliance Cleared',
                                                   compute='_compute_chemical_status', store=True)

    @api.depends('move_ids.product_id', 'chemical_dossier_id', 'chemical_dossier_id.state')
    def _compute_chemical_status(self):
        for picking in self:
            picking.has_chemical_items = any(
                move.product_id.product_tmpl_id.is_hazardous_chemical or bool(move.product_id.product_tmpl_id.chemical_substance_id)
                for move in picking.move_ids if move.product_id
            )
            if picking.chemical_dossier_id:
                picking.is_chemical_compliance_cleared = False
            else:
                picking.is_chemical_compliance_cleared = not picking.has_chemical_items

    def action_view_chemical_dossier(self):
        self.ensure_one()
        if not self.chemical_dossier_id:
            # Auto-create if PO linked
            if hasattr(self, 'purchase_id') and self.purchase_id:
                return self.purchase_id.action_create_chemical_dossier()
            dossier = self.env['is.chemical.compliance.dossier'].create({
                'partner_id': self.partner_id.id if self.partner_id else False,
                'picking_id': self.id,
                'importer_company_id': self.company_id.id,
            })
            self.chemical_dossier_id = dossier.id

        action = self.env['ir.actions.act_window']._for_xml_id('insilos_chemical_trade_compliance.action_is_chemical_compliance_dossier')
        action['views'] = [(self.env.ref('insilos_chemical_trade_compliance.view_is_chemical_compliance_dossier_form').id, 'form')]
        action['res_id'] = self.chemical_dossier_id.id
        return action
