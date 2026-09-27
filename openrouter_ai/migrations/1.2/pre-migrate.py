import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        WITH ranked AS (
            SELECT id,
                   first_value(id) OVER (
                       PARTITION BY model_id
                       ORDER BY create_date NULLS LAST, id
                   ) AS canonical_id
              FROM openrouter_model
        )
        UPDATE openrouter_log log
           SET model_id = ranked.canonical_id
          FROM ranked
         WHERE log.model_id = ranked.id
           AND ranked.id != ranked.canonical_id
    """)
    logs_relinked = cr.rowcount
    cr.execute("""
        WITH ranked AS (
            SELECT id,
                   first_value(id) OVER (
                       PARTITION BY model_id
                       ORDER BY create_date NULLS LAST, id
                   ) AS canonical_id
              FROM openrouter_model
        )
        UPDATE openrouter_domain domain
           SET primary_model_id = ranked.canonical_id
          FROM ranked
         WHERE domain.primary_model_id = ranked.id
           AND ranked.id != ranked.canonical_id
    """)
    domains_relinked = cr.rowcount
    cr.execute("""
        WITH ranked AS (
            SELECT id,
                   first_value(id) OVER (
                       PARTITION BY model_id
                       ORDER BY create_date NULLS LAST, id
                   ) AS canonical_id
              FROM openrouter_model
        )
        INSERT INTO openrouter_domain_fallback_rel (domain_id, model_id)
        SELECT DISTINCT rel.domain_id, ranked.canonical_id
          FROM openrouter_domain_fallback_rel rel
          JOIN ranked ON ranked.id = rel.model_id
         WHERE ranked.id != ranked.canonical_id
        ON CONFLICT DO NOTHING
    """)
    cr.execute("""
        WITH ranked AS (
            SELECT id,
                   first_value(id) OVER (
                       PARTITION BY model_id
                       ORDER BY create_date NULLS LAST, id
                   ) AS canonical_id
              FROM openrouter_model
        )
        UPDATE is_model_data data
           SET res_id = ranked.canonical_id
          FROM ranked
         WHERE data.model = 'openrouter.model'
           AND data.res_id = ranked.id
           AND ranked.id != ranked.canonical_id
    """)
    cr.execute("""
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY model_id
                       ORDER BY create_date NULLS LAST, id
                   ) AS duplicate_rank
              FROM openrouter_model
        )
        DELETE FROM openrouter_model model
         USING ranked
         WHERE model.id = ranked.id
           AND ranked.duplicate_rank > 1
    """)
    deleted = cr.rowcount
    _logger.info(
        "OpenRouter model dedupe: logs_relinked=%d domains_relinked=%d duplicates_deleted=%d",
        logs_relinked, domains_relinked, deleted,
    )
