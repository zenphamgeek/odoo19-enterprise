import hashlib
import json
from dataclasses import dataclass, replace


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _hash(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class ProjectionEvent:
    source: str
    cursor: str
    event_type: str
    payload_json: str
    payload_hash: str
    event_hash: str

    @classmethod
    def create(cls, source, cursor, event_type, payload):
        payload_json = _canonical(payload)
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        event_hash = _hash([str(source), str(cursor), str(event_type), payload_hash])
        return cls(str(source), str(cursor), str(event_type), payload_json, payload_hash, event_hash)

    @property
    def payload(self):
        return json.loads(self.payload_json)


@dataclass(frozen=True)
class ProjectionState:
    event: ProjectionEvent
    status: str = 'PENDING'
    attempts: int = 0
    error: str | None = None


@dataclass(frozen=True)
class Reconciliation:
    source: str
    cursor: str | None
    accepted: int
    projected: int
    pending_retry: int
    dead_letter: int


class ProjectionEventService:
    """Process-local projection contract; intentionally provides no durable delivery."""

    def __init__(self, projector, max_attempts=3):
        self.projector = projector
        self.max_attempts = max_attempts
        self._states = {}
        self._identity_hashes = {}
        self._cursors = {}

    def replay(self, event):
        identity = (event.source, event.cursor, event.event_type)
        bound_hash = self._identity_hashes.get(identity)
        if bound_hash and bound_hash != event.payload_hash:
            raise ValueError('Projection event identity is already bound to different payload.')
        self._identity_hashes[identity] = event.payload_hash
        state = self._states.get(event.event_hash)
        if state and state.status == 'PROJECTED':
            return state
        state = state or ProjectionState(event)
        return self._attempt(state)

    def retry(self, event_hash):
        state = self._states[event_hash]
        if state.status != 'RETRY':
            return state
        return self._attempt(state)

    def _attempt(self, state):
        attempts = state.attempts + 1
        try:
            self.projector(state.event)
        except Exception as error:  # Projection is best-effort; never escape into the business transaction.
            status = 'DEAD_LETTER' if attempts >= self.max_attempts else 'RETRY'
            state = replace(state, status=status, attempts=attempts, error=str(error))
        else:
            state = replace(state, status='PROJECTED', attempts=attempts, error=None)
            self._cursors[state.event.source] = state.event.cursor
        self._states[state.event.event_hash] = state
        return state

    def source_cursor(self, source):
        return self._cursors.get(str(source))

    def reconcile(self, source):
        source = str(source)
        states = [state for state in self._states.values() if state.event.source == source]
        return Reconciliation(
            source=source,
            cursor=self.source_cursor(source),
            accepted=len(states),
            projected=sum(state.status == 'PROJECTED' for state in states),
            pending_retry=sum(state.status == 'RETRY' for state in states),
            dead_letter=sum(state.status == 'DEAD_LETTER' for state in states),
        )
