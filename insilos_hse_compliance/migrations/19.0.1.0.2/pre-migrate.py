def migrate(cr, version):
    cr.execute("""
        ALTER TABLE is_hse_legal_document
        ADD COLUMN IF NOT EXISTS source_content_sha256 varchar,
        ADD COLUMN IF NOT EXISTS source_version varchar
    """)
