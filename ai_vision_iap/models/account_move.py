# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging
import requests
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    ai_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('processing', 'Processing'),
            ('done', 'Done'),
            ('failed', 'Failed'),
        ],
        string='AI Vision Status',
        default='draft',
        required=True,
        copy=False,
        index=True,
    )
    ai_error_log = fields.Text(string='AI Error Log', copy=False)
    ai_operation_id = fields.Char(copy=False, index=True)
    ai_extraction_run_id = fields.Char(copy=False, index=True)
    ai_trigger_run_id = fields.Char(copy=False, index=True)
    ai_callback_event_id = fields.Char(copy=False, index=True)
    # Số tiền AI đọc được từ ảnh. KHÔNG ghi thẳng vào `amount_total`: cột đó
    # `compute='_compute_amount'` từ các dòng bút toán, gán vào sẽ bị tính lại
    # đè mất. Giữ riêng để kế toán còn đối chiếu được với `amount_total` thật.
    ai_extracted_amount = fields.Monetary(
        string='AI Extracted Total', copy=False, currency_field='currency_id',
        help="Tổng tiền do AI đọc từ ảnh, để đối chiếu. Không dùng để ghi sổ.",
    )

    # ── IAP Credit Methods ────────────────────────────────────────────────────

    def _hold_iap(self, amount=None):
        """Hold credits for AI extraction. Returns the charge record.

        `amount=None` nghĩa là "lấy giá từ `iap.service`", không phải "miễn
        phí": giá là dữ liệu (`credit_cost`), không phải hằng trong code. Bản
        trước mặc định `amount=1` cho mọi ảnh, nên đổi giá theo provider là
        sửa code + build lại image.
        """
        Charge = self.env['iap.charge']
        account = self.env['iap.account'].sudo().get('ai_llm')
        wallet = self.env['iap.wallet'].get_wallet(self.company_id, iap_account=account)
        if amount is None:
            amount = self.env['iap.service'].cost_for('ai_vision')
        operation_id = f'ai_vision_{self._name}_{self.id}'
        return Charge.hold(
            wallet=wallet,
            amount=amount,
            operation_id=operation_id,
            service_name='ai_vision',
            reference=f'AI Vision extraction for {self._name}#{self.id}',
        )

    def _consume_iap(self, charge):
        """Consume held credits after successful extraction."""
        if charge and charge.state == 'held':
            charge.consume()
            _logger.info("IAP CONSUME: %s credits consumed for %s#%s", charge.amount, self._name, self.id)

    def _refund_iap(self, charge):
        """Release a hold, or refund an already consumed charge."""
        if charge and charge.state == 'held':
            charge.release()
        elif charge and charge.state == 'consumed':
            charge.refund()
        if charge:
            _logger.info("IAP RELEASE/REFUND: %s credits restored for %s#%s", charge.amount, self._name, self.id)

    # ── Action Methods ────────────────────────────────────────────────────────

    def action_trigger_ai_extraction(self):
        """Trigger background AI Vision data extraction via Trigger.dev worker."""
        self.ensure_one()
        if self.ai_status == 'processing':
            raise UserError(_('AI Vision extraction is already processing for this record.'))

        # Find first image or PDF attachment
        Attachment = self.env['ir.attachment']
        attachment = Attachment.search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('mimetype', 'in', ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']),
        ], limit=1)

        if not attachment:
            # Fallback to any attachment on this record
            attachment = Attachment.search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', self.id),
            ], limit=1)

        if not attachment:
            raise UserError(_('Please attach an invoice image or PDF document to this record before triggering AI extraction.'))

        # Generate access token if missing
        if not attachment.access_token:
            attachment.generate_access_token()

        params = self.env['ir.config_parameter'].sudo()
        base_url = params.get_param(
            'ai_vision.callback_base_url',
            params.get_param('web.base.url', 'https://insilos.com'),
        ).rstrip('/')
        image_url = f"{base_url}/web/content/{attachment.id}?access_token={attachment.access_token}"

        trigger_url = params.get_param('ai_vision.trigger_url')
        if not trigger_url:
            raise UserError(_('AI Vision trigger URL is not configured.'))
        trigger_secret = params.get_param('ai_vision.trigger_secret')
        if not trigger_secret:
            raise UserError(_('AI Vision trigger secret is not configured.'))
        iap_endpoint = params.get_param('ai.iap_endpoint')
        if not iap_endpoint:
            raise UserError(_('AI IAP endpoint is not configured.'))
        webhook_url = f"{base_url}/api/iap/webhook-ai"

        # Hold IAP credits before dispatch
        try:
            charge = self._hold_iap()
        except UserError as e:
            raise UserError(_('Insufficient IAP credits. %s', str(e)))

        extraction_run_id = charge.operation_id
        payload = {
            'schema_version': '1.0',
            'company_id': self.company_id.id,
            'tenant_id': self.env.cr.dbname,
            'document_id': attachment.id,
            'record_model': self._name,
            'record_id': self.id,
            'extraction_run_id': extraction_run_id,
            'operation_id': charge.operation_id,
            'correlation_id': charge.operation_id,
            'image_url': image_url,
            'webhook_url': webhook_url,
            'delegation_token': charge.mint_delegation_token(),
            'iap_endpoint': iap_endpoint,
            'service_name': 'ai_vision',
            'model_hint': params.get_param(
                'ai_vision.model', 'qwen/qwen2.5-vl-72b-instruct'),
            'credit_metadata': {'held_amount': charge.amount},
        }

        try:
            response = requests.post(
                trigger_url,
                headers={
                    'Authorization': f'Bearer {trigger_secret}',
                    'Content-Type': 'application/json',
                    'Idempotency-Key': charge.operation_id,
                },
                json={'payload': payload},
                timeout=5,
            )
            response.raise_for_status()
            response_data = response.json()
            if not isinstance(response_data, dict) or not response_data.get('id'):
                raise ValueError('Trigger.dev response has no run id')
        except (requests.RequestException, ValueError):
            _logger.warning("Could not dispatch async request to Trigger.dev")
            raise UserError(_('Could not dispatch AI Vision extraction. No credits were charged.'))

        self.write({
            'ai_status': 'processing',
            'ai_error_log': False,
            'ai_operation_id': charge.operation_id,
            'ai_extraction_run_id': extraction_run_id,
            'ai_trigger_run_id': response_data['id'],
            'ai_callback_event_id': False,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('AI Extraction Triggered'),
                'message': _('AI Vision is extracting invoice data in the background...'),
                'type': 'info',
                'sticky': False,
            }
        }

    # ── Cron Cleanup ──────────────────────────────────────────────────────────

    @api.model
    def _cron_cleanup_stuck_ai_processing(self):
        """Reset records stuck in 'processing' for > 15 minutes."""
        timeout_threshold = datetime.now() - timedelta(minutes=15)
        stuck_records = self.search([
            ('ai_status', '=', 'processing'),
            ('write_date', '<', timeout_threshold),
        ])
        for record in stuck_records:
            charge = self.env['iap.charge'].sudo().search([
                ('operation_id', '=', f'ai_vision_{record._name}_{record.id}'),
            ], limit=1)
            record._refund_iap(charge)
            record.write({
                'ai_status': 'failed',
                'ai_error_log': 'Extraction timed out after 15 minutes. Credits refunded.',
            })
            record.message_post(body=_('AI Vision extraction timed out after 15 minutes. 1 IAP credit refunded.'))
        _logger.info("Cleaned up %d stuck AI processing records", len(stuck_records))
