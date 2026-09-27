from odoo import fields
from odoo.exceptions import AccessError, ValidationError

from .evidence_service import EvidenceService

MAX_DEPTH = 3
MAX_PATHS = 100
MAX_EDGE_READS = 1000
MAX_FRONTIER = 100
MAX_QUERIES = 100


class GraphQuery:
    def __init__(self, env):
        self.env = env
        self.evidence = EvidenceService(env)

    def paths(self, from_urn, to_urn, *, valid_at=None, known_at=None, max_depth=3, limit=50):
        if not 1 <= max_depth <= MAX_DEPTH or not 1 <= limit <= MAX_PATHS:
            raise ValidationError('KG path query exceeds depth/result bounds.')
        try:
            endpoints = self.env['kg.node'].search([('urn', 'in', [from_urn, to_urn])])
        except AccessError:
            return []
        by_urn = {node.urn: node for node in endpoints if self.evidence.readable_node(node)}
        if from_urn not in by_urn or to_urn not in by_urn:
            return []
        source, target = by_urn[from_urn], by_urn[to_urn]
        valid_at = valid_at or fields.Datetime.now()
        known_at = known_at or fields.Datetime.now()
        domain = [
            ('company_id', 'in', self.env.companies.ids),
            ('state', '=', 'VERIFIED'), ('verified', '=', True),
            '|', ('valid_from', '=', False), ('valid_from', '<=', valid_at),
            '|', ('valid_to', '=', False), ('valid_to', '>', valid_at),
            '|', ('known_from', '=', False), ('known_from', '<=', known_at),
            '|', ('known_to', '=', False), ('known_to', '>', known_at),
        ]
        queue, paths = [(source, [], {source.id})], []
        edge_reads = queries = 0
        while queue and len(paths) < limit and queries < MAX_QUERIES and edge_reads < MAX_EDGE_READS:
            node, path, visited = queue.pop(0)
            if len(path) >= max_depth:
                continue
            query_limit = min(MAX_FRONTIER, MAX_EDGE_READS - edge_reads)
            edges = self.env['kg.edge'].search(domain + [
                '|', ('from_node_id', '=', node.id), ('to_node_id', '=', node.id),
            ], limit=query_limit)
            queries += 1
            edge_reads += len(edges)
            for edge in edges:
                envelope = self.evidence.envelope(edge)
                if not envelope:
                    continue
                other = edge.to_node_id if edge.from_node_id == node else edge.from_node_id
                if other.id in visited:
                    continue
                step = {
                    'edge_hash': edge.edge_hash,
                    'from': edge.from_node_id.urn,
                    'relation': edge.relation,
                    'to': edge.to_node_id.urn,
                    'valid_from': edge.valid_from,
                    'valid_to': edge.valid_to,
                    'known_from': edge.known_from,
                    'known_to': edge.known_to,
                    'provenance': envelope,
                }
                candidate = path + [step]
                if other == target:
                    paths.append(candidate)
                    if len(paths) == limit:
                        break
                elif len(queue) < MAX_FRONTIER:
                    queue.append((other, candidate, visited | {other.id}))
        return paths
