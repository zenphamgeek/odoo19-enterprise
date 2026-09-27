# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
import logging
import re
import time
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PubSubAutomationRule(models.Model):
    _name = 'is.pubsub.automation.rule'
    _description = 'Pub/Sub Automation Rule, Call Forwarding & Action Router'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True, default=lambda self: self.env.company,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('disabled', 'Disabled'),
    ], string='Rule State', default='active', required=True, index=True)

    # Trigger Conditions
    event_type_filter = fields.Selection([
        ('all', 'All Inbound Events (*)'),
        ('email.inbound.crm_lead', 'Quotation Inquiry / CRM Lead'),
        ('email.inbound.vendor_quote', 'Vendor Quotation / Price List'),
        ('email.inbound.chemical_sds', 'Chemical MSDS / SDS Compliance'),
        ('email.inbound.logistics_idp', 'Logistics IDP Manifest'),
        ('finance.inbound.invoice', 'Inbound Vendor Bill / Invoice XML'),
        ('finance.inbound.payment_advice', 'Inbound Bank Payment Advice'),
        ('logistics.customs.declaration', 'Inbound VNACCS Customs Declaration'),
        ('esg.emissions.cems_alert', 'ESG CEMS Online Exceedance Alert'),
        ('gmail.push.notification', 'Gmail Push Notification'),
    ], string='Event Type Trigger', default='all', required=True)

    sender_filter = fields.Char(string='Sender Filter (Domain/Email Regex)',
                                help='Match sender email or domain, e.g. @hapag-lloyd.com, partner.*')
    keyword_filter = fields.Char(string='Subject / Body Keyword Filter',
                                help='Comma-separated keywords to filter, e.g. Toluene, Bill of Lading, RFQ')

    # Actions Execution
    action_type = fields.Selection([
        ('route_model', '1. Dispatch to ERP Business Model'),
        ('call_forward', '2. Call Forward / Webhook Forwarding'),
        ('telegram_alert', '3. Send Instant Telegram Alert'),
        ('email_notify', '4. Send Email Notification'),
        ('multi_action', '5. Multi-Action (Dispatch + Forward + Alert)'),
    ], string='Action Execution Mode', default='multi_action', required=True)

    target_model = fields.Selection([
        ('crm.lead', 'CRM Lead (crm.lead)'),
        ('purchase.order', 'Purchase Order RFQ (purchase.order)'),
        ('account.move', 'Vendor Bill / Invoice (account.move)'),
        ('account.payment', 'Payment Voucher (account.payment)'),
        ('is.hse.chemical.substance', 'HSE Chemical Substance (is.hse.chemical.substance)'),
        ('is.hse.sds', 'Safety Data Sheet (is.hse.sds)'),
        ('logistics.idp.case', 'Logistics IDP Case (logistics.idp.case)'),
        ('project.task', 'Project Task / CAPA (project.task)'),
    ], string='Target ERP Model', default='crm.lead')

    # Call Forwarding Configuration
    call_forward_enabled = fields.Boolean(string='Enable Call Forwarding', default=False)
    forward_url = fields.Char(string='Forward Destination URL', help='e.g. http://10.123.214.220:8000/webhook/ingest')
    forward_http_method = fields.Selection([('POST', 'POST'), ('PUT', 'PUT')], string='HTTP Method', default='POST')
    forward_auth_header = fields.Char(
        string='Authorization Header / API Key', help='e.g. Bearer eyJhbGciOi...',
        groups='insilos_pubsub_bridge.group_pubsub_manager',
    )
    forward_timeout_sec = fields.Integer(string='HTTP Timeout (Seconds)', default=10)

    # Telegram Alert Configuration
    telegram_alert_enabled = fields.Boolean(string='Enable Telegram Alerts', default=False)
    telegram_bot_token = fields.Char(
        string='Telegram Bot Token', help='Leave blank to use system parameter insilos_pubsub.telegram_bot_token',
        groups='insilos_pubsub_bridge.group_pubsub_manager',
    )
    telegram_chat_id = fields.Char(string='Telegram Chat ID', default='1431349185')
    telegram_message_template = fields.Text(string='Message Template', default="""⚡ <b>[PUBSUB EVENT ALERT]</b>
<b>Event:</b> ${event_type}
<b>From:</b> ${sender_email} (${sender_name})
<b>Subject:</b> ${subject}
<b>AI Summary:</b> ${ai_summary}""")

    # Email Notification Configuration
    email_notify_enabled = fields.Boolean(string='Enable Email Notification', default=False)
    email_notify_to = fields.Char(string='Notify Email To',
                                  help='Comma-separated email addresses for notifications')
    email_notify_subject_template = fields.Char(
        string='Email Subject Template',
        default='[PubSub Alert] ${event_type}: ${subject}',
    )

    # Retry Configuration
    max_retries = fields.Integer(string='Max Retries', default=0,
                                 help='Number of retry attempts on failure. 0 = no retry.')
    retry_delay_sec = fields.Integer(string='Retry Delay (seconds)', default=30)

    execution_count = fields.Integer(string='Total Executions', readonly=True, default=0)
    success_count = fields.Integer(string='Successful Runs', readonly=True, default=0)
    failed_count = fields.Integer(string='Failed Runs', readonly=True, default=0)
    last_executed_at = fields.Datetime(string='Last Executed At', readonly=True)

    forward_log_ids = fields.One2many('is.pubsub.forward.log', 'rule_id', string='Forwarding History')

    # ── Filter Evaluation ───────────────────────────────────────────────

    def matches_event(self, event_log):
        """Evaluate whether this rule's filters match a given event log.

        Returns True if all configured filters (event_type, sender, keyword)
        pass, or False if any filter rejects the event.
        """
        self.ensure_one()

        # 1. Event type filter
        if self.event_type_filter and self.event_type_filter != 'all':
            if event_log.event_type != self.event_type_filter:
                return False

        # 2. Sender filter (regex match on email)
        if self.sender_filter and self.sender_filter.strip():
            sender = event_log.sender_email or ''
            pattern = self.sender_filter.strip()
            try:
                if not re.search(pattern, sender, re.IGNORECASE):
                    return False
            except re.error:
                # Fallback: simple substring match
                if pattern.lower() not in sender.lower():
                    return False

        # 3. Keyword filter (any keyword must appear in subject or ai_summary)
        if self.keyword_filter and self.keyword_filter.strip():
            keywords = [kw.strip().lower() for kw in self.keyword_filter.split(',') if kw.strip()]
            if keywords:
                search_text = f"{event_log.subject or ''} {event_log.ai_summary or ''}".lower()
                if not any(kw in search_text for kw in keywords):
                    return False

        return True

    # ── Execution ───────────────────────────────────────────────────────

    def execute_rule(self, event_log):
        """Execute automation actions for a matched event log."""
        self.ensure_one()

        # Skip if rule is not active
        if self.state != 'active':
            return False

        # Evaluate filters first
        if not self.matches_event(event_log):
            return False

        self.execution_count += 1
        self.last_executed_at = fields.Datetime.now()

        try:
            # 1. Execute Call Forwarding if configured
            if self.call_forward_enabled and self.forward_url:
                self._execute_call_forward(event_log)

            # 2. Execute Telegram Alert if configured
            if self.telegram_alert_enabled and self.telegram_chat_id:
                self._execute_telegram_alert(event_log)

            # 3. Execute Email Notification if configured
            if self.email_notify_enabled and self.email_notify_to:
                self._execute_email_notify(event_log)

            self.success_count += 1
            return True

        except Exception as exc:
            self.failed_count += 1
            _logger.error("Rule '%s' execution failed: %s", self.name, exc)

            # Retry logic
            if self.max_retries > 0:
                for attempt in range(1, self.max_retries + 1):
                    try:
                        import time as _time
                        _time.sleep(min(self.retry_delay_sec * attempt, 120))
                        if self.call_forward_enabled and self.forward_url:
                            self._execute_call_forward(event_log)
                        self.success_count += 1
                        _logger.info("Rule '%s' retry #%d succeeded.", self.name, attempt)
                        return True
                    except Exception:
                        continue

            return False

    def _execute_call_forward(self, event_log):
        headers = {'Content-Type': 'application/json'}
        if self.forward_auth_header:
            headers['Authorization'] = self.forward_auth_header

        payload = {
            "event_id": event_log.event_id,
            "event_type": event_log.event_type,
            "source": event_log.source,
            "sender_email": event_log.sender_email,
            "sender_name": event_log.sender_name,
            "subject": event_log.subject,
            "ai_summary": event_log.ai_summary,
            "ai_entities": json.loads(event_log.ai_entities_json) if event_log.ai_entities_json else {},
            "target_model": event_log.target_model,
            "target_res_id": event_log.target_res_id,
            "forwarded_at": fields.Datetime.now().isoformat(),
        }

        start_time = time.time()
        http_status = 0
        response_text = ''
        state = 'success'
        error_msg = False

        try:
            resp = requests.request(
                self.forward_http_method,
                self.forward_url,
                json=payload,
                headers=headers,
                timeout=self.forward_timeout_sec or 10
            )
            http_status = resp.status_code
            response_text = resp.text[:2000]
            if resp.status_code not in (200, 201, 202):
                state = 'failed'
                error_msg = f"HTTP Error {resp.status_code}: {resp.text[:500]}"
        except Exception as exc:
            state = 'failed'
            error_msg = str(exc)
            _logger.error("Pub/Sub Call Forward failed to %s: %s", self.forward_url, exc)

        latency = (time.time() - start_time) * 1000.0

        self.env['is.pubsub.forward.log'].sudo().create({
            'rule_id': self.id,
            'event_log_id': event_log.id,
            'forward_url': self.forward_url,
            'http_status': http_status,
            'response_body': response_text,
            'latency_ms': latency,
            'state': state,
            'error_message': error_msg,
        })
        if state == 'failed':
            raise UserError(error_msg)

    def _execute_telegram_alert(self, event_log):
        token = self.telegram_bot_token or self.env['ir.config_parameter'].sudo().get_param('insilos_pubsub.telegram_bot_token')
        if not token:
            _logger.info("Telegram alert skipped: bot token not configured.")
            return

        msg = (self.telegram_message_template or '')
        msg = msg.replace('${event_type}', str(event_log.event_type or ''))
        msg = msg.replace('${sender_email}', str(event_log.sender_email or ''))
        msg = msg.replace('${sender_name}', str(event_log.sender_name or ''))
        msg = msg.replace('${subject}', str(event_log.subject or ''))
        msg = msg.replace('${ai_summary}', str(event_log.ai_summary or ''))

        try:
            tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(tg_url, json={
                'chat_id': self.telegram_chat_id,
                'text': msg,
                'parse_mode': 'HTML',
            }, timeout=5)
        except Exception as exc:
            _logger.warning("PubSub Telegram alert failed: %s", exc)

    def _execute_email_notify(self, event_log):
        """Send email notification for matched events."""
        if not self.email_notify_to:
            return

        subject = (self.email_notify_subject_template or '[PubSub Alert] ${event_type}')
        subject = subject.replace('${event_type}', str(event_log.event_type or ''))
        subject = subject.replace('${subject}', str(event_log.subject or ''))

        body_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 16px;">
            <h2 style="color: #0B2E64;">⚡ Pub/Sub Event Alert</h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 12px;">
                <tr><td style="padding: 6px; font-weight: bold;">Event Type:</td><td style="padding: 6px;">{event_log.event_type}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">From:</td><td style="padding: 6px;">{event_log.sender_email} ({event_log.sender_name})</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Subject:</td><td style="padding: 6px;">{event_log.subject}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Priority:</td><td style="padding: 6px;">{event_log.priority}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">AI Summary:</td><td style="padding: 6px;">{event_log.ai_summary or 'N/A'}</td></tr>
            </table>
            <p style="margin-top: 16px; color: #666;">— Insilos Pub/Sub Gateway</p>
        </div>
        """

        recipients = [e.strip() for e in self.email_notify_to.split(',') if e.strip()]
        for email_to in recipients:
            try:
                self.env['mail.mail'].sudo().create({
                    'subject': subject,
                    'body_html': body_html,
                    'email_from': self.env.company.email or 'noreply@insilos.com',
                    'email_to': email_to,
                    'auto_delete': True,
                }).send()
            except Exception as exc:
                _logger.warning("Email notification to %s failed: %s", email_to, exc)

    def action_test_rule(self):
        """Simulate automation rule execution with a dummy event log."""
        self.ensure_one()
        EventLog = self.env['is.pubsub.event.log']
        test_log = EventLog.search([('event_type', '=', self.event_type_filter if self.event_type_filter != 'all' else 'email.inbound.crm_lead')], limit=1)
        if not test_log:
            test_log = EventLog.create({
                'event_id': f"test-rule-evt-{fields.Datetime.now()}",
                'event_type': 'email.inbound.crm_lead',
                'sender_email': 'test@partner.com',
                'sender_name': 'Test Partner',
                'subject': 'Simulated Test Event for Automation Rule',
                'ai_summary': 'This is a simulated AI extraction test summary.',
                'state': 'processed',
            })
        self.execute_rule(test_log)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Rule Executed Successfully"),
                'message': _("Executed automation actions for rule %s.") % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_activate(self):
        self.write({'state': 'active'})

    def action_disable(self):
        self.write({'state': 'disabled'})
