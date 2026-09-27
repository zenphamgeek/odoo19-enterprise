from datetime import date, datetime
from hashlib import sha256
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher

UOM_FACTORS = {'EA': Decimal('1'), 'PCS': Decimal('1'), 'KG': Decimal('1'), 'G': Decimal('0.001')}


def build_regulatory_change_notification(change, impact):
    """Build a deterministic, review-only notification intent; never sends messages."""
    change = change if isinstance(change, dict) else None
    impact = impact if isinstance(impact, dict) else None
    source = (change or {}).get('source') or (change or {}).get('source_reference')
    policy = (change or {}).get('policy') or (impact or {}).get('policy')
    payload = {'change': change, 'impact': impact}
    input_hash = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    intent = {'status': 'pending_review', 'audience': 'compliance_reviewers', 'reason': 'REGULATORY_CHANGE_NOTIFICATION_INCOMPLETE',
              'source': source, 'source_hash': (change or {}).get('source_hash'), 'policy_hash': (change or {}).get('policy_hash') or (policy or {}).get('hash'),
              'audit_input_hash': input_hash, 'send_external': False, 'activation_allowed': False}
    if not change or not impact:
        intent['intent'] = 'REVIEW'
    else:
        outcome = impact.get('outcome')
        if outcome == 'not_affected':
            intent = {'intent': 'NOT_APPLICABLE', 'status': 'not_applicable', 'reason': 'NOT_APPLICABLE', 'audit_input_hash': input_hash,
                      'send_external': False, 'activation_allowed': False}
        elif outcome == 'insufficient_context':
            intent['reason'] = 'REGULATORY_IMPACT_INSUFFICIENT_CONTEXT'
        elif outcome in ('affected', 'possibly_affected'):
            intent['intent'] = 'NOTIFICATION'
            intent['reason'] = impact.get('reason') or 'REGULATORY_CHANGE_REQUIRES_REVIEW'
            intent['audience'] = impact.get('audience') or intent['audience']
        else:
            intent['intent'] = 'REVIEW'
    if policy and not policy.get('authoritative', False):
        intent['reason'] = 'LEGAL_POLICY_DATASET_NOT_APPROVED'
    output_hash = sha256(json.dumps(intent, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    intent['output_hash'] = output_hash
    return intent


def evaluate_origin_evidence(payload, policy=None):
    payload = payload if isinstance(payload, dict) else {}
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    result = {'verdict': 'NOT_APPLICABLE', 'reason_codes': [], 'required_evidence': [],
              'conflicts': [], 'audit_input_hash': sha256(normalized.encode()).hexdigest()}
    facts = any(payload.get(key) not in (None, '', []) for key in (
        'fta_claim', 'fta_code', 'origin_criterion', 'co_number', 'co_issuer',
        'co_issue_date', 'co_valid_until', 'preference_evidence', 'origin_country',
        'declared_origin_country', 'origin_evidence'))
    if not facts:
        return result
    result['verdict'] = 'REVIEW'
    if payload.get('fta_claim') and not (policy or {}).get('approved_rule_pack'):
        result['reason_codes'].append('FTA_RULE_PACK_MISSING')
    if payload.get('origin_country') and payload.get('declared_origin_country') and payload['origin_country'] != payload['declared_origin_country']:
        result['reason_codes'].append('ORIGIN_EVIDENCE_CONFLICT')
        result['conflicts'].append('origin_country:declared_origin_country')
    evidence = payload.get('origin_evidence')
    if isinstance(evidence, list) and len({json.dumps(item, sort_keys=True) for item in evidence}) != len(evidence):
        result['reason_codes'].append('ORIGIN_EVIDENCE_CONFLICT')
    required = ('origin_country', 'origin_criterion', 'co_number', 'co_issuer', 'co_issue_date')
    if any(payload.get(key) in (None, '', []) for key in required):
        result['reason_codes'].append('ORIGIN_EVIDENCE_INCOMPLETE')
        result['required_evidence'] = [key for key in required if payload.get(key) in (None, '', [])]
    for key in ('co_issue_date', 'co_valid_until'):
        if payload.get(key):
            try:
                datetime.strptime(payload[key], '%Y-%m-%d')
            except (TypeError, ValueError):
                result['reason_codes'].append('ORIGIN_EVIDENCE_INVALID_DATE')
    if policy and not policy.get('authoritative', False):
        result['reason_codes'].append('ORIGIN_POLICY_DATASET_NOT_APPROVED')
    result['reason_codes'] = sorted(set(result['reason_codes']))
    return result


def evaluate_tariff_remedy_security(payload, policy=None):
    payload = payload if isinstance(payload, dict) else {}
    policy = policy if isinstance(policy, dict) else {}
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    result = {'verdict': 'NOT_APPLICABLE', 'reason_codes': [], 'required_evidence': [],
              'conflicts': [], 'matched_rules': [], 'audit_input_hash': sha256(normalized.encode()).hexdigest()}
    tariff_keys = ('tariff_code', 'tariff_schedule_code', 'tariff_rate', 'tariff', 'rate', 'schedule')
    remedy_keys = ('remedy_type', 'remedy_case_reference', 'remedy_evidence')
    security_keys = ('economic_security_claim', 'measure_reference')
    if not any(payload.get(key) not in (None, '', []) for key in (*tariff_keys, *remedy_keys, *security_keys)):
        return result
    result['verdict'] = 'REVIEW'
    has_tariff = any(payload.get(key) not in (None, '', []) for key in tariff_keys)
    if has_tariff and not payload.get('tariff_code'):
        result['reason_codes'].append('TARIFF_CLASSIFICATION_INCOMPLETE')
        result['required_evidence'].append('tariff_code')
    if has_tariff and not (policy.get('approved_tariff_pack') or policy.get('approved_rate_pack') or policy.get('approved_schedule')):
        result['reason_codes'].append('TARIFF_POLICY_DATASET_NOT_APPROVED')
        result['required_evidence'].append('approved_tariff_pack')
    remedy_present = any(payload.get(key) not in (None, '', []) for key in remedy_keys)
    if remedy_present:
        evidence = payload.get('remedy_evidence')
        if payload.get('remedy_type') and not payload.get('remedy_case_reference') or not evidence:
            result['reason_codes'].append('TRADE_REMEDY_EVIDENCE_INCOMPLETE')
            result['required_evidence'].extend(key for key in ('remedy_case_reference', 'remedy_evidence') if not payload.get(key))
        if payload.get('remedy_evidence_invalid') or payload.get('remedy_evidence_stale'):
            result['reason_codes'].append('TRADE_REMEDY_EVIDENCE_INCOMPLETE')
        if payload.get('remedy_claim') and payload.get('remedy_evidence_claim') and payload['remedy_claim'] != payload['remedy_evidence_claim']:
            result['reason_codes'].append('TRADE_REMEDY_EVIDENCE_CONFLICT')
            result['conflicts'].append('remedy_claim:remedy_evidence_claim')
    if any(payload.get(key) not in (None, '', []) for key in security_keys) and not (policy.get('approved_security_pack') or policy.get('security_evidence')):
        result['reason_codes'].append('ECONOMIC_SECURITY_POLICY_NOT_APPROVED')
        result['required_evidence'].append('approved_security_pack')
    if policy and not policy.get('authoritative', False):
        result['reason_codes'].append('LEGAL_POLICY_DATASET_NOT_APPROVED')
    result['reason_codes'] = sorted(set(result['reason_codes']))
    result['required_evidence'] = sorted(set(result['required_evidence']))
    result['conflicts'] = sorted(set(result['conflicts']))
    return result


def decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError('invalid decimal') from exc


def normalized_quantity(value, uom):
    code = str(uom or 'EA').upper()
    if code not in UOM_FACTORS:
        raise ValueError('unknown UoM')
    return decimal(value) * UOM_FACTORS[code]


def normalized_money(value, currency, fx_rates, rounding='0.01'):
    code = str(currency or '').upper()
    if code not in fx_rates:
        raise ValueError('missing effective FX rate')
    return (decimal(value) * decimal(fx_rates[code])).quantize(decimal(rounding), rounding=ROUND_HALF_UP)


def compare_line(expected, actual, tolerance='0', fx_rates=None):
    missing = [key for key in ('quantity', 'unit_price') if expected.get(key) is None or actual.get(key) is None]
    if missing:
        return {'verdict': 'review', 'reason': 'missing context: %s' % ', '.join(missing)}
    try:
        quantity_ok = abs(normalized_quantity(expected['quantity'], expected.get('uom')) - normalized_quantity(actual['quantity'], actual.get('uom'))) <= decimal(tolerance)
        expected_price = decimal(expected['unit_price']) / decimal(expected.get('price_per') or 1)
        actual_price = decimal(actual['unit_price']) / decimal(actual.get('price_per') or 1)
        expected_currency = str(expected.get('currency') or '').upper()
        actual_currency = str(actual.get('currency') or '').upper()
        if expected_currency != actual_currency and not fx_rates:
            return {'verdict': 'review', 'reason': 'currency mismatch requires effective FX rate'}
        if fx_rates:
            expected_price = normalized_money(expected_price, expected_currency, fx_rates)
            actual_price = normalized_money(actual_price, actual_currency, fx_rates)
        price_ok = abs(expected_price - actual_price) <= decimal(tolerance)
    except (ValueError, ZeroDivisionError):
        return {'verdict': 'review', 'reason': 'invalid or missing normalization context'}
    return {'verdict': 'pass' if quantity_ok and price_ok else 'block', 'quantity_ok': quantity_ok, 'price_ok': price_ok}


def _identity(line, cascade):
    for field in cascade:
        value = str(line.get(field) or '').strip().upper()
        if value:
            return field, value
    return None, None


def description_similarity_candidates(po_lines, invoice_lines, threshold):
    try:
        threshold = float(threshold)
    except (TypeError, ValueError) as exc:
        raise ValueError('description similarity threshold must be numeric') from exc
    if not 0 < threshold <= 1:
        raise ValueError('description similarity threshold must be within (0, 1]')

    def normalized(line):
        return ' '.join(str(line.get('description') or '').strip().upper().split())

    candidates = []
    for po_line in po_lines:
        po_description = normalized(po_line)
        if not po_description:
            continue
        for invoice_line in invoice_lines:
            invoice_description = normalized(invoice_line)
            if not invoice_description:
                continue
            similarity = SequenceMatcher(None, po_description, invoice_description).ratio()
            if similarity >= threshold:
                candidates.append({'po_line': po_line, 'invoice_line': invoice_line,
                                   'description_similarity': round(similarity, 4), 'result': 'candidate',
                                   'reason': 'description similarity suggestion only; never a standalone pass'})
    return candidates


def validate_declaration_group_rules(policy):
    rules = policy.get('declaration_group_rules')
    if rules is None:
        return []
    if not isinstance(rules, list):
        raise ValueError('declaration_group_rules must be a list')
    normalized = []
    seen_ids = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError('declaration group rule must be an object')
        regimes = rule.get('regimes')
        if not isinstance(regimes, list) or not regimes:
            raise ValueError('declaration group rule regimes must be a nonempty list')
        normalized_regimes = tuple(str(regime).strip().upper() for regime in regimes)
        if not all(normalized_regimes) or len(set(normalized_regimes)) != len(normalized_regimes):
            raise ValueError('declaration group rule regimes must be unique nonempty identifiers')
        count = rule.get('declaration_count')
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError('declaration group rule declaration_count must be positive')
        try:
            effective_from = date.fromisoformat(rule['effective_from'])
            effective_to = date.fromisoformat(rule['effective_to'])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('declaration group rule effective window must use ISO dates') from exc
        if effective_from > effective_to:
            raise ValueError('declaration group rule effective window is invalid')
        rule_id = rule.get('rule_id')
        if rule_id is not None:
            rule_id = str(rule_id).strip()
            if not rule_id or rule_id in seen_ids:
                raise ValueError('declaration group rule rule_id must be unique and nonempty')
            seen_ids.add(rule_id)
        normalized.append({'rule_id': rule_id or 'rule-%04d' % (index + 1), 'regimes': normalized_regimes,
                           'declaration_count': count, 'effective_from': effective_from.isoformat(),
                           'effective_to': effective_to.isoformat()})
    for index, rule in enumerate(normalized):
        for other in normalized[index + 1:]:
            if (frozenset(rule['regimes']) == frozenset(other['regimes'])
                    and rule['effective_from'] <= other['effective_to']
                    and other['effective_from'] <= rule['effective_to']):
                raise ValueError('overlapping declaration group rules are ambiguous')
    return normalized


def validate_draft_invoice_policy(policy):
    draft_invoice = policy.get('draft_invoice')
    if draft_invoice is None:
        return 'optional', False
    if not isinstance(draft_invoice, dict):
        raise ValueError('draft_invoice must be an object')
    mode = draft_invoice.get('mode')
    if mode not in ('required', 'optional', 'skipped', 'sales_invoice', 'commercial_invoice'):
        raise ValueError('draft_invoice.mode must be required, optional, skipped, sales_invoice, or commercial_invoice')
    allowed = draft_invoice.get('final_number_allowed', False)
    if not isinstance(allowed, bool):
        raise ValueError('draft_invoice.final_number_allowed must be a boolean')
    return mode, allowed


def validate_main_invoice_policy(policy):
    main_invoice = policy.get('main_invoice', {})
    if not isinstance(main_invoice, dict):
        raise ValueError('main_invoice must be an object')
    substitutes = main_invoice.get('allowed_substitutes', [])
    if not isinstance(substitutes, list) or any(item not in ('sales_invoice', 'commercial_invoice') for item in substitutes):
        raise ValueError('main_invoice.allowed_substitutes must list exact supported substitutes')
    draft_mode = policy.get('draft_invoice', {}).get('mode')
    return tuple(dict.fromkeys([*substitutes, *([draft_mode] if draft_mode in ('sales_invoice', 'commercial_invoice') else [])]))


def main_invoice_check(document_type, invoice_number, allowed_substitutes=()):
    observed_type = str(document_type or '').strip()
    number = str(invoice_number or '').strip()
    if not observed_type:
        return None
    if observed_type == 'main_vat_invoice':
        return None if number else {'result': 'review', 'rule': 'main_invoice.final_number',
                                    'observed_document_type': observed_type, 'observed_number': number,
                                    'reason': 'missing or invalid final invoice number'}
    if observed_type == 'draft_vat_invoice' or observed_type in allowed_substitutes:
        return None
    return {'result': 'review', 'rule': 'main_invoice.document_type',
            'observed_document_type': observed_type or None, 'observed_number': number,
            'reason': 'main VAT invoice required; substitute is not explicitly allowed'}


def draft_invoice_mode_check(mode, document_type):
    allowed_types = {
        'required': ('draft_vat_invoice',),
        'sales_invoice': ('sales_invoice',),
        'commercial_invoice': ('commercial_invoice',),
    }
    if mode == 'optional' or mode == 'skipped' and document_type != 'draft_vat_invoice':
        return None
    if document_type in allowed_types.get(mode, ()):
        return None
    return {'result': 'review', 'rule': 'draft_invoice.mode', 'mode': mode,
            'observed_document_type': document_type or None,
            'reason': 'missing required invoice document type' if mode == 'required' and not document_type
            else 'incompatible invoice document type'}


def _no_material_regime(policy):
    policy = policy or {}
    if str(policy.get('no_material_behavior') or '').strip().lower() != 'custom_code':
        return ''
    allowed = policy.get('allowed_regimes')
    if not isinstance(allowed, list) or len(allowed) != 1:
        return ''
    return str(allowed[0]).strip().upper() or ''


def line_regime_decisions(expected, actual, policy=None):
    expected_regimes = {str(line.get('regime') or '').strip().upper() for line in expected}
    expected_regimes.discard('')
    missing_expected = len(expected_regimes) != len(expected)
    no_material_regime = _no_material_regime(policy)
    decisions = []
    for line in actual:
        actual_regime = str(line.get('regime') or '').strip().upper()
        if no_material_regime and not str(line.get('material_code') or '').strip() and not actual_regime:
            actual_regime = no_material_regime
            result, reason = 'pass', 'no-material custom_code regime assignment'
        elif missing_expected or not actual_regime:
            result, reason = 'review', 'missing expected customs regime' if missing_expected else 'missing actual customs regime'
        elif len(expected_regimes) != 1:
            result, reason = 'review', 'conflicting expected customs regimes'
        elif actual_regime != next(iter(expected_regimes)):
            result, reason = 'block', 'customs regime mismatch'
        else:
            result, reason = 'pass', 'customs regime match'
        decisions.append({'invoice_line': line, 'expected_regimes': sorted(expected_regimes),
                          'actual_regime': actual_regime, 'result': result, 'reason': reason})
    return decisions


def declaration_group_check(actual_regimes, declaration_groups, effective_date, policy):
    rules = validate_declaration_group_rules(policy)
    if not rules:
        return None
    try:
        current_date = date.fromisoformat(str(effective_date))
    except (TypeError, ValueError) as exc:
        raise ValueError('effective date must use ISO date') from exc
    regime_set = frozenset(actual_regimes)
    applicable = [rule for rule in rules if frozenset(rule['regimes']) == regime_set
                  and rule['effective_from'] <= current_date.isoformat() <= rule['effective_to']]
    if len(applicable) > 1:
        raise ValueError('ambiguous active declaration group rules')
    if not applicable:
        return {'result': 'review', 'reason': 'no applicable declaration group rule', 'actual_regimes': sorted(regime_set)}
    rule = applicable[0]
    if not isinstance(declaration_groups, list) or not declaration_groups:
        return {**rule, 'result': 'review', 'reason': 'missing or invalid declaration groups',
                'actual_count': None}
    groups = [str(group).strip() for group in declaration_groups]
    if not all(groups):
        return {**rule, 'result': 'review', 'reason': 'missing or invalid declaration groups',
                'actual_count': None}
    actual_count = len(set(groups))
    return {**rule, 'result': 'pass' if actual_count == rule['declaration_count'] else 'block',
            'actual_count': actual_count}


def _compare_matched_group(expected, actual, tolerance, fx_rates, regime_policy, po, invoice, regime_checks):
    try:
        remaining = sum((normalized_quantity(line.get('remaining_quantity', line.get('quantity')), line.get('uom')) for line in expected), Decimal())
        quantity_1 = sum((normalized_quantity(line.get('quantity_1', line.get('quantity')), line.get('uom')) for line in actual), Decimal())
        quantity_2_lines = [line for line in actual if line.get('quantity_2') is not None]
        quantity_2 = sum((normalized_quantity(line['quantity_2'], line.get('uom')) for line in quantity_2_lines), Decimal()) if quantity_2_lines else None
        comparisons = [compare_line({**expected[0], 'quantity': line.get('quantity_1', line.get('quantity'))}, {**line, 'quantity': line.get('quantity_1', line.get('quantity'))}, tolerance, fx_rates) for line in actual]
        quantity_1_ok = remaining + decimal(tolerance) >= quantity_1
        supplier_ok = not po.get('supplier') or str(po['supplier']).strip().upper() == str(invoice.get('supplier') or '').strip().upper()
        required_price = regime_policy.get('price_required', True)
        price_ok = bool(comparisons) and all(item.get('price_ok') for item in comparisons)
        verdict = 'review' if any(item['verdict'] == 'review' for item in comparisons) else ('pass' if quantity_1_ok and supplier_ok and (price_ok or not required_price) else 'block')
        if any(item['result'] == 'block' for item in regime_checks):
            verdict = 'block'
        elif any(item['result'] == 'review' for item in regime_checks) and verdict == 'pass':
            verdict = 'review'
    except ValueError:
        quantity_1_ok, supplier_ok, price_ok, verdict, quantity_2 = False, False, False, 'review', None
    return {'quantity_1_ok': quantity_1_ok, 'supplier_ok': supplier_ok, 'price_ok': price_ok,
            'verdict': verdict, 'quantity_2': quantity_2}


def reconcile_documents(po, invoice, tolerance='0', fx_rates=None, policy=None, declaration_groups=None, effective_date=None, draft_invoice_policy_valid=True):
    policy = policy or {}
    draft_invoice_mode, final_number_allowed = validate_draft_invoice_policy(policy)
    allowed_main_substitutes = validate_main_invoice_policy(policy)
    document_type = invoice.get('document_type')
    main_invoice_check_result = (None if draft_invoice_policy_valid else {
        'result': 'review', 'rule': 'supplier_profile.main_invoice',
        'reason': 'missing or invalid supplier main-invoice policy'})
    main_invoice_check_result = main_invoice_check_result or main_invoice_check(
        document_type, invoice.get('invoice_number'), allowed_main_substitutes)
    draft_invoice_mode_check_result = (None if draft_invoice_policy_valid else {
        'result': 'review', 'rule': 'supplier_profile.draft_invoice', 'reason': 'missing or invalid supplier draft-invoice policy'})
    draft_invoice_mode_check_result = draft_invoice_mode_check_result or draft_invoice_mode_check(draft_invoice_mode, document_type)
    invoice_number = str(invoice.get('invoice_number') or '').strip()
    draft_invoice_check = ({'result': 'review', 'rule': 'draft_invoice.final_number_allowed',
                            'observed_number': invoice_number}
                           if draft_invoice_mode in ('required', 'optional') and document_type == 'draft_vat_invoice'
                           and not draft_invoice_mode_check_result and invoice_number and not final_number_allowed else None)
    cascade = policy.get('matching_cascade') or ['material_code', 'custom_code', 'supplier_part_number', 'description']
    regimes = policy.get('regimes') or {}
    po_lines, invoice_lines = po.get('lines', []), invoice.get('lines', [])
    matched_po_lines, matched_invoice_lines = set(), set()
    no_material_regime = _no_material_regime(policy)
    no_material_invoice_lines = [line for line in invoice_lines
                                 if not str(line.get('material_code') or '').strip()
                                 and not str(line.get('regime') or invoice.get('regime') or '').strip()]
    actual_regimes = {str(line.get('regime') or invoice.get('regime') or '').strip().upper() for line in invoice_lines}
    actual_regimes.discard('')
    if no_material_regime and no_material_invoice_lines:
        actual_regimes.add(no_material_regime)
    declaration_check = declaration_group_check(actual_regimes, declaration_groups, effective_date, policy)
    po_keys = list(dict.fromkeys(_identity(line, cascade) for line in po_lines))
    invoice_keys = list(dict.fromkeys(_identity(line, cascade) for line in invoice_lines))
    keys = po_keys + [key for key in invoice_keys if key not in po_keys]
    sequence_mismatch = [key for key in invoice_keys if key in po_keys] != [key for key in po_keys if key in invoice_keys]
    sequence_policy = policy.get('sequence_policy', 'ignore')
    results = []
    for strategy, key in keys:
        if not key:
            continue
        expected = [line for line in po_lines if _identity(line, cascade) == (strategy, key)]
        actual = [line for line in invoice_lines if _identity(line, cascade) == (strategy, key)]
        line_regimes = {str(line.get('regime') or invoice.get('regime') or '').upper() for line in actual}
        line_regimes.discard('')
        no_material_lines = [line for line in actual
                             if not str(line.get('material_code') or '').strip()
                             and not str(line.get('regime') or invoice.get('regime') or '').strip()]
        if no_material_regime and no_material_lines:
            line_regimes.add(no_material_regime)
        regime = next(iter(sorted(line_regimes)), str((expected[0] if expected else {}).get('regime') or invoice.get('regime') or '').upper())
        regime_policy = regimes.get(regime, {})
        regime_checks = line_regime_decisions(expected, actual, policy) if expected and actual and (any(line.get('regime') for line in expected) or (any(line.get('regime') for line in actual) and len(line_regimes) == 1) or (no_material_regime and no_material_lines)) else []
        if len(line_regimes) > 1 and not regime_checks and not (declaration_check and 'declaration_count' in declaration_check):
            results.append({'strategy': strategy, 'identity': key, 'regime': sorted(line_regimes),
                            'result': 'review', 'reason': 'mixed customs regimes require explicit grouping policy'})
            continue
        if not regime:
            materials = [str(line.get('material_code')).strip() for line in actual + expected
                         if str(line.get('material_code') or '').strip()]
            regime_checks = line_regime_decisions(expected, actual, policy) if expected and actual else []
            group = _compare_matched_group(expected, actual, tolerance, fx_rates, regimes.get('', {}), po, invoice, regime_checks)
            line_result = group['verdict']
            reason = 'missing customs regime' if line_result != 'block' else (
                'quantity mismatch' if not group['quantity_1_ok'] else
                'supplier mismatch' if not group['supplier_ok'] else 'price mismatch')
            for material in dict.fromkeys(materials or [None]):
                results.append({'strategy': strategy, 'identity': key, 'regime': '',
                                'customs_regime_checks': regime_checks,
                                'quantity_1_ok': group['quantity_1_ok'], 'supplier_ok': group['supplier_ok'],
                                'price_ok': group['price_ok'],
                                **({'material_code': material} if material else {}),
                                'result': line_result, 'reason': reason})
            if expected and actual:
                matched_po_lines.update(id(line) for line in expected)
                matched_invoice_lines.update(id(line) for line in actual)
            continue
        if not expected or not actual:
            results.append({'strategy': strategy, 'identity': key, 'regime': regime, 'result': 'review', 'reason': 'unmatched'})
            continue
        matched_po_lines.update(id(line) for line in expected)
        matched_invoice_lines.update(id(line) for line in actual)
        group = _compare_matched_group(expected, actual, tolerance, fx_rates, regime_policy, po, invoice, regime_checks)
        quantity_1_ok, supplier_ok, price_ok, verdict, quantity_2 = (group['quantity_1_ok'], group['supplier_ok'],
                                                                     group['price_ok'], group['verdict'], group['quantity_2'])
        results.append({'invoice_line': actual[0], 'invoice_lines': actual, 'po_line': expected[0], 'po_lines': expected,
                        'cardinality': '%s-to-%s' % ('one' if len(expected) == 1 else 'many', 'one' if len(actual) == 1 else 'many'),
                        'strategy': strategy, 'identity': key, 'regime': regime, 'customs_regime_checks': regime_checks,
                        'quantity_1_ok': quantity_1_ok, 'quantity_2': str(quantity_2) if quantity_2 is not None else None,
                        'quantity_2_evidence_only': True, 'price_ok': price_ok, 'supplier_ok': supplier_ok, 'result': verdict})
    if not results and len(po_lines) == len(invoice_lines) == 1:
        comparison = compare_line({**po_lines[0], 'quantity': invoice_lines[0].get('quantity_1', invoice_lines[0].get('quantity'))}, invoice_lines[0], tolerance, fx_rates)
        regime = str(invoice_lines[0].get('regime') or po_lines[0].get('regime') or invoice.get('regime') or '').upper()
        results = [{'invoice_line': invoice_lines[0], 'po_line': po_lines[0], 'strategy': 'single', 'cardinality': 'one-to-one', 'regime': regime, 'quantity_2_evidence_only': True,
                    'result': comparison['verdict'] if regime else 'review', **({} if regime else {'reason': 'missing customs regime'})}]
    description_config = policy.get('description_similarity')
    description_candidates = None
    if isinstance(description_config, dict) and description_config.get('enabled') is True and 'description' in cascade:
        try:
            threshold = float(description_config.get('threshold', 0.50))
            unmatched_po = [line for line in po_lines if id(line) not in matched_po_lines]
            unmatched_invoice = [line for line in invoice_lines if id(line) not in matched_invoice_lines]
            description_candidates = description_similarity_candidates(unmatched_po, unmatched_invoice, threshold)
        except (TypeError, ValueError):
            description_candidates = None
    verdict = 'pass' if results and all(item['result'] == 'pass' for item in results) else (
        'block' if any(item['result'] == 'block' and item.get('regime') not in (None, '') for item in results) else 'review')
    sequence = {'mismatch': sequence_mismatch, 'policy': sequence_policy,
                'result': ('block' if sequence_mismatch and sequence_policy == 'block'
                           else 'review' if sequence_mismatch and sequence_policy == 'warn' else 'pass')}
    if sequence['result'] == 'block' or sequence['result'] == 'review' and verdict == 'pass':
        verdict = sequence['result']
    if declaration_check:
        if declaration_check['result'] == 'block' or declaration_check['result'] == 'review' and verdict == 'pass':
            verdict = declaration_check['result']
    if (main_invoice_check_result or draft_invoice_mode_check_result or draft_invoice_check) and verdict == 'pass':
        verdict = 'review'
    return {'verdict': verdict, 'results': results, 'sequence': sequence,
            'declaration_group_check': declaration_check, 'main_invoice_check': main_invoice_check_result,
            'draft_invoice_mode': draft_invoice_mode, 'draft_invoice_mode_check': draft_invoice_mode_check_result,
            'draft_invoice_check': draft_invoice_check,
            **({'description_candidates': description_candidates} if description_candidates is not None else {})}


def reconcile_draft_main(draft, main, tolerance='0', fx_rates=None, policy=None):
    policy = policy or {}
    comparison_policy = {**policy, 'draft_invoice': {**policy.get('draft_invoice', {}), 'mode': 'skipped'}}
    result = reconcile_documents(draft, main, tolerance, fx_rates, comparison_policy)
    for item in result['results']:
        expected, actual = item.get('po_line'), item.get('invoice_line')
        if not expected or not actual or ('line_total' not in expected and 'line_total' not in actual):
            continue
        try:
            total_ok = ('line_total' in expected and 'line_total' in actual
                        and abs(decimal(expected['line_total']) - decimal(actual['line_total'])) <= decimal(tolerance))
        except ValueError:
            total_ok = False
        item['line_total_ok'] = total_ok
        if not total_ok:
            item['result'] = 'block'
    if any(item['result'] == 'block' for item in result['results']):
        result['verdict'] = 'block'
    return result


def customs_checks(values):
    if not values.get('regime'):
        return [{'code': 'customs_regime', 'verdict': 'review', 'reason': 'missing customs regime'}]
    checks = []
    if values.get('expected_hs') and values.get('actual_hs'):
        checks.append({'code': 'hs_code', 'verdict': 'pass' if values['expected_hs'] == values['actual_hs'] else 'block', 'reason': 'HS code comparison'})
    else:
        checks.append({'code': 'hs_code', 'verdict': 'review', 'reason': 'missing HS context'})
    checks.append({'code': 'regime', 'verdict': 'pass' if values['regime'] in ('E11', 'E13', 'E15') else 'review', 'reason': 'regime classification'})
    return checks
