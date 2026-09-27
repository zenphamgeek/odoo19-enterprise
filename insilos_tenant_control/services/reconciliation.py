from collections import Counter
from datetime import datetime
from urllib.parse import urlparse


class TenantReconciliationService:
    DRIFT_CLASSES = (
        'pg_database_without_registry',
        'active_registry_missing_db',
        'domain_route_mismatch',
        'projection_missing_or_wrong_tenant',
        'release_artifact_drift',
        'stale_operation_or_k8s_job',
    )

    INVENTORY_CLASSES = ('duplicate', 'conflict', 'unlinked', 'unknown', 'legacy')
    PG_INVENTORY_CATEGORIES = ('tenant_candidate', 'blueprint_inventory', 'infrastructure_telemetry', 'unknown')

    @classmethod
    def _pg_inventory(cls, snapshot):
        inventory = snapshot.get('pg_inventory')
        if inventory is None:
            inventory = ({'database_name': name, 'category': 'unknown'} for name in snapshot.get('pg_databases', ()))
        rows = []
        for item in inventory:
            item = {'database_name': item, 'category': 'unknown'} if isinstance(item, str) else dict(item)
            category = item.get('category', 'unknown')
            item['category'] = category if category in cls.PG_INVENTORY_CATEGORIES else 'unknown'
            rows.append(item)
        return rows

    def inventory(self, snapshot, dispositions=()):
        tenants = snapshot.get('tenants', ())
        projections = snapshot.get('projections', ())
        tenant_by_id = {tenant['id']: tenant for tenant in tenants}
        db_counts = Counter(projection.get('database_name') for projection in projections if projection.get('database_name'))
        domain_counts = Counter(projection.get('domain') for projection in projections if projection.get('domain'))
        rows = []
        for projection in projections:
            tenant = tenant_by_id.get(projection.get('tenant_id'))
            classification = projection.get('classification') or 'unknown'
            if db_counts[projection.get('database_name')] > 1 or domain_counts[projection.get('domain')] > 1:
                status = 'duplicate'
            elif tenant and (projection.get('database_name') != tenant.get('db_name') or projection.get('domain') != tenant.get('primary_domain')):
                status = 'conflict'
            elif not tenant and projection.get('tenant_id'):
                status = 'conflict'
            elif not projection.get('tenant_id'):
                status = classification if classification in ('legacy', 'unknown') else 'unlinked'
            else:
                continue
            rows.append({
                'projection_id': projection['id'], 'tenant_id': projection.get('tenant_id'),
                'database_name': projection.get('database_name'), 'domain': projection.get('domain'),
                'classification': status, 'owner_id': projection.get('owner_id'),
                'reviewer_id': projection.get('reviewer_id'), 'evidence': projection.get('evidence'),
                'classified_at': projection.get('classified_at'),
            })
        projected_dbs = set(db_counts)
        tenant_dbs = {tenant['db_name'] for tenant in tenants}
        for db_name in sorted(set(snapshot.get('pg_databases', ())) - projected_dbs - tenant_dbs):
            rows.append({'projection_id': None, 'tenant_id': None, 'database_name': db_name, 'domain': None,
                         'classification': 'unknown', 'owner_id': None, 'reviewer_id': None,
                         'evidence': None, 'classified_at': None})
        projected_tenants = {projection.get('tenant_id') for projection in projections}
        for tenant in tenants:
            if tenant['id'] not in projected_tenants:
                rows.append({'projection_id': None, 'tenant_id': tenant['id'], 'database_name': tenant['db_name'],
                             'domain': tenant.get('primary_domain'), 'classification': 'unlinked', 'owner_id': None,
                             'reviewer_id': None, 'evidence': None, 'classified_at': None})
        raw_summary = dict(Counter(row['classification'] for row in rows))
        accepted = [row for row in rows if self._disposition_for(row, dispositions)]
        return {
            'report_only': True, 'rows': rows, 'summary': raw_summary, 'raw_summary': raw_summary,
            'accepted_count': len(accepted), 'actionable_count': len(rows) - len(accepted),
        }

    def report(self, snapshot, now=None, stale_after_hours=24, dispositions=()):
        now = now or datetime.now()
        tenants = {tenant['db_name']: tenant for tenant in snapshot.get('tenants', ())}
        active = {name: tenant for name, tenant in tenants.items() if tenant['desired_state'] == 'provisioned'}
        raw_pg_inventory = self._pg_inventory(snapshot)
        pg_names = {item['database_name'] for item in raw_pg_inventory}
        tenant_candidates = {item['database_name'] for item in raw_pg_inventory if item['category'] in ('tenant_candidate', 'unknown')}
        blueprint_inventory = [item for item in raw_pg_inventory if item['category'] == 'blueprint_inventory']
        infrastructure_telemetry = [item for item in raw_pg_inventory if item['category'] == 'infrastructure_telemetry']
        projections = snapshot.get('projections', ())
        routes, routes_reason = self._observed(snapshot.get('routes'))
        artifacts, artifacts_reason = self._observed(snapshot.get('artifacts'))
        jobs, jobs_reason = self._observed(snapshot.get('jobs'))

        findings = []
        self._add(findings, self.DRIFT_CLASSES[0], sorted(tenant_candidates - set(tenants)))
        self._add(findings, self.DRIFT_CLASSES[1], sorted(set(active) - pg_names))

        if routes is None:
            self._add(findings, self.DRIFT_CLASSES[2], (), 'unknown', routes_reason)
        else:
            mismatches = [
                {'tenant_id': tenant['id'], 'domain': tenant['primary_domain'], 'expected_db_uuid': tenant['db_uuid'],
                 'actual_db_uuid': routes.get(tenant['primary_domain'])}
                for tenant in active.values()
                if routes.get(tenant['primary_domain']) != tenant['db_uuid']
            ]
            self._add(findings, self.DRIFT_CLASSES[2], mismatches)

        by_tenant = {}
        for projection in projections:
            by_tenant.setdefault(projection.get('tenant_id'), []).append(projection)
        projection_drift = []
        for db_name, tenant in active.items():
            linked = by_tenant.get(tenant['id'], ())
            if len(linked) != 1 or linked[0].get('database_name') != db_name or linked[0].get('domain') != tenant['primary_domain']:
                projection_drift.append({'tenant_id': tenant['id'], 'expected_db': db_name, 'projection_ids': [item['id'] for item in linked]})
        projection_drift.extend(
            {'projection_id': projection['id'], 'tenant_id': projection.get('tenant_id')}
            for projection in projections
            if projection.get('tenant_id') and projection.get('tenant_id') not in {tenant['id'] for tenant in tenants.values()}
        )
        self._add(findings, self.DRIFT_CLASSES[3], projection_drift)

        if artifacts is None:
            self._add(findings, self.DRIFT_CLASSES[4], (), 'unknown', artifacts_reason)
        else:
            artifact_drift = []
            for db_name, tenant in active.items():
                actual = artifacts.get(db_name)
                if not actual or actual.get('release_id') != tenant['release_id'] or actual.get('artifact_sha256') != tenant['artifact_sha256']:
                    artifact_drift.append({'tenant_id': tenant['id'], 'db_name': db_name, 'actual': actual})
            self._add(findings, self.DRIFT_CLASSES[4], artifact_drift)

        stale = []
        for operation in snapshot.get('operations', ()):
            if operation['state'] not in ('queued', 'running'):
                continue
            age = (now - operation['since']).total_seconds() / 3600
            job_state = jobs.get(operation.get('job_name')) if jobs is not None and operation.get('job_name') else None
            if age > stale_after_hours or operation['state'] == 'running' and jobs is not None and job_state not in ('active', 'complete'):
                stale.append({'operation_id': operation['id'], 'age_hours': round(age, 1), 'job_state': job_state})
        self._add(findings, self.DRIFT_CLASSES[5], stale, 'unknown' if jobs is None and not stale else None,
                  jobs_reason if jobs is None and not stale else None)
        for finding in findings:
            finding['accepted_count'] = sum(bool(self._disposition_for({'class': finding['class'], **detail} if isinstance(detail, dict) else {'class': finding['class'], 'database_name': detail}, dispositions)) for detail in finding['details'])
            finding['actionable_count'] = finding['count'] - finding['accepted_count']
        raw_summary = {status: sum(item['status'] == status for item in findings) for status in ('ok', 'drift', 'unknown')}
        return {
            'report_only': True, 'summary': raw_summary, 'raw_summary': raw_summary,
            'accepted_count': sum(item['accepted_count'] for item in findings),
            'actionable_count': sum(item['actionable_count'] for item in findings),
            'authoritative_tenant_drift': findings,
            'blueprint_inventory': blueprint_inventory,
            'infrastructure_telemetry': infrastructure_telemetry,
            'raw_pg_inventory': raw_pg_inventory,
            'findings': findings,
        }

    @staticmethod
    def _disposition_for(row, dispositions):
        return next((item for item in dispositions if all(row.get(key) == value for key, value in item.get('match', {}).items())), None)

    @staticmethod
    def _observed(value):
        if isinstance(value, dict) and set(value) == {'values', 'reason'}:
            return value['values'], value['reason']
        return value, 'observer unavailable' if value is None else None

    @staticmethod
    def projection_domain(database_url):
        return (urlparse(database_url or '').hostname or '').lower()

    @staticmethod
    def _add(findings, drift_class, details, status=None, reason=None):
        findings.append({
            'class': drift_class,
            'status': status or ('drift' if details else 'ok'),
            'count': len(details),
            'details': list(details),
            'reason': reason,
        })
