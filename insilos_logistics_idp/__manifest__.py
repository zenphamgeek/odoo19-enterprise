# Part of Insilos. See LICENSE file for full copyright and licensing details.
{
    'name': 'Logistics IDP',
    'version': '20.0.1.3.12',
    'category': 'Services/Project',
    'summary': 'Logistics document control and trade-compliance workspace',
    'description': """
Logistics IDP
=============
Logistics case control with immutable evidence, policy-decision and inbound MES
snapshots. External integrations remain explicit inbound boundaries; MES/MRP
execution and write-back are excluded.
""",
    'author': 'Insilos Core Team',
    'depends': [
        'project',
        'documents',
        'purchase',
        'account',
        'onboarding',
        'base_automation',
        'openrouter_ai',
        'iap_extract',
    ],
    'assets': {
        'web.assets_backend': [
            'insilos_logistics_idp/static/src/dashboard/*',
            'insilos_logistics_idp/static/src/document/*',
        ],
        'web.assets_unit_tests': [
            'insilos_logistics_idp/static/tests/**/*.test.js',
        ],
    },
    'data': [
        'security/logistics_idp_security.xml',
        'security/ir.model.access.csv',
        'reports/is_logistics_idp_report_actions.xml',
        'reports/is_logistics_idp_report_templates.xml',
        'data/logistics_idp_data.xml',
        'data/logistics_idp_onboarding.xml',
        'data/logistics_idp_policy_demo.xml',
        'views/logistics_idp_views.xml',
        'views/is_logistics_idp_onboarding_views.xml',
        'wizard/is_logistics_idp_import_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
}
