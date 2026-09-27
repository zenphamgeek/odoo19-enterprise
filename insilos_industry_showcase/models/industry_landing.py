# Part of Insilos. See LICENSE file for full copyright and licensing details.

import json
from odoo import api, fields, models


MODULE_ICONS = {
    'sale': 'ph-duotone ph-shopping-cart-simple',
    'purchase': 'ph-duotone ph-shopping-bag-open',
    'stock': 'ph-duotone ph-package',
    'account': 'ph-duotone ph-receipt',
    'mrp': 'ph-duotone ph-factory',
    'point_of_sale': 'ph-duotone ph-storefront',
    'pos_restaurant': 'ph-duotone ph-cooking-pot',
    'website': 'ph-duotone ph-globe-hemisphere-west',
    'website_sale': 'ph-duotone ph-shopping-bag',
    'website_event': 'ph-duotone ph-ticket',
    'website_slides': 'ph-duotone ph-presentation',
    'crm': 'ph-duotone ph-chart-line-up',
    'project': 'ph-duotone ph-kanban',
    'hr': 'ph-duotone ph-users',
    'hr_timesheet': 'ph-duotone ph-timer',
    'fleet': 'ph-duotone ph-car',
    'repair': 'ph-duotone ph-wrench',
    'appointment': 'ph-duotone ph-calendar-check',
    'event': 'ph-duotone ph-calendar-star',
    'helpdesk': 'ph-duotone ph-headset',
    'mass_mailing': 'ph-duotone ph-envelope-simple-open',
    'quality_control': 'ph-duotone ph-shield-check',
    'delivery': 'ph-duotone ph-truck',
    'maintenance': 'ph-duotone ph-gear-six',
}


class IndustryLanding(models.Model):
    _name = 'is.industry.landing'
    _description = 'Insilos Industry Product Landing Page'
    _order = 'sequence, id'

    name = fields.Char(string="Industry Name", required=True)
    template_id = fields.Many2one(
        'insilos.industry.template', string="Industry Template", ondelete='restrict'
    )
    slug = fields.Char(related='template_id.slug', store=True, index=True)
    category_name = fields.Char(string="Category", default="Industry Solution")
    icon = fields.Char(string="Phosphor Icon", default="ph-duotone ph-briefcase")
    hero_image_url = fields.Char(string="Hero Pexels Image URL")
    image_url = fields.Char(string="Banner Image URL")
    bg_image_url = fields.Char(string="Background Image URL")
    intro_text = fields.Char(string="Intro Text")
    contact_email = fields.Char(string="Contact Email")
    contact_phone = fields.Char(string="Contact Phone")
    contact_address = fields.Char(string="Contact Address")
    summary = fields.Text(string="Tagline / Summary")
    description = fields.Html(string="Detailed Solution Overview")
    features_json = fields.Text(string="Features JSON List")
    footer_json = fields.Text(string="Footer JSON Data")
    demo_url = fields.Char(string="Demo Instance Sub-Domain URL")
    module_names = fields.Char(related='template_id.module_names')
    sequence = fields.Integer(string="Sequence", default=10)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            legacy_slug = vals.pop('slug', None)
            if not vals.get('template_id'):
                template = self.env['insilos.industry.template'].search([
                    '|', ('slug', '=', legacy_slug), ('name', '=', vals.get('name')),
                ])
                if len(template) == 1:
                    vals['template_id'] = template.id
        return super().create(vals_list)

    @api.depends('features_json')
    def get_features_list(self):
        """Returns parsed list of features from JSON."""
        self.ensure_one()
        if not self.features_json:
            return []
        try:
            return json.loads(self.features_json)
        except Exception:
            return []

    def get_modules_list(self):
        """Returns list of included module technical names formatted nicely with Phosphor icons."""
        self.ensure_one()
        if not self.module_names:
            return []
        names = [m.strip() for m in self.module_names.split(',') if m.strip()]
        formatted = []
        for n in names:
            label = n.replace('_', ' ').title()
            icon = MODULE_ICONS.get(n, 'ph-duotone ph-app-window')
            formatted.append({'name': n, 'label': label, 'icon': icon})
        return formatted
