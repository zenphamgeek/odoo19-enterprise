# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import re
import uuid

from psycopg2 import IntegrityError

from odoo import fields, http
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)
_MAX_BODY_SIZE = 1024 * 1024
_SAFE_TOKEN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,254}$')
_ALLOWED_KEYS = {
    'spec_version', 'event_id', 'event_type', 'source', 'producer', 'company_id',
    'payload', 'metadata', 'subject', 'priority', 'trace_id', 'correlation_id',
    'causation_id', 'aggregate_id', 'aggregate_version', 'schema_name', 'schema_hash',
    'classification', 'consumer',
}


def _validate_envelope(data):
    if not isinstance(data, dict) or set(data) - _ALLOWED_KEYS:
        raise ValueError
    required = ('spec_version', 'event_id', 'event_type', 'source', 'producer', 'company_id', 'payload')
    if any(key not in data for key in required) or data['spec_version'] != '1.0':
        raise ValueError
    for key in ('event_id', 'event_type', 'source', 'producer'):
        if not isinstance(data[key], str) or not _SAFE_TOKEN.fullmatch(data[key]):
            raise ValueError
    for key in ('trace_id', 'correlation_id', 'causation_id', 'aggregate_id', 'schema_name',
                'schema_hash', 'classification', 'consumer'):
        if key in data and (not isinstance(data[key], str) or not _SAFE_TOKEN.fullmatch(data[key])):
            raise ValueError
    if type(data['company_id']) is not int or data['company_id'] <= 0:
        raise ValueError
    if 'aggregate_version' in data and (type(data['aggregate_version']) is not int or data['aggregate_version'] < 1):
        raise ValueError
    if not isinstance(data['payload'], dict) or len(json.dumps(data['payload']).encode()) > _MAX_BODY_SIZE:
        raise ValueError
    for key in ('sender', 'ai_analysis'):
        if key in data['payload'] and not isinstance(data['payload'][key], dict):
            raise ValueError
    if 'metadata' in data and not isinstance(data['metadata'], dict):
        raise ValueError
    if data.get('priority', 'NORMAL') not in ('LOW', 'NORMAL', 'HIGH', 'URGENT'):
        raise ValueError
    return data


class PubSubERPController(http.Controller):

    @http.route(['/api/v1/pubsub/ingest', '/insilos/pubsub/ingest'], type='http', auth='public', methods=['POST'], csrf=False)
    def ingest_pubsub_event(self, **kwargs):
        request_id = str(uuid.uuid4())
        raw_body = request.httprequest.get_data()
        headers = {'X-Request-ID': request_id}
        if not raw_body or len(raw_body) > _MAX_BODY_SIZE:
            return request.make_json_response({'status': 'error', 'message': 'Invalid request', 'request_id': request_id}, status=400, headers=headers)
        try:
            data = _validate_envelope(json.loads(raw_body.decode('utf-8')))
            company = request.env['res.company'].sudo().browse(data['company_id']).exists()
            if not company:
                raise ValueError
            source_type = 'gmail_push' if data['event_type'] == 'gmail.push.notification' else 'hermes_event_bus'
            channel = request.env['is.pubsub.channel'].sudo().search([
                ('company_id', '=', company.id), ('channel_type', '=', source_type),
                ('state', '=', 'active'), ('webhook_secret', '!=', False),
            ], order='id desc', limit=1)
            secret = channel.webhook_secret
            signature = request.httprequest.headers.get('X-Hermes-Signature', '')
            api_key = request.httprequest.headers.get('X-ERP-API-Key', '')
            authenticated = bool(secret) and (
                bool(signature) and hmac.compare_digest(signature, 'sha256=' + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest())
                or bool(api_key) and consteq(secret, api_key)
            )
            if not authenticated:
                _logger.warning('PubSub authentication rejected. Request ID: %s', request_id)
                return request.make_json_response({'status': 'error', 'message': 'Unauthorized', 'request_id': request_id}, status=401, headers=headers)

            request.update_context(allowed_company_ids=[company.id])
            payload = data['payload']
            sender = payload.get('sender', {})
            ai_data = payload.get('ai_analysis', {})
            metadata = data.get('metadata', {})
            EventLog = request.env['is.pubsub.event.log'].sudo()
            try:
                with request.env.cr.savepoint():
                    event_log = EventLog.create({
                        'event_id': data['event_id'],
                        'trace_id': data.get('trace_id') or request_id,
                        'correlation_id': data.get('correlation_id'), 'causation_id': data.get('causation_id'),
                        'aggregate_id': data.get('aggregate_id'), 'aggregate_version': data.get('aggregate_version'),
                        'schema_name': data.get('schema_name'), 'schema_hash': data.get('schema_hash'),
                        'classification': data.get('classification'), 'consumer': data.get('consumer') or 'default',
                        'event_type': data['event_type'] if data['event_type'] in dict(EventLog._fields['event_type'].selection) else 'general.event',
                        'source': data['source'], 'state': 'received',
                        'priority': data.get('priority', 'NORMAL'), 'producer': data['producer'],
                        'sender_email': sender.get('email') or payload.get('sender_email'),
                        'sender_name': sender.get('name') or payload.get('sender_name'),
                        'subject': payload.get('subject') or data.get('subject', 'PubSub Event'),
                        'gcp_message_id': metadata.get('gcp_message_id'),
                        'history_id': str(metadata['history_id']) if metadata.get('history_id') else False,
                        'payload': raw_body.decode(), 'ai_summary': ai_data.get('summary') or payload.get('summary', ''),
                        'ai_entities_json': json.dumps(ai_data.get('entities', {}), ensure_ascii=False),
                        'company_id': company.id,
                    })
            except IntegrityError:
                return request.make_json_response({'status': 'ignored', 'message': 'Duplicate event (already claimed)', 'event_id': data['event_id'], 'request_id': request_id}, headers=headers)

            event_log._process_claimed_event()
            rules = request.env['is.pubsub.automation.rule'].sudo().search([
                ('company_id', '=', company.id), ('active', '=', True), ('state', '=', 'active'),
            ])
            rules_triggered = sum(bool(rule.execute_rule(event_log)) for rule in rules)
            channel.write({'last_heartbeat': fields.Datetime.now(), 'last_status_message': f"Event {data['event_id']} ingested successfully."})
            return request.make_json_response({
                'status': 'success', 'event_id': data['event_id'], 'event_log_id': event_log.id,
                'target_model': event_log.target_model, 'target_res_id': event_log.target_res_id,
                'state': event_log.state, 'rules_triggered': rules_triggered, 'request_id': request_id,
            }, headers=headers)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
            request.env.cr.rollback()
            return request.make_json_response({'status': 'error', 'message': 'Invalid request', 'request_id': request_id}, status=400, headers=headers)
        except Exception:
            request.env.cr.rollback()
            _logger.exception('PubSub internal error. Request ID: %s', request_id)
            return request.make_json_response({'status': 'error', 'message': 'Internal error', 'request_id': request_id}, status=500, headers=headers)
