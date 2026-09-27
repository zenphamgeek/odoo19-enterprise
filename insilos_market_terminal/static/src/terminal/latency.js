/** @insilos-module **/

/**
 * MKT-003: end-to-end tick latency, measured where it actually matters.
 *
 * The sample is `browser render timestamp - provider source timestamp`, so it
 * covers provider fan-out, sidecar ingest, RPC and render. External provider
 * network time is inside the number by design; the SLA below is the internal
 * budget the terminal is held to.
 */

export const SLA_MS = { p50: 300, p95: 1_000, p99: 2_000 };

export function percentile(samples, p) {
    if (!samples.length) {
        return null;
    }
    const sorted = [...samples].sort((a, b) => a - b);
    // Nearest-rank: with few samples an interpolated percentile invents a
    // latency that was never observed.
    const rank = Math.ceil((p / 100) * sorted.length);
    return sorted[Math.min(Math.max(rank, 1), sorted.length) - 1];
}

export class LatencyTracker {
    constructor(capacity = 500) {
        this.capacity = capacity;
        this.samples = [];
    }

    /** Returns the sample in ms, or null when the tick cannot be measured. */
    record(sourceTs, renderedAt = Date.now()) {
        const source = Date.parse(sourceTs);
        if (!Number.isFinite(source)) {
            return null;
        }
        const delta = renderedAt - source;
        if (delta < 0) {
            // Clock skew ahead of us would report a flattering negative
            // latency. Drop it rather than let the SLA look better than it is.
            return null;
        }
        this.samples.push(delta);
        if (this.samples.length > this.capacity) {
            this.samples.shift();
        }
        return delta;
    }

    summary() {
        const measured = {
            p50: percentile(this.samples, 50),
            p95: percentile(this.samples, 95),
            p99: percentile(this.samples, 99),
        };
        const breaches = Object.keys(SLA_MS).filter(
            (key) => measured[key] !== null && measured[key] > SLA_MS[key]
        );
        return { count: this.samples.length, ...measured, breaches, within_sla: !breaches.length };
    }
}
