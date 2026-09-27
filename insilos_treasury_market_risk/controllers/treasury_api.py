# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Read-only treasury contracts; every result declares its calculation version."""

from odoo import fields, http
from odoo.http import request, route

from ..services import exposure_engine, liquidity_engine, risk_engine, scenario_engine

CALCULATION_VERSION = '1.0'


def _company(company_id=None):
    user = request.env['res.users'].sudo().browse(request.env.uid)
    allowed_ids = request.env.context.get('allowed_company_ids', user.company_ids.ids)
    company_id = company_id or user.company_id.id
    if company_id not in allowed_ids:
        raise ValueError('Unknown or unauthorised company.')
    return request.env['res.company'].sudo().browse(company_id).exists()


def _response(**payload):
    return {'calculation_version': CALCULATION_VERSION, **payload}


class TreasuryApiController(http.Controller):

    @route('/treasury/fx/exposure', type='jsonrpc', auth='user', methods=['POST'], csrf=False, readonly=True)
    def fx_exposure(self, company_id=None, as_of=None, **kwargs):
        company = _company(company_id)
        rows = exposure_engine.net_open_position(request.env, [company.id], as_of)
        net_rows = exposure_engine.natural_hedge(rows)
        return _response(as_of=str(as_of or fields.Date.context_today(request.env['res.company'])), rows=net_rows,
                         sensitivity=exposure_engine.sensitivity(request.env, net_rows, company, as_of=as_of))

    @route('/treasury/liquidity/forecast', type='jsonrpc', auth='user', methods=['POST'], csrf=False, readonly=True)
    def liquidity_forecast(self, company_id=None, as_of=None, ar_delay_days=0, **kwargs):
        company = _company(company_id)
        opening = liquidity_engine.opening_liquidity(request.env, [company.id])[0]['amount']
        rows = liquidity_engine.ladder(request.env, [company.id], as_of=as_of, ar_delay_days=ar_delay_days)
        min_buffer = liquidity_engine.min_cash_buffer(request.env, company)
        facility = liquidity_engine.committed_facility(request.env, company)
        closing = opening + (rows[-1]['cumulative_flow'] if rows else 0.0)
        status, required_draw, funding_gap = liquidity_engine.liquidity_status(closing, min_buffer, facility)
        return _response(opening=opening, rows=rows, min_buffer=min_buffer, facility=facility,
                         closing=closing, status=status, required_draw=required_draw, funding_gap=funding_gap,
                         survival_horizon=liquidity_engine.survival_horizon(opening, rows, min_buffer))

    @route('/treasury/limits', type='jsonrpc', auth='user', methods=['POST'], csrf=False, readonly=True)
    def limits(self, company_id=None, **kwargs):
        company = _company(company_id)
        metrics = risk_engine.portfolio_metrics(request.env, company)
        return _response(metrics=metrics, limits=risk_engine.limit_utilization(request.env, company, metrics))

    @route('/treasury/risk/stress', type='jsonrpc', auth='user', methods=['POST'], csrf=False, readonly=True)
    def stress(self, holdings, shocks_pct=None, haircuts=None, **kwargs):
        shocks_pct = shocks_pct or {}
        return _response(portfolio=scenario_engine.stress_loss(holdings, shocks_pct),
                         collateral=scenario_engine.secured_liquidity_capacity(holdings, haircuts or {}, shocks_pct))
