import hashlib
import json
from urllib.parse import quote


def node_urn(company_id, source_model, source_id):
    return 'urn:insilos:kg:%s:%s:%s' % (
        int(company_id), quote(str(source_model), safe=''), quote(str(source_id), safe=''))


def canonical_hash(value):
    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def edge_hash(company_id, from_urn, relation, to_urn, valid_from=None, valid_to=None):
    return canonical_hash([
        int(company_id), from_urn, relation, to_urn,
        str(valid_from or ''), str(valid_to or ''),
    ])
