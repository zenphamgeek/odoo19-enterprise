# Part of Insilos. See LICENSE file for full copyright and licensing details.
{
    'name': 'Insilos Market Data',
    'version': '1.0.0',
    'category': 'Accounting/Treasury',
    'summary': 'Provider-agnostic market data access and instrument symbol mapping',
    'description': """
Market data foundation for the Combined Capital Markets + Treasury combo.

- Instrument master mapping on product.template (SRS 14.2 field extensions)
- MarketDataProvider abstraction over the loopback sidecar (DATA-010)
- Normalised bars/quotes with provider lineage (DATA-001, DATA-007)

Raw ticks and time-series history stay outside the ORM, in the
market_data_sidecar service (DATA-004).
""",
    'author': 'Insilos',
    'license': 'OEEL-1',
    'depends': ['product', 'insilos_capital_markets_decision_governance'],
    'data': [
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
}
