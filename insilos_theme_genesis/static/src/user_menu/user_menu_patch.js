import { useState } from "@insilos/owl";
import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { cookie } from "@web/core/browser/cookie";

patch(UserMenu.prototype, {
    setup() {
        super.setup();
        const cookieScheme = cookie.get("color_scheme");
        const savedTheme = localStorage.getItem("insilos_theme") || (cookieScheme === "dark" ? "dark" : "light");
        this.insilosTheme = useState({
            current: savedTheme,
        });
        // Initial theme application
        this.applyTheme(savedTheme);
    },

    setTheme(mode) {
        this.insilosTheme.current = mode;
        localStorage.setItem("insilos_theme", mode);
        this.applyTheme(mode);
    },

    applyTheme(mode) {
        let isDark = false;
        if (mode === "dark") {
            isDark = true;
        } else if (mode === "light") {
            isDark = false;
        } else if (mode === "auto") {
            isDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
        }

        // If not explicitly configured in localStorage, adhere to system color_scheme cookie
        const explicitStorage = localStorage.getItem("insilos_theme");
        if (!explicitStorage && cookie.get("color_scheme") === "dark") {
            isDark = true;
        }

        if (isDark) {
            document.body.classList.add("o_dark_mode");
            document.documentElement.classList.add("o_dark_mode");
            document.documentElement.setAttribute("data-theme", "dark");
            document.documentElement.setAttribute("data-bs-theme", "dark");
        } else {
            if (cookie.get("color_scheme") !== "dark") {
                document.body.classList.remove("o_dark_mode");
                document.documentElement.classList.remove("o_dark_mode");
                document.documentElement.setAttribute("data-theme", "light");
                document.documentElement.setAttribute("data-bs-theme", "light");
            }
        }
    },
});
