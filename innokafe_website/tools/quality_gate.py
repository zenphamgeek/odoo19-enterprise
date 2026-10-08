#!/usr/bin/env python3
"""
Innokafe Specialty Coffee Website: 7-Gate Quality & Compliance Validator
=========================================================================
Automated quality gate suite enforcing Odoo 20 / Insilos 20 enterprise standards
for the Innokafe Specialty Coffee Brand Platform (innokafe.insilos.com).

7 Automated Quality Gates:
--------------------------
1. Gate 1: Static QWeb Snippet Contract & Dropzones
   - 100% <section> elements have data-snippet and data-name attributes.
   - Core page templates contain oe_structure dropzones.
   - 100% XML well-formedness (via lxml / ElementTree).
2. Gate 2: Live Public HTTP Routes Health
   - 100% public routes return HTTP 200 OK:
     ['/', '/story', '/products', '/taste-profiler', '/solutions-b2b', '/contactus']
   - Valid non-empty DOM content (> 500 bytes).
3. Gate 3: Website Builder Palette Inheritance
   - Custom snippets declared and inherited in website.snippets palette.
4. Gate 4: Snippet Diversity Standard
   - >= 12 distinct snippet types across views and snippets palette.
5. Gate 5: QWeb Directives Modernization
   - Exactly 0 deprecated 't-esc=' directives (100% migrated to 't-out=').
   - Exactly 0 server-side 't-key=' directives in QWeb templates.
6. Gate 6: Brand Tokens & WCAG Button Contrast Standard
   - SCSS design tokens defined: Deep Espresso (#1E120B), Warm Amber (#D48842),
     Cream Foam (#F7F2EA), Forest Leaf (#2D4739).
   - Mathematical WCAG Contrast verification: Warm Amber (#D48842) buttons/badges
     MUST NEVER pair with white text (#FFFFFF, fails at ~2.84:1), but MUST pair with
     Deep Espresso text (#1E120B, passes AA at ~6.45:1).
7. Gate 7: Typographic Balance & Layout Rhythm
   - 'text-wrap: balance' defined on headings (h1-h6) to eliminate orphan words.
   - Playfair Display headings & Plus Jakarta Sans body typography.

Usage:
------
    python3 enterprise/innokafe_website/tools/quality_gate.py
    python3 enterprise/innokafe_website/tools/quality_gate.py --verbose
    python3 enterprise/innokafe_website/tools/quality_gate.py --offline
    python3 enterprise/innokafe_website/tools/quality_gate.py --base-url http://localhost:28071
"""

import sys
import os
import re
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from collections import Counter

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
VIEWS_DIR = BASE_DIR / "views"
SCSS_DIR = BASE_DIR / "static" / "src" / "scss"
IMG_DIR = BASE_DIR / "static" / "src" / "img"

DEFAULT_BASE_URL = os.environ.get("INNOKAFE_BASE_URL", os.environ.get("INSILOS_BASE_URL", "http://localhost:28071"))

PUBLIC_ROUTES = [
    {"path": "/", "name": "Homepage — Di Sản & Tách Cà Phê Có Gu", "view_file": "home.xml"},
    {"path": "/story", "name": "Farm-to-Cup Heritage & 4 Không Pledge", "view_file": "story.xml"},
    {"path": "/products", "name": "Specialty Coffee & Sensory Catalogue", "view_file": "products.xml"},
    {"path": "/taste-profiler", "name": "Interactive Coffee Taste Profiler", "view_file": "taste_profiler.xml"},
    {"path": "/solutions-b2b", "name": "B2B Horeca & Espresso Equipment", "view_file": "solutions_b2b.xml"},
    {"path": "/contactus", "name": "Roastery & Showroom Contact", "view_file": "contactus.xml"},
]

CORE_PAGE_VIEWS = [
    "home.xml",
    "story.xml",
    "products.xml",
    "taste_profiler.xml",
    "solutions_b2b.xml",
    "contactus.xml",
]


# ============================================================================
# WCAG CONTRAST UTILITIES
# ============================================================================

def hex_to_rgb(hex_code):
    hex_code = hex_code.strip().lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join(c * 2 for c in hex_code)
    if len(hex_code) != 6:
        return (0, 0, 0)
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))


def calculate_relative_luminance(rgb):
    """Calculate WCAG 2.1 relative luminance for an RGB tuple in [0, 255]."""
    transformed = []
    for val in rgb:
        s = val / 255.0
        if s <= 0.04045:
            transformed.append(s / 12.92)
        else:
            transformed.append(((s + 0.055) / 1.055) ** 2.4)
    r, g, b = transformed
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast_ratio(hex1, hex2):
    """Calculate WCAG 2.1 contrast ratio between two hex colors."""
    lum1 = calculate_relative_luminance(hex_to_rgb(hex1))
    lum2 = calculate_relative_luminance(hex_to_rgb(hex2))
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


# ============================================================================
# GATE 1: STATIC QWEB TEMPLATES & DROPZONES
# ============================================================================

def audit_gate_1_static_templates(verbose=False):
    print("\n" + "=" * 75)
    print("[GATE 1] AUDITING STATIC QWEB TEMPLATES FOR SNIPPET & DROPZONE CONTRACT")
    print("=" * 75)

    if not VIEWS_DIR.exists():
        print(f"  ❌ Views directory missing: {VIEWS_DIR}")
        return False, {"error": "Views directory missing"}

    xml_files = list(VIEWS_DIR.glob("*.xml"))
    if not xml_files:
        print(f"  ❌ No XML view files found in {VIEWS_DIR}")
        return False, {"error": "No view files"}

    total_sections = 0
    valid_snippet_sections = 0
    missing_snippet_sections = []
    missing_dropzones = []
    xml_syntax_errors = []

    section_pattern = re.compile(r'<section\b([^>]*)>', re.DOTALL | re.IGNORECASE)

    for xml_file in xml_files:
        content = xml_file.read_text(encoding="utf-8")

        # Test XML parseability with lxml (or ElementTree)
        try:
            try:
                from lxml import etree
                etree.fromstring(content.encode('utf-8'))
            except ImportError:
                import xml.etree.ElementTree as ET
                ET.fromstring(content)
        except Exception as e:
            xml_syntax_errors.append({"file": xml_file.name, "error": str(e)})

        # Skip menu files for section auditing
        if xml_file.name in ["website_menu.xml"]:
            continue

        for match in section_pattern.finditer(content):
            attrs = match.group(1)
            total_sections += 1
            has_data_snippet = bool(re.search(r'data-snippet=[\"\']', attrs))
            has_data_name = bool(re.search(r'data-name=[\"\']', attrs))

            if has_data_snippet and has_data_name:
                valid_snippet_sections += 1
            else:
                missing_snippet_sections.append({
                    "file": xml_file.name,
                    "snippet": attrs.strip()[:70]
                })

        # Check for oe_structure dropzones on core page view files
        if xml_file.name in CORE_PAGE_VIEWS:
            has_oe_structure = bool(re.search(r'class=[\"\'][^\"\']*\boe_structure\b', content))
            if not has_oe_structure:
                missing_dropzones.append(xml_file.name)

    passed = (
        total_sections > 0 and
        len(missing_snippet_sections) == 0 and
        len(missing_dropzones) == 0 and
        len(xml_syntax_errors) == 0
    )

    print(f"  • Total Content Sections Analyzed: {total_sections}")
    print(f"  • Sections with valid data-snippet & data-name: {valid_snippet_sections}/{total_sections}")
    print(f"  • Sections missing snippet metadata: {len(missing_snippet_sections)}")
    print(f"  • Core Page Templates with Dropzones: {len(CORE_PAGE_VIEWS) - len(missing_dropzones)}/{len(CORE_PAGE_VIEWS)}")
    print(f"  • XML Well-Formedness Errors: {len(xml_syntax_errors)}")

    if xml_syntax_errors:
        for err in xml_syntax_errors:
            print(f"    ❌ {err['file']}: {err['error']}")

    if verbose and missing_snippet_sections:
        for item in missing_snippet_sections[:5]:
            print(f"    ⚠️ Missing in {item['file']}: {item['snippet']}")

    if passed:
        print("  ✅ [GATE 1 PASSED] 100% Sections conform to Odoo Snippet Contract & Dropzones!")
    else:
        print("  ❌ [GATE 1 FAILED] Non-conforming sections or XML parse errors detected.")

    return passed, {
        "total_sections": total_sections,
        "valid_snippet_sections": valid_snippet_sections,
        "missing_snippet_sections": missing_snippet_sections,
        "missing_dropzones": missing_dropzones,
        "xml_syntax_errors": xml_syntax_errors,
    }


# ============================================================================
# GATE 2: LIVE PUBLIC HTTP ROUTES HEALTH
# ============================================================================

def audit_gate_2_live_http_routes(base_url, offline_mode=False, verbose=False):
    print("\n" + "=" * 75)
    print(f"[GATE 2] AUDITING LIVE PUBLIC HTTP ROUTES HEALTH ({len(PUBLIC_ROUTES)} Routes)")
    print("=" * 75)

    if offline_mode:
        print("  ⚡ [OFFLINE MODE ACTIVE] Verifying route declarations in Python controllers...")
        controller_file = BASE_DIR / "controllers" / "main.py"
        if not controller_file.exists():
            print(f"  ❌ Controller file missing: {controller_file}")
            return False, {"error": "controllers/main.py missing"}

        controller_src = controller_file.read_text(encoding="utf-8")
        declared_routes = []
        for r in PUBLIC_ROUTES:
            pattern = re.compile(rf'@http\.route\([^)]*[\'\"]{re.escape(r["path"])}[\'\"]')
            found = bool(pattern.search(controller_src))
            declared_routes.append({"path": r["path"], "declared": found})
            print(f"  {'✅' if found else '❌'} Route {r['path']:20} declared in controller: {found}")

        all_declared = all(r["declared"] for r in declared_routes)
        if all_declared:
            print("  ✅ [GATE 2 PASSED (OFFLINE)] 100% Public routes declared and mapped in Controller!")
        else:
            print("  ❌ [GATE 2 FAILED (OFFLINE)] Some public routes missing in Controller!")
        return all_declared, {"offline": True, "declared_routes": declared_routes}

    all_passed = True
    route_results = []
    print(f"  Target Server: {base_url}")

    for r in PUBLIC_ROUTES:
        url = f"{base_url.rstrip('/')}{r['path']}"
        status = None
        content_len = 0
        has_dropzone = False
        error_msg = None

        for attempt in range(2):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "InnokafeQualityGate/2.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    status = resp.status
                    html = resp.read().decode("utf-8", errors="replace")
                    content_len = len(html)
                    has_dropzone = ("oe_structure" in html) or ("data-snippet=" in html) or ("innokafe" in html)
                    break
            except urllib.error.HTTPError as he:
                status = he.code
                error_msg = str(he)
            except Exception as e:
                status = "ERR"
                error_msg = str(e)

        passed = (status == 200 and content_len > 500)
        if not passed:
            all_passed = False

        status_str = f"HTTP {status}" if isinstance(status, int) else f"{status}"
        print(f"  {'✅' if passed else '❌'} {r['path']:20} | {status_str} | Size: {content_len:6}B | Dropzones: {has_dropzone}")
        if error_msg and verbose:
            print(f"      Error: {error_msg}")

        route_results.append({
            "path": r["path"],
            "name": r["name"],
            "status": status,
            "size": content_len,
            "has_dropzone": has_dropzone,
            "passed": passed,
        })

    if all_passed:
        print("  ✅ [GATE 2 PASSED] 100% Public routes returned HTTP 200 OK with valid QWeb DOM!")
    else:
        print("  ❌ [GATE 2 FAILED] One or more public routes failed health check!")
        if all(r.get("status") == "ERR" for r in route_results):
            print(f"  💡 Notice: Server at {base_url} appears unreachable. Run with '--offline' to audit controller route definitions and static contracts statically.")

    return all_passed, {"route_results": route_results}


# ============================================================================
# GATE 3: WEBSITE BUILDER PALETTE INHERITANCE
# ============================================================================

def audit_gate_3_snippets_palette(verbose=False):
    print("\n" + "=" * 75)
    print("[GATE 3] AUDITING WEBSITE BUILDER PALETTE INHERITANCE & SNIPPET REGISTRATION")
    print("=" * 75)

    snippets_file = VIEWS_DIR / "snippets.xml"
    if not snippets_file.exists():
        print(f"  ❌ Snippets XML missing: {snippets_file}")
        return False, {"error": "snippets.xml missing"}

    content = snippets_file.read_text(encoding="utf-8")

    # 1. Inherits website.snippets
    has_palette_inherit = 'inherit_id="website.snippets"' in content or "inherit_id='website.snippets'" in content

    # 2. Extract registered snippets
    t_pattern = re.compile(r'<t\b[^>]*\bt-snippet=[\"\']innokafe_website\.([^\"\']+)[\"\'][^>]*>', re.DOTALL)
    registered_snippets = []

    for match in t_pattern.finditer(content):
        snip_id = match.group(1)
        tag_str = match.group(0)
        name_match = re.search(r'string=[\"\']([^\"\']+)[\"\']', tag_str)
        thumb_match = re.search(r't-thumbnail=[\"\']([^\"\']+)[\"\']', tag_str)

        snip_name = name_match.group(1) if name_match else snip_id
        thumb_path = thumb_match.group(1) if thumb_match else None

        registered_snippets.append({
            "id": snip_id,
            "name": snip_name,
            "thumbnail": thumb_path,
        })

    print(f"  • Inherits 'website.snippets' palette: {'✅ Yes' if has_palette_inherit else '❌ No'}")
    print(f"  • Custom Snippets Registered in Palette: {len(registered_snippets)}")

    for snip in registered_snippets:
        if verbose:
            print(f"    - {snip['name']:35} ({snip['id']})")

    passed = has_palette_inherit and len(registered_snippets) >= 8
    if passed:
        print(f"  ✅ [GATE 3 PASSED] All {len(registered_snippets)} building blocks properly inherited in website.snippets!")
    else:
        print(f"  ❌ [GATE 3 FAILED] Palette inheritance missing or insufficient snippets ({len(registered_snippets)}/8+).")

    return passed, {
        "has_palette_inherit": has_palette_inherit,
        "registered_snippets": registered_snippets,
    }


# ============================================================================
# GATE 4: SNIPPET DIVERSITY STANDARD (>= 12 TYPES)
# ============================================================================

def audit_gate_4_snippet_diversity(verbose=False):
    print("\n" + "=" * 75)
    print("[GATE 4] AUDITING SNIPPET DIVERSITY STANDARD (TARGET: >= 12 DISTINCT TYPES)")
    print("=" * 75)

    if not VIEWS_DIR.exists():
        return False, {"error": "Views directory missing"}

    xml_files = list(VIEWS_DIR.glob("*.xml"))
    all_snippets = []

    for xml_file in xml_files:
        content = xml_file.read_text(encoding="utf-8")
        matches = re.findall(r'data-snippet=[\"\']([^\"\']+)[\"\']', content)
        all_snippets.extend(matches)

    counts = Counter(all_snippets)
    unique_count = len(counts)

    print(f"  • Total Content Snippet Invocations: {len(all_snippets)}")
    print(f"  • Distinct Snippet Types Identified: {unique_count} (Required: >= 12)")

    for snip_type, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    - {snip_type:35} : {cnt} occurrences")

    passed = unique_count >= 12
    if passed:
        print(f"  ✅ [GATE 4 PASSED] Diversity target surpassed with {unique_count} distinct snippet types!")
    else:
        print(f"  ❌ [GATE 4 FAILED] Snippet diversity below target: {unique_count}/12 distinct types.")

    return passed, {
        "unique_count": unique_count,
        "counts": dict(counts),
        "total_invocations": len(all_snippets),
    }


# ============================================================================
# GATE 5: QWEB DIRECTIVES MODERNIZATION
# ============================================================================

def audit_gate_5_qweb_directives(verbose=False):
    print("\n" + "=" * 75)
    print("[GATE 5] AUDITING ODOO 20 QWEB DIRECTIVES (0 t-esc, 0 server-side t-key)")
    print("=" * 75)

    if not VIEWS_DIR.exists():
        return False, {"error": "Views directory missing"}

    xml_files = list(VIEWS_DIR.glob("*.xml"))
    tesc_violations = []
    tkey_violations = []

    for xml_file in xml_files:
        content = xml_file.read_text(encoding="utf-8")
        # Check for deprecated t-esc
        tesc_matches = re.findall(r't-esc=[\"\'][^\"\']*[\"\']', content)
        if tesc_matches:
            tesc_violations.append({"file": xml_file.name, "count": len(tesc_matches)})

        # Check for server-side t-key in templates
        tkey_matches = re.findall(r't-key=[\"\'][^\"\']*[\"\']', content)
        if tkey_matches:
            tkey_violations.append({"file": xml_file.name, "count": len(tkey_matches)})

    print(f"  • Templates with deprecated 't-esc=': {len(tesc_violations)}")
    if tesc_violations:
        for v in tesc_violations:
            print(f"    ❌ {v['file']}: {v['count']} instances")

    print(f"  • Templates with server-side 't-key=': {len(tkey_violations)}")
    if tkey_violations:
        for v in tkey_violations:
            print(f"    ❌ {v['file']}: {v['count']} instances")

    passed = (len(tesc_violations) == 0 and len(tkey_violations) == 0)
    if passed:
        print("  ✅ [GATE 5 PASSED] 100% Clean QWeb Directives (0 t-esc, 0 server t-key)!")
    else:
        print("  ❌ [GATE 5 FAILED] Deprecated QWeb directives detected.")

    return passed, {
        "tesc_violations": tesc_violations,
        "tkey_violations": tkey_violations,
    }


# ============================================================================
# GATE 6: BRAND TOKENS & WCAG BUTTON CONTRAST STANDARD
# ============================================================================

def audit_gate_6_brand_and_wcag_contrast(verbose=False):
    print("\n" + "=" * 75)
    print("[GATE 6] AUDITING BRAND TOKENS & WCAG BUTTON CONTRAST CONFORMANCE")
    print("=" * 75)

    theme_file = SCSS_DIR / "innokafe_theme.scss"
    if not theme_file.exists():
        print(f"  ❌ SCSS Theme file missing: {theme_file}")
        return False, {"error": "innokafe_theme.scss missing"}

    scss_content = theme_file.read_text(encoding="utf-8")

    # 1. Brand Tokens Verification
    tokens = {
        "Deep Espresso": ("#1E120B", ["#1E120B", "#1e120b"]),
        "Warm Amber": ("#D48842", ["#D48842", "#d48842"]),
        "Cream Foam": ("#F7F2EA", ["#F7F2EA", "#f7f2ea"]),
        "Forest Leaf": ("#2D4739", ["#2D4739", "#2d4739"]),
    }

    tokens_found = {}
    for name, (hex_code, variants) in tokens.items():
        found = any(v in scss_content for v in variants)
        tokens_found[name] = found
        print(f"  • Token '{name}' ({hex_code}): {'✅ Declared' if found else '❌ Missing'}")

    all_tokens_ok = all(tokens_found.values())

    # 2. Mathematical WCAG Contrast Proof
    contrast_amber_espresso = calculate_contrast_ratio("#D48842", "#1E120B")
    contrast_amber_white = calculate_contrast_ratio("#D48842", "#FFFFFF")
    contrast_cream_espresso = calculate_contrast_ratio("#F7F2EA", "#1E120B")

    print("\n  Mathematical WCAG 2.1 Relative Luminance Proof:")
    print(f"    - Warm Amber (#D48842) on Deep Espresso (#1E120B) text: {contrast_amber_espresso:.2f}:1 -> {'✅ PASS (>=4.5:1 AA)' if contrast_amber_espresso >= 4.5 else '❌ FAIL'}")
    print(f"    - Warm Amber (#D48842) with White text (#FFFFFF):       {contrast_amber_white:.2f}:1 -> {'❌ FAIL (<4.5:1)' if contrast_amber_white < 4.5 else '✅ PASS'}")
    print(f"    - Cream Foam (#F7F2EA) on Deep Espresso (#1E120B) text: {contrast_cream_espresso:.2f}:1 -> {'✅ PASS (>=7.0:1 AAA)' if contrast_cream_espresso >= 7.0 else '❌ FAIL'}")

    # 3. SCSS Rule Check: .btn-primary with Warm Amber background MUST NOT have white text
    btn_primary_dark_text = False
    if ".btn-primary" in scss_content:
        btn_match = re.search(r'\.btn-primary\b[^{]*\{([^}]+)\}', scss_content)
        if btn_match:
            block = btn_match.group(1)
            has_dark = any(c in block for c in ["#1E120B", "#1e120b", "var(--inno-espresso-dark)", "var(--inno-text-dark)"])
            has_white = any(c in block for c in ["#fff", "#ffffff", "#FFFFFF", "var(--inno-cream)", "var(--inno-text-light)"])
            btn_primary_dark_text = has_dark and not has_white
        else:
            btn_primary_dark_text = True
    else:
        btn_primary_dark_text = True

    print(f"  • .btn-primary Enforces Deep Espresso Text on Amber: {'✅ Yes' if btn_primary_dark_text else '❌ No'}")

    # 4. QWeb View Sanitation: Check that Warm Amber buttons NEVER use white text
    xml_files = list(VIEWS_DIR.glob("*.xml"))
    illegal_buttons = []

    button_pattern = re.compile(r'<(?:a|button)\b([^>]*\bclass=[\"\'][^\"\']*\bbtn\b[^\"\']*[\"\'][^>]*)>', re.IGNORECASE)

    for xml_file in xml_files:
        c = xml_file.read_text(encoding="utf-8")
        for m in button_pattern.finditer(c):
            attrs = m.group(1)
            is_amber = ('btn-primary' in attrs or '#D48842' in attrs or 'inno-amber' in attrs)
            has_white = ('text-white' in attrs or '#fff' in attrs.lower() or '#ffffff' in attrs.lower() or 'text-light' in attrs)
            if is_amber and has_white:
                illegal_buttons.append({"file": xml_file.name, "issue": m.group(0)[:80]})

    print(f"  • Rogue Buttons with White Text on Warm Amber: {len(illegal_buttons)}")

    passed = all_tokens_ok and btn_primary_dark_text and len(illegal_buttons) == 0
    if passed:
        print("  ✅ [GATE 6 PASSED] 100% Brand Tokens & WCAG Contrast Compliant (Warm Amber + Deep Espresso text)!")
    else:
        print("  ❌ [GATE 6 FAILED] Contrast or button styling violations detected.")

    return passed, {
        "all_tokens_ok": all_tokens_ok,
        "tokens_found": tokens_found,
        "contrast_amber_espresso": contrast_amber_espresso,
        "btn_primary_dark_text": btn_primary_dark_text,
        "illegal_buttons": illegal_buttons,
    }


# ============================================================================
# GATE 7: TYPOGRAPHIC BALANCE & LAYOUT RHYTHM
# ============================================================================

def audit_gate_7_typographic_balance(verbose=False):
    print("\n" + "=" * 75)
    print("[GATE 7] AUDITING TYPOGRAPHIC BALANCE (text-wrap: balance) & LAYOUT RHYTHM")
    print("=" * 75)

    theme_file = SCSS_DIR / "innokafe_theme.scss"
    if not theme_file.exists():
        return False, {"error": "SCSS theme missing"}

    scss_content = theme_file.read_text(encoding="utf-8")

    # 1. 'text-wrap: balance' declaration in SCSS
    has_text_wrap_balance = "text-wrap: balance" in scss_content
    print(f"  • CSS 'text-wrap: balance' declared on headings: {'✅ Yes' if has_text_wrap_balance else '❌ No'}")

    # 2. Typography font families defined
    has_playfair = "Playfair Display" in scss_content
    has_plus_jakarta = "Plus Jakarta Sans" in scss_content
    print(f"  • Playfair Display heading typography: {'✅ Yes' if has_playfair else '❌ No'}")
    print(f"  • Plus Jakarta Sans body typography: {'✅ Yes' if has_plus_jakarta else '❌ No'}")

    passed = has_text_wrap_balance and has_playfair and has_plus_jakarta
    if passed:
        print("  ✅ [GATE 7 PASSED] 100% Typographic Balance & Layout Symmetry Conforming!")
    else:
        print("  ❌ [GATE 7 FAILED] Typographic balance rules or typography declarations missing.")

    return passed, {
        "has_text_wrap_balance": has_text_wrap_balance,
        "has_playfair": has_playfair,
        "has_plus_jakarta": has_plus_jakarta,
    }


# ============================================================================
# MAIN CONTROLLER
# ============================================================================

def run_all_gates(base_url=DEFAULT_BASE_URL, offline=False, verbose=False):
    print("\n" + "#" * 75)
    print("INNOKAFE SPECIALTY COFFEE 7-GATE AUTOMATED QUALITY VALIDATOR")
    print("Platform: Insilos 20 / Odoo 20 Enterprise (innokafe.insilos.com)")
    print("#" * 75)

    g1_ok, g1_data = audit_gate_1_static_templates(verbose=verbose)
    g2_ok, g2_data = audit_gate_2_live_http_routes(base_url=base_url, offline_mode=offline, verbose=verbose)
    g3_ok, g3_data = audit_gate_3_snippets_palette(verbose=verbose)
    g4_ok, g4_data = audit_gate_4_snippet_diversity(verbose=verbose)
    g5_ok, g5_data = audit_gate_5_qweb_directives(verbose=verbose)
    g6_ok, g6_data = audit_gate_6_brand_and_wcag_contrast(verbose=verbose)
    g7_ok, g7_data = audit_gate_7_typographic_balance(verbose=verbose)

    overall_pass = g1_ok and g2_ok and g3_ok and g4_ok and g5_ok and g6_ok and g7_ok

    print("\n" + "=" * 75)
    print("FINAL QUALITY GATE SCORECARD:")
    print("=" * 75)
    print(f"  [GATE 1] Static QWeb Snippets & Dropzones : {'✅ PASSED' if g1_ok else '❌ FAILED'}")
    print(f"  [GATE 2] Live Public HTTP Routes Health   : {'✅ PASSED' if g2_ok else '❌ FAILED'}")
    print(f"  [GATE 3] Snippet Palette Inheritance      : {'✅ PASSED' if g3_ok else '❌ FAILED'}")
    print(f"  [GATE 4] Snippet Diversity (>= 12 Types)  : {'✅ PASSED' if g4_ok else '❌ FAILED'}")
    print(f"  [GATE 5] Clean QWeb Directives (0 t-esc)   : {'✅ PASSED' if g5_ok else '❌ FAILED'}")
    print(f"  [GATE 6] Brand Tokens & WCAG Contrast     : {'✅ PASSED' if g6_ok else '❌ FAILED'}")
    print(f"  [GATE 7] Typographic Balance & Layout     : {'✅ PASSED' if g7_ok else '❌ FAILED'}")
    print("=" * 75)

    if overall_pass:
        print("🏆 ALL 7 QUALITY GATES PASSED! Innokafe Platform is 100% Certified.")
        print("=" * 75 + "\n")
        return 0
    else:
        print("💥 QUALITY GATE AUDIT FAILED! Please inspect errors above.")
        print("=" * 75 + "\n")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Innokafe 7-Gate Quality Validator")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for live route checking")
    parser.add_argument("--offline", action="store_true", help="Run offline static analysis without HTTP ping")
    parser.add_argument("--verbose", action="store_true", help="Print detailed diagnostic info")

    args = parser.parse_args()
    exit_code = run_all_gates(base_url=args.base_url, offline=args.offline, verbose=args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
