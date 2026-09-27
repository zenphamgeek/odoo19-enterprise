# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""MCP Gateway — cửa duy nhất cho dữ liệu ngoài vào lớp agent (E03).

Sidecar là một provider. Gateway là một **chính sách**: mọi tool đi qua đây
phải khai trước trong registry, mọi kết quả phải mang lineage đầy đủ, và mọi
lỗi phải có hình dạng — `unavailable`/`disabled` là kết quả có cấu trúc mà
skill buộc phải xử lý, không phải exception nuốt được rồi bịa số thay thế.

Bốn luật, mỗi luật có một lý do cụ thể:

- **Registry đóng.** Tool không khai trước thì không gọi được. Một agent được
  phép gọi "bất cứ URL nào nó nghĩ ra" không phải là agent, là lỗ hổng SSRF.
- **Lineage bắt buộc — từ chối, không cảnh báo.** Kết quả thiếu
  `source/provider/asOf/retrievedAt/requestFingerprint` bị loại ngay tại cửa.
  Cảnh báo rồi vẫn dùng nghĩa là con số không nguồn gốc đi tiếp vào decision
  packet, và đến lúc kiểm toán thì không ai truy được nó từ đâu ra.
- **Circuit breaker.** Provider hỏng thì hỏng nhanh và nói thật, thay vì để
  mọi skill treo theo timeout của nó.
- **Kill switch.** `finance_agent_os.mcp.enabled = false` tắt toàn bộ tool
  ngay lập tức mà không cần deploy — và hệ thống phần còn lại vẫn chạy, cùng
  bất biến "AI hỏng không dừng Treasury" đã gác ở chaos test.
"""

import hashlib
import json
import threading
import time
from datetime import datetime

KILL_SWITCH_PARAM = 'finance_agent_os.mcp.enabled'

CONTRACT_FIELDS = (
    'instrument', 'event_type', 'effective_at', 'retrieved_at', 'source',
    'source_tier', 'quality', 'license_profile', 'payload', 'raw_hash',
    'transform_version',
)
QUALITY_STATUSES = ('validated', 'unvalidated', 'rejected')
SOURCE_TIERS = ('T1', 'T2', 'T3', 'T4', 'T5')

# Lệch quá ngưỡng này thì không có "nguồn thắng" (FR-035).
DIVERGENCE_THRESHOLD = 0.005  # 0.5%

# Sau chừng này lỗi liên tiếp thì mở mạch; sau chừng này giây thì thử lại một
# lần (half-open). Số nhỏ và cố định: đây là van an toàn, không phải chỗ tinh
# chỉnh hiệu năng.
BREAKER_THRESHOLD = 3
BREAKER_COOLDOWN_SECONDS = 60.0


class ToolSpec:
    """Một tool đã khai: ai được gọi, đi đâu, chờ bao lâu."""

    __slots__ = ('name', 'transport', 'mode', 'timeout', 'allowed_sources')

    def __init__(self, name, transport, mode='READ', timeout=15.0, allowed_sources=()):
        self.name = name
        self.transport = transport  # callable(env, payload) -> dict envelope
        self.mode = mode
        self.timeout = timeout
        self.allowed_sources = tuple(allowed_sources)


class _BreakerState:
    __slots__ = ('failures', 'opened_at')

    def __init__(self):
        self.failures = 0
        self.opened_at = None


class McpGateway:
    """Registry + policy. Một instance cho một tập tool.

    Breaker state nằm trong bộ nhớ process. ponytail: với workers > 1 mỗi
    worker có breaker riêng nên mạch mở chậm hơn một chút; nâng cấp là dời
    state sang `is.config_parameter` nếu cần breaker toàn cụm. Kill switch
    thì đã toàn cụm sẵn vì đọc từ DB mỗi lần gọi.
    """

    def __init__(self):
        self._tools = {}
        self._breakers = {}
        self._lock = threading.Lock()

    # -- registry ------------------------------------------------------

    def register(self, spec):
        if spec.name in self._tools:
            raise ValueError('MCP tool already registered: %s' % spec.name)
        self._tools[spec.name] = spec
        self._breakers[spec.name] = _BreakerState()

    def tools(self):
        return sorted(self._tools)

    # -- policy pieces -------------------------------------------------

    @staticmethod
    def _enabled(env):
        value = env['ir.config_parameter'].sudo().get_param(KILL_SWITCH_PARAM)
        # Mặc định tắt: một gateway ra ngoài phải được bật có chủ đích.
        return (value or '').strip().lower() == 'true'

    @staticmethod
    def _contract_error(envelope):
        if not isinstance(envelope, dict):
            return 'contract must be an object'
        missing = [field for field in CONTRACT_FIELDS if envelope.get(field) in (None, '')]
        if missing:
            return 'contract missing: %s' % ', '.join(missing)
        quality = envelope.get('quality')
        if not isinstance(quality, dict) or quality.get('status') not in QUALITY_STATUSES:
            return 'quality.status must be one of %s' % ', '.join(QUALITY_STATUSES)
        score = quality.get('score')
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0.0 <= score <= 1.0:
            return 'quality.score must be between 0 and 1'
        raw_hash = envelope.get('raw_hash')
        if not isinstance(raw_hash, str) or not raw_hash.startswith('sha256:') or len(raw_hash) != 71:
            return 'raw_hash must be sha256:<64 lowercase hex>'
        try:
            int(raw_hash[7:], 16)
        except ValueError:
            return 'raw_hash must be sha256:<64 lowercase hex>'
        if raw_hash[7:] != raw_hash[7:].lower():
            return 'raw_hash must be sha256:<64 lowercase hex>'
        if not isinstance(envelope.get('payload'), dict):
            return 'payload must be an object'
        try:
            effective_at = datetime.fromisoformat(envelope['effective_at'].replace('Z', '+00:00'))
            retrieved_at = datetime.fromisoformat(envelope['retrieved_at'].replace('Z', '+00:00'))
        except (AttributeError, TypeError, ValueError):
            return 'effective_at and retrieved_at must be ISO-8601 timestamps'
        if effective_at.tzinfo is None or retrieved_at.tzinfo is None:
            return 'effective_at and retrieved_at must include timezone'
        if effective_at > retrieved_at:
            return 'effective_at must not be after retrieved_at'
        raw_bytes = envelope.get('raw_bytes')
        if raw_bytes is not None and (
                not isinstance(raw_bytes, bytes)
                or hashlib.sha256(raw_bytes).hexdigest() != raw_hash[7:]):
            return 'raw_bytes must match raw_hash'
        return None

    @staticmethod
    def fingerprint(tool_name, payload):
        """Fingerprint tất định của một lần gọi — để replay đối chiếu được."""
        canonical = json.dumps({'tool': tool_name, 'payload': payload or {}},
                               sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()

    # -- the one entry point -------------------------------------------

    def invoke(self, env, tool_name, payload=None, now=None):
        """Gọi một tool. Luôn trả dict có `status`; không bao giờ trả số mồ côi.

        status: ok | disabled | unavailable | rejected
        Chỉ `ok` mang `data`, và khi đó lineage đã được kiểm.
        """
        now = time.monotonic() if now is None else now

        if tool_name not in self._tools:
            return {'status': 'rejected', 'tool': tool_name,
                    'reason': 'tool not in MCP registry'}

        if not self._enabled(env):
            return {'status': 'disabled', 'tool': tool_name,
                    'reason': '%s is not true' % KILL_SWITCH_PARAM}

        spec = self._tools[tool_name]
        breaker = self._breakers[tool_name]
        request_payload = payload or {}
        request_fingerprint = self.fingerprint(tool_name, request_payload)

        with self._lock:
            if breaker.opened_at is not None:
                if now - breaker.opened_at < BREAKER_COOLDOWN_SECONDS:
                    return {'status': 'unavailable', 'tool': tool_name,
                            'reason': 'circuit open after %d consecutive failures' % breaker.failures}
                # half-open: cho đúng một lần gọi thử.
                breaker.opened_at = None

        try:
            envelope = spec.transport(env, request_payload)
        except Exception as exc:
            with self._lock:
                breaker.failures += 1
                if breaker.failures >= BREAKER_THRESHOLD:
                    breaker.opened_at = now
            return {'status': 'unavailable', 'tool': tool_name,
                    'reason': 'transport error: %s' % exc}

        contract_error = self._contract_error(envelope)
        if contract_error:
            return {'status': 'rejected', 'tool': tool_name, 'reason': contract_error}

        requested_instrument = request_payload.get('instrument', request_payload.get('symbol'))
        if requested_instrument is not None and envelope['instrument'] != requested_instrument:
            return {'status': 'rejected', 'tool': tool_name,
                    'reason': 'response instrument does not match request'}
        declared_fingerprint = envelope.get('request_fingerprint')
        if declared_fingerprint is not None and declared_fingerprint != request_fingerprint:
            return {'status': 'rejected', 'tool': tool_name,
                    'reason': 'response request fingerprint does not match request'}

        source = str(envelope['source'])
        if spec.allowed_sources and source not in spec.allowed_sources:
            return {'status': 'rejected', 'tool': tool_name,
                    'reason': 'source %r not allowed for this tool' % source}

        tier = str(envelope['source_tier'])
        if tier not in SOURCE_TIERS:
            # Một tier lạ không được coi là "chắc cũng ổn". Nếu không xếp hạng
            # được nguồn thì cũng không so sánh được nó với nguồn khác, và mọi
            # quyết định ưu tiên phía sau thành đoán mò.
            return {'status': 'rejected', 'tool': tool_name,
                    'reason': 'unknown sourceTier %r, expected one of %s'
                              % (tier, ', '.join(SOURCE_TIERS))}

        with self._lock:
            breaker.failures = 0
            breaker.opened_at = None
        return {'status': 'ok', 'tool': tool_name,
                'lineage': {
                    'source': envelope['source'],
                    'sourceTier': envelope['source_tier'],
                    'instrument': envelope['instrument'],
                    'requestFingerprint': request_fingerprint,
                    'effectiveAt': envelope['effective_at'],
                    'retrievedAt': envelope['retrieved_at'],
                    'rawHash': envelope['raw_hash'],
                    'rawHashStatus': 'verified' if 'raw_bytes' in envelope else 'declared',
                    'licenseProfile': envelope['license_profile'],
                    'transformVersion': envelope['transform_version'],
                },
                'data': envelope['payload']}


def reconcile(results, field, threshold=DIVERGENCE_THRESHOLD):
    """Chọn giá trị giữa nhiều nguồn — và nói thẳng khi chúng không đồng ý.

    Đây là chỗ dễ hỏng nhất trong một hệ nhiều nguồn: lấy đại nguồn đầu tiên,
    hoặc lấy nguồn "tốt nhất", rồi đi tiếp như thể không có gì xảy ra. Hai
    nguồn chênh nhau 8% về giá một mã không phải là chuyện chọn nguồn, đó là
    tín hiệu có gì đó sai — và người ra quyết định phải thấy nó (FR-035).

    Trả về dict có `status`:
      - `ok`        : các nguồn khớp trong ngưỡng; `value` là của tier cao nhất.
      - `divergent` : vượt ngưỡng — **không có** `value`, buộc phải xử lý.
      - `empty`     : không nguồn nào dùng được.
    """
    usable = []
    for result in results:
        if not isinstance(result, dict) or result.get('status') != 'ok':
            continue
        data = result.get('data') or {}
        if field not in data:
            continue
        try:
            value = float(data[field])
        except (TypeError, ValueError):
            continue
        tier = str((result.get('lineage') or {}).get('sourceTier') or '')
        if tier not in SOURCE_TIERS:
            continue
        usable.append({
            'tier': tier,
            'rank': SOURCE_TIERS.index(tier),
            'source': str((result.get('lineage') or {}).get('source') or ''),
            'value': value,
        })

    if not usable:
        return {'status': 'empty', 'field': field, 'sources': []}

    usable.sort(key=lambda item: item['rank'])
    values = [item['value'] for item in usable]
    low, high = min(values), max(values)
    # So sánh tương đối để ngưỡng còn nghĩa với mọi thang giá; nếu mốc bằng 0
    # thì mọi khác biệt đều là vô hạn về tỉ lệ, nên coi là lệch.
    base = max(abs(low), abs(high))
    spread = 0.0 if high == low else (float('inf') if not base else (high - low) / base)

    if spread > threshold:
        return {
            'status': 'divergent', 'field': field, 'spread': spread,
            'threshold': threshold, 'sources': usable,
            'reason': '%s: %d sources disagree by %.4g (threshold %.4g)'
                      % (field, len(usable), spread, threshold),
        }

    winner = usable[0]
    return {'status': 'ok', 'field': field, 'value': winner['value'],
            'source': winner['source'], 'sourceTier': winner['tier'],
            'spread': spread, 'sources': usable}
