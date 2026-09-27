# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Liquidity ladder đọc từ sổ cái; không tạo snapshot hay bảng cash-flow riêng."""

from datetime import timedelta

from odoo import fields

DEFAULT_HORIZONS = (7, 14, 30, 60, 90, 180, 365)


def _date(value):
    return fields.Date.to_date(value) if isinstance(value, str) else value


def opening_liquidity(env, company_ids):
    """Số dư cash/bank đã post, theo company currency.

    Restricted cash không tự suy đoán: tag `Restricted` là quy ước vận hành,
    nên chỉ loại khi tenant đã gán analytic tag đó trên dòng bút toán.
    """
    companies = env['res.company'].browse(company_ids)
    domain = [
        ('parent_state', '=', 'posted'), ('company_id', 'in', companies.ids),
        ('account_id.account_type', 'in', ('asset_cash', 'liability_credit_card')),
    ]
    restricted = env['account.account.tag'].search(
        [('name', '=', 'Restricted'), ('applicability', '=', 'accounts')], limit=1)
    if restricted:
        domain.append(('account_id.tag_ids', 'not in', restricted.ids))
    groups = env['account.move.line']._read_group(
        domain, groupby=['company_id'], aggregates=['balance:sum'],
    )
    amounts = {company.id: balance for company, balance in groups}
    return [
        {'company_id': company.id, 'company_name': company.name, 'currency_id': company.currency_id.id,
         'currency_name': company.currency_id.name, 'amount': amounts.get(company.id, 0.0)}
        for company in companies
    ]


def ladder(env, company_ids, horizons=DEFAULT_HORIZONS, as_of=None, ar_delay_days=0):
    """AR/AP open balance + loan schedule theo maturity; inflow dương, outflow âm.

    `amount_residual` là company currency, nên khi gộp nhiều company mọi dòng
    được quy về currency của company đầu tiên qua `_convert` — cùng đường
    accounting dùng, không tự chế tỷ giá. `ar_delay_days` dời inflow AR về
    sau (kịch bản khách trả trễ), không đụng outflow.
    """
    as_of = _date(as_of or fields.Date.context_today(env['account.move.line']))
    horizons = tuple(sorted(set(horizons)))
    companies = env['res.company'].browse(list(company_ids))
    target = companies[:1].currency_id
    rows = {horizon: {'horizon': horizon, 'inflow': 0.0, 'outflow': 0.0} for horizon in horizons}

    def add(company, maturity, amount, delay=0):
        if not amount:
            return
        if company.currency_id != target:
            amount = company.currency_id._convert(amount, target, company, as_of, round=False)
        days = max((_date(maturity) or as_of) - as_of, timedelta(0)).days + delay
        horizon = next((value for value in horizons if days <= value), horizons[-1])
        rows[horizon]['inflow' if amount >= 0 else 'outflow'] += amount

    groups = env['account.move.line']._read_group(
        [('parent_state', '=', 'posted'), ('company_id', 'in', companies.ids),
         ('amount_residual', '!=', 0),
         ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable'))],
        groupby=['company_id', 'account_id.account_type', 'date_maturity:day'],
        aggregates=['amount_residual:sum'],
    )
    for company, account_type, maturity, amount in groups:
        delay = ar_delay_days if account_type == 'asset_receivable' else 0
        add(company, maturity, amount, delay)

    # Fixed-income schedules use the existing loan lines. Principal and interest
    # remain distinct aggregates until their common liquidity bucket is assigned.
    loan_groups = env['account.loan.line']._read_group(
        [('loan_id.state', '=', 'running'), ('company_id', 'in', companies.ids)],
        groupby=['company_id', 'date:day'], aggregates=['principal:sum', 'interest:sum'],
    )
    for company, due, principal, interest in loan_groups:
        add(company, due, -principal)
        add(company, due, -interest)

    running = 0.0
    for horizon in horizons:
        row = rows[horizon]
        row['net_flow'] = row['inflow'] + row['outflow']
        running += row['net_flow']
        row['cumulative_flow'] = running
    return [rows[horizon] for horizon in horizons]


def survival_horizon(opening, ladder_rows, min_buffer=0.0):
    """Ngày đầu tiên closing liquidity dưới buffer; None nghĩa chưa breach."""
    for row in ladder_rows:
        if opening + row['cumulative_flow'] < min_buffer:
            return row['horizon']
    return None


def min_cash_buffer(env, company):
    """Config per company, tránh model liquidity.limit chỉ để giữ một số."""
    value = env['ir.config_parameter'].sudo().get_param('treasury.min_cash_buffer.%s' % company.id, '0')
    return float(value)


def committed_facility(env, company):
    """Hạn mức tín dụng cam kết chưa dùng, per company (LIQ-007)."""
    value = env['ir.config_parameter'].sudo().get_param('treasury.committed_facility.%s' % company.id, '0')
    return float(value)


def liquidity_status(closing, min_buffer, facility):
    """GREEN/AMBER/RED theo policy LIQ-005.

    AMBER khi facility cam kết đủ bù để giữ buffer; RED khi vẫn hụt.
    Trả (status, required_draw, funding_gap) — gap là phần vượt facility.
    """
    if closing >= min_buffer:
        return 'green', 0.0, 0.0
    required_draw = min_buffer - closing
    if required_draw <= facility:
        return 'amber', required_draw, 0.0
    return 'red', required_draw, required_draw - facility
