def migrate(cr, version):
    cr.execute("""
        SELECT left_row.id, right_row.id
          FROM logistics_idp_policy_source left_row
          JOIN logistics_idp_policy_source right_row
            ON left_row.id < right_row.id
           AND left_row.state = 'active' AND right_row.state = 'active'
           AND left_row.company_id IS NOT DISTINCT FROM right_row.company_id
           AND left_row.code = right_row.code
           AND left_row.jurisdiction = right_row.jurisdiction
           AND left_row.regime = right_row.regime
           AND left_row.effective_from <= COALESCE(right_row.effective_to, 'infinity'::date)
           AND right_row.effective_from <= COALESCE(left_row.effective_to, 'infinity'::date)
         LIMIT 1
    """)
    overlap = cr.fetchone()
    if overlap:
        raise RuntimeError('Active policy overlap blocks migration: %s/%s' % overlap)
    cr.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    cr.execute("""
        ALTER TABLE logistics_idp_policy_source
        DROP CONSTRAINT IF EXISTS logistics_policy_source_active_bucket_no_overlap
    """)
    cr.execute("""
        ALTER TABLE logistics_idp_policy_source
        ADD CONSTRAINT logistics_policy_source_active_bucket_no_overlap
        EXCLUDE USING gist (
            (COALESCE(company_id, 0)) WITH =,
            code WITH =,
            jurisdiction WITH =,
            regime WITH =,
            daterange(effective_from, effective_to, '[]') WITH &&
        ) WHERE (state = 'active')
    """)
