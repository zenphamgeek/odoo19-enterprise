from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..services.projection_event import ProjectionEvent, ProjectionEventService


@tagged('post_install', '-at_install')
class TestProjectionEvent(TransactionCase):
    def test_deterministic_immutable_envelope_and_idempotent_replay(self):
        first = ProjectionEvent.create('sale.order', 7, 'UPSERT', {'b': 2, 'a': 1})
        second = ProjectionEvent.create('sale.order', '7', 'UPSERT', {'a': 1, 'b': 2})
        self.assertEqual(first, second)
        with self.assertRaises(AttributeError):
            first.cursor = '8'

        projected = []
        service = ProjectionEventService(projected.append)
        self.assertEqual(service.replay(first).status, 'PROJECTED')
        self.assertEqual(service.replay(second).attempts, 1)
        self.assertEqual(projected, [first])
        self.assertEqual(service.source_cursor('sale.order'), '7')

    def test_payload_mismatch_is_rejected(self):
        service = ProjectionEventService(lambda event: None)
        service.replay(ProjectionEvent.create('sale.order', 7, 'UPSERT', {'name': 'A'}))
        with self.assertRaisesRegex(ValueError, 'different payload'):
            service.replay(ProjectionEvent.create('sale.order', 7, 'UPSERT', {'name': 'B'}))

    def test_projection_failure_is_contained_with_retry_and_dead_letter(self):
        calls = []

        def fail(event):
            calls.append(event.event_hash)
            raise RuntimeError('graph unavailable')

        event = ProjectionEvent.create('stock.move', 9, 'UPSERT', {'id': 9})
        service = ProjectionEventService(fail, max_attempts=2)
        first = service.replay(event)
        self.assertEqual((first.status, first.attempts, first.error), ('RETRY', 1, 'graph unavailable'))
        self.assertIsNone(service.source_cursor('stock.move'))
        second = service.retry(event.event_hash)
        self.assertEqual((second.status, second.attempts), ('DEAD_LETTER', 2))
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            service.reconcile('stock.move'),
            service.reconcile('stock.move').__class__('stock.move', None, 1, 0, 0, 1),
        )
