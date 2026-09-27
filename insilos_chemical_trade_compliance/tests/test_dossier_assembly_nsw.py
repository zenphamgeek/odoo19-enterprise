# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install', 'insilos_chemical_trade_compliance')
class TestDossierAssemblyNSW(TransactionCase):

    def setUp(self):
        super(TestDossierAssemblyNSW, self).setUp()
        self.Dossier = self.env['is.chemical.compliance.dossier']
        self.Rule = self.env['is.chemical.regulatory.rule']
        self.Partner = self.env['res.partner']

        self.supplier = self.Partner.create({
            'name': 'Overseas Chemical Supplier Corp',
            'country_id': self.env.ref('base.jp').id,
            'street': 'Test exporter address',
        })
        legal_document = self.env['is.hse.legal.document'].create({
            'name': 'Official NSW test source',
            'code': 'TEST-NSW-RULE-2026',
            'issuer': 'Test Authority',
            'issued_date': '2026-01-01',
            'effective_date': '2026-01-01',
            'source_url': 'https://official.example.test/nsw-rule',
            'source_content_sha256': 'a' * 64,
            'source_version': '2026.1',
        })
        legal_document.action_activate()
        self.Rule.create([{
            'name': 'NSW Acetone test rule',
            'rule_category': 'mandatory_nsw_declaration',
            'cas_number': '67-64-1',
            'hs_code': '2914.11.00',
            'nsw_procedure_code': 'BCT00001',
            'legal_basis': 'Official test provision',
            'legal_document_id': legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        }, {
            'name': 'NSW procedure-less test rule',
            'rule_category': 'mandatory_nsw_declaration',
            'cas_number': 'TEST-NO-PROCEDURE',
            'legal_basis': 'Official test provision',
            'legal_document_id': legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        }, {
            'name': 'Prohibited chemical test rule',
            'rule_category': 'prohibited_chemical_block',
            'cas_number': 'TEST-309-00-2',
            'legal_basis': 'Official test provision',
            'legal_document_id': legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        }])
        rules = self.Rule.search([('cas_number', 'in', ['67-64-1', 'TEST-NO-PROCEDURE', 'TEST-309-00-2'])])
        rules.action_submit_for_review()
        approver = self.env['res.users'].create({
            'name': 'NSW Rule Approver', 'login': 'nsw-rule-approver@example.test',
            'group_ids': [(6, 0, [
                self.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_manager').id,
                self.env.ref('insilos_hse_compliance.group_hse_manager').id,
            ])],
        })
        rules.with_user(approver).action_activate()
        self.env.company.with_context(no_vat_validation=True).write({'vat': 'TEST-TAX', 'street': 'Test importer address'})
        self.Dossier = self.Dossier.with_context(
            default_partner_id=self.supplier.id,
            default_invoice_date='2026-01-02', default_invoice_number='TEST-INVOICE',
            default_customs_office_code='TEST-OFFICE',
            default_port_of_loading='Test loading', default_port_of_discharge='Test discharge',
        )

    def test_01_dossier_nsw_payload_generation(self):
        """Test compiling dossier and generating structured JSON and XML NSW payloads."""
        dossier = self.Dossier.create({
            'dossier_type': 'nsw_declaration',
            'partner_id': self.supplier.id,
            'invoice_number': 'INV-2026-CH001',
            'nsw_procedure_code': 'BCT00001',
            'line_ids': [
                (0, 0, {
                    'trade_name': 'Acetone Industrial Grade',
                    'cas_number': '67-64-1',
                    'hs_code': '2914.11.00',
                    'concentration_percentage': 99.8,
                    'quantity': 50,
                    'package_type': 'Drum 200L',
                    'intended_use': 'Industrial use',
                    'net_weight_kg': 8000.0,
                })
            ]
        })
        dossier.action_evaluate_obligations()

        self.assertEqual(dossier.total_net_weight_kg, 8000.0)
        self.assertEqual(dossier.line_count, 1)

        with self.assertRaisesRegex(UserError, 'immutable evidence manifests'):
            dossier.action_generate_nsw_payload()
        self.assertEqual(dossier.state, 'evaluating')
        self.assertFalse(dossier.nsw_payload_json)
        self.assertFalse(dossier.nsw_payload_xml)

    def test_rpc_workflow_fields_cannot_be_forged(self):
        for vals in ({'state': 'internally_approved'}, {'submitted_by': self.env.uid}, {'approved_by': self.env.uid}):
            with self.subTest(vals=vals), self.assertRaises(UserError):
                self.Dossier.create(vals)
        for context in ({'default_state': 'approved'}, {'default_approved_by': self.env.uid}):
            with self.subTest(context=context), self.assertRaises(UserError):
                self.Dossier.with_context(**context).create({})
        dossier = self.Dossier.create({})
        self.assertNotIn('quota_deducted', dict(dossier._fields['state'].selection))
        for vals in ({'state': 'submission_prepared'}, {'state': 'internally_approved'},
                     {'submitted_by': self.env.uid}, {'approved_by': self.env.uid}):
            with self.subTest(vals=vals), self.assertRaises(UserError):
                dossier.with_context(skip_approval_check=True).write(vals)
        for action in (dossier.action_prepare_nsw_submission, dossier.action_complete_internal_review, dossier.action_deduct_permit_quota):
            with self.subTest(action=action.__name__), self.assertRaises(UserError):
                action()

    def test_rpc_nsw_receipt_references_cannot_be_forged(self):
        receipt_vals = ({'nsw_registration_no': 'FORGED-NSW-REG'}, {'nsw_verification_code': 'FORGED-NSW-VERIFY'})
        for vals in receipt_vals:
            with self.subTest(operation='create', vals=vals), self.assertRaises(UserError):
                self.Dossier.sudo().create(vals)
        dossier = self.Dossier.create({})
        for vals in receipt_vals:
            with self.subTest(operation='write', vals=vals), self.assertRaises(UserError):
                dossier.sudo().write(vals)

    def test_rpc_regulatory_findings_cannot_be_forged(self):
        dossier = self.Dossier.create({
            'line_ids': [(0, 0, {
                'trade_name': 'Unmatched chemical', 'cas_number': 'TEST-RPC-BYPASS', 'net_weight_kg': 1,
            })],
        })
        line = dossier.line_ids
        with self.assertRaises(UserError):
            line.write({'regulatory_status': 'exempt', 'matched_rule_ids': [(5, 0, 0)]})
        dossier.action_evaluate_obligations()
        self.assertEqual(line.regulatory_status, 'review')

    def test_evaluated_and_ready_dossier_lines_are_materially_immutable(self):
        dossier = self.Dossier.create({
            'nsw_procedure_code': 'BCT00001',
            'line_ids': [(0, 0, {
                'trade_name': 'Acetone', 'cas_number': '67-64-1', 'hs_code': '2914.11.00',
                'concentration_percentage': 99.8, 'quantity': 1, 'package_type': 'Drum',
                'intended_use': 'Industrial use', 'net_weight_kg': 1,
            })],
        })
        line = dossier.line_ids
        line.write({'net_weight_kg': 2})
        self.assertEqual(line.net_weight_kg, 2)
        dossier.action_evaluate_obligations()
        for vals in (
            {'cas_number': '67-63-0'}, {'hs_code': '2905.12.00'},
            {'concentration_percentage': 50}, {'net_weight_kg': 3},
        ):
            with self.subTest(state='evaluating', vals=vals), self.assertRaises(UserError):
                line.write(vals)
        with self.assertRaises(UserError):
            line.unlink()
        with self.assertRaises(UserError):
            self.env['is.chemical.compliance.dossier.line'].create({
                'dossier_id': dossier.id, 'trade_name': 'Injected', 'net_weight_kg': 1,
            })
        dossier.action_generate_nsw_payload()
        with self.assertRaises(UserError):
            line.write({'net_weight_kg': 3})

    def test_submitted_and_approved_dossiers_are_immutable(self):
        dossier = self.Dossier.create({
            'nsw_procedure_code': 'BCT00001',
            'line_ids': [(0, 0, {
                'trade_name': 'Acetone', 'cas_number': '67-64-1', 'net_weight_kg': 1,
                'hs_code': '29141100', 'quantity': 1, 'package_type': 'Drum', 'intended_use': 'Industrial use',
            })],
        })
        dossier.action_generate_nsw_payload()
        dossier.action_prepare_nsw_submission()
        officer = self.env['res.users'].create({
            'name': 'Chemical Officer', 'login': 'chemical-officer-security@example.test',
            'group_ids': [(6, 0, [self.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_user').id])],
        })
        checker = self.env['res.users'].create({
            'name': 'Chemical Reviewer', 'login': 'chemical-reviewer-security@example.test',
            'group_ids': [(6, 0, [self.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_manager').id])],
        })
        with self.assertRaises(UserError):
            dossier.with_user(officer).action_complete_internal_review()
        with self.assertRaises(UserError):
            dossier.action_complete_internal_review()
        other = self.Dossier.create({})
        line = dossier.line_ids
        loose_line = self.env['is.chemical.compliance.dossier.line'].create({
            'dossier_id': other.id, 'trade_name': 'Other', 'net_weight_kg': 1,
        })
        for expected_state in ('submission_prepared', 'internally_approved'):
            self.assertEqual(dossier.state, expected_state)
            attempts = (
                lambda: dossier.write({'nsw_payload_json': '{}'}),
                lambda: dossier.write({'invoice_number': 'forged'}),
                lambda: dossier.write({'line_ids': [(5, 0, 0)]}),
                lambda: dossier.unlink(),
                lambda: line.write({'net_weight_kg': 999}),
                lambda: line.write({'dossier_id': other.id}),
                lambda: loose_line.write({'dossier_id': dossier.id}),
                lambda: line.unlink(),
                lambda: self.env['is.chemical.compliance.dossier.line'].with_context(default_dossier_id=dossier.id).create({'trade_name': 'Injected'}),
                lambda: dossier.action_evaluate_obligations(),
                lambda: dossier.action_generate_nsw_payload(),
                lambda: dossier.action_prepare_nsw_submission(),
            )
            for index, attempt in enumerate(attempts):
                with self.subTest(state=expected_state, attempt=index), self.assertRaises(UserError):
                    attempt()
            if expected_state == 'submission_prepared':
                dossier.with_user(checker).action_complete_internal_review()
                self.assertEqual(dossier.approved_by, checker)
                self.assertEqual(dossier.submitted_by, self.env.user)
            elif expected_state == 'internally_approved':
                with self.assertRaises(UserError):
                    dossier.with_user(checker).action_deduct_permit_quota()
        with self.assertRaises(UserError):
            dossier.with_user(checker).action_deduct_permit_quota()

    def test_02_missing_nsw_procedure_is_blocked(self):
        dossier = self.Dossier.create({
            'dossier_type': 'nsw_declaration',
            'line_ids': [(0, 0, {
                'trade_name': 'Unscoped Chemical',
                'net_weight_kg': 1.0,
                'regulatory_status': 'nsw_required',
            })],
        })
        with self.assertRaises(UserError):
            dossier.action_generate_nsw_payload()

    def test_03_prohibited_chemical_blocks_nsw_generation(self):
        """Test that consignments containing Prohibited chemicals trigger a hard block."""
        dossier = self.Dossier.create({
            'dossier_type': 'nsw_declaration',
            'partner_id': self.supplier.id,
            'line_ids': [
                (0, 0, {
                    'trade_name': 'Aldrin Pesticide Raw',
                    'cas_number': '309-00-2',
                    'concentration_percentage': 100.0,
                    'net_weight_kg': 100.0,
                    'regulatory_status': 'prohibited',
                })
            ]
        })

        self.assertTrue(dossier.has_prohibited_chemicals)
        with self.assertRaises(UserError):
            dossier.action_generate_nsw_payload()
