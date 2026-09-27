import datetime
import hashlib
import json

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from ..services.graph_identity import canonical_hash, node_urn


SOURCE_PAYLOAD_FIELDS = {
    'logistics.idp.case': frozenset({'source_system', 'source_key', 'source_version', 'provenance', 'reconciled'}),
    'res.company': frozenset({'reconciled'}),
    'product.product': frozenset({'reconciled'}),
    'res.partner': frozenset({'reconciled'}),
    'purchase.order': frozenset({'reconciled'}),
    'sale.order': frozenset({'reconciled'}),
    'account.move': frozenset({'reconciled'}),
    'stock.quant': frozenset({'reconciled'}),
}
EVENT_TYPES = frozenset({'UPSERT', 'DELETE'})
IMMUTABLE_FIELDS = frozenset({
    'company_id', 'source_model', 'source_id', 'event_type', 'payload',
    'payload_hash', 'mutation_token', 'event_hash', 'create_date',
})


class KgOutbox(models.Model):
    _name = 'kg.outbox'
    _description = 'Knowledge Graph Transactional Outbox'
    _order = 'id'

    company_id = fields.Many2one('res.company', required=True, index=True, ondelete='cascade', readonly=True)
    source_model = fields.Char(required=True, index=True, readonly=True)
    source_id = fields.Char(required=True, index=True, readonly=True)
    event_type = fields.Selection([('UPSERT', 'Upsert'), ('DELETE', 'Delete')], required=True, readonly=True)
    payload = fields.Json(required=True, readonly=True)
    payload_hash = fields.Char(required=True, readonly=True)
    mutation_token = fields.Char(required=True, readonly=True)
    event_hash = fields.Char(required=True, index=True, readonly=True)
    state = fields.Selection([
        ('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('RETRY', 'Retry'),
        ('DONE', 'Done'), ('DEAD', 'Dead'),
    ], required=True, default='PENDING', index=True)
    attempts = fields.Integer(required=True, default=0, readonly=True)
    next_attempt_at = fields.Datetime(index=True)
    claimed_at = fields.Datetime(index=True, readonly=True)
    last_error = fields.Char(readonly=True)
    processed_at = fields.Datetime(readonly=True)

    _event_hash_unique = models.Constraint('UNIQUE(event_hash)', 'KG outbox event must be unique.')
    _attempts_check = models.Constraint('CHECK(attempts >= 0 AND attempts <= 8)', 'KG outbox attempts must be between 0 and 8.')
    _state_check = models.Constraint(
        "CHECK((state = 'PROCESSING') = (claimed_at IS NOT NULL) OR state IN ('DONE', 'DEAD'))",
        'KG outbox claim state is invalid.')

    @api.model
    def _event_digest(self, company_id, source_model, source_id, event_type, payload_hash, mutation_token):
        value = '%s\0%s\0%s\0%s\0%s\0%s' % (
            company_id, source_model, source_id, event_type, payload_hash, mutation_token)
        return hashlib.sha256(value.encode()).hexdigest()

    @api.model
    def _validated_payload(self, source_model, payload):
        allowed = SOURCE_PAYLOAD_FIELDS.get(source_model)
        if allowed is None:
            raise ValidationError('KG outbox source model is not allowed.')
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise ValidationError('KG outbox payload contains non-allowlisted fields.')
        return json.loads(json.dumps(payload, sort_keys=True, separators=(',', ':')))

    @api.model
    def enqueue(self, record, event_type='UPSERT', payload=None, mutation_token=None):
        record.ensure_one()
        record.check_access('read')
        if event_type not in EVENT_TYPES or record._name not in SOURCE_PAYLOAD_FIELDS:
            raise ValidationError('KG outbox event is not allowed.')
        company = record if record._name == 'res.company' else record.company_id
        if company not in self.env.companies:
            raise AccessError('KG outbox source company is not allowed.')
        reserved_id = False
        if mutation_token is None:
            self.env.cr.execute("SELECT nextval(pg_get_serial_sequence('kg_outbox', 'id'))")
            reserved_id = self.env.cr.fetchone()[0]
            mutation_token = 'outbox:%s' % reserved_id
        if not mutation_token or len(mutation_token) > 128:
            raise ValidationError('KG outbox mutation token is required and bounded.')
        clean = self._validated_payload(record._name, payload or {}) or {}
        payload_hash = canonical_hash(clean)
        event_hash = self._event_digest(
            company.id, record._name, record.id, event_type, payload_hash, mutation_token)
        values = {
            'company_id': company.id, 'source_model': record._name, 'source_id': str(record.id),
            'event_type': event_type, 'payload': clean, 'payload_hash': payload_hash,
            'mutation_token': mutation_token, 'event_hash': event_hash,
            **({'id': reserved_id} if reserved_id else {}),
        }
        elevated = self.sudo().with_context(allowed_company_ids=[company.id]).with_company(company)
        existing = elevated.search([('event_hash', '=', event_hash)], limit=1)
        if existing:
            return existing
        try:
            with self.env.cr.savepoint():
                return elevated.create(values)
        except IntegrityError:
            return elevated.search([('event_hash', '=', event_hash)], limit=1)

    @api.model
    def enqueue_delete(self, company, source_model, source_id, mutation_token):
        company.ensure_one()
        company.check_access('read')
        if company not in self.env.companies or source_model not in SOURCE_PAYLOAD_FIELDS:
            raise AccessError('KG outbox source company is not allowed.')
        clean = self._validated_payload(source_model, {'reconciled': True})
        payload_hash = canonical_hash(clean)
        event_hash = self._event_digest(
            company.id, source_model, source_id, 'DELETE', payload_hash, mutation_token)
        elevated = self.sudo().with_context(allowed_company_ids=[company.id]).with_company(company)
        existing = elevated.search([('event_hash', '=', event_hash)], limit=1)
        if existing:
            return existing
        values = {
            'company_id': company.id, 'source_model': source_model, 'source_id': str(source_id),
            'event_type': 'DELETE', 'payload': clean, 'payload_hash': payload_hash,
            'mutation_token': mutation_token, 'event_hash': event_hash,
        }
        try:
            with self.env.cr.savepoint():
                return elevated.create(values)
        except IntegrityError:
            return elevated.search([('event_hash', '=', event_hash)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        self.check_access('create')
        for vals in vals_list:
            clean = self._validated_payload(vals['source_model'], vals.get('payload'))
            payload_hash = canonical_hash(clean)
            expected = self._event_digest(
                vals['company_id'], vals['source_model'], vals['source_id'], vals['event_type'],
                payload_hash, vals.get('mutation_token'))
            if vals.get('payload_hash') != payload_hash or vals.get('event_hash') != expected:
                raise ValidationError('KG outbox canonical hashes are invalid.')
            vals['payload'] = clean
        return super().create(vals_list)

    def write(self, vals):
        if IMMUTABLE_FIELDS & vals.keys():
            raise ValidationError('KG outbox event identity and payload are immutable.')
        return super().write(vals)

    @api.model
    def _claim_batch(self, limit=100, lease_seconds=300):
        if not self.env.user.has_group('insilos_knowledge_graph.group_kg_processor'):
            raise AccessError('KG processor authority is required.')
        company_ids = self.env.companies.ids
        if not company_ids:
            return self.browse()
        limit = max(1, min(int(limit), 500))
        self.flush_model(['state', 'next_attempt_at', 'claimed_at', 'attempts', 'company_id'])
        self.env.cr.execute("""
            WITH claimed AS MATERIALIZED (
                SELECT id FROM kg_outbox
                 WHERE company_id = ANY(%s)
                   AND attempts < 8
                   AND ((state IN ('PENDING', 'RETRY') AND (next_attempt_at IS NULL OR next_attempt_at <= NOW() AT TIME ZONE 'UTC'))
                    OR (state = 'PROCESSING' AND claimed_at <= NOW() AT TIME ZONE 'UTC' - make_interval(secs => %s)))
                 ORDER BY id FOR UPDATE SKIP LOCKED LIMIT %s
            )
            UPDATE kg_outbox AS event
               SET state = CASE WHEN event.attempts + 1 >= 8 THEN 'DEAD' ELSE 'PROCESSING' END,
                   attempts = event.attempts + 1,
                   claimed_at = CASE WHEN event.attempts + 1 >= 8 THEN NULL ELSE NOW() AT TIME ZONE 'UTC' END
              FROM claimed
             WHERE event.id = claimed.id
         RETURNING event.id
        """, (company_ids, lease_seconds, limit))
        claimed = self.browse([row[0] for row in self.env.cr.fetchall()])
        claimed.invalidate_recordset(['state', 'claimed_at', 'attempts'])
        return claimed.filtered(lambda event: event.state == 'PROCESSING')

    def _project(self):
        self.ensure_one()
        company = self.company_id
        env = self.env(context=dict(
            self.env.context, allowed_company_ids=[company.id]))
        if self.event_type == 'DELETE':
            nodes = env['kg.node'].search([('urn', '=', node_urn(company.id, self.source_model, self.source_id))])
            nodes.check_access('unlink')
            nodes.unlink()
            return
        if self.source_model not in env.registry.models:
            raise ValidationError('KG outbox optional source model is absent.')
        source = env[self.source_model].browse(int(self.source_id)).exists()
        source.check_access('read')
        if not source:
            return
        if self.source_model == 'logistics.idp.case':
            from ..services.logistics_projection import LogisticsProjection
            LogisticsProjection(env).project_case(source)
            return
        from ..services.enterprise_projection import EnterpriseProjection
        edges = env['kg.edge'].search([
            ('company_id', '=', company.id),
            ('source_reference', '=', '%s:%s' % (self.source_model, self.source_id)),
        ])
        edges.check_access('unlink')
        edges.unlink()
        EnterpriseProjection(env).project_record(source)

    @api.model
    def _cron_process(self, limit=100):
        claimed = self._claim_batch(limit=limit)
        for event in claimed:
            try:
                with self.env.cr.savepoint():
                    event._project()
                event.write({
                    'state': 'DONE', 'claimed_at': False, 'processed_at': fields.Datetime.now(),
                    'last_error': False,
                })
            except Exception as error:
                dead = event.attempts >= 8
                event.write({
                    'state': 'DEAD' if dead else 'RETRY', 'claimed_at': False,
                    'next_attempt_at': False if dead else fields.Datetime.now() + datetime.timedelta(
                        seconds=min(3600, 2 ** event.attempts)),
                    'last_error': type(error).__name__[:128],
                })
        return len(claimed)

    def action_requeue(self):
        if not self.env.user.has_group('insilos_knowledge_graph.group_kg_manager'):
            raise AccessError('Only KG managers may requeue dead events.')
        self.filtered(lambda event: event.state == 'DEAD').write({
            'state': 'RETRY', 'next_attempt_at': fields.Datetime.now(),
            'claimed_at': False, 'last_error': False, 'processed_at': False,
        })
