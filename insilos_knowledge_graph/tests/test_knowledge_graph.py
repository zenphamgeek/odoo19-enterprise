from datetime import datetime, timedelta
from unittest.mock import Mock

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

from ..services.graph_identity import canonical_hash, edge_hash, node_urn
from ..services.graph_projection import TRADE_MODELS, GraphProjection
from ..services.graph_service import GraphService
from ..services.hybrid_retrieval import HybridRetrieval
from ..services.impact_service import ImpactService
from ..services.ontology import RELATIONS, VERSION


@tagged('post_install', '-at_install')
class TestKnowledgeGraph(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.projection = GraphProjection(cls.env)
        cls.product = cls.projection.project_node(cls.company, 'product.product', 7, {'name': 'P'})
        cls.partner = cls.projection.project_node(cls.company, 'res.partner', 9, {'name': 'S'})
        cls.provenance = {
            'source_type': 'BUSINESS_RECORD', 'source_reference': 'fixture:1',
            'source_hash': 'a' * 64, 'evidence_reference': 'evidence:1',
            'verified': True, 'state': 'VERIFIED', 'derivation': 'DETERMINISTIC',
        }

    def test_foundation_contract(self):
        self.assertEqual(self.product.urn, node_urn(self.company.id, 'product.product', 7))
        self.assertEqual(self.product.urn, node_urn(self.company.id, 'product.product', 7))
        expected = edge_hash(self.company.id, self.product.urn, 'SUPPLIES', self.partner.urn)
        first = self.projection.project_edge(self.company, self.product, 'SUPPLIES', self.partner, self.provenance)
        second = self.projection.project_edge(self.company, self.product, 'SUPPLIES', self.partner, self.provenance)
        self.assertEqual((first.id, first.edge_hash), (second.id, expected))
        with self.assertRaises(ValidationError):
            self.env['kg.edge'].create(dict(
                self.provenance, company_id=self.company.id, from_node_id=self.product.id,
                to_node_id=self.partner.id, relation='NOT_IN_ONTOLOGY'))
        with self.assertRaises(ValidationError):
            self.env['kg.edge'].create(dict(
                self.provenance, evidence_reference=False, company_id=self.company.id,
                from_node_id=self.product.id, to_node_id=self.partner.id, relation='RELATED_TO'))

    def test_anti_drift_contract(self):
        self.assertEqual(VERSION, '1.0')
        self.assertEqual(RELATIONS, frozenset({
            'SUPPLIES', 'PURCHASED_FROM', 'SOLD_TO', 'CONTAINS', 'CLASSIFIED_AS',
            'SUBJECT_TO', 'ELIGIBLE_FOR', 'CLAIMS_ORIGIN', 'SUPPORTED_BY',
            'ISSUED_BY', 'ISSUED_TO', 'REFERENCES', 'REQUIRES', 'APPLIES_TO',
            'IMPLEMENTS', 'GUIDES', 'AMENDS', 'REPEALS', 'REPLACES', 'BASED_ON',
            'HAS_PSR', 'HAS_TARIFF', 'HAS_NTM', 'SHIPPED_FROM', 'SHIPPED_TO',
            'CARRIED_BY', 'FORWARDED_BY', 'PACKED_IN', 'BELONGS_TO', 'RELATED_TO',
            'CONTROLLED_BY', 'OWNED_BY', 'AFFECTS', 'IMPACTS_ENVIRONMENT', 'MONITORED_BY_CEMS',
            'SUBJECT_TO_CBAM', 'EMITS_GHG', 'CALCULATED_AS_SCOPE3',
        }))
        self.assertEqual(node_urn(self.company.id, 'res.partner', 9), self.partner.urn)
        self.assertEqual(canonical_hash({'a': [1, 2], 'b': {'c': 3}}),
                         canonical_hash({'b': {'c': 3}, 'a': [1, 2]}))
        projected = self.projection.project_node(
            self.company, 'product.product', 7, {'b': {'c': 3}, 'a': [1, 2]})
        self.assertEqual(projected.source_hash, canonical_hash({'a': [1, 2], 'b': {'c': 3}}))
        self.assertEqual(edge_hash(self.company.id, self.product.urn, 'RELATED_TO', self.partner.urn),
                         edge_hash(self.company.id, self.product.urn, 'RELATED_TO', self.partner.urn))
        with self.assertRaises(ValidationError):
            self.env['kg.edge'].create(dict(
                self.provenance, company_id=self.company.id, from_node_id=self.product.id,
                to_node_id=self.partner.id, relation='UNKNOWN'))
        now = datetime.now()
        with self.assertRaises(ValidationError):
            self.env['kg.edge'].create(dict(
                self.provenance, company_id=self.company.id, from_node_id=self.product.id,
                to_node_id=self.partner.id, relation='RELATED_TO', valid_from=now, valid_to=now - timedelta(seconds=1)))
        with self.assertRaises(ValidationError):
            self.env['kg.edge'].create(dict(
                self.provenance, company_id=self.company.id, from_node_id=self.product.id,
                to_node_id=self.partner.id, relation='RELATED_TO', known_from=now, known_to=now - timedelta(seconds=1)))
        edge = self.projection.project_edge(self.company, self.product, 'RELATED_TO', self.partner, self.provenance)
        with self.assertRaises(ValidationError):
            edge.write({'known_to': now})
        ai = self.env['kg.edge'].create(dict(
            self.provenance, company_id=self.company.id, from_node_id=self.product.id,
            to_node_id=self.partner.id, relation='REFERENCES', derivation='AI_EXTRACTION',
            state='VERIFIED', verified=True))
        self.assertEqual((ai.state, ai.verified), ('CANDIDATE', False))
        self.assertNotIn(ai.edge_hash, {item['edge_hash'] for item in GraphService(self.env).neighbors(self.product.urn)})
        graph, vector = Mock(), Mock()
        retrieval = HybridRetrieval(self.env, graph_retriever=graph, vector_retriever=vector)
        for source_model in TRADE_MODELS:
            with self.subTest(source_model=source_model), self.assertRaises(ValidationError):
                self.projection.project_node(self.company, source_model, 'blocked', {})
            with self.subTest(source_model=source_model), self.assertRaises(ValidationError):
                self.env['kg.node'].create({
                    'company_id': self.company.id, 'source_model': source_model, 'source_id': 'blocked'})
            with self.subTest(source_model=source_model), self.assertRaises(ValidationError):
                self.projection.project_edge(
                    self.company, Mock(source_model=source_model), 'RELATED_TO', self.partner, self.provenance)
            with self.subTest(source_model=source_model), self.assertRaises(ValidationError):
                retrieval.retrieve(node_urn(self.company.id, source_model, 'blocked'), sources=[],
                                   query_embedding=[], embedding_model='unused')
        graph.assert_not_called()
        vector.assert_not_called()
        with self.assertRaises(ValidationError):
            ImpactService().measure({'domain': 'LEGAL'})

    def test_acl_and_immutable_edge_contract(self):
        reader = new_test_user(
            self.env, login='kg-reader', groups='insilos_knowledge_graph.group_kg_reader')
        manager = new_test_user(
            self.env, login='kg-manager', groups='insilos_knowledge_graph.group_kg_manager')
        edge = self.projection.project_edge(
            self.company, self.product, 'RELATED_TO', self.partner, self.provenance)
        self.assertEqual(edge.with_user(reader).relation, 'RELATED_TO')
        with self.assertRaises(AccessError):
            self.env['kg.node'].with_user(reader).create({
                'company_id': self.company.id, 'source_model': 'product.product', 'source_id': '10'})
        managed = self.env['kg.node'].with_user(manager).create({
            'company_id': self.company.id, 'source_model': 'product.product', 'source_id': '11'})
        self.assertTrue(managed)
        with self.assertRaises(ValidationError):
            edge.write({'valid_to': datetime.now()})
        with self.assertRaises(ValidationError):
            self.product.write({'source_id': 'changed'})
        with self.assertRaises(ValidationError):
            edge.write({'source_reference': 'changed'})
        with self.assertRaises(ValidationError):
            edge.write({'state': 'REJECTED'})
        ai = self.env['kg.edge'].create(dict(
            self.provenance, company_id=self.company.id, from_node_id=self.product.id,
            to_node_id=self.partner.id, relation='REFERENCES', derivation='AI_EXTRACTION'))
        ai.write({'state': 'VERIFIED', 'verified': True})
        self.assertEqual((ai.state, ai.verified), ('CANDIDATE', False))

    def test_temporal_query_ai_containment_and_bounds(self):
        now = datetime.now()
        old = self.projection.project_edge(
            self.company, self.product, 'PURCHASED_FROM', self.partner, self.provenance,
            valid_from=now - timedelta(days=2), valid_to=now - timedelta(days=1))
        ai = self.env['kg.edge'].create(dict(
            self.provenance, company_id=self.company.id, from_node_id=self.product.id,
            to_node_id=self.partner.id, relation='REFERENCES', derivation='AI_EXTRACTION',
            state='VERIFIED', verified=True))
        self.assertEqual((ai.state, ai.verified), ('CANDIDATE', False))
        service = GraphService(self.env)
        manager = new_test_user(
            self.env, login='kg-query-manager', groups='insilos_knowledge_graph.group_kg_manager')
        manager_service = GraphService(self.env(user=manager))
        hashes = {edge['edge_hash'] for edge in service.neighbors(self.product.urn, as_of=now)}
        self.assertNotIn(old.edge_hash, hashes)
        self.assertNotIn(ai.edge_hash, hashes)
        with self.assertRaises(ValidationError):
            service.neighbors(self.product.urn, include_unverified=True)
        self.assertEqual(
            manager_service.neighbors(
                self.product.urn, include_unverified=True, trust_state='CANDIDATE')[0]['state'],
            'CANDIDATE')
        reader = new_test_user(
            self.env, login='kg-query-reader', groups='insilos_knowledge_graph.group_kg_reader')
        with self.assertRaises(AccessError):
            GraphService(self.env(user=reader)).neighbors(
                self.product.urn, include_unverified=True, trust_state='CANDIDATE')
        with self.assertRaises(ValidationError):
            GraphService(self.env).neighbors(self.product.urn, depth=4)
        with self.assertRaises(ValidationError):
            GraphService(self.env).neighbors(self.product.urn, limit=101)

    def test_company_isolation_trade_disabled_and_rebuild(self):
        other = self.env['res.company'].create({'name': 'KG Other'})
        alien = self.projection.project_node(other, 'product.product', 8, {})
        with self.assertRaises(ValidationError):
            self.env['kg.edge'].create(dict(
                self.provenance, company_id=self.company.id, from_node_id=self.product.id,
                to_node_id=alien.id, relation='RELATED_TO'))
        with self.assertRaises(ValidationError):
            self.projection.project_node(self.company, 'trade.hs', '85171300', {})
        with self.assertRaises(ValidationError):
            self.env['kg.node'].create({
                'company_id': self.company.id, 'source_model': 'trade.hs',
                'source_id': '85171300'})
        service = GraphService(self.env(context=dict(self.env.context, allowed_company_ids=[self.company.id])))
        with self.assertRaises(AccessError):
            service.neighbors(alien.urn)
        nodes = {'p': ('product.product', 7, {}), 's': ('res.partner', 9, {})}
        edges = [('s', 'SUPPLIES', 'p', self.provenance, {})]
        self.assertEqual(self.projection.rebuild(self.company, nodes, edges),
                         self.projection.rebuild(self.company, nodes, edges))
