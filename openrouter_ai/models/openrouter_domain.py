# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class OpenRouterDomain(models.Model):
    _name = 'openrouter.domain'
    _description = 'Insilos IAP Smart Business Domain Router'
    _order = 'sequence, name'

    name = fields.Char(string='Domain Name', required=True)
    code = fields.Char(string='Domain Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')

    primary_model_id = fields.Many2one('openrouter.model', string='Primary AI Model')
    fallback_model_ids = fields.Many2many(
        'openrouter.model',
        'openrouter_domain_fallback_rel',
        'domain_id',
        'model_id',
        string='Fallback Model Chain'
    )

    require_free = fields.Boolean(string='Enforce FREE Models Only', default=False)
    max_temperature = fields.Float(string='Default Temperature', default=0.2)
    system_prompt = fields.Text(string='System Prompt Template')
    active = fields.Boolean(string='Active', default=True)

    # ── Multi-Provider Routing (AI Inference Orchestration Layer) ──
    provider = fields.Selection([
        ('openrouter', 'OpenRouter (Multi-Model Router)'),
        ('anthropic', 'Anthropic Claude (Direct)'),
        ('gemini', 'Google Gemini (Direct)'),
        ('lmstudio', 'LM Studio (Local GPU — Free)'),
        ('auto', 'Auto (Smart Routing)'),
    ], string='AI Provider', default='openrouter', required=True,
       help='Select which AI provider Trigger.dev will use for this domain.\n'
            '• OpenRouter: Routes to best available model (default)\n'
            '• Anthropic: Claude 3.5 Sonnet/Haiku (complex tasks)\n'
            '• Gemini: Google Gemini 1.5 Flash/Pro (fast vision)\n'
            '• LM Studio: Local GPU inference — FREE, no API credits\n'
            '• Auto: Smart routing based on task type + cost')

    provider_model_override = fields.Char(
        string='Model Override',
        help='Override the default model for this provider. Leave empty to use provider default.\n'
             'Examples: claude-3-5-haiku-20241022, gemini-1.5-flash, qwen/qwen3.7-flash'
    )

    is_local = fields.Boolean(
        string='Local Inference',
        compute='_compute_is_local',
        store=True,
        help='True if this domain uses local GPU inference (LM Studio) — no API credits consumed'
    )

    @api.depends('provider')
    def _compute_is_local(self):
        for rec in self:
            rec.is_local = rec.provider == 'lmstudio'

