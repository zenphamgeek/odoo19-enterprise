import { Component, useState } from "@odoo/owl";

export class Box extends Component {
    static template = "iap_extract.Box";
    static props = {
        box: Object,
        pageWidth: String,
        pageHeight: String,
        onClickBoxCallback: Function,
    };
    /**
     * @override
     */
    setup() {
        this.state = useState(this.props.box);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get style() {
        const style = [
            `left: calc(${this.state.midX} * ${this.props.pageWidth})`,
            `top: calc(${this.state.midY} * ${this.props.pageHeight})`,
            `width: calc(${this.state.width} * ${this.props.pageWidth})`,
            `height: calc(${this.state.height} * ${this.props.pageHeight})`,
            `transform: translate(-50%, -50%) rotate(${this.state.angle}deg)`,
            `-ms-transform: translate(-50%, -50%) rotate(${this.state.angle}deg)`,
            `-webkit-transform: translate(-50%, -50%) rotate(${this.state.angle}deg)`,
        ].join('; ');
        return style;
    }

    get confidenceRatio() {
        const conf = this.state.confidence;
        if (conf === undefined || conf === null) {
            return 0.95; // Default high confidence if not provided by backend
        }
        return conf > 1 ? conf / 100 : conf;
    }

    get confidencePercent() {
        return Math.round(this.confidenceRatio * 100);
    }

    get confidenceTier() {
        const pct = this.confidencePercent;
        if (pct >= 90) {
            return "high";
        } else if (pct >= 70) {
            return "medium";
        }
        return "low";
    }

    get boxType() {
        return this.state.boxType || this.state.type || this.props.boxType || "word";
    }

    get tooltipText() {
        const text = this.state.text !== undefined && this.state.text !== null ? String(this.state.text) : "";
        const conf = this.confidencePercent;
        return `${text} (${conf}% confidence)`;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onClick() {
        this.props.onClickBoxCallback(this.state.id, this.state.page);
    }
};
