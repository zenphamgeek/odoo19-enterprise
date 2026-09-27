import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.attachmentUploadService = useService("mail.attachment_upload");
        const threadModel = this.store.Thread || this.store["mail.thread"];
        const threadId = typeof this.threadId === "function" ? this.threadId() : this.props.threadId;
        const modelName = typeof this.threadModel === "function" ? this.threadModel() : this.props.threadModel;
        const thread = threadModel?.insert?.({
            model: modelName,
            id: threadId,
        });
        if (thread) {
            this.attachmentUploadService.onFileUploaded(thread, () => {
                if (this.state.thread?.model === "hr.applicant") {
                    this.reloadParentView();
                }
            });
        }
    },
});
