# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import base64
from pathlib import Path

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'insilos_esg_bridge')
class TestESGFacilityScorecard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Facility = self.env['is.hse.facility']
        self.Scorecard = self.env['is.esg.facility.scorecard']
        self.ExportWizard = self.env['is.esg.export.scorecard.wizard']
        self.facility = self.Facility.create({
            'name': 'Hải Phòng Industrial Plant #1',
            'code': 'HP-PLANT-01',
            'worker_count': 350,
        })

    def _scorecard(self, period='annual', **values):
        return self.Scorecard.create({
            'facility_id': self.facility.id, 'reporting_year': 2026,
            'reporting_period': period, **values,
        })

    def _governance_users(self):
        manager_group = self.env.ref('insilos_esg_bridge.group_esg_bridge_manager')
        user_group = self.env.ref('base.group_user')
        groups = [(4, manager_group.id), (4, user_group.id)]
        return (
            self.env['res.users'].create({'name': 'ESG Auditor', 'login': 'esg_auditor', 'group_ids': groups}),
            self.env['res.users'].create({'name': 'ESG Publisher', 'login': 'esg_publisher', 'group_ids': groups}),
        )

    def _add_evidence(self, scorecard):
        evidence = self.env['ir.attachment'].create({
            'name': 'cems-report.pdf', 'raw': b'evidence',
            'res_model': scorecard._name, 'res_id': scorecard.id,
        })
        scorecard.write({
            'evidence_attachment_ids': [(4, evidence.id)],
            'evidence_summary': 'CEMS report for the reporting period.',
            'source_url': 'https://evidence.example/cems-report',
            'source_version': 'v1',
            'source_date': '2026-01-01',
        })

    def test_action_audit_checks_evidence_read_access(self):
        source = (Path(__file__).parents[1] / 'models/is_esg_facility_scorecard.py').read_text()
        action = source[source.index('    def action_audit(self):'):source.index('    def action_publish_esg(self):')]
        self.assertIn("self.evidence_attachment_ids.check_access('read')", action)
        self.assertIn("self.evidence_attachment_ids.check_access_rule('read')", action)
        self.assertLess(action.index("check_access('read')"), action.index("super(ESGFacilityScorecard, self).write"))

    def test_00_scorecard_labels_are_internal_bands(self):
        source = (Path(__file__).parents[1] / 'models/is_esg_facility_scorecard.py').read_text()
        self.assertIn("'Internal Environmental Score (0-100)'", source)
        self.assertIn("'Internal Scorecard Band'", source)
        self.assertIn("'Internal Band A (80-89)'", source)
        self.assertNotIn('A Compliant', source)

    def test_01_scorecard_creation_and_naming(self):
        scorecard = self._scorecard(
            scope1_direct_co2e=1250.50, scope2_indirect_co2e=840.25,
            cems_so2_emissions_kg=45.0, cems_nox_emissions_kg=68.0, cems_tsp_dust_kg=12.0,
        )
        self.assertTrue(scorecard.name)
        self.assertIn(self.facility.name, scorecard.name)
        self.assertAlmostEqual(scorecard.total_scope1_2_co2e, 2090.75, places=2)
        self.assertEqual(scorecard.state, 'draft')
        self.assertEqual(scorecard.wastewater_compliance_pct, 0.0)
        self.assertEqual(scorecard.recycled_waste_percentage, 0.0)
        self.assertEqual(scorecard.safety_training_hours_per_worker, 0.0)
        self.assertEqual(scorecard.environmental_score, 0.0)
        self.assertEqual(scorecard.sustainability_grade, 'not_assessed')

    def test_01a_create_rejects_lifecycle_metadata(self):
        auditor, publisher = self._governance_users()
        for values in (
            {'state': 'audited'},
            {'state': 'published'},
            {'auditor_id': auditor.id, 'audited_at': '2026-01-01 00:00:00'},
            {'publisher_id': publisher.id, 'published_at': '2026-01-01 00:00:00'},
        ):
            with self.assertRaises(ValidationError):
                self._scorecard(**values)

    def test_01b_audit_requires_source_provenance_but_drafts_remain_editable(self):
        auditor, _publisher = self._governance_users()
        scorecard = self._scorecard('semi_annual_1')
        self._add_evidence(scorecard)
        scorecard.write({'source_url': False, 'source_version': False, 'source_date': False})
        with self.assertRaises(ValidationError):
            scorecard.with_user(auditor).action_audit()
        self.assertEqual(scorecard.state, 'draft')

    def test_01c_audit_requires_a_different_manager_than_creator(self):
        creator, auditor = self._governance_users()
        scorecard = self.Scorecard.with_user(creator).create({
            'facility_id': self.facility.id, 'reporting_year': 2026,
            'reporting_period': 'q1',
        })
        self._add_evidence(scorecard.with_user(creator))
        with self.assertRaises(ValidationError):
            scorecard.with_user(creator).action_audit()
        self.assertEqual(scorecard.state, 'draft')
        scorecard.with_user(auditor).action_audit()
        self.assertEqual(scorecard.state, 'audited')
        self.assertEqual(scorecard.auditor_id, auditor)

    def test_02_esg_scoring_requires_audited_evidence(self):
        auditor, _publisher = self._governance_users()
        scorecard_a_plus = self._scorecard('q1', scope1_direct_co2e=500.0, scope2_indirect_co2e=300.0, wastewater_compliance_pct=99.0, recycled_waste_percentage=75.0, ltifr_safety_rate=0.0)
        self.assertEqual(scorecard_a_plus.environmental_score, 0.0)
        self.assertEqual(scorecard_a_plus.sustainability_grade, 'not_assessed')
        self._add_evidence(scorecard_a_plus)
        scorecard_a_plus.with_user(auditor).action_audit()
        self.assertEqual(scorecard_a_plus.environmental_score, 100.0)
        self.assertEqual(scorecard_a_plus.sustainability_grade, 'a_plus')
        scorecard_moderate = self._scorecard('q2', scope1_direct_co2e=500.0, scope2_indirect_co2e=300.0, wastewater_compliance_pct=85.0, recycled_waste_percentage=30.0, ltifr_safety_rate=1.5)
        self._add_evidence(scorecard_moderate)
        scorecard_moderate.with_user(auditor).action_audit()
        self.assertEqual(scorecard_moderate.environmental_score, 70.0)
        self.assertEqual(scorecard_moderate.sustainability_grade, 'b')

    def test_03_lifecycle_requires_manager_evidence_and_distinct_auditor_and_publisher(self):
        auditor, publisher = self._governance_users()
        officer_group = self.env.ref('insilos_esg_bridge.group_esg_bridge_user')
        officer = self.env['res.users'].create({
            'name': 'ESG Officer', 'login': 'esg_officer', 'group_ids': [(4, officer_group.id)],
        })
        scorecard = self._scorecard()
        with self.assertRaises(ValidationError):
            scorecard.with_user(auditor).action_audit()
        self._add_evidence(scorecard)
        with self.assertRaises(AccessError):
            scorecard.with_user(officer).action_audit()
        scorecard.with_user(auditor).action_audit()
        self.assertEqual(scorecard.state, 'audited')
        self.assertEqual(scorecard.auditor_id, auditor)
        self.assertTrue(scorecard.audited_at)
        with self.assertRaises(AccessError):
            scorecard.with_user(officer).action_publish_esg()
        with self.assertRaises(ValidationError):
            scorecard.with_user(auditor).action_publish_esg()
        scorecard.with_user(publisher).action_publish_esg()
        self.assertEqual(scorecard.state, 'published')
        self.assertEqual(scorecard.publisher_id, publisher)
        self.assertTrue(scorecard.published_at)

    def test_04_audited_and_published_material_scorecards_are_immutable(self):
        auditor, publisher = self._governance_users()
        audited = self._scorecard(cems_so2_emissions_kg=10.0)
        self._add_evidence(audited)
        audited.with_user(auditor).action_audit()
        with self.assertRaises(ValidationError):
            audited.write({'cems_so2_emissions_kg': 1.0})
        self.assertEqual(audited.state, 'audited')
        published = self._scorecard('q1')
        self._add_evidence(published)
        published.with_user(auditor).action_audit()
        published.with_user(publisher).action_publish_esg()
        replacement = self.env['ir.attachment'].create({'name': 'replacement.pdf', 'raw': b'evidence'})
        with self.assertRaises(ValidationError):
            published.write({'evidence_attachment_ids': [(4, replacement.id)]})
        self.assertEqual(published.state, 'published')

    def test_05_governed_evidence_is_immutable(self):
        auditor, publisher = self._governance_users()
        scorecard = self._scorecard('q3')
        self._add_evidence(scorecard)
        evidence = scorecard.evidence_attachment_ids
        scorecard.with_user(auditor).action_audit()
        with self.assertRaises(UserError):
            evidence.write({'raw': b'tampered'})
        with self.assertRaises(UserError):
            evidence.unlink()
        scorecard.with_user(publisher).action_publish_esg()
        with self.assertRaises(UserError):
            evidence.write({'name': 'replaced.pdf'})
        unrelated = self.env['ir.attachment'].create({'name': 'draft.txt', 'raw': b'draft'})
        unrelated.write({'raw': b'updated'})
        self.assertEqual(unrelated.raw, b'updated')

    def test_06_publish_requires_audit(self):
        with self.assertRaises(ValidationError):
            self._scorecard('q3').action_publish_esg()

    def test_07_unique_period_and_metric_bounds(self):
        values = {'facility_id': self.facility.id, 'reporting_year': 2026, 'reporting_period': 'q4'}
        self.Scorecard.create(values)
        with self.assertRaises(Exception):
            self.Scorecard.create(values)
        with self.assertRaises(ValidationError):
            self.Scorecard.create({**values, 'reporting_period': 'semi_annual_1', 'scope1_direct_co2e': -1})
        with self.assertRaises(ValidationError):
            self.Scorecard.create({**values, 'reporting_period': 'semi_annual_2', 'recycled_waste_percentage': 101})

    def test_08_export_requires_manager_and_includes_only_published_scorecards(self):
        draft = self._scorecard('q1')
        auditor, publisher = self._governance_users()
        officer_group = self.env.ref('insilos_esg_bridge.group_esg_bridge_user')
        officer = self.env['res.users'].create({
            'name': 'ESG Officer', 'login': 'esg_export_officer', 'group_ids': [(4, officer_group.id)],
        })
        wizard = self.ExportWizard.create({'reporting_year': 2026})
        with self.assertRaises(UserError):
            wizard.with_user(publisher).action_export()
        self._add_evidence(draft)
        draft.with_user(auditor).action_audit()
        draft.with_user(publisher).action_publish_esg()
        with self.assertRaises(AccessError):
            wizard.with_user(officer).action_export()
        action = wizard.with_user(publisher).action_export()
        attachment = self.env['ir.attachment'].browse(int(action['url'].split('/')[3].split('?')[0]))
        export = base64.b64decode(attachment.datas).decode('utf-8-sig')
        self.assertIn(draft.name, export)
        self.assertIn(draft.source_url, export)
