# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from ..services import mcp_gateway
from ..services.http_connector import AUTH_PLACEHOLDER, HttpConnector
from ..services.mcp_gateway import KILL_SWITCH_PARAM, McpGateway, ToolSpec


class _Sidecar(BaseHTTPRequestHandler):
    calls = 0
    mode = 'ok'
    auth = None

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path != '/healthz':
            self.send_error(404)
            return
        self._send({'status': 'ok'})

    def do_POST(self):
        type(self).calls += 1
        type(self).auth = self.headers.get('Authorization')
        raw_request = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        if type(self).mode == 'timeout':
            time.sleep(0.15)
            return
        if type(self).mode == 'malformed':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{broken')
            return
        payload = json.loads(raw_request)
        raw_response = json.dumps({'close': 20600, 'symbol': payload['symbol']},
                                  sort_keys=True, separators=(',', ':')).encode()
        self._send({
            'instrument': payload['symbol'],
            'event_type': 'quote',
            'effective_at': '2026-08-14T01:00:00Z',
            'retrieved_at': '2026-08-14T01:00:01Z',
            'source': 'local-fake-sidecar',
            'source_tier': 'T2',
            'quality': {'status': 'validated', 'score': 1.0},
            'license_profile': 'local-test-only',
            'payload': json.loads(raw_response),
            'raw_hash': 'sha256:' + hashlib.sha256(raw_response).hexdigest(),
            'transform_version': 'local-quote-v1',
            'request_fingerprint': McpGateway.fingerprint('quote', payload),
        })

    def _send(self, payload):
        body = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@tagged('post_install', '-at_install', 'finance_agent_os')
class TestHttpConnector(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), _Sidecar)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = 'http://127.0.0.1:%d' % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        _Sidecar.calls = 0
        _Sidecar.mode = 'ok'
        _Sidecar.auth = None
        self.env['ir.config_parameter'].sudo().set_param(KILL_SWITCH_PARAM, 'true')
        self.connector = HttpConnector(self.base_url, '/quote', timeout=0.05)
        self.gateway = McpGateway()
        self.gateway.register(ToolSpec(
            'quote', self.connector, timeout=0.05,
            allowed_sources=('local-fake-sidecar',),
        ))

    def test_health_and_live_http_lineage(self):
        self.assertEqual(self.connector.health(), {'status': 'ok'})
        payload = {'symbol': 'HPG', 'range': '1D'}
        result = self.gateway.invoke(self.env, 'quote', payload)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['data'], {'close': 20600, 'symbol': 'HPG'})
        self.assertEqual(result['lineage']['sourceTier'], 'T2')
        self.assertEqual(result['lineage']['requestFingerprint'],
                         McpGateway.fingerprint('quote', payload))
        self.assertEqual(_Sidecar.auth, 'Bearer ' + AUTH_PLACEHOLDER)

    def test_timeout_and_malformed_response_are_honest(self):
        _Sidecar.mode = 'timeout'
        result = self.gateway.invoke(self.env, 'quote', {'symbol': 'HPG'})
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('timed out', result['reason'])
        _Sidecar.mode = 'malformed'
        result = self.gateway.invoke(self.env, 'quote', {'symbol': 'HPG'})
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('malformed JSON', result['reason'])

    def test_kill_switch_prevents_http_transport(self):
        self.env['ir.config_parameter'].sudo().set_param(KILL_SWITCH_PARAM, 'false')
        self.assertEqual(self.gateway.invoke(self.env, 'quote', {'symbol': 'HPG'})['status'],
                         'disabled')
        self.assertEqual(_Sidecar.calls, 0)

    def test_live_transport_breaker_and_recovery(self):
        _Sidecar.mode = 'malformed'
        for i in range(mcp_gateway.BREAKER_THRESHOLD):
            self.assertEqual(self.gateway.invoke(self.env, 'quote', {'symbol': 'HPG'}, now=10 + i)['status'],
                             'unavailable')
        calls = _Sidecar.calls
        self.assertIn('circuit open', self.gateway.invoke(
            self.env, 'quote', {'symbol': 'HPG'}, now=20)['reason'])
        self.assertEqual(_Sidecar.calls, calls)
        _Sidecar.mode = 'ok'
        result = self.gateway.invoke(
            self.env, 'quote', {'symbol': 'HPG'},
            now=12 + mcp_gateway.BREAKER_COOLDOWN_SECONDS + 1)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(self.gateway.invoke(
            self.env, 'quote', {'symbol': 'HPG'},
            now=12 + mcp_gateway.BREAKER_COOLDOWN_SECONDS + 2)['status'], 'ok')

    def test_auth_secret_is_redacted_from_transport_error(self):
        connector = HttpConnector(self.base_url, '/quote', auth_token='real-secret')
        with patch('urllib.request.urlopen', side_effect=RuntimeError('bad real-secret')):
            with self.assertRaisesRegex(RuntimeError, 'bad <redacted>'):
                connector(None, {'symbol': 'HPG'})
