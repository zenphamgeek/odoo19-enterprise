import hashlib
import json
from decimal import Decimal, InvalidOperation

REVIEW = "REVIEW"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def evaluate(rule, facts):
    if not rule.get("policy_hash"):
        return _result(REVIEW, "MISSING_APPROVED_POLICY", rule, facts)
    if rule.get("state", "active") != "active":
        return _result(REVIEW, "INACTIVE_POLICY", rule, facts)
    if facts.get("conflicting_evidence"):
        return _result(REVIEW, "CONFLICTING_EVIDENCE", rule, facts)
    missing = sorted(set(rule.get("required_evidence", ())) - set(facts.get("evidence", ())))
    if missing:
        return _result(REVIEW, "MISSING_EVIDENCE", rule, facts, {"missing": missing})
    criterion = rule.get("criterion")
    try:
        if criterion == "WO":
            if facts.get("all_originating") is None:
                return _result(REVIEW, "MISSING_ORIGIN_FACT", rule, facts)
            outcome = "PASS" if facts["all_originating"] is True else "BLOCK"
            reason = "WO_SATISFIED" if outcome == "PASS" else "NON_ORIGINATING_MATERIAL"
        elif criterion in ("CC", "CTH", "CTSH"):
            digits = {"CC": 2, "CTH": 4, "CTSH": 6}[criterion]
            output_hs = _hs(facts.get("output_hs"), digits)
            input_hs = [_hs(value, digits) for value in facts.get("input_hs", ())]
            if not input_hs:
                raise ValueError
            outcome = "PASS" if all(value != output_hs for value in input_hs) else "BLOCK"
            reason = "CTC_SATISFIED" if outcome == "PASS" else "CTC_NOT_SATISFIED"
        elif criterion in ("RVC", "LVC"):
            value = _decimal(facts.get("value"))
            non_originating = _decimal(facts.get("non_originating_value"))
            threshold = _decimal(rule.get("threshold"))
            if value <= 0 or non_originating < 0:
                raise ValueError
            margin = ((value - non_originating) / value * 100) - threshold
            outcome = "PASS" if margin >= 0 else "BLOCK"
            reason = "VALUE_THRESHOLD_SATISFIED" if outcome == "PASS" else "VALUE_THRESHOLD_NOT_SATISFIED"
            return _result(outcome, reason, rule, facts, {"margin": str(margin)})
        elif criterion in ("DE_MINIMIS", "CUMULATION", "PROCESS", "CONSIGNMENT"):
            predicate = rule.get("predicate")
            if not predicate or predicate not in facts or facts[predicate] is None:
                return _result(REVIEW, "MISSING_PREDICATE", rule, facts, {"predicate": predicate})
            outcome = "PASS" if facts[predicate] is True else "BLOCK"
            reason = "PREDICATE_SATISFIED" if outcome == "PASS" else "PREDICATE_NOT_SATISFIED"
        else:
            return _result(REVIEW, "UNSUPPORTED_CRITERION", rule, facts)
    except (InvalidOperation, TypeError, ValueError):
        return _result(REVIEW, "INVALID_INPUT", rule, facts)
    return _result(outcome, reason, rule, facts)


def rank_scenarios(scenarios):
    order = {"eligible": 0, "review": 1, "not_eligible": 2}
    return sorted(scenarios, key=lambda item: (
        order.get(item.get("state"), 1),
        -Decimal(str(item.get("evidence_completeness", 0))),
        -Decimal(str(item.get("margin", 0))),
        Decimal(str(item.get("cost", 0))),
        Decimal(str(item.get("lead_time", 0))),
        str(item["id"]),
    ))


def _decimal(value):
    if isinstance(value, bool) or value is None:
        raise ValueError
    return Decimal(str(value))


def _hs(value, digits):
    normalized = "".join(character for character in str(value or "") if character.isdigit())
    if len(normalized) < digits:
        raise ValueError
    return normalized[:digits]


def _result(outcome, reason, rule, facts, details=None):
    inputs = {"rule": rule, "facts": facts}
    return {"outcome": outcome, "reason_code": reason, "input_hash": digest(inputs),
            "policy_hash": rule.get("policy_hash"), "details": details or {}}
