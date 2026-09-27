# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_chemical_trade_compliance')
class TestChemicalUsageTracking(TransactionCase):

    def setUp(self):
        super(TestChemicalUsageTracking, self).setUp()
        self.Substance = self.env['is.hse.chemical.substance']
        self.Tracking = self.env['is.chemical.usage.tracking']
        self.TrackingLine = self.env['is.chemical.usage.tracking.line']

        self.sub_toluene = self.Substance.create({
            'name': 'Toluene Industrial',
            'cas_number': 'TEST-108-88-3-USAGE',
            'hazard_classification': 'restricted',
        })

    def test_01_five_stage_usage_chain_calculation(self):
        tracking = self.Tracking.create({
            'chemical_substance_id': self.sub_toluene.id,
            'reporting_year': 2026,
            'reporting_period': 'annual',
            'planned_demand_kg': 20000.0,
            'loss_or_evaporation_kg': 50.0,
        })

        # Add Import Line (10,000 kg)
        self.TrackingLine.create({
            'tracking_id': tracking.id,
            'flow_type': 'import',
            'document_ref': 'INV-2026-IMP-001',
            'quantity_kg': 10000.0,
        })

        # Add Domestic Purchase Line (5,000 kg)
        self.TrackingLine.create({
            'tracking_id': tracking.id,
            'flow_type': 'domestic_purchase',
            'document_ref': 'INV-DOM-0082',
            'quantity_kg': 5000.0,
        })

        # Add Production Consumption Line (8,000 kg)
        self.TrackingLine.create({
            'tracking_id': tracking.id,
            'flow_type': 'production_consumption',
            'document_ref': 'PROD-OUT-0451',
            'quantity_kg': 8000.0,
        })

        tracking.invalidate_recordset()
        
        self.assertEqual(tracking.imported_volume_kg, 10000.0)
        self.assertEqual(tracking.domestic_purchased_kg, 5000.0)
        self.assertEqual(tracking.total_inbound_volume_kg, 15000.0)
        self.assertEqual(tracking.consumed_in_production_kg, 8000.0)
        # Expected stock = 15000 - 8000 - 50 (loss) = 6950 kg
        self.assertEqual(tracking.current_stock_kg, 6950.0)
        self.assertEqual(tracking.calculated_balance_kg, 7000.0)
