# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""E02 — alias phải phân giải thật, và thiếu required phải ép read-only thật.

Điểm dễ sai nhất của capability layer là failure mode: log một dòng cảnh báo
rồi chạy tiếp. Bộ test này chứng minh chiều ngược lại — thiếu alias required
thì `assert_writable` ném `UserError`, không có đường ghi nào đi tiếp.
"""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..services import capability


@tagged('post_install', '-at_install', 'finance_agent_os')
class TestCapabilityResolver(TransactionCase):
    def test_every_required_alias_resolves_on_this_database(self):
        """Bảng alias trong plan phải khớp DB thật, không phải DB tưởng tượng."""
        for alias in capability.REQUIRED_ALIASES:
            cap = capability.resolve(self.env, alias)
            self.assertIsNotNone(cap, 'required alias %s không phân giải được' % alias)
            # Model phân giải ra phải nằm trong registry thật, không chỉ là chuỗi.
            for model in cap.models:
                self.assertIsNotNone(self.env.registry.get(model))
        self.assertEqual(capability.missing_required(self.env), [])
        self.assertFalse(capability.is_read_only(self.env))

    def test_authority_semantic_aliases_are_exact_and_resolve(self):
        self.assertEqual(
            capability.SEMANTIC_ALIASES,
            ('business_record', 'document_evidence', 'conversation_audit',
             'task_or_review', 'approval_request', 'authorized_action_stage'),
        )
        for alias in capability.SEMANTIC_ALIASES:
            self.assertIsNotNone(capability.resolve(self.env, alias), alias)

        cap = capability.resolve(self.env, 'document_evidence')
        self.assertEqual(cap.models, ('documents.document', 'ir.attachment'))
        self.assertEqual(cap.model, 'documents.document')

    def test_unknown_alias_is_a_programming_error_not_a_degrade(self):
        """Gõ nhầm alias phải nổ ngay, không được đọc thành 'capability absent'."""
        with self.assertRaises(UserError):
            capability.resolve(self.env, 'identiy')

    def test_require_returns_all_or_raises_naming_the_missing(self):
        resolved = capability.require(self.env, 'identity', 'work_item')
        self.assertEqual(set(resolved), {'identity', 'work_item'})
        with patch.dict(capability.REGISTRY, {'identity': (('no.such.model',), True, None)}):
            with self.assertRaises(UserError) as ctx:
                capability.require(self.env, 'identity', 'work_item')
            self.assertIn('identity', str(ctx.exception))

    def test_missing_required_forces_read_only_not_a_warning(self):
        """`on_missing_required_capability: read_only` phải có răng.

        Mô phỏng tenant mất `work_item`: mọi đường ghi qua `assert_writable`
        phải bị chặn bằng exception, còn `resolve` alias khác vẫn đọc được.
        """
        with patch.dict(capability.REGISTRY, {'work_item': (('no.such.model',), True, None)}):
            self.assertEqual(capability.missing_required(self.env), ['work_item'])
            self.assertTrue(capability.is_read_only(self.env))
            with self.assertRaises(UserError) as ctx:
                capability.assert_writable(self.env)
            self.assertIn('read-only', str(ctx.exception))
            self.assertIn('work_item', str(ctx.exception))
            # READ không bị vạ lây: alias khác vẫn phân giải bình thường.
            self.assertIsNotNone(capability.resolve(self.env, 'party'))

    def test_missing_optional_disables_one_feature_and_names_it(self):
        with patch.dict(capability.REGISTRY, {'automation': (('no.such.model',), False, 'rule_automation')}):
            degraded = capability.degraded_modes(self.env)
            self.assertEqual(degraded.get('automation'), 'rule_automation')
            # Optional thiếu không được kéo cả lớp về read-only.
            self.assertFalse(capability.is_read_only(self.env))
            capability.assert_writable(self.env)

    def test_fallback_order_first_present_candidate_wins(self):
        with patch.dict(capability.REGISTRY, {'rule_target': (('no.such.model', 'capital.alert.rule'), False, 'limit_rules')}):
            cap = capability.resolve(self.env, 'rule_target')
            self.assertEqual(cap.model, 'capital.alert.rule')
