# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Guards for the decision governance accelerator."""

import hashlib
import json
import os
from pathlib import Path
from datetime import timedelta
from unittest.mock import MagicMock, patch

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

MODULE = 'insilos_capital_markets_decision_governance'
ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MR_20260720 = json.loads((Path(__file__).parents[2] / 'insilos_market_data' / 'tests' / 'fixtures' / 'mr_20260720.json').read_text())


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalMarketsCatalog(TransactionCase):
    def _ref(self, xmlid):
        return self.env.ref(f'{MODULE}.{xmlid}')

    def test_catalog_entry_bundles_its_own_module(self):
        template = self._ref('industry_capital_markets_decision_governance')
        self.assertIn(MODULE, [m.strip() for m in (template.module_names or '').split(',')])
        self.assertEqual(template.category_id.name, self.env.ref('industry_templates.industry_cat_finance').name)
        self.assertTrue(template.slug)

    def test_workspace_is_a_template_not_a_live_project(self):
        self.assertTrue(self._ref('project_decision_governance').is_template)

    def test_stage_order_is_the_governance_order(self):
        expected = ['Intake', 'Evidence Collection', 'Independent Review', 'Rework', 'Approval', 'Closed']
        stages = self.env['project.task.type'].search([('project_ids', 'in', self._ref('project_decision_governance').ids)], order='sequence')
        self.assertEqual(stages.mapped('name'), expected)
        self.assertTrue(self._ref('stage_closed').fold)

    def test_source_tier_tags_cover_all_three_tiers(self):
        for xmlid in ('tag_source_official', 'tag_source_vendor', 'tag_source_unverified'):
            self.assertTrue(self._ref(xmlid).name.startswith('Source Tier: '))


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalMarketsAgentIsFailSafe(TransactionCase):
    def test_agent_has_no_write_tools_bound(self):
        agent = self.env.ref(f'{MODULE}.ai_agent_decision_research')
        self.assertFalse(agent.topic_ids.tool_ids)
        self.assertTrue(agent.restrict_to_sources)

    def test_system_prompt_states_the_hard_limits(self):
        prompt = self.env.ref(f'{MODULE}.ai_agent_decision_research').system_prompt.lower()
        for phrase in ('read-only', 'never approve', 'unverified'):
            self.assertIn(phrase, prompt)


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalMarketsSegregationOfDuties(TransactionCase):
    def test_approver_does_not_imply_requester(self):
        approver = self.env.ref(f'{MODULE}.group_decision_approver')
        requester = self.env.ref(f'{MODULE}.group_decision_requester')
        reviewer = self.env.ref(f'{MODULE}.group_decision_reviewer')
        self.assertNotIn(requester, approver.all_implied_ids)
        self.assertNotIn(reviewer, approver.all_implied_ids)
        self.assertNotIn(approver, requester.all_implied_ids)

    def test_governance_admin_holds_no_case_role(self):
        admin = self.env.ref(f'{MODULE}.group_governance_admin')
        for xmlid in ('group_decision_requester', 'group_decision_reviewer', 'group_decision_approver'):
            self.assertNotIn(self.env.ref(f'{MODULE}.{xmlid}'), admin.all_implied_ids)


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalMarketsMakerChecker(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.requester = cls.env['res.users'].create({'name': 'Case Requester', 'login': 'cmdg_requester', 'group_ids': [(4, cls.env.ref(f'{MODULE}.group_decision_requester').id)]})
        cls.reviewer = cls.env['res.users'].create({'name': 'Case Reviewer', 'login': 'cmdg_reviewer', 'group_ids': [(4, cls.env.ref(f'{MODULE}.group_decision_reviewer').id)]})
        cls.approver = cls.env['res.users'].create({'name': 'Case Approver', 'login': 'cmdg_approver', 'group_ids': [(4, cls.env.ref(f'{MODULE}.group_decision_approver').id)]})
        cls.project = cls.env['project.project'].create({'name': 'Maker-checker test desk', 'type_ids': [(6, 0, [cls.env.ref(f'{MODULE}.stage_intake').id, cls.env.ref(f'{MODULE}.stage_review').id, cls.env.ref(f'{MODULE}.stage_approval').id, cls.env.ref(f'{MODULE}.stage_closed').id])]})

    RATIONALE = '<p>Thesis, counter-thesis and sizing are recorded here so the decision can be re-read later.</p>'

    def _case_raised_by(self, user):
        case = self.env['project.task'].with_user(user).create({'name': 'Decision case under test', 'project_id': self.project.id, 'stage_id': self.env.ref(f'{MODULE}.stage_intake').id, 'user_ids': [(4, self.reviewer.id)], 'description': self.RATIONALE})
        self.env['ir.attachment'].create({'name': 'evidence.txt', 'raw': b'evidence', 'res_model': 'project.task', 'res_id': case.id})
        return case

    def test_requester_cannot_approve_own_case(self):
        with self.assertRaises(UserError):
            self._case_raised_by(self.requester).with_user(self.requester).stage_id = self.env.ref(f'{MODULE}.stage_approval')

    def test_requester_cannot_close_own_case_either(self):
        with self.assertRaises(UserError):
            self._case_raised_by(self.requester).with_user(self.requester).stage_id = self.env.ref(f'{MODULE}.stage_closed')

    def test_someone_else_may_approve(self):
        case = self._case_raised_by(self.requester)
        case.with_user(self.approver).stage_id = self.env.ref(f'{MODULE}.stage_approval')
        self.assertEqual(case.stage_id, self.env.ref(f'{MODULE}.stage_approval'))

    def test_approval_requires_evidence(self):
        case = self._case_raised_by(self.requester)
        self.env['ir.attachment'].search([('res_model', '=', 'project.task'), ('res_id', '=', case.id)]).unlink()
        with self.assertRaises(UserError):
            case.with_user(self.approver).stage_id = self.env.ref(f'{MODULE}.stage_approval')

    def test_approval_requires_reviewer_activity_complete(self):
        case = self._case_raised_by(self.requester)
        case.activity_schedule('mail.mail_activity_data_todo', user_id=self.reviewer.id, summary='Independent review')
        with self.assertRaises(UserError):
            case.with_user(self.approver).stage_id = self.env.ref(f'{MODULE}.stage_approval')
        case.activity_ids.filtered(lambda activity: activity.user_id == self.reviewer).action_feedback()
        case.with_user(self.approver).stage_id = self.env.ref(f'{MODULE}.stage_approval')
        self.assertEqual(case.stage_id, self.env.ref(f'{MODULE}.stage_approval'))

    def test_approver_cannot_be_assigned_reviewer(self):
        case = self._case_raised_by(self.requester)
        case.user_ids = [(6, 0, [self.approver.id])]
        with self.assertRaises(UserError):
            case.with_user(self.approver).stage_id = self.env.ref(f'{MODULE}.stage_approval')

    def test_requester_may_still_move_case_forward_before_the_gate(self):
        case = self._case_raised_by(self.requester)
        case.with_user(self.requester).stage_id = self.env.ref(f'{MODULE}.stage_review')
        self.assertEqual(case.stage_id, self.env.ref(f'{MODULE}.stage_review'))

    def test_unrelated_project_is_unchanged(self):
        project = self.env['project.project'].create({'name': 'Unrelated', 'type_ids': [(6, 0, [self.env.ref(f'{MODULE}.stage_approval').id])]})
        task = self.env['project.task'].create({'name': 'Unrelated task', 'project_id': project.id})
        task.with_user(self.requester).stage_id = self.env.ref(f'{MODULE}.stage_approval')


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalPortfolio(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portfolio = cls.env['capital.portfolio'].create({'name': 'Core Equity Book'})
        cls.position = cls.env['capital.position'].create({'portfolio_id': cls.portfolio.id, 'symbol': 'vnm', 'quantity': 100, 'average_cost': 60000, 'last_price': 66000})

    def test_mr_20260720_positions_value_from_golden_closes(self):
        portfolio = self.env['capital.portfolio'].create({'name': 'VN Industrial Holdings'})
        positions = self.env['capital.position'].create([
            {'portfolio_id': portfolio.id, 'symbol': symbol, 'quantity': quantity,
             'average_cost': cost, 'last_price': MR_20260720['instruments'][symbol]['bars'][-1]['close']}
            for symbol, quantity, cost in [('FPT', 1_500_000, 59_000), ('HPG', 4_000_000, 25_000), ('VIC', 300_000, 210_000)]
        ])
        self.assertEqual(positions.mapped('market_value'), [100_650_000_000, 82_400_000_000, 66_000_000_000])
        self.assertEqual(portfolio.market_value, 249_050_000_000)
        self.assertEqual(portfolio.unrealised_pnl, -2_450_000_000)

    def test_symbol_is_normalised_on_the_way_in(self):
        self.assertEqual(self.position.symbol, 'VNM')

    def test_valuation_arithmetic(self):
        self.assertEqual(self.position.cost_value, 6_000_000)
        self.assertEqual(self.position.market_value, 6_600_000)
        self.assertEqual(self.position.unrealised_pnl, 600_000)
        self.assertEqual(self.portfolio.unrealised_pnl, 600_000)

    def test_implausible_ticker_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'symbol': 'NOT A TICKER', 'quantity': 1})

    def test_same_symbol_cannot_be_held_twice_in_one_portfolio(self):
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'symbol': 'VNM', 'quantity': 5})


@tagged('post_install', '-at_install', 'capital_markets')
class TestMarketDataBoundary(TransactionCase):
    def test_disabled_kill_switch_reaches_nothing(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('capital_markets.market_data_enabled', 'false')
        params.set_param('capital_markets.sidecar_base_url', 'http://127.0.0.1:9')
        params.set_param('capital_markets.sidecar_token', 'x' * 32)
        with patch('requests.post') as post, self.assertRaises(UserError):
            self.env['capital.market.data'].call_tool('dnse_tickers', {'symbols': 'VNM'})
        post.assert_not_called()

    def test_sidecar_response_is_streamed_and_capped_before_parse(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('capital_markets.market_data_enabled', 'true')
        params.set_param('capital_markets.sidecar_base_url', 'http://127.0.0.1:18111')
        response = MagicMock(status_code=200)
        response.iter_content.return_value = [b'x' * 1_000_001, b'x' * 1_000_000]
        with patch.dict(os.environ, {'CAPITAL_MARKETS_SIDECAR_TOKEN': 'runtime-token'}), patch('requests.post', return_value=response) as post, self.assertRaises(UserError):
            self.env['capital.market.data'].call_tool('dnse_tickers', {'symbols': 'VNM'})
        self.assertTrue(post.call_args.kwargs['stream'])
        response.close.assert_called_once()

    def test_health_status_requires_governance_admin(self):
        user = self.env['res.users'].create({'name': 'Health Reader', 'login': 'cmdg_health_reader'})
        with self.assertRaises(AccessError):
            self.env['capital.market.data'].with_user(user).action_health_status()

    def test_governance_admin_can_view_health_status(self):
        admin = self.env['res.users'].create({
            'name': 'Health Admin',
            'login': 'cmdg_health_admin',
            'group_ids': [(4, self.env.ref(f'{MODULE}.group_governance_admin').id)],
        })
        status = self.env['capital.market.data'].with_user(admin).action_health_status()
        self.assertEqual(status['tag'], 'display_notification')
        self.assertIn('Market Data Health', status['params']['title'])

    def test_health_status_redacts_secrets_and_does_not_mutate_config(self):
        params = self.env['ir.config_parameter'].sudo()
        token = 'secret-token-must-not-appear'
        params.set_param('capital_markets.market_data_enabled', 'true')
        params.set_param('capital_markets.sidecar_base_url', 'http://127.0.0.1:9')
        # Bearer material is runtime-only. It must never enter config_parameter,
        # backups, or this model's normal configuration surface.
        with patch.dict(os.environ, {'CAPITAL_MARKETS_SIDECAR_TOKEN': token}), \
             patch('requests.post') as post, \
             patch('socket.create_connection', return_value=MagicMock()):
            status = self.env['capital.market.data'].action_health_status()
        self.assertNotIn(token, str(status))
        self.assertIn('Configured: Yes', status['params']['message'])
        self.assertFalse(params.get_param('capital_markets.sidecar_token'))
        post.assert_not_called()

    def test_health_status_reports_missing_runtime_secret(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('capital_markets.market_data_enabled', 'true')
        params.set_param('capital_markets.sidecar_base_url', 'http://127.0.0.1:18111')
        with patch.dict(os.environ, {}, clear=True):
            status = self.env['capital.market.data'].action_health_status()
        self.assertIn('Configured: No', status['params']['message'])
        self.assertIn('Runtime secret: Missing', status['params']['message'])
        self.assertIn('Sidecar reachable: No', status['params']['message'])

    def test_sidecar_url_must_be_loopback(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('capital_markets.market_data_enabled', 'true')
        params.set_param('capital_markets.sidecar_base_url', 'https://evil.example')
        params.set_param('capital_markets.sidecar_token', 'x' * 32)
        with self.assertRaises(UserError):
            self.env['capital.market.data'].call_tool('dnse_tickers', {'symbols': 'VNM'})

    def test_no_broker_credential_is_stored_by_this_module(self):
        field = self.env['capital.portfolio']._fields['broker_account_ref']
        self.assertEqual(field.type, 'char')
        self.assertNotIn('secret', self.env['capital.portfolio']._fields)
        self.assertNotIn('password', self.env['capital.portfolio']._fields)

    def test_a_mark_without_a_price_leaves_the_old_mark_alone(self):
        portfolio = self.env['capital.portfolio'].create({'name': 'Marking test'})
        position = self.env['capital.position'].create({'portfolio_id': portfolio.id, 'symbol': 'VNM', 'quantity': 10, 'average_cost': 1000, 'last_price': 1200})
        empty_envelope = {'source': 'test', 'requestFingerprint': 'deadbeef', 'asOf': None, 'data': []}
        with patch.object(type(self.env['capital.market.data']), 'call_tool', return_value=empty_envelope):
            portfolio.action_refresh_marks()
        self.assertEqual(position.last_price, 1200)

    def test_malformed_or_oversized_evidence_is_rejected(self):
        portfolio = self.env['capital.portfolio'].create({'name': 'Evidence guard test'})
        position = self.env['capital.position'].create({'portfolio_id': portfolio.id, 'symbol': 'EVD', 'quantity': 1})
        with self.assertRaises(UserError):
            portfolio.capture_market_evidence(position, {'data': []}, fields.Datetime.now())
        complete = {
            'source': 'test', 'provider': 'test', 'endpointClass': 'public-read', 'instrument': 'EVD',
            'asOf': '2026-08-07', 'retrievedAt': '2026-08-07 10:00:00', 'requestFingerprint': 'fp',
            'cacheStatus': 'miss', 'data': [], 'warnings': [], 'licenseClassification': 'public-source',
        }
        complete['data'] = ['x' * 2_000_000]
        with self.assertRaises(UserError):
            portfolio.capture_market_evidence(position, complete, fields.Datetime.now())

    def test_a_refreshed_mark_carries_immutable_evidence(self):
        portfolio = self.env['capital.portfolio'].create({'name': 'Provenance test'})
        position = self.env['capital.position'].create({'portfolio_id': portfolio.id, 'symbol': 'VNM', 'quantity': 10, 'average_cost': 1000})
        envelope = {
            'source': 'DNSE market-api tickers', 'provider': 'dnse', 'endpointClass': 'public-read',
            'instrument': 'VNM', 'asOf': '2026-08-05 09:00:00', 'retrievedAt': '2026-08-05 09:05:00',
            'requestFingerprint': 'abc123', 'cacheStatus': 'miss', 'warnings': [],
            'licenseClassification': 'public-source', 'data': [{'symbol': 'VNM', 'matchPrice': 65500}],
        }
        with patch.object(type(self.env['capital.market.data']), 'call_tool', return_value=envelope):
            portfolio.action_refresh_marks()
        self.assertEqual(position.last_price, 65500)
        self.assertTrue(position.price_as_of)
        self.assertTrue(position.evidence_hash)
        self.assertEqual(len(position.evidence_hash), 64)
        expected = hashlib.sha256(json.dumps(envelope, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(position.evidence_hash, expected)
        self.assertEqual(position.evidence_attachment_id.raw, json.dumps(envelope, sort_keys=True, separators=(',', ':')).encode())
        self.assertEqual(position.evidence_document_id.attachment_id, position.evidence_attachment_id)
        self.assertEqual(position.evidence_count, 1)
        self.assertIn('endpointClass', position.message_ids[:1].body)
        self.assertEqual(position.action_open_evidence()['context']['create'], False)
        with self.assertRaises(UserError):
            position.evidence_attachment_id.write({'name': 'tampered.json'})
        with self.assertRaises(UserError):
            position.unlink()

    def test_hbc_stale_price_suppresses_alert(self):
        portfolio = self.env['capital.portfolio'].create({'name': 'HBC stale book', 'freshness_hours': 1})
        position = self.env['capital.position'].create({'portfolio_id': portfolio.id, 'symbol': 'HBC', 'quantity': 10, 'last_price': 12000})
        position.with_context(capital_market_refresh=True).write({'price_as_of': fields.Datetime.now() - timedelta(hours=2)})
        rule = self.env['capital.alert.rule'].create({'name': 'HBC stale price', 'portfolio_id': portfolio.id, 'symbol': 'HBC', 'kind': 'price_below', 'threshold': 13000})
        before = self.env['mail.activity'].search_count([('res_model', '=', 'capital.portfolio'), ('res_id', '=', portfolio.id)])
        self.env['capital.alert.rule']._cron_scan_alerts()
        self.assertFalse(rule.triggered)
        self.assertEqual(position.mark_status, 'stale')
        self.assertEqual(self.env['mail.activity'].search_count([('res_model', '=', 'capital.portfolio'), ('res_id', '=', portfolio.id)]), before + 1)

    def test_mark_status_distinguishes_missing_fresh_and_provider_error(self):
        portfolio = self.env['capital.portfolio'].create({'name': 'Mark health book', 'freshness_hours': 24})
        position = self.env['capital.position'].create({'portfolio_id': portfolio.id, 'symbol': 'MSH', 'quantity': 1, 'last_price': 100})
        self.assertEqual(position.mark_status, 'missing')
        now = fields.Datetime.now()
        position.with_context(capital_market_refresh=True).write({'price_as_of': now, 'price_refreshed_at': now})
        self.assertEqual(position.mark_status, 'fresh')
        position.with_context(capital_market_refresh=True).write({'price_error_at': now + timedelta(seconds=1)})
        self.assertEqual(position.mark_status, 'error')


@tagged('post_install', '-at_install', 'capital_markets')
class TestCapitalAlerts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portfolio = cls.env['capital.portfolio'].create({'name': 'Alerting book'})
        cls.env['capital.position'].create({'portfolio_id': cls.portfolio.id, 'symbol': 'VNM', 'quantity': 100, 'average_cost': 60000, 'last_price': 50000}).with_context(capital_market_refresh=True).write({'price_as_of': fields.Datetime.now()})

    def _rule(self, **overrides):
        values = {'name': 'VNM below 55k', 'portfolio_id': self.portfolio.id, 'symbol': 'VNM', 'kind': 'price_below', 'threshold': 55000}
        values.update(overrides)
        return self.env['capital.alert.rule'].create(values)

    def test_breach_raises_an_activity_not_just_a_flag(self):
        rule = self._rule()
        before = self.env['mail.activity'].search_count([])
        self.env['capital.alert.rule']._cron_scan_alerts()
        self.assertTrue(rule.triggered)
        self.assertEqual(rule.last_triggered_value, 50000)
        self.assertGreater(self.env['mail.activity'].search_count([]), before)

    def test_a_breach_fires_once_not_every_tick(self):
        self._rule()
        self.env['capital.alert.rule']._cron_scan_alerts()
        after_first = self.env['mail.activity'].search_count([])
        self.env['capital.alert.rule']._cron_scan_alerts()
        self.assertEqual(self.env['mail.activity'].search_count([]), after_first)

    def test_ree_and_cii_alerts_rearm_after_the_condition_clears(self):
        ree = self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'symbol': 'REE', 'quantity': 10, 'last_price': 72000})
        cii = self.env['capital.position'].create({'portfolio_id': self.portfolio.id, 'symbol': 'CII', 'quantity': 10, 'last_price': 17500})
        (ree | cii).with_context(capital_market_refresh=True).write({'price_as_of': fields.Datetime.now()})
        ree_rule = self._rule(name='REE above 70k', symbol='REE', kind='price_above', threshold=70000)
        cii_rule = self._rule(name='CII below 18k', symbol='CII', kind='price_below', threshold=18000)
        self.env['capital.alert.rule']._cron_scan_alerts()
        self.assertTrue(ree_rule.triggered)
        self.assertTrue(cii_rule.triggered)
        ree.with_context(capital_market_refresh=True).write({'last_price': 68000})
        cii.with_context(capital_market_refresh=True).write({'last_price': 18500})
        self.env['capital.alert.rule']._cron_scan_alerts()
        self.assertFalse(ree_rule.triggered)
        self.assertFalse(cii_rule.triggered)

    def test_cron_isolates_a_failed_portfolio(self):
        failed = self.env['capital.portfolio'].create({'name': 'Failed scan book'})
        healthy = self.env['capital.portfolio'].create({'name': 'Healthy scan book'})
        self.env['capital.position'].create({'portfolio_id': healthy.id, 'symbol': 'SAFE', 'quantity': 1, 'last_price': 10}).with_context(capital_market_refresh=True).write({'price_as_of': fields.Datetime.now()})
        rule = self.env['capital.alert.rule'].create({'name': 'Healthy breach', 'portfolio_id': healthy.id, 'symbol': 'SAFE', 'kind': 'price_below', 'threshold': 20})
        original = type(healthy)._scan_alert_rules

        def scan(portfolio):
            if portfolio == failed:
                raise RuntimeError('simulated portfolio failure')
            return original(portfolio)

        with patch.object(type(healthy), '_scan_alert_rules', autospec=True, side_effect=scan):
            self.env['capital.alert.rule']._cron_scan_alerts()
        self.assertTrue(rule.triggered)

    def test_no_breach_no_alert(self):
        rule = self._rule(kind='price_above', threshold=99000)
        self.env['capital.alert.rule']._cron_scan_alerts()
        self.assertFalse(rule.triggered)

    def test_price_rule_requires_a_symbol(self):
        with self.assertRaises(ValidationError):
            self._rule(symbol=False)


@tagged('post_install', '-at_install', 'capital_markets', 'security_negative')
class TestPortfolioAccess(TransactionCase):
    def test_a_reviewer_cannot_edit_the_book(self):
        reviewer = self.env['res.users'].create({'name': 'Read-only reviewer', 'login': 'cmdg_ro_reviewer', 'group_ids': [(4, self.env.ref(f'{MODULE}.group_decision_reviewer').id)]})
        portfolio = self.env['capital.portfolio'].create({'name': 'Not yours to edit'})
        portfolio.invalidate_recordset()
        with self.assertRaises(AccessError):
            portfolio.with_user(reviewer).write({'name': 'Renamed'})
