from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..services.graph_identity import edge_hash, node_urn
from ..services.graph_projection import TRADE_MODELS
from ..services.ontology import RELATIONS, VERSION


class KgNode(models.Model):
    _name = 'kg.node'
    _description = 'Knowledge Graph Node Projection'
    _order = 'urn'

    urn = fields.Char(string='Node URN Identifier', required=True, index=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Operating Company', required=True, index=True, ondelete='cascade')
    source_model = fields.Char(string='Source Model', required=True, index=True, readonly=True)
    source_id = fields.Char(string='Source Record ID', required=True, index=True, readonly=True)
    source_hash = fields.Char(string='Source Payload Hash', readonly=True)
    projected_at = fields.Datetime(string='Projection Timestamp', required=True, default=fields.Datetime.now, readonly=True)

    _urn_unique = models.Constraint('UNIQUE(urn)', 'KG node URN must be unique.')

    @api.model
    def _cron_reconcile(self):
        from ..services.reconciliation import KgReconciliation
        return KgReconciliation(self.env).run()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals['source_model'] in TRADE_MODELS:
                raise ValidationError('Trade KG projection is disabled pending legal gates.')
            vals['urn'] = node_urn(vals['company_id'], vals['source_model'], vals['source_id'])
        return super().create(vals_list)

    def write(self, vals):
        if {'urn', 'company_id', 'source_model', 'source_id'} & vals.keys():
            raise ValidationError('KG node identity is immutable; project a new node.')
        if any(node.source_model in TRADE_MODELS for node in self):
            raise ValidationError('Trade KG projection is disabled pending legal gates.')
        return super().write(vals)


class KgEdge(models.Model):
    _name = 'kg.edge'
    _description = 'Knowledge Graph Edge Projection'
    _order = 'edge_hash'

    edge_hash = fields.Char(string='Edge Deterministic Hash', required=True, index=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Operating Company', required=True, index=True, ondelete='cascade')
    from_node_id = fields.Many2one('kg.node', string='Source Entity Node', required=True, index=True, ondelete='cascade')
    to_node_id = fields.Many2one('kg.node', string='Target Entity Node', required=True, index=True, ondelete='cascade')
    relation = fields.Char(string='Semantic Predicate', required=True, index=True, readonly=True)
    ontology_version = fields.Char(string='Ontology Semantic Version', required=True, default=VERSION, readonly=True)
    source_type = fields.Char(string='Provenance Source Type', required=True, readonly=True)
    source_reference = fields.Char(string='Source Record Reference', required=True, readonly=True)
    source_hash = fields.Char(string='Source Payload Hash', required=True, readonly=True)
    evidence_reference = fields.Char(string='Audit Evidence Reference', readonly=True)
    confidence = fields.Float(string='Extraction Confidence Score', required=True, default=1.0, readonly=True)
    verified = fields.Boolean(string='Verified', default=False, readonly=True)
    derivation = fields.Selection([
        ('DETERMINISTIC', 'Deterministic Rule Engine'),
        ('AI_EXTRACTION', 'AI / Neural Extraction'),
    ], string='Relationship Derivation Method', required=True, default='DETERMINISTIC', readonly=True)
    state = fields.Selection([
        ('CANDIDATE', 'Candidate Proposal'), ('VERIFIED', 'Verified & Active'),
        ('REJECTED', 'Rejected'), ('CONFLICT', 'Identity Conflict'),
    ], string='Relationship Lifecycle State', required=True, default='CANDIDATE', index=True)
    valid_from = fields.Datetime(string='Valid From (Business Time)', index=True, readonly=True)
    valid_to = fields.Datetime(string='Valid Until (Business Time)', index=True, readonly=True)
    known_from = fields.Datetime(string='Recorded At (System Time)', required=True, default=fields.Datetime.now, index=True, readonly=True)
    known_to = fields.Datetime(string='Superseded At (System Time)', index=True, readonly=True)

    _edge_hash_unique = models.Constraint('UNIQUE(edge_hash)', 'KG edge hash must be unique.')

    @api.model_create_multi
    def create(self, vals_list):
        nodes = self.env['kg.node']
        for vals in vals_list:
            if vals['relation'] not in RELATIONS:
                raise ValidationError('Unknown KG relation: %s' % vals['relation'])
            source = nodes.browse(vals['from_node_id']).exists()
            target = nodes.browse(vals['to_node_id']).exists()
            if source.source_model in TRADE_MODELS or target.source_model in TRADE_MODELS:
                raise ValidationError('Trade KG projection is disabled pending legal gates.')
            if source.company_id.id != vals['company_id'] or target.company_id.id != vals['company_id']:
                raise ValidationError('KG edge nodes must belong to its company.')
            if vals.get('derivation', 'DETERMINISTIC') == 'AI_EXTRACTION':
                vals.update(state='CANDIDATE', verified=False)
            if bool(vals.get('verified')) != (vals.get('state', 'CANDIDATE') == 'VERIFIED'):
                raise ValidationError('KG VERIFIED state and verified flag must agree.')
            if vals.get('verified') and not vals.get('evidence_reference'):
                raise ValidationError('Verified KG edge requires evidence.')
            if vals.get('valid_from') and vals.get('valid_to') and vals['valid_from'] > vals['valid_to']:
                raise ValidationError('KG valid interval is inverted.')
            if vals.get('known_from') and vals.get('known_to') and vals['known_from'] > vals['known_to']:
                raise ValidationError('KG known interval is inverted.')
            vals['edge_hash'] = edge_hash(
                vals['company_id'], source.urn, vals['relation'], target.urn,
                vals.get('valid_from'), vals.get('valid_to'))
        return super().create(vals_list)

    def write(self, vals):
        if any(edge.from_node_id.source_model in TRADE_MODELS
               or edge.to_node_id.source_model in TRADE_MODELS for edge in self):
            raise ValidationError('Trade KG projection is disabled pending legal gates.')
        immutable = {
            'edge_hash', 'company_id', 'from_node_id', 'to_node_id', 'relation',
            'ontology_version', 'source_type', 'source_reference', 'source_hash',
            'derivation', 'valid_from', 'valid_to', 'known_from', 'known_to',
        }
        if immutable & vals.keys():
            raise ValidationError('KG edge identity, provenance, and validity are immutable; project a new edge.')
        if any(edge.derivation == 'AI_EXTRACTION' for edge in self):
            vals.update(state='CANDIDATE', verified=False)
        for edge in self:
            state = vals.get('state', edge.state)
            verified = vals.get('verified', edge.verified)
            evidence = vals.get('evidence_reference', edge.evidence_reference)
            if bool(verified) != (state == 'VERIFIED'):
                raise ValidationError('KG VERIFIED state and verified flag must agree.')
            if verified and not evidence:
                raise ValidationError('Verified KG edge requires evidence.')
        return super().write(vals)
