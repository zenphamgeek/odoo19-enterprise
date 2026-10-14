import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export default class SystrayAction extends Component {
    static props = {};
    static template = "ai.SystrayAction";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.aiChatLauncher = useService("aiChatLauncher");
        this.notification = useService("notification");
        this._isLaunching = false;
    }

    async onClickLaunchAIChat() {
        if (this._isLaunching) {
            return;
        }
        this._isLaunching = true;
        try {
            const currentController = this.actionService.currentController;
            if (currentController?.view?.type === "form") {
                try {
                    const resModel = currentController.props?.resModel || currentController.model?.root?.resModel;
                    const resId = currentController.props?.resId || currentController.model?.root?.resId;
                    this.env.bus.trigger("AI:OPEN_AI_CHAT", {
                        origin: "chatter_ai_button",
                        resModel,
                        resId,
                    });
                    return;
                } catch (err) {
                    console.warn("[AI Systray] Form AI chat launch error, falling back to general chat:", err);
                    this.notification?.add(
                        "Could not link active record context to AI chat. Opening general chat instead.",
                        { type: "warning" }
                    );
                }
            }
            await this.aiChatLauncher.launchAIChat({
                callerComponentName: "systray_ai_button",
            });
        } finally {
            this._isLaunching = false;
        }
    }
}

registry
    .category("systray")
    .add("ai.systray_action", { Component: SystrayAction }, { sequence: 30 });
