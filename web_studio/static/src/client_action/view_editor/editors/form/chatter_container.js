import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import "@mail/chatter/web/chatter_patch";

import { Component } from "@insilos/owl";

export class ChatterContainer extends Chatter {
    static template = "web_studio.ChatterContainer";
    static props = { ...(Chatter.props || {}), studioXpath: { type: String, optional: true } };

    onClick(ev) {
        this.env.config.onNodeClicked(this.props.studioXpath);
    }
}

export class ChatterContainerHook extends Component {
    static template = "web_studio.ChatterContainerHook";
    static components = { Chatter };
    static props = {
        chatterData: Object,
        threadModel: String,
    };

    onClick() {
        this.env.viewEditorModel.doOperation({
            type: "chatter",
            model: this.env.viewEditorModel.resModel,
            ...this.props.chatterData,
        });
    }
}
