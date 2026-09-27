# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class IsCustomsRuling(models.Model):
    _name = 'is.customs.ruling'
    _description = 'Vietnam Customs Advance Classification Ruling'
    _order = 'issue_date desc, id desc'
    _rec_name = 'display_name'

    ruling_number = fields.Char(string='Ruling Number', required=True, index=True)
    issuing_authority = fields.Char(string='Issuing Authority', default='General Department of Vietnam Customs')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    hs_code = fields.Char(string='Determined HS Code (8-digit)', required=True, index=True)
    commercial_name = fields.Char(string='Commercial Name')
    technical_description = fields.Text(string='Technical Description')
    classification_rationale = fields.Text(string='Classification Rationale')
    source_url = fields.Char(string='Source URL')
    artifact_sha256 = fields.Char(string='Artifact SHA-256 Provenance', index=True)
    status = fields.Selection([
        ('active', 'Active'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ], string='Status', default='active', index=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    product_template_count = fields.Integer(string='Matching Products Count', compute='_compute_product_template_count')

    @api.depends('ruling_number', 'commercial_name', 'hs_code')
    def _compute_display_name(self):
        for rec in self:
            name_parts = [p for p in [rec.ruling_number, rec.commercial_name, f"[{rec.hs_code}]" if rec.hs_code else False] if p]
            rec.display_name = " - ".join(name_parts) if name_parts else (rec.ruling_number or _("Customs Ruling"))

    def _compute_product_template_count(self):
        product_template_model = self.env['product.template']
        for rec in self:
            if rec.hs_code:
                rec.product_template_count = product_template_model.search_count([('hs_code_customs', '=', rec.hs_code)])
            else:
                rec.product_template_count = 0

    def action_view_matching_products(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('product.product_template_action')
        action['domain'] = [('hs_code_customs', '=', self.hs_code)]
        action['context'] = {'default_hs_code_customs': self.hs_code}
        return action
