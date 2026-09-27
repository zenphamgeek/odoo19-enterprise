# Part of Insilos. See LICENSE file for full copyright and licensing details.
{
    'icon': '/industry_templates/static/description/icon.svg',
    'name': 'Industry Templates',
    'summary': 'Self-hosted industry template definitions for database creation and website configurator',
    'description': """
Industry Templates
==================
Provides 100+ industry template definitions that map industries to module bundles.
Replaces the upstream cloud-based IAP industry API with self-hosted local data.

Features:
- Industry definitions with categories, descriptions and icons
- Module bundle mapping per industry (which modules to install)
- Website Configurator local fallback (no IAP dependency)
- Database Manager industry selection during DB creation
    """,
    'category': 'Hidden/Tools',
    'sequence': 10,
    'version': '1.0',
    'author': 'Insilos',

    'depends': ['base', 'web', 'databases'],
    'data': [
        'security/ir.model.access.csv',
        'data/industry_categories.xml',
        'data/industries_retail.xml',
        'data/industries_food.xml',
        'data/industries_services.xml',
        'data/industries_health.xml',
        'data/industries_education.xml',
        'data/industries_manufacturing.xml',
        'data/industries_construction.xml',
        'data/industries_technology.xml',
        'data/industries_beauty.xml',
        'data/industries_automotive.xml',
        'data/industries_nonprofit.xml',
        'data/industries_agriculture.xml',
        'data/industries_media.xml',
        'data/industries_finance.xml',
        'data/industries_logistics.xml',
        'views/industry_template_views.xml',
        'views/industry_menus.xml',
        'reports/is_industry_template_report_actions.xml',
        'reports/is_industry_template_report_templates.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
