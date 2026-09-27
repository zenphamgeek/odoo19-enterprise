# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""DATA-001..005: rejected or suspect inbound rows are parked, never guessed.

A row that cannot be trusted must not silently become a position, and must not
silently disappear either. It lands here with the reason and the raw payload so
an operator can decide, and so an auditor can see what was refused.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CapitalDataQuarantine(models.Model):
    _name = 'capital.data.quarantine'
    _description = 'Quarantined Market Data Row'
    _inherit = ['mail.thread']
    _order = 'create_date desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    portfolio_id = fields.Many2one('capital.portfolio', ondelete='cascade', index=True)
    company_id = fields.Many2one(related='portfolio_id.company_id', store=True, index=True)
    import_id = fields.Many2one('capital.reconciliation.import', ondelete='cascade', index=True)
    symbol = fields.Char()
    reason = fields.Selection(
        [
            ('negative_quantity', 'Negative quantity'),
            ('unknown_instrument', 'Unknown instrument'),
            ('missing_currency', 'Missing currency'),
            ('stale_timestamp', 'Market timestamp beyond stale threshold'),
            ('unexplained_gap', 'Unexplained price gap'),
        ],
        required=True,
    )
    detail = fields.Char(required=True)
    payload = fields.Json(readonly=True)
    state = fields.Selection(
        [('open', 'Open'), ('resolved', 'Resolved'), ('discarded', 'Discarded')],
        default='open', required=True, tracking=True,
    )
    resolution_note = fields.Char(tracking=True)

    @api.depends('symbol', 'reason')
    def _compute_name(self):
        labels = dict(self._fields['reason'].selection)
        for record in self:
            record.name = '%s: %s' % (record.symbol or _('unmapped'), labels.get(record.reason, ''))

    @api.model
    def quarantine(self, reason, detail, **values):
        """Record one refused row. Returns the quarantine record."""
        return self.sudo().create(dict(values, reason=reason, detail=detail))

    def action_resolve(self):
        for record in self:
            if not record.resolution_note:
                raise UserError(_('Explain how the quarantined row was resolved before closing it.'))
        self.write({'state': 'resolved'})

    def action_discard(self):
        for record in self:
            if not record.resolution_note:
                raise UserError(_('Explain why the quarantined row is discarded before closing it.'))
        self.write({'state': 'discarded'})

    def unlink(self):
        if self.filtered(lambda record: record.state == 'open'):
            raise UserError(_('An open quarantine record cannot be deleted. Resolve or discard it.'))
        return super().unlink()
