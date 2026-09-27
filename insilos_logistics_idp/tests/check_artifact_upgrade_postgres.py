"""Run via tools/with_local_credentials.py --solo-dev-db; temporary DDL, rollback only."""
import ast
import os
from pathlib import Path
import runpy

import psycopg2
from psycopg2 import errors


def main():
    module = Path(__file__).resolve().parents[1]
    manifest = ast.literal_eval((module / '__manifest__.py').read_text())
    assert manifest['version'] == '19.0.1.3.12'
    ai_manifest = ast.literal_eval((module.parent / 'ai/__manifest__.py').read_text())
    assert ai_manifest['version'] == '1.1'
    migrate = runpy.run_path(str(module / 'migrations' / manifest['version'] / 'post-migrate.py'))['migrate']
    assert os.environ['PGDATABASE'] == 'insilos_migration_digiforce_v2'
    assert os.environ['PGHOST'] == '127.0.0.1' and os.environ['PGPORT'] == '5434'
    connection = psycopg2.connect(dbname=os.environ['PGDATABASE'])
    try:
        cr = connection.cursor()
        cr.execute('SELECT current_database(), inet_server_addr(), inet_server_port()')
        assert cr.fetchone() == ('insilos_migration_digiforce_v2', '127.0.0.1', 5434)
        print('DB=insilos_migration_digiforce_v2 owner=artifact-upgrade web/IAP=unused max_reruns=1')
        cr.execute("SET LOCAL statement_timeout = '20s'")
        cr.execute('CREATE TEMP TABLE ir_attachment (id integer PRIMARY KEY, name text) ON COMMIT DROP')
        cr.execute('CREATE TEMP TABLE logistics_idp_output (attachment_id integer) ON COMMIT DROP')
        cr.execute('SET LOCAL search_path = pg_temp')
        cr.execute('''CREATE FUNCTION pg_temp.logistics_idp_output_artifact_immutable()
            RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN OLD; END; $$''')
        cr.execute('''CREATE TRIGGER logistics_idp_output_artifact_immutable
            BEFORE UPDATE OR DELETE ON ir_attachment FOR EACH ROW
            EXECUTE FUNCTION pg_temp.logistics_idp_output_artifact_immutable()''')
        cr.execute("INSERT INTO ir_attachment VALUES (1, 'old'), (2, 'protected')")
        cr.execute('INSERT INTO logistics_idp_output VALUES (2)')
        cr.execute("UPDATE ir_attachment SET name = 'lost' WHERE id = 1 RETURNING name")
        assert cr.fetchone() == ('old',), 'Old trigger must reproduce discarded UPDATE'
        migrate(cr, '19.0.1.3.11')
        migrate(cr, '19.0.1.3.11')
        cr.execute("UPDATE ir_attachment SET name = 'saved' WHERE id = 1 RETURNING name")
        assert cr.fetchone() == ('saved',)
        for sql in ("UPDATE ir_attachment SET name = 'tampered' WHERE id = 2", 'DELETE FROM ir_attachment WHERE id = 2'):
            cr.execute('SAVEPOINT immutable')
            try:
                cr.execute(sql)
            except errors.ObjectNotInPrerequisiteState:
                cr.execute('ROLLBACK TO SAVEPOINT immutable')
            else:
                raise AssertionError('Generated artifact mutation was allowed')
        cr.execute('DELETE FROM ir_attachment WHERE id = 1 RETURNING id')
        assert cr.fetchone() == (1,)
        cr.execute('SELECT id, name FROM ir_attachment')
        assert cr.fetchall() == [(2, 'protected')]
        print('PASS: version path; old UPDATE reproduced; repeated migration; UPDATE/DELETE allowed only for ordinary attachments')
    finally:
        connection.rollback()
        connection.close()
        print('ROLLBACK: temporary fixtures 0/0; persistent mutations=0; DB/process created=0')


if __name__ == '__main__':
    main()
