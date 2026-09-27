# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


_MAPPING_VERIFICATION_CAPABILITY = object()


class ChemicalMaterialMapping(models.Model):
    _name = 'is.chemical.material.mapping'
    _description = 'Multi-tier Material to Chemical & Regulatory Mapping'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'product_tmpl_id asc, id desc'

    name = fields.Char(string='Mapping Reference', compute='_compute_name', store=True)
    product_tmpl_id = fields.Many2one('product.template', string='ERP Material', required=True, index=True, tracking=True)
    default_code = fields.Char(related='product_tmpl_id.default_code', string='Material Internal Reference', store=True)
    
    commercial_name = fields.Char(string='Commercial Product Name', tracking=True)
    chemical_substance_id = fields.Many2one('is.hse.chemical.substance', string='Chemical Substance Master', required=True, tracking=True)
    cas_number = fields.Char(related='chemical_substance_id.cas_number', string='CAS Registry No.', store=True)
    
    purpose_of_use_id = fields.Many2one('is.chemical.purpose.of.use', string='Primary Purpose of Use', tracking=True)
    
    uom_id = fields.Many2one('uom.uom', string='Operational Unit of Measure', default=lambda self: self.env.ref('uom.product_uom_kgm', raise_if_not_found=False))
    uom_to_kg_ratio = fields.Float(string='UoM to KG Conversion Factor', default=1.0, required=True,
                                   help='Multiplier to convert 1 operational UoM into kilograms (kg) for regulatory reporting.')

    concentration_percentage = fields.Float(string='Active Substance Concentration (% wt)', default=100.0,
                                            help='Concentration percentage of the primary hazardous chemical in this material.')

    regulatory_rule_ids = fields.Many2many('is.chemical.regulatory.rule', 'chem_mat_mapping_rule_rel',
                                           'mapping_id', 'rule_id', string='Applicable Regulatory Lists (2026 Framework)')

    is_verified = fields.Boolean(string='Internal Mapping Review Complete', default=False, tracking=True)
    verified_by = fields.Many2one('res.users', string='Internal Reviewer')
    verified_date = fields.Date(string='Internal Review Date')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    notes = fields.Text(string='Mapping Formulation & Compliance Notes')

    _verification_fields = {
        'product_tmpl_id', 'commercial_name', 'chemical_substance_id', 'purpose_of_use_id',
        'uom_id', 'uom_to_kg_ratio', 'concentration_percentage', 'regulatory_rule_ids',
        'company_id', 'notes', 'is_verified', 'verified_by', 'verified_date',
    }

    @api.model_create_multi
    def create(self, vals_list):
        if any({'is_verified', 'verified_by', 'verified_date'} & vals.keys() for vals in vals_list):
            raise AccessError(_('Mapping verification metadata is managed by the verification action.'))
        return super().create(vals_list)

    def write(self, vals):
        if ({'is_verified', 'verified_by', 'verified_date'} & vals.keys()
                and self.env.context.get('_chemical_mapping_verification') is not _MAPPING_VERIFICATION_CAPABILITY):
            raise AccessError(_('Mapping verification metadata is managed by the verification action.'))
        if self.filtered('is_verified') and self._verification_fields & vals.keys():
            raise ValidationError(_('Verified mappings are immutable; create a replacement mapping for a new review.'))
        return super().write(vals)

    @api.constrains('company_id', 'purpose_of_use_id')
    def _check_purpose_company(self):
        for mapping in self:
            if mapping.purpose_of_use_id and mapping.purpose_of_use_id.company_id != mapping.company_id:
                raise ValidationError(_('Purpose must belong to the mapping company.'))

    @api.depends('product_tmpl_id.name', 'chemical_substance_id.name')
    def _compute_name(self):
        for rec in self:
            p_name = rec.product_tmpl_id.name if rec.product_tmpl_id else 'MATERIAL'
            c_name = rec.chemical_substance_id.name if rec.chemical_substance_id else 'CHEMICAL'
            rec.name = f"MAP: {p_name} ↔ {c_name}"

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.commercial_name = self.product_tmpl_id.name
            if self.product_tmpl_id.chemical_substance_id:
                self.chemical_substance_id = self.product_tmpl_id.chemical_substance_id
            if self.product_tmpl_id.uom_id:
                self.uom_id = self.product_tmpl_id.uom_id

    def action_verify_mapping(self):
        self.ensure_one()
        if not self.env.user.has_group('insilos_chemical_trade_compliance.group_chemical_compliance_manager'):
            raise AccessError(_('Only a Chemical Compliance Manager can complete an internal mapping review.'))
        if self.create_uid == self.env.user:
            raise ValidationError(_('A different Chemical Compliance Manager must review this mapping.'))
        if self.is_verified:
            raise ValidationError(_('This mapping is already reviewed.'))
        if not self.chemical_substance_id:
            raise ValidationError(_("Cannot verify mapping without a linked Chemical Substance Master."))
        if self.uom_to_kg_ratio <= 0:
            raise ValidationError(_("UoM conversion ratio must be strictly greater than 0."))

        self.with_context(
            _chemical_mapping_verification=_MAPPING_VERIFICATION_CAPABILITY
        ).write({
            'is_verified': True,
            'verified_by': self.env.user.id,
            'verified_date': fields.Date.today(),
        })
        return True
