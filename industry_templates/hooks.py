def pre_init_hook(env):
    env.cr.execute("SELECT to_regclass('insilos_industry_template')")
    if not env.cr.fetchone()[0]:
        return
    env.cr.execute("""
        WITH duplicates AS (
            SELECT id, slug, row_number() OVER (PARTITION BY slug ORDER BY id) AS position
              FROM insilos_industry_template
             WHERE slug IS NOT NULL
        )
        UPDATE insilos_industry_template template
           SET slug = template.slug || '_duplicate_' || template.id,
               active = false
          FROM duplicates
         WHERE template.id = duplicates.id
           AND duplicates.position > 1
    """)
