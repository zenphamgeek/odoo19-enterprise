# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Instrument identity lives on the product master (SRS 14.2, INV-001).

No instrument model: a financial instrument *is* a product with a few extra
fields, so accounting, analytics and market data all share one identity.
"""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_financial_instrument = fields.Boolean(string='Financial Instrument')
    instrument_type = fields.Selection([
        ('equity', 'Equity'),
        ('government_bond', 'Government Bond'),
        ('corporate_bond', 'Corporate Bond'),
        ('fund', 'Fund'),
        ('derivative', 'Derivative'),
        ('deposit', 'Deposit'),
        ('other', 'Other'),
    ], string='Instrument Type')
    instrument_currency_id = fields.Many2one('res.currency', string='Instrument Currency')
    issuer_partner_id = fields.Many2one('res.partner', string='Issuer')
    isin = fields.Char(string='ISIN')
    ticker = fields.Char(string='Ticker')
    maturity_date = fields.Date(string='Maturity Date')
    coupon_rate = fields.Float(string='Coupon Rate (%)')
    market_provider_symbol = fields.Char(
        string='Provider Symbol',
        help='Symbol under the configured market data provider (e.g. DNSE ticker).')

    # Postgres UNIQUE ignores NULLs, so unmapped instruments do not collide.
    _market_provider_symbol_uniq = models.Constraint(
        'unique(market_provider_symbol)',
        'A provider symbol may map to only one instrument.')

    @api.constrains('is_financial_instrument', 'instrument_type', 'instrument_currency_id')
    def _check_instrument_identity(self):
        for template in self:
            if template.is_financial_instrument and not (template.instrument_type and template.instrument_currency_id):
                raise ValidationError(
                    'A financial instrument needs an instrument type and currency; '
                    'an untyped or currency-less instrument cannot be valued.')

    @api.model
    def resolve_provider_symbol(self, symbol):
        """DATA-003: a subscribed symbol resolves to one instrument or is
        explicitly unmapped — never silently attached to the wrong product."""
        if not symbol:
            return self.browse()
        return self.search([
            ('is_financial_instrument', '=', True),
            ('market_provider_symbol', '=ilike', symbol.strip()),
        ], limit=1)
