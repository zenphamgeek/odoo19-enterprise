def migrate(cr, version):
    cr.execute("""
        ALTER TABLE is_chemical_permit_quota_line
        ADD COLUMN IF NOT EXISTS dossier_line_id integer
    """)
    cr.execute("""
        WITH candidates AS (
            SELECT ledger.id, min(dossier_line.id) AS dossier_line_id
              FROM is_chemical_permit_quota_line ledger
              JOIN is_chemical_permit_quota quota ON quota.id = ledger.quota_id
              JOIN is_chemical_compliance_dossier_line dossier_line
                ON dossier_line.dossier_id = ledger.dossier_id
               AND dossier_line.permit_id = quota.permit_id
               AND dossier_line.chemical_substance_id = quota.chemical_substance_id
             WHERE ledger.dossier_line_id IS NULL
             GROUP BY ledger.id
            HAVING count(*) = 1
        )
        UPDATE is_chemical_permit_quota_line ledger
           SET dossier_line_id = candidates.dossier_line_id
          FROM candidates
         WHERE ledger.id = candidates.id
    """)
    cr.execute("""
        SELECT 1
          FROM is_chemical_permit_quota_line
         WHERE quota_id IS NOT NULL AND dossier_line_id IS NOT NULL
         GROUP BY quota_id, dossier_line_id
        HAVING count(*) > 1
         LIMIT 1
    """)
    if not cr.fetchone():
        cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS chemical_permit_quota_line_quota_dossier_line_uniq
                ON is_chemical_permit_quota_line (quota_id, dossier_line_id)
             WHERE quota_id IS NOT NULL AND dossier_line_id IS NOT NULL
        """)
