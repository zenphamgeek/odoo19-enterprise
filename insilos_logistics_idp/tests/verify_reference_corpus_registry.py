#!/usr/bin/env python3
"""Fail-closed deterministic anti-drift checks; never performs network I/O."""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "reference_corpus_registry.json"
CORPUS = HERE / "golden/sanitized_cases.json"
UAT = HERE / "../docs/tests/development_uat_result.json"
QA = HERE / "../docs/tests/qa_baseline_approval.json"
PARITY_REPORT = HERE / "../docs/tests/swarovski_srs_parity_coverage_20260907.json"
EXPORTER = ROOT / "tools/export_digiforce_idp.js"
PROVENANCE = {"type", "source_hash", "sanitization_class", "oracle_version"}
GOVERNED_CASES_SCHEMA = "insilos.logistics_idp.governed_cases/1.0.0"
COMPLIANCE_POLICY = ROOT / "insilos/apps/insilos_logistics_idp/config/compliance_policy.json"
TRACKER = ROOT / ".trae/documents/tracking/MASTER_TRACKER.md"
SECRET = re.compile(r"(?:\b(?:authorization|proxy-authorization)\s*[:=]\s*(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}|\b(?:cookie|set-cookie|session(?:_id)?|access_token|refresh_token|api[_-]?key|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{8,}|https?://[^\s'\"]+[?&](?:x-amz-signature|signature|sig|token|access_token|session)=[^\s'\"]+)", re.I)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text())

def validate_governed_cases(registry, corpus_path=CORPUS, policy_path=COMPLIANCE_POLICY, tracker_path=TRACKER):
    cases = registry.get("governed_cases")
    if registry.get("governed_cases_schema") != GOVERNED_CASES_SCHEMA or not isinstance(cases, list): return ["governed cases schema"]
    by_id = {case.get("id"): case for case in cases if isinstance(case, dict)}
    if set(by_id) != {"Case01", "Case02"} or len(cases) != 2: return ["governed cases inventory"]
    errors = []
    case01, case02 = by_id["Case01"], by_id["Case02"]
    try:
        corpus = load(corpus_path)
        capability = next(item for item in corpus["engine_capability_tests"] if item["test_id"] == "ENGINE-SYNTHETIC-MULTI-ATTACHMENT-001")
    except (OSError, json.JSONDecodeError, KeyError, StopIteration) as exc:
        return [f"governed case source: {exc}"]
    if case01.get("evidence_class") != "synthetic" or case01.get("outcome") != "PASS" or case01.get("source_sha256") != sha(corpus_path): errors.append("Case01 synthetic evidence/hash")
    if case01.get("claim_scope") != capability.get("claim_scope") or capability.get("provenance_type") != "synthetic": errors.append("Case01 claim scope")
    if case02.get("evidence_class") != "source_limit" or case02.get("outcome") != "REVIEW" or case02.get("reason") != "multi_attachment:not_observed/source_limit": errors.append("Case02 source_limit REVIEW")
    if case02.get("policy_source_sha256") != sha(policy_path): errors.append("Case02 policy hash")
    tracker = tracker_path.read_text()
    if "multi-attachment `not_observed/source_limit`" not in tracker and "multi-attachment source limitation" not in tracker: errors.append("Case02 tracker source limit")
    for case in cases:
        if case.get("customer_approval") is not None: errors.append(f"{case.get('id')} customer approval fabrication")
        if case.get("raw_data_included") is not False: errors.append(f"{case.get('id')} raw data boundary")
    return errors


def capabilities(source):
    match = re.search(r"const CAPABILITIES = \[(.*?)\n\];", source, re.S)
    if not match: raise ValueError("CAPABILITIES missing")
    rows = re.findall(r"\{ name: \"([^\"]+)\", endpoint: ([^,]+), required: (true|false), statuses: \[([^]]+)\], schema: \"([^\"]+)\" \}", match.group(1))
    resolved = {"DOCUMENTS_ENDPOINT": "/api/documents:list", "OPTIONAL_ENDPOINTS[0]": "/api/purchase_order_item_lines_new:list", "OPTIONAL_ENDPOINTS[1]": "/api/information_compare_logs:list", '"same-origin attachment URLs"': "same-origin attachment URLs"}
    result = []
    for name, endpoint, required, statuses, schema in rows:
        endpoint = resolved.get(endpoint.strip(), endpoint.strip().strip('"'))
        result.append({"name": name, "endpoint": endpoint, "required": required == "true", "statuses": [int(x.strip()) for x in statuses.split(",")], "schema": schema})
    return result

def validate_internal_readiness(registry_path=REGISTRY, corpus_path=CORPUS, uat_path=UAT, report_path=PARITY_REPORT):
    errors = []
    try:
        registry, corpus, uat, report = load(registry_path), load(corpus_path), load(uat_path), load(report_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"internal readiness artifact: {exc}"]
    gate = next((item for item in registry.get("gates", []) if item.get("id") == "internal_reference_readiness"), {})
    if gate.get("execution_mode") != "local_ci_deterministic_synthetic": errors.append("internal readiness mode")
    if "not external parity" not in gate.get("provenance", ""): errors.append("internal readiness claim boundary")
    if report.get("claim_boundary", {}).get("formal_swarovski_parity") != "not_claimable": errors.append("internal readiness formal parity claim")
    metrics = report.get("metrics", {})
    readiness = metrics.get("internal_reference_readiness", {})
    if readiness.get("status") != "PASS" or readiness.get("evidence_class") != "synthetic_self_oracle": errors.append("internal readiness verdict")
    if readiness.get("corpus_sha256") != sha(corpus_path) or readiness.get("corpus_manifest_sha256") != corpus.get("manifest_sha256"): errors.append("internal readiness corpus hash")
    if readiness.get("uat_sha256") != sha(uat_path): errors.append("internal readiness UAT hash")
    if uat.get("detailed_case_counts") != {"passed": 198, "failed": 0, "not_run": 0, "skipped": 0}: errors.append("internal readiness detailed UAT")
    if uat.get("golden_counts") != {"passed": 46, "partial": 2, "failed": 0, "not_run": 0, "skipped": 0}: errors.append("internal readiness Golden UAT")
    oracle = readiness.get("self_oracle", {})
    expected = {item["scenario_id"]: item["oracle"]["sha256"] for item in corpus.get("cases", [])}
    if oracle.get("algorithm") != "sha256" or oracle.get("case_count") != 198 or oracle.get("case_oracles") != expected:
        errors.append("internal readiness self-oracle")
    runtime = report.get("verification", {}).get("runtime_playwright", {})
    if runtime.get("status") != "PASS" or any(runtime.get(key) != 0 for key in ("console_errors", "page_errors", "network_errors")):
        errors.append("internal readiness runtime evidence")
    return errors


def validate(registry_path=REGISTRY, corpus_path=CORPUS, uat_path=UAT, qa_path=QA, exporter_path=EXPORTER):
    errors = []
    try: registry = load(registry_path)
    except (OSError, json.JSONDecodeError) as exc: return [f"registry: {exc}"]
    if registry.get("schema_version") != 2 or registry.get("provenance_schema_version") != 1: errors.append("registry schema")
    errors.extend(validate_governed_cases(registry, corpus_path))
    gates = registry.get("gates")
    required = {"corpus_build_verify", "uat", "qa_baseline", "wp6", "exporter_self_check_capability_lint", "authenticated_external_parity", "internal_reference_readiness"}
    if not isinstance(gates, list) or {gate.get("id") for gate in gates if isinstance(gate, dict)} != required: errors.append("registry required gates")
    for gate in gates if isinstance(gates, list) else []:
        if not isinstance(gate.get("artifacts"), list) or not isinstance(gate.get("verifier"), str) or not gate.get("execution_mode") or not gate.get("provenance"): errors.append(f"registry gate {gate.get('id')}")
        for artifact in gate.get("artifacts", []):
            if not isinstance(artifact, str) or not (ROOT / artifact).is_file(): errors.append(f"registry artifact {artifact}")
    external = next((gate for gate in gates if isinstance(gate, dict) and gate.get("id") == "authenticated_external_parity"), {})
    if external.get("execution_mode") != "non_ci_authenticated_external_not_executable_local": errors.append("external boundary")
    try:
        corpus, uat, qa = load(corpus_path), load(uat_path), load(qa_path)
        if corpus.get("schema_version") != 6 or not corpus.get("metadata", {}).get("synthetic") or corpus.get("metadata", {}).get("non_production") is not True: errors.append("corpus provenance schema")
        manifest = corpus.get("manifest_sha256")
        if not isinstance(manifest, str) or len(manifest) != 64: errors.append("corpus manifest")
        if uat.get("source", {}).get("corpus_manifest_sha256") != manifest or qa.get("source", {}).get("corpus_manifest_sha256") != manifest: errors.append("mixed corpus manifest")
        if uat.get("source", {}).get("corpus_file_sha256") != sha(corpus_path) or qa.get("source", {}).get("synthetic_corpus_sha256") != sha(corpus_path): errors.append("stale corpus hash")
        if qa.get("source", {}).get("development_result_sha256") != sha(uat_path): errors.append("stale UAT hash")
        for case in corpus.get("cases", []):
            provenance = case.get("provenance", {})
            if set(provenance) != PROVENANCE or provenance.get("type") != "synthetic" or provenance.get("source_hash") != case.get("artifact", {}).get("sha256"): errors.append("case provenance"); break
            try: payload = base64.b64decode(case["artifact"]["content"], validate=True)
            except (KeyError, ValueError): errors.append("case artifact encoding"); break
            if SECRET.search(payload.decode("utf8", "ignore")): errors.append("secret in corpus artifact"); break
    except (OSError, json.JSONDecodeError, KeyError) as exc: errors.append(f"local artifact: {exc}")
    try:
        caps = capabilities(exporter_path.read_text())
        expected = {"documents", "purchase_order_lines", "comparison_logs", "attachments"}
        if {row["name"] for row in caps} != expected or len(caps) != 4: errors.append("capabilities coverage")
        for row in caps:
            if not isinstance(row["required"], bool) or not row["endpoint"] or row["schema"] not in {"list", "binary"} or not row["statuses"] or any(status < 100 or status > 599 for status in row["statuses"]): errors.append("capabilities structure")
        docs = next((row for row in caps if row["name"] == "documents"), {})
        if docs != {"name": "documents", "endpoint": "/api/documents:list", "required": True, "statuses": [200], "schema": "list"}: errors.append("documents capability")
        for row in caps:
            if row["required"] is False and set(row["statuses"]) - {200, 404, 405}: errors.append("optional status policy")
        if "function itemsFrom(" not in exporter_path.read_text() or "function schemaOf(" not in exporter_path.read_text(): errors.append("synthetic schema observation unavailable")
        result = subprocess.run(["node", str(exporter_path), "--self-check"], cwd=ROOT, text=True, capture_output=True)
        if result.returncode or '"selfCheck":"passed"' not in result.stdout: errors.append("exporter self-check")
    except (OSError, ValueError) as exc: errors.append(f"capabilities: {exc}")
    for path in (registry_path, corpus_path, uat_path, qa_path):
        if path.is_file() and SECRET.search(path.read_text(errors="ignore")): errors.append(f"secret scan {path.name}")
    return errors

def self_check():
    assert not validate(), validate()
    with tempfile.TemporaryDirectory() as directory:
        registry = Path(directory) / "registry.json"; registry.write_text(REGISTRY.read_text())
        bad = load(registry); bad["gates"] = bad["gates"][1:]; registry.write_text(json.dumps(bad)); assert "registry required gates" in validate(registry)
        bad = load(REGISTRY); bad["governed_cases"][0]["customer_approval"] = "fabricated"; registry.write_text(json.dumps(bad)); assert "Case01 customer approval fabrication" in validate(registry)
        bad = load(REGISTRY); bad["governed_cases"][1]["outcome"] = "PASS"; registry.write_text(json.dumps(bad)); assert "Case02 source_limit REVIEW" in validate(registry)
        bad = load(REGISTRY); bad["governed_cases"][0]["source_sha256"] = "0" * 64; registry.write_text(json.dumps(bad)); assert "Case01 synthetic evidence/hash" in validate(registry)
        bad = load(REGISTRY); bad["governed_cases"][1]["raw_data_included"] = True; registry.write_text(json.dumps(bad)); assert "Case02 raw data boundary" in validate(registry)
    with tempfile.TemporaryDirectory() as directory:
        exporter = Path(directory) / "exporter.js"; exporter.write_text(EXPORTER.read_text().replace('required: true', 'required: false', 1)); assert "documents capability" in validate(exporter_path=exporter)
    with tempfile.TemporaryDirectory() as directory:
        corpus = Path(directory) / "corpus.json"; corpus.write_text(CORPUS.read_text()); bad = load(corpus); bad["cases"][0]["provenance"].pop("oracle_version"); corpus.write_text(json.dumps(bad)); assert "case provenance" in validate(corpus_path=corpus)
        corpus.write_text(CORPUS.read_text()); bad = load(corpus); bad["cases"][0]["artifact"]["content"] = base64.b64encode(b"Authorization: Bearer abcdefghijklmnop").decode(); corpus.write_text(json.dumps(bad)); assert "secret in corpus artifact" in validate(corpus_path=corpus)
    print("Reference corpus anti-drift self-check: PASS")

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--self-check", action="store_true"); parser.add_argument("--governed-cases", action="store_true"); parser.add_argument("--internal-readiness", action="store_true"); options = parser.parse_args()
    if options.self_check: self_check(); return
    if options.internal_readiness:
        errors = validate_internal_readiness()
        if errors: raise SystemExit("Internal reference readiness: FAIL " + "; ".join(sorted(set(errors))))
        print("Internal reference readiness: PASS")
        return
    if options.governed_cases:
        errors = validate_governed_cases(load(REGISTRY))
        if errors: raise SystemExit("Governed cases: FAIL " + "; ".join(sorted(set(errors))))
        print("Governed cases: PASS")
        return
    errors = validate()
    if errors: raise SystemExit("Reference corpus anti-drift: FAIL " + "; ".join(sorted(set(errors))))
    print("Reference corpus anti-drift: PASS")

if __name__ == "__main__": main()
