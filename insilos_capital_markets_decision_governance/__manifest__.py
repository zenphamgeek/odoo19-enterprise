# Part of Insilos. See LICENSE file for full copyright and licensing details.
{
    'name': 'Capital Markets Decision Governance Accelerator',
    'version': '1.0',
    'category': 'Services/Project',
    'summary': 'Decision governance, portfolio monitoring and AI alerts for capital markets',
    'description': """
Capital Markets Decision Governance Accelerator
===============================================
Investment decision governance built on existing capabilities: Project
(decision cases), Documents (evidence), Knowledge (policy/runbook), Mail (audit
trail) and AI (source-grounded research agent).

Portfolio monitoring adds three small models -- portfolio, position and alert
rule -- because holdings carry a quantity, a cost basis and a mark, and no
standard model carries those without misrepresenting what it is. Everything
else stays configuration on standard models.

Market data arrives through an internal MCP sidecar restricted to public-read
endpoints. No broker credential is held and no account, balance, position or
order endpoint is reachable from here.
""",
    'author': 'Insilos Core Team',
    'depends': [
        'industry_templates',
        'base_automation',
        'project',
        'documents',
        'knowledge',
        'mail',
        'ai',
        'website',
    ],
    'data': [
        'security/capital_markets_security.xml',
        'security/ir.model.access.csv',
        'data/industry_template_data.xml',
        'data/governance_workflow_data.xml',
        'data/maker_checker_data.xml',
        'data/evidence_knowledge_data.xml',
        'data/ai_agent_data.xml',
        'data/market_data_config.xml',
        'data/alert_cron_data.xml',
        'data/capital_ledger_data.xml',
        'views/capital_portfolio_views.xml',
        'views/capital_ledger_views.xml',
        'views/capital_search_views.xml',
        'views/capital_workflow_kanban_views.xml',
        'views/website_templates.xml',
        'reports/is_capital_report_actions.xml',
        'reports/is_capital_report_templates.xml',
    ],
    'demo': [
        'demo/capital_markets_demo.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
