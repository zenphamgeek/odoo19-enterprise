# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class IsHsTariff(models.Model):
    _name = 'is.hs.tariff'
    _description = 'Vietnam Customs HS Tariff Schedule'
    _order = 'hs_code asc, id desc'
    _rec_name = 'display_name'

    hs_code = fields.Char(string='HS Code (8-digit)', required=True, index=True)
    description_vi = fields.Text(string='Vietnamese Description', required=True)
    description_en = fields.Text(string='English Description')
    import_duty_rate = fields.Float(string='Preferential Import Duty (%)', digits=(5, 2))
    export_duty_rate = fields.Float(string='Export Duty (%)', digits=(5, 2))
    vat_rate = fields.Float(string='VAT Rate (%)', digits=(5, 2), default=10.0)
    unit = fields.Char(string='Unit of Measure')
    specialized_management_notes = fields.Text(string='Specialized Management')
    legal_basis = fields.Text(string='Legal Basis')
    valid_from = fields.Date(string='Valid From')
    valid_to = fields.Date(string='Valid To')
    source_url = fields.Char(string='Source URL')
    active = fields.Boolean(string='Active', default=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    ruling_count = fields.Integer(string='Rulings Count', compute='_compute_ruling_count')
    product_template_count = fields.Integer(string='Matching Products Count', compute='_compute_product_template_count')

    @api.depends('hs_code', 'description_vi')
    def _compute_display_name(self):
        for rec in self:
            desc = (rec.description_vi or '')[:60]
            rec.display_name = f"[{rec.hs_code}] {desc}" if rec.hs_code else (rec.description_vi or _("HS Tariff"))

    def _compute_ruling_count(self):
        ruling_model = self.env['is.customs.ruling']
        for rec in self:
            rec.ruling_count = ruling_model.search_count([('hs_code', '=', rec.hs_code)]) if rec.hs_code else 0

    def _compute_product_template_count(self):
        product_template_model = self.env['product.template']
        for rec in self:
            rec.product_template_count = product_template_model.search_count([('hs_code_customs', '=', rec.hs_code)]) if rec.hs_code else 0

    def action_view_rulings(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('insilos_hs_sync.action_is_customs_ruling')
        action['domain'] = [('hs_code', '=', self.hs_code)]
        action['context'] = {'default_hs_code': self.hs_code}
        return action

    def action_view_matching_products(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('product.product_template_action')
        action['domain'] = [('hs_code_customs', '=', self.hs_code)]
        action['context'] = {'default_hs_code_customs': self.hs_code}
        return action
