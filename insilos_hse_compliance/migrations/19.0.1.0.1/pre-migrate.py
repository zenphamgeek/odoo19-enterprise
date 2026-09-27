def migrate(cr, version):
    cr.execute("""
        SELECT event_id, array_agg(id ORDER BY id)
          FROM is_hse_compliance_event
         GROUP BY event_id
        HAVING count(*) > 1
         ORDER BY event_id
    """)
    duplicates = cr.fetchall()
    if duplicates:
        details = ', '.join(
            '%s (IDs: %s)' % (event_id, ','.join(map(str, ids)))
            for event_id, ids in duplicates
        )
        raise RuntimeError(
            'Cannot enable HSE webhook replay protection: duplicate event_id records exist: '
            + details
            + '. Reconcile each event through audited HSE review; no record was changed.'
        )
