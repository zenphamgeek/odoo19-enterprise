import json
import multiprocessing
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import psycopg2.errors

from odoo import api, fields
from odoo.modules.registry import Registry
from odoo.tests.common import BaseCase, get_db_name, new_test_user, standalone, tagged
from odoo.tools import mute_logger

from .common import unique_fixture


def _activation_worker(db_name, envelope, event_uuid, reviewer_id, start, results,
                       activate=True, locked=None, release=None, entered=None):
    if not start.wait(timeout=5):
        results.put(('error', 'TimeoutError: concurrency start gate timed out'))
        return
    for attempt in range(3):
        with Registry(db_name).cursor() as cr:
            try:
                cr.execute("SET LOCAL lock_timeout = '5s'")
                cr.execute("SET LOCAL statement_timeout = '10s'")
                ledger = api.Environment(cr, reviewer_id, {})['logistics.idp.policy.activation']
                if entered is not None:
                    entered.set()
                if locked is not None:
                    original = type(ledger)._lock_preview_cases

                    def synchronized_lock(recordset, case_ids):
                        result = original(recordset, case_ids)
                        locked.set()
                        if not release.wait(timeout=5):
                            raise TimeoutError('activation lock release timed out')
                        return result

                    with patch.object(type(ledger), '_lock_preview_cases', synchronized_lock):
                        event = ledger.decide(envelope, event_uuid, 'approve' if activate else 'reject', activate=activate)
                else:
                    event = ledger.decide(envelope, event_uuid, 'approve' if activate else 'reject', activate=activate)
                cr.commit()
                results.put(('ok', event.id, event.status))
                return
            except psycopg2.errors.SerializationFailure:
                cr.rollback()
                if attempt == 2:
                    results.put(('error', 'SerializationFailure after 3 attempts'))
            except Exception as exc:
                cr.rollback()
                results.put(('error', '%s: %s' % (type(exc).__name__, exc)))
                return


def _exception_worker(db_name, case_id, severity, start, results, locked=None, release=None,
                      competitor_entered=None):
    if not start.wait(timeout=5):
        results.put(('error', 'TimeoutError: exception start gate timed out'))
        return
    with Registry(db_name).cursor() as cr:
        try:
            if locked is not None:
                cr.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", [
                    'logistics-idp-preview-case:%s' % case_id])
            exception_model = api.Environment(cr, api.SUPERUSER_ID, {})['logistics.idp.exception']
            exception = exception_model.create({
                'case_id': case_id, 'exception_type': 'policy', 'severity': severity})
            cr.commit()
            if locked is not None:
                locked.set()
                if competitor_entered is not None and not competitor_entered.wait(timeout=5):
                    raise TimeoutError('competitor did not enter production ORM path')
                if not release.wait(timeout=5):
                    raise TimeoutError('exception lock release timed out')
                cr.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", [
                    'logistics-idp-preview-case:%s' % case_id])
            results.put(('ok', exception.id, severity))
        except Exception as exc:
            cr.rollback()
            results.put(('error', '%s: %s' % (type(exc).__name__, exc)))


def _activation_fixture(env, candidate_count):
    manager = new_test_user(env, login='g5-process-manager-%s' % uuid4().hex, email=False,
                            groups='insilos_logistics_idp.group_logistics_manager')
    reviewer = new_test_user(env, login='g5-process-reviewer-%s' % uuid4().hex, email=False,
                             groups='insilos_logistics_idp.group_logistics_reviewer')
    reference = env['logistics.idp.policy.source'].search([
        ('code', '=', 'TRADE_COMPLIANCE_VN_REFERENCE'), ('state', '=', 'active')], limit=1)
    code = 'CONCURRENT-G5-%s' % uuid4().hex
    effective_from = fields.Date.today()
    active = env['logistics.idp.policy.source']._controlled_create({
        'code': code, 'version': 'PREDECESSOR-%s' % uuid4().hex,
        'company_id': env.company.id, 'jurisdiction': reference.jurisdiction,
        'regime': reference.regime, 'source_tier': 'authoritative_tier_1',
        'citation': 'https://example.invalid/concurrency',
        'effective_from': effective_from, 'payload': reference.payload,
    }, 'test_fixture')
    env.cr.execute("UPDATE logistics_idp_policy_source SET state = 'active' WHERE id = %s", [active.id])
    active.invalidate_recordset(['state'])
    candidates = env['logistics.idp.policy.source']
    for index in range(candidate_count):
        candidates |= env['logistics.idp.policy.source']._controlled_create({
            'code': code, 'version': 'CANDIDATE-%s-%s' % (index, uuid4().hex),
            'company_id': env.company.id, 'jurisdiction': active.jurisdiction,
            'regime': active.regime, 'source_tier': 'authoritative_tier_1',
            'citation': 'https://example.invalid/concurrency',
            'effective_from': active.effective_from, 'payload': active.payload,
            'provenance': json.dumps({'verification': 'verified'}),
        }, 'test_fixture')
    decision_date = fields.Date.today()
    decision_time = '%sZ' % fields.Datetime.now().isoformat()
    context = {
        'schema_version': '1.0', 'company_id': env.company.id,
        'authority': 'authoritative_tier_1', 'who': {'party': 'fixture'},
        'when': fields.Date.to_string(decision_date), 'transaction_time': decision_time,
        'effective_time': decision_time, 'recorded_time': decision_time, 'evidence': [],
    }
    envelopes = [env['logistics.idp.policy.activation'].with_user(manager).submit(
        candidate, decision_date, decision_date, 10000, context, 'submit')
        for candidate in candidates]
    env.cr.commit()
    return active.id, candidates.ids, envelopes, manager.id, reviewer.id


def _run_processes(db_name, calls):
    context = multiprocessing.get_context('fork')
    start = context.Event()
    results = context.Queue()
    processes = [context.Process(target=_activation_worker, args=(
        db_name, *call[:3], start, results, *call[3:])) for call in calls]
    for process in processes:
        process.start()
    start.set()
    for process in processes:
        process.join(15)
    timed_out = [process for process in processes if process.is_alive()]
    for process in timed_out:
        process.terminate()
        process.join(5)
    if timed_out:
        raise AssertionError('G5 ORM worker timeout: %s' % [process.pid for process in timed_out])
    return [results.get(timeout=2) for _process in processes]


@standalone('logistics_idp_g5_concurrency')
def verify_g5_process_concurrency(env):
    db_name = env.cr.dbname
    fixture_ids = []
    user_ids = []
    try:
        active_id, candidate_ids, envelopes, manager_id, reviewer_id = _activation_fixture(env, 1)
        fixture_ids.extend([active_id, *candidate_ids])
        user_ids.extend([manager_id, reviewer_id])
        event_uuid = str(uuid4())
        same_event = _run_processes(db_name, [
            (envelopes[0], event_uuid, reviewer_id),
            (envelopes[0], event_uuid, reviewer_id),
        ])
        env.invalidate_all()
        assert {result[0] for result in same_event} == {'ok'}, same_event
        assert len({result[1] for result in same_event}) == 1, same_event
        assert env['logistics.idp.policy.activation'].search_count([('event_uuid', '=', event_uuid)]) == 1

        active2_id, candidate2_ids, envelopes2, manager2_id, reviewer2_id = _activation_fixture(env, 2)
        fixture_ids.extend([active2_id, *candidate2_ids])
        user_ids.extend([manager2_id, reviewer2_id])
        overlap = _run_processes(db_name, [
            (envelopes2[0], str(uuid4()), reviewer2_id),
            (envelopes2[1], str(uuid4()), reviewer2_id),
        ])
        env.invalidate_all()
        candidates = env['logistics.idp.policy.source'].browse(candidate2_ids)
        assert sorted(result[0] for result in overlap) == ['error', 'ok'], overlap
        assert candidates.mapped('state').count('active') == 1, candidates.mapped('state')
        assert candidates.mapped('state').count('draft') == 1, candidates.mapped('state')
        assert env['logistics.idp.policy.source'].browse(active2_id).state == 'retired'
        assert env['logistics.idp.policy.activation'].search_count([
            ('predecessor_policy_id', '=', active2_id), ('status', '=', 'activated')]) == 1

        active3_id, candidate3_ids, envelopes3, manager3_id, reviewer3_id = _activation_fixture(env, 1)
        fixture_ids.extend([active3_id, *candidate3_ids])
        user_ids.extend([manager3_id, reviewer3_id])
        case_ids = json.loads(envelopes3[0]['payload'])['preview_case_ids']
        assert case_ids, 'G5 blocker race requires a production preview case'
        process_context = multiprocessing.get_context('fork')
        start = process_context.Event()
        locked = process_context.Event()
        release = process_context.Event()
        entered = process_context.Event()
        results = process_context.Queue()
        blocker = process_context.Process(target=_exception_worker, args=(
            db_name, case_ids[0], 'critical', start, results, locked, release, entered))
        activation = process_context.Process(target=_activation_worker, args=(
            db_name, envelopes3[0], str(uuid4()), reviewer3_id, start, results,
            True, None, None, entered))
        blocker.start()
        start.set()
        assert locked.wait(timeout=5), 'blocker did not acquire preview advisory lock'
        activation.start()
        assert entered.wait(timeout=5), 'activation did not enter production ORM path'
        release.set()
        blocker.join(15)
        activation.join(15)
        blocker_first = [results.get(timeout=2), results.get(timeout=2)]
        assert sorted(result[0] for result in blocker_first) == ['error', 'ok'], blocker_first
        env.invalidate_all()
        assert env['logistics.idp.policy.source'].browse(candidate3_ids[0]).state == 'draft'
        assert env['logistics.idp.policy.source'].browse(active3_id).state == 'active'
        blocker_id = next(result[1] for result in blocker_first if result[0] == 'ok')
        env.cr.execute('DELETE FROM logistics_idp_exception WHERE id = %s', [blocker_id])
        env.cr.commit()

        active4_id, candidate4_ids, envelopes4, manager4_id, reviewer4_id = _activation_fixture(env, 1)
        fixture_ids.extend([active4_id, *candidate4_ids])
        user_ids.extend([manager4_id, reviewer4_id])
        case_id = json.loads(envelopes4[0]['payload'])['preview_case_ids'][0]
        start = process_context.Event()
        locked = process_context.Event()
        release = process_context.Event()
        results = process_context.Queue()
        activation = process_context.Process(target=_activation_worker, args=(
            db_name, envelopes4[0], str(uuid4()), reviewer4_id, start, results, True, locked, release))
        exception = process_context.Process(target=_exception_worker, args=(
            db_name, case_id, 'high', start, results))
        activation.start()
        start.set()
        assert locked.wait(timeout=5), 'activation did not acquire preview advisory lock'
        exception.start()
        release.set()
        activation.join(15)
        exception.join(15)
        activation_first = [results.get(timeout=2), results.get(timeout=2)]
        assert {result[0] for result in activation_first} == {'ok'}, activation_first
        env.invalidate_all()
        terminal = env['logistics.idp.policy.activation'].search([
            ('policy_source_id', '=', candidate4_ids[0]), ('status', '=', 'activated')], limit=1)
        appended = env['logistics.idp.exception'].search([
            ('case_id', '=', case_id), ('severity', '=', 'high')], order='id desc', limit=1)
        assert terminal and appended and terminal.create_date <= appended.create_date

        low_exception = env['logistics.idp.exception'].create({
            'case_id': case_id, 'exception_type': 'policy', 'severity': 'medium'})
        assert env['logistics.idp.policy.source'].browse(candidate4_ids[0]).state == 'active'
        env.cr.execute('DELETE FROM logistics_idp_exception WHERE id = ANY(%s)', [[appended.id, low_exception.id]])
        env.cr.commit()

        active5_id, candidate5_ids, envelopes5, manager5_id, reviewer5_id = _activation_fixture(env, 1)
        fixture_ids.extend([active5_id, *candidate5_ids])
        user_ids.extend([manager5_id, reviewer5_id])
        decision_race = _run_processes(db_name, [
            (envelopes5[0], str(uuid4()), reviewer5_id, True),
            (envelopes5[0], str(uuid4()), reviewer5_id, False),
        ])
        env.invalidate_all()
        terminals = env['logistics.idp.policy.activation'].search([
            ('policy_source_id', '=', candidate5_ids[0])])
        assert len(terminals) == 1, decision_race
        assert sorted(result[0] for result in decision_race) == ['error', 'ok'], decision_race
        winner = terminals.status
        same_decision = _run_processes(db_name, [(
            envelopes5[0], terminals.event_uuid, reviewer5_id, winner == 'activated')])
        assert same_decision[0][:2] == ('ok', terminals.id), same_decision

        print('G5_PROCESS_CONCURRENCY same_event=%r overlap=%r blocker_first=%r activation_first=%r decision_race=%r invariants=PASS' % (
            same_event, overlap, blocker_first, activation_first, decision_race))
    finally:
        env.cr.rollback()
        env.cr.execute("DELETE FROM logistics_idp_policy_activation WHERE policy_source_id = ANY(%s)", [fixture_ids])
        env.cr.execute("DELETE FROM logistics_idp_policy_source WHERE id = ANY(%s)", [fixture_ids])
        if user_ids:
            env['res.users'].browse(user_ids).unlink()
        env.cr.commit()


@tagged('-standard', '-at_install', 'post_install', 'logistics_idp', 'logistics_idp_concurrency')
class TestLogisticsIdpConcurrency(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = Registry(get_db_name())
        with cls.registry.cursor() as cr:
            cls.company_id = api.Environment(cr, api.SUPERUSER_ID, {}).company.id
        cls.identity = ('concurrency-erp', 'CONCURRENT-%s' % uuid4().hex, 'v1')
        cls.activation_policy_ids = []
        cls.activation_predecessor_ids = []
        cls.activation_user_ids = []
        cls.addClassCleanup(cls.cleanUpClass)

    @classmethod
    def cleanUpClass(cls):
        with cls.registry.cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {})
            env['logistics.idp.inbound.job'].search([
                ('source_system', '=', cls.identity[0]), ('source_key', '=', cls.identity[1])]).unlink()
            if cls.activation_policy_ids:
                cr.execute("DELETE FROM logistics_idp_policy_activation WHERE policy_source_id = ANY(%s)",
                           [cls.activation_policy_ids])
                cr.execute("DELETE FROM logistics_idp_policy_source WHERE id = ANY(%s)",
                           [cls.activation_policy_ids])
            if cls.activation_predecessor_ids:
                cr.execute("DELETE FROM logistics_idp_policy_source WHERE id = ANY(%s)",
                           [cls.activation_predecessor_ids])
            if cls.activation_user_ids:
                env['res.users'].browse(cls.activation_user_ids).unlink()
            cr.commit()

    @mute_logger('odoo.sql_db')
    def test_database_identity_constraint_under_true_concurrency(self):
        barrier = threading.Barrier(2)

        def create_job():
            with self.registry.cursor() as cr:
                barrier.wait(timeout=3)
                try:
                    cr.execute("""
                        INSERT INTO logistics_idp_inbound_job
                            (company_id, profile_code, adapter_type, source_system, source_key, source_version, payload,
                             state, attempt_count, max_attempts, next_attempt_at, create_uid, write_uid, create_date, write_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', 0, 3, NOW(), %s, %s, NOW(), NOW())
                    """, [self.company_id, 'local-test', 'generic_inbound', *self.identity,
                          json.dumps({'name': 'Concurrent'}), api.SUPERUSER_ID, api.SUPERUSER_ID])
                    cr.commit()
                    return False
                except psycopg2.errors.UniqueViolation:
                    return True

        with ThreadPoolExecutor(max_workers=2) as executor:
            collisions = [future.result(timeout=5) for future in (
                executor.submit(create_job), executor.submit(create_job))]
        with self.registry.cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {})
            jobs = env['logistics.idp.inbound.job'].search([
                ('source_system', '=', self.identity[0]), ('source_key', '=', self.identity[1]),
                ('source_version', '=', self.identity[2])])
            self.assertEqual(len(jobs), 1)
        self.assertEqual(sum(collisions), 1)

    @mute_logger('odoo.sql_db')
    def test_database_active_policy_overlap_guard_under_true_concurrency(self):
        with self.registry.cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {})
            reference = env['logistics.idp.policy.source'].search([('state', '=', 'active')], limit=1)
            code = 'DB-OVERLAP-%s' % uuid4().hex
            policies = env['logistics.idp.policy.source']
            for index in range(2):
                policies |= env['logistics.idp.policy.source']._controlled_create({
                    'code': code, 'version': 'v%s' % index, 'company_id': self.company_id,
                    'jurisdiction': reference.jurisdiction, 'regime': reference.regime,
                    'source_tier': 'authoritative_tier_1',
                    'citation': 'https://example.invalid/concurrency',
                    'effective_from': '2026-01-01', 'effective_to': '2026-12-31',
                    'payload': reference.payload,
                }, 'test_fixture')
            policy_ids = policies.ids
            self.activation_policy_ids.extend(policy_ids)
            cr.commit()
        barrier = threading.Barrier(2)

        def activate(policy_id):
            with self.registry.cursor() as cr:
                barrier.wait(timeout=3)
                try:
                    cr.execute("UPDATE logistics_idp_policy_source SET state = 'active' WHERE id = %s", [policy_id])
                    cr.commit()
                    return 'ok'
                except psycopg2.errors.ExclusionViolation:
                    cr.rollback()
                    return 'overlap'

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = [future.result(timeout=5) for future in (
                executor.submit(activate, policy_ids[0]), executor.submit(activate, policy_ids[1]))]
        self.assertEqual(sorted(outcomes), ['ok', 'overlap'])
        with self.registry.cursor() as cr:
            cr.execute("SELECT count(*) FROM logistics_idp_policy_source WHERE id = ANY(%s) AND state = 'active'", [policy_ids])
            self.assertEqual(cr.fetchone()[0], 1)

    @mute_logger('odoo.sql_db')
    def test_active_policy_overlap_guard_locks_reversed_buckets_without_deadlock(self):
        with self.registry.cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {})
            reference = env['logistics.idp.policy.source'].search([('state', '=', 'active')], limit=1)
            bucket_codes = ['DB-REVERSED-A-%s' % uuid4().hex, 'DB-REVERSED-B-%s' % uuid4().hex]
            policy_ids = []
            for code in bucket_codes:
                for index in range(2):
                    policy = env['logistics.idp.policy.source']._controlled_create({
                        'code': code, 'version': 'v%s' % index, 'company_id': self.company_id,
                        'jurisdiction': reference.jurisdiction, 'regime': reference.regime,
                        'source_tier': 'authoritative_tier_1',
                        'citation': 'https://example.invalid/concurrency',
                        'effective_from': '2026-01-01', 'effective_to': '2026-12-31',
                        'payload': reference.payload,
                    }, 'test_fixture')
                    policy_ids.append(policy.id)
            self.activation_policy_ids.extend(policy_ids)
            cr.commit()
        barrier = threading.Barrier(2)

        def activate(first_id, second_id):
            with self.registry.cursor() as cr:
                barrier.wait(timeout=3)
                try:
                    cr.execute("SET LOCAL statement_timeout = '5s'")
                    cr.execute("UPDATE logistics_idp_policy_source SET state = 'active' WHERE id = %s", [first_id])
                    cr.execute("UPDATE logistics_idp_policy_source SET state = 'active' WHERE id = %s", [second_id])
                    cr.commit()
                    return 'ok'
                except psycopg2.errors.ExclusionViolation:
                    cr.rollback()
                    return 'overlap'
                except psycopg2.errors.DeadlockDetected:
                    cr.rollback()
                    return 'deadlock'

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = [future.result(timeout=10) for future in (
                executor.submit(activate, policy_ids[0], policy_ids[2]),
                executor.submit(activate, policy_ids[3], policy_ids[1]))]
        self.assertEqual(sorted(outcomes), ['ok', 'overlap'])
        with self.registry.cursor() as cr:
            cr.execute("""
                SELECT code, count(*) FROM logistics_idp_policy_source
                 WHERE id = ANY(%s) AND state = 'active' GROUP BY code ORDER BY code
            """, [policy_ids])
            self.assertEqual(cr.fetchall(), [(bucket_codes[0], 1), (bucket_codes[1], 1)])

    def test_skip_locked_allows_exactly_one_worker_to_claim_job(self):
        claim_identity = (self.identity[0], '%s-claim' % self.identity[1], self.identity[2])
        with self.registry.cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {})
            cr.execute("UPDATE logistics_idp_inbound_job SET next_attempt_at = NOW() + INTERVAL '1 day' WHERE state IN ('pending', 'retry')")
            job = env['logistics.idp.inbound.job'].create({
                'profile_code': 'local-test', 'source_system': claim_identity[0],
                'source_key': claim_identity[1], 'source_version': claim_identity[2],
                'payload': json.dumps({'name': 'Concurrent', 'provenance': 'fixture', 'effective_date': '2026-01-01'}),
            })
            job_id = job.id
            cr.commit()
        claimed = threading.Event()
        release = threading.Event()

        def claim(hold=False):
            with self.registry.cursor() as cr:
                cr.execute("SELECT id FROM logistics_idp_inbound_job WHERE id = %s FOR UPDATE SKIP LOCKED", [job_id])
                ids = [row[0] for row in cr.fetchall()]
                if hold:
                    claimed.set()
                    release.wait(timeout=3)
                cr.commit()
                return ids

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(claim, True)
            self.assertTrue(claimed.wait(timeout=3))
            second_ids = executor.submit(claim).result(timeout=5)
            release.set()
            first_ids = first.result(timeout=5)
        self.assertEqual(first_ids, [job_id])
        self.assertEqual(second_ids, [])

    def test_terminal_insert_unique_violation_atomically_rolls_back_lifecycle(self):
        authority_registry = {
            'authoritative_tier_1': {
                'https://example.invalid/concurrency': {
                    'approved': True, 'source_tier': 'authoritative_tier_1',
                },
            },
        }
        with self.registry.cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {
                'logistics_idp_test_authority_registry': authority_registry,
            })
            active_id, candidate_ids, envelopes, manager_id, reviewer_id = _activation_fixture(env, 1)
            self.activation_predecessor_ids.append(active_id)
            self.activation_policy_ids.extend(candidate_ids)
            self.activation_user_ids.extend((manager_id, reviewer_id))
        with self.registry.cursor() as cr:
            env = api.Environment(cr, reviewer_id, {
                'logistics_idp_test_authority_registry': authority_registry,
            })
            ledger = env['logistics.idp.policy.activation']
            with patch.object(type(ledger), '_append', side_effect=psycopg2.errors.UniqueViolation()):
                with self.assertRaises(psycopg2.errors.UniqueViolation):
                    ledger.decide(envelopes[0], str(uuid4()), 'approve')
            cr.rollback()
        with self.registry.cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {})
            self.assertEqual((env['logistics.idp.policy.source'].browse(candidate_ids).state,
                              env['logistics.idp.policy.source'].browse(active_id).state),
                             ('draft', 'active'))
