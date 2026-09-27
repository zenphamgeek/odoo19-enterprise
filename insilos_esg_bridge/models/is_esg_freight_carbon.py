# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ESGFreightCarbon(models.Model):
    _name = 'is.esg.freight.carbon'
    _description = 'Scope 3 Category 4 Freight & Transportation Carbon Footprint'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Calculation Code', compute='_compute_name', store=True)
    case_id = fields.Many2one('logistics.idp.case', string='Logistics IDP Inbound Case', required=True, index=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', related='case_id.company_id', store=True)
    date = fields.Date(string='Calculation Date', default=fields.Date.today, required=True)

    transport_mode = fields.Selection([
        ('ocean_container', 'Ocean Container Vessel (0.015 kgCO₂e/t-km)'),
        ('ocean_bulk', 'Ocean Bulk Carrier (0.009 kgCO₂e/t-km)'),
        ('air_freight', 'Air Cargo (0.602 kgCO₂e/t-km)'),
        ('road_heavy_truck', 'Heavy Duty Truck (0.105 kgCO₂e/t-km)'),
        ('road_light_truck', 'Light Commercial Van (0.210 kgCO₂e/t-km)'),
        ('rail_freight', 'Freight Train (0.028 kgCO₂e/t-km)'),
    ], string='Transport Mode (GLEC Framework)', default='ocean_container', required=True, tracking=True)

    origin_port_or_city = fields.Char(string='Origin Port', tracking=True)
    destination_port_or_city = fields.Char(string='Destination Port', tracking=True)
    estimated_distance_km = fields.Float(string='Transport Distance (km)', default=1200.0, required=True, tracking=True)
    
    cargo_weight_ton = fields.Float(string='Shipment Cargo Weight (Tons)', required=True, tracking=True)
    
    emission_factor_kg_per_tkm = fields.Float(string='Emission Factor (kgCO2e per ton-km)', compute='_compute_emission_factor', store=True)
    
    gross_freight_emissions_kg_co2e = fields.Float(string='Gross Freight Carbon (kgCO₂e)', compute='_compute_carbon_metrics', store=True, tracking=True)
    gross_freight_emissions_t_co2e = fields.Float(string='Gross Freight Carbon (tCO₂e)', compute='_compute_carbon_metrics', store=True)

    # Paperless Digital Processing Offset Metric
    paperless_pages_processed = fields.Integer(string='Digital Document Pages Processed (IDP)', default=6)
    paperless_carbon_offset_kg = fields.Float(string='Digital Paperless Carbon Avoided (kgCO₂e)', compute='_compute_carbon_metrics', store=True)
    
    net_logistics_carbon_kg_co2e = fields.Float(string='Net Logistics Carbon Impact (kgCO₂e)', compute='_compute_carbon_metrics', store=True)

    esg_other_emission_id = fields.Many2one('esg.other.emission', string='Core ESG Carbon Ledger Entry', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get('esg_other_emission_id') for vals in vals_list):
            raise ValidationError(_("Freight estimates cannot be linked to the ESG ledger until verification is implemented."))
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('esg_other_emission_id'):
            raise ValidationError(_("Freight estimates cannot be linked to the ESG ledger until verification is implemented."))
        return super().write(vals)

    @api.depends('case_id.name', 'transport_mode')
    def _compute_name(self):
        for rec in self:
            c_name = rec.case_id.name or 'CASE'
            rec.name = f"CARBON-{c_name}-{rec.transport_mode or 'FREIGHT'}"

    @api.depends('transport_mode')
    def _compute_emission_factor(self):
        factors = {
            'ocean_container': 0.015,
            'ocean_bulk': 0.009,
            'air_freight': 0.602,
            'road_heavy_truck': 0.105,
            'road_light_truck': 0.210,
            'rail_freight': 0.028,
        }
        for rec in self:
            rec.emission_factor_kg_per_tkm = factors.get(rec.transport_mode, 0.015)

    @api.depends('cargo_weight_ton', 'estimated_distance_km', 'emission_factor_kg_per_tkm', 'paperless_pages_processed')
    def _compute_carbon_metrics(self):
        for rec in self:
            gross_kg = rec.cargo_weight_ton * rec.estimated_distance_km * rec.emission_factor_kg_per_tkm
            rec.gross_freight_emissions_kg_co2e = gross_kg
            rec.gross_freight_emissions_t_co2e = gross_kg / 1000.0
            
            # Paperless offset: 1 page ~ 0.009 kg CO2e saved (wood pulp & transport lifecycle)
            offset_kg = rec.paperless_pages_processed * 0.009
            rec.paperless_carbon_offset_kg = offset_kg
            rec.net_logistics_carbon_kg_co2e = max(0.0, gross_kg - offset_kg)

    def action_post_to_esg_ledger(self):
        self.ensure_one()
        # ponytail: estimates stay local until a verified factor/unit/source mapping exists.
        raise ValidationError(_(
            "Freight estimates cannot be posted to the ESG ledger until emission "
            "factor provenance, units and Scope 3 source mapping are verified."
        ))
