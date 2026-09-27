import { expect, test } from '@odoo/hoot';
import { animationFrame, Deferred, mockDate } from '@odoo/hoot-mock';
import {
    contains,
    mockService,
    mountWithCleanup,
} from '@web/../tests/web_test_helpers';
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { LogisticsIdpDashboard } from "@insilos_logistics_idp/dashboard/dashboard";

defineMailModels();

test("chart geometry handles empty, singleton and ranked aggregates", () => {
    const chart = LogisticsIdpDashboard.prototype;
    const rows = [{ __count: 2 }, { __count: 6 }];
    expect(chart.total(rows)).toBe(8);
    expect(chart.chartRows(rows, "supplier")[0].__count).toBe(6);
    expect(rows[0].__count).toBe(2);
    expect(chart.lineX(0, [rows[0]])).toBe(300);
    expect(chart.linePoints([])).toBe("");
    expect(chart.donutStyle([])).toBe("background: #e6edf5");
    expect(chart.donutStyle(rows)).toBe("background: conic-gradient(#1764ad 0% 25%,#008477 25% 100%)");
});

const DATA = {
    metrics: {
        received_today: { value: 12, delta: 2, available: true },
        processed_today: { value: 7, delta: 1, available: true },
        waiting_supplier: { value: null, delta: null, available: false },
        duplicate_detected: { value: 3, delta: 1, available: true },
        overdue_import_declaration_cases: { value: null, delta: null, available: false, contract: { formula: "No reliable due-date relation links an import declaration to its case." } },
        low_confidence_extraction_queue: { value: null, delta: null, available: false, contract: { formula: "No governed dashboard threshold identifies low-confidence runs." } },
        average_processing_duration: { value: null, delta: null, available: false, contract: { formula: "Case completion timestamps are not stored." } },
        ai_credits_per_document_case: { value: null, delta: null, available: false, contract: { formula: "No exact ORM charge-to-document/case relation exists." } },
    },
    onboarding: { closed: false, close_model: "onboarding.onboarding", close_method: "action_close_panel_logistics_idp", steps: [
        { id: 1, title: "Receive dossier", description: "Triage dossiers", state: "not_done", action: "action_open_logistics_intake" },
        { id: 2, title: "Collect document set", description: "Collect evidence", state: "not_done", action: "action_open_logistics_collecting" },
        { id: 3, title: "Classify and extract", description: "Process documents", state: "not_done", action: "action_open_logistics_processing" },
        { id: 4, title: "Review and compliance", description: "Review facts", state: "not_done", action: "action_open_logistics_review" },
        { id: 5, title: "Resolve exceptions", description: "Handle blocks", state: "not_done", action: "action_open_logistics_exceptions" },
        { id: 6, title: "Outputs and completion", description: "Complete dossiers", state: "not_done", action: "action_open_logistics_completion" },
    ] },
    case_states: [{ state: "review", __count: 1 }], document_throughput: [], verdicts: [], customs_regimes: [{ output_type: "e11", __count: 1 }],
    document_types: [{ document_type: "invoice", __count: 2 }], source_mix: [{ source_channel: "email", __count: 2 }],
    exceptions: [{ exception_type: "price", __count: 2 }], exception_severity: [{ severity: "high", __count: 2 }],
    exception_states: [{ state: "open", __count: 2 }], top_suppliers: [{ supplier_reference: "SUP-1", __count: 2 }],
    mapping_exceptions: [],
    ocr: [{ provider: "fixture-provider", __count: 2, confidence: 0.85, duration_seconds: 3.5, page_count: 5 }],
    ocr_by_model: [{ model_version: "fixture-model", __count: 2 }],
    ocr_by_status: [{ status: "review", __count: 1 }],
    live_queue: [{ id: 42, name: "CASE-42", state: "review", severity: "high",
        next_action: "Verify invoice", owner_id: false, po_reference: false, shipment_reference: false,
        document_count: 1, check_count: 2, output_count: 0, verdict: "review", sla_deadline: false }],
};

function mountDashboard(data = DATA) {
    const actions = [];
    const calls = [];
    if (data.onboarding) data.onboarding.closed = false;
    mockService("orm", {
        call(model, method, args) {
            calls.push({ model, method, args });
            if (model === "onboarding.onboarding.step") {
                return { type: "is.actions.act_window", res_model: "logistics.idp.case" };
            }
            if (model === "onboarding.onboarding") return false;
            expect(model).toBe("logistics.idp.case");
            if (method === "get_dashboard_data") return typeof data === "function" ? data() : data;
            return { type: "is.actions.act_window", res_model: model, res_id: args[2] };
        },
    });
    mockService("action", { doAction: (action) => actions.push(action) });
    return mountWithCleanup(LogisticsIdpDashboard, { props: { action: {} } }).then((component) => ({ actions, calls, component }));
}

test("dashboard renders numeric, unavailable and strategic states accessibly", async () => {
    await mountDashboard();
    await animationFrame();

    expect('[aria-label="Logistics IDP intelligence overview"]').toHaveCount(1);
    expect("h1").toHaveText("Dossier Control Tower");
    expect('[aria-label="Key performance indicators"]').toHaveCount(1);
    expect('.w_idp_kpis .w_idp_card').toHaveCount(6);
    expect('[aria-label="Open Open cases records"] strong').toHaveText("—");
    expect('[aria-label="Open Needs review records"] strong').toHaveText("—");
    expect('[aria-label="Open Compliance blocks records"] strong').toHaveText("—");
    expect('[aria-label="Open SLA overdue records"] strong').toHaveText("—");
    expect('[aria-label="Open Waiting for supplier records"] strong').toHaveText("Not Available");
    expect('[aria-label="Open Documents processed today records"] strong').toHaveText("7");
    expect(".w_idp_strategic strong").toHaveText("Not Configured");
    expect('[aria-label="Reset dashboard filters"]').toHaveCount(1);
    expect("details.w_idp_onboarding summary").toHaveText(/Standard dossier workflow/);
    for (const [index, text] of ["Dossier", "State", "Severity", "Next action", "Documents / checks / outputs", "Owner", "SLA"].entries()) {
        expect(`.w_idp_queue thead th:nth-child(${index + 1})`).toHaveText(text);
    }
    expect(".w_idp_queue tbody th[scope='row']").toHaveText("CASE-42");
    for (const [index, text] of ["review", "high", "Verify invoice", "1 / 2 / 0", "Unspecified", "—"].entries()) {
        expect(`.w_idp_queue tbody tr td:nth-child(${index + 2})`).toHaveText(text);
    }
});

test("initial RPC uses local calendar dates across UTC+7 boundary", async () => {
    mockDate("2024-02-29 17:30:00", +7);
    const { calls } = await mountDashboard();
    await animationFrame();

    expect(calls[0]).toMatchObject({
        model: "logistics.idp.case", method: "get_dashboard_data", args: [{
            date_from: "2024-02-01", date_to: "2024-03-01",
        }],
    });
});

test("filters apply only on submit and reset remains immediate", async () => {
    const { calls } = await mountDashboard();
    await animationFrame();

    expect('[aria-label="Dashboard filters"] button[type="submit"]').toHaveText("Apply");
    await contains('select[name="customs_regime"]').select("E13");
    expect(calls).toHaveLength(1);
    await contains('[aria-label="Dashboard filters"] button[type="submit"]').click();
    expect(calls.at(-1)).toEqual({
        model: "logistics.idp.case", method: "get_dashboard_data", args: [{ ...calls[0].args[0], customs_regime: "E13" }],
    });
    await contains('[aria-label="Reset dashboard filters"]').click();
    expect(calls).toHaveLength(3);
    expect(calls.at(-1).args[0].customs_regime).toBe(undefined);
});

test.tags("desktop");
test("deferred dashboard load cannot update state after destroy", async () => {
    let deferred;
    const { component } = await mountDashboard(() => deferred || DATA);
    deferred = new Deferred();
    component.load();
    component.__owl__.destroy();
    deferred.resolve({ ...DATA, live_queue: [] });
    await Promise.resolve();
    await Promise.resolve();

    expect(component.state.data.live_queue[0].name).toBe("CASE-42");
    expect(component.state.loading).toBe(true);
});

test("legacy partial payload renders without OwlError", async () => {
    await mountDashboard({ metrics: { received_today: { value: 1, delta: null } } });
    await animationFrame();

    expect("h1").toHaveText("Dossier Control Tower");
    expect(".w_idp_queue tbody tr").toHaveCount(0);
    expect(".w_idp_queue p").toHaveText("Queue empty.");
    expect(".w_idp_bar").toHaveCount(0);
});

test("native onboarding step RPC and close behavior remain available", async () => {
    const { actions, calls } = await mountDashboard();
    await animationFrame();
    expect(".w_onboarding_step").toHaveCount(6);
    await contains(".w_onboarding_step").click();
    expect(calls.at(-1)).toEqual({
        model: "onboarding.onboarding.step", method: "action_open_logistics_intake", args: [],
    });
    expect(actions[0].res_model).toBe("logistics.idp.case");
    await contains("button", { text: "Close workflow guide" }).click();
    expect(calls.at(-1)).toEqual({
        model: "onboarding.onboarding", method: "action_close_panel_logistics_idp", args: [],
    });
    expect("details.w_idp_onboarding").toHaveCount(0);
});

test("exception dimensions render as accessible SVG charts and drill down", async () => {
    const { actions, calls } = await mountDashboard();
    await animationFrame();
    expect('.w_idp_panel:contains("Exceptions by type") .w_idp_chart[role="img"]').toHaveAttribute("aria-label", "2 of 2");
    expect('.w_idp_panel:contains("Exceptions by type") .w_idp_chart_value').toHaveAttribute("width", "100");
    expect('.w_idp_panel:contains("Exceptions by type") .w_idp_bar').toHaveAttribute("aria-label", "Open price: 2 of 2");
    for (const title of [
        "Exceptions by type", "Exceptions by severity", "Exceptions by state", "Top suppliers by exceptions",
    ]) {
        expect(`h2:contains("${title}")`).toHaveCount(1);
    }
    for (const [text, metric, value] of [
        ["price", "exception", "price"], ["high", "exception_severity", "high"],
        ["open", "exception_state", "open"], ["SUP-1", "supplier", "SUP-1"],
    ]) {
        await contains(`.w_idp_bar:contains("${text}")`).click();
        expect(calls.at(-1).args).toEqual([metric, calls.at(-1).args[1], value]);
    }
    expect(actions).toHaveLength(4);
});

test("document distributions render and drill down", async () => {
    const { calls } = await mountDashboard();
    await animationFrame();
    for (const [title, metric, value] of [
        ["Source mix", "source", "email"], ["Customs regimes", "customs_regime", "e11"],
        ["Document types", "document_type", "invoice"],
    ]) {
        expect(`h2:contains("${title}")`).toHaveCount(1);
        await contains(`.w_idp_bar:contains("${value}")`).click();
        expect(calls.at(-1).args).toEqual([metric, calls.at(-1).args[1], value]);
    }
});

test("OCR aggregates and immutable history drilldown render", async () => {
    const { actions, calls } = await mountDashboard();
    await animationFrame();
    for (const [index, text] of ["fixture-provider", "2", "0.85", "3.5", "5"].entries()) {
        expect(`.w_idp_ocr tbody tr td:nth-child(${index + 1})`).toHaveText(text);
    }
    expect('.w_idp_panel:contains("Processing analytics · OCR") .w_idp_row button:contains("fixture-model: 2")').toHaveText("fixture-model: 2");
    expect("table.w_idp_ocr").toHaveCount(1);
    expect("table.w_idp_ocr thead th").toHaveCount(5);
    expect('.w_idp_ocr tbody tr[role="button"]').toHaveCount(0);
    await contains('.w_idp_ocr tbody td:first-child button', { text: "fixture-provider" }).click();
    expect(calls.at(-1).args).toEqual(["ocr_provider", calls.at(-1).args[1], "fixture-provider"]);
    await contains("button", { text: "Open extraction history" }).click();
    expect(calls.at(-1).args).toEqual(["ocr_history", calls.at(-1).args[1], null]);
    expect(actions.at(-1).res_model).toBe("logistics.idp.case");
});

test("queue keyboard and case state drilldowns remain available", async () => {
    const { actions, calls } = await mountDashboard();
    await animationFrame();
    await contains('.w_idp_queue tbody th[scope="row"] button').press("Enter");
    expect(actions[0].res_id).toBe(42);
    expect(calls.at(-1).args).toEqual(["case", calls.at(-1).args[1], 42]);
    await contains(".w_idp_panel .w_idp_bar").press("Enter");
    expect(calls.at(-1).args).toEqual(["case_state", calls.at(-1).args[1], "review"]);
    component.state.busyAction = true;
    await animationFrame();
    expect('[aria-label="Dashboard results"]').toHaveAttribute("inert", "inert");
});
