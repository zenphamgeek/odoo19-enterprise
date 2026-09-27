# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

{
    'name': 'HS Knowledge Sync Connector',
    'version': '20.0.1.0.0',
    'category': 'Customs/Logistics',
    'summary': 'Bi-directional HS Code, Customs Advance Rulings & Tariff Synchronization with Hermes Agent',
    'description': """
HS Knowledge Sync Connector
===========================
Synchronizes official Vietnam Customs advance classification rulings (Tổng cục Hải quan),
authoritative 8-digit HS code tariffs, and preferential duty rates from Hermes Agent Webhook Hub
and REST Services into Insilos Enterprise.

Features:
---------
* **Customs Advance Rulings Vault** (`is.customs.ruling`): Official rulings, legal citations, classification rationales, and artifact SHA-256 provenance.
* **HS Tariff Schedule Catalog** (`is.hs.tariff`): 8-digit Vietnam HS codes, descriptions, preferential import duties, VAT, and specialized regulatory notes.
* **Bi-directional Integration**:
  - Inbound HMAC-SHA256 authenticated webhook receiver (`/insilos/webhooks/hs-events`) with anti-replay protection.
  - Outbound REST API Client for on-demand HS code search, classification, and tariff calculations.
* **Product Catalog Integration**: Enriches `product.template` with official HS codes and smart lookup actions.
* **Audit & Synchronization Logs** (`is.hs.sync.log`): Full transparency and trace logs of received events and queries.
""",
    'author': 'Insilos Core Team',
    'website': 'https://insilos.com',
    'depends': [
        'base',
        'product',
        'account',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'reports/is_hs_sync_report_actions.xml',
        'reports/is_hs_sync_report_templates.xml',
        'views/is_customs_ruling_views.xml',
        'views/is_hs_tariff_views.xml',
        'views/is_hs_sync_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/is_hs_onboarding_views.xml',
        'views/product_template_views.xml',
        'views/menu_views.xml',
        'wizard/is_hs_tariff_import_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
