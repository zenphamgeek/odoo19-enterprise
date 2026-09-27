# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.mail import html2plaintext

_logger = logging.getLogger(__name__)

# Short enough that a genuine rationale clears it, long enough that "ok" does not.
MIN_RATIONALE_CHARS = 40
# A daily move beyond this is worth explaining; below it, ordinary volatility.
GAP_TOLERANCE_PCT = 20.0


class CapitalPosition(models.Model):
    _name = 'capital.position'
    _description = 'Portfolio Position'
    _inherit = ['mail.thread']
    _order = 'symbol'

    _instrument_unique_per_portfolio = models.Constraint('unique(portfolio_id, instrument_id)', 'An instrument appears once per portfolio. Adjust the existing position instead.')

    portfolio_id = fields.Many2one('capital.portfolio', string='Portfolio', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='portfolio_id.company_id', store=True, index=True)
    instrument_id = fields.Many2one('capital.instrument', required=True, ondelete='restrict', index=True)
    currency_id = fields.Many2one(related='instrument_id.currency_id')
    symbol = fields.Char(related='instrument_id.symbol', store=True, readonly=True)
    quantity = fields.Float(tracking=True, digits=(16, 4))
    average_cost = fields.Monetary(currency_field='currency_id', tracking=True)
    last_price = fields.Monetary(currency_field='currency_id', readonly=True)
    price_as_of = fields.Datetime(string='Price As Of', readonly=True)
    price_refreshed_at = fields.Datetime(string='Retrieved At', readonly=True)
    price_source = fields.Char(readonly=True, help='Provider host and tool that produced the mark.')
    evidence_hash = fields.Char(readonly=True, copy=False)
    evidence_reference = fields.Char(readonly=True, copy=False)
    evidence_attachment_id = fields.Many2one('ir.attachment', readonly=True, copy=False, ondelete='restrict')
    evidence_document_id = fields.Many2one('documents.document', readonly=True, copy=False, ondelete='restrict')
    price_error_at = fields.Datetime(string='Last Mark Error', readonly=True, copy=False)
    # DATA-005: a large move and a split look identical in the price series, so
    # the cause is recorded at mark time while the corporate action calendar is
    # still the obvious reference.
    price_gap_pct = fields.Float(string='Last Price Gap %', readonly=True, copy=False)
    price_gap_reason = fields.Selection(
        [
            ('none', 'Within tolerance'),
            ('economic', 'Economic price move'),
            ('corporate_action', 'Corporate action adjustment'),
        ],
        string='Price Gap Cause', readonly=True, copy=False,
    )
    # A single boolean cannot tell "we never had a price" from "the provider
    # errored" from "the price is simply old", yet each demands a different
    # operator response, so the state is explicit.
    mark_status = fields.Selection(
        [
            ('fresh', 'Fresh'),
            ('stale', 'Stale'),
            ('missing', 'Missing'),
            ('error', 'Error'),
        ],
        compute='_compute_mark_status', store=True, default='missing',
    )
    is_price_stale = fields.Boolean(compute='_compute_mark_status', store=True, string='Price Stale')
    fx_rate_id = fields.Many2one('capital.fx.rate', ondelete='restrict')
    fx_rate_as_of = fields.Datetime(related='fx_rate_id.as_of', string='FX As Of')
    exchange = fields.Char(related='instrument_id.exchange')

    cost_value = fields.Monetary(compute='_compute_values', currency_field='currency_id', store=True)
    market_value = fields.Monetary(compute='_compute_values', currency_field='currency_id', store=True)
    base_cost_value = fields.Monetary(compute='_compute_values', currency_field='portfolio_currency_id', store=True)
    base_market_value = fields.Monetary(compute='_compute_values', currency_field='portfolio_currency_id', store=True)
    portfolio_currency_id = fields.Many2one(related='portfolio_id.currency_id', string='Portfolio Currency')
    unrealised_pnl = fields.Monetary(compute='_compute_values', currency_field='currency_id', store=True)
    unrealised_pnl_pct = fields.Float(compute='_compute_values', string='Unrealised %', store=True)

    decision_case_id = fields.Many2one('project.task', string='Approving Decision Case', help='The decision case that approved this position.')
    evidence_count = fields.Integer(compute='_compute_evidence_count')

    def _compute_evidence_count(self):
        counts = dict(self.env['ir.attachment']._read_group(
            [('res_model', '=', 'capital.position'), ('res_id', 'in', self.ids)],
            ['res_id'], ['__count'],
        ))
        for position in self:
            position.evidence_count = counts.get(position.id, 0)

    def action_open_evidence(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Market Evidence'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'capital.position'), ('res_id', '=', self.id)],
            'context': {'create': False},
        }

    def _needs_fx_rate(self):
        self.ensure_one()
        return bool(self.currency_id) and bool(self.portfolio_currency_id) and self.currency_id != self.portfolio_currency_id

    @api.depends('price_as_of', 'last_price', 'price_error_at', 'price_refreshed_at', 'fx_rate_id', 'currency_id', 'portfolio_currency_id', 'portfolio_id.freshness_hours')
    def _compute_mark_status(self):
        now = fields.Datetime.now()
        for position in self:
            if not position.last_price or not position.price_as_of:
                status = 'missing'
            elif position.price_error_at and (not position.price_refreshed_at or position.price_error_at > position.price_refreshed_at):
                status = 'error'
            elif position._needs_fx_rate() and not position.fx_rate_id:
                # A mark nobody can translate into the book currency is not a
                # usable mark, whatever its age.
                status = 'error'
            elif position.price_as_of < now - timedelta(hours=position.portfolio_id.freshness_hours or 24):
                status = 'stale'
            else:
                status = 'fresh'
            position.mark_status = status
            position.is_price_stale = status != 'fresh'

    @api.depends('quantity', 'average_cost', 'last_price', 'fx_rate_id.rate', 'currency_id', 'portfolio_currency_id')
    def _compute_values(self):
        for position in self:
            position.cost_value = position.quantity * position.average_cost
            position.market_value = position.quantity * position.last_price
            rate = position.fx_rate_id.rate if position._needs_fx_rate() else 1
            position.base_cost_value = position.cost_value * rate
            position.base_market_value = position.market_value * rate
            position.unrealised_pnl = position.market_value - position.cost_value
            position.unrealised_pnl_pct = position.unrealised_pnl / position.cost_value * 100 if position.cost_value else 0.0

    @api.constrains('quantity', 'average_cost')
    def _check_long_only_values(self):
        if any(position.quantity < 0 or position.average_cost < 0 for position in self):
            raise ValidationError(_('Equity positions are long-only and costs cannot be negative.'))

    @api.constrains('fx_rate_id', 'instrument_id', 'portfolio_id')
    def _check_fx_rate_present(self):
        # Without this, a missing rate silently multiplies the base value by
        # zero and quietly deflates portfolio NAV.
        for position in self:
            if position._needs_fx_rate() and not position.fx_rate_id:
                raise ValidationError(_('A position in %(instrument)s needs an FX rate to %(book)s before it can be valued.', instrument=position.currency_id.name, book=position.portfolio_currency_id.name))
            if position.fx_rate_id and position._needs_fx_rate():
                pair = {position.fx_rate_id.base_currency_id, position.fx_rate_id.quote_currency_id}
                if pair != {position.currency_id, position.portfolio_currency_id}:
                    raise ValidationError(_('The FX rate does not convert %(instrument)s into %(book)s.', instrument=position.currency_id.name, book=position.portfolio_currency_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('instrument_id') and vals.get('symbol'):
                portfolio = self.env['capital.portfolio'].browse(vals['portfolio_id'])
                symbol = vals.pop('symbol').strip().upper()
                instrument = self.env['capital.instrument'].search([('symbol', '=', symbol), ('exchange', '=', 'UNSPECIFIED'), ('currency_id', '=', portfolio.currency_id.id)], limit=1)
                vals['instrument_id'] = (instrument or self.env['capital.instrument'].create({'symbol': symbol, 'exchange': 'UNSPECIFIED', 'currency_id': portfolio.currency_id.id})).id
        return super().create(vals_list)

    def _classify_price_gap(self, new_price, as_of):
        """DATA-005: separate an economic move from a corporate action adjustment.

        Returns (gap_pct, reason). An approved or applied corporate action
        effective in the window explains the gap; nothing else does.
        """
        self.ensure_one()
        if not self.last_price or not new_price:
            return 0.0, 'none'
        gap = (new_price - self.last_price) / self.last_price * 100
        if abs(gap) < GAP_TOLERANCE_PCT:
            return gap, 'none'
        window_start = (self.price_as_of or as_of or fields.Datetime.now()).date()
        window_end = (as_of or fields.Datetime.now()).date()
        explained = self.env['capital.corporate.action'].search_count([
            ('instrument_id', '=', self.instrument_id.id),
            ('state', 'in', ('approved', 'applied')),
            ('effective_date', '>=', window_start),
            ('effective_date', '<=', window_end),
        ])
        return gap, 'corporate_action' if explained else 'economic'

    def write(self, vals):
        protected = {'last_price', 'price_as_of', 'price_refreshed_at', 'price_source', 'price_error_at', 'evidence_hash', 'evidence_reference', 'evidence_attachment_id', 'evidence_document_id', 'price_gap_pct', 'price_gap_reason'}
        if protected.intersection(vals) and not self.env.context.get('capital_market_refresh'):
            raise UserError(_('Market marks and their evidence are created only by a refresh.'))
        return super().write(vals)

    def unlink(self):
        if self.filtered('evidence_attachment_id'):
            raise UserError(_('A position linked to canonical market evidence cannot be deleted.'))
        return super().unlink()


class CapitalEvidenceAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _is_canonical_market_evidence(self):
        return self.filtered(lambda attachment: attachment.res_model == 'capital.position' and attachment.res_id)

    def write(self, vals):
        if self._is_canonical_market_evidence():
            raise UserError(_('Canonical market evidence is immutable. Refresh creates a new record.'))
        return super().write(vals)

    def unlink(self):
        if self._is_canonical_market_evidence():
            raise UserError(_('Canonical market evidence cannot be deleted.'))
        return super().unlink()


class CapitalEvidenceDocument(models.Model):
    _inherit = 'documents.document'

    def _is_canonical_market_evidence(self):
        return self.filtered(lambda document: document.attachment_id.res_model == 'capital.position' and document.attachment_id.res_id)

    def write(self, vals):
        if self._is_canonical_market_evidence():
            raise UserError(_('Canonical market evidence is immutable.'))
        return super().write(vals)

    def unlink(self):
        if self._is_canonical_market_evidence():
            raise UserError(_('Canonical market evidence cannot be deleted.'))
        return super().unlink()


class CapitalGovernanceTask(models.Model):
    _inherit = 'project.task'

    # GOV-001: the committee's decision is a fact about the case, recorded by
    # the committee itself, not inferred from the stage the case happens to be in.
    ic_approved = fields.Boolean(string='IC Approved', copy=False, tracking=True)
    ic_approved_by_id = fields.Many2one('res.users', readonly=True, copy=False)
    ic_approved_at = fields.Datetime(readonly=True, copy=False)

    def action_record_ic_approval(self):
        for task in self:
            if not task.user_ids.filtered(lambda user: user.has_group('insilos_capital_markets_decision_governance.group_decision_reviewer')):
                raise UserError(_('An Investment Committee approval needs the reviewing members on the case.'))
        if not self.env.user.has_group('insilos_capital_markets_decision_governance.group_decision_approver'):
            raise UserError(_('Only a Decision Approver may record an Investment Committee approval.'))
        self.write({'ic_approved': True, 'ic_approved_by_id': self.env.user.id, 'ic_approved_at': fields.Datetime.now()})

    def _is_capital_case(self):
        required_stages = self.env.ref('insilos_capital_markets_decision_governance.stage_intake')
        required_stages |= self.env.ref('insilos_capital_markets_decision_governance.stage_approval')
        return self.filtered(lambda task: required_stages <= task.project_id.type_ids)

    def _audit_refused_transition(self, task, target, reason):
        """Record a refusal that the imminent UserError would otherwise erase.

        UserError rolls the transaction back, so the audit trail is written on
        an independent cursor. This is a security log, not a business write.
        """
        evidence = self.env['capital.position'].search([('decision_case_id', '=', task.id)]).mapped('evidence_hash')
        body = _(
            '<p>Stage transition refused.</p><ul>'
            '<li>Actor: %(actor)s</li><li>From: %(source)s</li><li>To: %(target)s</li>'
            '<li>Reason: %(reason)s</li><li>Evidence: %(evidence)s</li></ul>',
            actor=self.env.user.login, source=task.stage_id.name or '', target=target.name or '',
            reason=reason, evidence=', '.join(h for h in evidence if h) or 'none',
        )
        try:
            with self.env.registry.cursor() as cr:
                env = self.env(cr=cr)
                env['project.task'].browse(task.id).message_post(body=body, subtype_xmlid='mail.mt_note')
        except Exception:
            _logger.warning('Could not audit refused transition on task %s', task.id, exc_info=True)

    def _refuse(self, task, target, reason):
        self._audit_refused_transition(task, target, reason)
        raise UserError(reason)

    def write(self, vals):
        if 'stage_id' in vals:
            target = self.env['project.task.type'].browse(vals['stage_id'])
            gate_stages = self.env.ref('insilos_capital_markets_decision_governance.stage_approval')
            gate_stages |= self.env.ref('insilos_capital_markets_decision_governance.stage_closed')
            if target in gate_stages:
                governed = self._is_capital_case()
                if governed and not self.env.user.has_group('insilos_capital_markets_decision_governance.group_decision_approver'):
                    self._refuse(governed[0], target, _('Only a Decision Approver may move a capital markets case into %s.', target.name))
                raised = governed.filtered(lambda task: task.create_uid == self.env.user)
                if raised:
                    self._refuse(raised[0], target, _('You raised this decision case, so you cannot move it into %s.', target.name))
                if target == self.env.ref('insilos_capital_markets_decision_governance.stage_approval'):
                    for task in governed:
                        if not task.attachment_ids:
                            self._refuse(task, target, _('Capital markets cases require evidence before Approval.'))
                        # A written rationale is the one artefact that explains
                        # a decision to someone who was not in the room.
                        if len(html2plaintext(task.description or '').strip()) < MIN_RATIONALE_CHARS:
                            self._refuse(task, target, _('Capital markets cases need a written rationale of at least %s characters before Approval.', MIN_RATIONALE_CHARS))
                        reviewers = task.user_ids.filtered(lambda user: user.has_group('insilos_capital_markets_decision_governance.group_decision_reviewer'))
                        if not reviewers or self.env.user in reviewers:
                            self._refuse(task, target, _('Approval requires an assigned Reviewer who is not the Approver.'))
                        # An assigned reviewer who has not finished reviewing is
                        # a name on a form, not a control.
                        if task.activity_ids.filtered(lambda activity: activity.user_id in reviewers):
                            self._refuse(task, target, _('Approval requires the assigned Reviewer to complete their review activity.'))
        return super().write(vals)
