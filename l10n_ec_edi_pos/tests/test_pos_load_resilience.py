# Part of Insilos Enterprise. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosLoadResilience(TransactionCase):

    def test_load_pos_data_domain_empty_payload(self):
        """Exercise Ecuadorian POS domain loader with completely empty data dictionary."""
        Move = self.env['account.move']
        domain = Move._load_pos_data_domain({})
        self.assertEqual(domain, [('id', '=', False)], "Must return empty domain without raising KeyError")

    def test_load_pos_data_domain_malformed_order_list(self):
        """Exercise with malformed pos.order records missing 'id'."""
        Move = self.env['account.move']
        domain = Move._load_pos_data_domain({'pos.order': [None, {}, {'foo': 'bar'}]})
        self.assertEqual(domain, [('id', '=', False)], "Must gracefully skip non-dict or id-less items")

    def test_selection_key_immutability(self):
        """Assert GSTR-2B selection key preserves exact backward database compatibility."""
        if 'l10n_in_gstr2b_reconciliation_status' in self.env['account.move']._fields:
            field = self.env['account.move']._fields['l10n_in_gstr2b_reconciliation_status']
            selection_keys = [k for k, _ in field.selection]
            self.assertIn(
                'gstr2_bills_not_in_odoo',
                selection_keys,
                "Technical selection key must remain 'gstr2_bills_not_in_odoo' to prevent database corruption"
            )
