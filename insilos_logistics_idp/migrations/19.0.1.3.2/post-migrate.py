def migrate(cr, version):
    cr.execute("""
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
    """)
