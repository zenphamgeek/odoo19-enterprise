# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from insilos import models


class ReportPaperformat(models.Model):
    _name = 'report.paperformat'
    _inherit = ['studio.mixin', 'report.paperformat']
