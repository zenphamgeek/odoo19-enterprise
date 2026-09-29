# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from insilos import models


class IrActionsAct_Window(models.Model):
    _name = 'ir.actions.act_window'
    _inherit = ['studio.mixin', 'ir.actions.act_window']


class IrActionsAct_WindowView(models.Model):
    _name = 'ir.actions.act_window.view'
    _inherit = ['studio.mixin', 'ir.actions.act_window.view']
