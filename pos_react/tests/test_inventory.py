import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from types import SimpleNamespace

MODULE = Path(__file__).parents[1]
ROOT = MODULE.parents[2]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, MODULE / f"tools/{name}.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


generate_inventory = load_tool("generate_inventory")
collect_compiled_bundle = load_tool("collect_compiled_bundle")


def validate_phase2_port_evidence(evidence):
    if set(evidence) != {"artifacts", "database", "module", "phase", "result", "test", "timing"}:
        raise ValueError("invalid evidence fields")
    expected_paths = {
        "insilos/apps/pos_barcodelookup/__manifest__.py",
        "insilos/apps/pos_barcodelookup/static/src/pos_react_plugin.js",
        "insilos/apps/pos_barcodelookup/tests/test_pos_barcodelookup_start.py",
    }
    if set(evidence["artifacts"]) != expected_paths or any(
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        for digest in evidence["artifacts"].values()
    ):
        raise ValueError("invalid historical artifact provenance")
    timing = evidence["timing"]
    if set(timing) != {"start_ns", "end_ns", "elapsed_ns", "limit_ns", "within_4h"}:
        raise ValueError("invalid timing fields")
    start_ns, end_ns, elapsed_ns, limit_ns = (
        timing[field] for field in ("start_ns", "end_ns", "elapsed_ns", "limit_ns")
    )
    if not all(type(value) is int for value in (start_ns, end_ns, elapsed_ns, limit_ns)):
        raise ValueError("invalid nanosecond timing integers")
    if elapsed_ns != end_ns - start_ns or limit_ns != 4 * 60 * 60 * 1_000_000_000:
        raise ValueError("invalid timing arithmetic")
    if type(timing["within_4h"]) is not bool or timing["within_4h"] is not (elapsed_ns <= limit_ns):
        raise ValueError("invalid four-hour limit")
    return evidence


def validate_phase3_slice_evidence(evidence):
    fields = {"schema_version", "phase", "scope", "priority", "status", "phase3_pass_claim", "invariants", "runs", "test_cases", "totals", "sha256"}
    run_fields = {"database", "port", "browser_tests", "browser_passed", "browser_failed", "node_graph_tests", "node_graph_passed", "abort_count", "sync_call_count", "order_count", "line_count", "payment_count", "strict_ack", "cleanup"}
    count_fields = ("browser_tests", "browser_passed", "browser_failed", "node_graph_tests", "node_graph_passed", "abort_count", "sync_call_count", "order_count", "line_count", "payment_count")
    identities = [("tmp_pos_react_c174edd5", 19800), ("tmp_posreact_a362dd2a", 19801), ("tmp_posreact_f560d542", 19802), ("tmp_posreact_a7b54236", 19803), ("tmp_posreact_5663c867", 19804), ("tmp_posreact_6b47140d", 19805), ("tmp_posreact_4eb4b769", 19806), ("tmp_posreact_c6b985ed", 19807), ("tmp_posreact_86fc672b", 19808), ("tmp_posreact_63fc59cc", 19809)]
    invariants = {"hardened": True, "strict_ack": "fail_closed", "committed_response_abort": "idempotent_retry_no_duplicate", "offline_queue": "tenant_user_session_scoped", "payload_integrity": "sha256_tamper_blocked", "poison_order": "blocked_retained", "metadata_cache": "validated_scoped_fallback", "retry_policy": "exponential_backoff_capped_attempt_8_blocked", "recovery": "deadline_respected_targeted_retry_tamper_scope_blocked", "schema_v4": "draft_identity_immutable_atomic_commit_scope_isolated"}
    test_cases = [f"TestPosReactBrowser.{name}" for name in ("test_realtime_websocket_protocol_and_lifecycle", "test_remote_finalization_locks_local_draft", "test_missed_notification_reconciles_when_online", "test_cold_reload_renders_cached_shell_and_catalog", "test_same_tab_hard_reload_preserves_draft_identity_and_checkout_graph", "test_sync_retry_after_committed_response_abort", "test_app_retry_lifecycle_respects_deadline", "test_offline_store_reconnect_during_failing_drain", "test_offline_store_poison_reload_and_payload_tamper", "test_offline_store_v4_draft_kernel", "test_offline_store_scope_isolation_and_forgery", "test_metadata_cache_upgrade_fallback_and_scope_isolation", "test_offline_records_atomic_replace_cleanup_and_fallback", "test_pos_react_browser", "test_pos_react_offline_store", "test_pos_react_offline_store_retry_policy")]
    if set(evidence) != fields or (evidence["schema_version"], evidence["phase"], evidence["scope"], evidence["priority"], evidence["status"], evidence["phase3_pass_claim"]) != (4, 3, "data_and_offline_kernel_slice", "P0", "SLICE_PASS_PHASE_OPEN", False) or evidence["invariants"] != invariants:
        raise ValueError("invalid phase3 evidence envelope")
    if len(evidence["runs"]) != 10 or len(set(identities)) != 10 or evidence["test_cases"] != test_cases:
        raise ValueError("invalid phase3 run or test inventory")
    for run, identity in zip(evidence["runs"], identities):
        if set(run) != run_fields or (run["database"], run["port"]) != identity:
            raise ValueError("invalid phase3 run identity")
        if any(type(run[field]) is not int for field in count_fields) or run["strict_ack"] is not True or run["cleanup"] is not True:
            raise ValueError("invalid phase3 run types or hardened gates")
        if tuple(run[field] for field in count_fields) != (16, 16, 0, 1, 1, 1, 2, 1, 1, 1):
            raise ValueError("invalid phase3 run result")
    totals = evidence["totals"]
    expected_totals = {field: sum(run[field] for run in evidence["runs"]) for field in count_fields}
    expected_totals.update(strict_ack_runs=sum(run["strict_ack"] for run in evidence["runs"]), cleaned_databases=sum(run["cleanup"] for run in evidence["runs"]), remaining_databases=0)
    if totals != expected_totals or totals != {"browser_tests": 160, "browser_passed": 160, "browser_failed": 0, "node_graph_tests": 10, "node_graph_passed": 10, "abort_count": 10, "sync_call_count": 20, "order_count": 10, "line_count": 10, "payment_count": 10, "strict_ack_runs": 10, "cleaned_databases": 10, "remaining_databases": 0}:
        raise ValueError("invalid phase3 aggregate")
    if set(evidence["sha256"]) != {"kernel", "app", "graph", "service_worker", "controller", "browser_test", "graph_test"}:
        raise ValueError("invalid phase3 artifact roles")
    for artifact in evidence["sha256"].values():
        if set(artifact) != {"path", "digest"} or not isinstance(artifact["path"], str) or not isinstance(artifact["digest"], str) or len(artifact["digest"]) != 64:
            raise ValueError("invalid phase3 artifact")
        path = ROOT / artifact["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != artifact["digest"]:
            raise ValueError("phase3 artifact digest mismatch")
    return evidence


class InventoryTest(unittest.TestCase):
    def test_phase3_slice_evidence(self):
        evidence = validate_phase3_slice_evidence(json.loads((MODULE / "phase3_slice_evidence.json").read_text(encoding="utf-8")))
        self.assertFalse(evidence["phase3_pass_claim"])

    def test_phase3_slice_evidence_fails_closed(self):
        evidence = json.loads((MODULE / "phase3_slice_evidence.json").read_text(encoding="utf-8"))
        invalid = json.loads(json.dumps(evidence))
        invalid["totals"]["passed"] = 39
        with self.assertRaises(ValueError):
            validate_phase3_slice_evidence(invalid)
        invalid = json.loads(json.dumps(evidence))
        invalid["phase3_pass_claim"] = True
        with self.assertRaises(ValueError):
            validate_phase3_slice_evidence(invalid)

    def test_phase2_port_evidence(self):
        evidence = validate_phase2_port_evidence(json.loads((MODULE / "phase2_port_evidence.json").read_text(encoding="utf-8")))
        self.assertEqual(evidence["database"], "tmp_pos_react_011fbfeb")
        self.assertEqual(evidence["module"], "pos_barcodelookup")
        self.assertEqual((evidence["phase"], evidence["result"]), (2, "PASS"))
        self.assertEqual(evidence["test"], {
            "case": "TestPOSReactPlugin.test_action_matches_legacy_permissions_authentication_and_services",
            "summary": "Ran 1 test\n\nOK",
        })
        expected_paths = {
            "insilos/apps/pos_barcodelookup/__manifest__.py",
            "insilos/apps/pos_barcodelookup/static/src/pos_react_plugin.js",
            "insilos/apps/pos_barcodelookup/tests/test_pos_barcodelookup_start.py",
        }
        self.assertEqual(set(evidence["artifacts"]), expected_paths)
        self.assertTrue(all(len(digest) == 64 for digest in evidence["artifacts"].values()))
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("historical provenance must not read mutable sources")):
            self.assertIs(validate_phase2_port_evidence(evidence), evidence)

    def test_phase2_port_evidence_fails_closed(self):
        evidence = json.loads((MODULE / "phase2_port_evidence.json").read_text(encoding="utf-8"))
        for missing in evidence:
            invalid = evidence.copy()
            invalid.pop(missing)
            with self.assertRaises(ValueError):
                validate_phase2_port_evidence(invalid)
        for field, value in (("elapsed_ns", 2), ("limit_ns", 14399), ("within_4h", False), ("start_ns", True)):
            invalid = json.loads(json.dumps(evidence))
            invalid["timing"][field] = value
            with self.assertRaises(ValueError):
                validate_phase2_port_evidence(invalid)

    def test_inventory_is_complete_and_reproducible(self):
        actual = generate_inventory.generate()
        expected = json.loads((MODULE / "inventory.json").read_text(encoding="utf-8"))

        self.assertEqual(actual, expected)
        self.assertEqual(actual["direct_dependency_count"], 66)
        self.assertEqual(len({item["module"] for item in actual["dependencies"]}), 66)
        self.assertEqual(actual["schema_version"], 2)
        self.assertGreater(actual["baseline"]["expanded_source_bytes"], 0)
        self.assertGreater(actual["baseline"]["expanded_source_gzip_bytes"], 0)
        self.assertLess(actual["baseline"]["expanded_source_gzip_bytes"], actual["baseline"]["expanded_source_bytes"])
        self.assertTrue(all(item["extension_classification"] for item in actual["dependencies"]))
        owners = {item["owner"] for item in actual["capabilities"]}
        self.assertTrue({"core", "pos_sale", "pos_restaurant", "Enterprise"} <= owners)
        self.assertTrue(all(item["status"] in {"Inventoried", "Blocked"} for item in actual["capabilities"]))
        self.assertTrue(all(item["oracle_tests"] or item["blocker"] == "missing_oracle" for item in actual["capabilities"]))
        for item in actual["dependencies"]:
            for path in item["oracle_paths"]:
                self.assertTrue((generate_inventory.ROOT / path).is_file(), path)

    def test_unknown_bundle_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown asset bundle"):
            generate_inventory.expand_bundle("point_of_sale", "point_of_sale.missing", {"point_of_sale": {}})


class FakeRecordset(list):
    def sudo(self):
        return self

    def search(self, domain):
        urls = set(domain[0][2])
        return FakeRecordset(item for item in self if item.url in urls)


class FakeEnv(dict):
    cr = SimpleNamespace(dbname="test")


class CompiledBundleEvidenceTest(unittest.TestCase):
    def test_parser_collects_and_gate_accepts_compiled_artifact(self):
        url = "/web/assets/abc/point_of_sale.assets_prod.min.js?cache=1"
        attachment = SimpleNamespace(url=url.split("?")[0], name="pos.min.js", mimetype="application/javascript", raw=b"compiled")
        bundle = SimpleNamespace(js=lambda: attachment, css=lambda: [])
        env = FakeEnv({
            "ir.qweb": SimpleNamespace(
                _get_asset_links=lambda bundle, debug: [(url, None)],
                _get_asset_bundle=lambda *args, **kwargs: bundle,
            ),
            "ir.attachment": FakeRecordset([attachment]),
        })

        evidence = collect_compiled_bundle.collect(env, "2026-08-23T00:00:00+00:00")

        self.assertEqual(evidence["artifacts"][0]["bytes"], 8)
        self.assertEqual(len(evidence["artifacts"][0]["sha256"]), 64)
        self.assertEqual(collect_compiled_bundle.validate(evidence), evidence)
        self.assertEqual(
            collect_compiled_bundle.parse_links([("/insilos/assets/abc/pos.min.js", None)]),
            ["/web/assets/abc/pos.min.js"],
        )

    def test_parser_and_gate_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "no attachment URLs"):
            collect_compiled_bundle.parse_links([(None, "inline")])
        with self.assertRaisesRegex(ValueError, "no artifacts"):
            collect_compiled_bundle.validate({
                "schema_version": 1,
                "bundle": collect_compiled_bundle.BUNDLE,
                "database": "test",
                "collected_at": "2026-08-23T00:00:00+00:00",
                "artifacts": [],
            })

    def test_schema_and_cli_gate(self):
        schema = json.loads(collect_compiled_bundle.SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["bundle"]["const"], collect_compiled_bundle.BUNDLE)
        payload = {
            "schema_version": 1,
            "bundle": collect_compiled_bundle.BUNDLE,
            "database": "test",
            "collected_at": "2026-08-23T00:00:00+00:00",
            "artifacts": [{"url": "/a.js", "name": "a.js", "mimetype": "application/javascript", "bytes": 1, "sha256": "0" * 64}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            collect_compiled_bundle.main(["--check", str(path)])


if __name__ == "__main__":
    unittest.main()
