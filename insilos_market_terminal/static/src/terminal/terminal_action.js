import { Component, onMounted, onWillUnmount, useRef, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { standardActionServiceProps } from '@web/webclient/actions/action_service';
import { atr, ema, rsi, sma, vwap } from "./indicators";
import { LatencyTracker } from "./latency";

/* global LightweightCharts */

const INDICATORS = { sma, ema, vwap, rsi, atr };

export class MarketTerminalAction extends Component {
    static template = "insilos_market_terminal.Terminal";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.chartRef = useRef("chart");
        this.state = useState({ symbol: "", lineage: null, instrument: null, error: "", indicators: [], stream: null, marketState: null, portfolioCards: [], latency: null });
        this.chart = null;
        this.latency = new LatencyTracker();
        onMounted(() => this._createChart());
        onWillUnmount(() => {
            clearInterval(this.streamTimer);
            if (this.chart) this.chart.remove();
        });
    }

    _createChart() {
        this.chart = LightweightCharts.createChart(this.chartRef.el, {
            autoSize: true,
            layout: { attributionLogo: true },
            timeScale: { timeVisible: true },
        });
        this.series = this.chart.addCandlestickSeries();
        // MKT-002: volume lives on its own overlay scale, otherwise share counts
        // and prices share an axis and the candles collapse into a flat line.
        this.volumeSeries = this.chart.addHistogramSeries({
            priceFormat: { type: "volume" },
            priceScaleId: "volume",
        });
        this.chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    }

    async loadSymbol(symbol) {
        if (!symbol) return;
        this.state.error = "";
        const to = new Date().toISOString().slice(0, 10);
        const from = new Date(Date.now() - 365 * 864e5).toISOString().slice(0, 10);
        try {
            const payload = await this.orm.call("market.terminal.data", "get_terminal_payload", [symbol, from, to]);
            this.state.symbol = payload.symbol;
            this.state.lineage = payload.lineage;
            this.state.instrument = payload.instrument;
            this.state.marketState = payload.market_state;
            this.state.portfolioCards = payload.portfolio_cards || [];
            this.bars = payload.bars || [];
            this.series.setData(this.bars.map((bar) => ({
                time: bar.date || bar.time, open: bar.open, high: bar.high, low: bar.low, close: bar.close,
            })));
            this.volumeSeries.setData(this.bars.map((bar) => ({
                time: bar.date || bar.time,
                value: bar.volume ?? 0,
                color: bar.close >= bar.open ? "#26a69a80" : "#ef535080",
            })));
            this._applyOverlays(payload.overlays);
            this._applyIndicators();
            this._startStream();
        } catch (error) {
            this.state.error = error.data?.message || error.message || String(error);
        }
    }

    _startStream() {
        clearInterval(this.streamTimer);
        this._refreshStream();
        this.streamTimer = setInterval(() => this._refreshStream(), 5_000);
    }

    async _refreshStream() {
        try {
            const stream = await this.orm.call("market.terminal.data", "get_stream_payload", [this.state.symbol]);
            this.state.stream = stream;
            // MKT-003: a stale feed must not feed the latency budget, otherwise
            // a disconnect would be reported as a very slow but healthy pipe.
            if (!stream.stale && stream.source_ts) {
                this.latency.record(stream.source_ts);
                this.state.latency = this.latency.summary();
            }
        } catch {
            // The historical chart remains usable; status deliberately becomes stale.
            this.state.stream = { stale: true, sequence_gap: false };
        }
    }

    _applyOverlays(overlays) {
        (this.priceLines || []).forEach((line) => this.series.removePriceLine(line));
        this.priceLines = (overlays.price_lines || []).map((line) => this.series.createPriceLine({
            price: line.price, title: line.label, lineStyle: LightweightCharts.LineStyle.Dashed,
        }));
        this.overlayRecords = [...(overlays.price_lines || []), ...(overlays.markers || [])];
        const markers = (overlays.markers || []).map(({ res_model, res_id, ...marker }) => marker);
        if (this.series.setMarkers) this.series.setMarkers(markers);
    }

    _applyIndicators() {
        (this.indicatorSeries || []).forEach((series) => this.chart.removeSeries(series));
        this.indicatorSeries = this.state.indicators.map((name) => {
            const series = this.chart.addLineSeries({ title: name.toUpperCase(), lineWidth: 1 });
            series.setData(INDICATORS[name](this.bars));
            return series;
        });
    }

    toggleIndicator(name) {
        this.state.indicators = this.state.indicators.includes(name)
            ? this.state.indicators.filter((value) => value !== name)
            : [...this.state.indicators, name];
        if (this.bars) this._applyIndicators();
    }

    openEvidence(overlay) {
        this.actionService.doAction({
            type: "is.actions.act_window", res_model: overlay.res_model, res_id: overlay.res_id, views: [[false, "form"]],
        });
    }

    onSymbolKeydown(ev) {
        if (ev.key === "Enter") this.loadSymbol(ev.target.value.trim().toUpperCase());
    }
}

registry.category("actions").add("insilos_market_terminal.terminal", MarketTerminalAction);
