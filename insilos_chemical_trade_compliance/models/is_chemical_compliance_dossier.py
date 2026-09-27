# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from ..services.nsw_payload_builder import NSWChemicalPayloadBuilder

class ChemicalComplianceDossier(models.Model):
    _name = 'is.chemical.compliance.dossier'
    _description = 'Chemical Import & Trade Compliance Dossier'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Dossier Reference', required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('is.chemical.compliance.dossier') or _('New'))
    
    dossier_type = fields.Selection([
        ('specially_controlled_group_1', '1. Specially Controlled Chemicals Group 1 (Giấy phép Hóa chất Nhóm 1 - Luật 2025/2026)'),
        ('specially_controlled_group_2', '2. Specially Controlled Chemicals Group 2 (Giấy phép Hóa chất Nhóm 2 - Luật 2025/2026)'),
        ('nsw_declaration', '3. NSW Chemical Import Declaration (Khai báo Hóa chất NSW Phụ lục V)'),
        ('restricted_license', '4. Restricted Chemical License Application (Giấy phép Hóa chất Hạn chế BCT)'),
        ('precursor_permit', '5. Precursor Chemical Permit (Giấy phép Tiền chất BCA/BCT)'),
        ('general_compliance', '6. General Trade Compliance Dossier (Hồ sơ Tuân thủ XNK Tổng hợp)'),
    ], string='Dossier Category', required=True, default='nsw_declaration', tracking=True)

    partner_id = fields.Many2one('res.partner', string='Overseas Exporter', tracking=True)
    importer_company_id = fields.Many2one('res.company', string='Importer Entity', required=True, default=lambda self: self.env.company)
    
    purchase_order_id = fields.Many2one('purchase.order', string='Source Purchase Order (PO)', tracking=True)
    case_id = fields.Many2one('logistics.idp.case', string='Source Logistics IDP Case', tracking=True, index=True)
    picking_id = fields.Many2one('stock.picking', string='Inbound Shipment', tracking=True)
    usage_tracking_id = fields.Many2one('is.chemical.usage.tracking', string='Linked Usage Tracking Report')
    exception_ids = fields.One2many('is.chemical.compliance.exception', 'dossier_id', string='Compliance Data Exceptions')
    exception_count = fields.Integer(string='Exceptions Count', compute='_compute_exception_count')
    
    customs_declaration_no = fields.Char(string='Internal Customs Reference', tracking=True)
    customs_office_code = fields.Char(string='Customs Office Code')
    port_of_loading = fields.Char(string='Port of Loading')
    port_of_discharge = fields.Char(string='Port of Discharge')

    invoice_number = fields.Char(string='Commercial Invoice No.', tracking=True)
    invoice_date = fields.Date(string='Invoice Date')

    jurisdiction = fields.Char(string='Jurisdiction', default='VN', required=True, tracking=True)
    nsw_procedure_code = fields.Char(string='NSW Procedure Code', tracking=True)
    submitted_by = fields.Many2one('res.users', string='Submitted By', readonly=True, tracking=True)
    approved_by = fields.Many2one('res.users', string='Internal Reviewer', readonly=True, tracking=True)
    nsw_registration_no = fields.Char(string='Internal NSW Registration Reference', tracking=True)
    nsw_verification_code = fields.Char(string='Internal NSW Verification Reference', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('evaluating', 'Obligations Evaluated'),
        ('dossier_ready', 'Dossier Ready'),
        ('submission_prepared', 'Submission Prepared (Not Sent)'),
        ('internally_approved', 'Internally Reviewed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('is.chemical.compliance.dossier.line', 'dossier_id', string='Chemical Consignment Items')
    
    total_net_weight_kg = fields.Float(string='Total Net Weight (kg)', compute='_compute_total_weight', store=True)
    line_count = fields.Integer(string='Items Count', compute='_compute_total_weight', store=True)

    has_prohibited_chemicals = fields.Boolean(string='Has Prohibited Chemicals', compute='_compute_risk_flags', store=True)
    has_restricted_chemicals = fields.Boolean(string='Has Restricted Chemicals (Cần Giấy phép BCT)', compute='_compute_risk_flags', store=True)
    requires_nsw_declaration = fields.Boolean(string='Requires NSW Declaration', compute='_compute_risk_flags', store=True)

    attachment_ids = fields.Many2many('ir.attachment', 'is_chemical_dossier_attachment_rel',
                                      'dossier_id', 'attachment_id', string='Dossier Documents (PO, Invoice, CoA, SDS)')

    nsw_payload_json = fields.Text(string='NSW JSON Payload')
    nsw_payload_xml = fields.Text(string='NSW XML Payload')

    compliance_notes = fields.Text(string='Compliance Findings & Auditor Remarks')

    @api.model_create_multi
    def create(self, vals_list):
        protected_fields = ('state', 'submitted_by', 'approved_by', 'nsw_registration_no', 'nsw_verification_code')
        defaults = self.default_get(protected_fields)
        for vals in vals_list:
            effective = dict(defaults, **vals)
            if (effective.get('state', 'draft') != 'draft' or effective.get('submitted_by')
                    or effective.get('approved_by') or effective.get('nsw_registration_no')
                    or effective.get('nsw_verification_code')):
                raise UserError(_('Dossiers must be created in draft without reviewer attribution or NSW receipt references.'))
            vals.update(state='draft', submitted_by=False, approved_by=False,
                        nsw_registration_no=False, nsw_verification_code=False)
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('is.chemical.compliance.dossier') or f"DOS-{fields.Date.today().year}-{self.env['is.chemical.compliance.dossier'].search_count([]) + 1:04d}"
        return super(ChemicalComplianceDossier, self).create(vals_list)

    def _lock_workflow(self):
        if self.ids:
            self.env.cr.execute(
                'SELECT id FROM is_chemical_compliance_dossier WHERE id IN %s ORDER BY id FOR UPDATE',
                [tuple(self.ids)],
            )
            self.invalidate_recordset(['state', 'submitted_by', 'approved_by'])

    def _check_mutable(self):
        self._lock_workflow()
        if any(rec.state in ('submission_prepared', 'internally_approved') for rec in self):
            raise UserError(_('Prepared and internally reviewed dossiers are immutable.'))

    def _check_draft_dossiers(self):
        if any(dossier.state != 'draft' for dossier in self):
            raise UserError(_('Chemical consignment items can only be changed while the dossier is in draft.'))

    @api.constrains('importer_company_id', 'purchase_order_id', 'case_id', 'picking_id', 'usage_tracking_id')
    def _check_linked_company(self):
        for dossier in self:
            company = dossier.importer_company_id
            for record in (dossier.purchase_order_id, dossier.case_id, dossier.picking_id, dossier.usage_tracking_id):
                if record and record.company_id != company:
                    raise ValidationError(_('Dossier source records must belong to the importer company.'))

    def write(self, vals):
        protected_fields = {'state', 'submitted_by', 'approved_by', 'nsw_registration_no', 'nsw_verification_code'}
        if protected_fields & vals.keys():
            raise UserError(_('Use controlled workflow actions to change dossier status, attribution, or NSW receipt references.'))
        self._check_mutable()
        return super().write(vals)

    def unlink(self):
        self._check_mutable()
        return super().unlink()

    def _check_transition(self, source_states, manager=False):
        self.ensure_one()
        self.check_access('write')
        group = 'group_chemical_compliance_manager' if manager else 'group_chemical_compliance_user'
        if not self.env.user.has_group('insilos_chemical_trade_compliance.' + group):
            raise UserError(_('Your role cannot perform this dossier transition.'))
        self._lock_workflow()
        if self.state not in source_states:
            raise UserError(_('Invalid dossier workflow transition.'))

    @api.depends('line_ids.net_weight_kg')
    def _compute_total_weight(self):
        for rec in self:
            rec.total_net_weight_kg = sum(line.net_weight_kg for line in rec.line_ids)
            rec.line_count = len(rec.line_ids)

    @api.depends('line_ids.regulatory_status')
    def _compute_risk_flags(self):
        for rec in self:
            statuses = [line.regulatory_status for line in rec.line_ids]
            rec.has_prohibited_chemicals = ('prohibited' in statuses)
            rec.has_restricted_chemicals = ('license_required' in statuses)
            rec.requires_nsw_declaration = ('nsw_required' in statuses)

    @api.depends('exception_ids')
    def _compute_exception_count(self):
        for rec in self:
            rec.exception_count = len(rec.exception_ids)

    def action_run_compliance_data_check(self):
        """
        Runs automated compliance data verification across all products in this dossier.
        """
        self._check_transition(('draft', 'evaluating', 'dossier_ready'))
        ExceptionModel = self.env['is.chemical.compliance.exception']
        # Clear existing open exceptions for this dossier
        self.exception_ids.filtered(lambda e: e.state == 'open').unlink()
        exceptions = ExceptionModel.run_compliance_data_check(dossier=self)
        self._compute_exception_count()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Compliance Data Check Completed'),
                'message': _('Found %s data exceptions requiring attention.') % len(exceptions),
                'type': 'warning' if exceptions else 'success',
                'sticky': False,
            }
        }

    def action_evaluate_obligations(self):
        """
        Evaluates all lines against the Chemical Regulatory Rules matrix.
        """
        self._check_transition(('draft', 'evaluating', 'dossier_ready'))
        if not self.jurisdiction or not self.jurisdiction.strip() or not self.invoice_date:
            raise ValidationError(_('Jurisdiction and invoice date are required for evaluation.'))
        if not self.line_ids or any(not (line.cas_number or line.hs_code) for line in self.line_ids):
            raise ValidationError(_('Chemical items with CAS or HS codes are required for evaluation.'))
        Rule = self.env['is.chemical.regulatory.rule']
        for line in self.line_ids:
            rules = Rule.evaluate_chemical_obligations(
                cas_number=line.cas_number,
                hs_code=line.hs_code,
                concentration=line.concentration_percentage,
                effective_date=self.invoice_date,
                jurisdiction=self.jurisdiction,
            )
            # Determine line status based on highest severity rule
            if any(r.rule_category == 'prohibited_chemical_block' for r in rules):
                regulatory_status = 'prohibited'
            elif any(r.rule_category == 'specially_controlled_group_1' for r in rules):
                regulatory_status = 'group_1_license'
            elif any(r.rule_category == 'specially_controlled_group_2' for r in rules):
                regulatory_status = 'group_2_license'
            elif any(r.rule_category == 'restricted_chemical_license' for r in rules):
                regulatory_status = 'license_required'
            elif any(r.rule_category == 'precursor_narcotics_explosives' for r in rules):
                regulatory_status = 'precursor'
            elif any(r.rule_category == 'opcw_scheduled_chemicals' for r in rules):
                regulatory_status = 'opcw'
            elif any(r.rule_category == 'mandatory_nsw_declaration' for r in rules):
                regulatory_status = 'nsw_required'
            elif any(r.rule_category == 'sds_ghs_mandatory' for r in rules):
                regulatory_status = 'sds_only'
            else:
                regulatory_status = 'review'
            super(ChemicalComplianceDossierLine, line).write({
                'matched_rule_ids': [(6, 0, rules.ids)],
                'regulatory_status': regulatory_status,
            })

        nsw_rules = self.line_ids.mapped('matched_rule_ids').filtered(lambda r: r.rule_category == 'mandatory_nsw_declaration')
        procedure_codes = set(nsw_rules.mapped('nsw_procedure_code'))
        self.nsw_procedure_code = procedure_codes.pop() if len(procedure_codes) == 1 else False
        super(ChemicalComplianceDossier, self).write({'state': 'evaluating'})
        self._compute_risk_flags()
        return True

    def _check_regulatory_review(self):
        for line in self.line_ids:
            trusted_rules = line.matched_rule_ids.filtered(
                lambda rule: rule._has_trustworthy_legal_document(self.invoice_date)
            )
            if line.regulatory_status == 'review' or not trusted_rules:
                raise UserError(_('Regulatory review is required for unmatched or unverified chemical rules before NSW or customs processing.'))

    def action_generate_nsw_payload(self):
        raise UserError(_(
            'NSW payload generation is unavailable until governed legal sources, immutable evidence manifests, '
            'and an authority-controlled submission capability exist.'
        ))

    def action_prepare_nsw_submission(self):
        self._check_transition(('dossier_ready',))
        self.action_generate_nsw_payload()
        super(ChemicalComplianceDossier, self).write({'state': 'submission_prepared', 'submitted_by': self.env.user.id})
        return True

    def _check_final_screening(self):
        case = self.case_id.sudo()
        if not case:
            return
        overridden = case.override_ids.filtered(
            lambda item: item.state == 'approved'
            and item.audit_service == 'controlled_override'
            and item.requested_by and item.requested_at
            and item.approved_by and item.approved_at
            and item.approved_at >= item.requested_at
            and item.audit_actor_id == item.requested_by
            and item.exception_ids
            and all(exc.case_id == case for exc in item.exception_ids)
            and all(check.case_id == case for check in item.check_result_ids)
            and (not item.evidence_id or item.evidence_id.case_id == case)
            and (not any(exc.severity == 'critical' for exc in item.exception_ids)
                 or item.approved_by != item.requested_by)
        ).check_result_ids
        unresolved = case.check_result_ids.filtered(
            lambda item: item.required and item.verdict in ('review', 'block') and item not in overridden)
        if unresolved or case.verdict in ('review', 'block'):
            raise UserError(_('Resolve the linked logistics case screening before final approval or customs clearance.'))

    def action_complete_internal_review(self):
        self._check_transition(('submission_prepared',), manager=True)
        self._check_regulatory_review()
        self._check_final_screening()
        if not self.submitted_by:
            raise UserError(_('Dossier has no authenticated preparer.'))
        if self.submitted_by == self.env.user:
            raise UserError(_("Dossier preparer cannot review the same dossier."))
        super(ChemicalComplianceDossier, self).write({'state': 'internally_approved', 'approved_by': self.env.user.id})
        return True

    def action_deduct_permit_quota(self):
        raise UserError(_('Permit quota deduction is unavailable until an immutable externally verified customs receipt capability exists.'))


class ChemicalComplianceDossierLine(models.Model):
    _name = 'is.chemical.compliance.dossier.line'
    _description = 'Chemical Compliance Consignment Item Detail'

    dossier_id = fields.Many2one('is.chemical.compliance.dossier', string='Dossier', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product')
    chemical_substance_id = fields.Many2one('is.hse.chemical.substance', string='Chemical Substance Master')

    trade_name = fields.Char(string='Trade Name', required=True)
    cas_number = fields.Char(string='CAS No.', index=True)
    hs_code = fields.Char(string='HS Code', index=True)
    
    concentration_percentage = fields.Float(string='Concentration (% wt)', default=100.0)
    quantity = fields.Float(string='Package Quantity')
    package_type = fields.Char(string='Package Type')
    net_weight_kg = fields.Float(string='Net Weight (kg)', required=True, default=0.0)

    purpose_of_use_id = fields.Many2one('is.chemical.purpose.of.use', string='Purpose of Use')
    intended_use = fields.Char(string='Intended Industrial Use')

    regulatory_status = fields.Selection([
        ('review', 'Regulatory Review Required (Chưa có quy tắc pháp lý đáng tin cậy)'),
        ('exempt', 'Exempt / Non-Hazardous (Miễn trừ / Không thuộc danh mục)'),
        ('sds_only', 'SDS & GHS Only (Chỉ yêu cầu SDS & Nhãn phụ GHS)'),
        ('nsw_required', 'NSW Declaration Required (Bắt buộc Khai báo NSW Phụ lục V)'),
        ('group_1_license', 'Group 1 License Required (Bắt buộc Giấy phép Hóa chất Nhóm 1 - Luật 2026)'),
        ('group_2_license', 'Group 2 License Required (Bắt buộc Giấy phép Hóa chất Nhóm 2 - Luật 2026)'),
        ('license_required', 'Restricted License Required (Bắt buộc Giấy phép BCT Phụ lục II)'),
        ('precursor', 'Precursor Permit Required (Bắt buộc Giấy phép Tiền chất)'),
        ('opcw', 'OPCW Chemical Schedule Required (Hóa chất Bảng)'),
        ('prohibited', 'PROHIBITED (Hóa chất CẤM - Chặn nhập khẩu)'),
    ], string='Regulatory Finding', default='review')

    matched_rule_ids = fields.Many2many('is.chemical.regulatory.rule', 'chem_dossier_line_rule_rel',
                                        'line_id', 'rule_id', string='Matched Regulatory Rules')
    permit_id = fields.Many2one('is.hse.product.permit', string='Accompanying Permit for Quota Deduction')
    
    quota_deducted = fields.Float(string='Quota Deducted (kg)', readonly=True, default=0.0)
    is_quota_deducted = fields.Boolean(string='Quota Deducted Flag', readonly=True, default=False)

    @api.constrains('dossier_id', 'purpose_of_use_id', 'permit_id')
    def _check_linked_company(self):
        for line in self:
            company = line.dossier_id.importer_company_id
            for record in (line.purpose_of_use_id, line.permit_id):
                if record and record.company_id != company:
                    raise ValidationError(_('Purpose and permit must belong to the dossier importer company.'))

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(['dossier_id', 'quota_deducted', 'is_quota_deducted'])
        dossiers = self.env['is.chemical.compliance.dossier']
        for vals in vals_list:
            effective = dict(defaults, **vals)
            if effective.get('quota_deducted') or effective.get('is_quota_deducted'):
                raise UserError(_('Quota attribution is managed by customs clearance.'))
            dossiers |= self.env['is.chemical.compliance.dossier'].browse(effective.get('dossier_id'))
        dossiers._check_draft_dossiers()
        return super().create(vals_list)

    def write(self, vals):
        if {'quota_deducted', 'is_quota_deducted'} & vals.keys():
            raise UserError(_('Quota attribution is managed by customs clearance.'))
        if {'regulatory_status', 'matched_rule_ids'} & vals.keys():
            raise UserError(_('Regulatory findings are managed by obligation evaluation.'))
        dossiers = self.dossier_id
        if vals.get('dossier_id'):
            dossiers |= self.env['is.chemical.compliance.dossier'].browse(vals['dossier_id'])
        if {'product_id', 'chemical_substance_id', 'cas_number', 'hs_code',
                'concentration_percentage', 'net_weight_kg', 'dossier_id'} & vals.keys():
            dossiers._check_draft_dossiers()
        dossiers._check_mutable()
        return super().write(vals)

    def unlink(self):
        self.dossier_id._check_draft_dossiers()
        self.dossier_id._check_mutable()
        return super().unlink()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            tmpl = self.product_id.product_tmpl_id
            self.trade_name = self.product_id.name
            if tmpl.chemical_substance_id:
                self.chemical_substance_id = tmpl.chemical_substance_id
                self.cas_number = tmpl.cas_number
            if hasattr(tmpl, 'hs_code') and tmpl.hs_code:
                self.hs_code = tmpl.hs_code
            if tmpl.permit_ids:
                self.permit_id = tmpl.permit_ids[0].id
