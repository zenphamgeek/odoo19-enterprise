# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import logging
from functools import wraps

try:
    from odoo.exceptions import AccessError
except Exception:
    class AccessError(Exception):
        pass

_logger = logging.getLogger(__name__)


def enforce_tenant_isolation(company_field: str = "company_id"):
    """
    Decorator for model methods enforcing multi-company invariant boundaries:
      - Validates that each record belongs to a company within record.env.companies.ids.
      - Under sudo (record.env.su is True), guards against ambient company_id leakage:
        record company must match record.env.company.id or explicit context allowed_company_ids,
        otherwise an AccessError is raised.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            records = self if hasattr(self, "__iter__") else [self]
            for record in records:
                val = getattr(record, company_field, None)
                if val is None and hasattr(record, "company_id"):
                    val = record.company_id
                cid = val.id if hasattr(val, "id") else int(val or 0)
                if cid:
                    env = getattr(record, "env", None)
                    if env:
                        # Multi-company user authorization check
                        allowed_companies = getattr(env, "companies", None)
                        if allowed_companies is not None and hasattr(allowed_companies, "ids"):
                            if cid not in allowed_companies.ids:
                                raise AccessError(
                                    f"Access Denied: Record {getattr(record, '_name', 'model')}({getattr(record, 'id', 0)}) "
                                    f"belongs to company {cid}, not in user allowed companies {allowed_companies.ids}."
                                )

                        # Sudo ambient leakage check
                        if getattr(env, "su", False) is True:
                            current_company = getattr(env, "company", None)
                            current_cid = current_company.id if hasattr(current_company, "id") else int(current_company or 0)
                            ctx = getattr(env, "context", {}) or {}
                            ctx_allowed = ctx.get("allowed_company_ids", [])
                            if isinstance(ctx_allowed, (int, float)):
                                ctx_allowed = [int(ctx_allowed)]
                            elif not isinstance(ctx_allowed, (list, tuple, set)):
                                ctx_allowed = []

                            if cid != current_cid and cid not in ctx_allowed:
                                raise AccessError(
                                    f"Sudo Ambient Company Leakage: Record {getattr(record, '_name', 'model')}({getattr(record, 'id', 0)}) "
                                    f"company {cid} does not match active company {current_cid} or context allowed_company_ids {ctx_allowed}."
                                )
            return fn(self, *args, **kwargs)
        return wrapper

    if callable(company_field):
        fn = company_field
        company_field = "company_id"
        return decorator(fn)
    return decorator
