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


LockTimeoutSecurityException = LockAcquisitionTimeoutError


class BoundedAdvisoryLockGuard:
    """
    Bounded Flat Advisory Lock with Reversible Diagnostic Metadata and Lexicographical Sorting (Synthesis 4.4 / Patch 71).
    Supports both instance context-manager mode `with BoundedAdvisoryLockGuard(cr, keys, timeout_seconds):`
    and classmethod mode `with BoundedAdvisoryLockGuard.acquire(cursor, company_id, journal_id):`.
    """

    diagnostic_registry: Dict[Tuple[int, int], Dict[str, Any]] = {}
    _registry_lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        cr: Any,
        keys: Iterable[Tuple[int, int]],
        timeout_seconds: float = 5.0,
    ) -> None:
        if timeout_seconds <= 0.0:
            raise ValueError("Lock timeout must be strictly positive.")
        self.cr = cr
        self.keys: List[Tuple[int, int]] = sorted(set((int(k1), int(k2)) for k1, k2 in keys))
        self.timeout_seconds: float = float(timeout_seconds)
        self._acquired: bool = False

    def __enter__(self) -> "BoundedAdvisoryLockGuard":
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
        expected_token_hash: Optional[Union[str, int, List[int]]] = None,
        *,
        env: Optional[Any] = None,
        target_company_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        allowed_company_ids: Optional[List[int]] = None,
    ) -> None:
        resolved_env = env if env is not None else token
        if resolved_env is not None and hasattr(resolved_env, "context"):
            comp_val = target_company_id if target_company_id is not None else secret_key
            if isinstance(comp_val, bool) or not isinstance(comp_val, int) or comp_val <= 0:
                raise ValueError(f"Invalid target_company_id: {comp_val}")
            self.env = resolved_env
            self.target_company_id = int(comp_val)
            user_val = (
                target_user_id
                if target_user_id is not None
                else (expected_token_hash if isinstance(expected_token_hash, int) else None)
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
            self.original_context: Optional[Dict[str, Any]] = None
            self._original_context: Optional[Dict[str, Any]] = None
            self.original_uid: Optional[int] = None
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
            self.original_context = None
            self._original_context = None
            self.original_uid = None
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
            self.original_context = None
            self._original_context = None
            self.original_uid = None
            self._restored = False
            self.token = token
            self.secret_key = secret_key if isinstance(secret_key, bytes) else str(secret_key).encode("utf-8")
            self.tenant_id = ""
            self.secret_token = ""
            self.expected_token_hash = ""
            self._mode = "token"
        self._cv_token: Optional[contextvars.Token] = None

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
            self.original_context = dict(self.env.context)
            self._original_context = self.original_context
            new_context = dict(self.original_context)
            new_context["allowed_company_ids"] = list(self.allowed_company_ids)
            new_context["company_id"] = self.target_company_id
            if callable(self.env) and self.target_user_id is None:
                return self.env(context=new_context)
            self.original_uid = getattr(self.env, "uid", None)
            self.env.context = new_context
            if self.target_user_id is not None:
                self.env.uid = self.target_user_id
            return self.env
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
