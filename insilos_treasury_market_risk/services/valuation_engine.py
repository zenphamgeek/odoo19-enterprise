# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Read governed holdings and reconcile them to accounting products."""


def portfolio_valuation(env, company_ids):
    """Return marked positions with product mapping gaps made explicit."""
    positions = env['capital.position'].search([
        ('company_id', 'in', list(company_ids)), ('quantity', '!=', 0),
    ])
    products = env['product.product'].search([('default_code', 'in', positions.mapped('symbol'))])
    by_code = {product.default_code: product for product in products}
    rows = []
    for position in positions:
        product = by_code.get(position.symbol)
        rows.append({
            'position_id': position.id, 'portfolio_id': position.portfolio_id.id,
            'symbol': position.symbol, 'quantity': position.quantity,
            'market_value': position.base_market_value, 'mark_status': position.mark_status,
            'product_id': product.id if product else False,
            'mapping_status': 'mapped' if product else 'unmapped',
        })
    return rows


def fixed_income_metrics(face_value, coupon_rate, years_to_maturity, yield_rate):
    """Plain annual-coupon bond measures; inputs come from standard product config."""
    if years_to_maturity <= 0:
        return {'price': face_value, 'duration': 0.0, 'modified_duration': 0.0, 'dv01': 0.0}
    coupon = face_value * coupon_rate
    cashflows = [(year, coupon + (face_value if year == years_to_maturity else 0.0)) for year in range(1, years_to_maturity + 1)]
    price = sum(cashflow / (1 + yield_rate) ** year for year, cashflow in cashflows)
    duration = sum(year * cashflow / (1 + yield_rate) ** year for year, cashflow in cashflows) / price
    modified = duration / (1 + yield_rate)
    return {'price': price, 'duration': duration, 'modified_duration': modified, 'dv01': modified * price / 10000}
