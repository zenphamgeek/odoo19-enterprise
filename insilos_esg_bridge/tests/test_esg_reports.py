# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from pathlib import Path

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_esg_bridge')
class TestESGReports(TransactionCase):

    def setUp(self):
        super(TestESGReports, self).setUp()
        self.Facility = self.env['is.hse.facility']
        self.Scorecard = self.env['is.esg.facility.scorecard']
        self.Tariff = self.env['is.hs.tariff']
        self.CBAMAdvisor = self.env['is.esg.cbam.advisor']
        self.Project = self.env['project.project']
        self.IDPCase = self.env['logistics.idp.case']
        self.FreightCarbon = self.env['is.esg.freight.carbon']

        self.facility = self.Facility.create({
            'name': 'Đà Nẵng Green Technology Plant',
            'code': 'DN-TECH-01',
            'worker_count': 120,
        })
        self.scorecard = self.Scorecard.create({
            'facility_id': self.facility.id,
            'reporting_year': 2026,
            'reporting_period': 'annual',
            'scope1_direct_co2e': 350.0,
            'scope2_indirect_co2e': 180.0,
            'cems_so2_emissions_kg': 15.0,
            'cems_nox_emissions_kg': 28.0,
            'cems_tsp_dust_kg': 5.0,
        })
        self.tariff = self.Tariff.create({
            'hs_code': '72061000',
            'description_vi': 'Sắt và thép không hợp kim dạng thỏi',
        })
        self.cbam = self.CBAMAdvisor.create({
            'hs_tariff_id': self.tariff.id,
            'annual_export_volume_tons': 2000.0,
        })
        self.project = self.Project.create({
            'name': 'ESG Report Verification Project',
        })
        self.idp_case = self.IDPCase.create({
            'name': 'IDP-ESG-TEST-CASE-01',
            'team_id': self.project.id,
        })
        self.freight = self.FreightCarbon.create({
            'case_id': self.idp_case.id,
            'transport_mode': 'ocean_container',
            'cargo_weight_ton': 15.0,
            'estimated_distance_km': 800.0,
        })

    def test_01_only_governed_scorecard_report_action_exists(self):
        report_scorecard = self.env.ref('insilos_esg_bridge.action_report_esg_facility_scorecard', raise_if_not_found=False)
        self.assertTrue(report_scorecard, "Scorecard report action must exist")
        self.assertFalse(self.env.ref('insilos_esg_bridge.action_report_esg_cbam_declaration', raise_if_not_found=False))
        self.assertFalse(self.env.ref('insilos_esg_bridge.action_report_esg_freight_carbon', raise_if_not_found=False))

    def test_02_scorecard_template_is_non_disclosure_safe(self):
        source = (Path(__file__).parents[1] / 'reports' / 'is_esg_report_templates.xml').read_text()
        scorecard_template = source.split('<template id="report_esg_facility_scorecard_doc">', 1)[1].split('</template>', 1)[0].lower()
        self.assertIn('workflow state:', scorecard_template)
        self.assertIn('evidence status:', scorecard_template)
        self.assertIn('non-disclosure draft', scorecard_template)
        self.assertIn('no legal, regulatory, or standards conformance is represented.', scorecard_template)
        self.assertIn('no independent third-party conclusion is represented.', scorecard_template)
        self.assertNotIn('qcvn', scorecard_template)
        self.assertNotIn('compliant', scorecard_template)
        self.assertNotIn('verified', scorecard_template)
        self.assertNotIn('assured', scorecard_template)
        self.assertNotIn('certif', scorecard_template)

    def test_03_report_route_enforces_record_read_access(self):
        source = (Path(__file__).parents[1] / 'controllers' / 'report.py').read_text()
        self.assertIn("if not all(id_.isdigit() for id_ in ids):", source)
        self.assertIn("records.check_access('read')", source)
        self.assertIn("records.check_access_rule('read')", source)
        self.assertIn("Only published ESG scorecards can be rendered as reports.", source)
        self.assertIn("'This internal estimate report is unavailable until governed source, evidence, '", source)
        self.assertIn("'independent review, and publication controls exist.'", source)

    def test_04_scorecard_export_enforces_read_access_and_disclaimer(self):
        source = (Path(__file__).parents[1] / 'wizard' / 'is_esg_export_scorecard_wizard.py').read_text()
        self.assertIn("scorecards.check_access('read')", source)
        self.assertIn("scorecards.check_access_rule('read')", source)
        self.assertIn('not independently assured', source)
        for field in ('Evidence Summary', 'Audited By', 'Audited At', 'Published By', 'Published At', '"governance"'):
            self.assertIn(field, source)
        for field in ('Evidence Summary', 'Audited By', 'Audited At', 'Published By', 'Published At', '"governance"'):
            self.assertIn(field, source)

    def test_05_scorecard_template_contains_non_disclosure_markers(self):
        source = (Path(__file__).parents[1] / 'reports' / 'is_esg_report_templates.xml').read_text()
        scorecard_template = source.split('<template id="report_esg_facility_scorecard_doc">', 1)[1].split('</template>', 1)[0]
        self.assertIn('ESG FACILITY SCORECARD', scorecard_template)
        self.assertIn('Workflow state:', scorecard_template)
        self.assertIn('NON-DISCLOSURE DRAFT', scorecard_template)
        self.assertIn('no legal, regulatory, or standards conformance is represented.', scorecard_template)
