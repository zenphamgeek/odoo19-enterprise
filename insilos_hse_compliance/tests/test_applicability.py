# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import base64
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'insilos_hse_compliance')
class TestHSEApplicability(TransactionCase):

    def setUp(self):
        super(TestHSEApplicability, self).setUp()
        self.LegalDoc = self.env['is.hse.legal.document']
        self.LegalProv = self.env['is.hse.legal.provision']
        self.Facility = self.env['is.hse.facility']
        self.Register = self.env['is.hse.legal.register']
        self.hse_manager = new_test_user(
            self.env, login='hse-register-manager', groups='insilos_hse_compliance.group_hse_manager',
        )
        self.hse_user = new_test_user(
            self.env, login='hse-register-user', groups='insilos_hse_compliance.group_hse_user',
        )

        # Seed mandatory documents
        self.doc1 = self.LegalDoc.create({
            'name': 'Luật An toàn, vệ sinh lao động 84/2015/QH13',
            'code': 'TEST_LAW_84_2015',
            'authority_level': 'A1_MANDATORY_LAW',
            'category': 'safety',
            'issuer': 'National Assembly',
            'issued_date': '2015-06-25',
            'effective_date': '2016-07-01',
            'source_url': 'https://example.test/law-84-2015',
            'source_content_sha256': 'c' * 64,
            'source_version': '2015',
        })
        self.prov1 = self.LegalProv.create({
            'document_id': self.doc1.id,
            'article_number': 'Điều 18',
            'title': 'Kiểm soát các yếu tố nguy hiểm, có hại',
            'summary': 'Người sử dụng lao động phải định kỳ tổ chức đo đạc, đánh giá yếu tố có hại',
        })
        self.doc1.with_user(self.hse_manager).action_activate()

        self.facility = self.Facility.create({
            'name': 'Binh Duong Manufacturing Hub',
            'code': 'TEST_FAC_BD_01',
            'industry_type': 'metal_working',
            'worker_count': 250,
        })

    def test_evaluate_applicability_ignores_legacy_document_without_provenance(self):
        legacy = self.LegalDoc.create({
            'name': 'Legacy ungoverned law',
            'code': 'TEST_LEGACY_UNGOVERNED',
            'authority_level': 'A1_MANDATORY_LAW',
            'category': 'safety',
            'issuer': 'Government',
            'issued_date': '2015-01-01',
            'effective_date': '2015-02-01',
            'source_url': 'https://example.test/legacy',
            'source_content_sha256': 'd' * 64,
            'source_version': '2015',
        })
        legacy_provision = self.LegalProv.create({
            'document_id': legacy.id,
            'article_number': 'Điều legacy',
            'summary': 'Must not be generated without provenance',
        })
        legacy.with_user(self.hse_manager).action_activate()
        self.env.cr.execute(
            'UPDATE is_hse_legal_document SET source_url = NULL, source_content_sha256 = NULL, '
            'source_version = NULL, issuer = NULL, issued_date = NULL, effective_date = NULL WHERE id = %s',
            [legacy.id],
        )
        legacy.invalidate_recordset()
        register = self.Register.create({
            'name': 'Legal Register provenance gate',
            'facility_id': self.facility.id,
            'year': 2026,
        })

        register.with_user(self.hse_manager).action_evaluate_applicability()

        self.assertTrue(register.obligation_ids.filtered(lambda obligation: obligation.provision_id == self.prov1))
        self.assertFalse(register.obligation_ids.filtered(lambda obligation: obligation.provision_id == legacy_provision))

    def test_evaluate_applicability_ignores_amended_document_pending_governed_replacement(self):
        amended = self.LegalDoc.create({
            'name': 'Amended law pending governed replacement',
            'code': 'TEST_AMENDED_PENDING_REPLACEMENT',
            'authority_level': 'A1_MANDATORY_LAW',
            'category': 'safety',
            'issuer': 'Government',
            'issued_date': '2020-01-01',
            'effective_date': '2020-02-01',
            'source_url': 'https://example.test/amended-pending-replacement',
            'source_content_sha256': 'e' * 64,
            'source_version': '2020-01',
        })
        provision = self.LegalProv.create({
            'document_id': amended.id,
            'article_number': 'Điều amended',
            'summary': 'Must await a current active governed document',
        })
        self.env.cr.execute(
            "UPDATE is_hse_legal_document SET state = 'amended' WHERE id = %s", [amended.id],
        )
        amended.invalidate_recordset()
        self.assertFalse(amended.is_effective_on(date(2026, 12, 31)))
        register = self.Register.create({
            'name': 'Amended document gate',
            'facility_id': self.facility.id,
            'year': 2026,
        })

        register.with_user(self.hse_manager).action_evaluate_applicability()

        self.assertFalse(register.obligation_ids.filtered(lambda obligation: obligation.provision_id == provision))

    def test_01_evaluate_applicability_auto_populates_obligations(self):
        """Test action_evaluate_applicability populates active mandatory obligations."""
        register = self.Register.create({
            'name': 'Legal Register 2026 — Binh Duong Hub',
            'facility_id': self.facility.id,
            'year': 2026,
            'state': 'draft',
        })

        with self.assertRaises(UserError):
            register.with_user(self.hse_user).action_evaluate_applicability()
        register.with_user(self.hse_manager).action_evaluate_applicability()
        self.assertGreaterEqual(len(register.obligation_ids), 1)

        # Check obligation links
        ob = register.obligation_ids.filtered(lambda o: o.provision_id == self.prov1)
        self.assertTrue(ob)
        self.assertEqual(ob.authority_level, 'A1_MANDATORY_LAW')
        self.assertEqual(ob.compliance_status, 'not_assessed')

        with self.assertRaises(UserError):
            register.action_activate()
        with self.assertRaises(ValidationError):
            register.with_user(self.hse_manager).action_activate()

        with self.assertRaises(UserError):
            ob.write({'compliance_status': 'compliant'})

        reviewer = new_test_user(
            self.env, login='hse-obligation-reviewer', groups='insilos_hse_compliance.group_hse_manager',
        )
        with self.assertRaises(ValidationError):
            ob.with_user(reviewer).action_approve_compliance()

        attachment = self.env['ir.attachment'].create({
            'name': 'inspection-TEST-001.pdf',
            'datas': base64.b64encode(b'inspection evidence'),
            'res_model': ob._name,
            'res_id': ob.id,
            'company_id': ob.company_id.id,
        })
        ob.write({
            'evidence_summary': 'Verified inspection record TEST-001',
            'evidence_attachment_ids': [(4, attachment.id)],
        })
        with self.assertRaises(UserError):
            ob.action_approve_compliance()
        ob.with_user(reviewer).action_approve_compliance()
        self.assertEqual(ob.compliance_status, 'compliant')
        self.assertEqual(ob.compliance_approved_by_id, reviewer)
        with self.assertRaises(UserError):
            register.write({'state': 'active'})
        with self.assertRaises(UserError):
            register.write({'evaluation_date': '2026-12-31'})
        with self.assertRaises(UserError):
            register.action_activate()
        register.with_user(self.hse_manager).action_activate()
        self.assertEqual(register.state, 'active')

        for vals in (
            {'compliance_status': 'not_applicable'},
            {'compliance_status': 'partial'},
            {'compliance_status': 'non_compliant'},
            {'due_date': '2027-01-01'},
            {'provision_id': False},
            {'evidence_attachment_ids': [(5, 0, 0)]},
        ):
            with self.assertRaises(UserError):
                ob.with_user(self.hse_user).write(vals)
