# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
import logging
import re
from datetime import date
from urllib.parse import urlparse

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from .is_hse_legal_document import _COMPLIANCE_EVENT_WRITE_CAPABILITY
from .is_hse_sync_log import _SYNC_LOG_CREATE_CAPABILITY

_logger = logging.getLogger(__name__)
_WORKFLOW_WRITE_TOKEN = object()
_EVENT_CREATE_TOKEN = object()


class HSEComplianceEvent(models.Model):
    _name = 'is.hse.compliance.event'
    _description = 'HSE Knowledge Compliance Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('is.hse.compliance.event') or 'HSE-EVT')
    event_id = fields.Char(string='Event UUID', required=True, index=True, tracking=True)
    _event_id_unique = models.Constraint('unique(event_id)', 'Event ID must be unique.')
    event_type = fields.Selection([
        ('hse.legal.published', 'Legal Document Published (Ban hành văn bản mới)'),
        ('hse.qcvn.updated', 'QCVN / Technical Regulation Updated (Cập nhật QCVN)'),
        ('hse.chemical.sds_updated', 'Chemical SDS / GHS Updated (Cập nhật SDS/GHS)'),
        ('hse.applicability.evaluated', 'Facility Applicability Evaluated (Kết quả đánh giá cơ sở)'),
        ('hse.general_notice', 'General Regulatory Notice (Thông báo chung)'),
    ], string='Event Type', required=True, default='hse.general_notice', tracking=True)

    received_date = fields.Datetime(string='Received At', default=fields.Datetime.now, readonly=True)
    event_payload = fields.Text(string='Raw Payload JSON', readonly=True)
    summary = fields.Char(string='Event Summary', compute='_compute_summary', store=True)
    affected_document_code = fields.Char(string='Affected Document Code', index=True)
    affected_facility_id = fields.Many2one('is.hse.facility', string='Affected Facility')
    company_id = fields.Many2one('res.company', related='affected_facility_id.company_id', store=True, readonly=True)
    reviewed_by_id = fields.Many2one('res.users', string='Reviewer', readonly=True, tracking=True)
    reviewed_date = fields.Datetime(string='Reviewed At', readonly=True, tracking=True)

    state = fields.Selection([
        ('new', 'New / Unreviewed'),
        ('reviewed', 'Reviewed (Đã xem xét)'),
        ('applied', 'Applied to Legal Register (Đã áp dụng)'),
        ('ignored', 'Ignored / Inapplicable (Bỏ qua)'),
    ], string='Status', default='new', tracking=True)

    @api.depends('event_type', 'event_payload')
    def _compute_summary(self):
        for ev in self:
            if not ev.event_payload:
                ev.summary = f"[{ev.event_type}] Event recorded"
                continue
            try:
                data = json.loads(ev.event_payload)
                doc = data.get('document', {})
                if doc:
                    ev.summary = f"{doc.get('code', '')}: {doc.get('name', '')}"
                elif data.get('substance'):
                    sub = data.get('substance', {})
                    ev.summary = f"Chemical: {sub.get('name', '')} (CAS: {sub.get('cas_number', '')})"
                else:
                    ev.summary = f"HSE Event {ev.event_type} received"
            except Exception:
                ev.summary = f"HSE Event {ev.event_type}"

    @api.model_create_multi
    def create(self, vals_list):
        # Keep direct ORM writes behind the same immediate DB replay barrier as webhooks.
        self.env.cr.execute('SELECT event_id FROM is_hse_compliance_event LIMIT 0')
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1
                  FROM pg_constraint c
                  JOIN pg_attribute a ON a.attrelid = c.conrelid
                     AND a.attname = 'event_id' AND NOT a.attisdropped
                  JOIN pg_index i ON i.indexrelid = c.conindid
                 WHERE c.conrelid = 'is_hse_compliance_event'::regclass
                   AND c.contype = 'u' AND c.convalidated AND NOT c.condeferrable
                   AND c.conkey = ARRAY[a.attnum]::smallint[]
                   AND i.indisunique AND i.indisvalid AND i.indisready
            )
        """)
        if not self.env.cr.fetchone()[0]:
            raise UserError(_('HSE event replay protection is unavailable.'))
        if self.env.context.get('_hse_event_create') is not _EVENT_CREATE_TOKEN:
            raise AccessError(_('Compliance evidence can only be received through a verified webhook.'))
        sanitized_vals_list = []
        for incoming_vals in vals_list:
            vals = incoming_vals.copy()
            vals['state'] = 'new'
            vals['received_date'] = fields.Datetime.now()
            for field in ('name', 'reviewed_by_id', 'reviewed_date'):
                vals.pop(field, None)
            sanitized_vals_list.append(vals)
        return super().create(sanitized_vals_list)

    def _create_from_signed_webhook(self, vals_list, capability):
        if capability is not _EVENT_CREATE_TOKEN:
            raise AccessError(_('Compliance evidence requires verified webhook capability.'))
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        return self.with_context(_hse_event_create=_EVENT_CREATE_TOKEN).create(vals_list)

    def write(self, vals):
        if set(vals) - {'state', 'reviewed_by_id', 'reviewed_date'}:
            raise UserError(_('Recorded compliance evidence is immutable.'))
        if self.env.context.get('_hse_workflow_write') is not _WORKFLOW_WRITE_TOKEN:
            raise UserError(_('Use the compliance workflow actions to change event status.'))
        for ev in self:
            if vals.get('state') == 'reviewed':
                if (ev.state != 'new' or vals.get('reviewed_by_id') != self.env.user.id
                        or not vals.get('reviewed_date')):
                    raise UserError(_('A review must record the current HSE manager from a new event.'))
            elif 'reviewed_by_id' in vals or 'reviewed_date' in vals:
                raise UserError(_('Review metadata can only be recorded when reviewing an event.'))
            if vals.get('state') == 'applied' and (ev.state != 'reviewed' or ev.reviewed_by_id == self.env.user):
                raise UserError(_('A reviewed event must be applied by a different HSE manager.'))
        return super().write(vals)

    def unlink(self):
        raise UserError(_('Recorded compliance evidence cannot be deleted.'))

    def _write_workflow(self, vals):
        return self.with_context(_hse_workflow_write=_WORKFLOW_WRITE_TOKEN).write(vals)

    def action_mark_reviewed(self):
        if not self.env.user.has_group('insilos_hse_compliance.group_hse_manager'):
            raise UserError(_('Only HSE managers can review compliance events.'))
        for ev in self:
            if ev.state != 'new':
                raise UserError(_('Only new compliance events can be reviewed.'))
            ev._write_workflow({
                'state': 'reviewed',
                'reviewed_by_id': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
            })

    def action_ignore(self):
        if not self.env.user.has_group('insilos_hse_compliance.group_hse_manager'):
            raise UserError(_('Only HSE managers can ignore compliance events.'))
        for ev in self:
            if ev.state == 'applied':
                raise UserError(_('An applied compliance event cannot be ignored.'))
            ev._write_workflow({'state': 'ignored'})

    def _validated_legal_document_payload(self, data):
        doc = data.get('document')
        if not isinstance(doc, dict):
            raise UserError(_('A structured legal document payload is required.'))
        required = ('code', 'name', 'issuer', 'authority_level', 'category', 'issued_date',
                    'effective_date', 'state', 'source_url', 'source_content_sha256',
                    'source_version', 'provisions')
        if any(not doc.get(field) for field in required):
            raise UserError(_('Legal document provenance and metadata must be explicit.'))
        text_fields = required[:-1]
        if any(not isinstance(doc[field], str) or not doc[field].strip() for field in text_fields):
            raise UserError(_('Legal document metadata must be non-empty text.'))
        if doc['authority_level'] not in dict(self.env['is.hse.legal.document']._fields['authority_level'].selection):
            raise UserError(_('Invalid legal document authority level.'))
        if doc['category'] not in dict(self.env['is.hse.legal.document']._fields['category'].selection):
            raise UserError(_('Invalid legal document category.'))
        if doc['state'] != 'active':
            raise UserError(_('Compliance events can only apply active verified legal documents.'))
        source = urlparse(doc['source_url'])
        if source.scheme != 'https' or not source.netloc or source.username or source.password:
            raise UserError(_('An official HTTPS source locator without credentials is required.'))
        if not re.fullmatch(r'[0-9a-f]{64}', doc['source_content_sha256']):
            raise UserError(_('Official content SHA-256 must be a lowercase 64-character hash.'))
        try:
            date.fromisoformat(doc['issued_date'])
            date.fromisoformat(doc['effective_date'])
        except (TypeError, ValueError):
            raise UserError(_('Issued and effective dates must use YYYY-MM-DD.'))
        if not isinstance(doc['provisions'], list) or not doc['provisions']:
            raise UserError(_('At least one legal provision is required.'))
        if any(not isinstance(provision, dict) or not provision.get('article_number') or not provision.get('title')
               or not provision.get('summary') for provision in doc['provisions']):
            raise UserError(_('Each legal provision requires article number, title, and summary.'))
        return doc

    def action_apply_to_legal_register(self):
        """Apply a reviewed event; reviewer and applier must be distinct."""
        if not self.env.user.has_group('insilos_hse_compliance.group_hse_manager'):
            raise UserError(_('Only HSE managers can apply events to the legal register.'))
        for ev in self:
            if ev.state != 'reviewed' or not ev.reviewed_by_id:
                raise UserError(_('A compliance event must be reviewed before it can be applied.'))
            if ev.event_type not in ('hse.legal.published', 'hse.qcvn.updated'):
                raise UserError(_('Only legal document or QCVN update events can be applied to the legal register.'))
            if ev.reviewed_by_id == self.env.user:
                raise UserError(_('The reviewer must be distinct from the user applying the event.'))
            if not ev.event_payload:
                raise UserError(_('A compliance event without payload cannot be applied.'))
            try:
                data = json.loads(ev.event_payload)
                doc_data = ev._validated_legal_document_payload(data)
                LegalDoc = self.env['is.hse.legal.document']
                doc = LegalDoc.search([('code', '=', doc_data['code'])], limit=1)
                vals = {
                    'name': doc_data['name'],
                    'code': doc_data['code'],
                    'authority_level': doc_data['authority_level'],
                    'issuer': doc_data['issuer'],
                    'category': doc_data['category'],
                    'issued_date': doc_data['issued_date'],
                    'effective_date': doc_data['effective_date'],
                    'source_url': doc_data['source_url'],
                    'source_content_sha256': doc_data['source_content_sha256'],
                    'source_version': doc_data['source_version'],
                }
                activate_document = not doc or doc.state != 'active'
                if doc and doc.state == 'active':
                    if (doc.source_content_sha256 == vals['source_content_sha256']
                            or doc.source_version == vals['source_version']):
                        raise UserError(_('An active legal document requires a distinct incoming hash and version.'))
                    doc._write_from_compliance_event(vals, _COMPLIANCE_EVENT_WRITE_CAPABILITY)
                elif not doc:
                    doc = LegalDoc.create(vals)
                else:
                    doc.write(vals)
                for p in doc_data['provisions']:
                    art = p['article_number']
                    prov = doc.provision_ids.filtered(lambda pr: pr.article_number == art)
                    p_vals = {
                        'document_id': doc.id,
                        'article_number': art,
                        'title': p['title'],
                        'summary': p['summary'],
                        'sanction_summary': p.get('sanction_summary', ''),
                    }
                    if not prov:
                        self.env['is.hse.legal.provision']._create_from_compliance_event(
                            [p_vals], _COMPLIANCE_EVENT_WRITE_CAPABILITY,
                        )
                    else:
                        prov._write_from_compliance_event(p_vals, _COMPLIANCE_EVENT_WRITE_CAPABILITY)
                if activate_document:
                    doc._activate_from_compliance_event(_COMPLIANCE_EVENT_WRITE_CAPABILITY)
                ev._write_workflow({'state': 'applied'})
                self.env['is.hse.sync.log'].sudo()._create_from_trusted_sync([{
                    'sync_channel': 'webhook',
                    'event_type': ev.event_type,
                    'status': 'success',
                    'message': f"Applied compliance event {ev.name} ({ev.event_id}) to Legal Document registry.",
                }], _SYNC_LOG_CREATE_CAPABILITY)
            except Exception as exc:
                _logger.error(f"Failed to apply HSE event {ev.name}: {exc}")
                raise UserError(_("Failed to apply compliance event: %s") % str(exc))
