# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""EXE-001..003: what a dealer is allowed to send, and how fills are counted.

An order is the point where a governed decision becomes money moving. Two
things must hold no matter what the network does: the same instruction never
becomes two orders, and nothing larger than what was approved ever leaves.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CapitalOrder(models.Model):
    _name = 'capital.order'
    _description = 'Capital Markets Order'
    _inherit = ['mail.thread']
    _order = 'create_date desc, id desc'

    # EXE-001: idempotency lives in the database, not in retry code. A retry
    # after a timeout finds the row already there and stops.
    _client_order_id_unique = models.Constraint(
        'unique(client_order_id)',
        'This client order id already exists. A retry must not create a second order.',
    )

    name = fields.Char(related='client_order_id', store=True)
    client_order_id = fields.Char(required=True, copy=False, index=True)
    portfolio_id = fields.Many2one('capital.portfolio', required=True, ondelete='restrict', index=True)
    company_id = fields.Many2one(related='portfolio_id.company_id', store=True, index=True)
    instrument_id = fields.Many2one('capital.instrument', required=True, ondelete='restrict')
    currency_id = fields.Many2one(related='instrument_id.currency_id')
    side = fields.Selection([('buy', 'Buy'), ('sell', 'Sell')], required=True)
    decision_case_id = fields.Many2one('project.task', string='Approving Decision Case', required=True, ondelete='restrict')
    approved_quantity = fields.Float(required=True, digits=(16, 4))
    quantity = fields.Float(string='Order Quantity', required=True, digits=(16, 4))
    fill_ids = fields.One2many('capital.order.fill', 'order_id')
    executed_quantity = fields.Float(compute='_compute_execution', store=True, digits=(16, 4))
    open_quantity = fields.Float(compute='_compute_execution', store=True, digits=(16, 4))
    average_execution_price = fields.Monetary(compute='_compute_execution', store=True, currency_field='currency_id')
    realised_pnl = fields.Monetary(compute='_compute_execution', store=True, currency_field='currency_id')
    state = fields.Selection(
        [('draft', 'Draft'), ('sent', 'Sent'), ('partial', 'Partially Filled'), ('filled', 'Filled'), ('cancelled', 'Cancelled')],
        default='draft', required=True, tracking=True,
    )

    @api.constrains('quantity', 'approved_quantity')
    def _check_quantity_within_approval(self):
        for order in self:
            if order.quantity <= 0:
                raise ValidationError(_('An order quantity must be positive.'))
            # EXE-003: the approval is the ceiling. Exceeding it needs a new
            # approval, not a larger ticket.
            if order.quantity > order.approved_quantity:
                raise ValidationError(_(
                    'Order quantity %(quantity)s exceeds the approved %(approved)s. A new approval is required.',
                    quantity=order.quantity, approved=order.approved_quantity,
                ))

    @api.depends('fill_ids.quantity', 'fill_ids.price', 'quantity', 'side')
    def _compute_execution(self):
        for order in self:
            fills = order.fill_ids
            executed = sum(fills.mapped('quantity'))
            order.executed_quantity = executed
            order.open_quantity = order.quantity - executed
            notional = sum(fill.quantity * fill.price for fill in fills)
            order.average_execution_price = notional / executed if executed else 0.0
            position = order.portfolio_id.position_ids.filtered(lambda row: row.instrument_id == order.instrument_id)[:1]
            # Only a sale realises P&L; a buy just moves cash into inventory.
            order.realised_pnl = (notional - executed * position.average_cost) if (order.side == 'sell' and position) else 0.0

    notional = fields.Monetary(compute='_compute_notional', currency_field='currency_id')
    requires_ic = fields.Boolean(compute='_compute_notional', string='Needs IC Approval')

    @api.depends('quantity', 'instrument_id', 'portfolio_id.ic_threshold', 'portfolio_id.position_ids.last_price')
    def _compute_notional(self):
        for order in self:
            position = order.portfolio_id.position_ids.filtered(lambda row: row.instrument_id == order.instrument_id)[:1]
            order.notional = order.quantity * (position.last_price or 0.0)
            # GOV-001: the size of the trade decides who must sign it, and the
            # size is read from the marked price rather than asserted.
            order.requires_ic = bool(order.portfolio_id.ic_threshold) and order.notional > order.portfolio_id.ic_threshold

    def _check_execution_is_authorised(self):
        approved_stages = self.env.ref('insilos_capital_markets_decision_governance.stage_approval')
        approved_stages |= self.env.ref('insilos_capital_markets_decision_governance.stage_closed')
        for order in self:
            case = order.decision_case_id
            if case.stage_id not in approved_stages:
                raise UserError(_('The decision case is at %(stage)s. Execution is blocked before approval.', stage=case.stage_id.name or _('no stage')))
            if order.requires_ic and not case.ic_approved:
                raise UserError(_(
                    'A notional of %(notional)s is above the Investment Committee threshold and needs IC approval before execution.',
                    notional=order.notional,
                ))

    @api.model
    def submit(self, values):
        """EXE-001: send once. A retry of the same instruction returns the same order."""
        existing = self.search([('client_order_id', '=', values['client_order_id'])], limit=1)
        if existing:
            existing.message_post(body=_('Duplicate submission ignored; the original order stands.'), subtype_xmlid='mail.mt_note')
            return existing
        return self.create(dict(values, state='sent'))

    def register_fill(self, quantity, price):
        """EXE-002: a fill is added, never used to overwrite the running total."""
        self.ensure_one()
        self._check_execution_is_authorised()
        if quantity <= 0:
            raise UserError(_('A fill quantity must be positive.'))
        if quantity > self.open_quantity:
            raise UserError(_('Fill of %(fill)s exceeds the open quantity %(open)s.', fill=quantity, open=self.open_quantity))
        fill = self.env['capital.order.fill'].create({'order_id': self.id, 'quantity': quantity, 'price': price})
        self.state = 'filled' if self.open_quantity <= 0 else 'partial'
        return fill


class CapitalOrderFill(models.Model):
    _name = 'capital.order.fill'
    _description = 'Order Fill'
    _order = 'id'

    order_id = fields.Many2one('capital.order', required=True, ondelete='cascade', index=True)
    currency_id = fields.Many2one(related='order_id.currency_id')
    quantity = fields.Float(required=True, digits=(16, 4))
    price = fields.Monetary(required=True, currency_field='currency_id')
    executed_at = fields.Datetime(default=fields.Datetime.now, required=True)
