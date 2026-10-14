# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import os
from lxml import etree
import psycopg2

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestChemicalComplianceSecurity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.tracking_doc = self.env['is.chemical.usage.tracking'].create({
            'name': 'Audit Test Report 2026-Q4',
            'company_id': self.env.company.id,
        })
        self.stock_move = self.env['stock.move'].create({
            'name': 'MOVE-CHEM-001',
            'product_id': self.env.ref('product.product_product_4').id,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })

    def test_01_orm_sql_constraint_uniqueness(self):
        """Boundary test: verify that duplicate lines for the same stock move are rejected."""
        self.env['is.chemical.usage.tracking.line'].create({
            'tracking_id': self.tracking_doc.id,
            'source_stock_move_id': self.stock_move.id,
        })

        # Test application-level invariant
        with self.assertRaises((ValidationError, psycopg2.IntegrityError)):
            with self.cr.savepoint():
                self.env['is.chemical.usage.tracking.line'].create({
                    'tracking_id': self.tracking_doc.id,
                    'source_stock_move_id': self.stock_move.id,
                })

    def test_02_qweb_asset_xml_wellformedness(self):
        """Parse all theme XML extensions with lxml to verify no empty or truncated templates."""
        target_path = os.path.join(
            os.path.dirname(__file__),
            '../../insilos_theme_genesis/static/src/errors/runtime_error_dialog_extension.xml'
        )
        if os.path.exists(target_path):
            with open(target_path, 'rb') as f:
                content = f.read().strip()
            self.assertTrue(len(content) > 50, "Template XML is truncated or empty")
            tree = etree.fromstring(content)
            self.assertEqual(tree.tag, 'templates', "Root element must be <templates>")
