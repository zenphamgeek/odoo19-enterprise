# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CapitalAlertRule(models.Model):
    _name = 'capital.alert.rule'
    _description = 'Portfolio Alert Rule'
    _inherit = ['mail.thread']
    _order = 'portfolio_id, symbol, name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    portfolio_id = fields.Many2one(
        'capital.portfolio', string='Portfolio', required=True,
        ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(related='portfolio_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='portfolio_id.currency_id')
    # Empty means portfolio-wide. A drawdown rule cares about the book, a price
    # rule cares about one name.
    symbol = fields.Char(help='Leave empty to watch the whole portfolio.')

    kind = fields.Selection(
        [
            ('price_above', 'Price rises above'),
            ('price_below', 'Price falls below'),
            ('pnl_pct_below', 'Unrealised P&L falls below %'),
            ('position_weight_above', 'Position weight exceeds %'),
        ],
        required=True, default='price_below',
    )
    threshold = fields.Float(required=True)
    user_id = fields.Many2one(
        'res.users', string='Notify', required=True,
        default=lambda self: self.env.user,
    )

    # State, kept deliberately thin. An alert that already fired and has not
    # been acknowledged must not fire again every cron tick; that is how a
    # governance signal becomes noise people learn to ignore.
    last_triggered_on = fields.Datetime(readonly=True)
    last_triggered_value = fields.Float(readonly=True)
    triggered = fields.Boolean(readonly=True, help='Set while the condition holds. Cleared when it no longer does.')

    @api.constrains('kind', 'symbol')
    def _check_symbol_required(self):
        for rule in self:
            if rule.kind in ('price_above', 'price_below') and not rule.symbol:
                raise ValidationError(_('A price rule needs a symbol to watch.'))

    def _unusable_marks(self, position_by_symbol):
        """Positions this rule depends on whose mark cannot be trusted.

        A breach computed from a mark that is stale, missing or errored is a
        false signal, and a false signal is worse than silence.
        """
        self.ensure_one()
        if self.symbol:
            position = position_by_symbol.get(self.symbol.strip().upper())
            candidates = position if position else self.env['capital.position']
        else:
            candidates = self.portfolio_id.position_ids.filtered(lambda p: p.quantity)
        return candidates.filtered(lambda p: p.mark_status != 'fresh')

    def _evaluate(self, position_by_symbol):
        """Return the breaching value, or None when the rule does not trigger.

        `position_by_symbol` is passed in rather than read here so one cron pass
        marks the whole book once instead of re-reading prices per rule.
        """
        self.ensure_one()
        # Every kind is gated on mark usability, not only the price rules: a
        # weight or a P&L percentage derived from a bad mark is equally wrong.
        if self._unusable_marks(position_by_symbol):
            return None

        if self.kind == 'position_weight_above':
            total = self.portfolio_id.market_value
            if not total:
                return None
            position = position_by_symbol.get((self.symbol or '').strip().upper())
            if not position:
                return None
            weight = position.market_value / total * 100
            return weight if weight > self.threshold else None

        if self.kind == 'pnl_pct_below':
            if self.symbol:
                position = position_by_symbol.get(self.symbol.strip().upper())
                if not position or not position.cost_value:
                    return None
                value = position.unrealised_pnl_pct
            else:
                cost = self.portfolio_id.cost_value
                if not cost:
                    return None
                value = self.portfolio_id.unrealised_pnl / cost * 100
            return value if value < self.threshold else None

        position = position_by_symbol.get((self.symbol or '').strip().upper())
        if not position or not position.last_price:
            return None
        if self.kind == 'price_above':
            return position.last_price if position.last_price > self.threshold else None
        return position.last_price if position.last_price < self.threshold else None

    def _flag_unusable_marks(self, unusable):
        """Make a skipped scan visible instead of silently doing nothing."""
        self.ensure_one()
        summary = _('Alert scan skipped: unusable mark for %s', ', '.join(sorted(unusable.mapped('symbol'))))
        cutoff = fields.Datetime.now() - timedelta(days=1)
        already = self.env['mail.activity'].search_count([
            ('res_model', '=', 'capital.portfolio'),
            ('res_id', '=', self.portfolio_id.id),
            ('summary', '=', summary),
            ('create_date', '>=', cutoff),
        ])
        if already:
            return
        self.portfolio_id.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=summary,
            note=_('<p>Rule <b>%(name)s</b> could not be evaluated: %(detail)s.</p>', name=self.name, detail=', '.join('%s=%s' % (p.symbol, p.mark_status) for p in unusable)),
            user_id=(self.portfolio_id.manager_id or self.user_id).id,
        )

    def _fire(self, value):
        """Raise the alert as an activity on the portfolio and a chatter note.

        Activities and chatter are used instead of a bespoke alert log because
        they already carry assignment, deadline, acknowledgement and audit.
        """
        self.ensure_one()
        self.write({
            'triggered': True,
            'last_triggered_on': fields.Datetime.now(),
            'last_triggered_value': value,
        })
        body = _(
            '<p>Alert <b>%(name)s</b> triggered: %(kind)s %(threshold)s, observed %(value)s.</p>'
            '<p>This is a threshold breach, not a recommendation. Raise a decision case '
            'if action is warranted.</p>',
            name=self.name,
            kind=dict(self._fields['kind'].selection).get(self.kind),
            threshold=self.threshold,
            value=round(value, 4),
        )
        self.portfolio_id.message_post(body=body, subtype_xmlid='mail.mt_note')
        self.portfolio_id.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=_('Alert: %s', self.name),
            note=body,
            user_id=self.user_id.id,
        )

    @api.model
    def _cron_scan_alerts(self):
        """Evaluate every active rule against the current marks."""
        for portfolio in self.env['capital.portfolio'].search([]):
            # One portfolio failing must not silence every other book, so each
            # gets its own savepoint.
            try:
                with self.env.cr.savepoint():
                    portfolio._scan_alert_rules()
            except Exception:
                _logger.warning('Alert scan failed for portfolio %s', portfolio.id, exc_info=True)
