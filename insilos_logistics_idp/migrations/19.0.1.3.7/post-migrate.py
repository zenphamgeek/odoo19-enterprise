def migrate(cr, version):
    cr.execute("""
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
    """)
