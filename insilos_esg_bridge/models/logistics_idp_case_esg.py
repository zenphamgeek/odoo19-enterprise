# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LogisticsIdpCaseESG(models.Model):
    _inherit = 'logistics.idp.case'

    freight_carbon_ids = fields.One2many('is.esg.freight.carbon', 'case_id', string='Scope 3 Freight Carbon Calculations')
    freight_carbon_count = fields.Integer(string='Carbon Records', compute='_compute_freight_carbon_metrics')
    total_freight_carbon_kg = fields.Float(string='Freight Carbon Footprint (kgCO₂e)', compute='_compute_freight_carbon_metrics')
    paperless_pages_saved = fields.Integer(string='Paperless Pages Saved', compute='_compute_freight_carbon_metrics')

    @api.depends('freight_carbon_ids.gross_freight_emissions_kg_co2e', 'freight_carbon_ids.paperless_pages_processed')
    def _compute_freight_carbon_metrics(self):
        for case in self:
            case.freight_carbon_count = len(case.freight_carbon_ids)
            case.total_freight_carbon_kg = sum(fc.gross_freight_emissions_kg_co2e for fc in case.freight_carbon_ids)
            case.paperless_pages_saved = sum(fc.paperless_pages_processed for fc in case.freight_carbon_ids)

    is_orchestrated = fields.Boolean(string='Enterprise Orchestrated', default=False, tracking=True)
    orchestrated_po_id = fields.Many2one('purchase.order', string='Orchestrated ERP Purchase Order')
    orchestrated_nsw_dossier_id = fields.Many2one('is.chemical.compliance.dossier', string='Orchestrated NSW Customs Dossier')
    orchestrated_treasury_task_id = fields.Many2one('project.task', string='Orchestrated Treasury FX Hedge Task')

    def action_execute_enterprise_orchestration(self):
        self.ensure_one()
        # ponytail: refuse orchestration until source-backed cross-app mappings exist.
        raise ValidationError(_(
            "Enterprise orchestration is unavailable: source evidence and validated "
            "mappings are required for the supplier, freight measurements and page "
            "counts, chemical quantities, FX exposure and Knowledge Graph provenance. "
            "No purchase order, carbon ledger entry, customs dossier, treasury task "
            "or Knowledge Graph verification has been created."
        ))
