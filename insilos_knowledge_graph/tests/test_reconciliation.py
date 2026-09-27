from unittest.mock import patch, PropertyMock

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..services.enterprise_projection import EnterpriseProjection
from ..services.reconciliation import KgReconciliation


@tagged('post_install', '-at_install')
class TestKgReconciliation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'logistics.idp.case' not in cls.env.registry.models:
            cls.skipTest(cls, 'Logistics IDP is not installed; reconciler disabled.')
        cls.company = cls.env['res.company'].create({'name': 'KG reconciliation company'})
        cls.kg_env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        cls.case = cls.kg_env['logistics.idp.case'].create({
            'name': 'KG reconciliation', 'source_system': 'fixture',
            'source_key': 'kg-reconciliation', 'source_version': '1',
            'provenance': 'fixture:kg-reconciliation', 'effective_date': '2026-01-01',
            'company_id': cls.company.id,
        })
        cls.env.user.group_ids = [(4, cls.env.ref('insilos_knowledge_graph.group_kg_processor').id),
                                  (4, cls.env.ref('insilos_logistics_idp.group_logistics_admin').id)]

    def _nodes(self, company=None):
        return self.kg_env['kg.node'].search([
            ('company_id', '=', (company or self.company).id),
            ('source_model', '=', 'logistics.idp.case'),
        ])

    def test_repeated_scan_and_new_instance_converge(self):
        first = KgReconciliation(self.kg_env, limit=5000).run()
        count = self.kg_env['kg.outbox'].search_count([('company_id', '=', self.company.id)])
        second = KgReconciliation(self.kg_env, limit=5000).run()
        self.assertEqual(first, second)
        self.assertEqual(self.kg_env['kg.outbox'].search_count([
            ('company_id', '=', self.company.id)]), count)
        self.kg_env['kg.outbox']._cron_process(limit=500)
        self.assertEqual(len(self._nodes()), 1)

    def test_enqueue_rollback_and_retry(self):
        before = self.kg_env['kg.outbox'].search_count([])
        with self.assertRaises(RuntimeError):
            with self.kg_env.cr.savepoint():
                KgReconciliation(self.kg_env, limit=5000).run()
                raise RuntimeError('fixture failure')
        self.assertEqual(self.kg_env['kg.outbox'].search_count([]), before)
        KgReconciliation(self.kg_env, limit=5000).run()
        self.kg_env['kg.outbox']._cron_process(limit=500)
        self.assertEqual(len(self._nodes()), 1)

    def test_company_isolation(self):
        other = self.env['res.company'].create({'name': 'KG reconciliation other'})
        other_env = self.env(context=dict(self.env.context, allowed_company_ids=[other.id]))
        other_env['logistics.idp.case'].create({
            'name': 'Other KG reconciliation', 'source_system': 'fixture',
            'source_key': 'kg-reconciliation-other', 'source_version': '1',
            'provenance': 'fixture:kg-reconciliation-other', 'effective_date': '2026-01-01',
            'company_id': other.id,
        })
        KgReconciliation(other_env, limit=5000).run()
        other_env['kg.outbox']._cron_process(limit=500)
        self.assertEqual(other_env['kg.node'].search_count([
            ('company_id', '=', other.id), ('source_model', '=', 'logistics.idp.case'),
        ]), 1)
        self.assertEqual(len(self._nodes()), 0)

    def test_bound_refuses_partial_rebuild(self):
        result = KgReconciliation(self.kg_env, limit=1).run()[0]
        self.assertEqual(result['status'], 'bounded')
        self.assertEqual(self.kg_env['kg.outbox'].search_count([
            ('company_id', '=', self.company.id)]), 0)

    def test_optional_model_absent_is_explicit(self):
        projection = EnterpriseProjection(self.kg_env)
        with patch.object(EnterpriseProjection, 'disabled', new_callable=PropertyMock,
                          return_value=frozenset({'inventory'})):
            result = KgReconciliation(self.kg_env, limit=5000).run()[0]
        self.assertEqual(result['missing_optional_models'], ['inventory'])
        self.assertEqual(projection.models['company'], 'res.company')

    def test_stale_edge_repaired_after_source_change(self):
        partner = self.kg_env['res.partner'].create({'name': 'KG stale partner'})
        EnterpriseProjection(self.kg_env).project_record(partner)
        partner.unlink()
        KgReconciliation(self.kg_env, limit=5000).run()
        delete = self.kg_env['kg.outbox'].search([
            ('source_model', '=', 'res.partner'), ('source_id', '=', str(partner.id)),
            ('event_type', '=', 'DELETE'),
        ])
        self.assertEqual(len(delete), 1)
        delete._project()
        self.assertFalse(self.kg_env['kg.node'].search([
            ('source_model', '=', 'res.partner'), ('source_id', '=', str(partner.id))]))
