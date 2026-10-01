import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
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
        this.onFloatingBatchPrint = this.onFloatingBatchPrint.bind(this);
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

    async onFloatingBatchPrint() {
        const records = this.model.root.selection;
        if (!records.length) {
            return;
        }
        if (this.props.info?.actionMenus?.print?.length) {
            const primaryPrintAction = this.props.info.actionMenus.print[0];
            let activeIds = records.map((r) => r.resId);
            if (this.isDomainSelected && this.orm) {
                activeIds = await this.orm.search(this.model.root.resModel, this.model.root.domain, {
                    limit: session?.active_ids_limit || 80,
                    context: this.props.context,
                });
            }
            const activeIdsContext = {
                active_id: activeIds[0],
                active_ids: activeIds,
                active_model: this.model.root.resModel,
            };
            if (this.model.root.domain) {
                activeIdsContext.active_domain = this.model.root.domain;
            }
            if (this.actionService) {
                return this.actionService.doAction(primaryPrintAction.id, {
                    additionalContext: activeIdsContext,
                });
            } else if (this.env.services?.action) {
                return this.env.services.action.doAction(primaryPrintAction.id, {
                    additionalContext: activeIdsContext,
                });
            }
        }
        // Fallback: check if print menu button in control panel exists or trigger window.print
        const printBtn = this.rootRef()?.querySelector(
            `.o_control_panel .o_cp_action_menus button.o_print_menu_toggle, .o_control_panel [data-hotkey='u'], .o_control_panel button[name='print']`
        );
        if (printBtn) {
            printBtn.click();
            return;
        }
        window.print();
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
