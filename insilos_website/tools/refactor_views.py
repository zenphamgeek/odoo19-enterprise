#!/usr/bin/env python3
"""
Comprehensive QWeb & SCSS Refactoring Engine for Insilos Website
================================================================
Aligns 100% with:
- Native Odoo 20 Website Builder
- Bootstrap 5 Theme Architecture
- Odoo Color System (o_colored_level o_cc o_cc5)
- Standard Bootstrap .card, .card-body, .btn-primary, .nav-pills, .badge, .table
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VIEWS_DIR = BASE_DIR / "views"

def clean_inline_and_classes(content: str) -> str:
    # 1. Main wrappers to official Odoo dark canvas
    content = content.replace('class="oe_structure ins-c3-canvas ins-grid-bg"', 'class="oe_structure o_colored_level o_cc o_cc5"')
    content = content.replace('class="oe_structure insilos-site"', 'class="oe_structure o_colored_level o_cc o_cc5"')
    content = re.sub(r'\bw_cc\s+w_cc5\b', 'o_colored_level o_cc o_cc5', content)
    content = re.sub(r'\bw_cc\s+w_cc1\b', 'o_colored_level o_cc o_cc1', content)
    content = re.sub(r'\bw_cc\s+w_cc2\b', 'o_colored_level o_cc o_cc2', content)

    # 2. Convert raw background style sections to Odoo native o_background_image
    def replace_section_bg(match):
        full_tag = match.group(0)
        cls = match.group(1)
        snippet = match.group(2)
        name = match.group(3)
        img_url = match.group(4)
        
        # Clean existing classes
        clean_cls = cls.replace("ins-radial-glow", "").replace("pt-5", "").replace("pb-5", "").strip()
        if not clean_cls.startswith("s_"):
            clean_cls = f"{snippet} {clean_cls}"
        return (
            f'<section class="{clean_cls} o_colored_level o_cc o_cc5 pt80 pb80 position-relative overflow-hidden ins-radial-glow" '
            f'data-snippet="{snippet}" data-name="{name}" data-bs-theme="dark">\n'
            f'                    <span class="o_background_image o_not_editable" style="background-image: linear-gradient(135deg, rgba(7, 11, 20, 0.94), rgba(11, 19, 43, 0.88)), url(\'{img_url}\');"/>'
        )

    content = re.sub(
        r'<section class="([^"]+)" data-snippet="([^"]+)" data-name="([^"]+)" style="[^"]*background:[^"]*url\(\'([^\']+)\'\)[^"]*">',
        replace_section_bg,
        content
    )

    # 3. Clean button classes
    content = re.sub(r'\bbtn-c3-primary\b', 'btn-primary rounded-pill px-4 py-2', content)
    content = re.sub(r'\bbtn-c3-outline\b', 'btn-outline-secondary rounded-pill px-4 py-2', content)

    # 4. Standardize text colors & typography
    content = re.sub(r'\btext-slate-muted\b', 'text-secondary', content)
    content = re.sub(r'\btext-slate-light\b', 'text-light', content)
    content = re.sub(r'\bfont-weight-bold\b', 'fw-bold', content)

    # 5. Clean custom cards
    content = re.sub(r'\bins-bento-card\b', 'card border border-secondary border-opacity-25 rounded-4', content)
    content = re.sub(r'\bins-industry-card\b', 'card border border-secondary border-opacity-25 rounded-4', content)
    content = re.sub(r'\bins-dossier-card\b', 'card border border-secondary border-opacity-25 rounded-4', content)

    # 6. Clean specific inline styles on paragraphs and headings
    content = re.sub(
        r'<p class="([^"]*)\blead\b([^"]*)" style="[^"]*max-width:\s*[0-9]+px;[^"]*line-height:[^"]*">',
        r'<p class="\1lead\2 col-lg-10 p-0">',
        content
    )
    content = re.sub(
        r'<p class="([^"]*)" style="[^"]*max-width:\s*680px;?[^"]*">',
        r'<p class="\1 col-lg-8 mx-auto">',
        content
    )
    content = re.sub(
        r'<p class="([^"]*)" style="line-height:\s*1\.[0-9]+;?">',
        r'<p class="\1">',
        content
    )
    content = re.sub(
        r'<h1 class="([^"]*)" style="line-height:\s*1\.[0-9]+;?">',
        r'<h1 class="\1 lh-sm">',
        content
    )

    # 7. Clean border-color styles
    content = re.sub(
        r'class="([^"]*)" style="border-color:\s*var\(--c3-border\)\s*!important;?"',
        r'class="\1 border-secondary border-opacity-25"',
        content
    )
    content = re.sub(
        r'class="([^"]*)" style="border-color:\s*rgba\(255,\s*255,\s*255,\s*0\.08\)\s*!important;?"',
        r'class="\1 border-secondary border-opacity-25"',
        content
    )
    content = re.sub(
        r'class="([^"]*)" style="border-color:\s*rgba\(255,\s*255,\s*255,\s*0\.1\)\s*!important;?"',
        r'class="\1 border-secondary border-opacity-25"',
        content
    )

    # 8. Clean font-size styles
    content = re.sub(
        r'class="([^"]*)" style="font-size:\s*0\.[678][0-9]*rem;?"',
        r'class="\1 small font-monospace"',
        content
    )
    content = re.sub(
        r'class="([^"]*)" style="letter-spacing:\s*0\.[0-9]+em;\s*font-size:\s*0\.[678][0-9]*rem;?"',
        r'class="\1 small font-monospace"',
        content
    )
    content = re.sub(
        r'class="([^"]*)" style="letter-spacing:\s*0\.[0-9]+em;?"',
        r'class="\1 font-monospace"',
        content
    )

    # 9. Clean duplicate classes if any
    def dedupe_class(m):
        classes = m.group(1).split()
        seen = []
        for c in classes:
            if c not in seen:
                seen.append(c)
        return f'class="{" ".join(seen)}"'
    
    content = re.sub(r'class="([^"]+)"', dedupe_class, content)

    return content

def process_file(file_path: Path):
    print(f"Processing {file_path.name}...")
    orig = file_path.read_text(encoding="utf-8")
    cleaned = clean_inline_and_classes(orig)

    # Validate XML
    try:
        ET.fromstring(cleaned)
    except ET.ParseError as e:
        print(f"  ❌ XML Parse Error in {file_path.name}: {e}")
        # Show context around error line
        lines = cleaned.splitlines()
        err_line = e.position[0] - 1
        start = max(0, err_line - 5)
        end = min(len(lines), err_line + 6)
        for i in range(start, end):
            prefix = ">>" if i == err_line else "  "
            print(f"{prefix} {i+1}: {lines[i]}")
        sys.exit(1)

    file_path.write_text(cleaned, encoding="utf-8")
    print(f"  ✅ {file_path.name} refactored and 100% valid XML.")

def main():
    target_files = [
        VIEWS_DIR / "website_templates.xml",
        VIEWS_DIR / "resources_about_demo.xml",
        VIEWS_DIR / "home.xml",
        VIEWS_DIR / "industries.xml",
        VIEWS_DIR / "platform_solutions.xml",
    ]
    for tf in target_files:
        if tf.exists():
            process_file(tf)
    print("\nAll target views refactored cleanly!")

if __name__ == "__main__":
    main()
