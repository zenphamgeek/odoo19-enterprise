from datetime import datetime, timedelta

from odoo.tests import HttpCase, tagged
from odoo.tests.common import JsonRpcException, new_test_user

from ..services.graph_projection import GraphProjection


@tagged('post_install', '-at_install')
class TestKgApi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env, login='kg-api-reader', password='kg-api-reader',
            groups='insilos_knowledge_graph.group_kg_reader')
        cls.records = cls.env['res.partner'].create([
            {'name': 'KG API source'}, {'name': 'KG API target'}, {'name': 'KG API evidence'},
        ])
        projection = GraphProjection(cls.env)
        cls.nodes = [
            projection.project_node(cls.env.company, 'res.partner', record.id, {'name': record.name})
            for record in cls.records[:2]
        ]
        cls.edge = projection.project_edge(
            cls.env.company, cls.nodes[0], 'RELATED_TO', cls.nodes[1], {
                'source_type': 'BUSINESS_RECORD',
                'source_reference': 'rs.partner:%s' % cls.records[2].id,
                'source_hash': 'a' * 64,
                'evidence_reference': 'rs.partner:%s' % cls.records[2].id,
                'verified': True,
                'state': 'VERIFIED',
                'derivation': 'DETERMINISTIC',
            })

    def setUp(self):
        super().setUp()
        self.authenticate(self.user.login, 'kg-api-reader')

    def test_authenticated_health_and_queries(self):
        health = self.make_jsonrpc_request('/kg/api/health')
        self.assertEqual(health, {
            'status': 'ok', 'company_id': self.env.company.id,
            'user_id': self.user.id, 'trade_enabled': False,
        })
        neighbors = self.make_jsonrpc_request('/kg/api/neighbors', {
            'urn': self.nodes[0].urn, 'depth': 1, 'limit': 1,
        })
        self.assertEqual([item['edge_hash'] for item in neighbors], [self.edge.edge_hash])
        self.assertEqual(neighbors[0]['provenance']['evidence_reference'], 'rs.partner:%s' % self.records[2].id)
        paths = self.make_jsonrpc_request('/kg/api/paths', {
            'from_urn': self.nodes[0].urn, 'to_urn': self.nodes[1].urn,
            'max_depth': 1, 'limit': 1,
        })
        self.assertEqual(paths[0][0]['edge_hash'], self.edge.edge_hash)

    def test_neighbors_uses_independent_bitemporal_times(self):
        now = datetime.now()
        edge = GraphProjection(self.env).project_edge(
            self.env.company, self.nodes[0], 'SUPPLIES', self.nodes[1], {
                'source_type': 'BUSINESS_RECORD',
                'source_reference': 'rs.partner:%s' % self.records[2].id,
                'source_hash': 'b' * 64,
                'evidence_reference': 'rs.partner:%s' % self.records[2].id,
                'verified': True,
                'state': 'VERIFIED',
                'derivation': 'DETERMINISTIC',
            }, valid_from=now - timedelta(days=2), valid_to=now + timedelta(days=1),
            known_from=now - timedelta(days=1))
        neighbors = self.make_jsonrpc_request('/kg/api/neighbors', {
            'urn': self.nodes[0].urn,
            'valid_at': (now - timedelta(days=1, hours=12)).strftime('%Y-%m-%d %H:%M:%S'),
            'known_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        })
        self.assertIn(edge.edge_hash, {item['edge_hash'] for item in neighbors})

    def test_rejects_anonymous_unbounded_invalid_and_trade_queries(self):
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request('/kg/api/neighbors', {
                'urn': self.nodes[0].urn, 'depth': 4,
            })
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request('/kg/api/paths', {
                'from_urn': self.nodes[0].urn, 'to_urn': self.nodes[1].urn,
                'limit': 101,
            })
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request('/kg/api/neighbors', {
                'urn': self.nodes[0].urn, 'valid_at': 'not-a-date',
            })
        trade_urn = 'urn:insilos:kg:%s:trade.hs:8517' % self.env.company.id
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request('/kg/api/neighbors', {'urn': trade_urn})
        self.authenticate(None, None)
        response = self.opener.post(self.base_url() + '/kg/api/health', json={
            'jsonrpc': '2.0', 'method': 'call', 'id': 0, 'params': {},
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['error']['data']['name'], 'odoo.http.SessionExpiredException')
