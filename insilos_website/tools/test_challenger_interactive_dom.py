#!/usr/bin/env python3
"""
Insilos Empirical Challenger: Interactive Components & DOM Test Suite
=====================================================================
Rigorous automated Playwright stress-testing of:
1. 3D Risk Cockpit Stack on /compliance (DOM hooks, event bindings, parallax, toggles, exceptions).
2. Mega-menus dropdown hover telemetry (#ins_megamenu_industries, #ins_megamenu_solutions, preview cards, dataset bindings).
3. Dropzones & editor compatibility (/brochure?enable_editor=1, /dossiers?enable_editor=1, data-snippet, data-name, oe_structure).
4. Responsive layout simulation across Desktop (1920x1080), Tablet (768x1024), and Mobile (375x812, 390x844, 412x915), detecting horizontal scroll overflows.
"""

import sys
import os
import json
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("INSILOS_BASE_URL", "http://localhost:28069")
VIEWS_DIR = Path("/home/zen/O20/enterprise/insilos_website/views")

def audit_dropzones_and_snippets_static():
    """Verify that all sections in views/*.xml declare valid data-snippet and data-name,
    and all page templates have oe_structure dropzones."""
    print("\n" + "="*80)
    print("CHALLENGE 3A: Static Dropzones & Snippet Metadata Audit (views/*.xml)")
    print("="*80)

    xml_files = list(VIEWS_DIR.glob("*.xml"))
    total_sections = 0
    valid_sections = 0
    invalid_sections = []
    
    # Specific newly integrated files from M1-M4
    target_files = [
        "trust_compliance.xml",
        "brochure.xml",
        "dossiers.xml",
        "industry_verticals.xml",
        "home.xml",
        "platform_solutions.xml",
        "website_templates.xml",
    ]

    oe_structure_files = {}

    for xf in xml_files:
        content = xf.read_text(encoding="utf-8")
        has_oe = 'class="oe_structure' in content
        oe_structure_files[xf.name] = has_oe

        # Search for <section
        sec_pattern = re.compile(r'<section\b([^>]*)>', re.DOTALL)
        for m in sec_pattern.finditer(content):
            attrs = m.group(1)
            total_sections += 1
            has_snippet = 'data-snippet=' in attrs
            has_name = 'data-name=' in attrs
            if has_snippet and has_name:
                valid_sections += 1
            else:
                invalid_sections.append({
                    "file": xf.name,
                    "attrs": attrs.strip()[:80]
                })

    print(f"  • Total <section> tags analyzed: {total_sections}")
    print(f"  • Sections with valid data-snippet AND data-name: {valid_sections}/{total_sections}")
    print(f"  • Missing snippet metadata: {len(invalid_sections)}")

    if invalid_sections:
        for inv in invalid_sections[:10]:
            print(f"    ❌ [{inv['file']}] {inv['attrs']}")
    else:
        print("  ✅ All sections declare valid data-snippet and data-name attributes!")

    # Check target files for oe_structure
    print("\n  • Page templates dropzone (oe_structure) check:")
    for tf in ["trust_compliance.xml", "brochure.xml", "dossiers.xml", "industry_verticals.xml", "home.xml", "platform_solutions.xml"]:
        status = oe_structure_files.get(tf, False)
        print(f"    - {tf:25} : {'✅ oe_structure present' if status else '❌ MISSING oe_structure'}")

    return len(invalid_sections) == 0


def run_interactive_playwright_suite():
    print("\n" + "="*80)
    print("🔥 LAUNCHING PLAYWRIGHT HEADLESS FOR EMPIRICAL INTERACTIVE VERIFICATION")
    print(f"   Target URL: {BASE_URL}")
    print("="*80)

    report = {
        "cockpit_3d": {},
        "megamenu_telemetry": {},
        "editor_mode": {},
        "responsive_overflow": {},
        "console_errors": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) InsilosChallenger/2.0"
        )

        page = context.new_page()

        # Capture console messages and unhandled exceptions
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(f"UNHANDLED EXCEPTION: {err}"))
        page.on("console", lambda msg: page_errors.append(f"CONSOLE {msg.type.upper()}: {msg.text}") if msg.type in ["error"] else None)

        # =====================================================================
        # 1. 3D RISK COCKPIT STACK ON /compliance
        # =====================================================================
        print("\n" + "-"*80)
        print("CHALLENGE 1: 3D Risk Cockpit Stack Verification on /compliance")
        print("-"*80)

        page.goto(f"{BASE_URL}/compliance", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1000)

        cockpit_dom = page.evaluate("""() => {
            const section = document.querySelector("#compliance-3d-cockpit, .s_c3ai_3d_cockpit");
            if (!section) return { found: false, error: "Section #compliance-3d-cockpit not found" };

            const viewport = section.querySelector(".ins-3d-cockpit-viewport");
            if (!viewport) return { found: false, error: ".ins-3d-cockpit-viewport not found" };

            const deck = viewport.querySelector(".ins-cloud-cockpit");
            const btnIso = viewport.querySelector(".ins-btn-3d-isometric");
            const btnExp = viewport.querySelector(".ins-btn-3d-exploded");
            const cards = Array.from(viewport.querySelectorAll(".ins-cockpit-card"));
            const busSvg = viewport.querySelector(".ins-cockpit-bus-svg");

            // Check bindings and attributes
            const viewportAttrs = {};
            for (let i = 0; i < viewport.attributes.length; i++) {
                const a = viewport.attributes[i];
                viewportAttrs[a.name] = a.value;
            }

            const cardsInfo = cards.map(c => ({
                layer: c.getAttribute("data-layer"),
                plane: c.getAttribute("data-plane"),
                actTarget: c.getAttribute("data-act-target"),
                highlighted: c.classList.contains("ins-act-highlight"),
                title: (c.querySelector(".ins-cockpit-title") || {}).innerText || "",
                badge: (c.querySelector(".ins-cockpit-badge") || {}).innerText || ""
            }));

            // Check toggle buttons data-mode and classes
            const isoMode = btnIso ? btnIso.getAttribute("data-mode") : null;
            const expMode = btnExp ? btnExp.getAttribute("data-mode") : null;

            return {
                found: true,
                sectionSnippet: section.getAttribute("data-snippet"),
                sectionName: section.getAttribute("data-name"),
                hasViewport: !!viewport,
                hasDeck: !!deck,
                hasBtnIso: !!btnIso,
                hasBtnExp: !!btnExp,
                isoMode: isoMode,
                expMode: expMode,
                btnIsoClasses: btnIso ? btnIso.className : "",
                btnExpClasses: btnExp ? btnExp.className : "",
                cardsCount: cards.length,
                cardsInfo: cardsInfo,
                viewportAttrs: viewportAttrs,
                hasBusSvg: !!busSvg
            };
        }""")

        report["cockpit_3d"]["dom"] = cockpit_dom
        print(f"  • Section Found: {'✅ Yes' if cockpit_dom.get('found') else '❌ No'}")
        if cockpit_dom.get("found"):
            print(f"    - data-snippet: {cockpit_dom.get('sectionSnippet')}")
            print(f"    - data-name: {cockpit_dom.get('sectionName')}")
            print(f"    - Total Cockpit Cards: {cockpit_dom.get('cardsCount')}")
            for c in cockpit_dom.get("cardsInfo", []):
                print(f"      Layer {c['layer']}: {c['title']} | Badge: {c['badge']} | data-plane={c['plane']} | active={c['highlighted']}")

            print(f"    - 3D Toggle Buttons: ISO ({'✅ Present' if cockpit_dom.get('hasBtnIso') else '❌ Missing'}), EXP ({'✅ Present' if cockpit_dom.get('hasBtnExp') else '❌ Missing'})")
            print(f"    - Toggle Button data-mode attributes: ISO data-mode={cockpit_dom.get('isoMode')}, EXP data-mode={cockpit_dom.get('expMode')}")

        # Now test Cockpit Interactions in Playwright:
        print("\n  • Testing Cockpit Mode Toggling & Parallax:")
        cockpit_interaction = page.evaluate("""() => {
            const viewport = document.querySelector(".ins-3d-cockpit-viewport");
            const deck = viewport ? viewport.querySelector(".ins-cloud-cockpit") : null;
            const btnIso = viewport ? viewport.querySelector(".ins-btn-3d-isometric") : null;
            const btnExp = viewport ? viewport.querySelector(".ins-btn-3d-exploded") : null;

            if (!viewport || !deck || !btnIso || !btnExp) {
                return { success: false, error: "Viewport components missing" };
            }

            const results = {};

            // 1. Click Exploded Mode
            btnExp.click();
            results.afterExpClick = {
                deckHasExplodedClass: deck.classList.contains("ins-exploded-mode"),
                btnExpActive: btnExp.classList.contains("active"),
                btnIsoActive: btnIso.classList.contains("active")
            };

            // 2. Click Isometric Mode
            btnIso.click();
            results.afterIsoClick = {
                deckHasExplodedClass: deck.classList.contains("ins-exploded-mode"),
                btnIsoActive: btnIso.classList.contains("active"),
                btnExpActive: btnExp.classList.contains("active")
            };

            // 3. Click Layer Card 2, 3, 4 and verify highlight
            const cards = Array.from(deck.querySelectorAll(".ins-cockpit-card"));
            const card2 = cards[1];
            if (card2) {
                card2.click();
                results.afterCard2Click = {
                    card2Highlighted: card2.classList.contains("ins-act-highlight"),
                    card1Highlighted: cards[0].classList.contains("ins-act-highlight"),
                    busTap2Active: (deck.querySelector(".ins-bus-tap-2") || {}).classList ? deck.querySelector(".ins-bus-tap-2").classList.contains("active") : false,
                    busBranch2Active: (deck.querySelector(".ins-bus-branch-2") || {}).classList ? deck.querySelector(".ins-bus-branch-2").classList.contains("active") : false
                };
            }

            // Return to Card 1
            if (cards[0]) {
                cards[0].click();
            }

            return { success: true, results };
        }""")

        report["cockpit_3d"]["interaction"] = cockpit_interaction
        print(f"  • Exploded Mode Toggle: {'✅ Success' if cockpit_interaction.get('results', {}).get('afterExpClick', {}).get('deckHasExplodedClass') else '❌ Failed'}")
        print(f"  • Isometric Mode Toggle: {'✅ Success' if not cockpit_interaction.get('results', {}).get('afterIsoClick', {}).get('deckHasExplodedClass') else '❌ Failed'}")
        print(f"  • Card Click 2-Way Layer Binding: {'✅ Success' if cockpit_interaction.get('results', {}).get('afterCard2Click', {}).get('card2Highlighted') else '❌ Failed'}")

        # Test Parallax Mousemove
        print("  • Testing 3D Gyroscope Mouse Parallax (mousemove event simulation):")
        parallax_result = page.evaluate("""() => {
            const viewport = document.querySelector(".ins-3d-cockpit-viewport");
            const deck = viewport ? viewport.querySelector(".ins-cloud-cockpit") : null;
            if (!viewport || !deck) return { success: false };

            const rect = viewport.getBoundingClientRect();
            // Dispatch mousemove
            const evt = new MouseEvent("mousemove", {
                clientX: rect.left + rect.width * 0.8,
                clientY: rect.top + rect.height * 0.2,
                bubbles: true
            });
            viewport.dispatchEvent(evt);

            // Read CSS variables
            const tiltX = deck.style.getPropertyValue("--tilt-x");
            const tiltY = deck.style.getPropertyValue("--tilt-y");

            return {
                success: true,
                tiltX: tiltX,
                tiltY: tiltY
            };
        }""")
        report["cockpit_3d"]["parallax"] = parallax_result
        print(f"    - Tilt CSS vars after mousemove: --tilt-x={parallax_result.get('tiltX')}, --tilt-y={parallax_result.get('tiltY')}")

        # =====================================================================
        # 2. MEGA-MENUS DROPDOWN INTERACTIONS & HOVER TELEMETRY
        # =====================================================================
        print("\n" + "-"*80)
        print("CHALLENGE 2: Mega-menus Dropdown Interactions & Hover Telemetry Audit")
        print("-"*80)

        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(800)

        # Audit #ins_megamenu_solutions items and hover preview
        sol_menu_audit = page.evaluate("""() => {
            const menu = document.querySelector("#ins_megamenu_solutions");
            if (!menu) return { found: false, error: "#ins_megamenu_solutions not found" };

            const card = document.querySelector("#ins_sol_preview_card");
            const items = Array.from(menu.querySelectorAll(".ins-menu-link-item"));

            const requiredAttrs = ["badge", "title", "icon", "m1Val", "m1Lbl", "m2Val", "m2Lbl", "m3Val", "m3Lbl", "desc", "href"];

            const itemDetails = items.map((it, idx) => {
                const missing = [];
                for (const attr of requiredAttrs) {
                    if (!it.dataset[attr] && (attr !== "href" || !it.getAttribute("href"))) {
                        missing.push(attr);
                    }
                }
                return {
                    index: idx + 1,
                    title: it.dataset.title || "",
                    badge: it.dataset.badge || "",
                    icon: it.dataset.icon || "",
                    href: it.dataset.href || it.getAttribute("href"),
                    m1Val: it.dataset.m1Val || "",
                    m2Val: it.dataset.m2Val || "",
                    m3Val: it.dataset.m3Val || "",
                    missing: missing
                };
            });

            return {
                found: true,
                hasPreviewCard: !!card,
                itemsCount: items.length,
                validItemsCount: itemDetails.filter(d => d.missing.length === 0).length,
                itemDetails: itemDetails
            };
        }""")

        report["megamenu_telemetry"]["solutions"] = sol_menu_audit
        print(f"  • #ins_megamenu_solutions Found: {'✅ Yes' if sol_menu_audit.get('found') else '❌ No'}")
        print(f"  • Total Menu Items in Solutions: {sol_menu_audit.get('itemsCount')}")
        print(f"  • Items with 100% Required Dataset Attributes: {sol_menu_audit.get('validItemsCount')}/{sol_menu_audit.get('itemsCount')}")
        if sol_menu_audit.get("validItemsCount") < sol_menu_audit.get("itemsCount", 0):
            for it in sol_menu_audit.get("itemDetails", []):
                if it["missing"]:
                    print(f"    ❌ Item {it['index']} '{it['title']}': missing {it['missing']}")

        # Audit #ins_megamenu_industries items and hover preview
        ind_menu_audit = page.evaluate("""() => {
            const menu = document.querySelector("#ins_megamenu_industries");
            if (!menu) return { found: false, error: "#ins_megamenu_industries not found" };

            const card = document.querySelector("#ins_ind_preview_card");
            const items = Array.from(menu.querySelectorAll(".ins-menu-link-item"));

            const requiredAttrs = ["badge", "title", "icon", "m1Val", "m1Lbl", "m2Val", "m2Lbl", "m3Val", "m3Lbl", "desc", "href"];

            const itemDetails = items.map((it, idx) => {
                const missing = [];
                for (const attr of requiredAttrs) {
                    if (!it.dataset[attr] && (attr !== "href" || !it.getAttribute("href"))) {
                        missing.push(attr);
                    }
                }
                return {
                    index: idx + 1,
                    title: it.dataset.title || "",
                    badge: it.dataset.badge || "",
                    icon: it.dataset.icon || "",
                    href: it.dataset.href || it.getAttribute("href"),
                    m1Val: it.dataset.m1Val || "",
                    m2Val: it.dataset.m2Val || "",
                    m3Val: it.dataset.m3Val || "",
                    missing: missing
                };
            });

            return {
                found: true,
                hasPreviewCard: !!card,
                itemsCount: items.length,
                validItemsCount: itemDetails.filter(d => d.missing.length === 0).length,
                itemDetails: itemDetails
            };
        }""")

        report["megamenu_telemetry"]["industries"] = ind_menu_audit
        print(f"  • #ins_megamenu_industries Found: {'✅ Yes' if ind_menu_audit.get('found') else '❌ No'}")
        print(f"  • Total Menu Items in Industries: {ind_menu_audit.get('itemsCount')}")
        print(f"  • Items with 100% Required Dataset Attributes: {ind_menu_audit.get('validItemsCount')}/{ind_menu_audit.get('itemsCount')}")
        if ind_menu_audit.get("validItemsCount") < ind_menu_audit.get("itemsCount", 0):
            for it in ind_menu_audit.get("itemDetails", []):
                if it["missing"]:
                    print(f"    ❌ Item {it['index']} '{it['title']}': missing {it['missing']}")

        # Simulate Hover on Item 9 (Vertical Resilience Core) in Solutions Mega-menu:
        print("\n  • Testing Live Hover Telemetry Switching on Solutions Preview Card:")
        hover_sol_test = page.evaluate("""() => {
            return new Promise((resolve) => {
                const item = document.querySelector("#ins_megamenu_solutions a[data-href='/brochure']");
                const card = document.querySelector("#ins_sol_preview_card");
                if (!item || !card) {
                    resolve({ success: false, error: "Target item or card not found" });
                    return;
                }

                // Listen for custom event
                let eventReceived = false;
                let eventDetail = null;
                const handler = (e) => {
                    eventReceived = true;
                    eventDetail = e.detail;
                };
                document.addEventListener("insilos-menu-preview-change", handler, { once: true });

                // Dispatch mouseenter
                item.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));

                // Wait 120ms (debounce is 50ms)
                setTimeout(() => {
                    const titleEl = card.querySelector(".ins-sol-preview-title");
                    const badgeEl = card.querySelector(".ins-sol-preview-badge");
                    const btnEl = card.querySelector(".ins-sol-preview-btn");
                    const m1Val = card.querySelector(".ins-sol-m1-val");

                    resolve({
                        success: true,
                        eventReceived: eventReceived,
                        eventDetail: eventDetail,
                        renderedTitle: titleEl ? titleEl.textContent : "",
                        renderedBadge: badgeEl ? badgeEl.textContent : "",
                        renderedHref: btnEl ? btnEl.getAttribute("href") : "",
                        renderedM1Val: m1Val ? m1Val.textContent : ""
                    });
                }, 120);
            });
        }""")

        report["megamenu_telemetry"]["hover_sol_test"] = hover_sol_test
        print(f"    - Hover trigger on /brochure item: {'✅ Success' if hover_sol_test.get('success') else '❌ Failed'}")
        print(f"    - Preview Card Title: '{hover_sol_test.get('renderedTitle')}'")
        print(f"    - Preview Card Badge: '{hover_sol_test.get('renderedBadge')}'")
        print(f"    - Preview Card Button Href: '{hover_sol_test.get('renderedHref')}'")
        print(f"    - Custom Event 'insilos-menu-preview-change': {'✅ Dispatched' if hover_sol_test.get('eventReceived') else '❌ Not Dispatched'}")

        # Simulate Hover on Petrochem (Item 1) and Metallurgy in Industries Mega-menu:
        print("\n  • Testing Live Hover Telemetry Switching on Industries Preview Card:")
        hover_ind_test = page.evaluate("""() => {
            return new Promise((resolve) => {
                const item = document.querySelector("#ins_megamenu_industries a[data-href='/industries/petrochem']");
                const card = document.querySelector("#ins_ind_preview_card");
                if (!item || !card) {
                    resolve({ success: false, error: "Petrochem item or card not found" });
                    return;
                }

                item.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));

                setTimeout(() => {
                    const titleEl = card.querySelector(".ins-ind-preview-title");
                    const badgeEl = card.querySelector(".ins-ind-preview-badge");
                    const btnEl = card.querySelector(".ins-ind-preview-btn");
                    const m1Val = card.querySelector(".ins-ind-m1-val");

                    resolve({
                        success: true,
                        renderedTitle: titleEl ? titleEl.textContent : "",
                        renderedBadge: badgeEl ? badgeEl.textContent : "",
                        renderedHref: btnEl ? btnEl.getAttribute("href") : "",
                        renderedM1Val: m1Val ? m1Val.textContent : ""
                    });
                }, 120);
            });
        }""")

        report["megamenu_telemetry"]["hover_ind_test"] = hover_ind_test
        print(f"    - Hover trigger on Petrochem item: {'✅ Success' if hover_ind_test.get('success') else '❌ Failed'}")
        print(f"    - Preview Card Title: '{hover_ind_test.get('renderedTitle')}'")
        print(f"    - Preview Card Badge: '{hover_ind_test.get('renderedBadge')}'")
        print(f"    - Preview Card Button Href: '{hover_ind_test.get('renderedHref')}'")

        # =====================================================================
        # 3. WEBSITE EDITOR (?enable_editor=1) COMPATIBILITY AUDIT
        # =====================================================================
        print("\n" + "-"*80)
        print("CHALLENGE 3B: Website Editor Mode (?enable_editor=1) Verification")
        print("-"*80)

        editor_routes = [
            "/brochure?enable_editor=1",
            "/dossiers?enable_editor=1",
            "/compliance?enable_editor=1",
            "/industries/petrochem?enable_editor=1",
        ]

        editor_results = {}
        for eroute in editor_routes:
            sub_errors = []
            page.on("pageerror", lambda err: sub_errors.append(f"UNHANDLED: {err}"))
            resp = page.goto(f"{BASE_URL}{eroute}", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1000)

            status = resp.status if resp else 0
            has_oe = page.evaluate("() => document.querySelectorAll('.oe_structure').length")
            has_snippets_sidebar = page.evaluate("() => !!document.querySelector('#oe_snippets, .o_we_website_top_actions, body.editor_enable')")

            editor_results[eroute] = {
                "status": status,
                "oe_structure_count": has_oe,
                "errors": sub_errors
            }
            print(f"  • {eroute:38} | HTTP {status} | Dropzones (.oe_structure): {has_oe} | JS Errors: {len(sub_errors)}")
            if sub_errors:
                for se in sub_errors:
                    print(f"    ❌ {se}")

        report["editor_mode"] = editor_results

        # =====================================================================
        # 4. RESPONSIVE LAYOUT SIMULATION & HORIZONTAL OVERFLOW STRESS-TEST
        # =====================================================================
        print("\n" + "-"*80)
        print("CHALLENGE 4: Multi-Viewport Responsive Stacking & Horizontal Overflow Audit")
        print("-"*80)

        viewports = [
            {"name": "Desktop 1920x1080", "width": 1920, "height": 1080},
            {"name": "Desktop 1440x900",  "width": 1440, "height": 900},
            {"name": "Tablet Landscape 1024x768", "width": 1024, "height": 768},
            {"name": "Tablet Portrait 768x1024",  "width": 768, "height": 1024},
            {"name": "Mobile Pixel 412x915",      "width": 412, "height": 915},
            {"name": "Mobile iPhone 390x844",     "width": 390, "height": 844},
            {"name": "Mobile Compact 375x812",    "width": 375, "height": 812},
        ]

        routes_to_test = [
            "/compliance",
            "/brochure",
            "/dossiers",
            "/industries/petrochem",
            "/industries/gas-pipeline",
            "/industries/metallurgy",
            "/industries/thermal-power",
            "/industries/pharma",
            "/solutions",
            "/"
        ]

        overflow_defects = []

        for vp_info in viewports:
            print(f"\n  📱 Testing Viewport: {vp_info['name']} ({vp_info['width']}x{vp_info['height']})")
            context.close()
            context = browser.new_context(
                viewport={"width": vp_info["width"], "height": vp_info["height"]},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) InsilosChallenger/2.0" if vp_info["width"] < 600 else "Mozilla/5.0 InsilosChallenger/2.0"
            )
            page = context.new_page()

            for r in routes_to_test:
                page.goto(f"{BASE_URL}{r}", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(300)

                overflow_check = page.evaluate("""(vpWidth) => {
                    const scrollW = document.documentElement.scrollWidth;
                    const clientW = document.documentElement.clientWidth;
                    const innerW = window.innerWidth;
                    const hasDocOverflow = scrollW > innerW + 1;

                    // Scan for offending elements that protrude beyond innerWidth
                    const offenders = [];
                    const allEls = document.querySelectorAll("section, div, h1, h2, h3, p, table, .container, .row, .col, [class*='col-']");
                    for (const el of allEls) {
                        const rect = el.getBoundingClientRect();
                        if (rect.right > innerW + 2) {
                            offenders.push({
                                tag: el.tagName.toLowerCase(),
                                className: (el.className || '').toString().slice(0, 50),
                                right: Math.round(rect.right),
                                width: Math.round(rect.width)
                            });
                            if (offenders.length >= 3) break;
                        }
                    }

                    return {
                        scrollWidth: scrollW,
                        innerWidth: innerW,
                        hasOverflow: hasDocOverflow,
                        offenders: offenders
                    };
                }""", vp_info["width"])

                if overflow_check["hasOverflow"]:
                    overflow_defects.append({
                        "viewport": vp_info["name"],
                        "route": r,
                        "scrollWidth": overflow_check["scrollWidth"],
                        "innerWidth": overflow_check["innerWidth"],
                        "offenders": overflow_check["offenders"]
                    })
                    print(f"    ❌ OVERFLOW DETECTED: {r:24} | scrollWidth={overflow_check['scrollWidth']} > innerWidth={overflow_check['innerWidth']}")
                    for off in overflow_check["offenders"]:
                        print(f"       -> Element: <{off['tag']} class='{off['className']}'> right={off['right']}px")
                else:
                    print(f"    ✅ Clean: {r:24} | scrollWidth={overflow_check['scrollWidth']} == innerWidth={overflow_check['innerWidth']}")

        report["responsive_overflow"]["defects"] = overflow_defects
        report["console_errors"] = page_errors

        browser.close()

    return report

if __name__ == "__main__":
    gate3a_pass = audit_dropzones_and_snippets_static()
    report = run_interactive_playwright_suite()

    # Save detailed report
    report_file = Path("/home/zen/O20/.agents/teamwork/challenger_interactive_dom/test_report.json")
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[REPORT SAVED] -> {report_file}")
