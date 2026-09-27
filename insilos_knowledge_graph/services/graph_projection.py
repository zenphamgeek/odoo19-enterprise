from odoo import fields
from odoo.exceptions import ValidationError

from .graph_identity import canonical_hash, edge_hash, node_urn
from .ontology import require_relation

TRADE_MODELS = frozenset({'trade.hs', 'trade.fta', 'trade.tariff', 'trade.policy', 'legal.document'})


class GraphProjection:
    def __init__(self, env):
        self.env = env

    def project_node(self, company, source_model, source_id, source_value=None):
        if source_model in TRADE_MODELS:
            raise ValidationError('Trade KG projection is disabled pending legal gates.')
        urn = node_urn(company.id, source_model, source_id)
        values = {
            'company_id': company.id, 'source_model': source_model,
            'source_id': str(source_id), 'source_hash': canonical_hash(source_value),
        }
        node = self.env['kg.node'].search([('urn', '=', urn)], limit=1)
        if node:
            node.write({'source_hash': values['source_hash'], 'projected_at': fields.Datetime.now()})
            return node
        return self.env['kg.node'].create(values)

    def project_edge(self, company, source, relation, target, provenance, **temporal):
        require_relation(relation)
        if source.source_model in TRADE_MODELS or target.source_model in TRADE_MODELS:
            raise ValidationError('Trade KG projection is disabled pending legal gates.')
        valid_from, valid_to = temporal.get('valid_from'), temporal.get('valid_to')
        key = edge_hash(company.id, source.urn, relation, target.urn, valid_from, valid_to)
        edge = self.env['kg.edge'].search([('edge_hash', '=', key)], limit=1)
        if edge:
            bound = {field: provenance.get(field) for field in (
                'source_type', 'source_reference', 'source_hash', 'evidence_reference',
                'confidence', 'verified', 'derivation', 'state',
            ) if field in provenance}
            if any(edge[field] != value for field, value in bound.items()):
                raise ValidationError('KG edge identity is already bound to different provenance.')
            return edge
        values = dict(temporal, company_id=company.id, from_node_id=source.id,
                      to_node_id=target.id, relation=relation, **provenance)
        return self.env['kg.edge'].create(values)

    def rebuild(self, company, nodes, edges):
        self.env['kg.edge'].search([('company_id', '=', company.id)]).unlink()
        self.env['kg.node'].search([('company_id', '=', company.id)]).unlink()
        projected = {key: self.project_node(company, *value) for key, value in nodes.items()}
        for source, relation, target, provenance, temporal in edges:
            self.project_edge(company, projected[source], relation, projected[target], provenance, **temporal)
        return canonical_hash(sorted(self.env['kg.edge'].search([
            ('company_id', '=', company.id)]).mapped('edge_hash')))
