import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from odoo.exceptions import ValidationError

REGISTRY_KEY = 'traluat_documents'
ENDPOINT = 'https://traluat.com/api/documents'
HOST = 'traluat.com'
ALLOWED_QUERY = {'keyword', 'page', 'pageSize'}
MAX_PAGES = 10
MAX_RESULTS = 200
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT = 10
RETRIES = 3
_CONFIG = Path(__file__).resolve().parents[1] / 'config'


def _registry():
    policy = json.loads((_CONFIG / 'compliance_policy.json').read_text())
    pack = json.loads((_CONFIG / 'vn_legal_candidate_pack.json').read_text())
    provider = policy['provider_registry'][REGISTRY_KEY]
    option = pack['source_options'][REGISTRY_KEY]
    required = {
        'license_terms': 'pending', 'retention_terms': 'pending',
        'content_owner': 'pending', 'independent_oracle_status': 'pending',
    }
    if (provider['base_endpoint'] != ENDPOINT or option['base_endpoint'] != ENDPOINT
            or provider['allowed_methods'] != ['GET'] or option['allowed_methods'] != ['GET']
            or provider.get('source_tier') != 'early_warning_tier_4'
            or provider.get('verification') != 'pending_independent_verification'
            or provider.get('legal_authority') is not False or provider.get('auto_activation') is not False
            or option.get('source_tier') != 'early_warning_tier_4'
            or option.get('verification') != 'pending_independent_verification'
            or option.get('legal_authority') is not False or option.get('activation') is not False
            or option.get('automatic_activation') is not False
            or option.get('expected_terminal_status') != 'review'
            or any(option.get(key) != value for key, value in required.items())):
        raise ValidationError('Candidate API registry configuration is invalid.')
    return provider, option


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _validate_addresses(host):
    answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not answers:
        raise ValidationError('Candidate API DNS returned no answers.')
    addresses = []
    for answer in answers:
        address = ipaddress.ip_address(answer[4][0])
        if not address.is_global:
            raise ValidationError('Candidate API DNS answer is not public.')
        addresses.append(str(address))
    return tuple(sorted(set(addresses)))


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, address):
        super().__init__(HOST, 443, timeout=TIMEOUT, context=ssl.create_default_context())
        self._address = address

    def connect(self):
        sock = socket.create_connection((self._address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=HOST)


def _request(path):
    address = _validate_addresses(HOST)[0]
    connection = _PinnedHTTPSConnection(address)
    connection.request('GET', path, headers={'Accept': 'application/json', 'Host': HOST})
    response = connection.getresponse()
    try:
        if 300 <= response.status < 400:
            raise ValidationError('Candidate API redirects are forbidden.')
        if response.status != 200:
            raise OSError('HTTP %s' % response.status)
        content_type = response.getheader('Content-Type', '').split(';', 1)[0].strip().lower()
        if content_type not in ('application/json', 'application/problem+json') and not content_type.endswith('+json'):
            raise ValidationError('Candidate API response MIME is not JSON.')
        content_length = response.getheader('Content-Length')
        if content_length and (not content_length.isdigit() or int(content_length) > MAX_BYTES):
            raise ValidationError('Candidate API response exceeds maximum bytes.')
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValidationError('Candidate API response exceeds maximum bytes.')
        return body
    finally:
        connection.close()


def fetch_candidates(registry_key, query, *, now=None):
    if registry_key != REGISTRY_KEY:
        raise ValidationError('Unknown candidate API registry key.')
    _registry()
    if not isinstance(query, dict) or set(query) - ALLOWED_QUERY:
        raise ValidationError('Candidate API query contains unapproved fields.')
    if any(not isinstance(value, (str, int)) or isinstance(value, bool) for value in query.values()):
        raise ValidationError('Candidate API query values must be strings or integers.')
    base_query = {key: value for key, value in query.items() if key != 'page'}
    if not str(base_query.get('keyword', '')).strip():
        raise ValidationError('Candidate API query requires an approved keyword.')
    page_size = base_query.get('pageSize', 20)
    if not isinstance(page_size, int) or not 1 <= page_size <= 100:
        raise ValidationError('Candidate API pageSize is invalid.')
    page = query.get('page', 1)
    if not isinstance(page, int) or not 1 <= page <= MAX_PAGES:
        raise ValidationError('Candidate API page is invalid.')
    fingerprint = hashlib.sha256(_canonical({
        'method': 'GET', 'registry_key': registry_key, 'endpoint': ENDPOINT,
        'query': {**base_query, 'page': page, 'pageSize': page_size},
    }).encode()).hexdigest()
    collected = []
    bodies = []
    attempts = 0
    last_error = None
    seen_pages = set()
    for _ in range(MAX_PAGES):
        if page in seen_pages:
            last_error = 'pagination_cycle'
            break
        seen_pages.add(page)
        params = {**base_query, 'page': page, 'pageSize': page_size}
        body = None
        for attempt in range(RETRIES):
            attempts += 1
            try:
                body = _request(urlsplit(ENDPOINT).path + '?' + urlencode(sorted(params.items())))
                break
            except ValidationError:
                raise
            except (OSError, TimeoutError, socket.timeout) as exc:
                last_error = type(exc).__name__
                if attempt + 1 < RETRIES:
                    time.sleep(0)
        if body is None:
            return _result(fingerprint, collected, bodies, now, last_error or 'request_exhausted', attempts, True)
        bodies.append(body)
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValidationError('Candidate API response is malformed JSON.')
        if not isinstance(payload, dict):
            raise ValidationError('Candidate API response must be a JSON object.')
        items = payload.get('data', payload.get('documents', payload.get('results', [])))
        if isinstance(items, dict):
            items = items.get('items', [])
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ValidationError('Candidate API response items are invalid.')
        collected.extend(items)
        if len(collected) >= MAX_RESULTS:
            collected = collected[:MAX_RESULTS]
            break
        meta = payload.get('meta') or {}
        if not isinstance(meta, dict):
            raise ValidationError('Candidate API pagination metadata is invalid.')
        next_page = meta.get('nextPage', meta.get('next_page'))
        total_pages = meta.get('totalPages', meta.get('total_pages'))
        if next_page is None and isinstance(total_pages, int) and page < total_pages:
            next_page = page + 1
        if next_page is None:
            break
        if not isinstance(next_page, int) or next_page <= page or next_page > MAX_PAGES:
            last_error = 'invalid_pagination'
            break
        page = next_page
    return _result(fingerprint, collected, bodies, now, last_error, attempts, False)


def _result(fingerprint, items, bodies, now, error, attempts, dead_letter):
    unique = {}
    conflicted = set()
    for item in items:
        normalized = json.loads(_canonical(item))
        key = str(item.get('id') or '%s|%s' % (item.get('docNumber', ''), item.get('issueDate', '')))
        if not key.strip('|'):
            error = 'missing_source_identity'
            continue
        if key in conflicted:
            continue
        content_hash = hashlib.sha256(_canonical(normalized).encode()).hexdigest()
        previous = unique.get(key)
        if previous and previous['content_sha256'] != content_hash:
            error = 'conflicting_source_version_hash'
            unique.pop(key)
            conflicted.add(key)
            continue
        source_version = str(item.get('updatedAt') or item.get('version') or content_hash)
        unique[key] = {
            'source_key': key, 'source_version': source_version,
            'content': normalized, 'content_sha256': content_hash,
        }
    retrieved = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    body_hashes = tuple(hashlib.sha256(body).hexdigest() for body in bodies)
    candidates = [unique[key] for key in sorted(unique)]
    return {
        'schema_version': '1.0', 'registry_key': REGISTRY_KEY, 'provider_id': REGISTRY_KEY,
        'endpoint_config_reference': 'compliance_policy.provider_registry.traluat_documents',
        'request_fingerprint': fingerprint,
        'response_sha256': hashlib.sha256(b''.join(bodies)).hexdigest(),
        'body_sha256': body_hashes,
        'content_sha256': hashlib.sha256(_canonical(candidates).encode()).hexdigest(),
        'raw_response_sha256': body_hashes, 'candidates': candidates,
        'retrieved_at_utc': retrieved, 'source_tier': 'early_warning_tier_4',
        'legal_authority': False, 'verification': 'unverified', 'verdict': 'REVIEW',
        'activation_allowed': False, 'citation_clean_url': ENDPOINT,
        'license_terms': 'pending', 'retention_terms': 'pending', 'content_owner': 'pending',
        'independent_oracle_status': 'pending', 'error_code': error,
        'machine_status': 'DEAD_LETTER' if dead_letter else ('REVIEW' if error else 'FETCHED_REVIEW'),
        'attempt_count': attempts, 'dead_letter': dead_letter,
    }
