# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import logging
import math

from psycopg2 import IntegrityError, errorcodes

from odoo import fields, http
from odoo.http import request
from ..models.is_hse_compliance_event import _EVENT_CREATE_TOKEN
from ..models.is_hse_sync_log import _SYNC_LOG_CREATE_CAPABILITY

_logger = logging.getLogger(__name__)


class HSEWebhookController(http.Controller):

    def _replay_protection_ready(self):
        # Hold the relation lock until transaction end, preventing concurrent DDL.
        request.env.cr.execute('SELECT event_id FROM is_hse_compliance_event LIMIT 0')
        request.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1
                  FROM pg_constraint c
                  JOIN pg_attribute a ON a.attrelid = c.conrelid
                     AND a.attname = 'event_id' AND NOT a.attisdropped
                  JOIN pg_index i ON i.indexrelid = c.conindid
                 WHERE c.conrelid = 'is_hse_compliance_event'::regclass
                   AND c.contype = 'u' AND c.convalidated AND NOT c.condeferrable
                   AND c.conkey = ARRAY[a.attnum]::smallint[]
                   AND i.indisunique AND i.indisvalid AND i.indisready
            )
        """)
        return request.env.cr.fetchone()[0]

    @http.route(['/webhooks/hse-events', '/insilos/hse/webhook'], type='http', auth='public', methods=['POST'], csrf=False)
    def receive_hse_event(self, **kwargs):
        payload_bytes = request.httprequest.get_data()
        signature = request.httprequest.headers.get('X-HSE-Signature', '')
        event_type = request.httprequest.headers.get('X-HSE-Event', 'hse.general_notice')
        secret = request.env['ir.config_parameter'].sudo().get_param('insilos_hse_compliance.hse_webhook_secret')

        if not secret or not signature:
            _logger.warning("Rejected HSE webhook without configured secret or signature.")
            return request.make_json_response({'status': 'error', 'message': 'Missing HMAC signature'}, status=401)
        expected_sig = "sha256=" + hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            _logger.warning("Invalid HSE webhook HMAC signature received.")
            return request.make_json_response({'status': 'error', 'message': 'Invalid HMAC signature'}, status=401)

        if not self._replay_protection_ready():
            return request.make_json_response(
                {'status': 'error', 'message': 'Replay protection unavailable'}, status=503,
            )

        try:
            data = json.loads(payload_bytes.decode('utf-8'))
            event_id = data.get('event_id')
            if not event_id:
                return request.make_json_response({'status': 'error', 'message': 'Missing event_id'}, status=400)
            _logger.info("Successfully verified HSE event: %s (ID: %s)", event_type, event_id)

            Event = request.env['is.hse.compliance.event'].sudo()
            try:
                with request.env.cr.savepoint():
                    event = Event._create_from_signed_webhook([{
                        'event_id': event_id,
                        'event_type': event_type if event_type in dict(Event._fields['event_type'].selection) else 'hse.general_notice',
                        'event_payload': json.dumps(data, ensure_ascii=False),
                    }], _EVENT_CREATE_TOKEN)
            except IntegrityError as exc:
                if exc.pgcode != errorcodes.UNIQUE_VIOLATION:
                    raise
                event = Event.search([('event_id', '=', event_id)], limit=1)
                return request.make_json_response({
                    'status': 'duplicate',
                    'event_id': event_id,
                    'record_id': event.id,
                })

            request.env['is.hse.sync.log'].sudo()._create_from_trusted_sync([{
                'sync_channel': 'webhook',
                'event_type': event_type,
                'status': 'success',
                'message': f"Received and verified HSE event {event_type} ({event_id})",
                'items_processed': 1,
                'payload_snapshot': json.dumps(data)[:500],
            }], _SYNC_LOG_CREATE_CAPABILITY)
            return request.make_json_response({
                'status': 'success',
                'event_id': event_id,
                'event_type': event_type,
                'record_id': event.id,
            })
        except Exception as exc:
            _logger.error("Error processing HSE webhook: %s", exc, exc_info=True)
            request.env['is.hse.sync.log'].sudo()._create_from_trusted_sync([{
                'sync_channel': 'webhook',
                'event_type': event_type,
                'status': 'error',
                'message': f"Error processing HSE webhook: {exc}",
            }], _SYNC_LOG_CREATE_CAPABILITY)
            return request.make_json_response({'status': 'error', 'message': str(exc)}, status=400)

    @staticmethod
    def _valid_cems_measurement(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0

    @http.route(['/api/v1/hse/cems/telemetry', '/webhooks/cems-telemetry'], type='http', auth='public', methods=['POST'], csrf=False)
    def receive_cems_telemetry(self, **kwargs):
        payload_bytes = request.httprequest.get_data()
        signature = request.httprequest.headers.get('X-CEMS-Signature', '')
        secret = request.env['ir.config_parameter'].sudo().get_param('insilos_hse_compliance.cems_webhook_secret')

        if not secret or not signature:
            _logger.warning("Rejected CEMS telemetry without configured secret or signature.")
            return request.make_json_response({'status': 'error', 'message': 'Missing HMAC signature'}, status=401)
        expected_sig = "sha256=" + hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return request.make_json_response({'status': 'error', 'message': 'Invalid HMAC signature'}, status=401)

        return request.make_json_response({
            'status': 'error',
            'message': 'CEMS telemetry is unavailable until facility-specific tenant credentials and signed facility binding exist.',
        }, status=503)

        if not self._replay_protection_ready():
            return request.make_json_response(
                {'status': 'error', 'message': 'Replay protection unavailable'}, status=503,
            )

        try:
            payload = json.loads(payload_bytes.decode('utf-8'))
            if not isinstance(payload, dict):
                return request.make_json_response({'status': 'error', 'message': 'CEMS payload must be an object'}, status=400)
            event_id = payload.get('event_id')
            if not event_id:
                return request.make_json_response({'status': 'error', 'message': 'Missing event_id'}, status=400)
            facility_code = payload.get('facility_code') or payload.get('facility')
            air_data = payload.get('air_emissions')
            water_data = payload.get('wastewater')
            required_measurements = {
                'so2_mg_nm3': air_data.get('so2_mg_nm3') if isinstance(air_data, dict) else None,
                'nox_mg_nm3': air_data.get('nox_mg_nm3') if isinstance(air_data, dict) else None,
                'tsp_dust_mg_nm3': air_data.get('tsp_dust_mg_nm3') if isinstance(air_data, dict) else None,
                'exhaust_flow_m3_h': air_data.get('exhaust_flow_m3_h') if isinstance(air_data, dict) else None,
                'flow_rate_m3_h': water_data.get('flow_rate_m3_h') if isinstance(water_data, dict) else None,
            }
            invalid_measurements = [
                name for name, value in required_measurements.items()
                if not self._valid_cems_measurement(value)
            ]
            if invalid_measurements:
                return request.make_json_response({
                    'status': 'error',
                    'message': f"Invalid or missing CEMS measurements: {', '.join(invalid_measurements)}",
                }, status=400)
            facility = request.env['is.hse.facility'].sudo().search([('code', '=', facility_code)], limit=1)
            if not facility:
                return request.make_json_response({'status': 'error', 'message': f'Facility code {facility_code} not found'}, status=404)

            so2 = required_measurements['so2_mg_nm3']
            nox = required_measurements['nox_mg_nm3']
            tsp = required_measurements['tsp_dust_mg_nm3']
            exhaust_m3 = required_measurements['exhaust_flow_m3_h']
            wastewater_flow = required_measurements['flow_rate_m3_h']

            # No governed legal source, validity window, or facility permit is bound here.
            # Record telemetry only; legal applicability remains pending human review.
            review_status = 'REVIEW_REQUIRED'
            anomaly_status = 'UNASSESSED'

            Event = request.env['is.hse.compliance.event'].sudo()
            try:
                with request.env.cr.savepoint():
                    Event._create_from_signed_webhook([{
                        'event_id': event_id,
                        'event_type': 'hse.general_notice',
                        'affected_facility_id': facility.id,
                        'event_payload': json.dumps(payload, ensure_ascii=False),
                    }], _EVENT_CREATE_TOKEN)
            except IntegrityError as exc:
                if exc.pgcode != errorcodes.UNIQUE_VIOLATION:
                    raise
                event = Event.search([('event_id', '=', event_id)], limit=1)
                return request.make_json_response({
                    'status': 'duplicate',
                    'event_id': event_id,
                    'record_id': event.id,
                })

            scorecard_updated = False
            if 'is.esg.facility.scorecard' in request.env:
                year = fields.Date.today().year
                scorecard = request.env['is.esg.facility.scorecard'].sudo().search([
                    ('facility_id', '=', facility.id),
                    ('reporting_year', '=', year),
                    ('reporting_period', '=', 'annual'),
                ], limit=1)
                if scorecard and scorecard.state == 'draft':
                    scorecard.sudo().write({
                        'cems_so2_emissions_kg': scorecard.cems_so2_emissions_kg + (so2 * exhaust_m3) / 1000000.0,
                        'cems_nox_emissions_kg': scorecard.cems_nox_emissions_kg + (nox * exhaust_m3) / 1000000.0,
                        'cems_tsp_dust_kg': scorecard.cems_tsp_dust_kg + (tsp * exhaust_m3) / 1000000.0,
                        'wastewater_discharged_m3': scorecard.wastewater_discharged_m3 + wastewater_flow,
                    })
                    scorecard_updated = True

            return request.make_json_response({
                'status': 'success',
                'review_status': review_status,
                'anomaly_status': anomaly_status,
                'facility_id': facility.id,
                'facility_name': facility.name,
                'facility_code': facility.code,
                'event_id': event_id,
                'esg_scorecard_updated': scorecard_updated,
            })
        except Exception as exc:
            _logger.error("Error processing CEMS telemetry: %s", exc, exc_info=True)
            return request.make_json_response({'status': 'error', 'message': str(exc)}, status=400)
