import { Component, onWillStart, onWillUnmount, useState } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { user } from '@web/core/user';
import { standardActionServiceProps } from '@web/webclient/actions/action_service';

const OCR_STATUS_LABELS = {
    pending: _t("Pending"), valid: _t("Valid"), review: _t("Review"), error: _t("Error"),
};

const KPI_LABELS = {
    open_cases: _t("Open cases"), review_cases: _t("Needs review"), blocked_cases: _t("Compliance blocks"),
    overdue_cases: _t("SLA overdue"), documents: _t("Documents"), received_today: _t("Cases received today"),
    processed_today: _t("Documents processed today"), waiting_supplier: _t("Waiting for supplier"),
    waiting_broker_customs: _t("Waiting for broker/customs"), duplicate_detected: _t("Duplicates detected"),
    overdue_import_declaration_cases: _t("Overdue import declaration cases"), low_confidence_extraction_queue: _t("Low-confidence extraction queue"),
    average_processing_duration: _t("Average processing time"), ai_credits_per_document_case: _t("AI credits per document/case"),
    source_erp_api_mes: _t("ERP / API / MES sources"), stp_rate: _t("Straight-through rate"),
};
const PRIORITY_KPIS = ["open_cases", "review_cases", "blocked_cases", "overdue_cases", "waiting_supplier", "processed_today"];

export class LogisticsIdpDashboard extends Component {
    static template = "insilos_logistics_idp.Dashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.user = user;
        this.state = useState({ loading: true, busyAction: false, error: "", operationError: "", data: null, filters: this.defaultFilters() });
        this.loadSequence = 0;
        onWillStart(() => this.load());
        onWillUnmount(() => this.loadSequence++);
    }

    defaultFilters() {
        const toLocalDate = (date) => new Date(date.getTime() - date.getTimezoneOffset() * 60e3);
        const today = toLocalDate(new Date());
        const from = new Date(today);
        from.setUTCDate(from.getUTCDate() - 29);
        return { date_from: from.toISOString().slice(0, 10), date_to: today.toISOString().slice(0, 10), supplier: "", jurisdiction: "", customs_regime: "", document_type: "", company_ids: [...(user.context.allowed_company_ids || [])] };
    }

    async load() {
        const sequence = ++this.loadSequence;
        this.state.loading = true;
        this.state.error = "";
        try {
            const data = await this.orm.call("logistics.idp.case", "get_dashboard_data", [this.cleanFilters()]);
            if (sequence === this.loadSequence) this.state.data = data;
        } catch (error) {
            console.error("Unable to load Logistics IDP dashboard", error);
            if (sequence === this.loadSequence) this.state.error = _t("Unable to load dashboard. Retry or contact your administrator.");
        } finally {
            if (sequence === this.loadSequence) this.state.loading = false;
        }
    }

    cleanFilters() { return Object.fromEntries(Object.entries(this.state.filters).filter(([, value]) => value !== "" && value != null)); }
    onFilter(ev) { const { name, value } = ev.target; this.state.filters[name] = name === "company_ids" ? [Number(value)] : value; }
    applyFilters() { return this.load(); }
    resetFilters() { this.state.filters = this.defaultFilters(); return this.load(); }

    async runAction(callback) {
        if (this.state.busyAction) return;
        this.state.busyAction = true;
        this.state.operationError = "";
        try { return await callback(); } catch (error) {
            console.error("Unable to open Logistics IDP dashboard action", error);
            this.state.operationError = _t("Unable to complete this action. Retry or contact your administrator.");
        } finally { this.state.busyAction = false; }
    }

    drilldown(kind, value = null) { return this.runAction(async () => this.actionService.doAction(await this.orm.call("logistics.idp.case", "dashboard_drilldown", [kind, this.cleanFilters(), value]))); }
    drilldownChart(kind, row, field) { return this.drilldown(kind, kind === "document_throughput" ? row.__domain : row[field]); }
    openOnboardingStep(step) { return this.runAction(async () => this.actionService.doAction(await this.orm.call("onboarding.onboarding.step", step.action, []))); }
    closeOnboarding() { return this.runAction(async () => { const onboarding = this.state.data.onboarding; await this.orm.call(onboarding.close_model, onboarding.close_method, []); onboarding.closed = true; }); }
    formatMetric(key, value, available = true) { if (!available) return _t("Not Available"); if (value == null) return "—"; return key === "stp_rate" ? `${Math.round(value * 100)}%` : value.toLocaleString(); }
    metricEntries() { return Object.entries(this.state.data?.metrics || {}).map(([key, metric]) => ({ key, label: KPI_LABELS[key], ...metric })); }
    priorityMetrics() { const metrics = Object.fromEntries(this.metricEntries().map((metric) => [metric.key, metric])); return PRIORITY_KPIS.map((key) => metrics[key]).filter(Boolean); }
    activeQueue() { return (this.state.data?.live_queue || []).slice(0, 8); }
    count(row) { return row?.__count || row?.["id_count"] || 0; }
    stepStateLabel(state) { return ({ not_done: _t("To do"), just_done: _t("Just done"), done: _t("Done") })[state] || _t("To do"); }
    label(row, field) { const value = row?.[field]; return Array.isArray(value) ? value[1] : (field === "status" ? OCR_STATUS_LABELS[value] : value) || _t("Unspecified"); }
    max(rows) { return Math.max(1, ...(rows || []).map((row) => this.count(row))); }
    chartWidth(row, rows) { return Math.round(this.count(row) * 100 / this.max(rows)); }
    chartLabel(row, rows) { return _t("%s of %s", this.count(row), this.total(rows)); }
    total(rows) { return rows.reduce((sum, row) => sum + this.count(row), 0); }
    chartType(kind) { if (kind === "document_throughput") return "line"; return ["case_state", "verdict", "source", "customs_regime", "document_type", "exception_state"].includes(kind) ? "donut" : "ranking"; }
    chartColor(index) { return ["#1764ad", "#008477", "#9b6500", "#7652a4", "#be4658", "#42677a"][index % 6]; }
    chartRows(rows, kind) { return kind === "document_throughput" ? rows : [...rows].sort((a, b) => this.count(b) - this.count(a)); }
    donutStyle(rows) { const total = this.total(rows); if (!total) return "background: #e6edf5"; let offset = 0; return `background: conic-gradient(${rows.map((row, index) => { const start = offset; offset += this.count(row) * 100 / total; return `${this.chartColor(index)} ${start}% ${offset}%`; }).join(",")})`; }
    lineX(index, rows) { return rows.length < 2 ? 300 : 24 + index * 552 / (rows.length - 1); }
    lineY(row, rows) { return 176 - this.count(row) * 144 / this.max(rows); }
    linePoints(rows) { return rows.map((row, index) => `${this.lineX(index, rows)},${this.lineY(row, rows)}`).join(" "); }
    isEmpty() { return !Object.values(this.state.data?.metrics || {}).some((item) => item?.value); }
}

registry.category("actions").add("insilos_logistics_idp.dashboard", LogisticsIdpDashboard);
