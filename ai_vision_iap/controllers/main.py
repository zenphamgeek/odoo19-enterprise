# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging
import secrets

from odoo import http
from odoo.http import request, route, Response

_logger = logging.getLogger(__name__)


class AIVisionWebhookController(http.Controller):

    @route('/api/iap/webhook-ai', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def webhook_ai_vision(self, **kwargs):
        """Webhook callback endpoint for Trigger.dev AI Vision worker.

        Payload format:
            {
                "record_id": 123,
                "status": "success" | "failed",
                "data": {
                    "vendor_name": "ACME Corp",
                    "total_amount": 1500.0,
                    "invoice_date": "2026-07-29"
                },
                "error": "Error description..."
            }
        """
        # Security validation.
        #
        # KHÔNG có giá trị mặc định: tham số này chưa từng được seed ở đâu
        # (không `data/*.xml`, không migration), nên một literal làm default
        # nghĩa là **mọi** DB production đều dùng đúng một secret đã nằm sẵn
        # trong source code. Endpoint là `auth='public'`, `csrf=False`, và nó
        # ghi `account.move` rồi tiêu credit — ai đọc repo cũng giả được
        # callback. Chưa cấu hình thì phải từ chối, không phải đoán.
        expected_secret = request.env['ir.config_parameter'].sudo().get_param(
            'ai_vision.webhook_secret'
        )
        received_secret = request.httprequest.headers.get('X-Insilos-Webhook-Secret') or \
                          request.httprequest.headers.get('X-Insilos-Webhook-Secret')

        if not expected_secret:
            _logger.error(
                "AI Webhook bị từ chối: chưa đặt tham số `ai_vision.webhook_secret`. "
                "Đặt nó trước khi bật webhook."
            )
            return {'status': 'forbidden', 'code': 403, 'error': 'Webhook not configured'}

        # `compare_digest` thay vì `!=`: so sánh chuỗi thường thoát ra ở byte
        # đầu tiên khác nhau, để lộ độ dài tiền tố đúng qua thời gian đáp ứng.
        if not received_secret or not secrets.compare_digest(received_secret, expected_secret):
            _logger.warning("Unauthorized AI Webhook access attempt: invalid secret")
            return {'status': 'forbidden', 'code': 403, 'error': 'Invalid webhook secret'}

        # `kwargs` chứ **không** phải `request.dispatcher.jsonrequest`: với
        # `type='jsonrpc'` thì `jsonrequest` là cả phong bì JSON-RPC
        # (`{jsonrpc, method, params, id}`), nên `.get('record_id')` luôn trả
        # None và endpoint trả 400 "Missing record_id" cho **mọi** callback
        # hợp lệ. Dispatcher đã tách `params` ra thành tham số của hàm rồi.
        record_id = kwargs.get('record_id')
        status = kwargs.get('status')
        operation_id = kwargs.get('operation_id')
        event_id = kwargs.get('event_id')
        trigger_run_id = kwargs.get('trigger_run_id')
        data = kwargs.get('data') or {}
        error_msg = kwargs.get('error_class') or ''

        if not record_id:
            return {'status': 'error', 'code': 400, 'error': 'Missing record_id'}
        if kwargs.get('schema_version') != '1.0':
            return {'status': 'error', 'code': 400, 'error': 'Invalid schema version'}
        if not operation_id or not event_id or not trigger_run_id:
            return {'status': 'error', 'code': 400, 'error': 'Missing callback correlation'}
        if status not in ('succeeded', 'failed', 'timed_out', 'cancelled', 'dead_letter'):
            return {'status': 'error', 'code': 400, 'error': 'Invalid status'}

        move = request.env['account.move'].sudo().browse(int(record_id))
        if not move.exists():
            return {'status': 'error', 'code': 404, 'error': f'Record {record_id} not found'}
        expected_operation_id = move.ai_operation_id or f'ai_vision_account.move_{move.id}'
        if operation_id != expected_operation_id:
            return {'status': 'error', 'code': 409, 'error': 'Operation mismatch'}
        if kwargs.get('company_id') != move.company_id.id or kwargs.get('tenant_id') != request.env.cr.dbname:
            return {'status': 'error', 'code': 409, 'error': 'Tenant mismatch'}
        if move.ai_trigger_run_id and trigger_run_id != move.ai_trigger_run_id:
            return {'status': 'error', 'code': 409, 'error': 'Trigger run mismatch'}

        # Idempotency check: prevent double processing if already done or failed
        if move.ai_status in ('done', 'failed'):
            _logger.info("AI Webhook ignored: record %s is already in state %s", record_id, move.ai_status)
            return {'status': 'already_processed', 'ai_status': move.ai_status}

        # Chốt thứ hai, ở tầng nền tảng. Kiểm `ai_status` phía trên là **đọc rồi
        # ghi**: hai worker cùng retry một event đều đọc thấy `processing` rồi
        # cùng đi tiếp, và cùng tiêu credit. `claim()` chốt bằng
        # `UNIQUE(service, event_id)` nên chỉ một bên qua được.
        #
        # Khoá dùng `record_id` + `status`: một record có thể nhận `success` rồi
        # sau đó `failed` (worker retry đổi kết quả), hai event đó khác nhau và
        # đều phải xử lý được.
        if not request.env['iap.webhook.event'].sudo().claim(
                'ai_vision', event_id, status=status,
                record_ref=f'account.move,{move.id}'):
            return {'status': 'already_processed', 'ai_status': move.ai_status}

        if status == 'succeeded':
            # Parse values
            vals = {
                'ai_status': 'done', 'ai_error_log': False,
                'ai_callback_event_id': event_id,
                'ai_trigger_run_id': trigger_run_id,
            }
            partner_name = data.get('vendor_name')
            total_amount = data.get('total_amount')
            invoice_date = data.get('invoice_date')

            if partner_name:
                partner = request.env['res.partner'].sudo().search([
                    ('name', 'ilike', partner_name)
                ], limit=1)
                if partner:
                    vals['partner_id'] = partner.id

            if invoice_date:
                vals['invoice_date'] = invoice_date

            # `total_amount` trước đây chỉ được in ra chatter rồi vứt đi:
            # chatter báo "đã trích xuất" một con số mà không cột nào giữ.
            # Ghi vào `ai_extracted_amount` (không phải `amount_total`, cột đó
            # compute từ dòng bút toán).
            if total_amount is not None:
                try:
                    vals['ai_extracted_amount'] = float(total_amount)
                except (TypeError, ValueError):
                    _logger.warning(
                        "AI Webhook: total_amount không phải số (%r), bỏ qua", total_amount)

            move.write(vals)

            # Consume held credits via charge lookup
            charge = request.env['iap.charge'].sudo().search([
                ('operation_id', '=', f'ai_vision_account.move_{move.id}'),
                ('state', '=', 'held'),
            ], limit=1)
            move._consume_iap(charge)

            # Post message to Chatter
            chatter_msg = f"<b>🤖 AI Vision Extraction Complete</b><br/>"
            if partner_name:
                chatter_msg += f"• Vendor: {partner_name}<br/>"
            if total_amount:
                chatter_msg += f"• Total: {total_amount}<br/>"
            if invoice_date:
                chatter_msg += f"• Invoice Date: {invoice_date}<br/>"
            move.message_post(body=chatter_msg)

            # Send bus notification
            try:
                request.env['bus.bus']._sendone(
                    move.create_uid.partner_id,
                    'simple_notification',
                    {
                        'title': 'AI Vision Extraction Done',
                        'message': f'Invoice #{move.name or move.id} data extracted successfully!',
                        'type': 'success',
                    }
                )
            except Exception as e:
                _logger.info("Bus notification skipped (%s)", e)

            return {'status': 'success', 'record_id': move.id, 'ai_status': 'done'}

        else:
            # Failure logic - refund held credits
            charge = request.env['iap.charge'].sudo().search([
                ('operation_id', '=', f'ai_vision_account.move_{move.id}'),
            ], limit=1)
            move._refund_iap(charge)
            move.write({
                'ai_status': 'failed',
                'ai_error_log': error_msg or 'AI Vision extraction failed on worker.',
                'ai_callback_event_id': event_id,
                'ai_trigger_run_id': trigger_run_id,
            })
            move.message_post(body=f"❌ <b>AI Vision Extraction Failed:</b> {error_msg}. IAP credits refunded.")

            return {'status': 'failed', 'record_id': move.id, 'ai_status': 'failed'}
