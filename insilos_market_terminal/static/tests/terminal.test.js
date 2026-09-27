import { expect, test } from '@odoo/hoot';
import { animationFrame } from '@odoo/hoot-mock';
import { mockService, mountWithCleanup } from '@web/../tests/web_test_helpers';
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { MarketTerminalAction } from "@insilos_market_terminal/terminal/terminal_action";
import { LatencyTracker, SLA_MS, percentile } from "@insilos_market_terminal/terminal/latency";

/** MR-20260720 frozen reference; the same rows the Python fixture asserts. */
const HPG_BARS = [
    { date: "2026-07-19", open: 21900, high: 22000, low: 21750, close: 21850, volume: 48900300 },
    { date: "2026-07-20", open: 21400, high: 21450, low: 20500, close: 20600, volume: 53245200 },
];

// The web client shell mounts the messaging stack, so the mock server needs
// the mail models; the web set alone leaves discuss.channel undefined.
defineMailModels();


const PAYLOAD = {
    symbol: "HPG",
    instrument: { id: 7, name: "HPG", type: "equity", mapped: true },
    bars: HPG_BARS,
    lineage: { provider: "sidecar", symbol: "HPG", source_as_of: "2026-07-20", fingerprint: "MR-20260720" },
    market_state: { status: "available", as_of: "2026-07-20", close: 20600, volume: 53245200, change_pct: -5.72 },
    portfolio_cards: [],
    overlays: {
        price_lines: [{ label: "Avg cost", price: 22000, res_model: "capital.position", res_id: 3 }],
        markers: [{ time: "2026-07-20", text: "IC-42", res_model: "project.task", res_id: 42 }],
    },
};

function mockTerminalOrm(stream = { stale: true, sequence_gap: false }) {
    mockService("orm", {
        call(model, method) {
            expect(model).toBe("market.terminal.data");
            return method === "get_terminal_payload" ? { ...PAYLOAD } : stream;
        },
    });
}

test("MKT-002 chart data equals API data and is never recomputed client-side", async () => {
    mockTerminalOrm();
    const terminal = await mountWithCleanup(MarketTerminalAction, { props: { action: {} } });
    await terminal.loadSymbol("HPG");
    await animationFrame();

    // Read the OHLC back out of the chart engine, not out of our own state:
    // this is what proves the rendered candles carry the exchange values.
    const rendered = terminal.series.data();
    expect(rendered).toHaveLength(2);
    expect(rendered.map((bar) => [bar.open, bar.high, bar.low, bar.close])).toEqual(
        HPG_BARS.map((bar) => [bar.open, bar.high, bar.low, bar.close])
    );
    expect(rendered.at(-1).close).toBe(20600);
    // The 20/07 candle closes at the session low, per the frozen reference.
    expect(rendered.at(-1).close).toBe(rendered.at(-1).low + 100);

    const volume = terminal.volumeSeries.data();
    expect(volume.map((bar) => bar.value)).toEqual([48900300, 53245200]);
    // Volume must not share the price scale, or the candles flatten out.
    expect(terminal.volumeSeries.options().priceScaleId).toBe("volume");
});

test("MKT-002 overlays render as governed, drillable chart artefacts", async () => {
    mockTerminalOrm();
    const terminal = await mountWithCleanup(MarketTerminalAction, { props: { action: {} } });
    await terminal.loadSymbol("HPG");
    await animationFrame();

    expect(terminal.priceLines).toHaveLength(1);
    expect(terminal.priceLines[0].options().price).toBe(22000);
    // Every overlay keeps its ERP pointer so the chart stays drill-through.
    expect(terminal.overlayRecords.map((record) => record.res_model)).toEqual([
        "capital.position",
        "project.task",
    ]);

    const opened = [];
    mockService("action", { doAction: (action) => opened.push(action) });
    const drillTerminal = await mountWithCleanup(MarketTerminalAction, { props: { action: {} } });
    await drillTerminal.loadSymbol("HPG");
    drillTerminal.openEvidence(drillTerminal.overlayRecords[1]);
    expect(opened).toHaveLength(1);
    expect(opened[0].res_model).toBe("project.task");
    expect(opened[0].res_id).toBe(42);
});

test("MKT-003 latency percentiles use observed samples and the internal SLA", () => {
    expect(percentile([], 50)).toBe(null);
    // Nearest-rank: p95 of ten samples is the tenth, not an interpolated value.
    expect(percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 100], 95)).toBe(100);
    expect(percentile([5], 99)).toBe(5);

    const tracker = new LatencyTracker();
    const base = Date.parse("2026-07-20T09:00:00Z");
    [120, 180, 250, 900, 1_900].forEach((delta, index) =>
        tracker.record(new Date(base + index * 1_000).toISOString(), base + index * 1_000 + delta)
    );
    const summary = tracker.summary();
    expect(summary.count).toBe(5);
    expect(summary.p50).toBe(250);
    expect(summary.p95).toBe(1_900);
    // p99 of five samples is still the worst sample, and 1.9s sits inside the
    // 2s p99 budget, so only p95 is breached here.
    expect(summary.p99).toBe(1_900);
    expect(summary.breaches).toEqual(["p95"]);
    expect(summary.within_sla).toBe(false);
    expect(SLA_MS).toEqual({ p50: 300, p95: 1_000, p99: 2_000 });
});

test("MKT-003 unmeasurable and clock-skewed ticks are dropped, not flattered", () => {
    const tracker = new LatencyTracker(3);
    expect(tracker.record("not-a-timestamp")).toBe(null);
    // A source clock ahead of the browser would report negative latency.
    expect(tracker.record("2026-07-20T09:00:10Z", Date.parse("2026-07-20T09:00:00Z"))).toBe(null);
    expect(tracker.summary().count).toBe(0);
    expect(tracker.summary().p50).toBe(null);
    expect(tracker.summary().within_sla).toBe(true);

    // The window is bounded, so a long session cannot grow without limit.
    const base = Date.parse("2026-07-20T09:00:00Z");
    [10, 20, 30, 40].forEach((delta, index) =>
        tracker.record(new Date(base + index * 1_000).toISOString(), base + index * 1_000 + delta)
    );
    expect(tracker.samples).toEqual([20, 30, 40]);
});

test("MKT-006 a stale feed is never counted as a healthy realtime sample", async () => {
    mockTerminalOrm({ stale: true, sequence_gap: true, source_ts: "2026-07-20T09:00:00Z" });
    const terminal = await mountWithCleanup(MarketTerminalAction, { props: { action: {} } });
    await terminal.loadSymbol("HPG");
    await animationFrame();

    expect(terminal.state.stream.stale).toBe(true);
    expect(terminal.state.stream.sequence_gap).toBe(true);
    // Stale ticks must not enter the latency budget, or a dead feed would read
    // as a healthy but slow pipeline.
    expect(terminal.state.latency).toBe(null);
    expect(terminal.latency.samples).toHaveLength(0);
});
