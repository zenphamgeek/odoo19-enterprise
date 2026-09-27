# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


_CUSTOMS_CLEARANCE_CAPABILITY = object()
_QUOTA_COMPUTE_CAPABILITY = object()


class ChemicalPermitQuota(models.Model):
    _name = 'is.chemical.permit.quota'
    _description = 'Chemical Regulatory Permit Quota & Burn-down Ledger'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Quota Reference', compute='_compute_name', store=True, precompute=True)
    permit_id = fields.Many2one('is.hse.product.permit', string='Original Permit', required=True, index=True, tracking=True)
    permit_number = fields.Char(related='permit_id.permit_number', string='Permit Number', store=True)
    company_id = fields.Many2one('res.company', string='Company', related='permit_id.company_id', store=True)
    
    chemical_substance_id = fields.Many2one('is.hse.chemical.substance', string='Approved Chemical Substance', required=True, tracking=True)
    cas_number = fields.Char(related='chemical_substance_id.cas_number', string='CAS Registry No.', store=True)

    allocated_quota_kg = fields.Float(string='Allocated Quota (kg)', required=True, tracking=True,
                                      help='Total licensed import volume in kg for the validity period.')
    consumed_quota_kg = fields.Float(string='Consumed Volume (kg)', compute='_compute_quota_metrics', store=True, tracking=True,
                                     help='Cumulative imported volume deducted from customs declarations.')
    remaining_quota_kg = fields.Float(string='Remaining Quota (kg)', compute='_compute_quota_metrics', store=True, tracking=True)
    remaining_percentage = fields.Float(string='Remaining Percentage (%)', compute='_compute_quota_metrics', store=True)

    warning_threshold_pct = fields.Float(string='Low Quota Warning Threshold (%)', default=10.0,
                                         help='Threshold below which the system raises low-quota alerts.')
    is_quota_low = fields.Boolean(string='Low Quota Alert', compute='_compute_quota_metrics', store=True)
    is_quota_exhausted = fields.Boolean(string='Quota Exhausted', compute='_compute_quota_metrics', store=True)

    state = fields.Selection([
        ('active', 'Active & Available'),
        ('warning', 'Low Quota (< 10%)'),
        ('exhausted', 'Quota Exhausted (0 kg remaining)'),
        ('expired', 'Permit Expired'),
    ], string='Quota Status', compute='_compute_state', store=True, tracking=True)

    line_ids = fields.One2many('is.chemical.permit.quota.line', 'quota_id', string='Quota Deduction History')

    def _create_from_customs_workflow(self, values, capability):
        if capability is not _CUSTOMS_CLEARANCE_CAPABILITY:
            raise UserError(_('Permit quotas are registered only through a controlled authority workflow.'))
        return self.with_context(_quota_creation_capability=_CUSTOMS_CLEARANCE_CAPABILITY).create(values)

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('_quota_creation_capability') is not _CUSTOMS_CLEARANCE_CAPABILITY:
            raise UserError(_('Permit quotas are registered only through a controlled authority workflow.'))
        allowed_fields = {'permit_id', 'chemical_substance_id', 'allocated_quota_kg', 'warning_threshold_pct'}
        if any(set(vals) - allowed_fields for vals in vals_list):
            raise ValidationError(_('Permit quota registration cannot set balances, status, or deduction history.'))
        return super().create(vals_list)

    def write(self, vals):
        computed_fields = {
            'consumed_quota_kg', 'remaining_quota_kg', 'remaining_percentage',
            'is_quota_low', 'is_quota_exhausted', 'state',
        }
        if (
            self.env.context.get('_quota_compute_capability') is _QUOTA_COMPUTE_CAPABILITY
            and set(vals) <= computed_fields
        ):
            return super().write(vals)
        raise UserError(_('Permit quotas are immutable after controlled registration.'))

    def unlink(self):
        raise UserError(_('Permit quotas are immutable after controlled registration.'))

    @api.depends('permit_id.permit_number', 'chemical_substance_id.name')
    def _compute_name(self):
        for rec in self:
            p_num = rec.permit_id.permit_number or 'NO-PERMIT'
            c_name = rec.chemical_substance_id.name or 'CHEMICAL'
            rec.name = f"QUOTA-{p_num}-{c_name}"

    @api.depends('allocated_quota_kg', 'line_ids.quantity_kg', 'warning_threshold_pct')
    def _compute_quota_metrics(self):
        for rec in self.with_context(_quota_compute_capability=_QUOTA_COMPUTE_CAPABILITY):
            consumed = sum(line.quantity_kg for line in rec.line_ids)
            rec.consumed_quota_kg = consumed
            rec.remaining_quota_kg = max(0.0, rec.allocated_quota_kg - consumed)
            if rec.allocated_quota_kg > 0:
                rec.remaining_percentage = (rec.remaining_quota_kg / rec.allocated_quota_kg) * 100.0
            else:
                rec.remaining_percentage = 0.0
            rec.is_quota_exhausted = (rec.remaining_quota_kg <= 0.0)
            rec.is_quota_low = (rec.remaining_percentage <= rec.warning_threshold_pct and not rec.is_quota_exhausted)

    @api.depends('is_quota_exhausted', 'is_quota_low', 'permit_id.state')
    def _compute_state(self):
        for rec in self:
            if rec.permit_id and rec.permit_id.state in ('expired', 'revoked'):
                rec.state = 'expired'
            elif rec.is_quota_exhausted:
                rec.state = 'exhausted'
            elif rec.is_quota_low:
                rec.state = 'warning'
            else:
                rec.state = 'active'

    def deduct_quota(self, quantity_kg, dossier, dossier_line, remarks=None, _capability=None):
        if _capability is not _CUSTOMS_CLEARANCE_CAPABILITY:
            raise UserError(_('Quota deductions are only permitted through customs clearance.'))
        self.ensure_one()
        self.check_access('write')
        dossier.check_access('read')
        dossier_line.check_access('read')
        if dossier.state != 'internally_approved' or not dossier.customs_declaration_no or dossier_line.dossier_id != dossier:
            raise UserError(_('An internally reviewed dossier with a customs declaration is required for quota deduction.'))
        if dossier.importer_company_id != self.company_id:
            raise ValidationError(_('Dossier company must match the permit quota company.'))
        if dossier_line.permit_id != self.permit_id or dossier_line.chemical_substance_id != self.chemical_substance_id:
            raise ValidationError(_('Dossier line does not match this quota permit and chemical.'))
        if quantity_kg <= 0:
            raise ValidationError(_('Deduction quantity must be strictly greater than 0 kg.'))

        self.env.cr.execute('SELECT id FROM is_chemical_permit_quota WHERE id = %s FOR UPDATE', [self.id])
        if self.env['is.chemical.permit.quota.line'].search_count([
            ('quota_id', '=', self.id), ('dossier_line_id', '=', dossier_line.id),
        ]):
            raise UserError(_('This dossier line has already deducted this permit quota.'))
        self.invalidate_recordset(['line_ids', 'consumed_quota_kg', 'remaining_quota_kg'])
        if self.remaining_quota_kg < quantity_kg:
            raise UserError(_(
                'Insufficient permit quota! Requested: %(req)s kg, Available: %(avail)s kg on Permit %(permit)s.',
                req=quantity_kg, avail=self.remaining_quota_kg, permit=self.permit_id.permit_number,
            ))
        return self.env['is.chemical.permit.quota.line'].sudo().with_context(
            _quota_deduction_capability=_CUSTOMS_CLEARANCE_CAPABILITY,
        ).create({
            'quota_id': self.id,
            'dossier_id': dossier.id,
            'dossier_line_id': dossier_line.id,
            'customs_declaration_no': dossier.customs_declaration_no,
            'quantity_kg': quantity_kg,
            'deduction_date': fields.Date.today(),
            'user_id': self.env.uid,
            'notes': remarks or f'Customs clearance deduction for {quantity_kg} kg.',
        })


class ChemicalPermitQuotaLine(models.Model):
    _name = 'is.chemical.permit.quota.line'
    _description = 'Chemical Permit Quota Burn-down Deduction Entry'
    _order = 'deduction_date desc, id desc'

    quota_id = fields.Many2one('is.chemical.permit.quota', string='Permit Quota', required=True, ondelete='cascade', index=True)
    dossier_id = fields.Many2one('is.chemical.compliance.dossier', string='Compliance Dossier', required=True, index=True)
    dossier_line_id = fields.Many2one('is.chemical.compliance.dossier.line', string='Compliance Dossier Line', index=True, ondelete='restrict')
    customs_declaration_no = fields.Char(string='Internal Customs Reference', required=True, index=True)
    deduction_date = fields.Date(string='Deduction Date', default=fields.Date.today, required=True)
    quantity_kg = fields.Float(string='Deducted Quantity (kg)', required=True)
    user_id = fields.Many2one('res.users', string='Operator', default=lambda self: self.env.user)
    notes = fields.Char(string='Remarks')

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('_quota_deduction_capability') is not _CUSTOMS_CLEARANCE_CAPABILITY:
            raise UserError(_('Quota ledger entries are created only through customs clearance.'))
        allowed_fields = {
            'quota_id', 'dossier_id', 'dossier_line_id', 'customs_declaration_no',
            'quantity_kg', 'deduction_date', 'user_id', 'notes',
        }
        if any(set(vals) - allowed_fields for vals in vals_list):
            raise ValidationError(_('Quota ledger entries cannot set fields outside the controlled deduction flow.'))
        if any(not vals.get('dossier_line_id') for vals in vals_list):
            raise ValidationError(_('Quota ledger entries require a compliance dossier line.'))
        for vals in vals_list:
            quota = self.env['is.chemical.permit.quota'].browse(vals['quota_id'])
            dossier = self.env['is.chemical.compliance.dossier'].browse(vals['dossier_id'])
            dossier_line = self.env['is.chemical.compliance.dossier.line'].browse(vals['dossier_line_id'])
            if (dossier_line.dossier_id != dossier
                    or dossier.importer_company_id != quota.company_id
                    or dossier_line.permit_id != quota.permit_id
                    or dossier_line.chemical_substance_id != quota.chemical_substance_id):
                raise ValidationError(_('Quota ledger entries must match their quota, dossier, permit, and chemical.'))
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_('Quota ledger entries are immutable.'))

    def unlink(self):
        raise UserError(_('Quota ledger entries are immutable.'))
