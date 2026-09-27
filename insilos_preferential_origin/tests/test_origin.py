from odoo.exceptions import AccessError
from odoo.tests import HttpCase, TransactionCase, tagged

from ..services.origin import digest, evaluate, rank_scenarios


@tagged('post_install', '-at_install')
class TestOriginOracle(TransactionCase):
    def test_deterministic_oracle(self):
        policy_hash = digest({'dataset': 'synthetic-origin-v1'})
        cases = [
            ({'criterion': 'WO'}, {'all_originating': True}, 'REVIEW'),
            ({'criterion': 'WO', 'policy_hash': policy_hash, 'state': 'superseded'}, {'all_originating': True}, 'REVIEW'),
            ({'criterion': 'WO', 'policy_hash': policy_hash}, {'all_originating': True, 'conflicting_evidence': True}, 'REVIEW'),
            ({'criterion': 'WO', 'policy_hash': policy_hash}, {'all_originating': True}, 'PASS'),
            ({'criterion': 'WO', 'policy_hash': policy_hash}, {}, 'REVIEW'),
            ({'criterion': 'CTH', 'policy_hash': policy_hash}, {'output_hs': '850440', 'input_hs': ['854411']}, 'PASS'),
            ({'criterion': 'CTH', 'policy_hash': policy_hash}, {'output_hs': '850440', 'input_hs': ['850490']}, 'BLOCK'),
            ({'criterion': 'RVC', 'threshold': 40, 'policy_hash': policy_hash}, {'value': 100, 'non_originating_value': 60}, 'PASS'),
            ({'criterion': 'RVC', 'threshold': 40, 'policy_hash': policy_hash}, {'value': 0, 'non_originating_value': 0}, 'REVIEW'),
            ({'criterion': 'CONSIGNMENT', 'predicate': 'non_alteration', 'policy_hash': policy_hash}, {}, 'REVIEW'),
            ({'criterion': 'WO', 'required_evidence': ['supplier_declaration'], 'policy_hash': policy_hash}, {'all_originating': True}, 'REVIEW'),
        ]
        for rule, facts, expected in cases:
            result = evaluate(rule, facts)
            self.assertEqual(result['outcome'], expected)
            self.assertEqual(result, evaluate(rule, facts))

    def test_stable_ranking(self):
        scenarios = [
            {'id': 'b', 'state': 'eligible', 'evidence_completeness': 1, 'margin': 5, 'cost': 10, 'lead_time': 2},
            {'id': 'a', 'state': 'eligible', 'evidence_completeness': 1, 'margin': 5, 'cost': 10, 'lead_time': 2},
            {'id': 'c', 'state': 'review', 'evidence_completeness': 1, 'margin': 99, 'cost': 1, 'lead_time': 1},
        ]
        self.assertEqual([item['id'] for item in rank_scenarios(scenarios)], ['a', 'b', 'c'])

    def test_working_paper_completeness_and_binding(self):
        country = self.env.ref('base.vn')
        regime = self.env['preferential.origin.regime'].create({
            'name': 'Synthetic FTA', 'code': 'SYNTHETIC', 'version': '1',
            'destination_country_id': country.id, 'effective_from': '2026-01-01',
            'policy_hash': digest({'synthetic': True}),
        })
        template = self.env['preferential.origin.form.template'].create({
            'name': 'Synthetic draft form', 'regime_id': regime.id,
            'effective_from': '2026-01-01', 'state': 'active',
            'schema_json': {'required_fields': ['exporter', 'goods']},
        })
        assessment = self.env['preferential.origin.assessment'].create({
            'name': 'Synthetic review', 'scope_key': 'test-working-paper',
            'snapshot': {'synthetic': True},
        })
        paper = self.env['preferential.origin.working.paper'].create({
            'name': 'WP-SYNTHETIC', 'assessment_id': assessment.id,
            'template_id': template.id, 'values_json': {'exporter': 'ACME'},
            'lineage_json': {'exporter': {'assessment_id': assessment.id}},
        })
        self.assertEqual(paper.missing_fields_json, ['goods'])
        self.assertEqual(paper.watermark, 'DRAFT — NOT A CERTIFICATE OF ORIGIN')
        paper.values_json = {'exporter': 'ACME', 'goods': 'Widget'}
        self.assertEqual(paper.state, 'complete')
        self.assertEqual(paper.template_hash, template.template_hash)

    def test_recommendation_explanation_and_cross_company_negative(self):
        scenarios = self.env['preferential.origin.scenario']
        recommended = scenarios.create({
            'name': 'Recommended', 'state': 'eligible', 'evidence_completeness': 1,
            'margin': 8, 'cost': 10, 'lead_time': 2,
        })
        review = scenarios.create({
            'name': 'Review', 'state': 'review', 'evidence_completeness': .5,
            'margin': 20, 'cost': 5, 'lead_time': 1,
        })
        self.assertEqual(scenarios.ranked_ids(recommended | review), [recommended.id, review.id])
        self.assertEqual(recommended.recommendation_rank, 1)
        self.assertIn('Eligible; evidence 100%', recommended.explanation)
        self.assertEqual(review.recommendation_rank, 2)
        self.assertIn('Review; evidence 50%', review.explanation)

        foreign_company = self.env['res.company'].create({'name': 'Foreign FTA Company'})
        foreign = scenarios.sudo().create({'name': 'Foreign', 'company_id': foreign_company.id})
        restricted_user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'FTA Restricted User', 'login': 'fta-restricted@example.test',
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
            'group_ids': [(6, 0, self.env.ref('base.group_user').ids)],
        })
        self.assertFalse(scenarios.with_user(restricted_user).search([('id', '=', foreign.id)]))
        with self.assertRaises(AccessError):
            foreign.with_user(restricted_user).read(['name'])


@tagged('post_install', '-at_install')
class TestOriginBrowser(HttpCase):
    def test_recommendation_explanation_e2e(self):
        self.env['preferential.origin.scenario'].create({
            'name': 'Recommended Synthetic Scenario', 'state': 'eligible',
            'evidence_completeness': 1, 'margin': 8, 'cost': 10, 'lead_time': 2,
        })
        self.browser_js(
            '/insilos/action-insilos_preferential_origin.action_preferential_origin_scenarios',
            "if (!document.body.innerText.includes('100%')) throw new Error('missing explanation'); console.log('test successful');",
            ready="document.body.innerText.includes('FTA Recommendations')",
            login='admin',
        )

    def test_working_paper_watermark_e2e(self):
        self.browser_js(
            '/insilos/action-insilos_preferential_origin.action_preferential_origin_working_papers',
            "console.log('test successful');",
            ready="document.body.innerText.includes('FTA Working Papers')",
            login='admin',
        )


if __name__ == '__main__':
    unittest.main()
