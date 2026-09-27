# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CapitalInstrument(models.Model):
    _name = 'capital.instrument'
    _description = 'Equity Instrument'
    _order = 'symbol, exchange'

    _symbol_exchange_unique = models.Constraint('unique(symbol, exchange)', 'An instrument already exists for this symbol and exchange.')

    name = fields.Char(compute='_compute_name', store=True)
    symbol = fields.Char(required=True, index=True)
    exchange = fields.Char(required=True, string='Exchange MIC')
    isin = fields.Char()
    currency_id = fields.Many2one('res.currency', required=True)
    asset_class = fields.Selection([('equity', 'Equity')], default='equity', required=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.depends('symbol', 'exchange')
    def _compute_name(self):
        for instrument in self:
            instrument.name = ' / '.join(filter(None, [instrument.symbol, instrument.exchange]))

    @api.constrains('symbol')
    def _check_symbol(self):
        for instrument in self:
            if not instrument.symbol.isalnum() or not 3 <= len(instrument.symbol) <= 8:
                raise ValidationError(_('Symbol must contain 3 to 8 alphanumeric characters.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('symbol'):
                vals['symbol'] = vals['symbol'].strip().upper()
            if vals.get('exchange'):
                vals['exchange'] = vals['exchange'].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if {'symbol', 'exchange', 'currency_id', 'asset_class'} & set(vals) and self.env['capital.position'].search_count([('instrument_id', 'in', self.ids)]):
            raise UserError(_('An instrument referenced by a position cannot be changed. Archive it and create a replacement.'))
        return super().write(vals)
