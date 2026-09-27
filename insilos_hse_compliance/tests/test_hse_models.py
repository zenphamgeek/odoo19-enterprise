# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
from datetime import date
from pathlib import Path
from odoo import fields
from odoo.tests.common import TransactionCase, new_test_user, tagged
from odoo.exceptions import AccessError, UserError, ValidationError
from ..models.is_hse_compliance_event import _EVENT_CREATE_TOKEN
from ..models.is_hse_legal_document import _COMPLIANCE_EVENT_WRITE_CAPABILITY


@tagged('post_install', '-at_install', 'insilos_hse_compliance')
class TestHSEModels(TransactionCase):

    def setUp(self):
        super(TestHSEModels, self).setUp()
        self.LegalDoc = self.env['is.hse.legal.document']
        self.LegalProv = self.env['is.hse.legal.provision']
        self.Facility = self.env['is.hse.facility']
        self.Register = self.env['is.hse.legal.register']
        self.Obligation = self.env['is.hse.obligation']
        self.Chemical = self.env['is.hse.chemical.substance']
        self.SDS = self.env['is.hse.sds']
        self.OEL = self.env['is.hse.oel']
        self.Product = self.env['product.template']

    def test_01_legal_document_authority_and_validity(self):
        """Test legal document creation with 7-level authority and temporal checks."""
        doc = self.LegalDoc.create({
            'name': 'Quy chuẩn kỹ thuật quốc gia về chất lượng không khí xung quanh',
            'code': 'TEST_QCVN_05_2023',
            'authority_level': 'A2_MANDATORY_TECH_REG',
            'category': 'environment',
            'issuer': 'Bộ Tài nguyên và Môi trường',
            'issued_date': date(2023, 1, 1),
            'effective_date': date(2023, 9, 12),
            'source_url': 'https://example.test/qcvn-05-2023',
            'source_content_sha256': 'a' * 64,
            'source_version': '2023',
        })
        manager = new_test_user(
            self.env, login='hse-legal-authority-manager', groups='insilos_hse_compliance.group_hse_manager',
        )
        prov = self.LegalProv.create({
            'document_id': doc.id,
            'article_number': 'Mục 2.1',
            'title': 'Giới hạn nồng độ bụi TSP và PM2.5',
            'summary': 'Nồng độ PM2.5 trung bình 24 giờ không vượt quá 50 µg/m³',
        })
        doc.with_user(manager).action_activate()
        self.assertEqual(doc.authority_level, 'A2_MANDATORY_TECH_REG')
        self.assertTrue(doc.is_effective_on(date(2026, 8, 21)))
        self.assertFalse(doc.is_effective_on(date(2022, 1, 1)))
        self.assertEqual(doc.provision_count, 1)
        self.assertEqual(prov.authority_level, 'A2_MANDATORY_TECH_REG')

    def test_non_manager_cannot_create_or_alter_draft_legal_provenance(self):
        non_manager = new_test_user(self.env, login='hse-legal-draft-non-manager')
        with self.assertRaises(UserError):
            self.LegalDoc.with_user(non_manager).create({
                'name': 'Unapproved Draft', 'code': 'UNAPPROVED_DRAFT',
                'effective_date': date(2026, 2, 1),
                'source_url': 'https://example.test/unapproved',
                'source_content_sha256': 'a' * 64, 'source_version': '2026-01',
            })
        doc = self.LegalDoc.create({'name': 'Managed Draft', 'code': 'MANAGED_DRAFT'})
        with self.assertRaises(UserError):
            doc.with_user(non_manager).write({'effective_date': date(2026, 2, 1)})

    def test_active_legal_document_requires_provenance_but_draft_is_allowed(self):
        vals = {
            'name': 'Unverified Legal Document',
            'code': 'UNVERIFIED_ACTIVE',
            'authority_level': 'A1_MANDATORY_LAW',
            'state': 'active',
        }
        with self.assertRaises(UserError):
            self.LegalDoc.create(vals)
        vals['code'] = 'UNVERIFIED_DRAFT'
        vals['state'] = 'draft'
        draft = self.LegalDoc.create(vals)
        self.assertEqual(draft.state, 'draft')
        with self.assertRaises(UserError):
            draft.write({'state': 'active'})
        with self.assertRaises(ValidationError):
            draft.action_activate()

    def test_legal_document_activation_and_repeal_require_hse_manager(self):
        draft = self.LegalDoc.create({
            'name': 'Manager-controlled Legal Document',
            'code': 'MANAGER_CONTROLLED_LEGAL_DOC',
            'authority_level': 'A1_MANDATORY_LAW',
            'issuer': 'Government',
            'issued_date': date(2026, 1, 1),
            'effective_date': date(2026, 2, 1),
            'source_url': 'https://example.test/manager-controlled-law',
            'source_content_sha256': 'c' * 64,
            'source_version': '2026-01',
        })
        non_manager = new_test_user(self.env, login='hse-legal-non-manager')
        manager = new_test_user(
            self.env, login='hse-legal-manager', groups='insilos_hse_compliance.group_hse_manager',
        )

        with self.assertRaises(UserError):
            draft.with_user(non_manager).write({'state': 'active'})
        self.assertEqual(draft.state, 'draft')
        with self.assertRaises(UserError):
            draft.with_user(non_manager).action_activate()
        self.assertEqual(draft.state, 'draft')
        draft.with_user(manager).action_activate()
        self.assertEqual(draft.state, 'active')
        for state in ('active', 'amended', 'repealed'):
            with self.assertRaises(UserError):
                draft.with_user(manager).write({'state': state})
        with self.assertRaises(UserError):
            draft.with_user(non_manager).action_repeal()
        with self.assertRaises(UserError):
            draft.with_user(manager).sudo().action_repeal()
        self.assertEqual(draft.state, 'active')

    def test_02_facility_and_legal_register_metrics(self):
        """Test facility profile, legal register and compliance score calculation."""
        facility = self.Facility.create({
            'name': 'Test Plant Hai Phong',
            'code': 'TEST_FAC_HP_01',
            'industry_type': 'chemical',
            'worker_count': 120,
            'wastewater_capacity_m3_day': 150.0,
            'emission_classification': 'group_2',
            'fire_hazard_category': 'category_b',
            'has_hazardous_chemicals': True,
        })
        self.assertEqual(facility.industry_type, 'chemical')

        register = self.Register.create({
            'name': 'Legal Register 2026 — HP Plant',
            'facility_id': facility.id,
            'year': 2026,
            'state': 'draft',
        })
        self.assertEqual(register.compliance_score, 0.0)

        # Add obligations
        ob1 = self.Obligation.create({
            'register_id': register.id,
            'title': 'Quan trắc môi trường định kỳ quý',
            'compliance_status': 'partial',
        })
        ob2 = self.Obligation.create({
            'register_id': register.id,
            'title': 'Giấy phép xả thải bổ sung',
            'compliance_status': 'non_compliant',
        })

        register._compute_compliance_metrics()
        self.assertEqual(register.total_obligations, 2)
        self.assertEqual(register.compliant_count, 0)
        self.assertEqual(register.non_compliant_count, 1)
        self.assertEqual(register.compliance_score, 0.0)

    def test_generated_obligations_pending_and_event_requires_distinct_reviewer(self):
        facility = self.Facility.create({'name': 'Governance Plant', 'code': 'GOV_PLANT'})
        register = self.Register.create({'name': 'Governance Register', 'facility_id': facility.id})
        doc = self.LegalDoc.create({
            'name': 'Governance Law', 'code': 'GOV_LAW',
            'authority_level': 'A1_MANDATORY_LAW', 'issuer': 'Government',
            'issued_date': date(2026, 1, 1), 'effective_date': date(2026, 2, 1),
            'source_url': 'https://example.test/governance-law',
            'source_content_sha256': 'b' * 64, 'source_version': '2026-01',
        })
        manager = new_test_user(
            self.env, login='hse-governance-manager', groups='insilos_hse_compliance.group_hse_manager',
        )
        provision = self.LegalProv.create({'document_id': doc.id, 'article_number': 'Điều 1'})
        doc.with_user(manager).action_activate()
        register.with_user(manager).action_evaluate_applicability()
        obligation = self.Obligation.search([('register_id', '=', register.id), ('provision_id', '=', provision.id)])
        self.assertEqual(obligation.compliance_status, 'not_assessed')
        self.assertEqual(register.compliance_score, 0.0)

        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'GOV_EVENT', 'event_type': 'hse.legal.published', 'event_payload': '{}',
        }], _EVENT_CREATE_TOKEN)
        with self.assertRaises(UserError):
            event.action_apply_to_legal_register()
        event.action_mark_reviewed()
        with self.assertRaises(UserError):
            event.action_apply_to_legal_register()

    def test_workflow_write_cannot_forge_review_or_apply_metadata(self):
        reviewer = new_test_user(
            self.env, login='hse-workflow-reviewer', groups='insilos_hse_compliance.group_hse_manager',
        )
        applier = new_test_user(
            self.env, login='hse-workflow-applier', groups='insilos_hse_compliance.group_hse_manager',
        )
        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'FORGED_WORKFLOW_METADATA', 'event_type': 'hse.legal.published',
        }], _EVENT_CREATE_TOKEN)
        with self.assertRaises(UserError):
            event.with_user(reviewer)._write_workflow({
                'state': 'reviewed', 'reviewed_by_id': applier.id, 'reviewed_date': fields.Datetime.now(),
            })
        with self.assertRaises(UserError):
            event.with_user(reviewer)._write_workflow({'state': 'applied'})
        event.with_user(reviewer).action_mark_reviewed()
        with self.assertRaises(UserError):
            event.with_user(reviewer)._write_workflow({'state': 'applied'})
        self.assertEqual(event.state, 'reviewed')
        self.assertEqual(event.reviewed_by_id, reviewer)

    def test_non_manager_cannot_review_event_via_rpc(self):
        reviewer = new_test_user(self.env, login='hse-non-manager-reviewer')
        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'NON_MANAGER_REVIEW', 'event_type': 'hse.legal.published', 'event_payload': '{}',
        }], _EVENT_CREATE_TOKEN)
        with self.assertRaises(UserError):
            event.with_user(reviewer).action_mark_reviewed()
        self.assertEqual(event.state, 'new')

    def test_non_manager_cannot_ignore_event_and_manager_can_ignore_new_or_reviewed_event(self):
        non_manager = new_test_user(self.env, login='hse-non-manager-ignorer')
        manager = new_test_user(
            self.env, login='hse-event-ignore-manager', groups='insilos_hse_compliance.group_hse_manager',
        )
        new_event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'NON_MANAGER_IGNORE', 'event_type': 'hse.legal.published', 'event_payload': '{}',
        }], _EVENT_CREATE_TOKEN)
        with self.assertRaises(UserError):
            new_event.with_user(non_manager).action_ignore()
        self.assertEqual(new_event.state, 'new')
        new_event.with_user(manager).action_ignore()
        self.assertEqual(new_event.state, 'ignored')

        reviewed_event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'MANAGER_IGNORE_REVIEWED', 'event_type': 'hse.legal.published', 'event_payload': '{}',
        }], _EVENT_CREATE_TOKEN)
        reviewed_event.with_user(manager).action_mark_reviewed()
        reviewed_event.with_user(manager).action_ignore()
        self.assertEqual(reviewed_event.state, 'ignored')

    def test_reviewed_event_requires_hse_manager_to_apply(self):
        applier = new_test_user(self.env, login='hse-non-manager-applier')
        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'NON_MANAGER_APPLY', 'event_type': 'hse.legal.published', 'event_payload': '{}',
        }], _EVENT_CREATE_TOKEN)
        event.action_mark_reviewed()
        with self.assertRaises(UserError):
            event.with_user(applier).action_apply_to_legal_register()
        self.assertEqual(event.state, 'reviewed')

    def test_reviewed_non_legal_event_cannot_apply_to_legal_register(self):
        reviewer = new_test_user(
            self.env, login='hse-non-legal-reviewer', groups='insilos_hse_compliance.group_hse_manager',
        )
        applier = new_test_user(
            self.env, login='hse-non-legal-applier', groups='insilos_hse_compliance.group_hse_manager',
        )
        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'NON_LEGAL_APPLY', 'event_type': 'hse.general_notice', 'event_payload': '{}',
        }], _EVENT_CREATE_TOKEN)
        event.with_user(reviewer).action_mark_reviewed()
        with self.assertRaises(UserError):
            event.with_user(applier).action_apply_to_legal_register()
        self.assertEqual(event.state, 'reviewed')

    def test_reviewed_event_rejects_missing_legal_provenance(self):
        applier = new_test_user(
            self.env, login='hse-provenance-applier', groups='insilos_hse_compliance.group_hse_manager',
        )
        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'MISSING_PROVENANCE', 'event_type': 'hse.legal.published',
            'event_payload': json.dumps({'document': {'code': 'UNTRUSTED'}}),
        }], _EVENT_CREATE_TOKEN)
        event.action_mark_reviewed()
        with self.assertRaises(UserError):
            event.with_user(applier).action_apply_to_legal_register()
        self.assertEqual(event.state, 'reviewed')
        self.assertFalse(self.LegalDoc.search([('code', '=', 'UNTRUSTED')]))

    def test_reviewed_event_applies_explicit_verified_legal_document(self):
        applier = new_test_user(
            self.env, login='hse-verified-applier', groups='insilos_hse_compliance.group_hse_manager',
        )
        payload = {'document': {
            'code': 'VERIFIED_HSE_001', 'name': 'Verified HSE Law', 'issuer': 'Government',
            'authority_level': 'A1_MANDATORY_LAW', 'category': 'safety',
            'issued_date': '2026-01-01', 'effective_date': '2026-02-01', 'state': 'active',
            'source_url': 'https://vanban.chinhphu.vn/verified-hse-001',
            'source_content_sha256': 'a' * 64, 'source_version': '2026-01',
            'provisions': [{'article_number': 'Điều 1', 'title': 'Scope', 'summary': 'Verified obligation'}],
        }}
        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'VERIFIED_EVENT', 'event_type': 'hse.legal.published',
            'event_payload': json.dumps(payload),
        }], _EVENT_CREATE_TOKEN)
        event.action_mark_reviewed()
        event.with_user(applier).action_apply_to_legal_register()
        doc = self.LegalDoc.search([('code', '=', payload['document']['code'])])
        self.assertEqual(event.state, 'applied')
        self.assertEqual(doc.source_url, payload['document']['source_url'])
        self.assertEqual(doc.source_content_sha256, payload['document']['source_content_sha256'])
        self.assertEqual(doc.provision_count, 1)

    def test_active_legal_document_rejects_direct_material_and_provision_writes(self):
        doc = self.LegalDoc.create({
            'name': 'Immutable Law', 'code': 'IMMUTABLE_LEGAL_DOC',
            'issuer': 'Government', 'issued_date': date(2026, 1, 1),
            'effective_date': date(2026, 2, 1), 'source_url': 'https://example.test/immutable-law',
            'source_content_sha256': 'd' * 64, 'source_version': '2026-01',
        })
        provision = self.LegalProv.create({
            'document_id': doc.id, 'article_number': 'Điều 1', 'title': 'Scope', 'summary': 'Original',
        })
        manager = new_test_user(
            self.env, login='hse-immutable-manager', groups='insilos_hse_compliance.group_hse_manager',
        )
        doc.with_user(manager).action_activate()
        with self.assertRaises(UserError):
            doc.write({'source_url': 'https://example.test/tampered-law'})
        with self.assertRaises(UserError):
            provision.write({'summary': 'Tampered'})
        with self.assertRaises(UserError):
            doc.write({'provision_ids': [(1, provision.id, {'summary': 'Tampered'})]})

    def test_draft_legal_document_can_be_amended_before_activation(self):
        doc = self.LegalDoc.create({
            'name': 'Draft Law', 'code': 'DRAFT_AMENDABLE_LEGAL_DOC',
        })
        doc.write({
            'name': 'Amended Draft Law', 'issuer': 'Government', 'issued_date': date(2026, 1, 1),
            'effective_date': date(2026, 2, 1), 'source_url': 'https://example.test/draft-law',
            'source_content_sha256': 'e' * 64, 'source_version': '2026-01', 'summary': 'Draft summary',
        })
        self.assertEqual(doc.name, 'Amended Draft Law')
        self.assertEqual(doc.source_version, '2026-01')

    def test_reviewed_event_updates_active_document_with_distinct_hash_and_version(self):
        manager = new_test_user(
            self.env, login='hse-replacement-manager', groups='insilos_hse_compliance.group_hse_manager',
        )
        doc = self.LegalDoc.create({
            'name': 'Original Law', 'code': 'EVENT_REPLACEMENT_LEGAL_DOC',
            'issuer': 'Government', 'issued_date': date(2026, 1, 1),
            'effective_date': date(2026, 2, 1), 'source_url': 'https://example.test/original-law',
            'source_content_sha256': 'f' * 64, 'source_version': '2026-01',
        })
        doc.with_user(manager).action_activate()
        payload = {'document': {
            'code': doc.code, 'name': 'Replacement Law', 'issuer': 'Government',
            'authority_level': 'A1_MANDATORY_LAW', 'category': 'general',
            'issued_date': '2026-01-01', 'effective_date': '2026-02-01', 'state': 'active',
            'source_url': 'https://example.test/replacement-law',
            'source_content_sha256': '0' * 64, 'source_version': '2026-02',
            'provisions': [{'article_number': 'Điều 1', 'title': 'Scope', 'summary': 'Replacement'}],
        }}
        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'EVENT_REPLACEMENT', 'event_type': 'hse.legal.published',
            'event_payload': json.dumps(payload),
        }], _EVENT_CREATE_TOKEN)
        event.action_mark_reviewed()
        event.with_user(manager).action_apply_to_legal_register()
        self.assertEqual(doc.source_content_sha256, '0' * 64)
        self.assertEqual(doc.source_version, '2026-02')
        self.assertEqual(doc.provision_ids.summary, 'Replacement')
        self.assertEqual(event.state, 'applied')

    def test_reviewed_event_rejects_amended_payload_without_updating_active_document(self):
        manager = new_test_user(
            self.env, login='hse-reused-version-manager', groups='insilos_hse_compliance.group_hse_manager',
        )
        doc = self.LegalDoc.create({
            'name': 'Original Law', 'code': 'EVENT_REUSED_LEGAL_DOC', 'issuer': 'Government',
            'issued_date': date(2026, 1, 1), 'effective_date': date(2026, 2, 1),
            'source_url': 'https://example.test/original-law',
            'source_content_sha256': '1' * 64, 'source_version': '2026-01',
        })
        doc.with_user(manager).action_activate()
        payload = {'document': {
            'code': doc.code, 'name': 'Altered Law', 'issuer': 'Government',
            'authority_level': 'A1_MANDATORY_LAW', 'category': 'general',
            'issued_date': '2026-01-01', 'effective_date': '2026-02-01', 'state': 'amended',
            'source_url': 'https://example.test/altered-law',
            'source_content_sha256': '2' * 64, 'source_version': '2026-02',
            'provisions': [{'article_number': 'Điều 1', 'title': 'Scope', 'summary': 'Altered'}],
        }}
        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'EVENT_REUSED_VERSION', 'event_type': 'hse.legal.published',
            'event_payload': json.dumps(payload),
        }], _EVENT_CREATE_TOKEN)
        event.action_mark_reviewed()
        with self.assertRaises(UserError):
            event.with_user(manager).action_apply_to_legal_register()
        self.assertEqual(doc.source_content_sha256, '1' * 64)
        self.assertEqual(doc.source_version, '2026-01')
        self.assertEqual(event.state, 'reviewed')

    def test_03_chemical_sds_and_product_linkage(self):
        """Test chemical substance, SDS 16-section, OEL and product template auto-assignment."""
        chem = self.Chemical.create({
            'name': 'Acetone Pure',
            'cas_number': 'TEST_67-64-1',
            'un_number': 'UN 1090',
            'formula': 'C3H6O',
            'hazard_classification': 'conditional',
            'ghs_signal_word': 'danger',
            'ghs_flammable': True,
            'ghs_toxic': False,
        })

        sds = self.SDS.create({
            'name': 'SDS Acetone 99.5%',
            'substance_id': chem.id,
            'supplier_name': 'Chemical Supplier Co.',
            'sec1_identification': 'Acetone Industrial Grade',
            'sec9_physical_chemical': 'Flash point: -20 C',
        })

        oel = self.OEL.create({
            'substance_id': chem.id,
            'authority': 'BYT_QCVN03',
            'twa_mg_m3': 500.0,
            'stel_mg_m3': 1000.0,
        })
        self.assertEqual(chem.sds_count, 1)

        # Create product template linked to chemical
        product = self.Product.create({
            'name': 'Dung môi Acetone 200L',
            'chemical_substance_id': chem.id,
        })
        product._onchange_chemical_substance_id()
        self.assertTrue(product.is_hazardous_chemical)
        self.assertEqual(product.cas_number, 'TEST_67-64-1')
        self.assertEqual(product.ghs_signal_word, 'danger')
        self.assertTrue(product.ghs_flammable)
        self.assertEqual(product.sds_id.id, sds.id)

    def test_04_product_compliance_permits(self):
        """Test accompanying permits, validity tracking and linkage to products."""
        Permit = self.env['is.hse.product.permit']
        today = date.today()

        chem = self.Chemical.create({
            'name': 'Toluene Industrial',
            'cas_number': 'TEST_108-88-3',
            'hazard_classification': 'conditional',
        })

        permit = Permit.create({
            'name': 'Giấy chứng nhận đủ điều kiện kinh doanh hóa chất',
            'permit_number': 'TEST_128_GCN_SCT',
            'permit_type': 'conditional_cert',
            'issuing_authority': 'Sở Công Thương TP.HCM',
            'chemical_substance_id': chem.id,
            'issue_date': today,
            'expiry_date': date(today.year + 3, today.month, today.day),
        })
        self.assertEqual(permit.state, 'draft')

        # Product linked to permit
        product = self.Product.create({
            'name': 'Dung môi Toluene 200L Phuy',
            'chemical_substance_id': chem.id,
            'permit_ids': [(4, permit.id)],
        })
        self.assertEqual(product.permit_count, 1)
        self.assertFalse(product.has_valid_permits)
        self.assertEqual(permit.product_count, 1)
        with self.assertRaises(UserError):
            permit.sudo().write({'state': 'valid'})

        # Test action
        action = product.action_view_hse_permits()
        self.assertEqual(action.get('res_model'), 'is.hse.product.permit')
        self.assertIn(permit.id, action.get('domain')[0][2])

        # Test expired permit
        expired_permit = Permit.create({
            'name': 'Giấy phép vận chuyển hết hạn',
            'permit_number': 'TEST_EXPIRED_PERMIT_001',
            'permit_type': 'transport_permit',
            'issue_date': date(2020, 1, 1),
            'expiry_date': date(2021, 1, 1),
        })
        self.assertEqual(expired_permit.state, 'draft')

    def test_compliance_approval_checks_evidence_read_access(self):
        source = (Path(__file__).parents[1] / 'models/is_hse_legal_register.py').read_text()
        action = source[source.index('    def action_approve_compliance(self):'):]
        self.assertIn("obligation.evidence_attachment_ids.check_access('read')", action)
        self.assertIn("obligation.evidence_attachment_ids.check_access_rule('read')", action)
        self.assertLess(action.index("check_access('read')"), action.index('super(HSEObligation, obligation).write'))

    def test_approved_obligation_evidence_is_immutable(self):
        manager = new_test_user(
            self.env, login='hse-evidence-manager', groups='insilos_hse_compliance.group_hse_manager',
        )
        facility = self.Facility.create({'name': 'Evidence Plant', 'code': 'EVIDENCE_PLANT'})
        register = self.Register.create({'name': 'Evidence Register', 'facility_id': facility.id})
        obligation = self.Obligation.create({
            'register_id': register.id,
            'title': 'Evidence-protected obligation',
        })
        evidence = self.env['ir.attachment'].create({
            'name': 'inspection.pdf',
            'raw': b'approved evidence',
            'res_model': obligation._name,
            'res_id': obligation.id,
            'company_id': obligation.company_id.id,
        })
        obligation.write({
            'evidence_summary': 'Signed inspection report.',
            'evidence_attachment_ids': [(4, evidence.id)],
        })
        obligation.with_user(manager).action_approve_compliance()
        with self.assertRaises(UserError):
            evidence.write({'raw': b'tampered'})
        with self.assertRaises(UserError):
            evidence.unlink()

    def test_recorded_event_is_immutable_for_hse_manager(self):
        manager = new_test_user(
            self.env, login='hse-audit-manager', groups='insilos_hse_compliance.group_hse_manager',
        )
        event = self.env['is.hse.compliance.event']._create_from_signed_webhook([{
            'event_id': 'IMMUTABLE_EVENT', 'event_payload': '{"source": "webhook"}',
        }], _EVENT_CREATE_TOKEN)
        manager_event = event.with_user(manager)
        with self.assertRaises(UserError):
            manager_event.write({'event_payload': '{"source": "altered"}'})
        with self.assertRaises(UserError):
            manager_event.unlink()
        with self.assertRaises(UserError):
            manager_event.write({'state': 'ignored'})
        manager_event.action_ignore()
        self.assertEqual(event.state, 'ignored')
        with self.assertRaises(AccessError):
            self.env['is.hse.compliance.event'].sudo().create({
                'event_id': 'FORGED_SUDO_EVENT',
                'event_payload': '{"source_timestamp": "2020-01-01T00:00:00"}',
                'state': 'applied',
            })
        with self.assertRaises(AccessError):
            self.env['is.hse.sync.log'].with_user(manager).create({
                'sync_channel': 'manual', 'message': 'fabricated log',
            })
