from types import SimpleNamespace

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..services.graph_identity import node_urn
from ..services.graph_projection import GraphProjection
from ..services.hybrid_retrieval import HybridRetrieval


class FakeSources(list):
    def filtered(self, predicate):
        return FakeSources(source for source in self if predicate(source))


@tagged('post_install', '-at_install')
class TestHybridRetrieval(TransactionCase):
    def _source(self, source_id, attachment_id, checksum, *, allowed=True):
        attachment = SimpleNamespace(
            id=attachment_id, checksum=checksum, name='attachment-%s' % attachment_id)
        return SimpleNamespace(
            id=source_id, name='source-%s' % source_id, url=False,
            attachment_id=attachment, user_has_access=allowed)

    def test_preserves_separate_citations_without_fabrication(self):
        allowed = self._source(1, 11, 'allowed')
        denied = self._source(2, 22, 'denied', allowed=False)
        rogue_attachment = SimpleNamespace(id=99, checksum='rogue', name='rogue')
        calls = []

        def vectors(**kwargs):
            calls.append(kwargs)
            return [
                SimpleNamespace(content='allowed chunk', attachment_id=allowed.attachment_id),
                SimpleNamespace(content='unmapped chunk', attachment_id=rogue_attachment),
            ]

        records = self.env['res.partner'].create([
            {'name': 'hybrid source'}, {'name': 'hybrid target'}, {'name': 'hybrid evidence'}])
        projection = GraphProjection(self.env)
        nodes = [projection.project_node(self.env.company, 'res.partner', record.id, {})
                 for record in records[:2]]
        edge = projection.project_edge(self.env.company, nodes[0], 'RELATED_TO', nodes[1], {
            'source_type': 'BUSINESS_RECORD', 'source_reference': 'rs.partner:%s' % records[2].id,
            'source_hash': 'a' * 64, 'evidence_reference': 'rs.partner:%s' % records[2].id,
            'verified': True, 'state': 'VERIFIED', 'derivation': 'DETERMINISTIC'})
        graph_path = {
            'edge_hash': edge.edge_hash, 'from': nodes[0].urn, 'relation': 'RELATED_TO',
            'to': nodes[1].urn, 'evidence_reference': 'forged:7', 'state': 'VERIFIED',
        }
        result = HybridRetrieval(
            self.env, graph_retriever=lambda *args, **kwargs: [graph_path],
            vector_retriever=vectors,
        ).retrieve(
            nodes[0].urn, sources=FakeSources([allowed, denied]), query_embedding=[0.1],
            embedding_model='existing-model')

        self.assertEqual(calls[0]['sources'], [allowed])
        self.assertEqual(result['graph_paths'][0]['edge_hash'], edge.edge_hash)
        self.assertEqual(result['graph_paths'][0]['evidence_reference'],
                         'rs.partner:%s' % records[2].id)
        self.assertEqual(result['vector_evidence'], [
            {'content': 'allowed chunk', 'source_id': 1, 'attachment_id': 11}])
        self.assertEqual(result['citations'], {
            'graph_edges': [{'edge_hash': edge.edge_hash,
                             'evidence_reference': 'rs.partner:%s' % records[2].id}],
            'sources': [{'source_id': 1, 'name': 'source-1', 'url': None}],
            'attachments': [{'attachment_id': 11, 'name': 'attachment-11'}],
        })
        self.assertNotIn(denied.id, [evidence['source_id'] for evidence in result['vector_evidence']])
        self.assertNotIn(denied.attachment_id.id,
                         [evidence['attachment_id'] for evidence in result['vector_evidence']])
        self.assertNotIn(denied.id, [source['source_id'] for source in result['citations']['sources']])
        self.assertNotIn(denied.attachment_id.id,
                         [attachment['attachment_id']
                          for attachment in result['citations']['attachments']])
        self.assertNotIn('denied', repr(result))

    def test_no_accessible_source_skips_existing_retriever(self):
        denied = self._source(2, 22, 'denied', allowed=False)

        def forbidden(**kwargs):
            self.fail('vector retriever must not receive inaccessible sources')

        result = HybridRetrieval(
            self.env, graph_retriever=lambda *args, **kwargs: [],
            vector_retriever=forbidden,
        ).retrieve(
            node_urn(self.env.company.id, 'res.partner', 1),
            sources=FakeSources([denied]), query_embedding=[0.1],
            embedding_model='existing-model')
        self.assertEqual(result['vector_evidence'], [])
        self.assertEqual(result['citations'], {
            'graph_edges': [], 'sources': [], 'attachments': []})

    def test_trade_and_legal_retrieval_remains_disabled(self):
        service = HybridRetrieval(
            self.env, graph_retriever=lambda *args, **kwargs: self.fail('graph called'),
            vector_retriever=lambda **kwargs: self.fail('vector called'))
        for source_model in ('trade.hs', 'legal.document'):
            urn = node_urn(self.env.company.id, source_model, 1)
            with self.assertRaises(ValidationError):
                service.retrieve(
                    urn, sources=FakeSources(), query_embedding=[0.1],
                    embedding_model='existing-model')
            with self.assertRaises(ValidationError):
                service.retrieve(
                    urn, sources=FakeSources(), query_embedding=[0.1],
                    embedding_model='existing-model', source_model='res.partner')
