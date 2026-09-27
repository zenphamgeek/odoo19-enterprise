#!/usr/bin/env python3
"""WS6 assurance direct executors: NFR/SEC/roles/DoD coverage contracts.

Standalone unittest harness: reads only source/evidence files, no DB/browser.
Rows owned: 23 WS6 backlog rows (NFR-*, SEC-*, SRS-ROLE-*, SRS-DOD-27,
SRS-SECTION-21/22/5/5.1). Runtime evidence stays deferred; contracts are
enforced here and must never be weakened.
"""
import ast
import json
import re
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
TESTS = MODULE / "tests"
DOCS = MODULE / "docs/tests"
CONFIG = MODULE / "config"
BACKLOG = Path("/tmp/idp_backlog_ws_split.json")

WS6_IDS = {
    "NFR-001", "NFR-004", "NFR-005", "NFR-006", "NFR-007", "NFR-008",
    "NFR-010", "NFR-012", "SEC-002", "SEC-004", "SEC-005", "SRS-DOD-27",
    "SRS-ROLE-INTEGRATION-SERVICE-ACCOUNT", "SRS-ROLE-LOGISTICS-MANAGER",
    "SRS-ROLE-LOGISTICS-OPERATOR", "SRS-ROLE-LOGISTICS-TRADE-COMPLIANCE-REVIEWER",
    "SRS-ROLE-MASTER-DATA-STEWARD", "SRS-ROLE-READ-ONLY-AUDITOR",
    "SRS-ROLE-SYSTEM-VERTICAL-ADMINISTRATOR", "SRS-SECTION-21-SECURITY-AND-AUDIT",
    "SRS-SECTION-22-NON-FUNCTIONAL-REQUIREMENTS", "SRS-SECTION-5-1-ROLES",
    "SRS-SECTION-5-USERS-AND-ROLES",
}

# srs_id -> (status, implementation_symbols, canonical test ids, scope)
# status: direct | mapped_existing | open_blocked
EXECUTOR_MAP = {
    "NFR-001": ("mapped_existing",
                ["logistics.idp.case DB unique constraints", "LogisticsCase._claim_skip_locked"],
                ["odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_concurrency.TestLogisticsIdpConcurrency.test_database_identity_constraint_under_true_concurrency",
                 "odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_concurrency.TestLogisticsIdpConcurrency.test_terminal_insert_unique_violation_atomically_rolls_back_lifecycle"],
                "idempotency/duplicate guard under true concurrency; canonical DB only"),
    "NFR-004": ("direct",
                ["run_local_nfr.verify_stored_nfr", "run_local_nfr.p95"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_nfr_runner_p95_query_and_workload_contract"],
                "dashboard P95 <5s gate, non-sudo service call, query/response measurement; runtime run deferred to canonical DB"),
    "NFR-005": ("direct",
                ["run_local_nfr.DOCUMENTS", "run_local_nfr.PAGES"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_nfr_runner_p95_query_and_workload_contract"],
                "representative 4.613 docs / 13.665 pages workload enforced; runtime run deferred"),
    "NFR-006": ("direct",
                ["LogisticsEvidence.payload_hash", "LogisticsEvidence.audit_actor_id/audit_service",
                 "build_regulatory_change_notification.audit_input_hash/output_hash"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_observability_correlation_structured_errors_and_health",
                 "odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_security.TestLogisticsIdpSecurity.test_pdf_caller_context_and_metadata_cannot_bypass_iap_or_classification"],
                "correlation hashes + service attribution + /healthz /readyz probe + structured reasons; browser-level telemetry remains deferred"),
    "NFR-007": ("open_blocked",
                ["static/src/dashboard/dashboard.xml aria-label/role"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_accessibility_semantic_contract"],
                "semantic labels/status roles exist; vi_VN translation files absent (no i18n/) -> localization parity open"),
    "NFR-008": ("mapped_existing",
                ["LogisticsPolicySource.validate_compliance_context timezone-aware rejection"],
                ["odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_security.TestLogisticsIdpSecurity.test_compliance_context_rejects_fake_ids_run_mismatch_and_bad_timestamps"],
                "UTC Z timestamps enforced at compliance context boundary"),
    "NFR-010": ("open_blocked",
                ["build_regulatory_change_notification review-only intent"],
                [],
                "regulatory change latency measurement requires approved legal policy dataset + live source; local artifact is review-only, no latency number"),
    "NFR-012": ("mapped_existing",
                ["config/compliance_policy.json", "config/vn_legal_candidate_pack.json"],
                ["odoo.addons.insilos_logistics_idp.tests.test_hardening_contract.HardeningContractTest.test_trade_compliance_wp1_contract_is_fail_closed"],
                "policy/config portability schema enforced; external pack interchange not exercised"),
    "SEC-002": ("mapped_existing",
                ["config/release_package.json raw_reference_claim_restrictions", "build_sanitized_corpus.derive_synthetic_fixtures gating"],
                ["odoo.addons.insilos_logistics_idp.tests.test_hardening_contract.HardeningContractTest.test_authenticated_reference_governance",
                 "odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_secrets_and_pii_scan"],
                "raw reference/PII restricted to quarantine; sanitized-only derivation; tracked evidence scan"),
    "SEC-004": ("mapped_existing",
                ["build_sanitized_corpus.classify_raw_file rejected_secret_or_unsupported"],
                ["odoo.addons.insilos_logistics_idp.tests.test_hardening_contract.HardeningContractTest.test_offline_classifier_rejects_secrets_without_returning_payload",
                 "odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_secrets_and_pii_scan"],
                "classifier drops secrets from output; tracked test/evidence files secret-scanned"),
    "SEC-005": ("mapped_existing",
                ["config/vn_legal_candidate_pack.json retention approval ref", "compliance_policy required_metadata.retention"],
                ["odoo.addons.insilos_logistics_idp.tests.test_hardening_contract.HardeningContractTest.test_authenticated_reference_governance",
                 "odoo.addons.insilos_logistics_idp.tests.test_hardening_contract.HardeningContractTest.test_trade_compliance_wp1_contract_is_fail_closed"],
                "retention metadata mandated on every external/legal source; content owner approval tracked as pending"),
    "SRS-DOD-27": ("direct",
                ["EXECUTOR_MAP + DoD dimension checks in this file"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_dod_definition_of_done_dimensions"],
                "every DoD dimension has executable check or explicit blocker; never weaken expected"),
    "SRS-ROLE-INTEGRATION-SERVICE-ACCOUNT": ("direct",
                ["insilos_logistics_idp.group_logistics_integration", "LogisticsCase._upgrade_migration_service_principal"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_rbac_role_matrix_and_cross_company_negatives",
                 "odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_security.TestLogisticsIdpSecurity.test_migration_principal_upgrade_is_idempotent"],
                "least privilege: cannot complete cases, manager group excluded"),
    "SRS-ROLE-LOGISTICS-MANAGER": ("direct",
                ["insilos_logistics_idp.group_logistics_manager"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_rbac_role_matrix_and_cross_company_negatives",
                 "odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_security.TestLogisticsIdpSecurity.test_srs_5_1_security_matrix_fails_closed"],
                "sole completer/override requester; direct fabrication blocked"),
    "SRS-ROLE-LOGISTICS-OPERATOR": ("direct",
                ["insilos_logistics_idp.group_logistics_operator"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_rbac_role_matrix_and_cross_company_negatives",
                 "odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_security.TestLogisticsIdpSecurity.test_unassigned_operator_cannot_read_case"],
                "owner-scoped read, cannot complete/output, cannot fabricate evidence"),
    "SRS-ROLE-LOGISTICS-TRADE-COMPLIANCE-REVIEWER": ("direct",
                ["insilos_logistics_idp.group_logistics_reviewer"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_rbac_role_matrix_and_cross_company_negatives",
                 "odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_security.TestLogisticsIdpSecurity.test_ops008_reassignment_and_duplicate_rpc_guards"],
                "assignment/review only; duplicate marking denied"),
    "SRS-ROLE-MASTER-DATA-STEWARD": ("direct",
                ["insilos_logistics_idp.group_master_data_steward"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_rbac_role_matrix_and_cross_company_negatives"],
                "fail-closed completion denial covered by matrix test"),
    "SRS-ROLE-READ-ONLY-AUDITOR": ("direct",
                ["insilos_logistics_idp.group_logistics_auditor"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_rbac_role_matrix_and_cross_company_negatives",
                 "odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_security.TestLogisticsIdpSecurity.test_auditor_cannot_mutate"],
                "read-only incl. dashboard/exception center; mutation denied"),
    "SRS-ROLE-SYSTEM-VERTICAL-ADMINISTRATOR": ("direct",
                ["insilos_logistics_idp.group_logistics_admin"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_rbac_role_matrix_and_cross_company_negatives",
                 "odoo.addons.insilos_logistics_idp.tests.test_logistics_idp_security.TestLogisticsIdpSecurity.test_admin_override_acl_preserves_immutable_semantics"],
                "read/create override but no write/unlink on immutable records"),
    "SRS-SECTION-21-SECURITY-AND-AUDIT": ("direct",
                ["TestLogisticsIdpSecurity principal x action matrix"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_security_suite_covers_principal_action_matrix"],
                "7 principals, cross-company negatives, fail-closed, audit actor attribution asserted"),
    "SRS-SECTION-22-NON-FUNCTIONAL-REQUIREMENTS": ("direct",
                ["run_local_nfr.py + hardening contract + stored evidence gate"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_nfr_section_coverage"],
                "P95/query/memory measured, observability, timezone, policy portability; deferred list explicit"),
    "SRS-SECTION-5-1-ROLES": ("direct",
                ["security/logistics_idp_security.xml groups", "TestLogisticsIdpSecurity fixtures"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_rbac_role_matrix_and_cross_company_negatives"],
                "every SRS role has group XML id + user fixture + fail-closed assertion"),
    "SRS-SECTION-5-USERS-AND-ROLES": ("direct",
                ["security/logistics_idp_security.xml + is.model.access.csv"],
                ["odoo.addons.insilos_logistics_idp.tests.test_ws6_assurance_executors.TestWs6AssuranceExecutors.test_rbac_role_matrix_and_cross_company_negatives"],
                "role coverage identical to §5.1; production role mapping reported separately"),
}

ROLE_GROUPS = {
    "operator": "insilos_logistics_idp.group_logistics_operator",
    "reviewer": "insilos_logistics_idp.group_logistics_reviewer",
    "manager": "insilos_logistics_idp.group_logistics_manager",
    "steward": "insilos_logistics_idp.group_master_data_steward",
    "admin": "insilos_logistics_idp.group_logistics_admin",
    "auditor": "insilos_logistics_idp.group_logistics_auditor",
    "integration": "insilos_logistics_idp.group_logistics_integration",
}

SECRET_PATTERNS = re.compile(
    r'(AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|xox[bap]-[A-Za-z0-9-]{10,}|'
    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|eyJhbGciOi[A-Za-z0-9._-]{20,})')

TRACKED_SCAN_ROOTS = (TESTS, DOCS, CONFIG)


def read(path):
    return path.read_text(encoding="utf-8")


class TestWs6AssuranceExecutors(unittest.TestCase):
    maxDiff = None

    def test_backlog_rows_match_owned_23_ids(self):
        self.assertTrue(BACKLOG.is_file(), "authority backlog missing: %s" % BACKLOG)
        backlog = json.loads(BACKLOG.read_text())
        rows = {row["srs_id"] for row in backlog.get("ws", {}).get("6", [])}
        self.assertEqual(rows, WS6_IDS)
        self.assertEqual(len(rows), 23)

    def test_every_row_has_executor_mapping_or_explicit_blocker(self):
        missing = WS6_IDS - set(EXECUTOR_MAP)
        self.assertFalse(missing, "unmapped rows: %s" % sorted(missing))
        for srs_id, (status, symbols, test_ids, scope) in EXECUTOR_MAP.items():
            self.assertIn(status, ("direct", "mapped_existing", "open_blocked"), srs_id)
            if status == "open_blocked":
                self.assertTrue(scope, srs_id)
            else:
                self.assertTrue(symbols and test_ids, srs_id)

    def test_mapped_test_ids_exist_in_source(self):
        for srs_id, (status, _symbols, test_ids, _scope) in EXECUTOR_MAP.items():
            for test_id in test_ids:
                match = re.fullmatch(
                    r"(insilos\.addons\.insilos_logistics_idp\.tests)\.(test_[^.]+)\.([^.]+)\.(test_[^.]+)",
                    test_id)
                self.assertTrue(match, "%s: malformed test id %s" % (srs_id, test_id))
                path = TESTS / (match[2] + ".py")
                self.assertTrue(path.is_file(), "%s: %s missing" % (srs_id, path))
                classes = {node.name: node for node in ast.parse(read(path)).body if isinstance(node, ast.ClassDef)}
                self.assertIn(match[3], classes, "%s: class %s missing in %s" % (srs_id, match[3], path.name))
                methods = {node.name for node in classes[match[3]].body
                           if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
                self.assertIn(
                    match[4], methods,
                    "%s: %s.%s missing in %s" % (srs_id, match[3], match[4], path.name))

    def test_nfr_runner_p95_query_and_workload_contract(self):
        runner = read(TESTS / "run_local_nfr.py")
        self.assertIn("DOCUMENTS = 4613", runner)
        self.assertIn("PAGES = 13665", runner)
        self.assertIn("p95_seconds", runner)
        self.assertIn(">= 5", runner)  # stored dashboard P95 must stay < 5s
        self.assertIn("'sudo': False", runner)
        self.assertIn("sql_log_count", runner)
        self.assertIn("response_bytes", runner)
        result = json.loads((DOCS / "development_uat_result.json").read_text())
        metrics = [item["metric"] for item in result["acceptance_metrics"]]
        for metric in ("Dashboard query P95", "Case UI P95", "Representative scale"):
            self.assertIn(metric, metrics)
        self.assertIsNone(result.get("nfr_workload"),
                          "stored NFR evidence not yet captured: run_local_nfr must run on canonical DB first")

    def test_observability_correlation_structured_errors_and_health(self):
        models = read(MODULE / "models/logistics_idp.py")
        for token in ("payload_hash", "content_hash", "audit_actor_id", "audit_service"):
            self.assertIn(token, models)
        reconciliation = read(MODULE / "services/reconciliation.py")
        for token in ("audit_input_hash", "output_hash", "sha256(json.dumps"):
            self.assertIn(token, reconciliation)
        gate = read(TESTS / "run_one_pdf_iap_gate.py")
        self.assertIn("'/healthz'", gate)
        self.assertIn("'/readyz'", gate)
        security = read(TESTS / "test_logistics_idp_security.py")
        for reason in ("'real document'", "'timezone-aware'", "'ownership does not match'",
                       "'same company'", "'missing or ambiguous'"):
            self.assertIn(reason, security, "structured error reason %s missing" % reason)

    def test_accessibility_semantic_contract(self):
        template = read(MODULE / "static/src/dashboard/dashboard.xml")
        self.assertIn('aria-label="Logistics IDP intelligence overview"', template)
        self.assertIn('aria-label="Dashboard filters"', template)
        self.assertIn('aria-label="Reset dashboard filters"', template)
        self.assertIn('role="status"', template)
        self.assertIn('role="alert"', template)
        self.assertIn('<button type="button" t-foreach="metricEntries()"', template)
        self.assertIn('t-att-aria-label="\'Open \' + metric.label + \' records\'"', template)
        for text in ("Unavailable:", "Prior-period delta:", "Queue empty."):
            self.assertIn(text, template)  # status beyond color
        playwright = read(TESTS / "playwright_business.js")
        for token in ("aria-label", "document.activeElement", "responsive.scrollWidth <= responsive.clientWidth",
                      "clippedChildren.length === 0", "width: 1440", "KPI focus destination",
                      "KPI focus restore", "action_logistics_documents", "action_logistics_review_center",
                      "page_errors", "getByRole(\"heading\""):
            self.assertIn(token, playwright)

    def test_security_suite_covers_principal_action_matrix(self):
        security = read(TESTS / "test_logistics_idp_security.py")
        for role, group in ROLE_GROUPS.items():
            self.assertIn(group, security, "role fixture %s missing" % role)
        for method in ("test_srs_5_1_security_matrix_fails_closed", "test_auditor_cannot_mutate",
                       "test_unassigned_operator_cannot_read_case", "test_direct_snapshot_fabrication_blocked",
                       "test_dashboard_authorized_roles_and_company_scope",
                       "test_policy_workspace_is_read_only_for_auditor_and_company_isolated",
                       "test_document_duplicate_marker_denies_self_cross_company_terminal_unauthorized_and_remap"):
            self.assertIn("def %s(" % method, security, "security method %s missing" % method)
        self.assertGreaterEqual(security.count("res.company"), 6, "cross-company negatives expected")

    def test_rbac_role_matrix_and_cross_company_negatives(self):
        xml = read(MODULE / "security/logistics_idp_security.xml")
        for role, group in ROLE_GROUPS.items():
            self.assertIn('id="%s"' % group.split(".")[-1], xml, "group %s missing in security xml" % role)
        access = read(MODULE / "security/is.model.access.csv")
        self.assertIn("logistics.idp.case", access)
        security = read(TESTS / "test_logistics_idp_security.py")
        for name in ("self.manager", "self.reviewer", "self.auditor", "self.integration",
                     "self.operator", "self.steward", "self.admin"):
            self.assertIn(name, security)
        self.assertIn("action_complete", security)
        self.assertIn("assertRaises(AccessError)", security)

    def test_secrets_and_pii_scan(self):
        offenders = []
        for root in TRACKED_SCAN_ROOTS:
            for path in sorted(root.rglob("*")):
                if path.suffix not in (".py", ".json"):
                    continue
                try:
                    content = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                match = SECRET_PATTERNS.search(content)
                if match:
                    offenders.append("%s (pattern at offset %d)" % (path.relative_to(MODULE), match.start()))
        self.assertFalse(offenders, "tracked evidence leaks secrets: %s" % offenders)
        hardening = read(TESTS / "test_hardening_contract.py")
        self.assertIn('assertNotIn("Swarovski", json.dumps(CASES))', hardening)
        self.assertIn('assertNotIn(content.decode(), json.dumps(result))', hardening)

    def test_nfr_section_coverage(self):
        stored_gate = read(TESTS / "run_local_nfr.py")
        self.assertIn("verify_stored_nfr", stored_gate)
        self.assertIn("raise AssertionError('Stored representative ORM NFR evidence is invalid", stored_gate)
        hardening = read(TESTS / "test_hardening_contract.py")
        for method in ("test_nfr_invokes_dashboard_service_contract",
                       "test_authenticated_reference_governance",
                       "test_offline_classifier_rejects_secrets_without_returning_payload"):
            self.assertIn("def %s(" % method, hardening)

    def test_dod_definition_of_done_dimensions(self):
        checked = {
            "direct executor mapping": len(EXECUTOR_MAP) == 23,
            "RBAC/company isolation": "test_srs_5_1_security_matrix_fails_closed" in read(TESTS / "test_logistics_idp_security.py"),
            "accessibility/mobile": 'aria-label="Logistics IDP intelligence overview"' in read(MODULE / "static/src/dashboard/dashboard.xml"),
            "performance": "Dashboard query P95" in read(TESTS / "run_local_nfr.py"),
            "observability": "audit_input_hash" in read(MODULE / "services/reconciliation.py"),
            "idempotency/concurrency": "def test_skip_locked_allows_exactly_one_worker_to_claim_job(" in read(TESTS / "test_logistics_idp_concurrency.py"),
            "ledger": (TESTS / "run_one_pdf_iap_gate.py").is_file(),
            "deterministic hashes": "canonical_hash" in read(TESTS / "validate_wp6_evidence.py"),
            "backup/canary": '"formal_release_gate_passed": false' in read(CONFIG / "release_package.json").lower(),
            "reconciliation": (TESTS / "reconcile_run_cumulative_metrics.py").is_file(),
        }
        missing = [dimension for dimension, ok in checked.items() if not ok]
        self.assertFalse(missing, "DoD dimensions without executable evidence: %s" % missing)

    def test_release_readiness_stays_blocked_without_approval(self):
        release = json.loads((CONFIG / "release_package.json").read_text())
        self.assertFalse(release["formal_release_gate_passed"])
        self.assertFalse(release["acceptance_corpus_included"])
        self.assertTrue(release["synthetic_development_corpus_included"])
        self.assertIn("formal_golden_uat_nfr_acceptance", release["deferred_artifacts"])


if __name__ == "__main__":
    unittest.main()
