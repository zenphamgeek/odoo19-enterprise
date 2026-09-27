def migrate(cr, version):
    cr.execute("""
        CREATE OR REPLACE FUNCTION logistics_idp_completed_run_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.completed_at IS NOT NULL AND (TG_OP = 'DELETE' OR NEW.payload IS DISTINCT FROM OLD.payload
               OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash OR NEW.model_version IS DISTINCT FROM OLD.model_version
               OR NEW.schema_version IS DISTINCT FROM OLD.schema_version OR NEW.prompt_version IS DISTINCT FROM OLD.prompt_version
               OR NEW.completed_at IS DISTINCT FROM OLD.completed_at OR NEW.status IS DISTINCT FROM OLD.status) THEN
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
            IF TG_OP = 'DELETE' OR NEW.payload IS DISTINCT FROM OLD.payload
               OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash
               OR NEW.version IS DISTINCT FROM OLD.version
               OR NEW.attachment_id IS DISTINCT FROM OLD.attachment_id
               OR NEW.artifact_sha256 IS DISTINCT FROM OLD.artifact_sha256
               OR NEW.artifact_mimetype IS DISTINCT FROM OLD.artifact_mimetype THEN
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
