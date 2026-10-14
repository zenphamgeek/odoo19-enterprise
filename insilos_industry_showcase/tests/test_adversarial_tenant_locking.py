# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import importlib.util
import struct
import unittest
from pathlib import Path
from unittest.mock import MagicMock

try:
    from odoo.exceptions import AccessError, UserError
except Exception:
    class AccessError(Exception):
        pass
    class UserError(Exception):
        pass

try:
    from odoo.tests.common import TransactionCase, tagged
except Exception:
    TransactionCase = unittest.TestCase
    def tagged(*args, **kwargs):
        return lambda cls: cls

_CUR_DIR = Path(__file__).resolve().parent
_SEC_DIR = _CUR_DIR.parent / "security"


def _import_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    from ..security.advisory_lock import (
        acquire_tenant_xact_lock,
        compute_partitioned_lock_key,
        execute_with_detached_rpc,
        is_lock_active,
        _is_lock_active,
    )
    from ..security.tenant_guard import enforce_tenant_isolation
except Exception:
    _adv_mod = _import_file("advisory_lock", _SEC_DIR / "advisory_lock.py")
    acquire_tenant_xact_lock = _adv_mod.acquire_tenant_xact_lock
    compute_partitioned_lock_key = _adv_mod.compute_partitioned_lock_key
    execute_with_detached_rpc = _adv_mod.execute_with_detached_rpc
    is_lock_active = _adv_mod.is_lock_active
    _is_lock_active = _adv_mod._is_lock_active

    _guard_mod = _import_file("tenant_guard", _SEC_DIR / "tenant_guard.py")
    enforce_tenant_isolation = _guard_mod.enforce_tenant_isolation


@tagged("post_install", "-at_install", "security", "tenant_locking")
class TestAdversarialTenantLocking(TransactionCase):
    """
    Sovereign Adversarial Test Suite for Patch 15:
    - Cryptographic 64-bit Blake2b Transactional Advisory Lock Key Partitioning
    - Transaction Advisory Lock Lifecycle with Savepoint and Timeout Retry Bounds
    - Multi-Company Invariant Guard with Sudo Ambient Leakage Prevention
    - Strict Lock-RPC Separation (Detached External RPC Execution)
    """

    def test_adv_15_blake2b_partition_uniqueness(self):
        """
        Verifies 64-bit signed PostgreSQL bigint bounds [-2^63, 2^63 - 1],
        Blake2b digest mathematical parity, and elimination of 16-bit truncation collisions.
        """
        min_64bit = -(1 << 63)
        max_64bit = (1 << 63) - 1

        # 1. Deterministic lock key derivation and bounds check
        key = compute_partitioned_lock_key("saas.workspace", 1, 100)
        self.assertIsInstance(key, int)
        self.assertTrue(min_64bit <= key <= max_64bit)

        # Mathematical identity verification
        raw = f"saas.workspace:1:100".encode("utf-8")
        expected_digest = hashlib.blake2b(raw, digest_size=8).digest()
        expected_key = struct.unpack(">q", expected_digest)[0]
        self.assertEqual(key, expected_key)

        # 2. Distinctness across IDs > 65535 (eliminating 16-bit modulo truncation collisions)
        key_low = compute_partitioned_lock_key("res.partner", 1, 1)
        key_high1 = compute_partitioned_lock_key("res.partner", 1, 65537)
        key_high2 = compute_partitioned_lock_key("res.partner", 1, 131073)

        self.assertNotEqual(key_low, key_high1)
        self.assertNotEqual(key_low, key_high2)
        self.assertNotEqual(key_high1, key_high2)

        # 3. Collision resistance check across 1,000 distinct tenant-resource combinations
        seen_keys = set()
        for cid in range(1, 11):
            for rid in range(1, 101):
                k = compute_partitioned_lock_key("account.move", cid, rid)
                self.assertTrue(min_64bit <= k <= max_64bit)
                self.assertNotIn(k, seen_keys, f"Hash collision at company={cid}, record={rid}")
                seen_keys.add(k)
        self.assertEqual(len(seen_keys), 1000)

    def test_adv_15_acquire_tenant_xact_lock_lifecycle(self):
        """
        Verifies pg_try_advisory_xact_lock non-blocking acquisition,
        timeout retry logic, savepoint flush=True lifecycle, and rollback on error.
        """
        mock_cr = MagicMock()
        mock_cr.fetchone.return_value = (True,)
        sp = MagicMock()
        mock_cr.savepoint.return_value = sp
        sp.__enter__.return_value = sp
        sp.__exit__.return_value = None

        expected_key = compute_partitioned_lock_key("saas.workspace", 1, 42)

        # 1. Normal acquisition and savepoint entry
        executed = False
        with acquire_tenant_xact_lock(mock_cr, "saas.workspace", 1, 42, timeout_sec=0.5) as key:
            self.assertEqual(key, expected_key)
            self.assertTrue(is_lock_active("saas.workspace", 1, 42))
            executed = True

        self.assertTrue(executed)
        self.assertFalse(is_lock_active("saas.workspace", 1, 42))
        mock_cr.execute.assert_called_with(
            "SELECT pg_try_advisory_xact_lock(%s::bigint)",
            [expected_key],
        )
        mock_cr.savepoint.assert_called_with(flush=True)
        self.assertTrue(sp.__enter__.called)
        self.assertTrue(sp.__exit__.called)

        # 2. Contention failure raises UserError
        mock_cr.fetchone.return_value = (False,)
        with self.assertRaises(UserError) as cm:
            with acquire_tenant_xact_lock(mock_cr, "saas.workspace", 1, 42, timeout_sec=0.02, retry_delay=0.005, max_retries=2):
                pass
        self.assertIn("locked by another transaction", str(cm.exception))

        # 3. Exception inside savepoint handles rollback and untracks lock
        mock_cr.fetchone.return_value = (True,)
        with self.assertRaises(RuntimeError):
            with acquire_tenant_xact_lock(mock_cr, "saas.workspace", 1, 42, timeout_sec=0.0):
                self.assertTrue(is_lock_active("saas.workspace", 1, 42))
                raise RuntimeError("Simulated DB exception")

        self.assertFalse(is_lock_active("saas.workspace", 1, 42))
        self.assertTrue(sp.__exit__.called)

    def test_adv_15_multi_company_tenant_guard(self):
        """
        Verifies @enforce_tenant_isolation:
        - Allowed company succeeds.
        - Cross-tenant company raises AccessError.
        - Under sudo, ambient company_id mismatch without context raises AccessError.
        - Under sudo, ambient company_id match or explicit allowed_company_ids succeeds.
        """
        class DummyRecord:
            def __init__(self, record_id, company_id, env):
                self.id = record_id
                self._name = "industry.showcase.asset"
                self.company_id = company_id
                self.env = env

            @enforce_tenant_isolation(company_field="company_id")
            def execute_mutation(self, payload):
                return f"mutated_{payload}"

        mock_env = MagicMock()
        mock_env.companies.ids = [1, 2]
        mock_env.company.id = 1
        mock_env.su = False
        mock_env.context = {}

        # 1. Allowed company access
        rec_allowed = DummyRecord(101, 1, mock_env)
        self.assertEqual(rec_allowed.execute_mutation("ok"), "mutated_ok")

        rec_allowed2 = DummyRecord(102, 2, mock_env)
        self.assertEqual(rec_allowed2.execute_mutation("ok2"), "mutated_ok2")

        # 2. Cross-tenant company (company 3 is outside [1, 2])
        rec_cross = DummyRecord(103, 3, mock_env)
        with self.assertRaises(AccessError):
            rec_cross.execute_mutation("cross")

        # 3. Sudo mode ambient leakage prevention
        mock_env.su = True
        mock_env.company.id = 1
        mock_env.context = {}

        # Sudo match active company -> succeeds
        rec_sudo_match = DummyRecord(104, 1, mock_env)
        self.assertEqual(rec_sudo_match.execute_mutation("sudo_match"), "mutated_sudo_match")

        # Sudo ambient mismatch (company 2 != active company 1, not in context) -> AccessError
        rec_sudo_leak = DummyRecord(105, 2, mock_env)
        with self.assertRaises(AccessError) as cm:
            rec_sudo_leak.execute_mutation("sudo_leak")
        self.assertIn("Sudo Ambient Company Leakage", str(cm.exception))

        # Sudo ambient mismatch with explicit context allowed_company_ids -> succeeds
        mock_env.context = {"allowed_company_ids": [1, 2]}
        rec_sudo_ctx = DummyRecord(106, 2, mock_env)
        self.assertEqual(rec_sudo_ctx.execute_mutation("sudo_ctx"), "mutated_sudo_ctx")

    def test_adv_15_strict_lock_rpc_separation(self):
        """
        Verifies execute_with_detached_rpc ensures external network RPCs (HSM, SMS, API)
        run strictly outside the database transactional advisory lock.
        """
        mock_cr = MagicMock()
        mock_cr.fetchone.return_value = (True,)
        sp = MagicMock()
        mock_cr.savepoint.return_value = sp
        sp.__enter__.return_value = sp
        sp.__exit__.return_value = None

        rpc_lock_status = None
        db_lock_status = None

        def mock_external_rpc():
            nonlocal rpc_lock_status
            # Audit check: lock must NOT be active during RPC
            rpc_lock_status = is_lock_active("account.move", 1, 777)
            return {"hsm_ticket": "HSM_PASS_2026", "gateway_code": 200}

        def mock_database_mutation(rpc_res):
            nonlocal db_lock_status
            # Audit check: lock MUST be active during DB execution
            db_lock_status = is_lock_active("account.move", 1, 777)
            return f"committed_{rpc_res['hsm_ticket']}"

        result = execute_with_detached_rpc(
            mock_cr,
            "account.move",
            1,
            777,
            rpc_callable=mock_external_rpc,
            db_callable=mock_database_mutation,
            timeout_sec=2.0,
        )

        self.assertEqual(result, "committed_HSM_PASS_2026")
        self.assertFalse(rpc_lock_status, "Lock was unexpectedly active during external RPC")
        self.assertTrue(db_lock_status, "Lock was not active during database mutation")
        self.assertFalse(is_lock_active("account.move", 1, 777), "Lock was not released after execution")
        self.assertTrue(sp.__enter__.called)
        self.assertTrue(sp.__exit__.called)
