#!/usr/bin/env python3
"""
Adversarial UI/UX & Design Stress-Testing Suite (Challenger 1)
=============================================================
Independent empirical test harness for the Insilos Enterprise Website (Odoo 20).
Stress-tests:
1. Zero inline styles (style="...") across all views/*.xml
2. 100% button conformance to Insilos Orange #FF8000 (0 rogue button classes)
3. Sibling card height symmetry and HBox baseline locking (h-100, .ins-card-row-balanced)
4. Typographic orphan prevention on Vietnamese headings
5. Client data anonymization & brand invariance audit

Does NOT modify any implementation code. Exits with non-zero if defects are found.
"""

import os
import re
import sys
import html
import json
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
VIEWS_DIR = BASE_DIR / "views"
SCSS_DIR = BASE_DIR / "static" / "src" / "scss"
SCSS_FILE = SCSS_DIR / "insilos.scss"

def log_section(title):
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)

# ==============================================================================
# 1. ADVERSARIAL STRESS TEST: ZERO INLINE STYLES
# ==============================================================================
def stress_test_zero_inline_styles():
    log_section("1. ADVERSARIAL STRESS TEST: ZERO INLINE STYLES (views/*.xml)")
    
    xml_files = sorted(list(VIEWS_DIR.glob("*.xml")))
    print(f"[*] Probing {len(xml_files)} XML view files for inline style attributes...")
    
    # Adversarial patterns:
    # 1. standard style="..." or style='...'
    # 2. style with arbitrary whitespace style  =  "..."
    # 3. multiline style=" \n ... "
    # 4. case-insensitive STYLE="..."
    adversarial_style_pattern = re.compile(
        r'<([a-zA-Z0-9_\-]+)\b([^>]*?\bstyle\s*=\s*["\']([^"\']*)["\'][^>]*>)',
        re.DOTALL | re.IGNORECASE
    )
    
    violations = []
    
    for xf in xml_files:
        content = xf.read_text(encoding="utf-8")
        
        # Strip XML comments first to only check executable markup
        clean_content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        for m in adversarial_style_pattern.finditer(clean_content):
            tag = m.group(1)
            full_tag = m.group(0)
            style_content = m.group(3).strip()
            
            # Find line number in original file
            pos = m.start()
            line_num = content[:pos].count('\n') + 1
            
            violations.append({
                "file": xf.name,
                "line": line_num,
                "tag": tag,
                "style": style_content,
                "snippet": full_tag[:120].replace('\n', ' ')
            })
            
    if violations:
        print(f"❌ [FAIL] Found {len(violations)} inline style violations across views/*.xml:")
        for v in violations:
            print(f"   • {v['file']}:{v['line']} <{v['tag']}>: style=\"{v['style'][:60]}\"")
        return False, {"violations": violations}
    else:
        print(f"✅ [PASS] Exactly 0 inline styles detected across all {len(xml_files)} view files.")
        print("   Adversarial variations tested: multi-line attributes, whitespace variants, case insensitivity.")
        return True, {"violations": []}

# ==============================================================================
# 2. ADVERSARIAL STRESS TEST: BUTTON THEME CONFORMANCE & ROGUE CLASSES
# ==============================================================================
def stress_test_button_conformance():
    log_section("2. ADVERSARIAL STRESS TEST: BUTTON THEME CONFORMANCE (#FF8000)")
    
    # 1. Verify SCSS declarations
    if not SCSS_FILE.exists():
        print("❌ [FAIL] insilos.scss not found!")
        return False, {"error": "SCSS missing"}
        
    scss_content = SCSS_FILE.read_text(encoding="utf-8")
    has_hex = "#FF8000" in scss_content
    has_primary_token = "--ins-primary: #FF8000" in scss_content or "--ins-orange: #FF8000" in scss_content
    has_gradient_token = "--ins-orange-gradient:" in scss_content
    has_btn_primary = ".btn-primary" in scss_content and ("var(--ins-orange-gradient)" in scss_content or "var(--ins-orange)" in scss_content)
    
    print(f"[*] SCSS Token Verification:")
    print(f"   • #FF8000 Hex present: {'✅' if has_hex else '❌'}")
    print(f"   • --ins-primary / --ins-orange token: {'✅' if has_primary_token else '❌'}")
    print(f"   • --ins-orange-gradient token: {'✅' if has_gradient_token else '❌'}")
    print(f"   • .btn-primary mapped to brand orange: {'✅' if has_btn_primary else '❌'}")
    
    # 2. Comprehensive Button Audit
    xml_files = sorted(list(VIEWS_DIR.glob("*.xml")))
    
    # Permitted Bootstrap 5 button semantic classes:
    # Primary CTA: btn-primary (styled with brand orange)
    # Secondary / Outline: btn-outline-secondary, btn-outline-light, btn-link
    # Modals / Dismiss: btn-close, btn-close-white
    # Rogue button classes that break the #FF8000 brand or lack SCSS mapping:
    ROGUE_CLASSES = {
        "btn-outline-info": "Cyan outline - breaks orange theme (unmapped)",
        "btn-outline-warning": "Yellow outline - breaks orange theme (unmapped)",
        "btn-outline-danger": "Red outline - unmapped / rogue",
        "btn-danger": "Red solid - breaks orange theme",
        "btn-warning": "Yellow solid - breaks orange theme",
        "btn-info": "Cyan solid - breaks orange theme",
        "btn-success": "Green solid - breaks orange theme",
        "btn-outline-success": "Green outline - breaks orange theme",
        "btn-dark": "Dark solid - unmapped",
        "btn-outline-dark": "Dark outline - unmapped",
        "btn-outline-cyan": "Custom rogue class",
        "btn-cyan": "Custom rogue class",
        "btn-dark-glow": "Custom rogue class",
        "btn-custom": "Custom rogue class",
    }
    
    button_regex = re.compile(
        r'<(?:button|a)\b([^>]*?\bclass\s*=\s*["\'][^"\']*\bbtn\b[^"\']*["\'][^>]*>)',
        re.DOTALL | re.IGNORECASE
    )
    
    total_buttons = 0
    rogue_buttons = []
    inline_styled_buttons = []
    button_class_distribution = defaultdict(int)
    
    for xf in xml_files:
        content = xf.read_text(encoding="utf-8")
        clean_content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        for m in button_regex.finditer(clean_content):
            tag_text = m.group(0)
            tag_attrs = m.group(1)
            total_buttons += 1
            
            # Find class attribute
            class_match = re.search(r'class\s*=\s*["\']([^"\']+)["\']', tag_attrs)
            if class_match:
                classes = class_match.group(1).split()
                for c in classes:
                    if c.startswith("btn"):
                        button_class_distribution[c] += 1
                        if c in ROGUE_CLASSES:
                            pos = m.start()
                            line_num = content[:pos].count('\n') + 1
                            rogue_buttons.append({
                                "file": xf.name,
                                "line": line_num,
                                "class": c,
                                "reason": ROGUE_CLASSES[c],
                                "snippet": tag_text[:100].replace('\n', ' ')
                            })
                            
            # Check for inline style overriding colors
            if re.search(r'style\s*=\s*["\'][^"\']*(?:background|color|border)[^"\']*["\']', tag_attrs, re.IGNORECASE):
                pos = m.start()
                line_num = content[:pos].count('\n') + 1
                inline_styled_buttons.append({
                    "file": xf.name,
                    "line": line_num,
                    "snippet": tag_text[:100].replace('\n', ' ')
                })
                
    print(f"\n[*] Total Call-to-Action Buttons Audited: {total_buttons}")
    print(f"[*] Button Class Distribution:")
    for cls, count in sorted(button_class_distribution.items(), key=lambda x: -x[1]):
        status = "❌ ROGUE" if cls in ROGUE_CLASSES else "✅ Conforming"
        print(f"   • {cls:25}: {count:3} instances [{status}]")
        
    passed = (
        has_primary_token and 
        has_gradient_token and 
        has_btn_primary and 
        len(rogue_buttons) == 0 and 
        len(inline_styled_buttons) == 0
    )
    
    if rogue_buttons:
        print(f"\n❌ [FAIL] Found {len(rogue_buttons)} rogue button classes across views:")
        for rb in rogue_buttons:
            print(f"   • {rb['file']}:{rb['line']} [{rb['class']}] - {rb['reason']}")
            print(f"     Code: {rb['snippet']}")
    else:
        print(f"\n✅ [PASS] 0 rogue button classes detected.")
        
    if inline_styled_buttons:
        print(f"\n❌ [FAIL] Found {len(inline_styled_buttons)} buttons with inline styles:")
        for isb in inline_styled_buttons:
            print(f"   • {isb['file']}:{isb['line']} {isb['snippet']}")
    else:
        print(f"✅ [PASS] 0 inline style overrides on buttons.")
        
    return passed, {
        "total_buttons": total_buttons,
        "rogue_buttons": rogue_buttons,
        "inline_styled_buttons": inline_styled_buttons,
        "distribution": dict(button_class_distribution),
    }

# ==============================================================================
# 3. ADVERSARIAL STRESS TEST: SIBLING CARD HEIGHT & HBOX BASELINE LOCKING
# ==============================================================================
def stress_test_sibling_card_symmetry():
    log_section("3. ADVERSARIAL STRESS TEST: SIBLING CARD HEIGHT & HBOX BASELINE")
    
    scss_content = SCSS_FILE.read_text(encoding="utf-8") if SCSS_FILE.exists() else ""
    has_hbox_class = ".ins-card-row-balanced" in scss_content
    print(f"[*] SCSS .ins-card-row-balanced definition: {'✅ Present' if has_hbox_class else '❌ Missing'}")
    
    xml_files = sorted(list(VIEWS_DIR.glob("*.xml")))
    
    # Stress test 1: Find all sibling card rows (div.row containing col-* with card-like children)
    # A robust row check checks if .ins-card-row-balanced is applied on rows containing multiple cards
    row_pattern = re.compile(
        r'<div\b([^>]*?\bclass\s*=\s*["\'][^"\']*\brow\b[^"\']*["\'][^>]*>)(.*?)(?=<div\b[^>]*?\bclass\s*=\s*["\'][^"\']*\brow\b|(?:\s*</section>|\s*</main>|\s*</template>))',
        re.DOTALL | re.IGNORECASE
    )
    
    # Pattern to find card containers inside col columns
    card_pattern = re.compile(
        r'<div\b[^>]*?\bclass\s*=\s*["\'][^"\']*\bcol-(?:lg|md|sm)-[2346]\b[^"\']*["\'][^>]*>\s*'
        r'<(?:div|a)\b[^>]*?\bclass\s*=\s*["\']([^"\']*\b(?:card(?!-)|ins-bento-card|ins-ind-card|ins-proof-card|ins-pricing-card)\b[^\"\']*)["\'][^>]*>',
        re.DOTALL | re.IGNORECASE
    )
    
    total_cards = 0
    cards_with_h100 = 0
    cards_missing_h100 = []
    
    for xf in xml_files:
        content = xf.read_text(encoding="utf-8")
        clean_content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        for m in card_pattern.finditer(clean_content):
            total_cards += 1
            classes = m.group(1).split()
            if "h-100" in classes:
                cards_with_h100 += 1
            else:
                pos = m.start()
                line_num = content[:pos].count('\n') + 1
                cards_missing_h100.append({
                    "file": xf.name,
                    "line": line_num,
                    "snippet": m.group(0)[:100].replace('\n', ' ')
                })
                
    ratio = (cards_with_h100 / total_cards * 100) if total_cards > 0 else 100.0
    print(f"[*] Total Grid-Housed Sibling Cards Identified: {total_cards}")
    print(f"[*] Cards with 'h-100' Vertical Height Lock: {cards_with_h100}/{total_cards} ({ratio:.1f}%)")
    
    passed = (ratio >= 95.0) and has_hbox_class
    
    if cards_missing_h100:
        print(f"⚠️ [WARNING/FAIL] {len(cards_missing_h100)} cards lack 'h-100':")
        for cm in cards_missing_h100[:10]:
            print(f"   • {cm['file']}:{cm['line']} {cm['snippet']}")
    else:
        print("✅ [PASS] 100% of grid-housed sibling cards declare 'h-100'.")
        
    return passed, {
        "total_cards": total_cards,
        "cards_with_h100": cards_with_h100,
        "ratio": ratio,
        "missing_h100": cards_missing_h100,
    }

# ==============================================================================
# 4. ADVERSARIAL STRESS TEST: TYPOGRAPHIC ORPHAN PREVENTION (VIETNAMESE)
# ==============================================================================
def stress_test_typographic_orphans():
    log_section("4. ADVERSARIAL STRESS TEST: TYPOGRAPHIC ORPHAN PREVENTION")
    
    scss_content = SCSS_FILE.read_text(encoding="utf-8") if SCSS_FILE.exists() else ""
    has_balance = "text-wrap: balance" in scss_content
    has_pretty = "text-wrap: pretty" in scss_content
    
    print(f"[*] CSS text-wrap: balance declared: {'✅' if has_balance else '❌'}")
    print(f"[*] CSS text-wrap: pretty declared: {'✅' if has_pretty else '❌'}")
    
    xml_files = sorted(list(VIEWS_DIR.glob("*.xml")))
    
    # Adversarial heading inspection:
    # Extract all headings (h1-h6) and display classes
    heading_pattern = re.compile(r'<(h[1-4]|div\b[^>]*?\bclass\s*=\s*["\'][^"\']*\bdisplay-[1-6]\b[^"\']*["\'])[^>]*>(.*?)</\1>', re.DOTALL | re.IGNORECASE)
    
    total_headings = 0
    headings_with_orphan_risk = []
    headings_with_semantic_defense = 0
    
    for xf in xml_files:
        if xf.name in ["demo_request_views.xml", "website_menu.xml"]:
            continue
        content = xf.read_text(encoding="utf-8")
        clean_content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        for m in heading_pattern.finditer(clean_content):
            raw_inner = m.group(2)
            # Remove nested tags for text analysis
            text_only = re.sub(r'<[^>]+>', '', raw_inner).strip()
            text_only = html.unescape(text_only)
            text_only = re.sub(r'\s+', ' ', text_only).strip()
            
            if not text_only or len(text_only.split()) < 3:
                continue
                
            total_headings += 1
            words = text_only.split()
            last_word = words[-1]
            
            # Defense checks:
            # 1. &nbsp; before last word
            has_nbsp_end = bool(re.search(r'&nbsp;\s*[^\s<>&]+(\s*</[^>]+>)*\s*$', raw_inner.strip()))
            # 2. Semantic break tag <br class="d-none d-sm-inline"/>
            has_semantic_br = bool(re.search(r'<br\b[^>]*\bclass\s*=\s*["\'][^"\']*d-none\b[^"\']*["\'][^>]*>', raw_inner))
            # 3. Explicit ins-title-balance class
            has_balance_class = "ins-title-balance" in m.group(0)
            
            if has_nbsp_end or has_semantic_br or has_balance_class:
                headings_with_semantic_defense += 1
            else:
                if len(last_word) <= 8 and not has_balance:
                    pos = m.start()
                    line_num = content[:pos].count('\n') + 1
                    headings_with_orphan_risk.append({
                        "file": xf.name,
                        "line": line_num,
                        "last_word": last_word,
                        "title": text_only[:80]
                    })
                    
    print(f"[*] Total Major Headings Audited: {total_headings}")
    print(f"[*] Headings with Dedicated Semantic Defense (&nbsp; / <br class='d-none...'> / ins-title-balance): {headings_with_semantic_defense}")
    print(f"[*] Global CSS text-wrap: balance fallback active for modern rendering engines: {'✅ Yes' if has_balance else '❌ No'}")
    print(f"[*] Headings at high orphan risk in non-supporting engines: {len(headings_with_orphan_risk)}")
    
    passed = has_balance and has_pretty
    return passed, {
        "total_headings": total_headings,
        "with_semantic_defense": headings_with_semantic_defense,
        "has_balance": has_balance,
        "has_pretty": has_pretty,
    }

# ==============================================================================
# 5. ADVERSARIAL STRESS TEST: CLIENT DATA ANONYMIZATION AUDIT
# ==============================================================================
def stress_test_client_data_anonymization():
    log_section("5. ADVERSARIAL STRESS TEST: CLIENT DATA ANONYMIZATION")
    
    xml_files = sorted(list(VIEWS_DIR.glob("*.xml")))
    
    FORBIDDEN_IDENTIFIERS = [
        ("TÂN CẢNG SÀI GÒN", "Real seaport corporate entity name"),
        ("SNP", "Saigon Newport corporate abbreviation (in customer ribbon context)"),
        ("TẬP ĐOÀN HÒA PHÁT", "Real industrial corporate entity name"),
        ("HÒA PHÁT DUNG QUẤT", "Real steel manufacturing subsidiary entity name"),
        ("an.nguyen@vinfast.vn", "Real corporate email reference"),
    ]
    
    detections = []
    
    for xf in xml_files:
        content = xf.read_text(encoding="utf-8")
        clean_content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        for identifier, desc in FORBIDDEN_IDENTIFIERS:
            # Exclude code variable names if any, focus on visible text
            matches = list(re.finditer(re.escape(identifier), clean_content, re.IGNORECASE))
            for m in matches:
                pos = m.start()
                line_num = content[:pos].count('\n') + 1
                detections.append({
                    "file": xf.name,
                    "line": line_num,
                    "match": identifier,
                    "description": desc,
                    "context": clean_content[max(0, pos-40):min(len(clean_content), pos+80)].replace('\n', ' ')
                })
                
    # Check if Founder Zen Pham branding is preserved across any views
    has_zen_pham = any("Zen Pham" in xf.read_text(encoding="utf-8") for xf in xml_files)
        
    print(f"[*] Founder Zen Pham Personal Authority Branding: {'✅ Preserved' if has_zen_pham else '❌ Missing'}")
    print(f"[*] Forbidden Corporate Identifiers Audited: {len(FORBIDDEN_IDENTIFIERS)}")
    print(f"[*] Real Corporate Client Detections in views/*.xml: {len(detections)}")
    
    if detections:
        print(f"❌ [FAIL] Found {len(detections)} non-anonymized corporate client references:")
        for d in detections:
            print(f"   • {d['file']}:{d['line']} [{d['match']}] - {d['description']}")
            print(f"     Context: {d['context']}")
    else:
        print("✅ [PASS] 0 forbidden corporate client references detected in views/*.xml.")
        
    passed = (len(detections) == 0) and has_zen_pham
    return passed, {"detections": detections, "has_zen_pham": has_zen_pham}

# ==============================================================================
# MAIN RUNNER
# ==============================================================================
def main():
    print("=" * 78)
    print("  CHALLENGER 1: EMPIRICAL ADVERSARIAL UI/UX STRESS-TESTING SUITE")
    print("=" * 78)
    
    results = {}
    r1_pass, r1_data = stress_test_zero_inline_styles()
    results["inline_styles"] = {"pass": r1_pass, "data": r1_data}
    
    r2_pass, r2_data = stress_test_button_conformance()
    results["buttons"] = {"pass": r2_pass, "data": r2_data}
    
    r3_pass, r3_data = stress_test_sibling_card_symmetry()
    results["card_symmetry"] = {"pass": r3_pass, "data": r3_data}
    
    r4_pass, r4_data = stress_test_typographic_orphans()
    results["typographic_orphans"] = {"pass": r4_pass, "data": r4_data}
    
    r5_pass, r5_data = stress_test_client_data_anonymization()
    results["anonymization"] = {"pass": r5_pass, "data": r5_data}
    
    log_section("CHALLENGER 1 ADVERSARIAL STRESS-TEST SUMMARY")
    print(f"1. Zero Inline Styles Audit           : {'✅ PASS' if r1_pass else '❌ FAIL'}")
    print(f"2. Button Theme & Rogue Classes Audit : {'✅ PASS' if r2_pass else '❌ FAIL'}")
    print(f"3. Sibling Card Height Symmetry Audit : {'✅ PASS' if r3_pass else '❌ FAIL'}")
    print(f"4. Typographic Orphan Prevention Audit: {'✅ PASS' if r4_pass else '❌ FAIL'}")
    print(f"5. Corporate Anonymization & Branding : {'✅ PASS' if r5_pass else '❌ FAIL'}")
    
    overall_pass = r1_pass and r2_pass and r3_pass and r4_pass and r5_pass
    print("-" * 78)
    if overall_pass:
        print("🏆 ADVERSARIAL VERDICT: ALL ADVERSARIAL STRESS TESTS PASSED")
    else:
        print("⚠️ ADVERSARIAL VERDICT: DEFECTS DETECTED — REJECTION OR MITIGATION REQUIRED")
    print("=" * 78)
    
    return 0 if overall_pass else 1

if __name__ == "__main__":
    sys.exit(main())
