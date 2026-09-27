# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


_SYNC_LOG_CREATE_CAPABILITY = object()


class HSESyncLog(models.Model):
    _name = 'is.hse.sync.log'
    _description = 'HSE Knowledge Synchronization Log'
    _order = 'create_date desc, id desc'

    sync_channel = fields.Selection([
        ('webhook', 'Inbound Webhook'),
        ('on_demand_api', 'On-Demand API Query'),
        ('scheduled_cron', 'Scheduled Cron Sync'),
        ('manual', 'Manual User Action'),
    ], string='Sync Channel', required=True, default='webhook')

    event_type = fields.Char(string='Event Type')
    status = fields.Selection([
        ('success', 'Success'),
        ('warning', 'Warning / Partial'),
        ('error', 'Error / Failure'),
    ], string='Status', required=True, default='success')

    message = fields.Text(string='Log Details')
    items_processed = fields.Integer(string='Items Processed', default=1)
    payload_snapshot = fields.Text(string='Payload Snapshot')

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('_hse_sync_log_create') is not _SYNC_LOG_CREATE_CAPABILITY:
            raise AccessError(_("HSE synchronization logs can only be recorded by trusted synchronization flows."))
        return super().create(vals_list)

    def _create_from_trusted_sync(self, vals_list, capability):
        if capability is not _SYNC_LOG_CREATE_CAPABILITY:
            raise AccessError(_("HSE synchronization logs require trusted synchronization capability."))
        return self.with_context(_hse_sync_log_create=_SYNC_LOG_CREATE_CAPABILITY).create(vals_list)

    def write(self, vals):
        raise AccessError(_("HSE synchronization logs are immutable."))

    def unlink(self):
        raise AccessError(_("HSE synchronization logs are immutable."))
