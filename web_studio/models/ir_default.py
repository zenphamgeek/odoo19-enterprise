# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from insilos import models


class IrDefault(models.Model):
    _name = 'ir.default'
    _inherit = ['studio.mixin', 'ir.default']
