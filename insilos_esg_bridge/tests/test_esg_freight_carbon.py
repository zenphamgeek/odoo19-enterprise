# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_esg_bridge')
class TestESGFreightCarbon(TransactionCase):

    def setUp(self):
        super(TestESGFreightCarbon, self).setUp()
        self.Project = self.env['project.project']
        self.IDPCase = self.env['logistics.idp.case']
        self.FreightCarbon = self.env['is.esg.freight.carbon']

        self.project = self.Project.create({
            'name': 'Freight Carbon Logistics Project',
        })
        self.idp_case = self.IDPCase.create({
            'name': 'BILL-OF-LADING-VN-2026-001',
            'team_id': self.project.id,
        })

    def test_01_freight_carbon_calculation_and_modes(self):
        """Test GLEC emission factors and gross/net freight carbon calculations."""
        # Ocean container: factor 0.015 kg/t-km
        freight_ocean = self.FreightCarbon.create({
            'case_id': self.idp_case.id,
            'transport_mode': 'ocean_container',
            'cargo_weight_ton': 20.0,
            'estimated_distance_km': 1000.0,
            'paperless_pages_processed': 10,
        })
        self.assertAlmostEqual(freight_ocean.emission_factor_kg_per_tkm, 0.015, places=4)
        # Gross = 20.0 * 1000.0 * 0.015 = 300 kg CO2e
        self.assertAlmostEqual(freight_ocean.gross_freight_emissions_kg_co2e, 300.0, places=2)
        self.assertAlmostEqual(freight_ocean.gross_freight_emissions_t_co2e, 0.300, places=3)
        # Offset = 10 * 0.009 = 0.090 kg
        self.assertAlmostEqual(freight_ocean.paperless_carbon_offset_kg, 0.09, places=3)
        self.assertAlmostEqual(freight_ocean.net_logistics_carbon_kg_co2e, 299.91, places=2)

        # Air freight: factor 0.602 kg/t-km
        freight_air = self.FreightCarbon.create({
            'case_id': self.idp_case.id,
            'transport_mode': 'air_freight',
            'cargo_weight_ton': 2.0,
            'estimated_distance_km': 5000.0,
        })
        self.assertAlmostEqual(freight_air.emission_factor_kg_per_tkm, 0.602, places=4)
        # Gross = 2.0 * 5000.0 * 0.602 = 6020 kg CO2e
        self.assertAlmostEqual(freight_air.gross_freight_emissions_kg_co2e, 6020.0, places=2)
