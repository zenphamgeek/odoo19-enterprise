from contextlib import closing
import json
import os
import re

import odoo.sql_db
from odoo import api, fields, models
try:
    from odoo.addons.databases.api import InsilosDatabaseApi
except ImportError:
    from odoo.addons.databases.api import OdooDatabaseApi as InsilosDatabaseApi
from odoo.exceptions import UserError

from ..services import KubernetesJobService, TenantReconciliationService


_SECRET_RE = re.compile(
    r'(?i)(?:(?:postgres(?:ql)?|https?)://)[^\s]+|'
    r'((?:password|passwd|pwd|token|api[_-]?key)\s*[=:]\s*)[^\s,;]+')


def _redact_error(error):
    return _SECRET_RE.sub(lambda match: f'{match.group(1) or ""}[REDACTED]', str(error))


class ProjectProject(models.Model):
    _inherit = 'project.project'

    tenant_id = fields.Many2one(
        'insilos.tenant',
        string='Tenant',
        index=True,
        copy=False,
        ondelete='restrict',
    )
    fleet_classification = fields.Selection([
        ('production_tenant', 'Production Tenant'),
        ('industry_template', 'Industry Template'),
        ('dev', 'Development'),
        ('legacy', 'Legacy'),
        ('unknown', 'Unknown'),
    ], string='Fleet Classification', default='unknown', required=True, copy=False)
    classification_owner_id = fields.Many2one('res.users', string='Classification Owner', copy=False)
    classification_reviewer_id = fields.Many2one('res.users', string='Classification Reviewer', copy=False)
    classification_evidence = fields.Char(string='Classification Evidence', copy=False)
    classified_at = fields.Datetime(copy=False, readonly=True)
    tenant_db_name = fields.Char(related='tenant_id.db_name', string='Tenant Database', readonly=True)
    tenant_domain = fields.Char(related='tenant_id.primary_domain', string='Tenant Domain', readonly=True)
    tenant_observed_state = fields.Selection(related='tenant_id.observed_state', string='Tenant Health', readonly=True)

    _tenant_projection_unique = models.UniqueIndex(
        '(tenant_id) WHERE tenant_id IS NOT NULL',
        'A tenant can have only one fleet projection.',
    )

    def _require_tenant_projection(self):
        if self.filtered(lambda projection: not projection.tenant_id):
            raise UserError(self.env._('Link this fleet projection to a tenant before running tenant-sensitive actions.'))

    def write(self, values):
        if 'fleet_classification' in values and 'classified_at' not in values:
            values['classified_at'] = fields.Datetime.now()
        return super().write(values)

    @api.model
    def import_approved_tenant_mapping(self, artifact):
        if not self.env.user.has_group('insilos_tenant_control.group_tenant_operator'):
            raise UserError(self.env._('Only tenant operators can import an approved mapping.'))
        if not artifact.get('approved_by') or not artifact.get('approved_at') or not artifact.get('evidence'):
            raise UserError(self.env._('Mapping artifact requires approval identity, timestamp, and evidence.'))
        mappings = artifact.get('mappings')
        if not isinstance(mappings, list):
            raise UserError(self.env._('Mapping artifact must contain an explicit mappings list.'))
        for mapping in mappings:
            if set(mapping) != {'projection_id', 'tenant_id'}:
                raise UserError(self.env._('Each mapping must contain only projection_id and tenant_id.'))
            projection = self.browse(mapping['projection_id']).exists()
            tenant = self.env['insilos.tenant'].browse(mapping['tenant_id']).exists()
            if len(projection) != 1 or len(tenant) != 1 or projection.tenant_id:
                raise UserError(self.env._('Mapping references must exist and projection must be unlinked.'))
        for mapping in mappings:
            self.browse(mapping['projection_id']).write({'tenant_id': mapping['tenant_id']})
        return len(mappings)

    @api.model
    def action_synchronize_all_databases(self):
        projections = self.search([('database_hosting', 'not in', (False, 'other'))])
        projections._require_tenant_projection()
        return super().action_synchronize_all_databases()

    def _observe_routes(self):
        values = {}
        errors = []
        for projection in self:
            if not projection.tenant_id:
                continue
            try:
                api_client = InsilosDatabaseApi(
                    projection.database_url, projection.database_name,
                    projection.database_api_login, projection.database_api_key_to_use)
                values[projection.tenant_id.primary_domain] = api_client.get_database_uuid()
            except Exception as error:
                errors.append(_redact_error(error))
        return {'values': values, 'reason': '; '.join(errors) or None}

    @api.model
    def _observe_artifacts(self):
        return {'values': None, 'reason': 'No deployed artifact observer is configured.'}

    @api.model
    def _observe_jobs(self, operations):
        values = {}
        errors = []
        for operation in operations.filtered('k8s_job_name'):
            try:
                values[operation.k8s_job_name] = KubernetesJobService(operation.k8s_namespace).observed_state(operation.k8s_job_name)
            except Exception as error:
                errors.append(_redact_error(error))
        return {'values': values if not errors else None, 'reason': '; '.join(errors) or None}

    @api.model
    def _tenant_reconciliation_snapshot(self):
        with closing(insilos.sql_db.db_connect('postgres').cursor()) as cr:
            cr.execute("SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate AND datname LIKE 'insilos%' ORDER BY datname")
            pg_databases = [row[0] for row in cr.fetchall()]
        tenants = self.env['insilos.tenant'].search([])
        projections = self.search([('database_hosting', 'not in', (False, 'other'))])
        projection_classes = {projection.database_name: projection.fleet_classification for projection in projections}
        tenant_names = set(tenants.mapped('db_name'))
        disposition_path = os.environ.get('INSILOS_FLEET_DISPOSITION_PATH')
        reviewed_pg_names = set()
        if disposition_path:
            with open(disposition_path, encoding='utf-8') as disposition_file:
                reviewed_pg_names = set(json.load(disposition_file)['dispositions']['pg_only']['databases'])
        pg_inventory = []
        for database_name in pg_databases:
            fleet_classification = projection_classes.get(database_name)
            if fleet_classification == 'industry_template':
                category = 'blueprint_inventory'
            elif fleet_classification == 'dev':
                category = 'infrastructure_telemetry'
            elif fleet_classification == 'production_tenant' or database_name in tenant_names or database_name in reviewed_pg_names:
                category = 'tenant_candidate'
            else:
                category = 'unknown'
            pg_inventory.append({'database_name': database_name, 'category': category,
                                 'fleet_classification': fleet_classification})
        operations = self.env['insilos.tenant.operation'].search([('state', 'in', ('queued', 'running'))])
        return {
            'pg_databases': pg_databases,
            'pg_inventory': pg_inventory,
            'tenants': [{
                'id': tenant.id, 'db_name': tenant.db_name, 'db_uuid': tenant.db_uuid,
                'primary_domain': tenant.primary_domain,
                'desired_state': tenant.desired_state, 'release_id': tenant.release_id.id,
                'artifact_sha256': tenant.release_id.artifact_sha256,
            } for tenant in tenants],
            'projections': [{
                'id': projection.id, 'tenant_id': projection.tenant_id.id,
                'database_name': projection.database_name,
                'domain': TenantReconciliationService.projection_domain(projection.database_url),
                'classification': projection.fleet_classification,
                'owner_id': projection.classification_owner_id.id,
                'reviewer_id': projection.classification_reviewer_id.id,
                'evidence': projection.classification_evidence,
                'classified_at': projection.classified_at,
            } for projection in projections],
            'domains': [tenant.primary_domain for tenant in tenants],
            'operations': [{
                'id': operation.id, 'state': operation.state,
                'since': operation.started_at or operation.create_date,
                'job_name': operation.k8s_job_name,
            } for operation in operations],
            'routes': projections._observe_routes(),
            'artifacts': self._observe_artifacts(),
            'jobs': self._observe_jobs(operations),
        }

    @api.model
    def action_legacy_inventory(self):
        try:
            report = TenantReconciliationService().inventory(self._tenant_reconciliation_snapshot())
        except Exception as error:
            raise UserError(self.env._('Unable to build the legacy inventory: %s', str(error))) from error
        return report

    @api.model
    def action_sync_local_databases(self):
        try:
            report = TenantReconciliationService().report(self._tenant_reconciliation_snapshot())
        except Exception as error:
            raise UserError(self.env._('Unable to build the reconciliation preview: %s', str(error))) from error
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._('Reconciliation Preview'),
                'message': json.dumps(report, sort_keys=True, default=str),
                'type': 'warning' if report['summary']['drift'] else 'info',
                'sticky': True,
            },
        }

    def action_database_connect(self):
        self._require_tenant_projection()
        return super().action_database_connect()

    def action_database_synchronize(self):
        self._require_tenant_projection()
        return super().action_database_synchronize()

    def action_database_invite_users(self):
        self._require_tenant_projection()
        return super().action_database_invite_users()

    def action_database_remove_users(self, default_user_ids=None):
        self._require_tenant_projection()
        return super().action_database_remove_users(default_user_ids=default_user_ids)
