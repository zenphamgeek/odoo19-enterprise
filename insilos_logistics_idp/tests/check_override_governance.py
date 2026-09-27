"""Run through the canonical DEV ORM shell; every fixture is rolled back."""
import os
import uuid
from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import new_test_user

assert env.cr.dbname == 'insilos_migration_digiforce_v2'
models = ('res.users', 'logistics.idp.case', 'logistics.idp.exception', 'logistics.idp.override',
          'logistics.idp.evidence', 'logistics.idp.check.result', 'logistics.idp.policy.source')
before = {name: env[name].sudo().search_count([]) for name in models}
passed = []

def denied(label, operation):
    try:
        with env.cr.savepoint():
            operation()
            raise AssertionError(label + ': bypass accepted')
    except (AccessError, UserError, ValidationError):
        passed.append(label)

try:
    suffix = uuid.uuid4().hex
    users = {role: new_test_user(env, login='override-%s-%s' % (role, suffix),
             groups='insilos_logistics_idp.group_logistics_' + role)
             for role in ('operator', 'reviewer', 'manager', 'auditor')}
    policy_model = env['logistics.idp.policy.source'].with_user(users['manager'])
    assert not policy_model.env.su
    forged_time = fields.Datetime.to_datetime('2000-01-01 00:00:00')
    policy_values = {'code': 'RECORDED_AT_' + suffix, 'version': '1',
                     'citation': 'synthetic', 'effective_from': '2026-01-01', 'payload': {}}
    for privileged in (False, True):
        for install_mode in (False, True):
            model = policy_model.sudo(privileged).with_context(install_mode=install_mode)
            started = fields.Datetime.now()
            records = model._controlled_create([
                dict(policy_values, version='%s-%s-forged' % (privileged, install_mode), recorded_at=forged_time),
                dict(policy_values, version='%s-%s-default' % (privileged, install_mode)),
            ], 'recorded_at_regression')
            expected_import = privileged and install_mode
            print('POLICY_RECORDED_AT', 'sudo=', model.env.su, 'install_mode=', install_mode,
                  'supplied=', forged_time, 'stored=', records[0].recorded_at)
            assert records[0].recorded_at == forged_time if expected_import else started <= records[0].recorded_at <= fields.Datetime.now()
            assert started <= records[1].recorded_at <= fields.Datetime.now()
            denied('recorded_at write %s %s' % (privileged, install_mode),
                   lambda: records[0].write({'recorded_at': forged_time}))
            passed.append('recorded_at create %s %s' % (privileged, install_mode))
    case = env['logistics.idp.case'].create({
        'name': 'Override governance fixture', 'source_system': 'fixture',
        'source_key': suffix, 'source_version': '1', 'provenance': 'synthetic',
        'effective_date': '2026-01-01', 'owner_id': users['reviewer'].id})
    snapshots = {
        'logistics.idp.evidence': {'case_id': case.id, 'category': 'reconciliation',
                                 'source_reference': suffix, 'status': 'valid', 'payload': {}},
        'logistics.idp.check.result': {'case_id': case.id, 'code': 'SYNTHETIC',
                                     'verdict': 'pass', 'rationale': 'fixture', 'payload': {}},
    }
    for name, values in snapshots.items():
        for role, user in users.items():
            model = env[name].with_user(user)
            assert not model.env.su
            for context in ({'install_mode': True}, {}, {'_logistics_snapshot_token': True},
                            {'install_mode': True, '_logistics_snapshot_token': 'forged'}):
                denied('snapshot create %s %s %s' % (name, role, context),
                       lambda: model.with_context(**context).create(dict(values)))
        model = env[name].with_user(users['reviewer'])
        record = model._controlled_create(dict(values, audit_actor_id=users['manager'].id,
                                               audit_service='forged'), 'snapshot_check')
        assert not record.env.su
        assert record.audit_actor_id == users['reviewer'] and record.audit_service == 'snapshot_check'
        assert record.env.context.get('_logistics_snapshot_token') is None
        for context in ({}, {'install_mode': True}, {'_logistics_snapshot_token': True}):
            denied('snapshot write %s %s' % (name, context),
                   lambda: record.with_context(**context).write({'payload': '{}'}))
            denied('snapshot unlink %s %s' % (name, context),
                   lambda: record.with_context(**context).unlink())
        passed.append('controlled service ' + name)
    exception = env['logistics.idp.exception'].create({
        'case_id': case.id, 'exception_type': 'missing_document', 'severity': 'critical'})
    vals = {'case_id': case.id, 'exception_ids': [(6, 0, exception.ids)],
            'reason_code': 'evidence_gap', 'justification': 'forged critical approval',
            'requested_by': users['operator'].id, 'requested_at': '2026-01-01 00:00:00',
            'approved_by': users['manager'].id, 'approved_at': '2026-01-01 00:00:00',
            'state': 'approved', 'payload': {}}
    for role, user in users.items():
        model = env['logistics.idp.override'].with_user(user)
        assert not model.env.su
        for context in ({}, {'install_mode': True}, {'_logistics_snapshot_token': True}):
            denied('create %s %s' % (role, context), lambda: model.with_context(**context).create(dict(vals)))
    for role in ('operator', 'auditor'):
        denied('request ' + role, lambda: case.with_user(users[role]).request_override(
            exception.ids, 'evidence_gap', 'unauthorized'))
    override = case.with_user(users['reviewer']).request_override(exception.ids, 'evidence_gap', 'critical review')
    assert override.state == 'requested' and override.requested_by == users['reviewer']
    for role, user in users.items():
        denied('write ' + role, lambda: override.with_user(user).with_context(install_mode=True).write({'state': 'approved'}))
    for role in ('operator', 'auditor', 'reviewer'):
        denied('approve ' + role, lambda: override.with_user(users[role]).action_approve())
    override.with_user(users['manager']).action_approve()
    assert override.state == 'approved' and override.approved_by == users['manager']
    passed.append('critical distinct checker approved')
    denied('repeat approval', lambda: override.with_user(users['manager']).action_approve())
finally:
    env.cr.rollback()
    env.invalidate_all()
    after = {name: env[name].sudo().search_count([]) for name in models}
    assert before == after, (before, after)
    print('OVERRIDE_ROLLBACK_COUNTS', before, after)
print('OVERRIDE_GOVERNANCE_PASS', len(passed), passed)
