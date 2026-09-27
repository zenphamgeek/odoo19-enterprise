def migrate(cr, version):
    cr.execute("ALTER TABLE is_pubsub_event_log ADD COLUMN IF NOT EXISTS consumer varchar")
    cr.execute("UPDATE is_pubsub_event_log SET consumer = 'default' WHERE consumer IS NULL")
    cr.execute("ALTER TABLE is_pubsub_event_log DROP CONSTRAINT IF EXISTS is_pubsub_event_log_company_event_id_unique")
    cr.execute("ALTER TABLE is_pubsub_outbound_event ADD COLUMN IF NOT EXISTS event_id varchar")
    cr.execute("UPDATE is_pubsub_outbound_event SET event_id = COALESCE(name, 'OUT') || ':' || id")
