# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HSEFacility(models.Model):
    _name = 'is.hse.facility'
    _description = 'Industrial Facility / Plant Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'company_id, name'

    name = fields.Char(string='Facility Name', required=True, tracking=True)
    code = fields.Char(string='Facility Code', required=True, index=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one('stock.warehouse', string='Associated Warehouse', domain="[('company_id', '=', company_id)]")
    
    address = fields.Char(string='Physical Address')
    industry_type = fields.Selection([
        ('chemical', 'Chemical Manufacturing & Storage'),
        ('textile', 'Textile & Garment / Dyeing'),
        ('electronics', 'Electronics & Semiconductor'),
        ('metal_working', 'Mechanical & Metal Fabrication'),
        ('food_beverage', 'Food & Beverage Processing'),
        ('pharmaceutical', 'Pharmaceutical & Cosmetics'),
        ('logistics', 'Warehouse & Freight Logistics'),
        ('general_manufacturing', 'General Light Manufacturing'),
    ], string='Industry Type', required=True, default='general_manufacturing', tracking=True)

    worker_count = fields.Integer(string='Total Workforce (Headcount)', default=50, tracking=True)
    
    # Environmental aspects
    wastewater_capacity_m3_day = fields.Float(string='Wastewater Discharge (m³/day)', default=0.0,
                                             help='Daily wastewater volume per Environmental Permit.')
    emission_classification = fields.Selection([
        ('none', 'No Industrial Emissions'),
        ('group_3', 'Group III (Low Emission / Periodic Observation)'),
        ('group_2', 'Group II (Medium Emission / Semi-Annual Monitoring)'),
        ('group_1', 'Group I (High Emission / Continuous Online CEMS)'),
    ], string='Emission Source Classification', default='none', tracking=True)

    environmental_permit_code = fields.Char(string='Environmental Permit Number', tracking=True)
    environmental_permit_date = fields.Date(string='Permit Issue Date')
    environmental_permit_expiry = fields.Date(string='Permit Expiry Date')

    # Fire Safety & OSH
    fire_hazard_category = fields.Selection([
        ('category_a', 'Category A — High Explosion / Flammable Gases'),
        ('category_b', 'Category B — Flammable Liquids & Dusts'),
        ('category_c', 'Category C — Solid Combustibles'),
        ('category_d', 'Category D — Incombustible Hot Processes'),
        ('category_e', 'Category E — Non-combustible Cold Materials'),
    ], string='Fire Hazard Classification', default='category_c', tracking=True)

    has_hazardous_chemicals = fields.Boolean(string='Stores Hazardous Chemicals', default=False)
    
    legal_register_ids = fields.One2many('is.hse.legal.register', 'facility_id', string='Legal Registers')
    legal_register_count = fields.Integer(string='Legal Registers Count', compute='_compute_register_count')

    @api.constrains('code', 'company_id')
    def _check_code_company_unique(self):
        for fac in self:
            if fac.code and self.search_count([('code', '=', fac.code), ('company_id', '=', fac.company_id.id), ('id', '!=', fac.id)]) > 0:
                raise ValidationError(_("Facility code '%s' must be unique per company!") % fac.code)

    @api.depends('legal_register_ids')
    def _compute_register_count(self):
        for fac in self:
            fac.legal_register_count = len(fac.legal_register_ids)

    def action_create_legal_register(self):
        self.ensure_one()
        register = self.env['is.hse.legal.register'].create({
            'name': f"Legal Register — {self.name} ({fields.Date.today().year})",
            'facility_id': self.id,
            'company_id': self.company_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'is.hse.legal.register',
            'res_id': register.id,
            'view_mode': 'form',
            'target': 'current',
        }
