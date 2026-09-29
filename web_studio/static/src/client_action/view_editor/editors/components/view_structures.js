import { SidebarDraggableItem } from "@web_studio/client_action/components/sidebar_draggable_item/sidebar_draggable_item";
import { Component } from "@insilos/owl";

export class ViewStructures extends Component {
    static components = { SidebarDraggableItem };
    static template = "web_studio.ViewStructures";
    static props = {
        structures: { type: Object, optional: true },
    };
    get structures() {
        return this.props.structures || {};
    }
    get isVisible() {
        return Object.values(this.structures).filter(
            (e) => !e.isVisible || e.isVisible(this.env.viewEditorModel)
        ).length;
    }
}
