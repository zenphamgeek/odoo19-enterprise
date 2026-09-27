# -*- coding: utf-8 -*-
import ipaddress
import json
import logging
import socket
import time
from urllib.parse import urlsplit

import requests

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)


class PubSubOutboundEvent(models.Model):
    _name = 'is.pubsub.outbound.event'
    _description = 'Pub/Sub Transactional Outbox Event'
    _order = 'create_date desc'

    name = fields.Char(required=True, copy=False, index=True, default=lambda self: self.env['ir.sequence'].next_by_code('is.pubsub.outbound.event') or 'OUT-NEW')
    event_id = fields.Char(required=True, index=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('is.pubsub.outbound.event') or 'OUT-NEW')
    spec_version = fields.Char(required=True, default='1.0', copy=False)
    aggregate_id = fields.Char(index=True, copy=False)
    aggregate_version = fields.Integer(copy=False)
    schema_name = fields.Char(copy=False)
    schema_hash = fields.Char(copy=False)
    classification = fields.Char(copy=False)
    event_type = fields.Selection([('record.created', 'Record Created'), ('record.updated', 'Record Updated'), ('record.deleted', 'Record Deleted'), ('workflow.transition', 'Workflow Transition'), ('custom', 'Custom')], required=True, default='custom')
    source_model = fields.Char(required=True, index=True)
    source_res_id = fields.Integer()
    source_record_ref = fields.Char(compute='_compute_source_ref')
    payload = fields.Text(required=True, groups='insilos_pubsub_bridge.group_pubsub_manager')
    target_url = fields.Char(required=True)
    http_method = fields.Selection([('POST', 'POST'), ('PUT', 'PUT')], default='POST', required=True)
    auth_header = fields.Char(groups='insilos_pubsub_bridge.group_pubsub_manager')
    http_status = fields.Integer(readonly=True)
    response_body = fields.Text(readonly=True, groups='insilos_pubsub_bridge.group_pubsub_manager')
    latency_ms = fields.Float(readonly=True)
    state = fields.Selection([('pending', 'Pending'), ('processing', 'Processing'), ('sent', 'Sent'), ('retrying', 'Retrying'), ('dead', 'Dead')], default='pending', required=True, index=True)
    retry_count = fields.Integer(default=0, readonly=True)
    max_retries = fields.Integer(default=3)
    next_retry_at = fields.Datetime(readonly=True, index=True)
    lease_expires_at = fields.Datetime(readonly=True, index=True)
    correlation_id = fields.Char(index=True, copy=False)
    causation_id = fields.Char(index=True, copy=False)
    trace_id = fields.Char(index=True, copy=False)
    destination = fields.Char(compute='_compute_destination', store=True)
    error_class = fields.Char(readonly=True)
    error_message = fields.Text(readonly=True, groups='insilos_pubsub_bridge.group_pubsub_manager')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)

    _destination_event_unique = models.Constraint(
        'unique(company_id, target_url, event_id)',
        'Event may be delivered only once per company and destination.',
    )

    @api.depends('source_model', 'source_res_id')
    def _compute_source_ref(self):
        for rec in self:
            rec.source_record_ref = f'{rec.source_model},{rec.source_res_id}' if rec.source_res_id else False

    @api.depends('target_url')
    def _compute_destination(self):
        for rec in self:
            parsed = urlsplit(rec.target_url or '')
            rec.destination = parsed.hostname or False

    @api.constrains('target_url')
    def _check_target_url(self):
        for rec in self:
            parsed = urlsplit(rec.target_url or '')
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValidationError(_('Outbound URL must be an HTTPS URL without embedded credentials.'))
            try:
                addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
            except socket.gaierror as exc:
                raise ValidationError(_('Outbound URL hostname cannot be resolved.')) from exc
            if any(ipaddress.ip_address(address).is_private or ipaddress.ip_address(address).is_loopback or ipaddress.ip_address(address).is_link_local for address in addresses):
                raise ValidationError(_('Outbound URL must not resolve to a private network.'))

    def action_publish(self):
        self.ensure_one()
        if self.state not in ('pending', 'processing', 'retrying'):
            return
        self.write({'state': 'processing'})
        headers = {'Content-Type': 'application/json'}
        if self.auth_header:
            headers['Authorization'] = self.auth_header
        started = time.monotonic()
        try:
            response = requests.request(self.http_method, self.target_url, data=self.payload, headers=headers, timeout=15)
            latency = (time.monotonic() - started) * 1000
            if 200 <= response.status_code < 300 or response.status_code == 409:
                self.write({'state': 'sent', 'http_status': response.status_code, 'response_body': response.text[:2000], 'latency_ms': latency, 'lease_expires_at': False, 'error_class': False, 'error_message': False})
                return
            retryable = response.status_code in (408, 425, 429) or response.status_code >= 500
            retry_after = response.headers.get('Retry-After') if response.status_code == 429 else None
            self._delivery_failed(f'HTTP {response.status_code}: {response.text[:500]}', latency, response.status_code, retryable, retry_after)
        except requests.RequestException as exc:
            self._delivery_failed(str(exc), (time.monotonic() - started) * 1000, 0, True)

    def _delivery_failed(self, error, latency, status, retryable, retry_after=None):
        attempt = self.retry_count + 1
        dead = not retryable or attempt >= self.max_retries
        delay = min(3600, 30 * 2 ** (attempt - 1))
        if retry_after and retry_after.isdigit():
            delay = min(3600, int(retry_after))
        self.write({
            'state': 'dead' if dead else 'retrying', 'retry_count': attempt,
            'next_retry_at': False if dead else fields.Datetime.add(fields.Datetime.now(), seconds=delay),
            'lease_expires_at': False, 'http_status': status, 'latency_ms': latency,
            'error_class': 'terminal_http' if not retryable else ('network' if not status else 'retryable_http'),
            'error_message': error,
        })

    def action_retry(self):
        self.ensure_one()
        if not self.env.user.has_group('insilos_pubsub_bridge.group_pubsub_manager'):
            raise AccessError(_('Only Pub/Sub managers may retry deliveries.'))
        if self.state in ('retrying', 'dead'):
            self.write({'state': 'pending', 'next_retry_at': False})

    @api.model
    def _cron_dispatch_outbox(self, limit=20):
        self.env.cr.execute("""
            SELECT id FROM is_pubsub_outbound_event
             WHERE state = 'pending'
                OR (state = 'retrying' AND next_retry_at <= NOW())
                OR (state = 'processing' AND lease_expires_at <= NOW())
             ORDER BY id FOR UPDATE SKIP LOCKED LIMIT %s
        """, [limit])
        events = self.browse([row[0] for row in self.env.cr.fetchall()])
        if events:
            events.write({'state': 'processing', 'lease_expires_at': fields.Datetime.add(fields.Datetime.now(), minutes=2)})
        for event in events:
            event.action_publish()

    @api.model
    def publish_event(self, event_type, source_model, source_res_id, payload_dict, target_url, auth_header=False, company_id=False):
        envelope = {
            'spec_version': '1.0', 'event_id': payload_dict.get('event_id') or self.env['ir.sequence'].next_by_code('is.pubsub.outbound.event'),
            'event_type': event_type, 'source': source_model, 'producer': 'insilos_pubsub_bridge',
            'company_id': company_id or self.env.company.id, 'payload': payload_dict.get('payload', payload_dict),
            **{key: payload_dict[key] for key in (
                'correlation_id', 'causation_id', 'trace_id', 'aggregate_id', 'aggregate_version',
                'schema_name', 'schema_hash', 'classification') if payload_dict.get(key) is not None},
        }
        return self.create({
            'event_id': envelope['event_id'], 'spec_version': envelope['spec_version'],
            'event_type': event_type, 'source_model': source_model, 'source_res_id': source_res_id,
            'payload': json.dumps(envelope, ensure_ascii=False, default=str), 'target_url': target_url,
            'auth_header': auth_header, 'company_id': envelope['company_id'],
            **{key: envelope.get(key) for key in (
                'correlation_id', 'causation_id', 'trace_id', 'aggregate_id', 'aggregate_version',
                'schema_name', 'schema_hash', 'classification')},
        })

    def write(self, vals):
        protected = {
            'event_id', 'spec_version', 'event_type', 'source_model', 'source_res_id', 'payload',
            'target_url', 'http_method', 'company_id', 'correlation_id', 'causation_id', 'trace_id',
            'aggregate_id', 'aggregate_version', 'schema_name', 'schema_hash', 'classification',
        }
        if protected & set(vals) and any(record.id for record in self):
            raise AccessError(_('Outbound audit identity, destination and payload are immutable.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.is_superuser():
            raise AccessError(_('Outbound delivery records are immutable.'))
        return super().unlink()
