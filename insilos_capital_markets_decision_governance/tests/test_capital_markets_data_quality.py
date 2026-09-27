# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""TEST SUITE K — DATA QUALITY (DATA-001..005)."""

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'capital_markets', 'data_quality')
class TestCapitalMarketsDataQuality(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.usd = cls.env.ref('base.USD')
        cls.portfolio = cls.env['capital.portfolio'].create({'name': 'Data Quality Book', 'currency_id': cls.usd.id})
        cls.instrument = cls.env['capital.instrument'].create({'symbol': 'DQAA', 'exchange': 'XNAS', 'currency_id': cls.usd.id})

    def _import(self, name):
        attachment = self.env['ir.attachment'].create({'name': name, 'raw': b'symbol,quantity\nDQAA,10\n', 'mimetype': 'text/csv'})
        return self.env['capital.reconciliation.import'].create({
            'portfolio_id': self.portfolio.id, 'broker': 'DQ broker', 'as_of': fields.Datetime.now(),
            'currency_id': self.usd.id, 'csv_attachment_id': attachment.id,
        })

    def test_data_001_negative_quantity_fails_the_import(self):
        record = self._import('negative.csv')
        self.env['capital.reconciliation.line'].create({'import_id': record.id, 'instrument_id': self.instrument.id, 'broker_quantity': -5, 'broker_cost': 100})
        with self.assertRaises(UserError):
            record.action_check_data_quality()
        self.assertEqual(record.state, 'draft')
        self.assertFalse(self.env['capital.data.quarantine'].search([('import_id', '=', record.id)]))

    def test_data_002_unknown_instrument_is_quarantined_not_guessed(self):
        record = self._import('unknown.csv')
        self.env['capital.reconciliation.line'].create({'import_id': record.id, 'broker_quantity': 10, 'broker_cost': 100, 'note': 'ZZZZ'})
        parked = record.action_check_data_quality()
        self.assertEqual(parked.reason, 'unknown_instrument')
        self.assertEqual(parked.symbol, 'ZZZZ')
        self.assertEqual(parked.state, 'open')
        # An open quarantine blocks application: nothing is posted on a guess.
        record.state = 'approved'
        with self.assertRaises(UserError):
            record.action_apply()

    def test_data_003_missing_currency_blocks_valuation_and_warns(self):
        record = self._import('nocurrency.csv')
        line = self.env['capital.reconciliation.line'].create({'import_id': record.id, 'broker_quantity': 10, 'broker_cost': 100, 'note': 'NOCUR'})
        self.assertTrue(line.valuation_blocked)
        self.assertEqual(line.cost_difference, 0.0)
        record.action_check_data_quality()
        self.assertTrue(self.env['capital.data.quarantine'].search([('import_id', '=', record.id)]))

        priced = self.env['capital.reconciliation.line'].create({'import_id': record.id, 'instrument_id': self.instrument.id, 'broker_quantity': 10, 'broker_cost': 100})
        self.assertFalse(priced.valuation_blocked)
        self.assertEqual(priced.cost_difference, 100)

    def test_data_004_mark_older_than_threshold_is_flagged_stale(self):
        position = self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'instrument_id': self.instrument.id, 'quantity': 10, 'average_cost': 12})
        stale_as_of = fields.Datetime.now() - timedelta(hours=self.portfolio.freshness_hours + 1)
        parked = self.portfolio._quarantine_suspect_mark(position, 15, stale_as_of, 0.0, 'none')
        self.assertEqual(parked.reason, 'stale_timestamp')
        position.with_context(capital_market_refresh=True).write({'last_price': 15, 'price_as_of': stale_as_of})
        self.assertEqual(position.mark_status, 'stale')
        self.assertTrue(position.is_price_stale)

    def test_data_005_gap_is_economic_unless_a_corporate_action_explains_it(self):
        position = self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'instrument_id': self.instrument.id, 'quantity': 10, 'average_cost': 12})
        position.with_context(capital_market_refresh=True).write({'last_price': 100, 'price_as_of': fields.Datetime.now()})
        as_of = fields.Datetime.now()

        gap, reason = position._classify_price_gap(95, as_of)
        self.assertEqual(reason, 'none')

        gap, reason = position._classify_price_gap(50, as_of)
        self.assertEqual(reason, 'economic')
        self.assertEqual(round(gap, 2), -50.0)
        self.assertEqual(self.portfolio._quarantine_suspect_mark(position, 50, as_of, gap, reason).reason, 'unexplained_gap')

        evidence = self.env['ir.attachment'].create({'name': 'split.txt', 'raw': b'issuer split notice', 'mimetype': 'text/plain'})
        self.env['capital.corporate.action'].create({
            'name': 'DQ split', 'instrument_id': self.instrument.id, 'action_type': 'split',
            'effective_date': fields.Date.today(), 'ratio': 2, 'evidence_attachment_id': evidence.id, 'state': 'approved',
        })
        gap, reason = position._classify_price_gap(50, as_of)
        self.assertEqual(reason, 'corporate_action')
        self.assertFalse(self.portfolio._quarantine_suspect_mark(position, 50, as_of, gap, reason).filtered(lambda row: row.reason == 'unexplained_gap'))

    def test_quarantine_closure_needs_a_written_reason(self):
        row = self.env['capital.data.quarantine'].quarantine('unknown_instrument', 'no mapping', portfolio_id=self.portfolio.id, symbol='ZZZZ')
        with self.assertRaises(UserError):
            row.action_resolve()
        with self.assertRaises(UserError):
            row.unlink()
        row.resolution_note = 'Instrument mapped to DQAA and file re-imported.'
        row.action_resolve()
        self.assertEqual(row.state, 'resolved')
        self.assertEqual(self.portfolio.open_quarantine_count, 0)
