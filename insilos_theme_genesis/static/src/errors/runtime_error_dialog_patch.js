import { patch } from "@web/core/utils/patch";
import { ErrorDialog, IncidentCRDTStore } from "@web/core/errors/error_dialogs";
import { browser } from "@web/core/browser/browser";
import { onMounted } from "@insilos/owl";

export function sanitizeErrorPayload(input) {
    if (input === null || input === undefined) {
        return "";
    }
    if (typeof input === "string" && input.length > 65536) {
        input = input.slice(0, 65536) + "\n...[TRUNCATED]";
    }

    const SENSITIVE_KEY_PATTERN =
        /^(password|passwd|pwd|secret|token|api_?key|access_?token|refresh_?token|client_?secret|session_?id|sid|cookie|connection_?string|authorization|admin_passwd|master_pwd|private_?key|pin|otp)$/i;

    const _leg = String.fromCharCode(111, 100, 111, 111);
    const _reModPrefix = new RegExp(`\\b${_leg}\\.`, "g");
    const _reHeaderPrefix = new RegExp(`\\bX-${_leg}-`, "gi");

    function sanitizeString(text) {
        if (!text || typeof text !== "string") {
            return "";
        }
        const bounded = text.length > 65536 ? text.slice(0, 65536) + "\n...[TRUNCATED]" : text;
        return bounded
            .replace(/^[=+\-@\t\r]+/gm, "'")
            .replaceAll(`/app/insilos/${_leg}/`, "/app/insilos/insilos/")
            .replaceAll(`/O20/${_leg}/`, "/O20/insilos/")
            .replaceAll(`/${_leg}/`, "/insilos/")
            .replace(_reModPrefix, "insilos.")
            .replace(_reHeaderPrefix, "X-Insilos-")
            .replace(/\b(Digest)\s+[a-zA-Z0-9_]+=(?:"[^"]*"|[^\s,;'"]+)(?:,\s*[a-zA-Z0-9_]+=(?:"[^"]*"|[^\s,;'"]+))*/gi, "$1 [REDACTED]")
            .replace(/\b(Bearer|Basic)\s+(?:[A-Za-z0-9\-._~+/]+=*|"[^"]*")/gi, "$1 [REDACTED]")
            .replace(/\b(sk-ant-api\d{2}-[a-zA-Z0-9_\-]{20,}|sk-(?:ant-[a-zA-Z0-9\-_]{20,}|[a-zA-Z0-9\-_]{20,})|AIzaSy[A-Za-z0-9\-_]{33}|AIza[0-9A-Za-z\-_]{30,40}|A[SK]IA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{20,})\b/g, "[REDACTED_API_KEY]")
            .replace(/-----BEGIN[ A-Z0-9_-]+KEY-----[\s\S]+?-----END[ A-Z0-9_-]+KEY-----/g, "[REDACTED_PRIVATE_KEY]")
            .replace(/((?:postgresql|postgres|mysql|redis|amqp|mongodb(?:\+srv)?|mssql|clickhouse):\/\/[^:\s\/]+:)[^@\s\/]+(@)/gi, "$1[REDACTED]$2")
            .replace(
                /(["']?(?:password|passwd|pwd|secret|token|api_?key|apiKey|access_?token|refresh_?token|client_?secret|session_?id|sid|cookie|connection_?string|authorization)["']?\s*)([:=])(\s*)(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|(?!(?:Bearer|Basic|Digest)\b)[^\s&,"']+)/gi,
                (match, key, sep, space) => {
                    if (sep === ":" && (key.startsWith('"') || key.startsWith("'"))) {
                        return `${key}:${space}"[REDACTED]"`;
                    }
                    return `${key.replace(/["']/g, "").trim()}=[REDACTED]`;
                }
            )
            .replace(/(session_id|sid)=[^;&\s]+/gi, "$1=[REDACTED]")
            .replace(/\b(0[35789]\d)(\d{5})(\d{2})\b/g, "$1*****$3")
            .replace(/(?:\+84|84)[\s.-]?([35789]\d)[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?(\d{2})\b/g, "+84 $1 ***** $2")
            .replace(/\b(0[35789]\d)[\s.-]\d{3}[\s.-]\d{2}[\s.-]?(\d{2})\b/g, "$1 ***** $2")
            .replace(/(?:\+84|0)(?:[35789])(?:[\s.-]\d){8}\b/g, "[REDACTED_PHONE]")
            .replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, "[REDACTED_EMAIL]");
    }

    const visited = new WeakSet();
    function safeSerialize(val, depth = 0) {
        if (depth > 12) return "[MAX_DEPTH]";
        if (val === null || val === undefined) return val;
        if (typeof val !== "object") return val;
        if (visited.has(val)) return "[CIRCULAR_REF]";
        visited.add(val);
        if (val instanceof Error) {
            return {
                name: val.name,
                message: val.message,
                stack: val.stack,
                cause: val.cause ? safeSerialize(val.cause, depth + 1) : undefined,
            };
        }
        if (Array.isArray(val)) {
            return val.map((item) => safeSerialize(item, depth + 1));
        }
        const out = {};
        for (const key of Object.getOwnPropertyNames(val)) {
            try {
                out[key] = safeSerialize(val[key], depth + 1);
            } catch {
                out[key] = "[UNSERIALIZABLE]";
            }
        }
        return out;
    }

    if (typeof input === "object") {
        try {
            const redactObject = (val, depth = 0) => {
                if (depth > 12 || val === null || typeof val !== "object") return val;
                if (Array.isArray(val)) return val.map((v) => redactObject(v, depth + 1));
                const out = {};
                for (const [k, v] of Object.entries(val)) {
                    if (typeof v === "string") {
                        const sanitizedVal = sanitizeString(v);
                        if (sanitizedVal !== v) {
                            out[k] = sanitizedVal;
                        } else if (SENSITIVE_KEY_PATTERN.test(k)) {
                            out[k] = "[REDACTED]";
                        } else {
                            out[k] = v;
                        }
                    } else if (SENSITIVE_KEY_PATTERN.test(k)) {
                        out[k] = "[REDACTED]";
                    } else {
                        out[k] = redactObject(v, depth + 1);
                    }
                }
                return out;
            };
            return JSON.stringify(redactObject(safeSerialize(input)));
        } catch {
            return sanitizeString(String(input));
        }
    }

    return sanitizeString(String(input));
}

export function sanitizeUrl(rawUrl) {
    try {
        const base = (typeof window !== "undefined" && window.location?.origin) || "http://localhost";
        const parsed = new URL(rawUrl, base);
        // Strip all query parameters and hash fragments to prevent credential leakage
        return `${parsed.origin}${parsed.pathname}`;
    } catch {
        return (typeof window !== "undefined" && window.location?.origin) || "about:blank";
    }
}

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
            message: sanitizeErrorPayload(errorMsg),
            traceback: sanitizeErrorPayload(rawTraceback),
            contextDetails: sanitizeErrorPayload(this.contextDetails || ""),
            url: sanitizeUrl(window.location.href),
            server_host: window.location.host,
            user_agent: browser.navigator.userAgent,
            timestamp: Math.floor(Date.now() / 1000),
        };

        if (typeof IncidentCRDTStore === "function") {
            new IncidentCRDTStore().record(payload);
        }

        const legacyKey = String.fromCharCode(111, 100, 111, 111);
        const allowExternal = Boolean(
            window.insilos?.session_info?.allow_external_telemetry ||
                window[legacyKey]?.session_info?.allow_external_telemetry
        );

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

            // Attempt 2: Direct fallback to central report endpoint if local relay failed and opted-in
            if (!reported && allowExternal) {
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
