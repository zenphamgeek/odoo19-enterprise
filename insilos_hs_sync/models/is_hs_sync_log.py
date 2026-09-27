# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IsHsSyncLog(models.Model):
    _name = 'is.hs.sync.log'
    _description = 'HS Knowledge Sync Audit Log'
    _order = 'timestamp desc, id desc'

    event_id = fields.Char(string='Event ID', index=True)
    event_type = fields.Char(string='Event Type', index=True)
    direction = fields.Selection([
        ('inbound_webhook', 'Inbound Webhook (from Hermes)'),
        ('outbound_api', 'Outbound REST Query (to Hermes)'),
    ], string='Direction', default='inbound_webhook', required=True, index=True)
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('ignored', 'Ignored'),
    ], string='Status', default='success', required=True, index=True)
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True, index=True)
    payload_summary = fields.Text(string='Payload Summary')
    raw_payload = fields.Text(string='Raw Payload JSON')
    error_message = fields.Text(string='Error Message')
    remote_ip = fields.Char(string='Remote IP')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
