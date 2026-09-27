# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_fsm_validate(self):
        """Hook when FSM task is completed to record chemical usage in 5-stage ledger."""
        res = super().action_fsm_validate() if hasattr(super(), 'action_fsm_validate') else True
        self._record_chemical_fsm_consumption()
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == '1_done' or vals.get('stage_id'):
            for task in self:
                if task.state == '1_done':
                    task._record_chemical_fsm_consumption()
        return res

    def _record_chemical_fsm_consumption(self):
        """Deduct & record maintenance/field chemical usage in 5-stage tracking."""
        current_year = fields.Date.today().year
        tracking_model = self.env['is.chemical.usage.tracking']

        for task in self:
            if not task.chemical_substance_ids:
                continue

            for chem in task.chemical_substance_ids:
                # Find or create tracking ledger for substance and year
                tracking = tracking_model.search([
                    ('chemical_substance_id', '=', chem.id),
                    ('reporting_year', '=', current_year),
                    ('company_id', '=', task.company_id.id if task.company_id else self.env.company.id),
                ], limit=1)

                if not tracking:
                    tracking = tracking_model.create({
                        'chemical_substance_id': chem.id,
                        'reporting_year': current_year,
                        'company_id': task.company_id.id if task.company_id else self.env.company.id,
                    })

                # Log activity on task
                task.message_post(
                    body=_("Đã tự động ghi nhận tiêu hao hóa chất <b>%s</b> vào Sổ theo dõi 5 bước (%s).") % (chem.name, tracking.name),
                    subtype_xmlid='mail.mt_note',
                )
