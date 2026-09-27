import hashlib
import json
import re
from uuid import uuid4

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from ..services import KubernetesJobService


class TenantOperation(models.Model):
    _name = 'insilos.tenant.operation'
    _description = 'Tenant Operation'
    _order = 'create_date desc, id desc'

    tenant_id = fields.Many2one('insilos.tenant', required=True, ondelete='restrict')
    operation_type = fields.Selection([
        ('provision', 'Provision'), ('suspend', 'Suspend'), ('resume', 'Resume'),
        ('delete', 'Delete'), ('backup', 'Backup')
    ], required=True)
    state = fields.Selection([
        ('queued', 'Queued'), ('running', 'Running'), ('done', 'Done'),
        ('failed', 'Failed'), ('cancelled', 'Cancelled'),
    ], default='queued', required=True)
    idempotency_key = fields.Char(required=True, readonly=True)
    payload_sha256 = fields.Char(required=True, readonly=True, default='0' * 64)
    operation_uuid = fields.Char(required=True, readonly=True, default=lambda self: str(uuid4()))
    lock_owner = fields.Char(readonly=True)
    lock_token = fields.Char(readonly=True)
    locked_at = fields.Datetime(readonly=True)
    k8s_job_name = fields.Char(readonly=True)
    k8s_namespace = fields.Char(readonly=True)
    requested_by = fields.Many2one('res.users', required=True, readonly=True)
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)
    error = fields.Text(readonly=True)
    message = fields.Text(readonly=True)
    release_sha256 = fields.Char(readonly=True)
    installed_modules_sha256 = fields.Char(readonly=True)
    host_db_binding = fields.Char(readonly=True)
    health_status = fields.Char(readonly=True)
    reconciliation_uri = fields.Char(readonly=True)
    reconciliation_sha256 = fields.Char(readonly=True)

    _idempotency_key_unique = models.UniqueIndex('(tenant_id, operation_type, idempotency_key)', 'Operation idempotency key must be unique per tenant and operation type.')
    _operation_uuid_unique = models.UniqueIndex('(operation_uuid)', 'Operation UUID must be unique.')
    _lock_token_unique = models.UniqueIndex('(lock_token) WHERE lock_token IS NOT NULL', 'Operation lock token must be unique.')
    _terminal_states = {'done', 'failed', 'cancelled'}
    _transitions = {'queued': {'running', 'failed', 'cancelled'}, 'running': {'done', 'failed', 'cancelled'}}
    _evidence_fields = {'release_sha256', 'installed_modules_sha256', 'host_db_binding', 'health_status', 'reconciliation_uri', 'reconciliation_sha256'}

    @api.model
    def queue_operation(self, tenant, operation_type, idempotency_key=None, payload=None):
        if not (self.env.is_superuser() or self.env.user.has_group('insilos_tenant_control.group_tenant_requester')):
            raise AccessError(self.env._('Only tenant requesters can queue operations.'))
        key = idempotency_key or str(uuid4())
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', key):
            raise UserError(self.env._('Idempotency key must contain 8-128 safe characters.'))
        payload = payload or {'tenant_id': tenant.id, 'operation_type': operation_type, 'release_id': tenant.release_id.id}
        payload_sha256 = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        existing = self.search([('tenant_id', '=', tenant.id), ('operation_type', '=', operation_type), ('idempotency_key', '=', key)], limit=1)
        if existing:
            if existing.payload_sha256 != payload_sha256:
                raise UserError(self.env._('Idempotency key was already used with a different payload.'))
            return existing
        return self.create({
            'tenant_id': tenant.id, 'operation_type': operation_type, 'idempotency_key': key,
            'payload_sha256': payload_sha256, 'requested_by': self.env.user.id,
        })

    def action_submit(self):
        if not self.env.user.has_group('insilos_tenant_control.group_tenant_operator'):
            raise AccessError(self.env._('Only tenant operators can submit operations.'))
        for operation in self:
            if operation.state != 'queued':
                raise UserError(self.env._('Only queued operations can be submitted.'))
            namespace = self.env['ir.config_parameter'].sudo().get_param('insilos_tenant_control.k8s_namespace', 'production')
            try:
                job_name = KubernetesJobService(namespace).reconcile(operation)
            except Exception as error:
                operation.write({'state': 'failed', 'finished_at': fields.Datetime.now(), 'error': 'Kubernetes Job submission failed.'})
                raise UserError(self.env._('Kubernetes Job submission failed.')) from error
            operation.write({'state': 'running', 'started_at': fields.Datetime.now(), 'k8s_job_name': job_name, 'k8s_namespace': namespace})
        return True

    def action_reconcile_outcome(self, success, evidence=None, error=None):
        self.ensure_one()
        if self.state != 'running':
            raise UserError(self.env._('Only running operations can be reconciled.'))
        evidence = evidence or {}
        if success:
            if set(evidence) != self._evidence_fields or evidence.get('release_sha256') != self.tenant_id.release_id.artifact_sha256:
                raise UserError(self.env._('Complete reconciliation evidence is required for success.'))
            if not all(evidence.values()) or evidence['health_status'] != 'healthy':
                raise UserError(self.env._('Healthy reconciliation evidence is required for success.'))
            if evidence['host_db_binding'] != f'{self.tenant_id.primary_domain}={self.tenant_id.db_name}':
                raise UserError(self.env._('Host to database binding does not match the tenant.'))
            if any(not re.fullmatch(r'[0-9a-f]{64}', evidence[name]) for name in ('release_sha256', 'installed_modules_sha256', 'reconciliation_sha256')):
                raise UserError(self.env._('Reconciliation checksums must be lowercase SHA-256 values.'))
            self.write({'state': 'done', 'finished_at': fields.Datetime.now(), **evidence})
            self.tenant_id.write({'observed_state': 'healthy', 'last_reconciled_at': fields.Datetime.now(), 'reconciliation_evidence_uri': evidence['reconciliation_uri']})
        else:
            self.write({'state': 'failed', 'finished_at': fields.Datetime.now(), 'error': error or self.env._('Provisioning failed.')})
            self.tenant_id.observed_state = 'failed'
        return True

    def write(self, vals):
        allowed = {'state', 'lock_owner', 'lock_token', 'locked_at', 'k8s_job_name', 'k8s_namespace', 'started_at', 'finished_at', 'error', 'message'} | self._evidence_fields
        if not self.env.user.has_group('insilos_tenant_control.group_tenant_operator'):
            raise AccessError(self.env._('Only tenant operators can update operations.'))
        if set(vals) - allowed:
            raise UserError(self.env._('Operation identity is immutable; only state and execution metadata can change.'))
        for operation in self:
            if operation.state in self._terminal_states:
                raise UserError(self.env._('Terminal operations are immutable.'))
            target = vals.get('state')
            if not target or target == operation.state or target not in self._transitions[operation.state]:
                raise UserError(self.env._('Operation updates require a valid state transition.'))
        return super().write(vals)

    def unlink(self):
        raise UserError(self.env._('Tenant operations are append-only and cannot be deleted.'))
