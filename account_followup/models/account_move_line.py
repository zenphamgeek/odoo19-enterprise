from odoo import fields, models
from odoo.tools import SQL, Query


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    followup_line_id = fields.Many2one('account_followup.followup.line', 'Follow-up Level', copy=False)
    invoice_origin = fields.Char(related='move_id.invoice_origin')

    def _read_group_groupby(self, table, groupby_spec: str) -> SQL:
        if groupby_spec != 'followup_overdue':
            return super()._read_group_groupby(table, groupby_spec)
        return SQL(
            "%(date_maturity)s IS NOT NULL AND %(date_maturity)s < %(current_date)s",
            date_maturity=self._field_to_sql(table._alias, 'date_maturity', table._query),
            current_date=fields.Date.context_today(self),
        )

    def _read_group_empty_value(self, spec):
        if spec != 'followup_overdue':
            return super()._read_group_empty_value(spec)
        return False

    def _read_group_postprocess_groupby(self, groupby_spec, raw_values):
        if groupby_spec != 'followup_overdue':
            return super()._read_group_postprocess_groupby(groupby_spec, raw_values)
        return ((value or False) for value in raw_values)
