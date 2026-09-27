# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class OpenRouterLog(models.Model):
    _name = 'openrouter.log'
    _description = 'Insilos IAP Usage & Cost Audit Log'
    _order = 'create_date desc'

    domain_id = fields.Many2one('openrouter.domain', string='Business Domain')
    model_id = fields.Many2one('openrouter.model', string='Intended Model')
    used_model_name = fields.Char(string='Actual Model Used')

    prompt_tokens = fields.Integer(string='Prompt Tokens', default=0)
    completion_tokens = fields.Integer(string='Completion Tokens', default=0)
    total_tokens = fields.Integer(string='Total Tokens', default=0)
    total_cost = fields.Float(string='Estimated Cost ($)', digits=(12, 6), default=0.0)

    status = fields.Selection([
        ('success', 'Primary Model Success'),
        ('fallback', 'Fallback Chain Used'),
        ('failed', 'All Models Failed'),
    ], string='Status', required=True, default='success')

    execution_time = fields.Float(string='Execution Time (s)', digits=(6, 3))
    error_message = fields.Text(string='Error Message')
    operation_id = fields.Char(required=True, index=True)
    _operation_id_unique = models.Constraint(
        'UNIQUE(operation_id)',
        'An OpenRouter audit log already exists for this operation.',
    )
    tenant_id = fields.Char(index=True)
    company_id = fields.Many2one('res.company', index=True)
    user_id = fields.Many2one('res.users', index=True, ondelete='restrict')
    system_attribution = fields.Char(index=True)
    policy_version = fields.Char()
    credit_budget = fields.Float()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                raise ValidationError('Company attribution is required for new OpenRouter audit logs.')
            if not vals.get('user_id') and not vals.get('system_attribution'):
                raise ValidationError('User or explicit system attribution is required for new OpenRouter audit logs.')
        return super().create(vals_list)

    def write(self, vals):
        raise UserError('OpenRouter audit logs are append-only.')

    def unlink(self):
        raise UserError('OpenRouter audit logs are append-only.')
