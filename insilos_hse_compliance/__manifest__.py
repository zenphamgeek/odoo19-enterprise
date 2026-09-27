# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

{
    'name': 'Insilos HSE Knowledge & Compliance Suite',
    'version': '20.0.1.0.3',
    'category': 'Operations/HSE',
    'summary': 'Health, Safety & Environment Compliance Management, Legal Register, Chemical SDS 16-Section, QCVN 05A:2020/BCT (TT 19/2024/TT-BCT) & Webhook Sync',
    'description': """
Insilos HSE Knowledge & Compliance Suite
========================================
Enterprise EHS (Environmental, Health, Safety) compliance management platform:
- 7-Level Authority Model (Mandatory Laws, QCVN 05A:2020/BCT sửa đổi theo TT 19/2024/TT-BCT, Permits, Voluntary Standards, GIIP, Internal SOPs).
- Facility Legal Register & Automated Applicability Assessment.
- Chemical Master, 16-section SDS storage (NĐ 113/2017/NĐ-CP), GHS Pictograms & Occupational Exposure Limits (OELs).
- Webhook Inbound Event Receiver with HMAC-SHA256 signature verification.
- On-Demand HS & HSE Taxonomy Knowledge Client.
    """,
    'author': 'Insilos Team',
    'website': 'https://insilos.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
        'mail',
        'project',
    ],
    'data': [
        'security/security_groups.xml',
        'security/hse_company_rules.xml',
        'security/ir.model.access.csv',
        'reports/is_hse_report_actions.xml',
        'reports/is_hse_report_templates.xml',
        'views/is_hse_legal_document_views.xml',
        'views/is_hse_legal_register_views.xml',
        'views/is_hse_chemical_views.xml',
        'views/is_hse_product_permit_views.xml',
        'views/is_hse_facility_views.xml',
        'views/is_hse_compliance_event_views.xml',
        'views/is_hse_sync_log_views.xml',
        'views/is_hse_onboarding_views.xml',
        'views/product_template_views.xml',
        'views/project_task_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
        'wizard/is_hse_chemical_import_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
