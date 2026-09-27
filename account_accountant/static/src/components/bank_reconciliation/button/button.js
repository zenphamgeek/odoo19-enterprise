import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class BankRecButton extends Component {
    static template = "account_accountant.BankRecButton";
    static props = {
        label: { type: String, optional: true },
        action: { type: Function, optional: true },
        count: { type: [Number, { value: null }], optional: true },
        primary: { type: Boolean, optional: true },
        toReview: { type: Boolean, optional: true },
        classes: { type: String, optional: true },
    };

    get primary() {
        return this.props.primary ?? false;
    }

    get classes() {
        return this.props.classes ?? "";
    }

    setup() {
        this.ui = useService("ui");
    }
}
