#!/usr/bin/env python3
"""Validate or capture immutable WP6 tc_gov evidence; capture requires --write."""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
REPO = MODULE.parents[2]
TEST_MODULES = {
    "odoo.addons.insilos_logistics_idp.tests": MODULE / "tests",
    "odoo.addons.insilos_knowledge_graph.tests": REPO / "insilos/apps/insilos_knowledge_graph/tests",
}
ARTIFACTS = MODULE / "docs/tests"
TYPES = {
    "tc_gov_activation", "tc_gov_migration_rollback", "tc_gov_policy_diff_preview",
    "tc_gov_policy_import", "tc_gov_requirement_delta", "tc_gov_rule_evidence",
    "tc_gov_security_negative",
}
COMMON = {"schema_version", "generated_at_utc", "run_started_at_utc", "run_ended_at_utc",
          "start_ns", "end_ns", "elapsed_ns", "limit_ns", "within_4h",
          "environment", "commit_sha", "artifact_type", "status", "commands", "expected", "actual",
          "failures", "blockers", "exclusions", "artifact_sha256_scope", "artifact_sha256",
          "source_sha256", "worktree_dirty", "worktree_hash_scope", "worktree_status_sha256",
          "worktree_diff_sha256"}
ENVIRONMENT = {"scope", "database", "module", "module_version", "non_production", "external_calls"}
UTC_LIKE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
COMMIT_SHA = re.compile(r"^[0-9a-f]{7,64}$", re.I)
DB = "insilos_migration_digiforce_v2"
BASE = ["python3", "tools/with_local_credentials.py", "--solo-dev-db", "--", "python3",
        "insilos/insilos-bin", "-c", "insilos.conf", "-d", DB, "--test-enable", "--stop-after-init",
        "--workers=0", "--max-cron-threads=0", "--addons-path=insilos/addons,insilos/apps", "--http-port=18179",
        "--log-level=test"]
SUITES = {
    "configuration": "/insilos_logistics_idp:TestLogisticsIdpConfiguration",
    "security": "/insilos_logistics_idp:TestLogisticsIdpSecurity",
    "concurrency": "+logistics_idp_concurrency",
    "runtime": "/insilos_logistics_idp:TestLogisticsIdpRuntime",
}
ARTIFACT_SUITES = {
    "tc_gov_requirement_delta": ("runtime",),
    "tc_gov_activation": ("configuration", "security"),
    "tc_gov_migration_rollback": ("configuration",),
    "tc_gov_policy_diff_preview": ("configuration",),
    "tc_gov_policy_import": ("configuration", "security"),
    "tc_gov_rule_evidence": ("configuration", "runtime"),
    "tc_gov_security_negative": ("security", "configuration"),
}
ARTIFACT_SOURCES = {
    "tc_gov_activation": ("models/logistics_idp.py", "tests/test_logistics_idp_configuration.py", "tests/test_logistics_idp_concurrency.py", "tests/test_logistics_idp_security.py"),
    "tc_gov_migration_rollback": ("models/logistics_idp.py", "tests/test_logistics_idp_configuration.py", "tests/test_logistics_idp_concurrency.py"),
    "tc_gov_policy_diff_preview": ("models/logistics_idp.py", "tests/test_logistics_idp_configuration.py"),
    "tc_gov_policy_import": ("models/logistics_idp.py", "tests/test_logistics_idp_configuration.py", "tests/test_logistics_idp_security.py"),
    "tc_gov_rule_evidence": ("models/logistics_idp.py", "tests/test_logistics_idp_configuration.py", "tests/test_logistics_idp_runtime.py"),
    "tc_gov_security_negative": ("models/logistics_idp.py", "tests/test_logistics_idp_configuration.py", "tests/test_logistics_idp_security.py"),
    "tc_gov_requirement_delta": ("services/reconciliation.py", "tests/golden/build_sanitized_corpus.py", "tests/test_logistics_idp_phase_1_3.py", "tests/test_logistics_idp_runtime.py", "docs/tests/srs_canonical_crosswalk_v1.json"),
}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical_hash(data):
    data = dict(data)
    data.pop("artifact_sha256", None)
    return digest(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True).stdout


def current_worktree(scope):
    if scope == "module":
        paths = [str(MODULE.relative_to(REPO))]
    elif scope == "module_excluding_tc_gov_artifacts":
        module = str(MODULE.relative_to(REPO))
        paths = [module, f":(exclude){module}/docs/tests/tc_gov_*.json"]
    elif isinstance(scope, list) and all(isinstance(path, str) and path for path in scope):
        paths = scope
    else:
        return None
    return (digest(git("status", "--porcelain", "--", *paths)), digest(git("diff", "--binary", "HEAD", "--", *paths)))


def has_dirty_provenance(data):
    return (data.get("worktree_dirty") is True and data.get("worktree_hash_scope") is not None
            and isinstance(data.get("worktree_status_sha256"), str) and isinstance(data.get("worktree_diff_sha256"), str))


def validate_data(data, path):
    errors = []
    if not isinstance(data, dict): return ["JSON root must be object"]
    for field in sorted(COMMON - data.keys()): errors.append(f"schema missing {field}")
    for field in sorted(COMMON & data.keys()):
        if data[field] is None: errors.append(f"schema null {field}")
    for field in ("generated_at_utc", "run_started_at_utc", "run_ended_at_utc"):
        if not isinstance(data.get(field), str) or not UTC_LIKE.fullmatch(data[field]): errors.append(f"schema {field} must be UTC Z")
    start_ns, end_ns, elapsed_ns, limit_ns = (data.get(field) for field in ("start_ns", "end_ns", "elapsed_ns", "limit_ns"))
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in (start_ns, end_ns, elapsed_ns, limit_ns)): errors.append("schema nanosecond timing integers")
    elif elapsed_ns != end_ns - start_ns or limit_ns != 4 * 60 * 60 * 1_000_000_000 or data.get("within_4h") is not (elapsed_ns <= limit_ns): errors.append("timing arithmetic/boolean mismatch")
    if not isinstance(data.get("commands"), list) or not data["commands"] or any(not isinstance(x, str) or not x.strip() for x in data["commands"]): errors.append("schema commands must be non-empty list")
    for field in ("expected", "actual", "failures", "blockers", "exclusions"):
        if field not in data: errors.append(f"schema missing {field}")
    if not isinstance(data.get("actual"), dict): errors.append("schema actual must be object")
    for field in ("failures", "blockers", "exclusions"):
        if not isinstance(data.get(field), list): errors.append(f"schema {field} must be list")
    if not (isinstance(data.get("commit_sha"), str) and COMMIT_SHA.fullmatch(data["commit_sha"])) and not has_dirty_provenance(data): errors.append("schema commit_sha or dirty worktree provenance")
    env = data.get("environment")
    if not isinstance(env, dict): errors.append("schema environment must be object")
    else:
        for field in sorted(ENVIRONMENT):
            if env.get(field) is None: errors.append(f"schema environment missing {field}")
        if env.get("module") != "insilos_logistics_idp": errors.append("schema environment.module")
    if data.get("artifact_type") == "tc_gov_activation" and data.get("status") != "BLOCKED_APPROVED_POLICY_DATASET": errors.append("legal activation must remain blocked")
    if data.get("artifact_type") == "tc_gov_requirement_delta":
        delta = data.get("requirement_delta")
        if not isinstance(delta, list) or len(delta) != 310 or any(not isinstance(x, dict) or not x.get("srs_id") or "baseline_status" not in x or "after_status" not in x for x in delta): errors.append("schema requirement_delta must preserve 310 rows")
        elif not requirement_delta_matches_canonical_ids(delta): errors.append("requirement delta does not match canonical SRS crosswalk")
    return errors


def validate(path):
    try: data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc: return [f"JSON: {exc}"]
    errors = validate_data(data, path)
    env = data.get("environment")
    if data.get("artifact_type") != path.stem or path.stem not in TYPES: errors.append("schema artifact_type")
    if data.get("artifact_sha256_scope") != "canonical JSON excluding artifact_sha256": errors.append("schema artifact_sha256_scope")
    if data.get("artifact_sha256") != canonical_hash(data): errors.append("integrity artifact_sha256")
    try: manifest = json.loads((MODULE / "__manifest__.py").read_text().split("#", 1)[-1])
    except json.JSONDecodeError:
        import ast
        manifest = ast.literal_eval("\n".join((MODULE / "__manifest__.py").read_text().splitlines()[1:]))
    if not isinstance(env, dict) or env.get("module_version") != manifest["version"]: errors.append("stale module_version")
    sources = data.get("source_sha256")
    if not isinstance(sources, dict) or not sources: errors.append("stale source_sha256 missing")
    else:
        for relative, expected in sources.items():
            source = MODULE / relative
            if not source.is_file() or digest(source.read_bytes()) != expected: errors.append(f"stale source {relative}")
    current = current_worktree(data.get("worktree_hash_scope"))
    if current is None or current != (data.get("worktree_status_sha256"), data.get("worktree_diff_sha256")): errors.append("stale scoped worktree")
    return errors


def utc_now(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
def shell(command): return " ".join(command)
def suite_command(name): return [*BASE, "--test-tags", SUITES[name]]

def parse_success(output):
    matches = re.findall(r"insilos\.tests\.result:\s*(\d+)\s+failed,\s*(\d+)\s+error\(s\)\s+of\s+(\d+)\s+tests", output, re.I)
    if not matches: raise ValueError("không phân tích được dòng kết quả chuẩn Insilos")
    failed, errors, total = map(int, matches[-1])
    if failed or errors or not total: raise ValueError(f"kết quả test không thành công: {failed} failed, {errors} errors, {total} tests")
    return {"passed": total, "failed": failed, "errors": errors, "total": total}

def capture_suite(name):
    command = suite_command(name)
    result = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
    if result.returncode:
        return shell(command), None, f"exit={result.returncode}; output_sha256={digest((result.stdout + result.stderr).encode())}"
    try: return shell(command), parse_success(result.stdout + result.stderr), None
    except ValueError as exc: return shell(command), None, str(exc)

def source_hashes(kind):
    paths = ("__manifest__.py", *ARTIFACT_SOURCES[kind])
    return {path: digest((MODULE / path).read_bytes()) for path in paths}

def module_version():
    import ast
    return ast.literal_eval("\n".join((MODULE / "__manifest__.py").read_text().splitlines()[1:]))["version"]

def capture_corpus():
    command = ["python3", str(MODULE / "tests/golden/build_sanitized_corpus.py"), "--verify"]
    result = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
    if result.returncode:
        return shell(command), None, f"exit={result.returncode}; output_sha256={digest((result.stdout + result.stderr).encode())}"
    corpus = json.loads((MODULE / "tests/golden/sanitized_cases.json").read_text())
    return shell(command), {"verified": True, "manifest_sha256": corpus["manifest_sha256"], "cases": len(corpus["cases"])}, None


def canonical_requirement_ids():
    spec = importlib.util.spec_from_file_location("build_sanitized_corpus", MODULE / "tests/golden/build_sanitized_corpus.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    raw = builder.authoritative_srs_inventory([], ())
    _, governed = builder.canonical_srs_crosswalk(raw["items"])
    if raw["coverage_counts"]["total"] != 311 or len(governed) != 310:
        raise ValueError("canonical SRS crosswalk count mismatch")
    return governed


def requirement_delta_matches_canonical_ids(rows):
    return {row["srs_id"] for row in rows} == canonical_requirement_ids()


def refresh_requirement_delta(data):
    rows = data["requirement_delta"]
    if len(rows) != 310 or len({row["srs_id"] for row in rows}) != 310:
        raise ValueError("authoritative requirement mapping must contain 310 unique rows")
    if not requirement_delta_matches_canonical_ids(rows):
        raise ValueError("requirement delta does not match canonical SRS crosswalk")
    test_sources = {}
    for row in rows:
        for test_id in row["executable_test_ids"]:
            match = re.fullmatch(r"(insilos\.addons\.(?:insilos_logistics_idp|insilos_knowledge_graph)\.tests)\.(test_[^.]+)\.[^.]+\.(test_[^.]+)", test_id)
            if not match or match[1] not in TEST_MODULES:
                raise ValueError(f"unsupported canonical test ID: {test_id}")
            path = TEST_MODULES[match[1]] / f"{match[2]}.py"
            source = path.read_text()
            if not re.search(rf"^\s+def {re.escape(match[3])}\(", source, re.M):
                raise ValueError(f"stale canonical test ID: {test_id}")
            test_sources[str(path.relative_to(REPO))] = digest(path.read_bytes())
        evidence = {key: row[key] for key in ("srs_id", "baseline_status", "after_status", "tc_gov_ids", "implementation_symbols", "executable_test_ids", "remaining_or_deferred_reason")}
        evidence["test_source_sha256"] = {path: test_sources[path] for path in sorted(test_sources) if any(f".{Path(path).stem}." in test_id for test_id in row["executable_test_ids"])}
        row["evidence_hash"] = digest(json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
    counts = {status: sum(row["after_status"] == status for row in rows) for status in ("achieved", "partial", "missing")}
    if sum(counts.values()) != 310: raise ValueError(f"unsupported requirement status: {counts}")
    data["expected"].update(counts, unique_srs_ids=len({row["srs_id"] for row in rows}))
    data["actual"].update(counts, total=len(rows), unique_srs_ids=len({row["srs_id"] for row in rows}))
    data["cumulative"].update(counts, total=len(rows))


def capture_artifact(kind, existing, captures, started, ended):
    selected = [(name, captures[name]) for name in ARTIFACT_SUITES[kind]]
    commands = [capture[0] for _, capture in selected]
    failures = [capture[2] for _, capture in selected if capture[2]]
    actual = dict(existing.get("actual", {}))
    actual["local_captures"] = {name: capture[1] for name, capture in selected if capture[1] is not None}
    if kind == "tc_gov_requirement_delta":
        corpus = captures["corpus"]
        commands.append(corpus[0])
        if corpus[2]: failures.append(corpus[2])
        elif corpus[1] is not None: actual["local_captures"]["corpus"] = corpus[1]
    worktree = current_worktree("module_excluding_tc_gov_artifacts")
    data = dict(existing)
    data.setdefault("expected", {}); data.setdefault("failures", []); data.setdefault("blockers", []); data.setdefault("exclusions", [])
    environment = dict(existing["environment"])
    environment["module_version"] = module_version()
    data.update({"schema_version": "1.1", "environment": environment, "generated_at_utc": ended, "run_started_at_utc": started, "run_ended_at_utc": ended,
                 "commit_sha": git("rev-parse", "HEAD").decode().strip(), "worktree_dirty": True, "worktree_hash_scope": "module_excluding_tc_gov_artifacts",
                 "worktree_status_sha256": worktree[0], "worktree_diff_sha256": worktree[1], "source_sha256": source_hashes(kind),
                 "commands": commands, "expected": existing.get("expected", {}), "actual": actual, "failures": failures,
                 "blockers": list(existing.get("blockers", [])), "exclusions": list(existing.get("exclusions", [])),
                 "artifact_sha256_scope": "canonical JSON excluding artifact_sha256"})
    if kind == "tc_gov_activation":
        data["status"] = "BLOCKED_APPROVED_POLICY_DATASET"; data["content_status"] = "BLOCKED_APPROVED_POLICY_DATASET"
    if kind == "tc_gov_requirement_delta": refresh_requirement_delta(data)
    data["artifact_sha256"] = canonical_hash(data)
    return data

def self_check():
    sample = {"z": 1, "artifact_sha256": "ignored", "a": [True]}
    assert canonical_hash(sample) == canonical_hash({"a": [True], "z": 1})
    assert canonical_hash(sample) != canonical_hash({"a": [False], "z": 1})
    assert "schema missing expected" in validate_data({}, Path("tc_gov_policy_import.json"))
    timing = {field: None for field in COMMON}
    timing.update(start_ns=1787466372321813331, end_ns=1787467928341344380, elapsed_ns=1556019531049, limit_ns=14400000000000, within_4h=True)
    assert "timing arithmetic/boolean mismatch" not in validate_data(timing, Path("tc_gov_policy_import.json"))
    timing["within_4h"] = False
    assert "timing arithmetic/boolean mismatch" in validate_data(timing, Path("tc_gov_policy_import.json"))
    assert parse_success("odoo.tests.result: 0 failed, 0 error(s) of 3 tests") == {"passed": 3, "failed": 0, "errors": 0, "total": 3}
    delta = json.loads((ARTIFACTS / "tc_gov_requirement_delta.json").read_text())
    original = [row["srs_id"] for row in delta["requirement_delta"]]
    refresh_requirement_delta(delta)
    assert [row["srs_id"] for row in delta["requirement_delta"]] == original
    falsified = json.loads((ARTIFACTS / "tc_gov_requirement_delta.json").read_text())
    falsified["requirement_delta"].append(dict(falsified["requirement_delta"][0]))
    try: refresh_requirement_delta(falsified)
    except ValueError: pass
    else: raise AssertionError("duplicate requirement falsification accepted")
    falsified = json.loads((ARTIFACTS / "tc_gov_requirement_delta.json").read_text())
    falsified["requirement_delta"][0]["srs_id"] = "SRS-SECTION-4-2-2-T-NH-KH-THI-TRI-N-KHAI-DOANH-NGHI-P"
    assert "requirement delta does not match canonical SRS crosswalk" in validate_data(falsified, Path("tc_gov_requirement_delta.json"))
    try: refresh_requirement_delta(falsified)
    except ValueError: pass
    else: raise AssertionError("crosswalk mismatch falsification accepted")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--write", action="store_true"); parser.add_argument("--write-non-delta", action="store_true"); parser.add_argument("--write-delta-provenance", action="store_true")
    args = parser.parse_args()
    if args.self_check: self_check(); print("SELF-CHECK PASS"); return
    if args.dry_run:
        for kind, suites in ARTIFACT_SUITES.items():
            if kind == "tc_gov_requirement_delta": print(f"{kind}: EXCLUDED_DELTA_LOGICAL_MAPPING")
            else: print(f"{kind}: " + " | ".join(shell(suite_command(suite)) for suite in suites))
        return
    if args.write:
        started = utc_now()
        captures = {suite: capture_suite(suite) for suite in SUITES}
        captures["corpus"] = capture_corpus(); ended = utc_now()
        generated = {}
        for kind in ARTIFACT_SUITES:
            path = ARTIFACTS / f"{kind}.json"
            generated[path] = capture_artifact(kind, json.loads(path.read_text()), captures, started, ended)
        failures = [failure for data in generated.values() for failure in data["failures"]]
        if failures: raise SystemExit("capture failed: " + "; ".join(dict.fromkeys(failures)))
        for path, data in generated.items(): path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return
    if args.write_delta_provenance:
        kind = "tc_gov_requirement_delta"; started = utc_now()
        captures = {"runtime": capture_suite("runtime"), "corpus": capture_corpus()}; ended = utc_now()
        path = ARTIFACTS / f"{kind}.json"
        data = capture_artifact(kind, json.loads(path.read_text()), captures, started, ended)
        if data["failures"]: raise SystemExit("capture failed: " + "; ".join(data["failures"]))
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return
    if args.write_non_delta:
        kinds = tuple(kind for kind in ARTIFACT_SUITES if kind != "tc_gov_requirement_delta")
        started = utc_now(); captures = {suite: capture_suite(suite) for suite in dict.fromkeys(suite for kind in kinds for suite in ARTIFACT_SUITES[kind])}; ended = utc_now()
        for kind in kinds:
            path = ARTIFACTS / f"{kind}.json"
            path.write_text(json.dumps(capture_artifact(kind, json.loads(path.read_text()), captures, started, ended), indent=2, ensure_ascii=False) + "\n")
        return
    paths = sorted(ARTIFACTS.glob("tc_gov_*.json")); failures = 0
    for path in paths:
        errors = validate(path); failures += bool(errors); print(f"{'FAIL' if errors else 'PASS'} {path.name}" + (": " + "; ".join(errors) if errors else ""))
    for missing in sorted(TYPES - {path.stem for path in paths}): failures += 1; print(f"FAIL {missing}.json: artifact missing")
    print(f"WP6 evidence: {len(paths)}/7 artifacts, {'FAIL' if failures else 'PASS'}"); raise SystemExit(bool(failures))

if __name__ == "__main__": main()
