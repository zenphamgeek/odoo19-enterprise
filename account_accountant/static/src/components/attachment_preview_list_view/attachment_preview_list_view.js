import { AccountAttachmentView } from "./account_attachment_view";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListRenderer, listRendererProps } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { SIZES } from "@web/core/ui/ui_utils";
import { useChildSubEnv, proxy, signal, t, useProps } from "@odoo/owl";

export class AttachmentPreviewListController extends ListController {
    static template = "account_accountant.AttachmentPreviewListView";
    static components = {
        ...ListController.components,
        AccountAttachmentView,
    };
    setup() {
        super.setup();
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.mailPopoutService = useService("mail.popout");
        this.attachmentPreviewState = proxy({
            displayAttachment: localStorage.getItem(this.previewerStorageKey) !== "false",
            selectedRecord: false,
            thread: null,
        });
        this.thread = signal(null);
        this.popout = proxy({ active: false });

        useChildSubEnv({
            setPopout: this.setPopout.bind(this),
            setSelectedRecord: (record) => this.setSelectedRecord(record),
        });
    }

    async setSelectedRecord(record) {
        this.attachmentPreviewState.selectedRecord = record;
    }

    get previewEnabled() {
        return (
            !this.env.searchModel.context.disable_preview &&
            (this.ui.size >= SIZES.XXL || this.mailPopoutService.externalWindow)
        );
    }

    togglePreview() {
        this.attachmentPreviewState.displayAttachment =
            !this.attachmentPreviewState.displayAttachment;
        localStorage.setItem(
            this.previewerStorageKey,
            this.attachmentPreviewState.displayAttachment
        );
    }

    setPopout(value) {
        /**
         * This function will set the popout value to false or true depending on the situation.
         * We set popout to True when clicking on a line that has an attachment and then clicking on the popout button.
         * Once the external page is closed, the popout is set to false again.
         */
        if (this.attachmentPreviewState.thread?.attachmentsInWebClientView.length) {
            this.popout.active = value;
        }
    }

    async setThread(lineData, attachmentField, modelField) {
        const attachments = lineData?.data[attachmentField]?.records || [];
        if (!lineData || !attachments.length) {
            this.attachmentPreviewState.thread = null;
            this.thread.set(null);
            return;
        }
        const threadModel = this.store["mail.thread"] || this.store.Thread;
        const thread = threadModel.insert({
            attachments: attachments.map((attachment) => ({
                id: attachment.resId,
                mimetype: attachment.data.mimetype,
            })),
            id: lineData.data[modelField].id,
            model: lineData.fields[modelField].relation,
        });
        if (!thread.message_main_attachment_id && thread.attachmentsInWebClientView.length > 0) {
            thread.update({ message_main_attachment_id: thread.attachmentsInWebClientView[0] });
        }
        this.attachmentPreviewState.thread = thread;
        this.thread.set(thread);
    }
}

export class AttachmentPreviewListRenderer extends ListRenderer {
    props = useProps({
        ...listRendererProps,
        setSelectedRecord: t.any().optional(),
    });

    async onCellClicked(record, column, ev) {
        const setRec = this.props.setSelectedRecord || this.env.setSelectedRecord;
        setRec?.(record);
        await super.onCellClicked(record, column, ev);
    }

    findFocusFutureCell(cell, cellIsInGroupRow, direction) {
        const futureCell = super.findFocusFutureCell(cell, cellIsInGroupRow, direction);
        if (futureCell) {
            const dataPointId = futureCell.closest("tr").dataset.id;
            const record = this.props.list.records.filter((x) => x.id === dataPointId)[0];
            const setRec = this.props.setSelectedRecord || this.env.setSelectedRecord;
            setRec?.(record);
        }
        return futureCell;
    }
}
export const AccountAttachmentListView = {
    ...listView,
    Renderer: AttachmentPreviewListRenderer,
    Controller: AttachmentPreviewListController,
};

registry.category("views").add("account_attachment_list", AccountAttachmentListView);
