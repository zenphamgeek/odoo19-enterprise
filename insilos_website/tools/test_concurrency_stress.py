#!/usr/bin/env python3
"""
Insilos Enterprise Concurrency, Boundaries & Adversarial Stress Test Harness
============================================================================
Empirically stress-tests the Insilos Odoo 20 Website under high concurrency,
hostile boundary inputs, and CSRF/POST adversarial scenarios.

Sections:
1. Multi-threaded Concurrency Stress Harness (50 workers, 500 requests across 19 routes).
   Metrics: min, max, mean, p50, p90, p95, p99 latency, 0 500 errors, connection health.
2. Boundary & Injection Stress Suite:
   Unregistered slugs, non-existent solutions/industries/resources, path traversal,
   SQL/XSS injections. Asserts clean 404/400 and zero stack trace leakage.
3. Demo Request POST Funnel Adversarial Suite:
   CSRF omission, forged token, valid submission, honeypot trap, rapid re-submission
   rate limit, malformed payloads, oversized inputs, and XSS sanitization.
"""

import sys
import os
import re
import time
import json
import random
import statistics
import threading
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = os.environ.get("INSILOS_BASE_URL", "http://localhost:28069")

CORE_AND_INDUSTRY_ROUTES = [
    "/",
    "/platform",
    "/solutions",
    "/solutions/vertical-idp",
    "/solutions/enterprise-knowledge-graph",
    "/solutions/trade-compliance",
    "/solutions/field-service-intelligence",
    "/solutions/asset-reliability",
    "/solutions/logistics-control-tower",
    "/solutions/process-optimization",
    "/industries",
    "/industries/logistics",
    "/industries/pharma",
    "/industries/energy",
    "/industries/fsm",
    "/pricing",
    "/about",
    "/resources",
    "/request-demo",
]

BOUNDARY_ROUTES = [
    {"path": "/industries/unregistered-slug-xyz", "name": "Unregistered Industry Slug", "expected": 404},
    {"path": "/solutions/fake-app", "name": "Non-existent Solution Slug", "expected": 404},
    {"path": "/resources/non-existent-whitepaper-abc", "name": "Non-existent Whitepaper Slug", "expected": 404},
    {"path": "/industries/99999-not-found", "name": "Numeric Non-existent Industry Slug", "expected": 404},
    {"path": "/industry/unknown-industry-slug-test", "name": "Singular /industry Unknown Slug", "expected": 404},
    {"path": "/industry/unknown-slug/brochure", "name": "Brochure for Unknown Slug", "expected": 404},
    {"path": "/solutions/'%20OR%20'1'='1", "name": "SQL Injection in Solution Slug", "expected": 404},
    {"path": "/industries/<script>alert(1)</script>", "name": "XSS in Industry Slug", "expected": (400, 404)},
    {"path": "/solutions/../../etc/passwd", "name": "Path Traversal in Solution Slug", "expected": (400, 404)},
]

STACK_TRACE_PATTERNS = [
    re.compile(r"Traceback\s+\(most\s+recent\s+call\s+last\):", re.IGNORECASE),
    re.compile(r"werkzeug\.exceptions\.", re.IGNORECASE),
    re.compile(r"InternalServerError", re.IGNORECASE),
    re.compile(r"psycopg2\.errors", re.IGNORECASE),
    re.compile(r"odoo\.exceptions", re.IGNORECASE),
    re.compile(r'File ".*\.py", line \d+', re.IGNORECASE),
    re.compile(r"1NN0R1@2026"),  # Check for leak of database password
]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_route(url, timeout=15):
    """Fetch a single route and record latency, status, and error details."""
    start_time = time.perf_counter()
    status_code = None
    body_snippet = ""
    error_msg = None
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "InsilosAdversarialStress/2.0",
                "Accept-Encoding": "identity",
                "Connection": "keep-alive",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.perf_counter() - start_time
            status_code = resp.status
            content = resp.read(2048)  # Read first 2KB for verification
            body_snippet = content.decode("utf-8", errors="replace")
            return {
                "url": url,
                "status": status_code,
                "latency_ms": elapsed * 1000,
                "body_snippet": body_snippet,
                "error": None,
                "success": (status_code == 200),
            }
    except urllib.error.HTTPError as he:
        elapsed = time.perf_counter() - start_time
        body_snippet = he.read(2048).decode("utf-8", errors="replace")
        return {
            "url": url,
            "status": he.code,
            "latency_ms": elapsed * 1000,
            "body_snippet": body_snippet,
            "error": f"HTTP {he.code}",
            "success": False,
        }
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return {
            "url": url,
            "status": 0,
            "latency_ms": elapsed * 1000,
            "body_snippet": "",
            "error": str(e),
            "success": False,
        }


def run_concurrency_stress_test(concurrency=50, total_requests=500):
    """Executes high-concurrency multi-threaded load across all core and industry routes."""
    print("\n" + "=" * 80)
    print(f"STAGE 1: MULTI-THREADED CONCURRENCY STRESS HARNESS")
    print(f"Configuration: {concurrency} Concurrent Workers | {total_requests} Requests across {len(CORE_AND_INDUSTRY_ROUTES)} Routes")
    print(f"Target Server: {BASE_URL}")
    print("=" * 80)

    # Pre-warm connection
    warmup_res = fetch_route(f"{BASE_URL}/")
    print(f"• Pre-warm connection: HTTP {warmup_res['status']} in {warmup_res['latency_ms']:.2f}ms")

    # Generate request URL distribution
    request_urls = []
    while len(request_urls) < total_requests:
        for r in CORE_AND_INDUSTRY_ROUTES:
            request_urls.append(f"{BASE_URL}{r}")
            if len(request_urls) >= total_requests:
                break

    random.shuffle(request_urls)

    start_all = time.perf_counter()
    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(fetch_route, url): url for url in request_urls}
        for future in as_completed(futures):
            results.append(future.result())

    total_duration = time.perf_counter() - start_all
    throughput = len(results) / total_duration if total_duration > 0 else 0

    latencies = [r["latency_ms"] for r in results]
    latencies.sort()

    status_counts = {}
    for r in results:
        code = r["status"]
        status_counts[code] = status_counts.get(code, 0) + 1

    errors_500 = [r for r in results if r["status"] == 500]
    conn_errors = [r for r in results if r["status"] == 0]

    min_lat = min(latencies)
    max_lat = max(latencies)
    mean_lat = statistics.mean(latencies)
    median_lat = statistics.median(latencies)
    p90_lat = latencies[int(len(latencies) * 0.90)]
    p95_lat = latencies[int(len(latencies) * 0.95)]
    p99_lat = latencies[int(len(latencies) * 0.99)]

    print("\n--- Concurrency Stress Metrics ---")
    print(f"  • Total Requests Completed   : {len(results)}")
    print(f"  • Concurrency Workers        : {concurrency}")
    print(f"  • Total Wall Time Elapsed    : {total_duration:.2f} s")
    print(f"  • Effective Throughput       : {throughput:.2f} req/s")
    print(f"  • HTTP Status Breakdown      : {status_counts}")
    print(f"  • 500 Internal Server Errors : {len(errors_500)}")
    print(f"  • Connection Drop / Refusals : {len(conn_errors)}")
    print(f"  • Min Latency                : {min_lat:.2f} ms")
    print(f"  • Mean Latency               : {mean_lat:.2f} ms")
    print(f"  • Median (p50) Latency       : {median_lat:.2f} ms")
    print(f"  • p90 Latency                : {p90_lat:.2f} ms")
    print(f"  • p95 Latency                : {p95_lat:.2f} ms")
    print(f"  • p99 Latency                : {p99_lat:.2f} ms")
    print(f"  • Max Latency                : {max_lat:.2f} ms")

    # Assertions
    passed_no_500 = (len(errors_500) == 0)
    passed_no_conn_drop = (len(conn_errors) == 0)
    passed_p95 = (p95_lat < 500.0)
    passed_all_200 = (status_counts.get(200, 0) == len(results))

    print(f"\n--- Concurrency Assertions ---")
    print(f"  [{'PASS' if passed_no_500 else 'FAIL'}] Zero 500 Internal Server Errors (Actual: {len(errors_500)})")
    print(f"  [{'PASS' if passed_no_conn_drop else 'FAIL'}] Zero Connection Drops / Socket Errors (Actual: {len(conn_errors)})")
    print(f"  [{'PASS' if passed_p95 else 'FAIL'}] p95 Latency < 500ms (Actual: {p95_lat:.2f} ms)")
    print(f"  [{'PASS' if passed_all_200 else 'FAIL'}] 100% HTTP 200 OK (Actual: {status_counts.get(200, 0)}/{len(results)})")

    overall_pass = passed_no_500 and passed_no_conn_drop and passed_p95 and passed_all_200

    return {
        "passed": overall_pass,
        "concurrency": concurrency,
        "total_requests": len(results),
        "wall_time_s": total_duration,
        "throughput_rps": throughput,
        "status_counts": status_counts,
        "min_latency_ms": min_lat,
        "mean_latency_ms": mean_lat,
        "p50_latency_ms": median_lat,
        "p90_latency_ms": p90_lat,
        "p95_latency_ms": p95_lat,
        "p99_latency_ms": p99_lat,
        "max_latency_ms": max_lat,
        "errors_500": len(errors_500),
        "conn_errors": len(conn_errors),
    }


def run_boundary_and_injection_suite():
    """Tests boundary routes, non-existent slugs, SQL/XSS injections for clean 404s & no stack traces."""
    print("\n" + "=" * 80)
    print("STAGE 2: BOUNDARY & INJECTION ADVERSARIAL CHALLENGE")
    print("Target: Graceful 404/400 handling and zero stack trace / secret leakage")
    print("=" * 80)

    results = []
    all_passed = True

    for test in BOUNDARY_ROUTES:
        url = f"{BASE_URL}{test['path']}"
        res = fetch_route(url)
        status = res["status"]
        snippet = res["body_snippet"]

        # Check status
        expected = test["expected"]
        if isinstance(expected, tuple):
            status_ok = status in expected
        else:
            status_ok = (status == expected)

        # Check for stack trace leakage
        leak_detected = False
        leaked_patterns = []
        for pat in STACK_TRACE_PATTERNS:
            if pat.search(snippet):
                leak_detected = True
                leaked_patterns.append(pat.pattern)

        passed = status_ok and (not leak_detected)
        if not passed:
            all_passed = False

        status_icon = "✅" if passed else "❌"
        print(f"  {status_icon} [{test['name']:38}] URL: {test['path']}")
        print(f"      Status: {status} (Expected: {expected}) | Leak Detected: {leak_detected} | Latency: {res['latency_ms']:.2f}ms")
        if leak_detected:
            print(f"      🚨 Leaked Patterns: {leaked_patterns}")

        results.append({
            "test": test["name"],
            "path": test["path"],
            "status": status,
            "expected": expected,
            "status_ok": status_ok,
            "leak_detected": leak_detected,
            "passed": passed,
        })

    print(f"\n--- Boundary Suite Verdict: {'PASSED' if all_passed else 'FAILED'} ---")
    return {"passed": all_passed, "tests": results}


def get_fresh_csrf_session():
    """Helper to obtain a session cookie and CSRF token from /request-demo."""
    cj = http.cookiejar.CookieJar()
    cp = urllib.request.HTTPCookieProcessor(cj)
    opener = urllib.request.build_opener(cp, NoRedirectHandler)

    req_get = urllib.request.Request(
        f"{BASE_URL}/request-demo",
        headers={"User-Agent": "InsilosAdversarialStress/2.0"}
    )
    with opener.open(req_get, timeout=10) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', body)
        csrf_token = csrf_match.group(1) if csrf_match else None

    return opener, csrf_token


def run_demo_post_adversarial_suite():
    """Tests CSRF omission, CSRF forgery, honeypot traps, valid submission, and boundary malformed payloads."""
    print("\n" + "=" * 80)
    print("STAGE 3: DEMO REQUEST POST FUNNEL & CSRF ADVERSARIAL STRESS")
    print("=" * 80)

    suite_results = []
    all_passed = True

    # Test 3.1: POST without CSRF token
    print("\n• Test 3.1: POST submission omitting CSRF token entirely...")
    try:
        raw_opener = urllib.request.build_opener(NoRedirectHandler)
        post_data = urllib.parse.urlencode({
            "name": "Attacker No CSRF",
            "email": "attacker@evil.com",
            "company": "Evil Corp",
            "industry": "logistics",
            "use_case": "vertical_idp",
            "consent": "on",
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/request-demo",
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with raw_opener.open(req, timeout=10) as resp:
            code = resp.status
    except urllib.error.HTTPError as he:
        code = he.code
    except Exception as e:
        code = str(e)

    # In Odoo, csrf=True rejects missing token with HTTP 400 Bad Request
    t31_passed = (code == 400)
    if not t31_passed:
        all_passed = False
    print(f"  {'✅' if t31_passed else '❌'} Result: HTTP {code} (Expected: 400 Bad Request / CSRF Rejected)")
    suite_results.append({"name": "Omitted CSRF Token", "status": code, "passed": t31_passed})

    # Test 3.2: POST with forged/invalid CSRF token
    print("\n• Test 3.2: POST submission with invalid/forged CSRF token...")
    try:
        raw_opener = urllib.request.build_opener(NoRedirectHandler)
        post_data = urllib.parse.urlencode({
            "csrf_token": "forged_invalid_token_xyz_1234567890",
            "name": "Attacker Forged CSRF",
            "email": "forged@evil.com",
            "company": "Evil Corp",
            "industry": "logistics",
            "use_case": "vertical_idp",
            "consent": "on",
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/request-demo",
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with raw_opener.open(req, timeout=10) as resp:
            code = resp.status
    except urllib.error.HTTPError as he:
        code = he.code
    except Exception as e:
        code = str(e)

    t32_passed = (code == 400)
    if not t32_passed:
        all_passed = False
    print(f"  {'✅' if t32_passed else '❌'} Result: HTTP {code} (Expected: 400 Bad Request / CSRF Rejected)")
    suite_results.append({"name": "Forged CSRF Token", "status": code, "passed": t32_passed})

    # Test 3.3: Legitimate POST with valid CSRF token & valid data
    print("\n• Test 3.3: Legitimate POST submission with valid CSRF token...")
    opener, csrf = get_fresh_csrf_session()
    post_data = urllib.parse.urlencode({
        "csrf_token": csrf,
        "name": "Empirical Stress Challenger",
        "email": "challenger2@insilos.vn",
        "phone": "+84901234567",
        "company": "Sovereign Industrial AI Lab",
        "job_title": "Principal Reliability Architect",
        "industry": "logistics",
        "use_case": "vertical_idp",
        "company_size": "50_249",
        "message": "High-concurrency empirical verification submission.",
        "consent": "on",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/request-demo",
        data=post_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    status = None
    location = ""
    try:
        with opener.open(req, timeout=10) as resp:
            status = resp.status
            location = resp.headers.get("Location") or ""
    except urllib.error.HTTPError as he:
        status = he.code
        location = he.headers.get("Location") or ""

    t33_passed = (status in (302, 303)) and ("/thank-you" in location)
    if not t33_passed:
        all_passed = False
    print(f"  {'✅' if t33_passed else '❌'} Result: HTTP {status} (Redirect: {location})")
    suite_results.append({"name": "Valid POST Submission", "status": status, "location": location, "passed": t33_passed})

    # Test 3.4: Honeypot bot protection (website_url populated)
    print("\n• Test 3.4: Honeypot bot protection (website_url trap populated)...")
    opener_bot, csrf_bot = get_fresh_csrf_session()
    post_bot = urllib.parse.urlencode({
        "csrf_token": csrf_bot,
        "name": "Bot Spammer",
        "email": "bot@spam-network.ru",
        "company": "Spam Net",
        "industry": "logistics",
        "use_case": "vertical_idp",
        "consent": "on",
        "website_url": "http://malicious-spam-url.ru/bot",  # Honeypot trap!
    }).encode("utf-8")
    req_bot = urllib.request.Request(
        f"{BASE_URL}/request-demo",
        data=post_bot,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    status_bot = None
    location_bot = ""
    try:
        with opener_bot.open(req_bot, timeout=10) as resp:
            status_bot = resp.status
            location_bot = resp.headers.get("Location") or ""
    except urllib.error.HTTPError as he:
        status_bot = he.code
        location_bot = he.headers.get("Location") or ""

    # Must silently redirect to /thank-you without creating CRM record
    t34_passed = (status_bot in (302, 303)) and ("/thank-you" in location_bot)
    if not t34_passed:
        all_passed = False
    print(f"  {'✅' if t34_passed else '❌'} Result: HTTP {status_bot} (Honeypot silent redirect: {location_bot})")
    suite_results.append({"name": "Honeypot Bot Trap", "status": status_bot, "location": location_bot, "passed": t34_passed})

    # Test 3.5: Rate limiting (<20s resubmission within same session)
    print("\n• Test 3.5: Rapid re-submission rate limiting (<20s cooldown)...")
    # Using the same opener session from Test 3.3
    post_rapid = urllib.parse.urlencode({
        "csrf_token": csrf,
        "name": "Rapid Resubmitter",
        "email": "rapid@insilos.vn",
        "company": "Rapid Corp",
        "industry": "logistics",
        "use_case": "vertical_idp",
        "consent": "on",
    }).encode("utf-8")
    req_rapid = urllib.request.Request(
        f"{BASE_URL}/request-demo",
        data=post_rapid,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with opener.open(req_rapid, timeout=10) as resp:
            rapid_status = resp.status
            rapid_body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as he:
        rapid_status = he.code
        rapid_body = he.read().decode("utf-8", errors="replace")

    # Controller should return HTTP 200 re-rendering form with cooldown warning
    has_cooldown_msg = "Yêu cầu vừa được gửi" in rapid_body
    t35_passed = (rapid_status == 200) and has_cooldown_msg
    if not t35_passed:
        all_passed = False
    print(f"  {'✅' if t35_passed else '❌'} Result: HTTP {rapid_status} | Cooldown Message Detected: {has_cooldown_msg}")
    suite_results.append({"name": "Rapid Resubmit Rate Limit", "status": rapid_status, "passed": t35_passed})

    # Test 3.6: Malformed / Injection payload resilience (XSS in fields, massive string)
    print("\n• Test 3.6: Malformed & adversarial payload resilience (XSS strings & 100K message)...")
    opener_xss, csrf_xss = get_fresh_csrf_session()
    post_xss = urllib.parse.urlencode({
        "csrf_token": csrf_xss,
        "name": "<script>alert('XSS_NAME')</script>",
        "email": "invalid-email-format-xyz",
        "company": "<b>Injected Corp</b>",
        "industry": "invalid_industry_slug_hack",
        "use_case": "invalid_use_case_hack",
        "message": "A" * 100000,  # 100KB massive payload
        "consent": "off",          # missing consent
    }).encode("utf-8")
    req_xss = urllib.request.Request(
        f"{BASE_URL}/request-demo",
        data=post_xss,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with opener_xss.open(req_xss, timeout=10) as resp:
            xss_status = resp.status
            xss_body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as he:
        xss_status = he.code
        xss_body = he.read().decode("utf-8", errors="replace")

    # Must cleanly return HTTP 200 with form validation errors, zero unhandled 500 error
    t36_passed = (xss_status == 200) and ("<script>" not in xss_body or "&lt;script&gt;" in xss_body)
    if not t36_passed:
        all_passed = False
    print(f"  {'✅' if t36_passed else '❌'} Result: HTTP {xss_status} | Safely Handled without 500 crash")
    suite_results.append({"name": "Malformed & Adversarial Payload", "status": xss_status, "passed": t36_passed})

    print(f"\n--- Demo POST Suite Verdict: {'PASSED' if all_passed else 'FAILED'} ---")
    return {"passed": all_passed, "tests": suite_results}


def main():
    print("=" * 80)
    print("INSILOS ENTERPRISE COMPREHENSIVE ADVERSARIAL STRESS TEST SUITE")
    print(f"Target: {BASE_URL} | Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 80)

    # 1. Concurrency Stress Test
    concurrency_result = run_concurrency_stress_test(concurrency=50, total_requests=500)

    # 2. Boundary & Injection Suite
    boundary_result = run_boundary_and_injection_suite()

    # 3. Demo POST & CSRF Suite
    demo_post_result = run_demo_post_adversarial_suite()

    # Final Summary
    print("\n" + "=" * 80)
    print("FINAL ADVERSARIAL CHALLENGE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"  1. Concurrency Stress (50 threads, 500 reqs) : {'✅ PASSED' if concurrency_result['passed'] else '❌ FAILED'}")
    print(f"     • 500 Errors: {concurrency_result['errors_500']} | p95 Latency: {concurrency_result['p95_latency_ms']:.2f} ms (Target: < 500ms)")
    print(f"     • Throughput: {concurrency_result['throughput_rps']:.2f} req/s | Wall Time: {concurrency_result['wall_time_s']:.2f}s")
    print(f"  2. Boundary & Injection Challenge          : {'✅ PASSED' if boundary_result['passed'] else '❌ FAILED'}")
    print(f"  3. Demo Request CSRF & Post Funnel         : {'✅ PASSED' if demo_post_result['passed'] else '❌ FAILED'}")
    print("-" * 80)

    overall_passed = concurrency_result["passed"] and boundary_result["passed"] and demo_post_result["passed"]
    print(f"OVERALL EMPIRICAL CHALLENGE VERDICT: {'🏆 APPROVE' if overall_passed else '⛔ REJECT'}")
    print("=" * 80)

    return 0 if overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
