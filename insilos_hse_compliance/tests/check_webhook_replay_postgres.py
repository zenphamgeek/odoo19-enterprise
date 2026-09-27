"""Rollback-only local PostgreSQL check; run via with_local_credentials.py --solo-dev-db."""
import ast
import hashlib
import hmac
from pathlib import Path
from types import SimpleNamespace

import psycopg2


def main():
    source = Path(__file__).resolve().parents[1] / 'controllers' / 'webhook.py'
    tree = ast.parse(source.read_text())
    controller = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    controller.bases = []
    for method in controller.body:
        if isinstance(method, ast.FunctionDef):
            method.decorator_list = []
    namespace = {'hashlib': hashlib, 'hmac': hmac}
    exec(compile(ast.Module(body=[controller], type_ignores=[]), str(source), 'exec'), namespace)
    handler = namespace['HSEWebhookController']()
    connection = psycopg2.connect(host='127.0.0.1', port=5434)
    try:
        cr = connection.cursor()
        cr.execute('SELECT current_database()')
        assert cr.fetchone()[0] == 'insilos_migration_digiforce_v2'
        cr.execute("SET LOCAL lock_timeout = '3s'")
        cr.execute('SELECT count(*), count(*) - count(DISTINCT event_id) FROM public.is_hse_compliance_event')
        before = cr.fetchone()
        namespace['request'] = SimpleNamespace(env=SimpleNamespace(cr=cr))
        baseline = handler._replay_protection_ready()
        print('DB=insilos_migration_digiforce_v2 baseline_ready=%s counts=%s' % (baseline, before))
        # Temporary shadow relation leaves existing duplicate records untouched.
        cr.execute('CREATE TEMP TABLE is_hse_compliance_event (event_id text NOT NULL) ON COMMIT DROP')
        assert not handler._replay_protection_ready()

        class Env:
            def __init__(self):
                self.cr = cr

            def __getitem__(self, model):
                assert model == 'ir.config_parameter', 'Unexpected model access: ' + model
                return SimpleNamespace(sudo=lambda: SimpleNamespace(get_param=lambda key: 'fixture-secret'))

        body = b'{"event_id":"rollback-fixture"}'
        signature = 'sha256=' + hmac.new(b'fixture-secret', body, hashlib.sha256).hexdigest()
        namespace['request'] = SimpleNamespace(
            env=Env(),
            httprequest=SimpleNamespace(get_data=lambda: body, headers={
                'X-HSE-Signature': signature, 'X-CEMS-Signature': signature,
            }),
            make_json_response=lambda data, status=200: (status, data),
        )
        for receive in (handler.receive_hse_event, handler.receive_cems_telemetry):
            assert receive() == (503, {'status': 'error', 'message': 'Replay protection unavailable'})
        print('ABSENT: both signed routes 503; no business model access')
        cr.execute('ALTER TABLE pg_temp.is_hse_compliance_event ADD CONSTRAINT replay_unique UNIQUE(event_id)')
        assert handler._replay_protection_ready()
        cr.execute("INSERT INTO pg_temp.is_hse_compliance_event VALUES ('rollback-fixture')")
        cr.execute('SAVEPOINT duplicate_check')
        try:
            cr.execute("INSERT INTO pg_temp.is_hse_compliance_event VALUES ('rollback-fixture')")
        except psycopg2.errors.UniqueViolation:
            cr.execute('ROLLBACK TO SAVEPOINT duplicate_check')
        else:
            raise AssertionError('PostgreSQL accepted duplicate')
        print('PRESENT: validated immediate UNIQUE(event_id); duplicate SQLSTATE 23505')
        cr.execute('ALTER TABLE pg_temp.is_hse_compliance_event DROP CONSTRAINT replay_unique')
        assert not handler._replay_protection_ready()
        cr.execute('ALTER TABLE pg_temp.is_hse_compliance_event ADD CONSTRAINT replay_deferred UNIQUE(event_id) DEFERRABLE')
        assert not handler._replay_protection_ready()
        print('DEFERRABLE: rejected')
        connection.rollback()
        cr.execute('SELECT count(*), count(*) - count(DISTINCT event_id) FROM public.is_hse_compliance_event')
        assert cr.fetchone() == before
        assert handler._replay_protection_ready() == baseline
        print('ROLLBACK: public counts/constraint unchanged; temporary relation removed')
    finally:
        connection.rollback()
        connection.close()


if __name__ == '__main__':
    main()
