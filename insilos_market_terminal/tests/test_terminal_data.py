# Part of Insilos. See LICENSE file for full copyright and licensing details.
import json
from pathlib import Path
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.insilos_market_data.services.provider import SidecarProvider

MR_20260720 = json.loads((Path(__file__).parents[2] / 'insilos_market_data' / 'tests' / 'fixtures' / 'mr_20260720.json').read_text())
BARS = {'bars': MR_20260720['instruments']['FPT']['bars'],
        'lineage': {'provider': 'sidecar', 'symbol': 'FPT', 'source_as_of': '2026-07-20', 'fingerprint': 'MR-20260720'}}


@tagged('post_install', '-at_install', 'market_terminal')
class TestTerminalData(TransactionCase):

    def _payload(self, symbol='FPT'):
        bars_data = MR_20260720['instruments'].get(symbol) or MR_20260720['instruments']['FPT']
        mock_bars = {'bars': bars_data['bars'],
                     'lineage': {'provider': 'sidecar', 'symbol': symbol, 'source_as_of': '2026-07-20', 'fingerprint': 'MR-20260720'}}
        with patch.object(SidecarProvider, 'bars', return_value=mock_bars):
            return self.env['market.terminal.data'].get_terminal_payload(symbol, '2025-07-20', '2026-07-20')

    def test_mkt_001_historical_replay_reaches_chart_unadjusted(self):
        """MKT-001: provider → terminal payload must not touch the raw bars.

        The frozen MR-20260720 reference is the whole point of the scenario: a
        silently adjusted historical price may not replace the raw one. So this
        compares the payload against the fixture itself rather than re-stating
        the numbers, and derives the -5.72% daily move from `previous_close`,
        which is the figure the golden replay table publishes.
        """
        hpg = MR_20260720['instruments']['HPG']
        bars = {'bars': hpg['bars'], 'lineage': {'provider': 'sidecar', 'symbol': 'HPG',
                                                 'source_as_of': '2026-07-20', 'fingerprint': 'MR-20260720'}}
        with patch.object(SidecarProvider, 'bars', return_value=bars):
            payload = self.env['market.terminal.data'].get_terminal_payload('HPG', '2025-07-20', '2026-07-20')

        self.assertEqual(payload['bars'], hpg['bars'])
        self.assertEqual(payload['lineage']['fingerprint'], 'MR-20260720')
        # Golden replay table: HPG closes 20,600 on volume 53,245,200, -5.72%
        # against the 21,850 previous close.
        state = payload['market_state']
        self.assertEqual(state['as_of'], '2026-07-20')
        self.assertEqual(state['close'], 20_600)
        self.assertEqual(state['volume'], 53_245_200)
        self.assertAlmostEqual(state['change_pct'], -5.72, places=2)
        # The candle closes near the session low, which is what makes the
        # scenario's drop visible; a smoothed or adjusted bar would not.
        self.assertLess(payload['bars'][-1]['close'] - payload['bars'][-1]['low'],
                        payload['bars'][-1]['high'] - payload['bars'][-1]['close'])

    def test_unmapped_symbol_flags_no_overlays(self):
        payload = self._payload('ZZZ')
        self.assertFalse(payload['instrument']['mapped'])
        self.assertEqual(payload['overlays'], {'price_lines': [], 'markers': []})
        self.assertEqual(payload['lineage']['provider'], 'sidecar')
        self.assertEqual(payload['market_state'], {
            'status': 'available', 'as_of': '2026-07-20', 'close': 67_100,
            'volume': 7_346_800, 'change_pct': (67_100 - 67_000) / 67_000 * 100,
        })
        self.assertEqual(payload['portfolio_cards'], [])

    def test_mapped_symbol_returns_erp_overlays_and_decision_marker(self):
        company = self.env.company
        self.env['product.template'].create({
            'name': 'TEST FPT Shares', 'is_financial_instrument': True, 'instrument_type': 'equity',
            'instrument_currency_id': self.env.ref('base.VND').id,
            'market_provider_symbol': 'TESTFPT', 'ticker': 'TESTFPT',
        })
        portfolio = self.env['capital.portfolio'].create({
            'name': 'Terminal PF', 'company_id': company.id, 'currency_id': company.currency_id.id})
        instrument = self.env['capital.instrument'].create({
            'symbol': 'TESTFPT', 'exchange': 'HOSE', 'currency_id': company.currency_id.id})
        case = self.env['project.task'].create({'name': 'TESTFPT investment decision'})
        position = self.env['capital.position'].create({
            'portfolio_id': portfolio.id, 'instrument_id': instrument.id,
            'quantity': 1_500_000, 'average_cost': 58_200, 'last_price': 67_100,
            'decision_case_id': case.id,
        })
        rule = self.env['capital.alert.rule'].create({
            'name': 'TESTFPT loss limit', 'portfolio_id': portfolio.id, 'symbol': 'TESTFPT',
            'kind': 'price_below', 'threshold': 55_000,
        })
        payload = self._payload('TESTFPT')
        self.assertTrue(payload['instrument']['mapped'])
        lines = payload['overlays']['price_lines']
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]['price'], 58_200)
        self.assertEqual(lines[0]['res_model'], 'capital.position')
        self.assertEqual(lines[1]['price'], 55_000)
        self.assertEqual(lines[1]['res_model'], 'capital.alert.rule')
        self.assertEqual(lines[1]['res_id'], rule.id)
        marker = payload['overlays']['markers'][0]
        self.assertEqual(marker['res_model'], 'project.task')
        self.assertEqual(marker['res_id'], case.id)
        self.assertEqual(marker['time'], str(case.create_date.date()))
        self.assertEqual(position.decision_case_id, case)
        card = payload['portfolio_cards'][0]
        self.assertEqual(card['portfolio_id'], portfolio.id)
        self.assertEqual(card['quantity'], 1_500_000)
        self.assertEqual(card['market_value'], position.base_market_value)
        self.assertEqual(card['stale_positions'], 1)
        self.assertEqual(payload['market_state']['close'], 67_100)

    def test_market_terminal_security_groups(self):
        """Verify that market terminal user and manager security groups are correctly defined."""
        group_user = self.env.ref('insilos_market_terminal.group_market_terminal_user', raise_if_not_found=False)
        group_mgr = self.env.ref('insilos_market_terminal.group_market_terminal_manager', raise_if_not_found=False)
        self.assertTrue(group_user, "Market terminal user group must exist")
        self.assertTrue(group_mgr, "Market terminal manager group must exist")
        self.assertIn(group_user, group_mgr.implied_ids, "Manager group should imply user group")
