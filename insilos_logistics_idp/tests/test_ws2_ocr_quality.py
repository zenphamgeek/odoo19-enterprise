import json
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from .common import new_logistics_test_user, unique_fixture
from ..models.logistics_idp import _INTERNAL_OCR_GEOMETRY_TOKEN
from ..services.document_processor import (
    IAPDocumentProcessor, ProcessingError, _decode_provider_content, extraction_response_schema,
    extraction_template_contract, normalize_ocr_results,
)
from ..services.document_schemas import validate


def _new_logistics_user(env, **values):
    return new_logistics_test_user(new_test_user, env, **values)


@tagged('post_install', '-at_install', 'logistics_idp')
class TestWs2OcrQuality(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.case = cls.env['logistics.idp.case'].create({
            'name': 'WS2-OCR-QUALITY', 'source_system': 'fixture', 'source_key': 'WS2-OCR-QUALITY',
            'source_version': 'v1', 'provenance': 'fixture:development', 'effective_date': '2026-01-01',
        })
        cls.document = cls.env['logistics.idp.document'].intake_content(
                cls.case, b'{"document_type":"invoice","confidence":1,"payload":{}}',
                'application/json', {'filename': 'ws2.json'}, process=False)

    def test_native_box_contract_normalizes_center_coordinates(self):
        self.document.with_context(_logistics_ocr_geometry_token=_INTERNAL_OCR_GEOMETRY_TOKEN).write({
            'extracted_words': {'0': [{'content': 'INV-1', 'coords': [.5, .25, .2, .1, 0]}]},
        })
        box = self.document.get_boxes()['word']['0'][0]
        self.assertEqual(box, {
            'id': 1, 'text': 'INV-1', 'page': '0', 'minX': .4, 'midX': .5, 'maxX': .6,
            'minY': .2, 'midY': .25, 'maxY': .3, 'width': .2, 'height': .1, 'angle': 0,
        })

    def test_typed_correction_appends_immutable_run_bound_evidence(self):
        run = self.document.current_run_id
        self.document.write({'corrected_invoice_number': 'INV-CORRECTED', 'corrected_total_gross': 125.5})
        evidence = self.case.evidence_ids.filtered(lambda item: item.category == 'ocr_manual_correction')
        self.assertEqual(len(evidence), 1)
        self.assertEqual(json.loads(evidence.payload), {
            'after': {'corrected_invoice_number': 'INV-CORRECTED', 'corrected_total_gross': 125.5},
            'before': {'corrected_invoice_number': False, 'corrected_total_gross': 0.0},
            'document_id': self.document.id, 'run_hash': run.payload_hash, 'run_id': run.id,
        })
        self.document.write({'corrected_invoice_number': 'INV-CORRECTED'})
        self.assertEqual(len(self.case.evidence_ids.filtered(
            lambda item: item.category == 'ocr_manual_correction')), 1)

    def test_typed_seven_role_schemas_normalize_null_and_reject_malformed_provider(self):
        roles = {
            'purchase_order': {'supplier': 'S', 'po_reference': 'PO-1', 'lines': [{'item': 'L'}]},
            'main_vat_invoice': {'supplier': 'S', 'invoice_number': 'INV-1', 'lines': [{'item': 'L'}]},
            'sales_invoice': {'supplier': 'S', 'invoice_number': 'INV-2', 'lines': [{'item': 'L'}]},
            'commercial_invoice': {'supplier': 'S', 'invoice_number': 'INV-3', 'lines': [{'item': 'L'}]},
            'packing_list': {'supplier': 'S', 'lines': [{'item': 'L'}]},
            'warehouse_release': {'supplier': 'S', 'lines': [{'item': 'L'}]},
            'export_declaration_final': {'declaration_number': 'D-1', 'regime': 'E11', 'lines': [{'item': 'L'}]},
        }
        for role, payload in roles.items():
            schema = extraction_response_schema(role)['json_schema']['schema']
            self.assertEqual(schema['properties']['document_type']['enum'], [role])
            self.assertFalse(schema['additionalProperties'])
            self.assertEqual(validate(role, {**payload, 'document_date': '31/07/2026', 'currency': None},
                                      allow_review=True)['document_date'], '2026-07-31')
        with self.assertRaises(ProcessingError) as caught:
            _decode_provider_content('{"payload":')
        self.assertEqual(caught.exception.diagnostics['errors'], [
            {'path': '$', 'category': 'invalid_json'}])

    def test_ocr_geometry_schema_and_normalizer_fail_closed(self):
        geometry = {
            'words': {'0': [{'content': 'INV-1', 'coords': [.5, .25, .2, .1, 0]}]},
            'numbers': {}, 'dates': {},
        }
        schema = extraction_response_schema('invoice')['json_schema']['schema']['properties']['ocr_results']
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['properties']), {'words', 'numbers', 'dates'})
        self.assertEqual(normalize_ocr_results(geometry), geometry)
        for invalid in ({'words': {}, 'numbers': {}},
                        {'words': {'0': [{'content': 'x', 'coords': [0, 0, 0, 0, float('nan')]}]}, 'numbers': {}, 'dates': {}},
                        {'words': {'0': [{'content': 'x', 'coords': [0, 0, 0, 0]}]}, 'numbers': {}, 'dates': {}},
                        *({'words': {'0': [box]}, 'numbers': {}, 'dates': {}} for box in (None, [], 1))):
            with self.assertRaisesRegex(ProcessingError, 'invalid OCR geometry'):
                normalize_ocr_results(invalid)

    def test_direct_ocr_geometry_write_is_rejected(self):
        for field in ('extracted_words', 'extracted_numbers', 'extracted_dates'):
            with self.assertRaises(UserError):
                self.document.write({field: {}})
        with self.assertRaises(UserError):
            self.document.with_context(_logistics_ocr_geometry_token='spoofed').write({'extracted_words': {}})

    def test_provider_schema_and_template_snapshots_are_strict_and_historical(self):
        policy = {'horizontal': {'extraction': {'templates': {'invoice': {
            'version': 'invoice-v2', 'schema_version': '9',
            'prompt': 'Extract {document_type}. Contract: {schema}.',
        }}}}}
        snapshot = extraction_template_contract('invoice', policy)
        changed = json.loads(json.dumps(policy))
        changed['horizontal']['extraction']['templates']['invoice']['version'] = 'invoice-v3'
        self.assertNotEqual(snapshot['hash'], extraction_template_contract('invoice', changed)['hash'])
        self.assertEqual((snapshot['version'], snapshot['schema_version']), ('invoice-v2', '9'))
        schema = extraction_response_schema('invoice')['json_schema']
        self.assertTrue(schema['strict'])
        self.assertFalse(schema['schema']['additionalProperties'])
        self.assertEqual(schema['schema']['properties']['document_type']['enum'], ['invoice'])
        self.assertEqual(schema['schema']['properties']['payload']['properties']['document_date']['pattern'],
                         r'^(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})$')
        default_template = extraction_template_contract('invoice')
        self.assertEqual((default_template['version'], default_template['schema_version']),
                         ('logistics-ocr-v7', '11'))
        self.assertIn('document_date only as YYYY-MM-DD or DD/MM/YYYY', default_template['prompt'])

    def test_iap_strict_ocr_persists_canonical_run_and_rejects_invalid_geometry(self):
        operator = _new_logistics_user(
            self.env, login='ws2-iap-' + unique_fixture('operator'), context={'no_reset_password': True},
            groups='insilos_logistics_idp.group_logistics_operator')
        self.case.owner_id = operator
        self.env['openrouter.domain'].search([('code', '=', 'logistics_ocr')]).mapped(
            'primary_model_id').write({'supports_pdf_input': True, 'supports_strict_json_schema': True})
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        payload = {
            'supplier': 'SUP', 'invoice_number': 'INV-STRICT', 'supplier_address': None,
            'buyer_name': None, 'total_gross': '12', 'total_quantity': None, 'currency': 'VND',
            'document_date': '2026-07-31',
            'lines': [{
                'description': 'goods', 'material_code': None, 'quantity': 1, 'unit_price': 12,
                'value': None, 'uom': None, 'currency': None, 'price_per': None,
                'quantity_1': None, 'quantity_2': None, 'remaining_quantity': None, 'hs_code': None,
            }],
        }
        valid = {'document_type': 'invoice', 'confidence': .95, 'payload': payload,
                 'source_spans': [{'page': 1, 'text': 'INV-STRICT'}],
                 'ocr_results': {'words': {'0': [{'content': 'INV-STRICT', 'coords': [.5, .5, .2, .1, 0]}]},
                                 'numbers': {}, 'dates': {}}}
        invalid_geometry = {**valid, 'ocr_results': {
            'words': {'0': [{'content': 'INV-STRICT', 'coords': [2, .5, .2, .1, 0]}]},
            'numbers': {}, 'dates': {},
        }}
        invalid_payload = {**valid, 'payload': []}
        router = type(self.env['openrouter.router'])
        with patch.object(router, 'complete', autospec=True, side_effect=[
                {'choices': [{'message': {'content': json.dumps({'document_type': 'invoice', 'confidence': .95})}}]},
                {'model': 'strict-model', 'choices': [{'message': {'content': json.dumps(valid)}}]},
        ]) as complete:
            document = self.env['logistics.idp.document'].with_user(operator).intake_content(
                self.case, binary, 'application/pdf', {'filename': 'VAT Invoice.pdf'})
        extraction_call = complete.call_args_list[1]
        strict_schema = extraction_call.kwargs['response_format']['json_schema']
        self.assertTrue(strict_schema['strict'])
        self.assertEqual(strict_schema['schema']['properties']['document_type']['enum'], ['invoice'])
        self.assertFalse(strict_schema['schema']['additionalProperties'])
        run = document.current_run_id
        run_payload = json.loads(run.payload)
        self.assertEqual((document.status, run.status, run.provider, run.model_version),
                         ('valid', 'valid', IAPDocumentProcessor.provider, 'strict-model'))
        self.assertEqual(run_payload['payload']['invoice_number'], payload['invoice_number'])
        self.assertEqual(run_payload['payload']['lines'][0]['quantity'], '1')
        self.assertEqual(run_payload['source_spans'], valid['source_spans'])
        self.assertEqual(run_payload['ocr_results'], valid['ocr_results'])
        self.assertEqual(run_payload['extraction_template']['schema_version'], run.schema_version)
        self.assertEqual((document.extraction_template_version, document.extraction_template_hash),
                         (run.template_version, run.template_hash))
        self.assertTrue(run.started_at and run.completed_at)
        self.assertTrue(document.extracted_words)
        immutable = (run.payload, run.payload_hash)
        with patch.object(router, 'complete', autospec=True, side_effect=[
                {'choices': [{'message': {'content': json.dumps({'document_type': 'invoice', 'confidence': .95})}}]},
                {'model': 'strict-model', 'choices': [{'message': {'content': json.dumps(invalid_geometry)}}]},
        ]):
            reviewed = self.env['logistics.idp.document'].with_user(operator).intake_content(
                self.case, b'%PDF-1.4\n<</Type /Page>>\n% invalid geometry\n%%EOF', 'application/pdf',
                {'filename': 'VAT Invoice invalid geometry.pdf'})
        reviewed_payload = json.loads(reviewed.current_run_id.payload)
        self.assertEqual((reviewed.status, reviewed.current_run_id.status), ('review', 'review'))
        self.assertEqual(reviewed_payload['validation_warnings'], [
            'AI extraction incomplete; human review required', 'ocr_results'])
        self.assertNotIn('ocr_results', reviewed_payload)
        self.assertFalse(reviewed.extracted_words)
        self.assertEqual(reviewed_payload['provider_attempts'][0]['outcome'], 'semantic_review_candidate')
        with patch.object(router, 'complete', autospec=True, side_effect=[
                {'choices': [{'message': {'content': json.dumps({'document_type': 'invoice', 'confidence': .95})}}]},
                {'model': 'strict-model', 'choices': [{'message': {'content': json.dumps(invalid_payload)}}]},
        ]):
            rejected = self.env['logistics.idp.document'].with_user(operator).intake_content(
                self.case, b'%PDF-1.4\n<</Type /Page>>\n% invalid payload\n%%EOF', 'application/pdf',
                {'filename': 'VAT Invoice invalid payload.pdf'})
        self.assertEqual((rejected.status, rejected.current_run_id.status), ('error', 'error'))
        self.assertFalse(rejected.extracted_words)
        self.assertEqual((run.payload, run.payload_hash), immutable)
