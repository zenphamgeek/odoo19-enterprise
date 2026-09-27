# Part of Insilos. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.insilos_treasury_market_risk.services import exposure_engine
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'treasury_market_risk')
class TestBucketing(TransactionCase):
    def test_past_maturity_is_overdue_and_today_is_not(self):
        today = date(2026, 8, 7)
        self.assertEqual(exposure_engine.bucket_of(today - timedelta(days=1), today), 'overdue')
        self.assertEqual(exposure_engine.bucket_of(today, today), '0_7')

    def test_boundaries_land_in_exactly_one_bucket(self):
        today = date(2026, 8, 7)
        for days, expected in ((7, '0_7'), (8, '8_30'), (30, '8_30'), (31, '31_60'), (365, '181_365'), (366, 'over_1y'), (4000, 'over_1y')):
            self.assertEqual(exposure_engine.bucket_of(today + timedelta(days=days), today), expected, days)

    def test_missing_maturity_is_near_but_never_overdue(self):
        self.assertEqual(exposure_engine.bucket_of(None, date(2026, 8, 7)), '0_7')


@tagged('post_install', '-at_install', 'treasury_market_risk')
class TestNaturalHedge(TransactionCase):
    def test_opposite_flows_in_the_same_bucket_offset(self):
        rows = [
            {'currency_id': 1, 'currency_name': 'USD', 'bucket': '0_7', 'amount': 1000.0},
            {'currency_id': 1, 'currency_name': 'USD', 'bucket': '0_7', 'amount': -600.0},
        ]
        (result,) = exposure_engine.natural_hedge(rows)
        self.assertEqual(result['gross_long'], 1000.0)
        self.assertEqual(result['gross_short'], -600.0)
        self.assertEqual(result['natural_hedge'], 600.0)
        self.assertEqual(result['net_exposure'], 400.0)

    def test_different_buckets_do_not_offset(self):
        rows = [
            {'currency_id': 1, 'currency_name': 'USD', 'bucket': '0_7', 'amount': 1000.0},
            {'currency_id': 1, 'currency_name': 'USD', 'bucket': '91_180', 'amount': -1000.0},
        ]
        results = exposure_engine.natural_hedge(rows)
        self.assertEqual(len(results), 2)
        self.assertEqual([row['natural_hedge'] for row in results], [0.0, 0.0])


@tagged('post_install', '-at_install', 'treasury_market_risk')
class TestExposureFromLedger(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.as_of = date(2026, 8, 7)
        cls.foreign = cls.setup_other_currency('EUR')

    def _post_invoice(self, move_type, amount, maturity, currency):
        move = self.env['account.move'].with_company(self.env.company).create({
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
            'invoice_date': self.as_of,
            # A payment term would recompute date_maturity and quietly ignore
            # the due date this test is about.
            'invoice_payment_term_id': False,
            'invoice_date_due': maturity,
            'invoice_line_ids': [(0, 0, {'name': 'Line', 'quantity': 1, 'price_unit': amount, 'tax_ids': []})],
        })
        move.action_post()
        return move

    def _foreign_rows(self):
        rows = exposure_engine.net_open_position(self.env, self.env.company.ids, self.as_of)
        return [row for row in rows if row['currency_id'] == self.foreign.id]

    def test_open_receivable_shows_up_in_its_maturity_bucket(self):
        self._post_invoice('out_invoice', 1000, self.as_of + timedelta(days=20), self.foreign)
        rows = self._foreign_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['bucket'], '8_30')
        self.assertEqual(rows[0]['amount'], 1000.0)

    def test_payable_offsets_receivable_in_the_same_bucket(self):
        due = self.as_of + timedelta(days=20)
        self._post_invoice('out_invoice', 1000, due, self.foreign)
        self._post_invoice('in_invoice', 600, due, self.foreign)
        (row,) = exposure_engine.natural_hedge(self._foreign_rows())
        self.assertEqual(row['natural_hedge'], 600.0)
        self.assertEqual(row['net_exposure'], 400.0)

    def test_home_currency_is_not_an_fx_exposure(self):
        self._post_invoice('out_invoice', 500, self.as_of + timedelta(days=13), self.env.company.currency_id)
        rows = exposure_engine.net_open_position(self.env, self.env.company.ids, self.as_of)
        self.assertEqual([row for row in rows if row['currency_id'] == self.env.company.currency_id.id], [])

    def test_sensitivity_scales_the_converted_exposure(self):
        self._post_invoice('out_invoice', 1000, self.as_of + timedelta(days=20), self.foreign)
        rows = exposure_engine.natural_hedge(self._foreign_rows())
        (result,) = exposure_engine.sensitivity(self.env, rows, self.env.company, shocks=(10.0, -10.0), as_of=self.as_of)
        expected = self.foreign._convert(1000.0, self.env.company.currency_id, self.env.company, self.as_of, round=False)
        self.assertAlmostEqual(result['base_value'], expected, places=2)
        self.assertAlmostEqual(result['shocks'][10.0], expected * 0.10, places=2)
        self.assertAlmostEqual(result['shocks'][-10.0], -expected * 0.10, places=2)
