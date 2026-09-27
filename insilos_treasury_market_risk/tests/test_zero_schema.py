# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""The addon must stay measurement-only: no table of its own."""

from odoo.tests.common import TransactionCase, tagged

MODULE = 'insilos_treasury_market_risk'


@tagged('post_install', '-at_install', 'treasury_market_risk', 'treasury_l1')
class TestTreasuryZeroSchema(TransactionCase):
    def test_module_declares_no_persistent_model(self):
        """A persistent model here would fork the truth away from accounting.

        Wizards are allowed — they hold a scenario for the length of one screen
        and are cleaned up — so only non-transient models are a failure.
        """
        module = self.env['ir.module.module'].search([('name', '=', MODULE)], limit=1)
        self.assertEqual(module.state, 'installed')
        owned = self.env['ir.model.data'].search([('module', '=', MODULE), ('model', '=', 'ir.model')])
        persistent = []
        for data in owned:
            # `_inherit` of an existing model also registers a data entry;
            # only a model this module alone defines is a new table.
            shared = self.env['ir.model.data'].search_count([
                ('model', '=', 'ir.model'), ('res_id', '=', data.res_id), ('module', '!=', MODULE)])
            if shared:
                continue
            model = self.env['ir.model'].browse(data.res_id)
            registry_model = self.env.get(model.model)
            if registry_model is not None and not registry_model._transient and registry_model._auto:
                persistent.append(model.model)
        self.assertEqual(persistent, [], 'Treasury must not own business tables: %s' % persistent)

    def test_only_declared_transient_wizard_tables_exist(self):
        self.env.cr.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND (tablename LIKE 'treasury_%%' OR tablename LIKE 'tmr_%%')"
        )
        self.assertEqual(set(self.env.cr.fetchall()), {
            ('treasury_fx_scenario_wizard',),
            ('treasury_generate_ic_pack_wizard',),
            ('treasury_liquidity_scenario_wizard',),
        })
        for model_name in ('treasury.fx.scenario.wizard', 'treasury.generate.ic.pack.wizard', 'treasury.liquidity.scenario.wizard'):
            self.assertTrue(self.env[model_name]._transient)
