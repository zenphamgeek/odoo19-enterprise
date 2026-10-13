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

import { onMounted } from "@insilos/owl";

patch(ErrorDialog.prototype, {
    setup() {
        super.setup();
        if (this.state) {
            this.state.sharingError = false;
            this.state.sharingSuccess = false;
            this.state.incidentCode = "";
        }
        onMounted(() => {
            // Remove redundant legacy Share buttons from footer
            const footer = document.querySelector(".o_error_dialog .modal-footer");
            if (footer) {
                const buttons = footer.querySelectorAll("button");
                buttons.forEach((btn) => {
                    const txt = (btn.textContent || "").trim().toLowerCase();
                    if (
                        !btn.classList.contains("o_insilos_share_error_btn") &&
                        !btn.classList.contains("o-default-button") &&
                        (txt === "share" || txt.includes("share") || btn.getAttribute("t-on-click") === "shareTraceback")
                    ) {
                        btn.remove();
                    }
                });
            }
        });
    },

    async onClickShareRuntimeError() {
        if (!this.state || this.state.sharingError || this.state.sharingSuccess) {
            return;
        }
        this.state.sharingError = true;

        const errorName = this.props.data?.name || this.props.exceptionName || this.props.name || "ClientRuntimeError";
        const errorMsg = this.props.data?.message || this.props.message || (this.props.data ? JSON.stringify(this.props.data) : "");
        const rawTraceback = this.traceback || this.props.traceback || this.props.data?.debug || "";

        const payload = {
            name: String(errorName),
            message: sanitizeErrorPayload(String(errorMsg)),
            traceback: sanitizeErrorPayload(String(rawTraceback)),
            contextDetails: this.contextDetails || "",
            url: window.location.href,
            server_host: window.location.host,
            user_agent: browser.navigator.userAgent,
            timestamp: Math.floor(Date.now() / 1000),
        };

        try {
            let reported = false;

            // Attempt 1: Local instance relay endpoint
            try {
                const res = await browser.fetch("/insilos/runtime_error/relay", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                });

                if (res.ok) {
                    const data = await res.json();
                    const code = data?.incident_code || data?.result?.incident_code || "INC-SUBMITTED";
                    this.state.incidentCode = code;
                    this.state.sharingSuccess = true;
                    reported = true;
                }
            } catch (relayErr) {
                console.warn("[Insilos] Local relay dispatch failed, attempting direct gateway:", relayErr);
            }

            // Attempt 2: Direct fallback to central report endpoint if local relay failed
            if (!reported) {
                const directRes = await browser.fetch("https://report.insilos.com/api/v1/runtime-report", {
                    method: "POST",
                    mode: "cors",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                });
                if (directRes.ok) {
                    const directData = await directRes.json();
                    const code = directData?.incident_code || directData?.result?.incident_code || "INC-DIRECT";
                    this.state.incidentCode = code;
                    this.state.sharingSuccess = true;
                    reported = true;
                }
            }

            if (!reported) {
                this.state.incidentCode = "ERR-NET";
            }
        } catch (err) {
            console.warn("[Insilos] Failed to dispatch runtime error report:", err);
            this.state.incidentCode = "ERR-FAIL";
        } finally {
            this.state.sharingError = false;
        }
    },
});
