# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
import logging
import urllib.parse
import urllib.request
import urllib.error

_logger = logging.getLogger(__name__)


class HermesHSClient:
    """
    Client for communicating with the Hermes HS Knowledge Engine FastAPI Service.
    """

    def __init__(self, env):
        self.env = env
        self.base_url = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('insilos_hs_sync.hermes_api_url', 'http://127.0.0.1:8000')
            .rstrip('/')
        )
        self.timeout = 10

    def _log_event(self, event_type, status, summary, raw_payload, error_msg=None):
        try:
            self.env['is.hs.sync.log'].sudo().create({
                'event_type': event_type,
                'direction': 'outbound_api',
                'status': status,
                'payload_summary': summary,
                'raw_payload': raw_payload,
                'error_message': error_msg,
                'remote_ip': self.base_url,
            })
        except Exception as e:
            _logger.warning("Failed to record audit log in is.hs.sync.log: %s", e)

    def _send_request(self, endpoint, method='GET', params=None, json_body=None):
        url = f"{self.base_url}{endpoint}"
        if params:
            query_str = urllib.parse.urlencode(params)
            url = f"{url}?{query_str}"

        headers = {
            'User-Agent': 'Insilos-HS-Sync/19.0',
            'Accept': 'application/json',
        }
        data = None
        if json_body is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(json_body).encode('utf-8')

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        raw_request_info = f"{method} {url} | Body: {json_body}"

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.getcode()
                resp_bytes = resp.read()
                resp_text = resp_bytes.decode('utf-8')
                result = json.loads(resp_text)
                self._log_event(
                    event_type=f"hermes_api_{endpoint.replace('/', '_').strip('_')}",
                    status='success',
                    summary=f"HTTP {status_code} from {endpoint}",
                    raw_payload=f"Request: {raw_request_info}\nResponse: {resp_text[:1000]}"
                )
                return {'status': 'success', 'data': result, 'code': status_code}
        except urllib.error.HTTPError as he:
            err_body = he.read().decode('utf-8', errors='ignore')
            _logger.error("Hermes HS API HTTP error: %s - %s", he.code, err_body)
            self._log_event(
                event_type=f"hermes_api_{endpoint.replace('/', '_').strip('_')}",
                status='error',
                summary=f"HTTP {he.code} error from {endpoint}",
                raw_payload=raw_request_info,
                error_msg=f"{he.reason} - {err_body}"
            )
            return {'status': 'error', 'message': f"HTTP {he.code}: {he.reason}", 'code': he.code, 'error_body': err_body}
        except urllib.error.URLError as ue:
            _logger.error("Hermes HS API connection error: %s", ue.reason)
            self._log_event(
                event_type=f"hermes_api_{endpoint.replace('/', '_').strip('_')}",
                status='error',
                summary=f"Connection failure to {endpoint}",
                raw_payload=raw_request_info,
                error_msg=str(ue.reason)
            )
            return {'status': 'error', 'message': f"Connection failure: {ue.reason}"}
        except Exception as e:
            _logger.exception("Hermes HS API unexpected error")
            self._log_event(
                event_type=f"hermes_api_{endpoint.replace('/', '_').strip('_')}",
                status='error',
                summary=f"Exception during {endpoint}",
                raw_payload=raw_request_info,
                error_msg=str(e)
            )
            return {'status': 'error', 'message': str(e)}

    def search_hs_codes(self, query, limit=10):
        """Search HS Codes by text query or partial HS Code."""
        return self._send_request('/v1/hs/search', method='GET', params={'q': query, 'limit': limit})

    def classify_product(self, title, description=None, technical_specs=None):
        """Classify a product description into suggested HS Codes."""
        body = {
            'title': title,
            'description': description or '',
            'technical_specs': technical_specs or '',
        }
        return self._send_request('/v1/hs/classify', method='POST', json_body=body)

    def search_rulings(self, keyword=None, hs_code=None, limit=10):
        """Search advance classification rulings."""
        params = {'limit': limit}
        if keyword:
            params['q'] = keyword
        if hs_code:
            params['hs_code'] = hs_code
        return self._send_request('/v1/rulings/search', method='GET', params=params)

    def get_tariff_info(self, hs_code):
        """Fetch duty rates and regulatory notes for a specific 8-digit HS Code."""
        return self._send_request(f'/v1/tariff/schedule', method='GET', params={'hs_code': hs_code})
