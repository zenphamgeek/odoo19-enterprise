# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging

from odoo.exceptions import AccessError

try:
    from odoo import api, models
except (ImportError, Exception):
    class models:
        class AbstractModel:
            _name = None
            _description = None
        class Model:
            _name = None
            _inherit = None
            _description = None

    class api:
        @staticmethod
        def model(f):
            return f
        class Environment:
            pass

_logger = logging.getLogger(__name__)

# Sovereign set of tenant-isolated models requiring strict procedural guard under sudo
PROCEDURAL_TENANT_INVARIANTS = {
    'saas.workspace',
    'account.move',
    'account.analytic.line',
    'crm.lead',
    'res.partner',
    'insilos.tenant',
    'project.project',
    'project.task',
}


class TenantProceduralMemoryGuard(models.AbstractModel):
    _name = 'tenant.procedural.memory.guard'
    _description = 'Procedural Memory Tenant Boundary Guard'

    PROCEDURAL_TENANT_INVARIANTS = PROCEDURAL_TENANT_INVARIANTS

    @api.model
    def assert_procedural_tenant_invariant(self, model_name: str, domain: list, calling_env: api.Environment):
        """
        Mem0 Transplant - Tenant Procedural Memory Invariant Verification:
        If calling_env.su is True and model_name in PROCEDURAL_TENANT_INVARIANTS:
        Asserts an explicit company_id constraint matching the active company (calling_env.company.id).
        Raises AccessError if missing or mismatched, preventing sudo cross-tenant data leaks.
        """
        if not getattr(calling_env, 'su', False):
            # Non-sudo environments are bounded by standard Odoo ir.rule record rules
            return True

        if model_name not in PROCEDURAL_TENANT_INVARIANTS:
            return True

        active_company = getattr(calling_env, 'company', None)
        active_company_id = active_company.id if active_company else False
        if not active_company_id:
            raise AccessError(
                f"Procedural Memory Guard violation: Sudo call on '{model_name}' without active company context."
            )

        # Inspect domain for explicit company_id constraint
        has_valid_company_constraint = False
        if domain and isinstance(domain, (list, tuple)):
            for leaf in domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    field, operator, val = leaf
                    if field == 'company_id':
                        cid_val = val.id if hasattr(val, 'id') else val
                        if operator in ('=', '==') and cid_val == active_company_id:
                            has_valid_company_constraint = True
                            break
                        elif operator in ('in',) and isinstance(val, (list, tuple, set)):
                            val_ids = [v.id if hasattr(v, 'id') else v for v in val]
                            if active_company_id in val_ids and len(val_ids) == 1:
                                has_valid_company_constraint = True
                                break

        if not has_valid_company_constraint:
            _logger.error(
                "Procedural memory guard failed: Sudo domain on '%s' missing explicit ('company_id', '=', %s). Domain=%s",
                model_name, active_company_id, domain,
            )
            raise AccessError(
                f"AccessError: Procedural tenant invariant violated for '{model_name}'. "
                f"Sudo queries must provide explicit ('company_id', '=', {active_company_id}) constraint."
            )

        return True
