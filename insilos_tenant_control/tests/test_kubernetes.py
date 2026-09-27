from types import SimpleNamespace
from unittest.mock import Mock, patch

from odoo.tests.common import TransactionCase

from ..services.kubernetes import KubernetesJobService


class TestKubernetesJobService(TransactionCase):

    @patch('odoo.addons.insilos_tenant_control.services.kubernetes.requests')
    @patch('pathlib.Path.read_text', return_value='token')
    @patch.dict('os.environ', {'KUBERNETES_SERVICE_HOST': 'kubernetes.default'})
    def test_reconcile_creates_canonical_job_once(self, _token, requests):
        operation = SimpleNamespace(
            id=42,
            tenant_id=SimpleNamespace(id=1, slug='demo', name='Demo', db_name='insilos_ind_demo', primary_domain='demo.insilos.com', template_id=SimpleNamespace(slug='base'), release_id=SimpleNamespace(artifact_uri='s3://insilos-templates/releases/base/' + 'a' * 64 + '.sql.gz', artifact_sha256='a' * 64, image_ref='docker.io/innoriahub/insilos@sha256:' + 'c' * 64)),
        )
        requests.get.return_value = Mock(status_code=404)
        requests.post.return_value = Mock(status_code=201)

        name = KubernetesJobService('production').reconcile(operation)

        self.assertEqual(name, 'insilos-tenant-op-42')
        payload = requests.post.call_args.kwargs['json']
        self.assertEqual(payload['metadata']['name'], name)
        command = payload['spec']['template']['spec']['containers'][0]['args'][0]
        self.assertIn('/scripts/provision-tenant.sh', command)
        self.assertIn('$INSILOS_TENANT_SLUG', command)
        env_names = {env['name'] for env in payload['spec']['template']['spec']['containers'][0]['env']}
        self.assertTrue({'INSILOS_TENANT_SLUG', 'PGPASSWORD', 'MINIO_SECRET'} <= env_names)

    @patch('odoo.addons.insilos_tenant_control.services.kubernetes.requests')
    @patch('pathlib.Path.read_text', return_value='token')
    @patch.dict('os.environ', {'KUBERNETES_SERVICE_HOST': 'kubernetes.default'})
    def test_reconcile_accepts_existing_or_create_conflict(self, _token, requests):
        operation = SimpleNamespace(id=42, tenant_id=SimpleNamespace(id=1, slug='demo', name='Demo', db_name='db', primary_domain='demo.insilos.com', template_id=SimpleNamespace(slug='base'), release_id=SimpleNamespace(artifact_uri='s3://insilos-templates/releases/base/' + 'a' * 64 + '.sql.gz', artifact_sha256='a' * 64, image_ref='docker.io/innoriahub/insilos@sha256:' + 'c' * 64)))
        requests.get.return_value = Mock(status_code=200)

        KubernetesJobService('production').reconcile(operation)

        requests.post.assert_not_called()
        requests.get.return_value = Mock(status_code=404)
        requests.post.return_value = Mock(status_code=409)
        self.assertEqual(KubernetesJobService('production').reconcile(operation), 'insilos-tenant-op-42')

    @patch.dict('os.environ', {'KUBERNETES_SERVICE_HOST': 'kubernetes.default'})
    def test_job_rejects_mutable_image(self):
        operation = SimpleNamespace(id=42, tenant_id=SimpleNamespace(release_id=SimpleNamespace(image_ref='docker.io/innoriahub/insilos:latest')))
        with self.assertRaisesRegex(ValueError, 'immutable digest'):
            KubernetesJobService('production').job(operation)
