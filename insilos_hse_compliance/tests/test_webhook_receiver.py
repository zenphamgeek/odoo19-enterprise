# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json

from odoo.exceptions import AccessError
from odoo.addons.insilos_hse_compliance.models.is_hse_sync_log import _SYNC_LOG_CREATE_CAPABILITY
from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'insilos_hse_compliance')
class TestHSEWebhookReceiver(HttpCase):

    def setUp(self):
        super().setUp()
        self.secret = 'test_hse_secret_2026'
        self.cems_secret = 'test_cems_secret_2026'
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('insilos_hse_compliance.hse_webhook_secret', self.secret)
        params.set_param('insilos_hse_compliance.cems_webhook_secret', self.cems_secret)

    def _post(self, url, payload, secret, signature_header, extra_headers=None):
        body = json.dumps(payload).encode()
        headers = {'Content-Type': 'application/json', **(extra_headers or {})}
        if signature_header:
            headers[signature_header] = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return self.url_open(url, data=body, headers=headers)

    def test_valid_hmac_creates_event(self):
        payload = {'event_id': 'evt_hse_valid_001', 'event_type': 'hse.legal.published'}
        response = self._post(
            '/webhooks/hse-events', payload, self.secret, 'X-HSE-Signature',
            {'X-HSE-Event': 'hse.legal.published'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(self.env['is.hse.compliance.event'].search([('event_id', '=', payload['event_id'])]))

    def test_webhook_never_auto_applies_legal_document(self):
        self.env['ir.config_parameter'].sudo().set_param('insilos_hse_compliance.hse_auto_apply_updates', 'True')
        payload = {
            'event_id': 'evt_hse_no_auto_apply',
            'document': {'code': 'HSE_NO_AUTO_APPLY', 'name': 'Must be reviewed first'},
        }
        response = self._post(
            '/webhooks/hse-events', payload, self.secret, 'X-HSE-Signature',
            {'X-HSE-Event': 'hse.legal.published'},
        )
        self.assertEqual(response.status_code, 200)
        event = self.env['is.hse.compliance.event'].search([('event_id', '=', payload['event_id'])])
        self.assertEqual(event.state, 'new')
        self.assertFalse(self.env['is.hse.legal.document'].search([('code', '=', 'HSE_NO_AUTO_APPLY')]))

    def test_missing_event_id_is_rejected(self):
        response = self._post('/webhooks/hse-events', {}, self.secret, 'X-HSE-Signature')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'status': 'error', 'message': 'Missing event_id'})

        response = self._post('/webhooks/cems-telemetry', {}, self.cems_secret, 'X-CEMS-Signature')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'status': 'error', 'message': 'Missing event_id'})

    def test_hse_duplicate_event_has_deterministic_response(self):
        payload = {'event_id': 'evt_hse_duplicate_001'}
        first = self._post('/webhooks/hse-events', payload, self.secret, 'X-HSE-Signature')
        duplicate = self._post('/webhooks/hse-events', payload, self.secret, 'X-HSE-Signature')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json(), {
            'status': 'duplicate',
            'event_id': payload['event_id'],
            'record_id': first.json()['record_id'],
        })
        self.assertEqual(self.env['is.hse.compliance.event'].search_count([('event_id', '=', payload['event_id'])]), 1)

    def test_missing_or_invalid_hmac_creates_no_event(self):
        missing = {'event_id': 'evt_hse_missing_signature', 'event_type': 'hse.general_notice'}
        response = self._post('/webhooks/hse-events', missing, self.secret, None)
        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.env['is.hse.compliance.event'].search([('event_id', '=', missing['event_id'])]))

        invalid = {'event_id': 'evt_hse_invalid_signature', 'event_type': 'hse.general_notice'}
        response = self.url_open(
            '/webhooks/hse-events', data=json.dumps(invalid).encode(),
            headers={'Content-Type': 'application/json', 'X-HSE-Signature': 'sha256=invalid'},
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.env['is.hse.compliance.event'].search([('event_id', '=', invalid['event_id'])]))

    def test_cems_duplicate_event_is_not_replayed_or_auto_applied(self):
        self.env['is.hse.facility'].create({'name': 'CEMS facility', 'code': 'CEMS-001'})
        payload = {
            'event_id': 'evt_cems_duplicate_001',
            'facility_code': 'CEMS-001',
            'air_emissions': {
                'so2_mg_nm3': 501,
                'nox_mg_nm3': 0,
                'tsp_dust_mg_nm3': 0,
                'exhaust_flow_m3_h': 1000,
            },
            'wastewater': {'flow_rate_m3_h': 0},
        }
        Task = self.env['project.task']
        task_domain = [('name', 'ilike', '[CEMS ANOMALY] CEMS facility')]
        task_count = Task.search_count(task_domain)
        first = self._post('/webhooks/cems-telemetry', payload, self.cems_secret, 'X-CEMS-Signature')
        duplicate = self._post('/webhooks/cems-telemetry', payload, self.cems_secret, 'X-CEMS-Signature')
        event = self.env['is.hse.compliance.event'].search([('event_id', '=', payload['event_id'])])
        self.assertEqual(first.status_code, 200)
        self.assertEqual(event.state, 'new')
        self.assertEqual(Task.search_count(task_domain), task_count + 1)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json(), {
            'status': 'duplicate',
            'event_id': payload['event_id'],
            'record_id': event.id,
        })
        self.assertEqual(self.env['is.hse.compliance.event'].search_count([('event_id', '=', payload['event_id'])]), 1)

    def test_cems_does_not_mutate_audited_or_published_scorecard(self):
        facility = self.env['is.hse.facility'].create({'name': 'Locked CEMS facility', 'code': 'CEMS-LOCKED'})
        scorecard = self.env['is.esg.facility.scorecard'].create({
            'facility_id': facility.id,
            'reporting_year': 2026,
            'reporting_period': 'annual',
        })
        evidence = self.env['ir.attachment'].create({
            'name': 'locked-cems-evidence.pdf',
            'raw': b'governed evidence',
            'res_model': scorecard._name,
            'res_id': scorecard.id,
            'company_id': scorecard.company_id.id,
        })
        scorecard.write({
            'evidence_attachment_ids': [(4, evidence.id)],
            'evidence_summary': 'Verified CEMS evidence for the reporting period.',
            'source_url': 'https://evidence.example/locked-cems',
            'source_version': 'v1',
            'source_date': '2026-01-01',
        })
        auditor = new_test_user(
            self.env,
            login='hse-cems-esg-auditor',
            groups='insilos_esg_bridge.group_esg_bridge_manager',
        )
        scorecard.with_user(auditor).action_audit()
        payload = {
            'event_id': 'evt_cems_locked_scorecard',
            'facility_code': facility.code,
            'air_emissions': {
                'so2_mg_nm3': 10,
                'nox_mg_nm3': 0,
                'tsp_dust_mg_nm3': 0,
                'exhaust_flow_m3_h': 1000,
            },
            'wastewater': {'flow_rate_m3_h': 0},
        }
        response = self._post('/webhooks/cems-telemetry', payload, self.cems_secret, 'X-CEMS-Signature')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['esg_scorecard_updated'])
        self.assertEqual(scorecard.cems_so2_emissions_kg, 0.0)

    def test_cems_invalid_measurements_create_no_event_or_scorecard_update(self):
        facility = self.env['is.hse.facility'].create({'name': 'Validated CEMS facility', 'code': 'CEMS-VALIDATED'})
        scorecard = self.env['is.esg.facility.scorecard'].create({
            'facility_id': facility.id,
            'reporting_year': 2026,
            'reporting_period': 'annual',
        })
        payload = {
            'event_id': 'evt_cems_invalid_measurement',
            'facility_code': facility.code,
            'air_emissions': {
                'so2_mg_nm3': '1',
                'nox_mg_nm3': float('nan'),
                'tsp_dust_mg_nm3': [],
                'exhaust_flow_m3_h': -1,
            },
            'wastewater': {},
        }
        response = self._post('/webhooks/cems-telemetry', payload, self.cems_secret, 'X-CEMS-Signature')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['message'],
            'Invalid or missing CEMS measurements: so2_mg_nm3, nox_mg_nm3, tsp_dust_mg_nm3, exhaust_flow_m3_h, flow_rate_m3_h',
        )
        self.assertFalse(self.env['is.hse.compliance.event'].search([('event_id', '=', payload['event_id'])]))
        self.assertEqual(scorecard.cems_so2_emissions_kg, 0.0)
        self.assertEqual(scorecard.wastewater_discharged_m3, 0.0)

    def test_cems_unknown_facility_is_rejected_without_fallback(self):
        self.env['is.hse.facility'].create({'name': 'Existing facility', 'code': 'EXISTING'})
        response = self._post(
            '/webhooks/cems-telemetry', {'event_id': 'evt_cems_unknown_facility', 'facility_code': 'UNKNOWN', 'sensor_id': 'sensor-1'},
            self.cems_secret, 'X-CEMS-Signature',
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn('facility-specific tenant credentials', response.json()['message'])
        self.assertFalse(self.env['is.hse.compliance.event'].search([('event_id', '=', 'evt_cems_unknown_facility')]))

    def test_sync_logs_require_private_capability_and_are_immutable(self):
        SyncLog = self.env['is.hse.sync.log']
        with self.assertRaises(AccessError):
            SyncLog.sudo().create({
                'sync_channel': 'manual', 'status': 'success', 'message': 'fabricated audit',
                'payload_snapshot': '{"fabricated": true}',
            })
        with self.assertRaises(AccessError):
            SyncLog.sudo()._create_from_trusted_sync(
                [{'sync_channel': 'manual', 'status': 'success', 'message': 'fabricated audit'}], object(),
            )
        log = SyncLog.sudo()._create_from_trusted_sync(
            [{'sync_channel': 'webhook', 'status': 'success', 'message': 'verified audit'}],
            _SYNC_LOG_CREATE_CAPABILITY,
        )
        with self.assertRaises(AccessError):
            log.write({'message': 'changed'})
        with self.assertRaises(AccessError):
            log.unlink()
