{
    "name": "POS React Discounts",
    "summary": "Global discounts for POS React",
    "category": "Sales/Point of Sale",
    "version": "20.0.1.0.0",
    'author': 'Insilos',

    "depends": ["pos_react", "pos_discount"],
    "pos_react_plugin_scripts": ["/pos_discount_react/static/src/pos_react_plugin.js"],
    "pos_react_translations": [
        "Global discount",
        "Discount Percentage",
        "Discount percentage must be between 0 and 100.",
        "Apply",
        "Cancel",
    ],
    "installable": True,
    "license": "OEEL-1",
}
