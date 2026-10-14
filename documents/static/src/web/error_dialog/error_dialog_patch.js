import { ErrorDialog, sanitizeErrorPayload } from "@web/core/errors/error_dialogs";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

export class SanitizedCopyButton extends CopyButton {
    async onClick() {
        try {
            let rawContent = typeof this.props.content === "function"
                ? this.props.content()
                : this.props.content;

            // Universal Text Normalization Barrier
            let textToSanitize = "";
            if (typeof rawContent === "string" || rawContent instanceof String) {
                textToSanitize = String(rawContent);
            } else if (rawContent !== null && rawContent !== undefined) {
                try {
                    // Safe serialization guarding against cyclic graphs
                    const seen = new WeakSet();
                    textToSanitize = JSON.stringify(rawContent, (key, value) => {
                        if (typeof value === "object" && value !== null) {
                            if (seen.has(value)) {
                                return "[Circular Reference]";
                            }
                            seen.add(value);
                        }
                        return value;
                    }, 2);
                } catch (serializeErr) {
                    textToSanitize = String(rawContent);
                }
            }

            // Payload length bulkhead clamp (64KB)
            if (textToSanitize.length > 65536) {
                textToSanitize = textToSanitize.slice(0, 65536) + "\n...[TRUNCATED: Exceeded 64KB Sanitization Bulkhead]";
            }

            const sanitized = sanitizeErrorPayload(textToSanitize);
            await browser.navigator.clipboard.writeText(sanitized);
        } catch (error) {
            browser.console.warn("Clipboard sanitized write failed:", error);
            // Safe fallback to prevent complete user disruption
            await browser.navigator.clipboard.writeText("[Error payload scrubbed due to internal parsing constraint]");
        }
        this.showTooltip();
    }
}

patch(ErrorDialog.components, {
    CopyButton: SanitizedCopyButton,
});

patch(ErrorDialog.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.contextDetails && !this.contextDetails.startsWith("[SANITIZATION_FAILED]")) {
            try {
                this.contextDetails = sanitizeErrorPayload(this.contextDetails);
            } catch (err) {
                this.contextDetails = "[SANITIZATION_FAILED] Context suppressed for security.";
            }
        }
    },

    onClickClipboard() {
        const rawTraceback = this.traceback || this.props.traceback || "";
        // Bounded length protection (Max 128KB to prevent main-thread ReDoS)
        const clampedTraceback = rawTraceback.length > 131072
            ? rawTraceback.slice(0, 131072) + "\n\n[TRUNCATED: Traceback exceeded 128KB limit]"
            : rawTraceback;

        let payload = `${this.props.name || ""}\n\n${this.props.message || ""}\n\n${this.contextDetails || ""}\n\n${clampedTraceback}`;
        try {
            payload = sanitizeErrorPayload(payload);
        } catch (err) {
            browser.console.warn("Sanitization pass failed; falling back to scrubbed header:", err);
            payload = `${this.props.name || "Error"}\n\n${this.props.message || "An error occurred."}\n\n[PAYLOAD_SCRUBBED_DUE_TO_PARSING_FAILURE]`;
        }

        browser.navigator.clipboard.writeText(payload);
        this.showTooltip();
    },
});
// Legacy Share button removed in favor of native Insilos Incident Reporting
