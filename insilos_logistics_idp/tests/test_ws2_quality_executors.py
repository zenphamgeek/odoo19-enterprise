#!/usr/bin/env python3
"""WS2 direct-executor harness — pure Python, no ORM/DB.

Runs deterministic quality checks directly against pure executor functions
without requiring a running server, database connection, or Insilos ORM. Every check
mirrors one registered test in test_ws2_capabilities.py so the same
assertion runs without a database.

Run: python3 insilos/apps/insilos_logistics_idp/tests/test_ws2_quality_executors.py
"""
import ast
import hashlib
import importlib
import json
import re
import sys
import types
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
SERVICES_DIR = MODULE / 'services'

services = types.ModuleType('services')
services.__path__ = [str(SERVICES_DIR)]
sys.modules['services'] = services
schemas = importlib.import_module('services.document_schemas')
processor = importlib.import_module('services.document_processor')

DOCUMENT_TYPES = schemas.DOCUMENT_TYPES
normalize_decimal = schemas.normalize_decimal
validate = schemas.validate
SUPPORTED_MIMES = processor.SUPPORTED_MIMES
MAX_BYTES = processor.MAX_BYTES
ProcessingError = processor.ProcessingError
LocalDocumentProcessor = processor.LocalDocumentProcessor
IAPDocumentProcessor = processor.IAPDocumentProcessor
deterministic_classify = processor.deterministic_classify
batch_structure = processor.batch_structure
classification_response_schema = processor.classification_response_schema
extraction_response_schema = processor.extraction_response_schema
extraction_template_contract = processor.extraction_template_contract
normalize_ocr_results = processor.normalize_ocr_results
_decode_provider_content = processor._decode_provider_content
_normalized_text = processor._normalized_text
_semantic_diagnostics = processor._semantic_diagnostics

DECISION_VERBS = r'\b(?:match|approve|reject|decide|pass|fail|compliant|authorize|block)\b'
MINIMAL_PDF = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
SERVICE_PATHS = (SERVICES_DIR / 'document_processor.py', SERVICES_DIR / 'document_schemas.py')

VALID_INVOICE_ENVELOPE = {
    'document_type': 'invoice', 'confidence': .95,
    'payload': {
        'supplier': 'SUP', 'invoice_number': 'INV-1', 'supplier_address': None,
        'buyer_name': None, 'total_gross': '12', 'total_quantity': None, 'currency': 'VND',
        'document_date': '2026-07-31',
        'lines': [{
            'description': 'goods', 'material_code': None, 'quantity': 1, 'unit_price': 12,
            'value': None, 'uom': 'PCE', 'currency': None, 'price_per': None,
            'quantity_1': None, 'quantity_2': None, 'remaining_quantity': None, 'hs_code': None,
        }],
    },
    'source_spans': [{'page': 1, 'text': 'INV-1'}],
    'ocr_results': {'words': {}, 'numbers': {}, 'dates': {}},
}


def _module_level_names(tree):
    names = set()

    def visit(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return
        if isinstance(node, ast.Name):
            names.add(node.id)
        for child in ast.iter_child_nodes(node):
            visit(child)

    for node in tree.body:
        visit(node)
    return names


def _raises_message(func, message):
    try:
        func()
    except ProcessingError as exc:
        assert message in str(exc), (str(exc), message)
        return exc
    raise AssertionError('expected ProcessingError containing %r' % message)


def exec_ai_001():
    classified = deterministic_classify({'filename': 'purchase order 001.pdf'})
    assert (classified['type'], classified['confidence'], classified['reason']) == (
        'purchase_order', .95, 'unique filename phrase'), classified
    schema = extraction_response_schema('purchase_order')['json_schema']['schema']
    assert 'lines' in schema['properties']['payload']['properties']
    assert _normalized_text('HÓA ĐƠN GIÁ TRỊ GIA TĂNG') == 'hoa don gia tri gia tang'
    decoded, diagnostics = _decode_provider_content('{"document_type": "invoice", "confidence": 1}')
    assert decoded == {'document_type': 'invoice', 'confidence': 1}
    assert diagnostics['content_type'] == 'string'


def exec_ai_002():
    classification = classification_response_schema()['json_schema']['schema']
    assert set(classification['properties']) == {'document_type', 'confidence'}
    assert not classification['additionalProperties']
    extraction = extraction_response_schema('purchase_order')['json_schema']['schema']
    assert set(extraction['properties']) == {
        'document_type', 'confidence', 'payload', 'source_spans', 'ocr_results'}
    assert not extraction['additionalProperties']
    template = extraction_template_contract('purchase_order')
    assert re.search(DECISION_VERBS, template['prompt']) is None
    try:
        validate('invoice', {'supplier': 'S'})
        raise AssertionError('validate should raise on missing fields')
    except ValueError:
        pass


def exec_ai_004():
    schema = extraction_response_schema('purchase_order')['json_schema']['schema']
    assert 'confidence' in schema['required']
    assert schema['properties']['confidence'] == {'type': 'number', 'minimum': 0, 'maximum': 1}
    assert 'confidence' not in schema['properties']['payload']['properties']['lines']['items']['properties']
    incomplete = {**VALID_INVOICE_ENVELOPE, 'payload': {
        **VALID_INVOICE_ENVELOPE['payload'], 'invoice_number': None}}
    result = LocalDocumentProcessor().process(MINIMAL_PDF, 'application/pdf',
                                              {'provider_response': incomplete, 'allow_review': True})
    assert 'payload.invoice_number' in result['validation_warnings']
    assert result['confidence'] == .95
    _raises_message(lambda: LocalDocumentProcessor().process(MINIMAL_PDF, 'application/pdf', {
        'provider_response': {**VALID_INVOICE_ENVELOPE, 'confidence': 1.5}}), 'invalid confidence')


def exec_ai_008():
    assert {'application/pdf', 'image/png', 'image/jpeg'} <= SUPPORTED_MIMES
    processor_obj = LocalDocumentProcessor()
    png = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
    for content, mimetype in ((MINIMAL_PDF, 'application/pdf'), (png, 'image/png'), (jpeg, 'image/jpeg')):
        processor_obj._validate_binary(content, mimetype)
    for content, mimetype, message in (
            (b'%PDF-1.4\n/Encrypt 1 0 R\n%%EOF', 'application/pdf', 'encrypted PDF'),
            (b'%PDF-1.4\n<</Type /Page>>\n/JavaScript 1 0 R\n%%EOF', 'application/pdf', 'unsafe PDF active content'),
            (b'%PDF-MALFORMED-SYNTHETIC', 'application/pdf', 'malformed PDF structure'),
            (b'hello world', 'application/pdf', 'MIME and magic signature mismatch'),
            (b'\x89PNG\r\n\x1a\nshort', 'image/png', 'malformed PNG structure'),
            (b'%PDF-' + b'x' * MAX_BYTES, 'application/pdf', 'invalid document size'),
            (b'x', 'application/zip', 'unsupported MIME')):
        _raises_message(lambda c=content, m=mimetype: processor_obj._validate_binary(c, m), message)


def exec_ai_009():
    assert _normalized_text('HÓA ĐƠN GIÁ TRỊ GIA TĂNG') == _normalized_text('hoa don gia tri gia tang')
    assert _normalized_text('Đường số 1') == 'duong so 1'
    assert deterministic_classify({'filename': 'Hóa đơn GTGT 001.pdf'})['type'] == 'invoice'
    assert deterministic_classify({'filename': 'VAT Invoice 001.pdf'})['type'] == 'invoice'


def exec_nfr_011():
    error = _raises_message(lambda: _decode_provider_content('{"payload": "abc'), 'invalid provider JSON')
    diagnostics = error.diagnostics
    for key in ('error_class', 'json_error', 'truncation_category', 'wrapper_category',
                'first_character_class', 'last_character_class', 'empty'):
        assert key in diagnostics, (key, diagnostics)
    assert diagnostics['error_class'] == 'JSONDecodeError'
    assert diagnostics['json_error']['category'] == 'unterminated'
    assert diagnostics['errors'] == [{'path': '$', 'category': 'invalid_json'}]
    semantic = _semantic_diagnostics(VALID_INVOICE_ENVELOPE, 'invoice')
    assert semantic['errors'] == []
    assert 'type_map' in semantic
    assert 'reason' in deterministic_classify({'filename': 'packing list.pdf'})


def exec_srs_13():
    classified = deterministic_classify({'filename': 'purchase order 001.pdf'})
    assert classified['type'] == 'purchase_order'
    schema = extraction_response_schema(classified['type'])['json_schema']['schema']
    assert not schema['additionalProperties']
    assert not schema['properties']['payload']['additionalProperties']
    assert not schema['properties']['payload']['properties']['lines']['items']['additionalProperties']
    envelope = {
        'document_type': 'purchase_order', 'confidence': .95,
        'payload': {
            'supplier': 'SUP', 'supplier_address': 'ADDR', 'supplier_number': 'S-1',
            'po_reference': 'PO-1', 'total_value': '100', 'document_date': '2026-07-31',
            'currency': 'VND',
            'lines': [{'description': 'goods', 'quantity': 1, 'unit_price': 2}],
        },
        'source_spans': [], 'ocr_results': {'words': {}, 'numbers': {}, 'dates': {}},
    }
    assert _semantic_diagnostics(envelope, 'purchase_order')['errors'] == []
    _raises_message(lambda: _decode_provider_content('not json'), 'invalid provider JSON')


def exec_srs_16():
    manifest = [
        {'document_type': 'purchase_order'}, {'document_type': 'purchase_order'},
        {'document_type': 'draft_vat_invoice'}, {'document_type': 'main_vat_invoice'},
    ]
    structure = batch_structure(manifest)
    assert structure['duplicates'] == ['purchase_order'], structure
    assert structure['present'] == ['purchase_order', 'vat_invoice'], structure
    assert batch_structure([{'document_type': 'purchase_order'},
                            {'document_type': 'main_vat_invoice'}])['duplicates'] == []
    processor_obj = LocalDocumentProcessor()
    first = processor_obj.process(MINIMAL_PDF, 'application/pdf',
                                  {'provider_response': VALID_INVOICE_ENVELOPE})
    second = processor_obj.process(MINIMAL_PDF, 'application/pdf',
                                   {'provider_response': VALID_INVOICE_ENVELOPE})
    assert first == second
    assert first['raw_response_hash'] == hashlib.sha256(json.dumps(
        VALID_INVOICE_ENVELOPE, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def exec_srs_23():
    policy = {'horizontal': {'classification': {'thresholds': {'strong_filename': .99}}}}
    classified = deterministic_classify({'filename': 'packing list.pdf', 'idp_policy': policy})
    assert classified['confidence'] == .99
    schema = extraction_response_schema('invoice')['json_schema']['schema']
    assert not schema['additionalProperties']
    assert not schema['properties']['payload']['additionalProperties']
    _raises_message(lambda: LocalDocumentProcessor().process(
        b'%PDF-1.4\n/Encrypt 1 0 R\n%%EOF', 'application/pdf',
        {'provider_response': VALID_INVOICE_ENVELOPE}), 'encrypted PDF')
    _raises_message(lambda: _decode_provider_content('{"payload":'), 'invalid provider JSON')
    processor_obj = LocalDocumentProcessor()
    assert processor_obj.process(MINIMAL_PDF, 'application/pdf',
                                 {'provider_response': VALID_INVOICE_ENVELOPE}) == \
           processor_obj.process(MINIMAL_PDF, 'application/pdf',
                                 {'provider_response': VALID_INVOICE_ENVELOPE})


def exec_srs_doc_9():
    required = {
        'purchase_order', 'po_snapshot', 'draft_vat_invoice', 'main_vat_invoice', 'sales_invoice',
        'commercial_invoice', 'packing_list', 'bill_of_lading', 'export_declaration_draft',
        'export_declaration_final', 'import_declaration', 'master_data', 'dsnavl', 'sap_erp_output',
        'e13', 'e15', 'shipping_plan', 'gate_pass',
    }
    assert required <= set(DOCUMENT_TYPES)
    for document_type in DOCUMENT_TYPES:
        schema = extraction_response_schema(document_type)['json_schema']['schema']
        assert schema['properties']['document_type']['enum'] == [document_type], document_type
    assert batch_structure([{'document_type': 'draft_vat_invoice'},
                            {'document_type': 'main_vat_invoice'}])['present'] == ['vat_invoice']
    try:
        validate('unknown', {})
        raise AssertionError('validate should raise on unknown type')
    except ValueError:
        pass


def exec_va_01():
    source = (MODULE / 'models' / 'logistics_idp.py').read_text()
    assert "_inherit = ['extract.mixin.with.words']" in source
    assert (MODULE / 'docs' / 'MODEL_REUSE_MAP.md').is_file()


def exec_va_02():
    policy = {'horizontal': {'classification': {
        'aliases': {'purchase_order': [r'\bdon\s+mua\b']}, 'thresholds': {'strong_filename': .98}}}}
    classified = deterministic_classify({'filename': 'Don mua 001.pdf', 'idp_policy': policy})
    assert (classified['type'], classified['confidence']) == ('purchase_order', .98), classified
    for path in SERVICE_PATHS:
        assert re.search(r'\b(?:if|elif)\b[^\n]*\.name\s*==', path.read_text()) is None, path


def exec_va_03():
    template = extraction_template_contract('purchase_order')
    assert re.search(DECISION_VERBS, template['prompt']) is None
    try:
        validate('purchase_order', {'supplier': 'S', 'lines': []})
        raise AssertionError('validate should raise on missing fields')
    except ValueError as exc:
        assert 'missing fields' in str(exc)


def exec_va_04():
    payload = {'supplier': 'SUP', 'invoice_number': 'INV-1',
               'lines': [{'quantity': 1, 'unit_price': 2}]}
    assert normalize_decimal('1234.5') == '1234.5'
    assert normalize_decimal(2) == '2'
    try:
        normalize_decimal(True)
        raise AssertionError('normalize_decimal should reject bool')
    except ValueError:
        pass
    assert validate('invoice', payload) == validate('invoice', payload)
    metadata = {'filename': 'purchase order 001.pdf'}
    assert deterministic_classify(metadata) == deterministic_classify(metadata)
    assert _normalized_text('Đường 1') == _normalized_text('Đường 1')


def exec_va_05():
    processor_obj = LocalDocumentProcessor()
    result = processor_obj.process(MINIMAL_PDF, 'application/pdf',
                                   {'provider_response': VALID_INVOICE_ENVELOPE})
    assert result['raw_response_hash'] == hashlib.sha256(json.dumps(
        VALID_INVOICE_ENVELOPE, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    replay = processor_obj.process(MINIMAL_PDF, 'application/pdf',
                                   {'provider_response': VALID_INVOICE_ENVELOPE})
    assert result == replay


def exec_va_06():
    data_dir = MODULE / 'data'
    for name in ('logistics_idp_data.xml', 'logistics_idp_policy_demo.xml'):
        assert 'noupdate="1"' in (data_dir / name).read_text(), name
    onboarding = (data_dir / 'logistics_idp_onboarding.xml').read_text()
    assert set(re.findall(r'model="([^"]+)"', onboarding)) <= {
        'onboarding.onboarding.step', 'onboarding.onboarding'}
    for directory in ('models', 'services'):
        for path in sorted((MODULE / directory).glob('*.py')):
            assert 'env' not in _module_level_names(ast.parse(path.read_text())), path


def exec_va_07():
    default = extraction_template_contract('invoice')
    assert (default['version'], default['schema_version']) == ('logistics-ocr-v7', '11')
    assert len(default['hash']) == 64
    policy = {'horizontal': {'extraction': {'templates': {
        'default': {'version': 'invoice-v2', 'schema_version': '9',
                    'prompt': 'Extract {document_type}. Contract: {schema}.'}}}}}
    configured = extraction_template_contract('invoice', policy)
    assert configured['version'] == 'invoice-v2'
    assert configured['hash'] != default['hash']
    try:
        extraction_template_contract('invoice', {'horizontal': {'extraction': {
            'templates': {'default': 'not-a-dict'}}}})
        raise AssertionError('extraction_template_contract should reject non-dict template')
    except ValueError:
        pass


def exec_va_08():
    processor_obj = LocalDocumentProcessor()
    metadata = {'provider_response': VALID_INVOICE_ENVELOPE}
    first = processor_obj.process(MINIMAL_PDF, 'application/pdf', metadata)
    second = processor_obj.process(MINIMAL_PDF, 'application/pdf',
                                   {**metadata, 'filename': 'different-name.pdf'})
    assert first == second
    assert batch_structure([{'document_type': 'purchase_order'},
                            {'document_type': 'purchase_order'}])['duplicates'] == ['purchase_order']


def exec_va_09():
    schema = extraction_response_schema('purchase_order')['json_schema']['schema']
    payload_schema = schema['properties']['payload']
    assert 'currency' in payload_schema['required']
    line_schema = payload_schema['properties']['lines']['items']
    for field in ('uom', 'price_per', 'quantity', 'unit_price'):
        assert field in line_schema['required'], field
    assert line_schema['properties']['quantity'] == {'type': ['number', 'string', 'null']}
    normalized = validate('purchase_order', {
        'supplier': 'S', 'supplier_address': 'ADDR', 'supplier_number': 'S-1', 'po_reference': 'PO-1',
        'total_value': '100', 'document_date': '2026-07-31', 'currency': 'VND',
        'lines': [{'quantity': '0.10', 'unit_price': '1', 'uom': 'PCE', 'price_per': None}],
    })
    assert normalized['lines'][0]['uom'] == 'PCE'
    assert normalized['lines'][0]['quantity'] == '0.10'


def exec_va_10():
    error = ProcessingError('human message', {'errors': [{'path': '$', 'category': 'x'}]})
    assert (str(error), error.diagnostics['errors']) == (
        'human message', [{'path': '$', 'category': 'x'}])
    caught = _raises_message(lambda: _decode_provider_content('{"a":'), 'invalid provider JSON')
    assert caught.diagnostics['errors'] == [{'path': '$', 'category': 'invalid_json'}]


def exec_ocr_geometry():
    geometry = {
        'words': {'0': [{'content': 'INV-1', 'coords': [.5, .25, .2, .1, 0]}]},
        'numbers': {}, 'dates': {},
    }
    schema = extraction_response_schema('invoice')['json_schema']['schema']['properties']['ocr_results']
    assert not schema['additionalProperties']
    assert set(schema['properties']) == {'words', 'numbers', 'dates'}
    assert normalize_ocr_results(geometry) == geometry
    for invalid in ({'words': {}, 'numbers': {}},
                    {'words': {'0': [{'content': 'x', 'coords': [0, 0, 0, 0, float('nan')]}]}, 'numbers': {}, 'dates': {}},
                    {'words': {'0': [{'content': 'x', 'coords': [0, 0, 0, 0]}]}, 'numbers': {}, 'dates': {}}):
        _raises_message(lambda value=invalid: normalize_ocr_results(value), 'invalid OCR geometry')


def exec_provider_identity():
    assert (IAPDocumentProcessor.provider, IAPDocumentProcessor.model_version) == (
        'insilos-iap-openrouter', 'router-selected')
    assert LocalDocumentProcessor.provider == 'local-deterministic'


EXECUTORS = [
    ('AI-001', 'deterministic_classify, extraction_response_schema, _normalized_text, _decode_provider_content', exec_ai_001,
     'supported task contract: classify PO filename .95, lines in schema, VI normalization, JSON decode'),
    ('AI-002', 'classification_response_schema, extraction_response_schema, extraction_template_contract, validate', exec_ai_002,
     'no verdict authority: schema/prompt carry no decision fields/verbs; missing fields raise'),
    ('AI-004', 'extraction_response_schema, LocalDocumentProcessor.process', exec_ai_004,
     'confidence envelope 0..1 required at document level; review warning + confidence preserved; >1 rejected'),
    ('AI-008', 'SUPPORTED_MIMES, LocalDocumentProcessor._validate_binary', exec_ai_008,
     'scanned PDF/PNG/JPEG pass magic+structure; encrypted/active/malformed/oversize/unsupported fail closed'),
    ('AI-009', '_normalized_text, deterministic_classify', exec_ai_009,
     'VI/EN normalization equivalence; Hóa đơn GTGT and VAT Invoice both classify invoice'),
    ('NFR-011', '_decode_provider_content, _semantic_diagnostics, deterministic_classify', exec_nfr_011,
     'structured explainable diagnostics: error_class/json_error/truncation/wrapper/char classes; clean semantic errors'),
    ('SRS-SECTION-13-AI-INTELLIGENT-DOCUMENT-PROCESSING-REQUIREMENTS', 'extraction_response_schema, _semantic_diagnostics, _decode_provider_content', exec_srs_13,
     '§13 strict typed envelope additionalProperties=false at 3 levels; semantic-clean PO envelope; invalid JSON fails closed'),
    ('SRS-SECTION-16-DUPLICATE-DETECTION', 'batch_structure, LocalDocumentProcessor.process', exec_srs_16,
     '§16 duplicate detection: same role/subtype flagged, lifecycle subtypes not duplicates; processing deterministic with raw_response_hash'),
    ('SRS-SECTION-23-AI-QUALITY-AND-ACCEPTANCE-TARGETS', 'deterministic_classify, LocalDocumentProcessor.process, _decode_provider_content', exec_srs_23,
     '§23 quality targets: policy threshold honored; fail closed on encrypted PDF/malformed JSON; deterministic replay'),
    ('SRS-DOC-9-DOCUMENT-TYPES', 'DOCUMENT_TYPES, extraction_response_schema, batch_structure, validate', exec_srs_doc_9,
     '§9 catalog superset of 18 required types; per-type enum; lifecycle aliases collapse; unknown type raises'),
    ('VA-01', 'logistics_idp.py _inherit, MODEL_REUSE_MAP.md', exec_va_01,
     'inspect before create: document model reuses extract.mixin.with.words; MODEL_REUSE_MAP.md present'),
    ('VA-02', 'deterministic_classify (policy aliases/thresholds)', exec_va_02,
     'configuration over conditionals: policy alias/threshold drive classification; no customer-name conditionals in services'),
    ('VA-03', 'extraction_template_contract, validate', exec_va_03,
     'no business decision in prompt text alone: prompt has no decision verbs; missing fields rejected by Python validate'),
    ('VA-04', 'normalize_decimal, validate, deterministic_classify, _normalized_text', exec_va_04,
     'pure functions: normalization/validation/classification are deterministic side-effect-free; bool rejected'),
    ('VA-05', 'LocalDocumentProcessor.process raw_response_hash', exec_va_05,
     'preserve evidence: raw response bound by SHA-256; replay yields identical result'),
    ('VA-06', 'data/*.xml noupdate, module-level AST scan', exec_va_06,
     'no production mutation scripts: policy/demo data noupdate=1; onboarding limited models; no module-level env in models/services'),
    ('VA-07', 'extraction_template_contract', exec_va_07,
     'version configuration: default logistics-ocr-v7/11 hashed; policy override re-hashes; malformed template rejected'),
    ('VA-08', 'LocalDocumentProcessor.process, batch_structure', exec_va_08,
     'idempotent jobs: same content+response stable across filename change; duplicate role detection stable'),
    ('VA-09', 'extraction_response_schema, validate', exec_va_09,
     'explicit units/currencies: currency/uom/price_per/quantity/unit_price required; decimal strings normalized'),
    ('VA-10', 'ProcessingError, _decode_provider_content', exec_va_10,
     'structured errors: human message + diagnostics errors path/category; decode failures carry invalid_json'),
    ('SUPPORT-V3-OCR-GEOMETRY', 'normalize_ocr_results, extraction_response_schema', exec_ocr_geometry,
     'V3 support: OCR geometry shape/coords fail closed; NaN/4-tuple/missing category rejected'),
    ('SUPPORT-V3-PROVIDER-IDENTITY', 'IAPDocumentProcessor, LocalDocumentProcessor', exec_provider_identity,
     'V3 support: IAP provider/model identity stable; local adapter never claimed as OCR parity'),
]


def main():
    failures = []
    for srs_id, _symbols, executor, assertion in EXECUTORS:
        try:
            executor()
            print('PASS %-75s %s' % (srs_id, assertion))
        except Exception as exc:  # noqa: BLE001 - harness must report every failing row
            failures.append((srs_id, exc))
            print('FAIL %-75s %s: %r' % (srs_id, assertion, exc))
    print('WS2_EXECUTORS: %d PASS / %d FAIL' % (len(EXECUTORS) - len(failures), len(failures)))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
