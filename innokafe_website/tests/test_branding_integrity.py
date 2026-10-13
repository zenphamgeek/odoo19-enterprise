#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InnoKafe Brand Identity & Architectural Integrity Regression Test Suite
========================================================================
Council Gates Compliance & Static Build-Time Brand Integrity Guard:
1. Cryptographic SHA-256 integrity verification of all 10 branding assets
   against manifest.sha256 (tamper-proofing).
2. Static view architecture check across all QWeb XML templates:
   - Exactly ZERO fake/font-substitute <text> tags or .logo-text spans
     in branding selectors (navbar-brand, inno-brand-logo, headers, footers).
   - Enforce authentic vector SVG links (/innokafe_website/static/src/img/branding/).
3. Database view inspection guard (via psycopg2 or Odoo TransactionCase):
   - Queries ir.ui.view records for innokafe templates and asserts arch_db
     is clean of fake text logo fragments.
"""

import hashlib
import json
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# Paths
MODULE_ROOT = Path(__file__).resolve().parent.parent
BRANDING_DIR = MODULE_ROOT / "static" / "src" / "img" / "branding"
VIEWS_DIR = MODULE_ROOT / "views"
MANIFEST_FILE = BRANDING_DIR / "manifest.sha256"
if not MANIFEST_FILE.exists():
    MANIFEST_FILE = MODULE_ROOT / "manifest.sha256"


class TestBrandAssetCryptographicIntegrity(unittest.TestCase):
    """Verifies that all vector assets and favicons match their authoritative SHA-256 hashes."""

    def setUp(self):
        self.assertTrue(MANIFEST_FILE.exists(), f"manifest.sha256 not found at {MANIFEST_FILE}")
        self.manifest = {}
        for line in MANIFEST_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                checksum, rel_path = parts
                filename = Path(rel_path).name
                self.manifest[filename] = checksum

    def test_01_manifest_contains_all_core_assets(self):
        """Assert manifest tracks the 10 core vector and raster assets."""
        expected_assets = [
            "innokafe_logo_master.svg",
            "innokafe_logo_stacked.svg",
            "innokafe_mark_symbol.svg",
            "innokafe_logo_white.svg",
            "innokafe_logo_dark.svg",
            "favicon.svg",
            "favicon-16x16.png",
            "favicon-32x32.png",
            "apple-touch-icon-180x180.png",
            "site.webmanifest",
        ]
        for asset in expected_assets:
            self.assertIn(asset, self.manifest, f"Asset {asset} missing from manifest.sha256")

    def test_02_sha256_cryptographic_hashes_match(self):
        """Assert byte-for-byte SHA-256 hashes of on-disk assets match manifest.sha256."""
        for filename, expected_hash in self.manifest.items():
            asset_path = BRANDING_DIR / filename
            self.assertTrue(asset_path.exists(), f"Asset {filename} does not exist at {asset_path}")
            raw_bytes = asset_path.read_bytes()
            computed_hash = hashlib.sha256(raw_bytes).hexdigest()
            self.assertEqual(
                computed_hash,
                expected_hash,
                f"Cryptographic hash mismatch for {filename}!\nExpected: {expected_hash}\nActual:   {computed_hash}"
            )


class TestViewBrandingIntegrityStatic(unittest.TestCase):
    """Verifies that QWeb XML templates contain no fake/font-substitute text logos."""

    BANNED_BRANDING_PATTERNS = [
        re.compile(r'class=["\'][^"\']*\blogo-text\b[^"\']*["\']', re.IGNORECASE),
        re.compile(r'class=["\'][^"\']*\bbrand-text\b[^"\']*["\']', re.IGNORECASE),
        re.compile(r'class=["\'][^"\']*\binnokafe-text-logo\b[^"\']*["\']', re.IGNORECASE),
    ]

    def test_03_zero_fake_logo_text_in_all_views(self):
        """Assert no view XML file contains banned text logo classes."""
        xml_files = list(VIEWS_DIR.glob("*.xml"))
        self.assertGreater(len(xml_files), 0, "No XML view files found in views directory")

        for xml_file in xml_files:
            content = xml_file.read_text(encoding="utf-8")
            for pattern in self.BANNED_BRANDING_PATTERNS:
                matches = pattern.findall(content)
                self.assertEqual(
                    len(matches),
                    0,
                    f"Found banned fake text logo pattern in {xml_file.name}: {matches}"
                )

    def test_04_navbar_and_header_vector_logo_mandate(self):
        """Assert header and navbar branding elements strictly embed official vector SVGs."""
        templates_xml = VIEWS_DIR / "website_templates.xml"
        self.assertTrue(templates_xml.exists())
        content = templates_xml.read_text(encoding="utf-8")

        self.assertIn("innokafe_header_brand_logo", content)
        self.assertIn("innokafe_logo_master.svg", content)

        brand_tmpl_match = re.search(
            r'<template[^>]*id=["\']innokafe_header_brand_logo["\'].*?</template>',
            content,
            re.DOTALL
        )
        self.assertIsNotNone(brand_tmpl_match, "innokafe_header_brand_logo template not found")
        brand_tmpl = brand_tmpl_match.group(0)
        self.assertNotIn("<text", brand_tmpl, "Found forbidden inline <text> tag in header brand logo template")
        self.assertNotIn("logo-text", brand_tmpl, "Found forbidden logo-text class in header brand logo template")

    def test_05_footer_vector_logo_mandate(self):
        """Assert footer branding template strictly embeds white vector SVG and zero fake text."""
        templates_xml = VIEWS_DIR / "website_templates.xml"
        content = templates_xml.read_text(encoding="utf-8")

        footer_match = re.search(
            r'<template[^>]*id=["\']innokafe_footer_custom["\'].*?</template>',
            content,
            re.DOTALL
        )
        self.assertIsNotNone(footer_match, "innokafe_footer_custom template not found")
        footer_tmpl = footer_match.group(0)

        self.assertIn("innokafe_logo_white.svg", footer_tmpl)
        self.assertNotIn("<text", footer_tmpl, "Found forbidden inline <text> in footer brand template")
        self.assertNotIn("logo-text", footer_tmpl, "Found forbidden logo-text class in footer brand template")


class TestDatabaseBrandingIntegrityStandalone(unittest.TestCase):
    """Direct database audit when running outside Odoo test harness."""

    def test_06_database_arch_db_branding_integrity(self):
        """Query PostgreSQL ir_ui_view table directly and verify zero fake text logos."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=os.environ.get("PGHOST", "127.0.0.1"),
                port=int(os.environ.get("PGPORT", "5434")),
                user=os.environ.get("PGUSER", "odoo"),
                password=os.environ.get("PGPASSWORD", "1NN0R1@2026"),
                dbname=os.environ.get("PGDATABASE", "innokafe_prod"),
                connect_timeout=3
            )
        except Exception as e:
            self.skipTest(f"Direct PostgreSQL connection skipped: {e}")
            return

        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, key, name, arch_db::text
                FROM ir_ui_view
                WHERE key IN (
                    'innokafe_website.innokafe_header_brand_logo',
                    'innokafe_website.innokafe_footer_custom'
                )
            """)
            rows = cur.fetchall()
            self.assertGreaterEqual(len(rows), 1, "Expected branding views not found in database")
            for vid, key, name, arch in rows:
                self.assertNotIn("logo-text", arch, f"View {key} contains logo-text in arch_db!")
                self.assertNotIn("<text", arch, f"View {key} contains inline <text> in arch_db!")
                self.assertTrue(
                    "innokafe_logo_" in arch or "innokafe_mark_" in arch,
                    f"View {key} does not reference vector SVG logo in arch_db!"
                )
            conn.close()
        except Exception as e:
            conn.close()
            raise e


# Support Odoo's internal test runner when loaded under odoo-bin --test-enable
try:
    import odoo
    if getattr(odoo.tools.config, 'test_enable', False):
        from odoo.tests.common import TransactionCase, tagged

        @tagged('post_install', '-at_install', 'branding', 'innokafe')
        class TestBrandingIntegrityORM(TransactionCase):
            """ORM-level verification that database views have zero fake text logos."""

            def test_07_orm_arch_db_branding_integrity(self):
                """Query ir.ui.view for InnoKafe branding views and verify zero fake text logos in DB."""
                branding_views = self.env['ir.ui.view'].search([
                    ('key', 'in', [
                        'innokafe_website.innokafe_header_brand_logo',
                        'innokafe_website.innokafe_footer_custom',
                    ])
                ])
                for view in branding_views:
                    arch = view.arch_db or ""
                    self.assertNotIn("logo-text", arch, f"View {view.key} contains logo-text in arch_db!")
                    self.assertNotIn("<text", arch, f"View {view.key} contains <text> in arch_db!")
                    self.assertTrue(
                        "innokafe_logo_" in arch or "innokafe_mark_" in arch,
                        f"View {view.key} does not reference vector SVG logo in arch_db!"
                    )
except Exception:
    pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
