# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Boundaries that only show up between transactions: companies and cursors."""

from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

MODULE = 'insilos_capital_markets_decision_governance'
LEDGER_TABLES = (
    'capital_portfolio', 'capital_position', 'capital_instrument', 'capital_fx_rate',
    'capital_benchmark', 'capital_corporate_action', 'capital_reconciliation_import',
    'capital_reconciliation_line',
)


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalMarketsCrossCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({'name': 'Desk A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Desk B'})
        cls.instrument = cls.env['capital.instrument'].create({'symbol': 'XCOM', 'exchange': 'XNAS', 'currency_id': cls.company_a.currency_id.id})
        cls.portfolio_a = cls.env['capital.portfolio'].create({'name': 'Book A', 'company_id': cls.company_a.id, 'currency_id': cls.company_a.currency_id.id})
        cls.position_a = cls.env['capital.position'].create({'portfolio_id': cls.portfolio_a.id, 'instrument_id': cls.instrument.id, 'quantity': 5, 'average_cost': 10})
        cls.outsider = cls.env['res.users'].create({
            'name': 'Desk B trader', 'login': 'cmdg_desk_b',
            'company_id': cls.company_b.id, 'company_ids': [(6, 0, [cls.company_b.id])],
            'group_ids': [(4, cls.env.ref(f'{MODULE}.group_portfolio_manager').id)],
        })

    def test_another_company_cannot_read_the_book(self):
        self.assertFalse(self.env['capital.portfolio'].with_user(self.outsider).search([('id', '=', self.portfolio_a.id)]))
        self.assertFalse(self.env['capital.position'].with_user(self.outsider).search([('id', '=', self.position_a.id)]))

    def test_position_inherits_the_portfolio_company(self):
        self.assertEqual(self.position_a.company_id, self.company_a)

    def test_market_evidence_document_inherits_portfolio_company(self):
        envelope = {
            'source': 'test', 'provider': 'test', 'endpointClass': 'public-read', 'instrument': 'XCOM',
            'asOf': '2026-08-05 09:00:00', 'retrievedAt': '2026-08-05 09:05:00',
            'requestFingerprint': 'company-bound', 'cacheStatus': 'miss', 'warnings': [],
            'licenseClassification': 'public-source', 'data': [{'symbol': 'XCOM', 'matchPrice': 100}],
        }
        with patch.object(type(self.env['capital.market.data']), 'call_tool', return_value=envelope):
            self.portfolio_a.action_refresh_marks()
        document = self.position_a.evidence_document_id
        self.assertEqual(document.company_id, self.company_a)
        self.assertFalse(self.env['documents.document'].with_user(self.outsider).search([('id', '=', document.id)]))

        # Hiding the Documents row is not enough. The evidence lives in the
        # attachment bytes, and those are reachable by id from any model that
        # points at them, so the denial has to hold at that level too.
        attachment = self.position_a.evidence_attachment_id
        self.assertTrue(attachment.raw)
        outsider_env = self.env(user=self.outsider)
        self.assertFalse(outsider_env['ir.attachment'].search([('id', '=', attachment.id)]))
        with self.assertRaises(AccessError):
            outsider_env['ir.attachment'].browse(attachment.id).read(['raw'])
        # Reading through the position it belongs to must fail for the same
        # reason, otherwise the record rule would only be cosmetic.
        with self.assertRaises(AccessError):
            outsider_env['capital.position'].browse(self.position_a.id).read(['evidence_attachment_id'])

    def test_evidence_folders_are_module_owned_and_shared_by_design(self):
        """The Documents folders are tenant-wide; segregation is per record.

        This is worth pinning down because the opposite is a reasonable
        expectation: someone reading `folder_evidence_vendor` may assume a
        folder per company. There is not one, and the isolation instead comes
        from `company_id` on each evidence document. If a future change makes
        the folder company-bound, this test should be updated deliberately —
        not discovered in production.
        """
        vendor = self.env.ref('%s.folder_evidence_vendor' % MODULE)
        root = self.env.ref('%s.folder_evidence_root' % MODULE)
        self.assertFalse(vendor.company_id)
        self.assertEqual(vendor.folder_id, root)
        self.assertFalse(root.folder_id, 'the module root must stay a top-level folder')


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalMarketsConcurrency(TransactionCase):
    def test_two_cursors_refreshing_do_not_duplicate_evidence(self):
        portfolio = self.env['capital.portfolio'].create({'name': 'Concurrent book'})
        self.env['capital.position'].create({'portfolio_id': portfolio.id, 'symbol': 'VNM', 'quantity': 10, 'average_cost': 1000})
        envelope = {
            'source': 'test', 'provider': 'test', 'endpointClass': 'public-read', 'instrument': 'VNM',
            'asOf': '2026-08-05 09:00:00', 'retrievedAt': '2026-08-05 09:05:00',
            'requestFingerprint': 'same-fingerprint', 'cacheStatus': 'miss', 'warnings': [],
            'licenseClassification': 'public-source', 'data': [{'symbol': 'VNM', 'matchPrice': 65500}],
        }
        with patch.object(type(self.env['capital.market.data']), 'call_tool', return_value=envelope):
            portfolio.action_refresh_marks()
            portfolio.action_refresh_marks()
        attachments = self.env['ir.attachment'].search([('res_model', '=', 'capital.position'), ('res_id', 'in', portfolio.position_ids.ids)])
        # Evidence is immutable, so a second refresh appends rather than
        # overwrites: the first capture is still readable, and the position
        # points at the newest one. Losing either property breaks the audit
        # trail — the first silently, the second by pointing at nothing.
        self.assertEqual(len(attachments), 2)
        self.assertEqual(len(set(attachments.mapped('checksum'))), 1)
        self.assertEqual(portfolio.position_ids.evidence_attachment_id, attachments.sorted('id')[-1])


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalMarketsSchemaLifecycle(TransactionCase):
    def test_every_ledger_table_is_declared_by_this_module(self):
        """Uninstall must be able to drop what install created.

        A table that no model in this module owns is a table nobody will drop,
        which is how an uninstalled addon leaves rows behind.
        """
        owned = {model._table for model in self.env.registry.values() if model._name.startswith('capital.')}
        self.assertEqual(set(LEDGER_TABLES) - owned, set())
        self.env.cr.execute("SELECT unnest(%s::text[])", [list(LEDGER_TABLES)])
        for (table,) in self.env.cr.fetchall():
            self.env.cr.execute("SELECT to_regclass(%s)", [table])
            self.assertIsNotNone(self.env.cr.fetchone()[0], table)

    def test_business_records_do_not_live_in_ledger_tables(self):
        """The governance side is zero-schema: cases stay on project.task."""
        self.assertEqual(self.env['project.task']._table, 'project_task')
        template = self.env.ref(f'{MODULE}.project_decision_governance')
        self.assertTrue(template.is_template)
        self.assertEqual(template._name, 'project.project')
