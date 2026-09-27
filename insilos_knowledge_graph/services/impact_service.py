from datetime import timezone

from odoo.exceptions import ValidationError


class ImpactService:
    """Read-only measured impact for verified, non-legal canonical events."""

    BLOCKED_DOMAINS = {'LEGAL', 'REGULATORY', 'TRADE'}

    def measure(self, event, *, observed_at=None, paths=()):
        domain = str(event.get('domain', '')).upper()
        if domain in self.BLOCKED_DOMAINS or event.get('legal'):
            raise ValidationError('Trade/legal impact remains disabled until TRADE gates pass.')
        if not event.get('canonical') or not event.get('verified'):
            raise ValidationError('Impact requires a verified canonical non-legal event.')

        event_at = event.get('timestamp')
        mtti_seconds = None
        if event_at is not None and observed_at is not None:
            self._validate_timestamp(event_at, 'event timestamp')
            self._validate_timestamp(observed_at, 'observed projection timestamp')
            mtti_seconds = (observed_at - event_at).total_seconds()
            if mtti_seconds < 0:
                raise ValidationError('Observed projection timestamp precedes the event timestamp.')

        verified_paths = [path for path in paths if path and all(
            step.get('provenance', {}).get('verified') is True
            and step.get('provenance', {}).get('state') == 'VERIFIED'
            and bool(step.get('provenance', {}).get('evidence_reference'))
            for step in path
        )]
        verified_paths.sort(key=lambda path: tuple(
            step.get('edge_hash', '') for step in path
        ))
        entities = sorted({
            urn
            for path in verified_paths
            for step in path
            for urn in (step.get('from'), step.get('to'))
            if urn
        })
        evidence = sorted({
            step.get('evidence_reference')
            or step.get('provenance', {}).get('evidence_reference')
            for path in verified_paths
            for step in path
            if step.get('evidence_reference')
            or step.get('provenance', {}).get('evidence_reference')
        })
        return {
            'event_reference': event.get('reference'),
            'event_timestamp': event_at,
            'observed_at': observed_at,
            'measured_mtti_seconds': mtti_seconds,
            'affected_paths': verified_paths,
            'affected_entities': entities,
            'evidence_references': evidence,
            'action_proposal': event.get('action_proposal'),
            'execution': False,
        }

    @staticmethod
    def _validate_timestamp(value, label):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError('%s must be timezone-aware.' % label.capitalize())
        if value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValidationError('%s must use UTC.' % label.capitalize())
