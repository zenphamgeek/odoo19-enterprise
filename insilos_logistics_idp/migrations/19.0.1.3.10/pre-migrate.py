import logging


_logger = logging.getLogger(__name__)


_MIGRATION = '19.0.1.3.10'
_SOURCE_TABLE = 'logistics_idp_extracted_line'


def migrate(cr, version):
    cr.execute("""
        CREATE TABLE IF NOT EXISTS logistics_idp_migration_orphan_archive (
            migration varchar NOT NULL,
            source_table varchar NOT NULL,
            source_id integer NOT NULL,
            archived_at timestamptz NOT NULL DEFAULT statement_timestamp(),
            payload jsonb NOT NULL,
            PRIMARY KEY (migration, source_table, source_id)
        )
    """)
    cr.execute("""
        WITH orphan AS (
            SELECT line.*
              FROM logistics_idp_extracted_line line
              LEFT JOIN logistics_idp_document document ON document.id = line.document_id
             WHERE document.id IS NULL
        ), archived AS (
            INSERT INTO logistics_idp_migration_orphan_archive
                        (migration, source_table, source_id, payload)
                 SELECT %s, %s, id, to_jsonb(orphan)
                   FROM orphan
            ON CONFLICT (migration, source_table, source_id)
            DO UPDATE SET payload = EXCLUDED.payload
            RETURNING source_id
        )
        DELETE FROM logistics_idp_extracted_line line
         USING archived
         WHERE line.id = archived.source_id
    """, [_MIGRATION, _SOURCE_TABLE])
    _logger.info("Archived and removed %s orphan Logistics extracted lines", cr.rowcount)
