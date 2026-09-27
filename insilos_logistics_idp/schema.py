def ensure_database_invariants(cr):
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
        CREATE OR REPLACE FUNCTION logistics_policy_source_active_overlap_guard()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.state = 'active' THEN
                -- The gate prevents reversed multi-statement bucket acquisition from deadlocking.
                PERFORM pg_advisory_xact_lock(hashtextextended(
                    'logistics-policy-source-active-overlap-gate', 0));
                PERFORM pg_advisory_xact_lock(hashtextextended(
                    jsonb_build_array(NEW.company_id, NEW.code, NEW.jurisdiction, NEW.regime)::text, 0));
            END IF;
            RETURN NEW;
        END;
        $$;
        DROP TRIGGER IF EXISTS logistics_policy_source_active_overlap_guard ON logistics_idp_policy_source;
        CREATE TRIGGER logistics_policy_source_active_overlap_guard
        BEFORE INSERT OR UPDATE OF state, company_id, code, jurisdiction, regime,
                                   effective_from, effective_to
        ON logistics_idp_policy_source
        FOR EACH ROW EXECUTE FUNCTION logistics_policy_source_active_overlap_guard();
    """)
    cr.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM pg_constraint
                 WHERE conrelid = 'logistics_idp_policy_source'::regclass
                   AND conname = 'logistics_policy_source_active_bucket_no_overlap'
            ) THEN
                ALTER TABLE logistics_idp_policy_source
                ADD CONSTRAINT logistics_policy_source_active_bucket_no_overlap
                EXCLUDE USING gist (
                    (COALESCE(company_id, 0)) WITH =,
                    code WITH =,
                    jurisdiction WITH =,
                    regime WITH =,
                    daterange(effective_from, effective_to, '[]') WITH &&
                ) WHERE (state = 'active');
            END IF;
        END
        $$;
    """)
    cr.execute("""
        CREATE OR REPLACE FUNCTION logistics_policy_source_recorded_at_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.recorded_at IS DISTINCT FROM OLD.recorded_at THEN
                RAISE EXCEPTION 'policy recorded_at is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$;
        DROP TRIGGER IF EXISTS logistics_policy_source_recorded_at_immutable ON logistics_idp_policy_source;
        CREATE TRIGGER logistics_policy_source_recorded_at_immutable
        BEFORE UPDATE OF recorded_at ON logistics_idp_policy_source
        FOR EACH ROW EXECUTE FUNCTION logistics_policy_source_recorded_at_immutable();

        CREATE OR REPLACE FUNCTION logistics_idp_policy_decision_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Policy decisions are immutable; append a new decision instead.'
                USING ERRCODE = '55000';
        END;
        $$;
        DROP TRIGGER IF EXISTS logistics_idp_policy_decision_immutable ON logistics_idp_policy_decision;
        CREATE TRIGGER logistics_idp_policy_decision_immutable
        BEFORE UPDATE OR DELETE ON logistics_idp_policy_decision
        FOR EACH ROW EXECUTE FUNCTION logistics_idp_policy_decision_immutable();

        CREATE OR REPLACE FUNCTION logistics_idp_completed_run_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.completed_at IS NOT NULL AND TG_OP IN ('UPDATE', 'DELETE') THEN
                RAISE EXCEPTION 'Completed extraction runs are immutable; append a new run instead.'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$;
        DROP TRIGGER IF EXISTS logistics_idp_completed_run_immutable ON logistics_idp_extraction_run;
        CREATE TRIGGER logistics_idp_completed_run_immutable
        BEFORE UPDATE OR DELETE ON logistics_idp_extraction_run
        FOR EACH ROW EXECUTE FUNCTION logistics_idp_completed_run_immutable();

        CREATE OR REPLACE FUNCTION logistics_idp_output_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' OR NOT (
                OLD.status = 'generated' AND NEW.status = 'superseded'
                AND ROW(NEW.id, NEW.audit_actor_id, NEW.case_id, NEW.run_id, NEW.version,
                        NEW.supersedes_id, NEW.attachment_id, NEW.create_uid, NEW.write_uid,
                        NEW.payload_hash, NEW.audit_service, NEW.audit_input_hash, NEW.output_type,
                        NEW.idempotency_key, NEW.artifact_sha256, NEW.artifact_mimetype, NEW.payload,
                        NEW.create_date, NEW.write_date)
                    IS NOT DISTINCT FROM
                    ROW(OLD.id, OLD.audit_actor_id, OLD.case_id, OLD.run_id, OLD.version,
                        OLD.supersedes_id, OLD.attachment_id, OLD.create_uid, OLD.write_uid,
                        OLD.payload_hash, OLD.audit_service, OLD.audit_input_hash, OLD.output_type,
                        OLD.idempotency_key, OLD.artifact_sha256, OLD.artifact_mimetype, OLD.payload,
                        OLD.create_date, OLD.write_date)
            ) THEN
                RAISE EXCEPTION 'Generated outputs are immutable; append a new version instead.'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$;
        DROP TRIGGER IF EXISTS logistics_idp_output_immutable ON logistics_idp_output;
        CREATE TRIGGER logistics_idp_output_immutable
        BEFORE UPDATE OR DELETE ON logistics_idp_output
        FOR EACH ROW EXECUTE FUNCTION logistics_idp_output_immutable();

        CREATE OR REPLACE FUNCTION logistics_idp_output_protected_column_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Generated outputs are immutable; append a new version instead.'
                USING ERRCODE = '55000';
        END;
        $$;
        DROP TRIGGER IF EXISTS logistics_idp_output_protected_column_immutable ON logistics_idp_output;
        CREATE TRIGGER logistics_idp_output_protected_column_immutable
        BEFORE UPDATE OF id, audit_actor_id, case_id, run_id, version, supersedes_id, attachment_id,
            create_uid, write_uid, payload_hash, audit_service, audit_input_hash, output_type,
            idempotency_key, artifact_sha256, artifact_mimetype, payload, create_date, write_date
        ON logistics_idp_output
        FOR EACH ROW EXECUTE FUNCTION logistics_idp_output_protected_column_immutable();

        CREATE OR REPLACE FUNCTION logistics_idp_output_artifact_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM logistics_idp_output WHERE attachment_id = OLD.id) THEN
                RAISE EXCEPTION 'Generated output artifacts are immutable.' USING ERRCODE = '55000';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$;
        DROP TRIGGER IF EXISTS logistics_idp_output_artifact_immutable ON ir_attachment;
        CREATE TRIGGER logistics_idp_output_artifact_immutable
        BEFORE UPDATE OR DELETE ON ir_attachment
        FOR EACH ROW EXECUTE FUNCTION logistics_idp_output_artifact_immutable();
    """)
