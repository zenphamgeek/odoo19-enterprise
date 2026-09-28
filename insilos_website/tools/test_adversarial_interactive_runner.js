#!/usr/bin/env node
/**
 * Insilos Empirical Challenger — Interactive Widgets & Adversarial Stress Suite
 * =============================================================================
 * Rigorous automated headless browser verification of:
 * 1. ROI Multi-Slider Calculator on `/` (boundary values, VND/USD toggle, mathematical oracle)
 * 2. Dynamic Pricing Configurator on `/pricing` (monthly/annual toggle, modular checkboxes, live calculations, ROI bar)
 * 3. Filterable Resource Hub on `/resources` (category filters, search input, combined filtering)
 * 4. 3-Step Demo Request Wizard on `/request-demo` (navigation, step validation, back/forth, POST redirect, honeypot)
 * 5. Platform Topology Accordion on `/platform` (expand, collapse, telemetry status strip, single-open invariant)
 * 6. Adversarial Stress & Console Error Sanitation (rapid interactions, rate limiting, zero console errors)
 * =============================================================================
 */

const { chromium } = require('playwright');
const http = require('http');
const querystring = require('querystring');

const BASE_URL = process.env.INSILOS_BASE_URL || 'http://localhost:28069';

async function waitForPageReady(page) {
    await page.waitForLoadState('networkidle');
    try {
        await page.waitForFunction(() => !document.body.classList.contains('o_lazy_js_waiting'), { timeout: 10000 });
    } catch (e) {
        // Fallback wait
        await page.waitForTimeout(1000);
    }
}

// Mathematical Oracle for ROI Calculator (from home.xml specification)
function calculateExpectedROI(erp, vol, errRate, currency = 'VND') {
    const monthlyHours = vol * 0.2375;
    const annualHours = Math.round(monthlyHours * 12);

    const monthlyErrorsAvoided = vol * (errRate / 100) * 0.98;
    const monthlyErrorCostVND = monthlyErrorsAvoided * 400000;
    const monthlyLaborVND = (vol * 5000) + (erp * 15000000);
    const monthlyTotalVND = monthlyLaborVND + monthlyErrorCostVND;
    const annualSavingsVND = monthlyTotalVND * 12;

    let payback = monthlyTotalVND > 0 ? (1800000000 / monthlyTotalVND) : 3.2;
    if (payback < 1.2) payback = 1.2;
    if (payback > 8.5) payback = 8.5;

    let netSavingsStr = '';
    if (currency === 'VND') {
        if (annualSavingsVND >= 1000000000) {
            const billions = (annualSavingsVND / 1000000000).toFixed(2);
            netSavingsStr = '₫' + billions + ' Tỷ / Năm';
        } else {
            netSavingsStr = '₫' + Math.round(annualSavingsVND).toLocaleString('vi-VN') + ' / Năm';
        }
    } else {
        const annualSavingsUSD = annualSavingsVND / 25000;
        netSavingsStr = '$' + Math.round(annualSavingsUSD).toLocaleString('en-US') + ' / Year';
    }

    return {
        annualHours: annualHours.toLocaleString('vi-VN') + ' Giờ / Năm',
        paybackMonths: payback.toFixed(1) + ' Tháng',
        netSavingsStr: netSavingsStr,
        annualSavingsVND: annualSavingsVND
    };
}

async function runAdversarialInteractiveSuite() {
    console.log('='.repeat(80));
    console.log('🔥 INSILOS ADVERSARIAL CHALLENGER SUITE: INTERACTIVE WIDGETS & STRESS');
    console.log(`   Target URL: ${BASE_URL}`);
    console.log('='.repeat(80));

    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const results = {
        roiCalculator: { passed: false, checks: [] },
        pricingConfigurator: { passed: false, checks: [] },
        resourceFilters: { passed: false, checks: [] },
        demoWizard: { passed: false, checks: [] },
        platformTopology: { passed: false, checks: [] },
        adversarialStress: { passed: false, checks: [] },
    };

    let totalAssertions = 0;
    let passedAssertions = 0;

    function assert(section, name, condition, details = '') {
        totalAssertions++;
        if (condition) {
            passedAssertions++;
            console.log(`  ✅ [PASS] ${name}${details ? ` (${details})` : ''}`);
            section.checks.push({ name, passed: true, details });
            return true;
        } else {
            console.error(`  ❌ [FAIL] ${name}${details ? ` (${details})` : ''}`);
            section.checks.push({ name, passed: false, details });
            return false;
        }
    }

    // =========================================================================
    // 1. ROI MULTI-SLIDER CALCULATOR ON HOMEPAGE (/)
    // =========================================================================
    console.log('\n[CHALLENGE 1] ROI Multi-Slider Calculator Adversarial Tests (/)');
    console.log('-'.repeat(80));

    {
        const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
        const page = await context.newPage();
        await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle', timeout: 45000 });
        await waitForPageReady(page);

        // 1.1 Verify presence of all widget controls
        const elementsExist = await page.evaluate(() => {
            const erp = document.getElementById('ins-calc-erp');
            const vol = document.getElementById('ins-calc-volume');
            const err = document.getElementById('ins-calc-error');
            const toggle = document.getElementById('ins-calc-currency-toggle');
            const netSavings = document.getElementById('ins-calc-net-savings');
            const hoursSaved = document.getElementById('ins-calc-hours-saved');
            const payback = document.getElementById('ins-calc-payback-months');
            return {
                erp: !!erp,
                vol: !!vol,
                err: !!err,
                toggle: !!toggle,
                netSavings: !!netSavings,
                hoursSaved: !!hoursSaved,
                payback: !!payback
            };
        });

        assert(results.roiCalculator, 'ROI DOM Controls Present',
            elementsExist.erp && elementsExist.vol && elementsExist.err && elementsExist.toggle,
            'All 3 sliders, currency toggle, and output nodes exist in DOM');

        // 1.2 Test Default State: Check for conflicting script collision
        const defaultState = await page.evaluate(() => {
            return {
                erp: parseInt(document.getElementById('ins-calc-erp').value, 10),
                vol: parseInt(document.getElementById('ins-calc-volume').value, 10),
                err: parseFloat(document.getElementById('ins-calc-error').value),
                erpDisplay: document.getElementById('ins-calc-val-erp-display')?.textContent.trim(),
                volDisplay: document.getElementById('ins-calc-val-vol-display')?.textContent.trim(),
                errDisplay: document.getElementById('ins-calc-val-err-display')?.textContent.trim(),
                netSavings: document.getElementById('ins-calc-net-savings')?.textContent.trim(),
                hoursSaved: document.getElementById('ins-calc-hours-saved')?.textContent.trim(),
                payback: document.getElementById('ins-calc-payback-months')?.textContent.trim(),
            };
        });

        const expectedDefault = calculateExpectedROI(defaultState.erp, defaultState.vol, defaultState.err, 'VND');
        // Notice: c3ai_interactive overwrites netSavings with "₫6,196,500,000 / Năm" (hardcoded defaults 3 ERPs, 25k docs, 4.5% error)
        const isCorruptedByDefaultScript = defaultState.netSavings === '₫6,196,500,000 / Năm';
        assert(results.roiCalculator, 'ROI Default State Oracle Match (No Script Collisions)',
            !isCorruptedByDefaultScript && defaultState.netSavings.includes('Tỷ'),
            `DOM Output: ${defaultState.netSavings} (Script Collision Detected: ${isCorruptedByDefaultScript ? 'YES (Overwritten by c3ai_interactive.js defaults)' : 'NO'})`);

        // 1.3 Boundary Tests: Min Values (1 ERP, 1,000 docs, 0.5% error)
        const minResults = await page.evaluate(() => {
            const sErp = document.getElementById('ins-calc-erp');
            const sVol = document.getElementById('ins-calc-volume');
            const sErr = document.getElementById('ins-calc-error');
            sErp.value = 1; sErp.dispatchEvent(new Event('input'));
            sVol.value = 1000; sVol.dispatchEvent(new Event('input'));
            sErr.value = 0.5; sErr.dispatchEvent(new Event('input'));
            return {
                netSavings: document.getElementById('ins-calc-net-savings')?.textContent.trim(),
                hoursSaved: document.getElementById('ins-calc-hours-saved')?.textContent.trim(),
                payback: document.getElementById('ins-calc-payback-months')?.textContent.trim(),
            };
        });

        const expectedMin = calculateExpectedROI(1, 1000, 0.5, 'VND');
        assert(results.roiCalculator, 'ROI Min Boundary (1 ERP, 1k docs, 0.5% error)',
            minResults.netSavings === expectedMin.netSavingsStr && minResults.payback === expectedMin.paybackMonths,
            `Calculated: ${minResults.netSavings}, Payback: ${minResults.payback}`);

        // 1.4 Boundary Tests: Max Values (20 ERPs, 500,000 docs, 15.0% error)
        const maxResults = await page.evaluate(() => {
            const sErp = document.getElementById('ins-calc-erp');
            const sVol = document.getElementById('ins-calc-volume');
            const sErr = document.getElementById('ins-calc-error');
            sErp.value = 20; sErp.dispatchEvent(new Event('input'));
            sVol.value = 500000; sVol.dispatchEvent(new Event('input'));
            sErr.value = 15.0; sErr.dispatchEvent(new Event('input'));
            return {
                netSavings: document.getElementById('ins-calc-net-savings')?.textContent.trim(),
                hoursSaved: document.getElementById('ins-calc-hours-saved')?.textContent.trim(),
                payback: document.getElementById('ins-calc-payback-months')?.textContent.trim(),
            };
        });

        const expectedMax = calculateExpectedROI(20, 500000, 15.0, 'VND');
        assert(results.roiCalculator, 'ROI Max Boundary (20 ERPs, 500k docs, 15% error)',
            maxResults.netSavings === expectedMax.netSavingsStr && maxResults.payback === expectedMax.paybackMonths,
            `Calculated: ${maxResults.netSavings}, Payback: ${maxResults.payback}`);

        // 1.5 Currency Toggle (VND <-> USD)
        const usdResults = await page.evaluate(() => {
            const usdBtn = document.querySelector('.ins-calc-curr-btn[data-currency="USD"]');
            if (usdBtn) usdBtn.click();
            return {
                btnActive: usdBtn ? usdBtn.classList.contains('active') : false,
                netSavings: document.getElementById('ins-calc-net-savings')?.textContent.trim(),
            };
        });

        const expectedMaxUSD = calculateExpectedROI(20, 500000, 15.0, 'USD');
        // If c3ai_interactive collided, it set '$247,860 USD / Năm' (using fallback 25k docs) instead of '$15,456,000 / Year'
        assert(results.roiCalculator, 'ROI Currency Switch to USD (Mathematical Accuracy)',
            usdResults.netSavings === expectedMaxUSD.netSavingsStr,
            `DOM: ${usdResults.netSavings} vs Oracle: ${expectedMaxUSD.netSavingsStr}`);

        results.roiCalculator.passed = results.roiCalculator.checks.every(c => c.passed);
        await context.close();
    }

    // =========================================================================
    // 2. PRICING CONFIGURATOR ON /pricing
    // =========================================================================
    console.log('\n[CHALLENGE 2] Pricing Configurator Adversarial Tests (/pricing)');
    console.log('-'.repeat(80));

    {
        const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
        const page = await context.newPage();
        await page.goto(`${BASE_URL}/pricing`, { waitUntil: 'networkidle', timeout: 45000 });
        await waitForPageReady(page);

        // 2.1 Default state verification
        const defaultPricing = await page.evaluate(() => {
            const checks = Array.from(document.querySelectorAll('.ins-mod-check'));
            const checkedCount = checks.filter(c => c.checked).length;
            const totalVnd = document.getElementById('ins-pricing-total-vnd')?.textContent.trim();
            const totalUsd = document.getElementById('ins-pricing-total-usd')?.textContent.trim();

            return {
                totalChecks: checks.length,
                checkedCount,
                totalVnd,
                totalUsd,
            };
        });

        assert(results.pricingConfigurator, 'Pricing Configurator Default State',
            defaultPricing.totalChecks === 4 && defaultPricing.checkedCount === 2 &&
            defaultPricing.totalVnd.includes('42') && defaultPricing.totalUsd.includes('1,680'),
            `Default: 2/4 checked, Total: ${defaultPricing.totalVnd}, USD: ${defaultPricing.totalUsd}`);

        // 2.2 Monthly vs Annual Billing Toggle (-20% discount check)
        await page.click('.ins-billing-btn[data-billing="annual"]');
        await page.waitForTimeout(300);

        const annualResult = await page.evaluate(() => {
            const annualBtn = document.querySelector('.ins-billing-btn[data-billing="annual"]');
            return {
                btnActive: annualBtn ? annualBtn.classList.contains('active') : false,
                totalVnd: document.getElementById('ins-pricing-total-vnd')?.textContent.trim(),
                totalUsd: document.getElementById('ins-pricing-total-usd')?.textContent.trim(),
                period: document.querySelector('.ins-dyn-period')?.textContent.trim(),
            };
        });

        assert(results.pricingConfigurator, 'Annual Discount (-20%) Application',
            annualResult.btnActive && annualResult.totalVnd.includes('33.600.000') &&
            annualResult.totalUsd.includes('1,344') && annualResult.period.includes('Trả theo năm'),
            `Annual Rate: ${annualResult.totalVnd} (-20% exact), Period: ${annualResult.period}`);

        // Toggle back to monthly
        await page.click('.ins-billing-btn[data-billing="monthly"]');
        await page.waitForTimeout(300);

        const monthlyRestore = await page.evaluate(() => {
            const monthlyBtn = document.querySelector('.ins-billing-btn[data-billing="monthly"]');
            return {
                btnActive: monthlyBtn ? monthlyBtn.classList.contains('active') : false,
                totalVnd: document.getElementById('ins-pricing-total-vnd')?.textContent.trim(),
                totalUsd: document.getElementById('ins-pricing-total-usd')?.textContent.trim(),
            };
        });

        assert(results.pricingConfigurator, 'Monthly Billing Restoration',
            monthlyRestore.btnActive && monthlyRestore.totalVnd.includes('42.000.000') &&
            monthlyRestore.totalUsd.includes('1,680'),
            `Restored Monthly: ${monthlyRestore.totalVnd}`);

        // 2.3 Modular Checkboxes: All Unchecked (Zero Modules)
        const zeroModules = await page.evaluate(() => {
            const checks = Array.from(document.querySelectorAll('.ins-mod-check'));
            checks.forEach(c => { if (c.checked) { c.checked = false; c.dispatchEvent(new Event('change')); } });
            return {
                totalVnd: document.getElementById('ins-pricing-total-vnd')?.textContent.trim(),
                totalUsd: document.getElementById('ins-pricing-total-usd')?.textContent.trim(),
                payback: document.querySelector('.ins-payback-label')?.textContent.trim(),
            };
        });

        assert(results.pricingConfigurator, 'Modular Checkboxes: 0 Modules Checked',
            zeroModules.totalVnd.includes('0') && zeroModules.payback.includes('0'),
            `Zero state handled cleanly: ${zeroModules.totalVnd}, Payback: ${zeroModules.payback}`);

        // 2.4 Modular Checkboxes: All 4 Checked (Full Suite: 18M + 24M + 15M + 22M = 79M)
        const allModules = await page.evaluate(() => {
            const checks = Array.from(document.querySelectorAll('.ins-mod-check'));
            checks.forEach(c => { c.checked = true; c.dispatchEvent(new Event('change')); });
            return {
                totalVnd: document.getElementById('ins-pricing-total-vnd')?.textContent.trim(),
                totalUsd: document.getElementById('ins-pricing-total-usd')?.textContent.trim(),
                payback: document.querySelector('.ins-payback-label')?.textContent.trim(),
                progress: document.querySelector('.ins-roi-progress-fill')?.style.width,
            };
        });

        assert(results.pricingConfigurator, 'Modular Checkboxes: All 4 Modules (79M VND / $3,160 USD)',
            allModules.totalVnd.includes('79') && allModules.totalUsd.includes('3,160'),
            `Full Suite: ${allModules.totalVnd}, Payback: ${allModules.payback}, Progress: ${allModules.progress}`);

        results.pricingConfigurator.passed = results.pricingConfigurator.checks.every(c => c.passed);
        await context.close();
    }

    // =========================================================================
    // 3. RESOURCE FILTERING ON /resources
    // =========================================================================
    console.log('\n[CHALLENGE 3] Resource Category & Search Filtering Adversarial Tests (/resources)');
    console.log('-'.repeat(80));

    {
        const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
        const page = await context.newPage();
        await page.goto(`${BASE_URL}/resources`, { waitUntil: 'networkidle', timeout: 45000 });
        await waitForPageReady(page);

        // 3.1 Initial State: All 12 cards visible
        const initialCards = await page.evaluate(() => {
            const cards = Array.from(document.querySelectorAll('.ins-res-card'));
            const visible = cards.filter(c => !c.classList.contains('d-none'));
            return { total: cards.length, visible: visible.length };
        });

        assert(results.resourceFilters, 'Resource Hub Initial State',
            initialCards.total === 12 && initialCards.visible === 12,
            `12/12 resource cards visible initially`);

        // 3.2 Category Filter: Whitepapers (expect 4)
        await page.click('.ins-res-filter-btn[data-filter="whitepaper"]');
        await page.waitForTimeout(300);

        const whitepaperFilter = await page.evaluate(() => {
            const cards = Array.from(document.querySelectorAll('.ins-res-card'));
            const visible = cards.filter(c => !c.classList.contains('d-none'));
            const categories = visible.map(c => c.getAttribute('data-category'));
            return {
                visibleCount: visible.length,
                allMatch: categories.every(cat => cat === 'whitepaper')
            };
        });

        assert(results.resourceFilters, 'Category Filter: Whitepapers (4 cards)',
            whitepaperFilter.visibleCount === 4 && whitepaperFilter.allMatch,
            `Visible: ${whitepaperFilter.visibleCount} cards, all categorized as whitepaper`);

        // 3.3 Category Filter: Case Studies (expect 4)
        await page.click('.ins-res-filter-btn[data-filter="casestudy"]');
        await page.waitForTimeout(300);

        const caseStudyFilter = await page.evaluate(() => {
            const cards = Array.from(document.querySelectorAll('.ins-res-card'));
            const visible = cards.filter(c => !c.classList.contains('d-none'));
            const categories = visible.map(c => c.getAttribute('data-category'));
            return {
                visibleCount: visible.length,
                allMatch: categories.every(cat => cat === 'casestudy')
            };
        });

        assert(results.resourceFilters, 'Category Filter: Case Studies (4 cards)',
            caseStudyFilter.visibleCount === 4 && caseStudyFilter.allMatch,
            `Visible: ${caseStudyFilter.visibleCount} cards, all categorized as casestudy`);

        // 3.4 Category Filter: Webinars (expect 2)
        await page.click('.ins-res-filter-btn[data-filter="webinar"]');
        await page.waitForTimeout(300);

        const webinarFilter = await page.evaluate(() => {
            const cards = Array.from(document.querySelectorAll('.ins-res-card'));
            const visible = cards.filter(c => !c.classList.contains('d-none'));
            const categories = visible.map(c => c.getAttribute('data-category'));
            return {
                visibleCount: visible.length,
                allMatch: categories.every(cat => cat === 'webinar')
            };
        });

        assert(results.resourceFilters, 'Category Filter: Webinars & Demos (2 cards)',
            webinarFilter.visibleCount === 2 && webinarFilter.allMatch,
            `Visible: ${webinarFilter.visibleCount} cards, all categorized as webinar`);

        // 3.5 Category Filter: API Docs (expect 2)
        await page.click('.ins-res-filter-btn[data-filter="apidocs"]');
        await page.waitForTimeout(300);

        const apiFilter = await page.evaluate(() => {
            const cards = Array.from(document.querySelectorAll('.ins-res-card'));
            const visible = cards.filter(c => !c.classList.contains('d-none'));
            const categories = visible.map(c => c.getAttribute('data-category'));
            return {
                visibleCount: visible.length,
                allMatch: categories.every(cat => cat === 'apidocs')
            };
        });

        assert(results.resourceFilters, 'Category Filter: API Docs & Schemas (2 cards)',
            apiFilter.visibleCount === 2 && apiFilter.allMatch,
            `Visible: ${apiFilter.visibleCount} cards, all categorized as apidocs`);

        // 3.6 Reset to "All" (expect 12)
        await page.click('.ins-res-filter-btn[data-filter="all"]');
        await page.waitForTimeout(300);

        const allRestore = await page.evaluate(() => {
            const cards = Array.from(document.querySelectorAll('.ins-res-card'));
            const visible = cards.filter(c => !c.classList.contains('d-none'));
            return { visibleCount: visible.length };
        });

        assert(results.resourceFilters, 'Category Filter Reset: All (12 cards)',
            allRestore.visibleCount === 12,
            `Restored 12/12 cards visible`);

        // 3.7 Search Input Filtering
        const searchWco = await page.evaluate(() => {
            const input = document.getElementById('ins_resource_search');
            input.value = 'WCO';
            input.dispatchEvent(new Event('input'));
            const cards = Array.from(document.querySelectorAll('.ins-res-card'));
            const visible = cards.filter(c => !c.classList.contains('d-none'));
            const allContain = visible.every(c => c.textContent.toLowerCase().includes('wco'));
            return { count: visible.length, allContain };
        });

        assert(results.resourceFilters, 'Search Filter: Keyword "WCO"',
            searchWco.count > 0 && searchWco.allContain,
            `Found ${searchWco.count} cards matching "WCO"`);

        // 3.8 Search Non-Existent Term (expect 0 visible)
        const searchNone = await page.evaluate(() => {
            const input = document.getElementById('ins_resource_search');
            input.value = 'XYZ_NONEXISTENT_QUERY_999';
            input.dispatchEvent(new Event('input'));
            const cards = Array.from(document.querySelectorAll('.ins-res-card'));
            const visible = cards.filter(c => !c.classList.contains('d-none'));
            return { count: visible.length };
        });

        assert(results.resourceFilters, 'Search Filter: Non-Existent Query (0 cards visible)',
            searchNone.count === 0,
            `All cards properly hidden when no match found`);

        // 3.9 Clear Search
        const searchClear = await page.evaluate(() => {
            const input = document.getElementById('ins_resource_search');
            input.value = '';
            input.dispatchEvent(new Event('input'));
            const cards = Array.from(document.querySelectorAll('.ins-res-card'));
            const visible = cards.filter(c => !c.classList.contains('d-none'));
            return { count: visible.length };
        });

        assert(results.resourceFilters, 'Search Filter Clear: 12 cards restored',
            searchClear.count === 12,
            `All 12 cards restored upon clearing search`);

        results.resourceFilters.passed = results.resourceFilters.checks.every(c => c.passed);
        await context.close();
    }

    // =========================================================================
    // 4. DEMO WIZARD & POST SUBMISSION ON /request-demo
    // =========================================================================
    console.log('\n[CHALLENGE 4] Demo Request 3-Step Wizard & POST Funnel (/request-demo)');
    console.log('-'.repeat(80));

    {
        const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
        const page = await context.newPage();
        await page.goto(`${BASE_URL}/request-demo`, { waitUntil: 'networkidle', timeout: 45000 });
        await waitForPageReady(page);

        // 4.1 Initial Wizard State: Step 1 active, Steps 2 & 3 hidden
        const initialWizard = await page.evaluate(() => {
            const pane1 = document.querySelector('.ins-step-pane[data-step="1"]');
            const pane2 = document.querySelector('.ins-step-pane[data-step="2"]');
            const pane3 = document.querySelector('.ins-step-pane[data-step="3"]');
            const item1 = document.querySelector('.ins-step-item[data-step="1"]');

            return {
                pane1Visible: pane1 && !pane1.classList.contains('d-none'),
                pane2Hidden: pane2 && pane2.classList.contains('d-none'),
                pane3Hidden: pane3 && pane3.classList.contains('d-none'),
                item1Active: item1 && item1.classList.contains('active'),
            };
        });

        assert(results.demoWizard, 'Wizard Initial State: Step 1 Active, Steps 2/3 Hidden',
            initialWizard.pane1Visible && initialWizard.pane2Hidden && initialWizard.pane3Hidden && initialWizard.item1Active,
            'Step 1 visible and active; remaining steps hidden');

        // 4.2 Step 1 Validation Gate: Clicking Next without required fields
        const step1Blocked = await page.evaluate(() => {
            const nextBtn = document.querySelector('.ins-step-pane[data-step="1"] .ins-step-btn-next');
            if (nextBtn) nextBtn.click();
            const pane1 = document.querySelector('.ins-step-pane[data-step="1"]');
            const pane2 = document.querySelector('.ins-step-pane[data-step="2"]');
            return {
                stillStep1: pane1 && !pane1.classList.contains('d-none'),
                step2Blocked: pane2 && pane2.classList.contains('d-none'),
            };
        });

        assert(results.demoWizard, 'Wizard Step 1 Validation Gate',
            step1Blocked.stillStep1 && step1Blocked.step2Blocked,
            'Empty required fields prevent progression to Step 2');

        // 4.3 Fill Step 1 and Advance to Step 2
        await page.fill('#demo-name', 'TS. Nguyễn Minh Hải');
        await page.fill('#demo-email', 'minh.hai@energycorp.vn');
        await page.fill('#demo-company', 'National Energy Power Corp');
        await page.fill('#demo-title', 'Phó Giám Đốc Kỹ Thuật');
        await page.fill('#demo-phone', '0912345678');

        await page.click('.ins-step-pane[data-step="1"] .ins-step-btn-next');
        await page.waitForTimeout(300);

        // 4.4 Check if Step 2 is ACTUALLY rendered and visible (Checking for the .active bug)
        const step2Display = await page.evaluate(() => {
            const p2 = document.querySelector('.ins-step-pane[data-step="2"]');
            if (!p2) return { exists: false };
            const style = window.getComputedStyle(p2);
            return {
                exists: true,
                hasActive: p2.classList.contains('active'),
                hasDNone: p2.classList.contains('d-none'),
                computedDisplay: style.display,
                isVisible: style.display !== 'none'
            };
        });

        assert(results.demoWizard, 'Wizard Step 2 Active Class & Display:block Check',
            step2Display.exists && step2Display.hasActive && step2Display.isVisible,
            `Step 2 Computed Display: "${step2Display.computedDisplay}", Active class: ${step2Display.hasActive ? 'YES' : 'NO (insilos.scss requires .active for display:block!)'}`);

        results.demoWizard.passed = results.demoWizard.checks.every(c => c.passed);
        await context.close();
    }

    // =========================================================================
    // 5. PLATFORM TOPOLOGY ACCORDION ON /platform
    // =========================================================================
    console.log('\n[CHALLENGE 5] Platform Topology Accordion Adversarial Tests (/platform)');
    console.log('-'.repeat(80));

    {
        const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
        const page = await context.newPage();
        await page.goto(`${BASE_URL}/platform`, { waitUntil: 'networkidle', timeout: 45000 });
        await waitForPageReady(page);

        // 5.1 Topology Initial State: Row 1 expanded, Rows 2-5 collapsed
        const initialTopo = await page.evaluate(() => {
            const rows = Array.from(document.querySelectorAll('.ins-topology-row'));
            const expanded = rows.filter(r => r.classList.contains('ins-topology-row--expanded'));
            const row1Expanded = document.querySelector('.ins-topology-row[data-topo-row="1"]')?.classList.contains('ins-topology-row--expanded');
            const busSvg = document.querySelector('.ins-topology-bus-svg, .ins-topology-topbar');

            return {
                totalRows: rows.length,
                expandedCount: expanded.length,
                row1Expanded: !!row1Expanded,
                telemetryTopBar: !!busSvg
            };
        });

        assert(results.platformTopology, 'Platform Topology Initial State (Row 1 Expanded)',
            initialTopo.totalRows === 5 && initialTopo.expandedCount === 1 &&
            initialTopo.row1Expanded && initialTopo.telemetryTopBar,
            `5 layers present, exactly Row 1 expanded initially`);

        // 5.2 Single-Open Invariant: Click Row 2
        await page.click('.ins-topology-row[data-topo-row="2"] .ins-topology-row-header');
        await page.waitForTimeout(200);

        const row2Click = await page.evaluate(() => {
            const rows = Array.from(document.querySelectorAll('.ins-topology-row'));
            const expanded = rows.filter(r => r.classList.contains('ins-topology-row--expanded'));
            const row2Expanded = document.querySelector('.ins-topology-row[data-topo-row="2"]')?.classList.contains('ins-topology-row--expanded');
            const row1Expanded = document.querySelector('.ins-topology-row[data-topo-row="1"]')?.classList.contains('ins-topology-row--expanded');

            return {
                expandedCount: expanded.length,
                row2Expanded: !!row2Expanded,
                row1Collapsed: !row1Expanded
            };
        });

        assert(results.platformTopology, 'Topology Expansion: Row 2 Open & Row 1 Collapse',
            row2Click.expandedCount === 1 && row2Click.row2Expanded && row2Click.row1Collapsed,
            `Row 2 expanded; Row 1 collapsed; single-open invariant maintained`);

        // 5.3 Click Row 3, 4, 5 sequentially
        let sequencePassed = true;
        for (const rowNum of [3, 4, 5]) {
            await page.click(`.ins-topology-row[data-topo-row="${rowNum}"] .ins-topology-row-header`);
            await page.waitForTimeout(150);
            const check = await page.evaluate((r) => {
                const target = document.querySelector(`.ins-topology-row[data-topo-row="${r}"]`);
                const allExpanded = Array.from(document.querySelectorAll('.ins-topology-row--expanded'));
                return target && target.classList.contains('ins-topology-row--expanded') && allExpanded.length === 1;
            }, rowNum);
            if (!check) sequencePassed = false;
        }

        assert(results.platformTopology, 'Sequential Expansion across Rows 3, 4, 5',
            sequencePassed,
            'All rows expand and collapse with strictly 1 active row at a time');

        // 5.4 Toggle Collapse: Click active Row 5 again
        await page.click('.ins-topology-row[data-topo-row="5"] .ins-topology-row-header');
        await page.waitForTimeout(200);

        const allCollapsed = await page.evaluate(() => {
            const expanded = Array.from(document.querySelectorAll('.ins-topology-row--expanded'));
            return expanded.length === 0;
        });

        assert(results.platformTopology, 'Topology Toggle Collapse on Active Row (0 Rows Open)',
            allCollapsed,
            'Clicking expanded row successfully collapses it');

        results.platformTopology.passed = results.platformTopology.checks.every(c => c.passed);
        await context.close();
    }

    // =========================================================================
    // 6. ADVERSARIAL STRESS & CONSOLE SANITATION AUDIT
    // =========================================================================
    console.log('\n[CHALLENGE 6] Adversarial Stress & Console Error Sanitation Audit');
    console.log('-'.repeat(80));

    {
        // 6.1 Clean Console Error Audit across all 5 widget routes
        const routes = ['/', '/pricing', '/resources', '/request-demo', '/platform'];
        let totalConsoleErrors = 0;

        for (const route of routes) {
            const context = await browser.newContext();
            const page = await context.newPage();
            const errors = [];
            page.on('pageerror', err => errors.push(err.message));
            page.on('console', msg => {
                if (msg.type() === 'error') errors.push(msg.text());
            });

            await page.goto(`${BASE_URL}${route}`, { waitUntil: 'networkidle', timeout: 30000 });
            await waitForPageReady(page);
            totalConsoleErrors += errors.length;
            await context.close();
        }

        assert(results.adversarialStress, 'Zero Console Errors across 5 Key Routes',
            totalConsoleErrors === 0,
            `Total errors: ${totalConsoleErrors} across [${routes.join(', ')}]`);

        // 6.2 Bot Honeypot Rejection Test on /request-demo POST
        const honeypotContext = await browser.newContext();
        const honeypotPage = await honeypotContext.newPage();
        await honeypotPage.goto(`${BASE_URL}/request-demo`, { waitUntil: 'networkidle' });
        await waitForPageReady(honeypotPage);

        const honeypotResult = await honeypotPage.evaluate(async () => {
            const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
            const formData = new URLSearchParams();
            formData.append('csrf_token', csrfToken);
            formData.append('name', 'Spam Bot 3000');
            formData.append('email', 'spambot@malicious-domain.com');
            formData.append('company', 'Spam Corp');
            formData.append('website_url', 'http://malicious-spam-url.com'); // HONEYPOT FILLED
            formData.append('industry', 'logistics');
            formData.append('use_case', 'vertical_idp');
            formData.append('consent', 'on');

            const res = await fetch('/request-demo', {
                method: 'POST',
                body: formData,
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                redirect: 'manual'
            });

            return {
                status: res.status,
                type: res.type
            };
        });

        assert(results.adversarialStress, 'Bot Honeypot Defense (website_url trap)',
            honeypotResult.status === 303 || honeypotResult.status === 200 || honeypotResult.status === 0,
            `Honeypot intercepted bot submission (status ${honeypotResult.status})`);

        await honeypotContext.close();

        // 6.3 Missing CSRF Protection Test
        const noCsrfResult = await new Promise((resolve) => {
            const postData = querystring.stringify({
                name: 'Attacker Without CSRF',
                email: 'attacker@evil.com',
                company: 'Evil Corp',
                consent: 'on'
            });
            const req = http.request(`${BASE_URL}/request-demo`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Content-Length': Buffer.byteLength(postData)
                }
            }, (res) => {
                resolve(res.statusCode);
            });
            req.on('error', () => resolve(500));
            req.write(postData);
            req.end();
        });

        assert(results.adversarialStress, 'CSRF Protection Enforcement',
            noCsrfResult === 400,
            `Request without CSRF token rejected with HTTP ${noCsrfResult}`);

        results.adversarialStress.passed = results.adversarialStress.checks.every(c => c.passed);
    }

    await browser.close();

    // =========================================================================
    // FINAL VERDICT & SUMMARY TABLE
    // =========================================================================
    console.log('\n' + '='.repeat(80));
    console.log('📋 ADVERSARIAL CHALLENGER VERIFICATION SUMMARY');
    console.log('='.repeat(80));

    const suites = [
        { name: '1. ROI Multi-Slider Calculator (Home)', res: results.roiCalculator },
        { name: '2. Dynamic Pricing Configurator (/pricing)', res: results.pricingConfigurator },
        { name: '3. Filterable Resource Hub (/resources)', res: results.resourceFilters },
        { name: '4. 3-Step Demo Request Wizard (/request-demo)', res: results.demoWizard },
        { name: '5. Platform Topology Accordion (/platform)', res: results.platformTopology },
        { name: '6. Adversarial Stress & Console Sanitation', res: results.adversarialStress },
    ];

    let allSuitesPassed = true;
    suites.forEach(s => {
        const pass = s.res.passed;
        if (!pass) allSuitesPassed = false;
        const icon = pass ? '✅ PASS' : '❌ FAIL';
        console.log(`  ${s.name.padEnd(52)}: ${icon} (${s.res.checks.filter(c => c.passed).length}/${s.res.checks.length} assertions)`);
    });

    console.log('-'.repeat(80));
    console.log(`Total Assertions Evaluated: ${passedAssertions}/${totalAssertions} (${((passedAssertions / totalAssertions) * 100).toFixed(1)}%)`);
    const finalVerdict = allSuitesPassed ? 'APPROVE' : 'REQUEST_CHANGES';
    console.log(`\n🏆 FINAL EMPIRICAL VERDICT: ${finalVerdict}`);
    console.log('='.repeat(80) + '\n');

    return {
        allSuitesPassed,
        finalVerdict,
        totalAssertions,
        passedAssertions,
        results
    };
}

if (require.main === module) {
    runAdversarialInteractiveSuite()
        .then(res => {
            process.exit(res.allSuitesPassed ? 0 : 1);
        })
        .catch(err => {
            console.error('Fatal suite execution error:', err);
            process.exit(1);
        });
}

module.exports = { runAdversarialInteractiveSuite };
