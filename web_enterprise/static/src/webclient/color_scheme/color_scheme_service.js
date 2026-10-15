import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { user } from "@web/core/user";

const serviceRegistry = registry.category("services");

export function systemColorScheme() {
    return browser.matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light";
}

export function currentColorScheme() {
    return cookie.get("color_scheme");
}

export const blockingWebClient = Promise.withResolvers();

export const colorSchemeService = {
    async start() {
        const current = currentColorScheme();
        const savedLocalTheme = browser.localStorage?.getItem("insilos_theme");
        const preferred = current || savedLocalTheme;
        let newColorScheme = "light";
        if (preferred === "light" || current === "light" || savedLocalTheme === "light") {
            newColorScheme = "light";
        } else if (preferred === "dark" || current === "dark" || savedLocalTheme === "dark") {
            newColorScheme = "dark";
        } else if (["light", "dark"].includes(user.settings?.color_scheme)) {
            newColorScheme = user.settings.color_scheme;
        } else {
            newColorScheme = systemColorScheme();
        }
        if (newColorScheme !== current) {
            cookie.set("color_scheme", newColorScheme);
            if (current || (!current && newColorScheme === "dark")) {
                this.reload();
                await blockingWebClient.promise; // block WebClient rendering to avoid flickering
            }
        }
        const effective = newColorScheme;
        if (effective === "dark") {
            document.documentElement.setAttribute("data-bs-theme", "dark");
            document.documentElement.setAttribute("data-theme", "dark");
            document.documentElement.classList.add("o_dark_mode");
            if (document.body) {
                document.body.classList.add("o_dark_mode");
                document.body.setAttribute("data-bs-theme", "dark");
                document.body.setAttribute("data-theme", "dark");
            }
        } else {
            document.documentElement.classList.remove("o_dark_mode");
            document.documentElement.setAttribute("data-bs-theme", "light");
            document.documentElement.setAttribute("data-theme", "light");
            if (document.body) {
                document.body.classList.remove("o_dark_mode");
                document.body.setAttribute("data-bs-theme", "light");
                document.body.setAttribute("data-theme", "light");
            }
            if (cookie.get("color_scheme") !== "light") {
                cookie.set("color_scheme", "light");
            }
        }
        return {
            get systemColorScheme() {
                return systemColorScheme();
            },
            get currentColorScheme() {
                return currentColorScheme();
            },
            get userColorScheme() {
                return user.settings.color_scheme;
            },
            switchToColorScheme: async (scheme) => {
                await this.switchToColorScheme(scheme);
            },
        };
    },
    async switchToColorScheme(scheme) {
        const effective =
            scheme === "dark"
                ? "dark"
                : scheme === "light"
                ? "light"
                : systemColorScheme();
        browser.localStorage?.setItem("insilos_theme", scheme);
        cookie.set("color_scheme", effective);
        try {
            await user.setUserSettings("color_scheme", scheme);
        } catch {
            // Ignore RPC failure and rely on cookie/localStorage
        }
        this.reload();
    },
    reload() {
        if (
            window.location?.search?.includes("access_token=") &&
            (window.location.pathname.startsWith("/insilos/") ||
                window.location.pathname.startsWith("/odoo/"))
        ) {
            window.history.replaceState(null, "", window.location.pathname + window.location.hash);
        }
        browser.location.reload();
    },
};
serviceRegistry.add("color_scheme", colorSchemeService);
