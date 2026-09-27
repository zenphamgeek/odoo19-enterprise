# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_hazardous_chemical = fields.Boolean(string='Hazardous Chemical', default=False,
                                           help='Flag indicating product is subject to chemical safety regulations and requires SDS/GHS compliance.')
    chemical_substance_id = fields.Many2one('is.hse.chemical.substance', string='Chemical Substance Master',
                                            help='Linked master chemical entry with standardized CAS number and OELs.')
    cas_number = fields.Char(related='chemical_substance_id.cas_number', string='CAS Registry No.', store=True, readonly=False)
    un_number = fields.Char(related='chemical_substance_id.un_number', string='UN Number', store=True, readonly=False)
    
    sds_id = fields.Many2one('is.hse.sds', string='Primary SDS (16-Section)',
                             domain="[('substance_id', '=', chemical_substance_id)]")

    ghs_signal_word = fields.Selection([
        ('danger', 'DANGER (Nguy hiểm)'),
        ('warning', 'WARNING (Cảnh báo)'),
        ('none', 'None'),
    ], string='GHS Signal Word', default='none')

    ghs_flammable = fields.Boolean(string='Flammable (GHS02)')
    ghs_corrosive = fields.Boolean(string='Corrosive (GHS05)')
    ghs_toxic = fields.Boolean(string='Acute Toxicity (GHS06)')
    ghs_health_hazard = fields.Boolean(string='Health Hazard (GHS08)')
    ghs_environmental = fields.Boolean(string='Environmental Hazard (GHS09)')

    permit_ids = fields.Many2many('is.hse.product.permit', 'product_template_hse_permit_rel',
                                  'product_tmpl_id', 'permit_id', string='Accompanying Permits & Certificates (Giấy phép đi kèm)')
    permit_count = fields.Integer(string='Permits Count', compute='_compute_permit_count')
    has_valid_permits = fields.Boolean(string='Has Valid Permits', compute='_compute_permit_count',
                                       help='True if at least one accompanying permit is active and valid.')

    @api.depends('permit_ids', 'permit_ids.state')
    def _compute_permit_count(self):
        for prod in self:
            prod.permit_count = len(prod.permit_ids)
            prod.has_valid_permits = any(p.state in ('valid', 'expiring_soon') for p in prod.permit_ids)

    def action_view_hse_permits(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('insilos_hse_compliance.action_is_hse_product_permit')
        action['domain'] = [('id', 'in', self.permit_ids.ids)]
        action['context'] = {
            'default_product_template_ids': [(4, self.id)],
            'default_chemical_substance_id': self.chemical_substance_id.id if self.chemical_substance_id else False,
        }
        return action

    @api.onchange('chemical_substance_id')
    def _onchange_chemical_substance_id(self):
        if self.chemical_substance_id:
            sub = self.chemical_substance_id
            self.is_hazardous_chemical = sub.hazard_classification != 'non_hazardous'
            self.ghs_signal_word = sub.ghs_signal_word
            self.ghs_flammable = sub.ghs_flammable
            self.ghs_corrosive = sub.ghs_corrosive
            self.ghs_toxic = sub.ghs_toxic
            self.ghs_health_hazard = sub.ghs_health_hazard
            self.ghs_environmental = sub.ghs_environmental
            if sub.sds_ids:
                self.sds_id = sub.sds_ids[0].id
