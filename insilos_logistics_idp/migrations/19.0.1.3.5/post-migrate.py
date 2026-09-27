def migrate(cr, version):
    cr.execute("""
        CREATE OR REPLACE FUNCTION logistics_idp_completed_run_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.completed_at IS NOT NULL AND (TG_OP = 'DELETE'
               OR NEW.case_id IS DISTINCT FROM OLD.case_id
               OR NEW.document_id IS DISTINCT FROM OLD.document_id
               OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
               OR NEW.confidence IS DISTINCT FROM OLD.confidence
               OR NEW.duration_seconds IS DISTINCT FROM OLD.duration_seconds
               OR NEW.provider IS DISTINCT FROM OLD.provider
               OR NEW.model_version IS DISTINCT FROM OLD.model_version
               OR NEW.schema_version IS DISTINCT FROM OLD.schema_version
               OR NEW.prompt_version IS DISTINCT FROM OLD.prompt_version
               OR NEW.template_version IS DISTINCT FROM OLD.template_version
               OR NEW.template_hash IS DISTINCT FROM OLD.template_hash
               OR NEW.started_at IS DISTINCT FROM OLD.started_at
               OR NEW.completed_at IS DISTINCT FROM OLD.completed_at
               OR NEW.status IS DISTINCT FROM OLD.status
               OR NEW.error IS DISTINCT FROM OLD.error
               OR NEW.payload IS DISTINCT FROM OLD.payload
               OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash
               OR NEW.audit_actor_id IS DISTINCT FROM OLD.audit_actor_id
               OR NEW.audit_service IS DISTINCT FROM OLD.audit_service
               OR NEW.audit_input_hash IS DISTINCT FROM OLD.audit_input_hash) THEN
                RAISE EXCEPTION 'Completed extraction runs are immutable; append a new run instead.'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE OR REPLACE FUNCTION logistics_idp_output_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' OR NEW.case_id IS DISTINCT FROM OLD.case_id
               OR NEW.run_id IS DISTINCT FROM OLD.run_id
               OR NEW.output_type IS DISTINCT FROM OLD.output_type
               OR NEW.version IS DISTINCT FROM OLD.version
               OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
               OR NEW.supersedes_id IS DISTINCT FROM OLD.supersedes_id
               OR NEW.attachment_id IS DISTINCT FROM OLD.attachment_id
               OR NEW.artifact_sha256 IS DISTINCT FROM OLD.artifact_sha256
               OR NEW.artifact_mimetype IS DISTINCT FROM OLD.artifact_mimetype
               OR NEW.payload IS DISTINCT FROM OLD.payload
               OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash
               OR NEW.audit_actor_id IS DISTINCT FROM OLD.audit_actor_id
               OR NEW.audit_service IS DISTINCT FROM OLD.audit_service
               OR NEW.audit_input_hash IS DISTINCT FROM OLD.audit_input_hash
               OR (NEW.status IS DISTINCT FROM OLD.status
                   AND NOT (OLD.status = 'generated' AND NEW.status = 'superseded')) THEN
                RAISE EXCEPTION 'Generated outputs are immutable; append a new version instead.'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
