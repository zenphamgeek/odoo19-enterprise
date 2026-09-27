# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""REC-01 pure cross-domain reconciliation evidence contract."""

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType


_OWNER_KINDS = {
    'finance': frozenset({'ledger', 'position'}),
    'logistics': frozenset({'document', 'trade_case'}),
}
_READ_OPERATIONS = frozenset({'read', 'reconcile'})


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError('evidence must be canonical JSON data') from error


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class EvidenceEnvelope:
    owner: str
    kind: str
    reference: str
    payload: object
    evidence_hash: str


def envelope(owner, kind, reference, payload):
    if owner not in _OWNER_KINDS:
        raise ValueError('unknown evidence owner')
    if kind not in _OWNER_KINDS[owner]:
        raise ValueError('%s does not own %s evidence' % (owner, kind))
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError('evidence reference is required')
    body = {'owner': owner, 'kind': kind, 'reference': reference, 'payload': payload}
    digest = sha256(_canonical(body).encode()).hexdigest()
    return EvidenceEnvelope(owner, kind, reference, _freeze(payload), digest)


def authorize(requester, evidence, operation):
    if requester not in _OWNER_KINDS:
        raise ValueError('unknown evidence owner')
    if operation not in _READ_OPERATIONS and requester != evidence.owner:
        raise PermissionError('cross-owner mutation/action is forbidden')
    return evidence


def replay(current, candidate):
    identity = (current.owner, current.kind, current.reference)
    if identity != (candidate.owner, candidate.kind, candidate.reference):
        raise ValueError('replay identity mismatch')
    if current.evidence_hash != candidate.evidence_hash:
        raise ValueError('replay payload conflict')
    return current
