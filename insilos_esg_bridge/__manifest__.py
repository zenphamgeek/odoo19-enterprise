# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

{
    'name': 'Insilos ESG & Cross-App Sustainability Intelligence',
    'version': '20.0.1.0.1',
    'category': 'ESG/Operations',
    'summary': 'End-to-End ESG Integration: CEMS IoT Emissions, Freight Carbon (Scope 3 Cat 4), Chemical Environmental Footprint, CBAM Advisor & Knowledge Lineage',
    'description': """
Insilos ESG Cross-App Sustainability Intelligence
=================================================
Unifies core Insilos enterprise platforms with ESG & Carbon Accounting:
- 🛡️ HSE Compliance Integration: Auto-sync CEMS continuous emissions (SO2, NOx, CO2, TSP) and industrial wastewater (COD, BOD) into Scope 1 Direct Emissions and Facility ESG Scorecards.
- 📄 Logistics IDP Integration: Automatic Scope 3 Category 4 Freight Carbon Calculator (Ocean, Air, Road, Rail) derived directly from extracted Bills of Lading, AWB, and Manifests.
- 🧪 Chemical Trade Compliance Integration: Chemical process evaporation, volatile organic emissions, and GHS09 environmental hazard index.
- 🌐 HS Code Sync Integration: CBAM (Carbon Border Adjustment Mechanism) embedded carbon intensity and green customs tariff guidance.
- 🧠 Knowledge Graph Lineage: Cross-entity supplier ESG rating, carbon hotspot propagation, and bitemporal sustainability audit trail.
    """,
    'author': 'Insilos Team',
    'website': 'https://insilos.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'esg',
        'insilos_hse_compliance',
        'insilos_chemical_trade_compliance',
        'insilos_logistics_idp',
        'insilos_hs_sync',
        'insilos_knowledge_graph',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/esg_bridge_demo_data.xml',
        'views/is_esg_facility_scorecard_views.xml',
        'views/is_esg_freight_carbon_views.xml',
        'views/is_esg_chemical_impact_views.xml',
        'views/is_esg_cbam_advisor_views.xml',
        'views/logistics_idp_case_views.xml',
        'views/hse_facility_views.xml',
        'views/is_esg_bridge_menus.xml',
        'views/is_esg_onboarding_views.xml',
        'reports/is_esg_report_actions.xml',
        'reports/is_esg_report_templates.xml',
        'wizard/is_esg_export_scorecard_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
