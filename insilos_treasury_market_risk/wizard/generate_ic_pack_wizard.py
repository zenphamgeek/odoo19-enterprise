# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, fields, models


class GenerateICPackWizard(models.TransientModel):
    _name = 'treasury.generate.ic.pack.wizard'
    _description = 'Generate Treasury IC Pack'

    task_id = fields.Many2one('project.task', required=True, readonly=True)

    def action_generate(self):
        self.ensure_one()
        report = self.env.ref('insilos_treasury_market_risk.action_report_treasury_ic_pack')
        pdf, report_type = self.env['ir.actions.report']._render_qweb_pdf(report.report_name, res_ids=self.task_id.ids)
        attachments = self.env['ir.attachment'].create([
            {
                'name': f'IC Pack - {self.task_id.name}.pdf',
                'raw': pdf,
                'mimetype': 'application/pdf',
                'res_model': 'project.task',
                'res_id': self.task_id.id,
            }, {
                'name': f'IC Pack - {self.task_id.name}.json',
                'raw': json.dumps(self.task_id._treasury_ic_pack_data(), default=str, sort_keys=True).encode(),
                'mimetype': 'application/json',
                'res_model': 'project.task',
                'res_id': self.task_id.id,
            },
        ])
        self.task_id.message_post(body=_('Treasury IC Pack snapshot generated.'), attachment_ids=attachments.ids)
        return {'type': 'ir.actions.act_window_close'}
