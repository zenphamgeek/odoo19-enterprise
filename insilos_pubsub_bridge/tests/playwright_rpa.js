const { chromium } = require("playwright");
const { join } = require("path");
const { assert, authenticateAndAssert, collectFailures, writeFailureArtifacts } = require("../../../../tools/playwright_rpa");
const cases = require("./rpa_cases.json");

const BASE = process.env.INSILOS_BASE || "http://127.0.0.1:18069";
const DB = process.env.INSILOS_DB;
const USER = process.env.INSILOS_USER;
const PASS = process.env.INSILOS_PASSWORD;
if (!DB || !USER || !PASS) throw new Error("INSILOS_DB, INSILOS_USER and INSILOS_PASSWORD are required");

(async () => {
    const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await context.tracing.start({ screenshots: true, snapshots: true });
    const page = await context.newPage();
    const errors = collectFailures(page, ["net::ERR_ABORTED"]);
    const runId = process.env.RPA_RUN_ID;
    let activeCase = "RPA-PUBSUB-SETUP";
    let session;
    try {
        session = await authenticateAndAssert({ context, page, base: BASE, db: DB, user: USER, password: PASS });
        await page.waitForFunction(() => !!window.insilos?.__WOWL_DEBUG__?.root?.env?.services?.action, null, { timeout: 60000 });
        const rpc = (model, method, args = [], kwargs = {}) => page.evaluate(async ({ model, method, args, kwargs }) => {
            const response = await fetch("/web/dataset/call_kw", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { model, method, args, kwargs } }) });
            const body = await response.json();
            if (body.error) throw new Error(body.error.data?.message || body.error.message);
            return body.result;
        }, { model, method, args, kwargs });
        assert(cases.length === 2 && new Set(cases.map(item => item.case_id)).size === cases.length, "case registry must contain two unique cases");
        for (const item of cases) {
            activeCase = item.case_id;
            for (const key of ["case_id", "module_set", "risk", "roles", "company_mode", "seed", "entry", "steps", "oracles", "cleanup", "selectors"]) assert(item[key], `${item.case_id || "unknown"}: missing ${key}`);
            assert(item.entry.menu_xmlid.startsWith("insilos_pubsub_bridge."), `${item.case_id}: unstable menu selector`);
            assert(item.entry.action_xmlid.startsWith("insilos_pubsub_bridge."), `${item.case_id}: unstable action selector`);
        }
        assert(runId, "RPA_RUN_ID is required");
        const fixtureIds = await rpc("is.pubsub.event.log", "search", [[['trace_id', '=', runId]]]);
        assert(fixtureIds.length === 2, `expected two pre-seeded fixtures for ${runId}`);
        const [actionRef] = await rpc("is.model.data", "search_read", [[['module', '=', 'insilos_pubsub_bridge'], ['name', '=', 'action_pubsub_event_log']]], { fields: ["res_id"], limit: 1 });
        assert(actionRef?.res_id, "action XML ID not found");
        await page.evaluate(async actionId => window.insilos.__WOWL_DEBUG__.root.env.services.action.doAction(actionId), actionRef.res_id);
        const renderer = page.locator(".w_kanban_renderer, .w_list_renderer, .o_kanban_renderer, .o_list_renderer").first();
        await renderer.waitFor({ state: "visible", timeout: 60000 });
        const deepLink = page.url();
        assert(deepLink !== `${BASE}/insilos?debug=1&db=${encodeURIComponent(DB)}`, "action did not create a deep link");
        await page.reload({ waitUntil: "domcontentloaded" });
        await renderer.waitFor({ state: "visible", timeout: 60000 });
        assert(page.url() === deepLink, "reload did not preserve deep link");
        await page.goto(`${BASE}/insilos?debug=1&db=${encodeURIComponent(DB)}`, { waitUntil: "domcontentloaded" });
        await page.goto(deepLink, { waitUntil: "domcontentloaded" });
        await renderer.waitFor({ state: "visible", timeout: 60000 });
        await page.goBack({ waitUntil: "domcontentloaded" });
        assert(page.url() !== deepLink, "back navigation did not leave deep link");
        await page.goForward({ waitUntil: "domcontentloaded" });
        await renderer.waitFor({ state: "visible", timeout: 60000 });
        assert(page.url() === deepLink, "forward navigation did not restore deep link");
        const accessibilityFailures = await page.evaluate(() => {
            const visible = element => !!(element.offsetWidth || element.offsetHeight || element.getClientRects().length);
            const failures = [];
            if (!document.querySelector("main, [role='main']")) failures.push("main landmark missing");
            if (!document.querySelector("h1, h2, [role='heading'], .w_control_panel_breadcrumbs")) failures.push("page title missing");
            for (const element of document.querySelectorAll("button, a[href], input, select, textarea, [tabindex]")) {
                if (visible(element) && !element.matches(":disabled") && element.hasAttribute("tabindex") && element.tabIndex < 0 && !element.closest("[aria-hidden='true']")) failures.push(`not keyboard reachable: ${element.tagName}`);
                if (visible(element) && !element.matches(":disabled") && ["INPUT", "SELECT", "TEXTAREA"].includes(element.tagName) && !element.getAttribute("aria-label") && !element.getAttribute("placeholder") && !element.getAttribute("title") && !element.labels?.length) failures.push(`unlabelled control: ${element.getAttribute("name") || element.tagName}`);
            }
            return failures;
        });
        assert(accessibilityFailures.length === 0, accessibilityFailures.slice(0, 10).join("\n"));
        await page.keyboard.press("Tab");
        assert(await page.evaluate(() => document.activeElement !== document.body), "keyboard focus is not visible/reachable");
        const records = await rpc("is.pubsub.event.log", "read", [fixtureIds, ["event_id", "state", "producer", "target_model", "target_res_id"]]);
        assert(records.length === 2, "durable event ledger missing fixture records");
        assert(records.every(record => !record.target_model && !record.target_res_id), "notification/workflow fixture caused unexpected business mutation");
        assert(records.some(record => record.state === "processed") && records.some(record => record.state === "received"), "workflow states not persisted");
        assert(await page.getByText("Inbound Event Logs", { exact: true }).count(), "event-log journey did not open expected action");
        assert(errors.length === 0, errors.join("\n"));
        console.log(`PASS ${cases.map(item => item.case_id).join(", ")} db=${DB} uid=${session.uid}`);
        await context.tracing.stop();
    } catch (error) {
        await writeFailureArtifacts({ page, context, error, caseId: activeCase, db: DB, runId, role: "pubsub_manager", companyId: session?.user_companies?.current_company, traceId: runId, correlationId: runId, artifactDir: join(__dirname, "artifacts") });
        throw error;
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
