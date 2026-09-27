import base64
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from .common import unique_fixture


@tagged('post_install', '-at_install', 'logistics_idp')
class TestLogisticsIdpWizardLifecycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.operator = new_test_user(
            cls.env, login=unique_fixture('wizard-operator'), email=False,
            context={'no_reset_password': True},
            groups='insilos_logistics_idp.group_logistics_operator',
        )
        cls.manager = new_test_user(
            cls.env, login=unique_fixture('wizard-manager'), email=False,
            context={'no_reset_password': True},
            groups='insilos_logistics_idp.group_logistics_manager',
        )

    def setUp(self):
        super().setUp()
        token = unique_fixture(self._testMethodName)
        self.case = self.env['logistics.idp.case'].create({
            'name': 'WIZARD-' + token,
            'source_system': 'fixture',
            'source_key': token,
            'source_version': '1',
            'provenance': 'synthetic',
            'effective_date': fields.Date.today(),
            'owner_id': self.operator.id,
        })

    def test_upload_wizard_creates_processing_document_for_owned_case(self):
        content = b'%PDF-1.4\n/Type /Page\n%%EOF\n' + unique_fixture('upload').encode()
        wizard = self.env['logistics.idp.document.upload.wizard'].with_user(self.operator).create({
            'case_id': self.case.id,
            'company_id': self.case.company_id.id,
            'filename': unique_fixture('document') + '.pdf',
            'content': base64.b64encode(content),
            'mimetype': 'application/pdf',
        })
        with patch('odoo.addons.insilos_logistics_idp.models.logistics_idp.IAPDocumentProcessor.process') as process:
            self.assertEqual(wizard.action_upload(), {'type': 'is.actions.act_window_close'})
        document = self.case.document_ids
        self.assertEqual((len(document), document.status, document.case_id), (1, 'processing', self.case))
        process.assert_not_called()

    def test_waiting_resume_creates_immutable_transition_evidence(self):
        since = fields.Datetime.now()
        self.assertTrue(self.case.with_user(self.operator).action_set_waiting(
            'supplier', 'Awaiting corrected invoice', since=since))
        self.assertEqual((self.case.state, self.case.waiting_party), ('waiting_external', 'supplier'))
        self.assertTrue(self.case.with_user(self.operator).action_resume())
        evidence = self.case.evidence_ids.filtered(lambda item: item.category == 'waiting_transition')
        self.assertEqual((len(evidence), set(evidence.mapped('status'))), (2, {'review', 'valid'}))
        with self.assertRaises(UserError):
            evidence.unlink()

    def test_only_manager_completes_ready_case(self):
        self.case.write({
            'document_status': 'pass', 'reconciliation_status': 'pass',
            'compliance_status': 'pass', 'output_status': 'not_applicable',
        })
        self.env['logistics.idp.check.result']._controlled_create({
            'case_id': self.case.id, 'code': 'IMPORT_DECLARATION', 'required': True,
            'verdict': 'pass', 'rationale': 'synthetic fixture', 'payload': {},
        }, 'wizard_lifecycle_test')
        self.case._derive_lifecycle()
        self.assertEqual((self.case.state, self.case.verdict), ('ready', 'pass'))
        with self.assertRaises(UserError):
            self.case.with_user(self.operator).action_complete('unauthorized')
        self.assertTrue(self.case.with_user(self.manager).action_complete('reviewed fixture'))
        self.assertEqual(self.case.state, 'completed')
