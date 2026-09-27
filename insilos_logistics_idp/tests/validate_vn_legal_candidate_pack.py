#!/usr/bin/env python3
"""Fail-closed validation for the VN legal candidate pack and canonical policy hash."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

PACK = Path(__file__).resolve().parents[1] / "config/vn_legal_candidate_pack.json"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PROJECTION_VERSION = "1.0.0"
APPROVALS = ("source_verification", "content_owner", "independent_oracle", "maker", "checker")
ORACLE_CATEGORIES = {"positive", "negative", "boundary", "missing", "stale", "superseded", "cross_company", "conflict"}
ORACLE_OUTCOMES = {"PASS", "BLOCK", "REVIEW", "NOT_APPLICABLE"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def policy_projection(data):
    dossier = data["candidate_acceptance_dossier"]
    return {
        "projection_schema": "insilos.trade_compliance.canonical_policy_projection",
        "projection_schema_version": PROJECTION_VERSION,
        "policy_identity": {
            "policy_family": data.get("policy_family"), "document_identity": dossier.get("document_identity"),
            "jurisdiction": dossier.get("jurisdiction"), "scope_statement": dossier.get("scope_statement"),
        },
        "effective_dates": {"publication_date": dossier.get("publication_date"), "effective_date": dossier.get("effective_date")},
        "source_chain": dossier.get("source_chain"),
        "reviewed_policy": data.get("official_content_review"),
        "rules": data.get("rules"),
        "fail_safe_semantics": {
            "candidate_status": data.get("candidate_status"), "expected_terminal_status": data.get("expected_terminal_status"),
            "legal_authority": data.get("legal_authority"), "activation_allowed": data.get("activation_allowed"),
            "blocker": data.get("blocker"), "missing_context_verdict": "REVIEW",
        },
    }


def policy_sha256(data):
    return hashlib.sha256(canonical(policy_projection(data))).hexdigest()


def oracle_sha256(oracle):
    value = copy.deepcopy(oracle)
    value["canonical_oracle_sha256"] = None
    return hashlib.sha256(canonical(value)).hexdigest()


def pack_binding_sha256(data):
    value = copy.deepcopy(data)
    value["candidate_acceptance_dossier"]["independent_oracle"] = None
    value["independent_oracle_template"]["pack_artifact_sha256"] = None
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_oracle(data, oracle):
    template = data.get("independent_oracle_template", {})
    errors = []
    if oracle.get("schema_id") != template.get("schema_id") or oracle.get("schema_version") != template.get("schema_version"): errors.append("independent oracle schema mismatch")
    if oracle.get("requirement") != "TRADE-02": errors.append("independent oracle requirement mismatch")
    if oracle.get("policy_sha256") != data.get("candidate_acceptance_dossier", {}).get("policy_sha256"): errors.append("independent oracle policy mismatch")
    if oracle.get("pack_artifact_sha256") != pack_binding_sha256(data): errors.append("independent oracle pack binding mismatch")
    official = sorted(item.get("captured_sha256") for item in data.get("official_candidate_evidence", []))
    if sorted(oracle.get("official_source_sha256", [])) != official: errors.append("independent oracle official source mismatch")
    reviewer = oracle.get("reviewer", {})
    identities = [reviewer.get(name) for name in ("identity", "future_maker_identity", "future_checker_identity")] + reviewer.get("known_incompatible_identities", [])
    owner = data.get("candidate_acceptance_dossier", {}).get("content_owner", {}).get("identity")
    if reviewer.get("role") != "independent oracle reviewer" or not all(isinstance(value, str) and value.strip() for value in identities) or len(identities) != len(set(identities)) or owner not in reviewer.get("known_incompatible_identities", []): errors.append("independent oracle reviewer identity separation mismatch")
    if not reviewer.get("reviewed_at_utc") or not reviewer.get("signature_reference"): errors.append("independent oracle signature/reference missing")
    cases = oracle.get("input_cases_without_expected_outcomes", [])
    if len(cases) != 8 or {case.get("case_type") for case in cases} != ORACLE_CATEGORIES or cases != template.get("input_cases_without_expected_outcomes"): errors.append("independent oracle case contract mismatch")
    if oracle.get("case_inputs_sha256") != hashlib.sha256(canonical(template.get("input_cases_without_expected_outcomes"))).hexdigest(): errors.append("independent oracle case hash mismatch")
    results = oracle.get("reviewer_only_results", [])
    if len(results) != 8 or {result.get("case_id") for result in results} != {case.get("case_id") for case in cases}: errors.append("independent oracle results incomplete")
    signatures = []
    for result in results:
        if result.get("expected_outcome") not in ORACLE_OUTCOMES or not result.get("reason") or not result.get("required_evidence"): errors.append("independent oracle outcome contract incomplete"); break
        signatures.append(canonical([result["expected_outcome"], result["reason"], result["required_evidence"]]))
    if signatures and len(set(signatures)) == 1: errors.append("independent oracle outcomes copied")
    if not SHA256.fullmatch(oracle.get("canonical_oracle_sha256") or "") or oracle.get("canonical_oracle_sha256") != oracle_sha256(oracle): errors.append("independent oracle canonical hash mismatch")
    return errors


def _present(value):
    return value is not None and value != "" and value != [] and value != {}


def clean_https(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.netloc) and not any((parsed.username, parsed.password, parsed.query, parsed.fragment))
    except (TypeError, ValueError):
        return False


def validate_source_and_policy(data, require_policy_hash=True):
    errors = []
    dossier = data.get("candidate_acceptance_dossier")
    if not isinstance(dossier, dict): return ["missing candidate_acceptance_dossier"]
    if dossier.get("policy_projection_schema_version") not in (None, PROJECTION_VERSION): errors.append("unsupported policy projection schema version")
    chain = dossier.get("source_chain")
    evidence = {item.get("document_id"): item for item in data.get("official_candidate_evidence", []) if isinstance(item, dict)}
    if not isinstance(chain, list) or not chain: errors.append("missing immutable source_chain")
    for index, source in enumerate(chain if isinstance(chain, list) else []):
        document_id = source.get("document_id")
        matched = evidence.get(document_id)
        landing = urlsplit(source.get("official_landing_page") or "")
        if landing.scheme != "https" or not landing.netloc or landing.username or landing.password or landing.fragment or not clean_https(source.get("official_raw_download")):
            errors.append(f"source_chain[{index}] official URLs must be safe HTTPS")
        if not SHA256.fullmatch(source.get("captured_sha256") or "") or not source.get("articles_reviewed"):
            errors.append(f"source_chain[{index}] missing hash/article evidence")
        if not matched or matched.get("captured_sha256") != source.get("captured_sha256") or matched.get("raw_download_url") != source.get("official_raw_download"):
            errors.append(f"source drift for {document_id}")
        elif matched.get("captured_bytes", 0) <= 0 or matched.get("raw_storage") != "owner_only_quarantine_outside_git":
            errors.append(f"exact source bytes evidence incomplete for {document_id}")
    review = data.get("official_content_review", {})
    citations = review.get("citations") if isinstance(review, dict) else None
    reviewed = {(item.get("document_id"), item.get("article")) for item in citations or [] if isinstance(item, dict)}
    expected = {(source.get("document_id"), article) for source in chain or [] for article in source.get("articles_reviewed", [])}
    if reviewed != expected: errors.append("reviewed article citation drift")
    if any(item.get("outcome") != "REVIEW" or not item.get("fail_safe") for item in citations or []): errors.append("review rules must retain REVIEW and fail-safe semantics")
    day10 = review.get("day_10_support", {})
    if day10.get("status") != "unsupported" or day10.get("terminal_status") != "REVIEW" or day10.get("activation_allowed") is not False:
        errors.append("day-10 unsupported REVIEW semantics drift")
    for rule in data.get("rules", []):
        if rule.get("deadline_days") == 10 and (rule.get("official_support_status"), rule.get("outcome"), rule.get("activation_allowed")) != ("unsupported", "REVIEW", False):
            errors.append(f"day-10 rule drift: {rule.get('code')}")
    expected_hash = dossier.get("policy_sha256")
    if require_policy_hash and (not SHA256.fullmatch(expected_hash or "") or expected_hash != policy_sha256(data)):
        errors.append("policy_sha256 mismatch")
    oracle = dossier.get("independent_oracle")
    if oracle is not None: errors.extend(validate_oracle(data, oracle))
    return errors


def validate(data):
    errors = validate_source_and_policy(data)
    dossier = data.get("candidate_acceptance_dossier", {})
    for field in ("captured_sha256", "publication_date", "effective_date", "recorded_at_utc", "document_identity"):
        if not _present(dossier.get(field)): errors.append(f"missing {field}")
    if not clean_https(dossier.get("citation")): errors.append("citation must be a clean official HTTPS URL")
    for name, fields in {"license": ("status", "terms", "approval_reference"), "retention": ("status", "policy", "approval_reference"),
                         "content_owner": ("status", "identity", "approved_at_utc", "approval_reference")}.items():
        record = dossier.get(name, {})
        if any(not _present(record.get(field)) for field in fields): errors.append(f"incomplete {name}")
        if record.get("status") != "approved": errors.append(f"{name}.status must be approved")
    approvals = dossier.get("approval_statuses", {})
    for name in APPROVALS:
        allowed = {"approved"} if name in ("source_verification", "content_owner") else {"pending", "approved"}
        if approvals.get(name) not in allowed: errors.append(f"approval_statuses.{name} invalid for candidate pack")
    if approvals.get("independent_oracle") == "approved" and not dossier.get("independent_oracle"): errors.append("approved independent oracle artifact missing")
    identities = [dossier.get(role, {}).get("identity") for role in ("content_owner", "independent_oracle_reviewer", "maker", "checker")]
    if all(identities) and len(set(identities)) != len(identities): errors.append("approval role identities must be distinct")
    checklist = {item.get("item"): item for item in data.get("reviewer_checklist", [])}
    for item in ("official_url_verified", "official_document_verified", "official_article_verified", "official_publication_verified", "effective_date_verified", "license_terms_approved", "retention_terms_approved", "content_owner_approved"):
        if checklist.get(item, {}).get("checked") is not True or not checklist[item].get("evidence"):
            errors.append(f"reviewer_checklist.{item} must reflect approved repository evidence")
    for item in ("independent_oracle_completed_and_reviewed", "day_10_conflict_resolved", "maker_checker_are_distinct", "activation_blocker_cleared"):
        if checklist.get(item, {}).get("checked") is not False or checklist[item].get("evidence") is not None:
            errors.append(f"reviewer_checklist.{item} must remain externally blocked")
    if data.get("legal_authority") is not False or data.get("activation_allowed") is not False: errors.append("candidate pack must remain non-authoritative and activation-blocked")
    return errors


def self_check():
    data = json.loads(PACK.read_text(encoding="utf-8"))
    dossier = data["candidate_acceptance_dossier"]
    if dossier.get("policy_sha256"):
        assert dossier["policy_sha256"] == policy_sha256(data)
    assert not validate(data), "current candidate/pending pack must remain valid"
    assert data["activation_allowed"] is False and dossier["activation_allowed"] is False
    probes = {
        "policy drift after approval": lambda x: x["rules"][0].update(outcome="PASS"),
        "source/rule drift": lambda x: x["candidate_acceptance_dossier"]["source_chain"][0].update(captured_sha256="0" * 64),
        "hash self-reference": lambda x: x["candidate_acceptance_dossier"].update(policy_sha256="0" * 64),
        "oracle mismatch": lambda x: x["candidate_acceptance_dossier"].update(independent_oracle={"policy_sha256": "0" * 64}),
        "false oracle approval": lambda x: x["candidate_acceptance_dossier"]["approval_statuses"].update(independent_oracle="approved"),
        "stale completed checklist": lambda x: x["reviewer_checklist"][0].update(checked=False, evidence=None),
        "false external checklist closure": lambda x: x["reviewer_checklist"][7].update(checked=True, evidence="self-approved"),
    }
    for name, mutate in probes.items():
        changed = copy.deepcopy(data); mutate(changed)
        assert validate(changed), f"accepted red probe: {name}"
    projection = policy_projection(data)
    assert "policy_sha256" not in json.dumps(projection) and "approval_statuses" not in json.dumps(projection)
    print("SELF-CHECK PASS: canonical projection and drift probes")


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("path", nargs="?", type=Path, default=PACK); parser.add_argument("--self-check", action="store_true"); args = parser.parse_args()
    if args.self_check: self_check(); return
    errors = validate(json.loads(args.path.read_text(encoding="utf-8")))
    if errors:
        print(f"RED: {args.path}"); [print(f"- {error}") for error in errors]; raise SystemExit(1)
    print(f"PASS: {args.path}")

if __name__ == "__main__": main()
