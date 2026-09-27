# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Cross-domain stress: market shock → portfolio → collateral → liquidity.

Pure functions over already-derived numbers. Nothing here persists; a formal
decision freezes the output as attachment evidence, not as a table.
"""

import json


def hedge_ratio_status(pre_hedge_exposure, financial_hedge, policy=None):
    """FX hedge coverage against policy (target/warning/hard as ratios %).

    Ratio is hedge over gross pre-hedge exposure. Below `hard` is a breach,
    below `target` a warning — matching FX-003 semantics where 57.14% with a
    70% target and 50% floor is *Below Target*, not a hard breach.
    """
    policy = policy or {'target': 70.0, 'hard': 50.0}
    gross = abs(pre_hedge_exposure)
    ratio = abs(financial_hedge) / gross * 100.0 if gross else 100.0
    if ratio < float(policy['hard']):
        status = 'hard'
    elif ratio < float(policy['target']):
        status = 'warning'
    else:
        status = 'target'
    return {'hedge_ratio_pct': ratio, 'status': status,
            'residual_exposure': pre_hedge_exposure + financial_hedge}


def fx_hedge_policy(env, company):
    raw = env['ir.config_parameter'].sudo().get_param('treasury.fx_hedge_policy.%s' % company.id, '')
    return json.loads(raw) if raw else None


def collateral_haircuts(env, company):
    """{"government_bond": 5, "corporate_bond": 20} — percent haircut."""
    raw = env['ir.config_parameter'].sudo().get_param('treasury.collateral_haircuts.%s' % company.id, '{}')
    return json.loads(raw)


def secured_liquidity_capacity(holdings, haircuts, stress_pct=None):
    """COMB-001: stressed collateral value of pledgeable holdings.

    holdings: [{'asset_class': 'government_bond', 'market_value': 150e9}, ...]
    stress_pct: {'government_bond': -4.8, ...} applied before haircut.
    Assets without a configured haircut contribute nothing — unpledgeable by
    default is the safe direction.
    """
    stress_pct = stress_pct or {}
    rows, total = [], 0.0
    for holding in holdings:
        asset_class = holding['asset_class']
        if asset_class not in haircuts:
            continue
        stressed = holding['market_value'] * (1.0 + stress_pct.get(asset_class, 0.0) / 100.0)
        capacity = stressed * (1.0 - float(haircuts[asset_class]) / 100.0)
        rows.append({'asset_class': asset_class, 'market_value': holding['market_value'],
                     'stressed_value': stressed, 'haircut_pct': float(haircuts[asset_class]),
                     'secured_capacity': capacity})
        total += capacity
    return {'rows': rows, 'total_capacity': total}


def stress_loss(holdings, shocks_pct):
    """PF-005: loss per holding under percent shocks; positive number = loss.

    holdings: [{'asset_class'|'symbol': key, 'market_value': v}, ...]
    shocks_pct: {key: -12.0, ...}; unshocked holdings lose nothing.
    """
    total, rows = 0.0, []
    for holding in holdings:
        key = holding.get('symbol') or holding['asset_class']
        shock = shocks_pct.get(key, 0.0)
        loss = -holding['market_value'] * shock / 100.0
        rows.append({'key': key, 'loss': loss})
        total += loss
    return {'rows': rows, 'total_loss': total}


def minimum_rebalance(position_value, total_value, limit_pct, price, lot_size=100):
    """PF-004: smallest whole-lot sale bringing a weight back under limit.

    Sale proceeds stay in the portfolio as cash, so the total is unchanged
    and the required reduction is simply the excess weight times total.
    """
    required = position_value - total_value * limit_pct / 100.0
    if required <= 0:
        return {'required_value': 0.0, 'quantity': 0, 'sale_value': 0.0}
    lots = -(-required // (price * lot_size))  # ceil in whole lots
    quantity = int(lots) * lot_size
    return {'required_value': required, 'quantity': quantity, 'sale_value': quantity * price}


def combined_stress(portfolio_loss, fx_loss, liquidity_gap):
    """COMB-002: economic loss and funding need are different metrics.

    They are reported side by side, never summed — a liquidity gap is a
    financing requirement, not a P&L loss.
    """
    return {
        'economic_loss': portfolio_loss + fx_loss,
        'portfolio_loss': portfolio_loss,
        'fx_loss': fx_loss,
        'liquidity_funding_gap': liquidity_gap,
    }
