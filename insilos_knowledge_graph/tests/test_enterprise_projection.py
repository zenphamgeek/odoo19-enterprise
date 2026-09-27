from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

from ..services.enterprise_projection import EnterpriseProjection


@tagged('post_install', '-at_install')
class TestEnterpriseProjection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'KG-02 Partner'})
        cls.projection = EnterpriseProjection(cls.env)

    def test_registry_aliases_and_optional_models(self):
        self.assertEqual(self.projection.models['company'], 'res.company')
        self.assertEqual(self.projection.models['partner'], 'res.partner')
        expected_disabled = {
            kind for kind, aliases in self.projection.models.items() if aliases is None
        }
        self.assertEqual(self.projection.disabled, expected_disabled)

    def test_reference_only_idempotent_projection_and_rebuild(self):
        first = self.projection.project_record(self.partner)
        second = self.projection.project_record(self.partner)
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.source_hash, second.source_hash)
        self.assertEqual(
            self.env['kg.node'].search_count([
                ('company_id', '=', self.company.id),
                ('source_model', '=', 'res.partner'),
                ('source_id', '=', str(self.partner.id)),
            ]),
            1,
        )
        edge = self.env['kg.edge'].search([
            ('from_node_id', '=', first.id), ('relation', '=', 'BELONGS_TO'),
        ])
        self.assertEqual(len(edge), 1)
        self.assertEqual(edge.derivation, 'DETERMINISTIC')
        self.assertEqual(edge.source_reference, 'rs.partner:%s' % self.partner.id)
        self.assertTrue(self.projection.graph.env['res.partner'].browse(
            int(edge.source_reference.rpartition(':')[2])).exists())
        self.assertEqual(self.projection.rebuild(self.company), self.projection.rebuild(self.company))

    def test_source_read_and_company_access_enforced(self):
        other = self.env['res.company'].create({'name': 'KG-02 Other'})
        restricted_env = self.env(context=dict(self.env.context, allowed_company_ids=[self.company.id]))
        with self.assertRaises(AccessError):
            EnterpriseProjection(restricted_env).project_record(other.with_env(restricted_env))
        user = new_test_user(self.env, login='kg-02-no-partner-read', groups='base.group_user')
        self.env['ir.model.access'].create({
            'name': 'KG-02 deny partner read',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'group_id': user.group_ids[:1].id,
            'perm_read': False, 'perm_write': False, 'perm_create': False, 'perm_unlink': False,
        })
        denied = self.partner.with_user(user)
        if not denied.has_access('read'):
            with self.assertRaises(AccessError):
                EnterpriseProjection(denied.env).project_record(denied)
