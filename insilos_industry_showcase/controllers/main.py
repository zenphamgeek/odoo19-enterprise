# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import logging
import re
import time
import unicodedata
import uuid
from datetime import timedelta
from psycopg2 import IntegrityError

from odoo import fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

# RFC 1123 Hostname Label regex: lowercase ASCII alphanumeric with single internal hyphens, length 3 to 32
SLUG_REGEX = re.compile(r'^[a-z0-9](?:[a-z0-9]|-(?!-)){1,30}[a-z0-9]$', re.ASCII)

# Hardened reserved directory: infrastructure, cloud orchestrators, observability, and core Odoo HTTP routing endpoints
RESERVED_SLUGS = frozenset({
    'admin', 'administrator', 'airflow', 'alertmanager', 'api', 'app', 'argocd',
    'assets', 'auth', 'autoconfig', 'autodiscover', 'billing', 'blog', 'caddy',
    'cdn', 'consul', 'core', 'cpanel', 'dashboard', 'database', 'dev', 'dns',
    'docker', 'elastic', 'elasticsearch', 'envoy', 'event', 'forum', 'ftp',
    'git', 'github', 'gitlab', 'grafana', 'health', 'healthz', 'idp', 'im_livechat',
    'imap', 'internal', 'jaeger', 'jsonrpc', 'k8s', 'keycloak', 'kibana',
    'kubernetes', 'ldap', 'login', 'logout', 'loki', 'longpolling', 'mail',
    'metrics', 'mx', 'nginx', 'none', 'ns1', 'ns2', 'null', 'oauth', 'onboarding',
    'pop3', 'portal', 'postmaster', 'prefect', 'prometheus', 'registry', 'root',
    'router', 'saml', 'secure', 'shop', 'signin', 'signup', 'sso', 'ssl',
    'staging', 'static', 'status', 'system', 'tempo', 'test', 'traefik',
    'undefined', 'vault', 'vpn', 'web', 'websocket', 'wpad', 'www', 'xmlrpc',
})

SIGNUP_TOKEN_TTL_SECONDS = 1800          # 30-minute validation window for tenant onboarding
MAX_ALLOWED_CLOCK_SKEW_SECONDS = 300     # 5-minute tolerance for distributed fleet clock drift
HMAC_ONBOARDING_CONTEXT = b"insilos:tenant:onboarding:hmac-sha256:v1"
HMAC_LEASE_CONTEXT = b"insilos:sovereign:lease:hmac-sha256:v1"
_CONSUMED_ONBOARDING_NONCES = set()
_CONSUMED_ONBOARDING_NONCE_EXPIRY = {}
MAX_IN_MEMORY_NONCE_ENTRIES = 4096


def sanitize_and_validate_slug(raw_slug: str) -> str:
    """Validate tenant slug against RFC 1123 specifications and security allowlists.
    Enforces NFKC normalization, ASCII constraints, and reserved slug protection.
    """
    if not raw_slug or not isinstance(raw_slug, str):
        raise ValidationError("Tenant identifier cannot be empty.")

    normalized = unicodedata.normalize('NFKC', raw_slug).strip().lower()
    if len(normalized) < 3 or len(normalized) > 32:
        raise ValidationError("Tenant identifier length must be between 3 and 32 characters.")

    if not SLUG_REGEX.match(normalized):
        raise ValidationError(
            "Tenant identifier contains invalid characters. Use lowercase letters, digits, and non-consecutive hyphens."
        )

    if normalized in RESERVED_SLUGS:
        raise ValidationError(f"Tenant identifier '{normalized}' is reserved by the platform.")

    return normalized


def _resolve_onboarding_hmac_secret(env) -> str:
    """Retrieve the platform signing secret from ir.config_parameter without static key literals."""
    secret = None
    try:
        if env is not None:
            secret = env['ir.config_parameter'].sudo().get_param('database.secret')
    except Exception as exc:
        _logger.warning("Failed to read database.secret from ir.config_parameter: %s", exc)
    if not secret or not isinstance(secret, str) or not secret.strip():
        raise ValidationError("Missing database.secret configuration parameter for HMAC token signing.")
    return secret.strip()


def _derive_domain_hmac_secret(env, domain_context: bytes) -> bytes:
    """Derive an isolated, purpose-specific HMAC subkey from the platform root secret
    using HKDF-style context extraction to prevent cross-protocol signature forgery.
    """
    raw_root_secret = _resolve_onboarding_hmac_secret(env)
    return hmac.new(
        raw_root_secret.encode('utf-8'),
        bytes(domain_context),
        hashlib.sha256,
    ).digest()


def _ensure_nonce_ledger_table(cr):
    """Ensure the persistent PostgreSQL nonce ledger table exists with proper indexes."""
    cr.execute("""
        CREATE TABLE IF NOT EXISTS insilos_consumed_nonce (
            nonce VARCHAR(64) PRIMARY KEY,
            tenant_id INTEGER NOT NULL,
            slug VARCHAR(64) NOT NULL,
            expiry_ts BIGINT NOT NULL,
            consumed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
        );
        CREATE INDEX IF NOT EXISTS idx_insilos_consumed_nonce_expiry
            ON insilos_consumed_nonce (expiry_ts);
    """)


def _record_consumed_nonce_persistent(cr, nonce: str, tenant_id: int, slug: str, expiry_ts: int) -> bool:
    """Atomically record a consumed nonce in PostgreSQL.
    Returns True if the nonce was successfully recorded (first use).
    Returns False if the nonce was already consumed (replay detected).
    """
    _ensure_nonce_ledger_table(cr)
    now_ts = int(time.time())
    cr.execute(
        "DELETE FROM insilos_consumed_nonce WHERE expiry_ts < %s",
        (now_ts - MAX_ALLOWED_CLOCK_SKEW_SECONDS,),
    )
    cr.execute("""
        INSERT INTO insilos_consumed_nonce (nonce, tenant_id, slug, expiry_ts, consumed_at)
        VALUES (%s, %s, %s, %s, NOW() AT TIME ZONE 'UTC')
        ON CONFLICT (nonce) DO NOTHING;
    """, (nonce, tenant_id, slug, expiry_ts))
    return cr.rowcount > 0


def _prune_in_memory_nonces(now_ts: int):
    """Evict expired nonces and bound in-memory fallback cache size to prevent heap DoS."""
    cutoff = now_ts - MAX_ALLOWED_CLOCK_SKEW_SECONDS
    expired = [n for n, exp in list(_CONSUMED_ONBOARDING_NONCE_EXPIRY.items()) if exp < cutoff]
    for n in expired:
        _CONSUMED_ONBOARDING_NONCE_EXPIRY.pop(n, None)
        _CONSUMED_ONBOARDING_NONCES.discard(n)
    if len(_CONSUMED_ONBOARDING_NONCES) > MAX_IN_MEMORY_NONCE_ENTRIES:
        oldest = sorted(_CONSUMED_ONBOARDING_NONCE_EXPIRY.items(), key=lambda kv: kv[1])[
            : len(_CONSUMED_ONBOARDING_NONCES) - MAX_IN_MEMORY_NONCE_ENTRIES
        ]
        for n, _ in oldest:
            _CONSUMED_ONBOARDING_NONCE_EXPIRY.pop(n, None)
            _CONSUMED_ONBOARDING_NONCES.discard(n)


def generate_signup_token(env, tenant_id: int, slug: str, self_contained: bool = False) -> str:
    """Generate a domain-separated HMAC-SHA256 signature for secure unauthenticated confirmation routing.
    Includes a unique cryptographically secure 128-bit nonce to prevent replay attacks.
    Format (default): <expiry>.<nonce>.<signature>
    Format (self_contained=True): <tenant_id>.<clean_slug>.<expiry>.<nonce>.<signature>
    """
    if isinstance(tenant_id, bool) or not isinstance(tenant_id, int) or tenant_id <= 0:
        raise ValidationError("Tenant ID must be a positive integer.")

    clean_slug = sanitize_and_validate_slug(slug)
    signing_key = _derive_domain_hmac_secret(env, HMAC_ONBOARDING_CONTEXT)
    now_ts = int(time.time())
    expiry = now_ts + SIGNUP_TOKEN_TTL_SECONDS
    nonce = uuid.uuid4().hex  # 32-char cryptographic nonce

    message = f"{tenant_id}:{clean_slug}:{expiry}:{nonce}".encode('utf-8')
    signature = hmac.new(signing_key, message, hashlib.sha256).hexdigest()
    if self_contained:
        return f"{tenant_id}.{clean_slug}.{expiry}.{nonce}.{signature}"
    return f"{expiry}.{nonce}.{signature}"


def generate_self_contained_signup_token(env, tenant_id: int, slug: str) -> str:
    """Generate a 5-part self-contained signup token encapsulating tenant_id and slug."""
    return generate_signup_token(env, tenant_id, slug, self_contained=True)


def validate_and_consume_signup_token(env, token: str) -> dict:
    """Validate a self-contained 5-part signup token and atomically consume its nonce.
    Format: <tenant_id>.<clean_slug>.<expiry>.<nonce>.<signature>
    Returns:
        dict: {'tenant_id': int, 'slug': str, 'expiry': int, 'nonce': str}
    Raises:
        AccessError: If the token is invalid, expired, tampered, or replayed.
    """
    if not token or not isinstance(token, str):
        raise AccessError("Invalid onboarding confirmation token: empty or wrong type.")

    parts = token.strip().split('.')
    if len(parts) != 5:
        raise AccessError("Invalid onboarding confirmation token: malformed envelope structure.")

    raw_tenant_id, raw_slug, raw_expiry, nonce, signature = parts

    try:
        tenant_id = int(raw_tenant_id)
        if tenant_id <= 0:
            raise ValueError()
    except ValueError:
        raise AccessError("Invalid onboarding confirmation token: illegal tenant identifier.")

    try:
        clean_slug = sanitize_and_validate_slug(raw_slug)
    except ValidationError as exc:
        raise AccessError(f"Invalid onboarding confirmation token: {exc}")

    try:
        expiry = int(raw_expiry)
    except ValueError:
        raise AccessError("Invalid onboarding confirmation token: corrupt timestamp.")

    now_ts = int(time.time())
    if now_ts > expiry + MAX_ALLOWED_CLOCK_SKEW_SECONDS:
        raise AccessError("Onboarding confirmation token has expired.")
    if expiry > now_ts + SIGNUP_TOKEN_TTL_SECONDS + MAX_ALLOWED_CLOCK_SKEW_SECONDS:
        raise AccessError("Onboarding confirmation token has an invalid future timestamp.")

    if not re.fullmatch(r'^[a-f0-9]{32}$', nonce):
        raise AccessError("Invalid onboarding confirmation token: illegal nonce format.")

    if not re.fullmatch(r'^[a-f0-9]{64}$', signature):
        raise AccessError("Invalid onboarding confirmation token: illegal signature format.")

    signing_key = _derive_domain_hmac_secret(env, HMAC_ONBOARDING_CONTEXT)
    expected_message = f"{tenant_id}:{clean_slug}:{expiry}:{nonce}".encode('utf-8')
    expected_signature = hmac.new(signing_key, expected_message, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise AccessError("Onboarding confirmation token signature verification failed.")

    cr = getattr(env, 'cr', None) if env is not None else None
    if cr is None:
        raise AccessError("Database cursor unavailable for nonce replay verification.")

    is_fresh = _record_consumed_nonce_persistent(cr, nonce, tenant_id, clean_slug, expiry)
    if not is_fresh:
        raise AccessError("Onboarding confirmation token has already been consumed (replay rejected).")

    return {
        'tenant_id': tenant_id,
        'slug': clean_slug,
        'expiry': expiry,
        'nonce': nonce,
    }


def verify_signup_token(env, tenant_id: int, slug: str, token: str, consume: bool = False) -> bool:
    """Verify onboarding token validity, clock drift tolerance, and cryptographic tamper resistance.
    Supports both 3-part (<expiry>.<nonce>.<signature>) and 5-part (<tenant_id>.<slug>.<expiry>.<nonce>.<signature>).
    If consume=True, records the token nonce to enforce strictly-once consumption semantics.
    """
    if not token or not isinstance(token, str) or token.count('.') not in (2, 4):
        _logger.warning("Rejected token with invalid envelope format for tenant_id=%s", tenant_id)
        return False

    if isinstance(tenant_id, bool) or not isinstance(tenant_id, int) or tenant_id <= 0:
        _logger.warning("Rejected token verification with non-positive or non-integer tenant_id=%s", tenant_id)
        return False

    try:
        clean_slug = sanitize_and_validate_slug(slug)
        if token.count('.') == 4:
            tok_tid, tok_slug, expiry_str, nonce, signature = token.split('.', 4)
            if int(tok_tid) != tenant_id or sanitize_and_validate_slug(tok_slug) != clean_slug:
                return False
        else:
            expiry_str, nonce, signature = token.split('.', 2)
        expiry = int(expiry_str)

        if len(nonce) != 32 or not re.fullmatch(r'^[a-f0-9]{32}$', nonce):
            _logger.warning("Rejected onboarding token with malformed nonce for tenant_id=%s", tenant_id)
            return False

        if len(signature) != 64 or not re.fullmatch(r'^[a-f0-9]{64}$', signature):
            _logger.warning("Rejected onboarding token with malformed signature for tenant_id=%s", tenant_id)
            return False

        now_ts = int(time.time())
        if now_ts > expiry:
            _logger.warning("Expired onboarding token for tenant_id=%s (now=%s, expiry=%s)", tenant_id, now_ts, expiry)
            return False

        if expiry > now_ts + SIGNUP_TOKEN_TTL_SECONDS + MAX_ALLOWED_CLOCK_SKEW_SECONDS:
            _logger.warning("Onboarding token expiry post-dated beyond maximum window: tenant_id=%s", tenant_id)
            return False

        signing_key = _derive_domain_hmac_secret(env, HMAC_ONBOARDING_CONTEXT)
        message = f"{tenant_id}:{clean_slug}:{expiry}:{nonce}".encode('utf-8')
        expected_signature = hmac.new(signing_key, message, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            _logger.warning("Signature verification mismatch for tenant_id=%s, slug=%s", tenant_id, clean_slug)
            return False

        if consume:
            cr = getattr(env, 'cr', None) if env is not None else None
            if cr is not None:
                if not _record_consumed_nonce_persistent(cr, nonce, tenant_id, clean_slug, expiry):
                    _logger.error("Replay attack detected via persistent ledger: nonce %s already consumed.", nonce)
                    return False
            else:
                _prune_in_memory_nonces(now_ts)
                nonce_key = f"onboarding.nonce.consumed.{nonce}"
                already_used = nonce in _CONSUMED_ONBOARDING_NONCES
                if not already_used and env is not None:
                    try:
                        cp = env['ir.config_parameter'].sudo()
                        if cp.get_param(nonce_key):
                            already_used = True
                        elif hasattr(cp, 'set_param'):
                            cp.set_param(nonce_key, str(now_ts))
                    except Exception as exc:
                        _logger.debug("In-memory nonce fallback used: %s", exc)
                if already_used:
                    _logger.error("Replay attack detected: token nonce %s has already been consumed.", nonce)
                    return False
                _CONSUMED_ONBOARDING_NONCES.add(nonce)
                _CONSUMED_ONBOARDING_NONCE_EXPIRY[nonce] = expiry

        return True

    except (ValueError, TypeError, ValidationError) as exc:
        _logger.warning("Exception during onboarding token verification: %s", exc)
        return False


class OfflineLeaseToken:
    """Cryptographic lease envelope for 168-hour air-gapped sovereign node execution.
    Supports both monotonic epoch ratchets (.issue / .verify / .serialize / .deserialize)
    and direct air-gapped secret-key validation (.is_valid_at).
    """

    MAX_LEASE_DURATION_SECONDS = 168 * 3600  # Exactly 168 hours (7 days)

    def __init__(self, tenant_id, arg2, arg3, arg4, signature: str = None):
        if signature is None:
            # 4-arg mode: (tenant_id, issued_at, ttl_seconds, secret_key)
            issued_at = int(arg2)
            ttl_seconds = int(arg3)
            secret_key = str(arg4)
            if not secret_key or len(secret_key) < 16:
                raise ValueError("OfflineLeaseToken secret_key must be at least 16 characters.")
            self.tenant_id = tenant_id
            self.lease_epoch = 0
            self.issued_at = issued_at
            self.ttl_seconds = ttl_seconds
            self.expires_at = self.issued_at + self.ttl_seconds
            self.signature = self._sign(secret_key)
        else:
            # 5-arg mode: (tenant_id, lease_epoch, issued_at, expires_at, signature)
            lease_epoch = arg2
            issued_at = arg3
            expires_at = arg4
            if isinstance(tenant_id, bool) or not isinstance(tenant_id, int) or tenant_id <= 0:
                raise ValidationError("Tenant ID must be a positive integer.")
            if isinstance(lease_epoch, bool) or not isinstance(lease_epoch, int) or lease_epoch < 0:
                raise ValidationError("Lease epoch must be a non-negative integer.")
            if expires_at <= issued_at:
                raise ValidationError("Lease expiration must occur strictly after issuance timestamp.")
            if (expires_at - issued_at) > self.MAX_LEASE_DURATION_SECONDS:
                raise ValidationError("Lease duration exceeds maximum permitted 168-hour window.")
            self.tenant_id = tenant_id
            self.lease_epoch = lease_epoch
            self.issued_at = int(issued_at)
            self.expires_at = int(expires_at)
            self.ttl_seconds = self.expires_at - self.issued_at
            self.signature = str(signature)

    def _sign(self, secret: str) -> str:
        payload = f"{self.tenant_id}:{self.issued_at}:{self.expires_at}".encode('utf-8')
        return hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()

    def is_valid_at(self, current_timestamp: int, secret_key: str) -> bool:
        if not secret_key or current_timestamp > self.expires_at or current_timestamp < self.issued_at:
            return False
        expected = self._sign(secret_key)
        return hmac.compare_digest(self.signature, expected)

    @classmethod
    def issue(cls, env, tenant_id: int, lease_epoch: int) -> 'OfflineLeaseToken':
        """Issue a verified 168-hour sovereign lease token with domain-separated signing key."""
        if isinstance(tenant_id, bool) or not isinstance(tenant_id, int) or tenant_id <= 0:
            raise ValidationError("Tenant ID must be a positive integer.")
        if isinstance(lease_epoch, bool) or not isinstance(lease_epoch, int) or lease_epoch < 0:
            raise ValidationError("Lease epoch must be a non-negative integer.")

        now_ts = int(time.time())
        expires_at = now_ts + cls.MAX_LEASE_DURATION_SECONDS
        signing_key = _derive_domain_hmac_secret(env, HMAC_LEASE_CONTEXT)

        payload = f"{tenant_id}:{lease_epoch}:{now_ts}:{expires_at}".encode('utf-8')
        signature = hmac.new(signing_key, payload, hashlib.sha256).hexdigest()

        return cls(
            tenant_id,
            lease_epoch,
            now_ts,
            expires_at,
            signature=signature,
        )

    def verify(self, env, minimum_admissible_epoch: int = 0) -> bool:
        """Validate lease integrity, chronological validity, and epoch revocation status."""
        try:
            now_ts = int(time.time())
            if self.lease_epoch < minimum_admissible_epoch:
                _logger.warning(
                    "Revoked lease token: epoch %s is below minimum admissible %s for tenant %s",
                    self.lease_epoch, minimum_admissible_epoch, self.tenant_id,
                )
                return False

            if now_ts > self.expires_at + MAX_ALLOWED_CLOCK_SKEW_SECONDS:
                _logger.warning("Expired lease token encountered for tenant %s", self.tenant_id)
                return False

            if self.issued_at > now_ts + MAX_ALLOWED_CLOCK_SKEW_SECONDS:
                _logger.warning("Lease token issued timestamp is in the future for tenant %s", self.tenant_id)
                return False

            signing_key = _derive_domain_hmac_secret(env, HMAC_LEASE_CONTEXT)
            payload = f"{self.tenant_id}:{self.lease_epoch}:{self.issued_at}:{self.expires_at}".encode('utf-8')
            expected_signature = hmac.new(signing_key, payload, hashlib.sha256).hexdigest()

            return hmac.compare_digest(self.signature, expected_signature)
        except Exception as exc:
            _logger.error("Error evaluating OfflineLeaseToken verification: %s", exc)
            return False

    def serialize(self) -> str:
        """Serialize lease into a compact, transport-ready string format."""
        return f"{self.tenant_id}:{self.lease_epoch}:{self.issued_at}:{self.expires_at}:{self.signature}"

    @classmethod
    def deserialize(cls, raw_envelope: str) -> 'OfflineLeaseToken':
        """Parse and construct an OfflineLeaseToken instance from a serialized envelope."""
        if not raw_envelope or not isinstance(raw_envelope, str) or raw_envelope.count(':') != 4:
            raise ValidationError("Malformed offline lease envelope string format.")

        parts = raw_envelope.split(':')
        return cls(
            int(parts[0]),
            int(parts[1]),
            int(parts[2]),
            int(parts[3]),
            signature=parts[4],
        )


class VectorClockJournalSequence:
    """Node-prefixed monotonic sequence allocator preventing cross-node collisions during offline split-brain."""

    def __init__(self, node_id: str):
        if not node_id or not str(node_id).strip():
            raise ValueError("node_id cannot be empty.")
        self.node_id = str(node_id).strip()
        self.counter = 0

    def next_sequence(self, fiscal_year: int) -> str:
        self.counter += 1
        return f"INV/{int(fiscal_year)}/{self.node_id}-{self.counter:06d}"


def compute_tenant_workspace_url(slug: str) -> str:
    """Build a canonical HTTPS workspace access URL without cleartext or internal debug ports."""
    valid_slug = sanitize_and_validate_slug(slug)
    base_domain = 'insilos.com'
    try:
        if request and getattr(request, 'env', None):
            configured_domain = request.env['ir.config_parameter'].sudo().get_param(
                'insilos.saas.base_domain', 'insilos.com'
            )
            if configured_domain and isinstance(configured_domain, str) and configured_domain.strip():
                base_domain = configured_domain.strip()
    except Exception as exc:
        _logger.error("Failed to read insilos.saas.base_domain parameter: %s", exc)
        base_domain = 'insilos.com'
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
            token = generate_signup_token(request.env, operation.tenant_id.id, operation.tenant_id.slug)
            if hasattr(request, 'session') and isinstance(request.session, dict):
                request.session['insilos_last_signup_tenant_id'] = operation.tenant_id.id
            return request.redirect(
                f"/saas/signup/success?tenant_id={operation.tenant_id.id}&slug={operation.tenant_id.slug}&token={token}&status=requested"
            )

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

        token = generate_signup_token(request.env, tenant.id, slug)
        if hasattr(request, 'session') and isinstance(request.session, dict):
            request.session['insilos_last_signup_tenant_id'] = tenant.id
        return request.redirect(
            f"/saas/signup/success?tenant_id={tenant.id}&slug={slug}&token={token}&status=requested&operation_id={operation.id}"
        )

    @http.route('/saas/signup/success', type='http', auth="public", website=True, sitemap=False)
    def saas_signup_success(self, tenant_id=None, slug=None, token=None, **kwargs):
        """Confirmation and onboarding instruction page with strict authorization guarding."""
        tenant = None
        parsed_tenant_id = None
        if tenant_id:
            try:
                parsed_tenant_id = int(tenant_id)
            except (ValueError, TypeError):
                _logger.warning("Invalid tenant_id format supplied to signup_success: %s", tenant_id)
                return request.redirect('/industry?error=invalid_tenant_id')

        if not slug and not parsed_tenant_id:
            return request.redirect('/industry?error=missing_tenant_identifier')

        try:
            valid_slug = sanitize_and_validate_slug(slug) if slug else None
        except ValidationError as exc:
            _logger.warning("Invalid slug '%s' passed to signup success page: %s", slug, exc)
            return request.redirect('/industry?error=invalid_tenant_slug')

        # Defense-in-Depth: Validate access authorization via session matching OR cryptographic token
        session_tenant_id = request.session.get('insilos_last_signup_tenant_id') if hasattr(request, 'session') and request.session else None
        is_authorized = False

        if parsed_tenant_id and session_tenant_id == parsed_tenant_id:
            is_authorized = True
        elif parsed_tenant_id and valid_slug and token:
            is_authorized = verify_signup_token(request.env, parsed_tenant_id, valid_slug, token)

        if not is_authorized:
            _logger.warning(
                "Unauthorized access attempt to /saas/signup/success for tenant_id=%s, slug=%s",
                parsed_tenant_id, valid_slug,
            )
            return request.redirect('/saas/signup?error=access_denied')

        if parsed_tenant_id:
            tenant = request.env['insilos.tenant'].sudo().browse(parsed_tenant_id)
            if not tenant.exists():
                return request.redirect('/industry?error=tenant_not_found')
        elif valid_slug:
            tenant = request.env['insilos.tenant'].sudo().search([('slug', '=', valid_slug)], limit=1)
            if not tenant:
                return request.redirect('/industry?error=tenant_not_found')

        canonical_slug = sanitize_and_validate_slug(tenant.slug if tenant and tenant.slug else (valid_slug or 'workspace'))
        workspace_url = compute_tenant_workspace_url(canonical_slug)

        tenant_view_data = {
            'id': tenant.id if tenant else parsed_tenant_id,
            'name': tenant.name if tenant else canonical_slug,
            'slug': canonical_slug,
            'state': getattr(tenant, 'state', 'provisioning') if tenant else 'provisioning',
            'plan_tier': getattr(tenant, 'plan_tier', 'standard') if tenant else 'standard',
            'workspace_url': workspace_url,
        }

        values = {
            'tenant': tenant,
            'tenant_data': tenant_view_data,
            'slug': canonical_slug,
            'tenant_workspace_url': workspace_url,
            'tenant_base_url': workspace_url.rsplit('/insilos', 1)[0],
            'operation_id': kwargs.get('operation_id'),
            'status': kwargs.get('status', 'requested'),
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
