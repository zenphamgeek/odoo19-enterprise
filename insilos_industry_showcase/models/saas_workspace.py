# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging
import zlib
from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaasWorkspace(models.Model):
    _name = 'saas.workspace'
    _description = 'SaaS Workspace'

    subdomain = fields.Char(string='Subdomain', required=True, index=True)
    tenant_id = fields.Many2one('insilos.tenant', string='Tenant', ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('provisioning', 'Provisioning'),
        ('active', 'Active'),
        ('failed', 'Failed'),
    ], default='draft', string='State')
    idempotency_hash = fields.Char(string='Idempotency Hash', index=True)

    _sql_constraints = [
        ('subdomain_unique', 'unique(subdomain)', 'Workspace subdomain must be unique.'),
    ]

    @api.model
    def provision_atomic(self, subdomain, tenant_id=None, idempotency_key=None, **kwargs):
        """
        DISM-TRL Atomic Provisioning with Non-Blocking Advisory Hashing & Transient Rollback Ledger:
        - Advisory transaction lock based on zlib.crc32 hash of lowercase subdomain
        - Double-check pattern against TOCTOU race conditions
        - Savepoint rollback ensuring transient error recovery without transaction poison
        """
        import zlib
        import logging
        _log = logging.getLogger(__name__)

        if not subdomain or not isinstance(subdomain, str) or not subdomain.strip():
            raise UserError("subdomain_invalid")

        clean_subdomain = subdomain.strip().lower()
        lock_id = zlib.crc32(clean_subdomain.encode('utf-8'))

        self.env.cr.execute("SELECT pg_try_advisory_xact_lock(%s::bigint)", [lock_id])
        res = self.env.cr.fetchone()
        acquired = bool(res and res[0])
        if not acquired:
            _log.warning("DISM-TRL advisory lock conflict for subdomain '%s' (lock_id=%s)", clean_subdomain, lock_id)
            raise UserError("system_busy")

        # Double-check existing
        existing = self.search([('subdomain', '=', clean_subdomain)], limit=1)
        if existing:
            if idempotency_key and existing.idempotency_hash == idempotency_key:
                return existing
            raise UserError("subdomain_taken")

        self.env.cr.execute("SAVEPOINT saas_provision_atomic")
        try:
            vals = {
                'subdomain': clean_subdomain,
                'tenant_id': tenant_id.id if hasattr(tenant_id, 'id') else tenant_id,
                'state': kwargs.get('state', 'provisioning'),
                'idempotency_hash': idempotency_key,
            }
            for k, v in kwargs.items():
                if k in self._fields and k not in vals:
                    vals[k] = v
            workspace = self.create(vals)
            self.env.cr.execute("RELEASE SAVEPOINT saas_provision_atomic")
            return workspace
        except Exception as e:
            self.env.cr.execute("ROLLBACK TO SAVEPOINT saas_provision_atomic")
            _log.warning("DISM-TRL rollback for subdomain '%s': %s", clean_subdomain, e)
            if isinstance(e, UserError):
                raise
            err_msg = str(e).lower()
            if 'unique' in err_msg or 'subdomain_unique' in err_msg or isinstance(e, IntegrityError):
                raise UserError("subdomain_taken")
            raise UserError("system_busy")
