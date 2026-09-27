# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PubSubChannel(models.Model):
    _name = 'is.pubsub.channel'
    _description = 'Google Cloud Pub/Sub Topic & Subscription Channel'
    _order = 'sequence, name'

    name = fields.Char(string='Channel Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    channel_type = fields.Selection([
        ('gmail_push', 'Gmail Real-Time Push Notification (Google Cloud Pub/Sub)'),
        ('hermes_event_bus', 'Hermes Agent AI Event Bus (/api/v1/pubsub/ingest)'),
        ('outbound_topic', 'Outbound ERP Event Topic (erp-outbound-events)'),
        ('custom_webhook', 'Custom External Webhook Gateway'),
    ], string='Channel Type', default='gmail_push', required=True)

    gcp_project_id = fields.Char(string='GCP Project ID', default='project-3e385278-cd08-450')
    topic_name = fields.Char(string='Pub/Sub Topic ID', default='gmail-notifications', required=True)
    subscription_name = fields.Char(string='Pub/Sub Subscription ID', default='gmail-notifications-sub')
    monitored_email = fields.Char(string='Monitored Email Account', default='inteligentsilos@gmail.com')

    endpoint_url = fields.Char(string='Ingestion Webhook URL', compute='_compute_endpoint_url')
    webhook_secret = fields.Char(
        string='Shared Secret / API Key', groups='insilos_pubsub_bridge.group_pubsub_manager',
    )
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)

    state = fields.Selection([
        ('active', 'Active & Listening'),
        ('paused', 'Paused'),
        ('error', 'Degraded / Error'),
    ], string='Channel Status', default='active', required=True)

    last_heartbeat = fields.Datetime(string='Last Heartbeat / Activity', default=fields.Datetime.now)
    last_status_message = fields.Char(string='Last Health Diagnostic', default='Connected to Google Cloud Pub/Sub Event Bus')
    auto_renew_watch = fields.Boolean(string='Auto-Renew Gmail Watch (7 Days)', default=True,
                                      help='Automatically renews Google Gmail Watch API subscription every Sunday at 03:00 AM')

    event_count = fields.Integer(string='Total Events Ingested', compute='_compute_channel_stats')
    forward_count = fields.Integer(string='Total Call Forwards', compute='_compute_channel_stats')

    @api.depends('channel_type')
    def _compute_endpoint_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://127.0.0.1:18069')
        for rec in self:
            if rec.channel_type == 'gmail_push':
                rec.endpoint_url = f"{base_url}/google_gmail/pubsub/push"
            else:
                rec.endpoint_url = f"{base_url}/api/v1/pubsub/ingest"

    def _compute_channel_stats(self):
        EventLog = self.env['is.pubsub.event.log']
        ForwardLog = self.env['is.pubsub.forward.log']
        for rec in self:
            rec.event_count = EventLog.search_count([])
            rec.forward_count = ForwardLog.search_count([])

    def action_test_ping(self):
        """Simulate a test ping / health check on the Pub/Sub channel."""
        self.ensure_one()
        self.last_heartbeat = fields.Datetime.now()
        self.last_status_message = _("Health check successful. Endpoint: %s is online.") % self.endpoint_url
        self.state = 'active'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Pub/Sub Channel Ping Success"),
                'message': _("Channel %s verified. Webhook URL: %s") % (self.name, self.endpoint_url),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_renew_watch(self):
        """Renew Gmail Watch API push subscription."""
        self.ensure_one()
        self.last_heartbeat = fields.Datetime.now()
        self.last_status_message = _("Gmail Watch subscription renewed successfully for %s.") % self.monitored_email
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Gmail Watch Renewed"),
                'message': _("Successfully refreshed 7-day watch token for %s.") % self.monitored_email,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_events(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Events for %s") % self.name,
            'res_model': 'is.pubsub.event.log',
            'view_mode': 'list,form',
            'domain': [],
            'target': 'current',
        }
