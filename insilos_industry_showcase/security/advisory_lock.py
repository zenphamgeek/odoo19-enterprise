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
    tenant_id: int
    allowed_company_ids: Any
    lease_signature: str = ""
    created_at_mono: float = 0.0
    epoch_timestamp: float = 0.0
    nonce: str = ""
    signature: str = ""

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
from typing import Union


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


class HeterogeneousLockKey:
    """Immutable composite key guaranteeing global monotonic lock ordering across Redis, PG Advisory, and PG Row locks."""

    __slots__ = ("tier", "tenant_id", "resource_id", "record_id")

    def __init__(
        self,
        tier: LockSystemTier,
        tenant_id: int,
        resource_id: int,
        record_id: int,
    ) -> None:
        if not isinstance(tenant_id, int) or isinstance(tenant_id, bool) or tenant_id <= 0:
            raise ValueError(f"tenant_id must be a positive integer, got: {tenant_id!r}")
        if not isinstance(resource_id, int) or isinstance(resource_id, bool) or resource_id < 0:
            raise ValueError(f"resource_id must be a non-negative integer, got: {resource_id!r}")
        if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id < 0:
            raise ValueError(f"record_id must be a non-negative integer, got: {record_id!r}")

        self.tier = LockSystemTier(tier)
        self.tenant_id = tenant_id
        self.resource_id = resource_id
        self.record_id = record_id

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (int(self.tier), self.tenant_id, self.resource_id, self.record_id)

    def __lt__(self, other: "HeterogeneousLockKey") -> bool:
        if not isinstance(other, HeterogeneousLockKey):
            return NotImplemented
        return self.as_tuple() < other.as_tuple()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, HeterogeneousLockKey):
            return False
        return self.as_tuple() == other.as_tuple()

    def __hash__(self) -> int:
        return hash(self.as_tuple())

    def __repr__(self) -> str:
        return (
            f"HeterogeneousLockKey(tier={self.tier.name}, tenant={self.tenant_id}, "
            f"resource={self.resource_id}, record={self.record_id})"
        )


class _HeterogeneousCrossTierLockManager(CanonicalLockHierarchyManager):
    """Acquires heterogeneous locks in strictly sorted order with timeout protection AND supports class-level model-tier sorting."""

    def __init__(self, cr: Any = None, redis_client: Optional[Any] = None) -> None:
        super().__init__(cr=cr)
        self.redis_client = redis_client
        self._acquired_locks: List[HeterogeneousLockKey] = []

    def _acquire_postgres_advisory(self, key: HeterogeneousLockKey, timeout_sec: float) -> bool:
        lock_id_64 = (
            ((key.tenant_id & 0xFFFF) << 48)
            | ((key.resource_id & 0xFFFF) << 32)
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

    @contextmanager
    def acquire_heterogeneous_locks(
        self,
        lock_keys: List[HeterogeneousLockKey],
        timeout_sec: float = 3.0,
    ):
        sorted_keys = sorted(set(lock_keys))
        self._acquired_locks = []
        try:
            for key in sorted_keys:
                acquired = False
                if key.tier == LockSystemTier.DISTRIBUTED_REDIS:
                    acquired = self._acquire_redis_mutex(key, timeout_sec)
                elif key.tier == LockSystemTier.POSTGRES_ADVISORY:
                    acquired = self._acquire_postgres_advisory(key, timeout_sec)
                elif key.tier == LockSystemTier.POSTGRES_ROW_LEVEL:
                    acquired = self._acquire_postgres_row(key, timeout_sec)

                if not acquired:
                    raise TimeoutError(
                        f"DeterministicHeterogeneousLockManager: Failed to acquire {key} within {timeout_sec}s timeout."
                    )
                self._acquired_locks.append(key)
            yield self._acquired_locks
        finally:
            for key in reversed(self._acquired_locks):
                if key.tier == LockSystemTier.DISTRIBUTED_REDIS:
                    self._release_redis_mutex(key)
            self._acquired_locks.clear()


DeterministicHeterogeneousLockManager = _HeterogeneousCrossTierLockManager


class NFKDStrongRefFormulaSanitizer:
    """Canonicalizes and sanitizes formulas against injection and cyclic dependency graph explosion."""

    SAFE_FUNCTIONS: Set[str] = {
        "SUM", "AVERAGE", "COUNT", "COUNTA", "MAX", "MIN", "IF",
        "ROUND", "ABS", "SUBTOTAL", "VLOOKUP", "XLOOKUP", "INDEX", "MATCH",
    }
    CELL_REF_PATTERN = re.compile(
        r"^(?:'?[a-zA-Z0-9_\s]+'?!|\b)([A-Z]{1,3}[0-9]{1,7})\b"
    )
    MAX_RECURSION_DEPTH = 8
    MAX_FORMULA_LENGTH = 1024

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



