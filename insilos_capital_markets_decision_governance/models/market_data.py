# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Client for the loopback market-data sidecar.

The sidecar owns the egress allowlist. This side deliberately holds no provider
host, no credential and no endpoint path: it can only name a tool the sidecar
already decided to expose. That is what keeps "which broker endpoints are
reachable" a single question with a single answer.
"""

import json
import logging
import os
import socket
from datetime import datetime
from urllib.parse import urlsplit

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

# The sidecar is a loopback service, not a user-facing URL. Both parameters are
# absent by default so an unconfigured database reaches nothing at all.
PARAM_BASE_URL = 'capital_markets.sidecar_base_url'
ENV_TOKEN = 'CAPITAL_MARKETS_SIDECAR_TOKEN'
PARAM_MARKET_DATA_ENABLED = 'capital_markets.market_data_enabled'
TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 2_000_000


class CapitalMarketData(models.AbstractModel):
    _name = 'capital.market.data'
    _description = 'Capital Markets Data Sidecar Client'

    @api.model
    def _market_data_enabled(self):
        return (self.env['ir.config_parameter'].sudo().get_param(PARAM_MARKET_DATA_ENABLED) or '').strip().lower() == 'true'

    @api.model
    def _sidecar_config(self):
        base_url = (self.env['ir.config_parameter'].sudo().get_param(PARAM_BASE_URL) or '').strip().rstrip('/')
        token = os.environ.get(ENV_TOKEN, '').strip()
        if not base_url or not token:
            raise UserError(_('Market data sidecar is not configured or its runtime secret is missing.'))
        # Loopback only. A sidecar reachable over the network is a different
        # trust boundary than the one this design assumes.
        if not base_url.startswith(('http://127.0.0.1', 'http://localhost')):
            raise UserError(_('Sidecar base URL must be loopback, got %s', base_url))
        return base_url, token

    @api.model
    def action_health_status(self):
        if not self.env.is_superuser() and not self.env.user.has_group('insilos_capital_markets_decision_governance.group_governance_admin'):
            raise AccessError(_('Only Governance Administrators may view market data health.'))
        base_url = (self.env['ir.config_parameter'].sudo().get_param(PARAM_BASE_URL) or '').strip().rstrip('/')
        runtime_secret_present = bool(os.environ.get(ENV_TOKEN, '').strip())
        configured = bool(base_url and runtime_secret_present)
        reachable = False
        if configured:
            parsed = urlsplit(base_url)
            if parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost'):
                try:
                    with socket.create_connection((parsed.hostname, parsed.port or 80), timeout=1):
                        reachable = True
                except OSError:
                    pass
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Market Data Health'),
                'message': _('Configured: %(configured)s\nRuntime secret: %(secret)s\nEnabled: %(enabled)s\nSidecar reachable: %(reachable)s') % {
                    'configured': _('Yes') if configured else _('No'),
                    'secret': _('Present') if runtime_secret_present else _('Missing'),
                    'enabled': _('Yes') if self._market_data_enabled() else _('No'),
                    'reachable': _('Yes') if reachable else _('No'),
                },
                'sticky': True,
                'type': 'info',
            },
        }

    @api.model
    def call_tool(self, tool_name, payload=None):
        """Invoke one sidecar tool and return its evidence envelope."""
        if not self._market_data_enabled():
            raise UserError(_('Market data is disabled. Set %s to true to enable sidecar calls.', PARAM_MARKET_DATA_ENABLED))
        import requests  # noqa: PLC0415 - keep the import local to the call path

        base_url, token = self._sidecar_config()
        if not tool_name.replace('_', '').isalnum():
            raise UserError(_('Refusing to call a tool with a suspicious name: %s', tool_name))
        try:
            response = requests.post(
                f'{base_url}/tools/{tool_name}',
                json=payload or {},
                headers={'Authorization': f'Bearer {token}'},
                timeout=TIMEOUT_SECONDS,
                stream=True,
            )
        except Exception as exc:
            raise UserError(_('Market data sidecar is unreachable: %s', exc)) from exc

        try:
            if response.status_code == 403:
                raise UserError(_('The sidecar refused this request on policy grounds.'))
            if response.status_code != 200:
                raise UserError(_('Sidecar returned HTTP %s.', response.status_code))
            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise UserError(_('Sidecar response exceeded the size ceiling; refusing to parse it.'))
                chunks.append(chunk)
            try:
                return json.loads(b''.join(chunks))
            except json.JSONDecodeError as exc:
                raise UserError(_('Sidecar returned a non-JSON response.')) from exc
        finally:
            response.close()

    @api.model
    def stream_state(self, symbol):
        """Read the sidecar's normalized realtime state; never persists ticks."""
        if not self._market_data_enabled():
            raise UserError(_('Market data is disabled. Set %s to true to enable sidecar calls.', PARAM_MARKET_DATA_ENABLED))
        import requests  # noqa: PLC0415

        base_url, token = self._sidecar_config()
        normalized = (symbol or '').strip().upper()
        if not normalized.replace('_', '').isalnum():
            raise UserError(_('Refusing to query a suspicious symbol: %s', symbol))
        try:
            response = requests.get(
                f'{base_url}/stream', params={'symbol': normalized},
                headers={'Authorization': f'Bearer {token}'}, timeout=TIMEOUT_SECONDS, stream=True,
            )
        except Exception as exc:
            raise UserError(_('Market data sidecar is unreachable: %s', exc)) from exc
        try:
            if response.status_code != 200:
                raise UserError(_('Sidecar stream returned HTTP %s.', response.status_code))
            chunks, total = [], 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise UserError(_('Sidecar stream response exceeded the size ceiling; refusing to parse it.'))
                chunks.append(chunk)
            return json.loads(b''.join(chunks))
        except json.JSONDecodeError as exc:
            raise UserError(_('Sidecar stream returned a non-JSON response.')) from exc
        finally:
            response.close()

    @api.model
    def _extract_price(self, envelope, symbol):
        """Pull a last price and its as-of date out of an evidence envelope.

        Returns (price, as_of) or (None, None). A missing price is reported by
        the caller rather than defaulted to zero: a mark of zero is a wrong
        valuation, whereas a missing mark is a known gap.
        """
        rows = (envelope or {}).get('data') or []
        wanted = (symbol or '').strip().upper()
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get('symbol') or row.get('code') or '').strip().upper()
            if code and code != wanted:
                continue
            for key in ('matchPrice', 'close', 'lastPrice', 'price', 'c'):
                value = row.get(key)
                if isinstance(value, list) and value:
                    value = value[-1]
                if isinstance(value, (int, float)) and value > 0:
                    # The row's own timestamp beats the envelope's: it says when
                    # this candle was true, not when the batch was assembled.
                    as_of = row.get('time') or row.get('date') or (envelope or {}).get('asOf')
                    return float(value), self._parse_as_of(as_of)
        return None, None

    @api.model
    def _parse_as_of(self, raw):
        """Coerce a provider timestamp to a datetime, or None if it is unusable.

        A date we cannot parse is reported as absent rather than guessed; an
        invented as-of date is worse than a missing one.
        """
        if not raw or not isinstance(raw, str):
            return None
        text = raw.strip().replace('Z', '').replace('T', ' ')
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None
