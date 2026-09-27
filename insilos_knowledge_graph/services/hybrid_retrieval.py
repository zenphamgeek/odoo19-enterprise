from urllib.parse import unquote

from odoo.exceptions import ValidationError

from .evidence_service import EvidenceService
from .graph_projection import TRADE_MODELS
from .graph_service import GraphService


class HybridRetrieval:
    def __init__(self, env, *, graph_retriever=None, vector_retriever=None):
        self.env = env
        self.graph_retriever = graph_retriever or GraphService(env).neighbors
        self.vector_retriever = vector_retriever or self._retrieve_vectors

    def retrieve(self, urn, *, sources, query_embedding, embedding_model, top_n=5,
                 depth=1, limit=50, source_model=None):
        urn_model = self._urn_model(urn)
        if source_model and source_model != urn_model:
            raise ValidationError('KG source model does not match URN.')
        if urn_model in TRADE_MODELS:
            raise ValidationError('Trade and legal hybrid retrieval is disabled pending legal gates.')

        accessible_sources = sources.filtered(lambda source: source.user_has_access)
        paths = self._readable_paths(self.graph_retriever(urn, depth=depth, limit=limit))
        chunks = self.vector_retriever(
            query_embedding=query_embedding,
            sources=accessible_sources,
            embedding_model=embedding_model,
            top_n=top_n,
        ) if accessible_sources else []

        source_by_checksum = {
            source.attachment_id.checksum: source
            for source in accessible_sources
            if source.attachment_id and source.attachment_id.checksum
        }
        graph_citations = [
            {'edge_hash': path['edge_hash'], 'evidence_reference': path['evidence_reference']}
            for path in paths if path.get('edge_hash') and path.get('evidence_reference')
        ]
        vector_evidence = []
        source_citations = []
        attachment_citations = []
        seen_sources = set()
        seen_attachments = set()
        for chunk in chunks:
            attachment = chunk.attachment_id
            source = source_by_checksum.get(attachment.checksum)
            if not source:
                continue
            vector_evidence.append({'content': chunk.content, 'source_id': source.id,
                                    'attachment_id': attachment.id})
            if source.id not in seen_sources:
                source_citations.append({'source_id': source.id, 'name': source.name,
                                         'url': source.url or None})
                seen_sources.add(source.id)
            if attachment.id not in seen_attachments:
                attachment_citations.append({'attachment_id': attachment.id,
                                             'name': attachment.name})
                seen_attachments.add(attachment.id)

        return {
            'graph_paths': paths,
            'vector_evidence': vector_evidence,
            'citations': {
                'graph_edges': graph_citations,
                'sources': source_citations,
                'attachments': attachment_citations,
            },
        }

    def _readable_paths(self, paths):
        evidence = EvidenceService(self.env)
        readable = []
        for path in paths:
            edge_hash = path.get('edge_hash')
            edge = self.env['kg.edge'].search([('edge_hash', '=', edge_hash)], limit=1) if edge_hash else None
            envelope = evidence.envelope(edge) if edge else None
            if envelope:
                readable.append(dict(path, provenance=envelope,
                                     evidence_reference=envelope['evidence_reference']))
        return readable

    @staticmethod
    def _urn_model(urn):
        parts = urn.split(':', 5) if isinstance(urn, str) else []
        if len(parts) != 6 or parts[:3] != ['urn', 'insilos', 'kg'] or not parts[3].isdigit():
            raise ValidationError('Invalid KG URN.')
        return unquote(parts[4])

    def _retrieve_vectors(self, **kwargs):
        return self.env['ai.embedding']._get_similar_chunks(**kwargs)
