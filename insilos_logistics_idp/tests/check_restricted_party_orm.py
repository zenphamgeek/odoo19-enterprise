"""Run through the canonical local ORM shell; all fixtures roll back."""
import json
import unittest
import uuid

from odoo.addons.insilos_logistics_idp.tests.test_restricted_party import TestRestrictedPartyRuntime

assert env.cr.dbname == 'insilos_migration_digiforce_v2'
assert env['ir.module.module'].search_count([
    ('name', '=', 'insilos_logistics_idp'), ('state', '=', 'installed')]) == 1
MODELS = ('res.company', 'logistics.idp.case', 'logistics.idp.policy.source',
          'logistics.idp.check.result', 'logistics.idp.exception',
          'logistics.idp.evidence', 'logistics.idp.supplier.profile')
before = {name: env[name].sudo().search_count([]) for name in MODELS}
env = env(context=dict(env.context, install_demo=True))


def fixture():
    company = env['res.company'].create({'name': 'RPS rollback ' + uuid.uuid4().hex})
    local = env(context=dict(env.context, allowed_company_ids=[company.id]))
    test = unittest.TestCase()
    test.env = local
    for attr, supplier in [('case', 'Acme Trading Company'), ('clean_case', 'Clean Supplier')]:
        setattr(test, attr, local['logistics.idp.case'].create({
            'name': attr, 'company_id': company.id, 'source_system': 'fixture',
            'source_key': uuid.uuid4().hex, 'source_version': '1',
            'provenance': 'fixture:rps-rollback', 'effective_date': '2026-06-01',
            'supplier_reference': supplier}))
    payload = json.loads(local.ref('insilos_logistics_idp.policy_trade_compliance_vn_reference_2026_2').payload)
    payload['overlays']['restricted_parties'] = [{
        'list_name': 'SYN-DEMO', 'version': '1', 'source': 'synthetic_fixture',
        'entries': [{'name': 'Acme Trading Company', 'aliases': []}]}]
    test.policy = local['logistics.idp.policy.source']._controlled_create({
        'code': 'RPS-' + uuid.uuid4().hex, 'version': '1', 'company_id': company.id,
        'jurisdiction': 'XX', 'regime': 'ALL', 'source_tier': 'demo',
        'citation': 'fixture', 'effective_from': '2026-01-01', 'state': 'active',
        'payload': payload}, 'test_fixture')
    return test


class RollbackFixture(Exception):
    pass


passed = []
try:
    for name in (
        'test_screening_hit_routes_review_and_is_idempotent',
        'test_policy_change_creates_new_immutable_check',
        'test_clean_party_passes',
        'test_company_isolation_ignores_foreign_lists',
        'test_reconcile_wire_downgrades_pass_to_review_on_hit',
    ):
        try:
            with env.cr.savepoint():
                test = fixture()
                getattr(TestRestrictedPartyRuntime, name)(test)
                raise RollbackFixture()
        except RollbackFixture:
            passed.append(name)
            print('PASS', name)
    for name, values in (
        ('future_source', {'effective_from': '2027-01-01'}),
        ('expired_source', {'effective_to': '2026-05-31'}),
        ('inactive_source', {'state': 'draft'}),
    ):
        try:
            with env.cr.savepoint():
                test = fixture()
                payload = json.loads(test.policy.payload)
                payload['overlays']['restricted_parties'][0]['entries'] = [{'name': 'Clean Supplier'}]
                test.env['logistics.idp.policy.source']._controlled_create({
                    'code': 'RPS-' + uuid.uuid4().hex, 'version': '2',
                    'company_id': test.env.company.id, 'jurisdiction': 'XX', 'regime': 'ALL',
                    'source_tier': 'demo', 'citation': 'fixture', 'state': 'active',
                    'effective_from': '2026-01-01', 'payload': payload, **values}, 'test_fixture')
                result = test.clean_case._restricted_party_screening(
                    {'supplier': 'Clean Supplier'}, {}, name)
                assert result['verdict'] == 'pass' and result['lists_consulted'] == 1, result
                raise RollbackFixture()
        except RollbackFixture:
            passed.append(name)
            print('PASS', name)
finally:
    env.cr.rollback()
    env.invalidate_all()
    after = {name: env[name].sudo().search_count([]) for name in MODELS}
    print('DB', env.cr.dbname, 'COUNTS_BEFORE', before, 'COUNTS_AFTER', after)
    assert before == after, (before, after)
print('PASS rollback-only ORM:', len(passed), 'checks; provider calls: 0')
