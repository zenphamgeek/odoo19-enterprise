from urllib.parse import unquote

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

from ..services.evidence_service import EvidenceService
from ..services.graph_projection import TRADE_MODELS
from ..services.graph_query import GraphQuery
from ..services.graph_service import GraphService


class KgApi(http.Controller):
    @http.route('/kg/api/health', type='jsonrpc', auth='user', methods=['POST'], readonly=True)
    def health(self):
        return {
            'status': 'ok',
            'company_id': request.env.company.id,
            'user_id': request.env.user.id,
            'trade_enabled': False,
        }

    @http.route('/kg/api/neighbors', type='jsonrpc', auth='user', methods=['POST'], readonly=True)
    def neighbors(self, urn, valid_at=None, known_at=None, depth=1, limit=50):
        valid_at = self._datetime(valid_at, 'valid_at')
        known_at = self._datetime(known_at, 'known_at')
        self._allow_urn(urn)
        edges = GraphService(request.env).neighbors(
            urn, valid_at=valid_at, known_at=known_at, depth=depth, limit=limit)
        evidence = EvidenceService(request.env)
        readable = []
        for item in edges:
            edge = request.env['kg.edge'].search([('edge_hash', '=', item['edge_hash'])], limit=1)
            envelope = evidence.envelope(edge) if edge else None
            if envelope:
                readable.append(dict(item, provenance=envelope))
        return readable

    @http.route('/kg/api/paths', type='jsonrpc', auth='user', methods=['POST'], readonly=True)
    def paths(self, from_urn, to_urn, valid_at=None, known_at=None, max_depth=3, limit=50):
        valid_at = self._datetime(valid_at, 'valid_at')
        known_at = self._datetime(known_at, 'known_at')
        self._allow_urn(from_urn)
        self._allow_urn(to_urn)
        return GraphQuery(request.env).paths(
            from_urn, to_urn, valid_at=valid_at, known_at=known_at,
            max_depth=max_depth, limit=limit)

    @http.route('/kg/api/subgraph', type='jsonrpc', auth='user', methods=['POST'], readonly=True)
    def get_subgraph(self, urn, depth=2, limit=50):
        """
        Returns structured Node-Link canvas graph payload (nodes and links)
        formatted for frontend D3 / Owl KnowledgeGraphViewer component.
        """
        self._allow_urn(urn)
        node = request.env['kg.node'].search([('urn', '=', urn)], limit=1)
        if not node:
            return {'nodes': [], 'links': []}

        edges_raw = GraphService(request.env).neighbors(urn, depth=depth, limit=limit)
        nodes_dict = {}
        links_list = []

        # Add origin node
        nodes_dict[node.urn] = {
            'id': node.urn,
            'label': node.urn.split(':')[-1],
            'model': node.source_model,
            'res_id': node.source_id,
            'type': 'root',
        }

        for item in edges_raw:
            f_urn, t_urn = item['from'], item['to']
            rel = item['relation']

            for u in (f_urn, t_urn):
                if u not in nodes_dict:
                    n = request.env['kg.node'].search([('urn', '=', u)], limit=1)
                    nodes_dict[u] = {
                        'id': u,
                        'label': u.split(':')[-1],
                        'model': n.source_model if n else '',
                        'res_id': n.source_id if n else '',
                        'type': 'connected',
                    }

            links_list.append({
                'source': f_urn,
                'target': t_urn,
                'relation': rel,
                'edge_hash': item['edge_hash'],
                'state': item.get('state', 'VERIFIED'),
            })

        return {
            'nodes': list(nodes_dict.values()),
            'links': links_list,
            'total_nodes': len(nodes_dict),
            'total_links': len(links_list),
        }

    @http.route('/kg/api/blast_radius', type='jsonrpc', auth='user', methods=['POST'], readonly=True)
    def calculate_blast_radius(self, urn, max_depth=3):
        """
        Calculates downstream blast radius of an entity: identifies all dependent
        purchase orders, shipments, compliance permits, ESG scores, and financial exposures.
        """
        self._allow_urn(urn)
        subgraph = self.get_subgraph(urn, depth=max_depth, limit=100)
        
        impacted_models = {}
        for n in subgraph['nodes']:
            m = n.get('model')
            if m:
                impacted_models[m] = impacted_models.get(m, 0) + 1

        radius_score = min(100.0, len(subgraph['nodes']) * 12.5 + len(subgraph['links']) * 8.0)
        risk_level = 'CRITICAL' if radius_score > 75 else 'HIGH' if radius_score > 50 else 'MEDIUM' if radius_score > 25 else 'LOW'

        return {
            'origin_urn': urn,
            'total_impacted_entities': len(subgraph['nodes']),
            'total_dependency_links': len(subgraph['links']),
            'blast_radius_score': radius_score,
            'risk_level': risk_level,
            'impacted_breakdown': impacted_models,
            'subgraph': subgraph,
        }

    @staticmethod
    def _datetime(value, name):
        if value is None:
            return None
        try:
            return fields.Datetime.to_datetime(value)
        except (TypeError, ValueError) as error:
            raise ValidationError('Invalid KG %s.' % name) from error

    @staticmethod
    def _allow_urn(urn):
        parts = urn.split(':', 5) if isinstance(urn, str) else []
        if len(parts) != 6 or parts[:3] != ['urn', 'insilos', 'kg'] or not parts[3].isdigit():
            raise ValidationError('Invalid KG URN.')
        if unquote(parts[4]) in TRADE_MODELS:
            raise ValidationError('Trade KG query is disabled pending legal gates.')
