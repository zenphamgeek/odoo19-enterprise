import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { KanbanEditorRecord } from "@web_studio/client_action/view_editor/editors/kanban/kanban_editor_record";
import { useEffect, onMounted } from "@insilos/owl";
import { SelectionHeaderButtons } from "../../interactive_editor/action_button/action_button";

class KanbanEditorHeader extends KanbanHeader {
    static template = "web_studio.KanbanEditorHeader";
}

export class KanbanEditorRenderer extends kanbanView.Renderer {
    static template = "web_studio.KanbanEditorRenderer";
    static components = {
        ...kanbanView.Renderer.components,
        KanbanRecord: KanbanEditorRecord,
        KanbanHeader: KanbanEditorHeader,
        SelectionHeaderButtons,
    };

    setup() {
        super.setup();
        const getRootEl = () => (typeof this.rootRef === "function" ? this.rootRef() : (this.rootRef?.el || this.rootRef));
        onMounted(() => {
            const el = getRootEl();
            if (el) {
                el.classList.add("o_web_studio_kanban_view_editor");
            }
        });
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                el.classList.add("o_web_studio_kanban_view_editor");
            },
            () => [getRootEl()]
        );
    }

    get canUseSortable() {
        return false;
    }

    get showNoContentHelper() {
        return false;
    }

    getGroupsOrRecords() {
        const { list } = this.props;
        const groupsOrRec = super.getGroupsOrRecords(...arguments);
        if (list.isGrouped) {
            const firstGroup = groupsOrRec.find((el) => el?.group?.list?.records?.length);
            return firstGroup ? [firstGroup] : [];
        } else {
            return groupsOrRec[0] ? [groupsOrRec[0]] : [];
        }
    }

    canCreateGroup() {
        return false;
    }

    getGroupUnloadedCount() {
        return 0;
    }
}
