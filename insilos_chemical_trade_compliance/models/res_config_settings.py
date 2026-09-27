# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nsw_api_endpoint = fields.Char(
        string='National Single Window (NSW) Gateway Endpoint',
        config_parameter='insilos_chemical_trade_compliance.nsw_api_endpoint',
        default='https://vnsw.gov.vn/api/v2/bct/chemicals',
        help='Gateway endpoint URL for submitting electronic dossiers to the National Single Window portal.'
    )

    nsw_auto_evaluate_po = fields.Boolean(
        string='Auto-Evaluate PO Chemical Obligations',
        config_parameter='insilos_chemical_trade_compliance.nsw_auto_evaluate_po',
        default=True,
        help='Automatically evaluate regulatory chemical rules when Purchase Orders are confirmed.'
    )

    chemical_quota_warning_pct = fields.Float(
        string='Permit Quota Warning Threshold (%)',
        config_parameter='insilos_chemical_trade_compliance.chemical_quota_warning_pct',
        default=10.0,
        help='Trigger warning alerts when remaining permit quota falls below this percentage.'
    )
