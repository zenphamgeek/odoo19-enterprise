from datetime import datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

from ..services.graph_projection import GraphProjection
from ..services.graph_query import GraphQuery


@tagged('post_install', '-at_install')
class TestGraphQuery(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.projection = GraphProjection(cls.env)
        cls.records = cls.env['res.partner'].create([
            {'name': 'KG path start'}, {'name': 'KG path middle'}, {'name': 'KG path end'},
            {'name': 'KG evidence'},
        ])
        cls.nodes = [
            cls.projection.project_node(cls.env.company, 'res.partner', record.id, {'name': record.name})
            for record in cls.records[:3]
        ]
        cls.provenance = {
            'source_type': 'BUSINESS_RECORD',
            'source_reference': 'rs.partner:%s' % cls.records[3].id,
            'source_hash': 'a' * 64,
            'evidence_reference': 'rs.partner:%s' % cls.records[3].id,
            'verified': True,
            'state': 'VERIFIED',
            'derivation': 'DETERMINISTIC',
        }

    def test_bounded_explainable_path_and_distinct_bitemporal_filters(self):
        now = datetime.now()
        first = self.projection.project_edge(
            self.env.company, self.nodes[0], 'RELATED_TO', self.nodes[1], self.provenance,
            valid_from=now - timedelta(days=2), known_from=now - timedelta(hours=1))
        second = self.projection.project_edge(
            self.env.company, self.nodes[1], 'REFERENCES', self.nodes[2], self.provenance,
            valid_from=now - timedelta(days=2), known_from=now + timedelta(hours=1))
        query = GraphQuery(self.env)
        self.assertEqual(query.paths(
            self.nodes[0].urn, self.nodes[2].urn, valid_at=now, known_at=now), [])
        paths = query.paths(
            self.nodes[0].urn, self.nodes[2].urn,
            valid_at=now, known_at=now + timedelta(hours=2), max_depth=2)
        self.assertEqual([[step['edge_hash'] for step in path] for path in paths],
                         [[first.edge_hash, second.edge_hash]])
        self.assertEqual(paths[0][0]['provenance']['source_reference'], self.provenance['source_reference'])
        with self.assertRaises(ValidationError):
            query.paths(self.nodes[0].urn, self.nodes[2].urn, max_depth=4)
        with self.assertRaises(ValidationError):
            query.paths(self.nodes[0].urn, self.nodes[2].urn, limit=101)

    def test_acl_denial_returns_no_path_without_partial_leak(self):
        self.projection.project_edge(
            self.env.company, self.nodes[0], 'RELATED_TO', self.nodes[2], self.provenance)
        outsider = new_test_user(self.env, login='kg-path-no-reader', groups='base.group_user')
        self.assertEqual(GraphQuery(self.env(user=outsider)).paths(
            self.nodes[0].urn, self.nodes[2].urn), [])

    def test_unreadable_provenance_or_evidence_hides_whole_path(self):
        hidden = self.env['ir.model.access'].create({
            'name': 'KG hidden evidence',
            'model_id': self.env['ir.model']._get_id('res.partner'),
        })
        provenance = dict(
            self.provenance,
            source_reference='is.model.access:%s' % hidden.id,
            evidence_reference='is.model.access:%s' % hidden.id,
        )
        self.projection.project_edge(
            self.env.company, self.nodes[0], 'RELATED_TO', self.nodes[2], provenance)
        reader = new_test_user(
            self.env, login='kg-path-reader', groups='insilos_knowledge_graph.group_kg_reader')
        self.assertEqual(GraphQuery(self.env(user=reader)).paths(
            self.nodes[0].urn, self.nodes[2].urn), [])
