# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Portfolio policy limits read from company-scoped JSON configuration."""

import json

from . import valuation_engine


def portfolio_metrics(env, company):
    """Concentration and data-quality metrics from governed holdings.

    All values are percentages so limit policies read naturally:
    `single_name_pct` largest position weight, `stale_position_pct` share of
    positions without a fresh mark, `unmapped_position_pct` share without an
    accounting product mapping.
    """
    rows = valuation_engine.portfolio_valuation(env, company.ids)
    if not rows:
        return {}
    total = sum(abs(row['market_value']) for row in rows)
    largest = max(abs(row['market_value']) for row in rows)
    count = len(rows)
    return {
        'single_name_pct': largest / total * 100.0 if total else 0.0,
        'stale_position_pct': sum(1 for row in rows if row['mark_status'] != 'fresh') / count * 100.0,
        'unmapped_position_pct': sum(1 for row in rows if row['mapping_status'] != 'mapped') / count * 100.0,
    }


def limit_utilization(env, company, metrics):
    """Evaluate fixed policy limits without creating a risk.limit table.

    Config shape: {"single_name_pct": {"target": 20, "warning": 30, "hard": 40}}.
    Missing policy is visible as `unconfigured`, never silently green.
    """
    raw = env['ir.config_parameter'].sudo().get_param('treasury.risk_limits.%s' % company.id, '{}')
    policies = json.loads(raw)
    results = []
    for name, value in metrics.items():
        policy = policies.get(name)
        if not policy:
            results.append({'metric': name, 'value': value, 'status': 'unconfigured', 'utilization': None})
            continue
        hard = float(policy['hard'])
        status = 'hard' if value >= hard else 'warning' if value >= float(policy['warning']) else 'target'
        results.append({'metric': name, 'value': value, 'status': status, 'utilization': value / hard if hard else None})
    return results
