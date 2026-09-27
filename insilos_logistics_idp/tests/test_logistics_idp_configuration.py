import hashlib
import json
import re
from datetime import timezone
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4

from psycopg2.errors import UniqueViolation

from odoo import fields, tools
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, new_test_user as _new_test_user, tagged

from .common import new_logistics_test_user, unique_fixture
from ..models.logistics_idp import _INTERNAL_POLICY_LOADER_TOKEN
from ..services.document_processor import batch_structure, deterministic_classify, extraction_template_contract
from ..services.legal_candidate_adapter import MAX_PAGES, MAX_RESULTS, fetch_candidates
from ..services.reconciliation import (build_regulatory_change_notification, compare_line, customs_checks,
                                       evaluate_origin_evidence, evaluate_tariff_remedy_security)


def new_test_user(env, **values):
    return new_logistics_test_user(_new_test_user, env, **values)


@tagged('post_install', '-at_install', 'logistics_idp')
class TestLogisticsIdpConfiguration(TransactionCase):
    def setUp(self):
        super().setUp()
        approved = {
            tier: {url: {'approved': True, 'source_tier': tier} for url in (
                'https://example.invalid/g5', 'https://example.invalid/policy',
                'https://example.invalid/policy-preview')}
            for tier in ('authoritative_tier_1', 'authoritative_tier_2', 'approved_provider_tier_3')
        }
        self.env = self.env(context={**self.env.context,
                                    'logistics_idp_test_authority_registry': approved})
        self.policy_manager = new_test_user(
            self.env, login=unique_fixture('policy-manager'),
            groups='insilos_logistics_idp.group_logistics_manager')
        case = self.env['logistics.idp.case'].with_user(self.policy_manager).create({
            'name': 'POLICY-PROVENANCE', 'source_system': 'fixture',
            'source_key': unique_fixture('POLICY-PROVENANCE'), 'source_version': '1',
            'provenance': 'fixture', 'effective_date': '2026-08-12',
        })
        self.provenance_document = self.env['logistics.idp.document'].with_user(self.policy_manager).intake_content(case, json.dumps({
                'document_type': 'master_data', 'confidence': 1, 'payload': {'supplier': 'fixture'},
            }).encode(), 'application/json', {'filename': unique_fixture('policy.json')})
        self.policy_reviewer = new_test_user(
            self.env, login=unique_fixture('policy-reviewer'),
            groups='insilos_logistics_idp.group_logistics_reviewer')

    def test_origin_evidence_evaluator_is_deterministic_and_fail_closed(self):
        absent = evaluate_origin_evidence({})
        self.assertEqual(absent['verdict'], 'NOT_APPLICABLE')
        valid = {'origin_country': 'VN', 'origin_criterion': 'X', 'co_number': 'CO-1', 'co_issuer': 'issuer', 'co_issue_date': '2026-01-01'}
        result = evaluate_origin_evidence(valid)
        self.assertEqual(result['verdict'], 'REVIEW')
        self.assertNotIn(result['verdict'], ('PASS', 'BLOCK'))
        self.assertIn('ORIGIN_EVIDENCE_INCOMPLETE', evaluate_origin_evidence({'origin_country': 'VN'})['reason_codes'])
        self.assertIn('ORIGIN_EVIDENCE_CONFLICT', evaluate_origin_evidence({**valid, 'declared_origin_country': 'CN'})['reason_codes'])
        self.assertIn('FTA_RULE_PACK_MISSING', evaluate_origin_evidence({'fta_claim': 'yes'})['reason_codes'])
        self.assertIn('ORIGIN_EVIDENCE_INVALID_DATE', evaluate_origin_evidence({**valid, 'co_issue_date': 'bad'})['reason_codes'])
        self.assertEqual(result['audit_input_hash'], evaluate_origin_evidence(dict(valid))['audit_input_hash'])

    def test_regulatory_change_notification_intent_is_deterministic_and_review_only(self):
        change = {'source': 'source-1', 'source_hash': 's1', 'policy_hash': 'p1'}
        affected = build_regulatory_change_notification(change, {'outcome': 'affected', 'audience': 'compliance'})
        self.assertEqual(affected['status'], 'pending_review')
        self.assertFalse(affected['send_external'])
        self.assertFalse(affected['activation_allowed'])
        self.assertEqual(affected['source'], 'source-1')
        self.assertEqual(affected['audit_input_hash'], build_regulatory_change_notification(dict(change), {'outcome': 'affected', 'audience': 'compliance'})['audit_input_hash'])
        self.assertEqual(build_regulatory_change_notification(change, {'outcome': 'not_affected'})['intent'], 'NOT_APPLICABLE')
        self.assertEqual(build_regulatory_change_notification(change, {'outcome': 'insufficient_context'})['reason'], 'REGULATORY_IMPACT_INSUFFICIENT_CONTEXT')
        self.assertEqual(build_regulatory_change_notification(None, {'outcome': 'affected'})['reason'], 'REGULATORY_CHANGE_NOTIFICATION_INCOMPLETE')
        self.assertEqual(build_regulatory_change_notification(change, {'outcome': 'affected', 'policy': {'authoritative': False}})['reason'], 'LEGAL_POLICY_DATASET_NOT_APPROVED')
        self.assertIn('output_hash', affected)

    def test_tariff_remedy_security_evaluator_is_deterministic_and_fail_closed(self):
        self.assertEqual(evaluate_tariff_remedy_security({})['verdict'], 'NOT_APPLICABLE')
        missing = evaluate_tariff_remedy_security({'tariff_rate': '5%'})
        self.assertIn('TARIFF_CLASSIFICATION_INCOMPLETE', missing['reason_codes'])
        self.assertIn('TARIFF_POLICY_DATASET_NOT_APPROVED', missing['reason_codes'])
        self.assertIn('TRADE_REMEDY_EVIDENCE_CONFLICT', evaluate_tariff_remedy_security({
            'remedy_type': 'AD', 'remedy_case_reference': 'C1', 'remedy_evidence': {'claim': 'x'},
            'remedy_claim': 'x', 'remedy_evidence_claim': 'y'} )['reason_codes'])
        self.assertIn('ECONOMIC_SECURITY_POLICY_NOT_APPROVED', evaluate_tariff_remedy_security({'economic_security_claim': 'yes'})['reason_codes'])
        self.assertIn('LEGAL_POLICY_DATASET_NOT_APPROVED', evaluate_tariff_remedy_security({'tariff_code': '0101'}, {'authoritative': False})['reason_codes'])
        result = evaluate_tariff_remedy_security({'tariff_code': '0101'})
        self.assertEqual(result['audit_input_hash'], evaluate_tariff_remedy_security({'tariff_code': '0101'})['audit_input_hash'])
        self.assertNotIn(result['verdict'], ('PASS', 'BLOCK'))

    def test_recorded_at_rejects_direct_sql_update(self):
        policy = self.env['logistics.idp.policy.source'].search([], limit=1)
        self.assertTrue(policy)
        with self.assertRaisesRegex(Exception, 'policy recorded_at is immutable'), self.env.cr.savepoint():
            self.env.cr.execute(
                "UPDATE logistics_idp_policy_source SET recorded_at = recorded_at + interval '1 second' WHERE id = %s",
                [policy.id],
            )

    def test_policy_history_upgrade_preserves_legacy_source_tier(self):
        policy = self.env['logistics.idp.policy.source'].search([], limit=1)
        self.assertTrue(policy)
        self.env.cr.execute(
            "UPDATE logistics_idp_policy_source SET source_tier = 'official' WHERE id = %s", [policy.id])
        self.env['logistics.idp.policy.source'].with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN)._upgrade_effective_policy_history()
        self.env.cr.execute("SELECT source_tier FROM logistics_idp_policy_source WHERE id = %s", [policy.id])
        self.assertEqual(self.env.cr.fetchone()[0], 'official')

    def test_legacy_saigon_timezone_migration_keeps_graph_grouping_valid(self):
        self.env.cr.execute(
            "UPDATE res_partner SET tz = 'Asia/Saigon' WHERE id = %s",
            [self.policy_manager.partner_id.id],
        )
        self.assertEqual(self.env['res.users']._normalize_legacy_saigon_timezone(), 1)
        self.assertEqual(self.policy_manager.tz, 'Asia/Ho_Chi_Minh')
        self.policy_manager.tz = 'Asia/Saigon'
        self.assertEqual(self.policy_manager.tz, 'Asia/Ho_Chi_Minh')
        rows = self.env['logistics.idp.case'].with_user(self.policy_manager).with_context(
            tz=self.policy_manager.tz,
        ).formatted_read_group([], ['create_date:day'], ['__count'])
        self.assertTrue(rows)

    def _activation_candidate(self):
        active = self.env['logistics.idp.policy.source'].search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)
        candidate = self.env['logistics.idp.policy.source'].with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': active.code, 'version': unique_fixture('G5'), 'company_id': self.env.company.id,
            'jurisdiction': active.jurisdiction, 'regime': active.regime,
            'source_tier': 'authoritative_tier_1', 'citation': 'https://example.invalid/g5',
            'provenance': json.dumps({'verification': 'verified'}),
            'trade02_binding': json.dumps({
                'status': 'verified', 'activation_allowed': True, 'approval_status': 'approved',
                'policy_sha256': active.payload_hash,
                'canonical_oracle_sha256': 'a' * 64, 'receipt_sha256': 'b' * 64,
                'pack_binding_sha256': 'c' * 64, 'reviewer_identity': 'reviewer',
                'legal_owner_identity': 'legal-owner', 'maker_identity': 'maker',
                'checker_identity': 'checker',
            }),
            'effective_from': active.effective_from, 'last_successful_sync_at': fields.Datetime.now(),
            'payload': active.payload,
        })
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'fixture'}, 'when': '2026-08-12',
            'transaction_time': '2026-08-12T00:00:00Z', 'effective_time': '2026-08-12T00:00:00Z',
            'recorded_time': fields.Datetime.now().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'),
            'evidence': [],
        }
        return active, candidate, context

    def test_trade_submit_is_blocked_without_external_verifier(self):
        _active, candidate, context = self._activation_candidate()
        test_enable = tools.config['test_enable']
        try:
            tools.config['test_enable'] = True
            ledger = self.env['logistics.idp.policy.activation']
            envelope = ledger.with_user(self.policy_manager).submit(
                candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
            tools.config['test_enable'] = False
            with self.assertRaisesRegex(
                    ValidationError,
                    '^TRADE activation is blocked: cryptographic external verifier/trust store is not configured\\.$'):
                ledger.with_user(self.policy_reviewer).decide(envelope, str(uuid4()), 'approve')
        finally:
            tools.config['test_enable'] = test_enable

    def test_trade02_binding_is_required_for_trade_activation(self):
        active, _candidate, _context = self._activation_candidate()
        model = self.env['logistics.idp.policy.source']
        for trade02_binding in (None, '{'):
            candidate = model.with_context(
                _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
            ).create({
                'code': 'TRADE_COMPLIANCE_%s' % unique_fixture('UNBOUND'), 'version': '1',
                'company_id': self.env.company.id, 'jurisdiction': active.jurisdiction,
                'regime': active.regime, 'source_tier': 'authoritative_tier_1',
                'citation': 'https://example.invalid/g5', 'provenance': json.dumps({'verification': 'verified'}),
                'trade02_binding': trade02_binding,
                'effective_from': active.effective_from, 'payload': active.payload,
            })
            self.assertEqual((candidate.activation_eligible, candidate.activation_blocker), (
                False, 'REVIEW: TRADE-02 verified independent-oracle binding is required for activation.'))

    def test_trade_activation_requires_fresh_source_evidence(self):
        _active, candidate, _context = self._activation_candidate()
        candidate.env.cr.execute(
            'UPDATE logistics_idp_policy_source SET last_successful_sync_at = NULL WHERE id = %s', [candidate.id])
        candidate.invalidate_recordset()
        self.assertEqual((candidate.freshness_status, candidate.activation_eligible, candidate.activation_blocker), (
            'review', False, 'REVIEW: source freshness is missing, stale, or not eligible for activation.'))

    def test_g5_submit_activate_and_reject_terminal_lifecycle(self):
        active, candidate, context = self._activation_candidate()
        ledger = self.env['logistics.idp.policy.activation']
        before = ledger.search_count([])
        envelope = ledger.with_user(self.policy_manager).submit(
            candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
        self.assertEqual(ledger.search_count([]), before)
        event = ledger.with_user(self.policy_reviewer).decide(
            envelope, str(uuid4()), 'approve')
        self.assertEqual((event.status, event.predecessor_policy_id, candidate.state, active.state),
                         ('activated', active, 'active', 'retired'))
        _, candidate2, context2 = self._activation_candidate()
        predecessor2 = self.env['logistics.idp.policy.source'].search([
            ('code', '=', candidate2.code), ('state', '=', 'active')], limit=1)
        envelope2 = ledger.with_user(self.policy_manager).submit(
            candidate2, '2026-08-12', '2026-08-12', 10000, context2, 'submit')
        rejected = ledger.with_user(self.policy_reviewer).decide(
            envelope2, str(uuid4()), 'reject', activate=False)
        self.assertEqual((rejected.status, candidate2.state, predecessor2.state),
                         ('rejected', 'draft', 'active'))

    def test_dev_only_internal_review_is_bound_immutable_and_never_activates(self):
        active, _candidate, context = self._activation_candidate()
        candidate = self.env['logistics.idp.policy.source'].with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': active.code, 'version': unique_fixture('DEV-REVIEW'),
            'company_id': self.env.company.id, 'jurisdiction': active.jurisdiction,
            'regime': active.regime, 'source_tier': 'early_warning_tier_4',
            'citation': 'fixture', 'effective_from': active.effective_from,
            'payload': active.payload,
        })
        ledger = self.env['logistics.idp.policy.activation']
        activated_before = ledger.search_count([('status', '=', 'activated')])
        decisions_before = self.env['logistics.idp.policy.decision'].search_count([])
        evidence_before = self.env['logistics.idp.evidence'].search_count([
            ('category', '=', 'policy_activation_reevaluation')])
        envelope = ledger.with_user(self.policy_manager).submit(
            candidate, '2026-08-12', '2026-08-12', 10000, context, 'synthetic review', internal_review=True)
        event = ledger.with_user(self.policy_reviewer).decide(
            envelope, str(uuid4()), 'internal review complete', internal_review=True)
        payload = json.loads(event.payload)
        self.assertEqual((event.status, event.failure_code, event.activated_at,
                          candidate.state, active.state, candidate.legal_authority,
                          candidate.activation_eligible),
                         ('internal_reviewed', 'DEV_INTERNAL_REVIEW', False,
                          'draft', 'active', False, False))
        self.assertEqual((ledger.search_count([('status', '=', 'activated')]),
                          self.env['logistics.idp.policy.decision'].search_count([]),
                          self.env['logistics.idp.evidence'].search_count([
                              ('category', '=', 'policy_activation_reevaluation')]),
                          payload['envelope']['outcome_kind']),
                         (activated_before, decisions_before, evidence_before, 'internal_review'))
        self.assertEqual((event.policy_hash, event.diff_hash, event.preview_input_hash,
                          event.preview_output_hash),
                         (payload['envelope']['policy_hash'], payload['envelope']['diff_hash'],
                          payload['envelope']['preview_input_hash'],
                          payload['envelope']['preview_output_hash']))
        self.assertRegex(event.envelope_hash, '^[0-9a-f]{64}$')

    def test_g5_replay_tamper_self_approval_and_stale_binding(self):
        active, candidate, context = self._activation_candidate()
        ledger = self.env['logistics.idp.policy.activation']
        envelope = ledger.with_user(self.policy_manager).submit(
            candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
        event_uuid = str(uuid4())
        event = ledger.with_user(self.policy_reviewer).decide(envelope, event_uuid, 'approve')
        self.assertEqual(ledger.with_user(self.policy_reviewer).decide(
            envelope, event_uuid, 'approve'), event)
        with self.assertRaisesRegex(Exception, 'conflicting terminal outcome'):
            ledger.with_user(self.policy_reviewer).decide(envelope, event_uuid, 'reject', activate=False)
        with self.assertRaisesRegex(Exception, 'conflicting terminal outcome'):
            ledger.with_user(self.policy_reviewer).decide(envelope, str(uuid4()), 'approve')
        self.assertRegex(event.envelope_hash, '^[0-9a-f]{64}$')
        tampered = dict(envelope, payload=envelope['payload'] + ' ')
        with self.assertRaisesRegex(Exception, 'signature is invalid'):
            ledger.with_user(self.policy_reviewer).decide(tampered, str(uuid4()), 'approve')
        _, stale, stale_context = self._activation_candidate()
        stale_envelope = ledger.with_user(self.policy_manager).submit(
            stale, '2026-08-12', '2026-08-12', 10000, stale_context, 'submit')
        reviewer_group = self.env.ref('insilos_logistics_idp.group_logistics_reviewer')
        self.policy_manager.sudo().write({'group_ids': [(4, reviewer_group.id)]})
        with self.assertRaisesRegex(Exception, 'Maker and checker must differ'):
            ledger.with_user(self.policy_manager).decide(stale_envelope, str(uuid4()), 'approve')
        self.env.cr.execute("UPDATE logistics_idp_policy_source SET state = 'retired' WHERE id = %s", [stale.id])
        stale.invalidate_recordset()
        with self.assertRaisesRegex(Exception, 'draft policy candidate'):
            ledger.with_user(self.policy_reviewer).decide(stale_envelope, str(uuid4()), 'approve')
        with self.assertRaisesRegex(Exception, 'draft policy candidate'):
            ledger.with_user(self.policy_reviewer).decide(stale_envelope, str(uuid4()), 'reject', activate=False)
        self.assertEqual((stale.state, active.state), ('retired', 'retired'))

    def test_g5_activation_rechecks_governance_eligibility_at_decision(self):
        _active, candidate, context = self._activation_candidate()
        ledger = self.env['logistics.idp.policy.activation']
        envelope = ledger.with_user(self.policy_manager).submit(
            candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
        self.env.cr.execute("UPDATE logistics_idp_policy_source SET citation = %s WHERE id = %s", [
            'https://example.invalid/revoked', candidate.id])
        candidate.invalidate_recordset()
        with self.assertRaisesRegex(ValidationError, 'no longer governance-eligible'):
            ledger.with_user(self.policy_reviewer).decide(envelope, str(uuid4()), 'approve')
        self.assertEqual(candidate.state, 'draft')

    def test_g5_unresolved_blocker_and_terminal_insert_failure_roll_back(self):
        active, candidate, context = self._activation_candidate()
        ledger = self.env['logistics.idp.policy.activation']
        envelope = ledger.with_user(self.policy_manager).submit(
            candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
        payload = json.loads(envelope['payload'])
        if payload['preview_case_ids']:
            self.env['logistics.idp.exception'].create({
                'case_id': payload['preview_case_ids'][0], 'exception_type': 'policy', 'severity': 'critical'})
            with self.assertRaisesRegex(Exception, 'blockers'):
                ledger.with_user(self.policy_reviewer).decide(envelope, str(uuid4()), 'approve')
            self.assertEqual((candidate.state, active.state), ('draft', 'active'))

    def test_g5_submit_rejects_non_authority_tiers_and_cross_company(self):
        active, _candidate, context = self._activation_candidate()
        ledger = self.env['logistics.idp.policy.activation'].with_user(self.policy_manager)
        for tier in ('early_warning_tier_4', 'customer_reference', 'demo'):
            candidate = self.env['logistics.idp.policy.source'].with_context(
                _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
            ).create({
                'code': unique_fixture('G5-%s' % tier), 'version': '1',
                'company_id': self.env.company.id, 'jurisdiction': active.jurisdiction,
                'regime': active.regime, 'source_tier': tier,
                'citation': 'https://example.invalid/g5-authority',
                'provenance': '{"verification":"verified"}',
                'effective_from': active.effective_from, 'payload': active.payload,
            })
            with self.assertRaisesRegex(Exception, 'legal-authority candidate'):
                ledger.submit(candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
        foreign = self.env['res.company'].create({'name': unique_fixture('G5 Foreign')})
        foreign_candidate = self.env['logistics.idp.policy.source'].with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': unique_fixture('G5-FOREIGN'), 'version': '1', 'company_id': foreign.id,
            'jurisdiction': active.jurisdiction, 'regime': active.regime,
            'source_tier': 'authoritative_tier_1', 'citation': 'https://example.invalid/g5-foreign',
            'provenance': '{"verification":"verified"}', 'effective_from': active.effective_from,
            'payload': active.payload,
        })
        with self.assertRaisesRegex(Exception, 'allowed-company'):
            ledger.submit(foreign_candidate, '2026-08-12', '2026-08-12', 10000,
                          {**context, 'company_id': foreign.id}, 'submit')

    def test_g5_changed_policy_diff_preview_and_blocker_bindings_fail_closed(self):
        ledger = self.env['logistics.idp.policy.activation']
        for binding in ('policy', 'diff', 'preview_input', 'preview_output', 'blocker'):
            active, candidate, context = self._activation_candidate()
            envelope = ledger.with_user(self.policy_manager).submit(
                candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
            payload = json.loads(envelope['payload'])
            patches = []
            if binding == 'policy':
                self.env.cr.execute("UPDATE logistics_idp_policy_source SET payload_hash = %s WHERE id = %s",
                                    ['0' * 64, candidate.id])
                candidate.invalidate_recordset()
            elif binding == 'diff':
                original = type(candidate).diff_candidate
                patches.append(patch.object(type(candidate), 'diff_candidate', autospec=True,
                                            side_effect=lambda recordset, value: {
                                                **original(recordset, value), 'changes': [{'path': '$.changed'}]}))
            elif binding.startswith('preview_'):
                original = type(candidate).preview_impact
                key = 'input_hash' if binding == 'preview_input' else 'output_hash'
                patches.append(patch.object(type(candidate), 'preview_impact', autospec=True,
                                            side_effect=lambda recordset, *args, **kwargs: {
                                                **original(recordset, *args, **kwargs), key: '0' * 64}))
            else:
                patches.append(patch.object(type(ledger), '_blocker_binding', autospec=True,
                                            return_value=([{'id': 0}], '0' * 64)))
            with patches[0] if patches else patch.object(type(ledger), '_name', type(ledger)._name):
                with self.assertRaisesRegex(Exception, 'stale, mismatched, or has unresolved blockers'):
                    ledger.with_user(self.policy_reviewer).decide(envelope, str(uuid4()), 'approve')
            self.assertEqual((candidate.state, active.state), ('draft', 'active'))
            if binding == 'policy':
                self.env.cr.execute("UPDATE logistics_idp_policy_source SET payload_hash = %s WHERE id = %s",
                                    [payload['policy_hash'], candidate.id])
                candidate.invalidate_recordset()

    def test_srs_4a5_activation_reevaluates_only_bound_affected_cases(self):
        _active, candidate, context = self._activation_candidate()
        cases = self.env['logistics.idp.case']
        affected = cases.create({'name': unique_fixture('AFFECTED'), 'source_system': 'fixture',
            'source_key': unique_fixture('AFFECTED'), 'source_version': '1', 'provenance': 'fixture',
            'effective_date': candidate.effective_from, 'owner_id': self.policy_reviewer.id})
        untouched = [cases.create({'name': unique_fixture(outcome), 'source_system': 'fixture',
            'source_key': unique_fixture(outcome), 'source_version': '1', 'provenance': 'fixture',
            'effective_date': candidate.effective_from})
            for outcome in ('possibly_affected', 'insufficient_context', 'not_affected')]
        out_of_window = cases.create({'name': unique_fixture('OUTSIDE'), 'source_system': 'fixture',
            'source_key': unique_fixture('OUTSIDE'), 'source_version': '1', 'provenance': 'fixture',
            'effective_date': '2000-01-01'})
        selected = [affected, *untouched, out_of_window]
        preview = {'case_ids': [case.id for case in selected], 'cases': [
            {'id': case.id, 'company_id': case.company_id.id, 'identity': '%s:%s' % (case._name, case.id)}
            for case in selected], 'results': [
            {'case_id': affected.id, 'outcome': 'affected', 'reasons': ['fixture']},
            *[{'case_id': case.id, 'outcome': outcome, 'reasons': ['fixture']}
              for case, outcome in zip(untouched, ('possibly_affected', 'insufficient_context', 'not_affected'))],
            {'case_id': out_of_window.id, 'outcome': 'affected', 'reasons': ['outside']},
        ], 'input_hash': '1' * 64, 'output_hash': '2' * 64}
        ledger = self.env['logistics.idp.policy.activation']
        with patch.object(type(candidate), 'preview_impact', autospec=True, return_value=preview):
            envelope = ledger.with_user(self.policy_manager).submit(
                candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
            event_uuid = str(uuid4())
            event = ledger.with_user(self.policy_reviewer).decide(envelope, event_uuid, 'approve')
            replay = ledger.with_user(self.policy_reviewer).decide(envelope, event_uuid, 'approve')
        decisions = self.env['logistics.idp.policy.decision'].search([('case_id', 'in', [case.id for case in selected])])
        evidence = self.env['logistics.idp.evidence'].search([('case_id', 'in', [case.id for case in selected]),
            ('category', '=', 'policy_activation_reevaluation')])
        activities = self.env['mail.activity'].search([
            ('res_model', '=', affected._name), ('res_id', 'in', [case.id for case in selected]),
            ('summary', '=', 'Regulatory change review [%s]' % event_uuid),
        ])
        self.assertEqual((replay, decisions.case_id, evidence.case_id), (event, affected, affected))
        self.assertEqual((len(activities), activities.res_id, activities.user_id),
                         (1, affected.id, self.policy_reviewer))
        self.assertIn(affected.company_id, activities.user_id.company_ids)
        self.assertIn(event_uuid, activities.note)
        self.assertEqual(self.env['mail.mail'].sudo().search_count([
            ('body_html', 'ilike', event_uuid)]), 0)
        decision = decisions
        manifest = json.loads(decision.payload)['input_manifest']
        self.assertEqual((decision.verdict, manifest['activation_id'], manifest['activation_uuid'],
                          manifest['policy_hash'], manifest['selected_impact']['outcome']),
                         ('review', event.id, event.event_uuid, candidate.payload_hash, 'affected'))
        self.assertRegex(manifest['activation_hash'], '^[0-9a-f]{64}$')
        self.assertEqual(json.loads(evidence.payload)['decision_hash'], decision.payload_hash)

    def test_g5_terminal_event_is_immutable(self):
        _active, candidate, context = self._activation_candidate()
        ledger = self.env['logistics.idp.policy.activation']
        envelope = ledger.with_user(self.policy_manager).submit(
            candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
        event = ledger.with_user(self.policy_reviewer).decide(envelope, str(uuid4()), 'approve')
        with self.assertRaisesRegex(Exception, 'immutable'):
            event.write({'reason': 'tampered'})
        with self.assertRaisesRegex(Exception, 'immutable'):
            event.unlink()

    def test_workspace_reuses_standard_models(self):
        project = self.env.ref('insilos_logistics_idp.project_logistics_idp')
        self.assertEqual(project._name, 'project.project')
        self.assertEqual(len(project.type_ids), 7)
        self.assertEqual(project.type_ids[-1].name, 'Completed')
        self.assertTrue(project.type_ids[-1].fold)

    def test_fail_safe_case_properties_exist(self):
        definitions = self.env.ref('insilos_logistics_idp.project_logistics_idp').task_properties_definition
        by_name = {definition['name']: definition for definition in definitions}
        self.assertEqual(
            {tuple(item) for item in by_name['compliance_verdict']['selection']},
            {('pending', 'Pending'), ('pass', 'Pass'), ('review', 'Review'), ('block', 'Block'), ('na', 'Not Applicable')},
        )
        self.assertIn('policy_version', by_name)
        self.assertIn('evidence_reference', by_name)
        self.assertIn('source_provenance', by_name)

    def test_phase_tags_and_mes_boundary_are_seeded(self):
        self.assertEqual(self.env.ref('insilos_logistics_idp.tag_vietnam_e13').name, 'VN Customs: E13')
        self.assertEqual(self.env.ref('insilos_logistics_idp.tag_gate_pass_optional').name, 'Output: Gate Pass Optional')
        self.assertIn('Read Only', self.env.ref('insilos_logistics_idp.document_tag_mes_evidence').name)

    def test_role_separation_is_explicit(self):
        operator = self.env.ref('insilos_logistics_idp.group_logistics_operator')
        reviewer = self.env.ref('insilos_logistics_idp.group_logistics_reviewer')
        auditor = self.env.ref('insilos_logistics_idp.group_logistics_auditor')
        self.assertNotEqual(operator, reviewer)
        self.assertNotIn(reviewer, operator.implied_ids)
        self.assertNotIn(operator, reviewer.implied_ids)
        self.assertNotIn(operator, auditor.implied_ids)

    def test_actions_use_runtime_case_and_reused_documents(self):
        cases = self.env.ref('insilos_logistics_idp.action_logistics_cases')
        documents = self.env.ref('insilos_logistics_idp.action_logistics_documents')
        document_form = self.env.ref('insilos_logistics_idp.view_logistics_document_form')
        self.assertEqual(cases.res_model, 'logistics.idp.case')
        self.assertEqual(documents.res_model, 'logistics.idp.document')
        case_form = self.env.ref('insilos_logistics_idp.view_logistics_case_form')
        self.assertIn('name="action_open_inbox_wizard"', document_form.arch)
        self.assertNotIn('name="action_reclassify"', document_form.arch)
        self.assertIn('name="action_reextract"', document_form.arch)
        wizard_form = self.env.ref('insilos_logistics_idp.view_logistics_document_inbox_wizard_form')
        self.assertIn('name="action_apply"', wizard_form.arch)
        self.assertIn('<field name="case_id"/>', document_form.arch)
        self.assertIn('name="source_message_reference"', document_form.arch + self.env.ref('insilos_logistics_idp.view_logistics_document_list').arch)
        self.assertIn('name="attachment_id"', document_form.arch)
        self.assertIn('name="mark_semantic_duplicate"', case_form.arch)
        self.assertIn('name="canonical_case_id"', case_form.arch)
        self.assertIn("readonly=\"state in ('completed', 'closed_duplicate', 'closed_other')\"", case_form.arch)

    def test_srs_section_7_2_document_inbox_truthful_ui_contract(self):
        document_list = self.env.ref('insilos_logistics_idp.view_logistics_document_list').arch
        document_form = self.env.ref('insilos_logistics_idp.view_logistics_document_form').arch
        for field_name in ('create_date', 'source_channel', 'source_sender',
                           'source_message_reference', 'document_type',
                           'classification_confidence', 'case_id', 'status',
                           'inbox_action_required'):
            self.assertIn('name="%s"' % field_name, document_list + document_form)
        self.assertIn('name="attachment_id" widget="logistics_attachment_viewer"', document_form)
        self.assertIn('name="action_open_inbox_wizard"', document_form)
        self.assertNotIn('name="action_reclassify"', document_form)
        self.assertIn('name="action_reextract"', document_form)
        self.assertNotIn('action_assign_case', document_form)
        self.assertNotIn('name="action_open_duplicate_wizard"', document_form)
        self.assertIn('name="duplicate_of_id"', document_list)
        self.assertIn('name="action_open_source_email"', document_form)
        self.assertIn("invisible=\"source_channel != 'email'\"", document_form)

    def test_legacy_customer_reference_is_read_only_operational_runtime_configuration(self):
        policy = self.env['logistics.idp.policy.source'].search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)
        model = self.env['logistics.idp.policy.source']
        payload = model.validate_policy_payload(
            policy.payload, 'trade_compliance', 'vn_fdi_fta', 'VN', 'E13')
        self.assertEqual((policy.code, policy.version, policy.source_tier, policy.state),
                         ('TRADE_COMPLIANCE_VN_REFERENCE', '2026.3', 'customer_reference', 'active'))
        self.assertEqual(self.env.ref(
            'insilos_logistics_idp.policy_trade_compliance_vn_reference_2026_2').state, 'retired')
        citation = urlsplit(policy.citation)
        self.assertEqual((citation.scheme, citation.username, citation.password, citation.query),
                         ('https', None, None, ''))
        selected = model.select_effective_pack(
            self.env.company, 'trade_compliance', 'vn_fdi_fta', 'VN', 'E13', fields.Date.today())
        self.assertEqual(selected, policy)
        historical = model.select_effective_pack(
            self.env.company, 'trade_compliance', 'vn_fdi_fta', 'VN', 'E13',
            fields.Date.from_string('2026-07-16'))
        current = model.select_effective_pack(
            self.env.company, 'trade_compliance', 'vn_fdi_fta', 'VN', 'E13',
            fields.Date.from_string('2026-08-10'))
        self.assertEqual(historical, policy)
        self.assertEqual(current, policy)
        self.assertEqual(model.validate_policy_payload(
            historical.payload, 'trade_compliance', 'vn_fdi_fta', 'VN', 'E13')['schema_version'], '1')
        configured = deterministic_classify({'filename': 'PO_123.pdf', 'idp_policy': payload})
        self.assertEqual((configured['type'], configured['confidence']), ('purchase_order', .95))
        pack = payload['vertical']['packs']['vn_fdi_fta']
        self.assertFalse(batch_structure([
            {'document_type': role} for role in pack['batch']['expected_roles']
        ], payload)['missing'])
        self.assertIsNone(pack['reconciliation']['quantity_tolerance'])
        self.assertIsNone(pack['reconciliation']['rounding'])
        extraction = payload['horizontal']['extraction']
        self.assertEqual(extraction['review_thresholds']['main_vat_invoice'], .8)
        self.assertIn('lines[].quantity', extraction['critical_fields']['main_vat_invoice'])
        self.assertTrue(policy.audit_input_hash)
        operator = new_test_user(
            self.env, login='policy-audit-operator',
            groups='insilos_logistics_idp.group_logistics_operator')
        case = self.env['logistics.idp.case'].with_user(operator).create({
            'name': 'POLICY-AUDIT', 'source_system': 'fixture', 'source_key': unique_fixture('POLICY-AUDIT'),
            'source_version': '1', 'provenance': 'fixture', 'effective_date': '2026-08-10',
        })
        document = self.env['logistics.idp.document'].with_user(operator).intake_content(case, json.dumps({
                'document_type': 'packing_list', 'confidence': 1,
                'payload': {'supplier': 'S', 'lines': [{}]},
            }).encode(), 'application/json', {'filename': 'packing.json'})
        run_policy = json.loads(document.current_run_id.payload)['policy']
        self.assertEqual({key: run_policy[key] for key in ('code', 'version', 'hash')}, {
            'code': policy.code, 'version': policy.version, 'hash': policy.payload_hash,
        })
        self.assertEqual(len(run_policy['effective_hash']), 64)
        serialized = json.dumps(payload, sort_keys=True).casefold()
        forbidden = re.compile(r'"(?:password|token|secret|authorization|email|phone|customer_name)"\s*:')
        self.assertIsNone(forbidden.search(serialized))

    def test_lidp03_effective_regime_policy_selection_stays_non_authoritative(self):
        model = self.env['logistics.idp.policy.source']
        baseline = model.search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)

        def policy(regime, version, effective_from, effective_to=False):
            return model.with_context(
                _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
            ).create({
                'code': unique_fixture('LIDP03'), 'version': version,
                'company_id': self.env.company.id, 'jurisdiction': 'LIDP03', 'regime': regime,
                'source_tier': 'customer_reference', 'citation': 'fixture',
                'effective_from': effective_from, 'effective_to': effective_to,
                'state': 'active', 'payload': baseline.payload,
            })

        e13_before = policy('E13', 'before', '2026-01-01', '2026-06-30')
        e13_after = policy('E13', 'after', '2026-07-01')
        e15 = policy('E15', 'same-identity', '2026-01-01')
        before = model.select_effective(self.env.company, 'LIDP03', 'E13', '2026-06-30')
        after = model.select_effective(self.env.company, 'LIDP03', 'E13', '2026-07-01')
        mixed = model.select_effective(self.env.company, 'LIDP03', 'E15', '2026-07-01')
        self.assertEqual((before, after, mixed), (e13_before, e13_after, e15))
        self.assertEqual((before.legal_authority, after.legal_authority, mixed.legal_authority),
                         (False, False, False))
        self.assertEqual((before.activation_eligible, after.activation_eligible, mixed.activation_eligible),
                         (False, False, False))

    def test_policy_workspace_governed_actions_and_unverified_fail_closed(self):
        model = self.env['logistics.idp.policy.source']
        active, _candidate, context = self._activation_candidate()
        unverified = model.with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': unique_fixture('UNVERIFIED'), 'version': '1', 'company_id': self.env.company.id,
            'jurisdiction': 'VN', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'LAW:UNVERIFIED', 'effective_from': active.effective_from,
            'payload': active.payload, 'provenance': {'verification': 'unverified'},
        })
        self.assertEqual((unverified.verification_status, unverified.legal_authority,
                          unverified.activation_eligible), ('unverified', True, False))
        with self.assertRaisesRegex(Exception, 'verified draft'):
            self.env['logistics.idp.policy.activation'].with_user(self.policy_manager).submit(
                unverified, active.effective_from, active.effective_from, 10000, context, 'submit')

    def test_policy_workspace_exposes_governance_metadata_and_defers_unsafe_preview(self):
        model = self.env['logistics.idp.policy.source']
        manager = new_test_user(
            self.env, login='policy-view-manager',
            groups='insilos_logistics_idp.group_logistics_manager')
        views = model.with_user(manager).get_views([(False, 'list'), (False, 'form')])['views']
        combined = views['list']['arch'] + views['form']['arch']
        for field_name in ('source_tier', 'verification_status', 'legal_authority',
                           'activation_eligible', 'activation_blocker', 'citation', 'effective_from',
                           'effective_to', 'payload_hash', 'state', 'supersedes_id',
                           'impacted_case_count'):
            self.assertIn('name="%s"' % field_name, combined)
        self.assertNotIn('name="action_activate"', combined)
        self.assertIn('REVIEW: source is unverified; activation forbidden.', views['form']['arch'])
        self.assertIn('name="action_view_semantic_diff"', combined)
        self.assertIn('name="action_open_governance_wizard"', combined)
        self.assertIn("state != 'active' or source_tier != 'customer_reference'", views['form']['arch'])
        wizard = self.env.ref('insilos_logistics_idp.view_policy_governance_wizard_form').arch
        for label in ('DEV-only synthetic/internal review.', 'Non-production.',
                      'Legal activation blocked.', 'action_internal_review'):
            self.assertIn(label, wizard)
        self.assertNotIn('name="action_approve"', wizard)

    def test_trade_compliance_authority_and_context_contract(self):
        model = self.env['logistics.idp.policy.source']
        self.assertEqual(set(dict(model._fields['source_tier'].selection)), {
            'demo', 'customer_reference', 'early_warning_tier_4', 'authoritative_tier_1',
            'authoritative_tier_2', 'approved_provider_tier_3'})
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'SYNTHETIC'},
            'when': '2026-08-12', 'transaction_time': '2026-08-12T00:00:00Z',
            'effective_time': '2026-08-12T00:00:00Z', 'recorded_time': '2026-08-12T23:59:59Z',
            'evidence': [{'document_id': self.provenance_document.id, 'field': 'supplier',
                          'source_kind': 'document', 'source_hash': self.provenance_document.content_hash,
                          'extraction_run_id': self.provenance_document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
        }
        first = model.validate_compliance_context(context)
        second = model.validate_compliance_context(json.dumps(context, sort_keys=False))
        self.assertEqual(first['context_hash'], second['context_hash'])
        self.assertEqual(first['verdict'], 'pass')
        low_context = json.loads(json.dumps(context))
        low_context['authority'] = low_context['evidence'][0]['authority'] = 'customer_reference'
        self.assertEqual(model.validate_compliance_context(low_context)['verdict'], 'review')
        missing = model.validate_compliance_context({**context, 'who': None})
        self.assertEqual(missing['verdict'], 'review')
        self.assertIn('who', missing['missing_critical'])
        with self.assertRaisesRegex(Exception, 'Unknown compliance authority'):
            model.validate_compliance_context({**context, 'authority': 'official'})
        wrong_hash = json.loads(json.dumps(context))
        wrong_hash['evidence'][0]['source_hash'] = '0' * 64
        with self.assertRaisesRegex(Exception, 'does not match its referenced document'):
            model.validate_compliance_context(wrong_hash)

    def test_trade_g1_context_timezone_and_missing_contract(self):
        model = self.env['logistics.idp.policy.source']
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'SYNTHETIC'},
            'when': '2026-08-12', 'transaction_time': '2026-08-12T00:00:00Z',
            'effective_time': '2026-08-12T00:00:00Z', 'recorded_time': '2026-08-12T23:59:59Z',
            'evidence': [{'document_id': self.provenance_document.id, 'field': 'supplier',
                          'source_kind': 'document', 'source_hash': self.provenance_document.content_hash,
                          'extraction_run_id': self.provenance_document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
        }
        offset = {**context, 'transaction_time': '2026-08-12T07:00:00+07:00',
                  'effective_time': '2026-08-12T07:00:00+07:00',
                  'recorded_time': '2026-08-13T06:59:59+07:00'}
        normalized, equivalent = model.validate_compliance_context(context), model.validate_compliance_context(offset)
        self.assertEqual(
            (normalized['context']['transaction_time'], normalized['context']['effective_time'],
             normalized['context']['recorded_time'], normalized['context_hash'], normalized['mapping_evidence']['mapping_hash']),
            (equivalent['context']['transaction_time'], equivalent['context']['effective_time'],
             equivalent['context']['recorded_time'], equivalent['context_hash'], equivalent['mapping_evidence']['mapping_hash']),
        )
        for patch, missing in (({'who': None}, 'who'), ({'when': None}, 'when'), ({'evidence': []}, 'evidence'),
                               ({'evidence': [{**context['evidence'][0], 'source_hash': 'x' * 64}]}, 'evidence')):
            result = model.validate_compliance_context({**context, **patch})
            self.assertEqual(result['verdict'], 'review')
            self.assertIn(missing, result['missing_critical'])
        for patch in ({'transaction_time': None}, {'effective_time': 'invalid'}, {'recorded_time': '2026-08-12T23:59:59'}):
            with self.assertRaisesRegex(ValidationError, 'timezone-aware'):
                model.validate_compliance_context({**context, **patch})

    def test_srs_4a9_cross_border_context_is_canonical_deterministic_and_fail_closed(self):
        model = self.env['logistics.idp.policy.source']
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'SYNTHETIC'}, 'when': '2026-08-12',
            'transaction_time': '2026-08-12T00:00:00Z', 'effective_time': '2026-08-12T00:00:00Z',
            'recorded_time': '2026-08-12T23:59:59Z',
            'evidence': [{'document_id': self.provenance_document.id, 'field': 'supplier',
                          'source_kind': 'document', 'source_hash': self.provenance_document.content_hash,
                          'extraction_run_id': self.provenance_document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
            'what': {'hs': '123456'},
            'where': {'origin_country': 'VN', 'export_country': 'VN', 'import_country': 'US'},
            'procedure': {'code': 'E13'}, 'transport': {'mode': 'sea', 'extensions': {'x-demo:route': 'direct'}},
        }
        first = model.validate_compliance_context(context)
        second = model.validate_compliance_context(json.loads(json.dumps(context)))
        self.assertEqual((first['context_hash'], first['mapping_evidence']),
                         (second['context_hash'], second['mapping_evidence']))
        self.assertEqual(first['context']['what'], {'hs_code': '123456'})
        self.assertEqual(first['context']['where'], {
            'origin_country_code': 'VN', 'export_country_code': 'VN', 'import_country_code': 'US'})
        self.assertRegex(first['mapping_evidence']['mapping_hash'], '^[0-9a-f]{64}$')
        self.assertEqual(model.validate_compliance_context({**context, 'who': None})['verdict'], 'review')
        for patch, message in (
                ({'what': {'hs': '123456', 'hs_code': '654321'}}, 'alias conflicts'),
                ({'what': {'hs_code': '123456', 'tariff_code': 'x'}}, 'unknown fields'),
                ({'transport': {'mode': 'sea', 'extensions': {'x-demo:mode': 'air'}}}, 'extensions')):
            invalid = {**context, **patch}
            with self.assertRaisesRegex(ValidationError, message):
                model.validate_compliance_context(invalid)

    def test_srs_4a8_simulation_is_test_only_deterministic_read_only_and_non_legal(self):
        model = self.env['logistics.idp.policy.source']
        active = model.search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)
        candidate = model.with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': active.code, 'version': unique_fixture('SIMULATION'), 'company_id': self.env.company.id,
            'jurisdiction': active.jurisdiction, 'regime': active.regime,
            'source_tier': active.source_tier, 'citation': active.citation,
            'provenance': active.provenance, 'effective_from': active.effective_from,
            'payload': active.payload,
        })
        recorded_time = fields.Datetime.to_string(active.recorded_at).replace(' ', 'T') + 'Z'
        cutoff = fields.Date.to_string(active.recorded_at.date())
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': candidate.source_tier, 'who': {'party': 'fixture'}, 'when': cutoff,
            'transaction_time': recorded_time, 'effective_time': recorded_time, 'recorded_time': recorded_time,
            'evidence': [{'document_id': self.provenance_document.id, 'field': 'policy',
                          'source_kind': 'document', 'source_hash': self.provenance_document.content_hash,
                          'extraction_run_id': self.provenance_document.current_run_id.id,
                          'authority': candidate.source_tier}],
        }
        tracked = ['logistics.idp.case', 'logistics.idp.document', 'logistics.idp.extraction.run',
                   'logistics.idp.check.result', 'logistics.idp.evidence',
                   'logistics.idp.policy.decision', 'mail.activity', 'logistics.idp.policy.source']
        before = {name: self.env[name].sudo().search_count([]) for name in tracked}
        snapshot = {name: self.env[name].sudo().search([]).read(['write_date']) for name in tracked}
        hypothetical = {'id': candidate.id, 'payload_hash': candidate.payload_hash}
        test_enable = tools.config['test_enable']
        try:
            tools.config['test_enable'] = True
            first = model.simulate_scenario(candidate, cutoff, cutoff, 10000, context, hypothetical)
            second = model.simulate_scenario(candidate, cutoff, cutoff, 10000,
                                             json.loads(json.dumps(context)), hypothetical)
            self.assertEqual((first['input_hash'], first['output_hash'], first['counts']),
                             (second['input_hash'], second['output_hash'], second['counts']))
            self.assertEqual(first['simulation'], {
                'mode': 'non_production', 'read_only': True, 'legal_authority': False,
                'disclaimer': 'Hypothetical simulation; no legal authority.'})
            self.assertEqual(first['output_hash'], hashlib.sha256(json.dumps(
                {'counts': first['counts'], 'results': first['results']}, ensure_ascii=False,
                separators=(',', ':'), sort_keys=True).encode()).hexdigest())
            with self.assertRaisesRegex(Exception, 'explicit hypothetical candidate'):
                model.simulate_scenario(candidate, cutoff, cutoff, 10000, context, {})
            tools.config['test_enable'] = False
            with self.assertRaisesRegex(Exception, 'non-production only'):
                model.simulate_scenario(candidate, cutoff, cutoff, 10000, context, hypothetical)
        finally:
            tools.config['test_enable'] = test_enable
        self.assertEqual(before, {name: self.env[name].sudo().search_count([]) for name in tracked})
        self.assertEqual(snapshot, {name: self.env[name].sudo().search([]).read(['write_date']) for name in tracked})

    def test_verified_arbitrary_https_and_citation_path_mismatch_are_ineligible(self):
        model = self.env['logistics.idp.policy.source']
        self.assertFalse(model.with_context(logistics_idp_test_authority_registry=None)._citation_is_governed(
            'authoritative_tier_1', 'https://example.invalid/g5'))
        active = model.search([('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE')], limit=1)
        for citation in ('https://evil.invalid/law', 'https://example.invalid/g5/other'):
            candidate = model.with_context(
                _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
            ).create({
                'code': unique_fixture('UNGOVERNED'), 'version': '1',
                'company_id': self.env.company.id, 'jurisdiction': 'VN', 'regime': 'ALL',
                'source_tier': 'authoritative_tier_1', 'citation': citation,
                'provenance': '{"verification":"verified"}',
                'effective_from': active.effective_from, 'payload': active.payload,
            })
            self.assertFalse(candidate.activation_eligible)
        governed = model.with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': unique_fixture('GOVERNED'), 'version': '1',
            'company_id': self.env.company.id, 'jurisdiction': 'VN', 'regime': 'ALL',
            'source_tier': 'authoritative_tier_1', 'citation': 'https://example.invalid/g5',
            'provenance': '{"verification":"verified"}',
            'effective_from': active.effective_from, 'payload': active.payload,
        })
        self.assertTrue(governed.activation_eligible)

    def test_policy_candidate_import_is_draft_idempotent_and_diff_is_read_only(self):
        model = self.env['logistics.idp.policy.source'].with_user(self.policy_manager)
        active = self.env['logistics.idp.policy.source'].search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)
        payload = json.loads(active.payload)
        payload['policy_metadata'] = {
            'source_publication_date': '2026-08-10', 'applicability_predicate': {'jurisdiction': 'VN'},
            'severity_decision_effect': {'severity': 'medium', 'decision_effect': 'review'},
            'evidence_requirements': ['source_document'],
        }
        payload['horizontal']['classification']['thresholds']['strong_filename'] = .81
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'fixture'}, 'when': '2026-08-12',
            'transaction_time': '2026-08-12T00:00:00Z', 'effective_time': '2026-08-12T00:00:00Z',
            'recorded_time': '2026-08-12T23:59:59Z',
            'evidence': [{'document_id': self.provenance_document.id, 'field': 'policy',
                          'source_kind': 'document', 'source_hash': self.provenance_document.content_hash,
                          'extraction_run_id': self.provenance_document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
        }
        values = {
            'code': active.code, 'version': unique_fixture('CANDIDATE'), 'company_id': self.env.company.id,
            'jurisdiction': 'VN', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/policy',
            'provenance': {'source': 'fixture', 'captured_at': '2026-08-12T00:00:00Z'},
            'effective_from': fields.Date.today(), 'payload': payload, 'compliance_context': context,
        }
        candidate = model.import_candidate(values)
        self.assertEqual((candidate.state, candidate.provenance), (
            'draft', json.dumps(values['provenance'], separators=(',', ':'), sort_keys=True)))
        self.assertEqual(model.import_candidate(json.loads(json.dumps(values, default=str))), candidate)
        self.assertEqual(candidate.payload_hash, hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        self.assertEqual(model.select_effective_pack(
            self.env.company, 'trade_compliance', 'vn_fdi_fta', 'VN', 'E13', active.effective_from
        ).payload_hash, active.payload_hash)
        self.assertEqual(json.loads(candidate.payload)['policy_metadata'], payload['policy_metadata'])
        for field, malformed in (
                ('source_publication_date', None), ('source_publication_date', '2026-99-99'),
                ('applicability_predicate', None), ('applicability_predicate', []), ('applicability_predicate', '  '),
                ('severity_decision_effect', None),
                ('severity_decision_effect', {'severity': 'medium', 'decision_effect': 'invalid'}),
                ('severity_decision_effect', {'severity': 'x' * 129, 'decision_effect': 'review'}),
                ('evidence_requirements', None), ('evidence_requirements', ['']), ('evidence_requirements', [])):
            invalid = json.loads(json.dumps(payload))
            if malformed is None:
                invalid['policy_metadata'].pop(field)
            else:
                invalid['policy_metadata'][field] = malformed
            with self.assertRaisesRegex(ValidationError, 'policy_metadata'):
                model.validate_policy_payload(invalid, require_policy_metadata=True)
        before = candidate.write_date
        difference = model.diff_candidate(candidate)
        self.assertEqual((difference['candidate_hash'], difference['active_hash']),
                         (candidate.payload_hash, active.payload_hash))
        self.assertIn('$.horizontal.classification.thresholds.strong_filename',
                      [change['path'] for change in difference['changes']])
        self.assertEqual(candidate.write_date, before)
        changed = json.loads(json.dumps(values, default=str))
        changed['payload']['horizontal']['classification']['thresholds']['strong_filename'] = .82
        with self.assertRaisesRegex(Exception, 'different content'):
            model.import_candidate(changed)
        changed = json.loads(json.dumps(values, default=str))
        changed['provenance']['source'] = 'different-governance-source'
        with self.assertRaisesRegex(Exception, 'governance metadata'):
            model.import_candidate(changed)
        equivalent = json.loads(json.dumps(values, default=str))
        equivalent['provenance']['captured_at'] = '2026-08-12T07:00:00+07:00'
        self.assertEqual(model.import_candidate(equivalent), candidate)
        for captured_at in ('not-a-timestamp', '2026-08-12T00:00:00'):
            malformed = json.loads(json.dumps(values, default=str))
            malformed.update(version=unique_fixture('CAPTURED-AT'))
            malformed['provenance']['captured_at'] = captured_at
            with self.assertRaisesRegex(Exception, 'timezone-aware ISO 8601'):
                model.import_candidate(malformed)
        for field, value in (
                ('citation', 'https://example.invalid/different-policy'),
                ('provenance', {'source': 'different-governance-source',
                                'captured_at': '2026-08-12T00:00:00Z'}),
                ('compliance_context', {**context, 'when': '2026-08-13'})):
            raced = json.loads(json.dumps(values, default=str))
            raced[field] = value
            with patch.object(type(model), 'search', autospec=True,
                              side_effect=[model.browse(), candidate]), patch.object(
                                  type(model), '_controlled_create', autospec=True,
                                  side_effect=UniqueViolation()):
                with self.assertRaisesRegex(Exception, 'governance metadata'):
                    model.import_candidate(raced)
        for citation in ('http://example.invalid/policy', 'https://user:pass@example.invalid/policy',
                         'https://example.invalid/policy?token=x', 'https://example.invalid/policy#part',
                         'https://example.invalid/policy\nforged'):
            with self.assertRaisesRegex(Exception, 'citation'):
                model.import_candidate({**values, 'version': unique_fixture('CITATION'),
                                        'citation': citation})

    def test_policy_impact_preview_is_deterministic_read_only_and_fails_closed(self):
        model = self.env['logistics.idp.policy.source'].with_user(self.policy_manager)
        active = model.search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)
        payload = json.loads(active.payload)
        payload['policy_metadata'] = {
            'source_publication_date': '2026-08-10', 'applicability_predicate': {'jurisdiction': 'VN'},
            'severity_decision_effect': {'severity': 'medium', 'decision_effect': 'review'},
            'evidence_requirements': ['source_document'],
        }
        payload['vertical']['packs']['vn_fdi_fta']['counterpart_rules'][0]['deadline_days'] += 1
        recorded_time = fields.Datetime.to_string(active.recorded_at).replace(' ', 'T') + 'Z'
        preview_date = fields.Date.to_string(active.recorded_at.date())
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'fixture'}, 'when': preview_date,
            'transaction_time': recorded_time, 'effective_time': recorded_time,
            'recorded_time': recorded_time,
            'evidence': [{'document_id': self.provenance_document.id, 'field': 'policy',
                          'source_kind': 'document', 'source_hash': self.provenance_document.content_hash,
                          'extraction_run_id': self.provenance_document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
        }
        candidate = model.import_candidate({
            'code': active.code, 'version': unique_fixture('PREVIEW'), 'company_id': self.env.company.id,
            'jurisdiction': 'VN', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/policy-preview',
            'provenance': {'source': 'fixture', 'captured_at': recorded_time},
            'effective_from': preview_date, 'payload': payload, 'compliance_context': context,
        })
        tracked = ['logistics.idp.case', 'logistics.idp.document', 'logistics.idp.extraction.run',
                   'logistics.idp.check.result', 'logistics.idp.evidence',
                   'logistics.idp.policy.decision', 'mail.activity', 'logistics.idp.policy.source']
        before = {name: self.env[name].sudo().search_count([]) for name in tracked}
        snapshot = {
            name: self.env[name].sudo().search([]).read(['write_date']) for name in tracked
        }
        first = model.preview_impact(candidate, preview_date, preview_date, 10000, context)
        second = model.preview_impact(candidate, preview_date, preview_date, 10000,
                                      json.loads(json.dumps(context)))
        self.assertEqual(first, second)
        self.assertEqual(first['candidate_hash'], candidate.payload_hash)
        self.assertEqual(first['active_hash'], active.payload_hash)
        self.assertEqual(list(first['counts']), [
            'affected', 'possibly_affected', 'not_affected', 'insufficient_context'])
        manifest_case = next(item for item in first['cases'] if item['id'] == self.provenance_document.case_id.id)
        manifest_document = next(item for item in manifest_case['documents']
                                 if item['id'] == self.provenance_document.id)
        self.assertEqual(manifest_case['company_id'], self.provenance_document.company_id.id)
        self.assertEqual(manifest_case['identity'], '%s:%s' % (
            self.provenance_document.case_id._name, self.provenance_document.case_id.id))
        self.assertEqual(manifest_document['document_type'], self.provenance_document.document_type)
        self.assertEqual(manifest_document['content_hash'], self.provenance_document.content_hash)
        self.assertEqual(manifest_document['current_run_payload_hash'], __import__('hashlib').sha256(
            self.provenance_document.current_run_id.payload.encode()).hexdigest())
        dimensions = next(item for item in first['results']
                          if item['case_id'] == self.provenance_document.case_id.id)['dimensions']
        self.assertEqual(dimensions['open_cases']['outcome'], next(
            item for item in first['results'] if item['case_id'] == self.provenance_document.case_id.id)['outcome'])
        self.assertEqual(dimensions['products_materials_and_hs_codes'], {
            'outcome': 'insufficient_context', 'reasons': ['entity_model_unavailable'],
            'evidence_references': []})
        hashed_output = {'counts': first['counts'], 'results': first['results']}
        self.assertEqual(first['output_hash'], __import__('hashlib').sha256(
            json.dumps(hashed_output, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode()).hexdigest())
        mutated_output = json.loads(json.dumps(hashed_output))
        mutated_output['results'][0]['dimensions']['open_cases']['outcome'] = 'tampered'
        self.assertNotEqual(first['output_hash'], __import__('hashlib').sha256(
            json.dumps(mutated_output, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode()).hexdigest())
        audit = model.audit_effective(self.env.company, 'VN', candidate.regime, preview_date,
                                     active.recorded_at, code=active.code)
        self.assertIn(active.id, audit['policy_ids'])
        self.assertEqual(audit['legal_effective_date'], preview_date)
        with self.assertRaisesRegex(Exception, 'legal effective date'):
            model.audit_effective(self.env.company, 'VN', candidate.regime, None,
                                  active.recorded_at, code=active.code)
        test_enable = tools.config['test_enable']
        try:
            tools.config['test_enable'] = True
            simulation = model.simulate_scenario(
                candidate, preview_date, preview_date, 10000, context,
                {'id': candidate.id, 'payload_hash': candidate.payload_hash})
        finally:
            tools.config['test_enable'] = test_enable
        self.assertEqual(simulation['simulation'], {
            'mode': 'non_production', 'read_only': True, 'legal_authority': False,
            'disclaimer': 'Hypothetical simulation; no legal authority.'})
        with self.assertRaisesRegex(Exception, 'explicit hypothetical candidate'):
            model.simulate_scenario(candidate, preview_date, preview_date, 10000, context, {})
        try:
            tools.config['test_enable'] = False
            with self.assertRaisesRegex(Exception, 'non-production only'):
                model.simulate_scenario(candidate, preview_date, preview_date, 10000, context,
                                        {'id': candidate.id, 'payload_hash': candidate.payload_hash})
        finally:
            tools.config['test_enable'] = test_enable
        for item in (manifest_case, manifest_document, manifest_document['current_run']):
            self.assertRegex(item['write_date'], r'^\d{4}-\d{2}-\d{2}')
        self.assertEqual(before, {name: self.env[name].sudo().search_count([]) for name in tracked})
        self.assertEqual(snapshot, {
            name: self.env[name].sudo().search([]).read(['write_date']) for name in tracked
        })
        with self.assertRaisesRegex(Exception, 'explicit cutoff'):
            model.preview_impact(candidate, None, preview_date, 100, context)
        with self.assertRaisesRegex(Exception, 'company'):
            model.preview_impact(candidate, preview_date, preview_date, 100,
                                 {**context, 'company_id': False})
        with self.assertRaisesRegex(Exception, 'record limit'):
            model.preview_impact(candidate, preview_date, preview_date, 0, context)
        with self.assertRaisesRegex(Exception, 'draft policy candidate'):
            model.preview_impact(active, preview_date, preview_date, 100, context)

        document = self.provenance_document
        run = document.current_run_id
        successor = self.env['logistics.idp.extraction.run'].create({
            'case_id': run.case_id.id, 'document_id': document.id, 'provider': run.provider,
            'model_version': run.model_version, 'schema_version': run.schema_version,
            'prompt_version': run.prompt_version, 'started_at': run.started_at,
            'completed_at': fields.Datetime.now(), 'status': run.status,
            'payload': json.loads(run.payload) | {'preview_successor': True},
        })
        mutations = [
            (document, 'document_type', 'invoice' if document.document_type != 'invoice' else 'packing_list'),
            (document, 'current_run_id', successor.id),
            (document.case_id, 'write_date', document.case_id.write_date - __import__('datetime').timedelta(seconds=1)),
            (document, 'write_date', document.write_date - __import__('datetime').timedelta(seconds=1)),
        ]
        for record, field_name, changed in mutations:
            original = record[field_name]
            original = original.id if hasattr(original, 'id') else original
            self.env.cr.execute('UPDATE %s SET %s = %%s WHERE id = %%s' % (
                record._table, field_name), [changed, record.id])
            record.invalidate_recordset([field_name])
            mutated = model.preview_impact(candidate, preview_date, preview_date, 10000, context)
            self.assertNotEqual(mutated['input_hash'], first['input_hash'], field_name)
            self.assertEqual(mutated['output_hash'], first['output_hash'], field_name)
            self.env.cr.execute('UPDATE %s SET %s = %%s WHERE id = %%s' % (
                record._table, field_name), [original, record.id])
            record.invalidate_recordset([field_name])

    def test_impact_preview_is_pack_family_agnostic(self):
        model = self.env['logistics.idp.policy.source'].with_user(self.policy_manager)
        base = model.search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)
        payload = json.loads(base.payload)
        duty_pack = json.loads(json.dumps(payload['vertical']['packs']['vn_fdi_fta']))
        for rule in duty_pack['counterpart_rules']:
            rule['code'] = '%s_TARIFF' % rule['code']
            rule['source'] = 'TRADE_COMPLIANCE_TARIFF_DEMO'
            rule['version'] = '2026.4'
            rule['test_ids'] = ['UAT-40']
            rule['deadline_days'] += 5
        active_payload = json.loads(json.dumps(payload))
        active_payload['vertical']['packs']['tariff_duty_demo'] = duty_pack
        family_code = unique_fixture('TARIFF-FAMILY')
        active_source = model.with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': family_code, 'version': '2026.4', 'company_id': self.env.company.id,
            'jurisdiction': 'VN', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/policy-preview',
            'provenance': '{"verification":"verified"}',
            'effective_from': '2026-01-01', 'state': 'active',
            'payload': json.dumps(active_payload, ensure_ascii=False),
        })
        self.assertEqual(active_source.state, 'active')
        candidate_payload = json.loads(json.dumps(active_payload))
        candidate_payload['vertical']['pack'] = 'tariff_duty_demo'
        candidate_payload['vertical']['packs'] = {'tariff_duty_demo': duty_pack}
        candidate_payload['policy_metadata'] = {
            'source_publication_date': '2026-08-10', 'applicability_predicate': {'jurisdiction': 'VN'},
            'severity_decision_effect': {'severity': 'medium', 'decision_effect': 'review'},
            'evidence_requirements': ['source_document'],
        }
        recorded_time = fields.Datetime.to_string(active_source.recorded_at).replace(' ', 'T') + 'Z'
        preview_date = fields.Date.to_string(active_source.recorded_at.date())
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'fixture'}, 'when': preview_date,
            'transaction_time': recorded_time, 'effective_time': recorded_time,
            'recorded_time': recorded_time,
            'evidence': [{'document_id': self.provenance_document.id, 'field': 'policy',
                          'source_kind': 'document', 'source_hash': self.provenance_document.content_hash,
                          'extraction_run_id': self.provenance_document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
        }
        candidate = model.import_candidate({
            'code': family_code, 'version': unique_fixture('TARIFF-CANDIDATE'),
            'company_id': self.env.company.id, 'jurisdiction': 'VN', 'regime': 'ALL',
            'source_tier': 'authoritative_tier_1', 'citation': 'https://example.invalid/policy-preview',
            'provenance': {'source': 'fixture', 'captured_at': recorded_time},
            'effective_from': preview_date, 'payload': candidate_payload, 'compliance_context': context,
        })
        preview = model.preview_impact(candidate, preview_date, preview_date, 10000, context)
        self.assertEqual(preview['candidate_hash'], candidate.payload_hash)
        self.assertEqual(preview['active_hash'], active_source.payload_hash)
        self.assertEqual(list(preview['counts']), [
            'affected', 'possibly_affected', 'not_affected', 'insufficient_context'])
        self.assertEqual(preview['candidate_id'], candidate.id)
        self.assertEqual(preview['active_id'], active_source.id)
        self.assertTrue(preview['results'])
        validated = self.env['logistics.idp.policy.source'].validate_policy_payload(
            active_source.payload, 'trade_compliance', 'tariff_duty_demo', 'VN', 'ALL')
        self.assertEqual(validated['vertical']['packs']['tariff_duty_demo'],
                         duty_pack)

    def test_applicability_predicate_selectors_are_deterministic(self):
        model = self.env['logistics.idp.policy.source']
        base = model.search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)
        payload = json.loads(base.payload)

        def with_predicate(predicate):
            candidate_payload = json.loads(json.dumps(payload))
            candidate_payload['policy_metadata'] = {
                'source_publication_date': '2026-08-10', 'applicability_predicate': predicate,
                'severity_decision_effect': {'severity': 'medium', 'decision_effect': 'review'},
                'evidence_requirements': ['source_document'],
            }
            return candidate_payload

        case = self.env['logistics.idp.case'].with_user(self.policy_manager).create({
            'name': 'APPLICABILITY', 'source_system': 'fixture', 'source_key': unique_fixture('APPL'),
            'source_version': '1', 'provenance': 'fixture', 'effective_date': '2026-08-12',
            'supplier_reference': 'Acme Trading Company', 'po_reference': unique_fixture('PO-APPL'),
        })
        self.assertEqual(model.evaluate_applicability(payload, case),
                         {'verdict': 'matched', 'reasons': ['no_applicability_predicate']})
        self.assertEqual(model.evaluate_applicability(with_predicate({'jurisdiction': 'VN'}), case),
                         {'verdict': 'matched', 'reasons': ['jurisdiction_matched']})
        self.assertEqual(model.evaluate_applicability(with_predicate({'jurisdiction': 'JP'}), case),
                         {'verdict': 'not_matched', 'reasons': ['jurisdiction_mismatch']})
        self.assertEqual(model.evaluate_applicability(with_predicate({'parties': ['acme']}), case),
                         {'verdict': 'matched', 'reasons': ['parties_matched']})
        self.assertEqual(model.evaluate_applicability(with_predicate({'parties': ['NOMATCH-XYZ']}), case),
                         {'verdict': 'not_matched', 'reasons': ['party_not_matched']})
        self.assertEqual(model.evaluate_applicability(with_predicate({'hs_codes': ['8471']}), case),
                         {'verdict': 'indeterminate', 'reasons': ['hs_facts_unavailable']})
        self.env['logistics.idp.po.snapshot'].with_user(self.policy_manager).create({
            'company_id': self.env.company.id, 'po_reference': case.po_reference,
            'snapshot_date': '2026-08-12', 'source_system': 'fixture',
            'source_key': unique_fixture('PO-SNAP'), 'source_version': '1',
            'provenance': 'fixture', 'payload': {
                'lines': [{'line_key': '1', 'material_code': 'MAT-1', 'hs_code': '8471.30'}]},
        })
        self.assertEqual(model.evaluate_applicability(with_predicate({'hs_codes': ['8471']}), case),
                         {'verdict': 'matched', 'reasons': ['hs_codes_matched']})
        self.assertEqual(model.evaluate_applicability(with_predicate({'hs_codes': ['9999']}), case),
                         {'verdict': 'not_matched', 'reasons': ['hs_not_matched']})
        self.assertEqual(model.evaluate_applicability(with_predicate({'regimes': ['E13']}), case),
                         {'verdict': 'indeterminate', 'reasons': ['regime_facts_unavailable']})
        with self.assertRaisesRegex(ValidationError, 'unsupported selectors'):
            model.validate_policy_payload(
                with_predicate({'origin': ['CN']}), require_policy_metadata=True)

    def test_impact_preview_applicability_selectors_gate_cases(self):
        model = self.env['logistics.idp.policy.source'].with_user(self.policy_manager)
        active = model.search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)
        payload = json.loads(active.payload)
        payload['policy_metadata'] = {
            'source_publication_date': '2026-08-10',
            'applicability_predicate': {'parties': ['NOMATCH-XYZ']},
            'severity_decision_effect': {'severity': 'medium', 'decision_effect': 'review'},
            'evidence_requirements': ['source_document'],
        }
        preview_date = fields.Date.to_string(active.recorded_at.date())
        case = self.env['logistics.idp.case'].with_user(self.policy_manager).create({
            'name': 'APPL-WIRE', 'source_system': 'fixture', 'source_key': unique_fixture('APPL-WIRE'),
            'source_version': '1', 'provenance': 'fixture', 'effective_date': preview_date,
            'supplier_reference': 'Acme Trading Company',
        })
        recorded_time = fields.Datetime.to_string(active.recorded_at).replace(' ', 'T') + 'Z'
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'fixture'}, 'when': preview_date,
            'transaction_time': recorded_time, 'effective_time': recorded_time,
            'recorded_time': recorded_time,
            'evidence': [{'document_id': self.provenance_document.id, 'field': 'policy',
                          'source_kind': 'document', 'source_hash': self.provenance_document.content_hash,
                          'extraction_run_id': self.provenance_document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
        }
        candidate = model.import_candidate({
            'code': active.code, 'version': unique_fixture('APPL-CAND'),
            'company_id': self.env.company.id, 'jurisdiction': 'VN', 'regime': 'ALL',
            'source_tier': 'authoritative_tier_1', 'citation': 'https://example.invalid/policy-preview',
            'provenance': {'source': 'fixture', 'captured_at': recorded_time},
            'effective_from': preview_date, 'payload': payload, 'compliance_context': context,
        })
        preview = model.preview_impact(candidate, preview_date, preview_date, 10000, context)
        by_case = {item['case_id']: item for item in preview['results']}
        self.assertEqual(by_case[case.id]['outcome'], 'not_affected')
        self.assertEqual(by_case[case.id]['reasons'],
                         ['applicability_not_matched', 'party_not_matched'])

    def test_resilience_metrics_are_deterministic_and_scoped(self):
        model = self.env['logistics.idp.policy.source']
        as_of = fields.Datetime.now().replace(tzinfo=timezone.utc)
        metrics = model.compute_resilience_metrics(self.env.company, as_of)
        self.assertEqual(model.compute_resilience_metrics(self.env.company, as_of), metrics)
        self.assertEqual(metrics['schema_version'], '1.0')
        self.assertEqual(set(metrics), {
            'schema_version', 'generated_at', 'sources', 'detection_latency_days',
            'activation_latency_days', 'open_impact_assessments', 'unresolved_stale_exposures'})
        expected_sources = model.sudo().search([('company_id', '=', self.env.company.id)])
        self.assertEqual(metrics['sources']['total'], len(expected_sources))
        self.assertEqual(
            metrics['sources']['fresh'] + metrics['sources']['stale'] + metrics['sources']['unknown'],
            len(expected_sources))
        for latency in (metrics['detection_latency_days'], metrics['activation_latency_days']):
            self.assertEqual(set(latency), {'count', 'mean', 'max', 'min'})
            self.assertGreaterEqual(latency['count'], 0)
        decisions = self.env['logistics.idp.policy.decision'].sudo().search(
            [('case_id.company_id', '=', self.env.company.id)])
        self.assertEqual(metrics['open_impact_assessments']['total'], len(decisions))
        self.assertEqual(
            len(metrics['unresolved_stale_exposures']), metrics['sources']['stale'])
        empty_company = self.env['res.company'].create({'name': unique_fixture('KPI-EMPTY')})
        self.assertEqual(
            model.compute_resilience_metrics(empty_company, as_of)['sources']['total'], 0)

    def test_regulatory_source_freshness_fails_safe(self):
        model = self.env['logistics.idp.policy.source']
        active = model.search([('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE')], limit=1)
        source = model.with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': unique_fixture('STALE-SOURCE'), 'version': '1', 'company_id': self.env.company.id,
            'jurisdiction': 'VN', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/g5', 'provenance': '{"verification":"verified"}',
            'effective_from': '2026-01-01', 'payload': active.payload,
            'last_successful_sync_at': '2026-08-10 00:00:00', 'expected_refresh_hours': 24,
            'stale_after_hours': 48, 'stale_disposition': 'review',
        })
        result = source.evaluate_freshness(
            self.provenance_document.case_id,
            __import__('datetime').datetime(2026, 8, 12, tzinfo=__import__('datetime').timezone.utc),
        )
        self.assertEqual((result.code, result.actual, result.verdict),
                         ('REGULATORY_SOURCE_FRESHNESS', 'review', 'review'))
        self.assertEqual(source.evaluate_freshness(
            self.provenance_document.case_id,
            __import__('datetime').datetime(2026, 8, 12, tzinfo=__import__('datetime').timezone.utc),
        ), result)

    def test_external_candidate_adapter_is_fixed_deterministic_and_fail_closed(self):
        model = self.env['logistics.idp.policy.source'].with_user(self.policy_manager)
        with self.assertRaisesRegex(Exception, 'registry key'):
            model.fetch_external_candidates('arbitrary', {'keyword': 'hải quan'})
        with self.assertRaisesRegex(Exception, 'GET only'):
            model.fetch_external_candidates('traluat_documents', {'keyword': 'hải quan'}, 'POST')
        with self.assertRaisesRegex(Exception, 'unapproved fields'):
            model.fetch_external_candidates('traluat_documents', {'keyword': 'x', 'url': 'https://evil.invalid'})
        pages = [
            {'data': [{'id': 2, 'title': 'B'}, {'id': 1, 'title': 'A'}], 'meta': {'nextPage': 2}},
            {'data': [{'id': 1, 'title': 'A'}], 'meta': {}},
        ]
        with patch('odoo.addons.insilos_logistics_idp.services.legal_candidate_adapter._request',
                   side_effect=[json.dumps(page).encode() for page in pages]):
            first = fetch_candidates('traluat_documents', {'keyword': 'hải quan'}, now=fields.Datetime.to_datetime('2026-08-12 00:00:00').replace(tzinfo=__import__('datetime').timezone.utc))
        with patch('odoo.addons.insilos_logistics_idp.services.legal_candidate_adapter._request',
                   side_effect=[json.dumps(page).encode() for page in pages]):
            second = fetch_candidates('traluat_documents', {'keyword': 'hải quan'}, now=fields.Datetime.to_datetime('2026-08-12 00:00:00').replace(tzinfo=__import__('datetime').timezone.utc))
        self.assertEqual(first, second)
        self.assertEqual([item['source_key'] for item in first['candidates']], ['1', '2'])
        self.assertEqual((first['source_tier'], first['legal_authority'], first['verification'],
                          first['verdict'], first['activation_allowed']),
                         ('early_warning_tier_4', False, 'unverified', 'REVIEW', False))
        self.assertEqual(len(first['raw_response_sha256']), 2)
        for key in ('citation_clean_url', 'license_terms', 'retention_terms', 'content_owner',
                    'independent_oracle_status', 'request_fingerprint'):
            self.assertTrue(first[key])

    def test_external_candidate_adapter_caps_pagination_and_conflicts_review(self):
        page = {'data': [{'id': 1, 'version': '1', 'value': 'A'}], 'meta': {'nextPage': 2}}
        responses = []
        for number in range(1, MAX_PAGES + 1):
            responses.append(json.dumps({**page, 'data': [{'id': number, 'value': number}],
                                         'meta': {'nextPage': number + 1}}).encode())
        with patch('odoo.addons.insilos_logistics_idp.services.legal_candidate_adapter._request', side_effect=responses):
            capped = fetch_candidates('traluat_documents', {'keyword': 'x'})
        self.assertLessEqual(len(capped['candidates']), min(MAX_PAGES, MAX_RESULTS))
        conflict = [json.dumps({'data': [{'id': 1, 'value': 'A'}, {'id': 1, 'value': 'B'}]}).encode()]
        with patch('odoo.addons.insilos_logistics_idp.services.legal_candidate_adapter._request', side_effect=conflict):
            result = fetch_candidates('traluat_documents', {'keyword': 'x'})
        self.assertEqual((result['error_code'], result['verdict'], result['activation_allowed']),
                         ('conflicting_source_version_hash', 'REVIEW', False))

    def test_policy_candidate_import_rejects_trust_boundary_failures(self):
        model = self.env['logistics.idp.policy.source'].with_user(self.policy_manager)
        with self.assertRaisesRegex(Exception, 'JSON object'):
            model.import_candidate([])
        with self.assertRaisesRegex(Exception, 'unknown fields'):
            model.import_candidate({'unexpected': True})
        with self.assertRaisesRegex(Exception, '1 MiB'):
            model.import_candidate({'padding': 'x' * (1024 * 1024)})
        active = self.env['logistics.idp.policy.source'].search([], limit=1)
        base = {
            'code': 'INVALID', 'version': '1', 'jurisdiction': 'VN', 'regime': 'ALL',
            'source_tier': 'official', 'citation': 'fixture',
            'provenance': {'source': 'fixture', 'captured_at': '2026-08-12T00:00:00Z'},
            'effective_from': '2020-01-01', 'effective_to': '2020-01-02',
            'payload': json.loads(active.payload), 'compliance_context': {},
        }
        with self.assertRaisesRegex(Exception, 'Unknown compliance authority'):
            model.import_candidate(base)
        with self.assertRaisesRegex(Exception, 'Stale policy'):
            model.import_candidate({**base, 'source_tier': 'customer_reference',
                                    'citation': 'LAW:STALE-POLICY'})

    def test_extraction_template_selection_hash_and_version(self):
        policy = {'horizontal': {'extraction': {'templates': {
            'default': {'version': 'default-v1', 'schema_version': '9',
                        'prompt': 'Extract {document_type}. Contract: {schema}.'},
            'packing_list': {'version': 'packing-v2', 'schema_version': '10',
                             'prompt': 'Packing {document_type}. Contract: {schema}.'},
        }}}}
        selected = extraction_template_contract('packing_list', policy)
        fallback = extraction_template_contract('purchase_order', policy)
        self.assertEqual((selected['version'], selected['schema_version']), ('packing-v2', '10'))
        self.assertEqual(fallback['version'], 'default-v1')
        self.assertEqual(selected['hash'], extraction_template_contract('packing_list', policy)['hash'])
        changed = json.loads(json.dumps(policy))
        changed['horizontal']['extraction']['templates']['packing_list']['version'] = 'packing-v3'
        self.assertNotEqual(selected['hash'], extraction_template_contract('packing_list', changed)['hash'])
        with self.assertRaisesRegex(ValueError, 'invalid extraction template contract'):
            extraction_template_contract('packing_list', {'horizontal': {'extraction': {'templates': {
                'packing_list': {'version': 'bad', 'schema_version': '9', 'prompt': 'missing placeholders'},
            }}}})

    def test_usd_vnd_taxable_value_requires_explicit_effective_fx(self):
        evaluator = self.env['logistics.idp.case'].evaluate_taxable_value
        result = evaluator('12.50', 'USD', 'VND', {
            'rate': '25400', 'effective_date': '2026-01-02',
            'base_currency': 'USD', 'quote_currency': 'VND',
        })
        self.assertEqual((result['verdict'], result['invoice_value'], result['invoice_currency'],
                          result['taxable_value'], result['taxable_currency']),
                         ('pass', '12.50', 'USD', '317500.00', 'VND'))
        self.assertEqual(result['effective_fx'], {
            'rate': '25400', 'effective_date': '2026-01-02',
            'base_currency': 'USD', 'quote_currency': 'VND',
        })
        self.assertEqual(evaluator('12.50', 'USD', 'VND')['verdict'], 'review')
        self.assertEqual(evaluator('12.50', 'USD', 'VND', {
            'rate': '25400', 'effective_date': '2026-01-02',
            'base_currency': 'VND', 'quote_currency': 'USD',
        })['verdict'], 'review')

    def test_counterpart_deadline_boundaries_and_configuration(self):
        evaluator = self.env['logistics.idp.case'].evaluate_counterpart_deadline
        rule = {'deadline_days': 10, 'warning_offsets': [1]}
        self.assertEqual(evaluator('2026-01-01', '2026-01-09', rule)['status'], 'pending')
        self.assertEqual(evaluator('2026-01-01', '2026-01-10', rule)['status'], 'warning')
        day_10 = evaluator('2026-01-01', '2026-01-11', rule)
        self.assertEqual((day_10['status'], fields.Date.to_string(day_10['deadline'])),
                         ('overdue', '2026-01-11'))
        self.assertEqual(evaluator('2026-01-01', '2026-01-06', {**rule, 'deadline_days': 5})['status'], 'overdue')
        self.assertEqual(evaluator('2026-01-01', '2026-01-12', rule, True)['status'], 'satisfied')

    def test_directional_counterpart_runtime_is_idempotent_and_rule_scoped(self):
        baseline = self.env.ref(
            'insilos_logistics_idp.policy_trade_compliance_vn_reference_2026_2')
        self.env['logistics.idp.policy.source'].with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': 'COUNTERPART_TEST_%s' % self.env.company.id,
            'version': '1',
            'company_id': self.env.company.id,
            'jurisdiction': 'VN',
            'regime': 'ALL',
            'source_tier': 'customer_reference',
            'citation': 'fixture',
            'effective_from': '2026-01-01',
            'state': 'retired',
            'payload': baseline.payload,
        })
        mail_count = self.env['mail.mail'].sudo().search_count([])
        operator = new_test_user(
            self.env, login='counterpart-runtime-operator', context={'no_reset_password': True},
            groups='insilos_logistics_idp.group_logistics_operator')
        self.assertEqual(self.env['mail.mail'].sudo().search_count([]), mail_count)
        cases = self.env['logistics.idp.case'].with_user(operator)
        documents = self.env['logistics.idp.document'].with_user(operator)

        def make_case(key, role, document_date='2026-01-01'):
            case = cases.create({
                'name': key, 'source_system': 'fixture', 'source_key': key,
                'source_version': '1', 'provenance': 'fixture', 'effective_date': '2026-01-01',
            })
            payload = {'document_date': document_date, 'declaration_number': key, 'lines': [{}]}
            if role == 'export_declaration_final':
                payload['regime'] = 'E13'
            content = json.dumps({'document_type': role, 'confidence': 1, 'payload': payload}).encode()
            document = documents._intake_synthetic_content(case, content, 'application/json', {'filename': key + '.json'})
            document.sudo().write({'document_type': role})
            return case

        export_case = make_case('EXPORT-TRIGGER', 'export_declaration_final')
        unrelated = self.env['logistics.idp.exception'].create({
            'case_id': export_case.id, 'exception_type': 'policy', 'severity': 'low'})
        first = export_case.evaluate_compliance_deadlines('2026-01-10')
        retry = export_case.evaluate_compliance_deadlines('2026-01-10')
        self.assertEqual(first, retry)
        self.assertEqual(len(first), 1)
        self.assertEqual(
            export_case.check_result_ids.filtered(
                lambda check: check.code.startswith('EXPORT_REQUIRES_IMPORT')).mapped('code'),
            ['EXPORT_REQUIRES_IMPORT_WARNING'],
        )
        snapshot = json.loads(first.payload)
        self.assertEqual(snapshot['audit_input']['evaluation_cutoff'], '2026-01-10')
        self.assertEqual(snapshot['audit_input']['policy']['payload_hash'], first.policy_source_id.payload_hash)
        self.assertEqual(snapshot['rule_version'], '2026.3')
        self.assertEqual(len(first.audit_input_hash), 64)
        self.assertFalse(snapshot['legal_authority'])
        self.assertEqual((first.verdict, snapshot['disposition']), ('review', 'customer_policy'))
        counterpart_activities = export_case.activity_ids.filtered(
            lambda activity: (activity.summary or '').startswith('EXPORT_REQUIRES_IMPORT_'))
        self.assertEqual(len(counterpart_activities), 1)
        export_case.evaluate_compliance_deadlines('2026-01-11')
        self.assertEqual(set(export_case.check_result_ids.filtered(
            lambda check: check.code.startswith('EXPORT_REQUIRES_IMPORT_')).mapped('code')), {
            'EXPORT_REQUIRES_IMPORT_WARNING', 'EXPORT_REQUIRES_IMPORT_OVERDUE'})
        self.assertEqual(len(counterpart_activities), 1)
        self.assertEqual(unrelated.state, 'open')

        import_case = make_case('IMPORT-TRIGGER', 'import_declaration')
        import_case.evaluate_compliance_deadlines('2026-01-11')
        self.assertEqual(import_case.check_result_ids.filtered(
            lambda check: check.code.startswith('IMPORT_REQUIRES_EXPORT_')).mapped('code'), ['IMPORT_REQUIRES_EXPORT_OVERDUE'])
        counterpart = json.dumps({'document_type': 'export_declaration_final', 'confidence': 1,
                                  'payload': {'document_date': '2026-01-02'}}).encode()
        counterpart_document = documents.intake_content(
            import_case, counterpart, 'application/json', {'filename': 'counterpart.json'})
        counterpart_document.sudo().write({'document_type': 'export_declaration_final'})
        import_case.evaluate_compliance_deadlines('2026-01-12')
        self.assertEqual(len(import_case.check_result_ids.filtered(
            lambda check: check.code.startswith('IMPORT_REQUIRES_EXPORT_'))), 1)
        self.assertFalse(import_case.activity_ids.filtered(
            lambda activity: (activity.summary or '').startswith('IMPORT_REQUIRES_EXPORT_')))
        self.assertEqual(self.env['logistics.idp.exception'].search_count([
            ('case_id', '=', import_case.id), ('state', 'in', ('open', 'waiting')),
            ('message_ids.body', 'ilike', '[IMPORT_REQUIRES_EXPORT]')]), 0)

        missing_date = make_case('MISSING-DATE', 'export_declaration_final', None)
        insufficient = missing_date.evaluate_compliance_deadlines('2026-01-11')
        self.assertEqual((insufficient.verdict, insufficient.code),
                         ('review', 'EXPORT_REQUIRES_IMPORT_INSUFFICIENT_CONTEXT'))
        self.assertEqual(json.loads(insufficient.payload)['missing_critical'], ['when'])

    def test_sla004_counterpart_alert_intents_are_idempotent_cadenced_and_suppressed(self):
        operator = new_test_user(
            self.env, login=unique_fixture('sla004-operator'), context={'no_reset_password': True},
            groups='insilos_logistics_idp.group_logistics_operator')
        cases = self.env['logistics.idp.case'].with_user(operator)
        documents = self.env['logistics.idp.document'].with_user(operator)

        def make_case(key):
            case = cases.create({
                'name': key, 'source_system': 'fixture', 'source_key': key, 'source_version': '1',
                'provenance': 'fixture', 'effective_date': '2026-01-01'})
            content = json.dumps({'document_type': 'export_declaration_final', 'confidence': 1,
                                  'payload': {'document_date': '2026-01-01', 'declaration_number': key,
                                              'regime': 'E13', 'lines': [{}]}}).encode()
            documents._intake_synthetic_content(case, content, 'application/json', {'filename': key + '.json'}).sudo().write({
                'document_type': 'export_declaration_final'})
            return case

        case = make_case('SLA004')
        suppressed = make_case('SLA004-NO-SEND')
        suppressed.sudo().write({'state': 'completed'})
        mail_count = self.env['mail.mail'].sudo().search_count([('state', '=', 'sent')])
        first_check = case.evaluate_compliance_deadlines('2026-01-10')
        retry_check = case.evaluate_compliance_deadlines('2026-01-10')
        self.assertEqual(first_check, retry_check)
        intents = case.evidence_ids.filtered(lambda item: item.category == 'counterpart_alert_intent')
        self.assertEqual(len(intents), 1)
        first = json.loads(intents.payload)
        self.assertEqual((first['alert_status'], first['cutoff'], first['cadence_slot'], first['send_enabled']),
                         ('warning', '2026-01-10', 0, False))
        case.evaluate_compliance_deadlines('2026-01-11')
        case.evaluate_compliance_deadlines('2026-01-12')
        case.evaluate_compliance_deadlines('2026-01-12')
        self.assertEqual(len(case.evidence_ids.filtered(lambda item: item.category == 'counterpart_alert_intent')), 3)
        case.evaluate_compliance_deadlines('2026-01-14')
        self.assertEqual(len(case.evidence_ids.filtered(lambda item: item.category == 'counterpart_alert_intent')), 3)
        suppressed.evaluate_compliance_deadlines('2026-01-10')
        self.assertFalse(suppressed.evidence_ids.filtered(lambda item: item.category == 'counterpart_alert_intent'))
        self.assertEqual(self.env['mail.mail'].sudo().search_count([('state', '=', 'sent')]), mail_count)

    def test_policy_selector_fails_closed_on_invalid_or_overlapping_pack(self):
        model = self.env['logistics.idp.policy.source']
        baseline = self.env.ref('insilos_logistics_idp.policy_trade_compliance_vn_reference_2026_2')
        invalid = json.loads(baseline.payload)
        invalid['schema_version'] = 'invalid'
        policy = model.with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': 'INVALID_SELECTED_%s' % self.env.company.id, 'version': '1',
            'company_id': self.env.company.id, 'jurisdiction': 'ZZ', 'regime': 'ALL',
            'source_tier': 'customer_reference', 'citation': 'fixture',
            'effective_from': '2026-01-01', 'state': 'active', 'payload': invalid,
        })
        with self.assertRaisesRegex(Exception, 'Invalid horizontal/vertical/overlays'):
            model.select_effective_pack(
                self.env.company, 'trade_compliance', 'vn_fdi_fta', 'ZZ', 'ALL', '2026-01-01')
        second = model.with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': 'OVERLAP_SELECTED_%s' % self.env.company.id, 'version': '1',
            'company_id': self.env.company.id, 'jurisdiction': 'ZZ', 'regime': 'ALL',
            'source_tier': 'customer_reference', 'citation': 'fixture',
            'effective_from': '2026-01-01', 'state': 'active', 'payload': baseline.payload,
        })
        with self.assertRaisesRegex(Exception, 'Overlapping active policy packs'):
            model.select_effective_pack(
                self.env.company, 'trade_compliance', 'vn_fdi_fta', 'ZZ', 'ALL', '2026-01-01')
        self.assertEqual((policy.state, second.state), ('active', 'active'))

    def test_export_controls_contract_and_fail_closed_evaluator(self):
        model = self.env['logistics.idp.policy.source']
        baseline = json.loads(self.env['logistics.idp.policy.source'].search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1).payload)
        canonical_fields = {
            'origin_country': 'VN', 'export_country': 'VN', 'destination_country': 'US',
            'import_country': 'US', 'transit_countries': ['SG'], 'transshipment_countries': ['MY'],
            'end_user': 'fixture-user', 'end_use': 'fixture-use', 'control_classification': 'EAR99',
            'license_reference': 'LIC-1', 'license_valid_from': '2026-01-01',
            'license_valid_to': '2026-12-31',
        }
        overlay = {
            'enabled': True, 'jurisdiction': 'VN', 'required_fields': sorted(canonical_fields),
            'selectors': {key: (['US'] if key == 'destination_countries' else []) for key in (
                'destination_countries', 'export_countries', 'origin_countries',
                'transit_countries', 'transshipment_countries')},
            'rules': [{'code': 'FIXTURE-RULE', 'required_fields': ['destination_country']}],
            'missing_context_verdict': 'REVIEW', 'unknown_rule_verdict': 'REVIEW',
            'no_pack_verdict': 'NOT_APPLICABLE',
        }
        configured = json.loads(json.dumps(baseline))
        configured['overlays']['export_controls'] = overlay
        self.assertTrue(model.validate_policy_payload(configured, 'trade_compliance', 'vn_fdi_fta', 'VN', 'ALL'))
        evaluator = model.evaluate_export_controls
        self.assertEqual(evaluator(baseline)['verdict'], 'NOT_APPLICABLE')
        disabled = json.loads(json.dumps(configured))
        disabled['overlays']['export_controls']['enabled'] = False
        self.assertEqual(evaluator(disabled)['verdict'], 'NOT_APPLICABLE')
        missing_destination = json.loads(json.dumps(configured))
        missing_destination['document'] = {}
        self.assertEqual(evaluator(missing_destination)['verdict'], 'REVIEW')
        mismatch = json.loads(json.dumps(configured))
        mismatch['document'] = {'destination_country': 'JP'}
        self.assertEqual(evaluator(mismatch)['verdict'], 'NOT_APPLICABLE')
        matched = json.loads(json.dumps(configured))
        matched['document'] = canonical_fields
        first = evaluator(matched, self.env['logistics.idp.case'].browse(0))
        second = evaluator(matched, self.env['logistics.idp.case'].browse(0))
        self.assertEqual(first['verdict'], 'REVIEW')
        self.assertNotIn(first['verdict'], ('PASS', 'BLOCK'))
        self.assertEqual(first['audit_input_hash'], second['audit_input_hash'])
        self.assertRegex(first['audit_input_hash'], '^[0-9a-f]{64}$')
        invalid = json.loads(json.dumps(configured))
        invalid['overlays']['export_controls']['required_fields'] = ['not_canonical']
        with self.assertRaisesRegex(Exception, 'export_controls.required_fields'):
            model.validate_policy_payload(invalid, 'trade_compliance', 'vn_fdi_fta', 'VN', 'ALL')

    def test_policy_validation_and_runtime_fallback(self):
        model = self.env['logistics.idp.policy.source']
        with self.assertRaisesRegex(Exception, 'Invalid horizontal/vertical/overlays'):
            model.validate_policy_payload({'schema_version': '1'})
        baseline = json.loads(self.env['logistics.idp.policy.source'].search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1).payload)
        invalid_regex = json.loads(json.dumps(baseline))
        invalid_regex['vertical']['packs']['vn_fdi_fta']['classification']['aliases']['purchase_order'] = ['(a+)+$']
        with self.assertRaisesRegex(Exception, 'classification.aliases'):
            model.validate_policy_payload(invalid_regex, 'trade_compliance', 'vn_fdi_fta', 'VN', 'ALL')
        unknown_target = json.loads(json.dumps(baseline))
        unknown_target['vertical']['packs']['vn_fdi_fta']['classification']['aliases']['arbitrary'] = ['safe']
        with self.assertRaisesRegex(Exception, 'classification.aliases'):
            model.validate_policy_payload(unknown_target, 'trade_compliance', 'vn_fdi_fta', 'VN', 'ALL')
        changed = json.loads(json.dumps(baseline))
        changed['vertical']['packs']['vn_fdi_fta']['classification']['aliases'] = {'packing_list': [r'\bcustom\s+pack\b']}
        changed['horizontal']['classification']['thresholds']['strong_filename'] = .83
        classified = deterministic_classify({'filename': 'custom_pack.pdf', 'idp_policy': changed})
        self.assertEqual((classified['type'], classified['confidence']), ('packing_list', .83))
        changed['vertical']['packs']['vn_fdi_fta']['batch']['expected_roles'] = ['packing_list']
        self.assertEqual(batch_structure([{'document_type': 'packing_list'}], changed), {
            'present': ['packing_list'], 'missing': [], 'duplicates': []})
        with self.assertRaisesRegex(Exception, 'Invalid horizontal/vertical/overlays'):
            model.select_effective_pack(
                self.env.company, 'future_domain', 'missing', 'VN', 'ALL', fields.Date.today())
        self.assertEqual(deterministic_classify({'filename': 'PO_123.pdf'})['type'], 'purchase_order')
        self.assertFalse(batch_structure([
            {'document_type': role} for role in (
                'purchase_order', 'vat_invoice', 'sales_invoice', 'commercial_invoice',
                'packing_list', 'warehouse_release', 'export_declaration')
        ])['missing'])

    def test_customs_compliance_capabilities_are_deterministic_and_fail_closed(self):
        # SRS 31.3 — regime/HS comparison, valuation+FX, line consistency, deadlines
        self.assertEqual([item['verdict'] for item in customs_checks(
            {'regime': 'E13', 'expected_hs': '8471', 'actual_hs': '8471'})], ['pass', 'pass'])
        self.assertEqual(customs_checks(
            {'regime': 'E11', 'expected_hs': '8471', 'actual_hs': '9999'})[0]['verdict'], 'block')
        self.assertEqual(customs_checks({}), [{
            'code': 'customs_regime', 'verdict': 'review', 'reason': 'missing customs regime'}])
        evaluator = self.env['logistics.idp.case'].evaluate_taxable_value
        fx = {'rate': '25400', 'effective_date': '2026-01-02',
              'base_currency': 'USD', 'quote_currency': 'VND'}
        self.assertEqual(evaluator('12.50', 'USD', 'VND', fx)['verdict'], 'pass')
        self.assertEqual(evaluator('12.50', 'USD', 'VND')['verdict'], 'review')
        line = {'quantity': '2', 'uom': 'EA', 'unit_price': '10.00', 'currency': 'USD'}
        self.assertEqual(compare_line(line, dict(line), '0')['verdict'], 'pass')
        self.assertEqual(compare_line(
            line, {**line, 'quantity': '3'}, '0')['verdict'], 'block')
        self.assertEqual(compare_line(
            line, {**line, 'currency': 'VND'}, '0')['verdict'], 'review')
        self.assertEqual(self.env['logistics.idp.case'].evaluate_counterpart_deadline(
            '2026-01-01', '2026-01-11', {'deadline_days': 10, 'warning_offsets': [1]})['status'], 'overdue')

    def test_ai_role_guardrails_hold(self):
        # SRS 31.10 — AI may draft/suggest but cannot self-activate blocking rules,
        # override authoritative dates, or silently resolve conflicting sources.
        active, candidate, context = self._activation_candidate()
        self.assertEqual(candidate.state, 'draft')
        ledger = self.env['logistics.idp.policy.activation']
        envelope = ledger.with_user(self.policy_manager).submit(
            candidate, '2026-08-12', '2026-08-12', 10000, context, 'submit')
        reviewer_group = self.env.ref('insilos_logistics_idp.group_logistics_reviewer')
        self.policy_manager.sudo().write({'group_ids': [(4, reviewer_group.id)]})
        with self.assertRaisesRegex(Exception, 'Maker and checker must differ'):
            ledger.with_user(self.policy_manager).decide(envelope, str(uuid4()), 'approve')
        with self.assertRaisesRegex(Exception, 'Policy recorded_at is immutable and server-assigned'):
            candidate.write({'recorded_at': fields.Datetime.now()})
        model = self.env['logistics.idp.policy.source']
        baseline = self.env.ref('insilos_logistics_idp.policy_trade_compliance_vn_reference_2026_2')
        first = model.with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': 'AI_CONFLICT_A_%s' % self.env.company.id, 'version': '1',
            'company_id': self.env.company.id, 'jurisdiction': 'ZZ', 'regime': 'ALL',
            'source_tier': 'customer_reference', 'citation': 'fixture',
            'effective_from': '2026-01-01', 'state': 'active', 'payload': baseline.payload,
        })
        second = model.with_context(
            _logistics_policy_loader_token=_INTERNAL_POLICY_LOADER_TOKEN,
        ).create({
            'code': 'AI_CONFLICT_B_%s' % self.env.company.id, 'version': '1',
            'company_id': self.env.company.id, 'jurisdiction': 'ZZ', 'regime': 'ALL',
            'source_tier': 'customer_reference', 'citation': 'fixture',
            'effective_from': '2026-01-01', 'state': 'active', 'payload': baseline.payload,
        })
        with self.assertRaisesRegex(Exception, 'Overlapping active policy packs'):
            model.select_effective_pack(
                self.env.company, 'trade_compliance', 'vn_fdi_fta', 'ZZ', 'ALL', '2026-01-01')
        self.assertEqual((first.state, second.state), ('active', 'active'))

    def test_idp_to_trade_compliance_intelligence_evolution_chain(self):
        # SRS 31.1 — IDP stays the evidence acquisition layer beneath
        # cross-document control, customs compliance, trade compliance,
        # regulatory change intelligence and geopolitical trade resilience.
        model = self.env['logistics.idp.policy.source']
        # cross-document control
        self.assertEqual(compare_line(
            {'quantity': '2', 'uom': 'EA', 'unit_price': '10.00', 'currency': 'USD'},
            {'quantity': '2', 'uom': 'EA', 'unit_price': '10.00', 'currency': 'USD'}, '0')['verdict'], 'pass')
        # customs compliance
        self.assertEqual(customs_checks(
            {'regime': 'E13', 'expected_hs': '8471', 'actual_hs': '8471'})[0]['verdict'], 'pass')
        # trade compliance: governed pack selection over evidence
        base = model.search([
            ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('version', '=', '2026.3')], limit=1)
        self.assertTrue(model.validate_policy_payload(
            base.payload, 'trade_compliance', 'vn_fdi_fta', 'VN', 'ALL'))
        # regulatory change intelligence: candidate preview over open cases
        payload = json.loads(base.payload)
        payload['policy_metadata'] = {
            'source_publication_date': '2026-08-10', 'applicability_predicate': {'jurisdiction': 'VN'},
            'severity_decision_effect': {'severity': 'medium', 'decision_effect': 'review'},
            'evidence_requirements': ['source_document'],
        }
        recorded_time = fields.Datetime.to_string(base.recorded_at).replace(' ', 'T') + 'Z'
        preview_date = fields.Date.to_string(base.recorded_at.date())
        context = {
            'schema_version': '1.0', 'company_id': self.env.company.id,
            'authority': 'authoritative_tier_1', 'who': {'party': 'fixture'}, 'when': preview_date,
            'transaction_time': recorded_time, 'effective_time': recorded_time,
            'recorded_time': recorded_time,
            'evidence': [{'document_id': self.provenance_document.id, 'field': 'policy',
                          'source_kind': 'document', 'source_hash': self.provenance_document.content_hash,
                          'extraction_run_id': self.provenance_document.current_run_id.id,
                          'authority': 'authoritative_tier_1'}],
        }
        candidate = model.with_user(self.policy_manager).import_candidate({
            'code': base.code, 'version': unique_fixture('EVOLUTION'), 'company_id': self.env.company.id,
            'jurisdiction': 'VN', 'regime': 'ALL', 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/policy-preview',
            'provenance': {'source': 'fixture', 'captured_at': recorded_time},
            'effective_from': preview_date, 'payload': payload, 'compliance_context': context,
        })
        preview = model.preview_impact(candidate, preview_date, preview_date, 10000, context)
        self.assertEqual(preview['candidate_hash'], candidate.payload_hash)
        self.assertEqual(list(preview['counts']), [
            'affected', 'possibly_affected', 'not_affected', 'insufficient_context'])
        # geopolitical trade resilience
        metrics = model.compute_resilience_metrics(self.env.company)
        self.assertEqual(metrics['schema_version'], '1.0')
        self.assertEqual(set(metrics), {
            'schema_version', 'generated_at', 'sources', 'detection_latency_days',
            'activation_latency_days', 'open_impact_assessments', 'unresolved_stale_exposures'})
