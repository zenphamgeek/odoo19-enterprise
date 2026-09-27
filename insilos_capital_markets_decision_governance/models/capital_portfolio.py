# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import json
import logging
from datetime import timedelta

from markupsafe import escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# The sidecar envelope contract. Evidence without these cannot be audited.
EVIDENCE_REQUIRED_FIELDS = (
    'source', 'provider', 'endpointClass', 'instrument', 'asOf', 'retrievedAt',
    'requestFingerprint', 'cacheStatus', 'data', 'warnings', 'licenseClassification',
)
EVIDENCE_METADATA_FIELDS = tuple(field for field in EVIDENCE_REQUIRED_FIELDS if field != 'data')
MAX_EVIDENCE_BYTES = 2_000_000


class CapitalPortfolio(models.Model):
    _name = 'capital.portfolio'
    _description = 'Investment Portfolio'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    benchmark_id = fields.Many2one('capital.benchmark', ondelete='restrict')
    manager_id = fields.Many2one('res.users', string='Portfolio Manager', tracking=True, default=lambda self: self.env.user)
    broker_account_ref = fields.Char(string='Broker Account Reference', help='Broker-side account identifier this portfolio mirrors. Reference only; no balances, orders or positions are read from the broker.')
    freshness_hours = fields.Integer(default=24, required=True)
    position_ids = fields.One2many('capital.position', 'portfolio_id', string='Positions')
    alert_rule_ids = fields.One2many('capital.alert.rule', 'portfolio_id', string='Alert Rules')

    position_count = fields.Integer(compute='_compute_totals')
    market_value = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    cost_value = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    unrealised_pnl = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    nav = fields.Monetary(compute='_compute_totals', currency_field='currency_id', string='NAV')

    stale_position_count = fields.Integer(compute='_compute_health')
    open_alert_count = fields.Integer(compute='_compute_health')
    fx_freshness_hours = fields.Float(compute='_compute_health', string='Oldest FX Rate (h)')
    reconciliation_status = fields.Char(compute='_compute_health')
    # GOV-001: above this notional a trade is an Investment Committee matter,
    # not a desk matter. Zero means the book has no committee gate.
    ic_threshold = fields.Monetary(string='IC Approval Threshold', currency_field='currency_id')
    quarantine_ids = fields.One2many('capital.data.quarantine', 'portfolio_id', string='Quarantined Rows')
    open_quarantine_count = fields.Integer(compute='_compute_health')
    benchmark_return_pct = fields.Float(compute='_compute_benchmark_return', string='Benchmark Return %')
    benchmark_status = fields.Selection([('none', 'No Benchmark'), ('fresh', 'Fresh'), ('stale', 'Stale'), ('missing', 'Missing Mark')], compute='_compute_benchmark_return')

    @api.constrains('freshness_hours')
    def _check_freshness_hours(self):
        if any(portfolio.freshness_hours <= 0 for portfolio in self):
            raise UserError(_('Freshness must be greater than zero hours.'))

    @api.depends('position_ids.base_market_value', 'position_ids.base_cost_value')
    def _compute_totals(self):
        for portfolio in self:
            open_positions = portfolio.position_ids.filtered(lambda p: p.quantity)
            portfolio.position_count = len(open_positions)
            portfolio.market_value = sum(open_positions.mapped('base_market_value'))
            portfolio.cost_value = sum(open_positions.mapped('base_cost_value'))
            portfolio.unrealised_pnl = portfolio.market_value - portfolio.cost_value
            portfolio.nav = portfolio.market_value

    @api.depends('position_ids.mark_status', 'position_ids.fx_rate_id.as_of', 'alert_rule_ids.triggered', 'quarantine_ids.state')
    def _compute_health(self):
        now = fields.Datetime.now()
        for portfolio in self:
            open_positions = portfolio.position_ids.filtered(lambda p: p.quantity)
            portfolio.stale_position_count = len(open_positions.filtered(lambda p: p.mark_status != 'fresh'))
            portfolio.open_alert_count = len(portfolio.alert_rule_ids.filtered('triggered'))
            rate_dates = [rate.as_of for rate in open_positions.mapped('fx_rate_id') if rate.as_of]
            portfolio.fx_freshness_hours = max(((now - as_of).total_seconds() / 3600 for as_of in rate_dates), default=0.0)
            latest = self.env['capital.reconciliation.import'].search([('portfolio_id', '=', portfolio.id)], order='as_of desc, id desc', limit=1)
            portfolio.reconciliation_status = latest.state or 'none'
            portfolio.open_quarantine_count = len(portfolio.quarantine_ids.filtered(lambda row: row.state == 'open'))

    @api.depends('benchmark_id.last_value', 'benchmark_id.base_value', 'benchmark_id.mark_as_of', 'freshness_hours')
    def _compute_benchmark_return(self):
        now = fields.Datetime.now()
        for portfolio in self:
            benchmark = portfolio.benchmark_id
            if not benchmark:
                portfolio.benchmark_return_pct = 0.0
                portfolio.benchmark_status = 'none'
            elif not benchmark.mark_as_of or not benchmark.last_value:
                portfolio.benchmark_return_pct = 0.0
                portfolio.benchmark_status = 'missing'
            elif now - benchmark.mark_as_of > timedelta(hours=portfolio.freshness_hours):
                portfolio.benchmark_return_pct = 0.0
                portfolio.benchmark_status = 'stale'
            else:
                portfolio.benchmark_return_pct = (benchmark.last_value - benchmark.base_value) / benchmark.base_value * 100 if benchmark.base_value else 0.0
                portfolio.benchmark_status = 'fresh'

    def _validate_envelope(self, envelope, payload):
        """Reject anything that is not a complete, bounded provenance envelope.

        Evidence that cannot answer "where did this number come from" is worse
        than no evidence, because it looks authoritative.
        """
        if not isinstance(envelope, dict):
            raise UserError(_('The provider returned no provenance envelope.'))
        missing = [field for field in EVIDENCE_REQUIRED_FIELDS if field not in envelope]
        if missing:
            raise UserError(_('The provenance envelope is missing: %s.', ', '.join(missing)))
        if len(payload) > MAX_EVIDENCE_BYTES:
            raise UserError(_('The provenance envelope exceeds the %s byte ceiling.', MAX_EVIDENCE_BYTES))

    def capture_market_evidence(self, position, envelope, stamped_at, as_of=None):
        """Persist the provider envelope as immutable, addressable evidence."""
        payload = json.dumps(envelope, sort_keys=True, separators=(',', ':'), default=str).encode()
        self._validate_envelope(envelope, payload)
        digest = hashlib.sha256(payload).hexdigest()
        # Symbol, as-of and hash prefix in the filename so evidence is
        # identifiable and de-duplicable without opening it.
        stamp = (as_of or stamped_at).strftime('%Y%m%dT%H%M%SZ')
        attachment = self.env['ir.attachment'].with_context(no_document=True).create({
            'name': '%s-%s-%s.json' % (position.symbol, stamp, digest[:12]),
            'raw': payload,
            'mimetype': 'application/json',
            'res_model': 'capital.position',
            'res_id': position.id,
        })
        document = self.env['documents.document'].create({
            'name': attachment.name,
            'attachment_id': attachment.id,
            'folder_id': self.env.ref('insilos_capital_markets_decision_governance.folder_evidence_vendor').id,
            'company_id': position.portfolio_id.company_id.id,
            'access_internal': 'view',
        })
        self._post_evidence_metadata(position, envelope, attachment, digest)
        return attachment, document, digest

    def _post_evidence_metadata(self, position, envelope, attachment, digest):
        """Write provenance into chatter so it survives field-level refresh."""
        rows = ''.join(
            '<tr><td><b>%s</b></td><td>%s</td></tr>' % (escape(field), escape(str(envelope.get(field, ''))))
            for field in EVIDENCE_METADATA_FIELDS
        )
        body = _(
            '<p>Market evidence captured: <b>%(name)s</b></p><table class="table table-sm">%(rows)s'
            '<tr><td><b>sha256</b></td><td>%(digest)s</td></tr></table>',
            name=escape(attachment.name), rows=rows, digest=digest,
        )
        position.message_post(body=body, subtype_xmlid='mail.mt_note')
        # The decision case that authorised the position is the second place a
        # reviewer looks, so it gets a pointer, not a second copy of the bytes.
        if position.decision_case_id:
            position.decision_case_id.message_post(
                body=_('<p>Evidence <b>%(name)s</b> (sha256 %(digest)s) captured for position %(symbol)s.</p>', name=escape(attachment.name), digest=digest, symbol=escape(position.symbol or '')),
                attachment_ids=attachment.ids,
                subtype_xmlid='mail.mt_note',
            )

    def _quarantine_suspect_mark(self, position, price, as_of, gap_pct, gap_reason):
        """DATA-004/005: park a mark that is too old or moves without explanation.

        The mark is still applied - refusing it would leave the book with an
        older price - but it is on the record as needing a human look.
        """
        self.ensure_one()
        quarantine = self.env['capital.data.quarantine']
        payload = {'symbol': position.symbol, 'price': price, 'as_of': fields.Datetime.to_string(as_of), 'gap_pct': gap_pct}
        parked = quarantine
        if as_of and as_of < fields.Datetime.now() - timedelta(hours=self.freshness_hours or 24):
            parked |= quarantine.quarantine('stale_timestamp', _('Mark as-of %(as_of)s is older than the %(hours)sh threshold.', as_of=as_of, hours=self.freshness_hours), portfolio_id=self.id, symbol=position.symbol, payload=payload)
        if gap_reason == 'economic':
            parked |= quarantine.quarantine('unexplained_gap', _('Price moved %(gap).2f%% with no approved corporate action to explain it.', gap=gap_pct), portfolio_id=self.id, symbol=position.symbol, payload=payload)
        return parked

    def action_refresh_marks(self):
        self.ensure_one()
        marked = self.position_ids.filtered(lambda p: p.symbol and p.quantity)
        if not marked:
            raise UserError(_('This portfolio holds no position to mark.'))
        client = self.env['capital.market.data']
        stamped_at = fields.Datetime.now()
        today = fields.Date.context_today(self)
        window_start = today - timedelta(days=10)
        missed = []
        for position in marked:
            try:
                envelope = client.call_tool('dnse_ohlc', {'symbol': position.symbol, 'startDate': window_start.isoformat(), 'endDate': today.isoformat(), 'limit': 5})
                price, as_of = client._extract_price(envelope, position.symbol)
                if price is None:
                    missed.append(position.symbol)
                    position.with_context(capital_market_refresh=True).price_error_at = stamped_at
                    continue
                attachment, document, digest = self.capture_market_evidence(position, envelope, stamped_at, as_of)
                gap_pct, gap_reason = position._classify_price_gap(price, as_of or stamped_at)
                self._quarantine_suspect_mark(position, price, as_of or stamped_at, gap_pct, gap_reason)
                position.with_context(capital_market_refresh=True).write({
                    'price_gap_pct': gap_pct,
                    'price_gap_reason': gap_reason,
                    'last_price': price,
                    'price_as_of': as_of or stamped_at,
                    'price_refreshed_at': stamped_at,
                    'price_source': '%s (%s)' % (envelope.get('source') or 'sidecar', envelope.get('requestFingerprint') or ''),
                    'price_error_at': False,
                    'evidence_hash': digest,
                    'evidence_reference': '%s:%s' % (attachment._name, attachment.id),
                    'evidence_attachment_id': attachment.id,
                    'evidence_document_id': document.id,
                })
            except Exception:
                missed.append(position.symbol)
                # The mark itself is untouched: a failed refresh must not be
                # mistaken for a good price, so the error is recorded instead.
                position.with_context(capital_market_refresh=True).price_error_at = stamped_at
                _logger.warning('Mark refresh failed for position %s', position.id, exc_info=True)
        if missed:
            self.message_post(body=_('Marks refreshed. No public price returned for: %s. Those positions keep their previous mark.', ', '.join(missed)), subtype_xmlid='mail.mt_note')
        return True

    def _scan_alert_rules(self):
        """Evaluate this book's rules once against the current marks."""
        self.ensure_one()
        position_by_symbol = {p.symbol: p for p in self.position_ids if p.quantity}
        for rule in self.alert_rule_ids:
            unusable = rule._unusable_marks(position_by_symbol)
            if unusable:
                rule._flag_unusable_marks(unusable)
                continue
            value = rule._evaluate(position_by_symbol)
            if value is None:
                # Condition no longer holds: arm the rule again.
                if rule.triggered:
                    rule.triggered = False
            elif not rule.triggered:
                rule._fire(value)

    @api.model
    def _cron_refresh_all_marks(self):
        for portfolio in self.search([]):
            try:
                with self.env.cr.savepoint():
                    portfolio.action_refresh_marks()
            except Exception:
                _logger.warning('Mark refresh failed for portfolio %s', portfolio.id, exc_info=True)
