# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""E03 — mỗi nhánh policy của gateway có một test, và một falsify chủ đích.

Điều đáng test không phải là "gateway gọi được tool" mà là các đường từ chối:
tool lạ, kill switch, lineage thiếu, source lạ, breaker mở. Đó là những đường
mà nếu hỏng thì không ai thấy — cho tới lúc một con số không nguồn gốc nằm
trong decision packet.
"""

from odoo.tests.common import TransactionCase, tagged

from ..services import mcp_gateway
from ..services.mcp_gateway import McpGateway, ToolSpec, KILL_SWITCH_PARAM


def _good_envelope(env, payload):
    return {
        'instrument': 'HPG',
        'event_type': 'quote',
        'effective_at': '2026-07-20T15:00:00Z',
        'retrieved_at': '2026-08-08T09:00:00Z',
        'source': 'dnse',
        'source_tier': 'T1',
        'quality': {'status': 'validated', 'score': 1.0},
        'license_profile': 'contracted-broker',
        'payload': {'symbol': 'HPG', 'close': 20600},
        'raw_hash': 'sha256:' + 'a' * 64,
        'transform_version': 'quote-v1',
    }


@tagged('post_install', '-at_install', 'finance_agent_os')
class TestMcpGateway(TransactionCase):
    def setUp(self):
        super().setUp()
        self.gw = McpGateway()
        self.gw.register(ToolSpec('quote', _good_envelope, allowed_sources=('dnse',)))
        # Bật kill switch cho các test policy; test kill switch tự tắt lại.
        self.env['ir.config_parameter'].sudo().set_param(KILL_SWITCH_PARAM, 'true')

    def test_ok_path_returns_data_with_verified_lineage(self):
        result = self.gw.invoke(self.env, 'quote', {'symbol': 'HPG'})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['data']['close'], 20600)
        self.assertEqual(result['lineage']['source'], 'dnse')
        self.assertEqual(result['lineage']['instrument'], 'HPG')
        self.assertEqual(result['lineage']['requestFingerprint'],
                         McpGateway.fingerprint('quote', {'symbol': 'HPG'}))
        self.assertEqual(result['lineage']['rawHashStatus'], 'declared')

    def test_unregistered_tool_is_rejected_not_guessed(self):
        result = self.gw.invoke(self.env, 'fetch_any_url')
        self.assertEqual(result['status'], 'rejected')
        self.assertIn('registry', result['reason'])

    def test_kill_switch_disables_every_tool_without_deploy(self):
        self.env['ir.config_parameter'].sudo().set_param(KILL_SWITCH_PARAM, 'false')
        result = self.gw.invoke(self.env, 'quote')
        self.assertEqual(result['status'], 'disabled')
        self.assertIn(KILL_SWITCH_PARAM, result['reason'])

    def test_kill_switch_default_is_off(self):
        """Gateway ra ngoài phải được bật có chủ đích, không phải bật sẵn."""
        self.env['ir.config_parameter'].sudo().set_param(KILL_SWITCH_PARAM, '')
        self.assertEqual(self.gw.invoke(self.env, 'quote')['status'], 'disabled')

    def test_missing_contract_field_is_refused_not_warned(self):
        for dropped in mcp_gateway.CONTRACT_FIELDS:
            def transport(env, payload, _dropped=dropped):
                envelope = _good_envelope(env, payload)
                del envelope[_dropped]
                return envelope
            gw = McpGateway()
            gw.register(ToolSpec('quote', transport))
            result = gw.invoke(self.env, 'quote')
            self.assertEqual(result['status'], 'rejected', 'thiếu %s mà vẫn qua' % dropped)
            self.assertIn(dropped, result['reason'])

    def test_response_lineage_must_match_request_and_valid_time(self):
        variants = (
            ('instrument', 'FPT'),
            ('request_fingerprint', 'wrong'),
            ('effective_at', '2026-08-09T00:00:00Z'),
            ('retrieved_at', '2026-08-08T00:00:00'),
        )
        for field, value in variants:
            def transport(env, payload, _field=field, _value=value):
                envelope = _good_envelope(env, payload)
                envelope[_field] = _value
                return envelope
            gw = McpGateway()
            gw.register(ToolSpec('quote', transport))
            self.assertEqual(gw.invoke(self.env, 'quote', {'symbol': 'HPG'})['status'], 'rejected')

    def test_raw_hash_is_verified_only_with_matching_canonical_bytes(self):
        raw = b'{"close":20600,"symbol":"HPG"}'

        def transport(env, payload):
            envelope = _good_envelope(env, payload)
            envelope['raw_bytes'] = raw
            envelope['raw_hash'] = 'sha256:' + mcp_gateway.hashlib.sha256(raw).hexdigest()
            return envelope

        gw = McpGateway()
        gw.register(ToolSpec('quote', transport))
        result = gw.invoke(self.env, 'quote', {'symbol': 'HPG'})
        self.assertEqual(result['lineage']['rawHashStatus'], 'verified')

    def test_lineage_rejection_does_not_trip_the_breaker(self):
        """Provider nói dối nguồn gốc là lỗi dữ liệu; mở mạch sẽ che tín hiệu."""
        gw = McpGateway()
        gw.register(ToolSpec('quote', lambda env, p: {'data': {}}))
        for _ in range(mcp_gateway.BREAKER_THRESHOLD + 2):
            self.assertEqual(gw.invoke(self.env, 'quote')['status'], 'rejected')

    def test_disallowed_source_is_rejected(self):
        def transport(env, payload):
            envelope = _good_envelope(env, payload)
            envelope['source'] = 'random_blog'
            return envelope
        gw = McpGateway()
        gw.register(ToolSpec('quote', transport, allowed_sources=('dnse',)))
        result = gw.invoke(self.env, 'quote')
        self.assertEqual(result['status'], 'rejected')
        self.assertIn('random_blog', result['reason'])

    def test_breaker_opens_after_consecutive_failures_and_half_opens(self):
        calls = {'n': 0}

        def flaky(env, payload):
            calls['n'] += 1
            raise RuntimeError('provider down')

        gw = McpGateway()
        gw.register(ToolSpec('quote', flaky))
        t0 = 1000.0
        for i in range(mcp_gateway.BREAKER_THRESHOLD):
            result = gw.invoke(self.env, 'quote', now=t0 + i)
            self.assertEqual(result['status'], 'unavailable')
            self.assertIn('transport error', result['reason'])
        transports = calls['n']
        # Mạch mở: gọi tiếp không chạm transport nữa.
        result = gw.invoke(self.env, 'quote', now=t0 + 10)
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('circuit open', result['reason'])
        self.assertEqual(calls['n'], transports)
        # Hết cooldown: half-open cho đúng một lần thử.
        result = gw.invoke(self.env, 'quote', now=t0 + mcp_gateway.BREAKER_COOLDOWN_SECONDS + 11)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(calls['n'], transports + 1)

    def test_breaker_recovers_after_one_good_call(self):
        state = {'fail': True}

        def sometimes(env, payload):
            if state['fail']:
                raise RuntimeError('down')
            return _good_envelope(env, payload)

        gw = McpGateway()
        gw.register(ToolSpec('quote', sometimes))
        t0 = 2000.0
        for i in range(mcp_gateway.BREAKER_THRESHOLD):
            gw.invoke(self.env, 'quote', now=t0 + i)
        state['fail'] = False
        # Cooldown tính từ lúc mạch mở (lần fail cuối), không phải lần đầu.
        opened = t0 + mcp_gateway.BREAKER_THRESHOLD - 1
        result = gw.invoke(self.env, 'quote', now=opened + mcp_gateway.BREAKER_COOLDOWN_SECONDS + 1)
        self.assertEqual(result['status'], 'ok')
        # Mạch đóng lại hẳn, không còn di chứng.
        self.assertEqual(gw.invoke(self.env, 'quote', now=opened + mcp_gateway.BREAKER_COOLDOWN_SECONDS + 2)['status'], 'ok')

    def test_duplicate_registration_is_a_programming_error(self):
        with self.assertRaises(ValueError):
            self.gw.register(ToolSpec('quote', _good_envelope))

    def test_unknown_source_tier_is_rejected(self):
        """FR-033: nguồn không xếp hạng được thì không so sánh được với nguồn khác."""
        for bad_tier in ('', 'T0', 'official', 'unknown'):
            def transport(env, payload, _tier=bad_tier):
                envelope = _good_envelope(env, payload)
                envelope['source_tier'] = _tier
                return envelope
            gw = McpGateway()
            gw.register(ToolSpec('quote', transport))
            result = gw.invoke(self.env, 'quote')
            self.assertEqual(result['status'], 'rejected', 'tier %r mà vẫn qua' % bad_tier)

    def test_every_declared_tier_is_accepted(self):
        for tier in mcp_gateway.SOURCE_TIERS:
            def transport(env, payload, _tier=tier):
                envelope = _good_envelope(env, payload)
                envelope['source_tier'] = _tier
                return envelope
            gw = McpGateway()
            gw.register(ToolSpec('quote', transport))
            self.assertEqual(gw.invoke(self.env, 'quote')['status'], 'ok', tier)

    # -- FR-034/FR-035: nhiều nguồn --------------------------------------

    def _result(self, tier, value, source=None):
        return {'status': 'ok', 'tool': 'quote',
                'lineage': {'source': source or tier.lower(), 'sourceTier': tier},
                'data': {'close': value}}

    def test_reconcile_prefers_the_stronger_tier_when_sources_agree(self):
        out = mcp_gateway.reconcile(
            [self._result('T2', 20600.0), self._result('T1', 20610.0)],
            'close')
        self.assertEqual(out['status'], 'ok')
        self.assertEqual(out['sourceTier'], 'T1')
        self.assertEqual(out['value'], 20610.0)

    def test_reconcile_refuses_to_pick_a_winner_when_sources_diverge(self):
        """Lệch lớn không phải chuyện chọn nguồn — nó là tín hiệu phải nổi lên."""
        out = mcp_gateway.reconcile(
            [self._result('T1', 20600.0), self._result('T1', 22300.0)],
            'close')
        self.assertEqual(out['status'], 'divergent')
        self.assertNotIn('value', out, 'divergent mà vẫn trả value là im lặng chọn hộ')
        self.assertIn('disagree', out['reason'])
        self.assertEqual(len(out['sources']), 2)

    def test_reconcile_threshold_is_relative_not_absolute(self):
        """Cùng một khoảng lệch tuyệt đối: nhỏ với giá lớn, lớn với giá nhỏ."""
        agree = mcp_gateway.reconcile(
            [self._result('T1', 100000.0), self._result('T1', 100100.0)], 'close')
        self.assertEqual(agree['status'], 'ok')
        disagree = mcp_gateway.reconcile(
            [self._result('T1', 100.0), self._result('T1', 200.0)], 'close')
        self.assertEqual(disagree['status'], 'divergent')

    def test_reconcile_ignores_unusable_results_and_reports_empty(self):
        unusable = [
            {'status': 'unavailable', 'tool': 'quote'},
            {'status': 'ok', 'lineage': {'sourceTier': 'T1'}, 'data': {}},
            {'status': 'ok', 'lineage': {'sourceTier': 'MADE_UP'}, 'data': {'close': 1.0}},
            {'status': 'ok', 'lineage': {'sourceTier': 'T1'}, 'data': {'close': 'n/a'}},
        ]
        out = mcp_gateway.reconcile(unusable, 'close')
        self.assertEqual(out['status'], 'empty')
        # Một nguồn dùng được lẫn trong đám hỏng vẫn phải dùng được.
        out = mcp_gateway.reconcile(unusable + [self._result('T1', 5.0)], 'close')
        self.assertEqual(out['status'], 'ok')
        self.assertEqual(out['value'], 5.0)

    def test_reconcile_treats_zero_baseline_as_divergent(self):
        out = mcp_gateway.reconcile(
            [self._result('T1', 0.0), self._result('T1', 0.0)], 'close')
        self.assertEqual(out['status'], 'ok', 'bằng nhau thì không lệch, kể cả ở 0')
        out = mcp_gateway.reconcile(
            [self._result('T1', 0.0), self._result('T1', 1.0)], 'close')
        self.assertEqual(out['status'], 'divergent')

    def test_fingerprint_is_deterministic_and_payload_sensitive(self):
        a = McpGateway.fingerprint('quote', {'symbol': 'HPG', 'range': '1D'})
        b = McpGateway.fingerprint('quote', {'range': '1D', 'symbol': 'HPG'})
        c = McpGateway.fingerprint('quote', {'symbol': 'FPT', 'range': '1D'})
        self.assertEqual(a, b, 'thứ tự key không được đổi fingerprint')
        self.assertNotEqual(a, c)
