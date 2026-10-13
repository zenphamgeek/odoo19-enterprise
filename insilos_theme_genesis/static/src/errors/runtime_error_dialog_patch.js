import { patch } from "@web/core/utils/patch";
import { ErrorDialog } from "@web/core/errors/error_dialogs";
import { browser } from "@web/core/browser/browser";

// Sanitizer for Privacy and Security (Redact passwords, bearer tokens, session ids)
function sanitizeErrorPayload(text) {
    if (!text || typeof text !== "string") {
        return "";
    }
    return text
        .replace(/(password|passwd|pwd|secret|token|authorization)["']?\s*[:=]\s*["']?[^"'\s&,]+/gi, "$1=[REDACTED]")
        .replace(/Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*/gi, "Bearer [REDACTED]")
        .replace(/(session_id|sid)=[^;&\s]+/gi, "$1=[REDACTED]")
        .replace(/(0[3|5|7|8|9])+([0-9]{8})\b/g, "$1****$2");
}

patch(ErrorDialog.prototype, {
    setup() {
        super.setup();
        this.state.sharingError = false;
        this.state.sharingSuccess = false;
        this.state.incidentCode = "";
    },

    async onClickShareRuntimeError() {
        if (this.state.sharingError || this.state.sharingSuccess) {
            return;
        }
        this.state.sharingError = true;

        const payload = {
            name: this.props.name || "ClientRuntimeError",
            message: sanitizeErrorPayload(this.props.message || ""),
            traceback: sanitizeErrorPayload(this.props.traceback || this.traceback || ""),
            contextDetails: this.contextDetails || "",
            url: window.location.href,
            server_host: window.location.host,
            user_agent: browser.navigator.userAgent,
            timestamp: Math.floor(Date.now() / 1000),
        };

        try {
            // First attempt: Call local instance relay endpoint
            const res = await browser.fetch("/insilos/runtime_error/relay", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });

            if (res.ok) {
                const data = await res.json();
                const code = data?.result?.incident_code || data?.incident_code || "INC-SUBMITTED";
                this.state.incidentCode = code;
                this.state.sharingSuccess = true;
            } else {
                // Direct fallback to central report endpoint if local relay unavailable
                const directRes = await browser.fetch("https://report.insilos.com/api/v1/runtime-report", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                });
                if (directRes.ok) {
                    const directData = await directRes.json();
                    this.state.incidentCode = directData.incident_code || "INC-DIRECT";
                    this.state.sharingSuccess = true;
                }
            }
        } catch (err) {
            console.warn("Failed to dispatch runtime error report:", err);
        } finally {
            this.state.sharingError = false;
        }
    },
});
