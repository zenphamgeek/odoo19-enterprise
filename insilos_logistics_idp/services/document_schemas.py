from datetime import datetime
from decimal import Decimal, InvalidOperation

CANONICAL_EXPORT_FIELDS = {
    'origin_country': 'country', 'export_country': 'country', 'destination_country': 'country',
    'import_country': 'country', 'transit_countries': 'countries', 'transshipment_countries': 'countries',
    'end_user': 'string', 'end_use': 'string', 'control_classification': 'string',
    'license_reference': 'string', 'license_valid_from': 'date', 'license_valid_to': 'date',
    'fta_claim': 'string', 'fta_code': 'string', 'origin_criterion': 'string',
    'co_number': 'string', 'co_issuer': 'string', 'co_issue_date': 'date',
    'co_valid_until': 'date', 'preference_evidence': 'string',
}


DOCUMENT_TYPES = {
    'purchase_order': ('supplier', 'supplier_address', 'supplier_number', 'po_reference', 'total_value', 'document_date', 'currency', 'lines'),
    'po_snapshot': ('source_version', 'lines'),
    'draft_vat_invoice': ('supplier', 'invoice_number', 'lines'),
    'main_vat_invoice': ('supplier', 'invoice_number', 'lines'),
    'sales_invoice': ('supplier', 'invoice_number', 'lines'),
    'commercial_invoice': ('supplier', 'invoice_number', 'lines'),
    'invoice': ('supplier', 'invoice_number', 'lines'),
    'packing_list': ('supplier', 'lines'),
    'warehouse_release': ('supplier', 'lines'),
    'export_declaration_draft': ('declaration_number', 'regime', 'lines'),
    'export_declaration_final': ('declaration_number', 'regime', 'lines'),
    'import_declaration': ('declaration_number', 'lines'),
    'customs_declaration': ('declaration_number', 'regime', 'lines'),
    'master_data': ('source_version', 'lines'),
    'dsnavl': ('source_version', 'lines'),
    'sap_erp_output': ('source_version', 'lines'),
    'e11': ('regime', 'lines'),
    'e13': ('regime', 'lines'),
    'e15': ('regime', 'lines'),
    'manifest': ('shipment_reference', 'lines'),
    'bill_of_lading': ('shipment_reference', 'lines'),
    'broker_artifact': ('shipment_reference',),
    'shipping_plan': ('plan_key',),
    'gate_pass': ('shipping_plan_hash',),
}


import re


def _parse_flexible_date(value):
    if value is None:
        return None
    val_str = str(value).strip()
    if not val_str:
        return None
    # 1. Try ISO direct YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', val_str):
        try:
            return datetime.strptime(val_str, '%Y-%m-%d').date().isoformat()
        except ValueError:
            pass
    # 2. Try DD/MM/YYYY or DD.MM.YYYY or DD-MM-YYYY
    match_dmy = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', val_str)
    if match_dmy:
        d, m, y = int(match_dmy.group(1)), int(match_dmy.group(2)), int(match_dmy.group(3))
        try:
            return datetime(y, m, d).date().isoformat()
        except ValueError:
            pass
    # 3. Try YYYY/MM/DD or YYYY.MM.DD
    match_ymd = re.search(r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', val_str)
    if match_ymd:
        y, m, d = int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3))
        try:
            return datetime(y, m, d).date().isoformat()
        except ValueError:
            pass
    # 4. Try ISO timestamp YYYY-MM-DDTHH:MM:SS
    if 'T' in val_str:
        try:
            return datetime.fromisoformat(val_str.replace('Z', '+00:00')).date().isoformat()
        except (ValueError, TypeError):
            pass
    # 5. Vietnamese natural date: ngay DD thang MM nam YYYY
    match_vn = re.search(r'ng[aà]y\s+(\d{1,2})\s+th[aá]ng\s+(\d{1,2})\s+n[aăâ]m\s+(\d{4})', val_str, re.IGNORECASE)
    if match_vn:
        d, m, y = int(match_vn.group(1)), int(match_vn.group(2)), int(match_vn.group(3))
        try:
            return datetime(y, m, d).date().isoformat()
        except ValueError:
            pass
    return None


def normalize_decimal(value):
    if isinstance(value, bool):
        raise ValueError('invalid decimal')
    if value is None:
        raise ValueError('invalid decimal')
    val_str = str(value).strip()
    # Clean currency symbols and spaces
    val_str = re.sub(r'[^\d.,\-+eE]', '', val_str)
    if not val_str:
        raise ValueError('invalid decimal')
    # Handle European decimal: e.g. 1.250,50 -> 1250.50
    if ',' in val_str and '.' in val_str:
        if val_str.rfind(',') > val_str.rfind('.'):
            val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    elif ',' in val_str:
        # Check if single comma is decimal or thousand separator
        parts = val_str.split(',')
        if len(parts) == 2 and len(parts[1]) in (1, 2, 3, 4):
            val_str = val_str.replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    try:
        return str(Decimal(val_str))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError('invalid decimal') from exc


def validate(document_type, payload, policy=None, with_warnings=False, allow_review=False):
    if document_type not in DOCUMENT_TYPES:
        raise ValueError('unknown document type')
    if not isinstance(payload, dict):
        raise ValueError('payload must be an object')
    payload = dict(payload)
    if document_type == 'import_declaration' and payload.get('regime') in (None, ''):
        regimes = {line.get('regime') for line in payload.get('lines') or []
                   if isinstance(line, dict) and line.get('regime') not in (None, '')}
        if regimes:
            payload['regime'] = next(iter(regimes)) if len(regimes) == 1 else '/'.join(sorted(regimes))
    missing = [field for field in DOCUMENT_TYPES[document_type] if payload.get(field) in (None, '', [])]
    if missing and not allow_review:
        raise ValueError('missing fields: %s' % ', '.join(missing))
    review_type_warnings = []
    normalized = dict(payload)
    for field, kind in CANONICAL_EXPORT_FIELDS.items():
        value = payload.get(field)
        invalid = (value is not None and kind == 'string' and not isinstance(value, str)) or (value is not None and kind == 'country' and (not isinstance(value, str) or not value.strip())) or (value is not None and kind == 'countries' and (not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value)))
        if kind == 'date' and value is not None:
            parsed = _parse_flexible_date(value)
            if parsed:
                normalized[field] = parsed
            else:
                invalid = True
        if invalid:
            if not allow_review:
                raise ValueError('invalid %s type' % field)
            normalized[field] = None
            review_type_warnings.append('payload.%s' % field)
    string_fields = ('total_gross', 'total_quantity', 'currency') + (
        ('supplier', 'supplier_address', 'supplier_number', 'po_reference')
        if document_type == 'purchase_order' else ())
    for field in string_fields:
        if payload.get(field) is not None and not isinstance(payload[field], str):
            if not allow_review:
                raise ValueError('invalid %s type' % field)
            normalized[field] = None
            review_type_warnings.append('payload.%s' % field)
    invalid_date = False
    invalid_decimals = []
    if document_type == 'purchase_order' and payload.get('total_value') is not None:
        try:
            normalized['total_value'] = normalize_decimal(payload['total_value'])
        except ValueError:
            if not allow_review:
                raise
            normalized['total_value'] = None
            invalid_decimals.append('payload.total_value')
    if payload.get('document_date') is not None:
        parsed_doc_date = _parse_flexible_date(payload['document_date'])
        if parsed_doc_date:
            normalized['document_date'] = parsed_doc_date
        else:
            if not allow_review:
                raise ValueError('invalid document date')
            normalized['document_date'] = None
            invalid_date = True
    lines = []
    for line in payload.get('lines') or []:
        if not isinstance(line, dict):
            raise ValueError('line must be an object')
        item = dict(line)
        for field in ('quantity', 'unit_price', 'price_per', 'value'):
            value = item.get(field)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                    raise ValueError('invalid %s type' % field)
                try:
                    item[field] = normalize_decimal(value)
                except ValueError:
                    item[field] = None
                    invalid_decimals.append('payload.lines[].%s' % field)
        lines.append(item)
    if payload.get('lines') is not None:
        normalized['lines'] = lines
    if document_type == 'import_declaration' and normalized.get('regime') in (None, ''):
        regimes = {line.get('regime') for line in lines if line.get('regime') not in (None, '')}
        if regimes:
            normalized['regime'] = next(iter(regimes)) if len(regimes) == 1 else '/'.join(sorted(regimes))
    extraction = (policy or {}).get('horizontal', {}).get('extraction', {})
    critical = extraction.get('critical_fields', {}).get(document_type, [])
    warnings = (['payload.%s' % field for field in missing] + review_type_warnings + invalid_decimals) if allow_review else []
    if invalid_date:
        warnings.append('payload.document_date')
    for path in critical:
        if path.startswith('lines[].'):
            field = path.split('.', 1)[1]
            if any(line.get(field) in (None, '') for line in lines):
                warnings.append('payload.%s' % path)
        elif normalized.get(path) in (None, '', []):
            warnings.append('payload.%s' % path)
    return (normalized, sorted(set(warnings))) if with_warnings else normalized
