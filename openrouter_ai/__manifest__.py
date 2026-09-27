# Part of Insilos. See LICENSE file for full copyright and licensing details.

{
    'name': 'Insilos IAP — AI Gateway & Smart Router',
    'summary': 'Insilos AI Gateway: Key Management, Model Discovery, Business Domain Routing, and Automatic Fallback Chain',
    'description': """
Insilos IAP — AI Gateway & Smart Router
========================================
The Insilos In-App Purchase (IAP) AI Gateway provides enterprise-grade AI routing:
- Multi-Key Management & Live Credit Balance Dashboard
- Auto-discovery of 100+ AI Models via Insilos AI Gateway
- 6 Business Domain Routers (Vision/OCR, Document AI, Helpdesk Chatbot, Form Autocomplete, Financial Reasoning, Marketing/Translation)
- Automatic Model Fallback Routing Chain on rate-limit or 5xx errors
- OpenAI-compatible Proxy HTTP Controller for frontend & third-party integrations
    """,
    'author': 'Insilos',
    'category': 'Technical/AI',
    'sequence': 5,
    'version': '1.2',
    'depends': ['base', 'web', 'iap'],
    'data': [
        'security/openrouter_log_security.xml',
        'security/ir.model.access.csv',
        'data/openrouter_domain_data.xml',
        'data/ir_cron_data.xml',
        'views/openrouter_key_views.xml',
        'views/openrouter_model_views.xml',
        'views/openrouter_domain_views.xml',
        'views/openrouter_log_views.xml',
        'views/openrouter_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
