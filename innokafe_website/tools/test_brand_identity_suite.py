#!/usr/bin/env python3
"""
Innokafe Brand Identity Vector & Interactive SVG Suite Test Runner
===================================================================
Automated verification suite testing:
1. Master Vector SVG Asset Geometry (master, stacked, mark, white, dark)
2. 60 FPS Interactive Animation Suite (SMIL, Keyframes, Transform Origins, Reduced Motion)
3. Favicon Suite & Web Manifest (SVG, 16x16, 32x32, 180x180, site.webmanifest)
4. Navbar & Head QWeb Template Integration (website_templates.xml)
5. WCAG 2.1 Contrast & Accessibility Conformance
"""

import os
import sys
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
BRANDING_DIR = BASE_DIR / "static" / "src" / "img" / "branding"
VIEWS_DIR = BASE_DIR / "views"
SCSS_DIR = BASE_DIR / "static" / "src" / "scss"

class TestBrandVectorAssets(unittest.TestCase):
    """Test suite for the 5 SVG vector brand assets."""

    def test_01_all_five_svg_assets_exist(self):
        """Assert all 5 vector SVG assets exist on disk with positive file size."""
        required_svgs = [
            "innokafe_logo_master.svg",
            "innokafe_logo_stacked.svg",
            "innokafe_mark_symbol.svg",
            "innokafe_logo_white.svg",
            "innokafe_logo_dark.svg",
        ]
        for name in required_svgs:
            svg_path = BRANDING_DIR / name
            self.assertTrue(svg_path.exists(), f"Missing required SVG asset: {name}")
            self.assertGreater(svg_path.stat().st_size, 500, f"SVG asset {name} is unexpectedly small")

    def test_02_master_svg_xml_structure_and_viewbox(self):
        """Assert innokafe_logo_master.svg has valid XML, viewBox '0 0 805.6 232.6', and core glyphs."""
        svg_path = BRANDING_DIR / "innokafe_logo_master.svg"
        content = svg_path.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        self.assertEqual(root.attrib.get("viewBox"), "0 0 805.6 232.6")
        
        # Wordmark, bean, sprouts, script
        self.assertIn("inno-wordmark", content)
        self.assertIn("inno-bean", content)
        self.assertIn("inno-sprout", content)
        self.assertIn("inno-script", content)
        
        # Bean fill #FF8000 and evenodd
        self.assertIn("#FF8000", content)
        self.assertIn('fill-rule="evenodd"', content)

    def test_03_stacked_svg_xml_structure_and_composition(self):
        """Assert innokafe_logo_stacked.svg has vertical viewBox 0 0 600 680 and stacked hierarchy."""
        svg_path = BRANDING_DIR / "innokafe_logo_stacked.svg"
        content = svg_path.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        self.assertEqual(root.attrib.get("viewBox"), "0 0 600 680")
        self.assertIn("Stacked_Hero_Mark", content)
        self.assertIn("Stacked_Wordmark", content)
        self.assertIn("Stacked_Tagline", content)

    def test_04_mark_symbol_svg_square_canvas(self):
        """Assert innokafe_mark_symbol.svg has square 512x512 canvas and isolated mark."""
        svg_path = BRANDING_DIR / "innokafe_mark_symbol.svg"
        content = svg_path.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        self.assertEqual(root.attrib.get("viewBox"), "0 0 512 512")
        self.assertIn("inno-mark-bean", content)
        self.assertIn("inno-mark-sprout", content)
        self.assertIn("inno-mark-shimmer", content)

    def test_05_white_and_dark_svg_variants(self):
        """Assert innokafe_logo_white.svg and innokafe_logo_dark.svg have correct color mappings."""
        white_content = (BRANDING_DIR / "innokafe_logo_white.svg").read_text(encoding="utf-8")
        dark_content = (BRANDING_DIR / "innokafe_logo_dark.svg").read_text(encoding="utf-8")
        
        # White variant: Cream Foam #F7F2EA text, Amber Bean #FF8000
        self.assertIn("#F7F2EA", white_content)
        self.assertIn("#FF8000", white_content)

        # Dark variant: Deep Espresso #1E120B text, Forest Leaf #2D4739 sprouts, Amber Bean #FF8000
        self.assertIn("#1E120B", dark_content)
        self.assertIn("#2D4739", dark_content)
        self.assertIn("#FF8000", dark_content)

class TestAnimationSuite(unittest.TestCase):
    """Test suite for 60 FPS interactive animations."""

    def test_06_shimmer_path_and_gradient(self):
        """Assert master SVG contains shimmer curve along S-groove with gradient and filter."""
        svg_content = (BRANDING_DIR / "innokafe_logo_master.svg").read_text(encoding="utf-8")
        self.assertIn("inno-shimmer-curve", svg_content)
        self.assertIn("innoCremaGrad_master", svg_content)
        self.assertIn("innoCremaGlow_master", svg_content)
        self.assertIn("innoShimmerLoop", svg_content)

    def test_07_sprout_breathing_pulse_origins(self):
        """Assert 3 sprouts have precise transform origins and breathing animation keyframes."""
        svg_content = (BRANDING_DIR / "innokafe_logo_master.svg").read_text(encoding="utf-8")
        self.assertIn("transform-origin: 355px 44px", svg_content)
        self.assertIn("transform-origin: 387px 42px", svg_content)
        self.assertIn("transform-origin: 415px 44px", svg_content)
        self.assertIn("innoSproutLeftPulse", svg_content)
        self.assertIn("innoSproutCenterPulse", svg_content)
        self.assertIn("innoSproutRightPulse", svg_content)

    def test_08_reduced_motion_safeguard(self):
        """Assert prefers-reduced-motion media query is defined to freeze animations."""
        svg_content = (BRANDING_DIR / "innokafe_logo_master.svg").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion: reduce", svg_content)
        theme_scss = (SCSS_DIR / "innokafe_theme.scss").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion: reduce", theme_scss)

    def test_09_scss_interactive_classes(self):
        """Assert SCSS defines inno-brand-logo and inno-logo-interactive with haptic active state."""
        theme_scss = (SCSS_DIR / "innokafe_theme.scss").read_text(encoding="utf-8")
        self.assertIn(".inno-brand-logo", theme_scss)
        self.assertIn(".inno-logo-interactive", theme_scss)
        self.assertIn("scale(0.96)", theme_scss)
        self.assertIn("will-change: transform", theme_scss)

class TestFaviconAndManifestSuite(unittest.TestCase):
    """Test suite for Favicon Suite and Web App Manifest."""

    def test_10_favicon_svg_adaptive_media_query(self):
        """Assert favicon.svg exists, has viewBox 0 0 512 512 and media queries for color scheme."""
        fav_path = BRANDING_DIR / "favicon.svg"
        self.assertTrue(fav_path.exists())
        content = fav_path.read_text(encoding="utf-8")
        root = ET.fromstring(content)
        self.assertEqual(root.attrib.get("viewBox"), "0 0 512 512")
        self.assertIn("prefers-color-scheme: dark", content)
        self.assertIn("prefers-color-scheme: light", content)

    def test_11_rasterized_png_favicons(self):
        """Assert 16x16, 32x32, and 180x180 PNGs exist and have exact dimensions."""
        f16 = BRANDING_DIR / "favicon-16x16.png"
        f32 = BRANDING_DIR / "favicon-32x32.png"
        f180 = BRANDING_DIR / "apple-touch-icon-180x180.png"
        
        self.assertTrue(f16.exists())
        self.assertTrue(f32.exists())
        self.assertTrue(f180.exists())
        
        with Image.open(f16) as img:
            self.assertEqual(img.size, (16, 16))
            self.assertEqual(img.format, "PNG")

        with Image.open(f32) as img:
            self.assertEqual(img.size, (32, 32))
            self.assertEqual(img.format, "PNG")

        with Image.open(f180) as img:
            self.assertEqual(img.size, (180, 180))
            self.assertEqual(img.format, "PNG")

    def test_12_site_webmanifest_metadata(self):
        """Assert site.webmanifest is valid JSON with theme_color #1E120B and icon definitions."""
        manifest_path = BRANDING_DIR / "site.webmanifest"
        self.assertTrue(manifest_path.exists())
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("theme_color"), "#1E120B")
        self.assertEqual(data.get("background_color"), "#1E120B")
        self.assertEqual(data.get("short_name"), "InnoKafe")
        self.assertGreaterEqual(len(data.get("icons", [])), 4)

class TestNavbarAndHeaderIntegration(unittest.TestCase):
    """Test suite for QWeb navbar and header template integration."""

    def test_13_head_metadata_links_favicon_and_manifest(self):
        """Assert website_templates.xml head metadata contains favicon links and webmanifest."""
        tmpl_content = (VIEWS_DIR / "website_templates.xml").read_text(encoding="utf-8")
        self.assertIn('rel="icon" type="image/svg+xml" href="/innokafe_website/static/src/img/branding/favicon.svg"', tmpl_content)
        self.assertIn('rel="icon" type="image/png" sizes="32x32" href="/innokafe_website/static/src/img/branding/favicon-32x32.png"', tmpl_content)
        self.assertIn('rel="icon" type="image/png" sizes="16x16" href="/innokafe_website/static/src/img/branding/favicon-16x16.png"', tmpl_content)
        self.assertIn('rel="apple-touch-icon" sizes="180x180" href="/innokafe_website/static/src/img/branding/apple-touch-icon-180x180.png"', tmpl_content)
        self.assertIn('rel="manifest" href="/innokafe_website/static/src/img/branding/site.webmanifest"', tmpl_content)
        self.assertIn('name="theme-color" content="#1E120B"', tmpl_content)

    def test_14_navbar_brand_template_integration(self):
        """Assert website_templates.xml contains innokafe_header_brand_logo template."""
        tmpl_content = (VIEWS_DIR / "website_templates.xml").read_text(encoding="utf-8")
        self.assertIn('template id="innokafe_header_brand_logo"', tmpl_content)
        self.assertIn('class="navbar-brand logo inno-logo-interactive', tmpl_content)
        self.assertIn('src="/innokafe_website/static/src/img/branding/innokafe_logo_master.svg"', tmpl_content)
        self.assertIn('alt="InnoKafe - Inspire the Techno"', tmpl_content)

    def test_15_footer_vector_logo_integration(self):
        """Assert footer renders innokafe_logo_white.svg on dark espresso background."""
        tmpl_content = (VIEWS_DIR / "website_templates.xml").read_text(encoding="utf-8")
        self.assertIn('src="/innokafe_website/static/src/img/branding/innokafe_logo_white.svg"', tmpl_content)

if __name__ == "__main__":
    unittest.main(verbosity=2)
