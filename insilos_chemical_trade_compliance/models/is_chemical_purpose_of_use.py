# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ChemicalPurposeOfUse(models.Model):
    _name = 'is.chemical.purpose.of.use'
    _description = 'Chemical Purpose of Use & Maximum Consumption Quota'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(string='Purpose of Use', required=True, tracking=True)
    code = fields.Char(string='Purpose Code', index=True)
    description = fields.Text(string='Detailed Technical Description')
    
    industry_category = fields.Selection([
        ('electronics', 'Electronics & Semiconductor Manufacturing (Điện tử / Bán dẫn)'),
        ('industrial_paint', 'Paints, Inks & Coating Formulation (Sơn, Mực in & Phủ bề mặt)'),
        ('textile_dyeing', 'Textile Dyeing & Finishing (Dệt nhuộm & Xử lý sợi)'),
        ('water_treatment', 'Industrial Wastewater Treatment (Xử lý nước thải công nghiệp)'),
        ('laboratory_rd', 'Laboratory Testing & R&D (Thí nghiệm & Nghiên cứu R&D)'),
        ('pharmaceutical', 'Pharmaceutical & Fine Chemicals (Dược phẩm & Hóa chất tinh khiết)'),
        ('general_manufacturing', 'General Industrial Manufacturing (Sản xuất công nghiệp chung)'),
        ('commercial_trading', 'Commercial Trading / Distribution (Kinh doanh thương mại)'),
    ], string='Industry Sector', default='general_manufacturing', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    facility_id = fields.Many2one('is.hse.facility', string='Operating Facility')

    max_annual_demand_kg = fields.Float(string='Maximum Annual Demand (kg/year)', default=0.0,
                                        help='Approved maximum annual consumption volume for this purpose.')
    standard_loss_rate_pct = fields.Float(string='Standard Loss Rate (%)', default=1.0,
                                          help='Expected industrial loss rate during processing/manufacturing.')

    active = fields.Boolean(string='Active', default=True)

    @api.constrains('company_id', 'facility_id')
    def _check_facility_company(self):
        for purpose in self:
            if purpose.facility_id and purpose.facility_id.company_id != purpose.company_id:
                raise ValidationError(_('Facility must belong to the purpose company.'))
