from odoo import fields
from odoo.exceptions import AccessError, ValidationError

MAX_DEPTH = 3
MAX_RESULTS = 100


class GraphService:
    def __init__(self, env):
        self.env = env

    def neighbors(self, urn, *, as_of=None, valid_at=None, known_at=None, depth=1, limit=50,
                  include_unverified=False, trust_state=None):
        if not 1 <= depth <= MAX_DEPTH or not 1 <= limit <= MAX_RESULTS:
            raise ValidationError('KG query exceeds depth/result bounds.')
        if include_unverified:
            if trust_state not in {'CANDIDATE', 'REJECTED', 'CONFLICT'}:
                raise ValidationError('Unverified KG query requires an explicit trust state.')
            if not self.env.user.has_group('insilos_knowledge_graph.group_kg_manager'):
                raise AccessError('Unverified KG query requires projection manager access.')
        elif trust_state:
            raise ValidationError('KG trust state requires include_unverified=True.')
        node = self.env['kg.node'].search([('urn', '=', urn)], limit=1)
        if not node:
            return []
        allowed_companies = self.env.companies.ids
        if node.company_id.id not in allowed_companies:
            raise AccessError('KG node company is not allowed.')
        valid_at = valid_at or as_of or fields.Datetime.now()
        known_at = known_at or as_of or fields.Datetime.now()
        trust_domain = [('state', '=', trust_state)] if include_unverified else [
            ('state', '=', 'VERIFIED'), ('verified', '=', True),
        ]
        seen, frontier, result = {node.id}, {node.id}, []
        for _level in range(depth):
            edges = self.env['kg.edge'].search(trust_domain + [
                ('company_id', 'in', allowed_companies),
                '|', ('from_node_id', 'in', list(frontier)), ('to_node_id', 'in', list(frontier)),
                '|', ('valid_from', '=', False), ('valid_from', '<=', valid_at),
                '|', ('valid_to', '=', False), ('valid_to', '>', valid_at),
                '|', ('known_from', '=', False), ('known_from', '<=', known_at),
                '|', ('known_to', '=', False), ('known_to', '>', known_at),
            ], limit=limit - len(result))
            frontier = set()
            for edge in edges:
                other = edge.to_node_id if edge.from_node_id.id in seen else edge.from_node_id
                if other.id not in seen:
                    other.check_access('read')
                    seen.add(other.id)
                    frontier.add(other.id)
                result.append({
                    'edge_hash': edge.edge_hash, 'from': edge.from_node_id.urn,
                    'relation': edge.relation, 'to': edge.to_node_id.urn,
                    'evidence_reference': edge.evidence_reference,
                    'valid_from': edge.valid_from, 'valid_to': edge.valid_to,
                    'state': edge.state,
                })
                if len(result) == limit:
                    return result
            if not frontier:
                break
        return result
