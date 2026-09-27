# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
from pathlib import Path

from odoo.addons.insilos_treasury_market_risk.services import risk_engine, valuation_engine
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'treasury_market_risk', 'treasury_l3')
class TestRiskEngine(TransactionCase):
    def test_mr_20260720_portfolio_metrics_follow_governed_positions(self):
        closes = {symbol: data['bars'][-1]['close'] for symbol, data in json.loads(
            (Path(__file__).parents[2] / 'insilos_market_data' / 'tests' / 'fixtures' / 'mr_20260720.json').read_text()
        )['instruments'].items()}
        company = self.env['res.company'].create({'name': 'TMR MR Co', 'currency_id': self.env.ref('base.VND').id})
        portfolio = self.env['capital.portfolio'].create({'name': 'VN Industrial Holdings', 'company_id': company.id, 'currency_id': company.currency_id.id})
        instruments = []
        for symbol in closes:
            inst = self.env['capital.instrument'].search([('symbol', '=', symbol), ('exchange', '=', 'HOSE')], limit=1)
            if not inst:
                inst = self.env['capital.instrument'].create({'symbol': symbol, 'exchange': 'HOSE', 'currency_id': company.currency_id.id})
            instruments.append(inst)
        self.env['capital.position'].create([
            {'portfolio_id': portfolio.id, 'instrument_id': instrument.id, 'quantity': quantity,
             'average_cost': closes[instrument.symbol], 'last_price': closes[instrument.symbol]}
            for instrument, quantity in zip(instruments, (1_500_000, 4_000_000, 300_000))
        ])
        metrics = risk_engine.portfolio_metrics(self.env, company)
        self.assertAlmostEqual(metrics['single_name_pct'], 100_650_000_000 / 249_050_000_000 * 100)
        self.assertEqual(metrics['stale_position_pct'], 100.0)

    def test_limit_statuses_are_target_warning_hard_or_unconfigured(self):
        key = 'treasury.risk_limits.%s' % self.env.company.id
        self.env['ir.config_parameter'].sudo().set_param(key, json.dumps({'single_name_pct': {'target': 20, 'warning': 30, 'hard': 40}}))
        result = {row['metric']: row for row in risk_engine.limit_utilization(self.env, self.env.company, {'single_name_pct': 30, 'unknown': 1})}
        self.assertEqual(result['single_name_pct']['status'], 'warning')
        self.assertEqual(result['unknown']['status'], 'unconfigured')

    def test_portfolio_metrics_concentration_and_quality(self):
        company = self.env['res.company'].create({'name': 'TMR Concentration Co', 'currency_id': self.env.ref('base.VND').id})
        portfolio = self.env['capital.portfolio'].create({'name': 'TMR Metrics', 'company_id': company.id, 'currency_id': company.currency_id.id})
        instruments = self.env['capital.instrument'].create([
            {'symbol': 'TMRA', 'exchange': 'HOSE', 'currency_id': company.currency_id.id},
            {'symbol': 'TMRB', 'exchange': 'HOSE', 'currency_id': company.currency_id.id},
        ])
        self.env['capital.position'].create([
            {'portfolio_id': portfolio.id, 'instrument_id': instruments[0].id, 'quantity': 3, 'average_cost': 100, 'last_price': 100},
            {'portfolio_id': portfolio.id, 'instrument_id': instruments[1].id, 'quantity': 1, 'average_cost': 100, 'last_price': 100},
        ])
        metrics = risk_engine.portfolio_metrics(self.env, company)
        self.assertAlmostEqual(metrics['single_name_pct'], 75.0)
        self.assertIn('stale_position_pct', metrics)
        self.assertEqual(metrics['unmapped_position_pct'], 100.0)

    def test_portfolio_metrics_empty_when_no_positions(self):
        company = self.env['res.company'].create({'name': 'TMR Empty Co'})
        self.assertEqual(risk_engine.portfolio_metrics(self.env, company), {})

    def test_fixed_income_duration_and_dv01_are_positive(self):
        result = valuation_engine.fixed_income_metrics(1000, .05, 3, .04)
        self.assertGreater(result['price'], 1000)
        self.assertGreater(result['duration'], 0)
        self.assertGreater(result['dv01'], 0)
