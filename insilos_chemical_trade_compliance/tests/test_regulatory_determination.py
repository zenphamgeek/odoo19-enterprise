# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_chemical_trade_compliance')
class TestRegulatoryDetermination(TransactionCase):

    def setUp(self):
        super(TestRegulatoryDetermination, self).setUp()
        self.Rule = self.env['is.chemical.regulatory.rule']
        self.Chemical = self.env['is.hse.chemical.substance']
        self.Dossier = self.env['is.chemical.compliance.dossier']
        self.DossierLine = self.env['is.chemical.compliance.dossier.line']
        self.legal_document = self.env['is.hse.legal.document'].create({
            'name': 'Official chemical rule test source',
            'code': 'TEST-CHEMICAL-RULE-2026',
            'issuer': 'Test Authority',
            'issued_date': '2026-01-01',
            'effective_date': '2026-01-01',
            'source_url': 'https://official.example.test/chemical-rule',
            'source_content_sha256': 'a' * 64,
            'source_version': '2026.1',
        })
        self.legal_document.action_activate()

        # Setup standard rules with test-specific CAS
        self.rule_toluene = self.Rule.create({
            'name': 'Khai báo NSW Toluene Test',
            'rule_category': 'mandatory_nsw_declaration',
            'cas_number': 'TEST-108-88-3',
            'hs_code': '2902.30.00',
            'threshold_concentration': 1.0,
            'nsw_procedure_code': 'BCT00001',
            'legal_basis': 'Official test provision',
            'legal_document_id': self.legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        })
        self.rule_sulfuric = self.Rule.create({
            'name': 'Giấy phép Axit Sulfuric Test',
            'rule_category': 'restricted_chemical_license',
            'cas_number': 'TEST-7664-93-9',
            'hs_code': '2807.00.00',
            'threshold_concentration': 50.0,
            'required_permit_type': 'restricted_license',
            'nsw_procedure_code': 'BCT00002',
            'legal_basis': 'Official test provision',
            'legal_document_id': self.legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        })
        self.rule_prohibited = self.Rule.create({
            'name': 'Hóa chất Cấm Aldrin Test',
            'rule_category': 'prohibited_chemical_block',
            'cas_number': 'TEST-309-00-2',
            'threshold_concentration': 0.0,
            'legal_basis': 'Official test provision',
            'legal_document_id': self.legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        })
        rules = self.rule_toluene + self.rule_sulfuric + self.rule_prohibited
        rules.action_submit_for_review()
        approver = self.env['res.users'].create({
            'name': 'Determination Rule Approver', 'login': 'determination-rule-approver@example.test',
            'group_ids': [(6, 0, [
                self.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_manager').id,
                self.env.ref('insilos_hse_compliance.group_hse_manager').id,
            ])],
        })
        rules.with_user(approver).action_activate()

    def test_01_evaluate_nsw_declaration_obligation(self):
        """Test matching NSW declaration rule for Toluene above threshold."""
        rules = self.Rule.evaluate_chemical_obligations(cas_number='TEST-108-88-3', concentration=99.5)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].rule_category, 'mandatory_nsw_declaration')

        # Below threshold should not match
        rules_low = self.Rule.evaluate_chemical_obligations(cas_number='TEST-108-88-3', concentration=0.5)
        self.assertEqual(len(rules_low), 0)

    def test_02_scopes_rules_by_effective_date_and_jurisdiction(self):
        self.assertTrue(self.Rule.evaluate_chemical_obligations(
            cas_number='TEST-108-88-3', concentration=99.5, effective_date='2026-06-01', jurisdiction='VN'))
        self.assertFalse(self.Rule.evaluate_chemical_obligations(
            cas_number='TEST-108-88-3', concentration=99.5, effective_date='2027-01-01', jurisdiction='VN'))
        self.assertFalse(self.Rule.evaluate_chemical_obligations(
            cas_number='TEST-108-88-3', concentration=99.5, effective_date='2026-06-01', jurisdiction='US'))

    def test_03_evaluate_restricted_license_obligation(self):
        """Test matching Restricted License rule for concentrated Sulfuric Acid."""
        rules = self.Rule.evaluate_chemical_obligations(cas_number='TEST-7664-93-9', concentration=98.0)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].rule_category, 'restricted_chemical_license')
        self.assertEqual(rules[0].nsw_procedure_code, 'BCT00002')

    def test_04_dossier_evaluation_workflow(self):
        """Test complete evaluation on a multi-line compliance dossier."""
        dossier = self.Dossier.create({
            'name': 'DOS-TEST-EVAL-001',
            'dossier_type': 'general_compliance',
            'line_ids': [
                (0, 0, {
                    'trade_name': 'Toluene Solvent 99.5%',
                    'cas_number': 'TEST-108-88-3',
                    'concentration_percentage': 99.5,
                    'net_weight_kg': 1000.0,
                }),
                (0, 0, {
                    'trade_name': 'Sulfuric Acid 98%',
                    'cas_number': 'TEST-7664-93-9',
                    'concentration_percentage': 98.0,
                    'net_weight_kg': 5000.0,
                }),
            ]
        })

        dossier.action_evaluate_obligations()
        self.assertEqual(dossier.state, 'evaluating')
        self.assertTrue(dossier.has_restricted_chemicals)
        self.assertTrue(dossier.requires_nsw_declaration)
        
        line1 = dossier.line_ids.filtered(lambda l: l.cas_number == 'TEST-108-88-3')
        self.assertEqual(line1.regulatory_status, 'nsw_required')

        line2 = dossier.line_ids.filtered(lambda l: l.cas_number == 'TEST-7664-93-9')
        self.assertEqual(line2.regulatory_status, 'license_required')

    def test_05_manual_or_unmatched_rules_require_review_and_block_nsw(self):
        self.Rule.create({
            'name': 'Ungoverned manual rule',
            'rule_category': 'mandatory_nsw_declaration',
            'cas_number': 'TEST-UNTRUSTED',
            'nsw_procedure_code': 'BCT00001',
            'active': False,
        })
        self.assertFalse(self.Rule.evaluate_chemical_obligations(
            cas_number='TEST-UNTRUSTED', effective_date='2026-06-01'))
        dossier = self.Dossier.create({
            'invoice_date': '2026-06-01',
            'line_ids': [(0, 0, {
                'trade_name': 'Unmatched chemical',
                'cas_number': 'TEST-UNMATCHED',
                'net_weight_kg': 1.0,
            })],
        })
        dossier.action_evaluate_obligations()
        self.assertEqual(dossier.line_ids.regulatory_status, 'review')
        with self.assertRaises(UserError):
            dossier.action_generate_nsw_payload()

    def test_06_draft_rule_is_ignored_and_requires_different_approver(self):
        rule = self.Rule.create({
            'name': 'Maker checker test rule',
            'rule_category': 'mandatory_nsw_declaration',
            'cas_number': 'TEST-MAKER-CHECKER',
            'legal_basis': 'Official test provision',
            'legal_document_id': self.legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        })
        self.assertFalse(self.Rule.evaluate_chemical_obligations(cas_number='TEST-MAKER-CHECKER'))
        rule.action_submit_for_review()
        with self.assertRaises(UserError):
            rule.action_activate()
        rule.with_user(self.env.ref('base.user_root')).action_activate()
        self.assertTrue(self.Rule.evaluate_chemical_obligations(cas_number='TEST-MAKER-CHECKER'))

    def test_07_active_rule_requires_effective_date_range(self):
        rule = self.Rule.create({
            'name': 'Undated rule',
            'rule_category': 'mandatory_nsw_declaration',
            'cas_number': 'TEST-UNDATED',
            'legal_basis': 'Official test provision',
            'legal_document_id': self.legal_document.id,
        })
        rule.action_submit_for_review()
        with self.assertRaisesRegex(ValidationError, 'Effective From'):
            rule.with_user(self.env.ref('base.user_root')).action_activate()
        self.assertFalse(self.Rule.evaluate_chemical_obligations(
            cas_number='TEST-UNDATED', effective_date='2026-06-01'))

    def test_08_review_rejects_amended_or_not_yet_effective_legal_document(self):
        rule = self.Rule.create({
            'name': 'Rule requiring currently effective source',
            'rule_category': 'mandatory_nsw_declaration',
            'cas_number': 'TEST-CURRENT-LEGAL-SOURCE',
            'legal_basis': 'Official test provision',
            'legal_document_id': self.legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        })
        self.env.cr.execute(
            "UPDATE is_hse_legal_document SET state = 'amended' WHERE id = %s", [self.legal_document.id],
        )
        self.legal_document.invalidate_recordset()
        with self.assertRaises(ValidationError):
            rule.action_submit_for_review()

        self.env.cr.execute(
            "UPDATE is_hse_legal_document SET state = 'active', effective_date = '2026-02-01' WHERE id = %s",
            [self.legal_document.id],
        )
        self.legal_document.invalidate_recordset()
        with self.assertRaises(ValidationError):
            rule.action_submit_for_review()

    def test_09_direct_rule_rpc_requires_chemical_and_hse_manager(self):
        chemical_manager = self.env.ref(
            'insilos_chemical_trade_compliance.group_chemical_compliance_manager'
        )
        user = self.env['res.users'].create({
            'name': 'Chemical-only manager',
            'login': 'chemical-only-manager-rule-test',
            'group_ids': [(6, 0, [chemical_manager.id])],
        })
        with self.assertRaises(UserError):
            self.Rule.with_user(user).create({
                'name': 'Direct RPC active rule',
                'rule_category': 'mandatory_nsw_declaration',
                'cas_number': 'TEST-DIRECT-RPC',
                'legal_basis': 'Official test provision',
                'legal_document_id': self.legal_document.id,
            })
