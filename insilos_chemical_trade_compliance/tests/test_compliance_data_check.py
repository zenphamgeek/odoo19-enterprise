# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_chemical_trade_compliance')
class TestComplianceDataCheck(TransactionCase):

    def setUp(self):
        super(TestComplianceDataCheck, self).setUp()
        self.Substance = self.env['is.hse.chemical.substance']
        self.Product = self.env['product.product']
        self.Dossier = self.env['is.chemical.compliance.dossier']
        self.ExceptionModel = self.env['is.chemical.compliance.exception']

        self.sub_methanol = self.Substance.create({
            'name': 'Methanol Technical',
            'cas_number': 'TEST-67-56-1-CHECK',
            'hazard_classification': 'hazardous_general',
        })

        self.prod_methanol_prod = self.Product.create({
            'name': 'Methanol Unmapped Material',
            'is_hazardous_chemical': True,
            'chemical_substance_id': self.sub_methanol.id,
        })
        self.prod_methanol = self.prod_methanol_prod.product_tmpl_id

    def test_01_detect_missing_mapping_and_resolve(self):
        # Run compliance data check
        exceptions = self.ExceptionModel.run_compliance_data_check(product_tmpl_ids=self.prod_methanol)
        
        self.assertTrue(len(exceptions) >= 1)
        exc = exceptions.filtered(lambda e: e.product_tmpl_id == self.prod_methanol and e.exception_type == 'missing_mapping')
        self.assertTrue(exc)
        self.assertEqual(exc.severity, 'critical')
        self.assertEqual(exc.state, 'open')

        # Officer resolves exception
        exc.action_resolve_exception()
        self.assertEqual(exc.state, 'resolved')
        self.assertEqual(exc.resolved_by, self.env.user)
