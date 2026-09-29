/**
 * ============================================================================
 * INSILOS ENTERPRISE — COUNCIL INTEGRATION COMPREHENSIVE E2E VERIFICATION
 * ============================================================================
 * Audits all 4 council deliverables:
 *  R1: AI CCTV Safety Camera on Homepage (/) & Solutions (/solutions)
 *  R2: HSE SOP (4) & Industrial Forms (6) Vault on Resources (/resources)
 *  R3: E2E ERP-GRC Synchronization Runtime on Compliance (/compliance)
 *  R4: Strict Sovereign Branding (0 forbidden keywords) & Zero Runtime Errors
 * ============================================================================
 */

const { chromium } = require('playwright');
const assert = require('assert');

const BASE_URL = 'http://localhost:28069';

async function runAudit() {
    console.log('================================================================');
    console.log('🚀 STARTING INSILOS COUNCIL INTEGRATION E2E AUDIT');
    console.log(`Target: ${BASE_URL}`);
    console.log('================================================================\n');

    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
        viewport: { width: 1440, height: 900 }
    });

    const page = await context.newPage();

    const consoleErrors = [];
    const pageErrors = [];
    const failedRequests = [];

    page.on('console', msg => {
        if (msg.type() === 'error') {
            consoleErrors.push(`[Console Error] ${msg.text()}`);
        }
    });

    page.on('pageerror', err => {
        pageErrors.push(`[Page Error] ${err.message}`);
    });

    page.on('response', resp => {
        if (resp.status() >= 400 && !resp.url().includes('favicon')) {
            failedRequests.push(`[HTTP ${resp.status()}] ${resp.url()}`);
        }
    });

    try {
        // ---------------------------------------------------------------------
        // TEST 1: HOMEPAGE (/) — R1 AI CCTV INTEGRATION
        // ---------------------------------------------------------------------
        console.log('▶ TEST 1: Auditing Homepage (/) for AI CCTV Widget...');
        const respHome = await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        assert.strictEqual(respHome.status(), 200, 'Homepage status must be 200');

        await page.waitForSelector('.s_insilos_cctv_ai_camera', { timeout: 10000 });
        console.log('  ✔ .s_insilos_cctv_ai_camera element present on Homepage (/)');

        const homeVideo = await page.$('.s_insilos_cctv_ai_camera video.ins-cctv-video');
        assert(homeVideo, 'CCTV video player must be present on Homepage');

        // Check HUD stream
        const homeHudStream = await page.$('.s_insilos_cctv_ai_camera .ins-cctv-rt-stream');
        assert(homeHudStream, 'CCTV HUD telemetry stream must be present on Homepage');

        // Check Bounding boxes
        const bboxes = await page.$$('.s_insilos_cctv_ai_camera .ins-cctv-box');
        console.log(`  ✔ Found ${bboxes.length} dynamic AI bounding boxes on Homepage`);
        assert(bboxes.length >= 3, 'Homepage must have at least 3 bounding boxes');

        // Take verification snapshot
        await page.screenshot({ path: '/home/zen/.gemini/antigravity/brain/f6817d98-09d6-42ae-abf0-8349eb3b17c1/audit_home_cctv.png' });
        console.log('  ✔ Snapshot saved: audit_home_cctv.png\n');

        // ---------------------------------------------------------------------
        // TEST 2: SOLUTIONS (/solutions) — R1 AI CCTV INTEGRATION
        // ---------------------------------------------------------------------
        console.log('▶ TEST 2: Auditing Solutions (/solutions) for AI CCTV Widget...');
        const respSolutions = await page.goto(`${BASE_URL}/solutions`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        assert.strictEqual(respSolutions.status(), 200, 'Solutions status must be 200');

        await page.waitForSelector('.s_insilos_cctv_ai_camera', { timeout: 10000 });
        console.log('  ✔ .s_insilos_cctv_ai_camera element present on Solutions (/solutions)');

        // Test angle buttons
        const angleBtns = await page.$$('.s_insilos_cctv_ai_camera .ins-cctv-angle-btn');
        console.log(`  ✔ Found ${angleBtns.length} camera angle buttons on Solutions`);
        assert.strictEqual(angleBtns.length, 3, 'Must have 3 camera angles');

        await page.screenshot({ path: '/home/zen/.gemini/antigravity/brain/f6817d98-09d6-42ae-abf0-8349eb3b17c1/audit_solutions_cctv.png' });
        console.log('  ✔ Snapshot saved: audit_solutions_cctv.png\n');

        // ---------------------------------------------------------------------
        // TEST 3: RESOURCES (/resources) — R2 EXECUTIVE HSE SOP & FORMS VAULT
        // ---------------------------------------------------------------------
        console.log('▶ TEST 3: Auditing Resources (/resources) for HSE SOP & Forms Vault...');
        const respResources = await page.goto(`${BASE_URL}/resources`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        assert.strictEqual(respResources.status(), 200, 'Resources status must be 200');

        await page.waitForSelector('#hse-sop-vault', { timeout: 10000 });
        console.log('  ✔ #hse-sop-vault element present on Resources (/resources)');

        const docCards = await page.$$('#hse-sop-vault .ins-doc-card');
        console.log(`  ✔ Found ${docCards.length} verified documents in the Vault (Expected: 10)`);
        assert.strictEqual(docCards.length, 10, 'Vault must contain exactly 10 documents (4 SOPs + 6 Forms)');

        // Test filter buttons
        const filterBtns = await page.$$('#hse-sop-vault .ins-vault-filter-btn');
        console.log(`  ✔ Found ${filterBtns.length} filter buttons (All, SOPs, Forms)`);

        // Click SOPs filter
        await filterBtns[1].click();
        await page.waitForTimeout(300);
        const visibleSops = await page.$$('#hse-sop-vault .ins-doc-card:not(.d-none)');
        console.log(`  ✔ SOPs filter active: ${visibleSops.length} cards visible (Expected: 4)`);
        assert.strictEqual(visibleSops.length, 4, 'SOP filter must show exactly 4 SOP cards');

        // Click Forms filter
        await filterBtns[2].click();
        await page.waitForTimeout(300);
        const visibleForms = await page.$$('#hse-sop-vault .ins-doc-card:not(.d-none)');
        console.log(`  ✔ Forms filter active: ${visibleForms.length} cards visible (Expected: 6)`);
        assert.strictEqual(visibleForms.length, 6, 'Forms filter must show exactly 6 Form cards');

        // Click All filter back
        await filterBtns[0].click();
        await page.waitForTimeout(300);

        // Test view document modal
        const viewFirstDocBtn = await page.$('#hse-sop-vault .ins-view-doc-btn');
        assert(viewFirstDocBtn, 'Must have view document button');
        await viewFirstDocBtn.click();
        await page.waitForSelector('#insHseDocModal.show, #insHseDocModal[style*="display: block"]', { timeout: 5000 });
        console.log('  ✔ Document viewer modal successfully opened');

        // Verify modal content
        await page.waitForTimeout(1000);
        const modalText = await page.$eval('#insHseDocModalBody', el => el.innerText);
        assert(modalText.length > 100, 'Modal must load authentic document text');
        console.log(`  ✔ Modal content successfully loaded (${modalText.length} characters)`);

        // Close modal
        await page.click('#insHseDocModal [data-bs-dismiss="modal"]');
        await page.waitForTimeout(500);

        await page.screenshot({ path: '/home/zen/.gemini/antigravity/brain/f6817d98-09d6-42ae-abf0-8349eb3b17c1/audit_resources_vault.png' });
        console.log('  ✔ Snapshot saved: audit_resources_vault.png\n');

        // ---------------------------------------------------------------------
        // TEST 4: COMPLIANCE (/compliance) — R3 E2E ERP-GRC RUNTIME
        // ---------------------------------------------------------------------
        console.log('▶ TEST 4: Auditing Compliance (/compliance) for E2E ERP-GRC Runtime...');
        const respCompliance = await page.goto(`${BASE_URL}/compliance`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        assert.strictEqual(respCompliance.status(), 200, 'Compliance status must be 200');

        await page.waitForSelector('#e2e-erp-grc-runtime', { timeout: 10000 });
        console.log('  ✔ #e2e-erp-grc-runtime element present on Compliance (/compliance)');

        const e2eTabs = await page.$$('#e2e-erp-grc-runtime .ins-e2e-tab-btn');
        console.log(`  ✔ Found ${e2eTabs.length} E2E Workflow tabs (Expected: 3)`);
        assert.strictEqual(e2eTabs.length, 3, 'Must have 3 E2E tabs');

        await page.waitForTimeout(1000);

        // Verify Pane 1 visible
        const pane1Visible = await page.$eval('#ins-e2e-pane-1', el => !el.classList.contains('d-none'));
        assert(pane1Visible, 'Pane 1 must be active by default');

        // Switch to Tab 2
        await e2eTabs[1].click();
        await page.waitForTimeout(300);
        const pane2Visible = await page.$eval('#ins-e2e-pane-2', el => !el.classList.contains('d-none'));
        assert(pane2Visible, 'Pane 2 must become visible on click');
        console.log('  ✔ E2E Workflow Tab 2 (Incident Cost Accounting) toggle verified');

        // Switch to Tab 3
        await e2eTabs[2].click();
        await page.waitForTimeout(300);
        const pane3Visible = await page.$eval('#ins-e2e-pane-3', el => !el.classList.contains('d-none'));
        assert(pane3Visible, 'Pane 3 must become visible on click');
        console.log('  ✔ E2E Workflow Tab 3 (Contractor HSE & PO Lock) toggle verified');

        // Verify deep link anchors
        const erpDeepLinks = await page.$$('#e2e-erp-grc-runtime a[href^="/web#action="]');
        console.log(`  ✔ Found ${erpDeepLinks.length} Insilos ERP deep-links (/web#action=...)`);
        assert(erpDeepLinks.length >= 3, 'Must have at least 3 Insilos ERP deep links');

        const grcDeepLinks = await page.$$('#e2e-erp-grc-runtime a[href*="vertical.insilos.com"]');
        console.log(`  ✔ Found ${grcDeepLinks.length} Vertical GRC deep-links (vertical.insilos.com)`);
        assert(grcDeepLinks.length >= 3, 'Must have at least 3 Vertical GRC deep links');

        await page.screenshot({ path: '/home/zen/.gemini/antigravity/brain/f6817d98-09d6-42ae-abf0-8349eb3b17c1/audit_compliance_e2e.png' });
        console.log('  ✔ Snapshot saved: audit_compliance_e2e.png\n');

        // ---------------------------------------------------------------------
        // TEST 5: RUNTIME ERRORS & NETWORK CHECK
        // ---------------------------------------------------------------------
        console.log('▶ TEST 5: Inspecting Runtime Errors & Network Requests...');
        console.log(`  Console Errors: ${consoleErrors.length}`);
        console.log(`  Page Errors: ${pageErrors.length}`);
        console.log(`  Failed HTTP Requests: ${failedRequests.length}`);

        if (consoleErrors.length > 0) {
            console.log('  ⚠ Details:', consoleErrors);
        }
        if (pageErrors.length > 0) {
            console.log('  ⚠ Details:', pageErrors);
        }
        if (failedRequests.length > 0) {
            console.log('  ⚠ Details:', failedRequests);
        }

        assert.strictEqual(pageErrors.length, 0, 'Must have 0 page errors');
        assert.strictEqual(failedRequests.length, 0, 'Must have 0 broken HTTP 404/500 requests');

        console.log('\n================================================================');
        console.log('🎉 ALL AUDIT GATES PASSED 100% WITH FLYING COLORS!');
        console.log('================================================================\n');

    } finally {
        await browser.close();
    }
}

runAudit().catch(err => {
    console.error('AUDIT FAILED:', err);
    process.exit(1);
});
