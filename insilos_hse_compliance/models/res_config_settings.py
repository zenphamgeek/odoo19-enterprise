# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hse_knowledge_endpoint = fields.Char(
        string='HSE Knowledge Service Endpoint',
        config_parameter='insilos_hse_compliance.hse_knowledge_endpoint',
        default='https://hse.insilos.com',
        help='Base URL for Deterministic HSE Knowledge API (e.g. https://hse.insilos.com or http://localhost:8000)'
    )
    hse_api_key = fields.Char(
        string='HSE API Key',
        config_parameter='insilos_hse_compliance.hse_api_key',
        help='Authentication token for querying the HSE Knowledge Engine.'
    )
    hse_webhook_secret = fields.Char(
        string='HSE Inbound Webhook HMAC Secret',
        config_parameter='insilos_hse_compliance.hse_webhook_secret',
        default='sec_hse_2026',
        help='Shared secret key used to verify HMAC-SHA256 signatures on inbound HSE webhooks.'
    )
