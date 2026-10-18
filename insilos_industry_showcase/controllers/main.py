# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import logging
import re
import uuid
from datetime import timedelta
from psycopg2 import IntegrityError

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

# RFC 1123 Hostname Label regex: lowercase alphanumeric with single internal hyphens, length 3 to 32
SLUG_REGEX = re.compile(r'^[a-z0-9](?:[a-z0-9]|-(?!-)){1,30}[a-z0-9]$')
RESERVED_SLUGS = frozenset({
    'admin', 'administrator', 'api', 'app', 'assets', 'billing', 'cdn',
    'core', 'dashboard', 'database', 'dev', 'internal', 'mail', 'portal',
    'root', 'router', 'secure', 'ssl', 'staging', 'static', 'system', 'vpn', 'www',
})


def sanitize_and_validate_slug(raw_slug: str) -> str:
    """Validate tenant slug against RFC 1123 specifications and security allowlists.
    Raises ValidationError on any invalid characters, double hyphens, or reserved names.
    """
    if not raw_slug or not isinstance(raw_slug, str):
        raise ValidationError("Tenant identifier cannot be empty.")

    normalized = raw_slug.strip().lower()
    if len(normalized) < 3 or len(normalized) > 32:
        raise ValidationError("Tenant identifier length must be between 3 and 32 characters.")

    if not SLUG_REGEX.match(normalized):
        raise ValidationError(
            "Tenant identifier contains invalid characters. Use lowercase letters, digits, and non-consecutive hyphens."
        )

    if normalized in RESERVED_SLUGS:
        raise ValidationError(f"Tenant identifier '{normalized}' is reserved by the platform.")

    return normalized


def compute_tenant_workspace_url(slug: str) -> str:
    """Build a canonical HTTPS workspace access URL without cleartext or internal debug ports."""
    valid_slug = sanitize_and_validate_slug(slug)
    base_domain = 'insilos.com'
    try:
        if request and getattr(request, 'env', None):
            base_domain = request.env['ir.config_parameter'].sudo().get_param(
                'insilos.saas.base_domain', 'insilos.com'
            ) or 'insilos.com'
    except Exception as exc:
        _logger.debug("Fallback to default base_domain insilos.com: %s", exc)
    clean_domain = base_domain.split('://')[-1].split('/')[0].split(':')[0].strip().lower() or 'insilos.com'
    return f"https://{valid_slug}.{clean_domain}/insilos"



class IndustryShowcaseController(http.Controller):

    @http.route(['/industry', '/industry/category/<string:category>'], type='http', auth="public", website=True)
    def industry_hub(self, category=None, search=None, **kwargs):
        """Renders the SAP-Style Master 101 Industry Showcase Hub page."""
        domain = []
        if search:
            domain.append(('name', 'ilike', search))

        landings = request.env['is.industry.landing'].sudo().search(domain)

        categories = {}
        for land in landings:
            cat = land.category_name or "General"
            if category and cat.lower() != category.lower():
                continue
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(land)

        featured_landings = landings[:4]

        values = {
            'categories': categories,
            'current_category': category,
            'search': search,
            'total_count': len(landings),
            'featured_landings': featured_landings,
        }
        return request.render('insilos_industry_showcase.industry_hub_template', values)

    @http.route('/industry/<string:slug>', type='http', auth="public", website=True)
    def industry_detail(self, slug, **kwargs):
        """Renders the industry conversion landing page for the given slug."""
        landing = request.env['is.industry.landing'].sudo().search([('slug', '=', slug)], limit=1)
        if not landing:
            return request.redirect(f"/industries/{slug}")

        features = landing.get_features_list()
        modules = landing.get_modules_list()

        values = {
            'landing': landing,
            'features': features,
            'modules': modules,
        }
        return request.render('insilos_industry_showcase.industry_detail_template', values)

    @http.route('/saas/signup', type='http', auth="public", website=True)
    def saas_signup(self, template_slug=None, plan='standard', **kwargs):
        """Renders the Self-Service SaaS Tenant 30-Day Free Trial Signup form."""
        templates = request.env['insilos.industry.template'].sudo().search([('active', '=', True)], order='name')
        selected_template = None
        if template_slug:
            selected_template = request.env['insilos.industry.template'].sudo().search([
                ('active', '=', True),
                '|', ('name', 'ilike', template_slug), ('code', 'ilike', template_slug)
            ], limit=1)
        if not selected_template and templates:
            selected_template = templates[0]

        values = {
            'templates': templates,
            'selected_template': selected_template,
            'selected_plan': plan,
            'error': kwargs.get('error'),
        }
        return request.render('insilos_industry_showcase.saas_signup_template', values)

    @http.route('/saas/signup/submit', type='http', auth="public", methods=['POST'], website=True, csrf=True, readonly=False)
    def saas_signup_submit(self, **post):
        """Handles SaaS Tenant creation with 30-day Free Trial."""
        company_name = post.get('company_name', '').strip()
        owner_name = post.get('owner_name', '').strip()
        owner_email = post.get('owner_email', '').strip()
        owner_phone = post.get('owner_phone', '').strip()
        subdomain = post.get('subdomain', '').strip().lower()
        template_slug = post.get('template_slug', '').strip().lower()
        plan_tier = post.get('plan_tier', 'standard')
        company_size = post.get('company_size', '11-50')
        idempotency_key = post.get('idempotency_key', '').strip()

        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9_-]{1,62}[a-z0-9])?', template_slug):
            return request.redirect(f"/saas/signup?error=template_invalid&plan={plan_tier}")
        try:
            slug = sanitize_and_validate_slug(subdomain)
        except ValidationError:
            return request.redirect(f"/saas/signup?error=subdomain_invalid&plan={plan_tier}")

        # DISM-TRL: Collision-resistant deterministic 64-bit signed advisory lock via SHA-256 (CWE-328 / CWE-400)
        lock_bytes = hashlib.sha256(f"insilos_tenant_provision:{slug}".encode('utf-8')).digest()[:8]
        lock_id = int.from_bytes(lock_bytes, byteorder='big', signed=True)
        request.env.cr.execute("SELECT pg_try_advisory_xact_lock(%s)", [lock_id])
        lock_res = request.env.cr.fetchone()
        if not (lock_res and lock_res[0]):
            return request.redirect(f"/saas/signup?error=system_busy&plan={plan_tier}")

        TenantModel = request.env['insilos.tenant'].sudo()
        # Cross-Tenant Idempotency Probing & Hijack Guard (CWE-284 / CWE-384)
        existing_operation = None
        if idempotency_key and owner_email and 'insilos.tenant.operation' in request.env:
            existing_ops = request.env['insilos.tenant.operation'].sudo().search([
                ('operation_type', '=', 'provision'),
                ('idempotency_key', '=', idempotency_key),
            ])
            for op in existing_ops:
                if op.tenant_id and op.tenant_id.owner_email == owner_email:
                    existing_operation = op
                    break
        # Double-check existing
        existing = TenantModel.search([('slug', '=', slug)], limit=1)
        if existing and (not existing_operation or existing_operation.tenant_id != existing):
            return request.redirect(f"/saas/signup?error=subdomain_taken&plan={plan_tier}")

        templates = request.env['insilos.industry.template'].sudo().search([('slug', '=', template_slug), ('active', '=', True)])
        if len(templates) != 1:
            return request.redirect(f"/saas/signup?error=template_invalid&plan={plan_tier}")
        template = templates[0]
        releases = request.env['insilos.template.release'].sudo().search([
            ('template_id', '=', template.id), ('state', '=', 'published')
        ])
        if len(releases) != 1:
            return request.redirect(f"/saas/signup?error=release_invalid&plan={plan_tier}")
        release = releases[0]
        try:
            release._check_entitlement_contract({'enterprise'})
        except (UserError, ValidationError, ValueError):
            return request.redirect(f"/saas/signup?error=release_invalid&plan={plan_tier}")

        # Database and Domain attributes
        db_name = f"insilos_tenant_{slug}"
        primary_domain = f"{slug}.insilos.com"
        db_uuid = str(uuid.uuid4()).lower()
        now = fields.Datetime.now()
        trial_ends_at = now + timedelta(days=30)

        prices = {
            'starter': 490000.0,
            'standard': 990000.0,
            'enterprise': 2490000.0,
        }
        monthly_price = prices.get(plan_tier, 990000.0)

        payload = {'slug': slug, 'template_slug': template_slug, 'release_id': release.id, 'plan_tier': plan_tier, 'owner_email': owner_email}
        if existing_operation:
            try:
                operation = request.env['insilos.tenant.operation'].sudo().queue_operation(
                    existing_operation.tenant_id, 'provision', idempotency_key=idempotency_key, payload=payload,
                )
            except UserError:
                return request.redirect(f"/saas/signup?error=idempotency_conflict&plan={plan_tier}")
            return request.redirect(f"/saas/signup/success?tenant_id={operation.tenant_id.id}&slug={operation.tenant_id.slug}&status=requested")

        try:
            with request.env.cr.savepoint():
                tenant = TenantModel.create({
                    'name': (company_name or f"Doanh nghiệp {slug.capitalize()}").strip()[:128],
                    'slug': slug,
                    'db_name': db_name,
                    'primary_domain': primary_domain,
                    'db_uuid': db_uuid,
                    'environment': 'production',
                    'region': 'ap-southeast-1',
                    'cluster': 'insilos-k8s-vn-prod-01',
                    'template_id': template.id,
                    'release_id': release.id,
                    'desired_state': 'provisioned',
                    'tenant_type': 'trial',
                    'billing_state': 'trial_active',
                    'trial_started_at': now,
                    'trial_ends_at': trial_ends_at,
                    'plan_tier': plan_tier,
                    'monthly_price': monthly_price,
                    'owner_name': (owner_name or '').strip()[:128],
                    'owner_email': (owner_email or '').strip()[:128],
                    'owner_phone': (owner_phone or '').strip()[:32],
                    'company_size': company_size,
                })

                if 'saas.workspace' in request.env:
                    request.env['saas.workspace'].sudo().create({
                        'subdomain': slug,
                        'tenant_id': tenant.id,
                        'state': 'provisioning',
                        'idempotency_hash': idempotency_key or '',
                    })

                operation = request.env['insilos.tenant.operation'].sudo().queue_operation(
                    tenant, 'provision', idempotency_key=idempotency_key or str(uuid.uuid4()), payload=payload,
                )
        except Exception as e:
            err_msg = str(e).lower()
            if 'unique' in err_msg or 'slug' in err_msg or 'subdomain' in err_msg or isinstance(e, IntegrityError):
                return request.redirect(f"/saas/signup?error=subdomain_taken&plan={plan_tier}")
            _logger.exception("SaaS Provisioning transaction failed for slug=%s: %s", slug, e)
            return request.redirect(f"/saas/signup?error=system_busy&plan={plan_tier}")

        return request.redirect(f"/saas/signup/success?tenant_id={tenant.id}&slug={slug}&status=requested&operation_id={operation.id}")

    @http.route('/saas/signup/success', type='http', auth="public", website=True, sitemap=False)
    def saas_signup_success(self, tenant_id=None, slug=None, **kwargs):
        """Confirmation and onboarding instruction page for the newly created tenant."""
        tenant = None
        if tenant_id:
            try:
                tenant = request.env['insilos.tenant'].sudo().browse(int(tenant_id))
                if not tenant.exists():
                    tenant = None
            except (ValueError, TypeError):
                tenant = None

        raw_slug = slug or (tenant.slug if tenant else None)
        try:
            valid_slug = sanitize_and_validate_slug(raw_slug) if raw_slug else 'workspace'
            workspace_url = compute_tenant_workspace_url(valid_slug)
        except ValidationError as exc:
            _logger.warning("Invalid slug '%s' passed to signup success page: %s", slug, exc)
            return request.redirect('/industry?error=invalid_tenant_slug')

        if not tenant and valid_slug:
            tenant = request.env['insilos.tenant'].sudo().search([('slug', '=', valid_slug)], limit=1)

        values = {
            'tenant': tenant,
            'slug': valid_slug,
            'tenant_workspace_url': workspace_url,
            'tenant_base_url': workspace_url.rsplit('/insilos', 1)[0],
        }
        return request.render('insilos_industry_showcase.saas_signup_success_template', values)

    @http.route('/saas/checkout/<int:tenant_id>', type='http', auth="public", website=True)
    def saas_checkout(self, tenant_id, **kwargs):
        """Checkout and conversion portal for 30-day trial completion."""
        tenant = request.env['insilos.tenant'].sudo().browse(tenant_id)
        if not tenant.exists():
            return request.not_found()

        values = {
            'tenant': tenant,
        }
        return request.render('insilos_industry_showcase.saas_checkout_template', values)

    @http.route('/saas/checkout/confirm', type='http', auth="public", methods=['POST'], website=True, csrf=True, readonly=False)
    def saas_checkout_confirm(self, tenant_id, billing_cycle='annual', payment_method='vnpay', **post):
        try:
            tid = int(tenant_id)
        except (ValueError, TypeError):
            return request.not_found()
        tenant = request.env['insilos.tenant'].sudo().browse(tid)
        if not tenant.exists() or billing_cycle not in ('annual', 'monthly') or payment_method not in ('vnpay', 'card', 'bank_transfer'):
            return request.not_found()
        return request.redirect(f"/saas/checkout/{tenant.id}?status=payment_pending")

    @http.route('/saas/checkout/callback', type='http', auth="public", methods=['POST'], website=False, csrf=False, readonly=False)
    def saas_checkout_callback(self, tenant_id, provider_reference, status, signature, billing_cycle='annual', **post):
        try:
            tid = int(tenant_id)
        except (ValueError, TypeError):
            return request.make_response('invalid', status=400)
        tenant = request.env['insilos.tenant'].sudo().browse(tid)
        if not tenant.exists() or billing_cycle not in ('annual', 'monthly'):
            return request.make_response('invalid', status=400)
        try:
            tenant.action_verify_payment_callback(provider_reference, status, signature, 12 if billing_cycle == 'annual' else 1)
        except UserError:
            return request.make_response('invalid', status=400)
        return request.make_response('ok')

    @http.route('/saas/checkout/success', type='http', auth="public", website=True, sitemap=False)
    def saas_checkout_success(self, tenant_id=None, **kwargs):
        """Success confirmation for paid subscription activation."""
        tenant = None
        if tenant_id:
            try:
                tenant = request.env['insilos.tenant'].sudo().browse(int(tenant_id))
                if not tenant.exists():
                    tenant = None
            except (ValueError, TypeError):
                tenant = None
        raw_slug = tenant.slug if tenant and tenant.slug else 'workspace'
        try:
            valid_slug = sanitize_and_validate_slug(raw_slug)
            workspace_url = compute_tenant_workspace_url(valid_slug)
        except ValidationError:
            valid_slug = 'workspace'
            workspace_url = 'https://workspace.insilos.com/insilos'
        values = {
            'tenant': tenant,
            'slug': valid_slug,
            'tenant_workspace_url': workspace_url,
            'tenant_base_url': workspace_url.rsplit('/insilos', 1)[0],
        }
        return request.render('insilos_industry_showcase.saas_checkout_success_template', values)
