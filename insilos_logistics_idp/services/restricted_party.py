"""Restricted party screening (SRS 31.5) - provider-neutral, fail-closed review.

ponytail: parties are collected from case/reconciliation payloads only; typed
asset matching, ownership rules, and list-change re-screen notifications join
when structured list evidence exists (31.5 optional facets). Matches route to
review; screening never blocks and never asserts legal authority.
"""
from difflib import SequenceMatcher

DEFAULT_THRESHOLD = 0.92
CANONICAL_PARTY_ROLES = ('supplier', 'buyer', 'shipper', 'consignee', 'notify_party', 'beneficial_owner')
CANONICAL_IDENTIFIER_TYPES = ('lei', 'imo', 'mmsi', 'icao', 'iata', 'imo_number', 'aircraft_registration', 'tax_id', 'passport', 'other')
CANONICAL_ASSET_TYPES = ('vessel', 'aircraft')


def normalize_party(value):
    return ' '.join(str(value or '').lower().split())


def _canonical_items(items):
    return tuple((item['type'], item['value']) for item in items)


def canonical_party_evidence(*payloads):
    evidence = []
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        raw = payload.get('parties')
        if raw is None:
            raw = [{'role': 'supplier', 'name': payload.get('supplier'), 'identifiers': [], 'assets': []},
                   {'role': 'buyer', 'name': payload.get('buyer_name'), 'identifiers': [], 'assets': []}]
        if not isinstance(raw, list):
            continue
        for party in raw:
            if not isinstance(party, dict) or party.get('role') not in CANONICAL_PARTY_ROLES:
                continue
            name = normalize_party(party.get('name'))
            identifiers = []
            raw_identifiers = party.get('identifiers', [])
            if isinstance(raw_identifiers, list):
                for identifier in raw_identifiers:
                    if isinstance(identifier, dict):
                        kind = normalize_party(identifier.get('type'))
                        value = normalize_party(identifier.get('value'))
                        if kind in CANONICAL_IDENTIFIER_TYPES and value:
                            identifiers.append({'type': kind, 'value': value})
                    elif normalize_party(identifier):
                        identifiers.append({'type': 'other', 'value': normalize_party(identifier)})
            assets = []
            for asset in party.get('assets', []) if isinstance(party.get('assets', []), list) else []:
                if isinstance(asset, dict) and asset.get('type') in CANONICAL_ASSET_TYPES:
                    value = normalize_party(asset.get('value') or asset.get('name'))
                    if value:
                        assets.append({'type': asset['type'], 'value': value})
            identifiers = sorted({(item['type'], item['value']): item for item in identifiers}.values(), key=lambda item: (item['type'], item['value']))
            if name or identifiers or assets:
                evidence.append({'role': party['role'], 'name': name, 'identifiers': identifiers, 'assets': assets})
    return sorted({(item['role'], item['name'], _canonical_items(item['identifiers']), _canonical_items(item['assets'])): item for item in evidence}.values(),
                  key=lambda item: (item['role'], item['name'], _canonical_items(item['identifiers']), _canonical_items(item['assets'])))


def sanitize_lists(raw_lists):
    lists = []
    for raw in raw_lists if isinstance(raw_lists, list) else []:
        if not isinstance(raw, dict):
            continue
        entries = []
        raw_entries = raw.get('entries')
        for entry in raw_entries if isinstance(raw_entries, list) else []:
            if not isinstance(entry, dict):
                continue
            aliases = [normalize_party(alias) for alias in (entry.get('aliases') or [])
                       if isinstance(alias, str)] if isinstance(entry.get('aliases', []), list) else []
            name = normalize_party(entry.get('name'))
            id_numbers = sorted({normalize_party(value) for value in entry.get('id_numbers', []) if normalize_party(value)}) if isinstance(entry.get('id_numbers', []), list) else []
            if not name and not any(aliases) and not id_numbers:
                continue
            entries.append({
                'name': name,
                'aliases': [alias for alias in aliases if alias],
                'country': entry.get('country'),
                'id_numbers': id_numbers,
            })
        if not entries:
            continue
        lists.append({
            'list_name': raw.get('list_name'),
            'program': raw.get('program'),
            'source': raw.get('source'),
            'version': raw.get('version'),
            'entries': entries,
        })
    return lists


def screen_parties(parties, lists, threshold=DEFAULT_THRESHOLD):
    parties = sorted({normalize_party(party) for party in parties if normalize_party(party)})
    sanitized = sanitize_lists(lists)
    complete = bool(sanitized) and len(sanitized) == len(lists)
    for raw in lists if isinstance(lists, list) else []:
        if not isinstance(raw, dict) or not isinstance(raw.get('entries'), list):
            complete = False
            continue
        if raw.get('complete') is False or raw.get('incomplete') is True:
            complete = False
        for entry in raw['entries']:
            if not isinstance(entry, dict):
                complete = False
                continue
            if (not isinstance(entry.get('name', ''), str)
                    or any(not isinstance(entry.get(key, []), list)
                           or any(not isinstance(value, str) for value in entry.get(key, []))
                           for key in ('aliases', 'id_numbers'))
                    or not sanitize_lists([{'entries': [entry]}])):
                complete = False
    hits = []
    for party in parties:
        for restriction_list in sanitized:
            for entry in restriction_list['entries']:
                candidates = [(value, False) for value in [entry['name']] + entry['aliases']]
                candidates += [(value, True) for value in entry['id_numbers']]
                for candidate, exact in candidates:
                    if not candidate:
                        continue
                    ratio = float(party == candidate) if exact else SequenceMatcher(None, party, candidate).ratio()
                    if (party == candidate) if exact else (ratio >= threshold):
                        hits.append({
                            'party': party, 'matched': candidate,
                            'entry_name': entry['name'], 'list_name': restriction_list['list_name'],
                            'program': restriction_list['program'],
                            'source': restriction_list['source'],
                            'version': restriction_list['version'],
                            'country': entry.get('country'),
                            'id_numbers': entry.get('id_numbers'),
                            'ratio': round(ratio, 4),
                        })
                        break
    result = {'verdict': 'review' if hits or not complete or not parties else 'pass', 'hits': hits,
              'lists_consulted': len(sanitized)}
    if not complete or not parties:
        result['reason'] = 'restricted_party_screening_incomplete'
    return result
