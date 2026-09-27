# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""GOV-001 and TEST SUITE H — EXECUTION (EXE-001..003), reference data MR-20260720."""

import json
from pathlib import Path

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

MODULE = 'insilos_capital_markets_decision_governance'
MR_20260720 = json.loads((Path(__file__).parents[2] / 'insilos_market_data' / 'tests' / 'fixtures' / 'mr_20260720.json').read_text())
FPT_CLOSE = MR_20260720['instruments']['FPT']['bars'][-1]['close']
RATIONALE = 'Reduce the FPT overweight after the committee reviewed the concentration report and the alternatives.'


@tagged('post_install', '-at_install', 'capital_markets', 'execution')
class TestCapitalMarketsExecution(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reviewer = cls.env['res.users'].create({'name': 'EXE Reviewer', 'login': 'exe_reviewer', 'group_ids': [(4, cls.env.ref(f'{MODULE}.group_decision_reviewer').id), (4, cls.env.ref('project.group_project_user').id)]})
        cls.approver = cls.env['res.users'].create({'name': 'EXE Approver', 'login': 'exe_approver', 'group_ids': [(4, cls.env.ref(f'{MODULE}.group_decision_approver').id), (4, cls.env.ref('project.group_project_user').id)]})
        cls.project = cls.env['project.project'].create({
            'name': 'EXE governance',
            'type_ids': [(6, 0, [cls.env.ref(f'{MODULE}.stage_intake').id, cls.env.ref(f'{MODULE}.stage_review').id, cls.env.ref(f'{MODULE}.stage_approval').id, cls.env.ref(f'{MODULE}.stage_closed').id])],
        })
        # GOV-001: 20B threshold, and 300,000 FPT at 67,100 is 20.13B.
        cls.portfolio = cls.env['capital.portfolio'].create({'name': 'EXE book', 'ic_threshold': 20_000_000_000})
        cls.instrument = cls.env['capital.instrument'].search([('symbol', '=', 'FPT'), ('exchange', '=', 'HOSE')], limit=1)
        if not cls.instrument:
            cls.instrument = cls.env['capital.instrument'].create({'symbol': 'FPT', 'exchange': 'HOSE', 'currency_id': cls.env.ref('base.VND').id})
        cls.position = cls.env['capital.position'].create({'portfolio_id': cls.portfolio.id, 'instrument_id': cls.instrument.id, 'quantity': 400_000, 'average_cost': 60_000})
        cls.position.with_context(capital_market_refresh=True).write({'last_price': FPT_CLOSE, 'price_as_of': fields.Datetime.now()})

    def _case(self, approved=True, ic=False):
        case = self.env['project.task'].with_user(self.reviewer).create({
            'name': 'Sell FPT', 'project_id': self.project.id,
            'stage_id': self.env.ref(f'{MODULE}.stage_intake').id,
            'user_ids': [(4, self.reviewer.id)], 'description': RATIONALE,
        })
        self.env['ir.attachment'].create({'name': 'ic.txt', 'raw': b'committee minutes', 'res_model': 'project.task', 'res_id': case.id})
        if approved:
            case.with_user(self.approver).stage_id = self.env.ref(f'{MODULE}.stage_approval')
        if ic:
            case.with_user(self.approver).action_record_ic_approval()
        return case

    def _order(self, case, quantity=300_000, approved_quantity=300_000, client_order_id='IC-2026-001'):
        return self.env['capital.order'].submit({
            'client_order_id': client_order_id, 'portfolio_id': self.portfolio.id,
            'instrument_id': self.instrument.id, 'side': 'sell', 'decision_case_id': case.id,
            'approved_quantity': approved_quantity, 'quantity': quantity,
        })

    def test_gov_001_above_threshold_needs_ic_approval_before_execution(self):
        case = self._case(approved=True, ic=False)
        order = self._order(case)
        self.assertEqual(order.notional, 300_000 * FPT_CLOSE)
        self.assertEqual(order.notional, 20_130_000_000)
        self.assertTrue(order.requires_ic)
        with self.assertRaises(UserError):
            order.register_fill(100_000, FPT_CLOSE)
        case.with_user(self.approver).action_record_ic_approval()
        self.assertEqual(case.ic_approved_by_id, self.approver)
        self.assertTrue(case.ic_approved_at)
        order.register_fill(100_000, FPT_CLOSE)
        self.assertEqual(order.executed_quantity, 100_000)

    def test_gov_001_below_threshold_needs_no_committee(self):
        case = self._case(approved=True, ic=False)
        order = self._order(case, quantity=100_000, approved_quantity=100_000, client_order_id='IC-2026-SMALL')
        self.assertFalse(order.requires_ic)
        order.register_fill(100_000, FPT_CLOSE)
        self.assertEqual(order.state, 'filled')

    def test_exe_001_a_retried_submission_produces_one_order(self):
        case = self._case(ic=True)
        payload = {
            'client_order_id': 'IC-2026-001', 'portfolio_id': self.portfolio.id,
            'instrument_id': self.instrument.id, 'side': 'sell', 'decision_case_id': case.id,
            'approved_quantity': 300_000, 'quantity': 300_000,
        }
        first = self.env['capital.order'].submit(payload)
        retried = self.env['capital.order'].submit(dict(payload))
        self.assertEqual(first, retried)
        self.assertEqual(self.env['capital.order'].search_count([('client_order_id', '=', 'IC-2026-001')]), 1)
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env['capital.order'].create(payload)

    def test_exe_002_partial_fills_produce_weighted_price_and_open_quantity(self):
        case = self._case(ic=True)
        order = self._order(case)
        order.register_fill(100_000, 67_100)
        order.register_fill(100_000, 67_000)
        self.assertEqual(order.state, 'partial')
        order.register_fill(50_000, 66_800)
        self.assertEqual(order.executed_quantity, 250_000)
        self.assertEqual(order.open_quantity, 50_000)
        expected = (100_000 * 67_100 + 100_000 * 67_000 + 50_000 * 66_800) / 250_000
        self.assertAlmostEqual(order.average_execution_price, expected, places=4)
        # Realised P&L is executed quantity against average cost, not the whole ticket.
        self.assertAlmostEqual(order.realised_pnl, 250_000 * expected - 250_000 * 60_000, places=2)
        self.assertEqual(order.state, 'partial')
        with self.assertRaises(UserError):
            order.register_fill(60_000, 67_000)

    def test_exe_003_dealer_cannot_exceed_the_approved_quantity(self):
        case = self._case(ic=True)
        with self.assertRaises(ValidationError):
            self._order(case, quantity=350_000, approved_quantity=300_000, client_order_id='IC-2026-OVER')
        order = self._order(case)
        with self.assertRaises(ValidationError):
            order.quantity = 350_000
        # A new, larger approval is the only way through.
        order.write({'approved_quantity': 350_000, 'quantity': 350_000})
        self.assertEqual(order.quantity, 350_000)

    def test_exe_003_execution_is_blocked_before_approval(self):
        case = self._case(approved=False)
        order = self._order(case, client_order_id='IC-2026-EARLY')
        with self.assertRaises(UserError):
            order.register_fill(1_000, FPT_CLOSE)
        self.assertEqual(order.executed_quantity, 0)
