# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.addons.sign.tests.sign_request_common import SignRequestCommon
from odoo.tests.common import tagged

MODULE = 'insilos_treasury_market_risk'


@tagged('post_install', '-at_install', 'treasury_market_risk', 'treasury_l1', 'treasury_l3')
class TestTreasuryGovernanceSeed(SignRequestCommon):
    def test_template_has_full_committee_workflow(self):
        project = self.env.ref(f'{MODULE}.project_treasury_governance')
        self.assertTrue(project.is_template)
        self.assertEqual(project.type_ids.mapped('name'), [
            'Risk Trigger', 'Treasury Analysis', 'Decision Proposal', 'Risk Review',
            'Finance Review', 'Investment Committee', 'Execution', 'Settlement', 'Outcome Review',
        ])

    def _make_case(self):
        suffix = self.env['project.task'].search_count([])
        template = self.env.ref(f'{MODULE}.project_treasury_governance')
        project = template.copy({'name': 'TMR Gov Test', 'is_template': False})
        analyst = self.env['res.users'].create({
            'name': 'TMR Analyst', 'login': f'tmr_analyst_gov_{suffix}',
            'group_ids': [(4, self.env.ref(f'{MODULE}.group_treasury_analyst').id),
                          (4, self.env.ref('project.group_project_user').id)],
        })
        manager = self.env['res.users'].create({
            'name': 'TMR Manager', 'login': f'tmr_manager_gov_{suffix}', 'email': f'tmr_manager_gov_{suffix}@example.com',
            'group_ids': [(4, self.env.ref(f'{MODULE}.group_treasury_manager').id),
                          (4, self.env.ref('project.group_project_user').id)],
        })
        task = self.env['project.task'].with_user(analyst).create({
            'name': 'Hedge USD 8M', 'project_id': project.id,
            'stage_id': self.env.ref(f'{MODULE}.stage_decision_proposal').id,
        })
        return task, analyst, manager

    def _move_to_committee(self, task, manager):
        self.env['ir.attachment'].create({
            'name': 'evidence.json', 'raw': b'{}', 'res_model': 'project.task', 'res_id': task.id})
        task.description = '<p>%s</p>' % ('Hedge rationale with full context. ' * 3)
        task.action_snapshot_treasury_decision()
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_risk_review').id})
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_finance_review').id})
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_investment_committee').id})

    def _create_dual_signature_request(self, task, manager, state='sent', wrong_signer=False):
        cfo = self.env['res.users'].create({
            'name': 'TMR CFO', 'login': f'tmr_cfo_{task.id}_{state}', 'email': f'tmr_cfo_{task.id}_{state}@example.com',
            'group_ids': [(4, self.env.ref(f'{MODULE}.group_cfo').id)],
        })
        second_signer = manager.partner_id if wrong_signer else cfo.partner_id
        request = self.env['sign.request'].with_context(no_sign_mail=True).create({
            'template_id': self.template_2_roles.id,
            'reference': 'Treasury IC Pack',
            'reference_doc': f'project.task,{task.id}',
            'request_item_ids': [
                Command.create({'partner_id': manager.partner_id.id, 'role_id': self.role_signer_1.id}),
                Command.create({'partner_id': second_signer.id, 'role_id': self.role_signer_2.id}),
            ],
        })
        if state == 'signed':
            request.request_item_ids.filtered(lambda item: item.role_id == self.role_signer_1).sign(self.signer_1_sign_values_2_roles)
            request.request_item_ids.filtered(lambda item: item.role_id == self.role_signer_2).sign(self.signer_2_sign_values_2_roles)
        elif state == 'canceled':
            request.cancel()
        elif state == 'expired':
            request.validity = fields.Date.today().replace(year=fields.Date.today().year - 1)
            request._cron_reminder()
        return request

    def test_ai_challenge_is_source_restricted_and_has_no_write_tools(self):
        agent = self.env.ref(f'{MODULE}.ai_agent_treasury_decision_challenge')
        self.assertTrue(agent.restrict_to_sources)
        self.assertFalse(agent.topic_ids.tool_ids)
        prompt = agent.system_prompt.lower()
        for heading in ('observation', 'evidence', 'risk', 'alternatives', 'recommendation', 'confidence', 'assumptions', 'unknowns'):
            self.assertIn(heading, prompt)
        for phrase in ('read-only', 'never make', 'unverified'):
            self.assertIn(phrase, prompt)

    def test_proposer_cannot_move_case_to_committee(self):
        task, analyst, _manager = self._make_case()
        committee = self.env.ref(f'{MODULE}.stage_investment_committee')
        with self.assertRaises(UserError):
            task.with_user(analyst).write({'stage_id': committee.id})

    def test_risk_review_requires_decision_proposal(self):
        task, _analyst, manager = self._make_case()
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_treasury_analysis').id})
        with self.assertRaises(UserError):
            task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_risk_review').id})

    def test_committee_requires_finance_review_evidence_and_rationale(self):
        task, _analyst, manager = self._make_case()
        committee = self.env.ref(f'{MODULE}.stage_investment_committee')
        with self.assertRaises(UserError):
            task.with_user(manager).write({'stage_id': committee.id})
        with self.assertRaises(UserError):
            task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_finance_review').id})
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_risk_review').id})
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_finance_review').id})
        with self.assertRaises(UserError):
            task.with_user(manager).write({'stage_id': committee.id})
        self.env['ir.attachment'].create({
            'name': 'evidence.json', 'raw': b'{}', 'res_model': 'project.task', 'res_id': task.id})
        task.description = '<p>%s</p>' % ('Hedge rationale with full context. ' * 3)
        with self.assertRaises(UserError):
            task.with_user(manager).write({'stage_id': committee.id})
        task.action_snapshot_treasury_decision()
        task.with_user(manager).write({'stage_id': committee.id})
        self.assertEqual(task.stage_id, committee)

    def test_decision_snapshot_is_immutable_and_preserves_ai_recommendation(self):
        task, _analyst, _manager = self._make_case()
        task.write({'treasury_recommendation': 'Hedge 80% of USD exposure.'})
        task.action_snapshot_treasury_decision()
        task.write({'treasury_recommendation': 'Hedge 70% of USD exposure.'})
        self.assertEqual(task.treasury_decision_snapshot['recommendation'], 'Hedge 80% of USD exposure.')
        with self.assertRaises(UserError):
            task.action_snapshot_treasury_decision()
        with self.assertRaises(UserError):
            task.write({'treasury_decision_snapshot': {}})

    def test_human_override_requires_snapshot_and_auditable_rationale(self):
        task, _analyst, manager = self._make_case()
        with self.assertRaises(UserError):
            task.action_record_treasury_override('Hedge 70%', 'Rationale that is sufficiently long to be independently understood.')
        task.action_snapshot_treasury_decision()
        with self.assertRaises(UserError):
            task.action_record_treasury_override('Hedge 70%', 'too short')
        task.with_user(manager).action_record_treasury_override(
            'Hedge 70%', 'Liquidity uncertainty justifies a lower ratio than the AI recommendation today.'
        )
        self.assertEqual(task.treasury_human_decision, 'Hedge 70%')
        self.assertEqual(task.treasury_override_by_id, manager)
        self.assertTrue(task.treasury_override_at)

    def test_outcome_variance_is_expected_vs_actual_less_cost(self):
        task, _analyst, _manager = self._make_case()
        task.write({'treasury_expected_benefit': 100, 'treasury_actual_benefit': 130, 'treasury_hedge_cost': 20})
        self.assertEqual(task.treasury_decision_variance, 10)

    def test_execution_requires_signed_treasury_manager_and_cfo(self):
        execution = self.env.ref(f'{MODULE}.stage_execution')
        for state, wrong_signer in (('sent', False), ('canceled', False), ('expired', False), ('signed', True)):
            task, _analyst, manager = self._make_case()
            self._move_to_committee(task, manager)
            self._create_dual_signature_request(task, manager, state, wrong_signer)
            with self.assertRaises(UserError):
                task.with_user(manager).write({'stage_id': execution.id})
        task, _analyst, manager = self._make_case()
        self._move_to_committee(task, manager)
        request = self._create_dual_signature_request(task, manager, 'signed')
        self.assertEqual(request.state, 'signed')
        self.assertEqual(task.treasury_sign_status, 'signed')
        self.assertEqual(task.treasury_sign_request_count, 1)
        self.assertEqual(task.treasury_signer_count, 2)
        task.with_user(manager).write({'stage_id': execution.id})
        self.assertEqual(task.stage_id, execution)

    def test_settlement_requires_execution(self):
        task, _analyst, manager = self._make_case()
        with self.assertRaises(UserError):
            task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_settlement').id})

    def test_outcome_review_requires_settlement(self):
        task, _analyst, manager = self._make_case()
        with self.assertRaises(UserError):
            task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_outcome_review').id})

    def test_execution_schedules_post_decision_reviews(self):
        task, _analyst, manager = self._make_case()
        self._move_to_committee(task, manager)
        self._create_dual_signature_request(task, manager, 'signed')
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_execution').id})
        summaries = task.activity_ids.mapped('summary')
        self.assertIn('Post-decision review (30D)', summaries)
        self.assertIn('Post-decision review (90D)', summaries)
        # A returned case must restart at Proposal, then repeat reviews without duplicate activities.
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_decision_proposal').id})
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_risk_review').id})
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_finance_review').id})
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_investment_committee').id})
        task.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.stage_execution').id})
        self.assertEqual(len(task.activity_ids.filtered(lambda a: a.summary == 'Post-decision review (30D)')), 1)

    def test_all_treasury_crons_are_inactive(self):
        crons = self.env['ir.cron']
        for xmlid in ('cron_fx_exposure', 'cron_liquidity_projection', 'cron_portfolio_risk', 'cron_limit_scan'):
            crons |= self.env.ref(f'{MODULE}.{xmlid}')
        self.assertEqual(len(crons), 4)
        self.assertFalse(any(crons.mapped('active')))
