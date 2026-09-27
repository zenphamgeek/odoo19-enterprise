# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Governance gates over the treasury decision workflow — no new tables.

The treasury case is a `project.task` in a project carrying the seeded stage
set. Gates live in `write()` because that is the only door into a stage.
"""

from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.mail import html2plaintext

MODULE = 'insilos_treasury_market_risk'
# Same bar as capital markets: a rationale someone outside the room can read.
MIN_RATIONALE_CHARS = 40
REVIEW_OFFSETS_DAYS = (30, 90)


class TreasuryGovernanceTask(models.Model):
    _inherit = 'project.task'

    def _is_treasury_case(self):
        required = self.env.ref(f'{MODULE}.stage_investment_committee')
        required |= self.env.ref(f'{MODULE}.stage_execution')
        return self.filtered(lambda task: required <= task.project_id.type_ids)

    def write(self, vals):
        if 'stage_id' in vals:
            target = self.env['project.task.type'].browse(vals['stage_id'])
            committee = self.env.ref(f'{MODULE}.stage_investment_committee')
            decision_proposal = self.env.ref(f'{MODULE}.stage_decision_proposal')
            risk_review = self.env.ref(f'{MODULE}.stage_risk_review')
            finance_review = self.env.ref(f'{MODULE}.stage_finance_review')
            execution = self.env.ref(f'{MODULE}.stage_execution')
            settlement = self.env.ref(f'{MODULE}.stage_settlement')
            outcome_review = self.env.ref(f'{MODULE}.stage_outcome_review')
            if target in (risk_review | finance_review | committee | execution | settlement | outcome_review):
                for task in self._is_treasury_case():
                    if task.create_uid == self.env.user:
                        raise UserError(_('You raised this treasury case, so you cannot move it into %s.', target.name))
                    if not self.env.user.has_group(f'{MODULE}.group_treasury_manager'):
                        raise UserError(_('Only a Treasury Manager may move a case into %s.', target.name))
                    if target == risk_review and task.stage_id != decision_proposal:
                        raise UserError(_('Treasury cases must pass Decision Proposal before Risk Review.'))
                    if target == finance_review and task.stage_id != risk_review:
                        raise UserError(_('Treasury cases must pass Risk Review before Finance Review.'))
                    if target == committee:
                        if task.stage_id != finance_review:
                            raise UserError(_('Treasury cases must pass Finance Review before the Investment Committee.'))
                        if not task.treasury_decision_snapshot:
                            raise UserError(_('Treasury cases need an immutable decision snapshot before the Investment Committee.'))
                        if not task.attachment_ids:
                            raise UserError(_('Treasury cases need evidence attached before the Investment Committee.'))
                        if len(html2plaintext(task.description or '').strip()) < MIN_RATIONALE_CHARS:
                            raise UserError(_('Treasury cases need a written rationale of at least %s characters before the Investment Committee.', MIN_RATIONALE_CHARS))
                    if target == execution and task.stage_id != committee:
                        raise UserError(_('Treasury cases must pass the Investment Committee before Execution.'))
                    if target == execution and not task._has_valid_treasury_dual_signature():
                        raise UserError(_('Treasury cases need a signed IC Pack with completed Treasury Manager and CFO signatures before Execution.'))
                    if target == settlement and task.stage_id != execution:
                        raise UserError(_('Treasury cases must pass Execution before Settlement.'))
                    if target == outcome_review and task.stage_id != settlement:
                        raise UserError(_('Treasury cases must pass Settlement before Outcome Review.'))
        result = super().write(vals)
        if 'stage_id' in vals:
            execution = self.env.ref(f'{MODULE}.stage_execution')
            for task in self._is_treasury_case().filtered(lambda t: t.stage_id == execution):
                task._schedule_treasury_outcome_reviews()
        return result

    def _schedule_treasury_outcome_reviews(self):
        self.ensure_one()
        todo = self.env.ref('mail.mail_activity_data_todo')
        existing = self.activity_ids.filtered(lambda a: a.activity_type_id == todo).mapped('summary')
        for days in REVIEW_OFFSETS_DAYS:
            summary = _('Post-decision review (%sD)', days)
            if summary in existing:
                continue
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fields.Date.context_today(self) + timedelta(days=days),
                summary=summary,
                user_id=(self.user_ids[:1] or self.create_uid).id,
            )
