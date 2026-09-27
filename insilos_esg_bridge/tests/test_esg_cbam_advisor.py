# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_esg_bridge')
class TestESGCBAMAdvisor(TransactionCase):

    def setUp(self):
        super(TestESGCBAMAdvisor, self).setUp()
        self.Tariff = self.env['is.hs.tariff']
        self.CBAMAdvisor = self.env['is.esg.cbam.advisor']

        self.steel_tariff = self.Tariff.create({
            'hs_code': '72061000',
            'description_vi': 'Sắt và thép không hợp kim dạng thỏi',
        })
        self.aluminum_tariff = self.Tariff.create({
            'hs_code': '76011000',
            'description_vi': 'Nhôm chưa gia công, chưa hợp kim',
        })
        self.garment_tariff = self.Tariff.create({
            'hs_code': '61091000',
            'description_vi': 'Áo thun cotton dệt kim',
        })

    def test_01_cbam_applicability_and_sector_matching(self):
        """Test HS code prefix matching for CBAM regulated sectors."""
        steel_advisor = self.CBAMAdvisor.create({
            'hs_tariff_id': self.steel_tariff.id,
            'annual_export_volume_tons': 10000.0,
        })
        self.assertTrue(steel_advisor.is_cbam_applicable)
        self.assertEqual(steel_advisor.cbam_sector, 'iron_steel')
        self.assertEqual(steel_advisor.reporting_frequency, 'quarterly_transitional')

        al_advisor = self.CBAMAdvisor.create({
            'hs_tariff_id': self.aluminum_tariff.id,
        })
        self.assertTrue(al_advisor.is_cbam_applicable)
        self.assertEqual(al_advisor.cbam_sector, 'aluminum')

        garment_advisor = self.CBAMAdvisor.create({
            'hs_tariff_id': self.garment_tariff.id,
        })
        self.assertFalse(garment_advisor.is_cbam_applicable)
        self.assertEqual(garment_advisor.cbam_sector, 'not_applicable')
        self.assertEqual(garment_advisor.reporting_frequency, 'none')

    def test_02_carbon_intensity_and_mitigation_scenarios(self):
        """Test carbon intensity defaults, tariff liabilities and DPPA mitigation savings."""
        steel_advisor = self.CBAMAdvisor.create({
            'hs_tariff_id': self.steel_tariff.id,
            'direct_embedded_emissions_t_per_t': 1.95,
            'indirect_embedded_emissions_t_per_t': 0.50,
            'eu_carbon_certificate_price_eur': 70.0,
            'renewable_energy_share_pct': 50.0,
            'annual_export_volume_tons': 1000.0,
        })
        self.assertAlmostEqual(steel_advisor.total_embedded_emissions_t_per_t, 2.45, places=2)
        self.assertAlmostEqual(steel_advisor.estimated_cbam_cost_per_ton_eur, 171.50, places=2)
        # Mitigated indirect: 0.50 * (1 - 0.5) = 0.25
        self.assertAlmostEqual(steel_advisor.mitigated_indirect_emissions, 0.25, places=2)
        # Mitigated total: 1.95 + 0.25 = 2.20
        self.assertAlmostEqual(steel_advisor.mitigated_total_emissions, 2.20, places=2)
        # Savings per ton: (2.45 - 2.20) * 70 = 17.50 EUR/ton
        self.assertAlmostEqual(steel_advisor.potential_savings_per_ton_eur, 17.50, places=2)
        # Total annual savings: 17.50 * 1000 = 17,500 EUR
        self.assertAlmostEqual(steel_advisor.total_annual_cbam_savings_eur, 17500.0, places=2)

    def test_03_generate_internal_estimate_is_fail_closed_without_governance(self):
        steel_advisor = self.CBAMAdvisor.create({
            'hs_tariff_id': self.steel_tariff.id,
            'annual_export_volume_tons': 5000.0,
        })
        with self.assertRaisesRegex(UserError, 'governed source, evidence, independent review, and publication controls'):
            steel_advisor.action_generate_cbam_internal_estimate()

    def test_04_rpc_sudo_cannot_override_calculated_advisory_fields(self):
        advisor = self.CBAMAdvisor.create({'hs_tariff_id': self.steel_tariff.id})
        with self.assertRaises(ValidationError):
            self.CBAMAdvisor.sudo().create({
                'hs_tariff_id': self.steel_tariff.id,
                'is_cbam_applicable': False,
            })
        with self.assertRaises(ValidationError):
            advisor.sudo().write({
                'estimated_cbam_cost_per_ton_eur': 0.0,
                'reporting_frequency': 'none',
            })
        self.assertTrue(advisor.is_cbam_applicable)
        self.assertEqual(advisor.reporting_frequency, 'quarterly_transitional')

    def test_05_input_bounds_and_non_applicable_export_guard(self):
        """Test input validation and non-CBAM export guard."""
        with self.assertRaises(ValidationError):
            self.CBAMAdvisor.create({
                'hs_tariff_id': self.steel_tariff.id,
                'renewable_energy_share_pct': 101,
            })
        with self.assertRaises(ValidationError):
            self.CBAMAdvisor.create({
                'hs_tariff_id': self.steel_tariff.id,
                'annual_export_volume_tons': -1,
            })
        garment_advisor = self.CBAMAdvisor.create({'hs_tariff_id': self.garment_tariff.id})
        with self.assertRaises(UserError):
            garment_advisor.action_generate_cbam_internal_estimate()
