# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

{
    'name': 'Insilos Chemical Trade Compliance',
    'version': '20.0.1.0.2',
    'category': 'Logistics/Compliance',
    'summary': 'Chemical Regulatory Determination, NSW Dossier & Permit Quota — Luật Hóa chất 69/2025/QH15',
    'description': """
Insilos Chemical Trade Compliance
=================================
Automated logistics chemical trade compliance platform aligned with
Luật Hóa chất 69/2025/QH15 (effective 01/01/2026) and Nghị định 24/2026/NĐ-CP:
- 241 Controlled Chemicals (Phụ lục III NĐ 24/2026): Nhóm 1 (154 chemicals incl. CWC Schedule 2 &
  industrial precursors IVB) and Nhóm 2 (87 chemicals incl. CWC Schedule 3, Rotterdam & Stockholm).
- Regulatory Obligation Determination Engine with real-time Compliance Matrix 2026.
- Chemical Compliance Dossier compilation & National Single Window (NSW) XML/JSON payload generation.
- Phiếu kiểm soát mua, bán hóa chất cần kiểm soát đặc biệt (Transaction Control Voucher).
- Real-time Permit Quota Tracking & Burn-down ledger (5-year BCT licenses).
- 5-Stage Chemical Usage Tracking (Demand → Import → Domestic → Consumption → Inventory).
- Seamless integration with Purchase Orders, Inbound Shipments, and Customs Declarations.
    """,
    'author': 'Insilos Team',
    'website': 'https://insilos.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
        'purchase',
        'mail',
        'project',
        'insilos_hse_compliance',
        'insilos_hs_sync',
        'insilos_logistics_idp',
    ],
    'data': [
        'security/security_groups.xml',
        'security/chemical_company_rules.xml',
        'security/ir.model.access.csv',
        'reports/is_chemical_dossier_reports.xml',
        'reports/is_chemical_dossier_templates.xml',
        'wizard/is_chemical_obligation_simulator_views.xml',
        'views/is_chemical_purpose_of_use_views.xml',
        'views/is_chemical_material_mapping_views.xml',
        'views/is_chemical_usage_tracking_views.xml',
        'views/is_chemical_compliance_exception_views.xml',
        'views/is_chemical_regulatory_rule_views.xml',
        'views/is_chemical_permit_quota_views.xml',
        'views/is_chemical_compliance_dossier_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'views/logistics_idp_case_views.xml',
        'views/is_chemical_onboarding_views.xml',
        'views/is_unified_operations_hub_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
