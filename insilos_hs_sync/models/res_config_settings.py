# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class RsConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hermes_hs_api_url = fields.Char(
        string='Hermes HS Knowledge Engine API URL',
        config_parameter='insilos_hs_sync.hermes_api_url',
        default='http://127.0.0.1:8000',
        help='Base URL of the Hermes HS Knowledge Sync FastAPI service (e.g. http://127.0.0.1:8000 or https://hs-sync.hermes-agent.org).'
    )
    hermes_hs_webhook_secret = fields.Char(
        string='Hermes Webhook HMAC-SHA256 Secret',
        config_parameter='insilos_hs_sync.webhook_secret',
        help='Shared secret key used to compute and verify HMAC-SHA256 signatures on inbound webhook events.'
    )
    hermes_hs_auto_update_products = fields.Boolean(
        string='Auto-update Products on Tariff Change',
        config_parameter='insilos_hs_sync.auto_update_products',
        default=True,
        help='Automatically update import duty rates on matching Product Templates when a tariff event is received.'
    )
