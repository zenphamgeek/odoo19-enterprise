# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CapitalBenchmark(models.Model):
    _name = 'capital.benchmark'
    _description = 'Benchmark'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', required=True)
    last_value = fields.Float(tracking=True)
    mark_as_of = fields.Datetime()
    # Without a fixed starting point a benchmark level is a number with no
    # meaning; the return is only defined against a stated base.
    base_value = fields.Float(tracking=True, help='Index level the comparison starts from.')
    base_as_of = fields.Datetime(string='Base As Of')
    evidence_attachment_id = fields.Many2one('ir.attachment', ondelete='restrict')
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint('unique(code)', 'Benchmark code must be unique.')
