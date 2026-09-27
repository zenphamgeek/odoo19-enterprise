# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HSEChemicalSubstance(models.Model):
    _name = 'is.hse.chemical.substance'
    _description = 'Chemical Substance Master & Inventory'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name, cas_number'

    name = fields.Char(string='Chemical Name', required=True, tracking=True)
    cas_number = fields.Char(string='CAS Registry Number', required=True, index=True, tracking=True,
                             help='Chemical Abstracts Service number (e.g. 67-64-1 for Acetone, 108-88-3 for Toluene)')
    un_number = fields.Char(string='UN Number', help='United Nations Dangerous Goods Number (e.g. UN 1090)')
    formula = fields.Char(string='Chemical Formula', help='E.g. C3H6O, H2SO4')
    
    hazard_classification = fields.Selection([
        ('conditional', 'Conditional Chemical (Hoa chat kinh doanh co dieu kien)'),
        ('restricted', 'Restricted Chemical (Hoa chat han che san xuat kinh doanh)'),
        ('prohibited', 'Prohibited Chemical (Hoa chat cam)'),
        ('declaration_required', 'Declaration Required (Hoa chat phai khai bao)'),
        ('hazardous_general', 'General Hazardous Chemical (Hoa chat nguy hiem thong thuong)'),
        ('non_hazardous', 'Non-Hazardous / Standard Commodity'),
    ], string='VN Chemical Law Classification', default='hazardous_general', required=True, tracking=True)

    ghs_signal_word = fields.Selection([
        ('danger', 'DANGER (Nguy hiểm)'),
        ('warning', 'WARNING (Cảnh báo)'),
        ('none', 'None'),
    ], string='GHS Signal Word', default='warning')

    ghs_flammable = fields.Boolean(string='Flammable (GHS02)')
    ghs_corrosive = fields.Boolean(string='Corrosive (GHS05)')
    ghs_toxic = fields.Boolean(string='Acute Toxicity (GHS06)')
    ghs_health_hazard = fields.Boolean(string='Health Hazard (GHS08)')
    ghs_environmental = fields.Boolean(string='Environmental Hazard (GHS09)')

    sds_ids = fields.One2many('is.hse.sds', 'substance_id', string='Safety Data Sheets (SDS)')
    sds_count = fields.Integer(string='SDS Count', compute='_compute_sds_count')
    oel_ids = fields.One2many('is.hse.oel', 'substance_id', string='Occupational Exposure Limits (OELs)')

    @api.constrains('cas_number')
    def _check_cas_unique(self):
        for sub in self:
            if sub.cas_number and self.search_count([('cas_number', '=', sub.cas_number), ('id', '!=', sub.id)]) > 0:
                raise ValidationError(_("CAS Registry Number '%s' must be unique!") % sub.cas_number)

    @api.depends('sds_ids')
    def _compute_sds_count(self):
        for sub in self:
            sub.sds_count = len(sub.sds_ids)


class HSESafetyDataSheet(models.Model):
    _name = 'is.hse.sds'
    _description = 'Safety Data Sheet (16 Sections)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'substance_id, issue_date desc, id desc'

    name = fields.Char(string='SDS Title', required=True)
    substance_id = fields.Many2one('is.hse.chemical.substance', string='Chemical Substance', required=True, ondelete='cascade')
    supplier_name = fields.Char(string='Manufacturer')
    issue_date = fields.Date(string='Issue Date', default=fields.Date.today)
    version = fields.Char(string='Version', default='1.0')

    # 16-Section Standard SDS Format
    sec1_identification = fields.Text(string='1. Chemical Identification & Supplier Details')
    sec2_hazard_identification = fields.Text(string='2. Hazard Identification (GHS)')
    sec3_composition = fields.Text(string='3. Composition &amp; Ingredients')
    sec4_first_aid = fields.Text(string='4. First-Aid Measures')
    sec5_fire_fighting = fields.Text(string='5. Fire-Fighting Measures')
    sec6_accidental_release = fields.Text(string='6. Accidental Release Measures')
    sec7_handling_storage = fields.Text(string='7. Handling & Storage Guidelines')
    sec8_exposure_controls = fields.Text(string='8. Exposure Controls & Personal Protection (PPE)')
    sec9_physical_chemical = fields.Text(string='9. Physical & Chemical Properties')
    sec10_stability_reactivity = fields.Text(string='10. Stability & Reactivity')
    sec11_toxicological = fields.Text(string='11. Toxicological Information')
    sec12_ecological = fields.Text(string='12. Ecological Information')
    sec13_disposal = fields.Text(string='13. Disposal Considerations')
    sec14_transport = fields.Text(string='14. Transport Information (ADR/IMDG/IATA)')
    sec15_regulatory = fields.Text(string='15. Regulatory Information (Vietnamese & International)')
    sec16_other = fields.Text(string='16. Other Information & References')


class HSEOccupationalExposureLimit(models.Model):
    _name = 'is.hse.oel'
    _description = 'Occupational Exposure Limit (OEL)'
    _order = 'substance_id, authority, id'

    substance_id = fields.Many2one('is.hse.chemical.substance', string='Substance', required=True, ondelete='cascade')
    authority = fields.Selection([
        ('BYT_QCVN03', 'Vietnam MOH — QCVN 03:2019/BYT (Bắt buộc)'),
        ('BTNMT_QCVN05', 'Vietnam MONRE — QCVN 05:2023/BTNMT (Không khí xung quanh)'),
        ('ACGIH_TLV', 'ACGIH — Threshold Limit Values (TLV)'),
        ('NIOSH_REL', 'NIOSH — Recommended Exposure Limits (REL)'),
        ('OSHA_PEL', 'OSHA — Permissible Exposure Limits (PEL)'),
    ], string='Authority Standard', required=True, default='BYT_QCVN03')

    twa_mg_m3 = fields.Float(string='TWA (8-hour) mg/m³', help='Time-Weighted Average concentration over 8-hour shift.')
    twa_ppm = fields.Float(string='TWA (8-hour) ppm')
    stel_mg_m3 = fields.Float(string='STEL (15-min) mg/m³', help='Short-Term Exposure Limit over 15 minutes.')
    stel_ppm = fields.Float(string='STEL (15-min) ppm')
    ceiling_mg_m3 = fields.Float(string='Ceiling Limit mg/m³')
    notes = fields.Char(string='Notations', help='E.g. Skin absorption (Da), Carcinogen (K), Sensitizer')
