# Part of Insilos. See LICENSE file for full copyright and licensing details.

{
    'name': 'Industry Showcase',
    'version': '1.0.0',
    'category': 'Website/Website',
    'summary': '101 Industry-Specific Product Landing Pages & Conversion Showcases',
    'description': """
Insilos Industry Product Showcase
==================================
Package of 101 industry-specific product landing pages on dev.insilos.com.
Features:
- Master Industry Hub catalog at /industry
- 101 Conversion landing pages at /industry/<slug>
- Direct links to instant demo instances (http://<slug>.insilos.com)
- Curated Pexels imagery, Phosphor Duotone icons, and pre-configured module badges
""",
    'author': 'Insilos Core Team',
    'website': 'https://dev.insilos.com',
    'depends': ['website', 'industry_templates', 'insilos_tenant_control', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/industry_landing_data.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
