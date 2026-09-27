# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""E06 — engine trả X thì agent nói X, và engine hỏng thì nói "engine hỏng".

Hai bất biến từ plan:
1. "AI giải thích kết quả engine; không tự tính lại. Test: engine trả X,
   agent nói X, không phải X′." — so sánh bằng `assertEqual` với chính giá
   trị engine trả trong cùng transaction; skill chỉ được bọc, không được sửa.
2. Engine outage: patch engine ném RuntimeError → skill trả `engine_errors`
   có cấu trúc, KHÔNG exception, KHÔNG số bịa thế chỗ.
"""

import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.insilos_treasury_market_risk.services import (
    exposure_engine,
    liquidity_engine,
    risk_engine,
)

from ..services.skills import base, treasury_fx


@tagged('post_install', '-at_install', 'finance_agent_os')
class TestTreasuryFxPack(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    def test_all_pack_skills_are_read_only(self):
        for name in ('explain_fx_exposure', 'explain_liquidity', 'explain_portfolio_risk'):
            self.assertEqual(base.SKILL_MODES[name], base.READ,
                             '%s phải là READ: pack này chỉ giải thích' % name)

    def test_fx_proposal_is_deterministic_and_staged_without_execution(self):
        project = self.env.ref(
            'insilos_treasury_market_risk.project_treasury_governance').copy({
                'name': 'E06 FX Proposal', 'is_template': False})
        sources = ['account.move.line:USD', 'policy:hedge-ratio-v1']
        first = treasury_fx.stage_fx_hedge_proposal(
            self.env, project, 3500000.0, 2000000.0, 26250.0, 4.0, sources)
        second = treasury_fx.stage_fx_hedge_proposal(
            self.env, project, 3500000.0, 2000000.0, 26250.0, 4.0, sources)
        proposal = json.loads(first.treasury_alternatives)
        self.assertEqual(first.stage_id, self.env.ref(
            'insilos_treasury_market_risk.stage_decision_proposal'))
        self.assertEqual(first.treasury_alternatives, second.treasury_alternatives)
        self.assertEqual([option['ratio_pct'] for option in proposal['options']],
                         [70.0, 80.0, 100.0])
        self.assertEqual(proposal['options'][1]['incremental_hedge'], 800000.0)
        self.assertFalse(self.env['capital.order'].search([
            ('decision_case_id', 'in', (first.id, second.id))]))

    def test_agent_says_x_when_engine_says_x(self):
        """Bất biến trung tâm E06: không X′, không làm tròn, không chỉnh."""
        ids = [self.company.id]
        engine_net = exposure_engine.net_open_position(self.env, ids)
        engine_commit = exposure_engine.commitments(self.env, ids)
        report = treasury_fx.explain_fx_exposure(self.env, self.company)
        by_ref = {f['ref']: f['value'] for f in report['facts']}
        self.assertEqual(by_ref['engine:exposure_engine.net_open_position'], engine_net)
        self.assertEqual(by_ref['engine:exposure_engine.commitments'], engine_commit)
        self.assertEqual(report['engine_errors'], [])

    def test_liquidity_report_carries_engine_figures_verbatim(self):
        ids = [self.company.id]
        engine_opening = liquidity_engine.opening_liquidity(self.env, ids)
        report = treasury_fx.explain_liquidity(self.env, self.company)
        by_ref = {f['ref']: f['value'] for f in report['facts']}
        self.assertEqual(by_ref['engine:liquidity_engine.opening_liquidity'], engine_opening)
        # survival_horizon chỉ xuất hiện khi cả hai đầu vào của nó có mặt.
        self.assertIn('engine:liquidity_engine.ladder', by_ref)
        self.assertIn('engine:liquidity_engine.survival_horizon', by_ref)

    def test_risk_report_matches_engine_pair(self):
        engine_metrics = risk_engine.portfolio_metrics(self.env, self.company)
        report = treasury_fx.explain_portfolio_risk(self.env, self.company)
        by_ref = {f['ref']: f['value'] for f in report['facts']}
        self.assertEqual(by_ref['engine:risk_engine.portfolio_metrics'], engine_metrics)
        self.assertIn('engine:risk_engine.limit_utilization', by_ref)

    def test_every_fact_carries_an_engine_ref(self):
        report = treasury_fx.explain_fx_exposure(self.env, self.company)
        for fact in report['facts']:
            self.assertTrue(fact['ref'].startswith('engine:'),
                            'fact %r không có engine ref' % fact['label'])

    def test_engine_outage_is_reported_not_papered_over(self):
        """Engine chết → sự kiện có cấu trúc, không exception, không số bịa."""
        with patch.object(exposure_engine, 'net_open_position',
                          side_effect=RuntimeError('ledger unavailable')):
            report = treasury_fx.explain_fx_exposure(self.env, self.company)
        refs = [f['ref'] for f in report['facts']]
        self.assertNotIn('engine:exposure_engine.net_open_position', refs,
                         'engine hỏng mà vẫn có fact là số bịa')
        # entity_exposure gọi net_open_position bên trong nên chết theo —
        # đúng ngữ nghĩa: số dẫn xuất từ engine hỏng cũng phải vắng mặt.
        error_refs = [e['ref'] for e in report['engine_errors']]
        self.assertIn('engine:exposure_engine.net_open_position', error_refs)
        self.assertIn('engine:exposure_engine.entity_exposure', error_refs)
        self.assertNotIn('engine:exposure_engine.entity_exposure', refs)
        for error in report['engine_errors']:
            self.assertIn('RuntimeError', error['error'])
        # Engine khác không bị vạ lây: commitments vẫn có mặt.
        self.assertIn('engine:exposure_engine.commitments', refs)

    def test_dependent_figures_are_skipped_when_their_input_engine_dies(self):
        """survival_horizon cần opening + ladder; opening chết thì nó phải vắng
        mặt, không phải được tính từ số bịa."""
        with patch.object(liquidity_engine, 'opening_liquidity',
                          side_effect=RuntimeError('bank feed down')):
            report = treasury_fx.explain_liquidity(self.env, self.company)
        refs = [f['ref'] for f in report['facts']]
        self.assertNotIn('engine:liquidity_engine.survival_horizon', refs)
        self.assertEqual(report['engine_errors'][0]['ref'],
                         'engine:liquidity_engine.opening_liquidity')
