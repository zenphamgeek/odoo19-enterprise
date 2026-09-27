# Part of Insilos. See LICENSE file for full copyright and licensing details.

import hashlib
import json
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


def _slugify(name):
    """Convert a display name to a URL-safe slug.

    Example: 'Yoga / Pilates Studio' → 'yoga_pilates_studio'
    Handles JSON-encoded multilingual values stored by Insilos translate=True fields.
    """
    if not name:
        return ''
    # Extract plain text from JSON-translated field value
    if isinstance(name, str) and name.startswith('{'):
        try:
            d = json.loads(name)
            name = d.get('en_US', next(iter(d.values()), name))
        except (ValueError, TypeError):
            pass
    slug = str(name).lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug


class IndustryCategory(models.Model):
    _name = 'insilos.industry.category'
    _description = 'Industry Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    icon = fields.Char(help='Phosphor Duotone icon class, e.g. ph-duotone ph-shopping-bag')
    sequence = fields.Integer(default=10)
    color = fields.Char(help='CSS color value for category badge')
    template_ids = fields.One2many('insilos.industry.template', 'category_id', string='Templates')
    template_count = fields.Integer(compute='_compute_template_count')

    def _compute_template_count(self):
        for cat in self:
            cat.template_count = len(cat.template_ids)


class IndustryTemplate(models.Model):
    _name = 'insilos.industry.template'
    _description = 'Industry Template'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True, index=True)
    description = fields.Text(translate=True)
    icon = fields.Char(help='Phosphor Duotone icon class, e.g. ph-duotone ph-storefront')
    category_id = fields.Many2one('insilos.industry.category', string='Category', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Search/matching
    synonyms = fields.Char(
        help='Comma-separated synonyms for fuzzy search matching in the configurator'
    )

    # Module bundle — comma-separated technical module names
    module_names = fields.Char(
        string='Module Bundle',
        help='Comma-separated list of module technical names to install for this industry. '
             'Example: sale,purchase,stock,mrp'
    )

    # ── Template content & branding ──────────────────────────────────────────

    hero_image_url = fields.Char(
        string='Hero Image URL',
        help='Path to hero banner image, e.g. /web/static/src/img/banners/yoga.webp'
    )
    bg_image_url = fields.Char(
        string='Background Image URL',
        help='Path to background image for the tenant landing page'
    )
    intro_text = fields.Char(
        string='Intro Text',
        help='Short tagline shown on the tenant landing page'
    )
    contact_email = fields.Char(string='Contact Email')
    contact_phone = fields.Char(string='Contact Phone')
    contact_address = fields.Char(string='Contact Address')
    footer_json = fields.Text(
        string='Footer Data (JSON)',
        help='JSON blob with footer intro, email, phone, address, copyright'
    )


    slug = fields.Char(
        string='URL Slug',
        required=True,
        index=True,
        help='URL-safe identifier for subdomain routing: {slug}.insilos.com\n'
             'Auto-generated from name. Example: yoga_pilates_studio',
    )
    _slug_unique = models.Constraint('UNIQUE(slug)', 'Industry template slug must be unique.')

    # Website configurator compatibility
    configurator_industry_id = fields.Integer(
        string='Configurator ID',
        compute='_compute_configurator_industry_id',
        help='Numeric ID used by the Website Configurator JS frontend',
    )

    # ── Computes ──────────────────────────────────────────────────────────────

    def _compute_configurator_industry_id(self):
        for rec in self:
            rec.configurator_industry_id = rec.id

    # ── ORM hooks ─────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('slug') and vals.get('name'):
                vals['slug'] = _slugify(vals['name'])
        return super().create(vals_list)

    def write(self, vals):
        if 'name' in vals and not vals.get('slug'):
            vals['slug'] = _slugify(vals['name'])
        return super().write(vals)

    # ── Public API methods ────────────────────────────────────────────────────

    @api.model
    def get_industries_for_configurator(self):
        """Return industry list in format expected by the Website Configurator.

        Matches format previously returned by IAP:
            /api/website/1/configurator/industries
        """
        templates = self.search([])
        return [{
            'id': t.id,
            'label': t.name,
            'synonyms': t.synonyms or '',
        } for t in templates]

    @api.model
    def get_module_list(self, template_id):
        """Return module technical names for a given industry template ID."""
        template = self.browse(template_id)
        if not template.exists() or not template.module_names:
            return []
        return [m.strip() for m in template.module_names.split(',') if m.strip()]

    @api.model
    def get_template_by_slug(self, slug):
        """Resolve one canonical module bundle for a normalized slug."""
        if not isinstance(slug, str) or slug != _slugify(slug):
            raise ValidationError('Invalid industry template slug.')
        templates = self.search([('slug', '=', slug)])
        if len(templates) != 1:
            raise ValidationError('Industry template slug must resolve exactly once.')
        template = templates.ensure_one()
        modules = sorted(self.get_module_list(template.id))
        canonical = {
            'slug': template.slug,
            'module_bundle': modules,
            'required_entitlements': ['enterprise'],
            'conflicts': [],
            'supported_version': '19.0',
        }
        digest = hashlib.sha256(
            json.dumps(canonical, separators=(',', ':'), sort_keys=True).encode()
        ).hexdigest()
        return {
            'id': template.id,
            'name': template.name,
            **canonical,
            'digest': digest,
            'category': template.category_id.name,
            'icon': template.icon or '',
        }
