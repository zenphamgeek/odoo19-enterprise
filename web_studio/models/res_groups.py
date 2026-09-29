# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from insilos import models


class ResGroups(models.Model):
    _name = 'res.groups'
    _inherit = ['studio.mixin', 'res.groups']
