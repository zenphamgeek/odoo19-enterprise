# -*- coding: utf-8 -*-
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class PubSubEventLog(models.Model):
    _name = 'is.pubsub.event.log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Pub/Sub Inbound Event Log & Deduplication Ledger'
    _order = 'create_date desc'

    event_id = fields.Char(required=True, index=True, copy=False)
    trace_id = fields.Char(index=True, copy=False)
    correlation_id = fields.Char(index=True, copy=False)
    causation_id = fields.Char(index=True, copy=False)
    aggregate_id = fields.Char(index=True, copy=False)
    aggregate_version = fields.Integer(copy=False)
    schema_name = fields.Char(copy=False)
    schema_hash = fields.Char(copy=False)
    classification = fields.Char(copy=False)
    consumer = fields.Char(required=True, default='default', index=True, copy=False)
    event_type = fields.Selection([
        ('email.inbound.crm_lead', 'Inbound Email: Quotation / CRM Lead'),
        ('email.inbound.vendor_quote', 'Inbound Email: Vendor Quotation / Price List'),
        ('email.inbound.chemical_sds', 'Inbound Email: Chemical MSDS / Compliance Declaration'),
        ('email.inbound.logistics_idp', 'Inbound Email: Logistics IDP Document Manifest'),
        ('finance.inbound.invoice', 'Inbound Invoice: Vendor Bill / E-Invoice XML'),
        ('finance.inbound.payment_advice', 'Inbound Payment: Bank Advice & Remittance'),
        ('logistics.customs.declaration', 'Inbound Customs: VNACCS E-Declaration'),
        ('esg.emissions.cems_alert', 'ESG Telemetry: CEMS Online Emissions Threshold Alert'),
        ('gmail.push.notification', 'Gmail Pub/Sub Push Notification'),
        ('general.event', 'General Event Notice'),
    ], default='general.event', required=True, index=True)
    source = fields.Char(default='gmail.pubsub', required=True)
    state = fields.Selection([
        ('received', 'Received'), ('processed', 'Processed'), ('ignored', 'Ignored'),
        ('failed', 'Failed'), ('requeued', 'Requeued'),
    ], default='received', required=True, index=True)
    priority = fields.Selection([('LOW', 'Low'), ('NORMAL', 'Normal'), ('HIGH', 'High'), ('URGENT', 'Urgent')], default='NORMAL')
    producer = fields.Char(default='hermes-agent-event-bus')
    sender_email = fields.Char(index=True)
    sender_name = fields.Char()
    subject = fields.Char()
    gcp_message_id = fields.Char(index=True, copy=False)
    history_id = fields.Char(copy=False)
    payload = fields.Text(groups='insilos_pubsub_bridge.group_pubsub_manager')
    ai_summary = fields.Text()
    ai_entities_json = fields.Text()
    target_model = fields.Char()
    target_res_id = fields.Integer()
    target_record_ref = fields.Char(compute='_compute_target_record_ref')
    retry_count = fields.Integer(default=0, readonly=True)
    max_retries = fields.Integer(default=3)
    last_retry_at = fields.Datetime(readonly=True)
    error_message = fields.Text(groups='insilos_pubsub_bridge.group_pubsub_manager')
    requeue_reason = fields.Text(readonly=True)
    requeue_generation = fields.Integer(default=0, readonly=True)
    requeued_from_id = fields.Many2one('is.pubsub.event.log', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, index=True, default=lambda self: self.env.company)

    _company_consumer_event_id_unique = models.Constraint(
        'unique(company_id, consumer, event_id)',
        'Pub/Sub Event ID must be unique per company and consumer.',
    )
    _aggregate_version_unique = models.Constraint(
        'unique(company_id, consumer, aggregate_id, aggregate_version)',
        'Aggregate version must be unique per company and consumer.',
    )

    @api.depends('target_model', 'target_res_id')
    def _compute_target_record_ref(self):
        for rec in self:
            rec.target_record_ref = f'{rec.target_model},{rec.target_res_id}' if rec.target_model and rec.target_res_id else False

    def _process_claimed_event(self):
        """Single processing path. Owning addons override this method for their event types."""
        self.ensure_one()
        if self.state != 'received':
            return self
        if self.aggregate_id and self.aggregate_version and self.aggregate_version > 1:
            previous = self.search_count([
                ('company_id', '=', self.company_id.id), ('consumer', '=', self.consumer),
                ('aggregate_id', '=', self.aggregate_id), ('aggregate_version', '=', self.aggregate_version - 1),
                ('state', '=', 'processed'),
            ])
            if not previous:
                self.error_message = _('Waiting for aggregate version %s.') % (self.aggregate_version - 1)
                return self
        handler = getattr(self, f"_handle_{self.event_type.replace('.', '_')}", None)
        target = handler() if handler else False
        self.write({
            'state': 'processed' if target else 'received',
            'target_model': target._name if target else False,
            'target_res_id': target.id if target else False,
        })
        return self

    def _entities(self):
        self.ensure_one()
        return json.loads(self.ai_entities_json or '{}')

    def _handle_email_inbound_crm_lead(self):
        return self.env['crm.lead'].sudo().create({
            'name': f'[AI Inbound] {self.subject}', 'contact_name': self.sender_name,
            'email_from': self.sender_email, 'description': self.ai_summary or '',
            'priority': '3' if self.priority in ('HIGH', 'URGENT') else '1',
        })

    def _handle_email_inbound_vendor_quote(self):
        partner = self.env['res.partner'].sudo().search([('email', '=ilike', self.sender_email)], limit=1)
        partner = partner or self.env['res.partner'].sudo().create({'name': self.sender_name or self.sender_email, 'email': self.sender_email, 'supplier_rank': 1})
        return self.env['purchase.order'].sudo().create({'partner_id': partner.id, 'origin': f'PubSub Inbound Quote: {self.subject}', 'notes': self.ai_summary or ''})

    def _handle_finance_inbound_invoice(self):
        entities = self._entities()
        partner = self.env['res.partner'].sudo().search([('email', '=ilike', self.sender_email)], limit=1)
        partner = partner or self.env['res.partner'].sudo().create({'name': self.sender_name or self.sender_email or 'Vendor', 'email': self.sender_email, 'supplier_rank': 1})
        return self.env['account.move'].sudo().create({'move_type': 'in_invoice', 'partner_id': partner.id, 'ref': entities.get('invoice_number') or f'INV-{self.event_id}', 'narration': self.ai_summary or ''})

    def _handle_finance_inbound_payment_advice(self):
        entities = self._entities()
        partner = self.env['res.partner'].sudo().search([('email', '=ilike', self.sender_email)], limit=1)
        amount = float(entities.get('amount') or 0)
        if not partner or amount <= 0:
            return False
        return self.env['account.payment'].sudo().create({'partner_id': partner.id, 'amount': amount, 'payment_type': 'inbound', 'partner_type': 'customer', 'memo': self.subject})

    def _handle_esg_emissions_cems_alert(self):
        return self.env['project.task'].sudo().create({'name': f'[CEMS ESG ALERT] {self.subject}', 'description': self.ai_summary or '', 'priority': '1'})

    def action_open_target_record(self):
        self.ensure_one()
        return self.target_model and self.target_res_id and {'type': 'ir.actions.act_window', 'res_model': self.target_model, 'res_id': self.target_res_id, 'view_mode': 'form', 'target': 'current'}

    def action_route_notification(self):
        for event in self:
            event.message_post(body=event.ai_summary or event.subject or event.event_type, message_type='notification', subtype_xmlid='mail.mt_note')
            if event.priority in ('HIGH', 'URGENT'):
                event.activity_schedule('mail.mail_activity_data_todo', summary=event.subject or _('Pub/Sub event requires action'))
        return True

    def action_requeue_event(self, reason=None):
        self.ensure_one()
        if not self.env.user.has_group('insilos_pubsub_bridge.group_pubsub_manager'):
            raise AccessError(_('Only Pub/Sub managers may requeue events.'))
        reason = (reason or self.env.context.get('requeue_reason') or '').strip()
        if not reason:
            raise ValidationError(_('A requeue reason is required.'))
        generation = self.requeue_generation + 1
        new = self.sudo().copy({
            'event_id': f'{self.event_id}:requeue:{generation}', 'state': 'received',
            'target_model': False, 'target_res_id': False, 'retry_count': 0,
            'requeue_reason': reason, 'requeue_generation': generation, 'requeued_from_id': self.id,
        })
        self.sudo().write({'state': 'requeued'})
        new._process_claimed_event()
        return new

    def action_replay_event(self):
        return self.action_requeue_event()

    def write(self, vals):
        protected = {
            'event_id', 'event_type', 'source', 'producer', 'payload', 'company_id', 'consumer',
            'trace_id', 'correlation_id', 'causation_id', 'aggregate_id', 'aggregate_version',
            'schema_name', 'schema_hash', 'classification', 'requeued_from_id',
        }
        if protected & set(vals) and any(record.id for record in self):
            raise AccessError(_('Inbound audit identity and payload are immutable.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.is_superuser():
            raise AccessError(_('Inbound audit records are immutable.'))
        return super().unlink()
