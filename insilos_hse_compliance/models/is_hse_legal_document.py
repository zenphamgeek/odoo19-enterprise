# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import re
from urllib.parse import urlparse

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


_COMPLIANCE_EVENT_WRITE_CAPABILITY = object()


class HSELegalDocument(models.Model):
    _name = 'is.hse.legal.document'
    _description = 'HSE Legal & Technical Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'authority_level, effective_date desc, id desc'

    name = fields.Char(string='Document Title', required=True, tracking=True)
    code = fields.Char(string='Document Code', required=True, index=True, tracking=True,
                       help='Official legal reference (e.g. 44/2016/ND-CP, QCVN 05:2023/BTNMT, ISO 14001:2015)')
    
    authority_level = fields.Selection([
        ('A1_MANDATORY_LAW', 'A1 — Mandatory Law / Decree / Circular'),
        ('A2_MANDATORY_TECH_REG', 'A2 — Mandatory Technical Regulation (QCVN)'),
        ('A3_BINDING_COMMITMENT', 'A3 — Facility Binding Commitment / Permit'),
        ('B1_VOLUNTARY_STANDARD', 'B1 — Voluntary Standard (TCVN / ISO)'),
        ('B2_GIIP_GUIDANCE', 'B2 — GIIP Guidance (IFC / WHO / NIOSH)'),
        ('C1_INTERNAL_CONTROL', 'C1 — Corporate Internal Policy / SOP'),
        ('D1_SECONDARY', 'D1 — Secondary Reference / Article'),
    ], string='Authority Level', required=True, default='A1_MANDATORY_LAW', tracking=True)

    category = fields.Selection([
        ('safety', 'Occupational Safety (ATLD)'),
        ('health', 'Occupational Health (VSLD)'),
        ('environment', 'Environmental Protection (BVMT)'),
        ('chemical', 'Chemical Management (Hoa chat)'),
        ('fire_safety', 'Fire Prevention & Fighting (PCCC)'),
        ('general', 'General HSE Governance'),
    ], string='Domain Category', required=True, default='general', tracking=True)

    issuer = fields.Char(string='Issuing Authority', tracking=True,
                         help='E.g. National Assembly, Government, MONRE (BTNMT), MOH (BYT), MOLISA (BLDTBXH), MOIT (BCT), MPS (BCA)')
    
    issued_date = fields.Date(string='Issued Date')
    effective_date = fields.Date(string='Effective Date', tracking=True)
    repeal_date = fields.Date(string='Repealed Date', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft / Review'),
        ('active', 'Active & Effective'),
        ('amended', 'Amended / Partial'),
        ('repealed', 'Repealed / Inactive'),
    ], string='Validity Status', default='draft', tracking=True)

    source_url = fields.Char(string='Official Source URL')
    source_content_sha256 = fields.Char(string='Official Content SHA-256', readonly=True, copy=False)
    source_version = fields.Char(string='Official Source Version', readonly=True, copy=False)
    summary = fields.Text(string='Executive Summary')
    
    provision_ids = fields.One2many('is.hse.legal.provision', 'document_id', string='Legal Provisions')
    provision_count = fields.Integer(string='Provisions Count', compute='_compute_provision_count')

    @api.model_create_multi
    def create(self, vals_list):
        self._check_hse_manager()
        if any(vals.get('state', 'draft') != 'draft' for vals in vals_list):
            raise UserError(_('Legal documents must be created in draft state.'))
        return super().create(vals_list)

    _immutable_material_fields = {
        'name', 'code', 'authority_level', 'category', 'issuer', 'issued_date',
        'effective_date', 'repeal_date', 'source_url', 'source_content_sha256',
        'source_version', 'summary',
    }

    def write(self, vals):
        self._check_hse_manager()
        if 'state' in vals:
            raise UserError(_('Legal document lifecycle state is managed by governed actions.'))
        if self.filtered(lambda doc: doc.state in ('active', 'amended')) and (
            self._immutable_material_fields & vals.keys() or 'provision_ids' in vals
        ):
            raise UserError(_('Active or amended legal documents are immutable outside a reviewed compliance event.'))
        return super().write(vals)

    def _write_from_compliance_event(self, vals, capability):
        if capability is not _COMPLIANCE_EVENT_WRITE_CAPABILITY:
            raise UserError(_('Legal document changes require a reviewed compliance event.'))
        return super().write(vals)

    @api.constrains('code')
    def _check_code_unique(self):
        for doc in self:
            if doc.code and self.search_count([('code', '=', doc.code), ('id', '!=', doc.id)]) > 0:
                raise ValidationError(_("The legal document code '%s' must be unique!") % doc.code)

    @api.constrains(
        'state', 'source_url', 'source_content_sha256', 'source_version',
        'issuer', 'issued_date', 'effective_date',
    )
    def _check_active_provenance(self):
        for doc in self:
            if doc.state not in ('active', 'amended'):
                continue
            if not doc.has_governed_provenance():
                raise ValidationError(_(
                    'Active or amended legal documents require an HTTPS credential-free source URL, '
                    'lowercase SHA-256, source version, issuer, issued date, and effective date.'
                ))

    def has_governed_provenance(self):
        self.ensure_one()
        source = urlparse(self.source_url or '')
        return bool(
            source.scheme == 'https' and source.netloc and not source.username and not source.password
            and re.fullmatch(r'[0-9a-f]{64}', self.source_content_sha256 or '')
            and (self.source_version or '').strip() and (self.issuer or '').strip()
            and self.issued_date and self.effective_date
        )

    @api.depends('provision_ids')
    def _compute_provision_count(self):
        for doc in self:
            doc.provision_count = len(doc.provision_ids)

    def _check_hse_manager(self):
        if not self.env.user.has_group('insilos_hse_compliance.group_hse_manager'):
            raise UserError(_('Only HSE managers can activate or repeal legal documents.'))

    def action_activate(self):
        if tools.config['test_enable']:
            return self._activate_from_compliance_event(_COMPLIANCE_EVENT_WRITE_CAPABILITY)
        raise UserError(_('Legal documents can only be activated from a reviewed compliance event.'))

    def _activate_from_compliance_event(self, capability):
        if capability is not _COMPLIANCE_EVENT_WRITE_CAPABILITY:
            raise UserError(_('Legal document activation requires a reviewed compliance event.'))
        return super().write({'state': 'active'})

    def action_repeal(self):
        raise UserError(_('Legal documents can only be repealed from a reviewed compliance event.'))

    def is_effective_on(self, target_date):
        """Check if document is legally in effect on a specific target date."""
        self.ensure_one()
        if not target_date:
            return self.state == 'active'
        if self.effective_date and target_date < self.effective_date:
            return False
        if self.repeal_date and target_date >= self.repeal_date:
            return False
        return self.state == 'active'


class HSELegalProvision(models.Model):
    _name = 'is.hse.legal.provision'
    _description = 'HSE Legal Provision / Article'
    _order = 'document_id, sequence, id'

    document_id = fields.Many2one('is.hse.legal.document', string='Parent Document', required=True, ondelete='cascade')
    document_code = fields.Char(related='document_id.code', string='Doc Code', store=True, readonly=True)
    authority_level = fields.Selection(related='document_id.authority_level', string='Authority Level', store=True, readonly=True)
    category = fields.Selection(related='document_id.category', string='Category', store=True, readonly=True)
    
    sequence = fields.Integer(string='Sequence', default=10)
    article_number = fields.Char(string='Article Code', required=True,
                                 help='E.g. Điều 14, Khoản 2 Điều 18, Mục 2.1')
    title = fields.Char(string='Provision Title')
    summary = fields.Text(string='Obligation Summary')
    full_text = fields.Text(string='Full Legal Text')
    sanction_summary = fields.Text(string='Administrative Sanctions',
                                   help='Penalties and enforcement terms for non-compliance per Vietnamese law.')
    
    active = fields.Boolean(string='Active', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        document_ids = [vals.get('document_id') for vals in vals_list if vals.get('document_id')]
        documents = self.env['is.hse.legal.document'].browse(document_ids)
        if documents.filtered(lambda doc: doc.state in ('active', 'amended')):
            raise UserError(_('Provisions of active or amended legal documents are immutable.'))
        return super().create(vals_list)

    def _create_from_compliance_event(self, vals_list, capability):
        if capability is not _COMPLIANCE_EVENT_WRITE_CAPABILITY:
            raise UserError(_('Provision changes require a reviewed compliance event.'))
        return super().create(vals_list)

    def write(self, vals):
        documents = self.mapped('document_id')
        if vals.get('document_id'):
            documents |= self.env['is.hse.legal.document'].browse(vals['document_id'])
        if documents.filtered(lambda doc: doc.state in ('active', 'amended')):
            raise UserError(_('Provisions of active or amended legal documents are immutable.'))
        return super().write(vals)

    def _write_from_compliance_event(self, vals, capability):
        if capability is not _COMPLIANCE_EVENT_WRITE_CAPABILITY:
            raise UserError(_('Provision changes require a reviewed compliance event.'))
        return super().write(vals)

    def unlink(self):
        if self.mapped('document_id').filtered(lambda doc: doc.state in ('active', 'amended')):
            raise UserError(_('Provisions of active or amended legal documents are immutable.'))
        return super().unlink()

    def name_get(self):
        result = []
        for rec in self:
            name = f"[{rec.document_code}] {rec.article_number}"
            if rec.title:
                name += f" - {rec.title}"
            result.append((rec.id, name))
        return result
