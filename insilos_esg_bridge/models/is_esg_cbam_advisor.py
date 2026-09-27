# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ESGCBAMAdvisor(models.Model):
    _name = 'is.esg.cbam.advisor'
    _description = 'CBAM (Carbon Border Adjustment Mechanism) & Customs Carbon Tariff Advisor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'hs_code asc, id desc'

    name = fields.Char(string='Advisor Reference', compute='_compute_name', store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    hs_tariff_id = fields.Many2one('is.hs.tariff', string='Customs HS Tariff Schedule', required=True, index=True, tracking=True)
    hs_code = fields.Char(related='hs_tariff_id.hs_code', string='8-Digit HS Code', store=True)
    description_vi = fields.Text(related='hs_tariff_id.description_vi', string='Vietnamese Description', store=True)

    is_cbam_applicable = fields.Boolean(string='Within Configured Internal CBAM Advisory Scope', compute='_compute_cbam_rules', store=True, tracking=True,
                                        help='Internal HS-prefix screening only; verify current legal scope against governed regulatory sources.')
    cbam_sector = fields.Selection([
        ('iron_steel', 'Iron & Steel (Sắt thép — Chapter 72/73)'),
        ('aluminum', 'Aluminum (Nhôm — Chapter 76)'),
        ('fertilizer', 'Fertilizer (Phân bón — Chapter 31)'),
        ('cement', 'Cement (Xi măng — Chapter 25)'),
        ('hydrogen_chemicals', 'Hydrogen & Precursors (Hydro & Tiền chất — Chapter 28)'),
        ('not_applicable', 'Not in CBAM Scope'),
    ], string='Configured Internal Sector Scenario', compute='_compute_cbam_rules', store=True, tracking=True)

    # Configurable internal estimation inputs; verify sources and methodology before reliance.
    direct_embedded_emissions_t_per_t = fields.Float(string='Internal Estimated Direct Embedded Emissions (tCO2e per ton)', default=1.85,
                                                     help='Internal estimation input, not a verified regulatory emission factor.')
    indirect_embedded_emissions_t_per_t = fields.Float(string='Internal Estimated Indirect Electricity Emissions (tCO2e per ton)', default=0.45,
                                                       help='Internal estimation input, not a verified regulatory emission factor.')
    total_embedded_emissions_t_per_t = fields.Float(string='Total Embedded Carbon Intensity (tCO2e per ton)', compute='_compute_carbon_intensity', store=True)

    eu_carbon_certificate_price_eur = fields.Float(string='Internal Carbon Price Assumption (€/tCO₂e)', default=68.50, tracking=True,
                                                   help='Configurable internal estimate; verify applicable price and methodology before reliance.')
    estimated_cbam_cost_per_ton_eur = fields.Float(string='Estimated Carbon Cost Exposure (€/ton product)', compute='_compute_carbon_intensity', store=True)

    reporting_frequency = fields.Selection([
        ('quarterly_transitional', 'Internal Quarterly Reporting Scenario Assumption (Giả định kịch bản báo cáo nội bộ hàng quý)'),
        ('annual_surrender', 'Internal Annual Reporting Scenario Assumption (Giả định kịch bản báo cáo nội bộ hằng năm)'),
        ('none', 'No Internal Reporting Scenario'),
    ], string='Internal Reporting Scenario Assumption', compute='_compute_cbam_rules', store=True)

    # Internal decarbonization scenario simulator
    renewable_energy_share_pct = fields.Float(string='DPPA Renewable Energy Share (%)', default=40.0, tracking=True,
                                             help='Percentage of electricity sourced from direct PPA, solar rooftop or green I-RECs.')
    mitigated_indirect_emissions = fields.Float(string='Mitigated Indirect Emissions (tCO₂e/ton)', compute='_compute_decarbonization_scenarios', store=True)
    mitigated_total_emissions = fields.Float(string='Total Emissions After Decarbonization (tCO₂e/ton)', compute='_compute_decarbonization_scenarios', store=True)
    projected_cbam_cost_after_mitigation_eur = fields.Float(string='Projected CBAM Duty After Mitigation (€/ton)', compute='_compute_decarbonization_scenarios', store=True)
    potential_savings_per_ton_eur = fields.Float(string='CBAM Tariff Savings (€/ton exported)', compute='_compute_decarbonization_scenarios', store=True)

    annual_export_volume_tons = fields.Float(string='Target Annual Export Volume (Tons)', default=5000.0, tracking=True)
    total_annual_cbam_savings_eur = fields.Float(string='Projected Annual Internal Cost Difference (€)', compute='_compute_decarbonization_scenarios', store=True)

    action_recommendation = fields.Text(string='Internal Scenario Notes', compute='_compute_recommendation', store=True)

    _protected_calculation_fields = {
        'name', 'is_cbam_applicable', 'cbam_sector', 'reporting_frequency',
        'total_embedded_emissions_t_per_t', 'estimated_cbam_cost_per_ton_eur',
        'mitigated_indirect_emissions', 'mitigated_total_emissions',
        'projected_cbam_cost_after_mitigation_eur', 'potential_savings_per_ton_eur',
        'total_annual_cbam_savings_eur', 'action_recommendation',
    }

    @api.model_create_multi
    def create(self, vals_list):
        if any(self._protected_calculation_fields.intersection(vals) for vals in vals_list):
            raise ValidationError(_('CBAM calculated scope and advisory fields are server-controlled.'))
        return super().create(vals_list)

    def write(self, vals):
        if self._protected_calculation_fields.intersection(vals):
            raise ValidationError(_('CBAM calculated scope and advisory fields are server-controlled.'))
        return super().write(vals)

    @api.constrains(
        'direct_embedded_emissions_t_per_t', 'indirect_embedded_emissions_t_per_t',
        'eu_carbon_certificate_price_eur', 'annual_export_volume_tons',
    )
    def _check_nonnegative_inputs(self):
        for rec in self:
            if any(value < 0 for value in (
                rec.direct_embedded_emissions_t_per_t,
                rec.indirect_embedded_emissions_t_per_t,
                rec.eu_carbon_certificate_price_eur,
                rec.annual_export_volume_tons,
            )):
                raise ValidationError(_('CBAM emissions, price, and export volume cannot be negative.'))

    @api.constrains('renewable_energy_share_pct')
    def _check_renewable_energy_share(self):
        for rec in self:
            if not 0 <= rec.renewable_energy_share_pct <= 100:
                raise ValidationError(_('Renewable energy share must be between 0 and 100.'))

    @api.depends('hs_code')
    def _compute_name(self):
        for rec in self:
            code = rec.hs_code or 'HS'
            rec.name = f"CBAM-[{code}]"

    @api.depends('hs_code')
    def _compute_cbam_rules(self):
        for rec in self:
            code = rec.hs_code or ''
            if code.startswith(('72', '73')):
                rec.is_cbam_applicable = True
                rec.cbam_sector = 'iron_steel'
                rec.reporting_frequency = 'quarterly_transitional'
                rec.direct_embedded_emissions_t_per_t = 1.95
            elif code.startswith('76'):
                rec.is_cbam_applicable = True
                rec.cbam_sector = 'aluminum'
                rec.reporting_frequency = 'quarterly_transitional'
                rec.direct_embedded_emissions_t_per_t = 6.80
            elif code.startswith('31'):
                rec.is_cbam_applicable = True
                rec.cbam_sector = 'fertilizer'
                rec.reporting_frequency = 'quarterly_transitional'
                rec.direct_embedded_emissions_t_per_t = 2.40
            elif code.startswith('2523'):
                rec.is_cbam_applicable = True
                rec.cbam_sector = 'cement'
                rec.reporting_frequency = 'quarterly_transitional'
                rec.direct_embedded_emissions_t_per_t = 0.75
            elif code.startswith('280410'):
                rec.is_cbam_applicable = True
                rec.cbam_sector = 'hydrogen_chemicals'
                rec.reporting_frequency = 'quarterly_transitional'
                rec.direct_embedded_emissions_t_per_t = 9.20
            else:
                rec.is_cbam_applicable = False
                rec.cbam_sector = 'not_applicable'
                rec.reporting_frequency = 'none'

    @api.depends('direct_embedded_emissions_t_per_t', 'indirect_embedded_emissions_t_per_t', 'eu_carbon_certificate_price_eur')
    def _compute_carbon_intensity(self):
        for rec in self:
            total_t = rec.direct_embedded_emissions_t_per_t + rec.indirect_embedded_emissions_t_per_t
            rec.total_embedded_emissions_t_per_t = total_t
            rec.estimated_cbam_cost_per_ton_eur = total_t * rec.eu_carbon_certificate_price_eur

    @api.depends('direct_embedded_emissions_t_per_t', 'indirect_embedded_emissions_t_per_t', 'renewable_energy_share_pct', 'eu_carbon_certificate_price_eur', 'annual_export_volume_tons')
    def _compute_decarbonization_scenarios(self):
        for rec in self:
            mitigated_indirect = rec.indirect_embedded_emissions_t_per_t * (1.0 - (rec.renewable_energy_share_pct / 100.0))
            mitigated_total = rec.direct_embedded_emissions_t_per_t + mitigated_indirect
            projected_cost = mitigated_total * rec.eu_carbon_certificate_price_eur
            savings_per_t = rec.estimated_cbam_cost_per_ton_eur - projected_cost
            annual_savings = savings_per_t * rec.annual_export_volume_tons

            rec.mitigated_indirect_emissions = mitigated_indirect
            rec.mitigated_total_emissions = mitigated_total
            rec.projected_cbam_cost_after_mitigation_eur = projected_cost
            rec.potential_savings_per_ton_eur = savings_per_t
            rec.total_annual_cbam_savings_eur = annual_savings

    @api.depends('cbam_sector', 'is_cbam_applicable', 'potential_savings_per_ton_eur', 'total_annual_cbam_savings_eur')
    def _compute_recommendation(self):
        for rec in self:
            disclaimer = _("Internal estimate only. Verify HS scope, emission factors, price, methodology, and current obligations against governed regulatory sources before reliance or submission.")
            if not rec.is_cbam_applicable:
                rec.action_recommendation = _("This HS code is outside the configured internal CBAM advisory scope. %s") % disclaimer
            else:
                rec.action_recommendation = _(
                    "Recommended internal decarbonization scenario:\n"
                    "1. Consider direct power purchase agreements (DPPA) or rooftop solar to reduce estimated indirect emissions.\n"
                    "2. Estimated savings: €%.2f / ton exported (Total €%.2f / year for %.0f tons volume).\n"
                    "3. %s"
                ) % (rec.potential_savings_per_ton_eur, rec.total_annual_cbam_savings_eur, rec.annual_export_volume_tons, disclaimer)

    def action_generate_cbam_internal_estimate(self):
        raise UserError(_(
            'CBAM estimate export is unavailable until governed source, evidence, independent review, '
            'and publication controls exist.'
        ))
