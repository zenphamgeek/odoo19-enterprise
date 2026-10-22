# -*- coding: utf-8 -*-
{
    "name": "InnoKafe Specialty Coffee Brand Platform",
    "summary": "Specialty Coffee Website, Taste Profiler, Sensory Wheel & Farm-to-Cup Heritage for InnoKafe",
    "version": "1.0.0",
    "category": "Website/Website",
    "author": "InnoKafe / Insilos",
    "website": "https://innokafe.insilos.com",
    "license": "LGPL-3",
    "depends": [
        "website",
        "website_sale",
        "crm",
        "mail",
        "insilos_website",
    ],
    "data": [
        "data/website_data.xml",
        "data/products_specialty.xml",
        "views/website_templates.xml",
        "views/home.xml",
        "views/story.xml",
        "views/products.xml",
        "views/taste_profiler.xml",
        "views/solutions_b2b.xml",
        "views/contactus.xml",
        "views/snippets.xml",
        "views/website_menu.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "innokafe_website/static/src/scss/innokafe_liquid_spatial.scss",
            "innokafe_website/static/src/scss/innokafe_theme.scss",
            "innokafe_website/static/src/js/**/*",
        ],
    },
    "application": True,
    "installable": True,
}
