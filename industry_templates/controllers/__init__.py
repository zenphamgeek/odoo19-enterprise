# Part of Insilos. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request, route


class IndustryTemplateController(http.Controller):
    """Read-only industry catalog API."""

    @route('/api/industries', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def list_industries(self, **kwargs):
        templates = request.env['insilos.industry.template'].search_read(
            domain=[('active', '=', True)],
            fields=['id', 'name', 'slug', 'icon', 'synonyms', 'module_names'],
            order='sequence, name',
        )
        categories = request.env['insilos.industry.category'].search_read(
            fields=['id', 'name', 'icon', 'color', 'sequence'],
            order='sequence, name',
        )
        return {'industries': templates, 'categories': categories, 'total': len(templates)}

    @route('/api/industries/<string:slug>', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def get_industry(self, slug, **kwargs):
        template = request.env['insilos.industry.template'].get_template_by_slug(slug)
        if not template:
            return {'error': f'Industry template not found: {slug}', 'code': 404}
        return template

    @route('/api/industries/configurator', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def configurator_industries(self, lang='en_US', **kwargs):
        templates = request.env['insilos.industry.template'].sudo().search([])
        return {'industries': [
            {'id': template.id, 'label': template.name, 'synonyms': template.synonyms or ''}
            for template in templates
        ]}
