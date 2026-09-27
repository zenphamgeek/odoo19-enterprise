# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase, tagged


@tagged('at_install', 'insilos_chemical_trade_compliance')
class TestPermitQuotaMigration(TransactionCase):

    def test_migration_is_nullable_and_preserves_ambiguous_rows(self):
        path = Path(__file__).parents[1] / 'migrations/19.0.1.0.2/pre-migrate.py'
        spec = importlib.util.spec_from_file_location('chemical_permit_quota_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        cr = MagicMock()
        cr.fetchone.return_value = (1,)
        migration.migrate(cr, None)
        sql = '\n'.join(call.args[0] for call in cr.execute.call_args_list)
        self.assertIn('ADD COLUMN IF NOT EXISTS dossier_line_id integer', sql)
        self.assertIn('HAVING count(*) = 1', sql)
        self.assertNotIn('SET NOT NULL', sql)
        self.assertNotIn('CREATE UNIQUE INDEX', sql)
