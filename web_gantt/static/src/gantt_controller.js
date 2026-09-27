import { _t } from "@web/core/l10n/translation";
import { Component, onWillUnmount, signal, useSubEnv } from "@odoo/owl";
import { useLayoutEffect } from "@web/owl2/utils";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { Layout } from "@web/search/layout";
import { standardViewProps } from "@web/views/standard_view_props";
import { useModelWithSampleData } from "@web/model/model";
import { usePager } from "@web/search/pager_hook";
import { useService } from "@web/core/utils/hooks";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { CallbackRecorder, useSetupAction } from "@web/search/action_hook";
import { ActionHelper } from "@web/views/action_helper";

export class GanttController extends Component {
    static components = {
        CogMenu,
        Layout,
        SearchBar,
        ActionHelper,
    };
    static props = {
        ...standardViewProps,
        Model: Function,
        Renderer: Function,
        buttonTemplate: String,
        modelParams: Object,
        multiCreateValues: { type: Object, optional: true },
        scrollPosition: { type: Object, optional: true },
    };
    static template = "web_gantt.GanttController";

    rootRef = signal.ref();
    get root() {
        return this.rootRef;
    }

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.ui = useService("ui");

        useSubEnv({
            getCurrentFocusDateCallBackRecorder: new CallbackRecorder(),
            createFromSelectionCallBackRecorder: new CallbackRecorder(),
        });

        this.model = useModelWithSampleData(this.props.Model, this.props.modelParams);
        useSetupAction({
            rootRef: this.rootRef,
            getLocalState: () => ({
                metaData: this.model.metaData,
                displayParams: this.model.displayParams,
            }),
        });

        onWillUnmount(() => this.closeDialog?.());

        usePager(() => {
            const { groupedBy, pagerLimit, pagerOffset } = this.model.metaData;
            const { count } = this.model.data;
            if (pagerLimit !== null && groupedBy.length) {
                return {
                    offset: pagerOffset,
                    limit: pagerLimit,
                    total: count,
                    onUpdate: async ({ offset, limit }) => {
                        await this.model.updatePagerParams({ offset, limit });
                    },
                };
            }
        });

        useLayoutEffect(
            (showNoContentHelp) => {
                if (showNoContentHelp && this.rootRef.el) {
                    const realRows = [
                        ...this.rootRef.el.querySelectorAll(
                            ".o_gantt_row_header:not(.o_sample_data_disabled)"
                        ),
                    ];
                    // interactive rows created in extensions (fromServer undefined)
                    const headerGroupsEl = this.rootRef.el.querySelector(".o_gantt_header_groups");
                    const headerColumnsEl = this.rootRef.el.querySelector(".o_gantt_header_columns");
                    const headerContainerWidth =
                        (headerGroupsEl ? headerGroupsEl.clientHeight : 0) +
                        (headerColumnsEl ? headerColumnsEl.clientHeight : 0);

                    const offset = realRows.reduce(
                        (current, el) => current + el.clientHeight,
                        headerContainerWidth
                    );

                    const noContentHelperEl = this.rootRef.el.querySelector(".o_view_nocontent");
                    if (noContentHelperEl) {
                        noContentHelperEl.style.top = `${offset}px`;
                    }
                }
            },
            () => [this.showNoContentHelp]
        );
        this.searchBarToggler = useSearchBarToggler();
    }

    get className() {
        if (this.ui.isSmall) {
            const classList = (this.props.className || "").split(" ");
            classList.push("o_action_delegate_scroll");
            return classList.join(" ");
        }
        return this.props.className;
    }

    get showNoContentHelp() {
        return this.model.useSampleModel;
    }

    /**
     * @param {Record<string, any>} [context]
     */
    create(context) {
        const { createAction } = this.model.metaData;
        if (createAction) {
            this.actionService.doAction(createAction, {
                additionalContext: context,
                onClose: () => {
                    this.model.fetchData();
                },
            });
        } else {
            this.openDialog({ context });
        }
    }

    _getDialogProps(props) {
        const { canDelete, canEdit, resModel, formViewId: viewId } = this.model.metaData;

        const title = props.title || (props.resId ? _t("Open") : _t("Create"));

        let removeRecord;
        if (canDelete && props.resId) {
            removeRecord = () =>
                new Promise((resolve) => {
                    this.dialogService.add(ConfirmationDialog, {
                        title: _t("Bye-bye, record!"),
                        body: deleteConfirmationMessage,
                        confirmLabel: _t("Delete"),
                        confirm: async () => {
                            await this.orm.unlink(resModel, [props.resId]);
                            resolve();
                        },
                        cancel: () => {},
                        cancelLabel: _t("No, keep it"),
                    });
                });
        }

        return {
            title,
            resModel,
            viewId,
            resId: props.resId,
            size: props.size,
            canExpand: props.canExpand,
            readonly: !canEdit,
            context: props.context,
            removeRecord,
        };
    }

    /**
     * Opens dialog to add/edit/view a record
     *
     * @param {Record<string, any>} props dialog component props
     * @param {Record<string, any>} [options={}]
     * @param {Component} dialog component to instantiate, usually FormViewDialog
     */
    openDialog(props, options = {}, dialogComponent = FormViewDialog) {
        this.closeDialog = this.dialogService.add(dialogComponent, this._getDialogProps(props), {
            ...options,
            onClose: () => {
                this.closeDialog = null;
                this.model.fetchData();
            },
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onNewClicked() {
        const context = this.getAdditionalContext();
        this.create(context);
    }

    onNewClicked() {
        const created = this.createFromSelection();
        if (!created) {
            this._onNewClicked();
        }
    }

    getAdditionalContext() {
        const { scale } = this.model.metaData;
        const focusDate = this.getCurrentFocusDate();
        const start = focusDate.startOf(scale.unit);
        const stop = focusDate.endOf(scale.unit).plus({ millisecond: 1 });
        return this.model.getDialogContext({ start, stop, withDefault: true });
    }

    createFromSelection() {
        const { callbacks } = this.env.createFromSelectionCallBackRecorder;
        if (callbacks.length) {
            return callbacks[0]();
        }
        return false;
    }

    getCurrentFocusDate() {
        const { callbacks } = this.env.getCurrentFocusDateCallBackRecorder;
        if (callbacks.length) {
            return callbacks[0]();
        }
        return this.model.metaData.focusDate;
    }
}
