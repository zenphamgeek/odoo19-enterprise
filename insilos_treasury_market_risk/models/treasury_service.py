# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Cron entry points; all calculations stay transient and company-isolated."""

import logging

from odoo import api, models
from ..services import exposure_engine, liquidity_engine, risk_engine, valuation_engine

_logger = logging.getLogger(__name__)


class TreasuryService(models.AbstractModel):
    _name = 'treasury.market.risk.service'
    _description = 'Treasury & Market Risk Service'

    @api.model
    def _for_each_company(self, operation):
        for company in self.env['res.company'].search([]):
            try:
                with self.env.cr.savepoint():
                    operation(company)
            except Exception:
                _logger.warning('Treasury scheduled operation failed for company %s', company.id, exc_info=True)

    @api.model
    def _cron_fx_exposure(self):
        self._for_each_company(lambda company: exposure_engine.net_open_position(self.env, company.ids))

    @api.model
    def _cron_liquidity_projection(self):
        self._for_each_company(lambda company: liquidity_engine.ladder(self.env, company.ids))

    @api.model
    def _cron_portfolio_risk(self):
        self._for_each_company(lambda company: valuation_engine.portfolio_valuation(self.env, company.ids))

    @api.model
    def _cron_limit_scan(self):
        def scan(company):
            metrics = risk_engine.portfolio_metrics(self.env, company)
            for result in risk_engine.limit_utilization(self.env, company, metrics):
                if result['status'] in ('warning', 'hard'):
                    _logger.warning(
                        'Treasury limit %s for company %s: %s=%s (utilization %s)',
                        result['status'], company.id, result['metric'], result['value'], result['utilization'])
        self._for_each_company(scan)
