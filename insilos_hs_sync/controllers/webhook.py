# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hmac
import hashlib
import json
import logging
import time
from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class InsilosHSWebhookController(http.Controller):

    @http.route('/insilos/webhooks/hs-events', type='http', auth='public', methods=['POST'], csrf=False)
    def receive_hs_event(self, **kwargs):
        """
        Receives and processes signed HS knowledge events from Hermes Agent Webhook Hub.
        """
        req = request.httprequest
        secret = request.env['ir.config_parameter'].sudo().get_param('insilos_hs_sync.webhook_secret', '')
        received_sig = req.headers.get('X-HS-Signature-256')
        received_ts = req.headers.get('X-HS-Timestamp')
        raw_body = req.get_data()
        remote_addr = req.remote_addr

        # 1. Anti-replay verification (300s window) if timestamp provided
        if received_ts:
            try:
                ts_int = int(received_ts)
                now_int = int(time.time())
                if abs(now_int - ts_int) > 300:
                    _logger.warning("Rejected Hermes Webhook due to timestamp drift: %s (now=%s)", ts_int, now_int)
                    return request.make_json_response({'status': 'error', 'message': 'Timestamp outside valid window'}, status=400)
            except (ValueError, TypeError):
                pass

        # 2. Verify HMAC-SHA256 signature if secret configured
        if secret and received_sig:
            expected_sig = "sha256=" + hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, received_sig):
                _logger.warning("Invalid HMAC-SHA256 signature received for Insilos HS Webhook from %s", remote_addr)
                self._record_log(None, 'unauthorized', 'error', 'Invalid HMAC signature', raw_body.decode('utf-8', errors='ignore'), 'Invalid HMAC signature', remote_addr)
                return request.make_json_response({'status': 'error', 'message': 'Invalid signature'}, status=401)

        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except Exception as e:
            _logger.error("Invalid JSON body received: %s", e)
            self._record_log(None, 'parse_error', 'error', 'Invalid JSON body', str(raw_body), str(e), remote_addr)
            return request.make_json_response({'status': 'error', 'message': f'Invalid JSON payload: {e}'}, status=400)

        event_id = payload.get('event_id')
        event_type = payload.get('event_type')
        data = payload.get('data', {})
        _logger.info("Processing Insilos HS event: %s (id=%s)", event_type, event_id)

        env = request.env(su=True)

        try:
            # 3. Process specific event types
            if event_type == 'hs.ruling.published':
                self._process_ruling_published(env, data)
            elif event_type == 'hs.tariff.changed':
                self._process_tariff_changed(env, data)
            elif event_type == 'hs.legal.gazette':
                self._process_legal_gazette(env, data)
            else:
                _logger.info("Ignored unhandled event type: %s", event_type)

            # Record success audit log
            self._record_log(
                event_id=event_id,
                event_type=event_type,
                status='success',
                summary=f"Event {event_type} processed successfully",
                raw_payload=json.dumps(payload, indent=2, ensure_ascii=False),
                error_msg=None,
                remote_addr=remote_addr
            )

            return request.make_json_response({'status': 'success', 'event_id': event_id})

        except Exception as e:
            _logger.exception("Error processing HS Webhook event: %s", event_id)
            self._record_log(
                event_id=event_id,
                event_type=event_type,
                status='error',
                summary=f"Error executing handler for {event_type}",
                raw_payload=json.dumps(payload, indent=2, ensure_ascii=False),
                error_msg=str(e),
                remote_addr=remote_addr
            )
            return request.make_json_response({'status': 'error', 'message': str(e)}, status=500)

    def _record_log(self, event_id, event_type, status, summary, raw_payload, error_msg, remote_addr):
        try:
            env = request.env(su=True)
            env['is.hs.sync.log'].create({
                'event_id': event_id,
                'event_type': event_type,
                'direction': 'inbound_webhook',
                'status': status,
                'payload_summary': summary,
                'raw_payload': raw_payload,
                'error_message': error_msg,
                'remote_ip': remote_addr,
            })
        except Exception as e:
            _logger.warning("Failed to record webhook audit log: %s", e)

    def _process_ruling_published(self, env, data):
        ruling_model = env['is.customs.ruling']
        ruling_num = data.get('document_id') or data.get('ruling_number')
        if not ruling_num:
            return

        existing = ruling_model.search([('ruling_number', '=', ruling_num)], limit=1)
        vals = {
            'ruling_number': ruling_num,
            'issuing_authority': data.get('issuing_authority') or 'Tổng cục Hải quan',
            'hs_code': data.get('hs_code', ''),
            'commercial_name': data.get('title') or data.get('commercial_name', ''),
            'technical_description': data.get('content_snippet') or data.get('technical_description', ''),
            'classification_rationale': data.get('legal_basis') or data.get('classification_rationale', ''),
            'source_url': data.get('source_url', ''),
            'artifact_sha256': data.get('artifact_sha256', ''),
            'status': data.get('status', 'active'),
        }
        if data.get('issue_date'):
            vals['issue_date'] = data.get('issue_date')
        if data.get('expiry_date'):
            vals['expiry_date'] = data.get('expiry_date')

        if existing:
            existing.write(vals)
        else:
            ruling_model.create(vals)
            
        # Push real-time notification to UI
        self._notify_users(
            env,
            title="Phán Quyết Mã HS Mới Được Ban Hành",
            message=f"Hải quan ban hành thông báo xác định trước mã HS: {ruling_num} (Mã HS: {data.get('hs_code', 'N/A')})",
            notif_type='info',
            sticky=False
        )

    def _process_tariff_changed(self, env, data):
        tariff_model = env['is.hs.tariff']
        hs_code = data.get('hs_code')
        if not hs_code:
            return

        tariff_vals = {
            'hs_code': hs_code,
            'description_vi': data.get('description_vi') or data.get('title', ''),
            'description_en': data.get('description_en', ''),
            'import_duty_rate': data.get('import_duty_rate', 0.0),
            'export_duty_rate': data.get('export_duty_rate', 0.0),
            'vat_rate': data.get('vat_rate', 10.0),
            'unit': data.get('unit', ''),
            'specialized_management_notes': data.get('specialized_management_notes', ''),
            'legal_basis': data.get('legal_basis', ''),
            'source_url': data.get('source_url', ''),
        }
        existing_tariff = tariff_model.search([('hs_code', '=', hs_code)], limit=1)
        if existing_tariff:
            existing_tariff.write(tariff_vals)
        else:
            tariff_model.create(tariff_vals)

        # Update matching product templates if auto-update is enabled
        auto_update = env['ir.config_parameter'].get_param('insilos_hs_sync.auto_update_products', 'True')
        if auto_update in ('True', '1', True):
            products = env['product.template'].search([('hs_code_customs', '=', hs_code)])
            if products:
                prod_vals = {'hs_last_synced': fields.Datetime.now()}
                if data.get('import_duty_rate') is not None:
                    prod_vals['import_duty_rate'] = data.get('import_duty_rate')
                if data.get('vat_rate') is not None:
                    prod_vals['vat_rate'] = data.get('vat_rate')
                if data.get('specialized_management_notes'):
                    prod_vals['specialized_management_notes'] = data.get('specialized_management_notes')
                products.write(prod_vals)

        # Push real-time notification to UI
        self._notify_users(
            env,
            title="Biểu Thuế Quan Đã Cập Nhật",
            message=f"Mã HS {hs_code}: Thuế NK={data.get('import_duty_rate', 0)}%, VAT={data.get('vat_rate', 10)}%",
            notif_type='warning',
            sticky=True
        )

    def _process_legal_gazette(self, env, data):
        title = data.get('title') or 'Văn bản quy phạm pháp luật mới'
        doc_id = data.get('document_id') or 'N/A'
        self._notify_users(
            env,
            title=f"Văn Bản Pháp Luật Mới: {doc_id}",
            message=title,
            notif_type='info',
            sticky=True
        )

    def _notify_users(self, env, title, message, notif_type='info', sticky=False):
        """Bắn Toast Notification thời gian thực lên giao diện qua bus.bus."""
        try:
            users = env['res.users'].search([('share', '=', False)])
            partners = users.mapped('partner_id')
            payload = {
                'type': notif_type,
                'title': title,
                'message': message,
                'sticky': sticky,
            }
            for partner in partners:
                env['bus.bus']._sendone(partner, 'simple_notification', payload)
        except Exception as e:
            _logger.warning("Failed to broadcast UI notification: %s", e)
