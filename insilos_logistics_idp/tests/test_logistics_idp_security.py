import json
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user as _new_test_user, tagged

from ..models.logistics_idp import _INTERNAL_CASE_LIFECYCLE_TOKEN
from .common import new_logistics_test_user, unique_fixture


def new_test_user(env, **values):
    return new_logistics_test_user(_new_test_user, env, **values)


@tagged('post_install', '-at_install', 'security_negative')
class TestLogisticsIdpSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.operator = new_test_user(cls.env, login='log-sec-operator', groups='insilos_logistics_idp.group_logistics_operator')
        cls.reviewer = new_test_user(cls.env, login='log-sec-reviewer', groups='insilos_logistics_idp.group_logistics_reviewer')
        cls.auditor = new_test_user(cls.env, login='log-sec-auditor', groups='insilos_logistics_idp.group_logistics_auditor')
        cls.steward = new_test_user(cls.env, login='log-sec-steward', groups='insilos_logistics_idp.group_master_data_steward')
        cls.admin = cls.env.ref('base.user_admin')
        cls.manager = new_test_user(cls.env, login='log-sec-manager', groups='insilos_logistics_idp.group_logistics_manager')
        cls.integration = new_test_user(
            cls.env, login='log-sec-migration-service',
            groups='insilos_logistics_idp.group_logistics_integration')
        cls.other = new_test_user(cls.env, login='log-sec-other', groups='insilos_logistics_idp.group_logistics_operator')
        cls.case = cls.env['logistics.idp.case'].create({
            'name': 'SECURITY', 'source_system': 'fixture', 'source_key': unique_fixture('SECURITY'),
            'source_version': 'v1', 'provenance': 'synthetic', 'effective_date': '2026-01-01',
            'owner_id': cls.operator.id,
        })

    def test_inbound_recovery_is_manager_only_and_audited(self):
        values = {
            'profile_code': 'fixture', 'source_system': 'fixture',
            'source_key': unique_fixture('recovery'), 'source_version': '1',
            'payload': json.dumps({'name': 'fixture', 'provenance': 'fixture',
                                   'effective_date': '2026-01-01'}),
            'state': 'dead', 'attempt_count': 3,
        }
        job = self.env['logistics.idp.inbound.job'].with_user(self.manager).create(values)
        with self.assertRaises(AccessError):
            job.with_user(self.operator).action_retry()
        job.with_user(self.manager).action_retry()
        self.assertEqual((job.state, job.attempt_count, job.last_error), ('retry', 2, False))
        self.assertTrue(job.message_ids.filtered(lambda message: 'Inbound job recovery: retry' in message.body))
        job.with_user(self.manager).action_cancel()
        self.assertEqual(job.state, 'cancelled')
        job.with_user(self.manager).action_requeue()
        self.assertEqual((job.state, job.attempt_count), ('pending', 0))

    def test_pdf_caller_context_and_metadata_cannot_bypass_iap_or_classification(self):
        bypasses = (
            {'fixture': 'timeout'}, {'provider_response': {'document_type': 'invoice'}},
            {'document_type': 'invoice', 'document_type_trusted': True},
            {'document_type': 'invoice', 'structured': {'invoice_number': 'FORGED'}},
        )
        router = type(self.env['openrouter.router'])
        for index, metadata in enumerate(bypasses):
            binary = b'%PDF-1.4\n<</Type /Page>>\n%% bypass ' + str(index).encode() + b'\n%%EOF'
            responses = [
                {'choices': [{'message': {'content': json.dumps({'document_type': 'purchase_order', 'confidence': .95})}}]},
                {'model': 'vision-model', 'choices': [{'message': {'content': json.dumps({
                    'document_type': 'purchase_order', 'confidence': .95,
                    'payload': {'supplier': 'SUP', 'po_reference': 'PO-%s' % index, 'lines': [{}]},
                    'source_spans': []})}}]},
            ]
            with patch.object(router, 'complete', autospec=True, side_effect=responses) as complete:
                document = self.env['logistics.idp.document'].with_user(self.operator).with_context(
                    logistics_idp_local_ocr=True).intake_content(self.case, binary, 'application/pdf', metadata)
            self.assertEqual(document.document_type, 'purchase_order')
            self.assertEqual(document.current_run_id.provider, 'insilos-iap-openrouter')
            self.assertEqual(len(complete.call_args_list), 2)

    def test_pdf_filename_cannot_bypass_iap_classification(self):
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        responses = [
            {'choices': [{'message': {'content': json.dumps({'document_type': 'purchase_order', 'confidence': .95})}}]},
            {'model': 'vision-model', 'choices': [{'message': {'content': json.dumps({
                'document_type': 'purchase_order', 'confidence': .95,
                'payload': {'supplier': 'SUP', 'po_reference': 'PO-123', 'lines': [{}]}, 'source_spans': []})}}]},
        ]
        router = type(self.env['openrouter.router'])
        with patch.object(router, 'complete', autospec=True, side_effect=responses) as complete:
            document = self.env['logistics.idp.document'].with_user(self.operator).intake_content(
                self.case, binary, 'application/pdf', {'filename': 'PO_123.pdf'})
        payload = json.loads(document.current_run_id.payload)
        self.assertEqual(document.document_type, 'purchase_order')
        self.assertEqual(document.current_run_id.provider, 'insilos-iap-openrouter')
        self.assertEqual(len(complete.call_args_list), 2)
        self.assertEqual(payload['classification_source'], 'iap_multimodal')
        self.assertNotEqual(payload['classification_source'], 'deterministic_metadata')

    def test_test_mode_synthetic_pdf_entrypoint_is_local(self):
        binary = b'%PDF-1.4\n<</Type /Page>>\n%%EOF'
        document = self.env['logistics.idp.document'].with_user(self.operator)._intake_synthetic_content(
            self.case, binary, 'application/pdf', {'document_type': 'invoice', 'confidence': 1,
                                                    'payload': {'supplier': 'SUP', 'invoice_number': 'SYN', 'lines': [{}]}})
        self.assertEqual((document.current_run_id.provider, document.document_type),
                         ('local-deterministic', 'invoice'))

    def test_ops008_reassignment_and_duplicate_rpc_guards(self):
        target = self.env['logistics.idp.case'].create({
            'name': 'OPS008 TARGET', 'source_system': 'fixture', 'source_key': unique_fixture('ops008-target'),
            'source_version': 'v1', 'provenance': 'synthetic', 'effective_date': '2026-01-01',
            'owner_id': self.operator.id,
        })
        document = self.env['logistics.idp.document'].intake_content(
            self.case, unique_fixture('ops008-document').encode(), 'application/pdf', process=False)
        with self.assertRaises(UserError):
            document.with_user(self.operator).with_context(_logistics_document_assignment=True).write({'case_id': target.id})
        foreign = self.env['res.company'].create({'name': 'OPS008 Foreign'})
        self.operator.company_ids |= foreign
        foreign_case = target.with_company(foreign).copy({
            'name': 'OPS008 FOREIGN', 'company_id': foreign.id, 'source_key': unique_fixture('ops008-foreign'),
        })
        with self.assertRaises(ValidationError):
            document.with_user(self.operator).action_assign_case(foreign_case)
        target.with_context(_logistics_case_lifecycle=_INTERNAL_CASE_LIFECYCLE_TOKEN).write({'state': 'completed', 'completion_reason': 'fixture'})
        with self.assertRaises(ValidationError):
            document.with_user(self.operator).action_assign_case(target)
        target.with_context(_logistics_case_lifecycle=_INTERNAL_CASE_LIFECYCLE_TOKEN).write({'state': 'collecting', 'completion_reason': False})
        self.case.with_context(_logistics_case_lifecycle=_INTERNAL_CASE_LIFECYCLE_TOKEN).write({'state': 'completed', 'completion_reason': 'fixture'})
        with self.assertRaises(ValidationError):
            document.with_user(self.operator).action_assign_case(target)
        self.case.with_context(_logistics_case_lifecycle=_INTERNAL_CASE_LIFECYCLE_TOKEN).write({'state': 'collecting', 'completion_reason': False})
        with self.assertRaises(UserError):
            target.with_user(self.reviewer).mark_semantic_duplicate(self.case)
        self.assertTrue(target.with_user(self.manager).mark_semantic_duplicate(self.case))
        evidence = (target | self.case).evidence_ids.filtered(lambda item: item.category == 'semantic_duplicate')
        self.assertEqual(len(evidence), 2)
        self.assertTrue(all(item.audit_actor_id == self.manager for item in evidence))

    def test_document_duplicate_marker_denies_self_cross_company_terminal_unauthorized_and_remap(self):
        canonical = self.env['logistics.idp.document'].intake_content(
            self.case, unique_fixture('document-marker-canonical').encode(), 'application/pdf', process=False)
        source_case = self.env['logistics.idp.case'].create({
            'name': 'DOCUMENT MARKER', 'source_system': 'fixture', 'source_key': unique_fixture('document-marker'),
            'source_version': 'v1', 'provenance': 'synthetic', 'effective_date': '2026-01-01', 'owner_id': self.operator.id,
        })
        source = self.env['logistics.idp.document'].intake_content(
            source_case, unique_fixture('document-marker-source').encode(), 'application/pdf', process=False)
        with self.assertRaises(UserError):
            source.with_user(self.reviewer).action_mark_duplicate(canonical)
        with self.assertRaisesRegex(ValidationError, 'distinct canonical'):
            source.with_user(self.operator).action_mark_duplicate(source)
        foreign_company = self.env['res.company'].create({'name': unique_fixture('document-marker-foreign')})
        foreign_case = self.env['logistics.idp.case'].with_company(foreign_company).create({
            'name': 'DOCUMENT MARKER FOREIGN', 'company_id': foreign_company.id, 'source_system': 'fixture',
            'source_key': unique_fixture('document-marker-foreign'), 'source_version': 'v1', 'provenance': 'synthetic',
            'effective_date': '2026-01-01',
        })
        foreign = self.env['logistics.idp.document'].with_company(foreign_company).intake_content(
            foreign_case, unique_fixture('document-marker-foreign-document').encode(), 'application/pdf', process=False)
        self.operator.company_ids |= foreign_company
        with self.assertRaisesRegex(ValidationError, 'same company'):
            source.with_user(self.operator).action_mark_duplicate(foreign)
        canonical.with_context(_logistics_case_lifecycle=_INTERNAL_CASE_LIFECYCLE_TOKEN).case_id.write({'state': 'completed', 'completion_reason': 'fixture'})
        with self.assertRaisesRegex(ValidationError, 'terminal'):
            source.with_user(self.operator).action_mark_duplicate(canonical)
        canonical.with_context(_logistics_case_lifecycle=_INTERNAL_CASE_LIFECYCLE_TOKEN).case_id.write({'state': 'collecting', 'completion_reason': False})
        source.with_user(self.operator).action_mark_duplicate(canonical)
        alternative = self.env['logistics.idp.document'].intake_content(
            self.case, unique_fixture('document-marker-alternative').encode(), 'application/pdf', process=False)
        with self.assertRaisesRegex(ValidationError, 'cannot be remapped'):
            source.with_user(self.operator).action_mark_duplicate(alternative)

    def test_open_source_email_denies_missing_ambiguous_cross_company_non_email_and_unauthorized(self):
        reference = '<source-email-deny-%s@example.test>' % unique_fixture('source-email')
        document = self.env['logistics.idp.document'].intake_content(
            self.case, b'source-email-deny', 'application/pdf', {'source_message_reference': reference},
            source_channel='email', process=False)
        with self.assertRaisesRegex(ValidationError, 'missing or ambiguous'):
            document.with_user(self.operator).action_open_source_email()
        self.env['mail.message'].create({'message_id': reference, 'message_type': 'comment',
                                         'record_company_id': self.env.company.id})
        with self.assertRaisesRegex(ValidationError, 'missing or ambiguous'):
            document.with_user(self.operator).action_open_source_email()
        self.env['mail.message'].create({'message_id': reference, 'message_type': 'email',
                                         'record_company_id': self.env.company.id})
        self.env['mail.message'].create({'message_id': reference, 'message_type': 'email',
                                         'record_company_id': self.env.company.id})
        with self.assertRaisesRegex(ValidationError, 'missing or ambiguous'):
            document.with_user(self.operator).action_open_source_email()
        non_email = self.env['logistics.idp.document'].intake_content(
            self.case, b'non-email-source', 'application/pdf', {'source_message_reference': reference},
            source_channel='upload', process=False)
        with self.assertRaisesRegex(ValidationError, 'no persisted source email'):
            non_email.with_user(self.operator).action_open_source_email()
        foreign_company = self.env['res.company'].create({'name': unique_fixture('source-email-foreign')})
        self.operator.company_ids |= foreign_company
        foreign_case = self.env['logistics.idp.case'].with_company(foreign_company).create({
            'name': 'SOURCE EMAIL FOREIGN', 'company_id': foreign_company.id, 'source_system': 'fixture',
            'source_key': unique_fixture('source-email-foreign'), 'source_version': 'v1',
            'provenance': 'synthetic', 'effective_date': '2026-01-01',
        })
        cross_company_reference = '<source-email-cross-%s@example.test>' % unique_fixture('source-email')
        cross_company_document = self.env['logistics.idp.document'].intake_content(
            self.case, b'cross-company-source-email', 'application/pdf',
            {'source_message_reference': cross_company_reference}, source_channel='email', process=False)
        self.env['mail.message'].with_company(foreign_company).create({
            'message_id': cross_company_reference, 'message_type': 'email', 'record_company_id': foreign_company.id})
        with self.assertRaisesRegex(ValidationError, 'missing or ambiguous'):
            cross_company_document.with_user(self.operator).action_open_source_email()
        with self.assertRaises(AccessError):
            document.with_user(self.auditor).action_open_source_email()

    def test_inbox_candidate_projection_excludes_foreign_company_and_cannot_reassign(self):
        thread = unique_fixture('inbox-candidate-thread')
        foreign_company = self.env['res.company'].create({'name': unique_fixture('inbox-candidate-foreign')})
        foreign_case = self.env['logistics.idp.case'].with_company(foreign_company).create({
            'name': 'INBOX FOREIGN', 'company_id': foreign_company.id, 'source_system': 'fixture',
            'source_key': unique_fixture('inbox-candidate-foreign'), 'source_version': 'v1',
            'provenance': 'fixture', 'effective_date': '2026-01-01', 'thread_reference': thread,
        })
        document = self.env['logistics.idp.document'].intake_content(
            self.case, unique_fixture('inbox-candidate-document').encode(), 'application/pdf',
            {'source_message_reference': thread}, process=False)
        before = (document.case_id, self.env['logistics.idp.case'].search_count([]),
                  self.env['logistics.idp.document'].search_count([]))
        self.assertFalse(document.with_user(self.operator).related_case_candidate_id)
        self.assertIn('Review / assign case', document.with_user(self.operator).inbox_action_required)
        self.assertEqual(before, (document.case_id, self.env['logistics.idp.case'].search_count([]),
                                  self.env['logistics.idp.document'].search_count([])))
        with self.assertRaises(ValidationError):
            document.with_user(self.operator).action_assign_case(foreign_case)

    def test_inbox_wizard_preserves_assignment_authority_and_blocks_direct_type_write(self):
        document = self.env['logistics.idp.document'].intake_content(
            self.case, unique_fixture('wizard-security').encode(), 'application/pdf', process=False)
        target = self.env['logistics.idp.case'].create({
            'name': 'WIZARD SECURITY', 'source_system': 'fixture', 'source_key': unique_fixture('wizard-target'),
            'source_version': 'v1', 'provenance': 'synthetic', 'effective_date': '2026-01-01',
        })
        with self.assertRaises(UserError):
            document.with_user(self.operator).write({'document_type': 'invoice'})
        wizard = self.env['logistics.idp.document.inbox.wizard'].with_user(self.reviewer).create({
            'document_id': document.id, 'case_id': target.id, 'document_type': 'invoice'})
        with self.assertRaisesRegex(UserError, 'operators or managers'):
            wizard.action_apply()
        self.assertEqual(document.case_id, self.case)

    def test_fr106_thread_history_is_company_scoped_and_intake_controlled(self):
        values = {'name': 'FR106', 'source_system': 'fixture', 'source_key': unique_fixture('fr106'),
                  'source_version': '1', 'provenance': 'synthetic', 'effective_date': '2026-01-01',
                  'supplier_reference': 'FR106', 'email_subject': 'Subject'}
        case = self.env['logistics.idp.case'].intake(values)
        entry = case.email_thread_entry_ids
        with self.assertRaises(AccessError):
            entry.with_user(self.manager).write({'active': False})
        foreign_company = self.env['res.company'].create({'name': unique_fixture('fr106-foreign')})
        foreign = self.env['logistics.idp.case'].with_company(foreign_company).intake({
            **values, 'source_key': unique_fixture('fr106-foreign'), 'company_id': foreign_company.id})
        self.assertNotEqual(foreign, case)
        self.assertEqual((len(case.email_thread_entry_ids), len(foreign.email_thread_entry_ids)), (1, 1))
        with self.assertRaises(AccessError):
            self.env['logistics.idp.email.thread.entry'].with_user(self.manager).with_company(foreign_company).search([
                ('id', '=', entry.id)])

    def test_fr107_active_thread_selection_denies_unauthorized_and_cross_company(self):
        active = self.env['logistics.idp.case'].create({
            'name': 'FR107 ACTIVE', 'source_system': 'fixture', 'source_key': unique_fixture('fr107-active'),
            'source_version': 'v1', 'provenance': 'synthetic', 'effective_date': '2026-01-01',
            'supplier_reference': 'FR107', 'email_subject': 'Subject A', 'thread_reference': 'active-thread',
        })
        ambiguous = self.env['logistics.idp.case'].intake({
            'name': 'FR107 AMBIGUOUS', 'source_system': 'fixture', 'source_key': unique_fixture('fr107-ambiguous'),
            'source_version': 'v1', 'provenance': 'synthetic', 'effective_date': '2026-01-01',
            'supplier_reference': 'FR107', 'email_subject': 'Subject B', 'thread_reference': 'ambiguous-thread',
        })
        with self.assertRaises(UserError):
            ambiguous.with_user(self.operator).action_select_active_thread(active)
        foreign_company = self.env['res.company'].create({'name': unique_fixture('fr107-foreign')})
        foreign = self.env['logistics.idp.case'].with_company(foreign_company).create({
            'name': 'FR107 FOREIGN', 'company_id': foreign_company.id, 'source_system': 'fixture',
            'source_key': unique_fixture('fr107-foreign'), 'source_version': 'v1', 'provenance': 'synthetic',
            'effective_date': '2026-01-01', 'thread_reference': 'foreign-thread',
        })
        with self.assertRaises(ValidationError):
            ambiguous.with_user(self.reviewer).action_select_active_thread(foreign)
        unrelated = self.env['logistics.idp.case'].create({
            'name': 'FR107 UNRELATED', 'source_system': 'fixture', 'source_key': unique_fixture('fr107-unrelated'),
            'source_version': '1', 'provenance': 'synthetic', 'effective_date': '2026-01-01',
            'supplier_reference': 'OTHER', 'thread_reference': 'unrelated-thread',
        })
        for target in (False, unrelated):
            with self.assertRaises(ValidationError):
                ambiguous.with_user(self.reviewer).action_select_active_thread(target)
        active.with_context(_logistics_case_lifecycle=_INTERNAL_CASE_LIFECYCLE_TOKEN).write({'state': 'completed', 'completion_reason': 'fixture'})
        with self.assertRaises(ValidationError):
            ambiguous.with_user(self.reviewer).action_select_active_thread(active)
        self.assertTrue(ambiguous.activity_ids.filtered(
            lambda activity: activity.summary == 'FR-107: Select active supplier email thread'))

    def test_unassigned_operator_cannot_read_case(self):
        self.assertFalse(self.env['logistics.idp.case'].with_user(self.other).search([('id', '=', self.case.id)]))

    def test_auditor_cannot_mutate(self):
        with self.assertRaises(AccessError):
            self.case.with_user(self.auditor).write({'name': 'fabricated'})

    def test_exception_audit_center_excludes_foreign_company_and_exposes_no_write_context(self):
        foreign = self.env['res.company'].create({'name': 'Audit Foreign'})
        foreign_case = self.env['logistics.idp.case'].with_company(foreign).create({
            'name': 'AUDIT FOREIGN', 'source_system': 'fixture', 'source_key': unique_fixture('audit-foreign'),
            'source_version': 'v1', 'provenance': 'synthetic', 'effective_date': '2026-01-01', 'company_id': foreign.id,
        })
        self.env['logistics.idp.exception'].with_company(foreign).create({
            'case_id': foreign_case.id, 'exception_type': 'extraction_failure'})
        model = self.env['logistics.idp.case'].with_user(self.auditor)
        action = model.action_open_exception_audit_center()
        self.assertNotIn(foreign_case, model.search(action['domain']))
        self.assertEqual(action['context'], {'create': False, 'edit': False, 'delete': False})
        with self.assertRaises(AccessError):
            self.case.with_user(self.auditor).write({'name': 'fabricated'})

    def test_operator_processing_creates_internal_critical_check_but_direct_create_is_denied(self):
        document = self.env['logistics.idp.document'].with_user(self.operator)._intake_synthetic_content(
            self.case, unique_fixture('critical-check-acl').encode(), 'application/json',
            {'document_type': 'invoice', 'confidence': 1, 'payload': {'invoice_number': 'ACL', 'lines': [{}]}})
        check = self.case.check_result_ids.filtered(
            lambda item: item.run_id == document.current_run_id and item.code == 'EXTRACTION_CRITICAL_INPUTS')
        self.assertEqual((len(check), check.case_id, check.run_id), (1, self.case, document.current_run_id))
        check_model = self.env['logistics.idp.check.result'].with_user(self.operator)
        with self.assertRaises(AccessError):
            check_model.check_access('create')
        with self.assertRaises(UserError):
            check_model.create({'case_id': self.case.id, 'code': 'FORGED', 'rationale': 'forged', 'payload': {}})

    def test_check_result_fabrication_and_mutation_are_blocked_even_with_sudo(self):
        values = {
            'case_id': self.case.id, 'code': 'FORGED_REQUIRED_PASS', 'required': True,
            'verdict': 'pass', 'rationale': 'forged', 'payload': {'run_hash': 'forged'},
        }
        checks = self.env['logistics.idp.check.result'].sudo()
        with self.assertRaises(UserError):
            checks._controlled_create(values, 'rpc_forgery')
        with self.assertRaises(UserError):
            checks._create_from_check_runner(values, 'rpc_forgery')
        document = self.env['logistics.idp.document']._intake_synthetic_content(
            self.case, unique_fixture('check-write').encode(), 'application/json',
            {'document_type': 'invoice', 'confidence': 1, 'payload': {'invoice_number': 'CHECK', 'lines': [{}]}})
        check = self.case.check_result_ids.filtered(lambda item: item.run_id == document.current_run_id)
        with self.assertRaises(UserError):
            check.sudo().write({'verdict': 'pass', 'payload': {'forged': True}})

    def test_direct_snapshot_fabrication_blocked(self):
        values = {'case_id': self.case.id, 'category': 'invoice', 'source_reference': 'rpc', 'payload': {}}
        with self.assertRaises(UserError):
            self.env['logistics.idp.evidence'].with_user(self.operator).create(values)
        with self.assertRaises(UserError):
            self.env['logistics.idp.evidence'].with_user(self.auditor).create(values)

    def test_direct_case_pass_verdict_is_blocked(self):
        for context in ({}, {'_logistics_case_lifecycle': True}):
            with self.subTest(context=context), self.assertRaises(UserError):
                self.case.with_user(self.manager).with_context(**context).write({'verdict': 'pass'})

    def test_case_lifecycle_and_material_data_direct_rpc_bypasses_are_blocked(self):
        forged = self.env['logistics.idp.case'].with_user(self.manager).create({
            'name': 'FORGED LIFECYCLE', 'source_system': 'fixture', 'source_key': unique_fixture('forged-lifecycle'),
            'source_version': '1', 'provenance': 'synthetic', 'effective_date': '2026-01-01',
            'state': 'completed', 'verdict': 'pass',
        })
        self.assertEqual((forged.state, forged.verdict), ('collecting', 'review'))
        with self.assertRaises(UserError):
            forged.with_context(_logistics_case_lifecycle=True).write({'state': 'completed'})
        forged.write({'state': 'review'})
        with self.assertRaises(UserError):
            forged.write({'po_reference': 'FORGED-PO'})

    def test_operator_cannot_complete_or_generate_output(self):
        with self.assertRaises(UserError):
            self.case.with_user(self.operator).action_complete('fabricated')
        with self.assertRaises(UserError):
            self.env['logistics.idp.output'].with_user(self.operator).generate(self.case, 'e13', {'lines': []})

    def test_dashboard_roles_have_required_read_only_sources(self):
        for user in (self.operator, self.reviewer, self.auditor):
            model = self.env['logistics.idp.case'].with_user(user)
            model.get_dashboard_data({'company_ids': [self.env.company.id]})
            for source in ('logistics.idp.extraction.run', 'logistics.idp.check.result', 'logistics.idp.output', 'logistics.idp.exception'):
                self.env[source].with_user(user).check_access('read')
        for source in ('logistics.idp.check.result', 'logistics.idp.output'):
            with self.assertRaises(AccessError):
                self.env[source].with_user(self.operator).check_access('write')

    def test_override_direct_mutation_and_delete_are_blocked(self):
        exception = self.env['logistics.idp.exception'].create({
            'case_id': self.case.id, 'exception_type': 'missing_document'})
        values = {
            'case_id': self.case.id, 'exception_ids': [(6, 0, exception.ids)],
            'reason_code': 'evidence_gap', 'justification': 'forged', 'requested_by': self.manager.id,
            'requested_at': '2026-01-01 00:00:00', 'state': 'approved', 'payload': {},
        }
        with self.assertRaises(UserError):
            self.env['logistics.idp.override'].with_user(self.manager).create(values)
        with self.assertRaises(UserError):
            self.env['logistics.idp.override'].with_user(self.manager).with_context(
                _logistics_snapshot_token=True)._controlled_create(values, 'forged')
        override = self.case.with_user(self.manager).request_override(
            exception, 'evidence_gap', 'controlled override')
        with self.assertRaises(UserError):
            override.with_user(self.manager).write({
                'state': 'approved', 'approved_by': self.manager.id,
                'approved_at': '2026-01-01 00:00:00',
            })
        with self.assertRaises(UserError):
            override.with_user(self.manager).unlink()

    def test_admin_override_acl_preserves_immutable_semantics(self):
        access = self.env.ref('insilos_logistics_idp.access_logistics_override_admin')
        self.assertTrue(access.active and access.perm_read and access.perm_create)
        self.assertFalse(access.perm_write or access.perm_unlink)
        self.env['logistics.idp.override'].with_user(self.admin).check_access('read')
        self.env['logistics.idp.case'].with_user(self.admin).get_dashboard_data(
            {'company_ids': [self.env.company.id]})

    def test_migration_principal_upgrade_is_idempotent(self):
        manager = self.env.ref('insilos_logistics_idp.group_logistics_manager')
        integration = self.env.ref('insilos_logistics_idp.group_logistics_integration')
        self.integration.sudo().write({'group_ids': [(4, manager.id)]})
        self.env['ir.config_parameter'].sudo().set_param(
            'logistics_idp.migration_service_login', self.integration.login)
        model = self.env['logistics.idp.case']
        self.assertEqual(model._upgrade_migration_service_principal(), self.integration)
        first = self.integration.group_ids
        self.assertEqual(model._upgrade_migration_service_principal().group_ids, first)
        self.assertTrue(integration <= first)
        self.assertNotIn(manager, first)
        with self.assertRaises(UserError):
            model.with_user(self.integration).action_complete('forged')

    def test_srs_5_1_security_matrix_fails_closed(self):
        groups = {
            'operator': 'insilos_logistics_idp.group_logistics_operator',
            'reviewer': 'insilos_logistics_idp.group_logistics_reviewer',
            'manager': 'insilos_logistics_idp.group_logistics_manager',
            'steward': 'insilos_logistics_idp.group_master_data_steward',
            'admin': 'insilos_logistics_idp.group_logistics_admin',
            'auditor': 'insilos_logistics_idp.group_logistics_auditor',
            'integration': 'insilos_logistics_idp.group_logistics_integration',
        }
        users = {
            'operator': self.operator, 'reviewer': self.reviewer, 'manager': self.manager,
            'steward': self.steward, 'admin': self.admin, 'auditor': self.auditor,
            'integration': self.integration,
        }
        for role, group_xmlid in groups.items():
            if role != 'admin':
                self.assertTrue(users[role].has_group(group_xmlid))
        manager_group = self.env.ref(groups['manager'])
        self.assertNotIn(manager_group, self.integration.group_ids)
        for role, user in users.items():
            if role == 'manager':
                continue
            with self.assertRaises(UserError):
                self.case.with_user(user).action_complete('forged')
        for user in (self.auditor, self.integration):
            with self.assertRaises(UserError):
                self.case.with_user(user).action_set_waiting('supplier', 'forged')
        for user in (self.operator, self.reviewer, self.manager, self.auditor, self.admin):
            self.env['logistics.idp.override'].with_user(user).check_access('read')

    def test_compliance_context_rejects_cross_company_before_normalization(self):
        foreign = self.env['res.company'].create({'name': 'Context Foreign Company'})
        context = {
            'schema_version': '1.0', 'company_id': foreign.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'SYNTHETIC'},
            'when': '2026-08-12', 'transaction_time': '2026-08-12T00:00:00Z',
            'effective_time': '2026-08-12T00:00:00Z', 'recorded_time': '2026-08-12T23:59:59Z',
            'evidence': [],
        }
        with self.assertRaisesRegex(ValidationError, 'company is not allowed'):
            self.env['logistics.idp.policy.source'].with_user(self.operator).validate_compliance_context(
                context, self.case)

    def test_compliance_context_rejects_fake_ids_run_mismatch_and_bad_timestamps(self):
        document = self.env['logistics.idp.document'].with_user(self.operator).with_context(
            logistics_idp_local_ocr=True).intake_content(
                self.case, b'{"document_type":"master_data","confidence":1,"payload":{}}',
                'application/json', {'filename': unique_fixture('security.json')})
        other = self.env['logistics.idp.document'].with_user(self.operator).with_context(
            logistics_idp_local_ocr=True).intake_content(
                self.case, b'{"document_type":"master_data","confidence":1,"payload":{"x":1}}',
                'application/json', {'filename': unique_fixture('other.json')})
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'fixture'}, 'when': '2026-08-12',
            'transaction_time': '2026-08-12T00:00:00Z', 'effective_time': '2026-08-12T00:00:00Z',
            'recorded_time': '2026-08-12T23:59:59Z',
            'evidence': [{'document_id': document.id, 'field': 'policy', 'source_kind': 'document',
                          'source_hash': document.content_hash,
                          'extraction_run_id': document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
        }
        model = self.env['logistics.idp.policy.source']
        with self.assertRaisesRegex(ValidationError, 'real document'):
            model.validate_compliance_context({**context, 'evidence': [{**context['evidence'][0], 'document_id': 0}]})
        with self.assertRaisesRegex(ValidationError, 'does not exist'):
            model.validate_compliance_context({**context, 'evidence': [{**context['evidence'][0], 'document_id': 2147483647}]})
        with self.assertRaisesRegex(ValidationError, 'does not belong'):
            model.validate_compliance_context({**context, 'evidence': [{**context['evidence'][0], 'extraction_run_id': other.current_run_id.id}]})
        with self.assertRaisesRegex(ValidationError, 'timezone-aware'):
            model.validate_compliance_context({**context, 'transaction_time': '2026-08-12T00:00:00'})
        with self.assertRaisesRegex(ValidationError, 'ordering'):
            model.validate_compliance_context({**context, 'recorded_time': '2026-08-11T00:00:00Z'})

    def test_trade_g1_extraction_provenance_and_multicompany_binding_fail_closed(self):
        document = self.env['logistics.idp.document'].with_user(self.operator).with_context(
            logistics_idp_local_ocr=True).intake_content(
                self.case, b'{"document_type":"master_data","confidence":1,"payload":{}}',
                'application/json', {'filename': unique_fixture('trade-g1.json')})
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'fixture'}, 'when': '2026-08-12',
            'transaction_time': '2026-08-12T00:00:00Z', 'effective_time': '2026-08-12T00:00:00Z',
            'recorded_time': '2026-08-12T23:59:59Z',
            'evidence': [{'document_id': document.id, 'field': 'policy', 'source_kind': 'extraction_run',
                          'source_hash': document.current_run_id.payload_hash,
                          'extraction_run_id': document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
        }
        model = self.env['logistics.idp.policy.source']
        self.assertEqual(model.validate_compliance_context(context, self.case)['verdict'], 'pass')
        evidence = context['evidence'][0]
        for authority, patch, message in (
                ('authoritative_tier_1', {'source_hash': '0' * 64}, 'extraction run'),
                ('authoritative_tier_2', {}, 'exceeds'),
                ('authoritative_tier_1', {'source_kind': 'forged'}, 'source kind')):
            invalid = {**context, 'authority': authority, 'evidence': [{**evidence, **patch}]}
            with self.assertRaisesRegex(ValidationError, message):
                model.validate_compliance_context(invalid, self.case)
        foreign = self.env['res.company'].create({'name': unique_fixture('Trade G1 Foreign')})
        self.operator.company_ids |= foreign
        foreign_case = self.env['logistics.idp.case'].with_company(foreign).with_user(self.operator).create({
            'name': 'TRADE G1 FOREIGN', 'company_id': foreign.id, 'source_system': 'fixture',
            'source_key': unique_fixture('trade-g1-foreign'), 'source_version': '1',
            'provenance': 'synthetic', 'effective_date': '2026-08-12', 'owner_id': self.operator.id,
        })
        foreign_document = self.env['logistics.idp.document'].with_company(foreign).with_user(self.operator).with_context(
            logistics_idp_local_ocr=True).intake_content(
                foreign_case, b'{"document_type":"master_data","confidence":1,"payload":{}}',
                'application/json', {'filename': unique_fixture('trade-g1-foreign.json')})
        with self.assertRaisesRegex(ValidationError, 'ownership does not match'):
            model.validate_compliance_context({
                **context, 'evidence': [{**evidence, 'document_id': foreign_document.id,
                                          'extraction_run_id': foreign_document.current_run_id.id,
                                          'source_hash': foreign_document.current_run_id.payload_hash}],
            }, self.case)

    def test_policy_import_denies_non_manager_principals(self):
        for user in (self.operator, self.reviewer, self.integration):
            with self.assertRaisesRegex(UserError, 'Managers or Administrators'):
                self.env['logistics.idp.policy.source'].with_user(user).import_candidate({})

    def test_activation_ledger_is_read_only_and_service_controlled(self):
        model = self.env['logistics.idp.policy.activation']
        for user in (self.reviewer, self.manager, self.auditor):
            model.with_user(user).check_access('read')
            with self.assertRaises(AccessError):
                model.with_user(user).check_access('create')
        with self.assertRaises(UserError):
            model.with_user(self.manager).create({})
        with self.assertRaisesRegex(UserError, 'non-integration Logistics Manager'):
            model.with_user(self.integration).submit(
                self.env['logistics.idp.policy.source'].search([], limit=1),
                None, None, 1, {}, 'forged')

    def test_dashboard_authorized_roles_and_company_scope(self):
        foreign = self.env['res.company'].create({'name': 'Security Foreign Company'})
        foreign_case = self.case.copy({
            'name': 'FOREIGN', 'company_id': foreign.id,
            'source_key': unique_fixture('FOREIGN'), 'owner_id': False,
        })
        for user in (self.operator, self.reviewer, self.manager, self.auditor):
            dashboard = self.env['logistics.idp.case'].with_user(user).get_dashboard_data(
                {'company_ids': [self.env.company.id]})
            self.assertTrue(dashboard['metrics']['stp_rate']['available'])
            self.assertNotIn(foreign_case.id, [row['id'] for row in dashboard['live_queue']])
            state = next(row['state'] for row in dashboard['case_states'] if row['state'] == self.case.state)
            action = self.env['logistics.idp.case'].with_user(user).dashboard_drilldown(
                'case_state', {'company_ids': [self.env.company.id]}, state)
            visible_ids = self.env[action['res_model']].with_user(user).search(action['domain']).ids
            self.assertIn(self.case.id, visible_ids)
            self.assertNotIn(foreign_case.id, visible_ids)
            with self.assertRaises(ValidationError):
                self.env['logistics.idp.case'].with_user(user).get_dashboard_data({'company_ids': [foreign.id]})

    def test_policy_source_rejects_generic_and_forged_service_mutations(self):
        model = self.env['logistics.idp.policy.source']
        policy = model.search([], limit=1)
        values = {
            'code': unique_fixture('FORGED-POLICY'), 'version': '1',
            'jurisdiction': 'VN', 'regime': 'ALL', 'source_tier': 'demo',
            'citation': 'fixture', 'effective_from': '2030-01-01', 'payload': policy.payload,
        }
        for user in (self.manager, self.integration, self.admin):
            rpc = model.with_user(user)
            with self.assertRaisesRegex(AccessError, 'trusted policy service'):
                rpc.create(values)
            with self.assertRaisesRegex(AccessError, 'trusted policy service'):
                rpc._controlled_create(values, 'forged')
            with self.assertRaisesRegex(AccessError, 'trusted policy service'):
                policy.with_user(user).write({'state': 'retired'})
            with self.assertRaisesRegex(UserError, 'cannot be deleted'):
                policy.with_user(user).unlink()

    def test_policy_workspace_is_read_only_for_auditor_and_company_isolated(self):
        policy = self.env['logistics.idp.policy.source'].search([], limit=1)
        self.assertTrue(policy.with_user(self.auditor).exists())
        with self.assertRaises(UserError):
            policy.with_user(self.auditor).write({'citation': 'fabricated'})
        foreign = self.env['res.company'].create({'name': 'Policy Foreign Company'})
        foreign_policy = self.env['logistics.idp.policy.source']._controlled_create({
            'code': unique_fixture('FOREIGN-POLICY'), 'version': '1', 'company_id': foreign.id,
            'jurisdiction': 'VN', 'regime': 'ALL', 'source_tier': 'customer_reference',
            'citation': 'fixture', 'effective_from': '2026-01-01', 'payload': policy.payload,
        }, 'test_fixture')
        self.assertFalse(self.env['logistics.idp.policy.source'].with_user(self.manager).search([
            ('id', '=', foreign_policy.id)]))

    def test_rpc_activation_is_blocked_for_every_user_and_authority_class(self):
        baseline = self.env['logistics.idp.policy.source'].search([], limit=1)
        users = (self.operator, self.reviewer, self.auditor, self.manager, self.integration, self.env.ref('base.user_admin'))
        tiers = dict(self.env['logistics.idp.policy.source']._fields['source_tier'].selection)
        for tier in tiers:
            draft = self.env['logistics.idp.policy.source']._controlled_create({
                'code': unique_fixture('BLOCKED-%s' % tier), 'version': '1',
                'company_id': self.env.company.id, 'jurisdiction': 'VN', 'regime': 'ALL',
                'source_tier': tier, 'citation': 'https://example.invalid/authority',
                'effective_from': '2030-01-01', 'payload': baseline.payload,
            }, 'test_fixture')
            for user in users:
                with self.assertRaisesRegex(UserError, 'Direct policy activation is forbidden'):
                    draft.with_user(user).action_activate()
            self.assertEqual(draft.state, 'draft')

    def test_policy_history_upgrade_requires_trusted_loader_token(self):
        with self.assertRaisesRegex(AccessError, 'trusted policy loader'):
            self.env['logistics.idp.policy.source'].with_user(self.admin)._upgrade_effective_policy_history()

    def test_retire_requires_manager_and_active_legacy_customer_reference(self):
        active = self.env['logistics.idp.policy.source'].search([
            ('state', '=', 'active'), ('source_tier', '=', 'customer_reference')], limit=1)
        if active:
            with self.assertRaisesRegex(UserError, 'Only Logistics Managers'):
                active.with_user(self.operator).action_retire()
            with self.assertRaisesRegex(UserError, 'Only Logistics Managers'):
                active.with_user(self.integration).action_retire()
        draft = self.env['logistics.idp.policy.source']._controlled_create({
            'code': unique_fixture('RETIRE-DRAFT'), 'version': '1',
            'company_id': self.env.company.id, 'jurisdiction': 'VN', 'regime': 'ALL',
            'source_tier': 'customer_reference', 'citation': 'fixture',
            'effective_from': '2030-01-01',
            'payload': self.env['logistics.idp.policy.source'].search([], limit=1).payload,
        }, 'test_fixture')
        with self.assertRaisesRegex(UserError, 'Only active legacy Customer Reference'):
            draft.with_user(self.manager).action_retire()
