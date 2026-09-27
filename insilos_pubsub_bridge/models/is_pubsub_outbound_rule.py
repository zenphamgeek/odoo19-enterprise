# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing terms.

import json
import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class PubSubOutboundRule(models.Model):
    _name = 'is.pubsub.outbound.rule'
    _description = 'Pub/Sub Outbound Event Rule (ERP Model → Webhook Push)'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.company, index=True,
    )

    # Trigger: Which ERP model & action triggers this outbound event
    model_name = fields.Char(string='Source Model', required=True,
                             help='Technical model name, e.g. crm.lead, purchase.order')
    trigger_action = fields.Selection([
        ('create', 'On Record Creation'),
        ('write', 'On Record Update'),
        ('unlink', 'On Record Deletion'),
        ('state_change', 'On Workflow State Change'),
    ], string='Trigger Action', default='create', required=True)

    # Optional field-level filter
    watched_fields = fields.Char(string='Watched Fields (comma-separated)',
                                 help='Only trigger on changes to these fields, e.g. stage_id,priority')
    state_field = fields.Char(string='State Field Name', default='state',
                              help='Field name to monitor for state_change trigger')
    state_from = fields.Char(string='From State', help='e.g. draft')
    state_to = fields.Char(string='To State', help='e.g. confirmed')

    # Destination configuration
    target_url = fields.Char(string='Destination Webhook URL', required=True,
                             help='e.g. https://partner-api.com/v1/webhook/erp-events')
    http_method = fields.Selection([('POST', 'POST'), ('PUT', 'PUT')], default='POST', required=True)
    auth_header = fields.Char(
        string='Authorization Header', help='e.g. Bearer eyJ...',
        groups='insilos_pubsub_bridge.group_pubsub_manager',
    )
    timeout_sec = fields.Integer(string='HTTP Timeout (s)', default=15)

    # Retry policy
    max_retries = fields.Integer(string='Max Retries', default=3)
    retry_delay_sec = fields.Integer(string='Retry Delay (s)', default=60,
                                     help='Seconds between retry attempts (exponential)')

    # Payload template
    payload_template = fields.Text(string='Payload Template (Jinja2)',
                                   help='Optional JSON template. Available vars: record, model, action, timestamp.',
                                   default='')
    include_full_record = fields.Boolean(string='Include Full Record Data', default=True,
                                         help='Automatically serialize record.read() into payload')

    # Stats
    execution_count = fields.Integer(string='Total Triggered', readonly=True, default=0)
    last_triggered_at = fields.Datetime(string='Last Triggered', readonly=True)

    outbound_event_ids = fields.One2many('is.pubsub.outbound.event', compute='_compute_outbound_events',
                                         string='Generated Events')
    outbound_event_count = fields.Integer(string='Events Count', compute='_compute_outbound_events')

    def _compute_outbound_events(self):
        OutEvent = self.env['is.pubsub.outbound.event']
        for rec in self:
            events = OutEvent.search([
                ('company_id', '=', rec.company_id.id),
                ('source_model', '=', rec.model_name),
                ('target_url', '=', rec.target_url),
            ])
            rec.outbound_event_ids = events
            rec.outbound_event_count = len(events)

    def fire_rule(self, record, action='create', changed_fields=None):
        """Fire this outbound rule for a given record.

        Args:
            record: The recordset that triggered the event.
            action: One of 'create', 'write', 'unlink', 'state_change'.
            changed_fields: List of field names that were changed (for write triggers).
        """
        self.ensure_one()

        # Check watched fields filter
        if self.watched_fields and changed_fields:
            watched = [f.strip() for f in self.watched_fields.split(',') if f.strip()]
            if not any(f in changed_fields for f in watched):
                return  # No watched field was changed

        # Build payload
        event_type = {
            'create': 'record.created',
            'write': 'record.updated',
            'unlink': 'record.deleted',
            'state_change': 'workflow.transition',
        }[action]
        payload = {
            'event_type': event_type,
            'model': self.model_name,
            'record_id': record.id if hasattr(record, 'id') else 0,
            'action': action,
            'timestamp': fields.Datetime.now().isoformat(),
            'source': 'insilos-erp',
        }

        if self.include_full_record and action != 'unlink':
            try:
                payload['data'] = record.read()[0] if record else {}
                # Clean non-serializable
                for key, val in list(payload['data'].items()):
                    if isinstance(val, bytes):
                        del payload['data'][key]
            except Exception:
                payload['data'] = {'id': record.id}

        self.sudo().write({
            'execution_count': self.execution_count + 1,
            'last_triggered_at': fields.Datetime.now(),
        })

        # Transactional outbox only; dispatcher performs HTTP after this transaction commits.
        self.env['is.pubsub.outbound.event'].sudo().publish_event(
            event_type=event_type,
            source_model=self.model_name,
            source_res_id=record.id if hasattr(record, 'id') else 0,
            payload_dict=payload,
            target_url=self.target_url,
            auth_header=self.auth_header,
            company_id=self.company_id.id,
        )

    def action_view_outbound_events(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Outbound Events for %s") % self.name,
            'res_model': 'is.pubsub.outbound.event',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('source_model', '=', self.model_name),
                ('target_url', '=', self.target_url),
            ],
            'target': 'current',
        }
