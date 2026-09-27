import base64
import csv
import hashlib
import io
import json
import math
import os
import re
import unicodedata
import zipfile
from datetime import datetime
from email import policy
from email.parser import BytesParser
from xml.etree import ElementTree

from .document_schemas import DOCUMENT_TYPES, normalize_decimal, validate


SCHEMA_VERSION = '11'
PROMPT_VERSION = 'logistics-ocr-v7'
DEFAULT_EXTRACTION_PROMPT = (
    'Extract {document_type}. Use explicit values only; null when unavailable. '
    'Format document_date only as YYYY-MM-DD or DD/MM/YYYY. '
    'For ocr_results geometry use empty objects {"words": {}, "numbers": {}, "dates": {}}. '
    'Canonical contract: {schema}. Return JSON only.'
)
SHARED_PAYLOAD_FIELDS = (
    'supplier_address', 'buyer_name', 'total_gross', 'total_quantity', 'currency', 'document_date',
)
LINE_FIELDS = (
    'description', 'material_code', 'custom_code', 'quantity', 'unit_price', 'value', 'uom', 'currency', 'price_per',
    'quantity_1', 'quantity_2', 'remaining_quantity', 'hs_code',
)
CLASSIFICATION_RULES = (
    ('e11', r'\be\s*11\b'), ('e13', r'\be\s*13\b'), ('e15', r'\be\s*15\b'),
    ('purchase_order', r'\bpurchase\s+order\b|\bpo\b'),
    ('sales_invoice', r'\bsales\s+invoice\b'),
    ('commercial_invoice', r'\bcommercial\s+invoice\b'),
    ('packing_list', r'\bpacking\s+list\b'),
    ('warehouse_release', r'\bphieu\s+xuat\s+kho\b|\bdelivery\s+note\b|\bgoods\s+issue\b'),
    ('bill_of_lading', r'\bbill\s+of\s+lading\b|\bbol\b'),
    ('manifest', r'\bmanifest\b'),
    ('shipping_plan', r'\bshipping\s+plan\b'), ('gate_pass', r'\bgate\s+pass\b'),
)


def _normalized_text(value):
    text = unicodedata.normalize('NFKD', str(value or '')).casefold().replace('đ', 'd')
    text = ''.join(character for character in text if not unicodedata.combining(character))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def _sanitize_boundary_text(value):
    return re.sub(r'\b[^\s@]+@[^\s@]+\b', '[email]', str(value or ''))[:500]


def _policy_sections(policy):
    policy = policy or {}
    horizontal = policy.get('horizontal', {})
    vertical = policy.get('vertical', {})
    pack = vertical.get('packs', {}).get(vertical.get('pack')) or vertical.get('config', {})
    return horizontal, pack


def deterministic_classify(metadata):
    """Classify from caller-provided boundary metadata; never inspect document bytes."""
    metadata = metadata or {}
    horizontal, pack = _policy_sections(metadata.get('idp_policy'))
    profile = {**horizontal.get('classification', {}), **pack.get('classification', {})}
    thresholds = profile.get('thresholds', {})
    filename_confidence = float(thresholds.get('strong_filename', .95))
    ambiguous_confidence = float(thresholds.get('ambiguous', .7))
    rules = tuple((role, pattern) for role, patterns in profile.get('aliases', {}).items()
                  for pattern in patterns) or CLASSIFICATION_RULES
    filename = os.path.basename(str(metadata.get('filename') or metadata.get('attachment_name') or ''))
    filename_text = _normalized_text(os.path.splitext(filename)[0])
    subject_text = _normalized_text(_sanitize_boundary_text(metadata.get('email_subject')))
    filename_hits = {document_type for document_type, pattern in rules
                     if re.search(pattern, filename_text)}
    subject_hits = {document_type for document_type, pattern in rules
                    if re.search(pattern, subject_text)}
    invoice_phrase = bool(re.search(r'\b(?:vat\s+invoice|hoa\s+don\s+gtgt)\b', filename_text))
    if invoice_phrase:
        if re.search(r'\b(?:draft|nhap)\b', filename_text):
            filename_hits.add('draft_vat_invoice')
        elif re.search(r'\b(?:main|final|chinh)\b', filename_text):
            filename_hits.add('main_vat_invoice')
        else:
            filename_hits.add('invoice')
    declaration = re.search(r'\b(?:export\s+declaration|to\s+khai\s+xuat)\b', filename_text)
    if declaration:
        if re.search(r'\b(?:draft|nhap)\b', filename_text):
            filename_hits.add('export_declaration_draft')
        elif re.search(r'\b(?:final|chinh)\b', filename_text):
            filename_hits.add('export_declaration_final')
        else:
            filename_hits.add('customs_declaration')
    if re.search(r'\bgenesis\b', filename_text) and (re.search(r'\bpo\b', filename_text)
            or metadata.get('has_po_reference') or metadata.get('case_po_reference')):
        filename_hits.add('purchase_order')
    hits = filename_hits | subject_hits
    if len(filename_hits) == 1:
        return {'type': next(iter(filename_hits)), 'confidence': filename_confidence, 'reason': 'unique filename phrase'}
    if len(hits) == 1:
        return {'type': next(iter(hits)), 'confidence': ambiguous_confidence, 'reason': 'ambiguous non-filename metadata'}
    reason = 'ambiguous metadata tokens' if len(hits) > 1 else 'insufficient metadata signal'
    return {'type': None, 'confidence': ambiguous_confidence if hits else 0.0, 'reason': reason}


def batch_structure(manifest, policy=None):
    _, pack = _policy_sections(policy)
    profile = pack.get('batch', {})
    expected = set(profile.get('expected_roles') or (
        'purchase_order', 'vat_invoice', 'sales_invoice', 'commercial_invoice', 'packing_list',
        'warehouse_release', 'export_declaration'))
    aliases = profile.get('lifecycle_aliases') or {
        'draft_vat_invoice': 'vat_invoice', 'main_vat_invoice': 'vat_invoice', 'invoice': 'vat_invoice',
        'export_declaration_draft': 'export_declaration',
        'export_declaration_final': 'export_declaration', 'customs_declaration': 'export_declaration',
        'e11': 'export_declaration', 'e13': 'export_declaration', 'e15': 'export_declaration',
    }
    documents = [(aliases.get(role, role), role) for item in (manifest or [])
                 if (role := item.get('document_type')) and aliases.get(role, role) in expected]
    present = {role for role, subtype in documents}
    duplicates = {role for role, subtype in documents if documents.count((role, subtype)) > 1}
    return {'present': sorted(present), 'missing': sorted(expected - present),
            'duplicates': sorted(duplicates)}


def _nullable_string():
    return {'type': ['string', 'null']}


def _nullable_decimal():
    return {'type': ['number', 'string', 'null']}


def classification_response_schema():
    schema = {
        'type': 'object', 'additionalProperties': False, 'required': ['document_type', 'confidence'],
        'properties': {
            'document_type': {'type': 'string', 'enum': list(DOCUMENT_TYPES)},
            'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
        },
    }
    return {'type': 'json_schema', 'json_schema': {
        'name': 'logistics_document_classification', 'strict': True, 'schema': schema,
    }}


def extraction_template_contract(document_type, policy=None):
    extraction = (policy or {}).get('horizontal', {}).get('extraction', {})
    templates = extraction.get('templates', {})
    configured = templates.get(document_type) or templates.get('default') or {}
    if configured and not isinstance(configured, dict):
        raise ValueError('invalid extraction template contract')
    version = configured.get('version', PROMPT_VERSION)
    prompt = configured.get('prompt', DEFAULT_EXTRACTION_PROMPT)
    schema_version = configured.get('schema_version', SCHEMA_VERSION)
    if (not isinstance(version, str) or not version.strip() or not isinstance(schema_version, str)
            or not schema_version.strip() or not isinstance(prompt, str) or not prompt.strip()
            or '{document_type}' not in prompt or '{schema}' not in prompt):
        raise ValueError('invalid extraction template contract')
    snapshot = {'document_type': document_type, 'version': version, 'schema_version': schema_version,
                'prompt': prompt}
    snapshot['hash'] = hashlib.sha256(json.dumps(
        snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return snapshot


MAX_OCR_PAGES = 100
MAX_OCR_BOXES_PER_PAGE = 1000
MAX_OCR_CONTENT_LENGTH = 1000


def normalize_ocr_results(ocr_results):
    def invalid(path, category):
        raise ProcessingError('invalid OCR geometry', {'errors': [{'path': path, 'category': category}]})

    if not isinstance(ocr_results, dict) or set(ocr_results) != {'words', 'numbers', 'dates'}:
        invalid('ocr_results', 'shape')
    normalized = {}
    for category in ('words', 'numbers', 'dates'):
        pages = ocr_results[category]
        category_path = 'ocr_results.%s' % category
        if not isinstance(pages, dict) or len(pages) > MAX_OCR_PAGES:
            invalid(category_path, 'pages')
        normalized[category] = {}
        for page, boxes in pages.items():
            page_path = '%s.%s' % (category_path, page) if isinstance(page, str) and page else category_path
            if not isinstance(page, str) or not page or len(page) > 20 or not isinstance(boxes, list) or len(boxes) > MAX_OCR_BOXES_PER_PAGE:
                invalid(page_path, 'boxes')
            normalized[category][page] = []
            for index, box in enumerate(boxes):
                box_path = '%s[%s]' % (page_path, index)
                if not isinstance(box, dict) or set(box) != {'content', 'coords'} or not isinstance(box['content'], str) or len(box['content']) > MAX_OCR_CONTENT_LENGTH:
                    invalid(box_path, 'box')
                coords = box['coords']
                coords_path = '%s.coords' % box_path
                if not isinstance(coords, list) or len(coords) != 5 or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in coords):
                    invalid(coords_path, 'coordinates')
                center_x, center_y, width, height, angle = coords
                if not 0 <= center_x <= 1 or not 0 <= center_y <= 1 or not 0 <= width <= 1 or not 0 <= height <= 1 or not -360 <= angle <= 360:
                    invalid(coords_path, 'coordinate_range')
                normalized[category][page].append({'content': box['content'], 'coords': coords})
    return normalized


def extraction_response_schema(document_type, policy=None):
    _, pack = _policy_sections(policy)
    configured = set(pack.get('extraction_aliases', {}).values())
    allowed = set(DOCUMENT_TYPES[document_type]) | set(SHARED_PAYLOAD_FIELDS) | set(LINE_FIELDS)
    configured &= allowed
    decimal_fields = {'quantity', 'unit_price', 'price_per', 'value'}
    line = {
        'type': 'object', 'additionalProperties': False, 'required': list(LINE_FIELDS),
        'properties': {field: (_nullable_decimal() if field in decimal_fields else _nullable_string())
                       for field in LINE_FIELDS},
    }
    fields = tuple(dict.fromkeys(DOCUMENT_TYPES[document_type] + SHARED_PAYLOAD_FIELDS + tuple(sorted(configured))))
    properties = {field: _nullable_string() for field in fields}
    if 'total_value' in properties:
        properties['total_value'] = _nullable_decimal()
    if 'document_date' in properties:
        properties['document_date']['pattern'] = r'^(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})$'
    if 'lines' in properties:
        properties['lines'] = {'type': ['array', 'null'], 'items': line}
    payload = {
        'type': 'object', 'additionalProperties': False, 'required': list(fields), 'properties': properties,
    }
    spans = {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
        'required': ['page', 'text'], 'properties': {
            'page': {'type': ['integer', 'null']}, 'text': _nullable_string(),
        }}}
    geometry = {'type': 'object', 'additionalProperties': False, 'required': ['words', 'numbers', 'dates'],
        'properties': {category: {'type': 'object', 'additionalProperties': {
            'type': 'array', 'maxItems': MAX_OCR_BOXES_PER_PAGE, 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['content', 'coords'],
                'properties': {'content': {'type': 'string', 'maxLength': MAX_OCR_CONTENT_LENGTH},
                               'coords': {'type': 'array', 'minItems': 5, 'maxItems': 5,
                                          'items': {'type': 'number'}}},
            }}, 'maxProperties': MAX_OCR_PAGES} for category in ('words', 'numbers', 'dates')}}
    schema = {
        'type': 'object', 'additionalProperties': False,
        'required': ['document_type', 'confidence', 'payload', 'source_spans', 'ocr_results'],
        'properties': {
            'document_type': {'type': 'string', 'enum': [document_type]},
            'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
            'payload': payload, 'source_spans': spans, 'ocr_results': geometry,
        },
    }
    return {'type': 'json_schema', 'json_schema': {
        'name': 'logistics_document_extraction_%s' % document_type, 'strict': True, 'schema': schema,
    }}

SUPPORTED_MIMES = {
    'application/pdf', 'image/png', 'image/jpeg', 'text/csv',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'message/rfc822', 'application/json',
}
MAX_BYTES = 20 * 1024 * 1024
MAGIC = {
    'application/pdf': (b'%PDF-',), 'image/png': (b'\x89PNG\r\n\x1a\n',),
    'image/jpeg': (b'\xff\xd8\xff',),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': (b'PK\x03\x04',),
}


class ProcessingError(ValueError):
    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


def _bucket(value):
    if value == 0:
        return '0'
    for limit in (10, 100, 1000, 10000):
        if value <= limit:
            return '1-%s' % limit
    return '>10000'


def _character_class(character):
    if not character:
        return 'none'
    if character.isspace():
        return 'whitespace'
    if character.isalpha():
        return 'letter'
    if character.isdigit():
        return 'digit'
    return 'punctuation' if unicodedata.category(character).startswith('P') else 'other'


def _decode_provider_content(content, response=None):
    response = response if isinstance(response, dict) else {}
    choice = response.get('choices', [{}])[0] if isinstance(response.get('choices'), list) and response.get('choices') else {}
    finish_reason = choice.get('finish_reason') if isinstance(choice, dict) else None
    finish_category = finish_reason if finish_reason in ('stop', 'length', 'content_filter', 'tool_calls') else (
        'missing' if finish_reason is None else 'other')
    shape = {'provider': {'finish_reason_category': finish_category}}
    if isinstance(content, dict):
        return content, {**shape, 'content_type': 'dict', 'normalization': 'none'}
    if isinstance(content, list):
        shape.update({'content_type': 'array', 'part_count_bucket': _bucket(len(content)), 'part_types': []})
        texts = []
        for part in content:
            part_type = part.get('type') if isinstance(part, dict) else type(part).__name__
            shape['part_types'].append(str(part_type)[:40])
            if isinstance(part, dict) and part_type in ('text', 'output_text') and isinstance(part.get('text'), str):
                texts.append(part['text'])
        if not texts:
            raise ProcessingError('invalid provider content parts', shape)
        content = ''.join(texts)
    if not isinstance(content, str):
        raise ProcessingError('invalid provider content type', {'content_type': type(content).__name__})
    stripped = content.strip()
    starts_fence, ends_fence = stripped.startswith('```'), stripped.endswith('```')
    normalization = 'none'
    candidate = content
    if stripped.startswith('```json\n') and stripped.endswith('\n```') and stripped.count('```') == 2:
        candidate = stripped[8:-4]
        normalization = 'exact_json_fence'
    wrapper_category = ('exact_fence' if normalization == 'exact_json_fence' else 'other_fence' if starts_fence or ends_fence
                        else 'prose_prefix' if stripped and stripped[0] not in '[{' else
                        'prose_suffix' if stripped and stripped[-1] not in ']}' else 'none')
    common_diagnostics = {
        **shape, 'content_type': shape.get('content_type', 'string'), 'empty': not bool(stripped),
        'length_bucket': _bucket(len(content)), 'wrapper_category': wrapper_category,
    }
    try:
        return json.loads(candidate), {**common_diagnostics, 'normalization': normalization}
    except json.JSONDecodeError as exc:
        nonspace = content.strip()
        error_category = ('empty' if not nonspace else 'trailing_data' if exc.msg == 'Extra data' else
                          'unterminated' if exc.msg.startswith('Unterminated') else 'syntax')
        diagnostics = {
            **common_diagnostics, 'normalization': normalization,
            'first_character_class': _character_class(nonspace[:1]),
            'last_character_class': _character_class(nonspace[-1:]),
            'error_class': 'JSONDecodeError',
            'json_error': {'category': error_category, 'position_bucket': _bucket(exc.pos)},
            'truncation_category': ('provider_length' if finish_category == 'length' else
                                    'likely_incomplete' if error_category == 'unterminated' else 'not_indicated'),
            'errors': [{'path': '$', 'category': 'invalid_json'}],
        }
        raise ProcessingError('invalid provider JSON', diagnostics) from exc


def _json_type(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, str):
        return 'string'
    if isinstance(value, (int, float)):
        return 'number'
    if isinstance(value, list):
        return 'array'
    return 'object' if isinstance(value, dict) else 'unknown'


def _semantic_diagnostics(raw, selected_type=None):
    canonical = {'document_type', 'confidence', 'payload', 'source_spans', 'ocr_results'}
    diagnostics = {'content_type': _json_type(raw), 'errors': []}
    if not isinstance(raw, dict):
        diagnostics['errors'].append({'path': '$', 'category': 'type', 'expected': ['object'],
                                      'actual': _json_type(raw)})
        return diagnostics
    payload = raw.get('payload')
    document_type = raw.get('document_type')
    unknown_keys = sorted(set(raw) - canonical)
    diagnostics.update({
        'top_level_keys': sorted(canonical & set(raw)),
        'unknown_top_level_key_count': len(unknown_keys),
        'type_map': {key: _json_type(raw[key]) for key in canonical & set(raw)},
        'missing_required_keys': sorted(canonical - set(raw)),
        'document_type': {'valid': document_type in DOCUMENT_TYPES,
                          'matches_selected': selected_type is None or document_type == selected_type},
        'confidence': {'type': _json_type(raw.get('confidence')),
                       'in_range': isinstance(raw.get('confidence'), (int, float)) and not isinstance(raw.get('confidence'), bool)
                                   and 0 <= raw['confidence'] <= 1},
    })
    for key, expected in (('document_type', ['string']), ('confidence', ['number']),
                          ('payload', ['object']), ('source_spans', ['array'])):
        if key not in raw:
            diagnostics['errors'].append({'path': key, 'category': 'required', 'expected': expected})
        elif _json_type(raw[key]) not in expected:
            diagnostics['errors'].append({'path': key, 'category': 'type', 'expected': expected,
                                          'actual': _json_type(raw[key])})
    if isinstance(payload, dict) and document_type in DOCUMENT_TYPES:
        fields = set(DOCUMENT_TYPES[document_type]) | set(SHARED_PAYLOAD_FIELDS) | set(LINE_FIELDS)
        present = fields & set(payload)
        missing = sorted(field for field in DOCUMENT_TYPES[document_type] if payload.get(field) in (None, '', []))
        diagnostics['payload'] = {
            'present_keys': sorted(present), 'type_map': {key: _json_type(payload[key]) for key in present},
            'missing_required': missing,
        }
        for field in missing:
            diagnostics['errors'].append({'path': 'payload.%s' % field, 'category': 'required_non_null',
                                          'expected': ['string'] if field != 'lines' else ['array']})
        lines = payload.get('lines')
        diagnostics['payload']['lines'] = {'type': _json_type(lines),
                                            'count_bucket': _bucket(len(lines)) if isinstance(lines, list) else None}
        if isinstance(lines, list):
            errors = {}
            decimal_fields = {'quantity', 'unit_price', 'price_per', 'value'}
            for line in lines:
                if not isinstance(line, dict):
                    errors['payload.lines[]'] = ['object']
                else:
                    for field in LINE_FIELDS:
                        value = line.get(field)
                        expected = ['number', 'string', 'null'] if field in decimal_fields else ['string', 'null']
                        path = 'payload.lines[].%s' % field
                        if field in line and _json_type(value) not in expected:
                            errors[path] = expected
                        elif field in decimal_fields and value is not None:
                            try:
                                normalize_decimal(value)
                            except ValueError:
                                diagnostics['errors'].append({'path': path, 'category': 'invalid_decimal'})
            diagnostics['payload']['lines']['errors'] = sorted(errors)
            diagnostics['errors'].extend({'path': path, 'category': 'type', 'expected': errors[path]}
                                          for path in sorted(errors))
            diagnostics['errors'] = list({(error['path'], error['category']): error
                                          for error in diagnostics['errors']}.values())
        date = payload.get('document_date')
        date_format = 'missing'
        if date is not None:
            for label, date_pattern, date_format_string in (
                    ('valid', r'\d{4}-\d{2}-\d{2}', '%Y-%m-%d'),
                    ('vietnamese_normalizable', r'\d{2}/\d{2}/\d{4}', '%d/%m/%Y'),
                    ('dot_normalizable', r'\d{2}\.\d{2}\.\d{4}', '%d.%m.%Y'),
                    ('dash_normalizable', r'\d{2}-\d{2}-\d{4}', '%d-%m-%Y')):
                try:
                    if isinstance(date, str) and re.fullmatch(date_pattern, date):
                        datetime.strptime(date, date_format_string)
                        date_format = label
                        break
                except ValueError:
                    pass
            else:
                date_format = 'malformed'
                diagnostics['errors'].append({'path': 'payload.document_date', 'category': 'format',
                                              'expected': ['YYYY-MM-DD', 'DD/MM/YYYY']})
        diagnostics['payload']['date_format'] = date_format
    return diagnostics


class LocalDocumentProcessor:
    provider = 'local-deterministic'
    model_version = 'stdlib-v1'
    prompt_version = 'none'
    schema_version = '1'

    def _validate_binary(self, content, mimetype):
        if mimetype not in SUPPORTED_MIMES:
            raise ProcessingError('unsupported MIME')
        if not isinstance(content, bytes) or not content or len(content) > MAX_BYTES:
            raise ProcessingError('invalid document size')
        if mimetype in MAGIC and not content.startswith(MAGIC[mimetype]):
            raise ProcessingError('MIME and magic signature mismatch')
        try:
            if mimetype == 'application/pdf':
                eof = content.rfind(b'%%EOF')
                if b'/Encrypt' in content:
                    raise ProcessingError('encrypted PDF')
                if eof < 0 or not any(marker in content for marker in (b'/Type /Page', b'/Type/Page', b'/Type /Pages', b'/Type/Pages', b'/ObjStm', b'/Pages')):
                    raise ProcessingError('malformed PDF structure')
                if (content[eof + 5:].strip() and not content[eof + 5:].strip().startswith(b'%')) or any(marker in content for marker in (b'/JavaScript', b'/JS', b'/Launch', b'/EmbeddedFile')):
                    raise ProcessingError('unsafe PDF active content')
            elif mimetype == 'image/png' and (len(content) < 24 or content[12:16] != b'IHDR'):
                raise ProcessingError('malformed PNG structure')
            elif mimetype == 'image/jpeg' and not content.endswith(b'\xff\xd9'):
                raise ProcessingError('malformed JPEG structure')
            elif mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    names = archive.namelist()
                    if '[Content_Types].xml' not in names or not any(
                            name.startswith('xl/worksheets/sheet') for name in names):
                        raise ProcessingError('malformed XLSX structure')
                    if any(name.startswith(('xl/embeddings/', 'xl/externalLinks/')) or name.endswith('vbaProject.bin') for name in names):
                        raise ProcessingError('unsafe XLSX embedded content')
            elif mimetype == 'message/rfc822':
                message = BytesParser(policy=policy.default).parsebytes(content)
                if not message.get('From') or not message.get('Subject'):
                    raise ProcessingError('malformed EML structure')
                if any(part.get_filename() or part.get_content_disposition() == 'attachment' for part in message.walk()):
                    raise ProcessingError('unsafe EML embedded content')
        except (zipfile.BadZipFile, ElementTree.ParseError, UnicodeError) as exc:
            raise ProcessingError('malformed document structure') from exc

    def _xlsx_payload(self, content):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            shared = []
            if 'xl/sharedStrings.xml' in archive.namelist():
                root = ElementTree.fromstring(archive.read('xl/sharedStrings.xml'))
                shared = [''.join(node.itertext()) for node in root]
            root = ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        rows = []
        for row in root.findall('.//{*}row'):
            values = []
            for cell in row.findall('{*}c'):
                value = cell.find('{*}v')
                inline = cell.find('{*}is')
                text = ''.join(inline.itertext()) if inline is not None else value.text if value is not None else ''
                values.append(shared[int(text)] if cell.get('t') == 's' and text else text)
            if any(value != '' for value in values):
                rows.append(values)
        header_prefix = ['document_type', 'confidence', 'supplier', 'supplier_address', 'supplier_number',
                         'po_reference', 'total_value', 'document_date', 'currency']
        line_prefix = ['material_code', 'description', 'quantity', 'unit_price', 'uom', 'value', 'custom_code']
        if (len(rows) < 4 or rows[0][:len(header_prefix)] != header_prefix
                or rows[2][:len(line_prefix)] != line_prefix
                or len(set(rows[0])) != len(rows[0]) or len(set(rows[2])) != len(rows[2])):
            raise ProcessingError('XLSX requires normalized document table')
        header, values, line_header = rows[0], rows[1], rows[2]
        if len(values) > len(header) or any(len(line) > len(line_header) for line in rows[3:]):
            raise ProcessingError('XLSX requires normalized document table')
        payload = {field: values[index] if index < len(values) else '' for index, field in enumerate(header[2:], 2)}
        payload['lines'] = [{field: line[index] if index < len(line) else '' for index, field in enumerate(line_header)}
                            for line in rows[3:]]
        return {'document_type': values[0], 'confidence': values[1], 'payload': payload}

    def _embedded(self, content, mimetype):
        if mimetype == 'application/json':
            return json.loads(content)
        if mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            return self._xlsx_payload(content)
        if mimetype == 'text/csv':
            rows = list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))))
            if not rows or 'document_type' not in rows[0]:
                raise ProcessingError('CSV requires document_type header and data')
            first = rows[0]
            payload = {key: value for key, value in first.items() if key not in ('document_type', 'confidence')}
            if 'lines' in payload:
                payload['lines'] = json.loads(payload['lines'])
            return {'document_type': first['document_type'], 'confidence': first.get('confidence', 1), 'payload': payload}
        if mimetype == 'message/rfc822':
            message = BytesParser(policy=policy.default).parsebytes(content)
            body = message.get_body(preferencelist=('plain',))
            return json.loads(body.get_content() if body else message.get_payload())
        return None

    def process(self, content, mimetype, metadata=None):
        self._validate_binary(content, mimetype)
        metadata = metadata or {}
        if metadata.get('fixture') == 'timeout':
            raise TimeoutError('local adapter timeout fixture')
        try:
            raw = metadata['provider_response'] if 'provider_response' in metadata else self._embedded(content, mimetype) or metadata
            if isinstance(raw, str):
                raw = json.loads(raw)
        except (json.JSONDecodeError, UnicodeError, TypeError) as exc:
            raise ProcessingError('invalid deterministic payload') from exc
        if not isinstance(raw, dict):
            raise ProcessingError('missing deterministic payload')
        logical_documents = raw.get('logical_documents')
        if logical_documents is not None:
            if set(raw) != {'logical_documents'} or not isinstance(logical_documents, list) or not logical_documents:
                raise ProcessingError('invalid logical documents')
            results = []
            for item in logical_documents:
                if (not isinstance(item, dict) or 'logical_documents' in item
                        or not isinstance(item.get('payload'), dict)
                        or not isinstance(item['payload'].get('lines'), list)
                        or not item['payload']['lines']):
                    raise ProcessingError('invalid logical document item')
                results.append(self.process(content, mimetype, {
                    'provider_response': item, 'idp_policy': metadata.get('idp_policy'),
                    'allow_review': True,
                }))
            return {'logical_documents': results, 'raw_response_hash': hashlib.sha256(
                json.dumps(raw, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
        document_type = raw.get('document_type', 'unknown')
        try:
            payload, validation_warnings = validate(
                document_type, raw.get('payload', {}), metadata.get('idp_policy'), with_warnings=True,
                allow_review=metadata.get('allow_review', False))
            confidence = float(raw.get('confidence', 1))
        except (ValueError, TypeError) as exc:
            raise ProcessingError('semantic validation failed') from exc
        if not 0 <= confidence <= 1:
            raise ProcessingError('invalid confidence')
        spans = raw.get('source_spans', [])
        if not isinstance(spans, list):
            raise ProcessingError('invalid source spans')
        if any(not isinstance(span, dict) or set(span) - {'page', 'text'} for span in spans):
            validation_warnings.append('source_spans[]')
        return {
            'document_type': document_type, 'payload': payload, 'confidence': confidence,
            'validation_warnings': sorted(set(validation_warnings)), 'source_spans': spans,
            'raw_response_hash': hashlib.sha256(
                json.dumps(raw, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        }


class IAPDocumentProcessor(LocalDocumentProcessor):
    provider = 'insilos-iap-openrouter'
    model_version = 'router-selected'
    prompt_version = PROMPT_VERSION
    schema_version = SCHEMA_VERSION

    def __init__(self, env, operation_id, credit_budget=1, run=None, run_max_credits=3,
                 classification_callback=None):
        self.env = env
        self.operation_id = operation_id
        self.credit_budget = credit_budget
        self.run = run
        self.run_max_credits = run_max_credits
        self.classification_callback = classification_callback
        self.router_response = None
        self.failure_context = {}

    def _models(self, mimetype):
        domain = self.env['openrouter.domain'].search([('code', '=', 'logistics_ocr'), ('active', '=', True)], limit=1)
        models = [domain.primary_model_id] + list(domain.fallback_model_ids)
        if mimetype == 'application/pdf':
            models = [model for model in models if model.supports_pdf_input]
        unique = {}
        for model in models:
            unique.setdefault(model.model_id, model)
        return sorted(unique.values(), key=lambda model: (not model.supports_strict_json_schema,
                                                           not bool(model.capability_evidence_source)))[:3]

    def _persist_attempt(self, attempt):
        if self.run:
            pending = json.loads(self.run.payload)
            pending.setdefault('provider_attempts', []).append(attempt)
            self.run.sudo().write({'payload': pending})
            self.env.cr.flush()

    @staticmethod
    def _request_format(model, schema):
        if model.supports_strict_json_schema:
            return schema, 'strict_json_schema'
        return {'type': 'json_object'}, 'json_object_local_validation'

    def process(self, content, mimetype, metadata=None):
        self._validate_binary(content, mimetype)
        metadata = metadata or {}
        encoded = base64.b64encode(content).decode('ascii')
        media = ({'type': 'file', 'file': {
            'filename': os.path.basename(str(metadata.get('filename') or 'document.pdf')),
            'file_data': 'data:application/pdf;base64,%s' % encoded,
        }} if mimetype == 'application/pdf' else {
            'type': 'image_url', 'image_url': {'url': 'data:%s;base64,%s' % (mimetype, encoded)},
        })
        common = {'temperature': 0, 'policy_metadata': {'version': self.prompt_version},
                  'budget_metadata': {'credit_budget': self.credit_budget}}
        if mimetype == 'application/pdf':
            common['plugins'] = [{'id': 'file-parser', 'pdf': {'engine': 'native'}}]
        models = self._models(mimetype)
        if not models:
            raise ProcessingError('no capable Logistics OCR models')
        charged, attempts = [], []
        remaining = self.run_max_credits
        deterministic = deterministic_classify(metadata)
        operation_ceiling = min(1 if mimetype not in ('application/pdf', 'image/png', 'image/jpeg') and deterministic['confidence'] >= float(
            _policy_sections(metadata.get('idp_policy'))[0].get('classification', {}).get(
                'thresholds', {}).get('iap_cutoff', .9)) else 2,
            int(self.run_max_credits // self.credit_budget))

        def can_call():
            return len(charged) < operation_ceiling and remaining >= self.credit_budget

        def charge(operation):
            nonlocal remaining
            charged.append(operation)
            remaining -= self.credit_budget
        horizontal, _pack = _policy_sections(metadata.get('idp_policy'))
        cutoff = float(horizontal.get('classification', {}).get('thresholds', {}).get('iap_cutoff', .9))
        classification_response = None
        if mimetype not in ('application/pdf', 'image/png', 'image/jpeg') and deterministic['confidence'] >= cutoff:
            document_type, classification_confidence = deterministic['type'], deterministic['confidence']
            classification_method = 'deterministic_metadata'
        else:
            hints = {'filename': os.path.basename(str(metadata.get('filename') or metadata.get('attachment_name') or ''))[:255],
                     'mimetype': mimetype, 'source_channel': str(metadata.get('source_channel') or '')[:40],
                     'email_subject': _sanitize_boundary_text(metadata.get('email_subject')),
                     'has_po_reference': bool(metadata.get('has_po_reference'))}
            schema = classification_response_schema()
            classification = None
            classification_limit = min(3, len(models))
            for index, model in enumerate(models[:classification_limit]):
                if not can_call():
                    break
                operation = '%s:classify:model:%s' % (self.operation_id, index)
                response_format, request_mode = self._request_format(model, schema)
                attempt = {'operation_id': operation, 'task': 'classification', 'model_index': index,
                           'model': model.model_id, 'request_mode': request_mode, 'requested_max_tokens': 1024}
                self._persist_attempt(attempt)
                charge(operation)
                try:
                    classification_response = self.env['openrouter.router'].complete(
                        'logistics_ocr', [{'role': 'user', 'content': [{'type': 'text', 'text':
                        'Classify only. Contract: %s. Hints: %s. Return JSON only.' %
                        (json.dumps(schema['json_schema']['schema'], sort_keys=True), json.dumps(hints, sort_keys=True))}, media]}],
                        response_format=response_format, operation_id=operation,
                        model_index=index, max_tokens=1024, **common)
                    classification, diagnostics = _decode_provider_content(
                        classification_response['choices'][0]['message']['content'], classification_response)
                    semantic = _semantic_diagnostics(classification)
                    if set(classification) != {'document_type', 'confidence'} or semantic['document_type']['valid'] is not True \
                            or not semantic['confidence']['in_range']:
                        raise ProcessingError('invalid classification semantics', semantic)
                    attempt.update({'outcome': 'valid', 'diagnostics': diagnostics})
                    break
                except Exception as exc:
                    attempt.update({'outcome': 'invalid', 'diagnostics': getattr(exc, 'diagnostics', {})})
                    if getattr(exc, 'nonretryable', False):
                        raise
            if classification is None:
                diagnostics = getattr(locals().get('exc'), 'diagnostics', {})
                if not can_call():
                    self.failure_context.update({
                        'provider_operations': charged,
                        'planned_operation_budget': operation_ceiling,
                        'used_operation_budget': len(charged), 'stop_reason': 'run_credit_ceiling',
                    })
                raise ProcessingError('invalid IAP OCR classification response', diagnostics)
            document_type, classification_confidence = classification['document_type'], float(classification['confidence'])
            classification_method = 'iap_multimodal'
        classification_context = {
            'document_type': document_type,
            'classification_confidence': classification_confidence,
            'classification_source': classification_method,
            'classification_operation_id': (self.operation_id + ':classify' if classification_response else
                                            self.operation_id + ':classify:deterministic'),
        }
        self.failure_context.update(classification_context)
        if self.classification_callback:
            self.classification_callback(classification_context)
        schema = extraction_response_schema(document_type, metadata.get('idp_policy'))
        template = extraction_template_contract(document_type, metadata.get('idp_policy'))
        prompt = template['prompt'].replace('{document_type}', document_type).replace(
            '{schema}', json.dumps(schema['json_schema']['schema'], sort_keys=True))
        if self.run:
            pending = json.loads(self.run.payload)
            pending['extraction_template'] = template
            self.run.sudo().write({
                'payload': pending, 'template_version': template['version'],
                'template_hash': template['hash'], 'schema_version': template['schema_version'],
            })
        candidates = []
        result = None
        extraction_response = None
        extraction_limit = min(3, len(models))
        for index, model in enumerate(models[:extraction_limit]):
            if not can_call():
                break
            operation = '%s:extract:%s:model:%s' % (self.operation_id, document_type, index)
            response_format, request_mode = self._request_format(model, schema)
            requested_max = min(max(model.extraction_max_tokens or 4096, 4096), 8192)
            attempt = {'operation_id': operation, 'task': 'extraction', 'model_index': index, 'model': model.model_id,
                       'request_mode': request_mode, 'requested_max_tokens': requested_max}
            attempts.append(attempt)
            self._persist_attempt(attempt)
            charge(operation)
            try:
                extraction_response = self.env['openrouter.router'].complete(
                    'logistics_ocr', [{'role': 'user', 'content': [{'type': 'text', 'text': prompt}, media]}],
                    response_format=response_format, operation_id=operation,
                    model_index=index, max_tokens=requested_max, **common)
                choice = extraction_response['choices'][0]
                raw, parse_diagnostics = _decode_provider_content(choice['message']['content'], extraction_response)
                semantic = _semantic_diagnostics(raw, document_type)
                fatal = [error for error in semantic['errors'] if error['category'] == 'type'
                         or error['path'] == 'payload.document_date']
                representable = (isinstance(raw, dict) and raw.get('document_type') == document_type
                                 and not fatal and not semantic['unknown_top_level_key_count'])
                if representable:
                    try:
                        geometry_warning = False
                        if 'ocr_results' in raw:
                            try:
                                raw = {**raw, 'ocr_results': normalize_ocr_results(raw['ocr_results'])}
                            except ProcessingError:
                                raw = {key: value for key, value in raw.items() if key != 'ocr_results'}
                                geometry_warning = True
                        candidate = super().process(content, mimetype, {'provider_response': raw, 'allow_review': True,
                                                                         'idp_policy': metadata.get('idp_policy')})
                        if 'ocr_results' in raw:
                            candidate['ocr_results'] = raw['ocr_results']
                        if geometry_warning:
                            candidate['validation_warnings'] = sorted(set(
                                candidate['validation_warnings'] + ['ocr_results']))
                            semantic['errors'].append({'path': 'ocr_results', 'category': 'invalid_geometry'})
                        completeness = len(candidate['validation_warnings'])
                        candidates.append((not bool(semantic['errors']), -completeness, candidate['confidence'],
                                           -index, candidate, semantic, attempt, extraction_response))
                        if not semantic['errors'] and not candidate['validation_warnings']:
                            result = candidate
                            attempt['outcome'] = 'valid'
                            break
                        attempt['outcome'] = 'semantic_review_candidate'
                    except ProcessingError as exc:
                        attempt['outcome'] = 'semantic_invalid'
                        safe_errors = exc.diagnostics.get('errors', [])
                        semantic['errors'].extend(safe_errors or [{'path': '$', 'category': 'semantic_validation'}])
                else:
                    attempt['outcome'] = 'semantic_invalid'
                    if not semantic['errors']:
                        semantic['errors'].append({'path': '$', 'category': 'unrepresentable_envelope'})
                attempt['diagnostics'] = {**parse_diagnostics, **semantic}
            except Exception as exc:
                diagnostics = getattr(exc, 'diagnostics', {
                    'error_class': type(exc).__name__[:120], 'errors': [{'path': '$', 'category': 'provider_failure'}]})
                diagnostics = {**diagnostics, 'request_mode': request_mode}
                attempt.update({'outcome': 'provider_or_parse_failure', 'diagnostics': diagnostics})
                if getattr(exc, 'nonretryable', False):
                    raise
        selected_attempt = attempts[-1] if attempts else None
        selected_response = extraction_response
        if result is None and candidates:
            _valid_schema, _completeness, _confidence, _order, result, diagnostics, selected_attempt, selected_response = max(candidates)
            result['validation_warnings'] = sorted(set(result.get('validation_warnings', []) +
                                                       ['AI extraction incomplete; human review required']))
            selected_attempt['selected_review_candidate'] = True
        budget = {'run_max_credits': self.run_max_credits,
                  'planned_operation_budget': operation_ceiling,
                  'used_operation_budget': len(charged)}
        if result is not None and not can_call() and result.get('validation_warnings'):
            budget['stop_reason'] = 'best_candidate_at_credit_ceiling'
        if result is None:
            diagnostics = attempts[-1].get('diagnostics', {}) if attempts else {}
            if not can_call():
                budget['stop_reason'] = 'run_credit_ceiling'
            self.failure_context.update({'diagnostics': diagnostics, 'provider_attempts': attempts,
                                         'provider_operations': charged, **budget})
            raise ProcessingError('invalid IAP OCR extraction response', diagnostics)
        result.update({'extraction_template': template, 'template_version': template['version'],
                       'template_hash': template['hash'], 'provider_attempts': attempts,
                       'provider_model': selected_response.get('model') or selected_attempt['model'],
                       'router_log_id': selected_response.get('log_id'), 'operation_id': selected_attempt['operation_id'],
                       'classification_operation_id': (self.operation_id + ':classify' if classification_response else
                                                       self.operation_id + ':classify:deterministic'),
                       'classification_source': classification_method,
                       'classification_confidence': classification_confidence,
                       'provider_operations': charged, **budget})
        return result


SyntheticDocumentProcessor = LocalDocumentProcessor
