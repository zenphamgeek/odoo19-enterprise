# Part of Insilos. See LICENSE file for full copyright and licensing details.

from markupsafe import escape

from odoo import api, fields, models
from ..services import exposure_engine


class FxScenarioWizard(models.TransientModel):
    _name = 'treasury.fx.scenario.wizard'
    _description = 'FX Exposure Scenario'

    company_ids = fields.Many2many('res.company', required=True, default=lambda self: self.env.company)
    as_of = fields.Date(required=True, default=fields.Date.context_today)
    custom_shock = fields.Float(string='Additional Shock (%)')
    result_html = fields.Html(readonly=True)

    def action_calculate(self):
        self.ensure_one()
        rows = exposure_engine.natural_hedge(exposure_engine.net_open_position(self.env, self.company_ids.ids, self.as_of))
        shocks = tuple(sorted(set(exposure_engine.DEFAULT_SHOCKS + ((self.custom_shock,) if self.custom_shock else ()))))
        results = []
        for company in self.company_ids:
            results.extend(exposure_engine.sensitivity(self.env, rows, company, shocks, self.as_of))
        columns = ''.join('<th>%s%%</th>' % escape(str(shock)) for shock in shocks)
        body = ''.join('<tr><td>%s</td><td>%.2f</td>%s</tr>' % (escape(row['currency_name']), row['base_value'], ''.join('<td>%.2f</td>' % row['shocks'][shock] for shock in shocks)) for row in results)
        self.result_html = '<table class="table table-sm"><thead><tr><th>Currency</th><th>Base value</th>%s</tr></thead><tbody>%s</tbody></table>' % (columns, body or '<tr><td colspan="20">No foreign-currency exposure.</td></tr>')
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

    def action_open_ledger(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': 'FX Exposure Journal Items', 'res_model': 'account.move.line', 'view_mode': 'list,form', 'domain': [('parent_state', '=', 'posted'), ('company_id', 'in', self.company_ids.ids), ('amount_residual_currency', '!=', 0), ('account_id.account_type', 'in', exposure_engine.MONETARY_ACCOUNT_TYPES)]}
