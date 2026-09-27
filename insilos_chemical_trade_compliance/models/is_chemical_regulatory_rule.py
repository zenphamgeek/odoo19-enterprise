# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import re
from urllib.parse import urlparse

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ChemicalRegulatoryRule(models.Model):
    _name = 'is.chemical.regulatory.rule'
    _description = 'Chemical Trade Compliance Regulatory Rule & Obligation Matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'rule_category asc, sequence asc, id desc'

    name = fields.Char(string='Rule Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=False, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Review'),
        ('active', 'Active'),
    ], default='draft', required=True, readonly=True, tracking=True)
    prepared_by_id = fields.Many2one('res.users', string='Prepared By', readonly=True, tracking=True)
    jurisdiction = fields.Char(string='Jurisdiction', default='VN', required=True, tracking=True)
    effective_from = fields.Date(string='Effective From', tracking=True)
    effective_to = fields.Date(string='Effective To', tracking=True)

    rule_category = fields.Selection([
        ('specially_controlled_group_1', '1. Specially Controlled Chemicals Group 1 (Hóa chất kiểm soát đặc biệt Nhóm 1 - Luật 2025/2026)'),
        ('specially_controlled_group_2', '2. Specially Controlled Chemicals Group 2 (Hóa chất kiểm soát đặc biệt Nhóm 2 - Luật 2025/2026)'),
        ('mandatory_nsw_declaration', '3. NSW Chemical Declaration (Phụ lục V NĐ 113 - Khai báo Cổng Một Cửa)'),
        ('restricted_chemical_license', '4. Restricted Chemical License (Phụ lục II NĐ 113 - Giấy phép BCT)'),
        ('conditional_chemical_cert', '5. Conditional Chemical Certificate (Phụ lục I NĐ 113 - GCN đủ điều kiện)'),
        ('precursor_narcotics_explosives', '6. Precursor Narcotics & Explosives (Tiền chất ma túy / thuốc nổ - BCA/BQP)'),
        ('opcw_scheduled_chemicals', '7. OPCW Scheduled Chemicals (Hóa chất Bảng 1, 2, 3 - NĐ 38/2014)'),
        ('sds_ghs_mandatory', '8. SDS 16-Section & GHS Labeling Mandatory (Bắt buộc SDS & Nhãn phụ GHS)'),
        ('prohibited_chemical_block', '9. Prohibited Chemical - Hard Block (Phụ lục III NĐ 113 - Hóa chất CẤM)'),
    ], string='Regulatory Scope', required=True, default='mandatory_nsw_declaration', tracking=True)

    chemical_substance_id = fields.Many2one('is.hse.chemical.substance', string='Master Chemical Substance', tracking=True)
    cas_number = fields.Char(string='CAS Registry Number', index=True, tracking=True,
                             help='Specific CAS number subject to this rule (e.g. 108-88-3 for Toluene, 7664-93-9 for Sulfuric Acid).')
    hs_code = fields.Char(string='HS Code (4/6/8 Digits)', index=True, tracking=True,
                          help='Harmonized System tariff code matching this regulatory control.')
    
    threshold_concentration = fields.Float(string='Threshold Concentration (% wt)', default=0.0,
                                           help='Minimum concentration percentage in mixture to trigger this obligation (0.0 = applies to all concentrations).')
    
    required_permit_type = fields.Selection([
        ('conditional_cert', 'Conditional Chemical Certificate (GCN đủ điều kiện)'),
        ('restricted_license', 'Restricted Chemical License (Giấy phép hóa chất hạn chế)'),
        ('import_declaration', 'Import Chemical Declaration (Xác nhận khai báo nhập khẩu)'),
        ('transport_permit', 'Dangerous Goods Transport Permit (Giấy phép vận chuyển)'),
        ('coa_quality', 'Certificate of Analysis (CoA)'),
        ('sds_compliance', 'SDS Compliance Certificate'),
        ('environmental_permit', 'Specialized Environmental Permit'),
        ('none', 'None (Standard Clearance)'),
    ], string='Required Accompanying Permit Type', default='import_declaration', tracking=True)

    nsw_procedure_code = fields.Char(string='NSW Procedure Code', tracking=True,
                                    help='National Single Window procedure code (e.g. BCT00001 for chemical declaration, BCT00002 for restricted license).')

    legal_basis = fields.Char(string='Legal Reference Citation',
                              help='E.g. Phụ lục V Nghị định 113/2017/NĐ-CP, Nghị định 82/2022/NĐ-CP')
    legal_document_id = fields.Many2one('is.hse.legal.document', string='Linked Legal Document')

    notes = fields.Text(string='Compliance Conditions & Technical Remarks')

    _determination_fields = {
        'active', 'jurisdiction', 'effective_from', 'effective_to', 'rule_category',
        'chemical_substance_id', 'cas_number', 'hs_code', 'threshold_concentration',
        'required_permit_type', 'nsw_procedure_code', 'legal_basis', 'legal_document_id',
    }

    def _check_chemical_compliance_manager(self):
        if not (
            self.env.user.has_group('insilos_chemical_trade_compliance.group_chemical_compliance_manager')
            and self.env.user.has_group('insilos_hse_compliance.group_hse_manager')
        ):
            raise UserError(_('Regulatory rule changes require chemical compliance and HSE manager authority.'))

    def _check_active_rule_provenance(self):
        for rule in self.filtered(lambda rule: rule.active or rule.state == 'review'):
            document = rule.legal_document_id
            if not (
                (rule.legal_basis or '').strip()
                and document
                and document.state == 'active'
                and document.has_governed_provenance()
                and document.is_effective_on(rule.effective_from)
            ):
                raise ValidationError(_(
                    'Active regulatory rules require a cited active legal document with governed provenance.'
                ))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_chemical_compliance_manager()
        for vals in vals_list:
            vals.update({
                'active': False,
                'state': 'draft',
                'prepared_by_id': self.env.user.id,
            })
        return super().create(vals_list)

    def write(self, vals):
        if {'active', 'state', 'prepared_by_id'} & vals.keys():
            raise UserError(_('Regulatory rule activation is controlled by review and approval.'))
        if self._determination_fields & vals.keys():
            self._check_chemical_compliance_manager()
            vals = dict(vals, active=False, state='draft', prepared_by_id=self.env.user.id)
            return super().write(vals)
        return super().write(vals)

    def action_submit_for_review(self):
        self._check_chemical_compliance_manager()
        super().write({
            'active': False,
            'state': 'review',
            'prepared_by_id': self.env.user.id,
        })
        self._check_active_rule_provenance()

    def action_activate(self):
        self._check_chemical_compliance_manager()
        if any(rule.state != 'review' or rule.prepared_by_id == self.env.user for rule in self):
            raise UserError(_('A different authorized approver must activate a regulatory rule in review.'))
        self._check_active_rule_provenance()
        self._check_active_rule_effectivity()
        super().write({'active': True, 'state': 'active'})

    def _check_active_rule_effectivity(self):
        if any(not rule.effective_from or not rule.effective_to for rule in self):
            raise ValidationError(_('Active regulatory rules require both Effective From and Effective To dates.'))

    @api.onchange('chemical_substance_id')
    def _onchange_chemical_substance_id(self):
        if self.chemical_substance_id:
            self.cas_number = self.chemical_substance_id.cas_number
            if not self.name:
                self.name = f"Rule for {self.chemical_substance_id.name} ({self.chemical_substance_id.cas_number})"

    @api.constrains('effective_from', 'effective_to')
    def _check_effective_dates(self):
        for rule in self:
            if rule.effective_from and rule.effective_to and rule.effective_from > rule.effective_to:
                raise ValidationError(_('Effective To must not precede Effective From.'))

    def _has_trustworthy_legal_document(self, effective_date):
        self.ensure_one()
        document = self.legal_document_id
        source = urlparse(document.source_url or '')
        return bool(
            (self.legal_basis or '').strip()
            and document
            and document.state == 'active'
            and document.has_governed_provenance()
            and source.scheme == 'https'
            and source.netloc
            and not source.username
            and not source.password
            and re.fullmatch(r'[0-9a-f]{64}', document.source_content_sha256 or '')
            and (document.source_version or '').strip()
            and (document.issuer or '').strip()
            and document.issued_date
            and document.effective_date
            and document.is_effective_on(effective_date)
        )

    @api.model
    def evaluate_chemical_obligations(self, cas_number=None, hs_code=None, concentration=100.0, effective_date=None, jurisdiction='VN'):
        """Return only legally effective, provenance-valid, specifically matched rules."""
        effective_date = effective_date or fields.Date.today()
        domain = [
            ('active', '=', True),
            ('state', '=', 'active'),
            ('jurisdiction', '=', jurisdiction),
            ('legal_basis', '!=', False),
            ('legal_document_id', '!=', False),
            ('effective_from', '!=', False),
            ('effective_from', '<=', effective_date),
            ('effective_to', '!=', False),
            ('effective_to', '>=', effective_date),
        ]
        conditions = []
        if cas_number:
            conditions.append(('cas_number', '=', cas_number))
        if hs_code:
            conditions.append(('hs_code', '=', hs_code))
        if not conditions:
            return self.browse()
        if len(conditions) > 1:
            domain.append('|')
        domain.extend(conditions)
        return self.search(domain).filtered(
            lambda rule: concentration >= (rule.threshold_concentration or 0.0)
            and rule._has_trustworthy_legal_document(effective_date)
        )
