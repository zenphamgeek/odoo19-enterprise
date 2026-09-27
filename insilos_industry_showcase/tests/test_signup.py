import re
import uuid

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSaasSignup(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('insilos_tenant_control.group_tenant_operator')
        category = cls.env['insilos.industry.category'].create({'name': 'Signup Test'})
        cls.template = cls.env['insilos.industry.template'].create({'name': 'Signup Exact Template', 'slug': 'signup_exact', 'category_id': category.id})
        cls.release = cls.env['insilos.template.release'].create({
            'name': 'signup-v1', 'template_id': cls.template.id,
            'artifact_uri': 's3://test/' + 'a' * 64 + '.sql.gz', 'artifact_sha256': 'a' * 64,
            'catalog_sha256': 'b' * 64, 'module_manifest': '[]', 'app_version': '19.0',
            'image_ref': 'docker.io/insilos/app@sha256:' + 'c' * 64, 'postgres_version': '16',
            'schema_sha256': 'd' * 64, 'filestore_manifest_uri': 's3://test/' + 'e' * 64 + '.json',
            'test_evidence_uri': 's3://test/' + 'f' * 64 + '.json',
        })
        cls.release.action_publish()

    def _post_signup(self, template_slug, subdomain=None, key=None):
        self.authenticate('admin', 'admin')
        response = self.url_open('/saas/signup')
        token = re.search(r'csrf_token.+?value="([^"]+)"', response.text).group(1)
        slug = subdomain or f'test-{uuid.uuid4().hex[:10]}'
        data = {
            'csrf_token': token, 'template_slug': template_slug, 'subdomain': slug,
            'idempotency_key': key or f'request-{uuid.uuid4().hex}', 'company_name': 'Test Company',
            'owner_name': 'Owner', 'owner_email': 'owner@example.test', 'owner_phone': '0900000000',
            'plan_tier': 'standard', 'company_size': '11-50',
        }
        return self.url_open('/saas/signup/submit', data=data, allow_redirects=False), slug

    def test_landing_projection_tracks_template_without_drift(self):
        landing = self.env['is.industry.landing'].create({
            'name': 'Projection Test', 'template_id': self.template.id,
        })
        self.template.write({'module_names': 'sale,crm'})
        self.assertEqual(landing.slug, self.template.slug)
        self.assertEqual(landing.module_names, 'sale,crm')

    def test_valid_exact_slug_creates_requested_operation_once(self):
        key = f'request-{uuid.uuid4().hex}'
        response, slug = self._post_signup(self.template.slug, key=key)
        self.assertEqual(response.status_code, 303)
        tenant = self.env['insilos.tenant'].search([('slug', '=', slug)])
        operation = self.env['insilos.tenant.operation'].search([('tenant_id', '=', tenant.id)])
        self.assertEqual(len(operation), 1)
        self.assertEqual(operation.state, 'queued')
        self.assertIn('status=requested', response.headers['Location'])
        replay, _ = self._post_signup(self.template.slug, subdomain=slug, key=key)
        self.assertIn('status=requested', replay.headers['Location'])
        self.assertEqual(self.env['insilos.tenant.operation'].search_count([('idempotency_key', '=', key)]), 1)

    def test_unknown_and_malformed_template_create_nothing(self):
        for template_slug in ('unknown_slug', '../bad'):
            before = tuple(self.env[model].search_count([]) for model in ('insilos.tenant', 'insilos.tenant.operation', 'insilos.template.release'))
            response, _slug = self._post_signup(template_slug)
            after = tuple(self.env[model].search_count([]) for model in ('insilos.tenant', 'insilos.tenant.operation', 'insilos.template.release'))
            self.assertEqual(response.status_code, 303)
            self.assertIn('error=template_invalid', response.headers['Location'])
            self.assertEqual(after, before)

    def test_invalid_releases_create_nothing(self):
        for suffix, release_values in (
            ('missing', None),
            ('draft', {}),
            ('version', {'app_version': '20.0'}),
            ('entitlement', {'required_entitlements': ['community']}),
        ):
            template = self.env['insilos.industry.template'].create({
                'name': f'Invalid Release {suffix}', 'slug': f'invalid_release_{suffix}',
                'category_id': self.template.category_id.id,
            })
            if release_values is not None:
                values = self.release.copy_data({'name': f'invalid-{suffix}', 'template_id': template.id})[0]
                values.update(release_values)
                self.env['insilos.template.release'].create(values)
            before = tuple(self.env[model].search_count([]) for model in ('insilos.tenant', 'insilos.tenant.operation', 'insilos.template.release'))
            response, _slug = self._post_signup(template.slug)
            self.assertIn('error=release_invalid', response.headers['Location'])
            self.assertEqual(tuple(self.env[model].search_count([]) for model in ('insilos.tenant', 'insilos.tenant.operation', 'insilos.template.release')), before)
