"""Canonical ORM shell regression; synthetic fixtures, unconditional rollback."""
import os
import uuid

from odoo.exceptions import UserError
from odoo.addons.insilos_chemical_trade_compliance.models.is_chemical_compliance_dossier import ChemicalComplianceDossier

assert env.cr.dbname == 'insilos_migration_digiforce_v2'
models = ('logistics.idp.case', 'logistics.idp.check.result', 'logistics.idp.override',
          'logistics.idp.exception', 'is.chemical.compliance.dossier', 'res.users')
before = {model: env[model].sudo().search_count([]) for model in models}
reproduce = os.environ.get('REPRODUCE_SCREENING_BYPASS') == '1'
try:
    checker = env['res.users'].create({
        'name': 'Screening rollback checker', 'login': 'screening-' + uuid.uuid4().hex,
        'group_ids': [(4, env.ref('insilos_chemical_trade_compliance.group_chemical_compliance_manager').id)],
    })
    for verdict in ('review', 'block', 'pass'):
        case = env['logistics.idp.case'].create({
            'name': 'Screening rollback', 'source_system': 'fixture',
            'source_key': uuid.uuid4().hex, 'source_version': '1',
            'provenance': 'fixture:final-screening',
        })
        env['logistics.idp.check.result']._controlled_create({
            'case_id': case.id, 'code': 'RESTRICTED_PARTY_SCREENING', 'payload': {},
            'required': True, 'verdict': verdict, 'rationale': 'Synthetic regression',
        }, 'test_fixture')
        # Deliberately forge the mutable case summary: immutable checks remain authoritative.
        case.write({'verdict': 'pass', 'state': 'ready'})
        dossier = env['is.chemical.compliance.dossier'].create({'case_id': case.id})
        for state in ('internally_approved',):
            try:
                dossier.write({'state': state})
            except UserError:
                print('PASS direct-write denied', verdict, state)
            else:
                raise AssertionError('Direct-write bypass')
        for source, action in (('submission_prepared', 'action_complete_internal_review'), ('internally_approved', 'action_deduct_permit_quota')):
            # Test-only predecessor setup, not a public RPC path.
            super(ChemicalComplianceDossier, dossier).write({'state': source, 'submitted_by': env.uid})
            denied = False
            try:
                getattr(dossier.with_user(checker), action)()
            except UserError as error:
                denied = True
                print('DENIED', verdict, action, str(error))
            if action == 'action_deduct_permit_quota' or verdict != 'pass':
                assert denied, (verdict, action, dossier.state)
                assert dossier.state == source
            else:
                assert not denied, (verdict, action)
            print('PASS', verdict, action)
    from odoo import fields
    for scenario in ('forged', 'cross_case', 'stale', 'valid'):
        check = env['logistics.idp.check.result']._controlled_create({
            'case_id': case.id, 'code': 'OLD_SCREENING', 'payload': {},
            'required': True, 'verdict': 'pass', 'rationale': 'Earlier synthetic screening',
        }, 'test_fixture')
        foreign = env['logistics.idp.case'].create({
            'name': 'Override rollback', 'source_system': 'fixture',
            'source_key': uuid.uuid4().hex, 'source_version': '1', 'provenance': 'fixture:override',
        })
        target = env['logistics.idp.check.result']._controlled_create({
            'case_id': case.id, 'code': 'OVERRIDE_' + scenario, 'payload': {},
            'required': True, 'verdict': 'review', 'rationale': 'Synthetic override regression',
        }, 'test_fixture')
        exception = env['logistics.idp.exception'].create({
            'case_id': foreign.id if scenario == 'cross_case' else case.id,
            'exception_type': 'restricted_party_hit', 'severity': 'medium',
        })
        override = env['logistics.idp.override']._controlled_create({
            'case_id': case.id, 'exception_ids': [(6, 0, exception.ids)],
            'check_result_ids': [(6, 0, (check if scenario == 'stale' else target).ids)],
            'reason_code': 'evidence_gap', 'justification': 'Synthetic regression',
            'requested_by': env.uid, 'requested_at': fields.Datetime.now(),
            'state': 'approved', 'approved_by': False if scenario == 'forged' else env.uid,
            'approved_at': False if scenario == 'forged' else fields.Datetime.now(),
            'payload': {},
        }, 'controlled_override')
        case.write({'verdict': 'pass', 'state': 'ready'})
        denied = False
        try:
            dossier._check_final_screening()
        except UserError:
            denied = True
        expected = scenario != 'valid'
        if reproduce and scenario in ('forged', 'cross_case'):
            expected = False
        assert denied == expected, (scenario, denied, expected)
        print('OVERRIDE', scenario, 'DENIED' if denied else 'ACCEPTED')
        for source, action in (('submission_prepared', 'action_complete_internal_review'), ('internally_approved', 'action_deduct_permit_quota')):
            super(ChemicalComplianceDossier, dossier).write({'state': source, 'submitted_by': env.uid})
            denied = False
            try:
                getattr(dossier.with_user(checker), action)()
            except UserError:
                denied = True
            expected_action_denial = expected or action == 'action_deduct_permit_quota'
            assert denied == expected_action_denial, (scenario, action, denied, expected_action_denial)
            if denied:
                assert dossier.state == source
            print('PASS override', scenario, action)
        # Isolate subsequent scenarios without persisting fixture changes.
        case = foreign
        dossier = env['is.chemical.compliance.dossier'].create({'case_id': case.id})
finally:
    env.cr.rollback()
    env.invalidate_all()
    after = {model: env[model].sudo().search_count([]) for model in models}
    print('DB', env.cr.dbname, 'COUNTS_BEFORE', before, 'COUNTS_AFTER', after)
    assert before == after
print('PASS final screening; provider calls: 0; rollback complete')
