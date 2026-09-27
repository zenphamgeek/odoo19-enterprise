# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import json
import logging
import re
import time
import requests

from odoo import SUPERUSER_ID, api, models, _
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import UserError
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


class OpenRouterServiceRouter(models.AbstractModel):
    _name = 'openrouter.router'
    _description = 'Insilos IAP Smart AI Router & Fallback Engine'

    @staticmethod
    def _canonical_operation_id(operation_id, effective_index, requested_index=None):
        suffix = re.search(r':model:(\d+)$', operation_id)
        if suffix:
            if requested_index is not None and int(suffix.group(1)) != requested_index:
                error = UserError(_("Operation model suffix does not match the requested model index."))
                error.nonretryable = True
                raise error
            return operation_id
        return f'{operation_id}:model:{effective_index}'

    @api.model
    def _create_durable_log(self, vals):
        vals = {**vals, 'user_id': vals.get('user_id') or self.env.uid}
        try:
            with Registry(self.env.cr.dbname).cursor() as cr:
                cr.execute("SET LOCAL lock_timeout = '2s'")
                env = api.Environment(cr, SUPERUSER_ID, {
                    'allowed_company_ids': [vals['company_id']],
                    'company_id': vals['company_id'],
                })
                if not env['openrouter.log'].search_count([('operation_id', '=', vals['operation_id'])]):
                    env['openrouter.log'].create(vals)
                cr.commit()
        except Exception:
            operation_hash = hashlib.sha256(str(vals.get('operation_id', '')).encode()).hexdigest()[:12]
            _logger.warning("OpenRouter audit persistence failed category=database operation_hash=%s", operation_hash)

    @staticmethod
    def _validate_response(body):
        choices = body.get('choices') if isinstance(body, dict) else None
        choice = choices[0] if isinstance(choices, list) and choices else None
        message = choice.get('message') if isinstance(choice, dict) else None
        content = message.get('content') if isinstance(message, dict) else None
        error = body.get('error') if isinstance(body, dict) else None
        shape = {
            'top_level': {key: ('array' if isinstance(value, list) else 'null' if value is None else type(value).__name__) for key, value in body.items()} if isinstance(body, dict) else {'body': type(body).__name__},
            'error_code': str(error.get('code', 'provider_error')) if isinstance(error, dict) else ('provider_error' if error else None),
            'error_type': str(error.get('type', 'error')) if isinstance(error, dict) else (type(error).__name__ if error else None),
            'choices_count': len(choices) if isinstance(choices, list) else None,
            'finish_reason': choice.get('finish_reason') if isinstance(choice, dict) else None,
            'refusal': bool(message.get('refusal')) if isinstance(message, dict) else False,
            'content_type': 'array' if isinstance(content, list) else 'null' if content is None else type(content).__name__,
        }
        if error:
            return False, 'Provider error envelope', shape
        if not isinstance(choices, list) or not choices:
            return False, 'Provider response has no choices', shape
        if not isinstance(message, dict) or message.get('refusal') or content is None or content == '' or content == []:
            return False, 'Provider refusal or empty content', shape
        if choice.get('finish_reason') == 'error':
            return False, 'Provider reported an unsuccessful completion', shape
        return True, None, shape

    @api.model
    def complete(self, domain_code, messages, temperature=None, response_format=None, **kwargs):
        operation_id = kwargs.get('operation_id')
        policy_metadata = kwargs.get('policy_metadata')
        budget_metadata = kwargs.get('budget_metadata')
        tenant_id = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        company_id = self.env.company.id
        if not operation_id or not tenant_id or not company_id:
            raise UserError(_('Operation, canonical tenant, and company attribution are required.'))
        if not isinstance(policy_metadata, dict) or not policy_metadata.get('version'):
            raise UserError(_('AI policy metadata with version is required.'))
        if not isinstance(budget_metadata, dict) or 'credit_budget' not in budget_metadata:
            raise UserError(_('AI budget metadata with credit_budget is required.'))
        try:
            credit_budget = float(budget_metadata['credit_budget'])
        except (TypeError, ValueError) as exc:
            raise UserError(_('AI credit budget must be numeric and greater than zero.')) from exc
        if credit_budget <= 0:
            raise UserError(_('AI credit budget must be numeric and greater than zero.'))
        budget_metadata = {**budget_metadata, 'credit_budget': credit_budget}

        domain = self.env['openrouter.domain'].search([('code', '=', domain_code), ('active', '=', True)], limit=1)
        if not domain:
            _logger.warning("Domain '%s' not found or inactive, using default primary model", domain_code)
            models_to_try = [self.env['openrouter.model'].search([('is_free', '=', True)], limit=1)]
        else:
            models_to_try = [domain.primary_model_id] + list(domain.fallback_model_ids)
        unique_models = {}
        for model in models_to_try:
            if model:
                unique_models.setdefault(model.model_id, model)
        models_to_try = list(unique_models.values())[:3]
        if not models_to_try:
            models_to_try = list(self.env['openrouter.model'].search([('is_free', '=', True), ('active', '=', True)], limit=3))
        if not models_to_try:
            raise UserError(_("No AI models configured for domain '%s'. Please sync Insilos IAP models.", domain_code))
        model_index = kwargs.get('model_index')
        if model_index is not None:
            if not isinstance(model_index, int) or model_index < 0 or model_index >= len(models_to_try):
                raise UserError(_("AI model index is outside the configured fallback chain."))
            models_to_try = [models_to_try[model_index]]

        iap_endpoint = self.env['ir.config_parameter'].sudo().get_param('ai.iap_endpoint', '')
        account = self.env['iap.account'].sudo().get('ai_llm') if iap_endpoint else None
        account_token = account.sudo().account_token if account else None
        use_iap = bool(iap_endpoint and account_token)
        api_key = None
        if domain_code == 'logistics_ocr' and not use_iap:
            raise UserError(_("Logistics OCR requires Insilos IAP quota routing. Configure ai.iap_endpoint and the ai_llm account."))
        if not use_iap:
            _logger.warning("No IAP endpoint configured, using direct API key (dev mode)")
            # Router là service boundary: caller được phép chạy business OCR nhưng
            # không được đọc model chứa secret. Lookup nội bộ; plaintext key vẫn
            # chỉ tồn tại trong process và không trả về caller/log.
            api_key = self.env['openrouter.key'].sudo().get_default_key()
            if not api_key:
                raise UserError(_("No AI API key configured. Please configure an API key in the Insilos IAP settings."))

        audit = {
            'operation_id': operation_id,
            'tenant_id': tenant_id,
            'company_id': company_id,
            'policy_version': policy_metadata['version'],
            'credit_budget': budget_metadata['credit_budget'],
        }
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://insilos.com',
            'X-Title': 'Insilos Smart AI Router',
        }
        if domain and domain.system_prompt and not any(message.get('role') == 'system' for message in messages):
            messages = [{'role': 'system', 'content': domain.system_prompt}] + list(messages)
        temp = temperature if temperature is not None else (domain.max_temperature if domain else 0.2)
        start_time = time.time()
        last_error = None
        stopped_nonretryable = False
        attempt_operation_id = operation_id

        for idx, model_rec in enumerate(models_to_try):
            effective_index = model_index if model_index is not None else idx
            attempt_operation_id = self._canonical_operation_id(operation_id, effective_index, model_index)
            payload = {'model': model_rec.model_id, 'messages': messages, 'temperature': temp}
            if kwargs.get('max_tokens') is not None:
                payload['max_tokens'] = kwargs['max_tokens']
            if response_format:
                payload['response_format'] = response_format
            call_timeout = kwargs.get('timeout', 120 if domain_code == 'logistics_ocr' else 60)
            try:
                if use_iap:
                    iap_params = {
                        'provider': 'openrouter', 'account_token': account_token,
                        'operation_id': attempt_operation_id, 'parent_operation_id': attempt_operation_id,
                        'tenant_id': tenant_id, 'company_id': company_id,
                        'policy_metadata': policy_metadata, 'budget_metadata': budget_metadata,
                        'http_method': 'POST', 'base_url': 'https://openrouter.ai/api',
                        'api_endpoint': '/v1/chat/completions', 'headers': {**headers, 'Authorization': 'Bearer IAP_ROUTED'},
                        'body': payload, 'timeout': call_timeout,
                    }
                    resp_json = iap_tools.iap_jsonrpc(iap_endpoint, params=iap_params, timeout=call_timeout)
                else:
                    response = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload, timeout=call_timeout)
                    if response.status_code != 200:
                        last_error = f"HTTP {response.status_code}"
                        continue
                    resp_json = response.json()

                valid, semantic_error, response_shape = self._validate_response(resp_json)
                if not valid:
                    last_error = f'{semantic_error}; response_shape={json.dumps(response_shape, sort_keys=True)}'
                    _logger.warning("Model '%s' semantic failure: %s", model_rec.model_id, last_error)
                    continue

                usage = resp_json.get('usage', {})
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                self._create_durable_log({
                    **audit,
                    'operation_id': attempt_operation_id,
                    'domain_id': domain.id if domain else False,
                    'model_id': model_rec.id,
                    'used_model_name': model_rec.model_id,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': usage.get('total_tokens', 0),
                    'total_cost': ((prompt_tokens / 1000000.0) * model_rec.prompt_price) + ((completion_tokens / 1000000.0) * model_rec.completion_price),
                    'status': 'success' if idx == 0 else 'fallback',
                    'execution_time': time.time() - start_time,
                })
                return resp_json
            except Exception as error:
                last_error = str(error)
                non_retryable = (isinstance(error, iap_tools.IAPServerError)
                                 and (getattr(error, 'code', None) in (-32009, -32011)
                                      or getattr(error, 'data', {}).get('retryable') is False))
                _logger.warning("Exception on model '%s': %s%s", model_rec.model_id, last_error,
                                ', stopping fallback' if non_retryable else ', trying fallback...')
                if non_retryable:
                    stopped_nonretryable = True
                    break

        self._create_durable_log({
            **audit,
            'operation_id': attempt_operation_id,
            'domain_id': domain.id if domain else False,
            'model_id': models_to_try[0].id if models_to_try else False,
            'used_model_name': 'all_failed',
            'status': 'failed',
            'execution_time': time.time() - start_time,
            'error_message': last_error or 'All models in fallback chain failed.',
        })
        error = UserError(_("Insilos IAP AI completion failed for domain '%s'. All fallback models failed. Error: %s", domain_code, last_error))
        error.nonretryable = stopped_nonretryable
        raise error
