def migrate(cr, version):
    cr.execute("""
        ALTER TABLE logistics_idp_policy_source
        ADD COLUMN IF NOT EXISTS recorded_at timestamp without time zone
    """)
    cr.execute("""
        UPDATE logistics_idp_policy_source
           SET recorded_at = COALESCE(create_date, write_date, timezone('UTC', now()))
         WHERE recorded_at IS NULL
    """)
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
    cr.execute("ALTER TABLE logistics_idp_policy_source ALTER COLUMN recorded_at SET NOT NULL")
    cr.execute("""
        CREATE OR REPLACE FUNCTION logistics_policy_source_recorded_at_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $function$
        BEGIN
            IF NEW.recorded_at IS DISTINCT FROM OLD.recorded_at THEN
                RAISE EXCEPTION 'policy recorded_at is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    cr.execute("DROP TRIGGER IF EXISTS logistics_policy_source_recorded_at_immutable ON logistics_idp_policy_source")
    cr.execute("""
        CREATE TRIGGER logistics_policy_source_recorded_at_immutable
        BEFORE UPDATE OF recorded_at ON logistics_idp_policy_source
        FOR EACH ROW EXECUTE FUNCTION logistics_policy_source_recorded_at_immutable()
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS logistics_idp_policy_source_recorded_at_idx
        ON logistics_idp_policy_source (recorded_at)
    """)
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
    cr.execute("DROP TRIGGER IF EXISTS logistics_policy_source_active_overlap_guard ON logistics_idp_policy_source")
    cr.execute("""
        CREATE TRIGGER logistics_policy_source_active_overlap_guard
        BEFORE INSERT OR UPDATE OF state, company_id, code, jurisdiction, regime,
                                   effective_from, effective_to
        ON logistics_idp_policy_source
        FOR EACH ROW EXECUTE FUNCTION logistics_policy_source_active_overlap_guard()
    """)
