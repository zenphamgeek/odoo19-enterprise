# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging
import os
from urllib.parse import urlsplit

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OpenRouterModel(models.Model):
    _name = 'openrouter.model'
    _description = 'Insilos IAP AI Model'
    _order = 'is_free desc, name asc'

    name = fields.Char(string='Model Name', required=True)
    model_id = fields.Char(string='Model Identifier', required=True, index=True)
    _model_id_unique = models.Constraint(
        'UNIQUE(model_id)',
        'The AI model identifier must be unique.',
    )
    is_free = fields.Boolean(string='Free Model', index=True, default=False)

    context_length = fields.Integer(string='Context Window (Tokens)', default=0)
    prompt_price = fields.Float(string='Prompt Price ($/1M Tokens)', digits=(12, 6))
    completion_price = fields.Float(string='Completion Price ($/1M Tokens)', digits=(12, 6))

    supports_vision = fields.Boolean(string='Supports Vision', default=False)
    supports_json = fields.Boolean(string='Supports JSON Output', default=False)
    supports_strict_json_schema = fields.Boolean(string='Supports Strict JSON Schema', default=False)
    supports_pdf_input = fields.Boolean(string='Supports PDF Input', default=False)
    capability_evidence_source = fields.Char(string='Capability Evidence Source')
    extraction_max_tokens = fields.Integer(string='Extraction Max Tokens', default=4096)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    @staticmethod
    def _iap_catalog_url(iap_endpoint, environ=os.environ):
        try:
            configured = urlsplit(iap_endpoint.strip())
            trusted = urlsplit('http://127.0.0.1:3099/jsonrpc') if environ.get('INSILOS_LOCAL_DEV') == 'true' else urlsplit(environ['INSILOS_TRUSTED_IAP_URL'].strip())
            allowed_paths = ('', '/', '/jsonrpc')
            if (not trusted.hostname or trusted.query or trusted.fragment or trusted.username or trusted.password
                    or trusted.path not in allowed_paths
                    or (environ.get('INSILOS_LOCAL_DEV') != 'true' and trusted.scheme != 'https')
                    or configured.query or configured.fragment or configured.username or configured.password
                    or configured.path not in allowed_paths
                    or (configured.scheme, configured.hostname, configured.port or (443 if configured.scheme == 'https' else 80))
                    != (trusted.scheme, trusted.hostname, trusted.port or (443 if trusted.scheme == 'https' else 80))):
                raise ValueError
            return f'{trusted.scheme}://{trusted.netloc}/openrouter/v1/models'
        except (AttributeError, KeyError, TypeError, ValueError):
            raise UserError(_('IAP model catalog endpoint is not trusted.'))

    def action_sync_openrouter_models(self):
        """Fetch all models from the Insilos IAP AI Gateway and sync to database."""
        iap_endpoint = self.env['ir.config_parameter'].sudo().get_param('ai.iap_endpoint', '')
        account_token = None
        use_iap = False
        if iap_endpoint:
            try:
                account = self.env['iap.account'].get('ai_llm')
                account_token = account.account_token if account else None
                use_iap = bool(account_token)
            except Exception:
                pass

        if not use_iap:
            _logger.warning("No IAP endpoint configured, using direct API key (dev mode)")

        try:
            if use_iap:
                catalog_url = self._iap_catalog_url(iap_endpoint)
                res = requests.get(
                    catalog_url,
                    headers={'Authorization': f'Bearer {account_token}'},
                    timeout=15,
                )
                if res.status_code != 200:
                    raise UserError(_('Insilos IAP AI Gateway returned HTTP %s', res.status_code))
                models_data = res.json().get('data', [])
            else:
                res = requests.get('https://openrouter.ai/api/v1/models', timeout=15)
                if res.status_code != 200:
                    raise UserError(_('Insilos IAP AI Gateway returned HTTP %s', res.status_code))
                models_data = res.json().get('data', [])
            count_synced = 0
            count_free = 0

            for m in models_data:
                model_id = m.get('id', '')
                if not model_id:
                    continue

                pricing = m.get('pricing') or {}
                prompt_p = float(pricing.get('prompt') or 0.0) * 1000000.0
                completion_p = float(pricing.get('completion') or 0.0) * 1000000.0
                is_free_model = (':free' in model_id) or (prompt_p == 0.0 and completion_p == 0.0)

                architecture = m.get('architecture') or {}
                modalities = architecture.get('modality') or ''
                supports_vision = 'image' in str(modalities).lower() or 'vision' in str(modalities).lower()

                vals = {
                    'name': m.get('name') or model_id,
                    'is_free': is_free_model,
                    'context_length': m.get('context_length', 0),
                    'prompt_price': prompt_p,
                    'completion_price': completion_p,
                    'supports_vision': supports_vision,
                    'supports_json': True,
                    'description': m.get('description') or '',
                    'active': True,
                }

                existing = self.search([('model_id', '=', model_id)], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    vals['model_id'] = model_id
                    self.create(vals)

                count_synced += 1
                if is_free_model:
                    count_free += 1

            _logger.info("Insilos IAP Model Sync: %d total models, %d free models", count_synced, count_free)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Model Sync Complete'),
                    'message': _('Synced %d Insilos AI models (%d FREE models available)!', count_synced, count_free),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.exception("Failed to sync Insilos IAP AI models")
            raise UserError(_('Could not sync AI models: %s', str(e)))

    @api.model
    def _cron_sync_openrouter_models(self):
        """Cron job to sync Insilos IAP AI models catalog every 6 hours."""
        self.action_sync_openrouter_models()
