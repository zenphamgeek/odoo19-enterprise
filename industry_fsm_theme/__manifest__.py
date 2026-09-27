{
    'name': 'Field Service Industry Theme',
    'summary': 'Visual Theme & Login Hero Banner for Field Service Industry',
    'description': """
        Industry Theme module for Field Service Operations.
        Customizes Login Page Split-Screen Hero Banner, primary Navy palette (#0B2E64),
        and backend visual identity for Field Service Management.
    """,
    'version': '1.0',
    'category': 'Industry/Theme',
    'author': 'Insilos Architecture',
    'license': 'LGPL-3',
    'depends': ['web', 'web_enterprise', 'industry_fsm'],
    'data': [
        'views/web_assets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'industry_fsm_theme/static/src/scss/fsm_theme.scss',
        ],
        'web.assets_backend': [
            'industry_fsm_theme/static/src/scss/fsm_theme.scss',
            'industry_fsm_theme/static/src/webclient/home_menu_fsm.js',
            'industry_fsm_theme/static/src/webclient/home_menu_fsm.xml',
        ],
        'web.assets_unit_tests': [
            'industry_fsm_theme/static/tests/fsm_theme.test.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
