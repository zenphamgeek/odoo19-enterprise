# Part of Insilos. See LICENSE file for full copyright and licensing details.
{
    'name': 'Treasury & Market Risk',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'FX exposure, liquidity ladder, portfolio risk and committee governance',
    'description': """
Treasury & Market Risk
======================
Measurement and governance over data that already exists. FX exposure is read
from posted journal items and confirmed orders, the liquidity ladder from
receivables, payables and loan schedules, portfolio marks from the governed
Capital Markets ledger.

This addon holds no business table of its own. Every figure it shows drills
down to the journal item, order or position it came from, which is the point:
a treasury number nobody can trace is a number nobody can defend.
""",
    'author': 'Insilos Core Team',
    'depends': [
        'insilos_capital_markets_decision_governance',
        'account_accountant',
        'account_loans',
        'account_reports',
        'analytic',
        'approvals',
        'sign',
        'spreadsheet_dashboard',
        'documents',
        'knowledge',
        'ai',
    ],
    'data': [
        'security/treasury_security.xml',
        'security/ir.model.access.csv',
        'data/governance_data.xml',
        'data/ai_agent_data.xml',
        'data/cron_data.xml',
        'report/treasury_ic_pack_report.xml',
        'views/treasury_views.xml',
        'views/treasury_ic_pack_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
