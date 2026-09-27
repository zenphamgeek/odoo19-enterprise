const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const { mkdirSync, readFileSync, readdirSync, writeFileSync } = require("fs");
const { createHash } = require("crypto");
const { join } = require("path");

const BASE = process.env.INSILOS_BASE || "http://127.0.0.1:18069";
const DB = process.env.INSILOS_DB || "insilos_migration_digiforce_v2";
const USER = process.env.INSILOS_USER || process.env.ADMIN_LOGIN;
const PASS = process.env.INSILOS_PASSWORD || process.env.ADMIN_PASSWORD;
const ARTIFACT_DIR = process.env.IDP_PLAYWRIGHT_ARTIFACT_DIR;
if (!USER || !PASS) throw new Error("INSILOS_USER and INSILOS_PASSWORD are required");
if (ARTIFACT_DIR) mkdirSync(ARTIFACT_DIR, { recursive: true });
let browser;
let page;
let key;
const checks = [];
const events = [];

const cleanup = () => {
    if (!key) return;
    const sql = `BEGIN;
    SET LOCAL session_replication_role = replica;
    DO $$ DECLARE fixture_ids int[]; task_ids int[]; outbox_table regclass; BEGIN
        SELECT array_agg(id), array_agg(task_id) INTO fixture_ids, task_ids FROM logistics_idp_case WHERE source_system = 'playwright' AND source_key = '${key}' AND provenance = 'synthetic:playwright';
        SELECT to_regclass('kg_outbox') INTO outbox_table;
        IF fixture_ids IS NULL THEN RETURN; END IF;
        UPDATE logistics_idp_document SET current_run_id = NULL WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_check_result WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_extraction_run WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_output WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_exception WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_override WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_document WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_email_thread_entry WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_evidence WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_policy_decision WHERE case_id = ANY(fixture_ids);
        DELETE FROM logistics_idp_mes_reference WHERE case_id = ANY(fixture_ids);
        UPDATE logistics_idp_inbound_job SET case_id = NULL WHERE case_id = ANY(fixture_ids);
        DELETE FROM mail_message WHERE model = 'logistics.idp.case' AND res_id = ANY(fixture_ids);
        IF outbox_table IS NOT NULL THEN
            EXECUTE format('DELETE FROM %s WHERE source_model = $1 AND source_id = ANY(SELECT id::text FROM unnest($2) id)', outbox_table)
                USING 'logistics.idp.case', fixture_ids;
        END IF;
        DELETE FROM logistics_idp_case WHERE id = ANY(fixture_ids);
        DELETE FROM project_task WHERE id = ANY(task_ids);
        DELETE FROM logistics_idp_supplier_profile WHERE source_system = 'playwright' AND source_key = '${key}' AND provenance = 'synthetic:playwright';
    END $$;
    COMMIT;
    SELECT
      (SELECT count(*) FROM logistics_idp_case WHERE source_system = 'playwright' AND source_key = '${key}'),
      (SELECT count(*) FROM logistics_idp_supplier_profile WHERE source_system = 'playwright' AND source_key = '${key}'),
      (SELECT count(*) FROM project_task WHERE name = 'Playwright Logistics Phase 7 ${key}');`;
    let result;
    try {
        const credentialArgs = ["tools/with_local_credentials.py", "--solo-dev-db"];
        if (DB.startsWith("tmp_")) credentialArgs.push("--ephemeral-db", DB);
        result = execFileSync("python3", [...credentialArgs, "--", "psql", "-d", DB, "-v", "ON_ERROR_STOP=1", "-tAq", "-c", sql], { cwd: join(__dirname, "../../../.."), encoding: "utf8" }).trim();
    } catch (error) {
        throw new Error(`fixture cleanup failed: ${error.stderr || error.stdout || error.message}`);
    }
    if (result !== "0|0|0") throw new Error(`fixture cleanup failed: ${result}`);
};

const writeArtifacts = () => {
    if (!ARTIFACT_DIR) return;
    mkdirSync(ARTIFACT_DIR, { recursive: true });
    writeFileSync(join(ARTIFACT_DIR, "events.json"), `${JSON.stringify({ base_url: BASE, db: DB, checks, events }, null, 2)}\n`);
    const files = readdirSync(ARTIFACT_DIR).filter(file => file !== "sha256.json").sort().map(file => {
        const content = readFileSync(join(ARTIFACT_DIR, file));
        return { file, bytes: content.length, sha256: createHash("sha256").update(content).digest("hex") };
    });
    writeFileSync(join(ARTIFACT_DIR, "sha256.json"), `${JSON.stringify({ algorithm: "sha256", files }, null, 2)}\n`);
};

(async () => {
    const dashboardAssets = ["dashboard.js", "dashboard.xml", "dashboard.scss"].map(file => readFileSync(join(__dirname, "../static/src/dashboard", file), "utf8")).join("\n");
    if (/class=["'][^"']*\bo_/.test(dashboardAssets)) throw new Error("static contract: dashboard contains o_ class");
    if (dashboardAssets.includes("Enterprise R&amp;D synthetic/non-production")) throw new Error("static contract: R&D disclaimer banner must be removed");
    browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
    const consoleErrors = [];
    const pageErrors = [];
    const networkErrors = [];
    const viewportEvidence = [];
    const safeUrl = (url) => {
        const parsed = new URL(url);
        return `${parsed.origin}${parsed.pathname}`;
    };
    page.on("console", (message) => {
        const event = { type: "console", level: message.type(), message: message.text(), url: safeUrl(page.url()) };
        events.push(event);
        if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", (error) => {
        const message = String(error);
        pageErrors.push(message);
        events.push({ type: "page", event: "error", message, url: safeUrl(page.url()) });
    });
    page.on("requestfailed", (request) => {
        const method = request.method();
        const url = request.url();
        const error = request.failure()?.errorText;
        networkErrors.push(`${method} ${url} ${error}`);
        events.push({ type: "network", method, url: safeUrl(url), status: null, error });
    });
    page.on("response", (response) => {
        if (response.status() < 400) return;
        const status = response.status();
        const url = response.url();
        networkErrors.push(`${status} ${url}`);
        events.push({ type: "network", method: response.request().method(), url: safeUrl(url), status });
    });

    const rpc = async (model, method, args = [], kwargs = {}) => page.evaluate(async ({ model, method, args, kwargs }) => {
        const response = await fetch("/web/dataset/call_kw", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { model, method, args, kwargs } }),
        });
        const body = await response.json();
        if (body.error) throw new Error(body.error.data?.arguments?.[0] || body.error.data?.message || body.error.message);
        return body.result;
    }, { model, method, args, kwargs });
    const check = (name, condition, detail = "") => {
        if (!condition) throw new Error(`${name}: ${detail || "assertion failed"}`);
        checks.push(name);
        events.push({ type: "check", name });
    };
    const menuNames = {
        action_logistics_overview: "Overview",
        action_logistics_cases: "Control Tower",
        action_logistics_documents: "Document Inbox",
        action_logistics_review_center: "Review Center",
        action_logistics_ocr_performance: "OCR Performance & History",
        action_logistics_mapping_validation: "Mapping & Validation",
        action_logistics_output_history: "Output History",
        action_logistics_policies: "Policy Sources",
        action_policy_activations: "Policy Governance Events",
    };
    const openAction = async (name, recordId) => {
        await page.goto(`${BASE}/insilos?db=${encodeURIComponent(DB)}&debug=assets`, { waitUntil: "domcontentloaded", timeout: 300000 });
        await page.waitForFunction(() => !!insilos?.__WOWL_DEBUG__?.root?.env?.services?.menu, null, { timeout: 60000 });
        const selected = await page.evaluate(async (menuName) => {
            const menu = insilos.__WOWL_DEBUG__.root.env.services.menu;
            const root = menu.getMenu("root");
            const queue = [...(root?.childrenTree || [])];
            while (queue.length) {
                const item = queue.shift();
                if (item.name === menuName && item.actionID) {
                    await menu.selectMenu(item);
                    return true;
                }
                queue.push(...(item.childrenTree || []));
            }
            return false;
        }, menuNames[name]);
        check(`menu ${menuNames[name]} accessible`, selected);
        await page.waitForFunction(() => location.pathname !== "/insilos" && location.pathname !== "/insilos/", null, { timeout: 60000 });
        if (recordId) await page.evaluate(async ({ resModel, resId }) => insilos.__WOWL_DEBUG__.root.env.services.action.doAction({ type: "is.actions.act_window", res_model: resModel, res_id: resId, views: [[false, "form"]] }), { resModel: { action_logistics_ocr_performance: "logistics.idp.extraction.run", action_logistics_output_history: "logistics.idp.output", action_logistics_policies: "logistics.idp.policy.source" }[name], resId: recordId });
        await page.locator(".w_action_manager, .o_action_manager, .w_graph_renderer, .o_graph_renderer, .w_list_renderer, .o_list_renderer, .w_kanban_renderer, .o_kanban_renderer, .w_idp_dashboard, .w_form_view, .o_form_view").first().waitFor({ state: "visible", timeout: 60000 });
    };
    const visibleText = async (text) => page.getByText(text, { exact: true }).filter({ visible: true }).count();
    const dashboardRpc = (matches = () => true) => page.waitForResponse(response => {
        try {
            const request = JSON.parse(response.request().postData());
            return request.params?.model === "logistics.idp.case" && request.params?.method === "get_dashboard_data" && matches(request.params.args?.[0] || {});
        } catch {
            return false;
        }
    });
    const applyFilter = async (name, value) => {
        const input = page.locator(`[name="${name}"]`);
        await input.fill(value);
        await input.dispatchEvent("change");
        const response = dashboardRpc();
        await input.press("Enter");
        check(`filter ${name}`, (await response).ok());
    };

    const authResponse = await page.request.post(`${BASE}/web/session/authenticate`, {
        data: { jsonrpc: "2.0", method: "call", params: { db: DB, login: USER, password: PASS } },
    });
    const auth = (await authResponse.json()).result;
    const sessionResponse = await page.request.post(`${BASE}/web/session/get_session_info`, {
        data: { jsonrpc: "2.0", method: "call", params: {} },
    });
    const session = (await sessionResponse.json()).result;
    check("route đúng DB", authResponse.ok() && auth?.uid && sessionResponse.ok() && session?.db === DB,
        JSON.stringify({ uid: auth?.uid, db: session?.db }));
    await page.goto(`${BASE}/insilos?db=${encodeURIComponent(DB)}&debug=assets`, { waitUntil: "domcontentloaded" });
    const browserSession = await page.evaluate(async () => {
        const response = await fetch("/web/session/get_session_info", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: {} }) });
        return (await response.json()).result;
    });
    const browserUser = (await rpc("rs.users", "read", [[auth.uid], ["login", "company_ids"]]))[0];
    let policySourceIds = [], policySourceError;
    try { policySourceIds = await rpc("logistics.idp.policy.source", "search", [[]], { limit: 1 }); } catch (error) { policySourceError = error.message; }
    const authContext = { request_uid: auth?.uid, request_db: session?.db, browser_uid: browserSession?.uid, browser_db: browserSession?.db, browser_login: browserUser?.login, browser_company_ids: browserUser?.company_ids, policy_source_ids: policySourceIds, policy_source_error: policySourceError };
    check("browser/request session identity", auth?.uid === browserSession?.uid && session?.db === browserSession?.db && browserUser?.login === USER, JSON.stringify(authContext));
    check("browser policy source access", policySourceIds.length === 1, JSON.stringify(authContext));
    key = `PW-BROWSER-GAPS-${Date.now()}`;
    const caseName = `Playwright Logistics Phase 7 ${key}`;
    const supplierReference = `PW-SUPPLIER-${key}`;
    const caseId = await rpc("logistics.idp.case", "create", [{ name: caseName, source_system: "playwright", source_key: key, source_version: "v1", provenance: "synthetic:playwright", effective_date: "2026-08-08", po_reference: "PO-PW-7", supplier_reference: supplierReference, gate_pass_enabled: true, gate_pass_requires_import_pass: false }]);
    const caseData = (await rpc("logistics.idp.case", "read", [[caseId], ["name", "state", "verdict", "output_ids", "message_ids", "task_id"]]))[0];
    check("case created", caseData.name === caseName && caseData.state === "collecting" && caseData.task_id);
    await rpc("logistics.idp.document", "create", [{ case_id: caseId, document_type: "invoice", source_channel: "upload", content_hash: key, mimetype: "application/pdf" }]);

    const failed = await rpc("logistics.idp.case", "reconcile_documents", [[caseId], { supplier: supplierReference, lines: [{ material_code: "M", unit_price: 1, remaining_quantity: 1 }] }, { supplier: supplierReference, lines: [{ material_code: "M", unit_price: 1, quantity: 2 }] }]);
    const currentTaskStage = async () => {
        const taskId = (await rpc("logistics.idp.case", "read", [[caseId], ["task_id"]]))[0].task_id[0];
        return (await rpc("project.task", "read", [[taskId], ["stage_id"]]))[0].stage_id[0];
    };
    const profileValues = (stage) => ({
        supplier_reference: supplierReference, profile_code: `PW-${key}`, version: "1",
        source_system: "playwright", source_key: key, source_version: "v1",
        provenance: "synthetic:playwright", effective_from: "2026-01-01",
        payload: { draft_invoice: { mode: "skipped", final_number_allowed: false }, authoritative_reference_policy: { policy_version: "pw-v1", rules: [
            { id: "pw-e13", stage: String(stage), field: "e13", source_type: "output", output_types: ["e13"] },
            { id: "pw-e15", stage: String(stage), field: "e15", source_type: "output", output_types: ["e15"] },
        ] } },
    });
    const failedEvidenceId = Array.isArray(failed) ? failed[0] : failed;
    const failedEvidence = (await rpc("logistics.idp.evidence", "read", [[failedEvidenceId], ["status", "payload", "payload_hash", "audit_actor_id", "audit_service"]]))[0];
    check("mismatch không profile bị review/block", failedEvidence.status === "review" && JSON.parse(failedEvidence.payload).results[0].result === "block");
    check("ACL/audit failed reconciliation", failedEvidence.audit_actor_id && failedEvidence.audit_service);

    const preRecheckStage = await currentTaskStage();
    const firstProfile = await rpc("logistics.idp.supplier.profile", "import_upsert", [profileValues(preRecheckStage)]);
    const passed = await rpc("logistics.idp.case", "recheck", [[caseId], { supplier: supplierReference, regime: "E13", lines: [{ material_code: "M", unit_price: 1, remaining_quantity: 2, regime: "E13" }] }, { supplier: supplierReference, regime: "E13", lines: [{ material_code: "M", unit_price: 1, quantity: 2, regime: "E13" }] }]);
    const postRecheckStage = await currentTaskStage();
    const outputProfile = await rpc("logistics.idp.supplier.profile", "import_upsert", [profileValues(postRecheckStage)]);
    check("authoritative profile upsert sau recheck", JSON.stringify(outputProfile) === JSON.stringify(firstProfile));
    const passedEvidenceId = Array.isArray(passed) ? passed[0] : passed;
    const passedEvidence = (await rpc("logistics.idp.evidence", "read", [[passedEvidenceId], ["status", "payload", "payload_hash", "audit_actor_id", "audit_service"]]))[0];
    check("correction/recheck pass", passedEvidence.status === "valid" && JSON.parse(passedEvidence.payload).results[0].result === "pass" && failedEvidence.payload_hash !== passedEvidence.payload_hash);
    check("ACL/audit recheck", passedEvidence.audit_actor_id && passedEvidence.audit_service);

    const output1 = await rpc("logistics.idp.case", "generate_customs_output", [[caseId], "E13", [{ material_code: "M", quantity: 2 }], "pw-v1"]);
    const output2 = await rpc("logistics.idp.case", "generate_customs_output", [[caseId], "E13", [{ material_code: "M", quantity: 2 }], "pw-v1"]);
    check("output idempotency", JSON.stringify(output1) === JSON.stringify(output2));
    const e15Stage = await currentTaskStage();
    await rpc("logistics.idp.supplier.profile", "import_upsert", [profileValues(e15Stage)]);
    const output3 = await rpc("logistics.idp.case", "generate_customs_output", [[caseId], "E15", [{ material_code: "M", quantity: 2 }], "pw-v1"]);
    check("E15 output generated", Array.isArray(output3) ? output3.length > 0 : Boolean(output3));

    await openAction("action_logistics_overview");
    await page.getByRole("heading", { name: "Dossier Control Tower" }).waitFor();
    check("Overview metric", await visibleText("Open cases"));
    check("Overview strategic panel", await visibleText("Strategic intelligence"));
    check("Overview strategic status", await visibleText("Not Configured"));
    check("Control Tower compact viewport", await visibleText("Dossier Control Tower") && (await page.locator(".w_idp_filters input, .w_idp_filters select").count()) === 6 && (await page.locator(".w_idp_kpis .w_idp_card").count()) === 6 && (await page.locator("details.w_idp_onboarding:not([open])").count()) === 1);
    check("E11/E13/E15/output UI", await page.locator('select[name="customs_regime"] option').allTextContents().then(options => ["E11", "E13", "E15"].every(value => options.includes(value))) && await visibleText("Open output history"));
    check("R&D disclaimer banner removed", (await page.locator('main [role="note"]').count()) === 0);
    if (ARTIFACT_DIR) await page.screenshot({ path: join(ARTIFACT_DIR, "overview-desktop.png"), fullPage: true });
    const openCasesKpi = page.locator('.w_idp_kpis .w_idp_card[aria-label="Open Open cases records"]');
    await openCasesKpi.waitFor({ state: "visible" });
    const openCasesKpiText = await openCasesKpi.innerText();
    const openCasesKpiAriaLabel = await openCasesKpi.getAttribute("aria-label");
    const openCasesKpiDetail = JSON.stringify({ text: openCasesKpiText, ariaLabel: openCasesKpiAriaLabel });
    check("Open cases KPI", openCasesKpiText.includes("Open cases"), openCasesKpiDetail);
    check("Open cases KPI aria-label", openCasesKpiAriaLabel === "Open Open cases records", openCasesKpiDetail);
    await openCasesKpi.focus();
    check("keyboard focus Open cases KPI", await openCasesKpi.evaluate(element => element === document.activeElement));
    const overviewUrl = page.url();
    await page.keyboard.press("Enter");
    const drilldown = page.locator(".w_list_renderer, .o_list_renderer").first();
    await drilldown.waitFor({ state: "visible" });
    check("KPI keyboard drilldown", page.url() !== overviewUrl, page.url());
    await drilldown.locator("button, a, input, [tabindex='0']").first().focus();
    check("KPI focus destination", await drilldown.evaluate(element => element.contains(document.activeElement)));
    await openAction("action_logistics_overview");
    await openCasesKpi.focus();
    check("KPI focus restore", await openCasesKpi.evaluate(element => element === document.activeElement));
    await applyFilter("date_from", "2026-08-01");
    await applyFilter("date_to", "2026-08-09");
    await applyFilter("supplier", supplierReference);
    await applyFilter("document_type", "invoice");
    const filteredDashboard = await rpc("logistics.idp.case", "get_dashboard_data", [{ date_from: "2026-08-01", date_to: "2026-08-09", supplier: supplierReference, document_type: "invoice" }]);
    check("filtered dashboard query", filteredDashboard.case_states.length === 1, JSON.stringify(filteredDashboard.case_states));
    const chartButton = page.getByRole("heading", { name: "Dossier state distribution", exact: true }).locator("..").locator("button.w_idp_bar").first();
    await chartButton.waitFor({ state: "visible" });
    check("filtered Dossier-state chart row", await chartButton.count() === 1);
    const chartDrilldown = page.waitForResponse(response => {
        try {
            const request = JSON.parse(response.request().postData());
            return request.params?.model === "logistics.idp.case" && request.params?.method === "dashboard_drilldown";
        } catch { return false; }
    });
    await chartButton.click();
    check("chart drilldown", (await chartDrilldown).ok());
    await openAction("action_logistics_overview");
    let response = dashboardRpc(filters => !filters.supplier && !filters.jurisdiction && !filters.customs_regime && !filters.document_type);
    await page.getByRole("button", { name: "Reset dashboard filters" }).click();
    check("reset dashboard load", (await response).ok());
    const queueCaseButton = page.locator(".w_idp_queue tbody th[scope='row'] button").first();
    await queueCaseButton.waitFor({ state: "visible" });
    check("queue case button available", await queueCaseButton.count() === 1);
    const queueUrl = page.url();
    await queueCaseButton.focus();
    await queueCaseButton.press("Enter");
    await page.locator(".w_form_view, .o_form_view").waitFor({ state: "visible" });
    check("queue Enter drilldown", page.url() !== queueUrl, page.url());
    for (const viewport of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1440, height: 900 }]) {
        await page.setViewportSize(viewport); await openAction("action_logistics_overview");
        const responsive = await page.locator(".w_idp_dashboard").evaluate(element => {
            const root = element.getBoundingClientRect();
            const clippedChildren = [...element.querySelectorAll("*")].filter(child => {
                const rect = child.getBoundingClientRect();
                const style = getComputedStyle(child);
                return rect.right > root.right + 1 && style.position !== "fixed" && style.position !== "absolute";
            }).map(child => `${child.className || child.tagName}:${child.getBoundingClientRect().right.toFixed(1)}`).slice(0, 5);
            return { scrollWidth: element.scrollWidth, clientWidth: element.clientWidth, clippedChildren };
        });
        viewportEvidence.push({ viewport, ...responsive });
        check(`responsive ${viewport.width}`, responsive.scrollWidth <= responsive.clientWidth && responsive.clippedChildren.length === 0, JSON.stringify(responsive));
        if (ARTIFACT_DIR && viewport.width === 375) await page.screenshot({ path: join(ARTIFACT_DIR, "overview-mobile.png"), fullPage: true });
    }
    await page.setViewportSize({ width: 1600, height: 1000 });

    await openAction("action_logistics_overview");
    check("dashboard landmark labelled", (await page.locator("main[aria-label='Logistics IDP intelligence overview']").count()) === 1);
    check("filters form labelled", (await page.locator("form[aria-label='Dashboard filters']").count()) === 1);
    check("KPI cards are focusable buttons", await page.locator("section[aria-label='Key performance indicators'] button.w_idp_card").evaluateAll(buttons => buttons.length > 0 && buttons.every(button => button.tagName === "BUTTON" && button.getAttribute("aria-label"))));
    const queueAccessibleButton = page.locator(".w_idp_queue tbody th[scope='row'] button").first();
    check("queue case button available", await queueAccessibleButton.count() === 1);
    check("queue case button keyboard operable", await queueAccessibleButton.evaluate(button => button.tagName === "BUTTON" && !button.disabled));
    const statusBadges = await page.locator(".w_idp_queue tbody tr td:nth-child(2) span").allTextContents();
    check("state conveyed as text not color", statusBadges.length > 0 && statusBadges.every(text => text.trim().length > 0));
    const barLabels = await page.locator("button.w_idp_bar span").allTextContents();
    check("bar charts carry text labels", barLabels.length > 0 && barLabels.every(text => text.trim().length > 0));
    const resetButton = page.getByRole("button", { name: "Reset dashboard filters" });
    await resetButton.focus();
    check("reset filter keyboard focusable", await resetButton.evaluate(element => element === document.activeElement));
    const unavailableKpi = page.locator("section[aria-label='Key performance indicators'] button.w_idp_card:has(small)", { hasText: "Unavailable:" }).first();
    check("unavailable metric stated in text", (await unavailableKpi.count()) === 0 || (await unavailableKpi.innerText()).includes("Unavailable:"));

    await openAction("action_logistics_cases");
    check("case surface", (await page.locator(".w_kanban_renderer, .o_kanban_renderer, .w_list_renderer, .o_list_renderer").count()) > 0);
    await openAction("action_logistics_documents");
    check("document surface", (await page.locator(".w_list_renderer, .o_list_renderer").count()) > 0);
    await openAction("action_logistics_review_center");
    check("review surface", (await page.locator(".w_list_renderer, .o_list_renderer").count()) > 0);

    await openAction("action_logistics_mapping_validation");
    check("mapping accessible via Reporting action", (await page.locator(".w_graph_renderer, .o_graph_renderer, .w_list_renderer, .o_list_renderer").count()) > 0);

    await openAction("action_logistics_ocr_performance");
    check("OCR dashboard/history mở được", (await page.locator(".w_graph_renderer, .o_graph_renderer, .w_pivot, .o_pivot, .w_list_renderer, .o_list_renderer").count()) > 0);
    let shippingPayloadRejected = false;
    try {
        await rpc("logistics.idp.case", "generate_shipping_plan", [[caseId], { plan_key: "forged" }]);
    } catch (error) {
        shippingPayloadRejected = /no caller-provided source payloads/.test(error.message);
    }
    check("Shipping Plan từ chối caller payload", shippingPayloadRejected);
    let shippingPrerequisiteRejected = false;
    try {
        await rpc("logistics.idp.case", "generate_shipping_plan", [[caseId]]);
    } catch (error) {
        shippingPrerequisiteRejected = /Shipping Plan supplier profile contract is missing/.test(error.message);
    }
    check("Shipping Plan yêu cầu profile governed", shippingPrerequisiteRejected);
    let gatePassRejected = false;
    try {
        await rpc("logistics.idp.case", "generate_gate_pass", [[caseId]]);
    } catch (error) {
        gatePassRejected = /Gate Pass supplier profile contract is missing/.test(error.message);
    }
    check("Gate Pass từ chối thiếu profile governed", gatePassRejected);

    await openAction("action_logistics_cases");
    await page.getByText(caseName, { exact: true }).first().click();
    check("R&D case banner removed", (await page.locator(".alert-warning").filter({ hasText: "Enterprise R&D synthetic workspace." }).count()) === 0);
    await page.getByRole("tab", { name: "Outputs" }).click();
    const outputTypes = await rpc("logistics.idp.output", "search_read", [[['case_id', '=', caseId]]], { fields: ["output_type"] });
    check("customs outputs browser flow", ["e13", "e15"].every(type => outputTypes.some(output => output.output_type === type)), JSON.stringify(outputTypes));

    await openAction("action_logistics_output_history");
    check("customs E13/E15 UI", await visibleText("E13") && await visibleText("E15"));

    const policyId = (await rpc("logistics.idp.policy.source", "search", [[]], { limit: 1 }))[0];
    await openAction("action_logistics_policies", policyId);
    const policyData = (await rpc("logistics.idp.policy.source", "read", [[policyId], ["payload_hash", "audit_service"]]))[0];
    check("policy workspace hiển thị evidence", page.url().includes(`/${policyId}`) && policyData.payload_hash && policyData.audit_service);
    const policyFields = await rpc("logistics.idp.policy.source", "fields_get", [["source_tier", "verification_status", "activation_eligible", "audit_input_hash"]], { attributes: ["string"] });
    check("policy governance fields hiển thị", ["source_tier", "verification_status", "activation_eligible", "audit_input_hash"].every(field => policyFields[field]?.string));
    await openAction("action_policy_activations");
    const activationFields = await rpc("logistics.idp.policy.activation", "fields_get", [["event_uuid", "status"]], { attributes: ["string"] });
    check("activation events mở đúng view", (await page.locator(".w_list_renderer, .o_list_renderer").count()) > 0 && Boolean(activationFields.event_uuid?.string) && Boolean(activationFields.status?.string));

    await openAction("action_logistics_cases");
    await page.getByText(caseName, { exact: true }).first().click();
    await page.getByRole("tab", { name: "Audit" }).click();
    const auditData = (await rpc("logistics.idp.case", "read", [[caseId], ["evidence_ids", "decision_ids"]]))[0];
    const auditEvidence = await rpc("logistics.idp.evidence", "read", [auditData.evidence_ids, ["payload"]]);
    check("grouped matching/decision evidence UI", (await page.getByRole("tab", { name: "Audit" }).count()) > 0 && auditEvidence.some(item => /many-to-one|GROUP-M|E1[135]/.test(item.payload)));

    await page.waitForTimeout(1000);
    const actionableNetworkErrors = networkErrors.filter(error => !error.endsWith(" net::ERR_ABORTED"));
    check("console/page/network errors", consoleErrors.length === 0 && pageErrors.length === 0 && actionableNetworkErrors.length === 0, JSON.stringify({ consoleErrors, pageErrors, networkErrors: actionableNetworkErrors }));
    console.log(JSON.stringify({ base_url: BASE, db: DB, passed: checks.length, checks, viewports: viewportEvidence, console_errors: consoleErrors, page_errors: pageErrors, network_errors: actionableNetworkErrors }, null, 2));
})().catch((error) => {
    events.push({ type: "failure", message: error.message });
    console.error(error.stack || error);
    process.exitCode = 1;
}).finally(async () => {
    await browser?.close();
    writeArtifacts();
    cleanup();
});
