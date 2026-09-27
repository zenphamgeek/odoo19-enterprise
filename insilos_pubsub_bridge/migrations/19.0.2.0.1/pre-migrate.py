TABLES = (
    "is_pubsub_event_log",
    "is_pubsub_automation_rule",
    "is_pubsub_outbound_event",
    "is_pubsub_outbound_rule",
)


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE is_pubsub_event_log
        DROP CONSTRAINT IF EXISTS is_pubsub_event_log_event_id_unique
    """)
    for table in TABLES:
        cr.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS company_id INTEGER")

    for table in TABLES:
        cr.execute(f"SELECT id FROM {table} WHERE company_id IS NULL ORDER BY id")
        missing_ids = [row[0] for row in cr.fetchall()]
        if missing_ids:
            raise RuntimeError(
                f"Cannot migrate {table}: {len(missing_ids)} legacy row(s) lack historical "
                f"company_id (IDs: {missing_ids}). Restore each row's historical company_id "
                "from backup or audited business records, then rerun the upgrade; create_uid's "
                "current company is not historical evidence."
            )
        cr.execute(f"ALTER TABLE {table} ALTER COLUMN company_id SET NOT NULL")
        cr.execute(
            f"CREATE INDEX IF NOT EXISTS {table}_company_id_idx ON {table} (company_id)"
        )
