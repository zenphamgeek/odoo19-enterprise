# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CapitalReconciliationLine(models.Model):
    _name = 'capital.reconciliation.line'
    _description = 'Reconciliation Line'

    import_id = fields.Many2one('capital.reconciliation.import', required=True, ondelete='cascade')
    instrument_id = fields.Many2one('capital.instrument', ondelete='restrict')
    currency_id = fields.Many2one(related='import_id.currency_id')
    # The currency the broker stated for this row. Optional on purpose: a file
    # that omits it must be visible as "unknown", not silently read as the
    # import currency.
    broker_currency_id = fields.Many2one('res.currency', string='Broker Currency')
    broker_quantity = fields.Float(digits=(16, 4))
    internal_quantity = fields.Float(compute='_compute_internal', readonly=True)
    broker_cost = fields.Monetary(currency_field='currency_id')
    internal_cost = fields.Monetary(compute='_compute_internal', currency_field='currency_id')
    broker_cash = fields.Monetary(currency_field='currency_id')
    broker_price = fields.Monetary(currency_field='currency_id')
    quantity_difference = fields.Float(compute='_compute_difference', digits=(16, 4))
    cost_difference = fields.Monetary(compute='_compute_difference', currency_field='currency_id')
    valuation_blocked = fields.Boolean(compute='_compute_difference', help='The row states no currency, so no valuation is produced for it.')
    note = fields.Char()

    @api.depends('instrument_id', 'import_id.portfolio_id.position_ids.quantity', 'import_id.portfolio_id.position_ids.cost_value')
    def _compute_internal(self):
        for line in self:
            position = line.import_id.portfolio_id.position_ids.filtered(lambda item: item.instrument_id == line.instrument_id)[:1]
            line.internal_quantity = position.quantity
            line.internal_cost = position.cost_value

    @api.depends('broker_quantity', 'internal_quantity', 'broker_cost', 'internal_cost', 'broker_currency_id', 'instrument_id.currency_id')
    def _compute_difference(self):
        for line in self:
            line.valuation_blocked = not (line.broker_currency_id or line.instrument_id.currency_id)
            line.quantity_difference = line.broker_quantity - line.internal_quantity
            # DATA-003: a money difference computed from an unknown currency is
            # a number with no meaning, so none is produced.
            line.cost_difference = 0.0 if line.valuation_blocked else line.broker_cost - line.internal_cost
