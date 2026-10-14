# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tools import SQL
from odoo.exceptions import ValidationError


class TestCapTableSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({'name': 'Alpha Legal Corp'})
        cls.company_b = cls.env['res.company'].create({'name': 'Beta Holdings LLC'})

        cls.partner_issuer_a = cls.env['res.partner'].create({
            'name': 'Alpha Legal Corp Partner',
            'is_company': True,
            'company_id': cls.company_a.id,
        })
        cls.partner_issuer_b = cls.env['res.partner'].create({
            'name': 'Beta Holdings LLC Partner',
            'is_company': True,
            'company_id': cls.company_b.id,
        })

        cls.sec_class_a = cls.env['equity.security.class'].create({
            'name': 'Common Alpha',
        })
        cls.sec_class_b = cls.env['equity.security.class'].create({
            'name': 'Common Beta',
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'Shared Director',
            'company_id': False,
        })

        # Transaction for Company A
        cls.tx_a = cls.env['equity.transaction'].create({
            'partner_id': cls.partner_issuer_a.id,
            'subscriber_id': cls.partner.id,
            'security_class_id': cls.sec_class_a.id,
            'securities': 100000.0,
            'transaction_type': 'issuance',
            'date': '2026-01-01',
        })

        # Transaction for Company B
        cls.tx_b = cls.env['equity.transaction'].create({
            'partner_id': cls.partner_issuer_b.id,
            'subscriber_id': cls.partner.id,
            'security_class_id': cls.sec_class_b.id,
            'securities': 500000.0,
            'transaction_type': 'issuance',
            'date': '2026-01-01',
        })

    def test_multi_company_bleed_prevention(self):
        """Ensure Company B transactions are never visible in Company A cap table even if in env.companies."""
        cap_table_model = self.env['equity.cap.table'].with_company(self.company_a).with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id]
        )
        sql_query = cap_table_model._get_table_sql()

        self.env.cr.execute(SQL("SELECT security_class_id, SUM(securities) FROM (%s) AS q GROUP BY security_class_id", sql_query))
        results = dict(self.env.cr.fetchall())

        self.assertIn(self.sec_class_a.id, results)
        self.assertEqual(results[self.sec_class_a.id], 100000.0)
        self.assertNotIn(self.sec_class_b.id, results, "BOLA Leak: Company B shares contaminated Company A cap table!")

    def test_rpc_context_injection_hardening(self):
        """Ensure non-integer current_transaction_id in context raises clean ValidationError."""
        cap_table_model = self.env['equity.cap.table'].with_company(self.company_a).with_context(
            current_transaction_id="1; DROP TABLE res_partner;--"
        )
        with self.assertRaises(ValidationError):
            cap_table_model._get_table_sql()

    def test_unallocated_treasury_shares_retention(self):
        """Invariant: Transactions with partner_id=False (treasury/reserve) must not be dropped."""
        self.env['equity.transaction'].create({
            'company_id': self.company_a.id,
            'partner_id': False,
            'security_class_id': self.sec_class_a.id,
            'securities': 50000.0,
            'transaction_type': 'issuance',
            'date': '2026-01-01',
        })
        cap_table_model = self.env['equity.cap.table'].with_company(self.company_a)
        sql_query = cap_table_model._get_table_sql()
        self.env.cr.execute(SQL("SELECT security_class_id, SUM(securities) FROM (%s) AS q WHERE security_class_id = %s GROUP BY security_class_id", sql_query, self.sec_class_a.id))
        res = self.env.cr.fetchone()
        self.assertIsNotNone(res, "Treasury shares must be retained")
        self.assertEqual(res[1], 150000.0, "SILENT DATA LOSS: Unallocated shares with partner_id=False were dropped!")

