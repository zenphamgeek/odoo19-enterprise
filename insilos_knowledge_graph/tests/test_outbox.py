import datetime
import multiprocessing
from unittest.mock import patch
from uuid import uuid4

from odoo import api, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.modules.registry import Registry
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, standalone

from ..models.outbox import SOURCE_PAYLOAD_FIELDS


def _claim_worker(db_name, user_id, limit, ready, release, results, finish='done', lease_seconds=300):
    with Registry(db_name).cursor() as cr:
        try:
            events = api.Environment(cr, user_id, {})['kg.outbox']._claim_batch(
                limit=limit, lease_seconds=lease_seconds)
            results.put(('claimed', events.ids))
            ready.set()
            if not release.wait(timeout=10):
                raise TimeoutError('KG claim release timed out')
            if finish == 'done':
                cr.execute("UPDATE kg_outbox SET state = 'DONE', claimed_at = NULL, processed_at = NOW() AT TIME ZONE 'UTC' WHERE id = ANY(%s)", [events.ids])
                cr.commit()
            elif finish == 'commit':
                cr.commit()
            else:
                cr.rollback()
            results.put(('finished', finish))
        except Exception as error:
            cr.rollback()
            results.put(('error', '%s: %s' % (type(error).__name__, error)))


def _run_claim_process(context, db_name, user_id, limit, finish='done', lease_seconds=300):
    ready = context.Event()
    release = context.Event()
    results = context.Queue()
    process = context.Process(target=_claim_worker, args=(
        db_name, user_id, limit, ready, release, results, finish, lease_seconds))
    process.start()
    return process, ready, release, results


@standalone('kg_outbox_multi_worker')
def verify_kg_outbox_multi_worker(env):
    if 'logistics.idp.case' not in env.registry.models:
        raise AssertionError('Logistics IDP must be installed for KG outbox proof')
    context = multiprocessing.get_context('fork')
    token = uuid4().hex
    user_ids = []
    case_ids = []
    outbox_ids = []
    try:
        processor_group = env.ref('insilos_knowledge_graph.group_kg_processor')
        logistics_group = env.ref('insilos_logistics_idp.group_logistics_admin')
        for index in range(2):
            user = env['res.users'].create({
                'name': 'KG worker %s' % index, 'login': 'kg-worker-%s-%s' % (token, index),
                'company_id': env.company.id, 'company_ids': [(6, 0, [env.company.id])],
                'group_ids': [(6, 0, [processor_group.id, logistics_group.id])],
            })
            user_ids.append(user.id)
        for index in range(6):
            case = env['logistics.idp.case'].create({
                'name': 'KG concurrency %s' % index, 'source_system': 'kg-concurrency',
                'source_key': '%s-%s' % (token, index), 'source_version': '1',
                'provenance': 'fixture:kg-concurrency', 'effective_date': '2026-01-01',
                'company_id': env.company.id,
            })
            case_ids.append(case.id)
            payload = {field: case[field] for field in SOURCE_PAYLOAD_FIELDS[case._name]}
            env['kg.outbox'].enqueue(case, payload=payload, mutation_token='kg-concurrency:%s:%s' % (token, index))
        outbox_ids = env['kg.outbox'].sudo().search([
            ('source_model', '=', 'logistics.idp.case'), ('source_id', 'in', [str(case_id) for case_id in case_ids])]).ids
        assert len(outbox_ids) == 6, outbox_ids
        env.cr.commit()

        workers = [_run_claim_process(context, env.cr.dbname, user_ids[index], 2) for index in range(2)]
        assert all(ready.wait(timeout=10) for _process, ready, _release, _results in workers)
        claims = [results.get(timeout=2) for _process, _ready, _release, results in workers]
        assert all(result[0] == 'claimed' and len(result[1]) == 2 for result in claims), claims
        claimed_sets = [set(result[1]) for result in claims]
        assert claimed_sets[0].isdisjoint(claimed_sets[1]), claims
        for _process, _ready, release, _results in workers:
            release.set()
        for process, _ready, _release, results in workers:
            process.join(15)
            assert not process.is_alive() and process.exitcode == 0, process.exitcode
            finished = results.get(timeout=2)
            assert finished == ('finished', 'done'), finished
        env.invalidate_all()
        done_ids = set(env['kg.outbox'].sudo().browse(outbox_ids).filtered(lambda event: event.state == 'DONE').ids)
        assert done_ids == claimed_sets[0] | claimed_sets[1], (done_ids, claims)

        rollback_worker = _run_claim_process(context, env.cr.dbname, user_ids[0], 1, finish='rollback')
        process, ready, release, results = rollback_worker
        assert ready.wait(timeout=10)
        rolled_claim = results.get(timeout=2)
        release.set()
        process.join(15)
        assert results.get(timeout=2) == ('finished', 'rollback')
        recovery = _run_claim_process(context, env.cr.dbname, user_ids[1], 1, finish='commit')
        process, ready, release, results = recovery
        assert ready.wait(timeout=10)
        recovered_claim = results.get(timeout=2)
        assert recovered_claim == rolled_claim, (rolled_claim, recovered_claim)
        release.set()
        process.join(15)
        assert results.get(timeout=2) == ('finished', 'commit')

        env.cr.rollback()
        env.cr.execute("UPDATE kg_outbox SET claimed_at = claimed_at - interval '301 seconds' WHERE id = %s", [recovered_claim[1][0]])
        env.cr.commit()
        lease_recovery = _run_claim_process(context, env.cr.dbname, user_ids[0], 1, finish='done', lease_seconds=300)
        process, ready, release, results = lease_recovery
        assert ready.wait(timeout=10)
        lease_claim = results.get(timeout=2)
        assert lease_claim == recovered_claim, (recovered_claim, lease_claim)
        release.set()
        process.join(15)
        assert results.get(timeout=2) == ('finished', 'done')
        print('KG_OUTBOX_MULTI_WORKER claims=%r disjoint=PASS double_process=PASS rollback_recovery=%r lease_recovery=%r PASS' % (
            claims, recovered_claim[1], lease_claim[1]))
    finally:
        env.cr.rollback()
        env['kg.edge'].sudo().search([('company_id', '=', env.company.id)]).filtered(
            lambda edge: token in str(edge.evidence or '')).unlink()
        env['kg.node'].sudo().search([('source_model', '=', 'logistics.idp.case'),
                                      ('source_id', 'in', [str(case_id) for case_id in case_ids])]).unlink()
        env['kg.outbox'].sudo().browse(outbox_ids).exists().unlink()
        env['logistics.idp.case'].sudo().browse(case_ids).exists().with_context(_skip_kg_outbox=True).unlink()
        env['res.users'].sudo().browse(user_ids).exists().unlink()
        env.cr.commit()


@tagged('post_install', '-at_install')
class TestKgOutbox(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'logistics.idp.case' not in cls.env.registry.models:
            cls.skipTest(cls, 'Logistics IDP is not installed; outbox source disabled.')
        cls.company = cls.env.company
        cls.case = cls.env['logistics.idp.case'].create({
            'name': 'KG outbox', 'source_system': 'fixture', 'source_key': 'kg-outbox',
            'source_version': '1', 'provenance': 'fixture:kg-outbox',
            'effective_date': '2026-01-01', 'company_id': cls.company.id,
        })
        cls.payload = {field: cls.case[field] for field in SOURCE_PAYLOAD_FIELDS[cls.case._name]
                       if field in cls.case._fields}
        cls.env.user.group_ids = [(4, cls.env.ref('insilos_knowledge_graph.group_kg_processor').id),
                                  (4, cls.env.ref('insilos_logistics_idp.group_logistics_admin').id)]

    def setUp(self):
        super().setUp()
        self.env['kg.outbox'].sudo().search([]).unlink()

    def _enqueue(self, event_type='UPSERT', payload=None):
        return self.env['kg.outbox'].enqueue(self.case, event_type, self.payload if payload is None else payload)

    def test_exact_model_count_and_duplicate_event(self):
        self.assertEqual([name for name in ('kg.node', 'kg.edge', 'kg.outbox') if name in self.env.registry.models],
                         ['kg.node', 'kg.edge', 'kg.outbox'])
        first = self.env['kg.outbox'].enqueue(self.case, payload=self.payload, mutation_token='same-mutation')
        self.assertEqual(first, self.env['kg.outbox'].enqueue(
            self.case, payload=self.payload, mutation_token='same-mutation'))
        self.assertNotEqual(first, self._enqueue())

    def test_payload_allowlist_and_immutable_identity(self):
        event = self._enqueue()
        with self.assertRaises(ValidationError):
            self._enqueue(payload={'password': 'secret'})
        with self.assertRaises(ValidationError):
            event.write({'payload': {}})
        self.assertNotIn('password', event.payload)

    def test_transaction_savepoint_rollback(self):
        with self.assertRaises(RuntimeError):
            with self.env.cr.savepoint():
                event = self._enqueue(payload=dict(self.payload, source_version='rollback'))
                event_id = event.id
                raise RuntimeError('rollback')
        self.assertFalse(self.env['kg.outbox'].browse(event_id).exists())
        self.assertTrue(self._enqueue().exists())

    def test_claim_lease_recovery_batch_and_due_timing(self):
        events = [self._enqueue(payload=dict(self.payload, source_version=str(index))) for index in range(3)]
        claimed = self.env['kg.outbox']._claim_batch(limit=2)
        self.assertEqual(len(claimed), 2)
        claimed.write({'claimed_at': fields.Datetime.now() - datetime.timedelta(minutes=5, seconds=1)})
        self.assertEqual(len(self.env['kg.outbox']._claim_batch(limit=2)), 2)
        events[-1].write({'state': 'RETRY', 'next_attempt_at': fields.Datetime.now() + datetime.timedelta(hours=1)})
        self.assertNotIn(events[-1], self.env['kg.outbox']._claim_batch(limit=10))

    def test_projection_replay_restart_and_delete_tombstone(self):
        event = self._enqueue()
        event._project()
        event._project()
        self.assertEqual(self.env['kg.node'].search_count([('source_model', '=', self.case._name), ('source_id', '=', str(self.case.id))]), 1)
        delete = self._enqueue('DELETE')
        delete._project()
        self.assertFalse(self.env['kg.node'].search([('source_model', '=', self.case._name), ('source_id', '=', str(self.case.id))]))
        self.env['kg.outbox']._cron_process()

    def test_retry_dead_sanitized_error_and_manager_requeue(self):
        event = self._enqueue()
        with patch.object(type(event), '_project', side_effect=RuntimeError('secret payload value')):
            for _index in range(8):
                event.write({'state': 'PENDING', 'next_attempt_at': False})
                self.env['kg.outbox']._cron_process(limit=1)
        self.assertEqual((event.state, event.attempts, event.last_error), ('DEAD', 8, 'RuntimeError'))
        manager_group = self.env.ref('insilos_knowledge_graph.group_kg_manager')
        self.env.user.group_ids = [(4, manager_group.id)]
        event.action_requeue()
        self.assertEqual((event.state, event.attempts), ('RETRY', 8))

    def test_manager_read_acl_company_rule(self):
        manager = self.env['res.users'].create({
            'name': 'KG manager', 'login': 'kg-manager', 'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
            'group_ids': [(6, 0, [self.env.ref('insilos_knowledge_graph.group_kg_manager').id])],
        })
        event = self._enqueue()
        self.assertEqual(event.with_user(manager).read(['event_hash'])[0]['event_hash'], event.event_hash)
        with self.assertRaises(AccessError):
            self.env['kg.outbox'].with_user(manager).create({})
