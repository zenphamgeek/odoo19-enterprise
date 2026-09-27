# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HSELegalRegister(models.Model):
    _name = 'is.hse.legal.register'
    _description = 'Facility HSE Legal Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'company_id, facility_id, year desc, id desc'

    name = fields.Char(string='Register Title', required=True, tracking=True)
    facility_id = fields.Many2one('is.hse.facility', string='Facility', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    year = fields.Integer(string='Compliance Year', default=lambda self: fields.Date.today().year, tracking=True)
    evaluation_date = fields.Date(string='Last Evaluated Date', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft / Preparation'),
        ('active', 'Active Legal Register'),
        ('under_review', 'Under Audit / Review'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    obligation_ids = fields.One2many('is.hse.obligation', 'register_id', string='Compliance Obligations')
    total_obligations = fields.Integer(string='Total Obligations', compute='_compute_compliance_metrics', store=True)
    compliant_count = fields.Integer(string='Compliant Count', compute='_compute_compliance_metrics', store=True)
    non_compliant_count = fields.Integer(string='Non-Compliant Count', compute='_compute_compliance_metrics', store=True)
    compliance_score = fields.Float(string='Compliance Rate (%)', compute='_compute_compliance_metrics', store=True)
    notes = fields.Text(string='Auditor Notes')

    @api.depends('obligation_ids', 'obligation_ids.compliance_status')
    def _compute_compliance_metrics(self):
        for reg in self:
            total = len(reg.obligation_ids)
            assessed = reg.obligation_ids.filtered(lambda o: o.compliance_status not in ('not_assessed', 'not_applicable'))
            compliant = len(reg.obligation_ids.filtered(lambda o: o.compliance_status == 'compliant'))
            non_compliant = len(reg.obligation_ids.filtered(lambda o: o.compliance_status == 'non_compliant'))
            reg.total_obligations = total
            reg.compliant_count = compliant
            reg.non_compliant_count = non_compliant
            reg.compliance_score = (compliant / len(assessed) * 100.0) if assessed else 0.0

    @api.constrains('company_id', 'facility_id')
    def _check_facility_company(self):
        for register in self:
            if register.facility_id.company_id != register.company_id:
                raise ValidationError(_('Legal register and facility must belong to the same company.'))

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get('state', 'draft') != 'draft' for vals in vals_list):
            raise UserError(_('Legal registers must be created in draft state.'))
        return super().create(vals_list)

    def write(self, vals):
        if 'evaluation_date' in vals or ('state' in vals and vals['state'] != 'archived'):
            raise UserError(_('Legal register lifecycle fields are managed by governed actions.'))
        return super().write(vals)

    def _check_hse_manager(self):
        if not self.env.user.has_group('insilos_hse_compliance.group_hse_manager'):
            raise UserError(_('Only HSE managers can evaluate or activate legal registers.'))

    def action_activate(self):
        self._check_hse_manager()
        for reg in self:
            pending = reg.obligation_ids.filtered(lambda o: o.compliance_status == 'not_assessed')
            unsupported = reg.obligation_ids.filtered(
                lambda o: (
                    not (o.evidence_summary or '').strip()
                    or not o.evidence_attachment_ids
                    or (o.compliance_status == 'compliant' and not o.compliance_approved_by_id)
                )
            )
            if not reg.obligation_ids or pending or unsupported:
                raise ValidationError(_(
                    'An active legal register requires evidence for every obligation and independent approval for compliant obligations.'
                ))
            super(HSELegalRegister, reg).write({
                'state': 'active',
                'evaluation_date': fields.Date.today(),
            })

    def action_evaluate_applicability(self):
        """Create applicable obligations pending a human compliance assessment."""
        self._check_hse_manager()
        self.ensure_one()
        facility = self.facility_id
        Obligation = self.env['is.hse.obligation']
        target_date = date(self.year, 12, 31) if self.year else fields.Date.today()
        docs = self.env['is.hse.legal.document'].search([
            ('state', '=', 'active'),
            ('authority_level', 'in', ('A1_MANDATORY_LAW', 'A2_MANDATORY_TECH_REG')),
        ]).filtered(lambda doc: doc.has_governed_provenance() and doc.is_effective_on(target_date))
        created = 0
        for doc in docs:
            for prov in doc.provision_ids:
                existing = Obligation.search([('register_id', '=', self.id), ('provision_id', '=', prov.id)], limit=1)
                if not existing:
                    Obligation.create({
                        'register_id': self.id,
                        'facility_id': facility.id,
                        'company_id': self.company_id.id,
                        'provision_id': prov.id,
                        'title': f"{prov.article_number}: {prov.title or prov.summary or 'Tuân thủ quy định'}",
                        'summary': prov.summary,
                        'compliance_status': 'not_assessed',
                    })
                    created += 1
        super(HSELegalRegister, self).write({'evaluation_date': fields.Date.today()})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Evaluation Completed'),
                'message': _('Added %d obligations pending compliance assessment to legal register.') % created,
                'sticky': False,
            }
        }


class HSEObligation(models.Model):
    _name = 'is.hse.obligation'
    _description = 'HSE Compliance Obligation Item'
    _order = 'register_id, category, id'

    register_id = fields.Many2one('is.hse.legal.register', string='Legal Register', required=True, ondelete='cascade')
    facility_id = fields.Many2one('is.hse.facility', related='register_id.facility_id', string='Facility', store=True, readonly=True)
    company_id = fields.Many2one('res.company', related='register_id.company_id', string='Company', store=True, readonly=True)
    provision_id = fields.Many2one('is.hse.legal.provision', string='Legal Provision Reference', ondelete='restrict')
    document_id = fields.Many2one('is.hse.legal.document', related='provision_id.document_id', string='Source Legal Document', store=True, readonly=True)
    authority_level = fields.Selection(related='provision_id.authority_level', string='Authority Level', store=True, readonly=True)
    category = fields.Selection(related='provision_id.category', string='Category', store=True, readonly=True)
    title = fields.Char(string='Obligation Title', required=True)
    summary = fields.Text(string='Obligation Details')
    frequency = fields.Selection([
        ('once', 'One-time Initial'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'), ('annual', 'Annual'), ('event_based', 'Event-Based / On-Demand'),
    ], string='Compliance Cadence', default='annual')
    compliance_status = fields.Selection([
        ('not_assessed', 'Pending Assessment (Chờ đánh giá)'),
        ('compliant', 'Compliant (Đạt)'),
        ('partial', 'Partially Compliant (Đạt một phần)'),
        ('non_compliant', 'Non-Compliant (Chưa đạt)'),
        ('not_applicable', 'Not Applicable (Không áp dụng)'),
    ], string='Compliance Status', default='not_assessed', required=True)
    responsible_user_id = fields.Many2one('res.users', string='Responsible Person', default=lambda self: self.env.user)
    due_date = fields.Date(string='Next Due Date')
    evidence_summary = fields.Text(string='Compliance Evidence Description')
    evidence_attachment_ids = fields.Many2many(
        'ir.attachment', 'is_hse_obligation_evidence_attachment_rel',
        'obligation_id', 'attachment_id', string='Evidence Attachments',
    )
    compliance_approved_by_id = fields.Many2one('res.users', string='Compliance Approved By', readonly=True)
    compliance_approved_at = fields.Datetime(string='Compliance Approved At', readonly=True)
    notes = fields.Text(string='Internal Notes')

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get('compliance_status') == 'compliant' for vals in vals_list):
            raise UserError(_('Compliant status requires HSE manager approval.'))
        return super().create(vals_list)

    @api.constrains('company_id', 'evidence_attachment_ids')
    def _check_evidence_company(self):
        for obligation in self:
            if obligation.evidence_attachment_ids.filtered(
                lambda attachment: attachment.company_id != obligation.company_id
            ):
                raise ValidationError(_('Evidence attachments must belong to the obligation company.'))

    def write(self, vals):
        protected_active_fields = {
            'compliance_status', 'due_date', 'provision_id', 'evidence_summary',
            'evidence_attachment_ids', 'title', 'summary', 'frequency',
            'responsible_user_id', 'register_id', 'notes',
        }
        if self.filtered(lambda obligation: obligation.register_id.state == 'active') and protected_active_fields & vals.keys():
            raise UserError(_('Active legal register obligations cannot be materially changed.'))
        if vals.get('compliance_status') == 'compliant':
            raise UserError(_('Compliant status requires HSE manager approval.'))
        if {'compliance_approved_by_id', 'compliance_approved_at'} & vals.keys():
            raise UserError(_('Compliance approval metadata is managed by the approval action.'))
        if self.filtered(lambda obligation: obligation.compliance_status == 'compliant') and {
            'evidence_summary', 'evidence_attachment_ids', 'responsible_user_id',
        } & vals.keys():
            raise UserError(_('Reset compliant status before changing approved evidence or assessment maker.'))
        if 'compliance_status' in vals:
            vals = dict(vals, compliance_approved_by_id=False, compliance_approved_at=False)
        return super().write(vals)

    def action_approve_compliance(self):
        if not self.env.user.has_group('insilos_hse_compliance.group_hse_manager'):
            raise UserError(_('Only HSE managers can approve compliant obligations.'))
        for obligation in self:
            if obligation.responsible_user_id == self.env.user:
                raise UserError(_('The HSE manager approving compliance must differ from the assessment maker.'))
            obligation.evidence_attachment_ids.check_access('read')
            obligation.evidence_attachment_ids.check_access_rule('read')
            if not (obligation.evidence_summary or '').strip() or not obligation.evidence_attachment_ids:
                raise ValidationError(_('Compliant status requires an evidence summary and at least one evidence attachment.'))
            super(HSEObligation, obligation).write({
                'compliance_status': 'compliant',
                'compliance_approved_by_id': self.env.user.id,
                'compliance_approved_at': fields.Datetime.now(),
            })
        return True
