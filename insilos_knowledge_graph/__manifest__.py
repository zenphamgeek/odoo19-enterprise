{
    'name': 'Knowledge Graph',
    'version': '26.0.1.1.0',
    'category': 'Productivity/Knowledge',
    'summary': 'Enterprise Knowledge Graph & Rebuildable Cross-Domain Relationship Projection',
    'author': 'Insilos Core Team',
    'depends': ['base'],
    'data': [
        'security/knowledge_graph_security.xml',
        'security/ir.model.access.csv',
        'reports/is_kg_report_actions.xml',
        'reports/is_kg_report_templates.xml',
        'wizard/export_kg_triples_wizard_views.xml',
        'data/kg_cron.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
