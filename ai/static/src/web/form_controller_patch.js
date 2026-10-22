import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { useEffect } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.aiChatLauncher = useService("aiChatLauncher");
        this.mailStore = useService("mail.store");
        const openAiChat = (ev) => this.openAiChat(ev.detail.origin);
        useEffect(
            () => {
                this.env.bus.addEventListener("AI:OPEN_AI_CHAT", openAiChat);
                return () => this.env.bus.removeEventListener("AI:OPEN_AI_CHAT", openAiChat);
            },
            () => []
        );
    },

    async openAiChat(callerComponentName) {
        if (this._aiChatDispatching) {
            return;
        }
        this._aiChatDispatching = true;
        try {
            if (this.model?.root?.isNew) {
                const saved = await this.model.root.save();
                if (!saved) {
                    return;
                }
            }
            const recordModel = this.model?.root?.resModel;
            const recordId = this.model?.root?.resId;
            const channelTitle = typeof this.displayName === "function" ? this.displayName() : (this.model?.root?.data?.display_name || "Insilos AI Copilot");

            // Allowlist projection: Exclude passwords, hashes, financial accounts, and tokens
            const rawData = this.model?.root?.data || {};
            const safeRecordData = {};
            const FORBIDDEN_KEYS = /password|secret|token|hash|auth|credit|bank|salary|ssn|tax_id/i;
            for (const [k, v] of Object.entries(rawData)) {
                if (!FORBIDDEN_KEYS.test(k) && (typeof v !== "object" || v === null || Array.isArray(v))) {
                    safeRecordData[k] = v;
                }
            }

            await this.aiChatLauncher.launchAIChat({
                callerComponentName: callerComponentName || "chatter_ai_button",
                channelTitle: channelTitle || "Insilos AI Copilot",
                recordModel,
                recordId,
                originalRecordData: safeRecordData,
                originalRecordFields: this.model?.root?.fields || {},
                aiChatSourceId: recordId,
            });
        } catch (err) {
            console.error("[Insilos AI Copilot] Error in openAiChat:", err);
            // Fallback: launch general AI chat without crashing
            await this.aiChatLauncher.launchAIChat({
                callerComponentName: "systray_ai_button",
                channelTitle: "Insilos AI Copilot",
            });
        } finally {
            this._aiChatDispatching = false;
        }
    },
});
