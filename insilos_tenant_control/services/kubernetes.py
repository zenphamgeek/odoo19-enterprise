import os
from pathlib import Path

import requests


class KubernetesJobService:
    token_path = Path('/var/run/secrets/kubernetes.io/serviceaccount/token')
    ca_path = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'

    def __init__(self, namespace):
        self.namespace = namespace
        host = os.environ['KUBERNETES_SERVICE_HOST']
        port = os.environ.get('KUBERNETES_SERVICE_PORT_HTTPS', os.environ.get('KUBERNETES_SERVICE_PORT', '443'))
        self.base_url = f'https://{host}:{port}'

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.token_path.read_text().strip()}',
            'Content-Type': 'application/json',
        }

    def job_name(self, operation):
        return f'insilos-tenant-op-{operation.id}'

    def job(self, operation):
        tenant = operation.tenant_id
        if '@sha256:' not in tenant.release_id.image_ref:
            raise ValueError('Tenant provision image must use an immutable digest')
        return {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'name': self.job_name(operation),
                'namespace': self.namespace,
                'labels': {'app': 'insilos-saas', 'insilos.tenant-operation': str(operation.id)},
            },
            'spec': {
                'backoffLimit': 0,
                'ttlSecondsAfterFinished': 3600,
                'template': {
                    'spec': {
                        'serviceAccountName': 'insilos-tenant-job-controller',
                        'restartPolicy': 'Never',
                        'volumes': [{'name': 'provision-script', 'configMap': {'name': 'insilos-provision-scripts', 'defaultMode': 365}}],
                        'containers': [{
                            'name': 'tenant-provisioner',
                            'image': tenant.release_id.image_ref,
                            'command': ['/bin/bash', '-c'],
                            'args': [
                                'exec /scripts/provision-tenant.sh '
                                '--slug="$INSILOS_TENANT_SLUG" '
                                '--company="$INSILOS_TENANT_NAME" '
                                '--mode=template '
                                '--vertical="$INSILOS_TENANT_TEMPLATE" '
                                '--artifact-uri="$INSILOS_TENANT_ARTIFACT_URI" '
                                '--artifact-sha256="$INSILOS_TENANT_ARTIFACT_SHA256"',
                            ],
                            'volumeMounts': [{'name': 'provision-script', 'mountPath': '/scripts', 'readOnly': True}],
                            'env': [
                                {'name': 'PG_HOST', 'valueFrom': {'secretKeyRef': {'name': 'insilos-db-secret', 'key': 'db-host'}}},
                                {'name': 'PG_PORT', 'valueFrom': {'secretKeyRef': {'name': 'insilos-db-secret', 'key': 'db-port'}}},
                                {'name': 'PGPASSWORD', 'valueFrom': {'secretKeyRef': {'name': 'insilos-db-secret', 'key': 'pg-superpass'}}},
                                {'name': 'MINIO_URL', 'valueFrom': {'secretKeyRef': {'name': 'insilos-minio-secret', 'key': 'url'}}},
                                {'name': 'MINIO_ACCESS', 'valueFrom': {'secretKeyRef': {'name': 'insilos-minio-secret', 'key': 'access-key'}}},
                                {'name': 'MINIO_SECRET', 'valueFrom': {'secretKeyRef': {'name': 'insilos-minio-secret', 'key': 'secret-key'}}},
                                {'name': 'INSILOS_TENANT_OPERATION_ID', 'value': str(operation.id)},

                                {'name': 'INSILOS_TENANT_SLUG', 'value': tenant.slug},
                                {'name': 'INSILOS_TENANT_NAME', 'value': tenant.name},
                                {'name': 'INSILOS_TENANT_DB_NAME', 'value': tenant.db_name},
                                {'name': 'INSILOS_TENANT_PRIMARY_DOMAIN', 'value': tenant.primary_domain},
                                {'name': 'INSILOS_TENANT_TEMPLATE', 'value': tenant.template_id.slug},
                                {'name': 'INSILOS_TENANT_ARTIFACT_URI', 'value': tenant.release_id.artifact_uri},
                                {'name': 'INSILOS_TENANT_ARTIFACT_SHA256', 'value': tenant.release_id.artifact_sha256},
                            ],
                        }],
                    },
                },
            },
        }

    def observed_state(self, job_name):
        url = f'{self.base_url}/apis/batch/v1/namespaces/{self.namespace}/jobs/{job_name}'
        response = requests.get(url, headers=self._headers(), verify=self.ca_path, timeout=10)
        if response.status_code == 404:
            return 'missing'
        response.raise_for_status()
        status = response.json().get('status', {})
        if status.get('active'):
            return 'active'
        if status.get('succeeded'):
            return 'complete'
        if status.get('failed'):
            return 'failed'
        return 'pending'

    def reconcile(self, operation):
        name = self.job_name(operation)
        url = f'{self.base_url}/apis/batch/v1/namespaces/{self.namespace}/jobs/{name}'
        kwargs = {'headers': self._headers(), 'verify': self.ca_path, 'timeout': 10}
        response = requests.get(url, **kwargs)
        if response.status_code == 200:
            return name
        if response.status_code != 404:
            response.raise_for_status()
        response = requests.post(url.rsplit('/', 1)[0], json=self.job(operation), **kwargs)
        if response.status_code not in (201, 409):
            response.raise_for_status()
        return name
