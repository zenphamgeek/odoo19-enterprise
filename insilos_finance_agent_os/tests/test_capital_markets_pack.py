# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""E05 — con số không nguồn bị từ chối phát ngôn, không phải đánh dấu.

Test trung tâm theo plan: "bịa một con số không có evidence → skill phải từ
chối phát ngôn." Đường đó nằm ở `_fact` — mọi phát ngôn số liệu đi qua đó,
và ref rỗng ném `UserError` ngay tại chỗ tạo fact.
"""

import json

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..services import decision_packet
from ..services.skills import base, capital_markets

MODULE = 'insilos_treasury_market_risk'


@tagged('post_install', '-at_install', 'finance_agent_os')
class TestCapitalMarketsPack(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portfolio = cls.env['capital.portfolio'].create({'name': 'E05 Book'})
        cls.instrument = cls.env['capital.instrument'].create({
            'symbol': 'E05', 'exchange': 'HOSE',
            'currency_id': cls.env.ref('base.VND').id,
        })
        cls.position = cls.env['capital.position'].create({
            'portfolio_id': cls.portfolio.id,
            'instrument_id': cls.instrument.id,
            'quantity': 5000.0,
            'average_cost': 21.5,
        })
        cls.rule = cls.env['capital.alert.rule'].create({
            'name': 'E05 price floor',
            'portfolio_id': cls.portfolio.id,
            'symbol': 'E05',
            'kind': 'price_below',
            'threshold': 20.0,
        })
        template = cls.env.ref(f'{MODULE}.project_treasury_governance')
        cls.project = template.copy({'name': 'E05 IC', 'is_template': False})

    def test_agent_and_topics_ship_with_the_module(self):
        agent = self.env.ref('insilos_finance_agent_os.ai_agent_finance_os')
        self.assertTrue(agent.restrict_to_sources,
                        'agent không restrict_to_sources là agent được phép bịa')
        self.assertFalse(
            self.env.ref('insilos_finance_agent_os.ai_topic_capital_markets').tool_ids,
            'tool set rỗng là trạng thái fail-safe; bind tool phải là quyết định riêng')

    def test_unsourced_figure_is_refused_not_flagged(self):
        """Test trung tâm của E05 theo plan."""
        with self.assertRaises(UserError) as ctx:
            capital_markets._fact('made up alpha', 0.42, '')
        self.assertIn('Refusing to state', str(ctx.exception))
        with self.assertRaises(UserError):
            capital_markets._fact('made up beta', 1.7, None)

    def test_explain_limit_breach_speaks_only_recorded_figures(self):
        # Rule chưa trigger: không có gì để giải thích, và nói thẳng như vậy.
        result = capital_markets.explain_limit_breach(self.env, self.rule)
        self.assertFalse(result['triggered'])
        self.assertIn('has not triggered', result['statement'])
        # Trigger qua đúng đường domain, rồi giải thích từ số rule đã ghi.
        self.rule._fire(19.2)
        result = capital_markets.explain_limit_breach(self.env, self.rule)
        self.assertTrue(result['triggered'])
        by_label = {f['label']: f for f in result['facts']}
        self.assertEqual(by_label['threshold']['value'], 20.0)
        self.assertEqual(by_label['observed_value']['value'], 19.2)
        ref = 'capital.alert.rule,%d' % self.rule.id
        for fact in result['facts']:
            self.assertEqual(fact['ref'], ref)
        self.assertIn('not a recommendation', result['statement'])

    def test_prepare_ic_case_drafts_first_stage_with_verified_packet(self):
        case = capital_markets.prepare_ic_case(
            self.env, self.project, self.position,
            'Thesis: steel demand recovery through 2027.')
        self.assertEqual(case.stage_id, self.project.type_ids[:1])
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'project.task'), ('res_id', '=', case.id)])
        self.assertEqual(len(attachment), 1)
        packet = decision_packet.load(attachment)  # verify hash luôn thể
        by_label = {i['label']: i for i in packet['inputs']}
        self.assertEqual(by_label['quantity']['value'], self.position.quantity)
        self.assertEqual(by_label['market_value']['value'], self.position.market_value)
        # Mark chưa fresh: caveat phải nằm trong packet mà IC sẽ đọc.
        self.assertIn('mark_caveat', by_label)
        self.assertEqual(packet['recommendation']['action'], 'submit_to_ic')

    def test_capital_markets_ic_case_reaches_committee_through_domain_gates(self):
        case = capital_markets.prepare_ic_case(
            self.env, self.project, self.position,
            'Thesis: governed committee review based on the attached position evidence.')
        case.write({'stage_id': self.env.ref(
            f'{MODULE}.stage_decision_proposal').id})
        case.action_snapshot_treasury_decision()
        manager = self.env['res.users'].create({
            'name': 'E05 IC Manager', 'login': 'e05_ic_manager',
            'group_ids': [(4, self.env.ref(f'{MODULE}.group_treasury_manager').id),
                          (4, self.env.ref('project.group_project_manager').id)],
        })
        for stage in ('stage_risk_review', 'stage_finance_review',
                      'stage_investment_committee'):
            case.with_user(manager).write({'stage_id': self.env.ref(f'{MODULE}.{stage}').id})
        self.assertEqual(case.stage_id, self.env.ref(f'{MODULE}.stage_investment_committee'))
        self.assertFalse(self.env['capital.order'].search([('decision_case_id', '=', case.id)]))

    def test_pack_skills_registered_with_declared_modes(self):
        self.assertEqual(base.SKILL_MODES['explain_limit_breach'], base.READ)
        self.assertEqual(base.SKILL_MODES['prepare_ic_case'], base.DRAFT)
