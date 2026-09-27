from .graph_identity import canonical_hash
from .graph_projection import GraphProjection


MODEL_ALIASES = {
    'company': ('res.company',),
    'product': ('product.product',),
    'partner': ('res.partner',),
    'purchase': ('purchase.order',),
    'sales': ('sale.order',),
    'invoice': ('account.move',),
    'inventory': ('stock.quant',),
}


class EnterpriseProjection:
    def __init__(self, env):
        self.env = env
        self.graph = GraphProjection(env)
        self.models = {
            kind: next((name for name in aliases if name in env.registry), None)
            for kind, aliases in MODEL_ALIASES.items()
        }

    @property
    def disabled(self):
        return frozenset(kind for kind, model in self.models.items() if model is None)

    def source_hash(self, record):
        record.ensure_one()
        kind = next((kind for kind, model in self.models.items() if model == record._name), None)
        if kind is None:
            raise ValueError('Unsupported enterprise projection model: %s' % record._name)
        company = self._company(record)
        return canonical_hash([
            record._name, record.id,
            sorted((relation, target._name, target.id)
                   for relation, target in self._references(kind, record, company)),
        ])

    def project_record(self, record):
        record.ensure_one()
        kind = next((kind for kind, model in self.models.items() if model == record._name), None)
        if kind is None:
            raise ValueError('Unsupported enterprise projection model: %s' % record._name)
        record.check_access('read')
        company = self._company(record)
        self._check_company(company)
        node = self._node(company, record)
        for relation, target in self._references(kind, record, company):
            target.check_access('read')
            target_node = self._node(company, target)
            self.graph.project_edge(
                company, node, relation, target_node,
                self._provenance(record, relation, target),
            )
        return node

    def project_company(self, company):
        company.ensure_one()
        company.check_access('read')
        self._check_company(company)
        nodes = []
        for model_name in filter(None, self.models.values()):
            model = self.env[model_name]
            domain = self._company_domain(model, company)
            nodes.extend(self.project_record(record) for record in model.search(domain, order='id'))
        return nodes

    def rebuild(self, company):
        company.ensure_one()
        company.check_access('read')
        self._check_company(company)
        self.env['kg.edge'].search([('company_id', '=', company.id)]).unlink()
        self.env['kg.node'].search([('company_id', '=', company.id)]).unlink()
        self.project_company(company)
        return canonical_hash(sorted(self.env['kg.edge'].search([
            ('company_id', '=', company.id),
        ]).mapped('edge_hash')))

    def _node(self, company, record):
        return self.graph.project_node(company, record._name, record.id, {
            'model': record._name, 'id': record.id,
        })

    def _check_company(self, company):
        if company not in self.env.companies:
            from odoo.exceptions import AccessError
            raise AccessError('Enterprise projection company is not allowed.')

    def _company(self, record):
        if record._name == self.models['company']:
            return record
        if 'company_id' in record._fields and record.company_id:
            return record.company_id
        return self.env.company

    def _company_domain(self, model, company):
        if model._name == self.models['company']:
            return [('id', '=', company.id)]
        if 'company_id' in model._fields:
            return [('company_id', '=', company.id)]
        return []

    def _references(self, kind, record, company):
        references = []
        if kind != 'company' and self.models['company']:
            references.append(('BELONGS_TO', company))
        if kind == 'purchase':
            references.extend(self._many(record, 'partner_id', 'PURCHASED_FROM'))
            references.extend(self._line_products(record, 'order_line'))
        elif kind == 'sales':
            references.extend(self._many(record, 'partner_id', 'SOLD_TO'))
            references.extend(self._line_products(record, 'order_line'))
        elif kind == 'invoice':
            relation = 'ISSUED_TO' if record.move_type.startswith('out_') else 'ISSUED_BY'
            references.extend(self._many(record, 'partner_id', relation))
            references.extend(self._line_products(record, 'invoice_line_ids'))
        elif kind == 'inventory':
            references.extend(self._many(record, 'product_id', 'CONTAINS'))
            references.extend(self._many(record, 'owner_id', 'OWNED_BY'))
        return references

    @staticmethod
    def _many(record, field, relation):
        return [(relation, target) for target in record[field]] if field in record._fields else []

    def _line_products(self, record, field):
        if field not in record._fields:
            return []
        products = record[field].mapped('product_id').sorted('id')
        return [('CONTAINS', product) for product in products]

    @staticmethod
    def _provenance(source, relation, target):
        reference = '%s:%s' % (source._name, source.id)
        return {
            'source_type': 'BUSINESS_RECORD',
            'source_reference': reference,
            'source_hash': canonical_hash([reference, relation, target._name, target.id]),
            'evidence_reference': reference,
            'verified': True,
            'state': 'VERIFIED',
            'derivation': 'DETERMINISTIC',
        }
