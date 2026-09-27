# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""MarketDataProvider abstraction (DATA-010).

The risk engines consume `bars()` and `quote()` and never learn which vendor
answered. The only concrete provider today rides the loopback sidecar, which
owns the egress allowlist, credentials and rate limits — this layer adds
normalisation and lineage, nothing else.
"""


class MarketDataProvider:
    """Interface: a provider returns normalised rows with lineage."""

    name = 'abstract'

    def bars(self, env, symbol, date_from, date_to, resolution='1D'):
        raise NotImplementedError

    def quote(self, env, symbol):
        raise NotImplementedError

    def stream(self, env, symbol):
        raise NotImplementedError


def _lineage(provider, symbol, envelope):
    """DATA-007: every payload says where it came from and when."""
    return {
        'provider': provider,
        'symbol': symbol,
        'source_as_of': (envelope or {}).get('asOf'),
        'fingerprint': (envelope or {}).get('requestFingerprint'),
    }


class SidecarProvider(MarketDataProvider):
    """Provider #1: whatever tools the sidecar allowlists (DNSE et al.)."""

    name = 'sidecar'

    def bars(self, env, symbol, date_from, date_to, resolution='1D'):
        envelope = env['capital.market.data'].call_tool('price_history', {
            'symbol': symbol, 'startDate': str(date_from), 'endDate': str(date_to),
        })
        rows = (envelope or {}).get('data') or []
        return {'bars': rows, 'lineage': _lineage(self.name, symbol, envelope)}

    def quote(self, env, symbol):
        envelope = env['capital.market.data'].call_tool('market_quote', {'codes': symbol})
        price, as_of = env['capital.market.data']._extract_price(envelope, symbol)
        return {'price': price, 'as_of': as_of,
                'lineage': _lineage(self.name, symbol, envelope)}

    def stream(self, env, symbol):
        state = env['capital.market.data'].stream_state(symbol)
        return {
            'symbol': state['symbol'],
            'stale': state['stale'],
            'sequence_gap': state['sequenceGap'],
            'source_ts': state['lastSourceTs'],
            'ingest_ts': state['lastIngestTs'],
            'ticks': state['ticks'],
            'lineage': {'provider': self.name, 'symbol': state['symbol'],
                        'source_as_of': state['lastSourceTs'], 'fingerprint': None},
        }


_PROVIDERS = {'sidecar': SidecarProvider()}


def get_provider(env, company=None):
    """Provider selection is configuration, not code (DR-08)."""
    key = env['ir.config_parameter'].sudo().get_param('market_data.provider', 'sidecar')
    provider = _PROVIDERS.get(key)
    if provider is None:
        raise ValueError('Unknown market data provider: %s' % key)
    return provider
