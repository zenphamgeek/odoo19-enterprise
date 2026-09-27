# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LogisticsIDPCase(models.Model):
    _inherit = 'logistics.idp.case'

    chemical_dossier_id = fields.Many2one('is.chemical.compliance.dossier', string='Associated Chemical Compliance Dossier',
                                          tracking=True, index=True)
    chemical_dossier_count = fields.Integer(string='Chemical Dossiers', compute='_compute_chemical_dossier_count')

    def _compute_chemical_dossier_count(self):
        dossier_model = self.env['is.chemical.compliance.dossier']
        for case in self:
            count = dossier_model.search_count([('case_id', '=', case.id)])
            if not count and case.po_reference:
                count = dossier_model.search_count([('purchase_order_id.name', '=', case.po_reference)])
            case.chemical_dossier_count = count

    def action_generate_chemical_dossier_from_idp(self):
        """1-Click generate and evaluate Chemical Compliance Dossier from Logistics IDP Case."""
        self.ensure_one()
        dossier_model = self.env['is.chemical.compliance.dossier']

        # 1. Search existing dossier for this case
        existing = dossier_model.search([('case_id', '=', self.id)], limit=1)
        if existing:
            return {
                'name': _('Chemical Compliance Dossier'),
                'view_mode': 'form',
                'res_model': 'is.chemical.compliance.dossier',
                'res_id': existing.id,
                'type': 'ir.actions.act_window',
            }

        company = self.company_id or self.env.company
        self.check_access('write')

        # 2. Find a purchase order only inside the case company.
        po = False
        if self.po_reference:
            po = self.env['purchase.order'].search([
                ('name', '=', self.po_reference), ('company_id', '=', company.id),
            ], limit=1)

        # 3. Create a draft internal dossier. A supplier is taken from the scoped PO only.
        partner = po.partner_id if po else False
        if not partner and self.supplier_reference:
            partner = self.env['res.partner'].create({'name': self.supplier_reference})

        vals = {
            'name': f"DOSSIER-IDP-{self.name}",
            'case_id': self.id,
            'importer_company_id': self.company_id.id if self.company_id else self.env.company.id,
            'partner_id': partner.id if partner else False,
            'port_of_discharge': 'Cảng Cát Lái / Hải Phòng',
        }
        if po:
            vals['purchase_order_id'] = po.id
            if po.partner_id:
                vals['partner_id'] = po.partner_id.id

        dossier = dossier_model.create(vals)

        # 4. Populate lines from PO or material mappings
        if po and hasattr(po, '_auto_populate_chemical_dossier_lines'):
            po._auto_populate_chemical_dossier_lines(dossier)
        else:
            # Populate sample mapped products
            mappings = self.env['is.chemical.material.mapping'].search([
                ('company_id', '=', dossier.importer_company_id.id),
            ], limit=5)
            for m in mappings:
                prod = m.product_tmpl_id.product_variant_id if hasattr(m.product_tmpl_id, 'product_variant_id') else False
                self.env['is.chemical.compliance.dossier.line'].create({
                    'dossier_id': dossier.id,
                    'product_id': prod.id if prod else False,
                    'trade_name': m.commercial_name or m.product_tmpl_id.name,
                    'chemical_substance_id': m.chemical_substance_id.id,
                    'concentration_percentage': m.concentration_percentage or 100.0,
                    'purpose_of_use_id': m.purpose_of_use_id.id if m.purpose_of_use_id else False,
                    'net_weight_kg': 1000.0,
                })

        self.chemical_dossier_id = dossier.id
        self.message_post(
            body=_("Đã tự động khởi tạo Hồ sơ Tuân thủ Hóa chất <b>%s</b> từ Case IDP.") % (dossier.name),
            subtype_xmlid='mail.mt_note',
        )

        return {
            'name': _('Chemical Compliance Dossier'),
            'view_mode': 'form',
            'res_model': 'is.chemical.compliance.dossier',
            'res_id': dossier.id,
            'type': 'ir.actions.act_window',
        }
