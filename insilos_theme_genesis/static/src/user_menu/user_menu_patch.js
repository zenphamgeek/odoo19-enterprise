import { useState } from "@insilos/owl";
import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { user } from "@web/core/user";

patch(UserMenu.prototype, {
    setup() {
        super.setup();
        const cookieScheme = cookie.get("color_scheme");
        const localTheme = localStorage.getItem("insilos_theme");
        const savedTheme =
            cookieScheme === "dark" || cookieScheme === "light"
                ? cookieScheme
                : localTheme === "dark" || localTheme === "light" || localTheme === "auto"
                ? localTheme
                : "light";
        const targetScheme =
            savedTheme === "dark" ||
            (savedTheme === "auto" &&
                window.matchMedia &&
                window.matchMedia("(prefers-color-scheme: dark)").matches)
                ? "dark"
                : "light";
        localStorage.setItem("insilos_theme", savedTheme);
        cookie.set("color_scheme", targetScheme, 365 * 24 * 60 * 60);
        document.cookie =
            "color_scheme=" + targetScheme + "; path=/; max-age=31536000; SameSite=Lax";
        this.insilosTheme = useState({
            current: savedTheme,
        });
        // Initial theme application
        this.applyTheme(savedTheme);
    },

    async setTheme(mode) {
        let isDark = false;
        if (mode === "dark") {
            isDark = true;
        } else if (mode === "light") {
            isDark = false;
        } else if (mode === "auto") {
            isDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
        }
        const targetScheme = isDark ? "dark" : "light";

        this.insilosTheme.current = mode;
        localStorage.setItem("insilos_theme", mode);
        cookie.set("color_scheme", targetScheme, 365 * 24 * 60 * 60);
        document.cookie =
            "color_scheme=" + targetScheme + "; path=/; max-age=31536000; SameSite=Lax";
        this.applyTheme(mode);

        try {
            await user.setUserSettings("color_scheme", mode === "auto" ? "system" : targetScheme);
        } catch {
            // Fallback to cookie/localStorage if user settings RPC is unavailable
        }

        if (
            window.location?.search?.includes("access_token=") &&
            (window.location.pathname.startsWith("/insilos/") ||
                window.location.pathname.startsWith("/odoo/"))
        ) {
            window.history.replaceState(null, "", window.location.pathname + window.location.hash);
        }

        if (browser?.location?.reload) {
            browser.location.reload();
        } else {
            window.location.reload();
        }
    },

    applyTheme(mode) {
        let isDark = false;
        if (mode === "dark") {
            isDark = true;
        } else if (mode === "light") {
            isDark = false;
        } else if (mode === "auto") {
            isDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
        } else {
            const cookieScheme = cookie.get("color_scheme");
            if (cookieScheme === "dark" || cookieScheme === "light") {
                isDark = cookieScheme === "dark";
            } else {
                const saved = localStorage.getItem("insilos_theme");
                isDark = saved === "dark";
            }
        }

        if (isDark) {
            document.documentElement.classList.add("o_dark_mode");
            document.documentElement.setAttribute("data-theme", "dark");
            document.documentElement.setAttribute("data-bs-theme", "dark");
            if (document.body) {
                document.body.classList.add("o_dark_mode");
                document.body.setAttribute("data-theme", "dark");
                document.body.setAttribute("data-bs-theme", "dark");
            }
            for (const link of document.querySelectorAll('link[rel="stylesheet"]')) {
                const href = link.getAttribute("href") || "";
                if (href.includes("web.assets_web.") && !href.includes("web.assets_web_dark")) {
                    link.setAttribute(
                        "href",
                        href.replace("web.assets_web.", "web.assets_web_dark.")
                    );
                }
            }
        } else {
            document.documentElement.classList.remove("o_dark_mode");
            document.documentElement.setAttribute("data-theme", "light");
            document.documentElement.setAttribute("data-bs-theme", "light");
            if (document.body) {
                document.body.classList.remove("o_dark_mode");
                document.body.setAttribute("data-theme", "light");
                document.body.setAttribute("data-bs-theme", "light");
            }
            for (const link of document.querySelectorAll('link[rel="stylesheet"]')) {
                const href = link.getAttribute("href") || "";
                if (href.includes("web.assets_web_dark")) {
                    link.setAttribute(
                        "href",
                        href.replace("web.assets_web_dark", "web.assets_web")
                    );
                }
            }
        }
    },
});
