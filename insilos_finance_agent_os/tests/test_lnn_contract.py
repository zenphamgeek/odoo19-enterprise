# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""E08/E09 — ba luật an toàn của LNN contract, mỗi luật một cách phá thử.

Luật khó giữ nhất là số 1 (SHADOW-only) vì nó là luật về *code chưa viết*:
skill tương lai có thể import shadow log làm input. Gate ở đây kiểm mức
source: không file nào trong `services/skills/` được nhắc tới `lnn_contract`.
"""

import json
from pathlib import Path

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..services import lnn_contract
from ..services.lnn_contract import LnnSignal


def _signal(**overrides):
    values = dict(market_regime='risk_off', liquidity_state='tight',
                  volatility_state='elevated', fx_risk_urgency='monitor',
                  thesis_drift=0.2, ood_confidence=0.9)
    values.update(overrides)
    return LnnSignal(**values)


@tagged('post_install', '-at_install', 'finance_agent_os')
class TestLnnContract(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.task = cls.env['project.task'].create({'name': 'LNN shadow case'})

    # -- typed contract -------------------------------------------------

    def test_vocabulary_is_enforced_at_the_boundary(self):
        with self.assertRaises(UserError) as ctx:
            _signal(market_regime='new_paradigm')
        self.assertIn('outside the contract vocabulary', str(ctx.exception))
        for field in ('thesis_drift', 'ood_confidence'):
            with self.assertRaises(UserError):
                _signal(**{field: 1.7})
            with self.assertRaises(UserError):
                _signal(**{field: 'high'})

    def test_signal_is_immutable(self):
        signal = _signal()
        with self.assertRaises(Exception):
            signal.thesis_drift = 0.99

    # -- luật 2: trần OOD cứng -----------------------------------------

    def test_ood_below_floor_is_never_high_confidence(self):
        """Chỗ mô hình ngoài phân phối nói to nhất: mọi trường khác đẹp,
        OOD thấp → vẫn untrusted. Quét lưới giá trị để không có khe."""
        for drift in (0.0, 0.3, 0.49):
            for urgency in ('none', 'monitor'):
                pretty = _signal(thesis_drift=drift, fx_risk_urgency=urgency,
                                 ood_confidence=lnn_contract.OOD_CONFIDENCE_FLOOR - 0.01)
                self.assertEqual(lnn_contract.classify_confidence(pretty), 'untrusted')

    def test_confidence_ladder_above_the_floor(self):
        self.assertEqual(lnn_contract.classify_confidence(_signal()), 'high')
        self.assertEqual(lnn_contract.classify_confidence(_signal(thesis_drift=0.7)), 'advisory')
        self.assertEqual(
            lnn_contract.classify_confidence(_signal(fx_risk_urgency='immediate')), 'advisory')

    # -- benchmark offline + promotion gate ----------------------------

    def test_offline_benchmark_is_reproducible_and_approvable(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'lnn_offline_benchmark.json').read_text())
        first = lnn_contract.evaluate_benchmark(fixture['cases'], fixture['predictions'])
        second = lnn_contract.evaluate_benchmark(fixture['cases'], fixture['predictions'])
        self.assertEqual(first, second)
        self.assertEqual(first['accuracy'], 1.0)
        self.assertEqual(first['low_ood_high_confidence_count'], 0)
        approved = lnn_contract.approve_benchmark(
            first, fixture['cases'], fixture['predictions'],
            reviewer='reviewer-1', authority='risk-committee', approved_at='2026-08-14T01:00:00Z')
        self.assertTrue(approved['approved'])
        self.assertEqual(lnn_contract.advisory_access(approved), 'advisory')
        with self.assertRaises(TypeError):
            approved['approved'] = False

    def test_approval_recomputes_artifact_and_requires_authority_data(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'lnn_offline_benchmark.json').read_text())
        evaluation = lnn_contract.evaluate_benchmark(fixture['cases'], fixture['predictions'])
        tampered = {**evaluation, 'accuracy': 1.0 - evaluation['accuracy']}
        with self.assertRaises(UserError):
            lnn_contract.approve_benchmark(
                tampered, fixture['cases'], fixture['predictions'], 'reviewer-1',
                'risk-committee', '2026-08-14T01:00:00Z')
        with self.assertRaises(UserError):
            lnn_contract.approve_benchmark(
                evaluation, fixture['cases'], fixture['predictions'], '',
                'risk-committee', '2026-08-14T01:00:00Z')

    def test_advisory_is_strictly_read_only_and_validates_binding(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'lnn_offline_benchmark.json').read_text())
        evaluation = lnn_contract.evaluate_benchmark(fixture['cases'], fixture['predictions'])
        approved = lnn_contract.approve_benchmark(
            evaluation, fixture['cases'], fixture['predictions'], 'reviewer-1',
            'risk-committee', '2026-08-14T01:00:00Z')
        for action in ('influence', 'write', 'stage', 'execute', 'draft'):
            with self.assertRaises(UserError, msg=action):
                lnn_contract.advisory_access(approved, action)
        with self.assertRaises(UserError):
            lnn_contract.advisory_access({**approved, 'reviewer': 'attacker'})

    # -- luật 1: SHADOW-only -------------------------------------------

    def test_ingest_appends_to_shadow_log_only(self):
        lnn_contract.ingest(self.env, self.task, _signal(), 'cfc-stub-0')
        lnn_contract.ingest(self.env, self.task, _signal(ood_confidence=0.2), 'cfc-stub-0')
        log = lnn_contract.read_shadow_log(self.env, self.task)
        self.assertTrue(log['shadow'])
        self.assertEqual(len(log['entries']), 2)
        self.assertEqual(log['entries'][0]['confidence'], 'high')
        self.assertEqual(log['entries'][1]['confidence'], 'untrusted')
        # Đúng một attachment shadow, entry nối thêm chứ không ghi đè.
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'project.task'), ('res_id', '=', self.task.id),
            ('name', '=', lnn_contract.SHADOW_ATTACHMENT_NAME)])
        self.assertEqual(len(attachments), 1)

    def test_shadow_log_is_not_in_the_decision_path(self):
        """Gate source-level: không skill nào chạm tới lnn_contract.

        Đây là luật về code chưa viết — skill tương lai thêm import này sẽ
        làm test fail, và người thêm phải đối diện quyết định kiến trúc thay
        vì trôi vào decision path một cách vô tình. decision_packet cũng
        không được đọc shadow log.
        """
        services_dir = Path(lnn_contract.__file__).resolve().parent
        offenders = []
        for path in sorted((services_dir / 'skills').glob('*.py')) + [services_dir / 'decision_packet.py']:
            source = path.read_text(encoding='utf-8')
            if 'lnn_contract' in source or 'lnn_shadow_log' in source:
                offenders.append(path.name)
        self.assertEqual(offenders, [],
                         'shadow log đã rò vào decision path: %s' % offenders)

    # -- luật 3: vắng mặt là bình thường -------------------------------

    def test_absence_of_lnn_service_changes_nothing(self):
        """Không ingest → log rỗng có cấu trúc, và không đường code nào khác
        của addon phụ thuộc vào sự tồn tại của shadow log (mọi suite trước
        E08 đã xanh khi chưa có file này — đây là chốt chặn hồi quy)."""
        untouched = self.env['project.task'].create({'name': 'No LNN here'})
        log = lnn_contract.read_shadow_log(self.env, untouched)
        self.assertEqual(log, {'shadow': True, 'entries': []})
