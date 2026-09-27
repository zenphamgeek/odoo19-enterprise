import hashlib
import hmac

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestTenantControl(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('insilos_tenant_control.group_tenant_operator')

    def _template(self):
        template = self.env['insilos.industry.template'].search([], limit=1)
        if not template:
            category = self.env['insilos.industry.category'].create({'name': 'Test Category'})
            template = self.env['insilos.industry.template'].create({'name': 'Test Industry', 'category_id': category.id})
        return template

    def _release(self):
        template = self._template()
        sequence = getattr(self, '_release_sequence', 0) + 1
        self._release_sequence = sequence
        return self.env['insilos.template.release'].create({
            'name': f'v{sequence}', 'template_id': template.id,
            'artifact_uri': f's3://test/{sequence:064x}.sql.gz',
            'artifact_sha256': f'{sequence:064x}', 'catalog_sha256': 'b' * 64,
            'module_manifest': '[]', 'app_version': '19.0',
            'image_ref': 'docker.io/innoriahub/insilos@sha256:' + 'c' * 64,
            'postgres_version': '16', 'schema_sha256': 'd' * 64,
            'filestore_manifest_uri': 's3://test/' + 'e' * 64 + '.filestore.json',
            'test_evidence_uri': 's3://test/' + 'f' * 64 + '.tests.json',
        })

    def _tenant_values(self, **overrides):
        release = self._release()
        release.action_publish()
        values = {
            'name': 'Tenant One',
            'slug': 'tenant-one',
            'db_name': 'tenant_one',
            'primary_domain': 'tenant-one.insilos.test',
            'db_uuid': '12345678-1234-4234-9234-123456789abc',
            'environment': 'production',
            'region': 'ap-southeast-1',
            'cluster': 'primary',
            'template_id': release.template_id.id,
            'release_id': release.id,
        }
        values.update(overrides)
        return values

    def test_tenant_identity_is_unique(self):
        original = self._tenant_values()
        self.env['insilos.tenant'].create(original)
        for index, field in enumerate(('slug', 'db_name', 'primary_domain', 'db_uuid'), start=1):
            values = self._tenant_values(
                name=f'Tenant {field}', slug=f'tenant-{index + 1}', db_name=f'tenant_{index + 1}',
                primary_domain=f'tenant-{index + 1}.insilos.test',
                db_uuid=f'12345678-1234-4234-9234-{index:012x}',
            )
            values[field] = original[field]
            with self.env.cr.savepoint(), mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
                self.env['insilos.tenant'].create(values)

    def test_fleet_actions_keep_canonical_and_alias_metadata(self):
        canonical = self.env.ref('insilos_tenant_control.action_tenant')
        alias = self.env.ref('databases.action_view_databases_all')
        self.assertEqual((canonical.path, canonical.res_model), ('tenant-fleet', 'insilos.tenant'))
        self.assertEqual((alias.path, alias.res_model), ('databases', 'project.project'))

    def test_tenant_acl_denies_unprivileged_create(self):
        user = self.env['res.users'].create({
            'name': 'Fleet ACL User', 'login': 'fleet-acl-user',
            'partner_id': self.env['res.partner'].create({'name': 'Fleet ACL User'}).id,
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaises(AccessError):
            self.env['insilos.tenant'].with_user(user).create(self._tenant_values())

    def test_published_release_is_immutable(self):
        release = self._release()
        release.action_publish()
        with self.assertRaises(UserError):
            release.write({'name': 'v2'})
        with self.assertRaises(UserError):
            release.unlink()

    def test_tenant_requires_published_release(self):
        release = self._release()
        values = self._tenant_values(release_id=release.id, template_id=release.template_id.id)
        with self.assertRaises(ValidationError):
            self.env['insilos.tenant'].create(values)

    def test_release_entitlement_conflict_and_version_gate(self):
        for overrides in (
            {'app_version': '20.0'},
            {'required_entitlements': ['community']},
            {'module_manifest': '["sale"]', 'conflicts': ['sale']},
        ):
            release = self._release()
            release.write(overrides)
            with self.assertRaises(ValidationError):
                release.action_publish()
            self.assertEqual(release.state, 'draft')

    def test_release_identity_and_content_addressing(self):
        release = self._release()
        values = release.copy_data()[0]
        values['name'] = 'invalid-content-addressing'
        values['artifact_sha256'] = 'a' * 64
        values['artifact_uri'] = 's3://test/not-content-addressed.sql.gz'
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self.env['insilos.template.release'].create(values)
        values.update(artifact_uri='s3://test/' + 'a' * 64 + '.sql.gz', name=release.name)
        with self.env.cr.savepoint(), mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
            self.env['insilos.template.release'].create(values)

    def test_provision_is_idempotent_and_operation_identity_is_immutable(self):
        tenant = self.env['insilos.tenant'].create(self._tenant_values())
        operation = tenant.action_provision('caller-request-0001')
        self.assertEqual(operation, tenant.action_provision('caller-request-0001'))
        self.assertEqual(operation.operation_type, 'provision')
        self.assertEqual(operation.state, 'queued')
        with self.assertRaises(UserError):
            operation.write({'idempotency_key': 'caller-request-0002', 'state': 'running'})
        with self.assertRaises(UserError):
            operation.write({'message': 'state-less update'})
        operation.write({'state': 'running', 'lock_owner': 'worker-1', 'lock_token': 'lock-0001', 'locked_at': fields.Datetime.now()})
        operation.write({'state': 'done'})
        with self.assertRaises(UserError):
            operation.write({'state': 'failed'})
        with self.assertRaises(UserError):
            operation.unlink()

    def test_same_idempotency_key_rejects_different_payload(self):
        tenant = self.env['insilos.tenant'].create(self._tenant_values())
        tenant.action_provision('caller-request-0003', {'slug': tenant.slug})
        with self.assertRaises(UserError):
            tenant.action_provision('caller-request-0003', {'slug': 'different'})

    def test_reconciliation_evidence_controls_active_outcome(self):
        tenant = self.env['insilos.tenant'].create(self._tenant_values())
        operation = tenant.action_provision('caller-request-0004')
        operation.write({'state': 'running'})
        with self.assertRaises(UserError):
            operation.action_reconcile_outcome(True, {'release_sha256': tenant.release_id.artifact_sha256})
        self.assertEqual(tenant.observed_state, 'unknown')
        evidence = {
            'release_sha256': tenant.release_id.artifact_sha256,
            'installed_modules_sha256': '1' * 64,
            'host_db_binding': f'{tenant.primary_domain}={tenant.db_name}',
            'health_status': 'healthy',
            'reconciliation_uri': 's3://evidence/reconciliation.json',
            'reconciliation_sha256': '2' * 64,
        }
        operation.action_reconcile_outcome(True, evidence)
        self.assertEqual((operation.state, tenant.observed_state), ('done', 'healthy'))
        self.assertEqual(tenant.reconciliation_evidence_uri, evidence['reconciliation_uri'])

    def test_reconciliation_failure_keeps_tenant_inactive(self):
        tenant = self.env['insilos.tenant'].create(self._tenant_values())
        operation = tenant.action_provision('caller-request-0005')
        operation.write({'state': 'running'})
        operation.action_reconcile_outcome(False, error='executor failed')
        self.assertEqual((operation.state, tenant.observed_state), ('failed', 'failed'))
        self.assertEqual(operation.error, 'executor failed')

    def test_verified_payment_callback_converts_once_and_rejects_reorder(self):
        tenant = self.env['insilos.tenant'].create(self._tenant_values())
        secret = 'test-payment-secret'
        self.env['ir.config_parameter'].sudo().set_param('insilos_tenant_control.payment_callback_secret', secret)
        reference = 'provider-ref-1'
        payload = f'{reference}:paid:{tenant.id}:{tenant.plan_tier}:12'
        signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        self.assertTrue(tenant.action_verify_payment_callback(reference, 'paid', signature, 12))
        paid_until = tenant.paid_until
        self.assertFalse(tenant.action_verify_payment_callback(reference, 'paid', signature, 12))
        self.assertEqual(tenant.paid_until, paid_until)
        with self.assertRaises(UserError):
            tenant.action_verify_payment_callback('other-reference', 'paid', signature, 12)

    def test_invalid_and_failed_payment_callbacks_do_not_convert(self):
        tenant = self.env['insilos.tenant'].create(self._tenant_values())
        secret = 'test-payment-secret'
        self.env['ir.config_parameter'].sudo().set_param('insilos_tenant_control.payment_callback_secret', secret)
        with self.assertRaises(UserError):
            tenant.action_verify_payment_callback('provider-ref-2', 'paid', 'invalid', 12)
        reference = 'provider-ref-3'
        signature = hmac.new(secret.encode(), f'{reference}:failed:{tenant.id}:{tenant.plan_tier}:12'.encode(), hashlib.sha256).hexdigest()
        self.assertFalse(tenant.action_verify_payment_callback(reference, 'failed', signature, 12))
        self.assertEqual(tenant.tenant_type, 'trial')
