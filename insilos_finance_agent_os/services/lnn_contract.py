# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""LNN/CfC typed contract + SHADOW (E08/E09). Chưa có model thật — cố ý.

Đây là hợp đồng cho một service suy luận (liquid neural network) sẽ tồn tại
sau này. Ba luật an toàn được đóng đinh **trước khi** model đầu tiên chạy,
vì đóng sau nghĩa là đã có tín hiệu chưa kiểm vào decision path:

1. SHADOW-only. Tín hiệu ghi vào shadow log (JSON attachment trên work item)
   và dừng ở đó. Không skill nào, không packet nào đọc từ shadow log — gate
   `test_shadow_log_is_not_in_the_decision_path` giữ điều này ở mức source.
2. OOD trần cứng. `ood_confidence` dưới ngưỡng thì tín hiệu **không bao giờ**
   được xếp `high` — kể cả khi mọi trường khác đẹp. Model ngoài phân phối
   thường nói to nhất; trần này không cấu hình nới được bằng tham số runtime.
3. Vắng mặt là bình thường. Không có LNN service → `ingest` không được gọi
   → không degrade, không placeholder, hệ thống chạy như trước.
"""

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from types import MappingProxyType

from odoo.exceptions import UserError

CONTRACT_VERSION = 1
BENCHMARK_CONTRACT_VERSION = 1
SHADOW_ATTACHMENT_NAME = 'lnn_shadow_log.json'
ADVISORY_FORBIDDEN_ACTIONS = frozenset({'influence', 'write', 'stage', 'execute'})

# Dưới ngưỡng này mô hình tự nhận là ngoài phân phối — mọi tín hiệu chỉ được
# xếp tối đa 'untrusted'. Hằng số module, không phải config parameter: nới
# trần an toàn phải là một diff có review, không phải một lần set_param.
OOD_CONFIDENCE_FLOOR = 0.6

MARKET_REGIMES = ('risk_on', 'risk_off', 'transition', 'unknown')
LIQUIDITY_STATES = ('ample', 'adequate', 'tight', 'stressed')
VOLATILITY_STATES = ('low', 'normal', 'elevated', 'extreme')
FX_RISK_URGENCIES = ('none', 'monitor', 'act_soon', 'immediate')


@dataclass(frozen=True)
class LnnSignal:
    market_regime: str
    liquidity_state: str
    volatility_state: str
    fx_risk_urgency: str
    thesis_drift: float
    ood_confidence: float

    def __post_init__(self):
        # Hợp đồng typed: giá trị ngoài vốn từ vựng bị từ chối tại biên,
        # trước khi kịp vào shadow log. Enum lởm hôm nay là "regime mới
        # xuất hiện tự nhiên" trong báo cáo sáu tháng sau.
        for field_name, value, vocabulary in (
            ('market_regime', self.market_regime, MARKET_REGIMES),
            ('liquidity_state', self.liquidity_state, LIQUIDITY_STATES),
            ('volatility_state', self.volatility_state, VOLATILITY_STATES),
            ('fx_risk_urgency', self.fx_risk_urgency, FX_RISK_URGENCIES),
        ):
            if value not in vocabulary:
                raise UserError('LnnSignal.%s=%r is outside the contract vocabulary %r'
                                % (field_name, value, vocabulary))
        for field_name, value in (('thesis_drift', self.thesis_drift),
                                  ('ood_confidence', self.ood_confidence)):
            if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
                raise UserError('LnnSignal.%s=%r must be a float in [0, 1]'
                                % (field_name, value))


def classify_confidence(signal):
    """`high` | `advisory` | `untrusted` — với trần OOD cứng.

    Thứ tự kiểm là nội dung của luật: OOD xét TRƯỚC, mọi nhánh sau không
    thể nâng ngược lên. Một tín hiệu ngoài phân phối với thesis_drift đẹp
    vẫn là untrusted.
    """
    if signal.ood_confidence < OOD_CONFIDENCE_FLOOR:
        return 'untrusted'
    if signal.thesis_drift >= 0.5 or signal.fx_risk_urgency in ('act_soon', 'immediate'):
        return 'advisory'
    return 'high'


def evaluate_benchmark(cases, predictions):
    """Đánh giá deterministic/offline; fixture là oracle, không huấn luyện model."""
    if not cases or len(cases) != len(predictions):
        raise UserError('Benchmark cases and predictions must be non-empty and aligned')
    seen = set()
    correct = 0
    low_ood_high = 0
    for case, prediction in zip(cases, predictions):
        case_id = case.get('id')
        if not case_id or case_id in seen:
            raise UserError('Benchmark case IDs must be present and unique')
        seen.add(case_id)
        signal = LnnSignal(**prediction['signal'])
        confidence = classify_confidence(signal)
        correct += signal.market_regime == case['expected_market_regime']
        low_ood_high += signal.ood_confidence < OOD_CONFIDENCE_FLOOR and confidence == 'high'
    total = len(cases)
    result = {
        'contract_version': BENCHMARK_CONTRACT_VERSION,
        'case_count': total,
        'accuracy': correct / total,
        'low_ood_high_confidence_count': low_ood_high,
    }
    result['evidence_hash'] = sha256(json.dumps(
        {'cases': cases, 'predictions': predictions, 'result': result},
        sort_keys=True, separators=(',', ':'), ensure_ascii=False,
    ).encode()).hexdigest()
    return result


def _approval_digest(data):
    return sha256(json.dumps(data, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False).encode()).hexdigest()


def approve_benchmark(evaluation, cases, predictions, reviewer, authority, approved_at,
                      minimum_accuracy=0.8):
    """Audit authority duyệt đúng artifact; approval trả về là immutable."""
    if not all(isinstance(value, str) and value.strip()
               for value in (reviewer, authority, approved_at)):
        raise UserError('Benchmark approval requires reviewer, authority, and approved_at')
    recomputed = evaluate_benchmark(cases, predictions)
    if evaluation != recomputed:
        raise UserError('Benchmark evaluation is not bound to the supplied artifact')
    approval = {
        **recomputed,
        'reviewer': reviewer,
        'authority': authority,
        'approved_at': approved_at,
        'approved': (
            recomputed['accuracy'] >= minimum_accuracy
            and recomputed['low_ood_high_confidence_count'] == 0
        ),
    }
    approval['approval_digest'] = _approval_digest(approval)
    return MappingProxyType(approval)


def advisory_access(approved_benchmark, action='read'):
    """Promotion SHADOW→ADVISORY chỉ mở read-only với approval còn nguyên vẹn."""
    approval = dict(approved_benchmark)
    digest = approval.pop('approval_digest', None)
    if not digest or digest != _approval_digest(approval):
        raise UserError('ADVISORY requires an intact bound benchmark approval')
    if not approval.get('approved'):
        raise UserError('ADVISORY requires an approved benchmark')
    if action in ADVISORY_FORBIDDEN_ACTIONS or action != 'read':
        raise UserError('ADVISORY is read-only and cannot influence, write, stage, or execute')
    return 'advisory'


def ingest(env, work_item, signal, model_version):
    """Ghi một tín hiệu vào shadow log của work item. Đường ghi DUY NHẤT.

    Append-only về ngữ nghĩa: entry mới nối vào log cũ, không sửa entry cũ.
    Trả về attachment để test soi, nhưng không trả gì cho decision path —
    hàm này không có giá trị nào mà skill dùng được làm input.
    """
    work_item.ensure_one()
    entry = {
        'contract_version': CONTRACT_VERSION,
        'model_version': model_version,
        'signal': asdict(signal),
        'confidence': classify_confidence(signal),
        'logged_at': str(env.cr.now()),
    }
    attachment = env['ir.attachment'].search([
        ('res_model', '=', work_item._name),
        ('res_id', '=', work_item.id),
        ('name', '=', SHADOW_ATTACHMENT_NAME),
    ], limit=1)
    if attachment:
        log = json.loads(attachment.raw.decode())
        log['entries'].append(entry)
        attachment.write({'raw': json.dumps(log, ensure_ascii=False, indent=2).encode()})
    else:
        log = {'shadow': True, 'entries': [entry]}
        attachment = env['ir.attachment'].create({
            'name': SHADOW_ATTACHMENT_NAME,
            'raw': json.dumps(log, ensure_ascii=False, indent=2).encode(),
            'res_model': work_item._name,
            'res_id': work_item.id,
        })
    return attachment


def read_shadow_log(env, work_item):
    """Đọc shadow log — cho DASHBOARD/đánh giá offline, không cho skill.

    Tên hàm nói rõ nó là gì; gate source-level bảo đảm không skill nào
    import nó.
    """
    attachment = env['ir.attachment'].search([
        ('res_model', '=', work_item._name),
        ('res_id', '=', work_item.id),
        ('name', '=', SHADOW_ATTACHMENT_NAME),
    ], limit=1)
    if not attachment:
        return {'shadow': True, 'entries': []}
    return json.loads(attachment.raw.decode())
