# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""E07 — packet phải bất biến thật, và drift phải chỉ đúng chỗ trôi.

Đường kiểm quan trọng nhất là tamper: sửa một ký tự trong attachment đã lưu
thì `load` phải từ chối. Nếu đường đó không nổ, "bất biến" chỉ là một câu
trong docstring.
"""

import json

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..services import decision_packet

INPUTS = [
    {'ref': 'capital.position,7', 'label': 'HPG quantity', 'value': 10000},
    {'ref': 'mcp:quote:abc123', 'label': 'HPG close', 'value': 20600},
]
RECOMMENDATION = {'action': 'trim', 'size': 2000, 'rationale': 'concentration above limit'}
CONTEXT = {'skill': 'explain_position', 'mode': 'REPORT', 'user': 'fao_analyst'}


@tagged('post_install', '-at_install', 'finance_agent_os')
class TestDecisionPacket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.task = cls.env['project.task'].create({'name': 'FAO packet case'})

    def _packet(self):
        return decision_packet.build(INPUTS, RECOMMENDATION, CONTEXT)

    def test_build_is_deterministic_and_order_insensitive(self):
        a = decision_packet.build(INPUTS, RECOMMENDATION, CONTEXT)
        b = decision_packet.build(list(reversed(INPUTS)), RECOMMENDATION, CONTEXT)
        self.assertEqual(a['packet_hash'], b['packet_hash'],
                         'thứ tự inputs không được đổi hash')

    def test_canonical_replay_fixture_hash_is_locked(self):
        self.assertEqual(
            self._packet()['packet_hash'],
            '619cd5ad94cf43d3f1d31ac5ffb65f1903c57d882051a94dfcff8242ac1c8e1c')

    def test_build_refuses_orphan_inputs(self):
        with self.assertRaises(UserError) as ctx:
            decision_packet.build(INPUTS + [{'label': 'made up', 'value': 1}],
                                  RECOMMENDATION, CONTEXT)
        self.assertIn('no source ref', str(ctx.exception))

    def test_attach_load_roundtrip_verifies(self):
        attachment = decision_packet.attach(self.env, self.task, self._packet())
        self.assertTrue(attachment.name.startswith('decision_packet_'))
        loaded = decision_packet.load(attachment)
        self.assertEqual(loaded['recommendation'], RECOMMENDATION)

    def test_tampered_attachment_is_refused(self):
        """Bất biến có răng: sửa một giá trị trong file đã lưu → từ chối."""
        attachment = decision_packet.attach(self.env, self.task, self._packet())
        doctored = json.loads(attachment.raw.decode())
        doctored['recommendation']['size'] = 8000  # ai đó "chỉnh nhẹ" lịch sử
        attachment.write({'raw': json.dumps(doctored).encode()})
        with self.assertRaises(UserError) as ctx:
            decision_packet.load(attachment)
        self.assertIn('integrity', str(ctx.exception))

    def test_tampering_the_hash_itself_is_also_refused(self):
        attachment = decision_packet.attach(self.env, self.task, self._packet())
        doctored = json.loads(attachment.raw.decode())
        doctored['packet_hash'] = '0' * 64
        attachment.write({'raw': json.dumps(doctored).encode()})
        with self.assertRaises(UserError):
            decision_packet.load(attachment)

    def test_diff_names_exactly_what_changed(self):
        old = self._packet()
        new_inputs = [
            INPUTS[0],  # giữ nguyên
            {'ref': 'mcp:quote:abc123', 'label': 'HPG close', 'value': 19800},  # trôi
            {'ref': 'capital.fx.rate,3', 'label': 'USDVND', 'value': 25400},  # thêm
        ]
        new = decision_packet.build(new_inputs, {'action': 'hold'}, CONTEXT)
        drift = decision_packet.diff(old, new)
        self.assertEqual(drift['inputs_added'], ['capital.fx.rate,3'])
        self.assertEqual(drift['inputs_drifted']['mcp:quote:abc123']['now']['value'], 19800)
        self.assertNotIn('inputs_removed', drift)
        self.assertEqual(drift['recommendation']['now'], {'action': 'hold'})

    def test_diff_of_identical_packets_is_empty(self):
        self.assertEqual(decision_packet.diff(self._packet(), self._packet()), {})

    def test_replay_reports_drift_against_stored_packet(self):
        attachment = decision_packet.attach(self.env, self.task, self._packet())

        def rebuild_same(env):
            return INPUTS, RECOMMENDATION, CONTEXT

        result = decision_packet.replay(self.env, attachment, rebuild_same)
        self.assertEqual(result['drift'], {}, 'inputs y nguyên thì drift phải rỗng')

        def rebuild_drifted(env):
            drifted = [dict(INPUTS[0], value=9000), INPUTS[1]]
            return drifted, RECOMMENDATION, CONTEXT

        result = decision_packet.replay(self.env, attachment, rebuild_drifted)
        self.assertEqual(list(result['drift']), ['inputs_drifted'])
        self.assertIn('capital.position,7', result['drift']['inputs_drifted'])
