# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import logging
import struct
import threading
import time
from contextlib import contextmanager

try:
    from odoo.exceptions import UserError
except Exception:
    class UserError(Exception):
        pass

_logger = logging.getLogger(__name__)

# Thread-local storage for auditing active transaction advisory locks
_lock_state = threading.local()


def _get_active_locks() -> set:
    if not hasattr(_lock_state, "active"):
        _lock_state.active = set()
    return _lock_state.active


def is_lock_active(lock_key_or_model=None, company_id=None, record_id=None) -> bool:
    """
    Audit query to verify whether an advisory lock is actively held in the current thread.
    Can be queried with:
      - is_lock_active() -> bool (returns True if any lock is active)
      - is_lock_active(lock_key: int) -> bool
      - is_lock_active(model_name: str, company_id: int, record_id: int) -> bool
    """
    active = _get_active_locks()
    if lock_key_or_model is None:
        return bool(active)
    if isinstance(lock_key_or_model, int) and company_id is None:
        return lock_key_or_model in active
    if isinstance(lock_key_or_model, str) and company_id is not None and record_id is not None:
        key = compute_partitioned_lock_key(lock_key_or_model, int(company_id), int(record_id))
        return key in active
    return bool(active)


_is_lock_active = is_lock_active


def compute_partitioned_lock_key(model_name: str, company_id: int, record_id: int) -> int:
    """
    Cryptographic 64-bit signed advisory lock key derived using Blake2b (digest_size=8).
    Unpacks as big-endian signed 64-bit integer (>q) strictly bounded by [-2^63, 2^63 - 1].
    Eliminates 16-bit truncation modulo collisions (e.g. IDs > 65535).
    """
    raw = f"{model_name}:{company_id}:{record_id}".encode("utf-8")
    digest_8 = hashlib.blake2b(raw, digest_size=8).digest()
    key = struct.unpack(">q", digest_8)[0]
    return key


@contextmanager
def acquire_tenant_xact_lock(
    cr,
    model_name: str,
    company_id: int,
    record_id: int,
    timeout_sec: float = 3.0,
    retry_delay: float = 0.05,
    max_retries: int = None,
):
    """
    Acquires a transaction-level advisory lock (pg_try_advisory_xact_lock) for tenant resource isolation.
    Non-blocking retry loop bounded by timeout_sec or max_retries.
    Wraps yielded block in cr.savepoint(flush=True).
    Auto-releases upon transaction completion with zero PgBouncer session leaks.
    """
    lock_key = compute_partitioned_lock_key(model_name, int(company_id or 0), int(record_id or 0))
    deadline = time.time() + (timeout_sec if timeout_sec is not None else 0.0)
    attempt = 0
    acquired = False

    while True:
        cr.execute("SELECT pg_try_advisory_xact_lock(%s::bigint)", [lock_key])
        res = cr.fetchone()
        if res and res[0]:
            acquired = True
            break
        attempt += 1
        if max_retries is not None and attempt >= max_retries:
            break
        if timeout_sec is not None and time.time() >= deadline:
            break
        if retry_delay and retry_delay > 0:
            time.sleep(retry_delay)

    if not acquired:
        _logger.warning(
            "Advisory lock contention for %s(%s) company %s (lock_key=%s)",
            model_name, record_id, company_id, lock_key,
        )
        raise UserError(f"Resource {model_name}({record_id}) company {company_id} is locked by another transaction.")

    active_locks = _get_active_locks()
    active_locks.add(lock_key)
    try:
        with cr.savepoint(flush=True):
            yield lock_key
    finally:
        active_locks.discard(lock_key)


def execute_with_detached_rpc(
    cr,
    model_name: str,
    company_id: int,
    record_id: int,
    rpc_callable,
    db_callable,
    timeout_sec: float = 3.0,
):
    """
    Strict Lock-RPC Separation:
    Ensures network calls (HSM, SMS, external APIs) execute strictly outside database advisory locks.
    Phase 1 (External RPC): rpc_res = rpc_callable() executed while no lock is held.
    Phase 2 (Locked DB Mutex): with acquire_tenant_xact_lock(...): return db_callable(rpc_res)
    """
    # Phase 1: External RPC without lock
    rpc_res = rpc_callable()

    # Phase 2: Transaction-level advisory lock held only during database persistence
    with acquire_tenant_xact_lock(
        cr,
        model_name,
        company_id,
        record_id,
        timeout_sec=timeout_sec,
    ) as lock_key:
        return db_callable(rpc_res)


def acquire_canonical_ordered_locks(cr, table_name: str, record_ids: list) -> list:
    """Acquire row-level FOR UPDATE locks in deterministic ascending canonical order.
    Mathematically eliminates circular wait conditions (Coffman Invariant #4).
    """
    import re

    if not table_name or not re.fullmatch(r"[a-z_][a-z0-9_]{1,62}", table_name):
        raise ValueError(f"Invalid SQL table identifier for canonical lock: {table_name!r}")

    canonical_ids = sorted({int(rid) for rid in (record_ids or []) if rid is not None and int(rid) > 0})
    if not canonical_ids:
        return []

    cr.execute(
        f"SELECT id FROM {table_name} WHERE id IN %s ORDER BY id ASC FOR UPDATE;",
        (tuple(canonical_ids),),
    )
    return canonical_ids


import contextvars
import enum
import hmac
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple


class SecurityException(Exception):
    """Base security exception for all policy violations."""


class SecurityIntegrityError(SecurityException):
    """Raised when a tenant isolation invariant or security boundary is violated."""


class MultiTenantSecurityError(SecurityIntegrityError):
    """Raised when a multi-tenant boundary is violated or an invalid context token is presented."""


class MultiTenantIsolationViolationError(MultiTenantSecurityError):
    """Raised when tenant context integrity or company membership is violated."""


class TenantBoundaryViolation(MultiTenantIsolationViolationError):
    """Raised when an operation attempts to access data outside authorized tenant scope."""


class CyclicStructureDetected(ValueError, SecurityException):
    """Raised when an unhandled cyclic structure or excessive recursion depth is detected."""


class ConcurrencyLockTimeoutError(SecurityException):
    """Raised when acquiring locks in the canonical hierarchy exceeds the monotonic timeout."""


class LockHierarchyError(SecurityException):
    """Raised when lock acquisition violates the strict canonical hierarchy."""


class LockHierarchyViolationError(LockHierarchyError):
    """Raised when an attempt is made to acquire locks in violation of canonical hierarchy."""


class DeadlockHazardException(LockHierarchyViolationError):
    """Raised when lock acquisition order violates the canonical total-order hierarchy."""


class LockTierViolationError(LockHierarchyViolationError, RuntimeError):
    """Raised when locks are requested out of deterministic tier order."""


class LockTimeoutError(ConcurrencyLockTimeoutError):
    """Raised when acquiring a canonical lock exceeds the specified monotonic timeout."""



@dataclass(frozen=True)
class TenantContextToken:
    tenant_id: Any
    allowed_company_ids: Any = frozenset()
    lease_signature: str = ""
    created_at_mono: float = 0.0
    epoch_timestamp: float = 0.0
    nonce: str = ""
    signature: str = ""
    company_id: str = ""
    user_id: str = ""

    @classmethod
    def generate(
        cls,
        tenant_id: str,
        company_id: str,
        user_id: str,
        secret_key: bytes,
    ) -> "TenantContextToken":
        payload = f"{tenant_id}:{company_id}:{user_id}".encode("utf-8")
        sig = hmac.new(secret_key, payload, hashlib.sha256).hexdigest()
        return cls(
            tenant_id=tenant_id,
            company_id=company_id,
            user_id=user_id,
            signature=sig,
            lease_signature=sig,
        )

    @classmethod
    def create(
        cls,
        tenant_id: int,
        allowed_company_ids: Set[int],
        secret_key: bytes,
        nonce: str,
    ) -> "TenantContextToken":
        if not isinstance(tenant_id, int) or tenant_id <= 0:
            raise MultiTenantSecurityError(
                f"Invalid tenant_id: {tenant_id}. Must be positive integer."
            )
        if not allowed_company_ids or not all(
            isinstance(cid, int) and cid > 0 for cid in allowed_company_ids
        ):
            raise MultiTenantSecurityError(
                "allowed_company_ids must contain positive integers."
            )
        if tenant_id not in allowed_company_ids:
            raise MultiTenantSecurityError(
                f"Primary tenant_id {tenant_id} must be in allowed_company_ids."
            )

        now = time.time()
        sorted_cids = sorted(list(allowed_company_ids))
        payload = f"{tenant_id}:{','.join(map(str, sorted_cids))}:{now:.6f}:{nonce}".encode("utf-8")
        sig = hmac.new(secret_key, payload, hashlib.sha256).hexdigest()

        return cls(
            tenant_id=tenant_id,
            allowed_company_ids=frozenset(allowed_company_ids),
            lease_signature=sig,
            created_at_mono=time.monotonic(),
            epoch_timestamp=now,
            nonce=nonce,
            signature=sig,
        )

    def verify(self, secret_key: bytes, max_age_seconds: float = 300.0) -> bool:
        if self.company_id or self.user_id:
            payload = f"{self.tenant_id}:{self.company_id}:{self.user_id}".encode("utf-8")
            expected_sig = hmac.new(secret_key, payload, hashlib.sha256).hexdigest()
            active_sig = self.signature or self.lease_signature
            return hmac.compare_digest(active_sig, expected_sig)

        if (time.time() - self.epoch_timestamp) > max_age_seconds:
            _logger.error(
                "TenantContextToken expired. Age: %.2fs",
                time.time() - self.epoch_timestamp,
            )
            return False
        sorted_cids = sorted(list(self.allowed_company_ids))
        payload = f"{self.tenant_id}:{','.join(map(str, sorted_cids))}:{self.epoch_timestamp:.6f}:{self.nonce}".encode("utf-8")
        expected_sig = hmac.new(secret_key, payload, hashlib.sha256).hexdigest()
        active_sig = self.signature or self.lease_signature
        return hmac.compare_digest(active_sig, expected_sig)


_ACTIVE_TENANT_TOKEN: contextvars.ContextVar[Optional[TenantContextToken]] = contextvars.ContextVar(
    "_ACTIVE_TENANT_TOKEN", default=None
)
_ACTIVE_TENANT_ID: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "insilos_active_tenant_id", default=None
)


class AtomicMultiTenantGuard:
    """Context manager for fail-closed multi-tenant scoping (supports TenantContextToken, Odoo env, and integer tenant_id modes)."""

    def __init__(
        self,
        token_or_env: Any = None,
        secret_key_or_company_id: Any = None,
        *,
        tenant_id: Optional[int] = None,
        target_company_id: Optional[int] = None,
        enforce_strict_membership: bool = True,
    ):
        if isinstance(token_or_env, TenantContextToken):
            self._mode = "token"
            self.token: Optional[TenantContextToken] = token_or_env
            self.secret_key: bytes = secret_key_or_company_id
            self.env = None
            self.tenant_id = token_or_env.tenant_id
            self.target_company_id = token_or_env.tenant_id
            self.enforce_strict_membership = enforce_strict_membership
        elif (
            tenant_id is not None
            or (
                isinstance(token_or_env, (int, bool))
                and secret_key_or_company_id is None
                and target_company_id is None
            )
            or (
                token_or_env is None
                and secret_key_or_company_id is None
                and target_company_id is None
            )
        ):
            resolved_tid = tenant_id if tenant_id is not None else token_or_env
            if not isinstance(resolved_tid, int) or isinstance(resolved_tid, bool) or resolved_tid <= 0:
                raise ValueError("Invalid tenant_id: must be a positive integer.")
            self._mode = "tenant_id"
            self.token = None
            self.secret_key = b""
            self.env = None
            self.tenant_id = resolved_tid
            self.target_company_id = resolved_tid
            self.enforce_strict_membership = enforce_strict_membership
        else:
            self._mode = "env"
            self.token = None
            self.secret_key = b""
            self.env = token_or_env
            resolved_cid = (
                target_company_id
                if target_company_id is not None
                else secret_key_or_company_id
            )
            if not isinstance(resolved_cid, int) or isinstance(resolved_cid, bool) or resolved_cid <= 0:
                raise ValueError(
                    f"Invalid target_company_id: {resolved_cid}. Must be a positive integer."
                )
            self.tenant_id = resolved_cid
            self.target_company_id = resolved_cid
            self.enforce_strict_membership = enforce_strict_membership
        self._reset_token: Optional[contextvars.Token] = None
        self._reset_tid_token: Optional[contextvars.Token] = None
        self._original_context: Dict[str, Any] = {}
        self._original_company_id: Optional[int] = None
        self._is_active: bool = False

    def __enter__(self) -> Any:
        if self._mode == "token":
            assert self.token is not None
            if not self.token.verify(self.secret_key):
                raise MultiTenantSecurityError(
                    "Cryptographic verification failed for TenantContextToken."
                )

            current = _ACTIVE_TENANT_TOKEN.get()
            if current is not None and current.tenant_id != self.token.tenant_id:
                raise MultiTenantSecurityError(
                    f"Illegal nested tenant switch from tenant {current.tenant_id} to {self.token.tenant_id}."
                )

            self._reset_token = _ACTIVE_TENANT_TOKEN.set(self.token)
            self._reset_tid_token = _ACTIVE_TENANT_ID.set(self.token.tenant_id)
            self._is_active = True
            return self

        if self._mode == "tenant_id":
            self._reset_tid_token = _ACTIVE_TENANT_ID.set(self.tenant_id)
            self._is_active = True
            return self

        # Env mode: snapshot context, verify user company membership, invalidate ORM cache
        self._original_context = dict(getattr(self.env, "context", None) or {})
        current_company = getattr(self.env, "company", None)
        self._original_company_id = current_company.id if current_company else None

        if self.enforce_strict_membership and not getattr(self.env, "su", False):
            user = getattr(self.env, "user", None)
            user_company_ids = (
                user.company_ids.ids
                if user is not None and hasattr(user, "company_ids")
                else []
            )
            if self.target_company_id not in user_company_ids:
                raise MultiTenantIsolationViolationError(
                    f"Access Denied: User {getattr(user, 'id', 'UNKNOWN')} does not belong to Company {self.target_company_id}"
                )

        if hasattr(self.env, "invalidate_all"):
            self.env.invalidate_all()

        new_allowed = [self.target_company_id]
        if "allowed_company_ids" in self._original_context:
            existing = [
                cid
                for cid in self._original_context["allowed_company_ids"]
                if cid != self.target_company_id
            ]
            new_allowed = [self.target_company_id] + existing

        modified_context = dict(self._original_context)
        modified_context.update(
            {
                "company_id": self.target_company_id,
                "allowed_company_ids": new_allowed,
                "force_company": self.target_company_id,
            }
        )
        self.env.context = modified_context
        self._reset_tid_token = _ACTIVE_TENANT_ID.set(self.target_company_id)
        self._is_active = True
        return self.env

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if self._mode == "token":
            if self._reset_token is not None:
                _ACTIVE_TENANT_TOKEN.reset(self._reset_token)
                self._reset_token = None
            if self._reset_tid_token is not None:
                _ACTIVE_TENANT_ID.reset(self._reset_tid_token)
                self._reset_tid_token = None
            self._is_active = False
            return False

        if self._mode == "tenant_id":
            if self._reset_tid_token is not None:
                _ACTIVE_TENANT_ID.reset(self._reset_tid_token)
                self._reset_tid_token = None
            self._is_active = False
            return False

        try:
            if hasattr(self.env, "invalidate_all"):
                self.env.invalidate_all()
        finally:
            if self._reset_tid_token is not None:
                _ACTIVE_TENANT_ID.reset(self._reset_tid_token)
                self._reset_tid_token = None
            self.env.context = self._original_context
            self._is_active = False
        return False

    @classmethod
    @contextmanager
    def isolate_tenant(cls, env: Any, tenant_company_id: int):
        """Executes a block within an isolated tenant company context, flushing caches pre and post execution."""
        if not isinstance(tenant_company_id, int) or isinstance(tenant_company_id, bool) or tenant_company_id <= 0:
            raise MultiTenantIsolationViolationError("Invalid tenant company ID specified for isolation.")

        previous_company_id = getattr(getattr(env, "company", None), "id", None)
        previous_allowed = dict(getattr(env, "context", None) or {}).get("allowed_company_ids", [])

        if hasattr(env, "cache") and hasattr(env.cache, "invalidate"):
            env.cache.invalidate()
        if hasattr(env, "clear"):
            env.clear()

        isolated_env = env(
            context=dict(
                getattr(env, "context", None) or {},
                company_id=tenant_company_id,
                allowed_company_ids=[tenant_company_id],
            )
        )

        try:
            if getattr(getattr(isolated_env, "company", None), "id", None) != tenant_company_id:
                raise MultiTenantIsolationViolationError(
                    f"Tenant isolation mismatch: Expected {tenant_company_id}, "
                    f"resolved {getattr(getattr(isolated_env, 'company', None), 'id', None)}."
                )
            yield isolated_env
        finally:
            if hasattr(env, "cache") and hasattr(env.cache, "invalidate"):
                env.cache.invalidate()
            if hasattr(env, "clear"):
                env.clear()
            env.context = dict(
                getattr(env, "context", None) or {},
                company_id=previous_company_id,
                allowed_company_ids=previous_allowed,
            )

    @staticmethod
    def get_active_tenant_id() -> Optional[int]:
        token = _ACTIVE_TENANT_TOKEN.get()
        if token is not None:
            return token.tenant_id
        return _ACTIVE_TENANT_ID.get()

    @staticmethod
    def assert_record_access(record_company_id: int) -> None:
        token = _ACTIVE_TENANT_TOKEN.get()
        if token is None:
            raise MultiTenantSecurityError(
                "No active tenant context found during record boundary assertion."
            )
        if record_company_id not in token.allowed_company_ids:
            raise MultiTenantSecurityError(
                f"Cross-tenant access violation! Company {record_company_id} is not in allowed tenant scope: "
                f"{list(token.allowed_company_ids)}"
            )

    @staticmethod
    def validate_tenant_access(requested_tenant_id: Any, allowed_tenant_ids: List[int]) -> int:
        if not isinstance(requested_tenant_id, int) or isinstance(requested_tenant_id, bool):
            raise TenantBoundaryViolation(
                f"Tenant ID must be an integer. Received type: {type(requested_tenant_id).__name__}"
            )
        if requested_tenant_id <= 0:
            raise TenantBoundaryViolation(
                f"Tenant ID must be a strictly positive integer. Received: {requested_tenant_id}"
            )
        if not allowed_tenant_ids or not all(
            isinstance(tid, int) and not isinstance(tid, bool) and tid > 0
            for tid in allowed_tenant_ids
        ):
            raise TenantBoundaryViolation(
                "Allowed tenant context contains invalid or unauthenticated entries."
            )
        if requested_tenant_id not in allowed_tenant_ids:
            raise TenantBoundaryViolation(
                f"Access Denied: Tenant ID {requested_tenant_id} is not within authorized scope {allowed_tenant_ids}."
            )
        return requested_tenant_id


@enum.unique
class LockLevel(enum.IntEnum):
    """Global total order for resource lock acquisition. Lower levels MUST be acquired before higher levels."""

    SYSTEM_CONFIG = 10
    TENANT_ACCOUNT = 20
    FISCAL_PERIOD = 30
    GENERAL_LEDGER = 40
    JOURNAL_ENTRY = 50
    DOCUMENT_LINE = 60


@dataclass(frozen=True)
class ResourceLockKey:
    level: LockLevel
    resource_id: str

    def __lt__(self, other: "ResourceLockKey") -> bool:
        if self.level != other.level:
            return self.level < other.level
        return self.resource_id < other.resource_id


_THREAD_HELD_LOCKS: contextvars.ContextVar[Tuple[ResourceLockKey, ...]] = contextvars.ContextVar(
    "_THREAD_HELD_LOCKS", default=()
)


class CanonicalLockHierarchyManager:
    """Manages acquisition and release of synchronized resource locks (both in-memory LockLevel and DB row-level tiers)."""

    MODEL_LOCK_TIERS: Dict[str, int] = {
        "res.company": 10,
        "res.users": 20,
        "res.partner": 30,
        "sale.order": 40,
        "sale.order.line": 50,
        "account.move": 60,
        "account.move.line": 70,
        "stock.picking": 80,
        "stock.move": 90,
        "stock.quant": 100,
    }

    MODEL_TIER_HIERARCHY: Dict[str, int] = {
        "res.company": 10,
        "res.partner": 20,
        "account.journal": 30,
        "account.move": 40,
        "sale.order": 50,
        "sale.order.line": 60,
        "stock.picking": 70,
        "stock.move": 80,
        "stock.quant": 90,
    }

    LOCK_TIERS: Dict[str, int] = {
        "res.company": 1,
        "crm.team": 1,
        "crm.lead": 2,
        "sale.order": 2,
        "sale.order.line": 3,
        "account.move": 2,
        "account.move.line": 3,
    }

    def __init__(self, cr: Any = None) -> None:
        self.cr = cr
        self._current_max_tier_acquired: int = 0
        self._mutex_pool: Dict[ResourceLockKey, threading.Lock] = {}
        self._pool_lock = threading.Lock()

    def reset_transaction_state(self) -> None:
        self._current_max_tier_acquired = 0

    @classmethod
    def get_canonical_sort_key(cls, model_name: str, record_id: int) -> Tuple[int, str, int]:
        if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id <= 0:
            raise ValueError(f"Invalid record_id for locking: {record_id}. Must be positive integer.")
        tier = cls.MODEL_TIER_HIERARCHY.get(model_name, 999)
        return (tier, model_name, record_id)

    @classmethod
    def order_lock_requests(cls, requests: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        unique_requests = list(set(requests))
        return sorted(unique_requests, key=lambda req: cls.get_canonical_sort_key(req[0], req[1]))

    @classmethod
    def get_canonical_lock_order(
        cls, records_spec: Sequence[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        """Sort heterogeneous (model_name, record_id) pairs into a deterministic global lock order."""
        validated: List[Tuple[int, str, int]] = []
        seen: Set[Tuple[str, int]] = set()
        for model_name, record_id in records_spec:
            if not isinstance(model_name, str) or not model_name.strip():
                raise ValueError("Invalid model_name in lock specification.")
            if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id <= 0:
                raise ValueError(f"Invalid record_id {record_id} for model {model_name}.")
            key = (model_name, record_id)
            if key not in seen:
                seen.add(key)
                tier = cls.MODEL_LOCK_TIERS.get(model_name, 999)
                validated.append((tier, model_name, record_id))

        validated.sort(key=lambda item: (item[0], item[1], item[2]))
        return [(item[1], item[2]) for item in validated]

    @classmethod
    def acquire_deterministic_locks(
        cls,
        cursor: Any,
        model_name: str,
        record_ids: List[int],
        current_highest_tier: int = 0,
    ) -> int:
        if not record_ids:
            return current_highest_tier

        requested_tier = cls.LOCK_TIERS.get(model_name, 99)
        if requested_tier < current_highest_tier:
            raise LockTierViolationError(
                f"Deadlock hazard: Attempted to acquire tier {requested_tier} ({model_name}) "
                f"while holding tier {current_highest_tier} locks."
            )

        sorted_ids = sorted(list(set(record_ids)))
        table_name = model_name.replace(".", "_")
        query = f"SELECT id FROM {table_name} WHERE id = ANY(%s) ORDER BY id ASC FOR UPDATE"
        cursor.execute(query, [sorted_ids])
        return max(current_highest_tier, requested_tier)

    def acquire_locks(
        self,
        model_name: str,
        record_ids: List[int],
        nowait: bool = False,
    ) -> List[int]:
        if model_name not in self.MODEL_LOCK_TIERS:
            raise ValueError(f"Model '{model_name}' is not registered in the Canonical Lock Hierarchy.")

        tier = self.MODEL_LOCK_TIERS[model_name]
        if tier < self._current_max_tier_acquired:
            raise LockHierarchyViolationError(
                f"Deadlock Hazard: Cannot acquire lock on '{model_name}' (Tier {tier}) after "
                f"acquiring locks on Tier {self._current_max_tier_acquired}."
            )

        if not record_ids:
            return []

        valid_ids: List[int] = []
        for rid in record_ids:
            if not isinstance(rid, int) or isinstance(rid, bool) or rid <= 0:
                raise ValueError(f"Invalid record ID for locking: {rid}")
            valid_ids.append(rid)

        sorted_ids = sorted(set(valid_ids))
        table_name = model_name.replace(".", "_")
        lock_mode = "FOR UPDATE NOWAIT" if nowait else "FOR UPDATE"
        query = f"SELECT id FROM {table_name} WHERE id = ANY(%s) ORDER BY id ASC {lock_mode}"

        self.cr.execute(query, (sorted_ids,))
        locked_ids = [row[0] for row in self.cr.fetchall()]
        self._current_max_tier_acquired = tier
        return locked_ids

    def _get_mutex(self, key: ResourceLockKey) -> threading.Lock:
        with self._pool_lock:
            if key not in self._mutex_pool:
                self._mutex_pool[key] = threading.Lock()
            return self._mutex_pool[key]

    def acquire(
        self, level: LockLevel, resource_id: str, timeout_seconds: float = 5.0
    ) -> ResourceLockKey:
        key = ResourceLockKey(level=level, resource_id=str(resource_id))
        held = list(_THREAD_HELD_LOCKS.get())

        if held:
            highest_held = held[-1]
            if key.level < highest_held.level:
                raise LockHierarchyError(
                    f"Lock hierarchy inversion violation: Attempting to acquire {key.level.name} ({key.level.value}) "
                    f"while already holding higher level {highest_held.level.name} ({highest_held.level.value})."
                )
            if key.level == highest_held.level and key.resource_id <= highest_held.resource_id:
                raise LockHierarchyError(
                    f"Lock total-order violation within same level {key.level.name}: "
                    f"Attempting to acquire resource '{key.resource_id}' while holding '{highest_held.resource_id}'."
                )

        mutex = self._get_mutex(key)
        start_time = time.monotonic()
        acquired = mutex.acquire(timeout=timeout_seconds)
        elapsed = time.monotonic() - start_time

        if not acquired:
            raise LockTimeoutError(
                f"Failed to acquire canonical lock {key.level.name}::{key.resource_id} within {timeout_seconds}s (elapsed: {elapsed:.3f}s)."
            )

        held.append(key)
        _THREAD_HELD_LOCKS.set(tuple(held))
        return key

    def release(self, key: ResourceLockKey) -> None:
        held = list(_THREAD_HELD_LOCKS.get())
        if not held or held[-1] != key:
            expected = held[-1] if held else "None"
            raise LockHierarchyError(
                f"Illegal LIFO lock release order: Expected to release {expected}, but requested release of {key}."
            )

        mutex = self._get_mutex(key)
        mutex.release()
        held.pop()
        _THREAD_HELD_LOCKS.set(tuple(held))

    def release_all_for_current_scope(self) -> None:
        held = list(_THREAD_HELD_LOCKS.get())
        while held:
            top_key = held[-1]
            try:
                mutex = self._get_mutex(top_key)
                mutex.release()
            except RuntimeError as exc:
                _logger.error("Mutex release error during LIFO unwind for %s: %s", top_key, exc)
            held.pop()
        _THREAD_HELD_LOCKS.set(())


class DeterministicHeterogeneousLockManager(CanonicalLockHierarchyManager):
    """Guarantees global linear lock acquisition ordering across heterogeneous Odoo models."""


class CanonicalLockHierarchy:
    """Enforces strict lexicographical resource locking with monotonic timeouts to prevent
    circular wait deadlocks and worker starvation (CWE-821).
    """

    def __init__(self, secret_key: bytes = b""):
        self._locks: Dict[str, threading.Lock] = {}
        self._meta_lock = threading.Lock()
        self._secret_key = secret_key

    def _get_lock(self, resource_id: str) -> threading.Lock:
        with self._meta_lock:
            if resource_id not in self._locks:
                self._locks[resource_id] = threading.Lock()
            return self._locks[resource_id]

    def acquire_ordered_locks(
        self, resource_ids: List[str], timeout_seconds: float = 5.0
    ) -> List[threading.Lock]:
        sorted_ids = sorted(list(set(resource_ids)))
        acquired_locks: List[threading.Lock] = []
        deadline = time.monotonic() + max(0.05, timeout_seconds)

        for res_id in sorted_ids:
            lock = self._get_lock(res_id)
            remaining_time = deadline - time.monotonic()
            if remaining_time <= 0:
                self._release_partial_locks(acquired_locks)
                raise ConcurrencyLockTimeoutError(
                    f"Monotonic deadline expired while waiting to lock resource: {res_id}"
                )

            acquired = lock.acquire(timeout=remaining_time)
            if not acquired:
                self._release_partial_locks(acquired_locks)
                raise ConcurrencyLockTimeoutError(
                    f"Lock acquisition timed out for resource: {res_id} (timeout={timeout_seconds}s)"
                )
            acquired_locks.append(lock)

        return acquired_locks

    def _release_partial_locks(self, locks: List[threading.Lock]) -> None:
        for lock in reversed(locks):
            try:
                lock.release()
            except RuntimeError as exc:
                _logger.debug("Lock already released during partial cleanup: %s", exc)

    def release_locks(self, locks: List[threading.Lock]) -> None:
        self._release_partial_locks(locks)


class MultiTenantContextGuard:
    """Guarantees thread-local and coroutine multi-tenant isolation against savepoint poisoning (CWE-284)."""

    def __init__(self, secret_salt: bytes):
        self._secret_salt = secret_salt
        self._current_token_var: contextvars.ContextVar[Optional[TenantContextToken]] = (
            contextvars.ContextVar("current_tenant_token", default=None)
        )

    def _compute_signature(self, tenant_id: int, allowed_ids: Tuple[int, ...]) -> str:
        payload = f"{tenant_id}:{','.join(str(x) for x in allowed_ids)}".encode("utf-8")
        return hmac.new(self._secret_salt, payload, hashlib.sha256).hexdigest()

    def create_lease_token(self, tenant_id: int, allowed_company_ids: List[int]) -> TenantContextToken:
        if tenant_id <= 0:
            raise SecurityIntegrityError(f"Invalid primary tenant_id: {tenant_id}. Must be positive integer.")
        clean_allowed = tuple(sorted(list(set(x for x in allowed_company_ids if x > 0))))
        if tenant_id not in clean_allowed:
            clean_allowed = tuple(sorted(clean_allowed + (tenant_id,)))

        signature = self._compute_signature(tenant_id, clean_allowed)
        return TenantContextToken(
            tenant_id=tenant_id,
            allowed_company_ids=clean_allowed,
            lease_signature=signature,
            created_at_mono=time.monotonic(),
            epoch_timestamp=time.time(),
            nonce="default",
            signature=signature,
        )

    def bind_context(self, token: TenantContextToken) -> contextvars.Token:
        expected_sig = self._compute_signature(token.tenant_id, tuple(sorted(token.allowed_company_ids)))
        if not hmac.compare_digest(token.lease_signature, expected_sig):
            raise SecurityIntegrityError("Tampered or invalid tenant context signature detected.")
        return self._current_token_var.set(token)

    def restore_context(self, prev_token: contextvars.Token) -> None:
        self._current_token_var.reset(prev_token)

    def assert_tenant_access(self, record_company_id: int) -> None:
        active_token = self._current_token_var.get()
        if active_token is None:
            raise SecurityIntegrityError("Unauthorized operation: No active tenant context bound.")

        expected_sig = self._compute_signature(
            active_token.tenant_id, tuple(sorted(active_token.allowed_company_ids))
        )
        if not hmac.compare_digest(active_token.lease_signature, expected_sig):
            raise SecurityIntegrityError("Active tenant context token failed cryptographic verification.")

        if record_company_id not in active_token.allowed_company_ids:
            raise SecurityIntegrityError(
                f"Tenant boundary violation: Context tenant {active_token.tenant_id} with "
                f"companies {active_token.allowed_company_ids} attempted to access "
                f"unauthorized company record: {record_company_id}"
            )


class HardenedFormulaSanitizer:
    """Neutralizes CSV/TSV/ODS/Markdown formula injection, control-char cloaking & DDE execution (CWE-1236)."""

    MAX_RECURSION_DEPTH: int = 16
    FORMULA_TRIGGERS: Tuple[str, ...] = ("=", "+", "-", "@", "|", "%")
    CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202e\ufeff]")
    DANGEROUS_PREFIXES = frozenset(
        {
            "=",
            "+",
            "-",
            "@",
            "|",
            "%",
            "\t",
            "\r",
            "\n",
            "\uff1d",
            "\uff0b",
            "\uff0d",
            "\uff20",
            "\uff5c",
            "\ufe62",
            "\ufe63",
            "\ufe66",
        }
    )
    RISKY_PREFIXES: Tuple[str, ...] = (
        "=",
        "+",
        "-",
        "@",
        "|",
        "%",
        "\t",
        "\r",
        "\n",
        "\uff1d",
        "\uff0b",
        "\uff0d",
        "\uff20",
        "\uff5c",
        "\ufe62",
        "\ufe63",
        "\ufe66",
    )
    CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    STRIP_LEADING_REGEX = re.compile(
        r"^[\s\u0000-\u001f\u007f-\u009f\u200b-\u200d\ufeff\u3000]+"
    )
    DANGEROUS_TRIGGER_PATTERN = re.compile(
        r"^[\s\x00-\x1f\x7f\u200b\ufeff\u3000]*([=+\-@|\t\r\n%]|(\uff1d)|(\uff0b)|(\uff0d)|(\uff20)|(\uff5c)|(\ufe62)|(\ufe63)|(\ufe66))"
    )

    @classmethod
    def sanitize_string(cls, value: str) -> str:
        if not value:
            return value
        cleaned = cls.CONTROL_CHAR_RE.sub("", value)
        if not cleaned:
            return ""
        normalized = unicodedata.normalize("NFKD", cleaned)
        stripped = normalized.lstrip(" \t\r\n")
        if not stripped:
            return cleaned
        if stripped[0] in cls.FORMULA_TRIGGERS:
            return "'" + stripped
        return normalized

    @classmethod
    def sanitize_payload(
        cls,
        data: Any,
        max_depth: int = 16,
        current_depth: int = 0,
        seen_refs: Optional[Set[int]] = None,
        ref_retention: Optional[List[Any]] = None,
    ) -> Any:
        if current_depth > max_depth:
            raise CyclicStructureDetected(f"Traversal exceeded maximum allowable depth: {max_depth}")
        if seen_refs is None:
            seen_refs = set()
        if ref_retention is None:
            ref_retention = []

        if isinstance(data, dict):
            obj_id = id(data)
            if obj_id in seen_refs:
                raise CyclicStructureDetected(f"Cyclic dictionary reference detected at depth {current_depth}")
            seen_refs.add(obj_id)
            ref_retention.append(data)
            sanitized_dict: Dict[str, Any] = {}
            for k, v in data.items():
                sanitized_key = cls.sanitize_string(str(k))
                sanitized_val = cls.sanitize_payload(
                    v,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                    seen_refs=seen_refs,
                    ref_retention=ref_retention,
                )
                sanitized_dict[sanitized_key] = sanitized_val
            seen_refs.remove(obj_id)
            return sanitized_dict

        if isinstance(data, (list, tuple, set)):
            obj_id = id(data)
            if obj_id in seen_refs:
                raise CyclicStructureDetected(f"Cyclic iterable reference detected at depth {current_depth}")
            seen_refs.add(obj_id)
            ref_retention.append(data)
            sanitized_items = [
                cls.sanitize_payload(
                    item,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                    seen_refs=seen_refs,
                    ref_retention=ref_retention,
                )
                for item in data
            ]
            seen_refs.remove(obj_id)
            if isinstance(data, tuple):
                return tuple(sanitized_items)
            if isinstance(data, set):
                return set(sanitized_items)
            return sanitized_items

        if isinstance(data, str):
            return cls.sanitize_string(data)

        return data

    @classmethod
    def sanitize_cell(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if not value:
            return value
        clean_val = value.replace("\x00", "")
        normalized = unicodedata.normalize("NFKC", clean_val)
        stripped_norm = cls.STRIP_LEADING_REGEX.sub("", normalized)
        stripped_raw = cls.STRIP_LEADING_REGEX.sub("", clean_val)
        if (
            (stripped_norm and stripped_norm[0] in cls.DANGEROUS_PREFIXES)
            or (stripped_raw and stripped_raw[0] in cls.DANGEROUS_PREFIXES)
            or (normalized and normalized[0] in cls.DANGEROUS_PREFIXES)
            or (clean_val and clean_val[0] in cls.DANGEROUS_PREFIXES)
        ):
            return f"'{clean_val}"
        return clean_val

    @classmethod
    def sanitize_dict_structure(
        cls,
        data: Any,
        seen_ids: Optional[Set[int]] = None,
        depth: int = 0,
    ) -> Any:
        if depth > cls.MAX_RECURSION_DEPTH:
            raise CyclicStructureDetected(f"Max sanitization depth exceeded ({cls.MAX_RECURSION_DEPTH})")
        if seen_ids is None:
            seen_ids = set()

        if isinstance(data, str):
            return cls.sanitize_cell(data)

        if isinstance(data, dict):
            obj_id = id(data)
            if obj_id in seen_ids:
                raise CyclicStructureDetected("Cyclic reference detected during payload sanitization")
            next_seen = seen_ids | {obj_id}
            return {
                cls.sanitize_cell(k) if isinstance(k, str) else k: cls.sanitize_dict_structure(
                    v, next_seen, depth + 1
                )
                for k, v in data.items()
            }

        if isinstance(data, (list, tuple)):
            obj_id = id(data)
            if obj_id in seen_ids:
                raise CyclicStructureDetected("Cyclic reference detected during payload sanitization")
            next_seen = seen_ids | {obj_id}
            sanitized_items = [
                cls.sanitize_dict_structure(item, next_seen, depth + 1) for item in data
            ]
            return tuple(sanitized_items) if isinstance(data, tuple) else sanitized_items

        return data

    @classmethod
    def sanitize_field(cls, value: Any) -> str:
        if value is None:
            return ""
        raw_text = str(value)
        normalized = unicodedata.normalize("NFKC", raw_text)
        cleaned = cls.CONTROL_CHAR_REGEX.sub("", normalized)
        if not cleaned:
            return ""
        stripped = cls.STRIP_LEADING_REGEX.sub("", cleaned)
        if not stripped:
            return cleaned
        if stripped[0] in cls.DANGEROUS_PREFIXES or cleaned[0] in cls.DANGEROUS_PREFIXES:
            return f"'{cleaned}"
        if "|" in cleaned and ("cmd" in cleaned.lower() or "powershell" in cleaned.lower()):
            return f"'{cleaned}"
        return cleaned

    @classmethod
    def sanitize_row(cls, row: List[Any]) -> List[str]:
        return [cls.sanitize_field(item) for item in row]

    @classmethod
    def sanitize_cell_value(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKC", value)
        cleaned = cls.STRIP_LEADING_REGEX.sub("", normalized)
        if cleaned.startswith(cls.RISKY_PREFIXES):
            return "'" + value
        raw_stripped = cls.STRIP_LEADING_REGEX.sub("", value)
        if raw_stripped.startswith(cls.RISKY_PREFIXES):
            return "'" + value
        return value

    @classmethod
    def sanitize_record_dict(cls, record_dict: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        for key, val in record_dict.items():
            if isinstance(val, dict):
                sanitized[key] = cls.sanitize_record_dict(val)
            elif isinstance(val, list):
                sanitized[key] = [
                    cls.sanitize_record_dict(item)
                    if isinstance(item, dict)
                    else (cls.sanitize_cell_value(item) if isinstance(item, str) else item)
                    for item in val
                ]
            else:
                sanitized[key] = cls.sanitize_cell_value(val)
        return sanitized

    @classmethod
    def sanitize_scalar(cls, value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, (int, float, bool)):
            return value
        str_val = str(value)
        if not str_val:
            return ""
        if cls.DANGEROUS_TRIGGER_PATTERN.search(str_val):
            return f"'\t{str_val}"
        return str_val

    @classmethod
    def sanitize_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        for key, val in record.items():
            safe_key = cls.sanitize_scalar(key)
            if isinstance(val, dict):
                sanitized[str(safe_key)] = cls.sanitize_record(val)
            elif isinstance(val, list):
                sanitized[str(safe_key)] = [
                    cls.sanitize_record(item) if isinstance(item, dict) else cls.sanitize_scalar(item)
                    for item in val
                ]
            else:
                sanitized[str(safe_key)] = cls.sanitize_scalar(val)
        return sanitized

    @classmethod
    def sanitize_table(cls, rows: List[List[Any]]) -> List[List[Any]]:
        return [[cls.sanitize_scalar(cell) for cell in row] for row in rows]


FormulaInjectionSanitizer = HardenedFormulaSanitizer
FullwidthFormulaSanitizer = HardenedFormulaSanitizer


from decimal import Decimal
from typing import Callable, FrozenSet, Iterable, Mapping, Union


class TenantAccessViolation(PermissionError, TenantBoundaryViolation):
    """Raised when an RPC or ORM context attempts cross-company boundary violation."""


class FormulaSanitizationError(ValueError, SecurityException):
    """Raised when a formula violates grammar, security, or depth invariants."""


def validate_tenant_access(
    requested_company_id: Union[int, Any],
    authenticated_user: Any = None,
    allowed_company_ids: Optional[Union[Set[int], List[int]]] = None,
) -> int:
    """Enforces tenant scoping across both 2-arg (requested_id, allowed_ids) and 3-arg (requested_id, user, allowed_ids) signatures."""
    if allowed_company_ids is None and isinstance(authenticated_user, (list, set, tuple, frozenset)):
        resolved_allowed = authenticated_user
        resolved_user = None
    else:
        resolved_allowed = allowed_company_ids
        resolved_user = authenticated_user

    if isinstance(requested_company_id, bool):
        raise TenantAccessViolation(
            f"Type evasion attempt: boolean {requested_company_id!r} is not a valid tenant ID."
        )

    if not isinstance(requested_company_id, int):
        raise TenantAccessViolation(
            f"Tenant ID must be an integer. Received type: {type(requested_company_id).__name__}"
        )

    if requested_company_id <= 0:
        raise TenantAccessViolation(
            f"Tenant ID must be a strictly positive integer. Received: {requested_company_id}"
        )

    if not resolved_allowed or not all(
        isinstance(cid, int) and not isinstance(cid, bool) and cid > 0
        for cid in resolved_allowed
    ):
        raise TenantAccessViolation(
            "Allowed tenant context contains invalid or unauthenticated entries."
        )

    if requested_company_id not in resolved_allowed:
        user_login = getattr(resolved_user, "login", "anonymous") if resolved_user is not None else "anonymous"
        _logger.warning(
            "Security Boundary Alert: User '%s' attempted unauthorized access to company_id=%d. Permitted set: %s",
            user_login,
            requested_company_id,
            resolved_allowed,
        )
        raise TenantAccessViolation(
            f"Access Denied: Tenant ID {requested_company_id} is not within authorized scope {resolved_allowed}."
        )

    return requested_company_id


AtomicMultiTenantGuard.validate_tenant_access = staticmethod(validate_tenant_access)


class LockSystemTier(enum.IntEnum):
    DISTRIBUTED_REDIS = 1
    POSTGRES_ADVISORY = 2
    POSTGRES_ROW_LEVEL = 3


class LockTier(enum.IntEnum):
    """Canonical global lock hierarchy tiers for heterogeneous concurrency control."""

    DISTRIBUTED_REDIS = 1
    POSTGRES_ADVISORY = 2
    POSTGRES_ROW_LEVEL = 3
    GLOBAL_CONFIG = 10
    TENANT_COMPANY = 20
    CURRENCY_EXCHANGE = 30
    ACCOUNT_JOURNAL = 40
    ACCOUNT_MOVE_LINE = 50


class DeadlockPreventionError(RuntimeError, LockHierarchyViolationError):
    """Raised when lock acquisition violates canonical global tier ordering."""


class ConcurrencyLockError(ConcurrencyLockTimeoutError):
    """Base exception for lock acquisition and lifecycle management errors."""


class LockAcquisitionTimeoutError(TimeoutError, ConcurrencyLockError):
    """Raised when a lock cannot be acquired within the bounded timeout."""


LockTimeoutError = LockAcquisitionTimeoutError
LockTimeoutOrConflict = LockAcquisitionTimeoutError


class SecurityViolationError(SecurityException):
    """Raised when an unauthorized access, malformed input, or sandbox escape is detected."""


class ASTFormulaSandboxError(FormulaSanitizationError, SecurityViolationError):
    """Raised when an expression violates AST mathematical sandboxing rules."""


FormulaSecurityViolation = ASTFormulaSandboxError
SecurityFormulaEvaluationError = ASTFormulaSandboxError
FormulaSecurityError = ASTFormulaSandboxError


class TenantSecurityError(PermissionError, TenantBoundaryViolation, SecurityViolationError):
    """Raised when cross-tenant data access or context leakage is detected."""


class TenantIsolationError(TenantSecurityError):
    """Raised when multi-company tenant context drift or tampering is identified."""


TenantSecurityException = TenantIsolationError


class _DualCanonicalTupleDescriptor:
    """Allows HeterogeneousLockKey.canonical_tuple to act as an instance property -> Tuple[int, int] and a classmethod canonical_tuple(class_id, object_id) -> Tuple[int, int]."""

    def __get__(self, instance: Optional["HeterogeneousLockKey"], owner: type) -> Any:
        if instance is not None:
            return instance._hash_pair
        return owner._canonical_tuple_from_ints


class _HybridAcquireAllList(list):
    """List of acquired (int4, int4) lock pairs that also acts as a context manager for with-statement compatibility."""

    def __enter__(self) -> "_HybridAcquireAllList":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        return None


class HeterogeneousLockKey:
    """Immutable composite key guaranteeing global monotonic lock ordering across Redis, PG Advisory, PG Row, and Logical LockTiers."""

    INT4_MIN: int = -2147483648
    INT4_MAX: int = 2147483647

    __slots__ = (
        "tier",
        "tenant_id",
        "resource_id",
        "record_id",
        "tier_precedence",
        "tier_name",
        "resource_type",
        "namespace",
        "canonical_key",
        "_hash_pair",
        "_mode",
    )

    _GLOBAL_LOCK_REGISTRY: Dict[str, threading.Lock] = {}
    _REGISTRY_LOCK: threading.Lock = threading.Lock()

    _PRECEDENCE_MAP: Dict[str, int] = {
        "system": 10,
        "company": 20,
        "journal": 30,
        "partner": 40,
        "order": 50,
    }

    def __init__(
        self,
        tier: Union[LockTier, LockSystemTier, int, str, None] = None,
        tenant_or_resource: Union[int, str, None] = None,
        resource_id: Optional[Union[int, str]] = None,
        record_id: Optional[int] = None,
        *,
        tier_precedence: Optional[int] = None,
        tier_name: Optional[str] = None,
    ) -> None:
        if tier_precedence is not None and tier_name is not None:
            # Named dataclass-compatible mode: (tier_precedence, tier_name, resource_id)
            res_str = str(resource_id if resource_id is not None else (tenant_or_resource or ""))
            self.tier_precedence = int(tier_precedence)
            self.tier_name = str(tier_name).lower()
            self.tier = self.tier_precedence
            self.resource_type = self.tier_name
            self.namespace = self.resource_type
            self.resource_id = res_str
            self.canonical_key = f"{self.resource_type}:{res_str.lower()}"
            self._hash_pair = self._compute_canonical_hash_pair(self.namespace, self.resource_id)
            self.tenant_id = 0
            self.record_id = 0
            self._mode = "named"
        elif isinstance(tier, int) and not isinstance(tier, (LockTier, LockSystemTier)) and isinstance(tenant_or_resource, str) and isinstance(resource_id, str) and record_id is None:
            # Positional 3-arg mode: (tier_precedence: int, tier_name: str, resource_id: str)
            self.tier_precedence = int(tier)
            self.tier_name = tenant_or_resource.lower()
            self.tier = self.tier_precedence
            self.resource_type = self.tier_name
            self.namespace = self.resource_type
            self.resource_id = resource_id
            self.canonical_key = f"{self.resource_type}:{resource_id.lower()}"
            self._hash_pair = self._compute_canonical_hash_pair(self.namespace, self.resource_id)
            self.tenant_id = 0
            self.record_id = 0
            self._mode = "named"
        elif isinstance(tier, str) and resource_id is None and record_id is None:
            # 2-string mode: (resource_type: str, resource_id: str)
            if not tier.strip() or not isinstance(tenant_or_resource, str) or not tenant_or_resource.strip():
                raise ValueError("resource_type and resource_id must be non-empty strings.")
            self.resource_type = tier.strip().lower()
            self.namespace = self.resource_type
            self.resource_id = tenant_or_resource.strip()
            self.canonical_key = f"{self.resource_type}:{self.resource_id.lower()}"
            self._hash_pair = self._compute_canonical_hash_pair(self.namespace, self.resource_id)
            self.tier_name = self.resource_type
            self.tier_precedence = self._PRECEDENCE_MAP.get(self.resource_type, 100)
            self.tier = self.tier_precedence
            self.tenant_id = 0
            self.record_id = 0
            self._mode = "str2arg"
        elif resource_id is None and record_id is None:
            # 2-arg mode: (tier: LockTier, resource_id: str)
            if not isinstance(tier, (LockTier, LockSystemTier)):
                try:
                    tier = LockTier(int(tier))  # type: ignore[arg-type]
                except (ValueError, TypeError) as exc:
                    raise TypeError(f"Invalid lock tier: {tier!r}") from exc
            if not isinstance(tenant_or_resource, str) or not tenant_or_resource.strip():
                raise ValueError("Resource identifier must be a non-empty string.")
            self.tier = tier
            self.tier_precedence = int(tier)
            self.tier_name = tier.name.lower()
            self.resource_type = self.tier_name
            self.namespace = self.resource_type
            self.resource_id = tenant_or_resource.strip()
            self.canonical_key = f"{self.resource_type}:{self.resource_id.lower()}"
            self._hash_pair = self._compute_canonical_hash_pair(self.namespace, self.resource_id)
            self.tenant_id = 0
            self.record_id = 0
            self._mode = "2arg"
        else:
            # 4-arg mode: (tier: LockSystemTier, tenant_id: int, resource_id: int, record_id: int)
            tenant_id = tenant_or_resource
            if not isinstance(tenant_id, int) or isinstance(tenant_id, bool) or tenant_id <= 0:
                raise ValueError(f"tenant_id must be a positive integer, got: {tenant_id!r}")
            if not isinstance(resource_id, int) or isinstance(resource_id, bool) or resource_id < 0:
                raise ValueError(f"resource_id must be a non-negative integer, got: {resource_id!r}")
            if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id < 0:
                raise ValueError(f"record_id must be a non-negative integer, got: {record_id!r}")
            self.tier = LockSystemTier(int(tier))  # type: ignore[arg-type]
            self.tier_precedence = int(self.tier)
            self.tier_name = self.tier.name.lower()
            self.resource_type = self.tier_name
            self.namespace = self.resource_type
            self.tenant_id = tenant_id
            self.resource_id = resource_id
            self.record_id = record_id
            self.canonical_key = f"{self.resource_type}:{tenant_id}:{resource_id}:{record_id}"
            self._hash_pair = self._compute_canonical_hash_pair(
                self.namespace, f"{tenant_id}:{resource_id}:{record_id}"
            )
            self._mode = "4arg"

    @classmethod
    def to_signed_int4(cls, val: int) -> int:
        normalized = int(val) & 0xFFFFFFFF
        if normalized > cls.INT4_MAX:
            return normalized - 0x100000000
        return normalized

    @classmethod
    def _canonical_tuple_from_ints(cls, class_id: int, object_id: int) -> Tuple[int, int]:
        return (cls.to_signed_int4(class_id), cls.to_signed_int4(object_id))

    @staticmethod
    def _compute_canonical_hash_pair(ns: str, res: str) -> Tuple[int, int]:
        digest = hashlib.sha256(f"{ns}:{res}".encode("utf-8")).digest()
        k1, k2 = struct.unpack(">ii", digest[:8])
        return (k1, k2)

    canonical_tuple = _DualCanonicalTupleDescriptor()

    @classmethod
    def create(cls, tier_name: str, resource_id: str) -> "HeterogeneousLockKey":
        precedence = cls._PRECEDENCE_MAP.get(tier_name.lower(), 100)
        return cls(
            tier_precedence=precedence,
            tier_name=tier_name.lower(),
            resource_id=str(resource_id),
        )

    @classmethod
    def get_or_create_lock(cls, canonical_key: str) -> threading.Lock:
        with cls._REGISTRY_LOCK:
            if canonical_key not in cls._GLOBAL_LOCK_REGISTRY:
                cls._GLOBAL_LOCK_REGISTRY[canonical_key] = threading.Lock()
            return cls._GLOBAL_LOCK_REGISTRY[canonical_key]

    @classmethod
    @contextmanager
    def _acquire_all_thread_locks(
        cls,
        keys: List["HeterogeneousLockKey"],
        eff_timeout: float,
    ):
        if not keys:
            yield []
            return

        unique_sorted_keys = sorted(set(keys))
        acquired_locks: List[Tuple[str, threading.Lock]] = []
        try:
            for lock_key in unique_sorted_keys:
                raw_lock = cls.get_or_create_lock(lock_key.canonical_key)
                acquired = raw_lock.acquire(timeout=eff_timeout)
                if not acquired:
                    raise LockTimeoutOrConflict(
                        f"Failed to acquire lock '{lock_key.canonical_key}' "
                        f"within {eff_timeout}s timeout."
                    )
                acquired_locks.append((lock_key.canonical_key, raw_lock))

            yield [k for k, _ in acquired_locks]
        finally:
            for _, lock_instance in reversed(acquired_locks):
                lock_instance.release()

    @classmethod
    def acquire_all(
        cls,
        cursor_or_keys: Any,
        keys_or_timeout: Optional[Any] = None,
        timeout_seconds: float = 5.0,
    ) -> Any:
        if hasattr(cursor_or_keys, "execute"):
            cursor = cursor_or_keys
            seq_keys = list(keys_or_timeout) if keys_or_timeout else []
            if not seq_keys:
                return _HybridAcquireAllList([])
            normalized_pairs = set()
            for item in seq_keys:
                if isinstance(item, HeterogeneousLockKey):
                    normalized_pairs.add(item._hash_pair)
                elif isinstance(item, (tuple, list)) and len(item) == 2:
                    normalized_pairs.add(cls._canonical_tuple_from_ints(int(item[0]), int(item[1])))
                else:
                    raise TypeError(f"Unsupported lock key element: {item!r}")
            sorted_pairs = sorted(normalized_pairs, key=lambda x: (x[0], x[1]))
            for c_id, o_id in sorted_pairs:
                cursor.execute("SELECT pg_advisory_xact_lock(%s, %s);", (c_id, o_id))
            return _HybridAcquireAllList(sorted_pairs)

        keys: List[HeterogeneousLockKey] = list(cursor_or_keys) if cursor_or_keys else []
        eff_timeout = (
            float(keys_or_timeout)
            if isinstance(keys_or_timeout, (int, float))
            else float(timeout_seconds)
        )
        return cls._acquire_all_thread_locks(keys, eff_timeout)

    def as_tuple(self) -> Tuple[Any, ...]:
        if self._mode == "str2arg":
            return (self.canonical_key,)
        if self._mode == "named":
            return (self.tier_precedence, self.tier_name, str(self.resource_id))
        if self._mode == "2arg":
            return (int(self.tier), str(self.resource_id))
        return (int(self.tier), self.tenant_id, int(self.resource_id), self.record_id)

    def __lt__(self, other: "HeterogeneousLockKey") -> bool:
        if not isinstance(other, HeterogeneousLockKey):
            return NotImplemented
        return self.as_tuple() < other.as_tuple()

    def __le__(self, other: "HeterogeneousLockKey") -> bool:
        if not isinstance(other, HeterogeneousLockKey):
            return NotImplemented
        return self.as_tuple() <= other.as_tuple()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, HeterogeneousLockKey):
            return False
        return self.as_tuple() == other.as_tuple()

    def __hash__(self) -> int:
        return hash(self.as_tuple())

    def __repr__(self) -> str:
        if self._mode == "str2arg":
            return f"HeterogeneousLockKey({self.namespace!r}, {self.resource_id!r} -> {self._hash_pair})"
        if self._mode == "named":
            return f"HeterogeneousLockKey(tier_precedence={self.tier_precedence}, tier_name={self.tier_name!r}, resource_id={self.resource_id!r})"
        if self._mode == "2arg":
            return f"LockKey({self.tier.name}:{self.resource_id})"
        return (
            f"HeterogeneousLockKey(tier={self.tier.name}, tenant={self.tenant_id}, "
            f"resource={self.resource_id}, record={self.record_id})"
        )


class _AcquiredLockList(list):
    """List of acquired HeterogeneousLockKeys that also acts as a context manager for automatic release."""

    def __init__(
        self,
        items: Iterable[HeterogeneousLockKey],
        manager: "_HeterogeneousCrossTierLockManager",
        is_4arg_mode: bool = False,
    ) -> None:
        super().__init__(items)
        self._manager = manager
        self._is_4arg_mode = is_4arg_mode

    def __enter__(self) -> "_AcquiredLockList":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._is_4arg_mode:
            for key in reversed(self):
                if int(key.tier) == int(LockSystemTier.DISTRIBUTED_REDIS):
                    self._manager._release_redis_mutex(key)
            self._manager._acquired_locks.clear()
        else:
            self._manager.release_heterogeneous_locks(list(self))


class _HeterogeneousCrossTierLockManager(CanonicalLockHierarchyManager):
    """Acquires heterogeneous locks in strictly sorted order with timeout rollback and thread-local escalation guard."""

    _global_registry_lock: threading.Lock = threading.Lock()
    _active_locks: Dict[HeterogeneousLockKey, threading.RLock] = {}
    _lock_holders: Dict[HeterogeneousLockKey, int] = {}

    def __init__(
        self,
        cr: Any = None,
        redis_client: Optional[Any] = None,
        default_timeout_seconds: float = 3.0,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        super().__init__(cr=cr)
        self.redis_client = redis_client
        resolved_timeout = timeout_seconds if timeout_seconds is not None else default_timeout_seconds
        self._default_timeout = max(0.05, float(resolved_timeout))
        self.timeout_seconds = self._default_timeout
        self._acquired_locks: List[HeterogeneousLockKey] = []
        self._acquired_keys_lifo: List[HeterogeneousLockKey] = []
        self._local_lock_registry: Dict[HeterogeneousLockKey, threading.RLock] = self._active_locks
        self._registry_mutex = self._global_registry_lock
        self._thread_held_locks: contextvars.ContextVar[Tuple[HeterogeneousLockKey, ...]] = (
            contextvars.ContextVar("thread_held_locks", default=())
        )

    def _get_or_create_lock(self, key: HeterogeneousLockKey) -> threading.RLock:
        with self._global_registry_lock:
            if key not in self._active_locks:
                self._active_locks[key] = threading.RLock()
            return self._active_locks[key]

    def _get_or_create_primitive(self, key: HeterogeneousLockKey) -> threading.RLock:
        return self._get_or_create_lock(key)

    def _acquire_single_lock(self, key: HeterogeneousLockKey, timeout: float) -> bool:
        primitive = self._get_or_create_primitive(key)
        return primitive.acquire(blocking=True, timeout=timeout)

    def _release_single_lock(self, key: HeterogeneousLockKey) -> None:
        with self._global_registry_lock:
            primitive = self._active_locks.get(key)
        if primitive is not None:
            try:
                primitive.release()
            except RuntimeError:
                pass

    def _rollback_batch(self, acquired_batch: List[HeterogeneousLockKey]) -> None:
        for key in reversed(acquired_batch):
            self._release_single_lock(key)

    def acquire_all(
        self, keys: List[HeterogeneousLockKey]
    ) -> "_HeterogeneousCrossTierLockManager":
        sorted_keys = sorted(list(set(keys)))
        deadline = time.monotonic() + self.timeout_seconds
        acquired_so_far: List[HeterogeneousLockKey] = []

        for key in sorted_keys:
            remaining_time = deadline - time.monotonic()
            if remaining_time <= 0:
                self._rollback(acquired_so_far)
                raise LockTimeoutError(
                    f"Lock acquisition timed out while attempting to acquire {key}. "
                    f"Deadlock prevented. Acquired: {acquired_so_far}"
                )

            lock = self._get_or_create_lock(key)
            acquired = lock.acquire(timeout=remaining_time)

            if not acquired:
                self._rollback(acquired_so_far)
                raise LockTimeoutError(
                    f"Lock acquisition timed out: Failed to acquire lock {key} within allotted timeout."
                )

            acquired_so_far.append(key)

        self._acquired_keys_lifo = acquired_so_far
        return self

    def _rollback(self, keys_to_release: List[HeterogeneousLockKey]) -> None:
        release_errors: List[str] = []
        for key in reversed(keys_to_release):
            with self._global_registry_lock:
                lock = self._active_locks.get(key)
            if lock is not None:
                try:
                    lock.release()
                except RuntimeError as ex:
                    release_errors.append(f"Error releasing {key}: {str(ex)}")

        if release_errors:
            _logger.error("Critical error during lock rollback: %s", " | ".join(release_errors))
            raise ConcurrencyLockError(f"Partial lock rollback failure: {release_errors}")

    def release_all(self) -> None:
        keys_to_release = list(self._acquired_keys_lifo)
        self._acquired_keys_lifo.clear()
        self._rollback(keys_to_release)

    def __enter__(self) -> "_HeterogeneousCrossTierLockManager":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release_all()

    def _acquire_postgres_advisory(self, key: HeterogeneousLockKey, timeout_sec: float) -> bool:
        lock_id_64 = (
            ((key.tenant_id & 0xFFFF) << 48)
            | ((int(key.resource_id) & 0xFFFF) << 32)
            | (key.record_id & 0xFFFFFFFF)
        )
        start_time = time.monotonic()
        while True:
            self.cr.execute(
                "SELECT pg_try_advisory_xact_lock(%s);",
                (lock_id_64,),
            )
            row = self.cr.fetchone()
            if row and row[0]:
                return True
            if time.monotonic() - start_time >= timeout_sec:
                return False
            time.sleep(0.01)

    def _acquire_postgres_row(self, key: HeterogeneousLockKey, timeout_sec: float) -> bool:
        self.cr.execute(f"SET LOCAL lock_timeout = '{int(timeout_sec * 1000)}ms';")
        self.cr.execute(
            "SELECT id FROM account_move WHERE id = %s AND company_id = %s FOR UPDATE;",
            (key.record_id, key.tenant_id),
        )
        res = self.cr.fetchone()
        return res is not None

    def _acquire_redis_mutex(self, key: HeterogeneousLockKey, timeout_sec: float) -> bool:
        if self.redis_client is None:
            return True
        redis_key = f"lock:{key.tenant_id}:{key.resource_id}:{key.record_id}"
        start_time = time.monotonic()
        while True:
            acquired = self.redis_client.set(redis_key, "locked", nx=True, ex=30)
            if acquired:
                return True
            if time.monotonic() - start_time >= timeout_sec:
                return False
            time.sleep(0.01)

    def _release_redis_mutex(self, key: HeterogeneousLockKey) -> None:
        if self.redis_client is not None:
            redis_key = f"lock:{key.tenant_id}:{key.resource_id}:{key.record_id}"
            self.redis_client.delete(redis_key)

    def acquire_heterogeneous_locks(
        self,
        requested_keys: Iterable[HeterogeneousLockKey],
        timeout_sec: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> _AcquiredLockList:
        raw_list = list(requested_keys)
        if not raw_list:
            return _AcquiredLockList([], self, is_4arg_mode=False)

        effective_timeout = (
            timeout
            if timeout is not None
            else (timeout_sec if timeout_sec is not None else self._default_timeout)
        )

        # Check if 4-arg DB/Redis mode is used
        if raw_list[0]._mode == "4arg" and (self.cr is not None or self.redis_client is not None):
            sorted_keys = sorted(set(raw_list))
            self._acquired_locks = []
            try:
                for key in sorted_keys:
                    acquired = False
                    if int(key.tier) == int(LockSystemTier.DISTRIBUTED_REDIS):
                        acquired = self._acquire_redis_mutex(key, effective_timeout)
                    elif int(key.tier) == int(LockSystemTier.POSTGRES_ADVISORY):
                        acquired = self._acquire_postgres_advisory(key, effective_timeout)
                    elif int(key.tier) == int(LockSystemTier.POSTGRES_ROW_LEVEL):
                        acquired = self._acquire_postgres_row(key, effective_timeout)

                    if not acquired:
                        raise LockAcquisitionTimeoutError(
                            f"DeterministicHeterogeneousLockManager: Failed to acquire {key} within {effective_timeout}s timeout."
                        )
                    self._acquired_locks.append(key)
                return _AcquiredLockList(self._acquired_locks, self, is_4arg_mode=True)
            except Exception:
                for key in reversed(self._acquired_locks):
                    if int(key.tier) == int(LockSystemTier.DISTRIBUTED_REDIS):
                        self._release_redis_mutex(key)
                self._acquired_locks.clear()
                raise

        # 2-arg thread-local hierarchical lock mode
        deduplicated_requests = sorted(set(raw_list))
        current_held = self._thread_held_locks.get()
        if current_held:
            highest_held = current_held[-1]
            lowest_new_request = deduplicated_requests[0]
            if lowest_new_request < highest_held:
                raise DeadlockPreventionError(
                    f"Lock hierarchy violation: Cannot acquire {lowest_new_request} "
                    f"while already holding higher/later lock {highest_held}."
                )

        acquired_in_this_batch: List[HeterogeneousLockKey] = []
        deadline = time.monotonic() + effective_timeout

        try:
            for key in deduplicated_requests:
                if key in current_held:
                    continue
                remaining_time = max(0.001, deadline - time.monotonic())
                success = self._acquire_single_lock(key, timeout=remaining_time)
                if not success:
                    raise LockAcquisitionTimeoutError(
                        f"Timed out waiting to acquire lock on {key}."
                    )
                acquired_in_this_batch.append(key)

            updated_held = tuple(sorted(set(current_held).union(acquired_in_this_batch)))
            self._thread_held_locks.set(updated_held)
            return _AcquiredLockList(acquired_in_this_batch, self, is_4arg_mode=False)
        except BaseException:
            self._rollback_batch(acquired_in_this_batch)
            raise

    def release_heterogeneous_locks(
        self,
        locks_to_release: Iterable[HeterogeneousLockKey],
    ) -> None:
        release_list = sorted(set(locks_to_release), reverse=True)
        current_held = set(self._thread_held_locks.get())
        for key in release_list:
            if key in current_held:
                self._release_single_lock(key)
                current_held.remove(key)
        self._thread_held_locks.set(tuple(sorted(current_held)))


DeterministicHeterogeneousLockManager = _HeterogeneousCrossTierLockManager


from typing import Callable, NamedTuple


class TenantSecurityContext(NamedTuple):
    tenant_id: str
    user_id: str
    company_id: str
    is_active: bool = True


_ACTIVE_SCOPED_TENANT_ID: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "active_scoped_tenant_id", default=None
)
_ACTIVE_SCOPED_TENANT_STR_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "active_scoped_tenant_str_id", default=None
)
_ALLOWED_COMPANY_IDS: contextvars.ContextVar[FrozenSet[int]] = contextvars.ContextVar(
    "allowed_company_ids", default=frozenset()
)
_TENANT_CONTEXT_VAR: contextvars.ContextVar[Optional[TenantSecurityContext]] = contextvars.ContextVar(
    "enterprise_tenant_context", default=None
)


_ACTIVE_TENANT_DEPTH: contextvars.ContextVar[int] = contextvars.ContextVar(
    "active_tenant_depth", default=0
)

INT4_MIN: int = -2147483648
INT4_MAX: int = 2147483647
INT4_RANGE: int = 4294967296  # 2^32


def to_signed_int4(value: int) -> int:
    """
    Deterministically folds any integer into a PostgreSQL-compatible signed 32-bit integer (-2^31 to 2^31 - 1).
    Guarantees zero 'integer out of range' SQL errors when passed to pg_advisory_xact_lock(int4, int4).
    """
    unsigned_val = int(value) & 0xFFFFFFFF
    if unsigned_val > INT4_MAX:
        return unsigned_val - INT4_RANGE
    return unsigned_val


def canonical_advisory_key(namespace: str, resource_id: Union[int, str]) -> Tuple[int, int]:
    """
    Computes a deterministic, collision-resistant (int4, int4) pair for PostgreSQL pg_advisory_xact_lock(key1, key2).
    Part 1: Signed 32-bit integer hash of the namespace identifier.
    Part 2: Signed 32-bit integer of the resource_id (direct bounded int4, folded int, or SHA-256 slice for strings).
    """
    if not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("Advisory lock namespace must be a non-empty string.")
    ns_hash_bytes = hashlib.sha256(namespace.encode("utf-8")).digest()
    (ns_int_raw,) = struct.unpack(">I", ns_hash_bytes[:4])
    key_part1 = to_signed_int4(ns_int_raw)

    if isinstance(resource_id, int) and not isinstance(resource_id, bool):
        if INT4_MIN <= resource_id <= INT4_MAX:
            key_part2 = resource_id
        else:
            key_part2 = to_signed_int4(resource_id)
    else:
        res_str = str(resource_id)
        res_digest = hashlib.sha256(res_str.encode("utf-8")).digest()
        (key2_raw,) = struct.unpack(">I", res_digest[:4])
        key_part2 = to_signed_int4(key2_raw)

    return (key_part1, key_part2)


def canonical_advisory_key_64(domain_tag: str, tenant_id: int, resource_id: int) -> int:
    """
    Derives a collision-resistant 64-bit signed integer (-2^63 to 2^63 - 1) for pg_advisory_xact_lock(bigint).
    Uses BLAKE2b 8-byte digest to avoid 32-bit birthday-paradox collisions across multi-company workloads.
    """
    if not isinstance(domain_tag, str) or not domain_tag.strip():
        raise ValueError("domain_tag must be a non-empty string.")
    if isinstance(tenant_id, bool) or isinstance(resource_id, bool) or tenant_id < 0 or resource_id < 0:
        raise ValueError("Tenant and resource identifiers must be non-negative.")
    raw_payload = f"V2:{domain_tag}:{tenant_id}:{resource_id}".encode("utf-8")
    digest = hashlib.blake2b(raw_payload, digest_size=8).digest()
    (val,) = struct.unpack(">q", digest)
    return val


LockTimeoutSecurityException = LockAcquisitionTimeoutError


class BoundedAdvisoryLockGuard:
    """
    Bounded Flat Advisory Lock with Reversible Diagnostic Metadata and Lexicographical Sorting (Synthesis 4.4 / Patches 70-72).
    Supports:
    - 32-bit tuple instance mode: `with BoundedAdvisoryLockGuard(cr, keys=[(k1, k2), ...], timeout_seconds=2.5):`
    - 64-bit bigint instance mode: `with BoundedAdvisoryLockGuard(cr, lock_keys=[k64, ...], timeout_sec=3.0):`
    - Classmethod mode: `with BoundedAdvisoryLockGuard.acquire(cursor, company_id, journal_id):`
    """

    diagnostic_registry: Dict[Tuple[int, int], Dict[str, Any]] = {}
    _registry_lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        cr: Any,
        keys: Optional[Iterable[Any]] = None,
        timeout_seconds: float = 5.0,
        *,
        lock_keys: Optional[Sequence[int]] = None,
        timeout_sec: Optional[float] = None,
    ) -> None:
        raw_items = list(lock_keys) if lock_keys is not None else (list(keys) if keys is not None else [])
        resolved_timeout = timeout_sec if timeout_sec is not None else timeout_seconds
        if resolved_timeout <= 0.0:
            raise ValueError("Lock timeout must be strictly positive.")
        self.cr = cr
        self._acquired: bool = False

        if lock_keys is not None or (raw_items and isinstance(raw_items[0], int) and not isinstance(raw_items[0], bool)):
            self._is_64bit_mode = True
            self.lock_keys: List[int] = sorted(set(int(k) for k in raw_items))
            self.keys: List[Tuple[int, int]] = []
            self.timeout_sec: float = max(0.1, min(float(resolved_timeout), 30.0))
            self.timeout_seconds: float = self.timeout_sec
        else:
            self._is_64bit_mode = False
            self.lock_keys = []
            self.keys = sorted(set((int(k1), int(k2)) for k1, k2 in raw_items))
            self.timeout_seconds = float(resolved_timeout)
            self.timeout_sec = self.timeout_seconds

    def __enter__(self) -> "BoundedAdvisoryLockGuard":
        if self._is_64bit_mode:
            self.cr.execute("SET LOCAL lock_timeout = %s;", (f"{int(self.timeout_sec * 1000)}ms",))
            for key in self.lock_keys:
                try:
                    self.cr.execute("SELECT pg_advisory_xact_lock(%s);", (key,))
                except Exception as exc:
                    _logger.error("Advisory lock acquisition failed for key %d: %s", key, exc)
                    raise LockTimeoutSecurityException(
                        f"Resource lock unavailable for key {key}. Transaction aborted to prevent deadlock."
                    ) from exc
            self._acquired = True
            return self

        timeout_ms = int(self.timeout_seconds * 1000)
        self.cr.execute("SET LOCAL lock_timeout = %s;", (f"{timeout_ms}ms",))
        for k1, k2 in self.keys:
            if not (INT4_MIN <= k1 <= INT4_MAX and INT4_MIN <= k2 <= INT4_MAX):
                raise ValueError(f"Advisory lock key tuple out of bounds: ({k1}, {k2})")
            self.cr.execute("SELECT pg_advisory_xact_lock(%s, %s);", (k1, k2))
        self._acquired = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        try:
            if self._is_64bit_mode:
                self.cr.execute("SET LOCAL lock_timeout = DEFAULT;")
            else:
                self.cr.execute("RESET lock_timeout;")
        except Exception as reset_exc:
            _logger.warning("Failed to reset lock_timeout on BoundedAdvisoryLockGuard exit: %s", reset_exc)
        self._acquired = False
        return False

    @classmethod
    @contextmanager
    def acquire(
        cls,
        cursor: Any,
        company_id: int,
        journal_id: int,
        model_name: str = "account.journal",
        timeout_ms: int = 2500,
    ):
        if company_id <= 0 or journal_id <= 0:
            raise ValueError("company_id and journal_id must be positive integers.")
        namespace = f"{model_name}:{company_id}"
        key_pair = canonical_advisory_key(namespace, journal_id)
        try:
            cursor.execute(f"SET LOCAL lock_timeout = '{int(timeout_ms)}ms';")
            cursor.execute("SELECT pg_advisory_xact_lock(%s, %s);", key_pair)
        except Exception as exc:
            raise LockTimeoutSecurityException(
                f"Failed to acquire bounded advisory lock for {namespace}#{journal_id} within {timeout_ms}ms: {exc}"
            ) from exc

        with cls._registry_lock:
            cls.diagnostic_registry[key_pair] = {
                "int4_key1": key_pair[0],
                "int4_key2": key_pair[1],
                "model_name": model_name,
                "company_id": company_id,
                "target_id": journal_id,
                "acquired_at": time.time(),
            }
        try:
            yield key_pair
        finally:
            with cls._registry_lock:
                cls.diagnostic_registry.pop(key_pair, None)


class _DualActivateDescriptor:
    """Allows ScopedTenantEnvironmentGuard.activate to be called as either a 0-arg instance method or a 3-arg classmethod."""

    def __get__(self, instance: Optional["ScopedTenantEnvironmentGuard"], owner: type) -> Callable[..., Any]:
        if instance is not None:
            return instance._activate_instance
        return owner._activate_class


class ScopedTenantEnvironmentGuard:
    """Enforces strict multi-tenant context isolation using ContextVars and fail-closed Odoo Environment context restoration."""

    _current_token: contextvars.ContextVar[Optional[TenantContextToken]] = contextvars.ContextVar(
        "current_scoped_tenant_token", default=None
    )

    def __init__(
        self,
        token: Optional[Union[TenantContextToken, str, Any]] = None,
        secret_key: Union[bytes, str, int] = b"",
        expected_token_hash: Optional[Union[str, int, bool, List[int]]] = None,
        *,
        env: Optional[Any] = None,
        target_company_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        allowed_company_ids: Optional[List[int]] = None,
        strict_acl: Optional[bool] = None,
    ) -> None:
        resolved_env = env if env is not None else token
        if resolved_env is not None and hasattr(resolved_env, "context"):
            comp_val = target_company_id if target_company_id is not None else secret_key
            if isinstance(comp_val, bool) or not isinstance(comp_val, int) or comp_val <= 0:
                raise TenantSecurityException(f"Invalid target_company_id: {comp_val}")
            self.env = resolved_env
            self.target_company_id = int(comp_val)
            user_val = (
                target_user_id
                if target_user_id is not None
                else (
                    expected_token_hash
                    if isinstance(expected_token_hash, int) and not isinstance(expected_token_hash, bool)
                    else None
                )
            )
            self.target_user_id: Optional[int] = int(user_val) if user_val is not None else None
            resolved_allowed = (
                allowed_company_ids
                if allowed_company_ids is not None
                else (expected_token_hash if isinstance(expected_token_hash, list) else None)
            )
            self.allowed_company_ids: List[int] = (
                list(resolved_allowed) if resolved_allowed else [self.target_company_id]
            )
            self.strict_acl: bool = (
                strict_acl
                if strict_acl is not None
                else (expected_token_hash if isinstance(expected_token_hash, bool) else False)
            )
            self.original_context: Optional[Dict[str, Any]] = dict(resolved_env.context)
            self._original_context: Optional[Dict[str, Any]] = dict(resolved_env.context)
            self.original_uid: Optional[int] = None
            self._depth_token: Optional[contextvars.Token] = None
            self._restored: bool = False
            self.tenant_id = str(self.target_company_id)
            self.secret_token = ""
            self.expected_token_hash = ""
            self.token = None
            self.secret_key = b""
            self._mode = "env"
        elif expected_token_hash is not None or isinstance(token, str):
            if not token or not secret_key or not expected_token_hash:
                raise TenantSecurityException(
                    "Tenant ID, secret token, and expected token must be provided."
                )
            self.env = None
            self.target_company_id = 0
            self.target_user_id = None
            self.allowed_company_ids = []
            self.strict_acl = False
            self.original_context = None
            self._original_context = None
            self.original_uid = None
            self._depth_token = None
            self._restored = False
            self.tenant_id = str(token).strip()
            self.secret_token = str(secret_key)
            self.expected_token_hash = str(expected_token_hash)
            self.token = None
            self.secret_key = b""
            self._mode = "activate"
        else:
            self.env = None
            self.target_company_id = 0
            self.target_user_id = None
            self.allowed_company_ids = []
            self.strict_acl = False
            self.original_context = None
            self._original_context = None
            self.original_uid = None
            self._depth_token = None
            self._restored = False
            self.token = token
            self.secret_key = secret_key if isinstance(secret_key, bytes) else str(secret_key).encode("utf-8")
            self.tenant_id = ""
            self.secret_token = ""
            self.expected_token_hash = ""
            self._mode = "token"
        self._cv_token: Optional[contextvars.Token] = None

    @classmethod
    def get_active_depth(cls) -> int:
        return _ACTIVE_TENANT_DEPTH.get()

    def verify_token(self) -> bool:
        token_bytes = self.secret_token.encode("utf-8")
        expected_bytes = self.expected_token_hash.encode("utf-8")
        return hmac.compare_digest(token_bytes, expected_bytes)

    @contextmanager
    def _activate_instance(self):
        if not self.verify_token():
            raise TenantSecurityException(
                f"Unauthorized access: Invalid security token for tenant '{self.tenant_id}'."
            )
        tok = _ACTIVE_SCOPED_TENANT_STR_ID.set(self.tenant_id)
        try:
            yield self.tenant_id
        finally:
            _ACTIVE_SCOPED_TENANT_STR_ID.reset(tok)

    @classmethod
    @contextmanager
    def _activate_class(cls, tenant_id: str, user_id: str, company_id: str):
        if not all(isinstance(arg, str) and arg.strip() for arg in (tenant_id, user_id, company_id)):
            raise ValueError("Tenant activation arguments must be non-empty strings")
        new_context = TenantSecurityContext(
            tenant_id=tenant_id.strip(),
            user_id=user_id.strip(),
            company_id=company_id.strip(),
            is_active=True,
        )
        token_ctx = _TENANT_CONTEXT_VAR.set(new_context)
        token_str = _ACTIVE_SCOPED_TENANT_STR_ID.set(new_context.tenant_id)
        try:
            yield new_context
        finally:
            _TENANT_CONTEXT_VAR.reset(token_ctx)
            _ACTIVE_SCOPED_TENANT_STR_ID.reset(token_str)

    activate = _DualActivateDescriptor()

    @classmethod
    def get_current_context(cls) -> TenantSecurityContext:
        ctx = _TENANT_CONTEXT_VAR.get()
        if ctx is None or not ctx.is_active:
            raise TenantSecurityException(
                "Access denied: No active ScopedTenantEnvironmentGuard context"
            )
        return ctx

    def __enter__(self) -> Any:
        if self._mode == "env":
            depth = _ACTIVE_TENANT_DEPTH.get()
            self._depth_token = _ACTIVE_TENANT_DEPTH.set(depth + 1)
            try:
                if self.strict_acl and hasattr(self.env, "user") and hasattr(self.env.user, "company_ids"):
                    permitted_ids = getattr(self.env.user.company_ids, "ids", self.env.user.company_ids)
                    if self.target_company_id not in permitted_ids:
                        raise TenantSecurityException(
                            f"Access to tenant {self.target_company_id} rejected for UID {getattr(self.env, 'uid', None)}"
                        )
                self.original_context = dict(self.env.context)
                self._original_context = self.original_context
                new_context = dict(self.original_context)
                new_context["allowed_company_ids"] = list(self.allowed_company_ids)
                new_context["company_id"] = self.target_company_id
                new_context["current_company_id"] = self.target_company_id
                if callable(self.env) and self.target_user_id is None:
                    return self.env(context=new_context)
                self.original_uid = getattr(self.env, "uid", None)
                self.env.context = new_context
                if self.target_user_id is not None:
                    self.env.uid = self.target_user_id
                return self.env
            except BaseException:
                if self._depth_token is not None:
                    _ACTIVE_TENANT_DEPTH.reset(self._depth_token)
                    self._depth_token = None
                raise
        if self._mode == "activate":
            if not self.verify_token():
                raise TenantSecurityException(
                    f"Unauthorized access: Invalid security token for tenant '{self.tenant_id}'."
                )
            self._cv_token = _ACTIVE_SCOPED_TENANT_STR_ID.set(self.tenant_id)
            return self
        if self.token is None or not self.token.verify(self.secret_key):
            raise TenantIsolationError(
                "Cryptographic verification failed for TenantContextToken."
            )
        self._cv_token = self._current_token.set(self.token)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if self._mode == "env" and self.env is not None:
            try:
                if self._original_context is not None:
                    self.env.context = self._original_context
                    self._restored = True
                if self.original_uid is not None:
                    self.env.uid = self.original_uid
            finally:
                if self._depth_token is not None:
                    _ACTIVE_TENANT_DEPTH.reset(self._depth_token)
                    self._depth_token = None
                if hasattr(self.env, "invalidate_all"):
                    self.env.invalidate_all()
            return False
        if self._cv_token is not None:
            if self._mode == "activate":
                _ACTIVE_SCOPED_TENANT_STR_ID.reset(self._cv_token)
            else:
                self._current_token.reset(self._cv_token)
            self._cv_token = None
        return False

    def __call__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with self:
            return fn(*args, **kwargs)

    @classmethod
    def get_current_tenant_id(cls, secret_key: Optional[bytes] = None) -> str:
        if secret_key is None:
            current_str = _ACTIVE_SCOPED_TENANT_STR_ID.get()
            if current_str is not None:
                return current_str
            active_token = cls._current_token.get()
            if active_token is not None:
                return str(active_token.tenant_id)
            raise TenantSecurityException(
                "Operation attempted outside of an active ScopedTenantEnvironment."
            )
        active_token = cls._current_token.get()
        if active_token is None:
            raise TenantIsolationError(
                "Unauthenticated operation: No active TenantContextToken found in context."
            )
        if not active_token.verify(secret_key):
            raise TenantIsolationError("Active TenantContextToken signature is invalid.")
        return str(active_token.tenant_id)

    @classmethod
    def get_current_company_id(cls, secret_key: bytes) -> str:
        active_token = cls._current_token.get()
        if active_token is None:
            raise TenantIsolationError(
                "Unauthenticated operation: No active TenantContextToken found in context."
            )
        if not active_token.verify(secret_key):
            raise TenantIsolationError("Active TenantContextToken signature is invalid.")
        return str(active_token.company_id)

    @staticmethod
    def get_current_tenant() -> Optional[int]:
        return _ACTIVE_SCOPED_TENANT_ID.get()

    @staticmethod
    @contextmanager
    def scope_tenant(tenant_id: int, allowed_companies: Set[int]):
        if not isinstance(tenant_id, int) or isinstance(tenant_id, bool) or tenant_id <= 0:
            raise TenantSecurityError(f"Invalid tenant_id: {tenant_id}")
        if tenant_id not in allowed_companies:
            raise TenantSecurityError(
                f"Tenant {tenant_id} is not in allowed companies {allowed_companies}."
            )

        token_tenant = _ACTIVE_SCOPED_TENANT_ID.set(tenant_id)
        token_companies = _ALLOWED_COMPANY_IDS.set(frozenset(allowed_companies))
        try:
            yield
        finally:
            _ACTIVE_SCOPED_TENANT_ID.reset(token_tenant)
            _ALLOWED_COMPANY_IDS.reset(token_companies)

    @staticmethod
    def assert_record_tenant(record_company_id: int) -> None:
        active_tenant = _ACTIVE_SCOPED_TENANT_ID.get()
        allowed = _ALLOWED_COMPANY_IDS.get()
        if active_tenant is None:
            raise TenantSecurityError("Operation attempted outside of an active tenant scope.")
        if record_company_id not in allowed:
            raise TenantSecurityError(
                f"Cross-tenant access denied: Record belongs to company {record_company_id}, "
                f"but active context only permits {set(allowed)}."
            )


import ast
import math
import operator
from typing import Callable


class ScopedEnterpriseFormulaGuard:
    """Evaluates enterprise pricing and sales commission formulas safely via strict AST whitelisting."""

    _ALLOWED_OPERATORS: Dict[type, Callable[..., Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    _ALLOWED_COMPARATORS: Dict[type, Callable[..., Any]] = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    _ALLOWED_FUNCTIONS: Dict[str, Callable[..., Any]] = {
        "min": min,
        "max": max,
        "round": round,
        "abs": abs,
        "ceil": math.ceil,
        "floor": math.floor,
        "sqrt": math.sqrt,
    }

    _MAX_EXPRESSION_LENGTH: int = 512
    _MAX_EXPONENT_VALUE: float = 10.0
    _MAX_COMPUTED_NUMBER: float = 1e12

    @classmethod
    def sanitize_raw_input(cls, formula_str: str) -> str:
        if not isinstance(formula_str, str):
            raise ASTFormulaSandboxError("Formula input must be a valid string.")
        if len(formula_str) > cls._MAX_EXPRESSION_LENGTH:
            raise ASTFormulaSandboxError(
                f"Formula exceeds max allowed length ({cls._MAX_EXPRESSION_LENGTH} characters)."
            )

        normalized = unicodedata.normalize("NFKD", formula_str)
        for char in normalized:
            category = unicodedata.category(char)
            if category.startswith("C"):
                raise ASTFormulaSandboxError(f"Illegal control character detected: {char!r}")

        if "__" in normalized or "import" in normalized or "exec" in normalized:
            raise ASTFormulaSandboxError("Illegal token detected in formula string.")

        return normalized

    @classmethod
    def evaluate(cls, formula_str: str, context_variables: Dict[str, float]) -> float:
        clean_formula = cls.sanitize_raw_input(formula_str)

        sanitized_context: Dict[str, float] = {}
        for k, v in context_variables.items():
            if not isinstance(k, str) or k.startswith("__"):
                raise ASTFormulaSandboxError(f"Invalid context variable name: {k}")
            try:
                numeric_val = float(v)
                if math.isnan(numeric_val) or math.isinf(numeric_val):
                    raise ASTFormulaSandboxError(
                        f"Context variable '{k}' has invalid numeric value: {v}"
                    )
                sanitized_context[k] = numeric_val
            except (ValueError, TypeError) as err:
                raise ASTFormulaSandboxError(
                    f"Context variable '{k}' cannot be converted to float: {err}"
                ) from err

        try:
            parsed_ast = ast.parse(clean_formula, mode="eval")
        except SyntaxError as err:
            raise ASTFormulaSandboxError(f"Formula syntax is invalid: {err.msg}") from err

        return cls._eval_node(parsed_ast.body, sanitized_context)

    @classmethod
    def _eval_node(cls, node: ast.AST, context: Dict[str, float]) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                if abs(node.value) > cls._MAX_COMPUTED_NUMBER:
                    raise ASTFormulaSandboxError(
                        f"Constant exceeds numerical boundary limit: {node.value}"
                    )
                return float(node.value)
            raise ASTFormulaSandboxError(
                f"Literal constant type not allowed: {type(node.value).__name__}"
            )

        if isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            raise ASTFormulaSandboxError(f"Undefined variable in formula: {node.id}")

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in cls._ALLOWED_OPERATORS:
                operand_val = cls._eval_node(node.operand, context)
                return float(cls._ALLOWED_OPERATORS[op_type](operand_val))
            raise ASTFormulaSandboxError(f"Unary operator not permitted: {op_type.__name__}")

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in cls._ALLOWED_OPERATORS:
                raise ASTFormulaSandboxError(f"Binary operator not permitted: {op_type.__name__}")

            left_val = cls._eval_node(node.left, context)
            right_val = cls._eval_node(node.right, context)

            if op_type is ast.Pow:
                if abs(right_val) > cls._MAX_EXPONENT_VALUE:
                    raise ASTFormulaSandboxError(
                        f"Exponent exceeds safe threshold: {right_val}"
                    )
                if abs(left_val) > 1000.0 and right_val > 4.0:
                    raise ASTFormulaSandboxError(
                        "Computation exceeds maximum allowable density."
                    )

            if op_type in (ast.Div, ast.FloorDiv, ast.Mod):
                if right_val == 0.0:
                    raise ASTFormulaSandboxError("Division by zero in formula evaluation.")

            computed = float(cls._ALLOWED_OPERATORS[op_type](left_val, right_val))
            if (
                math.isnan(computed)
                or math.isinf(computed)
                or abs(computed) > cls._MAX_COMPUTED_NUMBER
            ):
                raise ASTFormulaSandboxError("Formula result overflow or illegal numerical state.")
            return computed

        if isinstance(node, ast.Compare):
            left_val = cls._eval_node(node.left, context)
            for op, comp in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in cls._ALLOWED_COMPARATORS:
                    raise ASTFormulaSandboxError(f"Comparator not permitted: {op_type.__name__}")
                right_val = cls._eval_node(comp, context)
                if not cls._ALLOWED_COMPARATORS[op_type](left_val, right_val):
                    return False
                left_val = right_val
            return True

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ASTFormulaSandboxError(
                    "Indirect or dynamic function calls are strictly forbidden."
                )

            func_name = node.func.id
            if func_name not in cls._ALLOWED_FUNCTIONS:
                raise ASTFormulaSandboxError(f"Function call not in allowlist: {func_name}")

            evaluated_args = [cls._eval_node(arg, context) for arg in node.args]
            target_func = cls._ALLOWED_FUNCTIONS[func_name]
            if func_name == "round" and len(evaluated_args) == 2:
                from decimal import ROUND_HALF_UP
                ndigits = int(evaluated_args[1])
                quant = Decimal("10") ** (-ndigits)
                return float(Decimal(str(evaluated_args[0])).quantize(quant, rounding=ROUND_HALF_UP))
            return float(target_func(*evaluated_args))

        raise ASTFormulaSandboxError(
            f"Disallowed AST expression element: {type(node).__name__}"
        )


class HardenedEnterpriseFormulaGuard(ScopedEnterpriseFormulaGuard):
    """Enforces fail-closed AST sandboxing with explicit node allowlist, recursion limits, MAX_NODES bound, and NFKD->NFC canonicalization."""

    MAX_EXPR_LENGTH: int = 2048
    MAX_INPUT_LENGTH: int = 2048
    MAX_PARENTHESIS_DEPTH: int = 32
    MAX_NODES: int = 40
    MAX_DEPTH: int = 5
    MAX_AST_DEPTH: int = 15
    MAX_EXPONENT: int = 100

    ALLOWED_NODES: Set[type] = {
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
    }

    ALLOWED_VARIABLES: Set[str] = {
        "qty",
        "unit_price",
        "discount",
        "tax_rate",
        "margin",
        "currency_rate",
        "historical_avg",
        "base_price",
        "surcharge",
        "min_cap",
    }

    @classmethod
    def sanitize_raw_expression(cls, raw_formula: str) -> str:
        if not isinstance(raw_formula, str) or not raw_formula.strip():
            raise FormulaSecurityViolation("Length violation: Formula input must be a non-empty string.")
        if len(raw_formula) > cls.MAX_EXPR_LENGTH:
            raise FormulaSecurityViolation(
                f"Length violation: Formula exceeds maximum length of {cls.MAX_EXPR_LENGTH} characters."
            )
        normalized = unicodedata.normalize("NFKD", raw_formula)
        canonical = unicodedata.normalize("NFC", normalized)
        depth = 0
        for char in canonical:
            category = unicodedata.category(char)
            if category.startswith("C") or category.startswith("Zl") or category.startswith("Zp"):
                raise FormulaSecurityViolation(
                    f"Forbidden unicode control character detected: U+{ord(char):04X}"
                )
            if char in "([{":
                depth += 1
                if depth > cls.MAX_PARENTHESIS_DEPTH:
                    raise FormulaSecurityViolation(
                        "Recursion bomb defense: Nesting depth exceeds maximum allowed limit (CWE-400)"
                    )
            elif char in ")]}":
                depth = max(0, depth - 1)
        return canonical

    @classmethod
    def validate(cls, formula_str: str) -> ast.AST:
        canonical = cls.sanitize_raw_expression(formula_str)
        try:
            tree = ast.parse(canonical, mode="eval")
        except SyntaxError as exc:
            raise FormulaSecurityError(f"Syntax error: {exc}") from exc
        node_count = sum(1 for _ in ast.walk(tree))
        if node_count > cls.MAX_NODES:
            raise FormulaSecurityError(
                f"Node count violation: Formula AST nodes ({node_count}) exceed MAX_NODES ({cls.MAX_NODES})"
            )
        return tree

    @classmethod
    def validate_ast(cls, node: ast.AST, current_depth: int = 0) -> None:
        if current_depth == 0:
            node_count = sum(1 for _ in ast.walk(node))
            if node_count > cls.MAX_NODES:
                raise FormulaSecurityViolation(
                    f"Node count violation: AST complexity limit exceeded (>{cls.MAX_NODES} nodes)"
                )
        if current_depth > cls.MAX_AST_DEPTH:
            raise FormulaSecurityViolation(
                f"Formula AST exceeds maximum recursion depth of {cls.MAX_AST_DEPTH}."
            )
        if type(node) not in cls.ALLOWED_NODES:
            raise FormulaSecurityViolation(
                f"Disallowed AST node type: {type(node).__name__}"
            )
        if isinstance(node, ast.Name):
            if node.id not in cls.ALLOWED_VARIABLES:
                raise FormulaSecurityViolation(
                    f"Unauthorized variable reference in formula: '{node.id}'"
                )
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if isinstance(node.right, ast.Constant):
                if isinstance(node.right.value, (int, float)) and node.right.value > cls.MAX_EXPONENT:
                    raise FormulaSecurityViolation(
                        f"Exponent value {node.right.value} exceeds maximum safe limit of {cls.MAX_EXPONENT}."
                    )
            else:
                raise FormulaSecurityViolation(
                    "Dynamic or non-constant exponents are strictly forbidden."
                )
        for child in ast.iter_child_nodes(node):
            cls.validate_ast(child, current_depth + 1)

    @classmethod
    def evaluate(cls, raw_formula: str, context: Dict[str, float]) -> Any:
        cleaned_formula = cls.sanitize_raw_expression(raw_formula)
        try:
            parsed_ast = ast.parse(cleaned_formula, mode="eval")
        except SyntaxError as syntax_err:
            raise FormulaSecurityViolation(f"Invalid formula syntax: {syntax_err}") from syntax_err

        cls.validate_ast(parsed_ast)
        safe_names = {k: float(context[k]) for k in cls.ALLOWED_VARIABLES if k in context}
        return cls._eval_node(parsed_ast.body, safe_names)



class NFKDStrongRefFormulaSanitizer:
    """Canonicalizes, sanitizes, and AST-evaluates formulas against injection, homoglyphs, and cyclic dependency graph explosion."""

    SAFE_FUNCTIONS: Set[str] = {
        "SUM", "AVERAGE", "COUNT", "COUNTA", "MAX", "MIN", "IF",
        "ROUND", "ABS", "SUBTOTAL", "VLOOKUP", "XLOOKUP", "INDEX", "MATCH",
    }
    CELL_REF_PATTERN = re.compile(
        r"^(?:'?[a-zA-Z0-9_\s]+'?!|\b)([A-Z]{1,3}[0-9]{1,7})\b"
    )
    MAX_RECURSION_DEPTH = 8
    MAX_FORMULA_LENGTH = 1024
    MAX_EXPRESSION_LENGTH = 1024
    MAX_AST_DEPTH = 15

    ALLOWED_OPERATORS: Dict[type, Callable[..., Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCTIONS: Dict[str, Callable[..., Any]] = {
        "round": round,
        "abs": abs,
        "min": min,
        "max": max,
        "ceil": math.ceil,
        "floor": math.floor,
    }

    def __init__(self, allowed_variables: Optional[Set[str]] = None) -> None:
        self._allowed_variables: FrozenSet[str] = frozenset(allowed_variables or set())

    def normalize_input(self, raw_formula: str) -> str:
        if not isinstance(raw_formula, str):
            raise FormulaSanitizationError("Formula input must be a string.")
        if len(raw_formula) > self.MAX_EXPRESSION_LENGTH:
            raise FormulaSanitizationError(
                f"Formula exceeds maximum length of {self.MAX_EXPRESSION_LENGTH} characters."
            )

        normalized_chars: List[str] = []
        for ch in raw_formula:
            category = unicodedata.category(ch)
            if category.startswith("C") and ch not in ("\t", "\n", "\r"):
                raise FormulaSanitizationError(
                    f"Disallowed Unicode control/format character detected: U+{ord(ch):04X}"
                )
            normalized_chars.append(ch)

        filtered_str = "".join(normalized_chars)
        canonical_str = unicodedata.normalize("NFKD", filtered_str)

        paren_depth = 0
        for ch in canonical_str:
            if ord(ch) > 127:
                raise FormulaSanitizationError(
                    f"Non-ASCII character remaining after NFKD normalization: {ch!r} (U+{ord(ch):04X})"
                )
            if ch == "(":
                paren_depth += 1
                if paren_depth > self.MAX_AST_DEPTH:
                    raise FormulaSanitizationError(
                        f"Formula parenthesis nesting depth exceeds maximum limit of {self.MAX_AST_DEPTH}."
                    )
            elif ch == ")":
                paren_depth = max(0, paren_depth - 1)

        return canonical_str.strip()

    def validate_ast(self, node: ast.AST, current_depth: int = 0) -> None:
        if current_depth > self.MAX_AST_DEPTH:
            raise FormulaSanitizationError(
                f"Formula AST depth exceeds maximum limit of {self.MAX_AST_DEPTH}."
            )

        if isinstance(node, ast.Expression):
            self.validate_ast(node.body, current_depth + 1)
        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float, Decimal)) or isinstance(node.value, bool):
                raise FormulaSanitizationError(
                    f"Disallowed constant type in formula: {type(node.value).__name__}"
                )
        elif isinstance(node, ast.Name):
            if not isinstance(node.ctx, ast.Load):
                raise FormulaSanitizationError("Variable mutation is strictly prohibited.")
            if node.id.startswith("_") or node.id not in self._allowed_variables:
                raise FormulaSanitizationError(
                    f"Unauthorized or private identifier in formula: '{node.id}'"
                )
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in self.ALLOWED_OPERATORS:
                raise FormulaSanitizationError(
                    f"Disallowed binary operator: {type(node.op).__name__}"
                )
            self.validate_ast(node.left, current_depth + 1)
            self.validate_ast(node.right, current_depth + 1)
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) not in self.ALLOWED_OPERATORS:
                raise FormulaSanitizationError(
                    f"Disallowed unary operator: {type(node.op).__name__}"
                )
            self.validate_ast(node.operand, current_depth + 1)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise FormulaSanitizationError(
                    "Method calls and dynamic callables are prohibited."
                )
            func_name = node.func.id
            if func_name not in self.ALLOWED_FUNCTIONS:
                raise FormulaSanitizationError(
                    f"Unauthorized function call in formula: '{func_name}'"
                )
            if node.keywords:
                raise FormulaSanitizationError(
                    "Keyword arguments are prohibited in formula functions."
                )
            for arg in node.args:
                self.validate_ast(arg, current_depth + 1)
        else:
            raise FormulaSanitizationError(
                f"Prohibited AST syntax construct: {type(node).__name__}"
            )

    def _eval_node(self, node: ast.AST, context: Mapping[str, Union[int, float, Decimal]]) -> Any:
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body, context)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in context:
                raise FormulaSanitizationError(f"Missing runtime value for variable: '{node.id}'")
            val = context[node.id]
            if not isinstance(val, (int, float, Decimal)) or isinstance(val, bool):
                raise FormulaSanitizationError(f"Invalid runtime type for variable '{node.id}'")
            return val
        if isinstance(node, ast.UnaryOp):
            op_func = self.ALLOWED_OPERATORS[type(node.op)]
            return op_func(self._eval_node(node.operand, context))
        if isinstance(node, ast.BinOp):
            op_func = self.ALLOWED_OPERATORS[type(node.op)]
            left_val = self._eval_node(node.left, context)
            right_val = self._eval_node(node.right, context)
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right_val == 0:
                raise FormulaSanitizationError("Division by zero in formula evaluation.")
            return op_func(left_val, right_val)
        if isinstance(node, ast.Call):
            assert isinstance(node.func, ast.Name)
            func = self.ALLOWED_FUNCTIONS[node.func.id]
            eval_args = [self._eval_node(arg, context) for arg in node.args]
            return func(*eval_args)
        raise FormulaSanitizationError(f"Unhandled AST node: {type(node).__name__}")

    def evaluate(
        self,
        raw_formula: str,
        context: Optional[Mapping[str, Union[int, float, Decimal]]] = None,
    ) -> Union[int, float, Decimal]:
        safe_context = context or {}
        canonical_expr = self.normalize_input(raw_formula)
        if not canonical_expr:
            raise FormulaSanitizationError("Empty formula expression.")
        try:
            parsed_ast = ast.parse(canonical_expr, mode="eval")
        except SyntaxError as exc:
            raise FormulaSanitizationError(f"Invalid formula syntax: {exc.msg}") from exc
        self.validate_ast(parsed_ast)
        return self._eval_node(parsed_ast, safe_context)

    @classmethod
    def canonicalize_unicode(cls, raw_formula: str) -> str:
        if not isinstance(raw_formula, str):
            raise FormulaSanitizationError("Formula input must be a string.")
        normalized = unicodedata.normalize("NFKD", raw_formula)
        cleaned = "".join(ch for ch in normalized if ch == "\t" or ch == "\n" or ord(ch) >= 32)
        return cleaned.strip()

    @classmethod
    def sanitize_formula_payload(
        cls,
        raw_formula: str,
        formula_dependency_graph: Dict[str, List[str]],
        target_cell: str,
        current_depth: int = 0,
    ) -> str:
        canonical = cls.canonicalize_unicode(raw_formula)
        if len(canonical) > cls.MAX_FORMULA_LENGTH:
            raise FormulaSanitizationError(
                f"Formula exceeds max allowed length of {cls.MAX_FORMULA_LENGTH} chars."
            )
        if any(canonical.startswith(prefix) for prefix in ("|", "%", "!")):
            return "'" + canonical
        if not canonical.startswith("="):
            if canonical.startswith(("+", "-", "@")):
                return "'" + canonical
            return canonical

        expression = canonical[1:].strip()
        dangerous_signatures = ("cmd", "powershell", "curl", "mshta", "exec", "system")
        lower_expr = expression.lower()
        for bad_sig in dangerous_signatures:
            if bad_sig in lower_expr:
                raise FormulaSanitizationError(f"Malicious payload pattern detected: {bad_sig}")

        if current_depth > cls.MAX_RECURSION_DEPTH:
            raise FormulaSanitizationError(
                f"Formula reference depth limit of {cls.MAX_RECURSION_DEPTH} exceeded at {target_cell}."
            )

        referenced_cells = formula_dependency_graph.get(target_cell, [])
        for ref in referenced_cells:
            if ref == target_cell:
                raise FormulaSanitizationError(f"Direct circular dependency detected in {target_cell}.")
            cls._check_cycle(ref, formula_dependency_graph, [target_cell], current_depth + 1)

        return "=" + expression

    @classmethod
    def _check_cycle(
        cls,
        current: str,
        graph: Dict[str, List[str]],
        visited: List[str],
        depth: int,
    ) -> None:
        if depth > cls.MAX_RECURSION_DEPTH:
            raise FormulaSanitizationError(f"Cycle check depth exceeded at node: {current}")
        if current in visited:
            cycle_path = " -> ".join(visited + [current])
            raise FormulaSanitizationError(f"Circular dependency cycle detected: {cycle_path}")
        for neighbor in graph.get(current, []):
            cls._check_cycle(neighbor, graph, visited + [current], depth + 1)


class MockAccountMoveLine:
    def __init__(
        self,
        line_id: int,
        company_id: int,
        currency_code: str,
        amount_currency: Decimal,
        balance_functional: Decimal,
    ) -> None:
        self.line_id = line_id
        self.company_id = company_id
        self.currency_code = currency_code
        self.amount_currency = amount_currency
        self.balance_functional = balance_functional


def revalue_journal_items_partitioned(
    lines: List[MockAccountMoveLine],
    rates: Dict[str, Decimal],
    lock_manager: Any = None,
) -> Tuple[Decimal, int]:
    """Executes partitioned, chunked currency revaluation adhering to strict monotonic company ordering."""
    total_revalued_diff = Decimal("0.0")
    processed_count = 0

    lines_by_company: Dict[int, List[MockAccountMoveLine]] = {}
    for line in lines:
        lines_by_company.setdefault(line.company_id, []).append(line)

    for comp_id in sorted(lines_by_company.keys()):
        comp_lines = lines_by_company[comp_id]
        chunk_size = 1000
        for i in range(0, len(comp_lines), chunk_size):
            chunk = comp_lines[i : i + chunk_size]
            for item in chunk:
                current_rate = rates[item.currency_code]
                new_balance = (item.amount_currency * current_rate).quantize(Decimal("0.01"))
                diff = new_balance - item.balance_functional
                total_revalued_diff += diff
                item.balance_functional = new_balance
                processed_count += 1

    return total_revalued_diff, processed_count


import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP
from enum import Enum
from typing import Set


class InvalidStateTransitionError(ValueError):
    """Raised when a sales order transition violates the deterministic lifecycle DAG."""


class ConstraintViolationError(ValueError):
    """Raised when pricing, discounts, or margins violate tenant business rules."""


class SalesOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    AI_SCORED = "AI_SCORED"
    DISCOUNT_REVIEW = "DISCOUNT_REVIEW"
    APPROVED = "APPROVED"
    CONFIRMED = "CONFIRMED"
    INVOICED = "INVOICED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class TenantContext:
    company_id: str
    allowed_company_ids: Tuple[str, ...]
    user_id: str
    is_system_admin: bool = False

    def can_access(self, target_company_id: str) -> bool:
        if self.is_system_admin:
            return True
        return target_company_id in self.allowed_company_ids


@dataclass(frozen=True)
class SalesOrderLine:
    line_id: str
    product_sku: str
    quantity: Decimal
    unit_price: Decimal
    unit_cost: Decimal
    discount_pct: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        if self.quantity <= Decimal("0"):
            raise ValueError(f"Line quantity must be positive, got {self.quantity}")
        if self.unit_price < Decimal("0"):
            raise ValueError(f"Line unit price cannot be negative, got {self.unit_price}")
        if self.unit_cost < Decimal("0"):
            raise ValueError(f"Line unit cost cannot be negative, got {self.unit_cost}")
        if not (Decimal("0.00") <= self.discount_pct <= Decimal("100.00")):
            raise ValueError(f"Discount percentage must be in [0, 100], got {self.discount_pct}")

    @property
    def gross_amount(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_cost(self) -> Decimal:
        return (self.quantity * self.unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def net_amount(self) -> Decimal:
        discount_factor = Decimal("1.00") - (self.discount_pct / Decimal("100.00"))
        return (self.gross_amount * discount_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def margin_amount(self) -> Decimal:
        return self.net_amount - self.total_cost


@dataclass
class FlowStateStepRecord:
    step_id: str
    source_status: SalesOrderStatus
    target_status: SalesOrderStatus
    timestamp_utc: str
    initiator_user_id: str
    state_payload_hash: str
    previous_hash: str
    cumulative_hash: str


@dataclass
class SalesOrder:
    order_id: str
    company_id: str
    customer_id: str
    status: SalesOrderStatus = SalesOrderStatus.DRAFT
    lines: List[SalesOrderLine] = field(default_factory=list)
    ai_risk_score: Optional[Decimal] = None
    ai_conversion_probability: Optional[Decimal] = None
    state_history: List[FlowStateStepRecord] = field(default_factory=list)
    current_state_hash: str = "GENESIS_0000000000000000000000000000000000000000000000000000000000000000"

    @property
    def total_net_amount(self) -> Decimal:
        return sum((line.net_amount for line in self.lines), Decimal("0.00"))

    @property
    def total_cost_amount(self) -> Decimal:
        return sum((line.total_cost for line in self.lines), Decimal("0.00"))

    @property
    def overall_margin_pct(self) -> Decimal:
        net = self.total_net_amount
        if net == Decimal("0.00"):
            return Decimal("0.00")
        margin = net - self.total_cost_amount
        return ((margin / net) * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def canonical_snapshot(self) -> Dict[str, Any]:
        """Produces deterministic, serializable representation for RFC 8785 hashing."""
        return {
            "order_id": self.order_id,
            "company_id": self.company_id,
            "customer_id": self.customer_id,
            "status": self.status.value,
            "lines": [
                {
                    "line_id": l.line_id,
                    "product_sku": l.product_sku,
                    "quantity": str(l.quantity),
                    "unit_price": str(l.unit_price),
                    "unit_cost": str(l.unit_cost),
                    "discount_pct": str(l.discount_pct),
                    "net_amount": str(l.net_amount),
                }
                for l in sorted(self.lines, key=lambda x: x.line_id)
            ],
            "total_net_amount": str(self.total_net_amount),
            "overall_margin_pct": str(self.overall_margin_pct),
            "ai_risk_score": str(self.ai_risk_score) if self.ai_risk_score is not None else None,
            "ai_conversion_probability": (
                str(self.ai_conversion_probability) if self.ai_conversion_probability is not None else None
            ),
        }


class DiscountConstraintSolver:
    """
    PubGrub-inspired rule-satisfaction engine (astral-sh/uv pattern)
    enforcing tenant margin boundaries and approval ceilings.
    """

    MAX_DISCOUNT_WITHOUT_APPROVAL = Decimal("15.00")
    MIN_ALLOWED_MARGIN_PCT = Decimal("12.00")
    MAX_EXECUTIVE_DISCOUNT = Decimal("40.00")

    @classmethod
    def evaluate_discount_constraints(
        cls, order: SalesOrder, target_discount_pct: Decimal, is_executive_override: bool = False
    ) -> Tuple[bool, str]:
        if target_discount_pct > cls.MAX_EXECUTIVE_DISCOUNT:
            return False, f"Discount {target_discount_pct}% exceeds maximum absolute ceiling {cls.MAX_EXECUTIVE_DISCOUNT}%"

        if target_discount_pct > cls.MAX_DISCOUNT_WITHOUT_APPROVAL and not is_executive_override:
            return False, f"Discount {target_discount_pct}% requires executive approval override"

        estimated_margin = order.overall_margin_pct
        if estimated_margin < cls.MIN_ALLOWED_MARGIN_PCT and not is_executive_override:
            return False, f"Resulting margin {estimated_margin}% drops below minimum threshold {cls.MIN_ALLOWED_MARGIN_PCT}%"

        return True, "Constraints satisfied"


class EnterpriseSalesProcessEngine:
    """
    Core state machine orchestrator binding Odoo multi-tenant row security
    with Prefect task flow transitions and immutable cryptographic audit trails (arXiv:2506.01423).
    """

    ALLOWED_TRANSITIONS: Dict[SalesOrderStatus, Set[SalesOrderStatus]] = {
        SalesOrderStatus.DRAFT: {SalesOrderStatus.AI_SCORED, SalesOrderStatus.CANCELLED},
        SalesOrderStatus.AI_SCORED: {
            SalesOrderStatus.DISCOUNT_REVIEW,
            SalesOrderStatus.APPROVED,
            SalesOrderStatus.CANCELLED,
        },
        SalesOrderStatus.DISCOUNT_REVIEW: {SalesOrderStatus.APPROVED, SalesOrderStatus.CANCELLED},
        SalesOrderStatus.APPROVED: {SalesOrderStatus.CONFIRMED, SalesOrderStatus.CANCELLED},
        SalesOrderStatus.CONFIRMED: {SalesOrderStatus.INVOICED, SalesOrderStatus.CANCELLED},
        SalesOrderStatus.INVOICED: set(),
        SalesOrderStatus.CANCELLED: set(),
    }

    def __init__(self, tenant_context: TenantContext) -> None:
        self.context = tenant_context

    def _assert_tenant_boundary(self, order: SalesOrder) -> None:
        if not self.context.can_access(order.company_id):
            _logger.error(
                "Tenant security breach attempt: user %s denied access to company %s",
                self.context.user_id,
                order.company_id,
            )
            raise TenantSecurityError(
                f"Unauthorized tenant operation. User {self.context.user_id} cannot access Company {order.company_id}"
            )

    def transition_order_state(
        self,
        order: SalesOrder,
        target_status: SalesOrderStatus,
        step_id: str,
        reason: str = "",
    ) -> FlowStateStepRecord:
        self._assert_tenant_boundary(order)

        current = order.status
        allowed = self.ALLOWED_TRANSITIONS.get(current, set())
        if target_status not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal state transition from {current.value} to {target_status.value}. Allowed: {[s.value for s in allowed]}"
            )

        if target_status == SalesOrderStatus.APPROVED:
            if order.overall_margin_pct < DiscountConstraintSolver.MIN_ALLOWED_MARGIN_PCT:
                if not self.context.is_system_admin:
                    raise ConstraintViolationError(
                        f"Cannot approve order: margin {order.overall_margin_pct}% violates minimum {DiscountConstraintSolver.MIN_ALLOWED_MARGIN_PCT}%"
                    )

        if target_status == SalesOrderStatus.CONFIRMED:
            if not order.lines:
                raise ConstraintViolationError("Cannot confirm an order with zero line items.")
            if order.total_net_amount <= Decimal("0.00"):
                raise ConstraintViolationError("Cannot confirm order with non-positive total net value.")

        source_status = order.status
        order.status = target_status

        snapshot = order.canonical_snapshot()
        serialized_state = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        state_payload_hash = hashlib.sha256(serialized_state.encode("utf-8")).hexdigest()

        chain_input = (
            f"{order.current_state_hash}|{source_status.value}|{target_status.value}|"
            f"{state_payload_hash}|{self.context.user_id}|{step_id}|{reason}"
        )
        cumulative_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()

        step_record = FlowStateStepRecord(
            step_id=step_id,
            source_status=source_status,
            target_status=target_status,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            initiator_user_id=self.context.user_id,
            state_payload_hash=state_payload_hash,
            previous_hash=order.current_state_hash,
            cumulative_hash=cumulative_hash,
        )

        order.current_state_hash = cumulative_hash
        order.state_history.append(step_record)
        return step_record

    def execute_ai_qualification_pipeline(
        self,
        order: SalesOrder,
        step_id: str,
        simulated_model_inference: Optional[Dict[str, Decimal]] = None,
    ) -> SalesOrder:
        self._assert_tenant_boundary(order)
        if order.status != SalesOrderStatus.DRAFT:
            raise InvalidStateTransitionError(
                f"AI qualification requires DRAFT status, currently in {order.status.value}"
            )

        if simulated_model_inference is not None:
            risk = simulated_model_inference.get("risk_score", Decimal("0.15"))
            prob = simulated_model_inference.get("conversion_prob", Decimal("0.85"))
        else:
            margin = order.overall_margin_pct
            if margin >= Decimal("30.00"):
                risk = Decimal("0.08")
                prob = Decimal("0.92")
            elif margin >= Decimal("15.00"):
                risk = Decimal("0.22")
                prob = Decimal("0.75")
            else:
                risk = Decimal("0.55")
                prob = Decimal("0.40")

        order.ai_risk_score = risk
        order.ai_conversion_probability = prob

        self.transition_order_state(
            order=order,
            target_status=SalesOrderStatus.AI_SCORED,
            step_id=step_id,
            reason="AI Lead Qualification and Financial Risk Analysis Complete",
        )
        return order

    def verify_invariant(self, order: SalesOrder) -> bool:
        self._assert_tenant_boundary(order)

        if not order.state_history:
            return order.current_state_hash.startswith("GENESIS_")

        expected_prev = "GENESIS_0000000000000000000000000000000000000000000000000000000000000000"
        for step in order.state_history:
            if step.previous_hash != expected_prev:
                return False
            expected_prev = step.cumulative_hash

        if order.current_state_hash != expected_prev:
            return False

        if order.total_cost_amount < Decimal("0.00") or order.total_net_amount < Decimal("0.00"):
            return False

        return True


from dataclasses import asdict
from typing import Mapping, Sequence


class DomainInvariantViolationError(Exception):
    """Raised when a formal business process state invariant is violated."""


class TenantIsolationViolationError(Exception):
    """Raised when cross-company record boundaries are breached without authorization."""


class LedgerIntegrityError(Exception):
    """Raised when the cryptographic hash chain or double-entry balance fails."""


class DealState(str, Enum):
    """Lifecycle states for autonomous A2A enterprise sales negotiations."""

    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    NEGOTIATING = "NEGOTIATING"
    COMMITTED = "COMMITTED"
    SETTLED = "SETTLED"
    TERMINATED = "TERMINATED"


@dataclass(frozen=True)
class AccountingLeg:
    """Represents one leg of a double-entry transaction commitment."""

    account_id: str
    debit_cents: int
    credit_cents: int

    def __post_init__(self) -> None:
        if self.debit_cents < 0 or self.credit_cents < 0:
            raise DomainInvariantViolationError(
                f"Negative monetary values rejected: debit={self.debit_cents}, credit={self.credit_cents}"
            )
        if self.debit_cents > 0 and self.credit_cents > 0:
            raise DomainInvariantViolationError(
                f"Accounting leg cannot have both debit and credit active simultaneously: {self}"
            )
        if self.debit_cents == 0 and self.credit_cents == 0:
            raise DomainInvariantViolationError("Accounting leg cannot have zero debit and zero credit")


@dataclass(frozen=True)
class LedgerEvent:
    """Discrete, immutable event driving the state machine."""

    event_id: str
    event_type: str
    company_id: str
    payload: Dict[str, Any]
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class DealSnapshot:
    """State snapshot of an enterprise sales transaction at sequence t."""

    deal_id: str
    initiating_company_id: str
    counterparty_company_id: str
    state: DealState
    sku_manifest: Sequence[str]
    total_value_cents: int
    accounting_legs: Sequence[AccountingLeg]
    sequence_number: int
    previous_hash: str
    current_hash: str


class EnterpriseStateInvariantEngine:
    """
    Formal State Transition Engine implementing FinRobot (arXiv:2506.01423)
    and Odoo multi-company double-entry isolation invariants.
    """

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, allowed_companies: Sequence[str]) -> None:
        self._allowed_companies = frozenset(allowed_companies)
        self._deal_history: Dict[str, List[DealSnapshot]] = {}

    def _compute_canonical_hash(
        self,
        deal_id: str,
        initiator: str,
        counterparty: str,
        state: DealState,
        total_cents: int,
        legs: Sequence[AccountingLeg],
        sequence: int,
        prev_hash: str,
        event: LedgerEvent,
    ) -> str:
        payload = {
            "deal_id": deal_id,
            "initiating_company_id": initiator,
            "counterparty_company_id": counterparty,
            "state": state.value,
            "total_value_cents": total_cents,
            "accounting_legs": [asdict(leg) for leg in legs],
            "sequence_number": sequence,
            "previous_hash": prev_hash,
            "trigger_event": {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "company_id": event.company_id,
                "timestamp_utc": event.timestamp_utc,
                "payload": event.payload,
            },
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def enforce_tenant_isolation(
        self,
        requesting_company_id: str,
        target_deal: DealSnapshot,
    ) -> None:
        if requesting_company_id not in self._allowed_companies:
            _logger.error("Unauthorized company access attempt: %s", requesting_company_id)
            raise TenantIsolationViolationError(
                f"Company {requesting_company_id} is not registered in sovereign fleet tenancy"
            )

        if requesting_company_id not in (
            target_deal.initiating_company_id,
            target_deal.counterparty_company_id,
        ):
            _logger.warning(
                "Cross-company tenant breach attempted by %s on deal %s",
                requesting_company_id,
                target_deal.deal_id,
            )
            raise TenantIsolationViolationError(
                f"Company {requesting_company_id} has no record clearance for Deal {target_deal.deal_id}"
            )

    def verify_double_entry_invariants(self, legs: Sequence[AccountingLeg]) -> bool:
        total_debit = sum(leg.debit_cents for leg in legs)
        total_credit = sum(leg.credit_cents for leg in legs)
        if total_debit != total_credit:
            raise LedgerIntegrityError(
                f"Double-entry balance check violated: Debits ({total_debit}) != Credits ({total_credit})"
            )
        return True

    def create_genesis_deal(
        self,
        deal_id: str,
        initiator_id: str,
        counterparty_id: str,
        sku_manifest: Sequence[str],
        total_value_cents: int,
        initial_legs: Sequence[AccountingLeg],
    ) -> DealSnapshot:
        if deal_id in self._deal_history:
            raise DomainInvariantViolationError(f"Deal {deal_id} already exists in ledger")

        if initiator_id not in self._allowed_companies or counterparty_id not in self._allowed_companies:
            raise TenantIsolationViolationError("Both initiating and counterparty companies must be valid")

        if initiator_id == counterparty_id:
            raise DomainInvariantViolationError("Initiator and counterparty cannot be the same entity")

        if total_value_cents <= 0:
            raise DomainInvariantViolationError("Total deal value must be strictly positive")

        if not sku_manifest:
            raise DomainInvariantViolationError("SKU manifest cannot be empty")

        self.verify_double_entry_invariants(initial_legs)

        genesis_event = LedgerEvent(
            event_id=f"evt-genesis-{deal_id}",
            event_type="GENESIS_PROPOSAL",
            company_id=initiator_id,
            payload={"initial_value_cents": total_value_cents, "skus": list(sku_manifest)},
        )

        current_hash = self._compute_canonical_hash(
            deal_id=deal_id,
            initiator=initiator_id,
            counterparty=counterparty_id,
            state=DealState.DRAFT,
            total_cents=total_value_cents,
            legs=initial_legs,
            sequence=0,
            prev_hash=self.GENESIS_HASH,
            event=genesis_event,
        )

        genesis_snapshot = DealSnapshot(
            deal_id=deal_id,
            initiating_company_id=initiator_id,
            counterparty_company_id=counterparty_id,
            state=DealState.DRAFT,
            sku_manifest=tuple(sku_manifest),
            total_value_cents=total_value_cents,
            accounting_legs=tuple(initial_legs),
            sequence_number=0,
            previous_hash=self.GENESIS_HASH,
            current_hash=current_hash,
        )

        self._deal_history[deal_id] = [genesis_snapshot]
        return genesis_snapshot

    def transition_state(
        self,
        deal_id: str,
        target_state: DealState,
        event: LedgerEvent,
        updated_legs: Optional[Sequence[AccountingLeg]] = None,
        updated_value_cents: Optional[int] = None,
    ) -> DealSnapshot:
        history = self._deal_history.get(deal_id)
        if not history:
            raise DomainInvariantViolationError(f"No active deal found for ID {deal_id}")

        current = history[-1]
        self.enforce_tenant_isolation(event.company_id, current)

        valid_transitions: Mapping[DealState, Sequence[DealState]] = {
            DealState.DRAFT: (DealState.PROPOSED, DealState.TERMINATED),
            DealState.PROPOSED: (DealState.NEGOTIATING, DealState.COMMITTED, DealState.TERMINATED),
            DealState.NEGOTIATING: (DealState.COMMITTED, DealState.TERMINATED),
            DealState.COMMITTED: (DealState.SETTLED, DealState.TERMINATED),
            DealState.SETTLED: (),
            DealState.TERMINATED: (),
        }

        if target_state not in valid_transitions.get(current.state, ()):
            raise DomainInvariantViolationError(
                f"Illegal state transition requested: {current.state} -> {target_state}"
            )

        active_legs = tuple(updated_legs) if updated_legs is not None else current.accounting_legs
        active_value = updated_value_cents if updated_value_cents is not None else current.total_value_cents

        if active_value <= 0:
            raise DomainInvariantViolationError("Updated deal value must be strictly positive")

        self.verify_double_entry_invariants(active_legs)

        next_sequence = current.sequence_number + 1
        new_hash = self._compute_canonical_hash(
            deal_id=deal_id,
            initiator=current.initiating_company_id,
            counterparty=current.counterparty_company_id,
            state=target_state,
            total_cents=active_value,
            legs=active_legs,
            sequence=next_sequence,
            prev_hash=current.current_hash,
            event=event,
        )

        next_snapshot = DealSnapshot(
            deal_id=deal_id,
            initiating_company_id=current.initiating_company_id,
            counterparty_company_id=current.counterparty_company_id,
            state=target_state,
            sku_manifest=current.sku_manifest,
            total_value_cents=active_value,
            accounting_legs=active_legs,
            sequence_number=next_sequence,
            previous_hash=current.current_hash,
            current_hash=new_hash,
        )

        history.append(next_snapshot)
        return next_snapshot

    def verify_ledger_chain(self, deal_id: str) -> bool:
        history = self._deal_history.get(deal_id)
        if not history:
            raise DomainInvariantViolationError(f"No history found for deal {deal_id}")

        for idx, snapshot in enumerate(history):
            if idx == 0:
                if snapshot.previous_hash != self.GENESIS_HASH:
                    raise LedgerIntegrityError(f"Genesis block previous_hash corrupt: {snapshot.previous_hash}")
            else:
                prior = history[idx - 1]
                if snapshot.previous_hash != prior.current_hash:
                    raise LedgerIntegrityError(
                        f"Hash chain broken at seq {snapshot.sequence_number}: "
                        f"{snapshot.previous_hash} != {prior.current_hash}"
                    )
        return True


# ==============================================================================
# ENTERPRISE SALES KANBAN PULL SYSTEM WITH EXPLICIT WIP LIMITS (coderedgen)
# ==============================================================================

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable


class PipelineStage(str, Enum):
    """Formal state transitions for the autonomous sales pipeline."""
    LEAD_TRIAGE = "LEAD_TRIAGE"
    DEAL_QUALIFICATION = "DEAL_QUALIFICATION"
    PROPOSAL_SYNTHESIS = "PROPOSAL_SYNTHESIS"
    EXECUTIVE_CLOSING = "EXECUTIVE_CLOSING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class KanbanCapacityExceededError(RuntimeError):
    """Raised when a non-blocking CONWIP pull request is rejected due to strict WIP limits."""


class TokenLeaseTimeoutError(TimeoutError):
    """Raised when waiting for an upstream CONWIP token exceeds the SLA bound."""


@dataclass(frozen=True)
class PipelineEvent:
    """Immutable domain event representing a single verified action in the sales funnel."""
    stage: PipelineStage
    timestamp: float
    payload: Mapping[str, Any]
    previous_hash: str
    event_hash: str

    @classmethod
    def create(
        cls,
        stage: PipelineStage,
        payload: Mapping[str, Any],
        previous_hash: str,
        timestamp: Optional[float] = None,
    ) -> "PipelineEvent":
        ts = timestamp if timestamp is not None else time.time()
        canonical_payload = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))
        raw_content = f"{stage.value}|{ts:.6f}|{canonical_payload}|{previous_hash}"
        digest = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
        return cls(
            stage=stage,
            timestamp=ts,
            payload=dict(payload),
            previous_hash=previous_hash,
            event_hash=digest,
        )


@dataclass(frozen=True)
class SalesLeadState:
    """Strictly immutable state container for an enterprise deal."""
    lead_id: str
    tenant_id: str
    current_stage: PipelineStage
    deal_metrics: Mapping[str, Any]
    event_log: Tuple[PipelineEvent, ...] = field(default_factory=tuple)

    @property
    def latest_hash(self) -> str:
        if not self.event_log:
            return hashlib.sha256(f"GENESIS|{self.lead_id}|{self.tenant_id}".encode("utf-8")).hexdigest()
        return self.event_log[-1].event_hash

    def verify_audit_chain(self) -> bool:
        expected_prev = hashlib.sha256(f"GENESIS|{self.lead_id}|{self.tenant_id}".encode("utf-8")).hexdigest()
        for ev in self.event_log:
            if ev.previous_hash != expected_prev:
                return False
            canonical_payload = json.dumps(dict(ev.payload), sort_keys=True, separators=(",", ":"))
            raw_content = f"{ev.stage.value}|{ev.timestamp:.6f}|{canonical_payload}|{ev.previous_hash}"
            recomputed = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
            if recomputed != ev.event_hash:
                return False
            expected_prev = ev.event_hash
        return True


@dataclass(frozen=True)
class ConwipToken:
    """Cryptographically verifiable lease token granting right-of-execution in a stage."""
    token_id: str
    stage: PipelineStage
    lead_id: str
    acquired_at: float


class KanbanPullController:
    """Enforces Little's Law (L = lambda * W) across multi-agent stages via CONWIP pull queues."""

    def __init__(self, wip_limits: Mapping[PipelineStage, int]) -> None:
        self._wip_limits: Dict[PipelineStage, int] = dict(wip_limits)
        self._token_pools: Dict[PipelineStage, asyncio.Queue[str]] = {}
        self._active_leases: Dict[str, ConwipToken] = {}

        for stage, limit in self._wip_limits.items():
            if limit <= 0:
                raise ValueError(f"WIP limit for {stage.value} must be strictly positive, got {limit}")
            q: asyncio.Queue[str] = asyncio.Queue(maxsize=limit)
            for idx in range(limit):
                q.put_nowait(f"KANBAN-{stage.value}-{idx:04d}")
            self._token_pools[stage] = q

    def get_active_wip(self, stage: PipelineStage) -> int:
        if stage not in self._wip_limits:
            return 0
        limit = self._wip_limits[stage]
        available = self._token_pools[stage].qsize()
        return limit - available

    def get_available_tokens(self, stage: PipelineStage) -> int:
        if stage not in self._token_pools:
            return 0
        return self._token_pools[stage].qsize()

    @asynccontextmanager
    async def pull_slot(
        self,
        stage: PipelineStage,
        lead_id: str,
        *,
        block: bool = True,
        timeout: float = 5.0,
    ) -> AsyncIterator[ConwipToken]:
        if stage not in self._token_pools:
            raise ValueError(f"Stage {stage} is not governed by WIP controller.")

        pool = self._token_pools[stage]
        raw_token_id: Optional[str] = None

        try:
            if not block:
                try:
                    raw_token_id = pool.get_nowait()
                except asyncio.QueueEmpty as exc:
                    raise KanbanCapacityExceededError(
                        f"CONWIP capacity exhausted for {stage.value} (Max WIP={self._wip_limits[stage]}). "
                        f"Upstream pull denied for lead '{lead_id}'."
                    ) from exc
            else:
                try:
                    raw_token_id = await asyncio.wait_for(pool.get(), timeout=timeout)
                except asyncio.TimeoutError as exc:
                    raise TokenLeaseTimeoutError(
                        f"Timed out after {timeout}s waiting for downstream pull signal on {stage.value}."
                    ) from exc

            lease = ConwipToken(
                token_id=raw_token_id,
                stage=stage,
                lead_id=lead_id,
                acquired_at=time.monotonic(),
            )
            self._active_leases[raw_token_id] = lease
            yield lease
        finally:
            if raw_token_id is not None:
                self._active_leases.pop(raw_token_id, None)
                pool.put_nowait(raw_token_id)


class EnterpriseSalesPipeline:
    """Deterministic Kanban Pull Pipeline orchestrating autonomous sales deals."""

    ALLOWED_TRANSITIONS: Mapping[PipelineStage, FrozenSet[PipelineStage]] = {
        PipelineStage.LEAD_TRIAGE: frozenset({PipelineStage.DEAL_QUALIFICATION, PipelineStage.ABORTED}),
        PipelineStage.DEAL_QUALIFICATION: frozenset({PipelineStage.PROPOSAL_SYNTHESIS, PipelineStage.ABORTED}),
        PipelineStage.PROPOSAL_SYNTHESIS: frozenset({PipelineStage.EXECUTIVE_CLOSING, PipelineStage.ABORTED}),
        PipelineStage.EXECUTIVE_CLOSING: frozenset({PipelineStage.COMPLETED, PipelineStage.ABORTED}),
        PipelineStage.COMPLETED: frozenset(),
        PipelineStage.ABORTED: frozenset(),
    }

    def __init__(self, controller: KanbanPullController) -> None:
        self._controller = controller

    @staticmethod
    def initialize_lead(
        lead_id: str,
        tenant_id: str,
        initial_metrics: Mapping[str, Any],
    ) -> SalesLeadState:
        genesis_state = SalesLeadState(
            lead_id=lead_id,
            tenant_id=tenant_id,
            current_stage=PipelineStage.LEAD_TRIAGE,
            deal_metrics=dict(initial_metrics),
            event_log=(),
        )
        genesis_event = PipelineEvent.create(
            stage=PipelineStage.LEAD_TRIAGE,
            payload=initial_metrics,
            previous_hash=genesis_state.latest_hash,
        )
        return SalesLeadState(
            lead_id=lead_id,
            tenant_id=tenant_id,
            current_stage=PipelineStage.LEAD_TRIAGE,
            deal_metrics=dict(initial_metrics),
            event_log=(genesis_event,),
        )

    async def execute_stage_pull(
        self,
        state: SalesLeadState,
        target_stage: PipelineStage,
        agent_transform: Callable[[SalesLeadState], Awaitable[Mapping[str, Any]]],
        *,
        block: bool = True,
        timeout: float = 5.0,
    ) -> SalesLeadState:
        allowed = self.ALLOWED_TRANSITIONS.get(state.current_stage, frozenset())
        if target_stage not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal transition for lead '{state.lead_id}': "
                f"{state.current_stage.value} -> {target_stage.value}"
            )

        if target_stage in (PipelineStage.COMPLETED, PipelineStage.ABORTED):
            delta_metrics = await agent_transform(state)
            merged_metrics = {**state.deal_metrics, **delta_metrics}
            event = PipelineEvent.create(
                stage=target_stage,
                payload=delta_metrics,
                previous_hash=state.latest_hash,
            )
            return SalesLeadState(
                lead_id=state.lead_id,
                tenant_id=state.tenant_id,
                current_stage=target_stage,
                deal_metrics=merged_metrics,
                event_log=state.event_log + (event,),
            )

        async with self._controller.pull_slot(
            target_stage,
            state.lead_id,
            block=block,
            timeout=timeout,
        ) as lease_token:
            delta_metrics = await agent_transform(state)
            enriched_delta = {
                **delta_metrics,
                "_conwip_token": lease_token.token_id,
            }
            merged_metrics = {**state.deal_metrics, **enriched_delta}
            event = PipelineEvent.create(
                stage=target_stage,
                payload=enriched_delta,
                previous_hash=state.latest_hash,
            )
            return SalesLeadState(
                lead_id=state.lead_id,
                tenant_id=state.tenant_id,
                current_stage=target_stage,
                deal_metrics=merged_metrics,
                event_log=state.event_log + (event,),
            )


# ==============================================================================
# ENTERPRISE SALES RESILIENT ORCHESTRATION ENGINE (just.ask.mr.zen)
# ==============================================================================

from datetime import datetime, timezone
from typing import Coroutine


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class SalesStage(str, Enum):
    P0_CLOSING = "P0_CLOSING"
    P1_QUOTATION = "P1_QUOTATION"
    P2_ENRICHMENT = "P2_ENRICHMENT"


class EnterpriseResilienceError(Exception):
    """Base exception for enterprise resilience boundaries."""


class CircuitBreakerOpenError(EnterpriseResilienceError):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""


class BulkheadCapacityExceededError(EnterpriseResilienceError):
    """Raised when a bulkhead compartment exceeds its concurrency capacity."""


@dataclass(frozen=True)
class SalesEvent:
    event_id: str
    tenant_id: str
    stage: SalesStage
    action: str
    payload: Dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_canonical_json(self) -> str:
        return json.dumps(
            {
                "event_id": self.event_id,
                "tenant_id": self.tenant_id,
                "stage": self.stage.value,
                "action": self.action,
                "payload": self.payload,
                "timestamp": self.timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


@dataclass
class TransactionBlock:
    block_index: int
    prev_hash: str
    event: SalesEvent
    state_after: Dict[str, Any]
    block_hash: str = field(init=False)

    def __post_init__(self) -> None:
        self.block_hash = self.compute_hash()

    def compute_hash(self) -> str:
        serialized = json.dumps(
            {
                "block_index": self.block_index,
                "prev_hash": self.prev_hash,
                "event_hash": hashlib.sha256(
                    self.event.to_canonical_json().encode("utf-8")
                ).hexdigest(),
                "state_after": self.state_after,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_time_seconds: float = 5.0,
        success_threshold: int = 2,
    ) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_time_seconds = max(0.1, recovery_time_seconds)
        self.success_threshold = max(1, success_threshold)

        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._last_state_change = datetime.now(timezone.utc).timestamp()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def can_execute(self) -> bool:
        async with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            if self._state == CircuitState.OPEN:
                if now - self._last_state_change >= self.recovery_time_seconds:
                    self._state = CircuitState.HALF_OPEN
                    self._consecutive_successes = 0
                    self._last_state_change = now
                    return True
                return False
            return True

    async def record_result(self, success: bool) -> None:
        async with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            if success:
                if self._state == CircuitState.HALF_OPEN:
                    self._consecutive_successes += 1
                    if self._consecutive_successes >= self.success_threshold:
                        self._state = CircuitState.CLOSED
                        self._consecutive_failures = 0
                        self._consecutive_successes = 0
                        self._last_state_change = now
                elif self._state == CircuitState.CLOSED:
                    self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1
                if (
                    self._state == CircuitState.CLOSED
                    and self._consecutive_failures >= self.failure_threshold
                ) or self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.OPEN
                    self._consecutive_successes = 0
                    self._last_state_change = now


class BulkheadPool:
    def __init__(self, limits: Dict[SalesStage, int]) -> None:
        self._semaphores: Dict[SalesStage, asyncio.Semaphore] = {
            stage: asyncio.Semaphore(limit) for stage, limit in limits.items()
        }
        self._limits = limits

    async def execute_in_bulkhead(
        self,
        stage: SalesStage,
        coro_func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        sem = self._semaphores.get(stage)
        if sem is None:
            raise BulkheadCapacityExceededError(f"No bulkhead defined for stage: {stage}")

        if sem.locked():
            raise BulkheadCapacityExceededError(
                f"Bulkhead for {stage.value} reached max capacity {self._limits[stage]}"
            )

        async with sem:
            return await coro_func(*args, **kwargs)


class ResilientSalesEngine:
    def __init__(self) -> None:
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3, recovery_time_seconds=1.0, success_threshold=2
        )
        self.bulkhead = BulkheadPool(
            {
                SalesStage.P0_CLOSING: 10,
                SalesStage.P1_QUOTATION: 5,
                SalesStage.P2_ENRICHMENT: 2,
            }
        )
        self.state_ledger: List[TransactionBlock] = []
        self._current_state: Dict[str, Any] = {
            "total_deals": 0,
            "pipeline_revenue": 0.0,
            "tenant_deals": {},
        }
        self._genesis_hash = "0" * 64
        self._ledger_lock = asyncio.Lock()

    def verify_invariant(self) -> bool:
        if not self.state_ledger:
            return True

        current_prev = self._genesis_hash
        for i, block in enumerate(self.state_ledger):
            if block.block_index != i:
                return False
            if block.prev_hash != current_prev:
                return False
            recomputed = block.compute_hash()
            if block.block_hash != recomputed:
                return False
            current_prev = block.block_hash

        return True

    def apply_odoo_odoo_pattern(self) -> bool:
        tenant_counts = self._current_state.get("tenant_deals", {})
        total_recorded = sum(tenant_counts.values())
        return total_recorded == self._current_state.get("total_deals", 0)

    def apply_astral_sh_uv_pattern(self) -> bool:
        return self.verify_invariant()

    async def execute_sales_step(
        self,
        event: SalesEvent,
        remote_agent_call: Callable[[SalesEvent], Coroutine[Any, Any, Dict[str, Any]]],
        fallback_call: Callable[[SalesEvent], Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not await self.circuit_breaker.can_execute():
            result = fallback_call(event)
            await self._record_transaction(event, result, fallback_used=True)
            return result

        try:
            result = await self.bulkhead.execute_in_bulkhead(
                event.stage, remote_agent_call, event
            )
            await self.circuit_breaker.record_result(success=True)
            await self._record_transaction(event, result, fallback_used=False)
            return result
        except BulkheadCapacityExceededError:
            result = fallback_call(event)
            await self._record_transaction(event, result, fallback_used=True)
            return result
        except Exception:
            await self.circuit_breaker.record_result(success=False)
            result = fallback_call(event)
            await self._record_transaction(event, result, fallback_used=True)
            return result

    async def _record_transaction(
        self, event: SalesEvent, result: Dict[str, Any], fallback_used: bool
    ) -> None:
        async with self._ledger_lock:
            amount = float(result.get("amount", 0.0))
            new_deals = self._current_state["total_deals"] + 1
            new_revenue = self._current_state["pipeline_revenue"] + amount

            tenant_map = dict(self._current_state["tenant_deals"])
            tenant_map[event.tenant_id] = tenant_map.get(event.tenant_id, 0) + 1

            new_state = {
                "total_deals": new_deals,
                "pipeline_revenue": round(new_revenue, 2),
                "tenant_deals": tenant_map,
                "last_action": event.action,
                "fallback_used": fallback_used,
            }

            prev_hash = (
                self.state_ledger[-1].block_hash
                if self.state_ledger
                else self._genesis_hash
            )
            block = TransactionBlock(
                block_index=len(self.state_ledger),
                prev_hash=prev_hash,
                event=event,
                state_after=new_state,
            )
            self.state_ledger.append(block)
            self._current_state = new_state


# ==============================================================================
# S-CURVE PUBGRUB DEAL CONSTRAINT SOLVER & MERKLE-EVENT STATE ENGINE
# ==============================================================================


class SalesProcessStage(str, Enum):
    LEAD_INCEPTION = "LEAD_INCEPTION"
    TECHNICAL_VALIDATION = "TECHNICAL_VALIDATION"
    COMMERCIAL_NEGOTIATION = "COMMERCIAL_NEGOTIATION"
    COMPLIANCE_SIGN_OFF = "COMPLIANCE_SIGN_OFF"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"


@dataclass(frozen=True)
class EnterpriseEvent:
    event_id: str
    tenant_id: str
    timestamp: float
    action: str
    payload: Dict[str, Any]
    actor_agent_id: str

    def compute_event_hash(self) -> str:
        serialized = json.dumps(
            {
                "event_id": self.event_id,
                "tenant_id": self.tenant_id,
                "timestamp": self.timestamp,
                "action": self.action,
                "payload": self.payload,
                "actor_agent_id": self.actor_agent_id,
            },
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class PubGrubDealConstraintSolver:
    """
    PubGrub-inspired deterministic constraint solver for enterprise deal terms.
    Ensures that commercial discount rates, contract durations, and SLA terms
    satisfy bounded dependency constraints without cycles or runtime deadlocks.
    """
    @staticmethod
    def resolve_deal_terms(
        requested_terms: Dict[str, Any],
        tenant_rules: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        max_discount = tenant_rules.get("max_authorized_discount", 0.20)
        req_discount = requested_terms.get("discount_rate", 0.0)

        if req_discount > max_discount:
            return False, f"ConstraintViolation: requested discount {req_discount} exceeds limit {max_discount}"

        required_clauses: Set[str] = set(tenant_rules.get("mandatory_riders", []))
        submitted_clauses: Set[str] = set(requested_terms.get("attached_riders", []))

        missing_clauses = required_clauses - submitted_clauses
        if missing_clauses:
            return False, f"ConstraintViolation: missing mandatory riders {sorted(missing_clauses)}"

        return True, None


@dataclass
class EnterpriseSalesState:
    tenant_id: str
    opportunity_id: str
    current_stage: SalesProcessStage
    active_terms: Dict[str, Any]
    state_history_hashes: List[str] = field(default_factory=list)
    last_block_hash: str = "0" * 64
    active_memory_slots: int = 0
    max_memory_slots: int = 1024

    def verify_invariant(self) -> bool:
        if not self.tenant_id or not self.opportunity_id:
            return False
        if len(self.last_block_hash) != 64:
            return False
        if self.active_memory_slots > self.max_memory_slots:
            return False
        return True

    def apply_odoo_odoo_pattern(self, request_tenant_id: str) -> bool:
        if request_tenant_id != self.tenant_id:
            raise PermissionError(
                f"MultiTenantIsolationViolation: Tenant {request_tenant_id} attempted access to {self.tenant_id}"
            )
        return True

    def apply_astral_sh_uv_pattern(
        self,
        new_terms: Dict[str, Any],
        tenant_policy: Dict[str, Any],
    ) -> bool:
        is_satisfiable, reason = PubGrubDealConstraintSolver.resolve_deal_terms(
            requested_terms=new_terms,
            tenant_rules=tenant_policy,
        )
        if not is_satisfiable:
            raise ValueError(f"PubGrubUnsatisfiableTerms: {reason}")
        return True

    def transition_state(
        self,
        event: EnterpriseEvent,
        next_stage: SalesProcessStage,
        tenant_policy: Dict[str, Any],
    ) -> str:
        self.apply_odoo_odoo_pattern(event.tenant_id)

        if "terms" in event.payload:
            self.apply_astral_sh_uv_pattern(event.payload["terms"], tenant_policy)
            self.active_terms.update(event.payload["terms"])

        if self.active_memory_slots >= self.max_memory_slots:
            raise BufferError(f"MemoryInvariantBreached: M(t) exceeds max_memory_slots ({self.max_memory_slots})")

        self.active_memory_slots += 1
        try:
            event_hash = event.compute_event_hash()
            combined_hash_input = f"{self.last_block_hash}:{event_hash}:{next_stage.value}"
            new_state_hash = hashlib.sha256(combined_hash_input.encode("utf-8")).hexdigest()

            self.current_stage = next_stage
            self.last_block_hash = new_state_hash
            self.state_history_hashes.append(new_state_hash)

            if not self.verify_invariant():
                raise RuntimeError("PostTransitionInvariantFailed: state integrity compromised")

            return new_state_hash
        finally:
            self.active_memory_slots -= 1


# ==============================================================================
# ASYNCHRONOUS DOUBLE-ENTRY SALES PIPELINE ORCHESTRATOR (immoon0009-gmail-com)
# ==============================================================================


class OrchestratorSalesStage(str, Enum):
    LEAD = "LEAD"
    QUALIFICATION = "QUALIFICATION"
    PROPOSAL = "PROPOSAL"
    NEGOTIATION = "NEGOTIATION"
    COMMITTED = "COMMITTED"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"


class ExecutionState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRIED = "RETRIED"


class SalesOrchestratorException(Exception):
    """Base exception for sovereign sales process orchestration."""


class InvariantViolationError(SalesOrchestratorException):
    """Raised when formal state machine or double-entry invariants fail."""


class TenantSecurityViolationError(SalesOrchestratorException):
    """Raised when multi-company tenant partitioning rules are breached."""


class ConcurrencyResourceExhaustedError(SalesOrchestratorException):
    """Raised when memory or task slots exceed bounded upper limit M_max."""


@dataclass(frozen=True)
class OrchestratorTenantContext:
    company_id: int
    allowed_company_ids: Tuple[int, ...]
    user_id: int
    is_system_admin: bool = False

    def validate_access(self, target_company_id: int) -> bool:
        if self.is_system_admin:
            return True
        return target_company_id in self.allowed_company_ids


@dataclass(frozen=True)
class OrchestratorSalesEvent:
    event_id: str
    opportunity_id: str
    company_id: int
    source_stage: OrchestratorSalesStage
    target_stage: OrchestratorSalesStage
    deal_value: float
    probability: float
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class LedgerEntry:
    index: int
    event_id: str
    opportunity_id: str
    company_id: int
    from_stage: OrchestratorSalesStage
    to_stage: OrchestratorSalesStage
    delta_weighted_value: float
    prev_hash: str
    current_hash: str
    timestamp: float


class BoundedResourcePool:
    """PubGrub / Astral-uv inspired deterministic slot manager enforcing M(t) <= M_max."""
    def __init__(self, max_concurrent_slots: int = 100):
        if max_concurrent_slots <= 0:
            raise InvariantViolationError("max_concurrent_slots must be greater than zero.")
        self.max_slots = max_concurrent_slots
        self._active_slots: Set[str] = set()

    @property
    def current_utilization(self) -> int:
        return len(self._active_slots)

    def acquire(self, task_id: str) -> None:
        if len(self._active_slots) >= self.max_slots:
            raise ConcurrencyResourceExhaustedError(
                f"Resource quota exhausted: {len(self._active_slots)}/{self.max_slots} slots active."
            )
        self._active_slots.add(task_id)

    def release(self, task_id: str) -> None:
        self._active_slots.discard(task_id)


class EnterpriseSalesOrchestrator:
    """
    Sovereign Orchestration Core combining Prefect reactive task flows
    with Odoo multi-tenant RLS and FinRobot cryptographically chained ledger invariants.
    """
    VALID_TRANSITIONS: Mapping[OrchestratorSalesStage, Set[OrchestratorSalesStage]] = {
        OrchestratorSalesStage.LEAD: {OrchestratorSalesStage.QUALIFICATION, OrchestratorSalesStage.CLOSED_LOST},
        OrchestratorSalesStage.QUALIFICATION: {OrchestratorSalesStage.PROPOSAL, OrchestratorSalesStage.CLOSED_LOST},
        OrchestratorSalesStage.PROPOSAL: {
            OrchestratorSalesStage.NEGOTIATION,
            OrchestratorSalesStage.QUALIFICATION,
            OrchestratorSalesStage.CLOSED_LOST,
        },
        OrchestratorSalesStage.NEGOTIATION: {
            OrchestratorSalesStage.COMMITTED,
            OrchestratorSalesStage.PROPOSAL,
            OrchestratorSalesStage.CLOSED_LOST,
        },
        OrchestratorSalesStage.COMMITTED: {
            OrchestratorSalesStage.CLOSED_WON,
            OrchestratorSalesStage.CLOSED_LOST,
            OrchestratorSalesStage.NEGOTIATION,
        },
        OrchestratorSalesStage.CLOSED_WON: set(),
        OrchestratorSalesStage.CLOSED_LOST: {OrchestratorSalesStage.LEAD},
    }

    GENESIS_HASH = "0" * 64

    def __init__(self, max_concurrent_slots: int = 64):
        self.resource_pool = BoundedResourcePool(max_concurrent_slots=max_concurrent_slots)
        self.ledger: List[LedgerEntry] = []
        self._opportunities: Dict[str, Dict[str, Any]] = {}

    def _compute_entry_hash(
        self,
        index: int,
        prev_hash: str,
        event: OrchestratorSalesEvent,
        delta_val: float,
        ts: float,
    ) -> str:
        serialized_payload = json.dumps(event.payload, sort_keys=True)
        raw_token = (
            f"{index}|{prev_hash}|{event.event_id}|{event.opportunity_id}|"
            f"{event.company_id}|{event.source_stage.value}|{event.target_stage.value}|"
            f"{delta_val:.4f}|{serialized_payload}|{ts:.4f}"
        )
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def apply_odoo_odoo_pattern(
        self,
        tenant_context: OrchestratorTenantContext,
        target_company_id: int,
    ) -> bool:
        if not tenant_context.validate_access(target_company_id):
            raise TenantSecurityViolationError(
                f"Tenant Security Violation: User {tenant_context.user_id} in company "
                f"{tenant_context.company_id} forbidden from accessing company {target_company_id}."
            )
        return True

    def apply_astral_sh_uv_pattern(self) -> bool:
        invariant_satisfied = self.resource_pool.current_utilization <= self.resource_pool.max_slots
        if not invariant_satisfied:
            raise InvariantViolationError("Resource utilization violated M(t) <= M_max invariant.")
        return True

    def verify_invariant(self) -> bool:
        if not self.ledger:
            return True

        for i, entry in enumerate(self.ledger):
            expected_prev = self.GENESIS_HASH if i == 0 else self.ledger[i - 1].current_hash
            if entry.prev_hash != expected_prev:
                return False
            if len(entry.current_hash) != 64:
                return False

        return True

    def register_opportunity(
        self,
        tenant_context: OrchestratorTenantContext,
        opportunity_id: str,
        company_id: int,
        initial_value: float,
    ) -> None:
        self.apply_odoo_odoo_pattern(tenant_context, company_id)
        if opportunity_id in self._opportunities:
            raise InvariantViolationError(f"Opportunity {opportunity_id} already registered.")
        if initial_value < 0.0:
            raise InvariantViolationError("Initial deal value cannot be negative.")

        self._opportunities[opportunity_id] = {
            "opportunity_id": opportunity_id,
            "company_id": company_id,
            "stage": OrchestratorSalesStage.LEAD,
            "deal_value": initial_value,
            "probability": 0.10,
            "weighted_value": initial_value * 0.10,
        }

    def execute_transition_flow(
        self,
        tenant_context: OrchestratorTenantContext,
        event: OrchestratorSalesEvent,
    ) -> LedgerEntry:
        self.apply_odoo_odoo_pattern(tenant_context, event.company_id)
        task_id = f"flow_transition_{event.event_id}"
        self.resource_pool.acquire(task_id)

        try:
            if event.opportunity_id not in self._opportunities:
                raise InvariantViolationError(f"Opportunity {event.opportunity_id} does not exist.")

            opp = self._opportunities[event.opportunity_id]
            current_stage: OrchestratorSalesStage = opp["stage"]

            allowed = self.VALID_TRANSITIONS.get(current_stage, set())
            if event.target_stage not in allowed:
                raise InvariantViolationError(
                    f"Illegal stage transition from {current_stage.value} to {event.target_stage.value}. "
                    f"Allowed targets: {[s.value for s in allowed]}"
                )

            if not (0.0 <= event.probability <= 1.0):
                raise InvariantViolationError(f"Probability {event.probability} out of valid bounds [0.0, 1.0].")
            if event.deal_value < 0.0:
                raise InvariantViolationError(f"Deal value {event.deal_value} cannot be negative.")

            old_weighted = opp["weighted_value"]
            new_weighted = event.deal_value * event.probability
            delta_weighted = new_weighted - old_weighted

            entry_idx = len(self.ledger)
            prev_hash = self.ledger[-1].current_hash if self.ledger else self.GENESIS_HASH
            now_ts = time.time()
            current_hash = self._compute_entry_hash(entry_idx, prev_hash, event, delta_weighted, now_ts)

            entry = LedgerEntry(
                index=entry_idx,
                event_id=event.event_id,
                opportunity_id=event.opportunity_id,
                company_id=event.company_id,
                from_stage=current_stage,
                to_stage=event.target_stage,
                delta_weighted_value=delta_weighted,
                prev_hash=prev_hash,
                current_hash=current_hash,
                timestamp=now_ts,
            )

            opp["stage"] = event.target_stage
            opp["deal_value"] = event.deal_value
            opp["probability"] = event.probability
            opp["weighted_value"] = new_weighted

            self.ledger.append(entry)
            return entry

        finally:
            self.resource_pool.release(task_id)
            self.apply_astral_sh_uv_pattern()


# ==============================================================================
# CRYPTOGRAPHIC DUAL-KEY COUNTER-SIGNATURE STATE MACHINE (CDK-CSSM) (zenphamgeek)
# ==============================================================================

import decimal


class SalesOrderState(str, Enum):
    DRAFT_LEAD = "DRAFT_LEAD"
    QUALIFIED = "QUALIFIED"
    QUOTATION_PROPOSED = "QUOTATION_PROPOSED"
    COUNTER_SIGNED_AUDITED = "COUNTER_SIGNED_AUDITED"
    CONFIRMED_SALES_ORDER = "CONFIRMED_SALES_ORDER"
    REJECTED = "REJECTED"


class DomainSecurityError(Exception):
    """Raised when tenant boundary or margin invariant is violated."""


@dataclass(frozen=True)
class TenantSecurityContext:
    tenant_id: str
    company_id: Any = ""
    minimum_margin_floor: decimal.Decimal = decimal.Decimal("0.00")
    allowed_agent_roles: Tuple[str, ...] = ()
    user_id: str = ""
    is_active: bool = True

    def validate_access(self, requesting_company_id: int, agent_role: str) -> None:
        if requesting_company_id != self.company_id:
            raise DomainSecurityError(
                f"Tenant isolation failure: requesting company {requesting_company_id} "
                f"does not match tenant scope {self.company_id}."
            )
        if agent_role not in self.allowed_agent_roles:
            raise DomainSecurityError(
                f"Role violation: agent role '{agent_role}' not authorized for tenant '{self.tenant_id}'."
            )


@dataclass(frozen=True)
class QuotationLineItem:
    product_sku: str
    quantity: int
    unit_cost: decimal.Decimal
    offered_price: decimal.Decimal

    def calculate_line_margin(self) -> decimal.Decimal:
        revenue = self.offered_price * self.quantity
        cost = self.unit_cost * self.quantity
        if revenue == decimal.Decimal("0.00"):
            return decimal.Decimal("-1.00")
        return (revenue - cost) / revenue


@dataclass(frozen=True)
class SalesTransitionEvent:
    event_id: str
    order_id: str
    from_state: SalesOrderState
    to_state: SalesOrderState
    agent_id: str
    agent_role: str
    agent_signature_digest: str
    line_items: Tuple[QuotationLineItem, ...]
    timestamp_utc: str

    def calculate_total_margin(self) -> decimal.Decimal:
        total_revenue = decimal.Decimal("0.00")
        total_cost = decimal.Decimal("0.00")
        for item in self.line_items:
            total_revenue += item.offered_price * item.quantity
            total_cost += item.unit_cost * item.quantity
        if total_revenue <= decimal.Decimal("0.00"):
            return decimal.Decimal("-1.00")
        return (total_revenue - total_cost) / total_revenue

    def to_canonical_bytes(self) -> bytes:
        payload = {
            "event_id": self.event_id,
            "order_id": self.order_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "agent_id": self.agent_id,
            "agent_role": self.agent_role,
            "agent_signature_digest": self.agent_signature_digest,
            "line_items": [
                {
                    "product_sku": item.product_sku,
                    "quantity": item.quantity,
                    "unit_cost": str(item.unit_cost),
                    "offered_price": str(item.offered_price),
                }
                for item in self.line_items
            ],
            "timestamp_utc": self.timestamp_utc,
        }
        canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return canonical_str.encode("utf-8")


@dataclass(frozen=True)
class CounterSignedLedgerEntry:
    sequence: int
    previous_hash: str
    current_hash: str
    event_id: str
    state: SalesOrderState
    rule_engine_witness_token: str


class EnterpriseSalesStateMachine:
    """
    Sovereign state machine orchestrating AI-driven sales process transitions.
    Implements formal invariant delta(S_t, E) -> S_{t+1} with dual-key cryptographic validation.
    """

    ALLOWED_TRANSITIONS: Dict[SalesOrderState, Tuple[SalesOrderState, ...]] = {
        SalesOrderState.DRAFT_LEAD: (SalesOrderState.QUALIFIED, SalesOrderState.REJECTED),
        SalesOrderState.QUALIFIED: (SalesOrderState.QUOTATION_PROPOSED, SalesOrderState.REJECTED),
        SalesOrderState.QUOTATION_PROPOSED: (SalesOrderState.COUNTER_SIGNED_AUDITED, SalesOrderState.REJECTED),
        SalesOrderState.COUNTER_SIGNED_AUDITED: (SalesOrderState.CONFIRMED_SALES_ORDER, SalesOrderState.REJECTED),
        SalesOrderState.CONFIRMED_SALES_ORDER: (),
        SalesOrderState.REJECTED: (),
    }

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, order_id: str, tenant_context: TenantSecurityContext) -> None:
        self.order_id = order_id
        self.tenant_context = tenant_context
        self.current_state = SalesOrderState.DRAFT_LEAD
        self.ledger: List[CounterSignedLedgerEntry] = []
        self._initialize_genesis()

    def _initialize_genesis(self) -> None:
        genesis_entry = CounterSignedLedgerEntry(
            sequence=0,
            previous_hash=self.GENESIS_HASH,
            current_hash=hashlib.sha256(
                f"GENESIS:{self.order_id}:{self.tenant_context.tenant_id}".encode("utf-8")
            ).hexdigest(),
            event_id="EVT_GENESIS",
            state=self.current_state,
            rule_engine_witness_token="SYSTEM_GENESIS_ROOT",
        )
        self.ledger.append(genesis_entry)

    @property
    def latest_hash(self) -> str:
        return self.ledger[-1].current_hash

    def verify_chain_integrity(self) -> bool:
        if not self.ledger:
            return False
        for i in range(1, len(self.ledger)):
            prev = self.ledger[i - 1]
            curr = self.ledger[i]
            if curr.previous_hash != prev.current_hash:
                return False
        return True

    def transition(self, event: SalesTransitionEvent, requesting_company_id: int) -> CounterSignedLedgerEntry:
        self.tenant_context.validate_access(requesting_company_id, event.agent_role)

        if event.from_state != self.current_state:
            raise InvalidStateTransitionError(
                f"State mismatch: order is currently in '{self.current_state.value}', "
                f"event specifies from_state '{event.from_state.value}'."
            )

        allowed_targets = self.ALLOWED_TRANSITIONS.get(self.current_state, ())
        if event.to_state not in allowed_targets:
            raise InvalidStateTransitionError(
                f"Illegal transition: '{self.current_state.value}' cannot transition to '{event.to_state.value}'. "
                f"Permitted targets: {[s.value for s in allowed_targets]}."
            )

        if event.to_state in (
            SalesOrderState.QUOTATION_PROPOSED,
            SalesOrderState.COUNTER_SIGNED_AUDITED,
            SalesOrderState.CONFIRMED_SALES_ORDER,
        ):
            if not event.line_items:
                raise DomainSecurityError("Cannot advance quotation without line items.")

            calculated_margin = event.calculate_total_margin()
            if calculated_margin < self.tenant_context.minimum_margin_floor:
                raise DomainSecurityError(
                    f"Financial Invariant Breach: Calculated margin {calculated_margin:.4f} is below "
                    f"mandatory tenant margin floor {self.tenant_context.minimum_margin_floor:.4f}."
                )

        witness_seed = f"{self.tenant_context.tenant_id}:{event.order_id}:{event.to_state.value}:{event.timestamp_utc}"
        witness_token = hashlib.sha256(witness_seed.encode("utf-8")).hexdigest()

        hasher = hashlib.sha256()
        hasher.update(self.latest_hash.encode("utf-8"))
        hasher.update(event.to_canonical_bytes())
        hasher.update(witness_token.encode("utf-8"))
        next_hash = hasher.hexdigest()

        new_entry = CounterSignedLedgerEntry(
            sequence=len(self.ledger),
            previous_hash=self.latest_hash,
            current_hash=next_hash,
            event_id=event.event_id,
            state=event.to_state,
            rule_engine_witness_token=witness_token,
        )

        self.current_state = event.to_state
        self.ledger.append(new_entry)
        return new_entry


# ==============================================================================
# PUBGRUB-GOVERNED CONTENT-ADDRESSED SALES POLICY RESOLUTION (PG-CASPR)
# ==============================================================================


class PolicySalesStage(str, Enum):
    """Defines the validated lifecycle stages of an enterprise deal."""
    LEAD = "LEAD"
    QUALIFIED = "QUALIFIED"
    PROPOSAL = "PROPOSAL"
    NEGOTIATION = "NEGOTIATION"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"


class PolicyConstraintUnsatError(Exception):
    """Raised when deal policy requirements are unsatisfiable."""


class ResourceExhaustionError(Exception):
    """Raised when the bounded active lease limit is reached."""


@dataclass(frozen=True)
class SalesTransactionEvent:
    """Immutable audit record representing a verified state transition."""
    event_id: str
    tenant_id: str
    deal_id: str
    from_stage: PolicySalesStage
    to_stage: PolicySalesStage
    payload_hash: str
    timestamp: float
    prev_hash: str
    current_hash: str


@dataclass(frozen=True)
class DealPolicyRequirement:
    """Governance constraints required before stage advancement."""
    max_discount_pct: float
    min_contract_value: float
    requires_executive_signoff: bool
    requires_security_review: bool


class PubGrubPolicyStateMachine:
    """High-assurance state machine for AI-driven enterprise sales policy SAT and stage progression."""

    LEGAL_TRANSITIONS: Dict[PolicySalesStage, Set[PolicySalesStage]] = {
        PolicySalesStage.LEAD: {PolicySalesStage.QUALIFIED, PolicySalesStage.CLOSED_LOST},
        PolicySalesStage.QUALIFIED: {PolicySalesStage.PROPOSAL, PolicySalesStage.CLOSED_LOST},
        PolicySalesStage.PROPOSAL: {PolicySalesStage.NEGOTIATION, PolicySalesStage.CLOSED_LOST},
        PolicySalesStage.NEGOTIATION: {PolicySalesStage.CLOSED_WON, PolicySalesStage.CLOSED_LOST},
        PolicySalesStage.CLOSED_WON: set(),
        PolicySalesStage.CLOSED_LOST: {PolicySalesStage.LEAD},
    }

    def __init__(self, tenant_id: str, max_concurrent_leases: int = 16) -> None:
        if not tenant_id or not isinstance(tenant_id, str):
            raise TenantSecurityViolationError("Invalid tenant identifier.")
        self.tenant_id: str = tenant_id
        self.max_concurrent_leases: int = max_concurrent_leases
        self._active_leases: int = 0
        self._ledger: List[SalesTransactionEvent] = []
        self._deal_states: Dict[str, PolicySalesStage] = {}

    def verify_invariant(self) -> bool:
        if not self._ledger:
            return True

        previous_hash = "0" * 64
        for event in self._ledger:
            if event.prev_hash != previous_hash:
                return False
            expected_hash = self._compute_event_hash(
                event_id=event.event_id,
                tenant_id=event.tenant_id,
                deal_id=event.deal_id,
                from_stage=event.from_stage,
                to_stage=event.to_stage,
                payload_hash=event.payload_hash,
                timestamp=event.timestamp,
                prev_hash=event.prev_hash,
            )
            if event.current_hash != expected_hash:
                return False
            previous_hash = event.current_hash
        return True

    def apply_odoo_odoo_pattern(self, request_tenant_id: str) -> bool:
        if request_tenant_id != self.tenant_id:
            raise TenantSecurityViolationError(
                f"Cross-tenant access rejected: actor={request_tenant_id}, context={self.tenant_id}"
            )
        return True

    def apply_astral_sh_uv_pattern(self) -> bool:
        return 0 <= self._active_leases <= self.max_concurrent_leases

    def acquire_lease(self) -> int:
        if self._active_leases >= self.max_concurrent_leases:
            raise ResourceExhaustionError(
                f"Capacity limit exceeded: {self._active_leases}/{self.max_concurrent_leases}"
            )
        self._active_leases += 1
        return self._active_leases

    def release_lease(self) -> int:
        if self._active_leases <= 0:
            raise ResourceExhaustionError("Attempted to release nonexistent lease slot.")
        self._active_leases -= 1
        return self._active_leases

    def _compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def _compute_event_hash(
        self,
        event_id: str,
        tenant_id: str,
        deal_id: str,
        from_stage: PolicySalesStage,
        to_stage: PolicySalesStage,
        payload_hash: str,
        timestamp: float,
        prev_hash: str,
    ) -> str:
        raw_block = f"{event_id}|{tenant_id}|{deal_id}|{from_stage.value}|{to_stage.value}|{payload_hash}|{timestamp:.6f}|{prev_hash}"
        return hashlib.sha256(raw_block.encode("utf-8")).hexdigest()

    def solve_policy_constraints(
        self,
        target_stage: PolicySalesStage,
        payload: Dict[str, Any],
        policy: DealPolicyRequirement,
    ) -> bool:
        discount = float(payload.get("discount_pct", 0.0))
        value = float(payload.get("contract_value", 0.0))
        has_exec_signoff = bool(payload.get("executive_signoff", False))
        has_sec_review = bool(payload.get("security_review_completed", False))

        if target_stage in (
            PolicySalesStage.QUALIFIED,
            PolicySalesStage.PROPOSAL,
            PolicySalesStage.NEGOTIATION,
            PolicySalesStage.CLOSED_WON,
        ):
            if discount > policy.max_discount_pct and not has_exec_signoff:
                raise PolicyConstraintUnsatError(
                    f"Policy Unsatisfiable: Discount {discount}% exceeds limit {policy.max_discount_pct}% without executive signoff."
                )
            if value < policy.min_contract_value:
                raise PolicyConstraintUnsatError(
                    f"Policy Unsatisfiable: Contract value {value} below minimum threshold {policy.min_contract_value}."
                )

        if target_stage == PolicySalesStage.CLOSED_WON:
            if policy.requires_security_review and not has_sec_review:
                raise PolicyConstraintUnsatError(
                    "Policy Unsatisfiable: Security review must be completed prior to CLOSED_WON."
                )
            if policy.requires_executive_signoff and not has_exec_signoff:
                raise PolicyConstraintUnsatError(
                    "Policy Unsatisfiable: Executive signoff mandatory for CLOSED_WON."
                )

        return True

    def transition_stage(
        self,
        request_tenant_id: str,
        deal_id: str,
        target_stage: PolicySalesStage,
        payload: Dict[str, Any],
        policy: DealPolicyRequirement,
    ) -> SalesTransactionEvent:
        self.apply_odoo_odoo_pattern(request_tenant_id)
        self.acquire_lease()
        try:
            current_stage = self._deal_states.get(deal_id, PolicySalesStage.LEAD)
            allowed_targets = self.LEGAL_TRANSITIONS.get(current_stage, set())
            if target_stage not in allowed_targets:
                raise InvalidStateTransitionError(
                    f"Illegal transition from {current_stage.value} to {target_stage.value} for deal {deal_id}."
                )

            self.solve_policy_constraints(target_stage, payload, policy)

            timestamp = time.time()
            payload_hash = self._compute_payload_hash(payload)
            event_id = f"evt_{deal_id}_{int(timestamp * 1000)}"
            prev_hash = self._ledger[-1].current_hash if self._ledger else "0" * 64
            current_hash = self._compute_event_hash(
                event_id=event_id,
                tenant_id=self.tenant_id,
                deal_id=deal_id,
                from_stage=current_stage,
                to_stage=target_stage,
                payload_hash=payload_hash,
                timestamp=timestamp,
                prev_hash=prev_hash,
            )

            event = SalesTransactionEvent(
                event_id=event_id,
                tenant_id=self.tenant_id,
                deal_id=deal_id,
                from_stage=current_stage,
                to_stage=target_stage,
                payload_hash=payload_hash,
                timestamp=timestamp,
                prev_hash=prev_hash,
                current_hash=current_hash,
            )

            self._ledger.append(event)
            self._deal_states[deal_id] = target_stage
            return event
        finally:
            self.release_lease()

    def get_ledger(self) -> List[SalesTransactionEvent]:
        return list(self._ledger)


# ==============================================================================
# CRDT-BASED OFFLINE-FIRST SALES QUOTATION ENGINE (sunward)
# ==============================================================================


@dataclass(frozen=True)
class QuoteItemTag:
    item_id: str
    client_id: str
    timestamp_ns: int


@dataclass
class QuoteLineItem:
    product_sku: str
    quantity: int
    unit_price_cents: int
    discount_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_sku": self.product_sku,
            "quantity": self.quantity,
            "unit_price_cents": self.unit_price_cents,
            "discount_pct": self.discount_pct,
        }


class SalesQuoteCRDT:
    """
    Observed-Remove Set (OR-Set) with LWW-Register attributes for
    Conflict-Free Concurrent Sales Proposal Generation.
    """

    def __init__(self, quote_id: str, client_id: str):
        self.quote_id: str = quote_id
        self.client_id: str = client_id
        self._add_set: Dict[QuoteItemTag, Tuple[QuoteLineItem, int]] = {}
        self._remove_set: Set[QuoteItemTag] = set()
        self._audit_chain: List[str] = []

    def add_line_item(
        self, product_sku: str, quantity: int, unit_price_cents: int, discount_pct: float = 0.0
    ) -> QuoteItemTag:
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")
        if discount_pct < 0.0 or discount_pct > 100.0:
            raise ValueError(f"Invalid discount percentage: {discount_pct}")

        tag = QuoteItemTag(
            item_id=hashlib.sha256(f"{product_sku}:{time.time_ns()}".encode()).hexdigest()[:12],
            client_id=self.client_id,
            timestamp_ns=time.time_ns(),
        )
        item = QuoteLineItem(product_sku, quantity, unit_price_cents, discount_pct)
        self._add_set[tag] = (item, tag.timestamp_ns)
        self._record_transition("ADD_LINE_ITEM", tag.item_id)
        return tag

    def remove_line_item(self, tag: QuoteItemTag) -> None:
        if tag in self._add_set:
            self._remove_set.add(tag)
            self._record_transition("REMOVE_LINE_ITEM", tag.item_id)

    def merge(self, incoming: "SalesQuoteCRDT") -> "SalesQuoteCRDT":
        for tag, (item, ts) in incoming._add_set.items():
            if tag not in self._add_set or self._add_set[tag][1] < ts:
                self._add_set[tag] = (item, ts)

        self._remove_set.update(incoming._remove_set)
        self._record_transition("MERGE_CRDT", incoming.client_id)
        return self

    def active_items(self) -> List[QuoteLineItem]:
        return [
            item
            for tag, (item, _) in self._add_set.items()
            if tag not in self._remove_set
        ]

    def calculate_total_cents(self) -> int:
        total = 0
        for item in self.active_items():
            discount_factor = 1.0 - (item.discount_pct / 100.0)
            item_total = int(item.quantity * item.unit_price_cents * discount_factor)
            total += item_total
        return total

    def _record_transition(self, action: str, reference: str) -> None:
        prev_hash = self._audit_chain[-1] if self._audit_chain else "GENESIS_0000000000000000"
        payload = f"{prev_hash}:{action}:{reference}:{time.time_ns()}"
        curr_hash = hashlib.sha256(payload.encode()).hexdigest()
        self._audit_chain.append(curr_hash)

    def verify_invariant(self) -> bool:
        if self.calculate_total_cents() < 0:
            return False
        if not self._audit_chain:
            return True
        return len(self._audit_chain) > 0


# ==============================================================================
# BANT-TO-CLOSED-WON SEMANTIC GATE STATE MACHINE (E2E-QA-11)
# ==============================================================================


class GateSalesStage(str, Enum):
    LEAD_DISCOVERY = "LEAD_DISCOVERY"
    QUALIFICATION_BANT = "QUALIFICATION_BANT"
    TECHNICAL_VALIDATION = "TECHNICAL_VALIDATION"
    COMMERCIAL_PROPOSAL = "COMMERCIAL_PROPOSAL"
    LEGAL_SECURITY_REVIEW = "LEGAL_SECURITY_REVIEW"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"


@dataclass(frozen=True)
class GateSalesEvent:
    event_id: str
    tenant_id: str
    target_stage: GateSalesStage
    payload: Dict[str, Any]
    timestamp_utc: str
    actor_id: str


@dataclass(frozen=True)
class StateAuditBlock:
    index: int
    prev_hash: str
    state_digest: str
    event_id: str
    timestamp_utc: str
    block_hash: str


class BantGateSalesStateMachine:
    """
    Deterministic Finite State Machine (FSM) enforcing BANT-to-Closed-Won
    semantic stage gates and append-only cryptographic provenance.
    """

    ALLOWED_TRANSITIONS: Dict[GateSalesStage, List[GateSalesStage]] = {
        GateSalesStage.LEAD_DISCOVERY: [
            GateSalesStage.QUALIFICATION_BANT,
            GateSalesStage.CLOSED_LOST,
        ],
        GateSalesStage.QUALIFICATION_BANT: [
            GateSalesStage.TECHNICAL_VALIDATION,
            GateSalesStage.CLOSED_LOST,
        ],
        GateSalesStage.TECHNICAL_VALIDATION: [
            GateSalesStage.COMMERCIAL_PROPOSAL,
            GateSalesStage.CLOSED_LOST,
        ],
        GateSalesStage.COMMERCIAL_PROPOSAL: [
            GateSalesStage.LEGAL_SECURITY_REVIEW,
            GateSalesStage.CLOSED_LOST,
        ],
        GateSalesStage.LEGAL_SECURITY_REVIEW: [
            GateSalesStage.CLOSED_WON,
            GateSalesStage.CLOSED_LOST,
        ],
        GateSalesStage.CLOSED_WON: [],
        GateSalesStage.CLOSED_LOST: [GateSalesStage.LEAD_DISCOVERY],
    }

    def __init__(self, tenant_id: str, opportunity_id: str) -> None:
        if not tenant_id or not opportunity_id:
            raise ValueError("tenant_id and opportunity_id must be non-empty strings.")
        self.tenant_id: str = tenant_id
        self.opportunity_id: str = opportunity_id
        self.current_stage: GateSalesStage = GateSalesStage.LEAD_DISCOVERY
        self.metadata: Dict[str, Any] = {}
        self.audit_chain: List[StateAuditBlock] = []
        self._genesis_hash: str = "0" * 64
        self._init_genesis_block()

    def _init_genesis_block(self) -> None:
        initial_state_repr = json.dumps(
            {"stage": self.current_stage.value, "opportunity_id": self.opportunity_id},
            sort_keys=True,
        )
        state_digest = hashlib.sha256(initial_state_repr.encode("utf-8")).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()
        raw_block = f"0:{self._genesis_hash}:{state_digest}:GENESIS:{timestamp}"
        block_hash = hashlib.sha256(raw_block.encode("utf-8")).hexdigest()
        genesis_block = StateAuditBlock(
            index=0,
            prev_hash=self._genesis_hash,
            state_digest=state_digest,
            event_id="GENESIS",
            timestamp_utc=timestamp,
            block_hash=block_hash,
        )
        self.audit_chain.append(genesis_block)

    def transition(self, event: GateSalesEvent) -> StateAuditBlock:
        if event.tenant_id != self.tenant_id:
            raise PermissionError(f"Access Denied: Tenant mismatch for {event.tenant_id}")

        allowed = self.ALLOWED_TRANSITIONS.get(self.current_stage, [])
        if event.target_stage not in allowed:
            raise ValueError(
                f"Invalid transition: Cannot advance from {self.current_stage.value} "
                f"to {event.target_stage.value}."
            )

        self._validate_stage_gate(event.target_stage, event.payload)

        self.current_stage = event.target_stage
        self.metadata.update(event.payload)

        prev_block = self.audit_chain[-1]
        state_repr = json.dumps(
            {
                "stage": self.current_stage.value,
                "opportunity_id": self.opportunity_id,
                "metadata": self.metadata,
            },
            sort_keys=True,
        )
        state_digest = hashlib.sha256(state_repr.encode("utf-8")).hexdigest()
        next_index = prev_block.index + 1
        raw_block = (
            f"{next_index}:{prev_block.block_hash}:{state_digest}:"
            f"{event.event_id}:{event.timestamp_utc}"
        )
        new_block_hash = hashlib.sha256(raw_block.encode("utf-8")).hexdigest()

        new_block = StateAuditBlock(
            index=next_index,
            prev_hash=prev_block.block_hash,
            state_digest=state_digest,
            event_id=event.event_id,
            timestamp_utc=event.timestamp_utc,
            block_hash=new_block_hash,
        )
        self.audit_chain.append(new_block)
        return new_block

    def _validate_stage_gate(self, target: GateSalesStage, payload: Dict[str, Any]) -> None:
        if target == GateSalesStage.QUALIFICATION_BANT:
            required_keys = {"budget", "authority", "need", "timeline"}
            missing = required_keys - set(payload.keys())
            if missing:
                raise ValueError(f"BANT qualification failed. Missing keys: {missing}")
            if not isinstance(payload["budget"], (int, float)) or payload["budget"] <= 0:
                raise ValueError("BANT qualification failed: 'budget' must be positive.")

        elif target == GateSalesStage.TECHNICAL_VALIDATION:
            if not payload.get("architecture_approved"):
                raise ValueError("Technical validation gate requires 'architecture_approved' = True.")

        elif target == GateSalesStage.COMMERCIAL_PROPOSAL:
            if not payload.get("pricing_schedule_id"):
                raise ValueError("Commercial proposal requires a valid 'pricing_schedule_id'.")

        elif target == GateSalesStage.LEGAL_SECURITY_REVIEW:
            if not payload.get("dpa_signed"):
                raise ValueError("Legal review gate requires Data Processing Agreement ('dpa_signed' = True).")

        elif target == GateSalesStage.CLOSED_WON:
            if not payload.get("contract_signature_ref"):
                raise ValueError("Closed-Won status requires valid 'contract_signature_ref'.")

    def verify_invariant(self) -> bool:
        if not self.audit_chain:
            return False

        genesis = self.audit_chain[0]
        if genesis.prev_hash != self._genesis_hash or genesis.index != 0:
            return False

        for i in range(1, len(self.audit_chain)):
            curr = self.audit_chain[i]
            prev = self.audit_chain[i - 1]

            if curr.index != prev.index + 1:
                return False
            if curr.prev_hash != prev.block_hash:
                return False

            raw_block = (
                f"{curr.index}:{prev.block_hash}:{curr.state_digest}:"
                f"{curr.event_id}:{curr.timestamp_utc}"
            )
            recomputed = hashlib.sha256(raw_block.encode("utf-8")).hexdigest()
            if curr.block_hash != recomputed:
                return False

        return True


# ==============================================================================
# JSON CRDT CONVERGENCE, MERKLE TRANSPARENCY LOG & PUBGRUB CPQ SOLVER (E2E-QA-11)
# ==============================================================================


class IntegrityViolationError(Exception):
    """Raised when cryptographic verification or CRDT causal invariants fail."""


class ConstraintResolutionError(Exception):
    """Raised when SKU pricing dependency constraints cannot be satisfied."""


@dataclass(frozen=True, order=True)
class LamportTimestamp:
    counter: int
    actor_id: str

    @property
    def node_id(self) -> str:
        return self.actor_id

    def increment(self, actor: str) -> "LamportTimestamp":
        return LamportTimestamp(counter=self.counter + 1, actor_id=actor)

    @classmethod
    def maximum(
        cls, t1: "LamportTimestamp", t2: "LamportTimestamp", actor: str
    ) -> "LamportTimestamp":
        return LamportTimestamp(counter=max(t1.counter, t2.counter) + 1, actor_id=actor)


@dataclass
class CRDTPolymorphicRegister:
    """Multi-Value Register preserving concurrent writes using deterministic tie-breaking."""

    value: Any
    timestamp: LamportTimestamp

    def merge(self, other: "CRDTPolymorphicRegister") -> "CRDTPolymorphicRegister":
        if other.timestamp > self.timestamp:
            return CRDTPolymorphicRegister(value=other.value, timestamp=other.timestamp)
        return self


class SalesQuotationCRDT:
    """
    Conflict-Free Replicated JSON Datatype tailored for Sales Quotation Documents (arXiv:1608.03960).
    Guarantees strong eventual consistency across multi-master distributed agents.
    """

    def __init__(self, document_id: str, actor_id: str) -> None:
        self.document_id: str = document_id
        self.actor_id: str = actor_id
        self.clock: LamportTimestamp = LamportTimestamp(counter=0, actor_id=actor_id)
        self.registers: Dict[str, CRDTPolymorphicRegister] = {}
        self.line_items: Dict[str, Dict[str, CRDTPolymorphicRegister]] = {}
        self.tombstones: Set[str] = set()

    def set_header_field(self, field_name: str, value: Any) -> None:
        self.clock = self.clock.increment(self.actor_id)
        self.registers[field_name] = CRDTPolymorphicRegister(value=value, timestamp=self.clock)

    def set_line_item(self, line_id: str, field_name: str, value: Any) -> None:
        if line_id in self.tombstones:
            raise IntegrityViolationError(f"Cannot mutate tombstoned line item: {line_id}")
        self.clock = self.clock.increment(self.actor_id)
        if line_id not in self.line_items:
            self.line_items[line_id] = {}
        self.line_items[line_id][field_name] = CRDTPolymorphicRegister(
            value=value, timestamp=self.clock
        )

    def remove_line_item(self, line_id: str) -> None:
        self.clock = self.clock.increment(self.actor_id)
        self.tombstones.add(line_id)
        if line_id in self.line_items:
            del self.line_items[line_id]

    def merge(self, peer: "SalesQuotationCRDT") -> None:
        """Commutative, associative, and idempotent merge operation."""
        self.clock = LamportTimestamp.maximum(self.clock, peer.clock, self.actor_id)

        for k, peer_reg in peer.registers.items():
            if k in self.registers:
                self.registers[k] = self.registers[k].merge(peer_reg)
            else:
                self.registers[k] = CRDTPolymorphicRegister(
                    value=peer_reg.value, timestamp=peer_reg.timestamp
                )

        self.tombstones.update(peer.tombstones)

        for lid in list(self.line_items.keys()):
            if lid in self.tombstones:
                del self.line_items[lid]

        for line_id, peer_fields in peer.line_items.items():
            if line_id in self.tombstones:
                continue
            if line_id not in self.line_items:
                self.line_items[line_id] = {}
            for field_name, peer_reg in peer_fields.items():
                if field_name in self.line_items[line_id]:
                    self.line_items[line_id][field_name] = self.line_items[line_id][
                        field_name
                    ].merge(peer_reg)
                else:
                    self.line_items[line_id][field_name] = CRDTPolymorphicRegister(
                        value=peer_reg.value, timestamp=peer_reg.timestamp
                    )

    def to_canonical_dict(self) -> Dict[str, Any]:
        header = {k: reg.value for k, reg in sorted(self.registers.items())}
        lines = {}
        for line_id, fields in sorted(self.line_items.items()):
            if line_id not in self.tombstones:
                lines[line_id] = {k: reg.value for k, reg in sorted(fields.items())}
        return {
            "document_id": self.document_id,
            "clock": {"counter": self.clock.counter, "actor_id": self.clock.actor_id},
            "header": header,
            "line_items": lines,
            "tombstones": sorted(list(self.tombstones)),
        }


class MerkleTransparencyLog:
    """
    Append-only Merkle Tree for Enterprise Sales Protocol Transparency (arXiv:2303.04500).
    Enforces tamper-evident logging of quotation approval events.
    """

    def __init__(self) -> None:
        self.entries: List[bytes] = []
        self.tree_levels: List[List[str]] = []

    @staticmethod
    def sha256_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def record_approval_event(self, event_data: Dict[str, Any]) -> Tuple[int, str]:
        canonical_bytes = json.dumps(event_data, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        leaf_hash = self.sha256_hash(canonical_bytes)
        self.entries.append(canonical_bytes)
        self._recompute_tree()
        leaf_index = len(self.entries) - 1
        return leaf_index, leaf_hash

    def _recompute_tree(self) -> None:
        current_level: List[str] = [self.sha256_hash(entry) for entry in self.entries]
        self.tree_levels = [current_level]
        while len(current_level) > 1:
            next_level: List[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
                next_level.append(combined)
            current_level = next_level
            self.tree_levels.append(current_level)

    def get_root_hash(self) -> str:
        if not self.tree_levels or not self.tree_levels[-1]:
            return self.sha256_hash(b"")
        return self.tree_levels[-1][0]

    def generate_inclusion_proof(self, index: int) -> List[Tuple[str, str]]:
        if index < 0 or index >= len(self.entries):
            raise IntegrityViolationError(
                f"Index {index} out of tree bounds [0, {len(self.entries)})"
            )

        proof: List[Tuple[str, str]] = []
        idx = index
        for level in self.tree_levels[:-1]:
            if idx % 2 == 0:
                sibling_idx = idx + 1 if idx + 1 < len(level) else idx
                proof.append((level[sibling_idx], "right"))
            else:
                sibling_idx = idx - 1
                proof.append((level[sibling_idx], "left"))
            idx //= 2
        return proof

    @classmethod
    def verify_inclusion_proof(
        cls, leaf_hash: str, proof: List[Tuple[str, str]], expected_root: str
    ) -> bool:
        current = leaf_hash
        for sibling, direction in proof:
            if direction in ("right", "R"):
                current = hashlib.sha256((current + sibling).encode("utf-8")).hexdigest()
            elif direction in ("left", "L"):
                current = hashlib.sha256((sibling + current).encode("utf-8")).hexdigest()
            else:
                raise IntegrityViolationError(f"Invalid proof direction: {direction}")
        return current == expected_root

    def append_event(self, state_hash: str) -> int:
        """Appends a new state hash leaf and updates the Merkle tree."""
        self.entries.append(state_hash.encode("utf-8"))
        self._recompute_tree()
        return len(self.entries) - 1

    def get_root(self) -> str:
        return self.get_root_hash()

    def get_inclusion_proof(self, leaf_index: int) -> List[Tuple[str, str]]:
        if leaf_index < 0 or leaf_index >= len(self.entries):
            raise IndexError("Leaf index out of bounds")
        raw_proof = self.generate_inclusion_proof(leaf_index)
        return [(sib, "L" if d == "left" else "R") for sib, d in raw_proof]

    @classmethod
    def verify_inclusion(
        cls, leaf_hash: str, proof: List[Tuple[str, str]], expected_root: str
    ) -> bool:
        return cls.verify_inclusion_proof(leaf_hash, proof, expected_root)

    def append_entry(self, entry: Dict[str, Any]) -> Tuple[int, str]:
        return self.record_approval_event(entry)



class PubGrubQuotationSolver:
    """
    Deterministic dependency and constraint solver for CPQ bundles (astral-sh/uv inspired).
    Ensures mutually exclusive enterprise discount packages and prerequisite SKUs resolve safely.
    """

    def __init__(self) -> None:
        self.dependencies: Dict[str, List[str]] = {}
        self.incompatibilities: Dict[str, Set[str]] = {}

    def register_dependency(self, target_sku: str, required_sku: str) -> None:
        if target_sku not in self.dependencies:
            self.dependencies[target_sku] = []
        self.dependencies[target_sku].append(required_sku)

    def register_incompatibility(self, sku_a: str, sku_b: str) -> None:
        if sku_a not in self.incompatibilities:
            self.incompatibilities[sku_a] = set()
        if sku_b not in self.incompatibilities:
            self.incompatibilities[sku_b] = set()
        self.incompatibilities[sku_a].add(sku_b)
        self.incompatibilities[sku_b].add(sku_a)

    def solve_bundle(self, requested_skus: List[str]) -> List[str]:
        resolved: Set[str] = set()
        to_process: List[str] = list(requested_skus)

        while to_process:
            current = to_process.pop(0)
            if current in resolved:
                continue

            conflicts = self.incompatibilities.get(current, set()).intersection(resolved)
            if conflicts:
                raise ConstraintResolutionError(
                    f"SKU conflict detected: '{current}' is mutually incompatible with '{sorted(list(conflicts))}'"
                )

            resolved.add(current)
            for req in self.dependencies.get(current, []):
                if req not in resolved:
                    to_process.append(req)

        return sorted(list(resolved))


# ==============================================================================
# AVIATION PRE-FLIGHT ENVELOPE PROTECTION & TWO-CHALLENGE CIRCUIT BREAKER (E2E-QA-11)
# ==============================================================================


class EnvelopeBreachError(Exception):
    """Raised when an agent quotation breaches hard flight-envelope margins."""


class TwoChallengeLockoutError(Exception):
    """Raised when consecutive envelope challenges trip the safety circuit breaker."""


class MerkleTreeIntegrity:
    """Automated transparency verification engine based on arXiv:2303.04500."""

    @staticmethod
    def hash_leaf(data: Dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_root(leaves: List[str]) -> str:
        if not leaves:
            return hashlib.sha256(b"").hexdigest()
        current_layer = list(leaves)
        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                left = current_layer[i]
                right = current_layer[i + 1] if i + 1 < len(current_layer) else left
                parent = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
                next_layer.append(parent)
            current_layer = next_layer
        return current_layer[0]


class CrdtJsonRegister:
    """
    Conflict-Free Replicated JSON Register based on arXiv:1608.03960.
    Enforces deterministic Last-Write-Wins (LWW) via Lamport logical timestamps.
    """

    def __init__(self, key: str, initial_value: Any, timestamp: int, author: str):
        self.key = key
        self.value = initial_value
        self.timestamp = timestamp
        self.author = author

    def update(self, new_value: Any, timestamp: int, author: str) -> bool:
        if timestamp > self.timestamp:
            self.value = new_value
            self.timestamp = timestamp
            self.author = author
            return True
        if timestamp == self.timestamp and author > self.author:
            self.value = new_value
            self.timestamp = timestamp
            self.author = author
            return True
        return False


class AviationPreFlightChecklistGate:
    """
    Aviation-inspired Pre-Flight Envelope Protection and CRM Two-Challenge Rule.
    Enforces financial margin limits, tenant partitioning, and cryptographic logging.
    """

    MIN_PROFIT_MARGIN_RATIO = 0.185

    def __init__(self, tenant_id: str, flag_enabled: bool = True):
        self.tenant_id = tenant_id
        self.flag_enabled = flag_enabled
        self.consecutive_challenge_failures = 0
        self.audit_log: List[Dict[str, Any]] = []

    def evaluate_preflight_envelope(
        self,
        quote_id: str,
        total_revenue: float,
        cost_basis: float,
        line_items: List[Dict[str, Any]],
        company_id: str,
    ) -> Dict[str, Any]:
        if not self.flag_enabled:
            return {"status": "BYPASS", "reason": "PREFLIGHT_FLAG_DISABLED"}

        if self.consecutive_challenge_failures >= 2:
            raise TwoChallengeLockoutError(
                f"Quote {quote_id} locked out: 2 consecutive flight-envelope challenges tripped."
            )

        if company_id != self.tenant_id:
            self.consecutive_challenge_failures += 1
            raise InvariantViolationError(
                f"Tenant Isolation Breach: Request company_id {company_id} != tenant {self.tenant_id}"
            )

        if total_revenue <= 0.0:
            self.consecutive_challenge_failures += 1
            raise EnvelopeBreachError("Negative or zero revenue quote rejected by envelope laws.")

        margin_ratio = (total_revenue - cost_basis) / total_revenue
        if margin_ratio < self.MIN_PROFIT_MARGIN_RATIO:
            self.consecutive_challenge_failures += 1
            raise EnvelopeBreachError(
                f"Margin breach: Computed {margin_ratio:.4f} < Hard Floor {self.MIN_PROFIT_MARGIN_RATIO:.4f}"
            )

        if not line_items:
            self.consecutive_challenge_failures += 1
            raise InvariantViolationError("Quote contains zero line items.")

        self.consecutive_challenge_failures = 0
        event_record = {
            "quote_id": quote_id,
            "tenant_id": self.tenant_id,
            "margin_ratio": round(margin_ratio, 6),
            "timestamp": int(time.time()),
            "status": "CLEARED",
        }
        self.audit_log.append(event_record)
        return {"status": "CLEARED", "margin_ratio": margin_ratio, "record": event_record}


# ==============================================================================
# STATEFUL CRDT-PREFECT ORCHESTRATION ENGINE (SCPOE) & MERKLE CHAINS (E2E-QA-11)
# ==============================================================================


@dataclass
class CRDTSalesItem:
    item_id: str
    product_code: str
    unit_price: float
    quantity: int
    discount_pct: float
    timestamp: float
    actor_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "product_code": self.product_code,
            "unit_price": self.unit_price,
            "quantity": self.quantity,
            "discount_pct": self.discount_pct,
            "timestamp": self.timestamp,
            "actor_id": self.actor_id,
        }


class JSONCRDTSalesDoc:
    """
    State-based Last-Write-Wins (LWW) and Observed-Remove CRDT for sales quote items.
    Guarantees strong eventual consistency under arbitrary message reordering.
    """

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self._items: Dict[str, CRDTSalesItem] = {}
        self._tombstones: Dict[str, float] = {}

    def set_item(
        self,
        item_id: str,
        product_code: str,
        unit_price: float,
        quantity: int,
        discount_pct: float,
        actor_id: str,
        timestamp: Optional[float] = None,
    ) -> None:
        ts = timestamp if timestamp is not None else time.time()
        if item_id in self._tombstones and self._tombstones[item_id] >= ts:
            return
        if item_id in self._items and self._items[item_id].timestamp >= ts:
            return

        self._items[item_id] = CRDTSalesItem(
            item_id=item_id,
            product_code=product_code,
            unit_price=unit_price,
            quantity=quantity,
            discount_pct=discount_pct,
            timestamp=ts,
            actor_id=actor_id,
        )

    def remove_item(self, item_id: str, actor_id: str, timestamp: Optional[float] = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        if item_id in self._items and self._items[item_id].timestamp <= ts:
            del self._items[item_id]
        if self._tombstones.get(item_id, 0.0) < ts:
            self._tombstones[item_id] = ts

    def merge(self, other: "JSONCRDTSalesDoc") -> "JSONCRDTSalesDoc":
        merged = JSONCRDTSalesDoc(self.doc_id)

        all_tomb_keys = set(self._tombstones.keys()).union(other._tombstones.keys())
        for k in all_tomb_keys:
            merged._tombstones[k] = max(
                self._tombstones.get(k, 0.0),
                other._tombstones.get(k, 0.0),
            )

        all_item_keys = set(self._items.keys()).union(other._items.keys())
        for k in all_item_keys:
            tomb_ts = merged._tombstones.get(k, -1.0)
            item_self = self._items.get(k)
            item_other = other._items.get(k)

            candidate: Optional[CRDTSalesItem] = None
            if item_self and item_other:
                if item_self.timestamp > item_other.timestamp:
                    candidate = item_self
                elif item_other.timestamp > item_self.timestamp:
                    candidate = item_other
                else:
                    candidate = (
                        item_self if item_self.actor_id >= item_other.actor_id else item_other
                    )
            elif item_self:
                candidate = item_self
            elif item_other:
                candidate = item_other

            if candidate and candidate.timestamp > tomb_ts:
                merged._items[k] = candidate

        return merged

    def compute_total(self) -> float:
        total = 0.0
        for item in self._items.values():
            subtotal = item.unit_price * item.quantity
            net = subtotal * (1.0 - (item.discount_pct / 100.0))
            total += net
        return round(total, 2)


class MerkleTransparencyTree:
    """
    Append-only Merkle tree providing formal audit trail verification
    for high-stakes quote and discount approvals.
    """

    def __init__(self):
        self.leaves: List[str] = []
        self._levels: List[List[str]] = []

    @staticmethod
    def _hash(data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def append_entry(self, entry: Dict[str, Any]) -> str:
        canonical_json = json.dumps(entry, sort_keys=True)
        leaf_hash = self._hash(canonical_json)
        self.leaves.append(leaf_hash)
        self._rebuild_tree()
        return leaf_hash

    def _rebuild_tree(self) -> None:
        if not self.leaves:
            self._levels = []
            return

        current_level = list(self.leaves)
        self._levels = [current_level]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = self._hash(left + right)
                next_level.append(combined)
            current_level = next_level
            self._levels.append(current_level)

    def get_root(self) -> str:
        if not self._levels or not self._levels[-1]:
            return self._hash("")
        return self._levels[-1][0]

    def get_audit_proof(self, leaf_index: int) -> List[Tuple[str, str]]:
        if leaf_index < 0 or leaf_index >= len(self.leaves):
            raise IndexError("Leaf index out of bounds")

        proof: List[Tuple[str, str]] = []
        idx = leaf_index

        for level in self._levels[:-1]:
            is_right_child = idx % 2 == 1
            sibling_idx = idx - 1 if is_right_child else idx + 1
            sibling_hash = level[sibling_idx] if sibling_idx < len(level) else level[idx]
            direction = "left" if is_right_child else "right"
            proof.append((sibling_hash, direction))
            idx = idx // 2

        return proof

    @classmethod
    def verify_proof(cls, leaf_hash: str, proof: List[Tuple[str, str]], expected_root: str) -> bool:
        current = leaf_hash
        for sibling_hash, direction in proof:
            if direction == "left":
                current = cls._hash(sibling_hash + current)
            else:
                current = cls._hash(current + sibling_hash)
        return current == expected_root


@dataclass
class OdooContext:
    active_company_id: int
    allowed_company_ids: List[int]
    user_id: int


class OdooModelRegistry:
    """Simulates Odoo dynamic model inheritance and record-rule security filters."""

    def __init__(self):
        self._records: Dict[str, List[Dict[str, Any]]] = {}

    def register_record(self, model_name: str, record: Dict[str, Any]) -> None:
        if model_name not in self._records:
            self._records[model_name] = []
        self._records[model_name].append(record)

    def search_records(
        self,
        model_name: str,
        domain: List[Tuple[str, str, Any]],
        context: OdooContext,
    ) -> List[Dict[str, Any]]:
        raw_list = self._records.get(model_name, [])
        filtered = []

        for rec in raw_list:
            rec_comp = rec.get("company_id")
            if rec_comp is not None and rec_comp not in context.allowed_company_ids:
                continue

            match = True
            for field_name, op, val in domain:
                rec_val = rec.get(field_name)
                if op == "=" and rec_val != val:
                    match = False
                    break
                if op == ">" and not (rec_val is not None and rec_val > val):
                    match = False
                    break
                if op == "in" and rec_val not in val:
                    match = False
                    break
            if match:
                filtered.append(rec)

        return filtered


class TaskState(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


@dataclass
class PrefectTaskResult:
    task_name: str
    state: TaskState
    return_value: Any
    retry_count: int
    error_message: Optional[str] = None


class PrefectSalesFlowRunner:
    """Executes DAG tasks with state-machine tracking, failure backoff, and caching."""

    def __init__(self):
        self.memoized_cache: Dict[str, Any] = {}

    def execute_task(
        self,
        name: str,
        fn: Callable[..., Any],
        args: Tuple[Any, ...],
        max_retries: int = 2,
    ) -> PrefectTaskResult:
        cache_key = hashlib.sha256(f"{name}:{json.dumps(args, default=str)}".encode()).hexdigest()
        if cache_key in self.memoized_cache:
            return PrefectTaskResult(
                task_name=name,
                state=TaskState.COMPLETED,
                return_value=self.memoized_cache[cache_key],
                retry_count=0,
            )

        attempts = 0
        last_error = None

        while attempts <= max_retries:
            try:
                val = fn(*args)
                self.memoized_cache[cache_key] = val
                return PrefectTaskResult(
                    task_name=name,
                    state=TaskState.COMPLETED,
                    return_value=val,
                    retry_count=attempts,
                )
            except Exception as exc:
                last_error = str(exc)
                attempts += 1

        return PrefectTaskResult(
            task_name=name,
            state=TaskState.FAILED,
            return_value=None,
            retry_count=attempts - 1,
            error_message=last_error,
        )


# ==============================================================================
# AXIOMATIC TRANSPARENCY LOGS & MERKLE PROOF ENCLAVES FOR AI DISCRETION (E2E-QA-11)
# ==============================================================================


class AxiomaticDiscretionEnclave:
    """
    Axiomatic Transparency Log & Merkle Proof Enclave for AI Sales Discretion.
    Provides commutative JSON delta merging (arXiv:1608.03960), Merkle proof
    enclave attestation (arXiv:2303.04500), and tenant/version bound checks.
    """

    def __init__(self, company_id: int) -> None:
        self.company_id = company_id
        self.leaves: List[str] = []

    @staticmethod
    def apply_commutative_delta(base: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        merged = json.loads(json.dumps(base))
        base_ver = int(merged.get("version", 0))
        delta_ver = int(delta.get("version", base_ver))
        base_actor = str(merged.get("actor", ""))
        delta_actor = str(delta.get("actor", ""))

        for k, v in delta.items():
            if k in ("version", "actor"):
                continue
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = AxiomaticDiscretionEnclave.apply_commutative_delta(merged[k], v)
            else:
                merged[k] = v

        if (delta_ver, delta_actor) >= (base_ver, base_actor):
            if "version" in delta:
                merged["version"] = delta_ver
            if "actor" in delta:
                merged["actor"] = delta_actor
        return merged

    @staticmethod
    def hash_node(left: str, right: str) -> str:
        return hashlib.sha256(f"{left}:{right}".encode("utf-8")).hexdigest()

    def record_discretionary_concession(self, action_tag: str) -> str:
        leaf = hashlib.sha256(action_tag.encode("utf-8")).hexdigest()
        self.leaves.append(leaf)
        return leaf

    def compute_merkle_root(self) -> str:
        if not self.leaves:
            return hashlib.sha256(b"").hexdigest()
        layer = list(self.leaves)
        while len(layer) > 1:
            next_layer: List[str] = []
            for i in range(0, len(layer), 2):
                left = layer[i]
                right = layer[i + 1] if i + 1 < len(layer) else left
                next_layer.append(self.hash_node(left, right))
            layer = next_layer
        return layer[0]

    def evaluate_quote_approval(
        self, record: Dict[str, Any], max_auto_approve_amount: float = 100000.0
    ) -> Dict[str, Any]:
        if record.get("company_id") != self.company_id:
            raise PermissionError("Multi-company isolation breach")
        updated = dict(record)
        updated["approved"] = float(updated.get("quote_amount", 0.0)) < max_auto_approve_amount
        return updated


# ==============================================================================
# MERKLE-CRDT SALES LEDGER WITH DOUBLE-RATCHET STATE ATTESTATION (E2E-QA-11)
# ==============================================================================


@dataclass(frozen=True)
class CRDTOperation:
    op_id: str
    tenant_id: str
    lead_id: str
    field_name: str
    value: Any
    lamport_timestamp: int
    actor_id: str


class MerkleAuditNode:
    def __init__(self, op_hash: str, prev_root: str):
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self.op_hash: str = op_hash
        self.prev_root: str = prev_root
        combined = f"{op_hash}:{prev_root}:{self.timestamp}".encode("utf-8")
        self.root_hash: str = hashlib.sha256(combined).hexdigest()


class ReplicatedSalesLeadCRDT:
    """
    Operation-based CRDT State Machine with Causal LWW-Element-Register
    semantics for multi-master sales negotiations (arXiv:1608.03960) and
    Merkle transparency chain attestation (arXiv:2303.04500).
    """

    def __init__(self, lead_id: str, tenant_id: str):
        self.lead_id: str = lead_id
        self.tenant_id: str = tenant_id
        self._registers: Dict[str, Tuple[Any, int, str, str]] = {}
        self._audit_trail: List[MerkleAuditNode] = []
        self._current_root: str = "GENESIS_ROOT_00000000000000000000000000000000"

    def apply_operation(self, op: CRDTOperation) -> str:
        if op.tenant_id != self.tenant_id:
            raise TenantSecurityError(
                f"Tenant mismatch: op tenant {op.tenant_id} != instance tenant {self.tenant_id}"
            )
        if op.lead_id != self.lead_id:
            raise InvariantViolationError(
                f"Lead mismatch: op lead {op.lead_id} != instance lead {self.lead_id}"
            )

        current = self._registers.get(op.field_name)
        should_update = False

        if current is None:
            should_update = True
        else:
            _, cur_timestamp, cur_actor, _ = current
            if op.lamport_timestamp > cur_timestamp:
                should_update = True
            elif op.lamport_timestamp == cur_timestamp and op.actor_id > cur_actor:
                should_update = True

        if should_update:
            self._registers[op.field_name] = (
                op.value,
                op.lamport_timestamp,
                op.actor_id,
                op.op_id,
            )

        canonical_payload = json.dumps(
            {
                "op_id": op.op_id,
                "tenant_id": op.tenant_id,
                "lead_id": op.lead_id,
                "field_name": op.field_name,
                "value": op.value,
                "lamport_timestamp": op.lamport_timestamp,
                "actor_id": op.actor_id,
            },
            sort_keys=True,
        ).encode("utf-8")
        op_hash = hashlib.sha256(canonical_payload).hexdigest()

        node = MerkleAuditNode(op_hash=op_hash, prev_root=self._current_root)
        self._audit_trail.append(node)
        self._current_root = node.root_hash
        return self._current_root

    def get_state(self) -> Dict[str, Any]:
        return {k: v[0] for k, v in self._registers.items()}

    def verify_transparency_chain(self) -> bool:
        if not self._audit_trail:
            return True

        expected_prev = "GENESIS_ROOT_00000000000000000000000000000000"
        for node in self._audit_trail:
            if node.prev_root != expected_prev:
                return False
            expected_combined = f"{node.op_hash}:{node.prev_root}:{node.timestamp}".encode("utf-8")
            recomputed_root = hashlib.sha256(expected_combined).hexdigest()
            if node.root_hash != recomputed_root:
                return False
            expected_prev = node.root_hash
        return True


# ==============================================================================
# DELTA-CRDT MERKLE FABRIC & PUBGRUB QUOTE CONSTRAINT ENGINE (E2E-QA-11)
# ==============================================================================


class CRDTRegister:
    """Multi-Value Register with Last-Write-Wins and Replica ID tie-breaking."""

    def __init__(
        self,
        value: Any = None,
        timestamp: float = 0,
        replica_id: str = "",
        *,
        actor_id: Optional[str] = None,
    ) -> None:
        self.value = value
        self.timestamp = timestamp
        self.replica_id = actor_id if actor_id is not None else replica_id

    @property
    def actor_id(self) -> str:
        return self.replica_id

    def update(self, value: Any, timestamp: float, replica_id: str) -> bool:
        if (timestamp, replica_id) > (self.timestamp, self.replica_id):
            self.value = value
            self.timestamp = timestamp
            self.replica_id = replica_id
            return True
        return False

    def merge(self, other: "CRDTRegister") -> "CRDTRegister":
        if (other.timestamp, other.replica_id) > (self.timestamp, self.replica_id):
            return CRDTRegister(other.value, other.timestamp, other.replica_id)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "replica_id": self.replica_id,
        }


class DeltaCRDTJsonObject:
    """
    Conflict-Free Replicated JSON Document for concurrent sales quoting.
    Guarantees strong eventual convergence across distributed AI and human agents.
    """

    def __init__(self, replica_id: str) -> None:
        self.replica_id = replica_id
        self.clock: int = 0
        self._registers: Dict[str, CRDTRegister] = {}
        self._nested_maps: Dict[str, "DeltaCRDTJsonObject"] = {}

    def _tick(self) -> float:
        self.clock += 1
        return time.time() + (self.clock * 0.0001)

    def set_field(self, key: str, value: Any) -> Dict[str, Any]:
        ts = self._tick()
        if key not in self._registers:
            self._registers[key] = CRDTRegister(value, ts, self.replica_id)
        else:
            self._registers[key].update(value, ts, self.replica_id)
        return {
            "op": "set",
            "key": key,
            "value": value,
            "timestamp": ts,
            "clock": self.clock,
            "replica_id": self.replica_id,
        }

    def apply_delta(self, delta: Dict[str, Any]) -> bool:
        op = delta.get("op")
        key = delta.get("key")
        value = delta.get("value")
        ts = delta.get("timestamp")
        rep = delta.get("replica_id")

        if not all([op == "set", key, ts, rep]):
            raise ValueError(f"Malformed delta payload: {delta}")

        incoming_clock = int(delta.get("clock", 0))
        if incoming_clock > self.clock:
            self.clock = incoming_clock

        if key not in self._registers:
            self._registers[key] = CRDTRegister(value, ts, rep)
            return True
        return self._registers[key].update(value, ts, rep)

    def read_document(self) -> Dict[str, Any]:
        return {k: reg.value for k, reg in self._registers.items()}

    def compute_state_hash(self) -> str:
        doc = self.read_document()
        serialized = json.dumps(doc, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class TransparencyMerkleLog:
    """
    Append-only Merkle Audit Tree verifying AI sales quotation transparency.
    Provides mathematical non-repudiation for pricing overrides and terms.
    """

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []
        self.leaf_hashes: List[str] = []

    @staticmethod
    def hash_leaf(data: Dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(b"\x00" + serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_internal(left: str, right: str) -> str:
        combined = b"\x01" + bytes.fromhex(left) + bytes.fromhex(right)
        return hashlib.sha256(combined).hexdigest()

    def append_decision(
        self, actor: str, action: str, details: Dict[str, Any]
    ) -> Tuple[int, str]:
        entry = {
            "index": len(self.entries),
            "timestamp": time.time(),
            "actor": actor,
            "action": action,
            "details": details,
        }
        leaf_hash = self.hash_leaf(entry)
        self.entries.append(entry)
        self.leaf_hashes.append(leaf_hash)
        current_root = self.get_merkle_root()
        return entry["index"], current_root

    def get_merkle_root(self) -> str:
        if not self.leaf_hashes:
            return hashlib.sha256(b"EMPTY_TREE").hexdigest()

        nodes = list(self.leaf_hashes)
        while len(nodes) > 1:
            next_level: List[str] = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    next_level.append(self.hash_internal(nodes[i], nodes[i + 1]))
                else:
                    next_level.append(nodes[i])
            nodes = next_level
        return nodes[0]

    def generate_inclusion_proof(self, index: int) -> List[Tuple[str, str]]:
        if index < 0 or index >= len(self.leaf_hashes):
            raise IndexError("Log index out of range for inclusion proof.")

        proof: List[Tuple[str, str]] = []
        nodes = list(self.leaf_hashes)
        curr_idx = index

        while len(nodes) > 1:
            next_level: List[str] = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    left = nodes[i]
                    right = nodes[i + 1]
                    parent = self.hash_internal(left, right)
                    next_level.append(parent)

                    if i == curr_idx:
                        proof.append(("right", right))
                    elif i + 1 == curr_idx:
                        proof.append(("left", left))
                else:
                    next_level.append(nodes[i])
            curr_idx //= 2
            nodes = next_level

        return proof

    @classmethod
    def verify_inclusion_proof(
        cls, leaf_data: Dict[str, Any], proof: List[Tuple[str, str]], expected_root: str
    ) -> bool:
        current_hash = cls.hash_leaf(leaf_data)
        for direction, sibling_hash in proof:
            if direction == "right":
                current_hash = cls.hash_internal(current_hash, sibling_hash)
            elif direction == "left":
                current_hash = cls.hash_internal(sibling_hash, current_hash)
            else:
                return False
        return current_hash == expected_root


class OdooTenantSecurityContext:
    """Enforces row-level security and company domain rules across sales quotes."""

    def __init__(
        self,
        user_id: str,
        company_id: int,
        allowed_company_ids: Set[int],
        is_admin: bool = False,
    ):
        self.user_id = user_id
        self.company_id = company_id
        self.allowed_company_ids = set(allowed_company_ids)
        self.is_admin = is_admin

    def evaluate_record_rule(self, record: Dict[str, Any]) -> bool:
        if self.is_admin:
            return True
        record_company_id = record.get("company_id")
        if record_company_id is None:
            return False
        return record_company_id in self.allowed_company_ids


class PubGrubQuoteConstraintEngine:
    """
    Evaluates enterprise quote line item bundles and discount policies
    using a deterministic constraint satisfiability solver.
    """

    def __init__(self) -> None:
        self.incompatibility_matrix: List[Tuple[str, str, str]] = []

    def register_incompatibility(self, sku_a: str, sku_b: str, reason: str) -> None:
        self.incompatibility_matrix.append((sku_a, sku_b, reason))

    def validate_quote(
        self, skus: List[str], discount_percent: float, is_executive: bool
    ) -> Tuple[bool, Optional[str]]:
        sku_set = set(skus)
        for a, b, reason in self.incompatibility_matrix:
            if a in sku_set and b in sku_set:
                return False, f"Conflict between {a} and {b}: {reason}"

        if discount_percent > 20.0 and not is_executive:
            return False, "Discounts exceeding 20.0% require Executive approval."

        if discount_percent < 0.0 or discount_percent > 100.0:
            return False, "Discount percentage must be within [0.0, 100.0]."

        return True, None


class HarnessVerificationError(Exception):
    """Base exception for E2E Sales Harness verification failures."""


class CRDTConvergenceError(HarnessVerificationError):
    """Raised when CRDT replicas fail to converge to a deterministic state."""


class MerkleIntegrityError(HarnessVerificationError):
    """Raised when audit log Merkle proof verification detects tampering."""


class TenantIsolationError(HarnessVerificationError):
    """Raised when an operation violates multi-tenant company_id security rules."""


class DependencyResolutionError(HarnessVerificationError):
    """Raised when PubGrub solver detects unsatisfiable package constraints."""


@dataclass(frozen=True)
class ZceseSalesLineItem:
    item_id: str
    product_name: str
    quantity: int
    unit_price: float
    timestamp: LamportTimestamp
    deleted: bool = False


class SalesOrderCRDTDocument:
    """
    A JSON CRDT representing an Enterprise Sales Order / Quotation (arXiv:1608.03960).
    Supports concurrent edits to line items, discounts, and stage transitions
    with guaranteed strong eventual consistency across distributed replicas.
    """

    def __init__(self, order_id: str, actor_id: str, company_id: int) -> None:
        self.order_id = order_id
        self.actor_id = actor_id
        self.company_id = company_id
        self.logical_clock = 0
        self.line_items: Dict[str, ZceseSalesLineItem] = {}
        self.discount_percent: Tuple[float, LamportTimestamp] = (
            0.0,
            LamportTimestamp(0, ""),
        )
        self.stage: Tuple[str, LamportTimestamp] = (
            "draft",
            LamportTimestamp(0, ""),
        )

    def _tick(self) -> LamportTimestamp:
        self.logical_clock += 1
        return LamportTimestamp(self.logical_clock, self.actor_id)

    def set_line_item(
        self, item_id: str, product_name: str, quantity: int, unit_price: float
    ) -> None:
        if quantity < 0 or unit_price < 0:
            raise ValueError("Quantity and unit price must be non-negative.")
        ts = self._tick()
        new_item = ZceseSalesLineItem(
            item_id=item_id,
            product_name=product_name,
            quantity=quantity,
            unit_price=unit_price,
            timestamp=ts,
            deleted=False,
        )
        self._apply_line_item(new_item)

    def remove_line_item(self, item_id: str) -> None:
        if item_id in self.line_items:
            existing = self.line_items[item_id]
            ts = self._tick()
            tombstone = ZceseSalesLineItem(
                item_id=item_id,
                product_name=existing.product_name,
                quantity=0,
                unit_price=existing.unit_price,
                timestamp=ts,
                deleted=True,
            )
            self._apply_line_item(tombstone)

    def _apply_line_item(self, item: ZceseSalesLineItem) -> None:
        self.logical_clock = max(self.logical_clock, item.timestamp.counter)
        current = self.line_items.get(item.item_id)
        if current is None or item.timestamp > current.timestamp:
            self.line_items[item.item_id] = item

    def set_discount(self, discount: float) -> None:
        if not (0.0 <= discount <= 100.0):
            raise ValueError("Discount must be between 0 and 100.")
        ts = self._tick()
        if ts > self.discount_percent[1]:
            self.discount_percent = (discount, ts)

    def transition_stage(self, new_stage: str) -> None:
        ts = self._tick()
        if ts > self.stage[1]:
            self.stage = (new_stage, ts)

    def merge(self, other: "SalesOrderCRDTDocument") -> None:
        """Idempotent, commutative, and associative state merge across replicas."""
        if self.order_id != other.order_id:
            raise CRDTConvergenceError("Cannot merge CRDT documents with different order_ids.")
        if self.company_id != other.company_id:
            raise TenantIsolationError("Cross-tenant CRDT merge is strictly prohibited.")

        self.logical_clock = max(self.logical_clock, other.logical_clock)

        for item in other.line_items.values():
            self._apply_line_item(item)

        if other.discount_percent[1] > self.discount_percent[1]:
            self.discount_percent = other.discount_percent

        if other.stage[1] > self.stage[1]:
            self.stage = other.stage

    def compute_total(self) -> float:
        subtotal = sum(
            item.quantity * item.unit_price
            for item in self.line_items.values()
            if not item.deleted
        )
        discount_factor = (100.0 - self.discount_percent[0]) / 100.0
        return round(subtotal * discount_factor, 2)

    def export_canonical_state(self) -> Dict[str, Any]:
        active_items = {
            k: {
                "product": v.product_name,
                "qty": v.quantity,
                "price": v.unit_price,
                "ts": (v.timestamp.counter, v.timestamp.actor_id),
            }
            for k, v in sorted(self.line_items.items())
            if not v.deleted
        }
        return {
            "order_id": self.order_id,
            "company_id": self.company_id,
            "stage": self.stage[0],
            "discount_percent": self.discount_percent[0],
            "total": self.compute_total(),
            "items": active_items,
        }


class SalesAuditMerkleTree:
    """
    Append-only cryptographic transparency log for sales workflow state transitions (arXiv:2107.05259).
    Uses RFC 6962 domain separation prefixes (0x00 for leaves, 0x01 for internal nodes).
    """

    def __init__(self) -> None:
        self.leaves: List[bytes] = []
        self.events: List[Dict[str, Any]] = []

    @staticmethod
    def _hash_leaf(data: bytes) -> bytes:
        return hashlib.sha256(b"\x00" + data).digest()

    @staticmethod
    def _hash_nodes(left: bytes, right: bytes) -> bytes:
        return hashlib.sha256(b"\x01" + left + right).digest()

    def append_event(self, event: Dict[str, Any]) -> int:
        canonical_bytes = json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
        leaf_hash = self._hash_leaf(canonical_bytes)
        self.events.append(event)
        self.leaves.append(leaf_hash)
        return len(self.leaves) - 1

    def get_root_hash(self) -> str:
        if not self.leaves:
            return hashlib.sha256(b"").hexdigest()
        return self._compute_root(self.leaves).hex()

    def _compute_root(self, nodes: List[bytes]) -> bytes:
        if len(nodes) == 1:
            return nodes[0]
        next_level: List[bytes] = []
        for i in range(0, len(nodes), 2):
            if i + 1 < len(nodes):
                next_level.append(self._hash_nodes(nodes[i], nodes[i + 1]))
            else:
                next_level.append(nodes[i])
        return self._compute_root(next_level)

    def generate_inclusion_proof(self, index: int) -> List[Tuple[str, str]]:
        if index < 0 or index >= len(self.leaves):
            raise IndexError("Leaf index out of bounds.")
        proof: List[Tuple[str, str]] = []
        nodes = list(self.leaves)
        curr_idx = index

        while len(nodes) > 1:
            next_level: List[bytes] = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    if i == curr_idx:
                        proof.append(("right", nodes[i + 1].hex()))
                        curr_idx = len(next_level)
                    elif i + 1 == curr_idx:
                        proof.append(("left", nodes[i].hex()))
                        curr_idx = len(next_level)
                    next_level.append(self._hash_nodes(nodes[i], nodes[i + 1]))
                else:
                    if i == curr_idx:
                        curr_idx = len(next_level)
                    next_level.append(nodes[i])
            nodes = next_level
        return proof

    @classmethod
    def verify_inclusion_proof(
        cls, event: Dict[str, Any], proof: List[Tuple[str, str]], expected_root_hex: str
    ) -> bool:
        canonical_bytes = json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
        curr_hash = cls._hash_leaf(canonical_bytes)
        for direction, sibling_hex in proof:
            sibling = bytes.fromhex(sibling_hex)
            if direction == "right":
                curr_hash = cls._hash_nodes(curr_hash, sibling)
            elif direction == "left":
                curr_hash = cls._hash_nodes(sibling, curr_hash)
            else:
                raise MerkleIntegrityError(f"Invalid proof direction: {direction}")
        return curr_hash.hex() == expected_root_hex


import os
from pathlib import Path


@dataclass(frozen=True)
class PackageVersion:
    name: str
    version: int
    dependencies: Dict[str, Set[int]]


class UvPubGrubCacheManager:
    """
    Simulates uv's PubGrub dependency solver and content-addressable hardlink cache
    for instantaneous E2E test environment provisioning.
    """

    def __init__(self, cache_root: Path) -> None:
        self.cache_root = cache_root
        self.cas_dir = self.cache_root / "cas_blobs"
        self.cas_dir.mkdir(parents=True, exist_ok=True)
        self.registry: Dict[str, Dict[int, PackageVersion]] = {}

    def register_package(
        self, name: str, version: int, dependencies: Optional[Dict[str, Set[int]]] = None
    ) -> None:
        if name not in self.registry:
            self.registry[name] = {}
        self.registry[name][version] = PackageVersion(
            name=name, version=version, dependencies=dependencies or {}
        )
        blob_content = f"pkg:{name}@{version}".encode("utf-8")
        digest = hashlib.sha256(blob_content).hexdigest()
        blob_path = self.cas_dir / digest
        if not blob_path.exists():
            blob_path.write_bytes(blob_content)

    def resolve_dependencies(self, root_requirements: Dict[str, Set[int]]) -> Dict[str, int]:
        """ Deterministic backtracking PubGrub-style constraint solver."""
        solution: Dict[str, int] = {}

        def _backtrack(pending: List[Tuple[str, Set[int]]]) -> bool:
            if not pending:
                return True
            pkg_name, allowed_versions = pending[0]
            rest = pending[1:]

            if pkg_name in solution:
                if solution[pkg_name] in allowed_versions:
                    return _backtrack(rest)
                return False

            available = self.registry.get(pkg_name, {})
            candidates = sorted(
                [v for v in available.keys() if v in allowed_versions], reverse=True
            )
            for candidate_ver in candidates:
                solution[pkg_name] = candidate_ver
                pkg_obj = available[candidate_ver]
                sub_constraints: List[Tuple[str, Set[int]]] = []
                conflict = False
                for dep_name, dep_allowed in pkg_obj.dependencies.items():
                    if dep_name in solution and solution[dep_name] not in dep_allowed:
                        conflict = True
                        break
                    sub_constraints.append((dep_name, dep_allowed))
                if not conflict and _backtrack(sub_constraints + rest):
                    return True
                del solution[pkg_name]
            return False

        initial_queue = list(root_requirements.items())
        if not _backtrack(initial_queue):
            raise DependencyResolutionError(
                f"Unsatisfiable dependency graph for requirements: {root_requirements}"
            )
        return solution

    def materialize_ephemeral_env(self, env_name: str, resolved: Dict[str, int]) -> Path:
        """Zero-copy environment creation using POSIX hardlinks from CAS store."""
        env_dir = self.cache_root / "envs" / env_name
        env_dir.mkdir(parents=True, exist_ok=True)
        for name, ver in resolved.items():
            blob_content = f"pkg:{name}@{ver}".encode("utf-8")
            digest = hashlib.sha256(blob_content).hexdigest()
            src_blob = self.cas_dir / digest
            dst_link = env_dir / f"{name}-{ver}.whl"
            if dst_link.exists():
                dst_link.unlink()
            os.link(src_blob, dst_link)
        return env_dir


class MemoryLimitExceededError(Exception):
    """Raised when memory consumption exceeds the strict upper bound M_max."""


class CRDTMap:
    """
    Conflict-Free Replicated JSON Object Map supporting commutative concurrent edits (arXiv:1608.03960).
    """

    def __init__(self, map_id: str) -> None:
        self.map_id = map_id
        self.entries: Dict[str, CRDTRegister] = {}

    def set_field(self, key: str, value: Any, timestamp: int, replica_id: str) -> None:
        new_register = CRDTRegister(value, timestamp, replica_id)
        if key in self.entries:
            self.entries[key] = self.entries[key].merge(new_register)
        else:
            self.entries[key] = new_register

    def get_field(self, key: str) -> Optional[Any]:
        reg = self.entries.get(key)
        return reg.value if reg is not None else None

    def merge(self, other: "CRDTMap") -> "CRDTMap":
        """Commutative, associative, idempotent merge of two CRDT maps."""
        merged = CRDTMap(self.map_id)
        all_keys: Set[str] = set(self.entries.keys()).union(other.entries.keys())
        for k in all_keys:
            if k in self.entries and k in other.entries:
                merged.entries[k] = self.entries[k].merge(other.entries[k])
            elif k in self.entries:
                merged.entries[k] = self.entries[k]
            else:
                merged.entries[k] = other.entries[k]
        return merged

    def compute_state_hash(self) -> str:
        """Generates deterministic SHA-256 hash of sorted key-value state."""
        canonical_repr = {
            k: self.entries[k].to_dict() for k in sorted(self.entries.keys())
        }
        raw = json.dumps(canonical_repr, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PubGrubDealRuleSolver:
    """
    Constraint solver adapted from astral-sh/uv PubGrub principles.
    Enforces bounded memory constraint: M(t) <= M_max with O(1) slot recycling.
    """

    def __init__(self, max_memory_slots: int = 128) -> None:
        self.max_memory_slots = max_memory_slots
        self.active_slots: Dict[str, Any] = {}
        self.rules: Dict[str, List[Tuple[str, str]]] = {}

    def register_incompatibility(self, item_a: str, item_b: str, reason: str) -> None:
        self.rules.setdefault(item_a, []).append((item_b, reason))
        self.rules.setdefault(item_b, []).append((item_a, reason))

    def allocate_slot(self, slot_id: str, payload: Any) -> None:
        """Strict bounding check: M(t) <= M_max."""
        if len(self.active_slots) >= self.max_memory_slots:
            raise MemoryLimitExceededError(
                f"Memory invariant violated: {len(self.active_slots)} >= {self.max_memory_slots}"
            )
        self.active_slots[slot_id] = payload

    def release_slot(self, slot_id: str) -> None:
        """O(1) slot recycling."""
        if slot_id in self.active_slots:
            del self.active_slots[slot_id]

    def solve_feasibility(self, selected_items: List[str]) -> Tuple[bool, Optional[str]]:
        selected_set = set(selected_items)
        for item in selected_items:
            incompatibilities = self.rules.get(item, [])
            for incompatible_item, reason in incompatibilities:
                if incompatible_item in selected_set:
                    return (
                        False,
                        f"Conflict between '{item}' and '{incompatible_item}': {reason}",
                    )
        return True, None


class MultiTenantRecordRuleEngine:
    """
    Row-Level Security & Multi-Company Domain Engine adapted from odoo/odoo.
    """

    def __init__(self) -> None:
        self.company_hierarchy: Dict[int, Optional[int]] = {}
        self.records: List[Dict[str, Any]] = []

    def register_company(self, company_id: int, parent_id: Optional[int] = None) -> None:
        self.company_hierarchy[company_id] = parent_id

    def add_record(self, record_id: str, company_id: int, data: Dict[str, Any]) -> None:
        self.records.append(
            {
                "id": record_id,
                "company_id": company_id,
                "data": data,
            }
        )

    def filter_records(self, allowed_company_ids: List[int]) -> List[Dict[str, Any]]:
        allowed_set = set(allowed_company_ids)
        effective_set = set(allowed_set)
        for child_id, parent_id in self.company_hierarchy.items():
            if parent_id in allowed_set:
                effective_set.add(child_id)

        return [r for r in self.records if r["company_id"] in effective_set]


class DealDeskSalesQuoteCRDT:
    """
    Conflict-Free Replicated JSON Document for Enterprise Sales Quotations.
    Implements arXiv:1608.03960 lattice convergence for concurrent deal-desk edits.
    """

    def __init__(self, quote_id: str) -> None:
        self.quote_id = quote_id
        self._fields: Dict[str, CRDTRegister] = {}
        self._items: Dict[str, Dict[str, CRDTRegister]] = {}

    def update_field(
        self, field_name: str, value: Any, timestamp: int, actor_id: str
    ) -> None:
        new_reg = CRDTRegister(timestamp=timestamp, actor_id=actor_id, value=value)
        if field_name in self._fields:
            self._fields[field_name] = self._fields[field_name].merge(new_reg)
        else:
            self._fields[field_name] = new_reg

    def update_item(
        self, sku: str, property_name: str, value: Any, timestamp: int, actor_id: str
    ) -> None:
        if sku not in self._items:
            self._items[sku] = {}
        new_reg = CRDTRegister(timestamp=timestamp, actor_id=actor_id, value=value)
        if property_name in self._items[sku]:
            self._items[sku][property_name] = self._items[sku][property_name].merge(
                new_reg
            )
        else:
            self._items[sku][property_name] = new_reg

    def merge_remote(self, remote: "DealDeskSalesQuoteCRDT") -> "DealDeskSalesQuoteCRDT":
        merged = DealDeskSalesQuoteCRDT(quote_id=self.quote_id)
        all_keys = set(self._fields.keys()).union(remote._fields.keys())
        for k in all_keys:
            if k in self._fields and k in remote._fields:
                merged._fields[k] = self._fields[k].merge(remote._fields[k])
            elif k in self._fields:
                merged._fields[k] = self._fields[k]
            else:
                merged._fields[k] = remote._fields[k]

        all_skus = set(self._items.keys()).union(remote._items.keys())
        for sku in all_skus:
            merged._items[sku] = {}
            props = set(self._items.get(sku, {}).keys()).union(
                remote._items.get(sku, {}).keys()
            )
            for p in props:
                in_self = self._items.get(sku, {}).get(p)
                in_remote = remote._items.get(sku, {}).get(p)
                if in_self is not None and in_remote is not None:
                    merged._items[sku][p] = in_self.merge(in_remote)
                elif in_self is not None:
                    merged._items[sku][p] = in_self
                elif in_remote is not None:
                    merged._items[sku][p] = in_remote
        return merged

    def to_canonical_dict(self) -> Dict[str, Any]:
        return {
            "quote_id": self.quote_id,
            "fields": {k: self._fields[k].value for k in sorted(self._fields.keys())},
            "items": {
                sku: {
                    p: self._items[sku][p].value for p in sorted(self._items[sku].keys())
                }
                for sku in sorted(self._items.keys())
            },
        }


class TransparencyTreeVerifier:
    """
    Merkle Tree Cryptographic Verifier for Sales Concession Audits.
    Implements formal transparency protocol invariants (arXiv:2303.04500).
    """

    @staticmethod
    def hash_leaf(data: Dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def combine_hashes(left: str, right: str) -> str:
        payload = f"{left}:{right}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def build_audit_root(self, records: List[Dict[str, Any]]) -> str:
        if not records:
            raise ValueError("Audit log cannot be empty for root calculation.")
        current_level = [self.hash_leaf(r) for r in records]
        while len(current_level) > 1:
            if len(current_level) % 2 != 0:
                current_level.append(current_level[-1])
            next_level = []
            for i in range(0, len(current_level), 2):
                next_level.append(
                    self.combine_hashes(current_level[i], current_level[i + 1])
                )
            current_level = next_level
        return current_level[0]


class PubGrubCPQValidator:
    """
    CPQ Constraint Solver inspired by astral-sh/uv PubGrub solver.
    Validates product dependency closures and incompatibilities.
    """

    def __init__(self) -> None:
        self.dependencies: Dict[str, Set[str]] = {}
        self.incompatibilities: Dict[str, Set[str]] = {}

    def add_dependency(self, sku: str, requires_sku: str) -> None:
        self.dependencies.setdefault(sku, set()).add(requires_sku)

    def add_incompatibility(self, sku: str, conflicts_with: str) -> None:
        self.incompatibilities.setdefault(sku, set()).add(conflicts_with)
        self.incompatibilities.setdefault(conflicts_with, set()).add(sku)

    def validate_cart(self, selected_skus: Set[str]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for sku in selected_skus:
            reqs = self.dependencies.get(sku, set())
            missing = reqs - selected_skus
            if missing:
                errors.append(
                    f"SKU '{sku}' requires missing dependency: {sorted(list(missing))}"
                )
            conflicts = self.incompatibilities.get(sku, set())
            active_conflicts = conflicts.intersection(selected_skus)
            if active_conflicts:
                errors.append(
                    f"SKU '{sku}' is incompatible with present items: {sorted(list(active_conflicts))}"
                )
        return len(errors) == 0, errors


class JSONCRDTOperation:
    """Represents a discrete, deterministic operation on a JSON CRDT structure."""

    def __init__(
        self, op_id: str, actor: str, path: List[str], op_type: str, value: Any
    ) -> None:
        self.op_id = op_id
        self.actor = actor
        self.path = path
        self.op_type = op_type
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op_id": self.op_id,
            "actor": self.actor,
            "path": self.path,
            "op_type": self.op_type,
            "value": self.value,
        }


class SalesQuoteCRDTHarness:
    """
    Local-first Conflict-Free Replicated Sales Quote State Machine
    with Merkle Transparency Audit Chain (Turn 13 Q1 State-Trellis).
    """

    def __init__(self, quote_id: str, tenant_id: str) -> None:
        self.quote_id = quote_id
        self.tenant_id = tenant_id
        self.document_state: Dict[str, Any] = {
            "quote_id": quote_id,
            "tenant_id": tenant_id,
            "lines": {},
            "status": "draft",
        }
        self.op_log: List[JSONCRDTOperation] = []
        self.merkle_history: List[str] = [self._calculate_root_hash(self.document_state)]

    def _calculate_root_hash(self, state: Dict[str, Any]) -> str:
        serialized = json.dumps(state, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def apply_operation(self, op: JSONCRDTOperation) -> str:
        if not op.path:
            raise ValueError("Operation path cannot be empty.")

        target = self.document_state
        for key in op.path[:-1]:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
            target = target[key]

        leaf_key = op.path[-1]
        if op.op_type == "set":
            target[leaf_key] = op.value
        elif op.op_type == "delete":
            target.pop(leaf_key, None)
        else:
            raise ValueError(f"Unsupported CRDT op_type: {op.op_type}")

        self.op_log.append(op)
        new_hash = self._calculate_root_hash(self.document_state)
        self.merkle_history.append(new_hash)
        return new_hash

    def verify_invariant(self) -> bool:
        if len(self.merkle_history) != len(self.op_log) + 1:
            return False

        test_state: Dict[str, Any] = {
            "quote_id": self.quote_id,
            "tenant_id": self.tenant_id,
            "lines": {},
            "status": "draft",
        }

        for idx, op in enumerate(self.op_log):
            target = test_state
            for key in op.path[:-1]:
                if key not in target or not isinstance(target[key], dict):
                    target[key] = {}
                target = target[key]
            if op.op_type == "set":
                target[op.path[-1]] = op.value
            elif op.op_type == "delete":
                target.pop(op.path[-1], None)

            step_hash = self._calculate_root_hash(test_state)
            if step_hash != self.merkle_history[idx + 1]:
                return False

        return self._calculate_root_hash(self.document_state) == self.merkle_history[-1]

    def apply_odoo_odoo_pattern(self) -> bool:
        return bool(self.tenant_id and self.document_state.get("tenant_id") == self.tenant_id)

    def apply_astral_sh_uv_pattern(self) -> bool:
        lines = self.document_state.get("lines", {})
        sku_list = [
            v.get("sku") for v in lines.values() if isinstance(v, dict) and "sku" in v
        ]
        return len(sku_list) == len(set(sku_list))


class CRDTSalesDocument:
    """Conflict-Free Replicated JSON Document for concurrent sales proposal mutations (arXiv:1608.03960)."""

    def __init__(self, doc_id: str, actor_id: str) -> None:
        self.doc_id: str = doc_id
        self.actor_id: str = actor_id
        self._fields: Dict[str, CRDTRegister] = {}
        self._items: Dict[str, Dict[str, CRDTRegister]] = {}

    def set_field(
        self, key: str, value: Any, timestamp: Optional[float] = None
    ) -> None:
        ts = timestamp if timestamp is not None else time.time()
        self._fields[key] = CRDTRegister(
            value=value, timestamp=ts, actor_id=self.actor_id
        )

    def set_line_item(
        self,
        item_id: str,
        field_name: str,
        value: Any,
        timestamp: Optional[float] = None,
    ) -> None:
        ts = timestamp if timestamp is not None else time.time()
        if item_id not in self._items:
            self._items[item_id] = {}
        self._items[item_id][field_name] = CRDTRegister(
            value=value, timestamp=ts, actor_id=self.actor_id
        )

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {k: reg.value for k, reg in self._fields.items()}
        items_dict: Dict[str, Dict[str, Any]] = {}
        for item_id, item_fields in sorted(self._items.items()):
            items_dict[item_id] = {k: reg.value for k, reg in item_fields.items()}
        result["items"] = items_dict
        return result

    def merge(self, other: "CRDTSalesDocument") -> "CRDTSalesDocument":
        merged = CRDTSalesDocument(
            doc_id=self.doc_id, actor_id=f"merged_{self.actor_id}_{other.actor_id}"
        )
        all_field_keys: Set[str] = set(self._fields.keys()).union(
            set(other._fields.keys())
        )
        for key in all_field_keys:
            if key in self._fields and key in other._fields:
                merged._fields[key] = self._fields[key].merge(other._fields[key])
            elif key in self._fields:
                merged._fields[key] = self._fields[key]
            else:
                merged._fields[key] = other._fields[key]

        all_item_keys: Set[str] = set(self._items.keys()).union(
            set(other._items.keys())
        )
        for item_id in all_item_keys:
            merged._items[item_id] = {}
            fields_self = self._items.get(item_id, {})
            fields_other = other._items.get(item_id, {})
            item_field_keys: Set[str] = set(fields_self.keys()).union(
                set(fields_other.keys())
            )
            for fk in item_field_keys:
                if fk in fields_self and fk in fields_other:
                    merged._items[item_id][fk] = fields_self[fk].merge(fields_other[fk])
                elif fk in fields_self:
                    merged._items[item_id][fk] = fields_self[fk]
                else:
                    merged._items[item_id][fk] = fields_other[fk]

        return merged


@dataclass
class OdooSalesOrder:
    order_id: str
    company_id: int
    customer_id: str
    total_amount: float
    state: str = "draft"


class OdooMultiTenantGuard:
    """Enforces multi-company record rules and double-entry reconciliation integrity."""

    def __init__(self) -> None:
        self.orders: Dict[str, OdooSalesOrder] = {}
        self.ledger_entries: List[Dict[str, Any]] = []

    def record_order(self, order: OdooSalesOrder, user_company_id: int) -> bool:
        if order.company_id != user_company_id:
            raise PermissionError(
                f"Multi-Company Violation: User company {user_company_id} cannot access order of company {order.company_id}"
            )
        self.orders[order.order_id] = order
        return True

    def post_double_entry_invoice(
        self, order_id: str, debit_acc: str, credit_acc: str, amount: float
    ) -> bool:
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} does not exist")
        if order.state == "posted":
            raise ValueError(f"Order {order_id} already posted")

        entry = {
            "order_id": order_id,
            "company_id": order.company_id,
            "debit": {debit_acc: amount},
            "credit": {credit_acc: amount},
            "balanced": True,
            "timestamp": time.time(),
        }
        self.ledger_entries.append(entry)
        order.state = "posted"
        return True

    def verify_ledger_equilibrium(self) -> bool:
        total_debits = sum(sum(e["debit"].values()) for e in self.ledger_entries)
        total_credits = sum(sum(e["credit"].values()) for e in self.ledger_entries)
        return abs(total_debits - total_credits) < 1e-6


class SalesRuleConstraintSolver:
    """Simulates PubGrub dependency and constraint resolution for complex pricing rules."""

    def __init__(self, max_memory_slots: int = 100) -> None:
        self.max_memory_slots = max_memory_slots
        self.cache: Dict[str, Any] = {}

    def resolve_bundle_eligibility(
        self, product_ids: List[str], rules: Dict[str, List[str]]
    ) -> Set[str]:
        if len(self.cache) >= self.max_memory_slots:
            oldest_key = next(iter(self.cache))
            self.cache.pop(oldest_key)

        cache_key = ":".join(sorted(product_ids))
        if cache_key in self.cache:
            return self.cache[cache_key]

        selected: Set[str] = set(product_ids)
        satisfied_rules: Set[str] = set()

        for rule_name, required_prereqs in rules.items():
            if all(req in selected for req in required_prereqs):
                satisfied_rules.add(rule_name)

        self.cache[cache_key] = satisfied_rules
        return satisfied_rules


class FlowState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


@dataclass
class FlowRunContext:
    flow_id: str
    idempotency_key: str
    state: FlowState = FlowState.PENDING
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[Any] = None
    error_message: Optional[str] = None


class PrefectSalesFlowOrchestrator:
    """Asynchronous, observable state machine managing resilient multi-step sales workflows."""

    def __init__(self) -> None:
        self.completed_keys: Dict[str, FlowRunContext] = {}

    def execute_flow(
        self,
        flow_id: str,
        idempotency_key: str,
        task_payload: Dict[str, Any],
        simulate_failure_once: bool = False,
    ) -> FlowRunContext:
        if idempotency_key in self.completed_keys:
            existing = self.completed_keys[idempotency_key]
            if existing.state == FlowState.COMPLETED:
                return existing

        ctx = FlowRunContext(
            flow_id=flow_id, idempotency_key=idempotency_key, state=FlowState.RUNNING
        )

        try:
            if "target_discount" not in task_payload:
                raise ValueError("Payload missing required key: 'target_discount'")

            discount = float(task_payload["target_discount"])
            if discount < 0.0 or discount > 1.0:
                raise ValueError(
                    f"Invalid discount {discount}: must be between 0.0 and 1.0"
                )

            if simulate_failure_once and ctx.retry_count == 0:
                ctx.state = FlowState.RETRYING
                ctx.retry_count += 1
                if discount > 0.40:
                    raise PermissionError(
                        "Discounts over 40% require Executive Council approval"
                    )
                ctx.result = {
                    "approved_discount": discount,
                    "status": "APPROVED_ON_RETRY",
                }
                ctx.state = FlowState.COMPLETED
            else:
                if discount > 0.40:
                    raise PermissionError(
                        "Discounts over 40% require Executive Council approval"
                    )
                ctx.result = {"approved_discount": discount, "status": "APPROVED"}
                ctx.state = FlowState.COMPLETED

        except Exception as exc:
            ctx.state = FlowState.FAILED
            ctx.error_message = str(exc)

        self.completed_keys[idempotency_key] = ctx
        return ctx


@dataclass
class CRDTRowMutation:
    """Single operation mutating a sales order line."""

    op_id: str
    line_id: str
    product_id: str
    quantity: float
    price_unit: float
    discount: float
    timestamp: LamportTimestamp
    is_deleted: bool = False


class BoundedSalesQuoteCRDT:
    """
    Conflict-Free Replicated JSON Data Type specialized for Odoo sales quote lines.
    Applies Last-Write-Wins (LWW) element registers indexed by unique line keys.
    """

    def __init__(self, order_id: str, company_id: int) -> None:
        self.order_id = order_id
        self.company_id = company_id
        self.current_clock = 0
        self.lines: Dict[str, CRDTRowMutation] = {}
        self.operation_log: List[CRDTRowMutation] = []
        self.max_log_size = 100

    def create_or_update_line(
        self,
        node_id: str,
        line_id: str,
        product_id: str,
        quantity: float,
        price_unit: float,
        discount: float,
    ) -> CRDTRowMutation:
        if quantity < 0:
            raise ValueError(f"Quantity must be non-negative, got {quantity}")
        if price_unit < 0:
            raise ValueError(f"Unit price must be non-negative, got {price_unit}")
        if not (0.0 <= discount <= 100.0):
            raise ValueError(f"Discount must be between 0 and 100, got {discount}")

        self.current_clock += 1
        ts = LamportTimestamp(counter=self.current_clock, actor_id=node_id)
        op_id = hashlib.sha256(
            f"{self.order_id}:{line_id}:{ts.counter}:{ts.node_id}".encode("utf-8")
        ).hexdigest()[:16]

        mutation = CRDTRowMutation(
            op_id=op_id,
            line_id=line_id,
            product_id=product_id,
            quantity=quantity,
            price_unit=price_unit,
            discount=discount,
            timestamp=ts,
            is_deleted=False,
        )
        self.apply_mutation(mutation)
        return mutation

    def delete_line(self, node_id: str, line_id: str) -> Optional[CRDTRowMutation]:
        if line_id not in self.lines or self.lines[line_id].is_deleted:
            return None

        self.current_clock += 1
        ts = LamportTimestamp(counter=self.current_clock, actor_id=node_id)
        existing = self.lines[line_id]
        op_id = hashlib.sha256(
            f"{self.order_id}:{line_id}:delete:{ts.counter}:{ts.node_id}".encode("utf-8")
        ).hexdigest()[:16]

        mutation = CRDTRowMutation(
            op_id=op_id,
            line_id=line_id,
            product_id=existing.product_id,
            quantity=existing.quantity,
            price_unit=existing.price_unit,
            discount=existing.discount,
            timestamp=ts,
            is_deleted=True,
        )
        self.apply_mutation(mutation)
        return mutation

    def apply_mutation(self, mutation: CRDTRowMutation) -> bool:
        self.current_clock = max(self.current_clock, mutation.timestamp.counter)

        target = self.lines.get(mutation.line_id)
        if target is None or target.timestamp < mutation.timestamp:
            self.lines[mutation.line_id] = mutation
            self.operation_log.append(mutation)
            self._compact_log_if_needed()
            return True
        return False

    def _compact_log_if_needed(self) -> None:
        if len(self.operation_log) > self.max_log_size:
            active_op_ids = {m.op_id for m in self.lines.values()}
            self.operation_log = [
                m for m in self.operation_log if m.op_id in active_op_ids
            ]

    def compute_subtotals(self, tax_rate_percent: float = 10.0) -> Dict[str, Decimal]:
        tax_multiplier = Decimal(str(tax_rate_percent)) / Decimal("100.0")
        subtotal_untaxed = Decimal("0.00")
        total_tax = Decimal("0.00")

        for line in self.lines.values():
            if line.is_deleted:
                continue

            qty = Decimal(str(line.quantity))
            price = Decimal(str(line.price_unit))
            disc = Decimal(str(line.discount))

            undiscounted_line = (qty * price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            discount_amount = (undiscounted_line * (disc / Decimal("100.0"))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            line_subtotal = undiscounted_line - discount_amount
            line_tax = (line_subtotal * tax_multiplier).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            subtotal_untaxed += line_subtotal
            total_tax += line_tax

        total_amount = subtotal_untaxed + total_tax
        return {
            "amount_untaxed": subtotal_untaxed,
            "amount_tax": total_tax,
            "amount_total": total_amount,
        }

    def canonical_json(self) -> str:
        active_lines = []
        for line_id in sorted(self.lines.keys()):
            line = self.lines[line_id]
            if not line.is_deleted:
                active_lines.append(
                    {
                        "line_id": line.line_id,
                        "product_id": line.product_id,
                        "quantity": line.quantity,
                        "price_unit": line.price_unit,
                        "discount": line.discount,
                        "clock": line.timestamp.counter,
                        "node_id": line.timestamp.node_id,
                    }
                )

        state = {
            "company_id": self.company_id,
            "order_id": self.order_id,
            "lines": active_lines,
        }
        return json.dumps(state, sort_keys=True, separators=(",", ":"))


class MerkleTransparencyLedger:
    """
    Append-only Merkle Hash Tree recording sales order state transitions.
    Guarantees non-repudiation and cryptographic auditability for pricing exceptions.
    """

    def __init__(self, genesis_salt: str = "insilos_sovereign_sales_v1") -> None:
        self.genesis_hash = hashlib.sha256(genesis_salt.encode("utf-8")).hexdigest()
        self.leaves: List[str] = []
        self.transition_history: List[Dict[str, Any]] = []
        self.current_root = self.genesis_hash

    def append_transition(self, actor: str, action: str, state_json: str) -> str:
        payload_hash = hashlib.sha256(state_json.encode("utf-8")).hexdigest()
        transition_record = {
            "index": len(self.leaves),
            "actor": actor,
            "action": action,
            "payload_hash": payload_hash,
            "timestamp_epoch": time.time(),
        }
        leaf_content = json.dumps(
            transition_record, sort_keys=True, separators=(",", ":")
        )
        leaf_hash = hashlib.sha256(leaf_content.encode("utf-8")).hexdigest()

        self.leaves.append(leaf_hash)
        self.transition_history.append(transition_record)
        self.current_root = hashlib.sha256(
            f"{self.current_root}:{leaf_hash}".encode("utf-8")
        ).hexdigest()
        return self.current_root

    def verify_chain_integrity(self) -> bool:
        computed_root = self.genesis_hash
        for record, recorded_leaf in zip(self.transition_history, self.leaves):
            reconstructed_content = json.dumps(
                record, sort_keys=True, separators=(",", ":")
            )
            expected_leaf = hashlib.sha256(
                reconstructed_content.encode("utf-8")
            ).hexdigest()
            if expected_leaf != recorded_leaf:
                return False
            computed_root = hashlib.sha256(
                f"{computed_root}:{expected_leaf}".encode("utf-8")
            ).hexdigest()

        return computed_root == self.current_root


class SalesWorkflowSupervisor:
    """
    Supervises the transition of sales orders through Odoo stages
    (draft -> sent -> sale) while enforcing multi-tenant rules and margin gates.
    """

    MIN_ALLOWED_MARGIN_PERCENT = Decimal("15.00")

    def __init__(self, tenant_company_id: int) -> None:
        self.tenant_company_id = tenant_company_id

    def validate_tenant_isolation(self, quote: BoundedSalesQuoteCRDT) -> bool:
        if quote.company_id != self.tenant_company_id:
            raise PermissionError(
                f"Tenant Isolation Violation: Active Company {self.tenant_company_id} "
                f"attempted to access Quote Company {quote.company_id}"
            )
        return True

    def validate_pricing_constraints(
        self, quote: BoundedSalesQuoteCRDT, product_costs: Dict[str, Decimal]
    ) -> Tuple[bool, Decimal]:
        totals = quote.compute_subtotals(tax_rate_percent=10.0)
        total_untaxed = totals["amount_untaxed"]

        if total_untaxed == Decimal("0.00"):
            return False, Decimal("0.00")

        total_cost = Decimal("0.00")
        for line in quote.lines.values():
            if line.is_deleted:
                continue
            cost = product_costs.get(line.product_id, Decimal("0.00"))
            total_cost += cost * Decimal(str(line.quantity))

        if total_cost > total_untaxed:
            margin_percent = Decimal("-100.00")
        else:
            margin = total_untaxed - total_cost
            margin_percent = (margin / total_untaxed) * Decimal("100.00")
            margin_percent = margin_percent.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        is_valid = margin_percent >= self.MIN_ALLOWED_MARGIN_PERCENT
        return is_valid, margin_percent
