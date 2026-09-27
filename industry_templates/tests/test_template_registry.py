# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'industry_templates')
class TestIndustryTemplatesRegistry(TransactionCase):

    def setUp(self):
        super(TestIndustryTemplatesRegistry, self).setUp()
        self.Category = self.env['insilos.industry.category']
        self.Template = self.env['insilos.industry.template']

    def test_01_categories_loaded(self):
        """Test that predefined industry categories exist and compute template counts."""
        categories = self.Category.search([])
        self.assertTrue(len(categories) > 0, "Industry categories should be pre-loaded from XML data")

        for cat in categories:
            self.assertTrue(cat.name)
            self.assertEqual(cat.template_count, len(cat.template_ids))

    def test_02_templates_loaded_and_slugified(self):
        """Test that industry templates exist and have valid slugs."""
        templates = self.Template.search([])
        self.assertTrue(len(templates) > 0, "Industry templates should be pre-loaded from XML data")

        for tmpl in templates:
            self.assertTrue(tmpl.name)
            self.assertTrue(tmpl.slug, f"Template {tmpl.name} must have a generated slug")
            self.assertTrue(tmpl.category_id, f"Template {tmpl.name} must belong to a category")

    def test_03_custom_template_creation(self):
        """Test creating a custom industry template with automatic slug generation."""
        category = self.Category.search([], limit=1)
        custom = self.Template.create({
            'name': 'Custom Semiconductor Manufacturing Hub',
            'category_id': category.id,
            'module_names': 'mrp,quality,stock,purchase,account',
            'synonyms': 'chip, wafer, microelectronics',
        })
        self.assertEqual(custom.slug, 'custom_semiconductor_manufacturing_hub')
        self.assertEqual(custom.configurator_industry_id, custom.id)

        modules = self.Template.get_module_list(custom.id)
        self.assertEqual(modules, ['mrp', 'quality', 'stock', 'purchase', 'account'])

    def test_04_configurator_and_slug_apis(self):
        """Test public API methods for website configurator and slug lookups."""
        config_list = self.Template.get_industries_for_configurator()
        self.assertTrue(len(config_list) > 0)
        self.assertIn('id', config_list[0])
        self.assertIn('label', config_list[0])

        template = self.Template.search([], limit=1)
        if template.slug:
            lookup = self.Template.get_template_by_slug(template.slug)
            self.assertIsNotNone(lookup)
            self.assertEqual(lookup['slug'], template.slug)
            self.assertEqual(lookup['id'], template.id)
            self.assertEqual(lookup['required_entitlements'], ['enterprise'])
            self.assertEqual(lookup['conflicts'], [])
            self.assertEqual(lookup['supported_version'], '19.0')

    def test_05_slug_unique_and_digest_deterministic(self):
        template = self.Template.search([], limit=1)
        first = self.Template.get_template_by_slug(template.slug)
        second = self.Template.get_template_by_slug(template.slug)
        self.assertEqual(first['digest'], second['digest'])
        with self.env.cr.savepoint(), mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
            self.Template.create({
                'name': 'Duplicate Slug', 'slug': template.slug,
                'category_id': template.category_id.id,
            })
