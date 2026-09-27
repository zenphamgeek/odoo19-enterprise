# Part of Insilos. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalLedger(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portfolio = cls.env['capital.portfolio'].create({'name': 'USD Book', 'currency_id': cls.env.ref('base.USD').id})
        cls.instrument = cls.env['capital.instrument'].create({'symbol': 'ACME', 'exchange': 'XNAS', 'currency_id': cls.env.ref('base.USD').id})

    def test_position_uses_instrument_currency_and_is_long_only(self):
        position = self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'instrument_id': self.instrument.id, 'quantity': 10, 'average_cost': 12, 'last_price': 15})
        self.assertEqual(position.currency_id, self.instrument.currency_id)
        self.assertEqual(position.market_value, 150)
        negative = self.env['capital.instrument'].create({'symbol': 'BETA', 'exchange': 'XNAS', 'currency_id': self.instrument.currency_id.id})
        with self.assertRaises(ValidationError):
            self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'instrument_id': negative.id, 'quantity': -1})

    def test_fx_pair_rejects_same_currency(self):
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env['capital.fx.rate'].create({'base_currency_id': self.env.ref('base.USD').id, 'quote_currency_id': self.env.ref('base.USD').id, 'rate': 1, 'as_of': fields.Datetime.now()})

    def test_reconciliation_hash_and_maker_approval_gate(self):
        attachment = self.env['ir.attachment'].create({'name': 'broker.csv', 'raw': b'symbol,quantity\nACME,10\n', 'mimetype': 'text/csv'})
        reconciliation = self.env['capital.reconciliation.import'].create({'portfolio_id': self.portfolio.id, 'broker': 'Manual broker', 'as_of': fields.Datetime.now(), 'currency_id': self.env.ref('base.USD').id, 'csv_attachment_id': attachment.id})
        self.assertEqual(len(reconciliation.csv_sha256), 64)
        with self.assertRaises(UserError):
            reconciliation.action_submit()
        reconciliation.write({'state': 'review', 'reviewer_id': self.env.ref('base.user_admin').id})
        with self.assertRaises(UserError):
            reconciliation.action_approve()

    def test_ledger_approval_requires_independent_completed_review(self):
        attachment = self.env['ir.attachment'].create({'name': 'review.csv', 'raw': b'symbol,quantity\nACME,10\n', 'mimetype': 'text/csv'})
        reconciliation = self.env['capital.reconciliation.import'].create({'portfolio_id': self.portfolio.id, 'broker': 'Manual broker', 'as_of': fields.Datetime.now(), 'currency_id': self.env.ref('base.USD').id, 'csv_attachment_id': attachment.id})
        with self.assertRaises(UserError):
            reconciliation.action_approve()
        reconciliation.write({'state': 'review', 'reviewer_id': self.env.user.id})
        with self.assertRaises(UserError):
            reconciliation.action_approve()

        evidence = self.env['ir.attachment'].create({'name': 'review.txt', 'raw': b'review evidence', 'mimetype': 'text/plain'})
        action = self.env['capital.corporate.action'].create({'name': 'Review split', 'instrument_id': self.instrument.id, 'action_type': 'split', 'effective_date': fields.Date.today(), 'ratio': 2, 'evidence_attachment_id': evidence.id})
        with self.assertRaises(UserError):
            action.action_approve()
        action.write({'state': 'review', 'reviewer_id': self.env.user.id})
        with self.assertRaises(UserError):
            action.action_approve()

    def test_reversal_requires_approved_record_and_audit_reason(self):
        admin = self.env['res.users'].create({'name': 'Ledger Governance Admin', 'login': 'ledger_governance_admin', 'group_ids': [(4, self.env.ref('insilos_capital_markets_decision_governance.group_governance_admin').id)]})
        evidence = self.env['ir.attachment'].create({'name': 'reverse.txt', 'raw': b'reversal evidence', 'mimetype': 'text/plain'})
        action = self.env['capital.corporate.action'].create({'name': 'Reverse split', 'instrument_id': self.instrument.id, 'action_type': 'split', 'effective_date': fields.Date.today(), 'ratio': 2, 'evidence_attachment_id': evidence.id})
        with self.assertRaises(UserError):
            action.with_user(admin).action_reverse()
        action.write({'state': 'approved', 'reversal_reason': 'no replacement: duplicate issuer announcement'})
        action.with_user(admin).action_reverse()
        self.assertEqual(action.state, 'reversed')

        attachment = self.env['ir.attachment'].create({'name': 'reverse.csv', 'raw': b'symbol,quantity\nACME,10\n', 'mimetype': 'text/csv'})
        reconciliation = self.env['capital.reconciliation.import'].create({'portfolio_id': self.portfolio.id, 'broker': 'Manual broker', 'as_of': fields.Datetime.now(), 'currency_id': self.env.ref('base.USD').id, 'csv_attachment_id': attachment.id, 'state': 'approved'})
        with self.assertRaises(UserError):
            reconciliation.with_user(admin).action_reverse()
        reconciliation.write({'reversal_reason': 'no replacement: source file duplicated'})
        reconciliation.with_user(admin).action_reverse()
        self.assertEqual(reconciliation.state, 'reversed')

    def test_reversal_accepts_only_same_scope_correction(self):
        admin = self.env['res.users'].create({'name': 'Correction Governance Admin', 'login': 'correction_governance_admin', 'group_ids': [(4, self.env.ref('insilos_capital_markets_decision_governance.group_governance_admin').id)]})
        evidence = self.env['ir.attachment'].create({'name': 'correct.txt', 'raw': b'correction evidence', 'mimetype': 'text/plain'})
        correction = self.env['capital.corporate.action'].create({'name': 'Correct split', 'instrument_id': self.instrument.id, 'action_type': 'split', 'effective_date': fields.Date.today(), 'ratio': 3, 'evidence_attachment_id': evidence.id})
        original = self.env['capital.corporate.action'].create({'name': 'Incorrect split', 'instrument_id': self.instrument.id, 'action_type': 'split', 'effective_date': fields.Date.today(), 'ratio': 2, 'evidence_attachment_id': evidence.id, 'state': 'approved', 'superseded_by_id': correction.id, 'reversal_reason': 'corrected issuer ratio'})
        original.with_user(admin).action_reverse()
        self.assertEqual(original.state, 'reversed')

        other = self.env['capital.instrument'].create({'symbol': 'OTHER', 'exchange': 'XNAS', 'currency_id': self.instrument.currency_id.id})
        bad = self.env['capital.corporate.action'].create({'name': 'Bad correction', 'instrument_id': self.instrument.id, 'action_type': 'split', 'effective_date': fields.Date.today(), 'ratio': 2, 'evidence_attachment_id': evidence.id, 'state': 'approved', 'reversal_reason': 'wrong correction', 'superseded_by_id': self.env['capital.corporate.action'].create({'name': 'Other action', 'instrument_id': other.id, 'action_type': 'split', 'effective_date': fields.Date.today(), 'ratio': 2, 'evidence_attachment_id': evidence.id}).id})
        with self.assertRaises(UserError):
            bad.with_user(admin).action_reverse()

    def test_split_applies_quantity_and_cost_without_changing_total_cost(self):
        position = self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'instrument_id': self.instrument.id, 'quantity': 10, 'average_cost': 12})
        evidence = self.env['ir.attachment'].create({'name': 'split.txt', 'raw': b'approved split', 'mimetype': 'text/plain'})
        action = self.env['capital.corporate.action'].create({'name': 'Two for one', 'instrument_id': self.instrument.id, 'action_type': 'split', 'effective_date': fields.Date.today(), 'ratio': 2, 'evidence_attachment_id': evidence.id, 'state': 'approved'})
        action.action_apply()
        self.assertEqual(action.state, 'applied')
        self.assertEqual(position.quantity, 20)
        self.assertEqual(position.average_cost, 6)
        self.assertEqual(position.cost_value, 120)

    def test_reference_data_is_tenant_wide_by_design_not_by_omission(self):
        """Instruments, FX and benchmarks are shared; that must be deliberate.

        VN30 is one index, not one index per desk, so these models carry no
        `company_id` and no company record rule. The risk is that a reader
        assumes per-company reference data and builds on it. Pin the model
        down instead: shared rows, but no ordinary user may delete them, so
        one desk cannot destroy another desk's valuation inputs.
        """
        shared = ('capital.instrument', 'capital.fx.rate', 'capital.benchmark')
        for model in shared:
            self.assertNotIn('company_id', self.env[model]._fields,
                             '%s is reference data; adding company_id changes valuation scope' % model)
            self.assertFalse(self.env['ir.rule'].search([
                ('model_id.model', '=', model), ('active', '=', True)]),
                '%s gained a record rule; the sharing contract changed' % model)

        manager = self.env['res.users'].create({
            'name': 'Ref data manager', 'login': 'cmdg_refdata_mgr',
            'group_ids': [(4, self.env.ref(
                'insilos_capital_markets_decision_governance.group_portfolio_manager').id)],
        })
        for model in shared:
            records = self.env[model].with_user(manager)
            self.assertTrue(records.has_access('write'),
                            'the fixture user must really be a portfolio manager on %s' % model)
            self.assertFalse(records.has_access('unlink'),
                             'a portfolio manager must not be able to delete shared %s rows' % model)

    def test_split_reaches_holders_the_applying_user_cannot_read(self):
        """A split is an issuer fact, so a partial application is a wrong book.

        The dangerous version of this bug is silent: the action flips to
        `applied`, the applier's own positions look right, and another
        company's positions keep a pre-split cost basis forever. Nothing in
        the single-company arithmetic tests can see that.
        """
        other_company = self.env['res.company'].create({'name': 'Split desk B'})
        other_book = self.env['capital.portfolio'].create({
            'name': 'Desk B book', 'company_id': other_company.id,
            'currency_id': self.instrument.currency_id.id})
        mine = self.env['capital.position'].create({
            'portfolio_id': self.portfolio.id, 'instrument_id': self.instrument.id,
            'quantity': 10, 'average_cost': 12})
        theirs = self.env['capital.position'].create({
            'portfolio_id': other_book.id, 'instrument_id': self.instrument.id,
            'quantity': 40, 'average_cost': 8})

        applier = self.env['res.users'].create({
            'name': 'Desk A manager', 'login': 'cmdg_split_desk_a',
            'company_id': self.portfolio.company_id.id,
            'company_ids': [(6, 0, [self.portfolio.company_id.id])],
            'group_ids': [(4, self.env.ref(
                'insilos_capital_markets_decision_governance.group_portfolio_manager').id)],
        })
        self.assertFalse(self.env['capital.position'].with_user(applier).search(
            [('id', '=', theirs.id)]), 'the fixture must actually hide the other book')

        evidence = self.env['ir.attachment'].create({
            'name': 'split-multi.txt', 'raw': b'approved split', 'mimetype': 'text/plain'})
        action = self.env['capital.corporate.action'].create({
            'name': 'Two for one, all holders', 'instrument_id': self.instrument.id,
            'action_type': 'split', 'effective_date': fields.Date.today(), 'ratio': 2,
            'evidence_attachment_id': evidence.id, 'state': 'approved'})
        action.with_user(applier).action_apply()

        self.assertEqual(mine.quantity, 20)
        self.assertEqual(mine.average_cost, 6)
        # The holder the applier cannot even see must be adjusted too.
        self.assertEqual(theirs.quantity, 80)
        self.assertEqual(theirs.average_cost, 4)
        # Total cost is invariant under a split, on both books.
        self.assertEqual(mine.cost_value, 120)
        self.assertEqual(theirs.cost_value, 320)

    def test_unsupported_corporate_action_stays_approved(self):
        evidence = self.env['ir.attachment'].create({'name': 'dividend.txt', 'raw': b'approved dividend', 'mimetype': 'text/plain'})
        action = self.env['capital.corporate.action'].create({'name': 'Cash dividend', 'instrument_id': self.instrument.id, 'action_type': 'dividend', 'effective_date': fields.Date.today(), 'cash_amount': 1, 'currency_id': self.env.ref('base.USD').id, 'evidence_attachment_id': evidence.id, 'state': 'approved'})
        with self.assertRaises(UserError):
            action.action_apply()
        self.assertEqual(action.state, 'approved')

    def test_benchmark_return_requires_fresh_mark(self):
        benchmark = self.env['capital.benchmark'].create({'name': 'Freshness benchmark', 'code': 'FRESH', 'currency_id': self.env.ref('base.USD').id, 'base_value': 100, 'base_as_of': fields.Datetime.now(), 'last_value': 110})
        portfolio = self.env['capital.portfolio'].create({'name': 'Benchmark portfolio', 'benchmark_id': benchmark.id, 'freshness_hours': 24})
        self.assertEqual(portfolio.benchmark_status, 'missing')
        benchmark.mark_as_of = fields.Datetime.now() - timedelta(hours=25)
        self.assertEqual(portfolio.benchmark_status, 'stale')
        self.assertEqual(portfolio.benchmark_return_pct, 0.0)
        benchmark.mark_as_of = fields.Datetime.now()
        self.assertEqual(portfolio.benchmark_status, 'fresh')
        self.assertEqual(portfolio.benchmark_return_pct, 10.0)

    def test_base_market_value_under_non_unity_fx(self):
        book = self.env['capital.portfolio'].create({'name': 'VND Book', 'currency_id': self.env.ref('base.VND').id})
        rate = self.env['capital.fx.rate'].create({
            'base_currency_id': self.env.ref('base.USD').id,
            'quote_currency_id': self.env.ref('base.VND').id,
            'rate': 25000,
            'as_of': fields.Datetime.now(),
        })
        position = self.env['capital.position'].create({'portfolio_id': book.id, 'instrument_id': self.instrument.id, 'quantity': 10, 'average_cost': 12, 'last_price': 15, 'fx_rate_id': rate.id})
        self.assertEqual(position.market_value, 150)
        self.assertEqual(position.base_market_value, 150 * 25000)
        unhedged = self.env['capital.instrument'].create({'symbol': 'GAMM', 'exchange': 'XNAS', 'currency_id': self.env.ref('base.USD').id})
        with self.assertRaises(ValidationError):
            self.env['capital.position'].create({'portfolio_id': book.id, 'instrument_id': unhedged.id, 'quantity': 1, 'average_cost': 12})

    def test_demo_references_resolve(self):
        module = 'insilos_capital_markets_decision_governance.'
        portfolio = self.env.ref(module + 'demo_portfolio_vn_equity', raise_if_not_found=False)
        if not portfolio:
            self.skipTest('Demo data is not loaded in this database.')
        for xmlid in (
            'demo_case_exit_cii', 'demo_case_limit_breach_hbc',
            'demo_synthetic_market_evidence', 'demo_synthetic_market_evidence_ree',
            'demo_synthetic_market_evidence_cii', 'demo_alert_cii_weight',
        ):
            self.assertTrue(self.env.ref(module + xmlid), xmlid)
        line = self.env.ref(module + 'demo_reconciliation_line_cii')
        self.assertEqual(line.quantity_difference, -100)

    def test_reconciliation_with_difference_stays_approved_without_mutating_position(self):
        position = self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'instrument_id': self.instrument.id, 'quantity': 10, 'average_cost': 12})
        attachment = self.env['ir.attachment'].create({'name': 'difference.csv', 'raw': b'symbol,quantity\nACME,11\n', 'mimetype': 'text/csv'})
        reconciliation = self.env['capital.reconciliation.import'].create({'portfolio_id': self.portfolio.id, 'broker': 'Manual broker', 'as_of': fields.Datetime.now(), 'currency_id': self.env.ref('base.USD').id, 'csv_attachment_id': attachment.id, 'state': 'approved'})
        self.env['capital.reconciliation.line'].create({'import_id': reconciliation.id, 'instrument_id': self.instrument.id, 'broker_quantity': 11, 'broker_cost': 120})
        with self.assertRaises(UserError):
            reconciliation.action_apply()
        self.assertEqual(reconciliation.state, 'approved')
        self.assertEqual((position.quantity, position.average_cost), (10, 12))
