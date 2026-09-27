# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
import logging
from odoo import http
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class OpenRouterProxyController(http.Controller):

    @route('/api/openrouter/v1/chat/completions', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def openrouter_chat_completions(self, **kwargs):
        """OpenAI-compatible chat completions proxy endpoint. Requires authentication."""
        params = request.dispatcher.jsonrequest
        domain_code = params.get('domain') or 'vision_ocr'
        messages = params.get('messages') or []
        temperature = params.get('temperature')
        response_format = params.get('response_format')
        operation_id = params.get('operation_id')

        if not messages:
            return {'error': 'Missing messages array in request body', 'code': 400}
        if not operation_id:
            return {'error': 'Missing operation_id in request body', 'code': 400}

        try:
            result = request.env['openrouter.router'].sudo().complete(
                domain_code=domain_code,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                operation_id=operation_id,
                parent_operation_id=params.get('parent_operation_id'),
                policy_metadata=params.get('policy_metadata'),
                budget_metadata=params.get('budget_metadata'),
            )
            return result
        except Exception as e:
            _logger.exception("OpenRouter Proxy Error")
            return {'error': str(e), 'code': 500}

    @route('/api/openrouter/v1/models', type='http', auth='public', methods=['GET'], csrf=False)
    def openrouter_list_models(self, **kwargs):
        """Return list of active discovered models in OpenAI format."""
        models = request.env['openrouter.model'].sudo().search([('active', '=', True)])
        data = [{
            'id': m.model_id,
            'object': 'model',
            'owned_by': 'openrouter',
            'is_free': m.is_free,
            'context_length': m.context_length,
            'supports_vision': m.supports_vision,
        } for m in models]
        return request.make_json_response({'object': 'list', 'data': data})
