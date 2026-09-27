def migrate(cr, version):
    cr.execute("ALTER TABLE logistics_idp_extraction_run ADD COLUMN IF NOT EXISTS retry_count integer")
    cr.execute("ALTER TABLE logistics_idp_extraction_run DISABLE TRIGGER logistics_idp_completed_run_immutable")
    try:
        cr.execute("""
            WITH numbered AS (
                SELECT id, row_number() OVER (PARTITION BY document_id ORDER BY attempt_number, id) - 1 AS retry_count
                  FROM logistics_idp_extraction_run
            )
            UPDATE logistics_idp_extraction_run run
               SET retry_count = numbered.retry_count
              FROM numbered
             WHERE run.id = numbered.id
               AND run.retry_count IS NULL
        """)
    finally:
        cr.execute("ALTER TABLE logistics_idp_extraction_run ENABLE TRIGGER logistics_idp_completed_run_immutable")
    cr.execute("ALTER TABLE logistics_idp_extraction_run ALTER COLUMN retry_count SET DEFAULT 0")
    cr.execute("ALTER TABLE logistics_idp_extraction_run ALTER COLUMN retry_count SET NOT NULL")
