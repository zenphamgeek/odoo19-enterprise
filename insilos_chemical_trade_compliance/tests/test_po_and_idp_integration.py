# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_chemical_trade_compliance')
class TestPOAndIDPIntegration(TransactionCase):

    def setUp(self):
        super(TestPOAndIDPIntegration, self).setUp()
        self.Product = self.env['product.product']
        self.ProductTemplate = self.env['product.template']
        self.Chemical = self.env['is.hse.chemical.substance']
        self.Rule = self.env['is.chemical.regulatory.rule']
        self.PurchaseOrder = self.env['purchase.order']
        self.StockPicking = self.env['stock.picking']
        self.Partner = self.env['res.partner']
        self.Dossier = self.env['is.chemical.compliance.dossier']

        self.vendor = self.Partner.create({'name': 'Mitsui Chemicals Japan'})

        self.chem_acetone = self.Chemical.create({
            'name': 'Acetone Industrial',
            'cas_number': 'TEST-67-64-1-PO',
            'hazard_classification': 'conditional',
        })
        self.legal_document = self.env['is.hse.legal.document'].create({
            'name': 'Official PO chemical rule test source', 'code': 'TEST-PO-CHEM-2026',
            'issuer': 'Test Authority', 'issued_date': '2026-01-01',
            'effective_date': '2026-01-01',
            'source_url': 'https://official.example.test/po-chemical-rule',
            'source_content_sha256': 'b' * 64, 'source_version': '2026.1',
        })
        self.legal_document.action_activate()

        self.rule_acetone = self.Rule.create({
            'name': 'Khai báo NSW Acetone',
            'rule_category': 'mandatory_nsw_declaration',
            'cas_number': 'TEST-67-64-1-PO',
            'threshold_concentration': 0.0,
            'nsw_procedure_code': 'BCT00001',
            'legal_basis': 'Official test provision',
            'legal_document_id': self.legal_document.id,
            'effective_from': '2026-01-01',
            'effective_to': '2026-12-31',
        })
        self.rule_acetone.action_submit_for_review()
        approver = self.env['res.users'].create({
            'name': 'PO Rule Approver', 'login': 'po-rule-approver@example.test',
            'group_ids': [(6, 0, [
                self.env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_manager').id,
                self.env.ref('insilos_hse_compliance.group_hse_manager').id,
            ])],
        })
        self.rule_acetone.with_user(approver).action_activate()

        self.prod_acetone = self.Product.create({
            'name': 'Dung môi Acetone 200L Phuy',
            'chemical_substance_id': self.chem_acetone.id,
            'is_hazardous_chemical': True,
        })

    def test_01_po_auto_generates_chemical_dossier(self):
        """Test that confirming/clicking action on Purchase Order with chemicals generates a complete dossier."""
        po = self.PurchaseOrder.create({
            'partner_id': self.vendor.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.prod_acetone.id,
                    'name': self.prod_acetone.name,
                    'product_qty': 100.0,
                    'price_unit': 50.0,
                })
            ]
        })

        self.assertTrue(po.has_chemical_items)
        self.assertEqual(po.chemical_dossier_count, 0)

        # Trigger generation
        action = po.action_create_chemical_dossier()
        self.assertEqual(action['res_model'], 'is.chemical.compliance.dossier')
        
        dossier = self.Dossier.browse(action['res_id'])
        self.assertTrue(dossier.exists())
        self.assertEqual(dossier.purchase_order_id, po)
        self.assertEqual(len(dossier.line_ids), 1)
        self.assertEqual(dossier.line_ids[0].cas_number, 'TEST-67-64-1-PO')
        self.assertEqual(dossier.line_ids[0].regulatory_status, 'nsw_required')

    def test_02_stock_picking_chemical_clearance_gate(self):
        """Test that Stock Picking verifies chemical compliance dossier clearance."""
        dossier = self.env['is.chemical.compliance.dossier'].create({
            'dossier_type': 'nsw_declaration',
            'partner_id': self.vendor.id,
            'state': 'draft',
        })

        picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming')], limit=1)
        location_src = self.env.ref('stock.stock_location_suppliers')
        location_dest = self.env.ref('stock.stock_location_stock')

        picking = self.StockPicking.create({
            'picking_type_id': picking_type.id,
            'location_id': location_src.id,
            'location_dest_id': location_dest.id,
            'partner_id': self.vendor.id,
            'chemical_dossier_id': dossier.id,
            'move_ids': [
                (0, 0, {
                    'product_id': self.prod_acetone.id,
                    'product_uom_qty': 50.0,
                    'product_uom': self.prod_acetone.uom_id.id,
                    'location_id': location_src.id,
                    'location_dest_id': location_dest.id,
                })
            ]
        })

        self.assertTrue(picking.has_chemical_items)
        self.assertFalse(picking.is_chemical_compliance_cleared)

        dossier.state = 'approved'
        picking._compute_chemical_status()
        self.assertFalse(picking.is_chemical_compliance_cleared)

        dossier.customs_declaration_no = 'TKHQ-105599882200'
        picking._compute_chemical_status()
        self.assertFalse(picking.is_chemical_compliance_cleared)
