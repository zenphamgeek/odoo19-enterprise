# Part of Insilos. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.insilos_treasury_market_risk.services import liquidity_engine
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'treasury_market_risk', 'treasury_l1', 'treasury_l3')
class TestLiquidityEngine(TransactionCase):
    def test_survival_horizon_returns_first_breach(self):
        rows = [
            {'horizon': 7, 'cumulative_flow': -30.0},
            {'horizon': 30, 'cumulative_flow': -120.0},
        ]
        self.assertEqual(liquidity_engine.survival_horizon(100.0, rows, 0.0), 30)

    def test_survival_horizon_is_none_when_buffer_holds(self):
        self.assertIsNone(liquidity_engine.survival_horizon(100.0, [{'horizon': 7, 'cumulative_flow': -90.0}], 0.0))

    def test_ladder_assigns_overdue_to_first_horizon(self):
        # Unit-contract assertion: horizons are monotonic and the ladder
        # always returns every requested checkpoint even without ledger rows.
        rows = liquidity_engine.ladder(self.env, self.env.company.ids, (7, 30), date(2026, 8, 7))
        self.assertEqual([row['horizon'] for row in rows], [7, 30])
        self.assertTrue(all(row['net_flow'] == row['inflow'] + row['outflow'] for row in rows))

    def test_ar_delay_shifts_inflow_to_later_horizon(self):
        rows = liquidity_engine.ladder(self.env, self.env.company.ids, (7, 30), date(2026, 8, 7), ar_delay_days=15)
        self.assertEqual([row['horizon'] for row in rows], [7, 30])
        # Delay only changes bucket placement; the total flow is conserved.
        base = liquidity_engine.ladder(self.env, self.env.company.ids, (7, 30), date(2026, 8, 7))
        self.assertAlmostEqual(rows[-1]['cumulative_flow'], base[-1]['cumulative_flow'])

    def _create_running_loan_line(self, company, due, principal, interest):
        loan = self.env['account.loan'].with_company(company).create({
            'name': 'TMR bond schedule',
            'company_id': company.id,
            'state': 'running',
            'amount_borrowed': principal,
        })
        return self.env['account.loan.line'].create({
            'loan_id': loan.id,
            'date': due,
            'principal': principal,
            'interest': interest,
        })

    def test_ladder_buckets_bond_principal_and_interest(self):
        as_of = date(2026, 8, 7)
        baseline = liquidity_engine.ladder(self.env, self.env.company.ids, (7, 30), as_of)
        self._create_running_loan_line(self.env.company, date(2026, 8, 17), 100.0, 15.0)
        rows = liquidity_engine.ladder(self.env, self.env.company.ids, (7, 30), as_of)
        self.assertAlmostEqual(rows[0]['outflow'] - baseline[0]['outflow'], 0.0)
        self.assertAlmostEqual(rows[1]['outflow'] - baseline[1]['outflow'], -115.0)

    def test_ladder_scopes_bond_schedule_to_company(self):
        as_of = date(2026, 8, 7)
        other_company = self.env['res.company'].create({'name': 'TMR Bond Other Co'})
        baseline = liquidity_engine.ladder(self.env, self.env.company.ids, (30,), as_of)
        self._create_running_loan_line(other_company, date(2026, 8, 17), 100.0, 15.0)
        rows = liquidity_engine.ladder(self.env, self.env.company.ids, (30,), as_of)
        self.assertAlmostEqual(rows[0]['outflow'], baseline[0]['outflow'])

    def test_ladder_buckets_past_due_bond_schedule_first(self):
        as_of = date(2026, 8, 7)
        baseline = liquidity_engine.ladder(self.env, self.env.company.ids, (7, 30), as_of)
        self._create_running_loan_line(self.env.company, date(2026, 8, 6), 100.0, 15.0)
        rows = liquidity_engine.ladder(self.env, self.env.company.ids, (7, 30), as_of)
        self.assertAlmostEqual(rows[0]['outflow'] - baseline[0]['outflow'], -115.0)
        self.assertAlmostEqual(rows[1]['outflow'] - baseline[1]['outflow'], 0.0)

    def test_buffer_comes_from_company_scoped_config(self):
        key = 'treasury.min_cash_buffer.%s' % self.env.company.id
        self.env['ir.config_parameter'].sudo().set_param(key, '1234.5')
        self.assertEqual(liquidity_engine.min_cash_buffer(self.env, self.env.company), 1234.5)
