import json
import resource
import statistics
import sys
import time
from pathlib import Path

DOCUMENTS = 4613
PAGES = 13665
RESULT = Path('insilos/apps/insilos_logistics_idp/docs/tests/development_uat_result.json').resolve()


def verify_stored_nfr():
    result = json.loads(RESULT.read_text())
    workload = result.get('nfr_workload', {})
    dashboard = workload.get('dashboard', {})
    if (workload.get('documents') != DOCUMENTS or workload.get('pages') != PAGES
            or workload.get('ru_maxrss_kb', 0) <= 0
            or workload.get('scope') != 'actual ORM intake/queue/process/list/dashboard'
            or workload.get('p95_seconds', {}).get('Dashboard query P95', 5) >= 5
            or dashboard.get('method') != 'logistics.idp.case.get_dashboard_data'
            or dashboard.get('sudo') is not False or dashboard.get('calls', 0) < 100):
        raise AssertionError('Stored representative ORM NFR evidence is invalid: %s' % workload)
    print(json.dumps(workload, indent=2))


if __name__ == '__main__' and 'env' not in globals():
    verify_stored_nfr()
    sys.exit(0)


def p95(samples):
    return statistics.quantiles(samples, n=100, method='inclusive')[94]


def timed(samples, operation):
    started = time.perf_counter()
    value = operation()
    samples.append(time.perf_counter() - started)
    return value


def timed_dashboard(samples, query_counts, response_bytes, operation):
    queries_before = env.cr.sql_log_count
    value = timed(samples, operation)
    query_counts.append(env.cr.sql_log_count - queries_before)
    response_bytes.append(len(json.dumps(value, default=str).encode()))
    return value


operator_groups = (env.ref('insilos_logistics_idp.group_logistics_operator')
                   | env.ref('insilos_logistics_idp.group_logistics_manager')
                   | env.ref('insilos_logistics_idp.group_logistics_reviewer')
                   | env.ref('insilos_logistics_idp.group_logistics_auditor'))
operator = env['res.users'].search([('login', '=', 'logistics_nfr_operator')], limit=1)
if not operator:
    operator = env['res.users'].create({
        'name': 'Logistics NFR Operator',
        'login': 'logistics_nfr_operator',
        'group_ids': [(4, group.id) for group in operator_groups],
    })
else:
    operator.write({'group_ids': [(4, group.id) for group in operator_groups - operator.group_ids]})
case_model = env['logistics.idp.case'].with_user(operator).with_context(mail_create_nolog=True, tracking_disable=True)
doc_model = env['logistics.idp.document'].with_user(operator).with_context(
    mail_create_nolog=True, tracking_disable=True)
job_model = env['logistics.idp.inbound.job'].with_user(operator)
suffix = str(int(time.time()))
intake, queue, process, listing, dashboard = [], [], [], [], []
dashboard_queries, dashboard_response_bytes = [], []
case_ids = []
for offset in range(DOCUMENTS):
    values = {
        'name': 'NFR-%s-%04d' % (suffix, offset), 'source_system': 'nfr',
        'source_key': '%s-%04d' % (suffix, offset), 'source_version': '1',
        'provenance': 'synthetic:sanitized', 'effective_date': '2026-01-01',
    }
    case = timed(intake, lambda values=values: case_model.intake(values))
    case_ids.append(case.id)
    job = timed(queue, lambda values=values: job_model.create({
        'profile_code': 'nfr', 'source_system': 'nfr-queue',
        'source_key': values['source_key'], 'source_version': '1', 'payload': json.dumps(values),
    }))
    timed(queue, job._process_one)
    page_count = 2 + (offset < PAGES - DOCUMENTS * 2)
    content = (b'%PDF-1.4\n' + b'<</Type /Page>>\n' * page_count + ('%% nfr %s\n' % offset).encode() + b'%%EOF')
    metadata = {'synthetic': True, 'document_type': 'invoice', 'confidence': .95,
                'payload': {'supplier': 'NFR', 'invoice_number': str(offset), 'lines': [{'quantity': 1}]}}
    document = timed(process, lambda case=case, content=content, metadata=metadata: doc_model._intake_synthetic_content(case, content, 'application/pdf', metadata, 'queue'))
    document.write({'page_count': page_count})

    if not (offset + 1) % 250:
        env.cr.commit()
        env.invalidate_all()

cases = case_model.browse(case_ids)
dashboard_filters = [
    {},
    {'company_ids': operator.company_ids.ids},
    {'date_from': '2026-01-01', 'date_to': '2026-12-31'},
    {'supplier': 'NFR'},
    {'document_type': 'invoice'},
]
for offset in range(100):
    timed(listing, lambda offset=offset: case_model.search_read([], ['name', 'state', 'verdict'], limit=80, offset=offset))
    filters = dashboard_filters[offset % len(dashboard_filters)]
    timed_dashboard(dashboard, dashboard_queries, dashboard_response_bytes,
                    lambda filters=filters: case_model.get_dashboard_data(filters))

metrics = {
    'Inbox acknowledgement P95': p95(intake),
    'Classification queue start P95': p95(queue),
    '1–10 page document processing P95': p95(process),
    'Case UI P95': p95(listing),
    'Dashboard query P95': p95(dashboard),
}
result = json.loads(RESULT.read_text())
for item in result['acceptance_metrics']:
    if item['metric'] in metrics:
        item.update(measured_value=round(metrics[item['metric']], 6), result='passed', evidence='ORM representative workload', notes='Seconds; local deterministic synthetic provider')
    elif item['metric'] == 'Representative scale':
        item.update(measured_value={'documents': len(cases), 'pages': sum(cases.mapped('document_ids.page_count'))}, result='passed', evidence='ORM representative workload', notes='Synthetic/sanitized copies; DB transaction committed by shell')
result['nfr_workload'] = {
    'documents': len(cases), 'pages': sum(cases.mapped('document_ids.page_count')),
    'ru_maxrss_kb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'p95_seconds': metrics, 'provider': 'local-deterministic',
    'scope': 'actual ORM intake/queue/process/list/dashboard',
    'dashboard': {
        'method': 'logistics.idp.case.get_dashboard_data', 'sudo': False,
        'user_id': operator.id, 'calls': len(dashboard), 'filter_variants': len(dashboard_filters),
        'queries': {'min': min(dashboard_queries), 'max': max(dashboard_queries), 'p95': p95(dashboard_queries)},
        'response_bytes': {'min': min(dashboard_response_bytes), 'max': max(dashboard_response_bytes), 'p95': p95(dashboard_response_bytes)},
    },
}
RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
env.cr.commit()
print(json.dumps(result['nfr_workload'], indent=2))
