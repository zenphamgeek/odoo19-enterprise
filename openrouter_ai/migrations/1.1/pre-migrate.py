import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE openrouter_log
           SET operation_id = 'legacy-openrouter-log:' || id
         WHERE operation_id IS NULL OR btrim(operation_id) = ''
    """)
    backfilled = cr.rowcount
    cr.execute("""
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY operation_id
                       ORDER BY
                           num_nonnulls(domain_id, model_id, used_model_name, prompt_tokens,
                                        completion_tokens, total_tokens, total_cost, execution_time,
                                        error_message, tenant_id, company_id, policy_version,
                                        credit_budget) DESC,
                           create_date NULLS LAST,
                           id
                   ) AS duplicate_rank
              FROM openrouter_log
        )
        UPDATE openrouter_log log
           SET operation_id = log.operation_id || ':legacy-duplicate:' || log.id
          FROM ranked
         WHERE ranked.id = log.id AND ranked.duplicate_rank > 1
    """)
    preserved_duplicates = cr.rowcount
    _logger.info(
        "OpenRouter audit migration: backfilled_missing=%d preserved_duplicate_rows=%d deleted=0",
        backfilled, preserved_duplicates,
    )
