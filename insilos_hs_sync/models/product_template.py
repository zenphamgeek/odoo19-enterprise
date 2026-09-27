# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hs_code_customs = fields.Char(
        string='Customs HS Code (8-digit)',
        index=True,
        help='Authoritative 8-digit Vietnam HS Code synchronized with Customs Tariff.'
    )
    import_duty_rate = fields.Float(
        string='Preferential Import Duty Rate (%)',
        digits=(5, 2),
        help='Preferential import duty rate applied to this HS code.'
    )
    vat_rate = fields.Float(
        string='Customs VAT Rate (%)',
        digits=(5, 2),
        help='Value Added Tax rate for import customs declaration.'
    )
    specialized_management_notes = fields.Text(
        string='Specialized Management',
        help='Specialized inspection / permit regulations from relevant Ministries.'
    )
    hs_last_synced = fields.Datetime(string='HS Last Synchronized')
    customs_ruling_count = fields.Integer(
        string='Customs Rulings Count',
        compute='_compute_customs_ruling_count'
    )

    def _compute_customs_ruling_count(self):
        ruling_model = self.env['is.customs.ruling']
        for rec in self:
            if rec.hs_code_customs:
                rec.customs_ruling_count = ruling_model.search_count([('hs_code', '=', rec.hs_code_customs)])
            else:
                rec.customs_ruling_count = 0

    def action_view_customs_rulings(self):
        self.ensure_one()
        if not self.hs_code_customs:
            raise UserError(_("Please assign a Customs HS Code (8-digit) to this product first."))
        action = self.env['ir.actions.act_window']._for_xml_id('insilos_hs_sync.action_is_customs_ruling')
        action['domain'] = [('hs_code', '=', self.hs_code_customs)]
        action['context'] = {'default_hs_code': self.hs_code_customs}
        return action

    def action_fetch_tariff_from_hermes(self):
        self.ensure_one()
        if not self.hs_code_customs:
            raise UserError(_("Please provide a Customs HS Code (8-digit) before querying the Hermes Tariff Engine."))
        client = self.env['is.hs.sync.service'] if 'is.hs.sync.service' in self.env else None
        
        # Look up locally in is.hs.tariff first
        tariff = self.env['is.hs.tariff'].search([('hs_code', '=', self.hs_code_customs)], limit=1)
        if tariff:
            self.write({
                'import_duty_rate': tariff.import_duty_rate,
                'vat_rate': tariff.vat_rate,
                'specialized_management_notes': tariff.specialized_management_notes,
                'hs_last_synced': fields.Datetime.now(),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Tariff Updated"),
                    'message': _("Product tariff rates updated from local HS Tariff catalog: %s", self.hs_code_customs),
                    'sticky': False,
                    'type': 'success',
                }
            }

        # Otherwise query Hermes REST API service
        from ..services.hermes_client import HermesHSClient
        client_service = HermesHSClient(self.env)
        result = client_service.get_tariff_info(self.hs_code_customs)
        if result and result.get('status') == 'success':
            data = result.get('data', {})
            vals = {
                'hs_last_synced': fields.Datetime.now(),
            }
            if data.get('import_duty_rate') is not None:
                vals['import_duty_rate'] = data.get('import_duty_rate')
            if data.get('vat_rate') is not None:
                vals['vat_rate'] = data.get('vat_rate')
            if data.get('specialized_management_notes'):
                vals['specialized_management_notes'] = data.get('specialized_management_notes')
            self.write(vals)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Hermes Tariff Synchronized"),
                    'message': _("Successfully fetched latest tariff rates for HS Code %s from Hermes Hub.", self.hs_code_customs),
                    'sticky': False,
                    'type': 'success',
                }
            }
        else:
            msg = result.get('message') if result else _("No tariff found for HS Code %s", self.hs_code_customs)
            raise UserError(msg)
