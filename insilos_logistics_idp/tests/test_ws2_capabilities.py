import ast
import hashlib
import json
import re
from pathlib import Path
from unittest.mock import patch

from odoo.tests.common import TransactionCase, new_test_user, tagged

from .common import new_logistics_test_user, unique_fixture
from ..services.document_processor import (
    MAX_BYTES, SUPPORTED_MIMES, IAPDocumentProcessor, LocalDocumentProcessor, ProcessingError,
    _decode_provider_content, _normalized_text, _semantic_diagnostics, batch_structure,
    classification_response_schema, deterministic_classify, extraction_response_schema,
    extraction_template_contract,
)
from ..services.document_schemas import DOCUMENT_TYPES, normalize_decimal, validate

MODULE = Path(__file__).resolve().parents[1]
SERVICES = (MODULE / 'services' / 'document_processor.py', MODULE / 'services' / 'document_schemas.py')
DECISION_VERBS = r'\b(?:match|approve|reject|decide|pass|fail|compliant|authorize|block)\b'
MINIMAL_PDF = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'


def _new_logistics_user(env, **values):
    return new_logistics_test_user(new_test_user, env, **values)


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


@tagged('post_install', '-at_install', 'logistics_idp')
class TestWs2Capabilities(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.case = cls.env['logistics.idp.case'].create({
            'name': 'WS2-CAPABILITIES', 'source_system': 'fixture', 'source_key': 'WS2-CAPABILITIES',
            'source_version': 'v1', 'provenance': 'fixture:development', 'effective_date': '2026-01-01',
        })
        cls.valid_invoice_envelope = {
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

    # --- AI-001 Supported tasks -------------------------------------------------------------

    def test_ai001_supported_tasks_contract(self):
        classified = deterministic_classify({'filename': 'purchase order 001.pdf'})
        self.assertEqual((classified['type'], classified['confidence'], classified['reason']),
                         ('purchase_order', .95, 'unique filename phrase'))
        schema = extraction_response_schema('purchase_order')['json_schema']['schema']
        self.assertIn('lines', schema['properties']['payload']['properties'])
        self.assertEqual(_normalized_text('HÓA ĐƠN GIÁ TRỊ GIA TĂNG'), 'hoa don gia tri gia tang')
        decoded, diagnostics = _decode_provider_content('{"document_type": "invoice", "confidence": 1}')
        self.assertEqual(decoded, {'document_type': 'invoice', 'confidence': 1})
        self.assertEqual(diagnostics['content_type'], 'string')

    # --- AI-002 Prohibited authority ---------------------------------------------------------

    def test_ai002_schemas_and_prompts_carry_no_verdict_authority(self):
        classification = classification_response_schema()['json_schema']['schema']
        self.assertEqual(set(classification['properties']), {'document_type', 'confidence'})
        self.assertFalse(classification['additionalProperties'])
        extraction = extraction_response_schema('purchase_order')['json_schema']['schema']
        self.assertEqual(set(extraction['properties']),
                         {'document_type', 'confidence', 'payload', 'source_spans', 'ocr_results'})
        self.assertFalse(extraction['additionalProperties'])
        template = extraction_template_contract('purchase_order')
        self.assertIsNone(re.search(DECISION_VERBS, template['prompt']))
        with self.assertRaises(ValueError):
            validate('invoice', {'supplier': 'S'})

    # --- AI-004 Confidence ---------------------------------------------------------------------

    def test_ai004_confidence_envelope_and_conservative_derivation(self):
        schema = extraction_response_schema('purchase_order')['json_schema']['schema']
        self.assertIn('confidence', schema['required'])
        self.assertEqual(schema['properties']['confidence'], {'type': 'number', 'minimum': 0, 'maximum': 1})
        self.assertNotIn('confidence', schema['properties']['payload']['properties']['lines']['items']['properties'])
        incomplete = {**self.valid_invoice_envelope, 'payload': {
            **self.valid_invoice_envelope['payload'], 'invoice_number': None}}
        result = LocalDocumentProcessor().process(MINIMAL_PDF, 'application/pdf',
                                                  {'provider_response': incomplete, 'allow_review': True})
        self.assertIn('payload.invoice_number', result['validation_warnings'])
        self.assertEqual(result['confidence'], .95)
        with self.assertRaisesRegex(ProcessingError, 'invalid confidence'):
            LocalDocumentProcessor().process(MINIMAL_PDF, 'application/pdf', {
                'provider_response': {**self.valid_invoice_envelope, 'confidence': 1.5}})

    # --- AI-008 Scanned documents --------------------------------------------------------------

    def test_ai008_scanned_binary_validation_and_mime_support(self):
        self.assertLessEqual({'application/pdf', 'image/png', 'image/jpeg'}, SUPPORTED_MIMES)
        processor = LocalDocumentProcessor()
        png = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
        for content, mimetype in ((MINIMAL_PDF, 'application/pdf'), (png, 'image/png'), (jpeg, 'image/jpeg')):
            processor._validate_binary(content, mimetype)
        for content, mimetype, message in (
                (b'%PDF-1.4\n/Encrypt 1 0 R\n%%EOF', 'application/pdf', 'encrypted PDF'),
                (b'%PDF-1.4\n<</Type /Page>>\n/JavaScript 1 0 R\n%%EOF', 'application/pdf', 'unsafe PDF active content'),
                (b'%PDF-MALFORMED-SYNTHETIC', 'application/pdf', 'malformed PDF structure'),
                (b'hello world', 'application/pdf', 'MIME and magic signature mismatch'),
                (b'\x89PNG\r\n\x1a\nshort', 'image/png', 'malformed PNG structure'),
                (b'%PDF-' + b'x' * MAX_BYTES, 'application/pdf', 'invalid document size'),
                (b'x', 'application/zip', 'unsupported MIME')):
            with self.assertRaisesRegex(ProcessingError, message):
                processor._validate_binary(content, mimetype)

    # --- AI-009 Multilingual ---------------------------------------------------------------------

    def test_ai009_vietnamese_and_english_normalization_equivalence(self):
        self.assertEqual(_normalized_text('HÓA ĐƠN GIÁ TRỊ GIA TĂNG'),
                         _normalized_text('hoa don gia tri gia tang'))
        self.assertEqual(_normalized_text('Đường số 1'), 'duong so 1')
        self.assertEqual(deterministic_classify({'filename': 'Hóa đơn GTGT 001.pdf'})['type'], 'invoice')
        self.assertEqual(deterministic_classify({'filename': 'VAT Invoice 001.pdf'})['type'], 'invoice')

    # --- NFR-011 Explainability -------------------------------------------------------------------

    def test_nfr011_structured_explainable_diagnostics(self):
        with self.assertRaises(ProcessingError) as caught:
            _decode_provider_content('{"payload": "abc')
        diagnostics = caught.exception.diagnostics
        self.assertEqual(str(caught.exception), 'invalid provider JSON')
        for key in ('error_class', 'json_error', 'truncation_category', 'wrapper_category',
                    'first_character_class', 'last_character_class', 'empty'):
            self.assertIn(key, diagnostics)
        self.assertEqual(diagnostics['error_class'], 'JSONDecodeError')
        self.assertEqual(diagnostics['json_error']['category'], 'unterminated')
        self.assertEqual(diagnostics['errors'], [{'path': '$', 'category': 'invalid_json'}])
        semantic = _semantic_diagnostics(self.valid_invoice_envelope, 'invoice')
        self.assertEqual(semantic['errors'], [])
        self.assertIn('type_map', semantic)
        self.assertIn('reason', deterministic_classify({'filename': 'packing list.pdf'}))

    # --- SRS §13 AI/IDP processing requirements -----------------------------------------------------

    def test_srs13_ai_idp_processing_contract(self):
        classified = deterministic_classify({'filename': 'purchase order 001.pdf'})
        self.assertEqual(classified['type'], 'purchase_order')
        schema = extraction_response_schema(classified['type'])['json_schema']['schema']
        self.assertFalse(schema['additionalProperties'])
        self.assertFalse(schema['properties']['payload']['additionalProperties'])
        self.assertFalse(schema['properties']['payload']['properties']['lines']['items']['additionalProperties'])
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
        self.assertEqual(_semantic_diagnostics(envelope, 'purchase_order')['errors'], [])
        with self.assertRaises(ProcessingError):
            _decode_provider_content('not json')

    # --- SRS §16 Duplicate detection -----------------------------------------------------------------

    def test_srs16_duplicate_detection_at_engine_level(self):
        manifest = [
            {'document_type': 'purchase_order'}, {'document_type': 'purchase_order'},
            {'document_type': 'draft_vat_invoice'}, {'document_type': 'main_vat_invoice'},
        ]
        structure = batch_structure(manifest)
        self.assertEqual(structure['duplicates'], ['purchase_order'])
        self.assertEqual(structure['present'], ['purchase_order', 'vat_invoice'])
        self.assertEqual(batch_structure([{'document_type': 'purchase_order'},
                                          {'document_type': 'main_vat_invoice'}])['duplicates'], [])
        processor = LocalDocumentProcessor()
        first = processor.process(MINIMAL_PDF, 'application/pdf',
                                  {'provider_response': self.valid_invoice_envelope})
        second = processor.process(MINIMAL_PDF, 'application/pdf',
                                   {'provider_response': self.valid_invoice_envelope})
        self.assertEqual(first, second)
        self.assertEqual(first['raw_response_hash'], hashlib.sha256(json.dumps(
            self.valid_invoice_envelope, sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    # --- SRS §23 AI quality and acceptance targets ----------------------------------------------------

    def test_srs23_quality_targets_are_deterministic_and_fail_closed(self):
        policy = {'horizontal': {'classification': {'thresholds': {'strong_filename': .99}}}}
        classified = deterministic_classify({'filename': 'packing list.pdf', 'idp_policy': policy})
        self.assertEqual(classified['confidence'], .99)
        schema = extraction_response_schema('invoice')['json_schema']['schema']
        self.assertFalse(schema['additionalProperties'])
        self.assertFalse(schema['properties']['payload']['additionalProperties'])
        with self.assertRaises(ProcessingError):
            LocalDocumentProcessor().process(b'%PDF-1.4\n/Encrypt 1 0 R\n%%EOF', 'application/pdf',
                                             {'provider_response': self.valid_invoice_envelope})
        with self.assertRaises(ProcessingError):
            _decode_provider_content('{"payload":')
        processor = LocalDocumentProcessor()
        self.assertEqual(
            processor.process(MINIMAL_PDF, 'application/pdf',
                              {'provider_response': self.valid_invoice_envelope}),
            processor.process(MINIMAL_PDF, 'application/pdf',
                              {'provider_response': self.valid_invoice_envelope}))

    # --- SRS-DOC-9 Document types ------------------------------------------------------------------------

    def test_srs_doc9_document_type_catalog_and_lifecycle_aliases(self):
        required = {
            'purchase_order', 'po_snapshot', 'draft_vat_invoice', 'main_vat_invoice', 'sales_invoice',
            'commercial_invoice', 'packing_list', 'bill_of_lading', 'export_declaration_draft',
            'export_declaration_final', 'import_declaration', 'master_data', 'dsnavl', 'sap_erp_output',
            'e13', 'e15', 'shipping_plan', 'gate_pass',
        }
        self.assertLessEqual(required, set(DOCUMENT_TYPES))
        for document_type in DOCUMENT_TYPES:
            schema = extraction_response_schema(document_type)['json_schema']['schema']
            self.assertEqual(schema['properties']['document_type']['enum'], [document_type])
        self.assertEqual(batch_structure([{'document_type': 'draft_vat_invoice'},
                                          {'document_type': 'main_vat_invoice'}])['present'],
                         ['vat_invoice'])
        with self.assertRaises(ValueError):
            validate('unknown', {})

    # --- VA-01 Inspect before create ----------------------------------------------------------------------

    def test_va01_core_reuse_is_documented_and_enforced(self):
        source = (MODULE / 'models' / 'logistics_idp.py').read_text()
        self.assertIn("_inherit = ['extract.mixin.with.words']", source)
        self.assertTrue((MODULE / 'docs' / 'MODEL_REUSE_MAP.md').is_file())

    # --- VA-02 Configuration over conditionals ---------------------------------------------------------------

    def test_va02_policy_config_drives_classification_no_customer_conditionals(self):
        policy = {'horizontal': {'classification': {
            'aliases': {'purchase_order': [r'\bdon\s+mua\b']}, 'thresholds': {'strong_filename': .98}}}}
        classified = deterministic_classify({'filename': 'Don mua 001.pdf', 'idp_policy': policy})
        self.assertEqual((classified['type'], classified['confidence']), ('purchase_order', .98))
        for path in SERVICES:
            self.assertIsNone(re.search(r'\b(?:if|elif)\b[^\n]*\.name\s*==', path.read_text()))

    # --- VA-03 No business decision in prompt text alone ------------------------------------------------------

    def test_va03_business_decisions_live_in_python_not_prompt(self):
        template = extraction_template_contract('purchase_order')
        self.assertIsNone(re.search(DECISION_VERBS, template['prompt']))
        with self.assertRaisesRegex(ValueError, 'missing fields'):
            validate('purchase_order', {'supplier': 'S', 'lines': []})

    # --- VA-04 Pure functions ------------------------------------------------------------------------------------

    def test_va04_pure_normalization_and_validation_functions(self):
        payload = {'supplier': 'SUP', 'invoice_number': 'INV-1',
                   'lines': [{'quantity': 1, 'unit_price': 2}]}
        self.assertEqual(normalize_decimal('1234.5'), '1234.5')
        self.assertEqual(normalize_decimal(2), '2')
        with self.assertRaises(ValueError):
            normalize_decimal(True)
        self.assertEqual(validate('invoice', payload), validate('invoice', payload))
        metadata = {'filename': 'purchase order 001.pdf'}
        self.assertEqual(deterministic_classify(metadata), deterministic_classify(metadata))
        self.assertEqual(_normalized_text('Đường 1'), _normalized_text('Đường 1'))

    # --- VA-05 Preserve evidence ----------------------------------------------------------------------------------

    def test_va05_evidence_binding_contract_is_stable(self):
        processor = LocalDocumentProcessor()
        result = processor.process(MINIMAL_PDF, 'application/pdf',
                                   {'provider_response': self.valid_invoice_envelope})
        self.assertEqual(result['raw_response_hash'], hashlib.sha256(json.dumps(
            self.valid_invoice_envelope, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        replay = processor.process(MINIMAL_PDF, 'application/pdf',
                                   {'provider_response': self.valid_invoice_envelope})
        self.assertEqual(result, replay)

    # --- VA-06 No production mutation scripts --------------------------------------------------------------------

    def test_va06_no_production_mutation_scripts_or_import_side_effects(self):
        data_dir = MODULE / 'data'
        for name in ('logistics_idp_data.xml', 'logistics_idp_policy_demo.xml'):
            self.assertIn('noupdate="1"', (data_dir / name).read_text())
        onboarding = (data_dir / 'logistics_idp_onboarding.xml').read_text()
        self.assertLessEqual(set(re.findall(r'model="([^"]+)"', onboarding)),
                             {'onboarding.onboarding.step', 'onboarding.onboarding'})
        for directory in ('models', 'services'):
            for path in sorted((MODULE / directory).glob('*.py')):
                self.assertNotIn('env', _module_level_names(ast.parse(path.read_text())), path)

    # --- VA-07 Version configuration -----------------------------------------------------------------------------

    def test_va07_version_configuration_snapshots_are_hashed(self):
        default = extraction_template_contract('invoice')
        self.assertEqual((default['version'], default['schema_version']), ('logistics-ocr-v7', '11'))
        self.assertEqual(len(default['hash']), 64)
        policy = {'horizontal': {'extraction': {'templates': {
            'default': {'version': 'invoice-v2', 'schema_version': '9',
                        'prompt': 'Extract {document_type}. Contract: {schema}.'}}}}}
        configured = extraction_template_contract('invoice', policy)
        self.assertEqual(configured['version'], 'invoice-v2')
        self.assertNotEqual(configured['hash'], default['hash'])
        with self.assertRaises(ValueError):
            extraction_template_contract('invoice', {'horizontal': {'extraction': {
                'templates': {'default': 'not-a-dict'}}}})

    # --- VA-08 Idempotent jobs ------------------------------------------------------------------------------------

    def test_va08_idempotent_processing_and_stable_dedupe_keys(self):
        processor = LocalDocumentProcessor()
        metadata = {'provider_response': self.valid_invoice_envelope}
        first = processor.process(MINIMAL_PDF, 'application/pdf', metadata)
        second = processor.process(MINIMAL_PDF, 'application/pdf',
                                   {**metadata, 'filename': 'different-name.pdf'})
        self.assertEqual(first, second)
        self.assertEqual(batch_structure([{'document_type': 'purchase_order'},
                                          {'document_type': 'purchase_order'}])['duplicates'],
                         ['purchase_order'])

    # --- VA-09 Explicit units/currencies --------------------------------------------------------------------------

    def test_va09_explicit_units_currency_and_scale_are_required(self):
        schema = extraction_response_schema('purchase_order')['json_schema']['schema']
        payload_schema = schema['properties']['payload']
        self.assertIn('currency', payload_schema['required'])
        line_schema = payload_schema['properties']['lines']['items']
        for field in ('uom', 'price_per', 'quantity', 'unit_price'):
            self.assertIn(field, line_schema['required'])
        self.assertEqual(line_schema['properties']['quantity'], {'type': ['number', 'string', 'null']})
        normalized = validate('purchase_order', {
            'supplier': 'S', 'supplier_address': 'ADDR', 'supplier_number': 'S-1', 'po_reference': 'PO-1',
            'total_value': '100', 'document_date': '2026-07-31', 'currency': 'VND',
            'lines': [{'quantity': '0.10', 'unit_price': '1', 'uom': 'PCE', 'price_per': None}],
        })
        self.assertEqual(normalized['lines'][0]['uom'], 'PCE')
        self.assertEqual(normalized['lines'][0]['quantity'], '0.10')

    # --- VA-10 Structured errors -----------------------------------------------------------------------------------

    def test_va10_structured_error_contract(self):
        error = ProcessingError('human message', {'errors': [{'path': '$', 'category': 'x'}]})
        self.assertEqual((str(error), error.diagnostics['errors']),
                         ('human message', [{'path': '$', 'category': 'x'}]))
        with self.assertRaises(ProcessingError) as caught:
            _decode_provider_content('{"a":')
        self.assertEqual(str(caught.exception), 'invalid provider JSON')
        self.assertEqual(caught.exception.diagnostics['errors'],
                         [{'path': '$', 'category': 'invalid_json'}])

    # --- Viewer: reads cause zero provider operations ------------------------------------------------------------

    def test_viewer_computed_fields_are_read_only_zero_provider_operations(self):
        operator = _new_logistics_user(
            self.env, login='ws2-viewer-' + unique_fixture('operator'), context={'no_reset_password': True},
            groups='insilos_logistics_idp.group_logistics_operator')
        self.case.owner_id = operator
        doc_model = self.env['logistics.idp.document'].with_user(operator)
        document = doc_model._intake_synthetic_content(
            self.case, MINIMAL_PDF, 'application/pdf',
            {'filename': 'viewer.pdf', 'document_type': 'invoice', 'confidence': .95,
             'provider_response': self.valid_invoice_envelope})
        run = document.current_run_id
        router = type(self.env['openrouter.router'])
        with patch.object(router, 'complete', autospec=True) as complete:
            rendered = json.loads(document.extraction_payload)
            normalized = json.loads(document.normalized_fields)
            spans = json.loads(document.source_spans)
            template_version = document.extraction_template_version
            template_hash = document.extraction_template_hash
        complete.assert_not_called()
        self.assertEqual(rendered['payload']['invoice_number'], 'INV-1')
        self.assertEqual(normalized['invoice_number'], 'INV-1')
        self.assertEqual(spans, self.valid_invoice_envelope['source_spans'])
        self.assertEqual((template_version, template_hash),
                         (run.template_version or document.current_run_id.template_version,
                          run.template_hash or document.current_run_id.template_hash))
        self.assertEqual(document.current_run_id, run)
        self.assertEqual(self.env['logistics.idp.extraction.run'].search_count([]), 1)
        self.assertEqual((IAPDocumentProcessor.provider, IAPDocumentProcessor.model_version),
                         ('insilos-iap-openrouter', 'router-selected'))
