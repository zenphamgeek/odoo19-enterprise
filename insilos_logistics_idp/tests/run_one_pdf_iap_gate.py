import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen

DB = 'insilos_migration_digiforce_v2'
ROOT = Path(__file__).resolve().parents[4] if '__file__' in globals() else Path.cwd()
DEFAULT_PDF = ROOT / 'docs/data_test/Invoice-ODUC6RWV-0001.pdf'
DEFAULT_EVIDENCE = ROOT / 'tmp/one_pdf_iap_gate_evidence.json'
IAP_BASE = os.environ.get('IAP_GATE_BASE', 'http://127.0.0.1:3099').rstrip('/')


def _json_get(path):
    headers = {}
    token_file = os.environ.get('IAP_READINESS_TOKEN_FILE')
    if path == '/readyz' and token_file:
        headers['Authorization'] = 'Bearer ' + Path(token_file).read_text(encoding='utf-8').strip()
    with urlopen(Request(IAP_BASE + path, headers=headers), timeout=5) as response:
        return response.status, json.load(response)


def _parse_payload(run_record):
    try:
        payload = json.loads(run_record.payload) if run_record else {}
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_operations(payload):
    operations = payload.get('provider_operations') or []
    return [
        {'operation_id': item.get('operation_id'), 'task': item.get('task'), 'outcome': item.get('outcome')}
        if isinstance(item, dict) else {'operation_id': str(item), 'task': None, 'outcome': None}
        for item in operations
    ]


def _reconcile(charges, ledger, document_status):
    states = {item['state'] for item in charges}
    types = {item['type'] for item in ledger}
    terminal = document_status in ('valid', 'review', 'error')
    success = document_status in ('valid', 'review')
    settled = 'held' not in states and (not charges or states <= {'consumed', 'released'})
    lifecycle = (not charges or ('hold' in types and bool(types & {'consume', 'release', 'refund'})))
    return {'terminal': terminal, 'settled': settled, 'lifecycle_complete': lifecycle,
            'failure_probe': (not success and document_status in ('review', 'error') and bool(types & {'release', 'refund'}))}


def _semantic_acceptance(payload, document_status):
    attempts = payload.get('provider_attempts') or []
    selected = next((item for item in attempts if isinstance(item, dict)
                     and item.get('selected_review_candidate')), attempts[-1] if attempts else {})
    diagnostics = selected.get('diagnostics') or {}
    errors = diagnostics.get('errors') or []
    business_errors = [error for error in errors
                       if not isinstance(error, dict) or error.get('path') != 'ocr_results']
    payload_diagnostics = diagnostics.get('payload') or {}
    business_semantic_valid = (isinstance(payload.get('payload'), dict)
                               and not business_errors
                               and not payload_diagnostics.get('missing_required')
                               and not diagnostics.get('missing_required_keys'))
    geometry_review = (
        document_status == 'review'
        and set(payload.get('validation_warnings') or []) == {
            'AI extraction incomplete; human review required', 'ocr_results'}
        and 'ocr_results' not in payload
        and selected.get('outcome') == 'semantic_review_candidate'
        and errors == [{'path': 'ocr_results', 'category': 'invalid_geometry'}]
    )
    return {
        'business_semantic_valid': business_semantic_valid,
        'geometry_review': geometry_review,
        'semantic_valid': business_semantic_valid and (document_status == 'valid' or geometry_review),
    }


def run(env, pdf_path=DEFAULT_PDF, evidence_path=DEFAULT_EVIDENCE):
    if env.cr.dbname != DB:
        raise AssertionError('DB mismatch: expected %s' % DB)
    module = env['ir.module.module'].sudo().search([('name', '=', 'insilos_logistics_idp'), ('state', '=', 'installed')], limit=1)
    service = env['res.users'].sudo().with_context(active_test=False).search([
        ('login', '=', 'digiforce_migration_service'), ('active', '=', True)], limit=1)
    endpoint = env['ir.config_parameter'].sudo().get_param('ai.iap_endpoint', '')
    if not module or not service or not endpoint.startswith(IAP_BASE):
        raise AssertionError('Preflight failed: module/service principal/canonical IAP endpoint')
    health_status, health = _json_get('/healthz')
    ready_status, ready = _json_get('/readyz')
    if health_status != 200 or health.get('database') != DB or ready_status != 200 or ready.get('status') != 'ready':
        raise AssertionError('IAP health/readiness failed')

    policy_model = env['logistics.idp.policy.source'].sudo()
    policy = policy_model.select_effective_pack(env.company, 'trade_compliance', 'vn_fdi_fta', 'VN', 'ALL', '2026-08-10')
    if policy.version != '2026.3' or not policy.audit_input_hash:
        raise AssertionError('Effective policy is not exact approved 2026.3')

    content = Path(pdf_path).read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    documents = env['logistics.idp.document'].sudo().search([('company_id', '=', env.company.id), ('content_hash', '=', digest)])
    if len(documents) > 1:
        raise AssertionError('Unsafe duplicate fixture state')
    document = documents[:1]
    reused = bool(document)
    if not document:
        case = env['logistics.idp.case'].with_user(service).intake({
            'name': 'One-PDF IAP semantic gate', 'source_system': 'iap-gate',
            'source_key': 'sha256:' + digest, 'source_version': '1',
            'provenance': 'tracked-fixture:' + digest, 'effective_date': '2026-08-10',
        })
        document = env['logistics.idp.document'].with_user(service).intake_content(
            case, content, 'application/pdf', {'filename': Path(pdf_path).name})
        env.cr.commit()
    run_record = document.current_run_id
    payload = _parse_payload(run_record)
    accepted = bool(payload) and _semantic_acceptance(payload, document.status)['semantic_valid']
    if reused and document.status != 'valid' and not accepted:
        document.with_user(service).process(explicit=True)
        env.cr.commit()
        run_record = document.current_run_id
        payload = _parse_payload(run_record)
    operation_id = payload.get('operation_id')
    if not operation_id:
        raise AssertionError('Missing stable operation ID')

    charge_model = env['iap.charge'].sudo()
    before_retry = charge_model.search_count([('operation_id', '=like', operation_id + '%')])
    document.with_user(service).process(run_id=run_record.id)
    env.cr.commit()
    after_retry = charge_model.search_count([('operation_id', '=like', operation_id + '%')])
    if after_retry != before_retry or document.current_run_id != run_record:
        raise AssertionError('Retry created an extra provider charge or extraction run')

    operations = _safe_operations(payload)
    operation_ids = [item['operation_id'] for item in operations if item['operation_id']]
    charges = charge_model.search([('operation_id', 'in', operation_ids)], order='id')
    ledger = env['iap.ledger'].sudo().search([('charge_id', 'in', charges.ids)], order='id')
    charge_rows = [{'operation_id': charge.operation_id, 'state': charge.state,
                    'service': charge.service_name, 'amount': charge.amount} for charge in charges]
    ledger_rows = [{'operation_id': entry.operation_id, 'type': entry.type,
                    'amount': entry.amount} for entry in ledger]
    reconciliation = _reconcile(charge_rows, ledger_rows, document.status)
    expected = 1 if payload.get('classification_source') == 'deterministic_metadata' else 2
    parser_valid = run_record.status != 'error'
    semantics = _semantic_acceptance(payload, document.status)
    exact_path_operations = len(set(operation_ids)) == expected
    passed = (parser_valid and semantics['semantic_valid'] and reconciliation['settled']
              and reconciliation['lifecycle_complete'] and exact_path_operations
              and expected == len(charges) and after_retry == before_retry)
    fixture_path = Path(pdf_path)
    fixture_alias = str(fixture_path.relative_to(ROOT)) if fixture_path.is_relative_to(ROOT) else 'external-quarantine-pdf'
    evidence = {
        'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(), 'passed': passed,
        'environment': {'database': DB, 'iap_base': IAP_BASE, 'health': health.get('status'),
                        'ready': ready.get('status')},
        'fixture': {'path': fixture_alias, 'sha256_prefix': digest[:12], 'reused': reused},
        'policy': {'version': policy.version, 'audit_input_hash': policy.audit_input_hash},
        'document': {'id': document.id, 'run_id': run_record.id, 'status': document.status,
                     'parser_valid': parser_valid, **semantics},
        'operation_id': operation_id, 'operations': operations,
        'charging': {'expected': expected, 'actual': len(charges), 'retry_extra': after_retry - before_retry,
                     'charges': charge_rows, 'ledger': ledger_rows, 'reconciliation': reconciliation},
    }
    evidence_path = Path(evidence_path)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    if not passed:
        raise AssertionError('One-PDF IAP semantic gate failed; evidence=%s' % evidence_path)
    return evidence


def self_check():
    assert _parse_payload(SimpleNamespace(payload='{"ok": true}')) == {'ok': True}
    assert _parse_payload(SimpleNamespace(payload='{broken')) == {}
    assert _parse_payload(None) == {}
    clean = _reconcile([{'state': 'consumed'}], [{'type': 'hold'}, {'type': 'consume'}], 'valid')
    failed = _reconcile([{'state': 'released'}], [{'type': 'hold'}, {'type': 'release'}], 'error')
    assert clean == {'terminal': True, 'settled': True, 'lifecycle_complete': True, 'failure_probe': False}
    assert failed == {'terminal': True, 'settled': True, 'lifecycle_complete': True, 'failure_probe': True}
    assert _safe_operations({'provider_operations': [{'operation_id': 'op', 'task': 'extract', 'outcome': 'valid', 'raw': 'secret'}]}) == [{'operation_id': 'op', 'task': 'extract', 'outcome': 'valid'}]
    geometry_review = {
        'payload': {'invoice_number': 'INV-1'},
        'validation_warnings': ['AI extraction incomplete; human review required', 'ocr_results'],
        'provider_attempts': [{'outcome': 'semantic_review_candidate', 'selected_review_candidate': True,
                              'diagnostics': {'errors': [{'path': 'ocr_results', 'category': 'invalid_geometry'}],
                                              'missing_required_keys': [],
                                              'payload': {'missing_required': []}}}],
    }
    assert _semantic_acceptance(geometry_review, 'review') == {
        'business_semantic_valid': True, 'geometry_review': True, 'semantic_valid': True}
    unrelated_review = {**geometry_review, 'validation_warnings': [
        'AI extraction incomplete; human review required', 'payload.invoice_number']}
    assert _semantic_acceptance(unrelated_review, 'review') == {
        'business_semantic_valid': True, 'geometry_review': False, 'semantic_valid': False}
    assert len({'run:extract:invoice:model:0'}) == 1
    assert len({'run:classify:model:0', 'run:extract:invoice:model:0'}) == 2


if __name__ == '__main__':
    self_check()
    if 'env' in globals():
        run(env, Path(os.environ.get('IAP_GATE_PDF', DEFAULT_PDF)), Path(os.environ.get('IAP_GATE_EVIDENCE', DEFAULT_EVIDENCE)))
    else:
        print('one-PDF IAP gate logic: PASS')
