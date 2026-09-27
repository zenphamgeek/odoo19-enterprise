# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ChemicalUsageESG(models.Model):
    _inherit = 'is.chemical.usage.tracking'

    chemical_impact_ids = fields.One2many('is.esg.chemical.impact', 'tracking_id', string='ESG Environmental Impact Records')
    chemical_impact_count = fields.Integer(string='ESG Impact Records', compute='_compute_impact_count')

    @api.depends('chemical_impact_ids')
    def _compute_impact_count(self):
        for tracking in self:
            tracking.chemical_impact_count = len(tracking.chemical_impact_ids)
