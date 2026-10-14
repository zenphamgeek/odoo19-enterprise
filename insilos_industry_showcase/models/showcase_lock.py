# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import logging
import struct
import time
from contextlib import contextmanager

from odoo.exceptions import UserError

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

_logger = logging.getLogger(__name__)


def generate_tenant_lock_key(company_id: int, model_name: str, resource_id: int) -> int:
    """
    Deterministic 64-bit signed advisory lock key derived via SHA-256 and struct.unpack('>q', ...).
    Guarantees cross-worker consistency and mathematical confinement within PostgreSQL bigint bounds.
    """
    raw = f"{company_id}:{model_name}:{resource_id}".encode("utf-8")
    digest_8 = hashlib.sha256(raw).digest()[:8]
    return struct.unpack(">q", digest_8)[0]


class ShowcaseLockManager(models.AbstractModel):
    _name = "insilos.showcase.lock.manager"
    _description = "Showcase Concurrency Advisory Lock Manager"

    @contextmanager
    def atomic_tenant_lock(self, target_record, timeout_seconds: float = 3.0):
        """
        Transactional advisory lock manager enforcing tenant-scoped resource isolation.
        - Calculates lock_key using generate_tenant_lock_key.
        - Attempts non-blocking pg_try_advisory_xact_lock with timeout retry bounds.
        - Encloses the yielded execution block in cr.savepoint(flush=True).
        - Automatically releases savepoint on normal completion or rolls back on error.
        """
        company_id = getattr(target_record, "company_id", None)
        if company_id:
            cid = company_id.id if hasattr(company_id, "id") else int(company_id)
        else:
            cid = self.env.company.id if getattr(self, "env", None) and getattr(self.env, "company", None) else 0

        model_name = getattr(target_record, "_name", "unknown")
        resource_id = getattr(target_record, "id", 0) or 0
        lock_key = generate_tenant_lock_key(cid, model_name, resource_id)

        cr = getattr(target_record, "env", self.env).cr
        deadline = time.time() + (timeout_seconds or 0.0)
        acquired = False

        while True:
            cr.execute("SELECT pg_try_advisory_xact_lock(%s::bigint)", [lock_key])
            res = cr.fetchone()
            if res and res[0]:
                acquired = True
                break
            if time.time() >= deadline:
                break
            time.sleep(0.05)

        if not acquired:
            _logger.warning(
                "Failed to acquire advisory lock for %s(%s) company %s (lock_key=%s)",
                model_name, resource_id, cid, lock_key,
            )
            raise UserError(f"Resource {model_name}({resource_id}) locked by another transaction.")

        with cr.savepoint(flush=True):
            yield target_record
