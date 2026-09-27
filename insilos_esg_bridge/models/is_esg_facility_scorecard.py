# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlparse

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class ESGFacilityScorecard(models.Model):
    _name = 'is.esg.facility.scorecard'
    _description = 'Industrial Plant ESG & Environmental Scorecard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reporting_year desc, id desc'

    name = fields.Char(string='Scorecard Reference', compute='_compute_name', store=True)
    facility_id = fields.Many2one('is.hse.facility', string='Industrial Facility', required=True, index=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', related='facility_id.company_id', store=True)
    reporting_year = fields.Integer(string='Reporting Year', required=True, default=lambda self: fields.Date.today().year, tracking=True)
    reporting_period = fields.Selection([
        ('annual', 'Annual (Cả năm)'), ('semi_annual_1', '1st Half Year (6 tháng đầu năm)'),
        ('semi_annual_2', '2nd Half Year (6 tháng cuối năm)'), ('q1', 'Quarter 1'),
        ('q2', 'Quarter 2'), ('q3', 'Quarter 3'), ('q4', 'Quarter 4'),
    ], string='Reporting Period', default='annual', required=True, tracking=True)

    scope1_direct_co2e = fields.Float(string='Scope 1: Direct GHG Emissions (tCO₂e)', tracking=True, help='Direct stationary combustion, process emissions and vehicle fleet.')
    scope2_indirect_co2e = fields.Float(string='Scope 2: Location-based Electricity GHG (tCO₂e)', tracking=True, help='Grid electricity and steam consumption emissions.')
    total_scope1_2_co2e = fields.Float(string='Total Scope 1 + 2 GHG (tCO₂e)', compute='_compute_totals', store=True)
    cems_so2_emissions_kg = fields.Float(string='SO₂ Sulfur Dioxide (kg)', tracking=True)
    cems_nox_emissions_kg = fields.Float(string='NOₓ Nitrogen Oxides (kg)', tracking=True)
    cems_tsp_dust_kg = fields.Float(string='Total Suspended Particulate Dust (kg)', tracking=True)
    wastewater_discharged_m3 = fields.Float(string='Total Wastewater Discharged (m³)', tracking=True)
    wastewater_cod_kg = fields.Float(string='Chemical Oxygen Demand (COD Load - kg)', tracking=True)
    wastewater_bod_kg = fields.Float(string='Biochemical Oxygen Demand (BOD₅ Load - kg)', tracking=True)
    wastewater_compliance_pct = fields.Float(string='Water Quality Compliance Rate (%)')
    hazardous_waste_generated_ton = fields.Float(string='Hazardous Waste Generated (Tons)', tracking=True)
    recycled_waste_percentage = fields.Float(string='Waste Diversion & Recycling Rate (%)', tracking=True)
    ltifr_safety_rate = fields.Float(string='LTIFR (Lost Time Injury Frequency Rate)', default=0.0, help='Injuries per 1,000,000 work hours.')
    total_worker_headcount = fields.Integer(related='facility_id.worker_count', string='Facility Headcount', store=True)
    safety_training_hours_per_worker = fields.Float(string='Safety & HSE Training (Hours/Worker)')
    environmental_score = fields.Float(string='Internal Environmental Score (0-100)', compute='_compute_esg_scores', store=True)
    sustainability_grade = fields.Selection([
        ('not_assessed', 'Not scored (Chưa chấm điểm)'),
        ('a_plus', 'Internal Band A+ (90-100)'), ('a', 'Internal Band A (80-89)'),
        ('b', 'Internal Band B (65-79)'), ('c', 'Internal Band C (Below 65)'),
    ], string='Internal Scorecard Band', compute='_compute_esg_scores', store=True)
    state = fields.Selection([
        ('draft', 'Draft (Dự thảo)'), ('audited', 'EHS Audited (Đã kiểm toán)'),
        ('published', 'ESG Published (Công bố báo cáo)'),
    ], string='Scorecard Status', default='draft', tracking=True)
    evidence_attachment_ids = fields.Many2many('ir.attachment', 'is_esg_scorecard_evidence_attachment_rel', 'scorecard_id', 'attachment_id', string='Supporting Evidence', copy=False)
    evidence_summary = fields.Text(string='Evidence Summary', copy=False)
    source_url = fields.Char(string='Source URL', copy=False)
    source_version = fields.Char(string='Source Version', copy=False)
    source_date = fields.Date(string='Source Date', copy=False)
    auditor_id = fields.Many2one('res.users', string='Audited By', readonly=True, copy=False, tracking=True)
    audited_at = fields.Datetime(string='Audited At', readonly=True, copy=False)
    publisher_id = fields.Many2one('res.users', string='Published By', readonly=True, copy=False, tracking=True)
    published_at = fields.Datetime(string='Published At', readonly=True, copy=False)
    notes = fields.Text(string='Auditor Comments & CAPA Action Plans')

    _facility_reporting_period_uniq = models.Constraint('unique(facility_id, reporting_year, reporting_period)', 'Only one ESG scorecard is allowed per facility and reporting period.')

    @api.constrains('scope1_direct_co2e', 'scope2_indirect_co2e', 'cems_so2_emissions_kg', 'cems_nox_emissions_kg', 'cems_tsp_dust_kg', 'wastewater_discharged_m3', 'wastewater_cod_kg', 'wastewater_bod_kg', 'hazardous_waste_generated_ton', 'ltifr_safety_rate', 'safety_training_hours_per_worker')
    def _check_nonnegative_metrics(self):
        for rec in self:
            if any(value < 0 for value in (rec.scope1_direct_co2e, rec.scope2_indirect_co2e, rec.cems_so2_emissions_kg, rec.cems_nox_emissions_kg, rec.cems_tsp_dust_kg, rec.wastewater_discharged_m3, rec.wastewater_cod_kg, rec.wastewater_bod_kg, rec.hazardous_waste_generated_ton, rec.ltifr_safety_rate, rec.safety_training_hours_per_worker)):
                raise ValidationError(_('ESG metrics cannot be negative.'))

    @api.constrains('wastewater_compliance_pct', 'recycled_waste_percentage')
    def _check_percentages(self):
        for rec in self:
            if not all(0 <= value <= 100 for value in (rec.wastewater_compliance_pct, rec.recycled_waste_percentage)):
                raise ValidationError(_('Percentage metrics must be between 0 and 100.'))

    def _check_source_provenance(self):
        self.ensure_one()
        parsed = urlparse(self.source_url or '')
        if not (parsed.scheme in ('http', 'https') and parsed.netloc and self.source_version and self.source_date):
            raise ValidationError(_('A source URL, version, and date are required before audit or export.'))

    @api.depends('facility_id.name', 'reporting_year', 'reporting_period')
    def _compute_name(self):
        for rec in self:
            rec.name = f"ESG-{rec.facility_id.name or 'PLANT'}-{rec.reporting_year}-{rec.reporting_period.upper()}"

    @api.depends('scope1_direct_co2e', 'scope2_indirect_co2e')
    def _compute_totals(self):
        for rec in self:
            rec.total_scope1_2_co2e = rec.scope1_direct_co2e + rec.scope2_indirect_co2e

    @api.depends('state', 'evidence_attachment_ids', 'evidence_summary', 'wastewater_compliance_pct', 'recycled_waste_percentage', 'ltifr_safety_rate', 'total_scope1_2_co2e')
    def _compute_esg_scores(self):
        for rec in self:
            if rec.state not in ('audited', 'published') or not rec.evidence_attachment_ids or not rec.evidence_summary.strip():
                rec.environmental_score = 0.0
                rec.sustainability_grade = 'not_assessed'
                continue
            score = 70.0 + (10.0 if rec.wastewater_compliance_pct >= 95.0 else 0.0) + (10.0 if rec.recycled_waste_percentage >= 50.0 else 0.0) + (10.0 if rec.ltifr_safety_rate == 0.0 else 0.0)
            rec.environmental_score = min(100.0, max(0.0, score))
            rec.sustainability_grade = 'a_plus' if rec.environmental_score >= 90.0 else 'a' if rec.environmental_score >= 80.0 else 'b' if rec.environmental_score >= 65.0 else 'c'

    @api.model_create_multi
    def create(self, vals_list):
        governance_fields = {'auditor_id', 'audited_at', 'publisher_id', 'published_at'}
        if any(vals.get('state') in ('audited', 'published') for vals in vals_list):
            raise ValidationError(_('ESG scorecards must be audited through the audit action before publication.'))
        if any(governance_fields.intersection(vals) for vals in vals_list):
            raise ValidationError(_('ESG scorecard governance fields are written only through their lifecycle actions.'))
        return super().create(vals_list)

    def write(self, vals):
        if any(rec.state in ('audited', 'published') for rec in self):
            raise ValidationError(_('Audited and published ESG scorecards are immutable.'))
        if {'state', 'auditor_id', 'audited_at', 'publisher_id', 'published_at'}.intersection(vals):
            raise ValidationError(_('ESG scorecard governance fields are written only through their lifecycle actions.'))
        return super().write(vals)

    def action_audit(self):
        self.ensure_one()
        if not self.env.user.has_group('insilos_esg_bridge.group_esg_bridge_manager'):
            raise AccessError(_('Only ESG managers can audit scorecards.'))
        if self.create_uid == self.env.user:
            raise ValidationError(_('The auditor must be different from the scorecard creator.'))
        if self.state != 'draft':
            raise ValidationError(_('Only draft ESG scorecards can be audited.'))
        self.evidence_attachment_ids.check_access('read')
        self.evidence_attachment_ids.check_access_rule('read')
        if not self.evidence_attachment_ids or not self.evidence_summary.strip():
            raise ValidationError(_('Supporting evidence attachments and an evidence summary are required before audit.'))
        self._check_source_provenance()
        return super(ESGFacilityScorecard, self).write({
            'state': 'audited', 'auditor_id': self.env.user.id, 'audited_at': fields.Datetime.now(),
        })

    def action_publish_esg(self):
        self.ensure_one()
        if not self.env.user.has_group('insilos_esg_bridge.group_esg_bridge_manager'):
            raise AccessError(_('Only ESG managers can publish scorecards.'))
        if self.state != 'audited':
            raise ValidationError(_('Only audited ESG scorecards can be published.'))
        if not self.evidence_attachment_ids or not self.evidence_summary.strip():
            raise ValidationError(_('Supporting evidence attachments and an evidence summary are required before publication.'))
        if self.auditor_id == self.env.user:
            raise ValidationError(_('The publisher must be different from the auditor.'))
        return super(ESGFacilityScorecard, self).write({
            'state': 'published', 'publisher_id': self.env.user.id, 'published_at': fields.Datetime.now(),
        })
