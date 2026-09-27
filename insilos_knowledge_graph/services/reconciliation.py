from .enterprise_projection import EnterpriseProjection
from .logistics_projection import LOGISTICS_MODELS


class KgReconciliation:
    DEFAULT_LIMIT = 500

    def __init__(self, env, limit=None):
        self.env = env
        self.limit = limit or self.DEFAULT_LIMIT

    def reconcile_company(self, company):
        company.ensure_one()
        env = self.env(context=dict(self.env.context, allowed_company_ids=[company.id]))
        env['kg.node'].check_access('create')
        env.cr.execute("SELECT pg_try_advisory_xact_lock(hashtext(%s), %s)",
                       ('insilos_knowledge_graph.reconcile', company.id))
        if not env.cr.fetchone()[0]:
            return {'status': 'overlap', 'company_id': company.id, 'scanned': 0}
        projection = EnterpriseProjection(env)
        sources = []
        missing = sorted(projection.disabled)
        if 'logistics.idp.case' in env.registry.models:
            sources.append(env['logistics.idp.case'])
        sources.extend(env[name] for name in filter(None, projection.models.values()))
        records = []
        for source in sources:
            source.check_access('read')
            domain = projection._company_domain(source, company)
            found = source.search(domain, order='id', limit=self.limit + 1)
            if len(found) > self.limit or len(records) + len(found) > self.limit:
                return {
                    'status': 'bounded', 'company_id': company.id, 'scanned': 0,
                    'missing_optional_models': missing,
                }
            records.extend(found)
        current = {(record._name, str(record.id)) for record in records}
        projected = env['kg.node'].search([
            ('company_id', '=', company.id),
            ('source_model', 'in', list({model for model, _source_id in current} | set(LOGISTICS_MODELS)
                                       | set(filter(None, projection.models.values())))),
        ])
        for node in projected:
            if (node.source_model, node.source_id) not in current:
                env['kg.outbox'].enqueue_delete(
                    company, node.source_model, node.source_id,
                    'reconcile-delete:%s:%s' % (node.source_model, node.source_id),
                )
        for record in records:
            if record._name == 'logistics.idp.case':
                payload = {field: record[field] for field in (
                    'source_system', 'source_key', 'source_version', 'provenance')}
                token = 'reconcile:%s:%s' % (record._name, record.id)
            else:
                payload = {'reconciled': True}
                token = 'reconcile:%s:%s:%s' % (
                    record._name, record.id, projection.source_hash(record))
            env['kg.outbox'].enqueue(record, payload=payload, mutation_token=token)
        return {
            'status': 'reconciled', 'company_id': company.id, 'scanned': len(records),
            'missing_optional_models': missing,
        }

    def run(self):
        results = []
        for company in self.env.companies.sorted('id'):
            with self.env.cr.savepoint():
                results.append(self.reconcile_company(company))
        return results
