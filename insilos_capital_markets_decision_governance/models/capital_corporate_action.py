# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CapitalCorporateAction(models.Model):
    _name = 'capital.corporate.action'
    _description = 'Corporate Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'effective_date desc, id desc'

    name = fields.Char(required=True, default='New', copy=False)
    instrument_id = fields.Many2one('capital.instrument', required=True, ondelete='restrict')
    action_type = fields.Selection([('split', 'Split'), ('dividend', 'Dividend'), ('rights', 'Rights'), ('merger', 'Merger')], required=True)
    effective_date = fields.Date(required=True)
    ratio = fields.Float(digits=(16, 8))
    cash_amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    evidence_attachment_id = fields.Many2one('ir.attachment', required=True, ondelete='restrict')
    state = fields.Selection([('draft', 'Draft'), ('review', 'In Review'), ('approved', 'Approved'), ('applied', 'Applied'), ('reversed', 'Reversed')], default='draft', required=True, tracking=True)
    reviewer_id = fields.Many2one('res.users', readonly=True)
    approver_id = fields.Many2one('res.users', readonly=True)
    reversal_reason = fields.Char(readonly=True)
    # A reversal that does not say what replaced it leaves an auditor with a
    # hole rather than a corrected record.
    superseded_by_id = fields.Many2one('capital.corporate.action', string='Superseded By', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('capital.corporate.action') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        if self.create_uid == self.env.user:
            raise UserError(_('The maker cannot review this corporate action.'))
        self.write({'state': 'review', 'reviewer_id': self.env.user.id})

    def action_approve(self):
        if not self.env.user.has_group('insilos_capital_markets_decision_governance.group_decision_approver'):
            raise UserError(_('Only a Decision Approver may approve a corporate action.'))
        if self.state != 'review' or not self.reviewer_id:
            raise UserError(_('A corporate action must complete independent review before approval.'))
        if self.create_uid == self.env.user:
            raise UserError(_('The maker cannot approve this corporate action.'))
        if self.reviewer_id == self.env.user:
            raise UserError(_('The reviewer cannot approve this corporate action.'))
        self.write({'state': 'approved', 'approver_id': self.env.user.id})

    def action_apply(self):
        if self.state != 'approved':
            raise UserError(_('Only an approved corporate action can be applied.'))
        if self.action_type != 'split':
            raise UserError(_('Applying %s corporate actions is deferred and not implemented.', self.action_type))
        if self.ratio <= 0:
            raise UserError(_('A split ratio must be greater than zero.'))
        # A split is an issuer fact: it hits every holder of the instrument, not
        # only the books this user may read. Searching under the user's record
        # rules would mark the action `applied` while silently leaving the other
        # companies' positions on a pre-split cost basis.
        positions = self.env['capital.position'].sudo().search([('instrument_id', '=', self.instrument_id.id)])
        for position in positions:
            position.write({'quantity': position.quantity * self.ratio, 'average_cost': position.average_cost / self.ratio})
            position.message_post(body=_('Split %s applied: ratio %s; quantity and average cost adjusted.', self.name, self.ratio))
        self.write({'state': 'applied'})

    def action_reverse(self):
        if not self.env.user.has_group('insilos_capital_markets_decision_governance.group_governance_admin'):
            raise UserError(_('Only a Governance Admin may reverse a corporate action.'))
        if self.state not in ('approved', 'applied'):
            raise UserError(_('Only an approved or applied corporate action can be reversed.'))
        if not self.reversal_reason:
            raise UserError(_('Provide a reversal reason before reversing a corporate action.'))
        if not self.superseded_by_id and 'no replacement' not in self.reversal_reason.lower():
            raise UserError(_('Link the corporate action that supersedes this one, or state "no replacement" in the reversal reason.'))
        if self.superseded_by_id and (self.superseded_by_id == self or self.superseded_by_id.instrument_id != self.instrument_id):
            raise UserError(_('A corporate action correction must be a different action for the same instrument.'))
        self.write({'state': 'reversed'})

    def unlink(self):
        if self.filtered(lambda action: action.state != 'draft'):
            raise UserError(_('Only draft corporate actions can be deleted.'))
        return super().unlink()
