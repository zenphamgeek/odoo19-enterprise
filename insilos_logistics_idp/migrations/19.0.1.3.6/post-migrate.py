def migrate(cr, version):
    cr.execute("""
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
    """)
