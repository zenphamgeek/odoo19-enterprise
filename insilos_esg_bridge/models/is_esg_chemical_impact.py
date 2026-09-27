# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ESGChemicalImpact(models.Model):
    _name = 'is.esg.chemical.impact'
    _description = 'Chemical Material Environmental Footprint & Scope 1 Process Emissions'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Analysis Code', compute='_compute_name', store=True)
    tracking_id = fields.Many2one('is.chemical.usage.tracking', string='Chemical Usage Tracking Record', required=True, index=True, tracking=True)
    chemical_substance_id = fields.Many2one('is.hse.chemical.substance', string='Chemical Substance', related='tracking_id.chemical_substance_id', store=True)
    cas_number = fields.Char(related='chemical_substance_id.cas_number', string='CAS Registry No.', store=True)
    company_id = fields.Many2one('res.company', string='Company', related='tracking_id.company_id', store=True)
    facility_id = fields.Many2one('is.hse.facility', string='Operating Facility', related='tracking_id.facility_id', store=True)

    reporting_year = fields.Integer(related='tracking_id.reporting_year', string='Reporting Year', store=True)
    total_consumed_kg = fields.Float(related='tracking_id.consumed_in_production_kg', string='Total Chemical Consumed (kg)', store=True)
    process_loss_kg = fields.Float(related='tracking_id.loss_or_evaporation_kg', string='Process Loss Evaporation (kg)', store=True)

    is_ghs_environmental = fields.Boolean(related='chemical_substance_id.ghs_environmental', string='GHS09 Environmental Toxicity', store=True)
    ghs_signal_word = fields.Selection(related='chemical_substance_id.ghs_signal_word', string='GHS Signal Word', store=True)

    # VOC & Process Emission conversion
    volatile_organic_fraction = fields.Float(string='Volatile Fraction (% VOC Content)', default=25.0,
                                             help='Percentage of chemical that volatilizes during manufacturing.')
    voc_emissions_kg = fields.Float(string='Calculated VOC Emissions (kg)', compute='_compute_environmental_metrics', store=True)
    
    gwp_factor = fields.Float(string='GWP (Global Warming Potential Factor)', default=1.0,
                              help='Direct GWP multiplier (e.g. 1.0 for CO2, 28.0 for CH4, higher for Fluorinated Gases).')
    process_ghg_emissions_kg_co2e = fields.Float(string='Scope 1 Process GHG Emissions (kgCO₂e)', compute='_compute_environmental_metrics', store=True)

    environmental_hazard_rating = fields.Selection([
        ('low', 'Low Environmental Impact'),
        ('moderate', 'Moderate Priority'),
        ('high', 'High Environmental Concern (GHS09 / Restricted)'),
        ('critical', 'Critical Hazard / Ozone Depleting'),
    ], string='ESG Material Hazard Class', compute='_compute_environmental_metrics', store=True)

    esg_other_emission_id = fields.Many2one('esg.other.emission', string='Linked ESG Scope 1 Ledger Entry', readonly=True)

    @api.depends('chemical_substance_id.name', 'reporting_year')
    def _compute_name(self):
        for rec in self:
            c_name = rec.chemical_substance_id.name or 'CHEM'
            rec.name = f"ESG-CHEM-{c_name}-{rec.reporting_year or 'YEAR'}"

    @api.depends('process_loss_kg', 'volatile_organic_fraction', 'gwp_factor', 'is_ghs_environmental', 'total_consumed_kg')
    def _compute_environmental_metrics(self):
        for rec in self:
            voc_kg = rec.process_loss_kg * (rec.volatile_organic_fraction / 100.0)
            rec.voc_emissions_kg = voc_kg
            rec.process_ghg_emissions_kg_co2e = voc_kg * max(1.0, rec.gwp_factor)
            
            if rec.is_ghs_environmental and rec.total_consumed_kg > 10000:
                rec.environmental_hazard_rating = 'critical'
            elif rec.is_ghs_environmental:
                rec.environmental_hazard_rating = 'high'
            elif rec.total_consumed_kg > 5000:
                rec.environmental_hazard_rating = 'moderate'
            else:
                rec.environmental_hazard_rating = 'low'

    def action_post_to_esg_scope1(self):
        raise ValidationError(_(
            'Scope 1 posting is unavailable until verified factors, provenance, and '
            'independent approval are recorded.'
        ))
