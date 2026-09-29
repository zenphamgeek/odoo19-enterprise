import { Component } from "@insilos/owl";

export class SidebarViewToolbox extends Component {
    static template = "web_studio.ViewEditor.ViewToolbox";
    static props = {
        canEditXml: { type: Boolean, optional: true },
        onMore: { type: Function, optional: true },
        openDefaultValues: { type: Function, optional: true },
        canEditDefaultValues: { type: Boolean, optional: true },
    };
}
