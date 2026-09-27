# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HSEProductPermit(models.Model):
    _name = 'is.hse.product.permit'
    _description = 'HSE Chemical & Product Compliance Permit / Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date asc, id desc'

    name = fields.Char(string='Permit Title', required=True, tracking=True)
    permit_number = fields.Char(string='Permit Number', required=True, index=True, tracking=True,
                                help='Official registration or permit number (e.g. 45/GP-BCT, 128/GCN-SCT)')
    
    permit_type = fields.Selection([
        ('conditional_cert', 'Conditional Chemical Certificate (GCN du dieu kien SX/KD hoa chat)'),
        ('restricted_license', 'Restricted Chemical License (Giay phep SX/KD hoa chat han che)'),
        ('import_declaration', 'Import Chemical Declaration (Xac nhan khai bao hoa chat nhap khau)'),
        ('transport_permit', 'Dangerous Goods Transport Permit (Giay phep van chuyen hang nguy hiem)'),
        ('coa_quality', 'Certificate of Analysis / Quality (Chung nhan chat luong CoA)'),
        ('sds_compliance', 'SDS Compliance Certification (Chung nhan phieu an toan hoa chat)'),
        ('environmental_permit', 'Specialized Environmental Permit (Giay phep chuyen nganh moi truong)'),
        ('other', 'Other Regulatory Permit / Certificate'),
    ], string='Permit Category', required=True, default='conditional_cert', tracking=True)

    issuing_authority = fields.Char(string='Issuing Authority', tracking=True,
                                    help='E.g. Ministry of Industry and Trade (BCT), Vietnam Chemicals Agency, Department of Industry and Trade (SCT)')
    
    issue_date = fields.Date(string='Issue Date', default=fields.Date.today, tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    is_perpetual = fields.Boolean(string='Perpetual (No Expiry)', default=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('valid', 'Active & Valid (Con hieu luc)'),
        ('expiring_soon', 'Expiring Soon (Sap het han < 30 ngay)'),
        ('expired', 'Expired (Het hieu luc)'),
        ('revoked', 'Revoked / Suspended (Thu hoi)'),
    ], string='Status', compute='_compute_state', store=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    chemical_substance_id = fields.Many2one('is.hse.chemical.substance', string='Related Chemical Substance')
    product_template_ids = fields.Many2many('product.template', 'product_template_hse_permit_rel',
                                            'permit_id', 'product_tmpl_id', string='Covered Products')
    product_count = fields.Integer(string='Products Count', compute='_compute_product_count')

    attachment_ids = fields.Many2many('ir.attachment', 'is_hse_product_permit_attachment_rel',
                                      'permit_id', 'attachment_id', string='Attached Documents')
    
    conditions_summary = fields.Text(string='Permit Conditions & Scope of Operations')
    notes = fields.Text(string='Internal Compliance Remarks')

    @api.model_create_multi
    def create(self, vals_list):
        if any('state' in vals and vals['state'] != 'draft' for vals in vals_list):
            raise UserError(_('Permit status is internal-only and cannot assert external authority.'))
        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals:
            raise UserError(_('Permit status is internal-only and cannot assert external authority.'))
        return super().write(vals)

    @api.depends('is_perpetual', 'expiry_date')
    def _compute_state(self):
        for rec in self:
            # ponytail: remain internal draft until an independently verified authority source exists.
            rec.state = 'draft'

    @api.depends('product_template_ids')
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_template_ids)

    @api.constrains('company_id', 'attachment_ids')
    def _check_attachment_company(self):
        for permit in self:
            if permit.attachment_ids.filtered(
                lambda attachment: attachment.company_id != permit.company_id
            ):
                raise ValidationError(_('Permit attachments must belong to the permit company.'))

    @api.constrains('permit_number', 'company_id')
    def _check_permit_number_unique(self):
        for rec in self:
            if rec.permit_number and self.search_count([('permit_number', '=', rec.permit_number), ('company_id', '=', rec.company_id.id), ('id', '!=', rec.id)]) > 0:
                raise ValidationError(_("Permit number '%s' must be unique per company!") % rec.permit_number)
