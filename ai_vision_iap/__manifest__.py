# Part of Insilos. See LICENSE file for full copyright and licensing details.

{
    'name': 'AI Vision IAP Extraction',
    'summary': 'Asynchronous AI Vision data extraction for Vendor Bills using IAP & Trigger.dev',
    'description': """
AI Vision IAP Extraction
========================
Extracts invoice date, partner, and amounts from vendor bill image attachments using
OpenRouter AI Vision and Trigger.dev background workers with Insilos IAP billing.
    """,
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'author': 'Insilos',

    'depends': ['account', 'mail', 'iap'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'data/iap_service_data.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
