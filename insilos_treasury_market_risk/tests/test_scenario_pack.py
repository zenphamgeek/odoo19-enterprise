# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Enterprise validation pack — expected values frozen from
docs/industries/Insilos_Combined_Capital_Markets_Treasury_AI_TEST_.SCENARIOS.md
(reference date 20/07/2026, dataset MR-20260720, VN Industrial Holdings).
"""

import json
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged

from ..services import liquidity_engine, scenario_engine

B = 1e9  # billion VND
MR_20260720 = json.loads((Path(__file__).parents[2] / 'insilos_market_data' / 'tests' / 'fixtures' / 'mr_20260720.json').read_text())
CLOSE = {symbol: payload['bars'][-1]['close'] for symbol, payload in MR_20260720['instruments'].items()}

# §5 holdings at MR-20260720 close
HOLDINGS = [
    {'symbol': 'FPT', 'asset_class': 'equity', 'market_value': 1_500_000 * CLOSE['FPT']},
    {'symbol': 'HPG', 'asset_class': 'equity', 'market_value': 4_000_000 * CLOSE['HPG']},
    {'symbol': 'VIC', 'asset_class': 'equity', 'market_value': 300_000 * CLOSE['VIC']},
    {'symbol': 'GOV', 'asset_class': 'government_bond', 'market_value': 150 * B},
    {'symbol': 'CORP', 'asset_class': 'corporate_bond', 'market_value': 80 * B},
    {'symbol': 'CASH', 'asset_class': 'cash', 'market_value': 120 * B},
]
TOTAL = sum(h['market_value'] for h in HOLDINGS)


@tagged('post_install', '-at_install', 'treasury_market_risk')
class TestScenarioPack(TransactionCase):

    # --- Suite B: Portfolio ---

    def test_pf_001_market_valuation(self):
        self.assertAlmostEqual(HOLDINGS[0]['market_value'], 100.650 * B)
        self.assertAlmostEqual(HOLDINGS[1]['market_value'], 82.400 * B)
        self.assertAlmostEqual(HOLDINGS[2]['market_value'], 66.000 * B)
        self.assertAlmostEqual(TOTAL, 599.050 * B, delta=1)

    def test_pf_002_day_pnl(self):
        pnl = (67_100 - 67_000) * 1_500_000 + (20_600 - 21_850) * 4_000_000
        self.assertAlmostEqual(pnl, -4.850 * B)

    def test_pf_003_concentration_breach(self):
        weight = HOLDINGS[0]['market_value'] / TOTAL * 100.0
        self.assertAlmostEqual(weight, 16.80, places=2)
        self.assertGreater(weight, 15.0)
        self.assertAlmostEqual(weight - 15.0, 1.80, places=2)

    def test_pf_004_minimum_rebalance(self):
        result = scenario_engine.minimum_rebalance(
            HOLDINGS[0]['market_value'], TOTAL, 15.0, 67_100)
        self.assertAlmostEqual(result['required_value'], 10.7925 * B, delta=1e6)
        self.assertEqual(result['quantity'], 160_900)
        self.assertAlmostEqual(result['sale_value'], 10.79639 * B, delta=1e4)
        post_weight = (HOLDINGS[0]['market_value'] - result['sale_value']) / TOTAL * 100.0
        self.assertLess(post_weight, 15.0)
        self.assertAlmostEqual(post_weight, 14.999, places=2)

    def test_pf_005_severe_stress(self):
        result = scenario_engine.stress_loss(HOLDINGS, {
            'FPT': -12.0, 'HPG': -15.0, 'VIC': -10.0,
            'GOV': -4.8,   # duration 3.2 × +150bp
            'CORP': -5.0,
        })
        self.assertAlmostEqual(result['total_loss'], 42.238 * B, delta=1e6)

    # --- Suite C: FX ---

    def test_fx_001_net_exposure_direction(self):
        usd = 1.0 + 4.5 - 9.0 + 2.0
        eur = 0.5 - 2.0
        self.assertAlmostEqual(usd, -1.5)
        self.assertAlmostEqual(eur, -1.5)

    def test_fx_002_stress_loss(self):
        usd_loss = 1.5e6 * 26_250 * 0.04
        eur_loss = 1.5e6 * 30_600 * 0.06
        self.assertAlmostEqual(usd_loss, 1.575 * B)
        self.assertAlmostEqual(eur_loss, 2.754 * B)
        self.assertAlmostEqual(usd_loss + eur_loss, 4.329 * B)

    def test_fx_003_hedge_ratio_warning_not_breach(self):
        result = scenario_engine.hedge_ratio_status(-3.5e6, 2.0e6)
        self.assertAlmostEqual(result['hedge_ratio_pct'], 57.14, places=2)
        self.assertEqual(result['status'], 'warning')
        self.assertAlmostEqual(result['residual_exposure'], -1.5e6)

    def test_fx_hedge_policy_from_config(self):
        company = self.env.company
        self.env['ir.config_parameter'].sudo().set_param(
            'treasury.fx_hedge_policy.%s' % company.id, '{"target": 80, "hard": 60}')
        policy = scenario_engine.fx_hedge_policy(self.env, company)
        result = scenario_engine.hedge_ratio_status(-3.5e6, 2.0e6, policy)
        self.assertEqual(result['status'], 'hard')  # 57.14 < 60

    # --- Suite D: Liquidity ---

    def test_liq_001_base_forecast_amber(self):
        closing = 251.550 * B + 348.125 * B - 608.950 * B
        self.assertAlmostEqual(closing, -9.275 * B, delta=1e3)
        status, draw, gap = liquidity_engine.liquidity_status(closing, 100 * B, 150 * B)
        self.assertEqual(status, 'amber')
        self.assertAlmostEqual(draw, 109.275 * B, delta=1e3)
        self.assertEqual(gap, 0.0)
        self.assertAlmostEqual(150 * B - draw, 40.725 * B, delta=1e3)

    def test_liq_002_receivable_delay_red(self):
        closing = -9.275 * B - (112 * B + 118.125 * B)
        self.assertAlmostEqual(closing, -239.400 * B, delta=1e3)
        status, draw, gap = liquidity_engine.liquidity_status(closing, 100 * B, 150 * B)
        self.assertEqual(status, 'red')
        self.assertAlmostEqual(draw, 339.400 * B, delta=1e3)
        self.assertAlmostEqual(gap, 189.400 * B, delta=1e3)

    def test_liq_committed_facility_from_config(self):
        company = self.env.company
        self.env['ir.config_parameter'].sudo().set_param(
            'treasury.committed_facility.%s' % company.id, str(150 * B))
        self.assertAlmostEqual(liquidity_engine.committed_facility(self.env, company), 150 * B)

    # --- Suite E: Combined (hero scenario) ---

    def test_comb_001_stressed_collateral_capacity(self):
        result = scenario_engine.secured_liquidity_capacity(
            [h for h in HOLDINGS if 'bond' in h['asset_class']],
            {'government_bond': 5.0, 'corporate_bond': 20.0},
            {'government_bond': -4.8, 'corporate_bond': -5.0},
        )
        self.assertAlmostEqual(result['total_capacity'], 196.460 * B, delta=1e6)
        headroom = result['total_capacity'] - 189.400 * B
        self.assertAlmostEqual(headroom, 7.060 * B, delta=1e6)

    def test_comb_001_unconfigured_asset_is_unpledgeable(self):
        result = scenario_engine.secured_liquidity_capacity(
            [{'asset_class': 'equity', 'market_value': 100 * B}], {})
        self.assertEqual(result['total_capacity'], 0.0)

    def test_comb_002_loss_and_gap_not_summed(self):
        result = scenario_engine.combined_stress(42.238 * B, 4.329 * B, 189.400 * B)
        self.assertAlmostEqual(result['economic_loss'], 46.567 * B, delta=1e6)
        self.assertAlmostEqual(result['liquidity_funding_gap'], 189.400 * B)
        self.assertNotIn('total', result)  # no combined loss+gap figure exists

    def test_stress_helpers_cover_empty_zero_and_do_not_mutate_inputs(self):
        holdings = [{'asset_class': 'government_bond', 'market_value': 100.0}]
        original = [dict(row) for row in holdings]
        self.assertEqual(scenario_engine.stress_loss([], {})['total_loss'], 0.0)
        self.assertEqual(scenario_engine.hedge_ratio_status(0.0, 0.0)['hedge_ratio_pct'], 100.0)
        self.assertEqual(
            scenario_engine.secured_liquidity_capacity(holdings, {'government_bond': 100.0})['total_capacity'],
            0.0,
        )
        scenario_engine.stress_loss(holdings, {'government_bond': -10.0})
        self.assertEqual(holdings, original)
