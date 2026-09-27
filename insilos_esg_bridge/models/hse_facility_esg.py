# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HSEFacilityESG(models.Model):
    _inherit = 'is.hse.facility'

    scorecard_ids = fields.One2many('is.esg.facility.scorecard', 'facility_id', string='ESG Scorecards')
    scorecard_count = fields.Integer(string='Scorecards Count', compute='_compute_scorecard_metrics')
    latest_environmental_score = fields.Float(string='Latest Internal Environmental Score', compute='_compute_scorecard_metrics')
    latest_sustainability_grade = fields.Selection([
        ('not_assessed', 'Not scored (Chưa chấm điểm)'),
        ('a_plus', 'Internal Band A+ (90-100)'),
        ('a', 'Internal Band A (80-89)'),
        ('b', 'Internal Band B (65-79)'),
        ('c', 'Internal Band C (Below 65)'),
    ], string='Latest Internal Scorecard Band', compute='_compute_scorecard_metrics')

    @api.depends('scorecard_ids', 'scorecard_ids.environmental_score', 'scorecard_ids.sustainability_grade')
    def _compute_scorecard_metrics(self):
        for facility in self:
            facility.scorecard_count = len(facility.scorecard_ids)
            latest = facility.scorecard_ids[:1]
            if latest:
                facility.latest_environmental_score = latest.environmental_score
                facility.latest_sustainability_grade = latest.sustainability_grade
            else:
                facility.latest_environmental_score = 0.0
                facility.latest_sustainability_grade = 'not_assessed'
