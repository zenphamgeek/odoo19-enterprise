# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    leave_id = fields.Many2one('hr.leave', string="Time Off")
    leave_state = fields.Selection(related='leave_id.state', string="Time Off State")

    def action_refuse_leave(self):
        for entry in self:
            if entry.leave_id:
                entry.leave_id.action_refuse()

    def action_approve_leave(self):
        for entry in self:
            if entry.leave_id:
                entry.leave_id.action_approve()
