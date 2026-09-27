from datetime import datetime, timedelta
import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from ..models.project_project import _redact_error
from ..services import TenantReconciliationService


class TestTenantReconciliation(TransactionCase):

    def test_fault_matrix(self):
        now = datetime(2026, 8, 5, 12)
        snapshot = {
            'pg_databases': ['orphan_db', 'tenant_a'],
            'tenants': [
                {'id': 1, 'db_name': 'tenant_a', 'db_uuid': 'uuid-a', 'primary_domain': 'a.test', 'desired_state': 'provisioned', 'release_id': 10, 'artifact_sha256': 'a' * 64},
                {'id': 2, 'db_name': 'tenant_b', 'db_uuid': 'uuid-b', 'primary_domain': 'b.test', 'desired_state': 'provisioned', 'release_id': 20, 'artifact_sha256': 'b' * 64},
            ],
            'routes': {'a.test': 'wrong', 'b.test': 'uuid-b'},
            'projections': [{'id': 30, 'tenant_id': 1, 'database_name': 'wrong', 'domain': 'a.test'}],
            'artifacts': {'tenant_a': {'release_id': 10, 'artifact_sha256': 'wrong'}},
            'operations': [{'id': 40, 'state': 'running', 'since': now - timedelta(hours=25), 'job_name': 'job-40'}],
            'jobs': {'job-40': 'active'},
        }

        report = TenantReconciliationService().report(snapshot, now=now)

        self.assertTrue(report['report_only'])
        self.assertEqual([finding['class'] for finding in report['findings']], list(TenantReconciliationService.DRIFT_CLASSES))
        self.assertEqual([finding['status'] for finding in report['findings']], ['drift'] * 6)
        self.assertEqual([finding['count'] for finding in report['findings']], [1, 1, 1, 2, 2, 1])

    def test_inventory_preserves_unknown_and_legacy(self):
        snapshot = {
            'pg_databases': [], 'domains': [], 'tenants': [],
            'projections': [
                {'id': 1, 'tenant_id': None, 'database_name': 'old', 'domain': 'old.test', 'classification': 'legacy'},
                {'id': 2, 'tenant_id': None, 'database_name': 'mystery', 'domain': 'mystery.test', 'classification': 'unknown'},
            ],
        }

        report = TenantReconciliationService().inventory(snapshot)

        self.assertTrue(report['report_only'])
        self.assertEqual([row['classification'] for row in report['rows']], ['legacy', 'unknown'])
        self.assertEqual(report['summary'], {'legacy': 1, 'unknown': 1})

    def test_dispositions_preserve_raw_findings_and_count_actionable(self):
        snapshot = {'pg_databases': ['orphan'], 'tenants': [], 'projections': []}
        dispositions = [{'match': {'classification': 'unknown', 'database_name': 'orphan'}, 'decision': 'accepted'}]

        inventory = TenantReconciliationService().inventory(snapshot, dispositions)
        report = TenantReconciliationService().report(snapshot, dispositions=[{'match': {'class': 'pg_database_without_registry', 'database_name': 'orphan'}, 'decision': 'accepted'}])

        self.assertEqual(inventory['raw_summary'], {'unknown': 1})
        self.assertEqual((inventory['accepted_count'], inventory['actionable_count']), (1, 0))
        self.assertEqual(report['findings'][0]['details'], ['orphan'])
        self.assertEqual((report['accepted_count'], report['actionable_count']), (1, 0))

    def test_approved_pg_scope_separates_inventory_without_hiding_raw(self):
        pg_inventory = (
            [{'database_name': f'insilos_ind_{index}', 'category': 'blueprint_inventory'} for index in range(101)]
            + [{'database_name': f'insilos_test_{index}', 'category': 'infrastructure_telemetry'} for index in range(8)]
            + [{'database_name': f'insilos_tenant_{index}', 'category': 'tenant_candidate'} for index in range(19)]
        )
        snapshot = {'pg_inventory': pg_inventory, 'tenants': [], 'projections': [], 'operations': [],
                    'routes': {}, 'artifacts': {}, 'jobs': {}}
        dispositions = [{'match': {'class': 'pg_database_without_registry', 'database_name': f'insilos_tenant_{index}'},
                         'decision': 'approved'} for index in range(19)]

        report = TenantReconciliationService().report(snapshot, dispositions=dispositions)

        self.assertTrue(report['report_only'])
        self.assertEqual(len(report['raw_pg_inventory']), 128)
        self.assertEqual(len(report['blueprint_inventory']), 101)
        self.assertEqual(len(report['infrastructure_telemetry']), 8)
        self.assertEqual(report['findings'][0]['details'], [f'insilos_tenant_{index}' for index in sorted(range(19), key=lambda value: f'insilos_tenant_{value}')])
        self.assertEqual((report['accepted_count'], report['actionable_count']), (19, 0))

    def test_unknown_pg_category_remains_actionable(self):
        snapshot = {'pg_inventory': [{'database_name': 'insilos_mystery', 'category': 'not-approved'}],
                    'tenants': [], 'projections': [], 'operations': [], 'routes': {}, 'artifacts': {}, 'jobs': {}}

        report = TenantReconciliationService().report(snapshot)

        self.assertEqual(report['raw_pg_inventory'][0]['category'], 'unknown')
        self.assertEqual(report['findings'][0]['details'], ['insilos_mystery'])
        self.assertEqual(report['actionable_count'], 1)

    def test_explicit_unknown_reason_is_json_normalized(self):
        snapshot = {
            'pg_databases': [], 'tenants': [], 'projections': [], 'operations': [],
            'routes': {'values': None, 'reason': 'route probe unavailable'},
            'artifacts': {'values': None, 'reason': 'artifact observer unavailable'},
            'jobs': {'values': None, 'reason': 'cluster unavailable'},
        }
        report = TenantReconciliationService().report(snapshot)
        unknown = {finding['class']: finding['reason'] for finding in report['findings'] if finding['status'] == 'unknown'}
        self.assertEqual(unknown, {
            'domain_route_mismatch': 'route probe unavailable',
            'release_artifact_drift': 'artifact observer unavailable',
            'stale_operation_or_k8s_job': 'cluster unavailable',
        })
        json.dumps(report)

    def test_ui_error_redacts_secrets(self):
        message = _redact_error('postgresql://user:pass@db/x password=hunter2 token=abc123')
        self.assertNotIn('user:pass@db', message)
        self.assertNotIn('hunter2', message)
        self.assertNotIn('abc123', message)
        self.assertEqual(message.count('[REDACTED]'), 3)

    def test_preview_performs_zero_model_writes(self):
        snapshot = {'pg_databases': [], 'tenants': [], 'projections': [], 'operations': [], 'routes': {}, 'artifacts': {}, 'jobs': {}}
        model = self.env['project.project']
        with patch.object(type(model), '_tenant_reconciliation_snapshot', return_value=snapshot), \
             patch.object(type(self.env['insilos.tenant']), 'create', side_effect=AssertionError('tenant write')), \
             patch.object(type(model), 'create', side_effect=AssertionError('projection write')), \
             patch.object(type(model), 'write', side_effect=AssertionError('projection write')), \
             patch.object(type(model), 'unlink', side_effect=AssertionError('projection write')):
            action = model.action_sync_local_databases()

        self.assertEqual(action['tag'], 'display_notification')
        self.assertIn('"report_only": true', action['params']['message'])
