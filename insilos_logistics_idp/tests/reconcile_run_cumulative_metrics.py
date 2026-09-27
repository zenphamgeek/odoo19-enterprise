import argparse
import copy
import json
from pathlib import Path

DIMENSIONS = {
    "source_records": ("discovered", "fetched", "unique", "failed", "skipped"),
    "documents": ("accepted", "pass", "review", "error", "quarantined"),
    "attachments": ("discovered", "downloaded", "rejected"),
    "pages": ("discovered", "processed", "failed"),
    "extraction_runs": ("attempted", "succeeded", "review", "error"),
    "detailed_golden": ("detailed_pass", "detailed_fail", "golden_pass", "golden_fail", "unmapped"),
    "iap_ledger": ("holds", "consumes", "releases", "refunds"),
    "trigger": ("attempts", "retries", "dead_letter"),
    "parity": ("pass", "fail", "mismatch"),
}


def _blank(status="unavailable"):
    return {group: {metric: {"status": status, "value": None} for metric in metrics}
            for group, metrics in DIMENSIONS.items()}


def _set(target, group, metric, value):
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        target[group][metric] = {"status": "available", "value": value}


def _observed(payload):
    observed = _blank()
    records = payload.get("records")
    inventory = payload.get("source_inventory")
    if isinstance(inventory, dict):
        total = inventory.get("records")
        rejected = inventory.get("attachment_rejected_records")
        for metric in ("discovered", "fetched", "unique"):
            _set(observed, "source_records", metric, total)
        _set(observed, "source_records", "failed", rejected)
    if isinstance(records, list):
        _set(observed, "documents", "accepted", len(records))
        for status in ("pass", "review", "error", "quarantined"):
            _set(observed, "documents", status, sum(row.get("terminal_status") == status for row in records if isinstance(row, dict)))
        if not isinstance(inventory, dict):
            _set(observed, "pages", "discovered", sum(row.get("pages", 0) for row in records if isinstance(row, dict) and isinstance(row.get("pages", 0), int)))
        _set(observed, "detailed_golden", "unmapped", sum(row.get("oracle_status") != "independently_approved" for row in records if isinstance(row, dict)))
    document = payload.get("document")
    if isinstance(document, dict):
        _set(observed, "documents", "accepted", 1)
        status = {"valid": "pass", "review": "review", "error": "error"}.get(document.get("status"))
        if status:
            for metric in ("pass", "review", "error", "quarantined"):
                _set(observed, "documents", metric, int(metric == status))
        _set(observed, "extraction_runs", "attempted", int(document.get("run_id") is not None))
        for metric in ("succeeded", "review", "error"):
            mapped = "succeeded" if status == "pass" else status
            _set(observed, "extraction_runs", metric, int(mapped == metric))
    charging = payload.get("charging")
    if isinstance(charging, dict):
        ledger = charging.get("ledger") or []
        for metric, kind in (("holds", "hold"), ("consumes", "consume"), ("releases", "release"), ("refunds", "refund")):
            _set(observed, "iap_ledger", metric, sum(row.get("type") == kind for row in ledger if isinstance(row, dict)))
    trigger = payload.get("trigger_control_plane") or payload.get("original_run")
    if isinstance(trigger, dict):
        attempts = trigger.get("attempt_count")
        _set(observed, "trigger", "attempts", attempts)
        _set(observed, "trigger", "retries", max(attempts - 1, 0) if isinstance(attempts, int) else None)
        _set(observed, "trigger", "dead_letter", int((trigger.get("output_status") or trigger.get("terminal_status")) == "dead_letter"))
    reconciliation = payload.get("reconciliation")
    ledger = reconciliation.get("ledger") if isinstance(reconciliation, dict) else None
    if isinstance(ledger, list):
        for metric, kind in (("holds", "hold"), ("consumes", "consume"), ("releases", "release"), ("refunds", "refund")):
            _set(observed, "iap_ledger", metric, sum(row.get("type") == kind for row in ledger if isinstance(row, dict)))
    return observed


def _scope(payload, name, observed):
    reported = (payload.get("counts") or {}).get(name)
    result = _blank("not_run" if name == "run" and reported is None else "unavailable")
    mismatches = []
    if not isinstance(reported, dict):
        return result, mismatches
    for group, metrics in DIMENSIONS.items():
        values = reported.get(group)
        for metric in metrics:
            value = values.get(metric) if isinstance(values, dict) else None
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                result[group][metric] = {"status": "available", "value": value}
                actual = observed[group][metric]
                if actual["status"] == "available" and actual["value"] != value:
                    mismatch = {"dimension": f"{group}.{metric}", "reported": value, "observed": actual["value"]}
                    result[group][metric]["status"] = "mismatch"
                    result[group][metric]["observed"] = actual["value"]
                    mismatches.append(mismatch)
    return result, mismatches


def reconcile(payload, source="<memory>"):
    observed = _observed(payload)
    run, run_mismatches = _scope(payload, "run", observed)
    cumulative, cumulative_mismatches = _scope(payload, "cumulative", observed)
    mismatches = [{"scope": "run", **row} for row in run_mismatches] + [{"scope": "cumulative", **row} for row in cumulative_mismatches]
    checks = []
    for scope_name, scope in (("run", run), ("cumulative", cumulative)):
        def value(group, metric):
            cell = scope[group][metric]
            return cell["value"] if cell["status"] == "available" else None
        balances = (
            ("documents.accepted", value("documents", "accepted"), sum(filter(lambda x: x is not None, (value("documents", key) for key in ("pass", "review", "error", "quarantined"))))) ,
            ("attachments.discovered", value("attachments", "discovered"), sum(filter(lambda x: x is not None, (value("attachments", "downloaded"), value("attachments", "rejected"))))),
            ("extraction_runs.attempted", value("extraction_runs", "attempted"), sum(filter(lambda x: x is not None, (value("extraction_runs", key) for key in ("succeeded", "review", "error"))))),
        )
        for dimension, total, outcomes in balances:
            if total is not None and total != outcomes:
                mismatch = {"scope": scope_name, "dimension": dimension, "reported": total, "balanced_outcomes": outcomes}
                mismatches.append(mismatch)
                checks.append({"status": "mismatch", **mismatch})
    parity_mismatch = any(scope["parity"]["mismatch"].get("value", 0) for scope in (run, cumulative))
    return {"source": source, "status": "red" if mismatches or parity_mismatch else "green", "run": run,
            "cumulative": cumulative, "observed": observed, "mismatches": mismatches, "balance_checks": checks}


def self_check():
    clean = {"records": [{"terminal_status": "pass", "pages": 1, "oracle_status": "independently_approved"}],
             "counts": {"run": {"documents": {"accepted": 1, "pass": 1, "review": 0, "error": 0, "quarantined": 0},
                                "pages": {"discovered": 1}, "parity": {"mismatch": 0}}}}
    assert reconcile(clean)["status"] == "green"
    bad_observed = copy.deepcopy(clean); bad_observed["counts"]["run"]["documents"]["accepted"] = 2
    assert reconcile(bad_observed)["status"] == "red"
    bad_balance = copy.deepcopy(clean); bad_balance["counts"]["run"]["documents"]["review"] = 1
    assert reconcile(bad_balance)["status"] == "red"
    bad_parity = copy.deepcopy(clean); bad_parity["counts"]["run"]["parity"]["mismatch"] = 1
    assert reconcile(bad_parity)["status"] == "red"
    sampled_inventory = copy.deepcopy(clean); sampled_inventory["source_inventory"] = {"records": 10}
    sampled_inventory["counts"]["run"]["pages"]["discovered"] = 100
    sampled_result = reconcile(sampled_inventory)
    assert sampled_result["status"] == "green"
    assert sampled_result["observed"]["pages"]["discovered"]["status"] == "unavailable"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+")
    parser.add_argument("--output")
    options = parser.parse_args()
    self_check()
    results = [reconcile(json.loads(Path(path).read_text()), path) for path in options.artifacts]
    report = {"schema_version": 1, "status": "red" if any(row["status"] == "red" for row in results) else "green", "artifacts": results}
    text = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if options.output:
        Path(options.output).write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
