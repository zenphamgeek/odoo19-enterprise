# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class PubSubForwardLog(models.Model):
    _name = 'is.pubsub.forward.log'
    _description = 'Pub/Sub Call Forwarding Audit & HTTP Delivery Log'
    _order = 'create_date desc'

    rule_id = fields.Many2one('is.pubsub.automation.rule', string='Automation Rule', required=True, ondelete='cascade', index=True)
    event_log_id = fields.Many2one('is.pubsub.event.log', string='Source Event', required=True, ondelete='cascade', index=True)
    forward_url = fields.Char(string='Target URL', required=True)
    http_status = fields.Integer(string='HTTP Status Code')
    latency_ms = fields.Float(string='Latency (ms)')
    state = fields.Selection([
        ('success', 'Delivered (2xx)'),
        ('failed', 'Delivery Failed'),
    ], string='Delivery Status', default='success', required=True, index=True)

    response_body = fields.Text(string='HTTP Response')
    error_message = fields.Text(string='Error Diagnostics')
