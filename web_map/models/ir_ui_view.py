# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from insilos import fields, models


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('map', "Map")])

    def _get_view_info(self):
        return {'map': {'icon': 'map-pin'}} | super()._get_view_info()
