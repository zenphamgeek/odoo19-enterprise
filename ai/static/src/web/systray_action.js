import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class StigmergicCircuitBreaker {
    constructor(threshold = 3, cooldownMs = 15000) {
        this.failures = 0;
        this.threshold = threshold;
        this.cooldownMs = cooldownMs;
        this.trippedUntil = 0;
    }

    canAttempt() {
        if (this.failures < this.threshold) {
            return true;
        }
        if (Date.now() >= this.trippedUntil) {
            this.failures = 0;
            return true;
        }
        return false;
    }

    recordSuccess() {
        this.failures = 0;
        this.trippedUntil = 0;
    }

    recordFailure() {
        this.failures += 1;
        if (this.failures >= this.threshold) {
            this.trippedUntil = Date.now() + this.cooldownMs;
        }
    }
}

export default class SystrayAction extends Component {
    static props = {};
    static template = "ai.SystrayAction";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.aiChatLauncher = useService("aiChatLauncher");
        this.notification = useService("notification");
        this.isLaunching = false;
        this._isLaunching = false;
        this.circuitBreaker = new StigmergicCircuitBreaker();
    }

    async onClickLaunchAIChat() {
        if (this.isLaunching || this._isLaunching) {
            return;
        }
        this.isLaunching = true;
        this._isLaunching = true;
        try {
            const currentController = this.actionService.currentController;
            let handled = false;
            if (currentController?.view?.type === "form" && this.circuitBreaker.canAttempt()) {
                const canTriggerBus = typeof this.env.bus.hasListener === "function"
                    ? this.env.bus.hasListener("AI:OPEN_AI_CHAT")
                    : true;
                if (canTriggerBus) {
                    try {
                        const resModel = currentController.props?.resModel || currentController.model?.root?.resModel;
                        const resId = currentController.props?.resId || currentController.model?.root?.resId;
                        await this.env.bus.trigger("AI:OPEN_AI_CHAT", {
                            origin: "chatter_ai_button",
                            resModel,
                            resId,
                        });
                        this.circuitBreaker.recordSuccess();
                        handled = true;
                    } catch (err) {
                        this.circuitBreaker.recordFailure();
                        console.warn("[AI Systray] Form AI chat trigger failed, launching fallback chat:", err);
                        this.notification?.add(
                            "Could not link active record context to AI chat. Opening general chat instead.",
                            { type: "warning" }
                        );
                    }
                }
            }
            if (!handled) {
                await this.aiChatLauncher.launchAIChat({
                    callerComponentName: "systray_ai_button",
                });
            }
        } finally {
            this.isLaunching = false;
            this._isLaunching = false;
        }
    }
}

registry
    .category("systray")
    .add("ai.systray_action", { Component: SystrayAction }, { sequence: 30 });
