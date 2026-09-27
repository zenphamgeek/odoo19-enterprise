# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
import logging
import urllib.parse
import urllib.request
from odoo import _

_logger = logging.getLogger(__name__)


class HSEKnowledgeClient:
    """Client for communicating with Deterministic HSE Knowledge Platform API."""

    def __init__(self, env):
        self.env = env
        params = env['ir.config_parameter'].sudo()
        self.endpoint = (params.get_param('insilos_hse_compliance.hse_knowledge_endpoint') or 'https://hse.insilos.com').rstrip('/')
        self.api_key = params.get_param('insilos_hse_compliance.hse_api_key') or ''

    def _headers(self):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Insilos-HSE-Client/19.0',
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def _request(self, path, method='GET', payload=None, timeout=10):
        url = f"{self.endpoint}{path}"
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode('utf-8')
                return json.loads(body) if body else {}
        except Exception as exc:
            _logger.warning(f"HSE Knowledge API request error ({method} {path}): {exc}")
            return {'status': 'error', 'message': str(exc)}

    def get_substance_by_cas(self, cas_number):
        """Query substance master and GHS data by CAS number."""
        query = urllib.parse.quote(cas_number.strip())
        return self._request(f"/api/v1/chemicals/{query}")

    def get_oels_by_substance(self, query):
        """Query occupational exposure limits (BYT, MONRE, ACGIH, NIOSH)."""
        encoded = urllib.parse.quote(query.strip())
        return self._request(f"/api/v1/oels?substance={encoded}")

    def trigger_on_demand_crawl(self, topic, scope='vietnam-core', callback_url=None):
        """Request real-time on-demand crawling of legal/technical regulation or chemical data."""
        payload = {
            'topic': topic,
            'scope': scope,
        }
        if callback_url:
            payload['callback_url'] = callback_url
        return self._request("/api/v1/on-demand", method='POST', payload=payload, timeout=20)

    def evaluate_facility_applicability(self, facility_profile):
        """Evaluate legal register and compliance obligations for an industrial facility profile."""
        return self._request("/api/v1/applicability/evaluate", method='POST', payload=facility_profile, timeout=15)

    def search_regulations(self, query, as_of=None):
        """Search legal provisions and QCVN standards temporally."""
        params = {'q': query}
        if as_of:
            params['as_of'] = str(as_of)
        encoded = urllib.parse.urlencode(params)
        return self._request(f"/api/v1/search?{encoded}")
