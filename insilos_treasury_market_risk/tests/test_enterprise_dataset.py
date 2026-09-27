# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""VN Industrial Holdings, built in the database rather than asserted in prose.

The scenario pack fixes the expected numbers; this suite makes the product
produce them from real positions and real journal items, so a regression in the
ORM path cannot pass by leaving the arithmetic tests untouched.
"""

import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.addons.insilos_treasury_market_risk.services import ai_advisory, exposure_engine, liquidity_engine, risk_engine, scenario_engine
from odoo.tests.common import tagged

B = 1e9
MR_20260720 = json.loads((Path(__file__).parents[2] / 'insilos_market_data' / 'tests' / 'fixtures' / 'mr_20260720.json').read_text())
CLOSE = {symbol: payload['bars'][-1]['close'] for symbol, payload in MR_20260720['instruments'].items()}
COST = {'FPT': 61_000, 'HPG': 22_000, 'VIC': 200_000}
QUANTITY = {'FPT': 1_500_000, 'HPG': 4_000_000, 'VIC': 300_000}
USD_VND = 26_250
EUR_VND = 30_600


@tagged('post_install', '-at_install', 'treasury_market_risk', 'enterprise_dataset')
class TestVNIndustrialHoldings(AccountTestInvoicingCommon):
    @classmethod
    def setup_main_company(cls, currency_code='USD'):
        # VN Industrial Holdings keeps its books in VND; USD and EUR are the
        # foreign currencies whose exposure the suite measures.
        return super().setup_main_company(currency_code='VND')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.as_of = date(2026, 7, 20)
        cls.company = cls.env.company
        # Loading the chart template writes its own currency onto the company,
        # so the books have to be put back into VND afterwards. Reading the
        # company currency before this point silently yields USD, and every
        # foreign-currency assertion below would then be measuring nothing.
        cls._use_currency(cls.company, 'VND')
        cls.vnd = cls.company.currency_id
        cls.usd = cls.setup_other_currency('USD', rates=[(cls.as_of, 1.0 / USD_VND)])
        cls.eur = cls.setup_other_currency('EUR', rates=[(cls.as_of, 1.0 / EUR_VND)])
        cls.env.user.group_ids |= cls.env.ref('insilos_capital_markets_decision_governance.group_portfolio_manager')

        cls.portfolio = cls.env['capital.portfolio'].create({
            'name': 'Corporate Liquidity & Strategic Reserve',
            'company_id': cls.company.id, 'currency_id': cls.vnd.id,
        })
        for symbol, quantity in QUANTITY.items():
            instrument = cls.env['capital.instrument'].search([('symbol', '=', symbol), ('exchange', '=', 'HOSE')], limit=1)
            if not instrument:
                instrument = cls.env['capital.instrument'].create({'symbol': symbol, 'exchange': 'HOSE', 'currency_id': cls.vnd.id})
            position = cls.env['capital.position'].create({
                'portfolio_id': cls.portfolio.id, 'instrument_id': instrument.id,
                'quantity': quantity, 'average_cost': COST[symbol],
            })
            position.with_context(capital_market_refresh=True).write({'last_price': CLOSE[symbol]})

        # §5 non-equity sleeves, valued directly because they are not marked
        # from the equity feed.
        cls.non_equity = [
            {'symbol': 'GOV', 'asset_class': 'government_bond', 'market_value': 150 * B},
            {'symbol': 'CORP', 'asset_class': 'corporate_bond', 'market_value': 80 * B},
            {'symbol': 'CASH', 'asset_class': 'cash', 'market_value': 120 * B},
        ]

    # --- ledger construction -------------------------------------------------

    @classmethod
    def _entry(cls, groups, name):
        move = cls.env['account.move'].create({
            'move_type': 'entry', 'date': cls.as_of, 'ref': name,
            'line_ids': [(0, 0, line) for group in groups for line in group],
        })
        move.action_post()
        return move

    @classmethod
    def _monetary_line(cls, account, amount_vnd, currency=None, amount_currency=0.0, maturity=None, partner=None):
        """One monetary line plus its mirror on equity.

        Mirroring in the same currency keeps the entry balanced whatever rate
        the ORM applies, so the suite tests exposure rather than test plumbing.
        """
        contra = cls.company_data['default_account_revenue']
        lines = []
        for target, sign in ((account, 1), (contra, -1)):
            line = {
                'account_id': target.id,
                'debit': amount_vnd if amount_vnd * sign > 0 else 0.0,
                'credit': amount_vnd if amount_vnd * sign < 0 else 0.0,
            }
            line['debit'] = abs(amount_vnd) if amount_vnd * sign > 0 else 0.0
            line['credit'] = abs(amount_vnd) if amount_vnd * sign < 0 else 0.0
            if currency:
                line.update({'currency_id': currency.id, 'amount_currency': amount_currency * sign})
            if maturity and sign == 1:
                line['date_maturity'] = maturity
            if partner and sign == 1:
                line['partner_id'] = partner.id
            lines.append(line)
        return lines

    def _build_treasury_ledger(self):
        cash = self.company_data['default_account_assets'].copy({'name': 'Cash VND', 'account_type': 'asset_cash', 'code': 'CASHVND'})
        cash_usd = cash.copy({'name': 'Cash USD', 'code': 'CASHUSD'})
        cash_eur = cash.copy({'name': 'Cash EUR', 'code': 'CASHEUR'})
        receivable = self.company_data['default_account_receivable']
        payable = self.company_data['default_account_payable']
        partner = self.partner_a
        due = self.as_of + timedelta(days=20)

        # §8 opening cash: 210B VND, USD 1.0M, EUR 0.5M.
        self._entry([
            self._monetary_line(cash, 210 * B),
            self._monetary_line(cash_usd, 1_000_000 * USD_VND, self.usd, 1_000_000),
            self._monetary_line(cash_eur, 500_000 * EUR_VND, self.eur, 500_000),
        ], 'Opening cash')

        # §11 inflows due within 30 days: VND AR 160B, USD AR 4.5M, investment maturity 70B.
        self._entry([
            self._monetary_line(receivable, 160 * B, maturity=due, partner=partner),
            self._monetary_line(receivable, 4_500_000 * USD_VND, self.usd, 4_500_000, maturity=due, partner=partner),
            self._monetary_line(receivable, 70 * B, maturity=due, partner=partner),
        ], 'Receivables')

        # §11 outflows due within 30 days.
        self._entry([
            self._monetary_line(payable, -190 * B, maturity=due, partner=partner),
            self._monetary_line(payable, -9_000_000 * USD_VND, self.usd, -9_000_000, maturity=due, partner=partner),
            self._monetary_line(payable, -2_000_000 * EUR_VND, self.eur, -2_000_000, maturity=due, partner=partner),
            self._monetary_line(payable, -38 * B, maturity=due, partner=partner),   # payroll
            self._monetary_line(payable, -26 * B, maturity=due, partner=partner),   # tax
            self._monetary_line(payable, -57.5 * B, maturity=due, partner=partner),  # debt service
        ], 'Payables')

    # --- Suite B: portfolio, from stored positions ---------------------------

    def test_pf_001_and_003_weights_come_from_stored_positions(self):
        positions = self.portfolio.position_ids
        equity_value = sum(positions.mapped('base_market_value'))
        self.assertAlmostEqual(equity_value, 249.050 * B, delta=1)
        total = equity_value + sum(row['market_value'] for row in self.non_equity)
        self.assertAlmostEqual(total, 599.050 * B, delta=1)

        fpt = positions.filtered(lambda row: row.symbol == 'FPT')
        self.assertAlmostEqual(fpt.market_value, 100.650 * B, delta=1)
        weight = fpt.market_value / total * 100.0
        self.assertAlmostEqual(weight, 16.80, places=2)
        self.assertGreater(weight, 15.0)

    def test_pf_unrealised_pnl_is_computed_by_the_model(self):
        by_symbol = {position.symbol: position for position in self.portfolio.position_ids}
        self.assertAlmostEqual(by_symbol['FPT'].unrealised_pnl, 9.150 * B, delta=1)
        self.assertAlmostEqual(by_symbol['HPG'].unrealised_pnl, -5.600 * B, delta=1)
        self.assertAlmostEqual(by_symbol['VIC'].unrealised_pnl, 6.000 * B, delta=1)
        self.assertAlmostEqual(sum(position.unrealised_pnl for position in by_symbol.values()), 9.550 * B, delta=1)

    def test_pf_003_concentration_metric_flags_the_breach_through_the_risk_engine(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'treasury.risk_limits.%s' % self.company.id,
            json.dumps({'single_name_pct': {'target': 15, 'warning': 15, 'hard': 20}}),
        )
        metrics = risk_engine.portfolio_metrics(self.env, self.company)
        # Measured against the equity sleeve the engine can see, FPT is largest.
        self.assertAlmostEqual(metrics['single_name_pct'], 100.650 / 249.050 * 100, places=2)
        statuses = {row['metric']: row['status'] for row in risk_engine.limit_utilization(self.env, self.company, metrics)}
        self.assertEqual(statuses['single_name_pct'], 'hard')

    def test_pf_004_minimum_rebalance_restores_the_policy_weight(self):
        total = sum(self.portfolio.position_ids.mapped('base_market_value')) + sum(row['market_value'] for row in self.non_equity)
        fpt = self.portfolio.position_ids.filtered(lambda row: row.symbol == 'FPT')
        result = scenario_engine.minimum_rebalance(fpt.market_value, total, 15.0, CLOSE['FPT'])
        self.assertEqual(result['quantity'], 160_900)
        self.assertLess((fpt.market_value - result['sale_value']) / total * 100.0, 15.0)

    # --- Suite C: FX, from posted journal items ------------------------------

    def test_fx_001_net_exposure_is_read_out_of_the_ledger(self):
        self._build_treasury_ledger()
        rows = exposure_engine.net_open_position(self.env, self.company.ids, self.as_of)
        by_currency = {}
        for row in rows:
            by_currency[row['currency_id']] = by_currency.get(row['currency_id'], 0.0) + row['amount']
        # USD: cash +1.0M, AR +4.5M, AP -9.0M. The +2.0M forward is a financial
        # hedge and is deliberately not in the balance-sheet exposure.
        self.assertAlmostEqual(by_currency[self.usd.id], -3_500_000, delta=1)
        self.assertAlmostEqual(by_currency[self.eur.id], -1_500_000, delta=1)

    def test_fx_003_hedge_ratio_is_computed_from_the_ledger_exposure(self):
        self._build_treasury_ledger()
        rows = exposure_engine.net_open_position(self.env, self.company.ids, self.as_of)
        usd = sum(row['amount'] for row in rows if row['currency_id'] == self.usd.id)
        result = scenario_engine.hedge_ratio_status(usd, 2_000_000)
        self.assertAlmostEqual(result['hedge_ratio_pct'], 57.14, places=2)
        self.assertEqual(result['status'], 'warning')
        self.assertAlmostEqual(result['residual_exposure'], -1_500_000, delta=1)

    def test_fx_004_hedge_alternatives_are_priced_off_the_ledger_exposure(self):
        self._build_treasury_ledger()
        rows = exposure_engine.net_open_position(self.env, self.company.ids, self.as_of)
        # Short USD, so the eligible amount to hedge is the absolute exposure.
        eligible = abs(sum(row['amount'] for row in rows if row['currency_id'] == self.usd.id))
        self.assertAlmostEqual(eligible, 3_500_000, delta=1)

        result = ai_advisory.hedge_alternatives(
            eligible, 2_000_000, USD_VND, 4.0,
            sources=['account.move.line:USD'],
        )
        options = {option['ratio_pct']: option for option in result['options']}
        self.assertEqual(sorted(options), [70.0, 80.0, 100.0])

        # 70%: hedge 2.45M, 0.45M still to buy, 1.05M left open, losing 1,050
        # VND per USD under the +4% shock.
        self.assertAlmostEqual(options[70.0]['required_hedge'], 2_450_000, delta=1)
        self.assertAlmostEqual(options[70.0]['incremental_hedge'], 450_000, delta=1)
        self.assertAlmostEqual(options[70.0]['residual_exposure'], 1_050_000, delta=1)
        self.assertAlmostEqual(options[70.0]['stress_loss'], 1.1025e9, delta=1e3)

        self.assertAlmostEqual(options[80.0]['required_hedge'], 2_800_000, delta=1)
        self.assertAlmostEqual(options[80.0]['incremental_hedge'], 800_000, delta=1)
        self.assertAlmostEqual(options[80.0]['residual_exposure'], 700_000, delta=1)
        self.assertAlmostEqual(options[80.0]['stress_loss'], 735e6, delta=1e3)

        self.assertAlmostEqual(options[100.0]['incremental_hedge'], 1_500_000, delta=1)
        self.assertAlmostEqual(options[100.0]['residual_exposure'], 0.0, delta=1)
        self.assertAlmostEqual(options[100.0]['stress_loss'], 0.0, delta=1)

        self.assertAlmostEqual(result['basis']['eligible_exposure'], 3_500_000, delta=1)
        self.assertAlmostEqual(result['basis']['rate_delta'], 1_050, delta=1)
        self.assertTrue(ai_advisory.is_grounded(result))

    # --- Suite D: liquidity, from posted journal items -----------------------

    def test_liq_001_opening_cash_and_thirty_day_ladder_from_the_ledger(self):
        self._build_treasury_ledger()
        opening = liquidity_engine.opening_liquidity(self.env, self.company.ids)[0]['amount']
        self.assertAlmostEqual(opening, 251.550 * B, delta=1e3)

        ladder = {row['horizon']: row for row in liquidity_engine.ladder(self.env, self.company.ids, as_of=self.as_of)}
        thirty = ladder[30]
        self.assertAlmostEqual(thirty['inflow'], 348.125 * B, delta=1e3)
        self.assertAlmostEqual(thirty['outflow'], -608.950 * B, delta=1e3)
        closing = opening + thirty['cumulative_flow']
        self.assertAlmostEqual(closing, -9.275 * B, delta=1e3)

        status, draw, gap = liquidity_engine.liquidity_status(closing, 100 * B, 150 * B)
        self.assertEqual(status, 'amber')
        self.assertAlmostEqual(draw, 109.275 * B, delta=1e3)
        self.assertEqual(gap, 0.0)

    def test_liq_002_delayed_receivables_turn_the_forecast_red(self):
        self._build_treasury_ledger()
        opening = liquidity_engine.opening_liquidity(self.env, self.company.ids)[0]['amount']
        delayed = {row['horizon']: row for row in liquidity_engine.ladder(self.env, self.company.ids, as_of=self.as_of, ar_delay_days=45)}[30]
        # With receivables pushed beyond the window, only the outflows remain.
        self.assertAlmostEqual(delayed['inflow'], 0.0, delta=1e3)
        closing = opening + delayed['cumulative_flow']
        status, draw, gap = liquidity_engine.liquidity_status(closing, 100 * B, 150 * B)
        self.assertEqual(status, 'red')
        self.assertGreater(gap, 0.0)

    # --- Suite G: chaos ------------------------------------------------------

    def test_chaos_ai_outage_does_not_stop_treasury_operations(self):
        """Scenario pack §53: AI is an enhancement, not a dependency.

        The failure mode worth guarding is the quiet one: an advisory helper
        raising inside a shared code path and taking exposure, liquidity, risk
        and the approval chain down with it. So the AI surface is made to fail
        hard, and the core numbers must still come out of the ledger.
        """
        self._build_treasury_ledger()

        def dead_service(*args, **kwargs):
            raise RuntimeError('AI service unavailable')

        with patch.object(ai_advisory, 'market_regime', dead_service), \
             patch.object(ai_advisory, 'risk_attribution', dead_service), \
             patch.object(ai_advisory, 'hedge_alternatives', dead_service), \
             patch.object(ai_advisory, 'hedge_recommendation', dead_service):
            with self.assertRaises(RuntimeError):
                ai_advisory.market_regime({'index_change_pct': -2.0, 'as_of': self.as_of})

            # Exposure, straight off the ledger.
            rows = exposure_engine.net_open_position(self.env, self.company.ids, self.as_of)
            usd = sum(row['amount'] for row in rows if row['currency_id'] == self.usd.id)
            self.assertAlmostEqual(usd, -3_500_000, delta=1)

            # Liquidity, unchanged by the outage.
            opening = liquidity_engine.opening_liquidity(self.env, self.company.ids)[0]['amount']
            self.assertAlmostEqual(opening, 251.550 * B, delta=1e3)
            thirty = {row['horizon']: row for row in liquidity_engine.ladder(
                self.env, self.company.ids, as_of=self.as_of)}[30]
            self.assertAlmostEqual(opening + thirty['cumulative_flow'], -9.275 * B, delta=1e3)

            # Risk limits still evaluate, and still breach.
            self.env['ir.config_parameter'].sudo().set_param(
                'treasury.risk_limits.%s' % self.company.id,
                json.dumps({'single_name_pct': {'target': 15, 'warning': 15, 'hard': 20}}),
            )
            metrics = risk_engine.portfolio_metrics(self.env, self.company)
            statuses = {row['metric']: row['status']
                        for row in risk_engine.limit_utilization(self.env, self.company, metrics)}
            self.assertEqual(statuses['single_name_pct'], 'hard')

            # Deterministic scenario maths is not an AI call either.
            stress = scenario_engine.hedge_ratio_status(usd, 2_000_000)
            self.assertEqual(stress['status'], 'warning')

            # And the governance chain still refuses an ungoverned jump, which
            # is the control an AI outage must never relax.
            # The accounting fixture user has no project rights; the control
            # under test is the stage gate, not project ACL.
            self.env.user.group_ids |= self.env.ref('project.group_project_manager')
            template = self.env.ref('insilos_treasury_market_risk.project_treasury_governance')
            project = template.copy({'name': 'Chaos AI outage', 'is_template': False})
            task = self.env['project.task'].create({
                'name': 'Case during AI outage', 'project_id': project.id,
                'stage_id': self.env.ref('insilos_treasury_market_risk.stage_decision_proposal').id,
            })
            with self.assertRaises(UserError):
                task.write({'stage_id': self.env.ref('insilos_treasury_market_risk.stage_execution').id})

    # --- Suite F: scale ------------------------------------------------------

    def _warm_query_count(self, run):
        """Queries used by a *warm* call, so ormcache misses are not counted.

        The first call fills the registry and property caches; measuring that
        one would report a constant overhead that hides the growth this test
        is looking for.
        """
        run()
        self.env.flush_all()
        self.env.invalidate_all()
        run()
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.cr.sql_log_count
        run()
        return self.cr.sql_log_count - before

    def test_scale_engines_do_not_issue_a_query_per_ledger_row(self):
        """Query cost must stay flat as the ledger grows.

        The engines aggregate with `_read_group`, so a tenant-sized ledger
        costs the same as a demo one. A refactor that walks the rows in
        Python would still return the right numbers, which is exactly why the
        arithmetic suites cannot catch it — only the query count can.
        """
        self._build_treasury_ledger()
        cash = self.env['account.account'].search(
            [('company_ids', 'in', self.company.ids), ('code', '=', 'CASHUSD')], limit=1)
        receivable = self.company_data['default_account_receivable']

        def measure():
            return (
                self._warm_query_count(
                    lambda: exposure_engine.net_open_position(self.env, self.company.ids, self.as_of)),
                self._warm_query_count(
                    lambda: liquidity_engine.ladder(self.env, self.company.ids, as_of=self.as_of)),
                self._warm_query_count(
                    lambda: liquidity_engine.opening_liquidity(self.env, self.company.ids)),
            )

        small = measure()

        # Fan out over distinct partners and maturities: grouping keys, not
        # just more rows under the keys already present.
        partners = self.env['res.partner'].create(
            [{'name': 'Scale counterparty %02d' % index} for index in range(20)])
        for index, partner in enumerate(partners):
            self._entry([
                self._monetary_line(cash, 1_000 * USD_VND, self.usd, 1_000,
                                    maturity=self.as_of + timedelta(days=index + 1), partner=partner),
                self._monetary_line(receivable, 2_000 * USD_VND, self.usd, 2_000,
                                    maturity=self.as_of + timedelta(days=index + 2), partner=partner),
            ], 'Scale entry %02d' % index)

        large = measure()
        self.assertEqual(
            large, small,
            'Query count grew with the ledger: %s -> %s. An engine is reading row by row.' % (small, large))

        # The extra rows must actually reach the engines, otherwise the flat
        # query count above would only prove the fixture did nothing.
        rows = exposure_engine.net_open_position(self.env, self.company.ids, self.as_of)
        usd = sum(row['amount'] for row in rows if row['currency_id'] == self.usd.id)
        self.assertAlmostEqual(usd, -3_500_000 + 20 * 3_000, delta=1)

    # --- Suite E: combined -----------------------------------------------------

    def test_comb_002_economic_loss_and_funding_gap_stay_separate(self):
        self._build_treasury_ledger()
        holdings = [
            {'symbol': position.symbol, 'asset_class': 'equity', 'market_value': position.base_market_value}
            for position in self.portfolio.position_ids
        ] + self.non_equity
        stress = scenario_engine.stress_loss(holdings, {'FPT': -12.0, 'HPG': -15.0, 'VIC': -10.0, 'GOV': -4.8, 'CORP': -5.0})
        self.assertAlmostEqual(stress['total_loss'], 42.238 * B, delta=1e6)

        combined = scenario_engine.combined_stress(stress['total_loss'], 4.329 * B, 189.400 * B)
        self.assertAlmostEqual(combined['economic_loss'], 46.567 * B, delta=1e6)
        self.assertNotIn('total', combined)
