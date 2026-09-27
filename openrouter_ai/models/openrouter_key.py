# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging
import os
import requests

from odoo import api, fields, models, _
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import UserError
from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)


class OpenRouterKey(models.Model):
    _name = 'openrouter.key'
    _description = 'Insilos IAP Key & Credit Balance'

    name = fields.Char(string='Key Label', required=True, default='Primary Insilos IAP Key')
    # `groups` chặn ở tầng ORM: field không vào view, không vào `web_search_read`,
    # không vào export. Khác `password="True"` — cái đó chỉ che ở UI, giá trị vẫn
    # đi qua RPC tới mọi user đọc được record.
    # Khi IAP endpoint đã cấu hình (`ai.iap_endpoint`), key thật sống ở canonical
    # Node IAP server (`iap_server/server.js`, đọc từ env/secret file) — record này
    # KHÔNG còn cần lưu giá trị thật, và action_check_balance()/get_default_key() không bao
    # field này qua mạng. Dev-mode fallback đọc trực tiếp env var, không ghi DB.
    api_key = fields.Char(
        string='API Key (environment-managed)',
        compute='_compute_api_key_mask',
        readonly=True,
        groups='base.group_system',
    )
    is_default = fields.Boolean(string='Default Key', default=False)
    is_free_tier = fields.Boolean(string='Free Tier Key', readonly=True)

    usage = fields.Float(string='Total Usage (USD)', readonly=True, digits=(12, 6))
    usage_daily = fields.Float(string='Daily Usage (USD)', readonly=True, digits=(12, 6))
    usage_monthly = fields.Float(string='Monthly Usage (USD)', readonly=True, digits=(12, 6))
    limit_remaining = fields.Float(string='Credit Limit Remaining (USD)', readonly=True, digits=(12, 6))

    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    state = fields.Selection([
        ('untested', 'Untested'),
        ('valid', 'Valid & Active'),
        ('invalid', 'Invalid Key'),
    ], string='Status', default='untested', readonly=True)

    def _auto_init(self):
        # Chỉ scrub cột legacy đã tồn tại. Fresh install để super tạo schema;
        # upgrade xóa secret trước khi ORM có thể bỏ cột computed khỏi DB.
        if column_exists(self.env.cr, self._table, 'api_key'):
            self.env.cr.execute("UPDATE openrouter_key SET api_key = NULL WHERE api_key IS NOT NULL")
        return super()._auto_init()

    @api.depends()
    def _compute_api_key_mask(self):
        token = os.getenv('INSILOS_OPENROUTER_API_KEY', '')
        mask = f'••••{token[-4:]}' if token else False
        for record in self:
            record.api_key = mask

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.is_default:
                self.search([('id', '!=', rec.id), ('is_default', '=', True)]).write({'is_default': False})
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_default'):
            self.search([('id', 'not in', self.ids), ('is_default', '=', True)]).write({'is_default': False})
        return res

    def action_check_balance(self):
        """Fetch live key info & credit balance from the Insilos IAP AI Gateway."""
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

        for rec in self:
            direct_key = os.getenv('INSILOS_OPENROUTER_API_KEY', '')
            if not use_iap and not direct_key:
                raise UserError(_('INSILOS_OPENROUTER_API_KEY is not configured.'))

            try:
                if use_iap:
                    # Không forward api_key thật qua mạng — IAP server tự tra key
                    # thật server-side theo `account_token` (R21: BEACON vs SERVICE,
                    # ở đây là nguyên tắc tương tự cho secret: không rò rỉ giá trị
                    # ra khỏi biên tin cậy khi không cần thiết).
                    iap_params = {
                        'provider': 'openrouter',
                        'account_token': account_token,
                    }
                    data = iap_tools.iap_jsonrpc(
                        iap_endpoint + '/openrouter/v1/auth/key',
                        params=iap_params,
                        timeout=10,
                    )
                    data = data.get('data', {})
                    rec.write({
                        'state': 'valid',
                        'is_free_tier': data.get('is_free_tier', False),
                        'usage': data.get('usage', 0.0) or 0.0,
                        'usage_daily': data.get('usage_daily', 0.0) or 0.0,
                        'usage_monthly': data.get('usage_monthly', 0.0) or 0.0,
                        'limit_remaining': data.get('limit_remaining', 0.0) or 0.0,
                        'last_sync_date': fields.Datetime.now(),
                    })
                else:
                    res = requests.get(
                        'https://openrouter.ai/api/v1/auth/key',
                        headers={'Authorization': f'Bearer {direct_key.strip()}'},
                        timeout=10,
                    )
                    if res.status_code == 200:
                        data = res.json().get('data', {})
                        rec.write({
                            'state': 'valid',
                            'is_free_tier': data.get('is_free_tier', False),
                            'usage': data.get('usage', 0.0) or 0.0,
                            'usage_daily': data.get('usage_daily', 0.0) or 0.0,
                            'usage_monthly': data.get('usage_monthly', 0.0) or 0.0,
                            'limit_remaining': data.get('limit_remaining', 0.0) or 0.0,
                            'last_sync_date': fields.Datetime.now(),
                        })
                    else:
                        rec.write({
                            'state': 'invalid',
                            'last_sync_date': fields.Datetime.now(),
                        })
                        # Nhánh này gọi thẳng openrouter.ai, **không** qua IAP —
                        # ghi "Insilos IAP returned" ở đây gửi người đọc đi soi
                        # nhầm dịch vụ. Thông báo lỗi là bản đồ dẫn tới chỗ
                        # hỏng; chỉ sai tên là mất cả buổi.
                        raise UserError(_('OpenRouter returned HTTP %s: %s', res.status_code, res.text[:200]))
            except Exception as e:
                rec.write({'state': 'invalid'})
                _logger.exception("Failed to check Insilos IAP key balance for %s", rec.name)
                raise UserError(_('Could not check balance: %s', str(e)))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Key Verified'),
                'message': _('Insilos IAP Key verified successfully!'),
                'type': 'success',
                'sticky': False,
            }
        }

    @staticmethod
    def _resolve_direct_key():
        if 'INSILOS_OPENROUTER_API_KEY' in os.environ:
            return os.environ['INSILOS_OPENROUTER_API_KEY']
        secret_file = os.getenv('INSILOS_OPENROUTER_API_KEY_FILE')
        if secret_file:
            with open(secret_file, encoding='utf-8') as stream:
                return stream.read().rstrip('\r\n')
        return False

    @api.model
    def get_default_key(self):
        """Return the auth value to use for direct OpenRouter calls.

        Khi IAP endpoint đã cấu hình, key thật không rời IAP server — trả
        placeholder "IAP_ROUTED" giống `llm_api_service.py:_get_api_token()`.
        Chỉ dev-mode (không IAP) mới trả giá trị thật từ `INSILOS_OPENROUTER_API_KEY`.
        """
        if self.env['ir.config_parameter'].sudo().get_param('ai.iap_endpoint'):
            return "IAP_ROUTED"
        key_rec = self.search([('is_default', '=', True), ('state', '=', 'valid')], limit=1)
        if not key_rec:
            key_rec = self.search([('state', '=', 'valid')], limit=1)
        if not key_rec:
            key_rec = self.search([], limit=1)
        return self._resolve_direct_key()
