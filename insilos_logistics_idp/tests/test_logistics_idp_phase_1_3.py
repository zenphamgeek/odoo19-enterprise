import hashlib
import io
import json
import re
from email import policy
from email.parser import BytesParser
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user as _new_test_user, tagged

from .common import new_logistics_test_user, unique_fixture
from ..services.document_processor import (
    IAPDocumentProcessor, ProcessingError, SyntheticDocumentProcessor, _decode_provider_content,
    _semantic_diagnostics, batch_structure, deterministic_classify, extraction_response_schema,
)
from ..services.document_schemas import DOCUMENT_TYPES, validate
from ..services.reconciliation import compare_line, customs_checks, description_similarity_candidates, reconcile_documents


def new_test_user(env, **values):
    return new_logistics_test_user(_new_test_user, env, **values)


@tagged('post_install', '-at_install', 'logistics_idp')
class TestLogisticsIdpPhase13(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        identity = unique_fixture('PHASE-13')
        cls.case = cls.env['logistics.idp.case'].create({
            'name': 'SYNTHETIC-PHASE-13', 'source_system': 'fixture', 'source_key': identity,
            'source_version': 'v1', 'provenance': 'fixture:development', 'effective_date': '2026-01-01',
        })
        # process() đòi group Logistics; superuser không thuộc group nào nên phải đóng vai operator.
        cls.operator = new_test_user(
            cls.env, login='log-phase13-operator', context={'no_reset_password': True},
            groups='insilos_logistics_idp.group_logistics_operator',
        )
        cls.mail_count = cls.env['mail.mail'].sudo().search_count([])
        cls.case.owner_id = cls.operator
        cls.doc_model = cls.env['logistics.idp.document'].with_user(cls.operator)
        cls.env['openrouter.domain'].search([('code', '=', 'logistics_ocr')]).mapped(
            'primary_model_id').write({'supports_pdf_input': True})

    def _eligible_operation_ceiling(self, deterministic=False, credit_budget=1, run_max_credits=3):
        return min(1 if deterministic else 2, run_max_credits // credit_budget)

    def test_openrouter_operation_id_is_canonical_once(self):
        router = self.env['openrouter.router']
        self.assertEqual(router._canonical_operation_id('run:extract', 1, 1), 'run:extract:model:1')
        self.assertEqual(router._canonical_operation_id('run:extract:model:1', 1, 1), 'run:extract:model:1')
        with self.assertRaises(UserError) as caught:
            router._canonical_operation_id('run:extract:model:0', 1, 1)
        self.assertTrue(caught.exception.nonretryable)
        self.assertNotRegex(router._canonical_operation_id('run:extract:model:1', 1, 1), r':model:\d+:model:')

    def test_case_has_one_task_and_required_check_lifecycle(self):
        self.assertTrue(self.case.task_id)
        check = self.env['logistics.idp.check.result']._controlled_create({
            'case_id': self.case.id, 'code': 'IMPORT_DECLARATION', 'required': True, 'verdict': 'pass',
            'rationale': 'synthetic pass', 'payload': {'actual': 'pass'},
        }, 'phase_1_3_test')
        self.case.write({'document_status': 'pass', 'reconciliation_status': 'pass', 'compliance_status': 'pass'})
        self.case._derive_lifecycle()
        self.assertEqual(self.case.state, 'ready')
        self.assertEqual(json.loads(check.payload)['actual'], 'pass')

    def test_pdf_intake_exact_hash_reuse_and_run_provenance(self):
        metadata = {'synthetic': True, 'document_type': 'invoice', 'confidence': .95, 'payload': {
            'supplier': 'SUP-1', 'invoice_number': 'INV-1',
            'lines': [{'quantity': 1, 'unit_price': 2}],
        }}
        binary = b'%PDF-1.4\n1 0 obj <</Type /Page>> endobj\n%%EOF'
        document = self.doc_model._intake_synthetic_content(self.case, binary, 'application/pdf', metadata)
        duplicate = self.doc_model._intake_synthetic_content(self.case, binary, 'application/pdf', metadata)
        self.assertEqual(document, duplicate)
        self.assertEqual((document.status, document.document_type), ('valid', 'invoice'))
        self.assertTrue(document.attachment_id and document.document_id)
        self.assertEqual(document.attachment_id.raw, binary)
        self.assertEqual(document.current_run_id.provider, 'local-deterministic')
        first_run = document.current_run_id
        self.assertEqual((first_run.company_id, first_run.document_type, first_run.page_count),
                         (self.case.company_id, 'invoice', document.page_count))
        self.assertEqual(first_run.confidence, .95)
        self.assertTrue(first_run.completed_at and first_run.duration_seconds >= 0)
        document._reprocess_synthetic({**metadata, 'confidence': .5})
        self.assertNotEqual(document.current_run_id, first_run)
        self.assertEqual(first_run.status, 'valid')

    def test_review_activity_owner_idempotency_and_resolution(self):
        mail_count = self.env['mail.mail'].sudo().search_count([])
        reviewer = new_test_user(
            self.env, login='log-phase13-reviewer', context={'no_reset_password': True},
            groups='insilos_logistics_idp.group_logistics_reviewer')
        self.assertEqual(self.env['mail.mail'].sudo().search_count([]), mail_count)
        self.operator.active = False
        content = ('From: test@example.com\nSubject: %s\n\n{}' % self._testMethodName).encode()
        document = self.doc_model.with_user(reviewer).intake_content(
            self.case, content, 'message/rfc822',
            {'provider_response': {'document_type': 'invoice', 'confidence': .5, 'payload': {}}})
        document._sync_review_activity()
        self.assertIn(self.case.owner_id, self.case._authorized_reviewers())
        self.assertIn(self.case.company_id, self.case.owner_id.company_ids)
        self.assertEqual(len(self.case.activity_ids), 1)
        document.with_user(reviewer).reprocess({
            'provider_response': {'document_type': 'invoice', 'confidence': .99, 'payload': {
                'supplier': 'SUP', 'invoice_number': 'INV',
                'lines': [{'quantity': 1, 'unit_price': 1}]}}})
        self.assertEqual(document.status, 'valid')
        self.assertFalse(self.case.activity_ids)

    def test_invalid_and_timeout_fail_to_review(self):
        invalid = self.doc_model.intake_content(
            self.case, b'From: test@example.com\nSubject: Bad\n\n{bad', 'message/rfc822', {'provider_response': '{bad'})
        timeout = self.doc_model.intake_content(
            self.case, b'\x89PNG\r\n\x1a\nxxxxIHDRxxxxxxxx', 'image/png', {'fixture': 'timeout'})
        self.assertEqual((invalid.status, timeout.status), ('error', 'error'))
        self.assertTrue(invalid.current_run_id.completed_at and invalid.current_run_id.duration_seconds >= 0)
        self.assertEqual(invalid.current_run_id.confidence, 0)
        self.assertEqual(self.case.document_status, 'review')

    def test_iap_ocr_multimodal_metadata_idempotency_and_failure_review(self):
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        extracted = {'document_type': 'invoice', 'confidence': .95, 'payload': {
            'supplier': 'SUP', 'invoice_number': 'INV', 'lines': [{'quantity': 1}]}, 'source_spans': []}
        classification = {'document_type': 'invoice', 'confidence': .95}
        responses = [
            {'choices': [{'message': {'content': json.dumps(classification)}}]},
            {'model': 'vision-model', 'log_id': 42, 'choices': [{'message': {'content': json.dumps(extracted)}}]},
        ] * 2
        router = type(self.env['openrouter.router'])
        config = self.env['ir.config_parameter'].sudo()
        config.set_param('logistics_idp.ocr_credit_budget', '1')
        with patch.object(router, 'complete', autospec=True, side_effect=responses) as complete:
            document = self.doc_model.intake_content(self.case, binary, 'application/pdf')
            first_run = document.current_run_id
            config.set_param('logistics_idp.ocr_credit_budget', '1')
            document.process(run_id=first_run.id)
            document.reprocess({})
        first, second, third, fourth = complete.call_args_list
        self.assertNotEqual(first.kwargs['operation_id'], third.kwargs['operation_id'])
        self.assertNotEqual(second.kwargs['operation_id'], fourth.kwargs['operation_id'])
        self.assertIn(':attempt:1:run:%s:' % first_run.id, first.kwargs['operation_id'])
        self.assertIn(':attempt:2:run:%s:' % document.current_run_id.id, third.kwargs['operation_id'])
        self.assertEqual(IAPDocumentProcessor.schema_version, '11')
        self.assertIn(':schema:11:prompt:%s' % IAPDocumentProcessor.prompt_version,
                      first.kwargs['operation_id'])
        self.assertEqual(first.kwargs['policy_metadata']['version'], IAPDocumentProcessor.prompt_version)
        self.assertEqual(first.kwargs['budget_metadata']['credit_budget'], 1)
        self.assertEqual(second.kwargs['budget_metadata']['credit_budget'], 1)
        self.assertEqual(third.kwargs['budget_metadata']['credit_budget'], 1)
        self.assertEqual(fourth.kwargs['budget_metadata']['credit_budget'], 1)
        first_payload = json.loads(first_run.payload)
        second_payload = json.loads(document.current_run_id.payload)
        self.assertEqual(first_payload['credit_budget'], 1)
        self.assertEqual(second_payload['credit_budget'], 1)
        ceiling = self._eligible_operation_ceiling()
        self.assertEqual(first_payload['planned_operation_budget'], ceiling)
        self.assertEqual(first_payload['used_operation_budget'], ceiling)
        self.assertEqual(ceiling, 2)
        self.assertEqual(first_payload['credit_budget_provenance']['key'], 'logistics_idp.ocr_credit_budget')
        response_schema = second.kwargs['response_format'].get('json_schema')
        if response_schema:
            self.assertTrue(response_schema['strict'])
        else:
            self.assertEqual(second.kwargs['response_format'], {'type': 'json_object'})
            response_schema = extraction_response_schema('invoice')['json_schema']
        schema = response_schema['schema']
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(schema['properties']['document_type']['enum'], ['invoice'])
        payload = schema['properties']['payload']
        self.assertFalse(payload['additionalProperties'])
        self.assertLessEqual(set(payload['required']), set(payload['properties']))
        self.assertIn('invoice_number', payload['properties'])
        self.assertNotIn('declaration_number', payload['properties'])
        lines = payload['properties']['lines']['items']
        self.assertFalse(lines['additionalProperties'])
        self.assertLessEqual(set(lines['required']), set(lines['properties']))
        media = first.args[2][0]['content'][1]
        self.assertEqual(media['type'], 'file')
        self.assertTrue(media['file']['file_data'].startswith('data:application/pdf;base64,'))
        self.assertEqual((document.status, document.current_run_id.provider, document.current_run_id.model_version),
                         ('valid', 'insilos-iap-openrouter', 'vision-model'))
        with patch.object(router, 'complete', autospec=True, side_effect=UserError('provider timeout')):
            document.reprocess({})
        self.assertEqual((document.status, self.case.document_status), ('error', 'review'))
        self.assertEqual(document.current_run_id.error, 'invalid IAP OCR classification response')
        failed_payload = json.loads(document.current_run_id.payload)
        self.assertNotIn('provider timeout', json.dumps(failed_payload))
        self.assertEqual(document.current_run_id.attempt_number, 3)
        self.assertIn(':attempt:3:run:%s' % document.current_run_id.id, failed_payload['operation_id'])
        self.assertEqual(failed_payload['classification_operation_id'], failed_payload['operation_id'] + ':classify')
        self.assertEqual(failed_payload['classification_source'], 'failed_before_classification')

    def test_pdf_filename_uses_iap_classification(self):
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        classification = {'document_type': 'invoice', 'confidence': .95}
        extracted = {'document_type': 'invoice', 'confidence': .95, 'payload': {
            'supplier': 'SUP', 'invoice_number': 'INV', 'lines': [{}]}, 'source_spans': []}
        router = type(self.env['openrouter.router'])
        with patch.object(router, 'complete', autospec=True, side_effect=[
                {'choices': [{'message': {'content': json.dumps(classification)}}]},
                {'model': 'vision-model', 'choices': [{'message': {'content': json.dumps(extracted)}}]},
        ]) as complete:
            document = self.doc_model.intake_content(
                self.case, binary, 'application/pdf', {'filename': 'VAT Invoice.pdf'})
        payload = json.loads(document.current_run_id.payload)
        self.assertEqual(len(complete.call_args_list), 2)
        self.assertEqual(payload['classification_source'], 'iap_multimodal')
        self.assertEqual(payload['planned_operation_budget'], 2)
        self.assertEqual(payload['used_operation_budget'], 2)
        self.assertEqual(len(payload['provider_operations']), 2)

    def test_provider_parse_diagnostics_are_causal_and_sanitized(self):
        secret = 'sk-live-SECRET customer@example.com unknown_private_key'
        cases = [
            ('{"value":"%s"' % secret, 'length', 'prose_suffix', 'provider_length'),
            ('```json\n{"value":\n```', 'stop', 'exact_fence', 'not_indicated'),
            ('```yaml\n%s\n```' % secret, 'mystery_reason', 'other_fence', 'not_indicated'),
            ('prefix {"value":1}', None, 'prose_prefix', 'not_indicated'),
            ('{"value":1} suffix', 'stop', 'prose_suffix', 'not_indicated'),
        ]
        for content, finish_reason, wrapper, truncation in cases:
            response = {'choices': [{'finish_reason': finish_reason, 'message': {'content': content}}]}
            with self.assertRaises(ProcessingError) as caught:
                _decode_provider_content(content, response)
            diagnostics = caught.exception.diagnostics
            serialized = json.dumps(diagnostics)
            self.assertEqual(diagnostics['content_type'], 'string')
            self.assertFalse(diagnostics['empty'])
            self.assertEqual(diagnostics['wrapper_category'], wrapper)
            self.assertEqual(diagnostics['truncation_category'], truncation)
            self.assertIn('position_bucket', diagnostics['json_error'])
            self.assertIn('length_bucket', diagnostics)
            self.assertNotIn(secret, serialized)
            self.assertNotIn('unknown_private_key', serialized)
            self.assertNotIn('finish_reason', diagnostics['provider'])
        self.assertEqual(diagnostics['provider']['finish_reason_category'], 'stop')
        with self.assertRaises(ProcessingError) as empty:
            _decode_provider_content('')
        self.assertTrue(empty.exception.diagnostics['empty'])
        self.assertEqual(empty.exception.diagnostics['json_error']['category'], 'empty')

    def test_invalid_json_does_not_retry_extraction(self):
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        classification = {'choices': [{'message': {'content': json.dumps(
            {'document_type': 'invoice', 'confidence': .95})}}]}
        valid = {'document_type': 'invoice', 'confidence': .95, 'payload': {
            'supplier': 'SUP', 'invoice_number': 'INV', 'lines': [{}]}, 'source_spans': []}
        first = {'choices': [{'finish_reason': 'length', 'message': {'content': '{"private":"SECRET"'}}],
                 'usage': {'prompt_tokens': 123, 'completion_tokens': 9, 'total_tokens': 132}}
        repaired = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(valid)}}]}
        router = type(self.env['openrouter.router'])
        with patch.object(router, 'complete', autospec=True,
                          side_effect=[classification, first, repaired]) as complete:
            document = self.doc_model.intake_content(self.case, binary, 'application/pdf')
        self.assertEqual(document.status, 'error')
        calls = complete.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1].kwargs['max_tokens'], 8192)
        self.assertIn(':extract:invoice:model:0', calls[1].kwargs['operation_id'])
        payload = json.loads(document.current_run_id.payload)
        attempts = [item for item in payload['provider_attempts'] if item['task'] == 'extraction']
        self.assertEqual(len(attempts), 1)
        self.assertEqual(payload['used_operation_budget'], 2)
        self.assertEqual(payload['planned_operation_budget'], 2)
        self.assertEqual(payload['stop_reason'], 'run_credit_ceiling')
        self.assertNotIn('SECRET', json.dumps(payload))

    def test_extraction_runtime_error_uses_sanitized_provider_failure_diagnostics(self):
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        classification = {'choices': [{'message': {'content': json.dumps(
            {'document_type': 'invoice', 'confidence': .95})}}]}
        router = type(self.env['openrouter.router'])
        with patch.object(router, 'complete', autospec=True,
                          side_effect=[classification, RuntimeError('SECRET')]):
            document = self.doc_model.intake_content(self.case, binary, 'application/pdf')
        payload = json.loads(document.current_run_id.payload)
        attempt = next(item for item in payload['provider_attempts'] if item['task'] == 'extraction')
        self.assertEqual(document.status, 'error')
        self.assertEqual(attempt['outcome'], 'provider_or_parse_failure')
        self.assertEqual(attempt['diagnostics'], {
            'error_class': 'RuntimeError', 'errors': [{'path': '$', 'category': 'provider_failure'}],
            'request_mode': attempt['request_mode']})
        self.assertNotIn('SECRET', json.dumps(payload))

    def test_nullable_critical_type_error_becomes_review_warning(self):
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        classification = {'choices': [{'message': {'content': json.dumps(
            {'document_type': 'invoice', 'confidence': .95})}}]}
        review = {'document_type': 'invoice', 'confidence': .95, 'payload': {
            'supplier': 'SUP', 'invoice_number': 'INV', 'total_gross': 1200, 'lines': [{}]},
            'source_spans': []}
        response = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(review)}}]}
        router = type(self.env['openrouter.router'])
        with patch.object(router, 'complete', autospec=True,
                          side_effect=[classification, response, response]) as complete:
            document = self.doc_model.intake_content(self.case, binary, 'application/pdf')
        payload = json.loads(document.current_run_id.payload)
        self.assertEqual((document.status, len(complete.call_args_list)), ('review', 2))
        self.assertIn('payload.total_gross', payload['validation_warnings'])
        self.assertEqual(payload['used_operation_budget'], 2)
        self.assertEqual(payload['stop_reason'], 'best_candidate_at_credit_ceiling')

    def test_review_candidate_at_credit_ceiling_is_accepted_without_fourth_call(self):
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        classification = {'choices': [{'message': {'content': json.dumps(
            {'document_type': 'invoice', 'confidence': .95})}}]}
        review = {'document_type': 'invoice', 'confidence': .95, 'payload': {
            'supplier': 'SUP', 'invoice_number': 'INV', 'currency': None,
            'document_date': '31/07/2026', 'lines': [{}]},
            'source_spans': [{'unexpected': 'redacted'}]}
        malformed = {'choices': [{'finish_reason': 'stop', 'message': {'content': '{'}}]}
        response = {'model': 'review-model', 'choices': [{'finish_reason': 'stop',
                    'message': {'content': json.dumps(review)}}]}
        router = type(self.env['openrouter.router'])
        with patch.object(router, 'complete', autospec=True,
                          side_effect=[classification, malformed, response]) as complete:
            document = self.doc_model.intake_content(self.case, binary, 'application/pdf')
        payload = json.loads(document.current_run_id.payload)
        self.assertEqual((document.status, len(complete.call_args_list)), ('error', 2))
        self.assertEqual(payload['used_operation_budget'], 2)
        self.assertEqual(payload['planned_operation_budget'], 2)
        self.assertEqual(payload['run_max_credits'], 3)
        self.assertEqual(len(payload['provider_operations']), 2)
        self.assertNotIn('charged_operations', payload)
        self.assertEqual(payload['stop_reason'], 'run_credit_ceiling')
        self.assertNotIn('payload', payload)

    def test_both_invalid_json_attempts_leave_durable_redacted_error(self):
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        classification = {'choices': [{'message': {'content': json.dumps(
            {'document_type': 'invoice', 'confidence': .95})}}]}
        malformed = {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"secret":"NOPE"'}}]}
        router = type(self.env['openrouter.router'])
        with patch.object(router, 'complete', autospec=True,
                          side_effect=[classification, malformed, malformed]) as complete:
            document = self.doc_model.intake_content(self.case, binary, 'application/pdf')
        self.assertEqual((document.status, len(complete.call_args_list)), ('error', 2))
        payload = json.loads(document.current_run_id.payload)
        self.assertEqual(len(payload['provider_attempts']), 1)
        self.assertEqual(payload['diagnostics']['error_class'], 'JSONDecodeError')
        self.assertEqual((document.document_type, payload['document_type']), ('invoice', 'invoice'))
        self.assertEqual(payload['classification_confidence'], .95)
        self.assertEqual(payload['classification_source'], 'iap_multimodal')
        self.assertEqual(payload['provider_operations'], [call.kwargs['operation_id'] for call in complete.call_args_list])
        self.assertNotIn('charged_operations', payload)
        self.assertEqual(payload['used_operation_budget'], 2)
        self.assertEqual(payload['planned_operation_budget'], 2)
        self.assertNotIn('NOPE', json.dumps(payload))

    def test_output_is_idempotent_versioned_and_superseding(self):
        output = self.env['logistics.idp.output'].generate(self.case, 'e13', {'regime': 'E13', 'lines': [{'id': 1}]})
        self.assertEqual(self.env['logistics.idp.output'].generate(self.case, 'e13', {'lines': [{'id': 1}], 'regime': 'E13'}), output)
        successor = self.env['logistics.idp.output'].generate(self.case, 'e13', {'regime': 'E13', 'lines': [{'id': 2}]})
        self.assertEqual((successor.version, successor.supersedes_id), (2, output))
        self.assertEqual((output.status, successor.status), ('superseded', 'generated'))
        self.assertEqual(hashlib.sha256(successor.attachment_id.raw).hexdigest(), successor.artifact_sha256)
        self.assertEqual(load_workbook(io.BytesIO(successor.attachment_id.raw)).active['A1'].value, 'field')
        declaration = self.env['logistics.idp.output'].generate(self.case, 'import_declaration', {'number': 'D-1'})
        pdf = declaration.attachment_id.raw
        self.assertTrue(pdf.startswith(b'%PDF-') and pdf.rstrip().endswith(b'%%EOF'))
        self.assertEqual(len(re.findall(rb'/Type\s*/Page(?!s)\b', pdf)), 1)
        email = self.env['logistics.idp.output'].generate(self.case, 'report_email', {'subject': 'Daily report'})
        self.assertEqual(BytesParser(policy=policy.default).parsebytes(email.attachment_id.raw)['Subject'], 'Daily report')

    def test_task_sync_is_one_way(self):
        self.case.write({'next_action': 'Review invoice', 'severity': 'high', 'document_status': 'block'})
        self.case._derive_lifecycle()
        self.assertEqual(self.case.task_id.stage_id, self.env.ref('insilos_logistics_idp.stage_exception'))
        self.assertIn('Review invoice', self.case.task_id.description)
        self.case.task_id.name = 'Task-only change'
        self.assertNotEqual(self.case.name, self.case.task_id.name)


@tagged('post_install', '-at_install', 'logistics_idp')
class TestLogisticsIdpPurePhase13(TransactionCase):
    def test_smart_filename_classifier_and_batch_structure(self):
        cases = {
            'PO_123.pdf': 'purchase_order', 'Hóa-đơn_GTGT_draft.pdf': 'draft_vat_invoice',
            'hoa don gtgt chinh.PDF': 'main_vat_invoice', 'sales_invoice.pdf': 'sales_invoice',
            'Commercial Invoice.pdf': 'commercial_invoice', 'packing-list.xlsx': 'packing_list',
            'Phiếu xuất kho.pdf': 'warehouse_release', 'to khai xuat final.pdf': 'export_declaration_final',
            'export declaration draft.pdf': 'export_declaration_draft',
        }
        for filename, expected in cases.items():
            result = deterministic_classify({'filename': filename})
            self.assertEqual((result['type'], result['confidence']), (expected, .95))
        self.assertIsNone(deterministic_classify({'filename': 'report.pdf'})['type'])
        self.assertIsNone(deterministic_classify({'filename': 'supporting.pdf'})['type'])
        self.assertIsNone(deterministic_classify({'filename': 'genesis.pdf'})['type'])
        self.assertEqual(deterministic_classify({'filename': 'genesis_PO.pdf'})['type'], 'purchase_order')
        self.assertIsNone(deterministic_classify({
            'document_type': 'packing_list', 'document_type_trusted': True})['type'])
        structure = batch_structure([
            {'document_type': 'purchase_order'}, {'document_type': 'draft_vat_invoice'},
            {'document_type': 'sales_invoice'}, {'document_type': 'commercial_invoice'},
            {'document_type': 'packing_list'}, {'document_type': 'warehouse_release'},
            {'document_type': 'export_declaration_draft'},
        ])
        self.assertFalse(structure['missing'])
        self.assertEqual(structure['present'], [
            'commercial_invoice', 'export_declaration', 'packing_list', 'purchase_order',
            'sales_invoice', 'vat_invoice', 'warehouse_release',
        ])
        lifecycle = batch_structure([
            {'document_type': 'draft_vat_invoice'}, {'document_type': 'main_vat_invoice'},
            {'document_type': 'export_declaration_draft'}, {'document_type': 'export_declaration_final'},
        ])
        self.assertFalse(lifecycle['duplicates'])
        duplicates = batch_structure([
            {'document_type': 'draft_vat_invoice'}, {'document_type': 'draft_vat_invoice'},
            {'document_type': 'e11'}, {'document_type': 'e11'},
        ])
        self.assertEqual(duplicates['duplicates'], ['export_declaration', 'vat_invoice'])

    def test_provider_json_parse_and_redacted_diagnostics(self):
        direct = {'document_type': 'main_vat_invoice'}
        self.assertEqual(_decode_provider_content(direct)[0], direct)
        self.assertEqual(_decode_provider_content('```json\n{"document_type":"main_vat_invoice"}\n```')[1]['normalization'],
                         'exact_json_fence')
        secret = 'FAKE_SECRET_CUSTOMER_123'
        with self.assertRaises(ProcessingError) as caught:
            _decode_provider_content('{"supplier":"%s"' % secret)
        serialized = json.dumps(caught.exception.diagnostics)
        self.assertNotIn(secret, serialized)
        diagnostics = caught.exception.diagnostics
        self.assertEqual(diagnostics['json_error']['category'], 'syntax')
        self.assertIn('position_bucket', diagnostics['json_error'])
        self.assertEqual(diagnostics['error_class'], 'JSONDecodeError')
        self.assertEqual(diagnostics['errors'], [{'path': '$', 'category': 'invalid_json'}])
        array_content = [{'type': 'text', 'text': '{"document_'}, {'type': 'image_url', 'image_url': {}},
                         {'type': 'output_text', 'text': 'type":"invoice"}'}]
        parsed, shape = _decode_provider_content(array_content)
        self.assertEqual(parsed, {'document_type': 'invoice'})
        self.assertEqual(shape['content_type'], 'array')
        with self.assertRaises(ProcessingError) as arbitrary:
            _decode_provider_content([{'type': 'image_url', 'value': secret}])
        self.assertNotIn(secret, json.dumps(arbitrary.exception.diagnostics))

    def test_semantic_diagnostics_and_main_vat_strict_schema(self):
        secret = 'FAKE_SECRET_UNKNOWN_KEY'
        raw = {'document_type': 'main_vat_invoice', 'confidence': 'high', secret: 'hidden',
               'payload': {'supplier': 'PRIVATE_SUPPLIER', 'lines': 'wrong'}, 'source_spans': []}
        diagnostics = _semantic_diagnostics(raw, 'main_vat_invoice')
        serialized = json.dumps(diagnostics)
        self.assertNotIn(secret, serialized)
        self.assertNotIn('PRIVATE_SUPPLIER', serialized)
        self.assertEqual(diagnostics['unknown_top_level_key_count'], 1)
        self.assertIn('invoice_number', diagnostics['payload']['missing_required'])
        self.assertEqual(diagnostics['payload']['lines']['type'], 'string')
        self.assertEqual(diagnostics['confidence']['type'], 'string')
        self.assertIn({'path': 'confidence', 'category': 'type', 'expected': ['number'], 'actual': 'string'},
                      diagnostics['errors'])
        schema = extraction_response_schema('main_vat_invoice')['json_schema']['schema']
        self.assertEqual(set(schema['required']), set(schema['properties']))
        self.assertEqual(schema['properties']['document_type']['enum'], ['main_vat_invoice'])
        payload = schema['properties']['payload']
        self.assertEqual(set(payload['required']), set(payload['properties']))
        line = payload['properties']['lines']['items']
        self.assertEqual(set(line['required']), set(line['properties']))
        for field in ('quantity', 'unit_price', 'price_per', 'value'):
            self.assertEqual(line['properties'][field]['type'], ['number', 'string', 'null'])
        self.assertEqual(line['properties']['uom']['type'], ['string', 'null'])
        self.assertFalse(schema['additionalProperties'] or payload['additionalProperties'] or line['additionalProperties'])
        self.assertEqual(schema['properties']['source_spans']['items']['required'], ['page', 'text'])

    def test_xlsx_normalized_schema_requires_extended_ordered_headers(self):
        header = ['document_type', 'confidence', 'supplier', 'supplier_address', 'supplier_number',
                  'po_reference', 'total_value', 'document_date', 'currency']
        line_header = ['material_code', 'description', 'quantity', 'unit_price', 'uom', 'value', 'custom_code']

        def workbook_bytes(top=header, lines=line_header):
            workbook = Workbook(); sheet = workbook.active
            sheet.append(top)
            sheet.append(['purchase_order', '.95', 'SUP', 'Address', 'SUP-1', 'PO-1', '2.5', '2026-01-01', 'USD'])
            sheet.append(lines)
            sheet.append(['MAT-1', 'Item', '1', '2.5', 'EA', '2.5', 'PO-1-1'])
            output = io.BytesIO(); workbook.save(output)
            return output.getvalue()

        processor = SyntheticDocumentProcessor()
        parsed = processor._xlsx_payload(workbook_bytes())
        self.assertEqual(parsed['payload'], {
            'supplier': 'SUP', 'supplier_address': 'Address', 'supplier_number': 'SUP-1', 'po_reference': 'PO-1',
            'total_value': '2.5', 'document_date': '2026-01-01', 'currency': 'USD',
            'lines': [{'material_code': 'MAT-1', 'description': 'Item', 'quantity': '1', 'unit_price': '2.5',
                       'uom': 'EA', 'value': '2.5', 'custom_code': 'PO-1-1'}],
        })
        for top, lines in ((header[:5] + header[6:], line_header),
                           ([header[0], header[1], header[3], header[2], *header[4:]], line_header),
                           (header, line_header[:2] + line_header[3:]),
                           (header, [line_header[1], line_header[0], *line_header[2:]]),
                           (header + ['currency'], line_header)):
            with self.assertRaisesRegex(ProcessingError, 'normalized document table'):
                processor._xlsx_payload(workbook_bytes(top, lines))

    def test_processor_mimes_and_typed_validation(self):
        processor = SyntheticDocumentProcessor()
        fixture = {'document_type': 'packing_list', 'payload': {'supplier': 'S', 'lines': [{'quantity': 1, 'unit_price': 2}]}}
        pdf = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        self.assertEqual(processor.process(pdf, 'application/pdf', fixture)['document_type'], 'packing_list')
        policy = {'horizontal': {'extraction': {'critical_fields': {'main_vat_invoice': [
            'currency', 'lines[].description', 'lines[].quantity', 'lines[].unit_price']}}}}
        attempt21 = {'document_type': 'main_vat_invoice', 'confidence': .9, 'payload': {
            'supplier': 'S', 'invoice_number': 'INV', 'total_gross': '1,200 USD',
            'total_quantity': '10 KG', 'currency': None, 'lines': [{
                'description': None, 'quantity': None, 'unit_price': None}]}}
        result = processor.process(pdf, 'application/pdf', {**attempt21, 'idp_policy': policy})
        self.assertEqual(result['payload']['total_gross'], '1,200 USD')
        self.assertEqual(result['payload']['total_quantity'], '10 KG')
        self.assertEqual(result['validation_warnings'], [
            'payload.currency', 'payload.lines[].description', 'payload.lines[].quantity',
            'payload.lines[].unit_price'])
        self.assertNotIn('S', json.dumps(_semantic_diagnostics(attempt21)))
        typed = {**fixture, 'payload': {**fixture['payload'], 'lines': [{
            'quantity': 1, 'unit_price': '2.50', 'price_per': None, 'value': 5.0}]}}
        numeric = processor.process(pdf, 'application/pdf', typed)
        self.assertEqual(numeric['payload']['lines'][0], {
            'quantity': '1', 'unit_price': '2.50', 'price_per': None, 'value': '5.0'})
        diagnostics = _semantic_diagnostics({**typed, 'confidence': .9, 'source_spans': []})
        self.assertFalse(diagnostics['errors'])
        fake_secret = 'FAKE_SECRET_DECIMAL_123'
        invalid_decimal = {**typed, 'payload': {**typed['payload'], 'lines': [
            {**typed['payload']['lines'][0], 'quantity': fake_secret},
            {**typed['payload']['lines'][0], 'quantity': '3', 'unit_price': fake_secret}]}}
        reviewed = processor.process(pdf, 'application/pdf', {**invalid_decimal, 'allow_review': True})
        self.assertEqual([line['quantity'] for line in reviewed['payload']['lines']], [None, '3'])
        self.assertIsNone(reviewed['payload']['lines'][1]['unit_price'])
        self.assertEqual(reviewed['validation_warnings'], [
            'payload.lines[].quantity', 'payload.lines[].unit_price'])
        decimal_errors = _semantic_diagnostics({**invalid_decimal, 'confidence': .9, 'source_spans': []})['errors']
        self.assertIn({'path': 'payload.lines[].quantity', 'category': 'invalid_decimal'}, decimal_errors)
        self.assertNotIn(fake_secret, json.dumps(decimal_errors))
        for invalid_value in (True, [], {}):
            invalid = {**typed, 'payload': {**typed['payload'], 'lines': [{
                **typed['payload']['lines'][0], 'quantity': invalid_value}]}}
            with self.assertRaises(ProcessingError):
                processor.process(pdf, 'application/pdf', invalid)
            error = _semantic_diagnostics({**invalid, 'confidence': .9, 'source_spans': []})['errors'][0]
            self.assertEqual(error['path'], 'payload.lines[].quantity')
            self.assertEqual(error['expected'], ['number', 'string', 'null'])
        for invalid in (
                {**attempt21, 'payload': {**attempt21['payload'], 'total_gross': 1200}},
                {**attempt21, 'payload': {**attempt21['payload'], 'supplier': None}},
                {**attempt21, 'payload': {**attempt21['payload'], 'invoice_number': None}},
                {**attempt21, 'payload': {**attempt21['payload'], 'lines': None}}):
            with self.assertRaises(ProcessingError):
                processor.process(pdf, 'application/pdf', invalid)
        with self.assertRaises(ProcessingError):
            processor.process(b'not-pdf', 'application/pdf', fixture)
        with self.assertRaises(ProcessingError):
            processor.process(pdf, 'application/pdf', {'document_type': 'unknown'})

    def test_fr201_purchase_order_missing_invalid_and_low_confidence_review(self):
        processor = SyntheticDocumentProcessor()
        pdf = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        policy = {'horizontal': {'extraction': {'acceptance_threshold': .8, 'critical_fields': {'purchase_order': [
            'supplier', 'supplier_address', 'supplier_number', 'po_reference', 'total_value', 'document_date',
            'currency', 'lines', 'lines[].material_code', 'lines[].description', 'lines[].unit_price',
            'lines[].quantity', 'lines[].uom', 'lines[].value', 'lines[].custom_code']}}}}
        payload = {'supplier': 'SUP', 'supplier_address': 'Address', 'supplier_number': 'SUP-1', 'po_reference': 'PO-1',
                   'total_value': '2.50', 'document_date': '2026-07-31', 'currency': 'USD',
                   'lines': [{'material_code': 'MAT-1', 'description': 'Item', 'unit_price': '2.5', 'quantity': '1',
                              'uom': 'EA', 'value': '2.5', 'custom_code': 'PO-1-1'}]}
        for path, broken in (('supplier', None), ('lines[].material_code', None),
                             ('lines[].quantity', 'not-a-number'), ('document_date', '31/02/2026')):
            candidate = {**payload, 'lines': [dict(payload['lines'][0])]}
            if path.startswith('lines[].'):
                candidate['lines'][0][path.split('.', 1)[1]] = broken
            else:
                candidate[path] = broken
            result = processor.process(pdf, 'application/pdf', {'document_type': 'purchase_order', 'confidence': .9,
                'payload': candidate, 'idp_policy': policy, 'allow_review': True})
            self.assertIn('payload.%s' % path, result['validation_warnings'])
        for broken in ({**payload, 'supplier_number': 1}, {**payload, 'lines': 'not-lines'},
                       {**payload, 'lines': [{**payload['lines'][0], 'quantity': []}]}):
            with self.assertRaises(ProcessingError):
                processor.process(pdf, 'application/pdf', {'document_type': 'purchase_order', 'payload': broken})
        with self.assertRaises(ProcessingError):
            processor.process(pdf, 'application/pdf', {'document_type': 'not_a_document', 'payload': payload})
        self.assertEqual(processor.process(pdf, 'application/pdf', {'document_type': 'purchase_order', 'confidence': .79,
            'payload': payload, 'idp_policy': policy})['confidence'], .79)

    def test_document_date_normalizes_vietnamese_format_and_rejects_invalid_date(self):
        payload = {'supplier': 'S', 'lines': [{}], 'document_date': '18/06/2026'}
        self.assertEqual(validate('packing_list', payload)['document_date'], '2026-06-18')
        self.assertEqual(_semantic_diagnostics({'document_type': 'packing_list', 'confidence': .9,
            'payload': payload, 'source_spans': []})['payload']['date_format'], 'vietnamese_normalizable')
        self.assertFalse(_semantic_diagnostics({'document_type': 'packing_list', 'confidence': .9,
            'payload': {**payload, 'document_date': None}, 'source_spans': []})['errors'])
        with self.assertRaises(ValueError):
            validate('packing_list', {**payload, 'document_date': '31/02/2026'})
        diagnostics = _semantic_diagnostics({'document_type': 'packing_list', 'confidence': .9,
            'payload': {**payload, 'document_date': '31/02/2026'}, 'source_spans': []})
        self.assertEqual(diagnostics['errors'][-1]['path'], 'payload.document_date')
        with self.assertRaises(ValueError):
            validate('packing_list', {**payload, 'document_date': 'June 18, 2026'}, allow_review=False)
        malformed = _semantic_diagnostics({'document_type': 'packing_list', 'confidence': .9,
            'payload': {**payload, 'document_date': 'June 18, 2026'}, 'source_spans': []})
        self.assertIn({'path': 'payload.document_date', 'category': 'format',
                       'expected': ['YYYY-MM-DD', 'DD/MM/YYYY']}, malformed['errors'])

    def test_nullable_attempt_shape_returns_review_warnings(self):
        processor = SyntheticDocumentProcessor()
        pdf = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        policy = {'horizontal': {'extraction': {'critical_fields': {'main_vat_invoice': [
            'currency', 'lines[].description', 'lines[].quantity', 'lines[].unit_price']}}}}
        result = processor.process(pdf, 'application/pdf', {'document_type': 'main_vat_invoice',
            'confidence': .9, 'payload': {'supplier': 'S', 'invoice_number': 'INV', 'lines': [{
                'description': None, 'quantity': None, 'unit_price': None, 'value': None}],
                'currency': None, 'document_date': '18/06/2026', 'supplier_address': None},
            'idp_policy': policy})
        self.assertEqual(result['payload']['document_date'], '2026-06-18')
        self.assertTrue(result['validation_warnings'])

    def test_expanded_reference_document_taxonomy(self):
        for document_type, payload in (
            ('po_snapshot', {'source_version': 'v1', 'lines': [{}]}),
            ('master_data', {'source_version': 'v1', 'lines': [{}]}),
            ('e11', {'regime': 'E11', 'lines': [{}]}),
            ('import_declaration', {'declaration_number': 'TK-1', 'lines': [{}]}),
            ('bill_of_lading', {'shipment_reference': 'SHIP-1', 'lines': [{}]}),
        ):
            self.assertEqual(validate(document_type, payload), payload)

    def test_currency_uom_per_rounding_and_customs_fail_safe(self):
        result = compare_line(
            {'quantity': 1000, 'uom': 'G', 'unit_price': 25000000, 'price_per': 1000, 'currency': 'VND'},
            {'quantity': 1, 'uom': 'KG', 'unit_price': 1, 'currency': 'USD'},
            fx_rates={'VND': '0.00004', 'USD': '1'},
        )
        self.assertEqual(result['verdict'], 'pass')
        self.assertEqual(customs_checks({})[0]['verdict'], 'review')
        self.assertEqual(customs_checks({'regime': 'E13', 'expected_hs': '1', 'actual_hs': '2'})[0]['verdict'], 'block')
        po = {'lines': [{'material_code': 'M', 'quantity': 1, 'unit_price': 1}]}
        invoice_line = {'material_code': 'M', 'quantity': 1, 'unit_price': 1}
        missing = reconcile_documents(po, {'lines': [invoice_line]})
        self.assertEqual((missing['verdict'], missing['results'][0]['material_code'], missing['results'][0]['regime'], missing['results'][0]['reason']),
                         ('review', 'M', '', 'missing customs regime'))
        for regime in ('E11', 'E13', 'E15'):
            explicit = reconcile_documents(po, {'regime': regime, 'lines': [invoice_line]})
            self.assertEqual((explicit['verdict'], explicit['results'][0]['regime']), ('pass', regime))

    def test_missing_regime_identifies_only_affected_materials(self):
        result = reconcile_documents(
            {'lines': [
                {'material_code': 'MAT-1', 'quantity': 1, 'unit_price': 1},
                {'material_code': 'MAT-2', 'quantity': 1, 'unit_price': 1},
                {'description': 'No material', 'quantity': 1, 'unit_price': 1},
            ]},
            {'lines': [
                {'material_code': 'MAT-1', 'quantity': 1, 'unit_price': 1},
                {'material_code': 'MAT-2', 'regime': 'E13', 'quantity': 1, 'unit_price': 1},
                {'description': 'No material', 'regime': 'E13', 'quantity': 1, 'unit_price': 1},
            ]},
        )
        self.assertEqual([(item.get('material_code'), item['result']) for item in result['results']],
                         [('MAT-1', 'review'), (None, 'review'), (None, 'review')])
        self.assertEqual([item['customs_regime_checks'][0]['reason'] for item in result['results']],
                         ['missing expected customs regime'] * 3)
        self.assertNotIn('material_code', result['results'][1])

    def test_fr302_draft_identity_final_number_policy_is_scoped(self):
        po = {'supplier': 'S', 'lines': [{'material_code': 'M', 'regime': 'E13', 'quantity': 1, 'unit_price': 1}]}
        draft = {'supplier': 'S', 'document_type': 'draft_vat_invoice', 'invoice_number': 'FINAL-001',
                 'lines': [{'material_code': 'M', 'regime': 'E13', 'quantity': 1, 'unit_price': 1}]}
        denied = reconcile_documents(po, draft, policy={'draft_invoice': {'mode': 'required', 'final_number_allowed': False}})
        self.assertEqual((denied['verdict'], denied['draft_invoice_check']), ('review', {
            'result': 'review', 'rule': 'draft_invoice.final_number_allowed', 'observed_number': 'FINAL-001'}))
        allowed = reconcile_documents(po, draft, policy={'draft_invoice': {'mode': 'required', 'final_number_allowed': True}})
        self.assertEqual((allowed['verdict'], allowed['draft_invoice_check']), ('pass', None))
        for policy in ({'draft_invoice': {'mode': 'skipped', 'final_number_allowed': False}},
                       {'draft_invoice': {'mode': 'sales_invoice', 'final_number_allowed': False}}):
            result = reconcile_documents(po, draft, policy=policy)
            self.assertIsNone(result['draft_invoice_check'])
            self.assertEqual(result['verdict'], 'review')
            self.assertEqual(result['draft_invoice_mode_check']['rule'], 'draft_invoice.mode')
        non_draft = reconcile_documents(po, {**draft, 'document_type': 'sales_invoice'},
                                        policy={'draft_invoice': {'mode': 'optional', 'final_number_allowed': False},
                                                'main_invoice': {'allowed_substitutes': ['sales_invoice']}})
        self.assertEqual((non_draft['verdict'], non_draft['draft_invoice_check'], non_draft['draft_invoice_mode_check']),
                         ('pass', None, None))

    def test_fr404_declaration_groups_count_rules_are_exact_and_effective(self):
        po = {'supplier': 'S', 'lines': [{'material_code': 'M', 'remaining_quantity': 2, 'quantity': 2, 'unit_price': 1}]}
        invoice = {'supplier': 'S', 'lines': [{'material_code': 'M', 'regime': 'E11', 'quantity': 1, 'unit_price': 1},
                                               {'material_code': 'M', 'regime': 'E15', 'quantity': 1, 'unit_price': 1}]}
        policy = {'declaration_group_rules': [{'rule_id': 'e11-e15', 'regimes': ['E11', 'E15'],
            'declaration_count': 2, 'effective_from': '2026-01-01', 'effective_to': '2026-12-31'}]}
        passed = reconcile_documents(po, invoice, policy=policy, declaration_groups=['TK-1', 'TK-2'], effective_date='2026-06-01')
        self.assertEqual((passed['verdict'], passed['declaration_group_check']['rule_id'], passed['declaration_group_check']['actual_count']), ('pass', 'e11-e15', 2))
        mismatch = reconcile_documents(po, invoice, policy=policy, declaration_groups=['TK-1'], effective_date='2026-06-01')
        self.assertEqual((mismatch['verdict'], mismatch['declaration_group_check']['result']), ('block', 'block'))
        missing = reconcile_documents(po, invoice, policy=policy, effective_date='2026-06-01')
        self.assertEqual((missing['verdict'], missing['declaration_group_check']['reason']), ('review', 'missing or invalid declaration groups'))
        self.assertTrue(all(line['result'] == 'pass' for line in missing['results']))
        expired = reconcile_documents(po, invoice, policy=policy, declaration_groups=['TK-1'], effective_date='2027-01-01')
        self.assertEqual((expired['verdict'], expired['declaration_group_check']['reason']), ('review', 'no applicable declaration group rule'))
        nonmatching = reconcile_documents(po, {**invoice, 'lines': [{**invoice['lines'][0], 'regime': 'E13'}]}, policy=policy, declaration_groups=['TK-1'], effective_date='2026-06-01')
        self.assertEqual(nonmatching['declaration_group_check']['reason'], 'no applicable declaration group rule')
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            reconcile_documents(po, invoice, policy={'declaration_group_rules': [
                policy['declaration_group_rules'][0], {**policy['declaration_group_rules'][0], 'rule_id': 'e11-e15-2'}]}, effective_date='2026-06-01')

    def test_fr405_line_regimes_use_explicit_po_and_invoice_lines(self):
        po = {'supplier': 'S', 'lines': [
            {'material_code': 'MATCH', 'regime': 'E11', 'quantity': 1, 'unit_price': 1},
            {'material_code': 'MISMATCH', 'regime': 'E15', 'quantity': 1, 'unit_price': 1},
        ]}
        invoice = {'supplier': 'S', 'regime': 'E13', 'lines': [
            {'material_code': 'MATCH', 'regime': 'E11', 'quantity': 1, 'unit_price': 1},
            {'material_code': 'MISMATCH', 'regime': 'E13', 'quantity': 1, 'unit_price': 1},
        ]}
        result = reconcile_documents(po, invoice)
        self.assertEqual((result['verdict'], [line['result'] for line in result['results']]), ('block', ['pass', 'block']))
        self.assertEqual(result['results'][1]['customs_regime_checks'][0], {
            'invoice_line': invoice['lines'][1], 'expected_regimes': ['E15'], 'actual_regime': 'E13',
            'result': 'block', 'reason': 'customs regime mismatch'})
        grouped = reconcile_documents(
            {'supplier': 'S', 'lines': [{'material_code': 'GROUP', 'regime': 'E11', 'quantity': 2, 'unit_price': 1}]},
            {'supplier': 'S', 'regime': 'E13', 'lines': [
                {'material_code': 'GROUP', 'regime': 'E11', 'quantity': 1, 'unit_price': 1},
                {'material_code': 'GROUP', 'quantity': 1, 'unit_price': 1},
            ]})
        self.assertEqual([line['result'] for line in grouped['results'][0]['customs_regime_checks']], ['pass', 'review'])
        self.assertEqual(grouped['results'][0]['customs_regime_checks'][1]['reason'], 'missing actual customs regime')
        missing_expected = reconcile_documents(
            {'supplier': 'S', 'lines': [{'material_code': 'MISSING', 'quantity': 1, 'unit_price': 1}]},
            {'supplier': 'S', 'lines': [{'material_code': 'MISSING', 'regime': 'E11', 'quantity': 1, 'unit_price': 1}]})
        self.assertEqual(missing_expected['results'][0]['customs_regime_checks'][0]['result'], 'review')
        conflicting = reconcile_documents(
            {'supplier': 'S', 'lines': [
                {'material_code': 'CONFLICT', 'regime': 'E11', 'quantity': 1, 'unit_price': 1},
                {'material_code': 'CONFLICT', 'regime': 'E15', 'quantity': 1, 'unit_price': 1},
            ]}, {'supplier': 'S', 'lines': [{'material_code': 'CONFLICT', 'regime': 'E11', 'quantity': 2, 'unit_price': 1}]})
        self.assertEqual(conflicting['results'][0]['customs_regime_checks'][0]['reason'], 'conflicting expected customs regimes')

    def test_fr402_no_material_default_is_policy_driven_not_core(self):
        po = {'supplier': 'S', 'lines': [
            {'custom_code': 'PO-NOMAT', 'description': 'No material item', 'quantity': 1, 'unit_price': 2}]}
        invoice = {'supplier': 'S', 'lines': [
            {'custom_code': 'PO-NOMAT', 'description': 'No material item', 'quantity': 1, 'unit_price': 2}]}
        rule_policy = {
            'no_material_behavior': 'custom_code',
            'allowed_regimes': ['E13'],
            'declaration_group_rules': [{'rule_id': 'e13-single', 'regimes': ['E13'], 'declaration_count': 1,
                                         'effective_from': '2026-01-01', 'effective_to': '2026-12-31'}],
        }
        assigned = reconcile_documents(po, invoice, policy=rule_policy,
                                       declaration_groups=['TK-1'], effective_date='2026-06-01')
        self.assertEqual(assigned['verdict'], 'pass')
        line = assigned['results'][0]
        self.assertEqual((line['regime'], line['result']), ('E13', 'pass'))
        self.assertEqual(line['customs_regime_checks'][0]['result'], 'pass')
        self.assertEqual(line['customs_regime_checks'][0]['actual_regime'], 'E13')
        self.assertEqual(line['customs_regime_checks'][0]['reason'], 'no-material custom_code regime assignment')
        self.assertEqual(assigned['declaration_group_check']['result'], 'pass')
        self.assertEqual((assigned['declaration_group_check']['rule_id'],
                          assigned['declaration_group_check']['actual_count']), ('e13-single', 1))
        other_regime = reconcile_documents(po, invoice,
                                           policy={'no_material_behavior': 'custom_code', 'allowed_regimes': ['E11']})
        self.assertEqual((other_regime['verdict'], other_regime['results'][0]['regime']), ('pass', 'E11'))
        defaulted = reconcile_documents(po, invoice, policy={'no_material_behavior': 'review'})
        self.assertEqual((defaulted['verdict'], defaulted['results'][0]['regime'],
                          defaulted['results'][0]['reason']), ('review', '', 'missing customs regime'))
        absent = reconcile_documents(po, invoice)
        self.assertEqual((absent['verdict'], absent['results'][0]['reason']), ('review', 'missing customs regime'))
        ambiguous = reconcile_documents(po, invoice,
                                        policy={'no_material_behavior': 'custom_code', 'allowed_regimes': ['E11', 'E13']})
        self.assertEqual((ambiguous['verdict'], ambiguous['results'][0]['reason']), ('review', 'missing customs regime'))

    def test_srs_11_2_description_similarity_is_candidate_only_never_pass(self):
        po_lines = [{'description': 'Stainless steel hex bolt M6', 'regime': 'E13', 'quantity': 1, 'unit_price': 1}]
        invoice_lines = [{'description': 'Stainless steel hex bolt M6 x 1', 'regime': 'E13', 'quantity': 1, 'unit_price': 1}]
        self.assertFalse(description_similarity_candidates(po_lines, invoice_lines, 0.99))
        with self.assertRaises(ValueError):
            description_similarity_candidates(po_lines, invoice_lines, 'not-a-number')
        with self.assertRaises(ValueError):
            description_similarity_candidates(po_lines, invoice_lines, 0)
        candidates = description_similarity_candidates(po_lines, invoice_lines, 0.50)
        self.assertTrue(candidates)
        self.assertEqual(candidates[0]['result'], 'candidate')
        self.assertNotIn('verdict', candidates[0])
        self.assertNotIn('pass', candidates[0])
        enabled = reconcile_documents({'lines': po_lines}, {'lines': invoice_lines},
                                      policy={'description_similarity': {'enabled': True}})
        self.assertEqual(enabled['verdict'], 'review')
        self.assertTrue(enabled['description_candidates'])
        self.assertGreaterEqual(enabled['description_candidates'][0]['description_similarity'], 0.50)
        disabled = reconcile_documents({'lines': po_lines}, {'lines': invoice_lines},
                                       policy={'description_similarity': {'enabled': False}})
        self.assertNotIn('description_candidates', disabled)
        default = reconcile_documents({'lines': po_lines}, {'lines': invoice_lines})
        self.assertNotIn('description_candidates', default)
        self.assertEqual(default['verdict'], 'review')

    def test_quantity_1_blocks_quantity_2_is_evidence_and_lines_group(self):
        result = reconcile_documents(
            {'supplier': 'S', 'lines': [{'material_code': 'M', 'remaining_quantity': 5, 'quantity': 5, 'unit_price': 2}]},
            {'supplier': 'S', 'regime': 'E13', 'lines': [
                {'material_code': 'M', 'quantity_1': 3, 'quantity_2': 100, 'unit_price': 2},
                {'material_code': 'M', 'quantity_1': 3, 'quantity_2': 200, 'unit_price': 2},
            ]}, policy={'regimes': {'E13': {'price_required': True}}})
        self.assertEqual(result['verdict'], 'block')
        self.assertEqual(result['results'][0]['quantity_2'], '300')
        self.assertTrue(result['results'][0]['quantity_2_evidence_only'])
        self.assertEqual(result['results'][0]['cardinality'], 'one-to-many')
