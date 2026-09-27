# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""E04 — trần quyền của skill là thứ phải chứng minh, không phải tin.

Ba bất biến:
1. Mode thấp gọi helper ghi cao hơn → nổ tại decorator/context, trước khi
   kịp ghi gì.
2. Tenant read-only (thiếu capability required) → mọi skill khác READ bị
   chặn ngay cửa.
3. CONTROLLED không vượt được stage gate của domain: skill cho case nhảy
   Decision Proposal → Execution phải nhận đúng `UserError` mà một người
   dùng thường cũng nhận — cùng bất biến chaos test AI outage đang giữ.
"""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..services import capability
from ..services.skills import base, finance_core

MODULE = 'insilos_treasury_market_risk'


@tagged('post_install', '-at_install', 'finance_agent_os')
class TestFinanceCoreSkills(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        template = cls.env.ref(f'{MODULE}.project_treasury_governance')
        cls.project = template.copy({'name': 'FAO Skill Test', 'is_template': False})
        cls.task = cls.env['project.task'].create({
            'name': 'FAO governed case',
            'project_id': cls.project.id,
            'stage_id': cls.env.ref(f'{MODULE}.stage_decision_proposal').id,
        })

    def test_skill_registry_locks_the_mode_table(self):
        """Bảng skill → mode theo build spec, khoá bằng test."""
        self.assertEqual(base.SKILL_MODES, {
            # finance_core (E04)
            'explain_position': base.READ,
            'evidence_pack': base.REPORT,
            'draft_proposal': base.DRAFT,
            'execute_governed_action': base.CONTROLLED,
            # capital_markets (E05)
            'explain_limit_breach': base.READ,
            'prepare_ic_case': base.DRAFT,
            # treasury_fx (E06)
            'explain_fx_exposure': base.READ,
            'explain_liquidity': base.READ,
            'explain_portfolio_risk': base.READ,
            'stage_fx_hedge_proposal': base.DRAFT,
        })

    def test_read_mode_cannot_reach_any_write_helper(self):
        ctx = base.SkillContext(self.env, base.READ)
        with self.assertRaises(UserError):
            ctx.post_evidence(self.task, body='x')
        with self.assertRaises(UserError):
            ctx.create_draft('project.task', {})
        with self.assertRaises(UserError):
            ctx.run_governed(self.task, 'write', {})

    def test_report_mode_stops_below_draft_and_controlled(self):
        ctx = base.SkillContext(self.env, base.REPORT)
        with self.assertRaises(UserError):
            ctx.create_draft('project.task', {})
        with self.assertRaises(UserError):
            ctx.run_governed(self.task, 'write', {})

    def test_explain_position_reads_domain_figures_verbatim(self):
        """Agent nói X khi domain nói X — không tính lại, không làm tròn."""
        portfolio = self.env['capital.portfolio'].create({'name': 'FAO Book'})
        instrument = self.env['capital.instrument'].create({
            'symbol': 'FAO', 'exchange': 'HOSE',
            'currency_id': self.env.ref('base.VND').id,
        })
        position = self.env['capital.position'].create({
            'portfolio_id': portfolio.id,
            'instrument_id': instrument.id,
            'quantity': 1234.0,
            'average_cost': 67.1,
        })
        result = finance_core.explain_position(self.env, position)
        self.assertEqual(result['quantity'], position.quantity)
        self.assertEqual(result['average_cost'], position.average_cost)
        self.assertEqual(result['market_value'], position.market_value)
        self.assertEqual(result['record'], 'capital.position,%d' % position.id)
        # Chưa có mark: caveat phải nói thẳng, không phải im lặng với số 0.
        self.assertTrue(result['caveats'])

    def test_golden_research_uat_is_deterministic(self):
        portfolio = self.env['capital.portfolio'].create({'name': 'Golden Research'})
        instrument = self.env['capital.instrument'].create({
            'symbol': 'GOLDEN', 'exchange': 'HOSE',
            'currency_id': self.env.ref('base.VND').id,
        })
        position = self.env['capital.position'].create({
            'portfolio_id': portfolio.id, 'instrument_id': instrument.id,
            'quantity': 1234.0, 'average_cost': 67.1,
        })
        first = finance_core.explain_position(self.env, position)
        second = finance_core.explain_position(self.env, position)
        self.assertEqual(first, second)
        self.assertEqual(first['record'], 'capital.position,%d' % position.id)
        self.assertTrue(first['caveats'])

    def test_evidence_pack_refuses_orphan_facts(self):
        with self.assertRaises(UserError) as ctx:
            finance_core.evidence_pack(self.env, self.task, 'FX exposure', [
                {'label': 'USD net', 'value': -3500000, 'ref': 'account.move.line domain'},
                {'label': 'made up', 'value': 42},
            ])
        self.assertIn('no source ref', str(ctx.exception))
        # Fact đủ nguồn thì ghi được: message + attachment trên task.
        finance_core.evidence_pack(self.env, self.task, 'FX exposure', [
            {'label': 'USD net', 'value': -3500000, 'ref': 'account.move.line domain'},
        ])
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'project.task'), ('res_id', '=', self.task.id),
            ('name', '=', 'evidence_pack.json')])
        self.assertTrue(attachment)

    def test_draft_proposal_lands_in_first_stage_only(self):
        draft = finance_core.draft_proposal(
            self.env, self.project, 'Hedge USD 8M',
            'Rationale long enough to be read by someone outside the room.')
        self.assertEqual(draft.stage_id, self.project.type_ids[:1])
        self.assertEqual(draft.project_id, self.project)

    def test_controlled_skill_cannot_jump_the_stage_gate(self):
        """Bất biến trung tâm của E04: CONTROLLED vẫn đứng sau gate domain."""
        execution = self.env.ref(f'{MODULE}.stage_execution')
        with self.assertRaises(UserError):
            finance_core.execute_governed_action(
                self.env, self.task, 'write', {'stage_id': execution.id})
        # Case không nhúc nhích.
        self.assertEqual(self.task.stage_id, self.env.ref(f'{MODULE}.stage_decision_proposal'))

    def test_controlled_skill_does_not_escalate_privilege(self):
        """`run_governed` không được sudo — đo trực tiếp `env.su` tại domain.

        Bắt buộc đo trực tiếp: stage gate đọc `env.user` (thứ `sudo()` giữ
        nguyên) nên một sabotage `record.sudo()` vẫn qua được test nhảy stage
        — nhưng nó tắt ACL/record rule một cách vô hình. Probe này gắn tạm
        một method lên `project.task` trả về `self.env.su` tại thời điểm domain
        method chạy: đó chính là giá trị mà ACL sẽ nhìn thấy.
        """
        def fao_su_probe(records):
            return records.env.su

        # Env test mặc định là SUPERUSER (su=True sẵn) — probe phải chạy
        # dưới một user thường, nếu không sabotage sudo() sẽ vô hình.
        user = self.env.ref('base.user_admin')
        env = self.env(user=user)
        task = self.task.with_user(user)
        self.assertFalse(env.su, 'probe setup sai: env đã su từ đầu')
        with patch.object(type(self.env['project.task']), 'fao_su_probe',
                          fao_su_probe, create=True):
            self.assertFalse(
                finance_core.execute_governed_action(env, task, 'fao_su_probe'),
                'run_governed đã escalate: domain method chạy dưới sudo')

    def test_read_only_tenant_blocks_every_writing_skill_at_the_door(self):
        with patch.dict(capability.REGISTRY, {'work_item': (('no.such.model',), True, None)}):
            # READ vẫn chạy.
            portfolio = self.env['capital.portfolio'].search([], limit=1)
            position = self.env['capital.position'].search([], limit=1)
            if position:
                finance_core.explain_position(self.env, position)
            # Mọi mode ghi bị chặn trước khi hàm skill chạy.
            for call in (
                lambda: finance_core.evidence_pack(self.env, self.task, 't', []),
                lambda: finance_core.draft_proposal(self.env, self.project, 'n', 'r'),
                lambda: finance_core.execute_governed_action(self.env, self.task, 'write', {}),
            ):
                with self.assertRaises(UserError) as ctx:
                    call()
                self.assertIn('read-only', str(ctx.exception))
