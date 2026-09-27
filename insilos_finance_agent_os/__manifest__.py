# Part of Insilos. See LICENSE file for full copyright and licensing details.
{
    'name': 'Finance Agent OS',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Agent skills, capability gateway and decision packets over existing finance models',
    'description': """
The agent layer for Capital Markets and Treasury. It owns no table.

Every fact an agent states must come from a model that already exists or from a
tool result carrying its own lineage, and every write goes through the approval
path the domain addon already enforces. That is the whole design: an agent that
cannot invent a number, and cannot approve its own work.

Capabilities are resolved by alias rather than hard-coded model names, so a
tenant missing an optional model loses one feature instead of failing to
install; a tenant missing a required one is forced read-only rather than
silently writing somewhere else.
""",
    'author': 'Insilos Core Team',
    'depends': [
        'insilos_capital_markets_decision_governance',
        'insilos_treasury_market_risk',
        'documents',
        'project',
        'ai',
    ],
    'data': [
        'data/ai_agent_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
