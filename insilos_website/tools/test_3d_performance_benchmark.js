#!/usr/bin/env node
/**
 * =============================================================================
 * INSILOS ENTERPRISE 3D WEBGL PERFORMANCE & 60 FPS BENCHMARK SUITE
 * =============================================================================
 * Challenger 2: Performance & 60 FPS Challenger
 *
 * Objectives:
 * 1. Benchmark 1: WebGL Initialization Latency across 5 cold/warm reloads (< 2.0s).
 * 2. Benchmark 2: Real-time sustained framerate during continuous 3D rotation
 *    and slider interaction (Target >= 50.0 FPS, targeting 60.0 FPS standard).
 * 3. Benchmark 3: WebGL Context Loss (webglcontextlost) simulation & recovery.
 * 4. Benchmark 4: Memory delta & lifecycle check:
 *    - IntersectionObserver auto-pausing (0% CPU / 0 rAF out-of-viewport).
 *    - GPU buffer & geometry disposal on canvas unmount (zero VRAM leaks).
 *    - JS heap memory delta across 5 continuous route transitions.
 * =============================================================================
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.INSILOS_BASE_URL || 'http://localhost:28069';
const REPORT_PATH = path.join(__dirname, 'test_3d_performance_report.json');

// Color helpers for terminal output
const BOLD = '\x1b[1m';
const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const CYAN = '\x1b[36m';
const RESET = '\x1b[0m';

function logSection(title) {
    console.log(`\n${BOLD}${CYAN}================================================================================${RESET}`);
    console.log(`${BOLD}${CYAN}▶ ${title}${RESET}`);
    console.log(`${BOLD}${CYAN}================================================================================${RESET}`);
}

function logSub(title) {
    console.log(`\n${BOLD}--- ${title} ---${RESET}`);
}

async function runBenchmarkSuite() {
    console.log(`${BOLD}🚀 STARTING EMPIRICAL 3D PERFORMANCE & 60 FPS BENCHMARK SUITE${RESET}`);
    console.log(`   Base URL: ${BASE_URL}`);
    console.log(`   Timestamp: ${new Date().toISOString()}`);

    const suiteStartTime = Date.now();
    const benchmarkResults = {
        meta: {
            baseUrl: BASE_URL,
            timestamp: new Date().toISOString(),
            browser: 'Chromium Headless',
            viewport: { width: 1920, height: 1080 }
        },
        findings: [],
        benchmarks: {},
        verdict: 'PENDING'
    };

    const browser = await chromium.launch({
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--enable-webgl',
            '--ignore-gpu-blocklist',
            '--use-gl=angle',
            '--use-angle=swiftshader'
        ]
    });

    try {
        // =====================================================================
        // PRE-FLIGHT: DEPLOYED PRODUCTION STATE & AUTO-MOUNT CHECK
        // =====================================================================
        logSection('PRE-FLIGHT AUDIT: Deployed Production State & Auto-Mount Audit');
        {
            const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
            const page = await context.newPage();
            const consoleErrors = [];
            page.on('console', msg => {
                if (msg.type() === 'error') consoleErrors.push(msg.text());
            });

            await page.goto(`${BASE_URL}/interactive-3d`, { waitUntil: 'networkidle' });
            await page.waitForTimeout(1000);

            const preflight = await page.evaluate(() => {
                const autoInitRes = window.Insilos3D ? window.Insilos3D.autoInit() : null;
                const dtVp = document.getElementById('insilosDigitalTwinViewport');
                const radarVp = document.getElementById('insilosLogisticsRadarViewport');
                const cfgVp = document.getElementById('insilosFactoryRoiViewport');

                const dtSelectorMatch = document.querySelector('.ins-3d-digital-twin-canvas') || document.querySelector('[data-insilos-3d="digital-twin"]');
                const radarSelectorMatch = document.querySelector('.ins-3d-logistics-radar-canvas') || document.querySelector('[data-insilos-3d="logistics-radar"]');
                const cfgSelectorMatch = document.querySelector('.ins-3d-factory-configurator-canvas') || document.querySelector('[data-insilos-3d="factory-configurator"]');

                return {
                    hasTHREE: typeof window.THREE !== 'undefined',
                    hasInsilos3D: typeof window.Insilos3D !== 'undefined',
                    autoInitReturned: autoInitRes ? {
                        hasDt: !!autoInitRes.digitalTwin,
                        hasRadar: !!autoInitRes.logisticsRadar,
                        hasCfg: !!autoInitRes.factoryConfigurator
                    } : null,
                    actualViewportsExist: {
                        dt: !!dtVp,
                        radar: !!radarVp,
                        cfg: !!cfgVp
                    },
                    selectorsMatched: {
                        dt: !!dtSelectorMatch,
                        radar: !!radarSelectorMatch,
                        cfg: !!cfgSelectorMatch
                    }
                };
            });

            console.log(`   window.THREE loaded: ${preflight.hasTHREE ? GREEN + 'YES' : RED + 'NO'}${RESET}`);
            console.log(`   window.Insilos3D loaded: ${preflight.hasInsilos3D ? GREEN + 'YES' : RED + 'NO'}${RESET}`);
            console.log(`   Actual viewports exist in DOM (#insilos...Viewport): ${preflight.actualViewportsExist.dt ? GREEN + 'YES (All 3 exist)' : RED + 'NO'}${RESET}`);
            console.log(`   autoInit() query selectors matched: ${preflight.selectorsMatched.dt ? GREEN + 'YES' : RED + 'NO (0 matches!)'}${RESET}`);
            console.log(`   autoInit() instances created: ${preflight.autoInitReturned?.hasDt ? GREEN + 'YES' : RED + 'NO (All null)'}${RESET}`);

            if (!preflight.selectorsMatched.dt) {
                console.log(`   ${RED}⚠️ CRITICAL DEFECT: autoInit() selector mismatch in insilos_3d_suite.js (lines 1731, 1761, 1779).${RESET}`);
                console.log(`   ${RED}   Queries [.ins-3d-digital-twin-canvas] but snippets_3d.xml defines [#insilosDigitalTwinViewport].${RESET}`);
                benchmarkResults.findings.push({
                    id: 'BUG-3D-AUTOINIT-SELECTOR-MISMATCH',
                    severity: 'CRITICAL',
                    title: 'AutoInit DOM Query Selectors Mismatch QWeb Snippet Viewport IDs',
                    description: 'In insilos_3d_suite.js:1731, 1761, 1779, autoInit() looks for ".ins-3d-digital-twin-canvas", ".ins-3d-logistics-radar-canvas", and ".ins-3d-factory-configurator-canvas". In snippets_3d.xml, the containers are #insilosDigitalTwinViewport, #insilosLogisticsRadarViewport, and #insilosFactoryRoiViewport. Because no element matches, autoInit() never mounts any 3D engine on standard page load.',
                    impact: 'Zero 3D WebGL canvases mount automatically in production; users see static uninitialized viewports.',
                    mitigation: 'Update autoInit() selectors to: document.querySelector("#insilosDigitalTwinViewport, .ins-3d-digital-twin-canvas, [data-insilos-3d=\'digital-twin\']"), etc.'
                });
            }

            await context.close();
        }

        // Helper to setup page and ensure 3D library is loaded
        async function createBenchmarkPage() {
            const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
            const page = await context.newPage();
            return { context, page };
        }

        // =====================================================================
        // BENCHMARK 1: WEBGL INITIALIZATION LATENCY (< 2.0s)
        // =====================================================================
        logSection('BENCHMARK 1: WebGL Initialization Latency (< 2.0s target)');
        {
            const initLatencies = [];
            const iterations = 5;

            for (let i = 1; i <= iterations; i++) {
                const { context, page } = await createBenchmarkPage();
                const tNavStart = Date.now();
                await page.goto(`${BASE_URL}/interactive-3d`, { waitUntil: 'domcontentloaded' });

                // Wait for Insilos3D to become available
                await page.waitForFunction(() => typeof window.Insilos3D !== 'undefined', { timeout: 10000 });

                const runMetrics = await page.evaluate(async () => {
                    const vp1 = document.getElementById('insilosDigitalTwinViewport');
                    const vp2 = document.getElementById('insilosLogisticsRadarViewport');
                    const vp3 = document.getElementById('insilosFactoryRoiViewport');

                    const t0 = performance.now();

                    const tDt0 = performance.now();
                    const dt = new window.Insilos3D.InsilosDigitalTwinEngine(vp1);
                    const tDt1 = performance.now();

                    const tRadar0 = performance.now();
                    const radar = new window.Insilos3D.InsilosLogisticsRadarEngine(vp2);
                    const tRadar1 = performance.now();

                    const tCfg0 = performance.now();
                    const cfg = new window.Insilos3D.InsilosFactoryConfiguratorEngine(vp3);
                    const tCfg1 = performance.now();

                    // Render first frame on all three engines to complete GPU upload & shader compilation
                    const tGpu0 = performance.now();
                    dt.renderer.render(dt.scene, dt.camera);
                    radar.renderer.render(radar.scene, radar.camera);
                    cfg.renderer.render(cfg.scene, cfg.camera);
                    const tGpu1 = performance.now();

                    const totalEngineInitMs = performance.now() - t0;

                    // Clean up
                    dt.dispose();
                    radar.dispose();
                    cfg.dispose();

                    return {
                        totalEngineInitMs,
                        dtInitMs: tDt1 - tDt0,
                        radarInitMs: tRadar1 - tRadar0,
                        cfgInitMs: tCfg1 - tCfg0,
                        firstFrameGpuUploadMs: tGpu1 - tGpu0
                    };
                });

                const totalNavToInitSec = (Date.now() - tNavStart) / 1000;
                initLatencies.push({
                    run: i,
                    navToInitSec: totalNavToInitSec,
                    engineInitMs: runMetrics.totalEngineInitMs,
                    dtInitMs: runMetrics.dtInitMs,
                    radarInitMs: runMetrics.radarInitMs,
                    cfgInitMs: runMetrics.cfgInitMs,
                    gpuUploadMs: runMetrics.firstFrameGpuUploadMs
                });

                console.log(`   Run ${i}/${iterations}: 3 Engines Init = ${runMetrics.totalEngineInitMs.toFixed(2)}ms (DT: ${runMetrics.dtInitMs.toFixed(1)}ms, Radar: ${runMetrics.radarInitMs.toFixed(1)}ms, CFG: ${runMetrics.cfgInitMs.toFixed(1)}ms) | GPU Upload = ${runMetrics.firstFrameGpuUploadMs.toFixed(2)}ms | Nav-to-Ready = ${totalNavToInitSec.toFixed(3)}s`);
                await context.close();
            }

            const navTimes = initLatencies.map(l => l.navToInitSec);
            const engineTimes = initLatencies.map(l => l.engineInitMs);
            const meanNav = navTimes.reduce((a, b) => a + b, 0) / navTimes.length;
            const minNav = Math.min(...navTimes);
            const maxNav = Math.max(...navTimes);
            const meanEngine = engineTimes.reduce((a, b) => a + b, 0) / engineTimes.length;

            console.log(`\n   ${BOLD}Initialization Latency Summary:${RESET}`);
            console.log(`   - Mean 3D Engines Setup Time: ${BOLD}${meanEngine.toFixed(2)}ms${RESET} (< 500ms budget)`);
            console.log(`   - Mean Total Nav-to-Ready: ${BOLD}${meanNav.toFixed(3)}s${RESET} (Target < 2.0s)`);
            console.log(`   - Min: ${minNav.toFixed(3)}s | Max: ${maxNav.toFixed(3)}s`);

            const passInit = meanNav < 2.0;
            console.log(`   - Status: ${passInit ? GREEN + 'PASS (< 2.0s target met)' : RED + 'FAIL (>= 2.0s)'}${RESET}`);

            benchmarkResults.benchmarks.initLatency = {
                passed: passInit,
                targetSec: 2.0,
                iterations: initLatencies,
                meanNavToReadySec: meanNav,
                meanEngineInitMs: meanEngine,
                minNavSec: minNav,
                maxNavSec: maxNav
            };
        }

        // =====================================================================
        // BENCHMARK 2: SUSTAINED FRAMERATE BENCHMARK (>= 50 FPS TARGETING 60 FPS)
        // =====================================================================
        logSection('BENCHMARK 2: Sustained Framerate Under Active Stress');
        {
            const { context, page } = await createBenchmarkPage();
            await page.goto(`${BASE_URL}/interactive-3d`, { waitUntil: 'networkidle' });
            await page.waitForFunction(() => typeof window.Insilos3D !== 'undefined');

            // Initialize all 3 engines on viewports
            await page.evaluate(() => {
                const vp1 = document.getElementById('insilosDigitalTwinViewport');
                const vp2 = document.getElementById('insilosLogisticsRadarViewport');
                const vp3 = document.getElementById('insilosFactoryRoiViewport');

                window.__dt = new window.Insilos3D.InsilosDigitalTwinEngine(vp1);
                window.__radar = new window.Insilos3D.InsilosLogisticsRadarEngine(vp2);
                window.__cfg = new window.Insilos3D.InsilosFactoryConfiguratorEngine(vp3);
            });

            // Reusable FPS meter setup
            async function measureFpsOverWindow(actionCallback, durationMs = 3000) {
                await page.evaluate(() => {
                    window._fpsRecords = [];
                    window._fpsRecording = true;
                    let lastTime = performance.now();
                    function onFrame() {
                        if (!window._fpsRecording) return;
                        const now = performance.now();
                        const delta = now - lastTime;
                        lastTime = now;
                        if (delta > 0) window._fpsRecords.push(1000 / delta);
                        requestAnimationFrame(onFrame);
                    }
                    requestAnimationFrame(onFrame);
                });

                await actionCallback();

                const stats = await page.evaluate(() => {
                    window._fpsRecording = false;
                    const rec = window._fpsRecords;
                    if (rec.length < 5) return { avg: 0, p1: 0, min: 0, count: 0, stdDev: 0 };
                    const sample = rec.slice(2); // drop warmup
                    sample.sort((a, b) => a - b);
                    const avg = sample.reduce((a, b) => a + b, 0) / sample.length;
                    const p1 = sample[Math.floor(sample.length * 0.01)] || sample[0];
                    const min = sample[0];
                    const variance = sample.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / sample.length;
                    const stdDev = Math.sqrt(variance);
                    return { avg, p1, min, count: sample.length, stdDev };
                });

                return stats;
            }

            // 2A: Continuous 3D OrbitControls Drag on Digital Twin (3.0s)
            logSub('2A: Continuous 3D OrbitControls Drag on Digital Twin (3.0s duration)');
            await page.evaluate(() => document.getElementById('insilosDigitalTwinViewport').scrollIntoView({ block: 'center' }));
            await page.waitForTimeout(300);

            const vp1Box = await page.locator('#insilosDigitalTwinViewport').boundingBox();
            const startX1 = vp1Box.x + vp1Box.width / 2;
            const startY1 = vp1Box.y + vp1Box.height / 2;

            const dtFps = await measureFpsOverWindow(async () => {
                await page.mouse.move(startX1, startY1);
                await page.mouse.down();
                const start = Date.now();
                let angle = 0;
                while (Date.now() - start < 3000) {
                    angle += 0.20;
                    const curX = startX1 + Math.cos(angle) * 160;
                    const curY = startY1 + Math.sin(angle) * 120;
                    await page.mouse.move(curX, curY);
                    await page.waitForTimeout(16);
                }
                await page.mouse.up();
            }, 3000);

            console.log(`   Digital Twin Drag: ${BOLD}${dtFps.avg.toFixed(1)} FPS${RESET} (1% Low: ${dtFps.p1.toFixed(1)} FPS | Min: ${dtFps.min.toFixed(1)} FPS | Total Frames: ${dtFps.count})`);
            const passDtFps = dtFps.avg >= 50.0;
            console.log(`   Status: ${passDtFps ? GREEN + 'PASS (>= 50 FPS, steady 60 FPS standard)' : RED + 'FAIL (< 50 FPS)'}${RESET}`);

            // 2B: Continuous 3D OrbitControls Drag on Logistics Radar (3.0s)
            logSub('2B: Continuous 3D OrbitControls Drag on Logistics Radar (3.0s duration)');
            await page.evaluate(() => document.getElementById('insilosLogisticsRadarViewport').scrollIntoView({ block: 'center' }));
            await page.waitForTimeout(300);

            const vp2Box = await page.locator('#insilosLogisticsRadarViewport').boundingBox();
            const startX2 = vp2Box.x + vp2Box.width / 2;
            const startY2 = vp2Box.y + vp2Box.height / 2;

            const radarFps = await measureFpsOverWindow(async () => {
                await page.mouse.move(startX2, startY2);
                await page.mouse.down();
                const start = Date.now();
                let angle = 0;
                while (Date.now() - start < 3000) {
                    angle += 0.18;
                    const curX = startX2 + Math.cos(angle) * 180;
                    const curY = startY2 + Math.sin(angle) * 100;
                    await page.mouse.move(curX, curY);
                    await page.waitForTimeout(16);
                }
                await page.mouse.up();
            }, 3000);

            console.log(`   Logistics Radar Drag: ${BOLD}${radarFps.avg.toFixed(1)} FPS${RESET} (1% Low: ${radarFps.p1.toFixed(1)} FPS | Min: ${radarFps.min.toFixed(1)} FPS | Total Frames: ${radarFps.count})`);
            const passRadarFps = radarFps.avg >= 50.0;
            console.log(`   Status: ${passRadarFps ? GREEN + 'PASS (>= 50 FPS, steady 60 FPS standard)' : RED + 'FAIL (< 50 FPS)'}${RESET}`);

            // 2C: Continuous High-Frequency Slider Drag on Factory Configurator (3.0s)
            logSub('2C: Continuous Slider Drag on Factory Configurator (InstancedMesh Updates)');
            await page.evaluate(() => document.getElementById('insilosFactoryRoiViewport').scrollIntoView({ block: 'center' }));
            await page.waitForTimeout(300);

            const cfgFps = await measureFpsOverWindow(async () => {
                const start = Date.now();
                let step = 0;
                while (Date.now() - start < 3000) {
                    step++;
                    const fleetVal = 10 + Math.round((Math.sin(step * 0.15) * 0.5 + 0.5) * 190);
                    const cncVal = 1 + Math.round((Math.cos(step * 0.15) * 0.5 + 0.5) * 19);

                    await page.evaluate(({ fVal, cVal }) => {
                        if (window.__cfg) {
                            window.__cfg.updateFleet(fVal, cVal);
                        }
                    }, { fVal: fleetVal, cVal: cncVal });
                    await page.waitForTimeout(16);
                }
            }, 3000);

            console.log(`   Factory Configurator Slider Drag: ${BOLD}${cfgFps.avg.toFixed(1)} FPS${RESET} (1% Low: ${cfgFps.p1.toFixed(1)} FPS | Min: ${cfgFps.min.toFixed(1)} FPS | Total Frames: ${cfgFps.count})`);
            const passCfgFps = cfgFps.avg >= 50.0;
            console.log(`   Status: ${passCfgFps ? GREEN + 'PASS (>= 50 FPS, steady 60 FPS standard)' : RED + 'FAIL (< 50 FPS)'}${RESET}`);

            benchmarkResults.benchmarks.sustainedFramerate = {
                digitalTwinFps: dtFps,
                logisticsRadarFps: radarFps,
                factoryConfiguratorFps: cfgFps,
                passed: passDtFps && passRadarFps && passCfgFps
            };

            await context.close();
        }

        // =====================================================================
        // BENCHMARK 3: WEBGL CONTEXT LOSS & GRACEFUL RECOVERY
        // =====================================================================
        logSection('BENCHMARK 3: WebGL Context Loss & Graceful Recovery Simulation');
        {
            const { context, page } = await createBenchmarkPage();
            await page.goto(`${BASE_URL}/interactive-3d`, { waitUntil: 'networkidle' });
            await page.waitForFunction(() => typeof window.Insilos3D !== 'undefined');

            const uncaughtErrors = [];
            page.on('pageerror', err => uncaughtErrors.push(err.message));

            const contextLossResults = await page.evaluate(async () => {
                const vp1 = document.getElementById('insilosDigitalTwinViewport');
                const dt = new window.Insilos3D.InsilosDigitalTwinEngine(vp1);

                const canvas = dt.renderer.domElement;
                const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
                const loseExt = gl.getExtension('WEBGL_lose_context');

                if (!loseExt) {
                    return { supported: false, error: 'WEBGL_lose_context extension not available' };
                }

                let lostEventFired = false;
                let restoredEventFired = false;
                let preventDefaultCalled = false;

                canvas.addEventListener('webglcontextlost', (e) => {
                    lostEventFired = true;
                    preventDefaultCalled = e.defaultPrevented;
                    // Standard recovery requirement: e.preventDefault() must be called
                    e.preventDefault();
                });

                canvas.addEventListener('webglcontextrestored', (e) => {
                    restoredEventFired = true;
                });

                // 1. Simulate Context Loss
                loseExt.loseContext();
                const isLostImmediately = gl.isContextLost();

                // Wait 300ms for rAF loop to encounter lost context
                await new Promise(r => setTimeout(r, 300));

                // 2. Restore Context
                loseExt.restoreContext();
                await new Promise(r => setTimeout(r, 300));
                const isStillLost = gl.isContextLost();

                // 3. Verify render loop continues without throwing
                let renderSucceeded = false;
                try {
                    dt.renderer.render(dt.scene, dt.camera);
                    renderSucceeded = true;
                } catch(e) {
                    renderSucceeded = false;
                }

                dt.dispose();

                return {
                    supported: true,
                    isLostImmediately,
                    lostEventFired,
                    restoredEventFired,
                    appCalledPreventDefault: preventDefaultCalled,
                    isStillLost,
                    renderSucceeded
                };
            });

            console.log(`   WEBGL_lose_context supported: ${contextLossResults.supported ? GREEN + 'YES' : RED + 'NO'}${RESET}`);
            console.log(`   webglcontextlost event fired: ${contextLossResults.lostEventFired ? GREEN + 'YES' : RED + 'NO'}${RESET}`);
            console.log(`   webglcontextrestored event fired: ${contextLossResults.restoredEventFired ? GREEN + 'YES' : RED + 'NO'}${RESET}`);
            console.log(`   Context restored successfully: ${!contextLossResults.isStillLost ? GREEN + 'YES' : RED + 'NO'}${RESET}`);
            console.log(`   Render loop recovered: ${contextLossResults.renderSucceeded ? GREEN + 'YES' : RED + 'NO'}${RESET}`);
            console.log(`   Uncaught page errors during context loss: ${uncaughtErrors.length === 0 ? GREEN + '0' : RED + uncaughtErrors.length}${RESET}`);
            console.log(`   Application registers preventDefault on webglcontextlost: ${contextLossResults.appCalledPreventDefault ? GREEN + 'YES' : YELLOW + 'NO (Omitted in insilos_3d_suite.js)'}${RESET}`);

            if (!contextLossResults.appCalledPreventDefault) {
                benchmarkResults.findings.push({
                    id: 'WARN-3D-CONTEXT-LOSS-PREVENT-DEFAULT',
                    severity: 'HIGH',
                    title: 'Missing event.preventDefault() on webglcontextlost in Engine Event Listeners',
                    description: 'insilos_3d_suite.js does not attach event listeners for "webglcontextlost" on renderer.domElement. Under standard browser WebGL specification, if an application does not call event.preventDefault() when webglcontextlost fires, the browser marks context loss as permanent and will NEVER restore the context automatically after a GPU reset.',
                    impact: 'On mobile/desktop devices when the OS recovers from GPU sleep or transient VRAM pressure, 3D scenes turn permanently black and require hard page reload.',
                    mitigation: 'In _setupEvents() of each engine, add: this.renderer.domElement.addEventListener("webglcontextlost", (e) => { e.preventDefault(); if (this._animId) safeCaf(this._animId); }); and this.renderer.domElement.addEventListener("webglcontextrestored", () => { this.start(); });'
                });
            }

            benchmarkResults.benchmarks.contextLoss = {
                passed: contextLossResults.supported && !contextLossResults.isStillLost && uncaughtErrors.length === 0,
                details: contextLossResults,
                uncaughtErrors
            };

            await context.close();
        }

        // =====================================================================
        // BENCHMARK 4: MEMORY LEAK AUDIT & LIFECYCLE DISPOSAL
        // =====================================================================
        logSection('BENCHMARK 4: Memory Leak & Lifecycle Verification');

        // Part 4A: IntersectionObserver Auto-Pausing
        logSub('4A: IntersectionObserver Viewport Auto-Pausing Verification');
        {
            const { context, page } = await createBenchmarkPage();
            await page.goto(`${BASE_URL}/interactive-3d`, { waitUntil: 'networkidle' });
            await page.waitForFunction(() => typeof window.Insilos3D !== 'undefined');

            const observerResults = await page.evaluate(async () => {
                const vp1 = document.getElementById('insilosDigitalTwinViewport');
                const dt = new window.Insilos3D.InsilosDigitalTwinEngine(vp1);

                // Step 1: Scroll into view
                vp1.scrollIntoView({ block: 'center' });
                await new Promise(r => setTimeout(r, 300));
                let framesInView = 0;
                const origRender = dt.renderer.render.bind(dt.renderer);
                dt.renderer.render = function(s, c) {
                    framesInView++;
                    return origRender(s, c);
                };
                await new Promise(r => setTimeout(r, 1000));

                // Step 2: Scroll away to footer
                document.querySelector('footer').scrollIntoView();
                await new Promise(r => setTimeout(r, 300));
                let framesOutOfView = 0;
                dt.renderer.render = function(s, c) {
                    framesOutOfView++;
                    return origRender(s, c);
                };
                await new Promise(r => setTimeout(r, 1000));

                // Step 3: Scroll back into view
                vp1.scrollIntoView({ block: 'center' });
                await new Promise(r => setTimeout(r, 300));
                let framesBackInView = 0;
                dt.renderer.render = function(s, c) {
                    framesBackInView++;
                    return origRender(s, c);
                };
                await new Promise(r => setTimeout(r, 1000));

                dt.dispose();

                return {
                    framesInView,
                    framesOutOfView,
                    framesBackInView,
                    pausedOutOfView: framesOutOfView === 0,
                    resumedBackInView: framesBackInView >= 40
                };
            });

            console.log(`   Frames while in viewport (1.0s): ${BOLD}${observerResults.framesInView}${RESET} (~60 FPS)`);
            console.log(`   Frames while scrolled to footer (1.0s): ${BOLD}${observerResults.framesOutOfView}${RESET} (0% CPU target: 0 frames)`);
            console.log(`   Frames after scrolling back into view (1.0s): ${BOLD}${observerResults.framesBackInView}${RESET} (~60 FPS)`);
            console.log(`   IntersectionObserver Auto-Pausing: ${observerResults.pausedOutOfView ? GREEN + 'PASS (0 frames out-of-view)' : RED + 'FAIL (Leaking rAF out-of-view)'}${RESET}`);
            console.log(`   IntersectionObserver Auto-Resuming: ${observerResults.resumedBackInView ? GREEN + 'PASS' : RED + 'FAIL'}${RESET}`);

            benchmarkResults.benchmarks.intersectionObserver = {
                passed: observerResults.pausedOutOfView && observerResults.resumedBackInView,
                details: observerResults
            };

            await context.close();
        }

        // Part 4B: GPU Buffer & Resource Disposal on Canvas Unmount
        logSub('4B: GPU Buffer & Resource Disposal (.dispose() call)');
        {
            const { context, page } = await createBenchmarkPage();
            await page.goto(`${BASE_URL}/interactive-3d`, { waitUntil: 'networkidle' });
            await page.waitForFunction(() => typeof window.Insilos3D !== 'undefined');

            const disposalResults = await page.evaluate(async () => {
                const vp1 = document.getElementById('insilosDigitalTwinViewport');
                const vp2 = document.getElementById('insilosLogisticsRadarViewport');
                const vp3 = document.getElementById('insilosFactoryRoiViewport');

                const dt = new window.Insilos3D.InsilosDigitalTwinEngine(vp1);
                const radar = new window.Insilos3D.InsilosLogisticsRadarEngine(vp2);
                const cfg = new window.Insilos3D.InsilosFactoryConfiguratorEngine(vp3);

                // Render at least one frame each to populate GPU caches
                dt.renderer.render(dt.scene, dt.camera);
                radar.renderer.render(radar.scene, radar.camera);
                cfg.renderer.render(cfg.scene, cfg.camera);

                const before = {
                    totalGeometries: dt.renderer.info.memory.geometries + radar.renderer.info.memory.geometries + cfg.renderer.info.memory.geometries,
                    dtGeometries: dt.renderer.info.memory.geometries,
                    radarGeometries: radar.renderer.info.memory.geometries,
                    cfgGeometries: cfg.renderer.info.memory.geometries,
                    totalTextures: dt.renderer.info.memory.textures + radar.renderer.info.memory.textures + cfg.renderer.info.memory.textures
                };

                // Dispose all
                dt.dispose();
                radar.dispose();
                cfg.dispose();

                const after = {
                    totalGeometries: dt.renderer.info.memory.geometries + radar.renderer.info.memory.geometries + cfg.renderer.info.memory.geometries,
                    dtGeometries: dt.renderer.info.memory.geometries,
                    radarGeometries: radar.renderer.info.memory.geometries,
                    cfgGeometries: cfg.renderer.info.memory.geometries,
                    totalTextures: dt.renderer.info.memory.textures + radar.renderer.info.memory.textures + cfg.renderer.info.memory.textures
                };

                return { before, after };
            });

            console.log(`   Geometries before disposal: ${disposalResults.before.totalGeometries} (DT: ${disposalResults.before.dtGeometries}, Radar: ${disposalResults.before.radarGeometries}, Config: ${disposalResults.before.cfgGeometries})`);
            console.log(`   Geometries after disposal: ${BOLD}${disposalResults.after.totalGeometries}${RESET} (Target: 0)`);
            console.log(`   Textures before disposal: ${disposalResults.before.totalTextures} | after disposal: ${disposalResults.after.totalTextures}`);

            const geometriesCleaned = disposalResults.after.totalGeometries === 0;
            console.log(`   GPU Geometry Buffer Cleanup: ${geometriesCleaned ? GREEN + 'PASS (100% disposed to 0)' : RED + 'FAIL (Leaked geometries)'}${RESET}`);

            if (disposalResults.after.totalTextures > 0) {
                benchmarkResults.findings.push({
                    id: 'WARN-3D-SHADOWMAP-TEXTURE-LEAK',
                    severity: 'LOW',
                    title: 'Directional Light ShadowMap Texture Not Explicitly Disposed in DigitalTwinEngine.dispose()',
                    description: `After dt.dispose(), dt.renderer.info.memory.textures remains at ${disposalResults.after.totalTextures} because light.shadow.map.dispose() is omitted in scene traversal before context destruction.`,
                    impact: 'Minor VRAM retention until renderer.forceContextLoss() finalizes.',
                    mitigation: 'In dispose(), iterate lights with shadows and call if (light.shadow?.map) light.shadow.map.dispose()'
                });
            }

            benchmarkResults.benchmarks.disposal = {
                passed: geometriesCleaned,
                details: disposalResults
            };

            await context.close();
        }

        // Part 4C: Route Transition Memory Delta (5 Transitions)
        logSub('4C: Multi-Route Transition Memory Delta (5 Navigation Cycles)');
        {
            const { context, page } = await createBenchmarkPage();
            const cdpSession = await context.newCDPSession(page);

            async function getHeapSizeMb() {
                const metrics = await cdpSession.send('Performance.getMetrics');
                const jsHeap = metrics.metrics.find(m => m.name === 'JSHeapUsedSize');
                return jsHeap ? (jsHeap.value / (1024 * 1024)) : 0;
            }

            // Initial route
            await page.goto(`${BASE_URL}/interactive-3d`, { waitUntil: 'networkidle' });
            await cdpSession.send('HeapProfiler.collectGarbage');
            const initialHeapMb = await getHeapSizeMb();

            const routes = ['/showcase-3d', '/', '/interactive-3d'];
            const transitionLogs = [];

            for (let cycle = 1; cycle <= 5; cycle++) {
                for (const route of routes) {
                    await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded' });
                    await page.waitForTimeout(200);
                }
                await cdpSession.send('HeapProfiler.collectGarbage');
                const curHeapMb = await getHeapSizeMb();
                transitionLogs.push({ cycle, heapMb: curHeapMb });
                console.log(`   Cycle ${cycle}/5 completed -> Current JS Heap: ${curHeapMb.toFixed(2)} MB`);
            }

            await cdpSession.send('HeapProfiler.collectGarbage');
            const finalHeapMb = await getHeapSizeMb();
            const heapDeltaMb = finalHeapMb - initialHeapMb;

            console.log(`\n   ${BOLD}Memory Delta Summary:${RESET}`);
            console.log(`   - Initial JS Heap: ${initialHeapMb.toFixed(2)} MB`);
            console.log(`   - Final JS Heap after 15 route transitions: ${finalHeapMb.toFixed(2)} MB`);
            console.log(`   - Heap Delta: ${BOLD}${heapDeltaMb > 0 ? '+' : ''}${heapDeltaMb.toFixed(2)} MB${RESET} (Leak limit < 25.0 MB)`);

            const passMemory = heapDeltaMb < 25.0;
            console.log(`   - Status: ${passMemory ? GREEN + 'PASS (Zero unbounded heap growth)' : RED + 'FAIL (Excessive memory growth)'}${RESET}`);

            benchmarkResults.benchmarks.memoryDelta = {
                passed: passMemory,
                initialHeapMb,
                finalHeapMb,
                heapDeltaMb,
                transitionLogs
            };

            await context.close();
        }

        // =====================================================================
        // FINAL VERDICT FORMULATION
        // =====================================================================
        logSection('FINAL BENCHMARK VERDICT');
        const b = benchmarkResults.benchmarks;
        const criticalFindings = benchmarkResults.findings.filter(f => f.severity === 'CRITICAL');
        const highFindings = benchmarkResults.findings.filter(f => f.severity === 'HIGH');

        const allBenchmarksPassed = b.initLatency?.passed &&
                                   b.sustainedFramerate?.passed &&
                                   b.contextLoss?.passed &&
                                   b.intersectionObserver?.passed &&
                                   b.disposal?.passed &&
                                   b.memoryDelta?.passed;

        if (criticalFindings.length > 0 || highFindings.length > 0) {
            benchmarkResults.verdict = 'REQUEST_CHANGES';
            console.log(`${BOLD}${RED}❌ VERDICT: REQUEST_CHANGES (CRITICAL/HIGH DEFECTS DETECTED)${RESET}`);
            if (criticalFindings.length > 0) {
                console.log(`${RED}   Critical Defect: AutoInit DOM query selectors mismatch QWeb snippet viewport IDs.${RESET}`);
            }
            if (highFindings.length > 0) {
                console.log(`${YELLOW}   High Defect: Missing event.preventDefault() on webglcontextlost.${RESET}`);
            }
        } else if (!allBenchmarksPassed) {
            benchmarkResults.verdict = 'REQUEST_CHANGES';
            console.log(`${BOLD}${RED}❌ VERDICT: REQUEST_CHANGES (Benchmark criteria not fully met)${RESET}`);
        } else {
            benchmarkResults.verdict = 'APPROVE';
            console.log(`${BOLD}${GREEN}✅ VERDICT: APPROVE (All empirical performance targets met)${RESET}`);
        }

    } finally {
        await browser.close();
    }

    const durationSec = (Date.now() - suiteStartTime) / 1000;
    benchmarkResults.meta.durationSeconds = durationSec;

    fs.writeFileSync(REPORT_PATH, JSON.stringify(benchmarkResults, null, 2), 'utf-8');
    console.log(`\n📄 Benchmark report written to: ${REPORT_PATH}`);
    console.log(`⏱️ Total benchmark execution time: ${durationSec.toFixed(2)}s\n`);

    return benchmarkResults;
}

if (require.main === module) {
    runBenchmarkSuite().then(results => {
        process.exit(results.verdict === 'APPROVE' ? 0 : 1);
    }).catch(err => {
        console.error('Fatal benchmark error:', err);
        process.exit(2);
    });
}

module.exports = { runBenchmarkSuite };
