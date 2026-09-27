# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CapitalFxRate(models.Model):
    _name = 'capital.fx.rate'
    _description = 'FX Rate'
    _order = 'as_of desc, id desc'

    _rate_unique = models.Constraint('unique(base_currency_id, quote_currency_id, as_of, source)', 'An FX rate already exists for this currency pair, timestamp and source.')

    base_currency_id = fields.Many2one('res.currency', required=True)
    quote_currency_id = fields.Many2one('res.currency', required=True)
    rate = fields.Float(required=True, digits=(16, 8), help='Quote currency per one base currency.')
    as_of = fields.Datetime(required=True)
    source = fields.Char(required=True, default='manual')
    evidence_attachment_id = fields.Many2one('ir.attachment', ondelete='restrict')
    active = fields.Boolean(default=True)

    _check_rate = models.Constraint('CHECK(rate > 0)', 'FX rate must be greater than zero.')
    _check_currency_pair = models.Constraint('CHECK(base_currency_id != quote_currency_id)', 'Base and quote currencies must differ.')
