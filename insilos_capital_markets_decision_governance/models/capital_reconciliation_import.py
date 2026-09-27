# Part of Insilos. See LICENSE file for full copyright and licensing details.

import base64
import hashlib

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CapitalReconciliationImport(models.Model):
    _name = 'capital.reconciliation.import'
    _description = 'Reconciliation Import'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'as_of desc, id desc'

    name = fields.Char(required=True, default='New', copy=False)
    portfolio_id = fields.Many2one('capital.portfolio', required=True, ondelete='restrict')
    company_id = fields.Many2one(related='portfolio_id.company_id', store=True, index=True)
    broker = fields.Char(required=True)
    as_of = fields.Datetime(required=True)
    currency_id = fields.Many2one('res.currency', required=True)
    csv_attachment_id = fields.Many2one('ir.attachment', required=True, ondelete='restrict', copy=False)
    csv_sha256 = fields.Char(readonly=True, copy=False)
    maker_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, readonly=True)
    reviewer_id = fields.Many2one('res.users', readonly=True)
    approver_id = fields.Many2one('res.users', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('review', 'In Review'), ('approved', 'Approved'), ('applied', 'Applied'), ('reversed', 'Reversed')], default='draft', required=True, tracking=True)
    line_ids = fields.One2many('capital.reconciliation.line', 'import_id')
    reversal_reason = fields.Char(readonly=True)
    # A reversal that does not say what replaced it leaves an auditor with a
    # hole rather than a corrected record.
    superseded_by_id = fields.Many2one('capital.reconciliation.import', string='Superseded By', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('capital.reconciliation.import') or 'New'
        records = super().create(vals_list)
        records._compute_csv_sha256()
        return records

    def write(self, vals):
        if self.filtered(lambda record: record.state != 'draft') and {'csv_attachment_id', 'portfolio_id', 'broker', 'as_of', 'currency_id', 'line_ids'} & set(vals):
            raise UserError(_('Approved reconciliation evidence is immutable. Create a correction import instead.'))
        result = super().write(vals)
        if 'csv_attachment_id' in vals:
            self._compute_csv_sha256()
        return result

    def _compute_csv_sha256(self):
        for record in self:
            raw = record.csv_attachment_id.raw
            if not raw:
                raise UserError(_('The reconciliation attachment is empty.'))
            if isinstance(raw, str):
                raw = base64.b64decode(raw)
            record.csv_sha256 = hashlib.sha256(raw).hexdigest()

    def action_check_data_quality(self):
        """DATA-001..003: refuse bad rows loudly and park the suspect ones.

        Run before review so a maker fixes the file rather than a reviewer
        discovering the damage after approval.
        """
        self.ensure_one()
        quarantine = self.env['capital.data.quarantine']
        rejected = []
        parked = quarantine
        for line in self.line_ids:
            payload = {
                'symbol': line.instrument_id.symbol or line.note,
                'broker_quantity': line.broker_quantity,
                'broker_cost': line.broker_cost,
            }
            # DATA-001: a negative broker quantity in a long-only book is a
            # parsing or feed error, not a short. It fails the import outright.
            if line.broker_quantity < 0:
                rejected.append(_('%(symbol)s: negative quantity %(quantity)s', symbol=payload['symbol'] or _('unmapped'), quantity=line.broker_quantity))
                continue
            # DATA-002: an unmapped instrument is quarantined, not guessed at.
            if not line.instrument_id:
                parked |= quarantine.quarantine('unknown_instrument', _('Broker row has no mapped instrument.'), portfolio_id=self.portfolio_id.id, import_id=self.id, symbol=line.note, payload=payload)
                continue
            # DATA-003: no currency means no valuation. The row is kept, but it
            # is flagged rather than valued at an implied rate.
            if not line.instrument_id.currency_id:
                parked |= quarantine.quarantine('missing_currency', _('Instrument has no currency; the row cannot be valued.'), portfolio_id=self.portfolio_id.id, import_id=self.id, symbol=line.instrument_id.symbol, payload=payload)
        if rejected:
            raise UserError(_('Import refused on data quality:\n%s', '\n'.join(rejected)))
        if parked:
            self.message_post(body=_('Data quality warning: %s row(s) quarantined and excluded from valuation.', len(parked)), subtype_xmlid='mail.mt_note')
        return parked

    def action_submit(self):
        self.action_check_data_quality()
        if self.maker_id == self.env.user:
            raise UserError(_('The maker cannot review this reconciliation import.'))
        self.write({'state': 'review', 'reviewer_id': self.env.user.id})

    def action_approve(self):
        if not self.env.user.has_group('insilos_capital_markets_decision_governance.group_decision_approver'):
            raise UserError(_('Only a Decision Approver may approve a reconciliation import.'))
        if self.state != 'review' or not self.reviewer_id:
            raise UserError(_('A reconciliation import must complete independent review before approval.'))
        if self.maker_id == self.env.user:
            raise UserError(_('The maker cannot approve this reconciliation import.'))
        if self.reviewer_id == self.env.user:
            raise UserError(_('The reviewer cannot approve this reconciliation import.'))
        self.write({'state': 'approved', 'approver_id': self.env.user.id})

    def action_apply(self):
        if self.state != 'approved':
            raise UserError(_('Only an approved reconciliation import can be applied.'))
        if self.env['capital.data.quarantine'].sudo().search_count([('import_id', '=', self.id), ('state', '=', 'open')]):
            raise UserError(_('Quarantined rows are still open on this import. Resolve or discard them first.'))
        if any(
            abs(line.quantity_difference) >= 0.00005
            or not self.currency_id.is_zero(line.cost_difference)
            for line in self.line_ids
        ):
            raise UserError(_('Reconciliation differences remain. Resolve them before applying; positions are not changed.'))
        self.write({'state': 'applied'})

    def action_reverse(self):
        if not self.env.user.has_group('insilos_capital_markets_decision_governance.group_governance_admin'):
            raise UserError(_('Only a Governance Admin may reverse a reconciliation import.'))
        if self.state not in ('approved', 'applied'):
            raise UserError(_('Only an approved or applied reconciliation import can be reversed.'))
        if not self.reversal_reason:
            raise UserError(_('Provide a reversal reason before reversing a reconciliation import.'))
        if not self.superseded_by_id and 'no replacement' not in self.reversal_reason.lower():
            raise UserError(_('Link the correction import that supersedes this one, or state "no replacement" in the reversal reason.'))
        if self.superseded_by_id and (self.superseded_by_id == self or self.superseded_by_id.portfolio_id != self.portfolio_id):
            raise UserError(_('A reconciliation correction must be a different import for the same portfolio.'))
        self.write({'state': 'reversed'})

    def unlink(self):
        if self.filtered(lambda record: record.state != 'draft'):
            raise UserError(_('Only draft reconciliation imports can be deleted.'))
        return super().unlink()
