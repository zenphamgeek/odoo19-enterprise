# Part of Insilos. See LICENSE file for full copyright and licensing details.
{
    'name': 'Market Terminal',
    'version': '1.0.0',
    'category': 'Accounting/Treasury',
    'summary': 'Real-Time Market Intelligence Terminal with ERP Treasury Decision Overlays',
    'description': """
Candlestick terminal (TradingView Lightweight Charts, Apache 2.0) fed by the
market data provider, with ERP overlays: average cost, hedge triggers and
IC decision markers (UI-001..007). Read-only decision support; no order
execution.
""",
    'author': 'Insilos',
    'license': 'OEEL-1',
    'depends': ['web', 'insilos_market_data'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/terminal_actions.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'insilos_market_terminal/static/lib/lightweight-charts.standalone.production.js',
            'insilos_market_terminal/static/src/terminal/terminal.scss',
            'insilos_market_terminal/static/src/terminal/terminal_action.js',
            'insilos_market_terminal/static/src/terminal/terminal_action.xml',
            'insilos_market_terminal/static/src/terminal/indicators.js',
            'insilos_market_terminal/static/src/terminal/latency.js',
        ],
        'web.assets_web_dark': [
            'insilos_market_terminal/static/src/terminal/terminal.dark.scss',
        ],
        # The chart library must be present in the test bundle: the terminal
        # imports it at module level, and without it the whole suite fails to
        # register and silently reports zero tests.
        'web.assets_unit_tests_setup': [
            'insilos_market_terminal/static/lib/lightweight-charts.standalone.production.js',
            'insilos_market_terminal/static/src/terminal/**/*',
        ],
        'web.assets_unit_tests': [
            'insilos_market_terminal/static/tests/**/*.test.js',
        ],
    },
    'installable': True,
    'application': True,
}
