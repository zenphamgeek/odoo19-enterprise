import { useState } from "@insilos/owl";
import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { cookie } from "@web/core/browser/cookie";
import { user } from "@web/core/user";

patch(UserMenu.prototype, {
    setup() {
        super.setup();
        const cookieScheme = cookie.get("color_scheme");
        const savedTheme =
            cookieScheme === "dark" || cookieScheme === "light"
                ? cookieScheme
                : localStorage.getItem("insilos_theme") || "light";
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
        const currentCookie = cookie.get("color_scheme");

        this.insilosTheme.current = mode;
        localStorage.setItem("insilos_theme", mode);
        cookie.set("color_scheme", targetScheme, 365 * 24 * 60 * 60, "lax");
        this.applyTheme(mode);

        try {
            await user.setUserSettings("color_scheme", mode === "auto" ? "system" : targetScheme);
        } catch {
            // Fallback to cookie/localStorage if user settings RPC is unavailable
        }

        if (currentCookie !== targetScheme) {
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
            const saved = localStorage.getItem("insilos_theme");
            if (saved) {
                isDark = saved === "dark";
            } else {
                isDark = cookie.get("color_scheme") === "dark";
            }
        }

        if (isDark) {
            document.body.classList.add("o_dark_mode");
            document.documentElement.classList.add("o_dark_mode");
            document.documentElement.setAttribute("data-theme", "dark");
            document.documentElement.setAttribute("data-bs-theme", "dark");
        } else {
            document.body.classList.remove("o_dark_mode");
            document.documentElement.classList.remove("o_dark_mode");
            document.documentElement.setAttribute("data-theme", "light");
            document.documentElement.setAttribute("data-bs-theme", "light");
        }
    },
});
