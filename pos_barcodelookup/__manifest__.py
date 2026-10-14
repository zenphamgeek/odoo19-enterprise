{
    'name': 'POS - Barcode Lookup',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'This module enables product creation by scanning barcodes with a camera, utilizing the Barcode Lookup API Key.',
    'depends': ['point_of_sale', 'product_barcodelookup'],
    'data': [
        'views/product_view.xml',
    ],
    'pos_react_plugin_scripts': [
        '/pos_barcodelookup/static/src/pos_react_plugin.js',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            "product_barcodelookup/static/src/widgets/**/*",
            "pos_barcodelookup/static/src/overrides/**/*",
        ],
        'web.assets_tests': [
            'pos_barcodelookup/static/tests/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}
