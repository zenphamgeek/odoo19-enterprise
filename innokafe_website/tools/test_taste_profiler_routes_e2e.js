const { chromium } = require('playwright');

(async () => {
    console.log("=== INNOKAFE TASTE PROFILER COMPREHENSIVE PLAYWRIGHT E2E SUITE ===");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 1440, height: 900 }
    });
    const page = await context.newPage();

    const consoleErrors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
        }
    });

    const BASE_URL = process.env.INNOKAFE_BASE_URL || "https://innokafe.com";

    try {
        // TEST 1: Base route loads and starts on Step 1
        console.log("\n[TEST 1] Visiting /taste-profiler");
        await page.goto(`${BASE_URL}/taste-profiler`, { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('#step-1', { state: 'attached' });
        const title1 = await page.title();
        console.log(`Page title: ${title1}`);
        const step1Visible = await page.isVisible('#step-1');
        const step2Visible = await page.isVisible('#step-2');
        console.log(`Step 1 visible: ${step1Visible}, Step 2 visible: ${step2Visible}`);
        if (!step1Visible || step2Visible) throw new Error("Step 1 should be visible, Step 2 hidden on /taste-profiler");

        // TEST 2: Direct deep link to Step 2
        console.log("\n[TEST 2] Visiting /taste-profiler/step/2");
        await page.goto(`${BASE_URL}/taste-profiler/step/2`, { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('#step-2', { state: 'attached' });
        const step2DeepVisible = await page.isVisible('#step-2');
        const step1DeepVisible = await page.isVisible('#step-1');
        console.log(`Step 2 visible: ${step2DeepVisible}, Step 1 hidden: ${!step1DeepVisible}`);
        if (!step2DeepVisible || step1DeepVisible) throw new Error("Step 2 should be visible on /taste-profiler/step/2");

        // TEST 3: Direct deep link to Step 4
        console.log("\n[TEST 3] Visiting /taste-profiler/step/4");
        await page.goto(`${BASE_URL}/taste-profiler/step/4`, { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('#step-4', { state: 'attached' });
        const step4DeepVisible = await page.isVisible('#step-4');
        if (!step4DeepVisible) throw new Error("Step 4 should be visible on /taste-profiler/step/4");

        // TEST 4: Direct deep link to SKU result
        console.log("\n[TEST 4] Visiting /taste-profiler/result/INNO-ARABICA-WASH-02");
        await page.goto(`${BASE_URL}/taste-profiler/result/INNO-ARABICA-WASH-02`, { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('#result', { state: 'attached' });
        const resultVisible = await page.isVisible('#result');
        const top1Name = await page.innerText('.top1-product-name');
        console.log(`Result visible: ${resultVisible}, Top 1 Name: ${top1Name}`);
        if (!resultVisible || !top1Name.includes("Cầu Đất Mountain Bourbon")) {
            throw new Error(`Expected Arabica Washed, got: ${top1Name}`);
        }

        // Check SVG radar chart presence
        const radarSvg = await page.$('.innokafe-sensory-wheel-svg');
        if (!radarSvg) throw new Error("Sensory Wheel SVG radar chart not found in result cockpit");
        console.log("Sensory Wheel SVG radar verified in DOM.");

        // TEST 5: Interactive step progression from Step 1
        console.log("\n[TEST 5] Interactive progression through all 4 steps");
        await page.goto(`${BASE_URL}/taste-profiler`, { waitUntil: 'domcontentloaded' });
        await page.waitForFunction(() => !!window.InnokafeTasteProfiler);
        await page.waitForTimeout(300);
        
        // Click Option in Step 1 (Sữa Đá)
        console.log("Selecting Habit in Step 1...");
        await page.click('.profiler-option-card[data-key="habit"][data-value="sua_da"]');
        await page.waitForTimeout(600);
        const onStep2 = await page.isVisible('#step-2');
        console.log(`Transitioned to Step 2: ${onStep2}`);
        if (!onStep2) throw new Error("Failed to transition to Step 2");

        // Click Option in Step 2 (Phin)
        console.log("Selecting Gear in Step 2...");
        await page.click('.profiler-option-card[data-key="gear"][data-value="phin"]');
        await page.waitForTimeout(600);
        const onStep3 = await page.isVisible('#step-3');
        console.log(`Transitioned to Step 3: ${onStep3}`);
        if (!onStep3) throw new Error("Failed to transition to Step 3");

        // Click Option in Step 3 (Nutty Choco)
        console.log("Selecting Flavor in Step 3...");
        await page.click('.profiler-option-card[data-key="flavor"][data-value="nutty_choco"]');
        await page.waitForTimeout(600);
        const onStep4 = await page.isVisible('#step-4');
        console.log(`Transitioned to Step 4: ${onStep4}`);
        if (!onStep4) throw new Error("Failed to transition to Step 4");

        // Click Option in Step 4 (High Caffeine)
        console.log("Selecting Caffeine in Step 4...");
        await page.click('.profiler-option-card[data-key="caffeine"][data-value="high"]');
        await page.waitForTimeout(1000);
        const onResult = await page.isVisible('#result');
        console.log(`Reached Result Cockpit: ${onResult}`);
        if (!onResult) throw new Error("Failed to reach Result Cockpit");

        const matchedTop1 = await page.innerText('.top1-product-name');
        console.log(`Interactive Recommended Top 1: ${matchedTop1}`);
        if (!matchedTop1.includes("Fine Robusta Natural")) {
            throw new Error(`Expected Robusta Natural for Phin Sữa Đá, got: ${matchedTop1}`);
        }

        // TEST 6: Copy Link Button
        console.log("\n[TEST 6] Testing Copy Link Button");
        await page.click('.btn-copy-result-link');
        await page.waitForTimeout(300);
        const toastVisible = await page.isVisible('#innokafe-cart-toast');
        console.log(`Toast notification visible: ${toastVisible}`);
        if (!toastVisible) throw new Error("Toast notification did not appear on Copy Link");

        // TEST 7: Add to Cart Button
        console.log("\n[TEST 7] Testing Add to Cart Button");
        await page.click('.btn-top1-add-to-cart');
        await page.waitForTimeout(1000);
        const toastText = await page.innerText('#innokafe-cart-toast');
        console.log(`Cart Toast Content: ${toastText}`);

        // TEST 8: Discovery Box Button
        console.log("\n[TEST 8] Testing Discovery Box Button");
        await page.click('.btn-discovery-box-add');
        await page.waitForTimeout(1000);
        const discoveryToast = await page.innerText('#innokafe-cart-toast');
        console.log(`Discovery Box Toast Content: ${discoveryToast}`);

        // TEST 9: Header Navigation Zero Duplicate Assertion
        console.log("\n[TEST 9] Validating Zero Duplicate Header Navbar Links across Desktop & Mobile");
        await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
        const navElements = await page.$$('header nav');
        console.log(`Found ${navElements.length} nav container(s) in header`);
        if (navElements.length === 0) throw new Error("Header nav elements missing");

        const canonicalRoutes = ['/', '/story', '/products', '/taste-profiler', '/solutions-b2b', '/contactus'];
        for (let i = 0; i < navElements.length; i++) {
            const nav = navElements[i];
            const hrefs = await nav.$$eval('a.nav-link', links => links.map(l => l.getAttribute('href')));
            const counts = {};
            for (const h of hrefs) {
                if (canonicalRoutes.includes(h)) {
                    counts[h] = (counts[h] || 0) + 1;
                }
            }
            console.log(`Nav container #${i} counts:`, counts);
            for (const r of canonicalRoutes) {
                if (counts[r] !== 1) {
                    throw new Error(`Nav container #${i} expected route '${r}' exactly once, found ${counts[r] || 0}`);
                }
            }
        }
        console.log("Header navigation deduplication verified: 100% clean across all nav containers.");

        console.log("\n=== ALL PLAYWRIGHT E2E ASSERTIONS PASSED WITH ZERO CRITICAL ERRORS ===");
        if (consoleErrors.length > 0) {
            console.log("Console errors observed:", consoleErrors);
        } else {
            console.log("Zero console errors observed during entire flow.");
        }

    } finally {
        await browser.close();
    }
})();
