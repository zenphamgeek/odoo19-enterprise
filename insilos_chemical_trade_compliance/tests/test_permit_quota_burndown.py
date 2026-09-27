# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from datetime import date
from odoo import models
from odoo.addons.insilos_chemical_trade_compliance.models.is_chemical_permit_quota import _CUSTOMS_CLEARANCE_CAPABILITY
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install', 'insilos_chemical_trade_compliance')
class TestPermitQuotaBurndown(TransactionCase):

    def setUp(self):
        super(TestPermitQuotaBurndown, self).setUp()
        self.Chemical = self.env['is.hse.chemical.substance']
        self.Permit = self.env['is.hse.product.permit']
        self.Quota = self.env['is.chemical.permit.quota']
        self.Dossier = self.env['is.chemical.compliance.dossier']

        self.chem = self.Chemical.create({
            'name': 'Toluene Industrial',
            'cas_number': 'TEST-108-88-3-QUOTA',
            'hazard_classification': 'conditional',
        })
        self.permit = self.Permit.create({
            'name': 'Giấy phép Nhập khẩu Hóa chất Hạn chế 2026',
            'permit_number': 'TEST_PERMIT_BCT_2026_01',
            'permit_type': 'restricted_license',
            'issuing_authority': 'Bộ Công Thương - Cục Hóa chất',
            'chemical_substance_id': self.chem.id,
            'issue_date': date.today(),
            'expiry_date': date(date.today().year + 1, 12, 31),
        })
        self.quota = self.Quota._create_from_customs_workflow({
            'permit_id': self.permit.id,
            'chemical_substance_id': self.chem.id,
            'allocated_quota_kg': 50000.0,
        }, _CUSTOMS_CLEARANCE_CAPABILITY)

    def test_01_direct_quota_creation_is_blocked(self):
        with self.assertRaises(UserError):
            self.Quota.create({
                'permit_id': self.permit.id,
                'chemical_substance_id': self.chem.id,
                'allocated_quota_kg': 1.0,
            })

    def test_01_controlled_registration_rejects_forged_quota_state(self):
        with self.assertRaises(ValidationError):
            self.Quota.sudo()._create_from_customs_workflow({
                'permit_id': self.permit.id,
                'chemical_substance_id': self.chem.id,
                'allocated_quota_kg': 1.0,
                'remaining_quota_kg': 999999.0,
                'state': 'active',
            }, _CUSTOMS_CLEARANCE_CAPABILITY)

    def test_02_direct_deduction_is_blocked(self):
        with self.assertRaises(UserError):
            self.quota.deduct_quota(20000.0, False, False)
        self.assertFalse(self.quota.line_ids)

    def test_02_direct_ledger_mutation_is_blocked(self):
        with self.assertRaises(UserError):
            self.env['is.chemical.permit.quota.line'].create({
                'quota_id': self.quota.id,
                'dossier_id': self.Dossier.create({}).id,
                'customs_declaration_no': 'FORGED',
                'quantity_kg': 1,
            })

    def test_03_customs_declaration_number_cannot_deduct_quota(self):
        dossier = self.Dossier.create({
            'customs_declaration_no': 'TEST-CLEARANCE-REFUSED',
            'line_ids': [(0, 0, {
                'trade_name': 'Toluene', 'chemical_substance_id': self.chem.id,
                'permit_id': self.permit.id, 'net_weight_kg': 100.0,
            })],
        })
        models.Model.write(dossier, {'state': 'internally_approved'})
        with self.assertRaisesRegex(UserError, 'immutable externally verified customs receipt'):
            dossier.action_deduct_permit_quota()
        self.assertEqual(dossier.state, 'internally_approved')
        self.assertFalse(self.quota.line_ids)
