# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""TEST SUITE I & J — accounting is the source of truth (ACC-001..003) and
multi-company elimination (MULTI)."""

from datetime import date, timedelta

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.insilos_treasury_market_risk.services import exposure_engine
from odoo.tests.common import tagged


@tagged('post_install', '-at_install', 'treasury_market_risk', 'accounting_truth')
class TestAccountingIsTheSourceOfTruth(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.as_of = date(2026, 8, 7)
        cls.foreign = cls.setup_other_currency('EUR')

    def _post_invoice(self, move_type, amount, maturity, currency, company=None):
        company = company or self.env.company
        move = self.env['account.move'].with_company(company).create({
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
            'invoice_date': self.as_of,
            'invoice_payment_term_id': False,
            'invoice_date_due': maturity,
            'invoice_line_ids': [(0, 0, {'name': 'Line', 'quantity': 1, 'price_unit': amount, 'tax_ids': []})],
        })
        move.action_post()
        return move

    def _foreign_amount(self):
        rows = exposure_engine.net_open_position(self.env, self.env.company.ids, self.as_of)
        return sum(row['amount'] for row in rows if row['currency_id'] == self.foreign.id)

    def test_acc_001_realised_fx_comes_from_accounting_and_is_not_recomputed(self):
        """A settled invoice leaves no residual, so treasury reports no exposure.

        The realised gain belongs to the ledger. Treasury deriving its own would
        be a second, conflicting FX P&L for the same event.
        """
        invoice = self._post_invoice('out_invoice', 1000, self.as_of + timedelta(days=20), self.foreign)
        self.assertAlmostEqual(self._foreign_amount(), 1000.0)

        payment_date = self.as_of + timedelta(days=10)
        self.env['res.currency.rate'].create({'currency_id': self.foreign.id, 'name': payment_date, 'rate': 4.0, 'company_id': self.env.company.id})
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=invoice.ids,
        ).create({'payment_date': payment_date}).action_create_payments()

        self.assertIn(invoice.payment_state, ('paid', 'in_payment'))
        # Exposure is gone because the residual is gone; nothing was netted by hand.
        self.assertAlmostEqual(self._foreign_amount(), 0.0)
        exchange_lines = invoice.line_ids.filtered(lambda line: line.account_id.account_type not in ('asset_receivable', 'liability_payable'))
        self.assertTrue(exchange_lines, 'The ledger, not treasury, records the FX result.')

    def test_acc_003_a_ledger_change_is_reflected_on_the_next_refresh(self):
        invoice = self._post_invoice('out_invoice', 1000, self.as_of + timedelta(days=20), self.foreign)
        self.assertAlmostEqual(self._foreign_amount(), 1000.0)
        invoice.button_draft()
        # A draft move is not posted, so it is not an exposure. No cached copy
        # keeps the old number alive.
        self.assertAlmostEqual(self._foreign_amount(), 0.0)
        invoice.action_post()
        self.assertAlmostEqual(self._foreign_amount(), 1000.0)

    def test_acc_002_a_sale_moves_position_cash_and_realised_pnl_together(self):
        self.env.user.group_ids |= self.env.ref('insilos_capital_markets_decision_governance.group_portfolio_manager')
        self.env.user.group_ids |= self.env.ref('project.group_project_manager')
        portfolio = self.env['capital.portfolio'].create({'name': 'ACC book', 'company_id': self.env.company.id, 'currency_id': self.env.company.currency_id.id})
        instrument = self.env['capital.instrument'].create({'symbol': 'ACCX', 'exchange': 'HOSE', 'currency_id': self.env.company.currency_id.id})
        position = self.env['capital.position'].create({'portfolio_id': portfolio.id, 'instrument_id': instrument.id, 'quantity': 1_000, 'average_cost': 100})
        position.with_context(capital_market_refresh=True).write({'last_price': 120})

        reviewer = self.env['res.users'].create({'name': 'ACC Reviewer', 'login': 'acc_reviewer', 'group_ids': [(4, self.env.ref('insilos_capital_markets_decision_governance.group_decision_reviewer').id), (4, self.env.ref('project.group_project_user').id)]})
        approver = self.env['res.users'].create({'name': 'ACC Approver', 'login': 'acc_approver', 'group_ids': [(4, self.env.ref('insilos_capital_markets_decision_governance.group_decision_approver').id), (4, self.env.ref('project.group_project_user').id)]})
        project = self.env['project.project'].create({'name': 'ACC gov', 'type_ids': [(6, 0, [
            self.env.ref('insilos_capital_markets_decision_governance.stage_intake').id,
            self.env.ref('insilos_capital_markets_decision_governance.stage_approval').id,
        ])]})
        case = self.env['project.task'].with_user(reviewer).create({
            'name': 'Sell ACCX', 'project_id': project.id, 'user_ids': [(4, reviewer.id)],
            'description': 'Trim the ACCX holding after the review of the concentration report and alternatives.',
        })
        self.env['ir.attachment'].create({'name': 'e.txt', 'raw': b'evidence', 'res_model': 'project.task', 'res_id': case.id})
        case.with_user(approver).stage_id = self.env.ref('insilos_capital_markets_decision_governance.stage_approval')

        order = self.env['capital.order'].submit({
            'client_order_id': 'ACC-002', 'portfolio_id': portfolio.id, 'instrument_id': instrument.id,
            'side': 'sell', 'decision_case_id': case.id, 'approved_quantity': 400, 'quantity': 400,
        })
        order.register_fill(400, 120)
        self.assertEqual(order.executed_quantity, 400)
        self.assertAlmostEqual(order.realised_pnl, 400 * (120 - 100))
        # Treasury reports the trade; the ledger entry remains the accountant's
        # to post, and the two must agree on the same realised figure.
        self.assertAlmostEqual(order.average_execution_price, 120)


@tagged('post_install', '-at_install', 'treasury_market_risk', 'treasury_l1', 'treasury_l3', 'multi_company')
class TestGroupElimination(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.as_of = date(2026, 8, 7)
        # A currency the companies do not keep their books in; the group's
        # exposure is precisely what is not in the reporting currency.
        cls.usd = cls.setup_other_currency('EUR')
        cls.manufacturing = cls.env.company
        cls.trading = cls.setup_other_company(name='MULTI Trading Co')['company']
        cls.env.user.company_ids |= cls.trading

    def _invoice(self, company, move_type, amount, partner):
        move = self.env['account.move'].with_company(company).with_context(allowed_company_ids=[company.id]).create({
            'move_type': move_type, 'partner_id': partner.id, 'currency_id': self.usd.id,
            'invoice_date': self.as_of, 'invoice_payment_term_id': False,
            'invoice_date_due': self.as_of + timedelta(days=20),
            'invoice_line_ids': [(0, 0, {'name': 'L', 'quantity': 1, 'price_unit': amount, 'tax_ids': []})],
        })
        move.action_post()
        return move

    def test_multi_entity_keeps_intercompany_and_group_eliminates_it(self):
        companies = self.manufacturing | self.trading
        # External: manufacturing owes 5.0, trading is owed 3.0.
        self._invoice(self.manufacturing, 'in_invoice', 5_000_000, self.partner_a)
        self._invoice(self.trading, 'out_invoice', 3_000_000, self.partner_a)
        # Intercompany: manufacturing owes trading 1.5, trading is owed 1.5.
        self._invoice(self.manufacturing, 'in_invoice', 1_500_000, self.trading.partner_id)
        self._invoice(self.trading, 'out_invoice', 1_500_000, self.manufacturing.partner_id)

        entities = {row['company_id']: row for row in exposure_engine.entity_exposure(self.env, companies.ids, self.as_of) if row['currency_id'] == self.usd.id}
        self.assertAlmostEqual(entities[self.manufacturing.id]['external'], -5_000_000)
        self.assertAlmostEqual(entities[self.manufacturing.id]['intercompany'], -1_500_000)
        self.assertAlmostEqual(entities[self.manufacturing.id]['entity_total'], -6_500_000)
        self.assertAlmostEqual(entities[self.trading.id]['external'], 3_000_000)
        self.assertAlmostEqual(entities[self.trading.id]['intercompany'], 1_500_000)

        (group,) = [row for row in exposure_engine.group_exposure(self.env, companies.ids, self.as_of) if row['currency_id'] == self.usd.id]
        self.assertAlmostEqual(group['intercompany_eliminated'], 0.0)
        self.assertAlmostEqual(group['net_external'], -2_000_000)
