# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""One RPC returns everything the terminal draws: bars + governed overlays."""

from odoo import api, fields, models

from odoo.addons.insilos_market_data.services import provider
from odoo.addons.insilos_market_data.services.provider import get_provider


class MarketTerminalData(models.AbstractModel):
    _name = 'market.terminal.data'
    _description = 'Market Terminal Data Access'

    @api.model
    def get_terminal_payload(self, symbol, date_from, date_to):
        template = self.env['product.template'].resolve_provider_symbol(symbol)
        bars = provider.get_provider(self.env).bars(self.env, symbol, date_from, date_to)
        positions = self._positions(template)
        return {
            'symbol': symbol,
            'instrument': {
                'id': template.id,
                'name': template.display_name,
                'type': template.instrument_type,
                'mapped': bool(template),
            } if template else {'mapped': False},
            'bars': bars['bars'],
            'lineage': bars['lineage'],
            'market_state': self._market_state(bars['bars']),
            'portfolio_cards': self._portfolio_cards(positions),
            'overlays': self._overlays(template, positions),
        }

    @api.model
    def get_stream_payload(self, symbol):
        """Realtime state remains in the sidecar; terminal only reads it."""
        return get_provider(self.env).stream(self.env, symbol)

    def _positions(self, template):
        if not template:
            return self.env['capital.position']
        symbol = template.ticker or template.market_provider_symbol
        return self.env['capital.position'].search([('instrument_id.symbol', '=ilike', symbol)]) if symbol else self.env['capital.position']

    @staticmethod
    def _market_state(bars):
        if not bars:
            return {'status': 'unavailable'}
        latest = bars[-1]
        close = latest.get('close')
        previous_close = bars[-2].get('close') if len(bars) > 1 else None
        change_pct = (close - previous_close) / previous_close * 100 if previous_close else None
        return {
            'status': 'available', 'as_of': latest.get('date') or latest.get('time'),
            'close': close, 'volume': latest.get('volume'), 'change_pct': change_pct,
        }

    @staticmethod
    def _portfolio_cards(positions):
        cards = []
        for portfolio in positions.mapped('portfolio_id'):
            scoped = positions.filtered(lambda position: position.portfolio_id == portfolio)
            cards.append({
                'portfolio_id': portfolio.id, 'name': portfolio.display_name,
                'quantity': sum(scoped.mapped('quantity')),
                'market_value': sum(scoped.mapped('base_market_value')),
                'unrealised_pnl': sum(scoped.mapped('base_market_value')) - sum(scoped.mapped('base_cost_value')),
                'stale_positions': len(scoped.filtered(lambda position: position.mark_status != 'fresh')),
            })
        return cards

    def _overlays(self, template, positions):
        """UI-005/006: ERP cost and price limits, plus decision drill-through."""
        if not template:
            return {'price_lines': [], 'markers': []}
        symbol = template.ticker or template.market_provider_symbol
        price_lines = [{
            'label': 'Avg cost — %s' % position.portfolio_id.display_name,
            'price': position.average_cost,
            'kind': 'average_cost',
            'res_model': 'capital.position',
            'res_id': position.id,
        } for position in positions if position.average_cost]
        rules = self.env['capital.alert.rule'].search([
            ('active', '=', True),
            ('symbol', '=ilike', symbol),
            ('kind', 'in', ('price_above', 'price_below')),
        ]) if symbol else self.env['capital.alert.rule']
        price_labels = {'price_above': 'Price rises above', 'price_below': 'Price falls below'}
        price_lines += [{
            'label': '%s — %s' % (rule.name, price_labels[rule.kind]),
            'price': rule.threshold,
            'kind': rule.kind,
            'res_model': 'capital.alert.rule',
            'res_id': rule.id,
        } for rule in rules]
        markers = [{
            'time': fields.Date.to_string(fields.Datetime.to_datetime(position.decision_case_id.create_date).date()),
            'position': 'belowBar', 'color': '#0B2E64', 'shape': 'arrowUp',
            'text': position.decision_case_id.display_name,
            'res_model': 'project.task', 'res_id': position.decision_case_id.id,
        } for position in positions if position.decision_case_id]
        return {'price_lines': price_lines, 'markers': markers}
