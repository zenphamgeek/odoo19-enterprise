# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Deterministic HTTP transport for a governed local MCP sidecar."""

import json
from urllib import request

AUTH_PLACEHOLDER = '<PROVIDER_TOKEN>'


class HttpConnector:
    """Small stdlib adapter; policy, lineage validation, and breaker stay in McpGateway."""

    def __init__(self, base_url, endpoint, timeout=15.0, auth_token=AUTH_PLACEHOLDER):
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint
        self.timeout = timeout
        self.auth_token = auth_token

    def _open(self, req):
        try:
            return request.urlopen(req, timeout=self.timeout)
        except Exception as exc:
            message = str(exc)
            if self.auth_token:
                message = message.replace(self.auth_token, '<redacted>')
            raise RuntimeError(message) from None

    def health(self):
        req = request.Request('%s/healthz' % self.base_url, method='GET')
        with self._open(req) as response:
            if response.status != 200:
                raise RuntimeError('sidecar health returned HTTP %s' % response.status)
            try:
                payload = json.loads(response.read().decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise RuntimeError('sidecar health returned malformed JSON') from None
        return payload

    def __call__(self, env, payload):
        body = json.dumps(payload or {}, sort_keys=True, separators=(',', ':')).encode('utf-8')
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = 'Bearer %s' % self.auth_token
        req = request.Request('%s/%s' % (self.base_url, self.endpoint.lstrip('/')),
                              data=body, headers=headers, method='POST')
        with self._open(req) as response:
            if response.status != 200:
                raise RuntimeError('sidecar returned HTTP %s' % response.status)
            try:
                envelope = json.loads(response.read().decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise RuntimeError('sidecar returned malformed JSON') from None
        if not isinstance(envelope, dict):
            raise RuntimeError('sidecar response must be an object')
        return envelope
