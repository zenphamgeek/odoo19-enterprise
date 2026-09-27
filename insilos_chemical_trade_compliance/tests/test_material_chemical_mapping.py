# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError, ValidationError


@tagged('post_install', '-at_install', 'insilos_chemical_trade_compliance')
class TestMaterialChemicalMapping(TransactionCase):

    def setUp(self):
        super(TestMaterialChemicalMapping, self).setUp()
        self.Substance = self.env['is.hse.chemical.substance']
        self.Purpose = self.env['is.chemical.purpose.of.use']
        self.Mapping = self.env['is.chemical.material.mapping']
        self.Product = self.env['product.product']

        self.sub_acetone = self.Substance.create({
            'name': 'Acetone Pure Grade',
            'cas_number': 'TEST-67-64-1-MAP',
            'hazard_classification': 'hazardous_general',
        })

        self.purpose_electronics = self.Purpose.create({
            'name': 'Circuit Board Degreaser (Tẩy rửa bo mạch)',
            'code': 'PURPOSE-ELEC-01',
            'industry_category': 'electronics',
            'max_annual_demand_kg': 50000.0,
            'standard_loss_rate_pct': 2.5,
        })

        self.prod_acetone = self.Product.create({
            'name': 'RAW-ACETONE-DRUM-200L',
            'default_code': 'MAT-CHEM-001',
            'is_hazardous_chemical': True,
            'chemical_substance_id': self.sub_acetone.id,
        })
        self.prod_acetone_mat = self.prod_acetone.product_tmpl_id

    def test_01_create_and_independently_review_material_mapping(self):
        officer = self.env['res.users'].create({
            'name': 'Chemical Mapping Officer', 'login': 'chemical-mapping-officer@example.test',
            'group_ids': [(6, 0, [self.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_user').id])],
        })
        reviewer = self.env['res.users'].create({
            'name': 'Chemical Mapping Reviewer', 'login': 'chemical-mapping-reviewer@example.test',
            'group_ids': [(6, 0, [self.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_manager').id])],
        })
        mapping = self.Mapping.with_user(officer).create({
            'product_tmpl_id': self.prod_acetone_mat.id,
            'commercial_name': 'Acetone Industrial Solvent 200L',
            'chemical_substance_id': self.sub_acetone.id,
            'purpose_of_use_id': self.purpose_electronics.id,
            'uom_to_kg_ratio': 160.0,
            'concentration_percentage': 99.5,
        })

        self.assertEqual(mapping.cas_number, 'TEST-67-64-1-MAP')
        self.assertFalse(mapping.is_verified)
        self.assertIn('RAW-ACETONE-DRUM-200L', mapping.name)
        with self.assertRaises(AccessError):
            mapping.with_user(officer).action_verify_mapping()
        mapping.with_user(reviewer).action_verify_mapping()
        self.assertTrue(mapping.is_verified)
        self.assertEqual(mapping.verified_by, reviewer)
        with self.assertRaises(AccessError):
            mapping.sudo().write({'is_verified': False})
        with self.assertRaises(ValidationError):
            mapping.with_user(officer).write({'uom_to_kg_ratio': 1})

    def test_02_verification_metadata_and_invalid_ratio_are_rejected(self):
        with self.assertRaises(AccessError):
            self.Mapping.create({
                'product_tmpl_id': self.prod_acetone_mat.id,
                'chemical_substance_id': self.sub_acetone.id,
                'is_verified': True,
            })
        officer = self.env['res.users'].create({
            'name': 'Chemical Mapping Officer 2', 'login': 'chemical-mapping-officer-2@example.test',
            'group_ids': [(6, 0, [self.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_user').id])],
        })
        reviewer = self.env['res.users'].create({
            'name': 'Chemical Mapping Reviewer 2', 'login': 'chemical-mapping-reviewer-2@example.test',
            'group_ids': [(6, 0, [self.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_manager').id])],
        })
        mapping = self.Mapping.with_user(officer).create({
            'product_tmpl_id': self.prod_acetone_mat.id,
            'chemical_substance_id': self.sub_acetone.id,
            'uom_to_kg_ratio': 0.0,
        })
        with self.assertRaises(ValidationError):
            mapping.with_user(reviewer).action_verify_mapping()
