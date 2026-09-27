# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class Tenant(models.Model):
    _name = 'insilos.tenant'
    _description = 'Tenant'
    _order = 'name'

    name = fields.Char(string='Tenant Name', required=True)
    slug = fields.Char(string='Subdomain Slug', required=True, index=True)
    db_name = fields.Char(string='Database Name', required=True, index=True)
    primary_domain = fields.Char(string='Primary Domain', required=True, index=True)
    db_uuid = fields.Char(string='DB UUID', required=True, index=True)
    environment = fields.Selection([
        ('production', 'Production'),
        ('staging', 'Staging'),
        ('development', 'Development')
    ], string='Environment', default='production', required=True)
    region = fields.Char(string='Region', default='ap-southeast-1', required=True)
    cluster = fields.Char(string='Cluster', default='insilos-k8s-vn-prod-01', required=True)
    last_reconciled_at = fields.Datetime(string='Last Reconciled At', readonly=True)
    reconciliation_evidence_uri = fields.Char(string='Reconciliation Evidence URI', readonly=True)
    template_id = fields.Many2one('insilos.industry.template', string='Industry Template', required=True, ondelete='restrict')
    release_id = fields.Many2one('insilos.template.release', string='Template Release', required=True, ondelete='restrict')
    desired_state = fields.Selection([
        ('provisioned', 'Provisioned'),
        ('suspended', 'Suspended'),
        ('deleted', 'Deleted')
    ], string='Desired State', default='provisioned', required=True)
    observed_state = fields.Selection([
        ('unknown', 'Unknown'),
        ('healthy', 'Healthy'),
        ('drifted', 'Drifted'),
        ('failed', 'Failed')
    ], string='Observed State', default='unknown', required=True)
    operation_ids = fields.One2many('insilos.tenant.operation', 'tenant_id', string='Operations')
    projection_ids = fields.One2many('project.project', 'tenant_id', string='Fleet Projection', readonly=True)

    # 30-Day Free Trial & Subscription Conversion Lifecycle
    tenant_type = fields.Selection([
        ('trial', '30-Day Free Trial'),
        ('paid', 'Active Paid Subscription'),
        ('partner', 'Partner / Sandbox'),
        ('internal', 'Internal / Demo')
    ], string='Tenant Type', default='trial', required=True, index=True)

    trial_started_at = fields.Datetime(string='Trial Started At', default=fields.Datetime.now)
    trial_ends_at = fields.Datetime(string='Trial Ends At')
    trial_days_left = fields.Integer(string='Trial Days Left', compute='_compute_trial_metrics', store=True)

    billing_state = fields.Selection([
        ('trial_active', 'Trial Active'),
        ('trial_expiring', 'Trial Expiring (<= 5 Days)'),
        ('grace_period', 'Grace Period (7 Days)'),
        ('suspended', 'Suspended (Payment Required)'),
        ('paid_active', 'Paid Active')
    ], string='Billing State', default='trial_active', required=True, index=True)

    paid_until = fields.Datetime(string='Paid Until')
    payment_provider_reference = fields.Char(readonly=True, copy=False)
    payment_callback_state = fields.Selection([
        ('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'), ('cancelled', 'Cancelled')
    ], readonly=True, copy=False)
    plan_tier = fields.Selection([
        ('starter', 'Starter'),
        ('standard', 'Standard'),
        ('enterprise', 'Enterprise')
    ], string='Plan Tier', default='standard', required=True)
    monthly_price = fields.Float(string='Monthly Price (VND)', default=990000.0)

    # Contact & Onboarding Metadata
    owner_name = fields.Char(string='Owner Name')
    owner_email = fields.Char(string='Admin Email')
    owner_phone = fields.Char(string='Owner Phone')
    company_size = fields.Selection([
        ('1-10', '1-10 nhân sự'),
        ('11-50', '11-50 nhân sự'),
        ('51-200', '51-200 nhân sự'),
        ('200+', 'Trên 200 nhân sự')
    ], string='Company Scale', default='11-50')

    _slug_unique = models.UniqueIndex('(slug)', 'Tenant slug must be unique.')
    _db_name_unique = models.UniqueIndex('(db_name)', 'Tenant database name must be unique.')
    _db_uuid_unique = models.UniqueIndex('(db_uuid)', 'Tenant database UUID must be unique.')
    _primary_domain_unique = models.UniqueIndex('(primary_domain)', 'Tenant primary domain must be unique.')

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if not vals.get('trial_started_at'):
                vals['trial_started_at'] = now
            if not vals.get('trial_ends_at') and vals.get('trial_started_at'):
                start_dt = fields.Datetime.from_string(vals['trial_started_at'])
                vals['trial_ends_at'] = start_dt + timedelta(days=30)
        return super().create(vals_list)

    @api.depends('trial_started_at', 'trial_ends_at', 'billing_state', 'paid_until', 'tenant_type')
    def _compute_trial_metrics(self):
        now = fields.Datetime.now()
        for tenant in self:
            if tenant.tenant_type == 'paid' or tenant.billing_state == 'paid_active':
                tenant.trial_days_left = 0
                if tenant.paid_until and tenant.paid_until < now:
                    tenant.billing_state = 'grace_period'
                continue

            if not tenant.trial_ends_at:
                tenant.trial_days_left = 30
                continue

            delta = tenant.trial_ends_at - now
            days = delta.days if delta.total_seconds() > 0 else 0
            tenant.trial_days_left = days

            if days > 5:
                tenant.billing_state = 'trial_active'
            elif 0 < days <= 5:
                tenant.billing_state = 'trial_expiring'
            elif days == 0:
                grace_end = tenant.trial_ends_at + timedelta(days=7)
                if now <= grace_end:
                    tenant.billing_state = 'grace_period'
                else:
                    tenant.billing_state = 'suspended'

    @api.constrains('db_uuid')
    def _check_db_uuid(self):
        for tenant in self:
            if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', tenant.db_uuid or ''):
                raise ValidationError(self.env._('Tenant database UUID must be a canonical lowercase UUID.'))

    @api.constrains('template_id', 'release_id')
    def _check_release_template(self):
        for tenant in self:
            if tenant.release_id.template_id != tenant.template_id:
                raise ValidationError(self.env._('The selected release must belong to the tenant template.'))
            if tenant.release_id.state != 'published':
                raise ValidationError(self.env._('Tenants must use a published template release.'))
            tenant.release_id._check_entitlement_contract({'enterprise'})

    def action_provision(self, idempotency_key=None, payload=None):
        self.ensure_one()
        if not self.env.user.has_group('insilos_tenant_control.group_tenant_requester'):
            raise AccessError(self.env._('Only tenant requesters can provision tenants.'))
        return self.env['insilos.tenant.operation'].queue_operation(self, 'provision', idempotency_key=idempotency_key, payload=payload)

    def action_verify_payment_callback(self, provider_reference, status, signature, duration_months=12):
        self.ensure_one()
        secret = self.env['ir.config_parameter'].sudo().get_param('insilos_tenant_control.payment_callback_secret')
        entitlement = f'{self.id}:{self.plan_tier}:{duration_months}'
        expected = hmac.new((secret or '').encode(), f'{provider_reference}:{status}:{entitlement}'.encode(), hashlib.sha256).hexdigest()
        if not secret or not provider_reference or not hmac.compare_digest(signature or '', expected):
            raise UserError(self.env._('Payment callback verification failed.'))
        if self.payment_provider_reference and self.payment_provider_reference != provider_reference:
            raise UserError(self.env._('A different payment reference was already processed.'))
        if self.payment_callback_state == 'paid':
            return False
        if self.payment_callback_state in ('failed', 'cancelled'):
            raise UserError(self.env._('Terminal payment callbacks cannot be reordered.'))
        if status not in ('paid', 'failed', 'cancelled'):
            raise UserError(self.env._('Unsupported payment callback status.'))
        self.write({'payment_provider_reference': provider_reference, 'payment_callback_state': status})
        if status != 'paid':
            return False
        self.action_convert_to_paid(duration_months=duration_months)
        return True

    def action_convert_to_paid(self, duration_months=12):
        """Converts tenant from free trial to active paid subscription."""
        self.ensure_one()
        now = fields.Datetime.now()
        paid_until = now + timedelta(days=duration_months * 30)
        self.write({
            'tenant_type': 'paid',
            'billing_state': 'paid_active',
            'desired_state': 'provisioned',
            'paid_until': paid_until,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Kích hoạt Bản quyền Thành công! 🌟',
                'message': f"Tenant {self.name} đã được nâng cấp lên gói {self.plan_tier} với hạn bản quyền đến {fields.Datetime.to_string(paid_until)}.",
                'type': 'success',
                'sticky': False,
            }
        }

    def action_extend_trial(self, extra_days=14):
        """Customer Success: Extends trial period for prospects."""
        self.ensure_one()
        now = fields.Datetime.now()
        base_date = self.trial_ends_at if (self.trial_ends_at and self.trial_ends_at > now) else now
        new_end = base_date + timedelta(days=extra_days)
        self.write({
            'trial_ends_at': new_end,
            'billing_state': 'trial_active',
            'desired_state': 'provisioned',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Gia hạn Dùng thử Thành công! ⏳',
                'message': f"Thời hạn dùng thử của {self.name} đã được gia hạn thêm {extra_days} ngày (đến {fields.Datetime.to_string(new_end)}).",
                'type': 'info',
                'sticky': False,
            }
        }

    @api.model
    def _cron_reconcile_tenant_trial_states(self):
        """Daily automated check of trial deadlines and suspension of expired tenants."""
        tenants = self.search([('tenant_type', '=', 'trial')])
        tenants._compute_trial_metrics()
        for t in tenants:
            if t.billing_state == 'suspended' and t.desired_state != 'suspended':
                t.desired_state = 'suspended'
                self.env['insilos.tenant.operation'].sudo().queue_operation(t, 'suspend')
