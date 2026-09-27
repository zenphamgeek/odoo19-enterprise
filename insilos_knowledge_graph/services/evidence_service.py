from odoo.exceptions import AccessError


class EvidenceService:
    def __init__(self, env):
        self.env = env

    def readable_node(self, node):
        try:
            node.check_access('read')
            return self._readable_record(node.source_model, node.source_id)
        except AccessError:
            return False

    def readable_edge(self, edge):
        try:
            edge.check_access('read')
        except AccessError:
            return False
        return (
            self.readable_node(edge.from_node_id)
            and self.readable_node(edge.to_node_id)
            and self._readable_reference(edge.source_reference)
            and self._readable_reference(edge.evidence_reference)
        )

    def envelope(self, edge):
        if not self.readable_edge(edge):
            return None
        return {
            'source_type': edge.source_type,
            'source_reference': edge.source_reference,
            'source_hash': edge.source_hash,
            'evidence_reference': edge.evidence_reference,
            'confidence': edge.confidence,
            'verified': edge.verified,
            'state': edge.state,
        }

    def _readable_reference(self, reference):
        if not reference:
            return False
        model, separator, record_id = reference.rpartition(':')
        return bool(separator and record_id.isdigit() and self._readable_record(model, record_id))

    def _readable_record(self, model_name, record_id):
        if model_name not in self.env:
            return False
        try:
            record = self.env[model_name].browse(int(record_id)).exists()
            record.check_access('read')
            return bool(record)
        except (AccessError, ValueError):
            return False
