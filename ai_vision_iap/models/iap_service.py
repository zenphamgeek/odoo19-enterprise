# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class IapService(models.Model):
    _inherit = 'iap.service'

    credit_cost = fields.Float(
        string='Credit Cost',
        default=1.0,
        help="Credit amount charged per service invocation. 0 = free.",
    )

    @api.model
    def cost_for(self, technical_name, default=1.0):
        service = self.search([('technical_name', '=', technical_name)], limit=1)
        if not service:
            return default
        return service.credit_cost
