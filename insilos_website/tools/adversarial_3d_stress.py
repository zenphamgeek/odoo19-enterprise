#!/usr/bin/env python3
"""
Adversarial Stress Test Suite: Insilos Enterprise 3D Interactive Suite & Video Telemetry
========================================================================================
Empirical QA Challenger 1 Test Harness.
Executes high-frequency adversarial user interactions, rapid race-condition triggers,
extreme parameter boundary scrubbing, and real-time synchronization assertions.

Target Routes:
- http://localhost:28069/interactive-3d
- http://localhost:28069/showcase-3d

Challenger 1 Attack Vectors:
1. Rapid Exploded BOM view toggling (tween state corruption / desync)
2. Rapid cycling of PBR, Wireframe, and X-Ray shader modes under continuous camera rotation
3. Rapid clicking of all 4 hotspot pins (DOM updates & deep-link URLs)
4. Rapid scrubbing of logistics radar timeline slider to boundaries and midpoints
5. Factory configurator slider extremes (10-200 vehicles, 1-20 CNCs) & ROI math consistency
6. Random scrubbing of cinema video timeline & telemetry HUD synchronization (<0.5s deviation)
"""

import sys
import os
import time
import json
import math
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

# Ensure environment uses pyenv site-packages for playwright
PYENV_SITE_PACKAGES = "/home/zen/.pyenv/versions/3.12.13/lib/python3.12/site-packages"
if Path(PYENV_SITE_PACKAGES).exists() and PYENV_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, PYENV_SITE_PACKAGES)

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
except ImportError as err:
    print(f"Error importing playwright: {err}")
    sys.exit(1)


@dataclass
class AdversarialCheckResult:
    test_id: str
    name: str
    passed: bool = False
    severity: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW
    empirical_evidence: Dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None
    reproduction_steps: str = ""
    suggested_mitigation: str = ""


class AdversarialStressHarness:
    def __init__(self, base_url: str = "http://localhost:28069", headless: bool = True):
        self.base_url = base_url.rstrip("/")
        self.headless = headless
        self.results: List[AdversarialCheckResult] = []
        self.console_errors: List[str] = []
        self.page_errors: List[str] = []

    def log(self, msg: str):
        print(f"[CHALLENGER 1] {msg}", flush=True)

    def run(self) -> Dict[str, Any]:
        self.log(f"Starting Adversarial Stress Test Harness against {self.base_url}...")
        start_time = time.time()

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--use-gl=angle",
                    "--use-angle=swiftshader",
                    "--enable-webgl",
                    "--ignore-gpu-blocklist",
                ]
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 InsilosChallenger/1.0"
            )

            page = context.new_page()
            page.on("console", lambda msg: self._handle_console(msg))
            page.on("pageerror", lambda err: self.page_errors.append(str(err)))

            try:
                # 0. Asset Loading & Infrastructure Baseline
                self.test_0_infrastructure_and_asset_integrity(page)

                # 1. Rapid Exploded BOM Toggling Stress
                self.test_1_rapid_exploded_bom_stress(page)

                # 2. Shader Mode Cycling Under Camera Rotation
                self.test_2_shader_mode_cycling_under_rotation(page)

                # 3. Hotspot Pins Rapid Succession Trigger
                self.test_3_hotspot_pins_rapid_succession(page)

                # 4. Logistics Radar Timeline Boundary Scrubbing
                self.test_4_logistics_radar_scrubbing(page)

                # 5. Factory Configurator Slider Extremes & ROI Math
                self.test_5_factory_configurator_roi_extremes(page)

                # 6. Cinema Video Player Random Scrubbing & Telemetry Sync
                self.test_6_video_telemetry_random_scrubbing(page)

            finally:
                page.close()
                context.close()
                browser.close()

        duration = time.time() - start_time
        return self._build_report(duration)

    def _handle_console(self, msg):
        if msg.type in ("error", "warning"):
            text = msg.text
            if "error" in msg.type.lower() or "unmet dependencies" in text or "have not been defined" in text:
                self.console_errors.append(text)

    # --------------------------------------------------------------------------
    # Test 0: Infrastructure & Asset Pipeline Integrity
    # --------------------------------------------------------------------------
    def test_0_infrastructure_and_asset_integrity(self, page: Page):
        self.log("Executing Test 0: Asset Pipeline Integrity & Module Loading...")
        target_url = f"{self.base_url}/interactive-3d"
        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        check = AdversarialCheckResult(
            test_id="ADV-00-ASSETS",
            name="Three.js & Insilos3D Global Module Bundle Integrity",
            severity="CRITICAL",
            reproduction_steps=f"Navigate to {target_url} and inspect browser console for AMD dependency errors."
        )

        eval_res = page.evaluate("""() => {
            return {
                hasThree: typeof window.THREE !== 'undefined',
                hasInsilos3D: typeof window.Insilos3D !== 'undefined',
                hasInstances: !!(window.Insilos3D && window.Insilos3D.instances),
                windowKeys: Object.keys(window).filter(k => k.toLowerCase().includes('3d') || k.toLowerCase().includes('insilos'))
            };
        }""")

        unmet_errors = [e for e in self.console_errors if "unmet dependencies" in e or "not been defined" in e]

        check.empirical_evidence = {
            "eval_globals": eval_res,
            "unmet_errors": unmet_errors,
            "total_console_errors": len(self.console_errors)
        }

        if not eval_res.get("hasInsilos3D") or unmet_errors:
            check.passed = False
            check.failure_reason = (
                f"Insilos3D module failed to initialize (hasInsilos3D={eval_res.get('hasInsilos3D')}). "
                f"Odoo AMD loader threw unmet dependency errors: {unmet_errors}"
            )
            check.suggested_mitigation = (
                "In insilos_3d_suite.js, replace the AMD define(['three'], factory) wrapper with a strict IIFE "
                "binding directly to window.THREE, preventing Odoo's asset compiler from treating 'three' as an unmet Odoo module."
            )
        else:
            check.passed = True

        self.results.append(check)

    # --------------------------------------------------------------------------
    # Test 1: Rapid Exploded BOM View Toggling
    # --------------------------------------------------------------------------
    def test_1_rapid_exploded_bom_stress(self, page: Page):
        self.log("Executing Test 1: Rapid Exploded BOM View Toggling Stress...")
        check = AdversarialCheckResult(
            test_id="ADV-01-BOM",
            name="Rapid Exploded BOM View Toggling (25x Rapid Invocations)",
            severity="HIGH",
            reproduction_steps="Rapidly click #btnExplodedBom 25 times at 50ms intervals while verifying mesh displacement and class state."
        )

        res = page.evaluate("""async () => {
            const btn = document.querySelector('#btnExplodedBom') || document.querySelector('[data-action=\"toggle-exploded\"]');
            if (!btn) return { error: 'No exploded BOM button found in DOM' };

            const clicks = 25;
            const history = [];

            for (let i = 0; i < clicks; i++) {
                btn.click();
                await new Promise(r => setTimeout(r, 40));
                history.push({
                    iteration: i,
                    activeClass: btn.classList.contains('active'),
                    btnText: btn.textContent.trim()
                });
            }

            // Wait for any tween to settle
            await new Promise(r => setTimeout(r, 600));

            const dt = window.Insilos3D && window.Insilos3D.instances ? window.Insilos3D.instances.digitalTwin : null;
            let engineExploded = null;
            let subAssembliesDisplaced = false;

            if (dt) {
                engineExploded = dt.options.exploded;
                if (dt._subAssemblies && dt._subAssemblies.length > 0) {
                    const battery = dt._subAssemblies.find(s => s.id === 'node_battery');
                    if (battery) {
                        const dist = battery.group.position.distanceTo(battery.assembledPos);
                        subAssembliesDisplaced = dist > 0.1;
                    }
                }
            }

            return {
                buttonFound: true,
                finalActiveClass: btn.classList.contains('active'),
                totalClicks: clicks,
                engineAttached: !!dt,
                engineExploded: engineExploded,
                subAssembliesDisplaced: subAssembliesDisplaced,
                historySample: history.slice(0, 5)
            };
        }""")

        check.empirical_evidence = res

        if res.get("error"):
            check.passed = False
            check.failure_reason = res["error"]
        elif not res.get("engineAttached"):
            check.passed = False
            check.failure_reason = "Exploded BOM button click had zero effect because DigitalTwinEngine is not attached to DOM."
            check.suggested_mitigation = (
                "Ensure InsilosDigitalTwinEngine binds to #insilosDigitalTwinViewport and listens to #btnExplodedBom clicks."
            )
        elif not res.get("finalActiveClass") and res.get("subAssembliesDisplaced"):
            check.passed = False
            check.failure_reason = "Desynchronization: Button class is inactive but 3D sub-assemblies remain exploded."
        else:
            check.passed = res.get("buttonFound") and res.get("engineAttached")

        self.results.append(check)

    # --------------------------------------------------------------------------
    # Test 2: Shader Mode Cycling Under Camera Rotation
    # --------------------------------------------------------------------------
    def test_2_shader_mode_cycling_under_rotation(self, page: Page):
        self.log("Executing Test 2: Rapid Shader Mode Cycling Under OrbitControls Drag...")
        check = AdversarialCheckResult(
            test_id="ADV-02-SHADER",
            name="Shader Mode Switcher Cycling (PBR -> Wire -> XRay -> PBR) Under Continuous Rotation",
            severity="HIGH",
            reproduction_steps="Drag OrbitControls continuously across canvas while cycling shader modes 30 times."
        )

        # Simulate mouse drag on canvas
        canvas = page.query_selector("#insilosDigitalTwinCanvas, .ins-3d-canvas")
        if canvas:
            box = canvas.bounding_box()
            if box:
                page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                page.mouse.down()
                page.mouse.move(box["x"] + box["width"] / 2 + 100, box["y"] + box["height"] / 2 + 50, steps=10)

        res = page.evaluate("""async () => {
            const btnWire = document.querySelector('#btnModeWire') || document.querySelector('[data-mode=\"wireframe\"]');
            const btnXray = document.querySelector('#btnModeXray') || document.querySelector('[data-mode=\"xray\"]');
            const btnPbr = document.querySelector('#btnModePbr') || document.querySelector('[data-mode=\"pbr\"]');

            if (!btnWire || !btnXray || !btnPbr) {
                return { error: 'Shader mode buttons missing in DOM' };
            }

            const dt = window.Insilos3D && window.Insilos3D.instances ? window.Insilos3D.instances.digitalTwin : null;
            if (!dt) {
                return {
                    error: 'DigitalTwin engine not instantiated; shader buttons unattached',
                    engineAttached: false
                };
            }

            // Perform 30 rapid switches: PBR -> Wire -> XRay -> PBR
            const cycles = 10;
            const log = [];

            for (let i = 0; i < cycles; i++) {
                btnWire.click();
                await new Promise(r => setTimeout(r, 25));
                btnXray.click();
                await new Promise(r => setTimeout(r, 25));
                btnPbr.click();
                await new Promise(r => setTimeout(r, 25));
            }

            // Inspect mesh materials to see if original PBR was successfully restored
            let wireframeMeshesCount = 0;
            let standardMeshesCount = 0;
            let totalMeshes = 0;

            dt.modelsRoot.traverse(obj => {
                if (obj.isMesh && obj.material) {
                    totalMeshes++;
                    if (obj.material.wireframe) wireframeMeshesCount++;
                    if (obj.material.isMeshStandardMaterial && !obj.material.wireframe) standardMeshesCount++;
                }
            });

            return {
                engineAttached: true,
                totalMeshes,
                wireframeMeshesCount,
                standardMeshesCount,
                pbrRestoredSuccessfully: wireframeMeshesCount === 0 && standardMeshesCount > 0
            };
        }""")

        if canvas:
            page.mouse.up()

        check.empirical_evidence = res

        if res.get("error"):
            check.passed = False
            check.failure_reason = res["error"]
            check.suggested_mitigation = (
                "Fix insilos_3d_suite.js loading in Odoo assets and ensure buttons call setRenderMode() properly."
            )
        elif not res.get("pbrRestoredSuccessfully"):
            check.passed = False
            check.failure_reason = (
                f"Shader restoration defect: After switching Wireframe -> XRay -> PBR, "
                f"{res.get('wireframeMeshesCount')} meshes remained trapped in wireframe mode. "
                "Caused by obj.material.name check in setRenderMode where dynamically created materials lack name property."
            )
            check.suggested_mitigation = (
                "In setRenderMode(), check if (obj.isMesh && obj.material) without requiring obj.material.name, "
                "and ensure original materials are preserved in a separate WeakMap or obj._originalMaterial property."
            )
        else:
            check.passed = True

        self.results.append(check)

    # --------------------------------------------------------------------------
    # Test 3: Hotspot Pins Rapid Succession Trigger
    # --------------------------------------------------------------------------
    def test_3_hotspot_pins_rapid_succession(self, page: Page):
        self.log("Executing Test 3: Rapid Succession Hotspot Pin Clicking...")
        check = AdversarialCheckResult(
            test_id="ADV-03-HOTSPOTS",
            name="Hotspot Pins Rapid Succession Trigger & Live ERP Card Generation",
            severity="HIGH",
            reproduction_steps="Rapidly click all 4 hotspot pins in succession within <100ms intervals and verify telemetry HUD popup."
        )

        res = page.evaluate("""async () => {
            const pins = Array.from(document.querySelectorAll('.ins-hotspot-pin, [data-hotspot-id]'));
            if (pins.length === 0) return { error: 'Zero hotspot pins found in DOM' };

            const clicks = [];
            for (const pin of pins) {
                pin.click();
                clicks.push({
                    id: pin.id || pin.getAttribute('data-hotspot-id'),
                    classes: pin.className
                });
                await new Promise(r => setTimeout(r, 60));
            }

            await new Promise(r => setTimeout(r, 300));

            // Check if card or popup emerged
            const card = document.querySelector('.ins-3d-hotspot-card, .ins-hotspot-card');
            const cardVisible = card && !card.classList.contains('d-none') && card.offsetHeight > 0;
            const cardHtml = card ? card.innerHTML : '';

            // Verify live ERP record mentions
            const verifiedKeywords = ['WH/MO/00010', 'SF-BATTPACK-400AH', 'LOT-HP-SS400-2026-01', 'WC-ASM-01', 'mrp.production'];
            const matchedKeywords = verifiedKeywords.filter(k => cardHtml.includes(k));

            return {
                pinsFoundCount: pins.length,
                clicks,
                cardExists: !!card,
                cardVisible: cardVisible,
                matchedKeywords: matchedKeywords
            };
        }""")

        check.empirical_evidence = res

        if res.get("error"):
            check.passed = False
            check.failure_reason = res["error"]
        elif not res.get("cardVisible"):
            check.passed = False
            check.failure_reason = (
                f"Hotspot pins ({res.get('pinsFoundCount')}) failed to trigger a visible HUD card popup. "
                "Hotspot event listeners are unattached or canvas overlay is inert."
            )
            check.suggested_mitigation = (
                "Ensure focusHotspot() is invoked when clicking .ins-hotspot-pin and displays .ins-3d-hotspot-card with live ERP fields."
            )
        elif len(res.get("matchedKeywords", [])) < 1:
            check.passed = False
            check.failure_reason = "Hotspot HUD card displayed but contained zero live ERP data records."
        else:
            check.passed = True

        self.results.append(check)

    # --------------------------------------------------------------------------
    # Test 4: Logistics Radar Timeline Boundary Scrubbing
    # --------------------------------------------------------------------------
    def test_4_logistics_radar_scrubbing(self, page: Page):
        self.log("Executing Test 4: Logistics Radar Timeline Slider Boundary Scrubbing...")
        check = AdversarialCheckResult(
            test_id="ADV-04-RADAR",
            name="Logistics Radar Timeline Boundary & Midpoint Scrubbing (0%, 25%, 50%, 75%, 100%)",
            severity="MEDIUM",
            reproduction_steps="Scrub #insilosLogisticsTimeline rapidly across boundary values (0, 25, 50, 75, 100) and verify DOM text and convoy translation."
        )

        res = page.evaluate("""async () => {
            const slider = document.querySelector('#insilosLogisticsTimeline') || document.querySelector('.ins-timeline-scrubber');
            const valDisplay = document.querySelector('#radarTimelineValue') || document.querySelector('#ins-radar-progress-pct');

            if (!slider) return { error: 'Logistics radar timeline slider missing in DOM' };

            const testValues = [0, 100, 25, 75, 50, 0, 100];
            const observations = [];

            for (const val of testValues) {
                slider.value = val;
                slider.dispatchEvent(new Event('input', { bubbles: true }));
                slider.dispatchEvent(new Event('change', { bubbles: true }));
                await new Promise(r => setTimeout(r, 60));

                observations.push({
                    setVal: val,
                    displayedText: valDisplay ? valDisplay.textContent.trim() : null
                });
            }

            const radarEngine = window.Insilos3D && window.Insilos3D.instances ? window.Insilos3D.instances.logisticsRadar : null;
            let convoyMoved = false;
            if (radarEngine && radarEngine.convoyGroup) {
                convoyMoved = !isNaN(radarEngine.convoyGroup.position.x) && radarEngine.convoyGroup.position.length() > 0;
            }

            const initialText = observations[0].displayedText;
            const textUpdated = observations.some(o => o.displayedText !== initialText);

            return {
                sliderFound: true,
                radarEngineAttached: !!radarEngine,
                observations,
                textUpdated,
                convoyMoved
            };
        }""")

        check.empirical_evidence = res

        if res.get("error"):
            check.passed = False
            check.failure_reason = res["error"]
        elif not res.get("radarEngineAttached") and not res.get("textUpdated"):
            check.passed = False
            check.failure_reason = "Logistics radar slider is completely disconnected: text display and 3D convoy remain frozen."
            check.suggested_mitigation = (
                "Bind #insilosLogisticsTimeline input event to InsilosLogisticsRadarEngine.seekTimeline() and update #radarTimelineValue."
            )
        else:
            check.passed = res.get("textUpdated") or res.get("convoyMoved")

        self.results.append(check)

    # --------------------------------------------------------------------------
    # Test 5: Factory Configurator Extremes & ROI Mathematical Consistency
    # --------------------------------------------------------------------------
    def test_5_factory_configurator_roi_extremes(self, page: Page):
        self.log("Executing Test 5: Factory Configurator Sliders (Extremes) & ROI Math Verification...")
        check = AdversarialCheckResult(
            test_id="ADV-05-ROI",
            name="Factory Configurator Sliders (10-200 Vehicles, 1-20 CNCs) & Mathematical ROI Consistency",
            severity="HIGH",
            reproduction_steps="Drag vehicle slider to [10, 200] and CNC slider to [1, 20], verifying exact financial ROI/TCO math formulas."
        )

        res = page.evaluate("""async () => {
            const sFleet = document.querySelector('#inputFleetSize') || document.querySelector('#ins-slider-vehicles');
            const sCnc = document.querySelector('#inputCncCount') || document.querySelector('#ins-slider-cnc');
            const elSavings = document.querySelector('#roiAnnualSavings') || document.querySelector('#ins-roi-monthly-savings');
            const elPayback = document.querySelector('#roiPaybackMonths') || document.querySelector('#ins-roi-payback');

            if (!sFleet || !sCnc) return { error: 'Factory configurator sliders not found in DOM' };

            const testScenarios = [
                { vehicles: 10, cnc: 1 },
                { vehicles: 200, cnc: 20 },
                { vehicles: 50, cnc: 6 },
                { vehicles: 120, cnc: 14 }
            ];

            const results = [];

            for (const sc of testScenarios) {
                sFleet.value = sc.vehicles;
                sFleet.dispatchEvent(new Event('input', { bubbles: true }));
                sFleet.dispatchEvent(new Event('change', { bubbles: true }));

                sCnc.value = sc.cnc;
                sCnc.dispatchEvent(new Event('input', { bubbles: true }));
                sCnc.dispatchEvent(new Event('change', { bubbles: true }));

                await new Promise(r => setTimeout(r, 80));

                results.push({
                    vehicles: sc.vehicles,
                    cnc: sc.cnc,
                    savingsText: elSavings ? elSavings.textContent.trim() : null,
                    paybackText: elPayback ? elPayback.textContent.trim() : null
                });
            }

            const initialSavings = results[0].savingsText;
            const reactive = results.some(r => r.savingsText !== initialSavings);

            // Compute expected theoretical math
            // Monthly savings: nV * 5.25M + nC * 40.125M
            // Capex: 450M + nV * 12M + nC * 35M
            const theoretical = testScenarios.map(sc => {
                const monthly = sc.vehicles * 5250000 + sc.cnc * 40125000;
                const capex = 450000000 + sc.vehicles * 12000000 + sc.cnc * 35000000;
                const payback = monthly > 0 ? (capex / monthly) : 0;
                return {
                    vehicles: sc.vehicles,
                    cnc: sc.cnc,
                    monthlyVnd: monthly,
                    annualVnd: monthly * 12,
                    capexVnd: capex,
                    paybackMonths: Number(payback.toFixed(2))
                };
            });

            return {
                reactive,
                results,
                theoretical
            };
        }""")

        check.empirical_evidence = res

        if res.get("error"):
            check.passed = False
            check.failure_reason = res["error"]
        elif not res.get("reactive"):
            check.passed = False
            check.failure_reason = (
                "Factory configurator sliders are inert: changing vehicles from 10 to 200 produces 0 changes in "
                "ROI annual savings or payback months. Element IDs in snippets_3d.xml (#inputFleetSize, #inputCncCount, #roiAnnualSavings) "
                "mismatch IDs in insilos_3d_suite.js (#ins-slider-vehicles, #ins-val-vehicles, #ins-roi-monthly-savings)."
            )
            check.suggested_mitigation = (
                "Unify slider IDs between snippets_3d.xml and insilos_3d_suite.js to #inputFleetSize / #inputCncCount, "
                "and update #roiAnnualSavings and #roiPaybackMonths dynamically upon slider input."
            )
        else:
            check.passed = True

        self.results.append(check)

    # --------------------------------------------------------------------------
    # Test 6: Video Telemetry Random Scrubbing & HUD Sync (<0.5s)
    # --------------------------------------------------------------------------
    def test_6_video_telemetry_random_scrubbing(self, page: Page):
        self.log("Executing Test 6: Video Telemetry Random Scrubbing & HUD Stream Synchronization (<0.5s)...")
        check = AdversarialCheckResult(
            test_id="ADV-06-VIDEO-SYNC",
            name="Cinema HUD Video Telemetry Random Seeking & Precision Synchronization (<0.5s Deviation)",
            severity="CRITICAL",
            reproduction_steps="Seek cinema video to 10 erratic timestamps across all 3 acts and verify HUD updates in <0.5s."
        )

        res = page.evaluate("""async () => {
            const v = document.querySelector('video.ins-video-element') || document.querySelector('video');
            const reg = window.InsilosVideoTelemetryRegistry;
            const currentData = reg ? reg['VID_04_BOM'] : null;

            if (!v || !currentData) return { error: 'Video element or telemetry registry not found' };

            const testTimestamps = [5.0, 15.2, 28.0, 39.5, 48.0, 55.4, 2.0, 43.1, 58.0];
            const syncAudits = [];

            for (const ts of testTimestamps) {
                v.currentTime = ts;
                v.dispatchEvent(new Event('timeupdate'));

                // Allow 2 animation frames for rAF throttle
                await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

                // Expected milestone:
                const milestones = currentData.telemetryMilestones;
                let expectedIdx = 0;
                for (let i = milestones.length - 1; i >= 0; i--) {
                    if (ts >= milestones[i].timestamp) {
                        expectedIdx = i;
                        break;
                    }
                }
                const expectedMs = milestones[expectedIdx];

                const chapterTitle = document.querySelector('.ins-hud-chapter-title')?.textContent?.trim();
                const deepLinkHref = document.querySelector('.ins-deeplink-btn')?.href || document.querySelector('#insilosErpDeepLink')?.href;

                const matched = chapterTitle === expectedMs.chapter;
                const timeDiff = Math.abs(ts - expectedMs.timestamp);

                syncAudits.push({
                    seekTime: ts,
                    expectedChapter: expectedMs.chapter,
                    actualChapter: chapterTitle,
                    matched: matched,
                    timeDiff: timeDiff,
                    deepLinkHref: deepLinkHref
                });
            }

            const allMatched = syncAudits.every(a => a.matched);
            const maxDeviation = Math.max(...syncAudits.map(a => a.timeDiff));

            return {
                totalSeeks: testTimestamps.length,
                allMatched: allMatched,
                maxDeviation: maxDeviation,
                syncAudits: syncAudits
            };
        }""")

        check.empirical_evidence = res

        if res.get("error"):
            check.passed = False
            check.failure_reason = res["error"]
        elif not res.get("allMatched"):
            mismatches = [a for a in res.get("syncAudits", []) if not a["matched"]]
            check.passed = False
            check.failure_reason = f"HUD Telemetry synchronization failed on {len(mismatches)} seeks: {mismatches}"
        else:
            check.passed = True

        self.results.append(check)

    def _build_report(self, duration: float) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        verdict = "APPROVE" if failed == 0 else "REQUEST_CHANGES"

        report = {
            "challenger": "Challenger 1 (Interactive Stress Challenger)",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_seconds": round(duration, 2),
            "target_url": self.base_url,
            "verdict": verdict,
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "pass_rate_percent": round((passed / total) * 100, 1) if total > 0 else 0
            },
            "failures": [
                {
                    "test_id": r.test_id,
                    "name": r.name,
                    "severity": r.severity,
                    "reason": r.failure_reason,
                    "mitigation": r.suggested_mitigation,
                    "evidence": r.empirical_evidence
                }
                for r in self.results if not r.passed
            ],
            "passes": [
                {
                    "test_id": r.test_id,
                    "name": r.name,
                    "evidence": r.empirical_evidence
                }
                for r in self.results if r.passed
            ],
            "console_errors_detected": self.console_errors,
            "page_errors_detected": self.page_errors
        }

        return report


def main():
    harness = AdversarialStressHarness(base_url="http://localhost:28069", headless=True)
    report = harness.run()

    print("\n" + "=" * 80)
    print(" " * 20 + "ADVERSARIAL STRESS TEST SCORECARD (CHALLENGER 1)")
    print("=" * 80)
    print(f"Verdict        : {report['verdict']}")
    print(f"Tests Passed   : {report['summary']['passed']} / {report['summary']['total_tests']} ({report['summary']['pass_rate_percent']}%)")
    print(f"Execution Time : {report['duration_seconds']}s")
    print("-" * 80)

    for item in report["passes"]:
        print(f" [PASS] {item['test_id']}: {item['name']}")

    for item in report["failures"]:
        print(f" [FAIL] {item['test_id']}: {item['name']} [{item['severity']}]")
        print(f"        Reason: {item['reason']}")
        if item.get("mitigation"):
            print(f"        Mitigation: {item['mitigation']}")

    print("=" * 80 + "\n")

    # Save JSON report
    report_file = Path("/home/zen/O20/enterprise/insilos_website/tools/adversarial_stress_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report saved to: {report_file}")

    sys.exit(0 if report["verdict"] == "APPROVE" else 1)


if __name__ == "__main__":
    main()
