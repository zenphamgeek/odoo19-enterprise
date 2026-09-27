import logging


_logger = logging.getLogger(__name__)


_MIGRATION = '19.0.1.3.11'
_SOURCE_TABLE = 'mail_tracking_value'


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
        WITH orphan AS MATERIALIZED (
            SELECT tracking.*
              FROM mail_tracking_value tracking
              JOIN is_model_fields field
                ON field.id = tracking.field_id
               AND field.model = 'logistics.idp.case'
             WHERE NOT EXISTS (
                       SELECT 1
                         FROM mail_message message
                        WHERE message.id = tracking.mail_message_id
                   )
               FOR UPDATE OF tracking
        ), archived AS (
            INSERT INTO logistics_idp_migration_orphan_archive
                        (migration, source_table, source_id, payload)
                 SELECT %s, %s, id, to_jsonb(orphan)
                   FROM orphan
            ON CONFLICT (migration, source_table, source_id) DO NOTHING
            RETURNING source_id
        ), preserved AS (
            SELECT source_id FROM archived
            UNION ALL
            SELECT archive.source_id
              FROM logistics_idp_migration_orphan_archive archive
              JOIN orphan ON orphan.id = archive.source_id
                         AND archive.payload = to_jsonb(orphan)
             WHERE archive.migration = %s
               AND archive.source_table = %s
        )
        DELETE FROM mail_tracking_value tracking
         USING preserved
         WHERE tracking.id = preserved.source_id
    """, [_MIGRATION, _SOURCE_TABLE, _MIGRATION, _SOURCE_TABLE])
    _logger.info("Archived and removed %s orphan Logistics mail tracking values", cr.rowcount)
