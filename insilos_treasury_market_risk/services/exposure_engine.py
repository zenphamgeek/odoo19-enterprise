# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""FX exposure read out of what accounting already recorded.

Every figure here comes from posted journal items, confirmed orders or a loan
schedule, so each one can be drilled back to its source. Nothing is persisted:
an exposure number is only true as of the moment it was computed, and storing
it would invite someone to read a stale one.
"""

from datetime import date as date_cls, timedelta

from odoo import fields

# Overdue first, then widening windows. The last bucket is open-ended because a
# receivable due in three years is still an exposure, just not a near one.
BUCKETS = (
    ('overdue', 'Overdue', None, 0),
    ('0_7', '0–7D', 0, 7),
    ('8_30', '8–30D', 8, 30),
    ('31_60', '31–60D', 31, 60),
    ('61_90', '61–90D', 61, 90),
    ('91_180', '91–180D', 91, 180),
    ('181_365', '181–365D', 181, 365),
    ('over_1y', '>1Y', 366, None),
)
DEFAULT_SHOCKS = (-10.0, -5.0, -3.0, -1.0, 1.0, 3.0, 5.0, 10.0)
MONETARY_ACCOUNT_TYPES = ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card')


def bucket_of(due, as_of):
    """Return the bucket key for a maturity date, or 'overdue' when it passed."""
    if not due:
        # No maturity is not the same as due today; treat it as the near bucket
        # but never as overdue, which would overstate the urgent column.
        return '0_7'
    days = (due - as_of).days
    if days < 0:
        return 'overdue'
    for key, _label, low, high in BUCKETS:
        if low is None:
            continue
        if days >= low and (high is None or days <= high):
            return key
    return 'over_1y'


def net_open_position(env, company_ids, as_of=None):
    """Foreign-currency balances still outstanding, by currency and bucket.

    Reads `account.move.line` in aggregate; iterating the ledger row by row is
    how a treasury screen becomes unusable on a real company.
    """
    as_of = as_of or fields.Date.context_today(env['account.move.line'])
    if isinstance(as_of, str):
        as_of = fields.Date.to_date(as_of)
    companies = env['res.company'].browse(company_ids)
    domain = [
        ('parent_state', '=', 'posted'),
        ('company_id', 'in', companies.ids),
        ('currency_id', 'not in', companies.mapped('currency_id').ids),
        ('amount_currency', '!=', 0),
        ('account_id.account_type', 'in', MONETARY_ACCOUNT_TYPES),
    ]
    # Companies inside the consolidation. A counterparty that is one of them
    # makes the line intercompany, which the group view must eliminate and the
    # entity view must keep.
    group_partners = env['res.company'].sudo().search([]).mapped('partner_id')
    groups = env['account.move.line']._read_group(
        domain,
        # Account is in the grouping because a receivable and a payable falling
        # on the same day would otherwise be summed into one net number, and the
        # offset natural_hedge measures would already be gone.
        groupby=['currency_id', 'account_id', 'company_id', 'partner_id', 'date_maturity:day'],
        aggregates=['amount_currency:sum', 'amount_residual_currency:sum', 'id:count'],
    )
    rows = {}
    for currency, account, company, partner, due, booked, outstanding, count in groups:
        # Reconcilable accounts carry a residual that already nets settlements;
        # cash accounts do not reconcile and their residual is always zero, so
        # reading it there would silently drop every foreign-currency balance.
        residual = outstanding if account.reconcile else booked
        due = fields.Date.to_date(due) if due else None
        is_intercompany = bool(partner) and partner in group_partners
        key = (currency.id, bucket_of(due, as_of), company.id, is_intercompany)
        row = rows.setdefault(key, {
            'currency_id': currency.id, 'currency_name': currency.name,
            'company_id': company.id, 'company_name': company.name, 'is_intercompany': is_intercompany,
            'bucket': key[1], 'amount': 0.0, 'gross_long': 0.0, 'gross_short': 0.0, 'line_count': 0,
        })
        row['amount'] += residual
        # Keep the two directions apart. Summing them first would erase the
        # offset that natural_hedge exists to measure.
        row['gross_long' if residual >= 0 else 'gross_short'] += residual
        row['line_count'] += count
    order = [key for key, _label, _low, _high in BUCKETS]
    return sorted(rows.values(), key=lambda row: (row['currency_name'], order.index(row['bucket'])))


def commitments(env, company_ids, as_of=None):
    """Confirmed orders not yet invoiced — contracted, not yet booked."""
    as_of = as_of or fields.Date.context_today(env['res.company'])
    if isinstance(as_of, str):
        as_of = fields.Date.to_date(as_of)
    companies = env['res.company'].browse(company_ids)
    home = companies.mapped('currency_id').ids
    rows = {}
    for model, states, sign, field in (
        ('sale.order', ('sale',), 1.0, 'invoice_status'),
        ('purchase.order', ('purchase',), -1.0, 'invoice_status'),
    ):
        if model not in env:
            continue
        groups = env[model]._read_group(
            [('company_id', 'in', companies.ids), ('state', 'in', states),
             ('currency_id', 'not in', home), (field, '!=', 'invoiced')],
            groupby=['currency_id'],
            aggregates=['amount_total:sum'],
        )
        for currency, total in groups:
            row = rows.setdefault(currency.id, {'currency_id': currency.id, 'currency_name': currency.name, 'amount': 0.0})
            row['amount'] += sign * total
    return sorted(rows.values(), key=lambda row: row['currency_name'])


def loan_schedule(env, company_ids, as_of=None, horizon_days=365):
    """Future loan principal and interest, from the amortisation already computed."""
    as_of = as_of or fields.Date.context_today(env['res.company'])
    if isinstance(as_of, str):
        as_of = fields.Date.to_date(as_of)
    groups = env['account.loan.line']._read_group(
        [('company_id', 'in', list(company_ids)), ('date', '>=', as_of),
         ('date', '<=', as_of + timedelta(days=horizon_days))],
        groupby=['currency_id', 'date:day'],
        aggregates=['principal:sum', 'interest:sum'],
    )
    rows = {}
    for currency, due, principal, interest in groups:
        due = fields.Date.to_date(due) if due else as_of
        key = (currency.id, bucket_of(due, as_of))
        row = rows.setdefault(key, {
            'currency_id': currency.id, 'currency_name': currency.name,
            'bucket': key[1], 'principal': 0.0, 'interest': 0.0,
        })
        row['principal'] += principal
        row['interest'] += interest
    return sorted(rows.values(), key=lambda row: (row['currency_name'], row['bucket']))


def natural_hedge(rows):
    """Offset inflows against outflows in the same currency and bucket.

    Gross numbers overstate what actually has to be hedged: a receivable and a
    payable in the same currency maturing in the same week largely cancel.
    """
    out = {}
    for row in rows:
        key = (row['currency_id'], row['bucket'])
        agg = out.setdefault(key, {
            'currency_id': row['currency_id'], 'currency_name': row['currency_name'],
            'bucket': row['bucket'], 'gross_long': 0.0, 'gross_short': 0.0,
        })
        if 'gross_long' in row:
            agg['gross_long'] += row['gross_long']
            agg['gross_short'] += row['gross_short']
        else:
            amount = row.get('amount', 0.0)
            agg['gross_long' if amount >= 0 else 'gross_short'] += amount
    for agg in out.values():
        agg['natural_hedge'] = min(agg['gross_long'], -agg['gross_short'])
        agg['net_exposure'] = agg['gross_long'] + agg['gross_short']
    return sorted(out.values(), key=lambda row: (row['currency_name'], row['bucket']))


def entity_exposure(env, company_ids, as_of=None):
    """MULTI: what each entity actually owes and is owed, intercompany included.

    A subsidiary hedges its own balance sheet, so its intercompany payable is a
    real exposure to it even though the group nets to zero on it.
    """
    rows = net_open_position(env, company_ids, as_of=as_of)
    out = {}
    for row in rows:
        key = (row['company_id'], row['currency_id'])
        agg = out.setdefault(key, {
            'company_id': row['company_id'], 'company_name': row['company_name'],
            'currency_id': row['currency_id'], 'currency_name': row['currency_name'],
            'external': 0.0, 'intercompany': 0.0,
        })
        agg['intercompany' if row['is_intercompany'] else 'external'] += row['amount']
    for agg in out.values():
        agg['entity_total'] = agg['external'] + agg['intercompany']
    return sorted(out.values(), key=lambda row: (row['company_name'], row['currency_name']))


def group_exposure(env, company_ids, as_of=None):
    """MULTI: the group's exposure to the outside world only.

    Intercompany amounts are eliminated because a payable in one entity and the
    matching receivable in another cancel at group level; hedging both would be
    hedging the same risk twice.
    """
    out = {}
    for row in entity_exposure(env, company_ids, as_of=as_of):
        agg = out.setdefault(row['currency_id'], {
            'currency_id': row['currency_id'], 'currency_name': row['currency_name'],
            'external': 0.0, 'intercompany_gross': 0.0,
        })
        agg['external'] += row['external']
        agg['intercompany_gross'] += row['intercompany']
    for agg in out.values():
        # Kept visible rather than dropped: an intercompany total that does not
        # net to zero means the two sides disagree, which is worth seeing.
        agg['intercompany_eliminated'] = agg.pop('intercompany_gross')
        agg['net_external'] = agg['external']
    return sorted(out.values(), key=lambda row: row['currency_name'])


def sensitivity(env, net_rows, company, shocks=DEFAULT_SHOCKS, as_of=None):
    """Value the net exposure in company currency, then shock the rate.

    The spot comes from `res.currency._convert`, the same path accounting uses,
    so the unshocked column reconciles with the books instead of drifting from
    them.
    """
    as_of = as_of or fields.Date.context_today(env['res.company'])
    if isinstance(as_of, str):
        as_of = fields.Date.to_date(as_of)
    totals = {}
    for row in net_rows:
        totals[row['currency_id']] = totals.get(row['currency_id'], 0.0) + row.get('net_exposure', row.get('amount', 0.0))
    results = []
    for currency_id, amount in totals.items():
        currency = env['res.currency'].browse(currency_id)
        base = currency._convert(amount, company.currency_id, company, as_of, round=False)
        results.append({
            'currency_id': currency_id,
            'currency_name': currency.name,
            'net_exposure': amount,
            'base_value': base,
            'shocks': {shock: base * shock / 100.0 for shock in shocks},
        })
    return sorted(results, key=lambda row: row['currency_name'])
