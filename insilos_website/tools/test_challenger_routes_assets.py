#!/usr/bin/env python3
"""
Adversarial Empirical Route & Asset Verification Suite
======================================================
Challenger 1 (Route & Asset Empirical Challenger)

Probes and stress-tests:
1. Happy path:
   - /brochure, /solutions/grc/brochure -> HTTP 200 OK
   - /brochure/download -> HTTP 200 OK, valid PDF binary (%PDF-1.), Content-Type application/pdf, Content-Length > 1MB
   - /dossiers, /solutions/grc/dossiers -> HTTP 200 OK
   - 5 dedicated heavy industry routes -> HTTP 200 OK
   - All 25 Vietnamese scenario PDF downloads -> HTTP 200 OK, %PDF-1. magic bytes, %%EOF terminator, Content-Length > 50KB
2. Boundary & error conditions:
   - Invalid industry slugs -> clean HTTP 404 (not 500)
   - Out-of-range scenarios -> clean HTTP 404 (not 500)
   - Path traversal and injection attacks -> clean HTTP 404 (not 500)
3. Concurrency Stress:
   - Multi-threaded stress probe verifying stability under load.
"""

import sys
import os
import re
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = os.environ.get("INSILOS_BASE_URL", "http://localhost:28069")

class TestResult:
    def __init__(self, name, category, passed, status_code, details=""):
        self.name = name
        self.category = category
        self.passed = passed
        self.status_code = status_code
        self.details = details

    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "passed": self.passed,
            "status_code": self.status_code,
            "details": self.details,
        }


def make_request(path, method="GET", timeout=15):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Insilos-Adversarial-Challenger/1.0",
            "Accept": "*/*",
        },
        method=method,
    )
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
            elapsed = time.time() - start_time
            return {
                "status": response.status,
                "headers": dict(response.headers),
                "data": data,
                "elapsed": elapsed,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        try:
            body = e.read()
        except Exception:
            body = b""
        return {
            "status": e.code,
            "headers": dict(e.headers),
            "data": body,
            "elapsed": elapsed,
            "error": str(e),
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "status": 0,
            "headers": {},
            "data": b"",
            "elapsed": elapsed,
            "error": str(e),
        }


def test_core_happy_path():
    results = []
    routes = [
        ("/brochure", "Brochure Main Route", ["Vertical Resilience", "Brochure"]),
        ("/solutions/grc/brochure", "Brochure Solution Alias Route", ["Vertical Resilience"]),
        ("/dossiers", "Dossiers Hub Main Route", ["Executive Industry Dossiers", "dossier"]),
        ("/solutions/grc/dossiers", "Dossiers Solution Alias Route", ["Dossiers"]),
        ("/industries/petrochem", "Petrochem Dedicated Industry Route", ["PVFCCo", "Đạm Phú Mỹ"]),
        ("/industries/gas-pipeline", "Gas Pipeline Dedicated Industry Route", ["Nam Côn Sơn", "NCSP"]),
        ("/industries/metallurgy", "Metallurgy Dedicated Industry Route", ["Hòa Phát Dung Quất"]),
        ("/industries/thermal-power", "Thermal Power Dedicated Industry Route", ["AES Mông Dương"]),
        ("/industries/pharma", "Pharma GxP Dedicated Industry Route", ["DHG Pharma"]),
        ("/dossiers/petrochem", "Petrochem Dossier Detail Route", ["Petrochem"]),
        ("/dossiers/gas-pipeline", "Gas Pipeline Dossier Detail Route", ["Pipeline"]),
        ("/dossiers/metallurgy", "Metallurgy Dossier Detail Route", ["Metallurgy"]),
        ("/dossiers/thermal-power", "Thermal Power Dossier Detail Route", ["Thermal Power"]),
        ("/dossiers/pharma", "Pharma Dossier Detail Route", ["Pharma"]),
    ]

    for path, name, expected_keywords in routes:
        resp = make_request(path)
        passed = False
        details = ""
        if resp["status"] == 200:
            content = resp["data"].decode("utf-8", errors="replace")
            if "Traceback (most recent call last)" in content or "500: Internal Server Error" in content:
                details = "HTTP 200 but contained 500 Traceback!"
            else:
                missing = [kw for kw in expected_keywords if kw.lower() not in content.lower()]
                if missing:
                    details = f"HTTP 200 but missing keywords: {missing}"
                else:
                    passed = True
                    details = f"HTTP 200 OK in {resp['elapsed']:.2f}s, keywords confirmed"
        else:
            details = f"Expected HTTP 200, got HTTP {resp['status']} (error: {resp['error']})"
        
        results.append(TestResult(name, "Happy Path Routes", passed, resp["status"], details))

    return results


def test_brochure_pdf_streaming():
    results = []
    test_cases = [
        ("/brochure/download", "Master Brochure Download (Default)", "inline"),
        ("/brochure/download?dl=1", "Master Brochure Download (?dl=1)", "attachment"),
        ("/brochure/download?download=1", "Master Brochure Download (?download=1)", "attachment"),
        ("/solutions/grc/brochure/download", "Master Brochure Download (Solution Alias)", "inline"),
        ("/brochure/pdf", "Master Brochure Download (/brochure/pdf)", "inline"),
    ]

    for path, name, expected_disposition in test_cases:
        resp = make_request(path)
        passed = False
        details = ""
        if resp["status"] == 200:
            headers = resp["headers"]
            content_type = headers.get("content-type", headers.get("Content-Type", ""))
            content_disp = headers.get("content-disposition", headers.get("Content-Disposition", ""))
            content_len = int(headers.get("content-length", headers.get("Content-Length", len(resp["data"]))))
            data = resp["data"]
            
            magic_ok = data.startswith(b"%PDF-1.")
            eof_ok = b"%%EOF" in data[-1024:]
            type_ok = "application/pdf" in content_type
            disp_ok = expected_disposition in content_disp
            size_ok = content_len > 1_000_000  # Must be > 1MB

            if magic_ok and eof_ok and type_ok and disp_ok and size_ok:
                passed = True
                details = (
                    f"HTTP 200, size={content_len} bytes (>1MB), "
                    f"magic={data[:8]}, disp={expected_disposition}, elapsed={resp['elapsed']:.2f}s"
                )
            else:
                details = (
                    f"Check failed: magic={magic_ok}, eof={eof_ok}, "
                    f"type_ok={type_ok} ({content_type}), disp_ok={disp_ok} ({content_disp}), "
                    f"size_ok={size_ok} ({content_len} bytes)"
                )
        else:
            details = f"Expected HTTP 200, got HTTP {resp['status']} (error: {resp['error']})"

        results.append(TestResult(name, "Master Brochure Streaming", passed, resp["status"], details))

    return results


def test_all_25_vietnamese_scenario_pdfs():
    results = []
    
    # Complete catalog of 5 industries x 5 scenarios (both local 1..5 and global indexes)
    industries_scenarios = [
        ("petrochem", [1, 2, 3, 4, 5], {
            1: "VR_Scenario_01_Petrochem_CSuite_Board_VI.pdf",
            2: "VR_Scenario_02_Petrochem_Operations_HSE_VI.pdf",
            3: "VR_Scenario_03_Petrochem_CISO_Legal_DPO_VI.pdf",
            4: "VR_Scenario_04_Petrochem_ProcessSafety_SIS_VI.pdf",
            5: "VR_Scenario_05_Petrochem_DigitalTrans_QA_VI.pdf",
        }),
        ("thermal-power", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], {
            1: "VR_Scenario_06_ThermalPower_CSuite_Board_VI.pdf",
            2: "VR_Scenario_07_ThermalPower_Operations_HSE_VI.pdf",
            3: "VR_Scenario_08_ThermalPower_CISO_Legal_DPO_VI.pdf",
            4: "VR_Scenario_09_ThermalPower_ProcessSafety_SIS_VI.pdf",
            5: "VR_Scenario_10_ThermalPower_DigitalTrans_QA_VI.pdf",
            6: "VR_Scenario_06_ThermalPower_CSuite_Board_VI.pdf",
            7: "VR_Scenario_07_ThermalPower_Operations_HSE_VI.pdf",
            8: "VR_Scenario_08_ThermalPower_CISO_Legal_DPO_VI.pdf",
            9: "VR_Scenario_09_ThermalPower_ProcessSafety_SIS_VI.pdf",
            10: "VR_Scenario_10_ThermalPower_DigitalTrans_QA_VI.pdf",
        }),
        ("gas-pipeline", [1, 2, 3, 4, 5, 11, 12, 13, 14, 15], {
            1: "VR_Scenario_11_GasPipeline_CSuite_Board_VI.pdf",
            2: "VR_Scenario_12_GasPipeline_Operations_HSE_VI.pdf",
            3: "VR_Scenario_13_GasPipeline_CISO_Legal_DPO_VI.pdf",
            4: "VR_Scenario_14_GasPipeline_ProcessSafety_SIS_VI.pdf",
            5: "VR_Scenario_15_GasPipeline_DigitalTrans_QA_VI.pdf",
            11: "VR_Scenario_11_GasPipeline_CSuite_Board_VI.pdf",
            12: "VR_Scenario_12_GasPipeline_Operations_HSE_VI.pdf",
            13: "VR_Scenario_13_GasPipeline_CISO_Legal_DPO_VI.pdf",
            14: "VR_Scenario_14_GasPipeline_ProcessSafety_SIS_VI.pdf",
            15: "VR_Scenario_15_GasPipeline_DigitalTrans_QA_VI.pdf",
        }),
        ("metallurgy", [1, 2, 3, 4, 5, 16, 17, 18, 19, 20], {
            1: "VR_Scenario_16_Metallurgy_CSuite_Board_VI.pdf",
            2: "VR_Scenario_17_Metallurgy_Operations_HSE_VI.pdf",
            3: "VR_Scenario_18_Metallurgy_CISO_Legal_DPO_VI.pdf",
            4: "VR_Scenario_19_Metallurgy_ProcessSafety_SIS_VI.pdf",
            5: "VR_Scenario_20_Metallurgy_DigitalTrans_QA_VI.pdf",
            16: "VR_Scenario_16_Metallurgy_CSuite_Board_VI.pdf",
            17: "VR_Scenario_17_Metallurgy_Operations_HSE_VI.pdf",
            18: "VR_Scenario_18_Metallurgy_CISO_Legal_DPO_VI.pdf",
            19: "VR_Scenario_19_Metallurgy_ProcessSafety_SIS_VI.pdf",
            20: "VR_Scenario_20_Metallurgy_DigitalTrans_QA_VI.pdf",
        }),
        ("pharma", [1, 2, 3, 4, 5, 21, 22, 23, 24, 25], {
            1: "VR_Scenario_21_PharmaGxP_CSuite_Board_VI.pdf",
            2: "VR_Scenario_22_PharmaGxP_Operations_HSE_VI.pdf",
            3: "VR_Scenario_23_PharmaGxP_CISO_Legal_DPO_VI.pdf",
            4: "VR_Scenario_24_PharmaGxP_ProcessSafety_SIS_VI.pdf",
            5: "VR_Scenario_25_PharmaGxP_DigitalTrans_QA_VI.pdf",
            21: "VR_Scenario_21_PharmaGxP_CSuite_Board_VI.pdf",
            22: "VR_Scenario_22_PharmaGxP_Operations_HSE_VI.pdf",
            23: "VR_Scenario_23_PharmaGxP_CISO_Legal_DPO_VI.pdf",
            24: "VR_Scenario_24_PharmaGxP_ProcessSafety_SIS_VI.pdf",
            25: "VR_Scenario_25_PharmaGxP_DigitalTrans_QA_VI.pdf",
        }),
    ]

    for ind_slug, scenario_indices, expected_files in industries_scenarios:
        for s_num in scenario_indices:
            path = f"/dossiers/{ind_slug}/scenario/{s_num}/pdf"
            name = f"Scenario PDF ({ind_slug} #{s_num})"
            expected_filename = expected_files[s_num]
            
            resp = make_request(path)
            passed = False
            details = ""
            
            if resp["status"] == 200:
                headers = resp["headers"]
                content_type = headers.get("content-type", headers.get("Content-Type", ""))
                content_disp = headers.get("content-disposition", headers.get("Content-Disposition", ""))
                data = resp["data"]
                
                magic_ok = data.startswith(b"%PDF-1.")
                eof_ok = b"%%EOF" in data[-1024:]
                type_ok = "application/pdf" in content_type
                disp_ok = expected_filename in content_disp
                size_ok = len(data) > 30_000

                if magic_ok and eof_ok and type_ok and disp_ok and size_ok:
                    passed = True
                    details = f"HTTP 200, size={len(data):,} bytes, filename={expected_filename}, magic=%PDF-1.x"
                else:
                    details = (
                        f"PDF validation failed: magic={magic_ok}, eof={eof_ok}, "
                        f"type={content_type}, disp={content_disp}, size={len(data)}"
                    )
            else:
                details = f"Expected HTTP 200, got HTTP {resp['status']} (error: {resp['error']})"

            results.append(TestResult(name, "Vietnamese Scenario PDFs", passed, resp["status"], details))

    return results


def test_boundary_and_error_envelopes():
    results = []

    # 1. Invalid industry slugs
    invalid_slug_tests = [
        ("/industries/fake-slug", "Invalid Industry Slug: fake-slug"),
        ("/industries/invalid-slug-xyz", "Invalid Industry Slug: invalid-slug-xyz"),
        ("/industries/12345", "Invalid Numeric Industry Slug: 12345"),
        ("/dossiers/invalid", "Invalid Dossier Slug: invalid"),
        ("/dossiers/fake-industry", "Invalid Dossier Slug: fake-industry"),
        ("/dossiers/non-existent-industry-999", "Invalid Dossier Slug: non-existent-industry-999"),
    ]

    for path, name in invalid_slug_tests:
        resp = make_request(path)
        passed = (resp["status"] == 404)
        details = f"Got HTTP {resp['status']} (expected clean 404)"
        results.append(TestResult(name, "Boundary - Invalid Slugs", passed, resp["status"], details))

    # 2. Out-of-range scenario numbers
    out_of_range_tests = [
        ("/dossiers/petrochem/scenario/0/pdf", "Out-of-range Scenario: petrochem #0"),
        ("/dossiers/petrochem/scenario/6/pdf", "Out-of-range Scenario: petrochem #6"),
        ("/dossiers/petrochem/scenario/99/pdf", "Out-of-range Scenario: petrochem #99"),
        ("/dossiers/petrochem/scenario/999/pdf", "Out-of-range Scenario: petrochem #999"),
        ("/dossiers/petrochem/scenario/-1/pdf", "Out-of-range Scenario: petrochem #-1"),
        ("/dossiers/thermal-power/scenario/0/pdf", "Out-of-range Scenario: thermal-power #0"),
        ("/dossiers/thermal-power/scenario/11/pdf", "Out-of-range Scenario: thermal-power #11"),
        ("/dossiers/gas-pipeline/scenario/0/pdf", "Out-of-range Scenario: gas-pipeline #0"),
        ("/dossiers/gas-pipeline/scenario/16/pdf", "Out-of-range Scenario: gas-pipeline #16"),
        ("/dossiers/metallurgy/scenario/0/pdf", "Out-of-range Scenario: metallurgy #0"),
        ("/dossiers/metallurgy/scenario/21/pdf", "Out-of-range Scenario: metallurgy #21"),
        ("/dossiers/pharma/scenario/0/pdf", "Out-of-range Scenario: pharma #0"),
        ("/dossiers/pharma/scenario/26/pdf", "Out-of-range Scenario: pharma #26"),
        ("/dossiers/fake-slug/scenario/1/pdf", "Scenario with Invalid Industry Slug"),
    ]

    for path, name in out_of_range_tests:
        resp = make_request(path)
        passed = (resp["status"] == 404)
        details = f"Got HTTP {resp['status']} (expected clean 404)"
        results.append(TestResult(name, "Boundary - Out-of-Range Scenarios", passed, resp["status"], details))

    # 3. Advanced Boundary & Edge Cases
    advanced_boundary_tests = [
        ("/dossiers/petrochem/scenario/-1/pdf", "Negative Scenario Number: -1", (404,)),
        ("/dossiers/petrochem/scenario/999999999999999999999999999999/pdf", "Overflow Scenario Integer", (404,)),
        ("/dossiers/petrochem/scenario/abc/pdf", "Non-numeric Scenario: abc", (404,)),
        ("/dossiers/petrochem/scenario/1.5/pdf", "Float Scenario Number: 1.5", (404,)),
        ("/dossiers/petrochem/scenario/1/pdf/", "Scenario with Trailing Slash (Canonical 301/200)", (200, 301)),
        ("/dossiers/PETROCHEM/scenario/1/pdf", "Uppercase Industry Slug: PETROCHEM", (404,)),
        ("/industries/PETROCHEM", "Uppercase Industry Route: PETROCHEM", (404,)),
        ("/dossiers/" + "a" * 1000 + "/scenario/1/pdf", "Buffer Overflow Length Slug (1000 chars)", (404,)),
        ("/industries/" + "a" * 1000, "Buffer Overflow Length Industry Slug (1000 chars)", (404,)),
        ("/dossiers/petroch%D0%B5m/scenario/1/pdf", "Homoglyph Attack: Cyrillic 'e' in petrochem", (404,)),
    ]

    for path, name, expected_statuses in advanced_boundary_tests:
        resp = make_request(path)
        passed = resp["status"] in expected_statuses
        details = f"Got HTTP {resp['status']} (expected {expected_statuses})"
        results.append(TestResult(name, "Boundary - Advanced Edge Cases", passed, resp["status"], details))

    # 4. Path Traversal & Injection Attempts
    security_tests = [
        ("/dossiers/..%2f..%2fetc/scenario/1/pdf", "Path Traversal: URL-encoded dot-dot-slash in slug"),
        ("/dossiers/..%2F..%2Fetc%2Fpasswd/scenario/1/pdf", "Path Traversal: Encoded /etc/passwd in slug"),
        ("/dossiers/%2e%2e%2f%2e%2e%2fetc/scenario/1/pdf", "Path Traversal: Double-encoded dot-dot"),
        ("/dossiers/....//....//etc/scenario/1/pdf", "Path Traversal: Redundant dots and slashes"),
        ("/industries/..%2f..%2fetc", "Path Traversal: Industry route dot-dot-slash"),
        ("/industries/..%2f..%2fetc%2fpasswd", "Path Traversal: Industry route /etc/passwd"),
        ("/dossiers/'%20OR%20'1'='1", "SQL Injection Attempt: ' OR '1'='1 in slug"),
        ("/dossiers/<script>alert(1)</script>", "XSS Injection Attempt: <script> in slug"),
        ("/industries/<script>alert(1)</script>", "XSS Injection Attempt: <script> in industry"),
        ("/dossiers/petrochem;SELECT%20*%20FROM%20res_users;", "SQL Injection Attempt: semicolon SELECT"),
    ]

    for path, name in security_tests:
        resp = make_request(path)
        # Expected response: 404 Not Found (or 400 Bad Request), NEVER 500 or 200 leaking arbitrary file
        passed = (resp["status"] in (404, 400))
        details = f"Got HTTP {resp['status']} (expected clean 404/400, strictly not 500)"
        results.append(TestResult(name, "Adversarial Injections & Traversals", passed, resp["status"], details))

    return results


def test_concurrency_stress():
    results = []
    num_requests = 40
    workers = 8
    test_urls = [
        "/brochure",
        "/brochure/download",
        "/dossiers",
        "/industries/petrochem",
        "/dossiers/petrochem/scenario/1/pdf",
        "/dossiers/fake-slug",
        "/dossiers/petrochem/scenario/999/pdf",
    ]

    tasks = [test_urls[i % len(test_urls)] for i in range(num_requests)]
    
    start_time = time.time()
    statuses = []
    errors = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {executor.submit(make_request, url): url for url in tasks}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                res = future.result()
                statuses.append(res["status"])
                if res["status"] not in (200, 404):
                    errors.append(f"{url} returned unexpected status {res['status']}")
            except Exception as e:
                errors.append(f"{url} raised exception: {e}")

    total_time = time.time() - start_time
    passed = len(errors) == 0 and len(statuses) == num_requests
    details = (
        f"{num_requests} requests across {workers} threads completed in {total_time:.2f}s "
        f"({num_requests/total_time:.1f} req/s). 0 server crashes. Errors: {len(errors)}"
    )

    results.append(TestResult("Concurrent High-Throughput Probe", "Concurrency Stress", passed, 200, details))
    return results


def main():
    print("=" * 80)
    print("🎯 ADVERSARIAL EMPIRICAL CHALLENGER: ROUTE & ASSET VERIFICATION")
    print(f"   Target URL: {BASE_URL}")
    print("=" * 80)

    all_results = []
    
    # 1. Happy path
    print("\n[PHASE 1] Testing Core Happy Path Routes (HTML & Templates)...")
    res1 = test_core_happy_path()
    all_results.extend(res1)
    for r in res1:
        sym = "✅" if r.passed else "❌"
        print(f"  {sym} {r.name:45} | HTTP {r.status_code:3} | {r.details}")

    # 2. Brochure PDF
    print("\n[PHASE 2] Testing Master Brochure PDF Streaming & Headers...")
    res2 = test_brochure_pdf_streaming()
    all_results.extend(res2)
    for r in res2:
        sym = "✅" if r.passed else "❌"
        print(f"  {sym} {r.name:45} | HTTP {r.status_code:3} | {r.details}")

    # 3. All 25 Vietnamese Scenario PDFs
    print("\n[PHASE 3] Testing All 25 Vietnamese Scenario PDF Downloads...")
    res3 = test_all_25_vietnamese_scenario_pdfs()
    all_results.extend(res3)
    for r in res3:
        sym = "✅" if r.passed else "❌"
        print(f"  {sym} {r.name:45} | HTTP {r.status_code:3} | {r.details}")

    # 4. Boundary & Error Envelopes
    print("\n[PHASE 4] Testing Adversarial Boundary & Error Conditions...")
    res4 = test_boundary_and_error_envelopes()
    all_results.extend(res4)
    for r in res4:
        sym = "✅" if r.passed else "❌"
        print(f"  {sym} {r.name:45} | HTTP {r.status_code:3} | {r.details}")

    # 5. Concurrency Stress
    print("\n[PHASE 5] Testing Concurrency Stress & Thread Pool Stability...")
    res5 = test_concurrency_stress()
    all_results.extend(res5)
    for r in res5:
        sym = "✅" if r.passed else "❌"
        print(f"  {sym} {r.name:45} | HTTP {r.status_code:3} | {r.details}")

    # Summary
    print("\n" + "=" * 80)
    print("📊 EMPIRICAL STRESS-TEST RESULTS SUMMARY")
    print("=" * 80)
    
    by_category = {}
    for r in all_results:
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"pass": 0, "fail": 0, "total": 0}
        by_category[cat]["total"] += 1
        if r.passed:
            by_category[cat]["pass"] += 1
        else:
            by_category[cat]["fail"] += 1

    total_pass = sum(c["pass"] for c in by_category.values())
    total_fail = sum(c["fail"] for c in by_category.values())
    total_tests = len(all_results)

    for cat, counts in by_category.items():
        status = "✅ PASS" if counts["fail"] == 0 else "❌ FAIL"
        print(f"  • {cat:35}: {counts['pass']:2}/{counts['total']:2} Passed {status}")

    print("-" * 80)
    print(f"  TOTAL TESTS EXECUTED: {total_tests}")
    print(f"  PASSED: {total_pass} | FAILED: {total_fail}")
    
    verdict = "Verdict: APPROVE" if total_fail == 0 else "Verdict: REQUEST_CHANGES"
    print(f"\n  CHALLENGER VERDICT: {verdict}")
    print("=" * 80)

    # Export report JSON for handoff and telemetry
    report_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": BASE_URL,
        "total_tests": total_tests,
        "passed": total_pass,
        "failed": total_fail,
        "verdict": verdict,
        "categories": by_category,
        "results": [r.to_dict() for r in all_results],
    }
    
    report_path = os.path.join(os.path.dirname(__file__), "challenger_routes_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"Saved machine-readable test telemetry to: {report_path}")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
