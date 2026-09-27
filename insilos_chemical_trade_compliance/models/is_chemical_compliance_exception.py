# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ChemicalComplianceException(models.Model):
    _name = 'is.chemical.compliance.exception'
    _description = 'Chemical Trade Compliance Data Exception & Anomaly'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'severity desc, id desc'

    name = fields.Char(string='Exception Title', required=True, tracking=True)
    
    exception_type = fields.Selection([
        ('missing_mapping', '1. Material Not Mapped to Chemical Master (Chưa mapping Material - Hóa chất)'),
        ('missing_uom_ratio', '2. Missing UoM to KG Conversion Factor (Thiếu hệ số quy đổi ra KG)'),
        ('missing_purpose_of_use', '3. Missing Purpose of Use (Thiếu Mục đích sử dụng)'),
        ('missing_sds', '4. Missing SDS 16-Section / MSDS (Thiếu Phiếu an toàn hóa chất)'),
        ('unverified_vendor', '5. Unverified Chemical Vendor / Exporter (Nhà cung cấp chưa thẩm định)'),
        ('prohibited_chemical', '6. Prohibited Chemical Detected (Phát hiện Hóa chất CẤM Phụ lục III)'),
    ], string='Exception Type', required=True, tracking=True)

    severity = fields.Selection([
        ('critical', 'Critical (Chặn lập hồ sơ / Block)'),
        ('warning', 'Warning (Cảnh báo cần bổ sung)'),
        ('info', 'Info (Thông tin lưu ý)'),
    ], string='Severity Level', default='warning', required=True, tracking=True)

    product_tmpl_id = fields.Many2one('product.template', string='ERP Material', index=True)
    chemical_substance_id = fields.Many2one('is.hse.chemical.substance', string='Chemical Substance Master')
    dossier_id = fields.Many2one('is.chemical.compliance.dossier', string='Associated Dossier', index=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Associated Purchase Order')

    description = fields.Text(string='Anomaly Details & Missing Fields')
    resolution_guide = fields.Text(string='Recommended Action for Logistics Officer')

    state = fields.Selection([
        ('open', 'Open / Action Required (Cần xử lý)'),
        ('resolved', 'Resolved (Đã khắc phục)'),
        ('ignored', 'Acknowledged / Ignored (Đã xác nhận bỏ qua)'),
    ], string='Status', default='open', tracking=True)

    resolved_by = fields.Many2one('res.users', string='Resolved By')
    resolved_date = fields.Date(string='Resolution Date')

    def action_resolve_exception(self):
        self.ensure_one()
        self.state = 'resolved'
        self.resolved_by = self.env.user
        self.resolved_date = fields.Date.today()
        return True

    def action_quick_fix_mapping(self):
        """
        Mở màn hình Mapping tương ứng hoặc khởi tạo Mapping mới điền sẵn thông tin để người dùng hoàn thiện ngay.
        """
        self.ensure_one()
        company = self.dossier_id.importer_company_id or self.env.company
        mapping = self.env['is.chemical.material.mapping'].search([
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('company_id', '=', company.id),
        ], limit=1)

        if mapping:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Sửa Mapping Material - Chemical'),
                'res_model': 'is.chemical.material.mapping',
                'res_id': mapping.id,
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Tạo Mapping Mới cho Material'),
                'res_model': 'is.chemical.material.mapping',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_product_tmpl_id': self.product_tmpl_id.id,
                    'default_commercial_product_name': self.product_tmpl_id.name,
                    'default_chemical_substance_id': self.chemical_substance_id.id if self.chemical_substance_id else False,
                    'default_uom_to_kg_ratio': 1.0,
                }
            }

    @api.model
    def run_compliance_data_check(self, product_tmpl_ids=None, dossier=None):
        """
        Scans products or a specific dossier for compliance data completeness.
        Creates exception records for any missing mappings, UoM ratios, or SDS.
        """
        exceptions_created = self.browse()
        Mapping = self.env['is.chemical.material.mapping']
        
        products = product_tmpl_ids or (dossier.line_ids.mapped('product_id.product_tmpl_id') if dossier else self.env['product.template'].search([('is_hazardous_chemical', '=', True)]))

        for prod in products:
            # 1. Check if mapping exists
            mapping = Mapping.search([('product_tmpl_id', '=', prod.id)], limit=1)
            if not mapping and (prod.is_hazardous_chemical or prod.chemical_substance_id):
                exc = self.create({
                    'name': f"Missing Mapping: {prod.name}",
                    'exception_type': 'missing_mapping',
                    'severity': 'critical',
                    'product_tmpl_id': prod.id,
                    'chemical_substance_id': prod.chemical_substance_id.id if prod.chemical_substance_id else False,
                    'dossier_id': dossier.id if dossier else False,
                    'description': f"Material '{prod.name}' is flagged as hazardous chemical but has no Material-Chemical Mapping entry.",
                    'resolution_guide': "Navigate to Chemical Trade Compliance > Material-Chemical Mapping and create a mapping entry with CAS and conversion ratio.",
                })
                exceptions_created |= exc
            elif mapping:
                # 2. Check UoM conversion ratio
                if mapping.uom_to_kg_ratio <= 0:
                    exc = self.create({
                        'name': f"Invalid UoM Ratio: {prod.name}",
                        'exception_type': 'missing_uom_ratio',
                        'severity': 'critical',
                        'product_tmpl_id': prod.id,
                        'chemical_substance_id': mapping.chemical_substance_id.id,
                        'dossier_id': dossier.id if dossier else False,
                        'description': f"Mapping for '{prod.name}' has invalid UoM to KG ratio ({mapping.uom_to_kg_ratio}).",
                        'resolution_guide': "Set a valid conversion ratio (> 0) to convert operational UoM to kg.",
                    })
                    exceptions_created |= exc

                # 3. Check Purpose of Use
                if not mapping.purpose_of_use_id:
                    exc = self.create({
                        'name': f"Missing Purpose of Use: {prod.name}",
                        'exception_type': 'missing_purpose_of_use',
                        'severity': 'warning',
                        'product_tmpl_id': prod.id,
                        'chemical_substance_id': mapping.chemical_substance_id.id,
                        'dossier_id': dossier.id if dossier else False,
                        'description': f"Material '{prod.name}' has no defined Purpose of Use (Mục đích sử dụng).",
                        'resolution_guide': "Assign a Purpose of Use to ensure smooth licensing application.",
                    })
                    exceptions_created |= exc

                # 4. Check SDS
                if mapping.chemical_substance_id and not mapping.chemical_substance_id.sds_ids:
                    exc = self.create({
                        'name': f"Missing SDS 16-Section: {mapping.chemical_substance_id.name}",
                        'exception_type': 'missing_sds',
                        'severity': 'warning',
                        'product_tmpl_id': prod.id,
                        'chemical_substance_id': mapping.chemical_substance_id.id,
                        'dossier_id': dossier.id if dossier else False,
                        'description': f"Chemical '{mapping.chemical_substance_id.name}' has no active 16-section SDS uploaded.",
                        'resolution_guide': "Upload the Vietnamese Safety Data Sheet (SDS) in Chemicals & SDS.",
                    })
                    exceptions_created |= exc

        return exceptions_created
