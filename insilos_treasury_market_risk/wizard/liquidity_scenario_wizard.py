# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from ..services import liquidity_engine


class LiquidityScenarioWizard(models.TransientModel):
    _name = 'treasury.liquidity.scenario.wizard'
    _description = 'Liquidity Risk Scenario'

    company_ids = fields.Many2many('res.company', required=True, default=lambda self: self.env.company)
    as_of = fields.Date(required=True, default=fields.Date.context_today)
    scenario = fields.Selection([('normal', 'Normal'), ('ar_delay', 'AR delayed 15 days'), ('revenue_down', 'Revenue down 20%'), ('combined', 'Combined')], default='normal', required=True)
    result_html = fields.Html(readonly=True)

    def action_calculate(self):
        self.ensure_one()
        delay = 15 if self.scenario in ('ar_delay', 'combined') else 0
        rows = liquidity_engine.ladder(self.env, self.company_ids.ids, as_of=self.as_of, ar_delay_days=delay)
        if self.scenario in ('revenue_down', 'combined'):
            for row in rows:
                row['inflow'] *= .8
                row['net_flow'] = row['inflow'] + row['outflow']
        running = 0.0
        for row in rows:
            running += row['net_flow']
            row['cumulative_flow'] = running
        opening = sum(row['amount'] for row in liquidity_engine.opening_liquidity(self.env, self.company_ids.ids))
        buffer = sum(liquidity_engine.min_cash_buffer(self.env, company) for company in self.company_ids)
        breach = liquidity_engine.survival_horizon(opening, rows, buffer)
        body = ''.join('<tr><td>%sD</td><td>%.2f</td><td>%.2f</td></tr>' % (row['horizon'], row['net_flow'], opening + row['cumulative_flow']) for row in rows)
        status = 'Buffer breached at %sD.' % breach if breach else 'Buffer holds through the configured horizon.'
        self.result_html = '<p><strong>%s</strong></p><table class="table table-sm"><thead><tr><th>Horizon</th><th>Net flow</th><th>Closing liquidity</th></tr></thead><tbody>%s</tbody></table>' % (status, body)
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'target': 'new'}
