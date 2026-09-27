def migrate(cr, version):
    cr.execute("""
        UPDATE is_hse_obligation
           SET compliance_status = 'not_assessed'
         WHERE compliance_status = 'compliant'
    """)
