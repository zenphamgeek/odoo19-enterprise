# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

MODULE = 'insilos_treasury_market_risk'


class TreasuryICPackTask(models.Model):
    _inherit = 'project.task'

    treasury_decision_value = fields.Monetary(currency_field='treasury_decision_currency_id', tracking=True)
    treasury_decision_currency_id = fields.Many2one('res.currency', string='Decision Currency', tracking=True)
    treasury_recommendation = fields.Text(tracking=True)
    treasury_alternatives = fields.Text(tracking=True)
    treasury_scorecard_json = fields.Json(string='Scorecard JSON')
    treasury_independent_challenge = fields.Text(tracking=True)
    treasury_assumptions_unknowns = fields.Text(tracking=True)
    treasury_evidence_references = fields.Text(tracking=True)
    treasury_decision_snapshot = fields.Json(copy=False, readonly=True)
    treasury_decision_snapshot_at = fields.Datetime(copy=False, readonly=True)
    treasury_human_decision = fields.Text(tracking=True)
    treasury_override_reason = fields.Text(tracking=True)
    treasury_override_by_id = fields.Many2one('res.users', readonly=True, copy=False)
    treasury_override_at = fields.Datetime(readonly=True, copy=False)
    treasury_expected_benefit = fields.Monetary(currency_field='treasury_decision_currency_id', tracking=True)
    treasury_actual_benefit = fields.Monetary(currency_field='treasury_decision_currency_id', tracking=True)
    treasury_hedge_cost = fields.Monetary(currency_field='treasury_decision_currency_id', tracking=True)
    treasury_decision_variance = fields.Monetary(currency_field='treasury_decision_currency_id', compute='_compute_treasury_decision_variance', store=True)
    treasury_approval_request_ids = fields.One2many('approval.request', 'treasury_task_id', string='Approval Requests')
    treasury_sign_request_count = fields.Integer(string='IC Pack Sign Requests', compute='_compute_treasury_sign_status')
    treasury_signer_count = fields.Integer(string='Completed IC Pack Signatures', compute='_compute_treasury_sign_status')
    treasury_sign_status = fields.Selection([
        ('none', 'Not Requested'),
        ('pending', 'Pending Signatures'),
        ('signed', 'Treasury Manager + CFO Signed'),
        ('invalid', 'Invalid, Cancelled or Expired'),
    ], string='IC Pack Signature Status', compute='_compute_treasury_sign_status')

    @api.depends('treasury_expected_benefit', 'treasury_actual_benefit', 'treasury_hedge_cost')
    def _compute_treasury_decision_variance(self):
        for task in self:
            task.treasury_decision_variance = task.treasury_actual_benefit - task.treasury_hedge_cost - task.treasury_expected_benefit

    def write(self, vals):
        protected = {'treasury_decision_snapshot', 'treasury_decision_snapshot_at', 'treasury_override_by_id', 'treasury_override_at'}
        if protected.intersection(vals) and not self.env.context.get('treasury_governance_write'):
            raise UserError(_('Treasury decision evidence is written only through its governance action.'))
        return super().write(vals)

    def action_snapshot_treasury_decision(self):
        """Freeze the decision inputs before committee approval (GOV-003)."""
        for task in self:
            if task.treasury_decision_snapshot:
                raise UserError(_('Treasury decision snapshot is immutable.'))
            task.with_context(treasury_governance_write=True).write({
                'treasury_decision_snapshot': task._treasury_ic_pack_data(),
                'treasury_decision_snapshot_at': fields.Datetime.now(),
            })
        return True

    def action_record_treasury_override(self, decision, reason):
        """GOV-004: human choice is allowed, but its accountable rationale is not optional."""
        self.ensure_one()
        if not self.treasury_decision_snapshot:
            raise UserError(_('Freeze the decision snapshot before recording an override.'))
        if not (decision or '').strip() or len((reason or '').strip()) < 40:
            raise UserError(_('A human override needs a decision and a rationale of at least 40 characters.'))
        self.with_context(treasury_governance_write=True).write({
            'treasury_human_decision': decision.strip(), 'treasury_override_reason': reason.strip(),
            'treasury_override_by_id': self.env.user.id, 'treasury_override_at': fields.Datetime.now(),
        })
        return True

    def _treasury_sign_requests(self):
        self.ensure_one()
        return self.env['sign.request'].sudo().search([('reference_doc', '=', f'project.task,{self.id}')])

    def _is_valid_treasury_dual_signature(self, sign_request):
        required_groups = (
            f'{MODULE}.group_treasury_manager',
            f'{MODULE}.group_cfo',
        )
        items = sign_request.request_item_ids
        if sign_request.state != 'signed' or len(items) != len(required_groups) or len(items.partner_id) != len(required_groups) or any(item.state != 'completed' for item in items):
            return False
        manager_items = items.filtered(
            lambda item: item.partner_id.user_ids.filtered(
                lambda user: user.has_group(f'{MODULE}.group_treasury_manager')
            )
        )
        cfo_items = items.filtered(
            lambda item: item.partner_id.user_ids.filtered(
                lambda user: user.has_group(f'{MODULE}.group_cfo')
            )
        )
        return any(
            manager_item.partner_id != cfo_item.partner_id
            for manager_item in manager_items
            for cfo_item in cfo_items
        )

    def _compute_treasury_sign_status(self):
        for task in self:
            requests = task._treasury_sign_requests()
            task.treasury_sign_request_count = len(requests)
            task.treasury_signer_count = len(requests.request_item_ids.filtered(lambda item: item.state == 'completed'))
            if any(task._is_valid_treasury_dual_signature(request) for request in requests):
                task.treasury_sign_status = 'signed'
            elif not requests:
                task.treasury_sign_status = 'none'
            elif requests.filtered(lambda request: request.state in ('canceled', 'expired')):
                task.treasury_sign_status = 'invalid'
            else:
                task.treasury_sign_status = 'pending'

    def _has_valid_treasury_dual_signature(self):
        self.ensure_one()
        return any(self._is_valid_treasury_dual_signature(request) for request in self._treasury_sign_requests())

    def action_generate_treasury_ic_pack(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate IC Pack',
            'res_model': 'treasury.generate.ic.pack.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    def action_send_treasury_ic_pack_for_signature(self):
        self.ensure_one()
        if not self.env.user.has_group(f'{MODULE}.group_treasury_manager'):
            raise UserError(_('Only a Treasury Manager may initiate an IC Pack signature request.'))
        if not self.attachment_ids.filtered(lambda attachment: attachment.name.startswith('IC Pack - ') and attachment.mimetype == 'application/pdf'):
            raise UserError(_('Generate an IC Pack snapshot before requesting signatures.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send IC Pack for Signature'),
            'res_model': 'sign.send.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reference_doc': f'project.task,{self.id}'},
        }

    def _treasury_ic_pack_data(self):
        self.ensure_one()
        return {
            'task_id': self.id,
            'task_name': self.name,
            'decision_value': self.treasury_decision_value,
            'currency': self.treasury_decision_currency_id.name or False,
            'recommendation': self.treasury_recommendation,
            'alternatives': self.treasury_alternatives,
            'scorecard': self.treasury_scorecard_json,
            'independent_challenge': self.treasury_independent_challenge,
            'assumptions_unknowns': self.treasury_assumptions_unknowns,
            'evidence_references': self.treasury_evidence_references,
            'approval_request_ids': self.treasury_approval_request_ids.ids,
        }


class TreasuryICPackApproval(models.Model):
    _inherit = 'approval.request'

    treasury_task_id = fields.Many2one('project.task', string='Treasury Decision Case', ondelete='set null', index=True)
