# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, JsonRpcException, new_test_user, tagged


@tagged('post_install', '-at_install', 'treasury_market_risk', 'treasury_l2', 'treasury_l3')
class TestTreasuryApi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({'name': 'Treasury API Other Company'})
        cls.user = new_test_user(
            cls.env,
            login='treasury_api_user',
            password='treasury_api_user',
            groups='insilos_treasury_market_risk.group_treasury_analyst,account.group_account_readonly,insilos_capital_markets_decision_governance.group_decision_reviewer',
            company_id=cls.company.id,
            company_ids=[(6, 0, cls.company.ids)],
        )

    def setUp(self):
        super().setUp()
        self.authenticate(self.user.login, 'treasury_api_user')

    def _business_counts(self):
        return {
            model: self.env[model].sudo().search_count([])
            for model in ('account.move', 'mail.activity', 'ir.attachment', 'project.task')
        }

    def test_all_routes_are_versioned_read_only_and_replay_safe(self):
        before = self._business_counts()
        calls = (
            ('/treasury/fx/exposure', {}),
            ('/treasury/liquidity/forecast', {}),
            ('/treasury/limits', {}),
            ('/treasury/risk/stress', {
                'holdings': [{'symbol': 'BOND', 'asset_class': 'government_bond', 'market_value': 100.0}],
                'shocks_pct': {'BOND': -10.0},
                'haircuts': {'government_bond': 5.0},
            }),
        )
        for route, params in calls:
            first = self.make_jsonrpc_request(route, params)
            replay = self.make_jsonrpc_request(route, params)
            self.assertEqual(first, replay, route)
            self.assertEqual(first['calculation_version'], '1.0', route)
        self.assertEqual(self._business_counts(), before)

    def test_company_acl_denies_unknown_and_unallowed_company(self):
        current = self.make_jsonrpc_request('/treasury/fx/exposure', {})
        explicit = self.make_jsonrpc_request('/treasury/fx/exposure', {'company_id': self.company.id})
        self.assertEqual(current, explicit)
        for company_id in (self.other_company.id, 2_147_483_647):
            with self.assertRaises(JsonRpcException):
                self.make_jsonrpc_request('/treasury/fx/exposure', {'company_id': company_id})

    def test_malformed_stress_payload_rolls_back_without_business_writes(self):
        before = self._business_counts()
        for params in ({}, {'holdings': 'not-a-list'}, {'holdings': [{'market_value': 'invalid'}]}):
            with self.assertRaises(JsonRpcException):
                self.make_jsonrpc_request('/treasury/risk/stress', params)
        self.assertEqual(self._business_counts(), before)

    def test_replayed_scenarios_are_isolated_and_read_only(self):
        before = self._business_counts()
        params = {
            'holdings': [{'symbol': 'BOND', 'asset_class': 'government_bond', 'market_value': 100.0}],
            'shocks_pct': {'BOND': -10.0},
            'haircuts': {'government_bond': 5.0},
        }
        results = [self.make_jsonrpc_request('/treasury/risk/stress', params) for _index in range(2)]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]['portfolio']['total_loss'], 10.0)
        self.assertEqual(self._business_counts(), before)
