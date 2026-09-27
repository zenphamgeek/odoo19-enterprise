# Part of Insilos. See LICENSE file for full copyright and licensing details.
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..services import provider


FIXTURE = Path(__file__).parent / 'fixtures' / 'mr_20260720.json'
FIXTURE_SHA256 = '4bbec7b4fb22f2e624551ba281e96779721531f7282444dcf0149a21c8a0350a'


@tagged('post_install', '-at_install', 'market_data')
class TestInstrumentMapping(TransactionCase):

    def _instrument(self, **overrides):
        values = {
            'name': 'FPT Corp Shares',
            'is_financial_instrument': True,
            'instrument_type': 'equity',
            'instrument_currency_id': self.env.ref('base.VND').id,
            'market_provider_symbol': 'FPT',
        }
        values.update(overrides)
        return self.env['product.template'].create(values)

    def test_mr_20260720_is_immutable_historical_ohlc_fixture(self):
        raw = FIXTURE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), FIXTURE_SHA256)
        fixture = json.loads(raw)
        self.assertEqual(fixture['fixture_id'], 'MR-20260720')
        self.assertEqual(fixture['classification'], 'REAL-MKT')
        self.assertEqual(fixture['instruments']['HPG']['bars'][-1], {
            'date': '2026-07-20', 'open': 21400, 'high': 21450, 'low': 20500,
            'close': 20600, 'volume': 53245200,
        })
        self.assertEqual(fixture['instruments']['FPT']['bars'][-1]['volume'], 7346800)

    def test_instrument_requires_type_and_currency(self):
        with self.assertRaises(ValidationError):
            self._instrument(instrument_type=False)
        with self.assertRaises(ValidationError):
            self._instrument(instrument_currency_id=False)

    def test_provider_symbol_resolves_case_insensitively(self):
        instrument = self._instrument()
        self.assertEqual(self.env['product.template'].resolve_provider_symbol(' fpt '), instrument)

    def test_unmapped_symbol_returns_empty_not_wrong(self):
        self._instrument()
        self.assertFalse(self.env['product.template'].resolve_provider_symbol('HPG'))
        self.assertFalse(self.env['product.template'].resolve_provider_symbol(''))

    def test_provider_symbol_unique(self):
        self._instrument()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._instrument(name='Duplicate FPT')

    def test_null_symbols_do_not_collide(self):
        self._instrument(market_provider_symbol=False)
        self._instrument(name='Another unmapped', market_provider_symbol=False)

    def test_provider_selection_is_configuration(self):
        self.assertEqual(provider.get_provider(self.env).name, 'sidecar')
        self.env['ir.config_parameter'].sudo().set_param('market_data.provider', 'bloomberg')
        with self.assertRaises(ValueError):
            provider.get_provider(self.env)

    def test_lineage_carries_provider_symbol_and_as_of(self):
        lineage = provider._lineage('sidecar', 'FPT', {'asOf': '2026-07-20', 'requestFingerprint': 'abc'})
        self.assertEqual(lineage, {'provider': 'sidecar', 'symbol': 'FPT',
                                   'source_as_of': '2026-07-20', 'fingerprint': 'abc'})

    def test_stream_state_preserves_stale_and_lineage(self):
        state = {
            'symbol': 'FPT', 'stale': True, 'sequenceGap': True,
            'lastSourceTs': '2026-07-20T09:00:00Z', 'lastIngestTs': '2026-07-20T09:00:31Z',
            'ticks': [{'tradeId': 'X'}],
        }
        market_data = self.env['capital.market.data']
        with patch.object(type(market_data), 'stream_state', return_value=state):
            result = provider.SidecarProvider().stream(self.env, 'FPT')
        self.assertTrue(result['stale'])
        self.assertTrue(result['sequence_gap'])
        self.assertEqual(result['source_ts'], '2026-07-20T09:00:00Z')
        self.assertEqual(result['lineage']['symbol'], 'FPT')
        self.assertEqual(result['ticks'], [{'tradeId': 'X'}])

    def test_sidecar_contracts_use_registered_tool_schemas(self):
        market_data = self.env['capital.market.data']
        bars_envelope = {'data': [{'date': '2026-07-20', 'close': 67_100}], 'asOf': '2026-07-20', 'requestFingerprint': 'bars'}
        quote_envelope = {'data': [{'code': 'FPT', 'close': 67_100}], 'asOf': '2026-07-20', 'requestFingerprint': 'quote'}
        with patch.object(type(market_data), 'call_tool', side_effect=[bars_envelope, quote_envelope]) as call_tool, \
             patch.object(type(market_data), '_extract_price', return_value=(67_100, '2026-07-20')):
            data_provider = provider.SidecarProvider()
            bars = data_provider.bars(self.env, 'FPT', '2026-07-01', '2026-07-20')
            quote = data_provider.quote(self.env, 'FPT')
        self.assertEqual(bars['bars'][0]['close'], 67_100)
        self.assertEqual(bars['lineage']['fingerprint'], 'bars')
        self.assertEqual(quote['price'], 67_100)
        self.assertEqual(quote['lineage']['fingerprint'], 'quote')
        self.assertEqual(call_tool.call_args_list[0].args, ('price_history', {
            'symbol': 'FPT', 'startDate': '2026-07-01', 'endDate': '2026-07-20',
        }))
        self.assertEqual(call_tool.call_args_list[1].args, ('market_quote', {'codes': 'FPT'}))
