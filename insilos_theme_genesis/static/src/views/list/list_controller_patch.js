import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { FloatingBatchActionBar } from "./floating_action_bar/floating_action_bar";

// Register on base ListController
if (ListController.components) {
    ListController.components.FloatingBatchActionBar = FloatingBatchActionBar;
}

patch(ListController, {
    components: {
        ...ListController.components,
        FloatingBatchActionBar,
    },
});

// Sync existing view controllers in registry
try {
    const viewReg = registry.category("views");
    for (const [, viewDef] of viewReg.entries()) {
        if (viewDef?.Controller && viewDef.Controller.components) {
            viewDef.Controller.components.FloatingBatchActionBar = FloatingBatchActionBar;
        }
    }
} catch (_) {}

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.constructor.components) {
            this.constructor.components = {};
        }
        this.constructor.components.FloatingBatchActionBar = FloatingBatchActionBar;
    },

    onFloatingBatchApprove() {
        if (this.archInfo.headerButtons?.length) {
            const approveBtn =
                this.archInfo.headerButtons.find(
                    (b) =>
                        (b.string || "").toLowerCase().includes("approve") ||
                        (b.string || "").toLowerCase().includes("confirm") ||
                        (b.string || "").toLowerCase().includes("validate")
                ) || this.archInfo.headerButtons[0];
            if (approveBtn) {
                const btnEl = this.rootRef()?.querySelector(
                    `.o_control_panel .o_selection_container button[name='${approveBtn.clickParams?.name}']`
                );
                if (btnEl) {
                    btnEl.click();
                    return;
                }
            }
        }
        if (this.model.root.selection.length) {
            this.env.services.notification?.add(
                `${this.model.root.selection.length} record(s) processed`,
                { type: "info" }
            );
        }
    },

    onFloatingBatchExport() {
        this.exportRecords();
    },

    onFloatingBatchArchive() {
        this.model.root.toggleArchiveWithConfirmation(true, this.archiveDialogProps);
    },

    onFloatingBatchDelete() {
        this.onDeleteSelectedRecords();
    },

    onFloatingBatchDiscard() {
        this.discardSelection();
    },
});
