# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import threading
import uuid
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install', 'concurrency', 'security')
class TestAdversarialSaaSProvisioning(TransactionCase):

    def test_concurrent_16_threads_subdomain_squatting(self):
        """
        Adversarial Concurrency Stress Test:
        16 concurrent threads attempt to provision the exact same subdomain simultaneously.
        DISM-TRL Invariant:
          - Exactly 1 winner acquires the advisory lock and provisions the workspace.
          - Exactly 15 contestants are rejected with either 'system_busy' (lock contention)
            or 'subdomain_taken' (TOCTOU double-check / unique constraint violation).
          - Zero deadlock, zero duplicate records in saas.workspace.
        """
        subdomain = f"audit3-test-{uuid.uuid4().hex[:8]}"
        results = []
        errors = []
        lock = threading.Lock()

        def worker(thread_idx):
            with self.env.registry.cursor() as cr:
                env = self.env(cr=cr)
                try:
                    ws = env['saas.workspace'].provision_atomic(
                        subdomain=subdomain,
                        idempotency_key=f"key-{thread_idx}",
                    )
                    cr.commit()
                    with lock:
                        results.append((thread_idx, ws.id))
                except UserError as e:
                    with lock:
                        errors.append((thread_idx, str(e)))
                except Exception as e:
                    with lock:
                        errors.append((thread_idx, f"unexpected_{type(e).__name__}_{e}"))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 1, f"Expected exactly 1 winner, got {len(results)}: {results}")
        self.assertEqual(len(errors), 15, f"Expected 15 rejected, got {len(errors)}: {errors}")
        for thread_idx, err in errors:
            self.assertIn(err, ('system_busy', 'subdomain_taken'), f"Unexpected error code: {err}")

        # Invariant: exactly 1 workspace exists
        self.assertEqual(
            self.env['saas.workspace'].search_count([('subdomain', '=', subdomain)]),
            1,
            "Exactly one saas.workspace record must exist for the contested subdomain"
        )
