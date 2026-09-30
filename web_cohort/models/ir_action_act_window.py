# -*- coding: utf-8 -*-
from insilos import fields, models


class IrActionsAct_WindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[
        ('cohort', 'Cohort')
    ], ondelete={'cohort': 'cascade'})
