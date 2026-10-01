#!/usr/bin/env python3
"""
Adversarial Security, Data Anonymization & Route Integrity Challenger Test Suite
================================================================================
Empirical test suite for Insilos Enterprise Website (Odoo 20).
Audits:
1. Live penetration of 35+ routes on http://localhost:28069 (HTTP 200, non-empty, zero tracebacks).
2. Confidentiality & Data Anonymization scan (MST tax IDs, customer emails, contracts).
3. Sole Founder Branding Verification (Founder Zen Pham).
4. Canonical domain & OpenGraph audit (zero insilos.ai in website_templates.xml, JSON-LD syntax, live server vs disk).
5. Adversarial Demo Request POST funnel testing (HTTP 303 redirect, validation, honeypot, XSS/SQLi resilience).
"""

import sys
import os
import re
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
from pathlib import Path
from collections import defaultdict

BASE_URL = os.environ.get("INSILOS_BASE_URL", "http://localhost:28069")
BASE_DIR = Path(__file__).resolve().parent.parent
VIEWS_DIR = BASE_DIR / "views"

ROUTES_TO_PROBE = [
    # Core Public Pages
    {"path": "/", "name": "Homepage", "expected_code": 200},
    {"path": "/platform", "name": "Platform Overview", "expected_code": 200},
    {"path": "/solutions", "name": "Solutions Directory", "expected_code": 200},
    {"path": "/industries", "name": "101 Industries Catalog", "expected_code": 200},
    {"path": "/pricing", "name": "Pricing & Micro-Ledger", "expected_code": 200},
    {"path": "/about", "name": "About & Zero-Trust Shield", "expected_code": 200},
    {"path": "/resources", "name": "Resources & Knowledge Hub", "expected_code": 200},
    {"path": "/request-demo", "name": "Request Demo Walkthrough", "expected_code": 200},
    {"path": "/trust", "name": "Sovereign Trust & Security", "expected_code": 200},
    {"path": "/compliance", "name": "Regulatory GRC Architecture", "expected_code": 200},
    {"path": "/sandbox", "name": "Interactive Industrial Sandbox", "expected_code": 200},
    {"path": "/privacy", "name": "Privacy Policy", "expected_code": 200},
    {"path": "/privacy-policy", "name": "Privacy Policy Alias", "expected_code": 200},
    {"path": "/media-credits", "name": "Media Credits & Attribution", "expected_code": 200},
    {"path": "/showcase-3d", "name": "3D Cinematic Showcase", "expected_code": 200},
    {"path": "/interactive-3d", "name": "Interactive 3D Digital Twin Suite", "expected_code": 200},
    {"path": "/thank-you", "name": "Demo Confirmation Page", "expected_code": 200},

    # Dedicated Solution Routes
    {"path": "/solutions/vertical-idp", "name": "Vertical IDP Solution", "expected_code": 200},
    {"path": "/solutions/enterprise-knowledge-graph", "name": "Enterprise Knowledge Graph", "expected_code": 200},
    {"path": "/solutions/trade-compliance", "name": "Trade Compliance Solution", "expected_code": 200},
    {"path": "/solutions/field-service-intelligence", "name": "Field Service Intelligence", "expected_code": 200},
    {"path": "/solutions/asset-reliability", "name": "Asset Reliability Solution", "expected_code": 200},
    {"path": "/solutions/logistics-control-tower", "name": "Logistics Control Tower", "expected_code": 200},
    {"path": "/solutions/process-optimization", "name": "Process Optimization Solution", "expected_code": 200},
    {"path": "/solutions/industrial-showcase", "name": "Industrial Showcase", "expected_code": 200},

    # Dedicated & Extended Industry Routes
    {"path": "/industries/logistics", "name": "Logistics Dedicated Industry", "expected_code": 200},
    {"path": "/industries/pharma", "name": "Pharma Dedicated Industry", "expected_code": 200},
    {"path": "/industries/energy", "name": "Energy Dedicated Industry", "expected_code": 200},
    {"path": "/industries/fsm", "name": "Field Service Operations Industry", "expected_code": 200},
    {"path": "/industries/freight", "name": "Freight Forwarding Industry Fallback", "expected_code": 200},
    {"path": "/industries/cold_chain", "name": "Cold Chain Industry Fallback", "expected_code": 200},

    # Resources Technical Whitepapers
    {"path": "/resources/operational-ai", "name": "Operational AI Whitepaper", "expected_code": 200},
    {"path": "/resources/vertical-idp-logistics-roi", "name": "Logistics IDP ROI Whitepaper", "expected_code": 200},
    {"path": "/resources/trade-compliance-handbook", "name": "Trade Compliance Handbook", "expected_code": 200},

    # Vietnamese Prefixed Routes
    {"path": "/vi/trust", "name": "VI Trust Page", "expected_code": 200},
    {"path": "/vi/compliance", "name": "VI Compliance Page", "expected_code": 200},
    {"path": "/vi/sandbox", "name": "VI Sandbox Page", "expected_code": 200},
    {"path": "/vi/privacy", "name": "VI Privacy Policy", "expected_code": 200},
    {"path": "/vi/showcase-3d", "name": "VI Showcase 3D", "expected_code": 200},
    {"path": "/vi/interactive-3d", "name": "VI Interactive 3D", "expected_code": 200},

    # Boundary 404 Check
    {"path": "/solutions/non-existent-solution-12345", "name": "Boundary 404 Solution", "expected_code": 404},
    {"path": "/industries/unregistered-industry-67890", "name": "Boundary 404 Industry", "expected_code": 404},
    {"path": "/resources/non-existent-article-99999", "name": "Boundary 404 Resource", "expected_code": 404},
]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_route(path, timeout=25):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "InsilosAdversarialChallenger/2.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            body = resp.read().decode("utf-8", errors="replace")
            headers = dict(resp.headers)
            return code, body, headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, dict(e.headers)
    except Exception as e:
        return 0, str(e), {}


def test_1_probe_all_routes():
    print("\n" + "=" * 80)
    print("TASK 1: LIVE HTTP PENETRATION & INTEGRITY PROBE (35+ ROUTES)")
    print("=" * 80)

    total_probed = 0
    passed_count = 0
    failed_routes = []
    route_details = []

    for r in ROUTES_TO_PROBE:
        total_probed += 1
        path = r["path"]
        name = r["name"]
        expected = r["expected_code"]

        code, body, headers = fetch_route(path)
        is_expected = (code == expected)
        has_min_size = len(body) > 500 if expected == 200 else True
        has_no_traceback = ("Traceback (most recent call last)" not in body and "Internal Server Error" not in body) if expected == 200 else True

        route_ok = is_expected and has_min_size and has_no_traceback
        if route_ok:
            passed_count += 1
            print(f"  ✅ [{code}] {path:<42} | {name:<32} ({len(body)} bytes)")
        else:
            failed_routes.append({
                "path": path,
                "name": name,
                "expected": expected,
                "actual": code,
                "size": len(body),
                "has_traceback": not has_no_traceback
            })
            print(f"  ❌ [{code}] {path:<42} | {name:<32} (Expected: {expected}, Size: {len(body)})")

        route_details.append({
            "path": path,
            "status": code,
            "size": len(body),
            "ok": route_ok,
            "body": body if expected == 200 else ""
        })

    print(f"\nRoute Penetration Summary: {passed_count}/{total_probed} Passed ({passed_count/total_probed*100:.1f}%)")
    return (len(failed_routes) == 0), route_details, failed_routes


def test_2_confidentiality_anonymization(rendered_pages):
    print("\n" + "=" * 80)
    print("TASK 2: ADVERSARIAL SCAN FOR LEAKED TAX IDS, CUSTOMER EMAILS & CONTRACTS")
    print("=" * 80)

    findings = []

    # Leaked customer emails pattern
    forbidden_email_domains = ["vinfast.vn", "hoaphat.com.vn", "saigonnewport.com.vn", "dungquat.com.vn"]

    # Known real corporate tax IDs (MST)
    # 0100779774 is Hoa Phat Dung Quat, 0300446975 is Tan Cang Saigon
    # (Note: 0313683499 is Insilos's own legitimate registered company tax ID)
    forbidden_msts = ["0100779774", "0100779774-001", "0300446975"]

    # Known unanonymized corporate partner names in client context
    forbidden_client_names = ["HOAPHAT_SS400_CORP", "TẬP ĐOÀN HÒA PHÁT DUNG QUẤT", "TÂN CẢNG SÀI GÒN"]

    # Scan rendered HTML pages
    print("  • Scanning rendered HTML responses across all live routes...")
    for p in rendered_pages:
        path = p["path"]
        body = p["body"]
        if not body:
            continue

        for dom in forbidden_email_domains:
            if dom in body:
                matches = re.findall(rf"[a-zA-Z0-9_.+-]+@{re.escape(dom)}", body)
                for m in set(matches):
                    findings.append({
                        "source": f"Live Route {path}",
                        "type": "LEAKED_CUSTOMER_EMAIL",
                        "match": m,
                        "severity": "HIGH"
                    })

        for mst in forbidden_msts:
            if mst in body:
                findings.append({
                    "source": f"Live Route {path}",
                    "type": "LEAKED_REAL_TAX_ID (MST)",
                    "match": mst,
                    "severity": "CRITICAL"
                })

        for cname in forbidden_client_names:
            if cname in body:
                findings.append({
                    "source": f"Live Route {path}",
                    "type": "UNANONYMIZED_CORPORATE_CLIENT",
                    "match": cname,
                    "severity": "HIGH"
                })

    # Scan XML views, JS, and Python in enterprise/insilos_website
    print("  • Scanning source code tree in enterprise/insilos_website...")
    extensions = [".xml", ".js", ".py", ".scss"]
    for ext in extensions:
        for fpath in BASE_DIR.rglob(f"*{ext}"):
            if ".git" in str(fpath) or "__pycache__" in str(fpath) or "test_" in fpath.name or "quality_gate" in fpath.name or "adversarial_" in fpath.name:
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            rel_path = fpath.relative_to(BASE_DIR)

            for dom in forbidden_email_domains:
                if dom in content:
                    matches = re.findall(rf"[a-zA-Z0-9_.+-]+@{re.escape(dom)}", content)
                    for m in set(matches):
                        findings.append({
                            "source": f"File {rel_path}",
                            "type": "LEAKED_CUSTOMER_EMAIL",
                            "match": m,
                            "severity": "HIGH"
                        })

            for mst in forbidden_msts:
                if mst in content:
                    findings.append({
                        "source": f"File {rel_path}",
                        "type": "LEAKED_REAL_TAX_ID (MST)",
                        "match": mst,
                        "severity": "CRITICAL"
                    })

            for cname in forbidden_client_names:
                if cname in content:
                    findings.append({
                        "source": f"File {rel_path}",
                        "type": "UNANONYMIZED_CORPORATE_CLIENT",
                        "match": cname,
                        "severity": "HIGH"
                    })

    # Deduplicate findings
    unique_findings = []
    seen = set()
    for f in findings:
        key = (f["source"], f["type"], f["match"])
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    if unique_findings:
        print(f"  ❌ Found {len(unique_findings)} confidentiality / anonymization findings:")
        for idx, f in enumerate(unique_findings, 1):
            print(f"     [{idx}] {f['severity']:<8} | {f['type']:<28} | Match: {f['match']:<24} | Location: {f['source']}")
    else:
        print("  ✅ Zero leaked customer emails, real corporate MSTs, or unanonymized client contracts found!")

    return (len(unique_findings) == 0), unique_findings


def test_3_verify_founder_branding(rendered_pages):
    print("\n" + "=" * 80)
    print("TASK 3: FOUNDER BRANDING VERIFICATION (FOUNDER ZEN PHAM SOLE FOUNDER)")
    print("=" * 80)

    issues = []
    zen_pham_found = False

    # Check /about rendered page
    about_page = next((p for p in rendered_pages if p["path"] == "/about"), None)
    if about_page and about_page["body"]:
        body = about_page["body"]
        if "Founder Zen Pham" in body or "Zen Pham" in body:
            zen_pham_found = True
            print("  ✅ Confirmed 'Founder Zen Pham' is prominently featured on /about leadership section.")
        else:
            issues.append("Founder Zen Pham missing on /about leadership section.")

    # Check views/resources_about_demo.xml
    rad_path = VIEWS_DIR / "resources_about_demo.xml"
    if rad_path.exists():
        rad_content = rad_path.read_text(encoding="utf-8")
        if "Founder Zen Pham" in rad_content:
            print("  ✅ views/resources_about_demo.xml designates 'Founder Zen Pham' as Founder & Chief Architect.")
        else:
            issues.append("views/resources_about_demo.xml missing 'Founder Zen Pham'")

    # Check if any OTHER individual is claimed as founder or CEO
    forbidden_founder_patterns = [
        r"(?:Co-Founder|Co-founder|Đồng sáng lập|Co-CEO|CEO)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"(?:Founder|Nhà sáng lập)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
    ]

    detected_founders = set()
    for p in rendered_pages:
        body = p["body"]
        if not body:
            continue
        for pat in forbidden_founder_patterns:
            matches = re.findall(pat, body)
            for m in matches:
                detected_founders.add(m.strip())

    print(f"  • Detected executive names across platform: {detected_founders}")
    for name in detected_founders:
        if "Zen Pham" not in name and "Insilos" not in name:
            issues.append(f"Unexpected individual named as founder/executive: {name}")

    passed = (zen_pham_found and len(issues) == 0)
    if passed:
        print("  ✅ [TASK 3 PASSED] Founder Zen Pham verified as sole internal founder branding!")
    else:
        print(f"  ❌ [TASK 3 FAILED] Issues: {issues}")

    return passed, issues


def test_4_canonical_og_and_json_ld(rendered_pages):
    print("\n" + "=" * 80)
    print("TASK 4: CANONICAL DOMAIN, OPENGRAPH & JSON-LD SCHEMA SYNTAX VALIDATION")
    print("=" * 80)

    issues = []
    live_issues = []

    # 1. Verify zero references to insilos.ai in website_templates.xml on disk
    print("  • [Test 4.1] Checking website_templates.xml on disk for insilos.ai in canonical & OG tags...")
    wt_path = VIEWS_DIR / "website_templates.xml"
    wt_content = wt_path.read_text(encoding="utf-8")

    # Check canonical xpath replacement
    canonical_xpath = re.search(r'<xpath expr="//link\[@rel=\'canonical\'\]"[^>]*>([\s\S]*?)</xpath>', wt_content)
    if canonical_xpath:
        snippet = canonical_xpath.group(1)
        if "insilos.ai" in snippet:
            issues.append(f"website_templates.xml canonical xpath contains insilos.ai: {snippet.strip()}")
        elif "insilos.com" in snippet:
            print("     ✅ Canonical tag in website_templates.xml points strictly to https://insilos.com")
        else:
            issues.append(f"website_templates.xml canonical missing insilos.com: {snippet.strip()}")
    else:
        issues.append("website_templates.xml missing xpath for //link[@rel='canonical']")

    # Check OG tags in website_templates.xml
    og_block = re.search(r'<meta property="og:url"[^>]*content="([^"]*)"', wt_content)
    if og_block:
        og_url = og_block.group(1)
        if "insilos.ai" in og_url:
            issues.append(f"website_templates.xml og:url contains insilos.ai: {og_url}")
        elif "insilos.com" in og_url:
            print(f"     ✅ og:url in website_templates.xml points strictly to https://insilos.com")

    # Check all <script type="application/ld+json"> in website_templates.xml
    print("  • [Test 4.2] Validating JSON-LD schema syntax inside website_templates.xml...")
    xml_script_blocks = re.findall(r'<script\s+type="application/ld\+json">([\s\S]*?)</script>', wt_content)
    wt_valid_json = 0
    for idx, block in enumerate(xml_script_blocks, 1):
        # Strip QWeb tags for pure JSON syntax validation
        cleaned_json = re.sub(r'<t\s+[^>]*>.*?</t>', 'dummy_val', block)
        cleaned_json = re.sub(r'<t\s+[^>]*/>', 'dummy_val', cleaned_json)
        cleaned_json = re.sub(r'</?t[^>]*>', '', cleaned_json)
        cleaned_json = cleaned_json.strip()
        try:
            parsed = json.loads(cleaned_json)
            wt_valid_json += 1
        except json.JSONDecodeError as je:
            issues.append(f"website_templates.xml JSON-LD block #{idx} invalid syntax: {je}")

    print(f"     ✅ Validated {wt_valid_json}/{len(xml_script_blocks)} JSON-LD blocks in website_templates.xml syntax!")

    # 2. Check live server rendered HTML for canonical and OG domain
    print("  • [Test 4.3] Auditing live server rendered canonical & OG tags...")
    for p in rendered_pages:
        path = p["path"]
        body = p["body"]
        if not body:
            continue

        canonicals = re.findall(r'<link\s+rel="canonical"\s+href="([^"]*)"', body)
        for c in canonicals:
            if "insilos.ai" in c:
                live_issues.append(f"Live Route {path} renders legacy canonical to insilos.ai: {c} (pending module upgrade)")

        og_urls = re.findall(r'<meta\s+property="og:url"\s+content="([^"]*)"', body)
        for u in og_urls:
            if "insilos.ai" in u:
                live_issues.append(f"Live Route {path} renders legacy og:url to insilos.ai: {u} (pending module upgrade)")

    if live_issues:
        print(f"     ⚠️  Live server rendered {len(live_issues)} references to insilos.ai (Module upgrade pending on odoo20_dev DB).")
    else:
        print("     ✅ Live server rendered zero references to insilos.ai in canonical & OG tags!")

    # 3. Extract and validate all live rendered JSON-LD schemas
    print("  • [Test 4.4] Parsing rendered JSON-LD schemas across all live routes...")
    live_total_schemas = 0
    live_valid_schemas = 0
    schema_types_found = set()

    for p in rendered_pages:
        path = p["path"]
        body = p["body"]
        if not body:
            continue

        script_blocks = re.findall(r'<script\s+type="application/ld\+json">([\s\S]*?)</script>', body)
        for block in script_blocks:
            live_total_schemas += 1
            cleaned = block.strip()
            try:
                data = json.loads(cleaned)
                live_valid_schemas += 1

                ctx = data.get("@context")
                if not ctx or "schema.org" not in ctx:
                    issues.append(f"Route {path} JSON-LD missing valid @context: {ctx}")

                if "@type" in data:
                    schema_types_found.add(data["@type"])
                elif "@graph" in data:
                    for item in data["@graph"]:
                        if "@type" in item:
                            schema_types_found.add(item["@type"])

            except json.JSONDecodeError as e:
                issues.append(f"Route {path} JSON-LD parsing error: {e}")

    print(f"     Rendered JSON-LD parsed: {live_valid_schemas}/{live_total_schemas} valid")
    print(f"     Schema types verified: {sorted(list(schema_types_found))}")

    passed = (len(issues) == 0)
    if passed:
        print("  ✅ [TASK 4 PASSED] website_templates.xml verified with zero insilos.ai canonicals and valid JSON-LD!")
    else:
        print(f"  ❌ [TASK 4 FAILED] Issues: {issues}")

    return passed, issues, live_issues


def test_5_demo_request_post_funnel():
    print("\n" + "=" * 80)
    print("TASK 5: ADVERSARIAL DEMO REQUEST POST SUBMISSION & FUNNEL TESTS")
    print("=" * 80)

    sub_results = []

    def make_fresh_opener():
        cj = http.cookiejar.CookieJar()
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NoRedirectHandler)

    # Test 5.1: Valid submission with HTTP 303 Redirect to /thank-you
    print("  • [Test 5.1] Submitting valid demo request payload (Fresh session)...")
    opener1 = make_fresh_opener()
    with opener1.open(urllib.request.Request(f"{BASE_URL}/request-demo")) as resp:
        b1 = resp.read().decode("utf-8")
        m1 = re.search(r'name="csrf_token"\s+value="([^"]+)"', b1)
        csrf1 = m1.group(1) if m1 else ""

    valid_payload = {
        "csrf_token": csrf1,
        "name": "Audit Director Zen Pham",
        "email": "audit.valid@insilos-demo.vn",
        "phone": "+84944311811",
        "company": "Tập Đoàn Công Nghiệp Nặng V-Corp",
        "job_title": "Giám Đốc Vận Hành",
        "industry": "logistics",
        "use_case": "vertical_idp",
        "company_size": "1000_plus",
        "core_erp": "sap_s4",
        "project_timeline": "1_3_mo",
        "message": "Thử nghiệm kiểm toán tự động hoá bóc tách chứng từ.",
        "consent_decree13": "on",
        "consent": "on",
        "website_url": "",
    }

    p1_code = None
    p1_loc = ""
    try:
        r1 = opener1.open(urllib.request.Request(
            f"{BASE_URL}/request-demo",
            data=urllib.parse.urlencode(valid_payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        ))
        p1_code = r1.status
        p1_loc = r1.headers.get("Location") or ""
    except urllib.error.HTTPError as e:
        p1_code = e.code
        p1_loc = e.headers.get("Location") or ""

    is_redirect = (p1_code == 303 and "/thank-you" in p1_loc)
    print(f"     Valid Submission Response: HTTP {p1_code} -> Location: {p1_loc} | Redirect OK: {is_redirect}")
    sub_results.append(("Valid Submission HTTP 303 Redirect", is_redirect))

    # Follow redirect to /thank-you
    ty_code, ty_body, _ = fetch_route("/thank-you")
    has_ty_content = (ty_code == 200 and ("Cảm ơn bạn đã đăng ký" in ty_body or "Xác Nhận" in ty_body or "thank-you" in ty_body.lower()))
    print(f"     Landing /thank-you: HTTP {ty_code} | Has confirmation content: {has_ty_content}")
    sub_results.append(("Follow Redirect to /thank-you (HTTP 200)", has_ty_content))

    # Test 5.2: Bot Honeypot Trap (website_url filled)
    print("  • [Test 5.2] Submitting Bot Honeypot payload (website_url filled)...")
    opener2 = make_fresh_opener()
    with opener2.open(urllib.request.Request(f"{BASE_URL}/request-demo")) as resp:
        b2 = resp.read().decode("utf-8")
        m2 = re.search(r'name="csrf_token"\s+value="([^"]+)"', b2)
        csrf2 = m2.group(1) if m2 else ""

    hp_payload = dict(valid_payload)
    hp_payload["csrf_token"] = csrf2
    hp_payload["email"] = "bot@spammer.org"
    hp_payload["website_url"] = "http://spam-link.org"

    hp_code = None
    hp_loc = ""
    try:
        r2 = opener2.open(urllib.request.Request(
            f"{BASE_URL}/request-demo",
            data=urllib.parse.urlencode(hp_payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        ))
        hp_code = r2.status
        hp_loc = r2.headers.get("Location") or ""
    except urllib.error.HTTPError as e:
        hp_code = e.code
        hp_loc = e.headers.get("Location") or ""

    hp_ok = (hp_code == 303 and "/thank-you" in hp_loc)
    print(f"     Honeypot Trap Response: HTTP {hp_code} -> Location: {hp_loc} | Trap Silent OK: {hp_ok}")
    sub_results.append(("Bot Honeypot Trap Redirect", hp_ok))

    # Test 5.3: Missing Decree 13 Consent Validation
    print("  • [Test 5.3] Testing Missing Decree 13 Consent Rejection...")
    opener3 = make_fresh_opener()
    with opener3.open(urllib.request.Request(f"{BASE_URL}/request-demo")) as resp:
        b3 = resp.read().decode("utf-8")
        m3 = re.search(r'name="csrf_token"\s+value="([^"]+)"', b3)
        csrf3 = m3.group(1) if m3 else ""

    no_consent_payload = dict(valid_payload)
    no_consent_payload["csrf_token"] = csrf3
    no_consent_payload["email"] = "noconsent@example.com"
    no_consent_payload.pop("consent_decree13", None)
    no_consent_payload.pop("consent", None)

    nc_code = None
    nc_body = ""
    try:
        r3 = opener3.open(urllib.request.Request(
            f"{BASE_URL}/request-demo",
            data=urllib.parse.urlencode(no_consent_payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        ))
        nc_code = r3.status
        nc_body = r3.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        nc_code = e.code
        nc_body = e.read().decode("utf-8") if e.fp else ""

    nc_ok = (nc_code == 200 and ("Nghị định 13/2023/NĐ-CP" in nc_body or "đồng ý" in nc_body))
    print(f"     Missing Consent Response: HTTP {nc_code} | Form validation returned: {nc_ok}")
    sub_results.append(("Missing Consent Rejection", nc_ok))

    # Test 5.4: Adversarial XSS & SQLi Resilience
    print("  • [Test 5.4] Testing Adversarial XSS & SQLi Payload Resilience...")
    opener4 = make_fresh_opener()
    with opener4.open(urllib.request.Request(f"{BASE_URL}/request-demo")) as resp:
        b4 = resp.read().decode("utf-8")
        m4 = re.search(r'name="csrf_token"\s+value="([^"]+)"', b4)
        csrf4 = m4.group(1) if m4 else ""

    sqli_payload = dict(valid_payload)
    sqli_payload["csrf_token"] = csrf4
    sqli_payload["name"] = "<script>alert('XSS')</script>Robert'); DROP TABLE res_partner;--"
    sqli_payload["company"] = "' UNION SELECT 1,2,3,4,5,6,7,8,9,10-- "
    sqli_payload["email"] = "adversarial.qa@example.com"
    sqli_payload["message"] = "<h1>Adversarial Test</h1><img src=x onerror=alert(1)>"

    sqli_code = None
    sqli_loc = ""
    try:
        r4 = opener4.open(urllib.request.Request(
            f"{BASE_URL}/request-demo",
            data=urllib.parse.urlencode(sqli_payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        ))
        sqli_code = r4.status
        sqli_loc = r4.headers.get("Location") or ""
    except urllib.error.HTTPError as e:
        sqli_code = e.code
        sqli_loc = e.headers.get("Location") or ""

    sqli_safe = (sqli_code in [200, 303] and sqli_code != 500)
    print(f"     XSS/SQLi Submission: HTTP {sqli_code} -> Location: {sqli_loc} | Safe Handling (No 500): {sqli_safe}")
    sub_results.append(("XSS/SQLi Server Crash Resilience", sqli_safe))

    all_passed = all(status for name, status in sub_results)
    print("\nTask 5 Sub-results:")
    for name, status in sub_results:
        print(f"  • {name:<45}: {'✅ PASSED' if status else '❌ FAILED'}")

    return all_passed, sub_results


def main():
    print("=" * 80)
    print("INSILOS ADVERSARIAL CHALLENGER 2: ROUTE INTEGRITY & DATA CONFIDENTIALITY")
    print(f"Target Server: {BASE_URL}")
    print("=" * 80)

    # Task 1: Probe routes
    t1_pass, rendered_pages, failed_routes = test_1_probe_all_routes()

    # Task 2: Data Confidentiality & Anonymization
    t2_pass, findings_2 = test_2_confidentiality_anonymization(rendered_pages)

    # Task 3: Founder Branding Verification
    t3_pass, issues_3 = test_3_verify_founder_branding(rendered_pages)

    # Task 4: Canonical, OG & JSON-LD
    t4_pass, issues_4, live_issues_4 = test_4_canonical_og_and_json_ld(rendered_pages)

    # Task 5: Demo Request POST Funnel
    t5_pass, sub_5 = test_5_demo_request_post_funnel()

    print("\n" + "=" * 80)
    print("ADVERSARIAL CHALLENGER 2 EXECUTIVE SUMMARY TABLE")
    print("=" * 80)
    print(f"1. Live Route Penetration (35+ Routes)        : {'✅ PASS' if t1_pass else '❌ FAIL'}")
    print(f"2. Data Confidentiality & Client Anonymization : {'✅ PASS' if t2_pass else '❌ FAIL'}")
    print(f"3. Founder Zen Pham Sole Branding              : {'✅ PASS' if t3_pass else '❌ FAIL'}")
    print(f"4. Canonical Domain & JSON-LD Schemas          : {'✅ PASS' if t4_pass else '❌ FAIL'}")
    print(f"5. Demo Request POST Funnel & Redirection      : {'✅ PASS' if t5_pass else '❌ FAIL'}")
    print("=" * 80)

    # Notice: Task 2 has concrete findings of leaked real tax IDs and emails.
    overall_pass = t1_pass and t2_pass and t3_pass and t4_pass and t5_pass
    verdict = "APPROVE" if overall_pass else "REJECT"
    print(f"\nFinal Adversarial Verdict: {verdict}")

    report_data = {
        "verdict": verdict,
        "overall_pass": overall_pass,
        "task_1_routes": {"passed": t1_pass, "total_probed": len(ROUTES_TO_PROBE), "failed_routes": failed_routes},
        "task_2_confidentiality": {"passed": t2_pass, "findings": findings_2},
        "task_3_founder": {"passed": t3_pass, "issues": issues_3},
        "task_4_canonical_json_ld": {"passed": t4_pass, "issues_disk": issues_4, "live_issues_db_upgrade_pending": live_issues_4},
        "task_5_demo_post": {"passed": t5_pass, "sub_results": sub_5},
    }

    report_out = Path("/home/zen/O20/.agents/teamwork/teamwork_preview_challenger_sec_2/adversarial_challenge_report.json")
    report_out.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Detailed JSON report saved to: {report_out}")

    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
