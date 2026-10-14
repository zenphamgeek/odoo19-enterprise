from collections import defaultdict
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import SQL


class EquityCapTable(models.Model):
    _name = 'equity.cap.table'
    _description = "Cap Table"
    _auto = False

    partner_id = fields.Many2one('res.partner')
    holder_id = fields.Many2one('res.partner')
    security_class_id = fields.Many2one('equity.security.class')

    securities = fields.Float()
    securities_type = fields.Selection(related='security_class_id.class_type')
    votes = fields.Float()

    ownership = fields.Float()
    voting_rights = fields.Float()
    dividend_payout = fields.Float()
    dilution = fields.Float()
    valuation = fields.Float()

    @property
    def _table_sql(self):
        return self._get_table_sql()

    @property
    def _table_query(self):
        return self._table_sql

    def _get_table_sql(self):
        self.env['equity.transaction'].flush_model()
        current_date = self.env.context.get('current_date') or datetime.max.date()

        domain = Domain('date', '<=', current_date)
        raw_tx_id = self.env.context.get('current_transaction_id')
        if raw_tx_id:
            try:
                sanitized_tx_id = int(raw_tx_id)
                domain &= Domain('id', '!=', sanitized_tx_id)
            except (ValueError, TypeError):
                raise ValidationError("Invalid transaction identifier in execution context.")

        target_company = getattr(self, 'company_id', False) or self.env.company
        if 'company_id' in self.env['equity.transaction']._fields:
            domain &= Domain('company_id', '=', target_company.id)
        else:
            domain &= Domain('partner_id.company_id', 'in', [False, target_company.id])

        Transaction = self.env['equity.transaction']
        transactions_query = Transaction._search(domain)
        exercise_transactions_query = Transaction._search(domain & Domain('transaction_type', '=', 'exercise'))
        transfer_transactions_query = Transaction._search(domain & Domain('transaction_type', '=', 'transfer'))

        tx_table = SQL.identifier(transactions_query.table)
        ex_table = SQL.identifier(exercise_transactions_query.table)
        tr_table = SQL.identifier(transfer_transactions_query.table)

        all_transactions = SQL(" UNION ALL ").join([
            transactions_query.select(
                SQL("%s.partner_id AS partner_id", tx_table),
                SQL("%s.subscriber_id AS holder_id", tx_table),
                SQL("%s.security_class_id AS security_class_id", tx_table),
                SQL("""(CASE
                        WHEN %s.transaction_type IN ('issuance', 'transfer') THEN CAST(%s.securities AS NUMERIC(18, 4))
                        ELSE -CAST(%s.securities AS NUMERIC(18, 4))
                    END) AS securities""", tx_table, tx_table, tx_table),
            ),
            exercise_transactions_query.select(
                SQL("%s.partner_id AS partner_id", ex_table),
                SQL("%s.subscriber_id AS holder_id", ex_table),
                SQL("%s.destination_class_id AS security_class_id", ex_table),
                SQL("CAST(%s.securities AS NUMERIC(18, 4)) AS securities", ex_table),
            ),
            transfer_transactions_query.select(
                SQL("%s.partner_id AS partner_id", tr_table),
                SQL("%s.seller_id AS holder_id", tr_table),
                SQL("%s.security_class_id AS security_class_id", tr_table),
                SQL("-CAST(%s.securities AS NUMERIC(18, 4)) AS securities", tr_table),
            ),
        ])
        return SQL(
            """(
                WITH transactions AS (%(all_transactions)s),
                     security_class AS (
                        SELECT *,
                               CASE WHEN class_type = 'shares' THEN 1 ELSE 0 END AS share_factor,
                               CASE WHEN dividend_payout THEN 1 ELSE 0 END AS dp_factor
                          FROM equity_security_class
                     )
              SELECT CONCAT(partner_id, '-', holder_id, '-', security_class_id, '-', %(current_date)s) AS id,
                     partner_id,
                     holder_id,
                     security_class_id,
                     SUM(securities) AS securities,
                     SUM(securities * security_class.share_votes) AS votes,
                     SUM(securities * security_class.share_factor) / NULLIF(SUM(SUM(securities * security_class.share_factor)) OVER by_partner, 0) AS ownership,
                     SUM(securities * security_class.share_votes) / NULLIF(SUM(SUM(securities * security_class.share_votes)) OVER by_partner, 0) AS voting_rights,
                     SUM(securities * security_class.dp_factor) / NULLIF(SUM(SUM(securities * security_class.dp_factor)) OVER by_partner, 0) AS dividend_payout,
                     SUM(securities) / NULLIF(SUM(SUM(securities)) OVER by_partner, 0) AS dilution,
                     SUM(securities) / NULLIF((SUM(SUM(securities)) OVER by_partner), 0) * last_valuation.valuation AS valuation
                FROM transactions
                JOIN security_class ON security_class.id = transactions.security_class_id
   LEFT JOIN LATERAL (
                        SELECT valuation
                          FROM equity_valuation
                         WHERE partner_id = transactions.partner_id
                           AND date <= %(current_date)s
                      ORDER BY date DESC
                         LIMIT 1
                     ) last_valuation ON TRUE
            GROUP BY partner_id, holder_id, security_class_id, last_valuation.valuation
              WINDOW by_partner AS (PARTITION BY partner_id)
            )""",
            all_transactions=all_transactions,
            current_date=current_date,
        )

    def _append_cap_table_entry(self, data, cap_table_entry):
        security_class_id = cap_table_entry.security_class_id.id
        data['classes'][security_class_id] += cap_table_entry.securities

        data['ownership'] += cap_table_entry.ownership
        data['voting_rights'] += cap_table_entry.voting_rights
        data['dividend_payout'] += cap_table_entry.dividend_payout
        data['dilution'] += cap_table_entry.dilution
        data['valuation'] += cap_table_entry.valuation
        return data

    @api.model
    def get_cap_table_data(self, partner_ids):
        # {partner_id: {holder_id: {...}}}
        partner_holder_data = defaultdict(lambda: defaultdict(lambda: {
            'classes': defaultdict(int),
            'ownership': 0,
            'voting_rights': 0,
            'dividend_payout': 0,
            'dilution': 0,
            'valuation': 0,
        }))
        partner_classes_ids = defaultdict(list)
        partner_data = {}
        class_data = {}

        domain = []
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))

        for cap_table_entry in self.search(domain):
            partner = cap_table_entry.partner_id
            holder = cap_table_entry.holder_id
            security_class = cap_table_entry.security_class_id

            if partner.id not in partner_data:
                partner_data[partner.id] = partner._get_cap_table_data()
            if holder and holder.id not in partner_data:
                partner_data[holder.id] = holder._get_cap_table_data()

            if security_class.id not in class_data:
                class_data[security_class.id] = security_class._get_cap_table_data()

            if security_class.id not in partner_classes_ids[partner.id]:
                partner_classes_ids[partner.id].append(security_class.id)

            self._append_cap_table_entry(partner_holder_data[partner.id][holder.id], cap_table_entry)

        for partner_id, security_class_ids in partner_classes_ids.items():
            # to have a deterministic order of share classes on the cap table
            partner_classes_ids[partner_id] = self.env['equity.security.class'].browse(security_class_ids).sorted().ids

        return {
            'partner_holder_data': partner_holder_data,
            'partner_classes_ids': partner_classes_ids,
            'partner_data': partner_data,
            'class_data': class_data,
        }

    @api.model
    @api.readonly
    def search(self, domain, offset: int = 0, limit: int | None = None, order: str | None = None):
        # Always fetch all the fields when searching to avoid doing a lookup by id afterwards
        return self.search_fetch(domain, list(self._fields), offset=offset, limit=limit, order=order)
