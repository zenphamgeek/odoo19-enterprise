import { Dialog } from "@web/core/dialog/dialog";
import { Component, proxy } from "@odoo/owl";

export class ConfirmQuantDialog extends Component {
    static components = { Dialog };
    static template = "stock_barcode.ConfirmQuantDialog";
    static props = {
        close: Function,
        onConfirm: Function,
        onWaitReview: Function,
    };

    setup() {
        this.inventoryReason = proxy({ value: "Physical Inventory" });
    }

    onConfirm() {
        this.props.onConfirm({
            inventory_name: this.prop,
        });
        this.props.close();
    }

    onWaitReview() {
        this.props.onWaitReview();
        this.props.close();
    }

    onInventoryReasonChange(ev) {
        this.inventoryReason.value = ev.target.value;
    }
}
