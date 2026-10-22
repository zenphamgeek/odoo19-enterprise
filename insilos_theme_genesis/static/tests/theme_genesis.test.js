/** @odoo-module **/

import { expect, test } from "@insilos/hoot";
import { animationFrame } from "@insilos/hoot-mock";
import { contains, mountWithCleanup, assignDialogTestEnv } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { FloatingBatchActionBar } from "@insilos_theme_genesis/views/list/floating_action_bar/floating_action_bar";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { ErrorDialog } from "@web/core/errors/error_dialogs";
import { browser } from "@web/core/browser/browser";

defineMailModels();

test("@insilos_theme_genesis/floating_action_bar/renders selected count and handles approve action", async () => {
    let approved = false;
    await mountWithCleanup(FloatingBatchActionBar, {
        props: {
            selectedCount: 5,
            totalCount: 10,
            isDomainSelected: false,
            onApprove: () => {
                approved = true;
            },
        },
    });
    await animationFrame();

    expect(".o_floating_batch_action_bar").toHaveCount(1);
    expect(".o_selected_count").toHaveText("5");
    expect(".is-floating-bar-text").toHaveText("selected");
    expect(".is-floating-btn-approve").toHaveCount(1);

    await contains(".is-floating-btn-approve").click();
    expect(approved).toBe(true);
});

test("@insilos_theme_genesis/floating_action_bar/displays domain indicator when all in domain selected", async () => {
    await mountWithCleanup(FloatingBatchActionBar, {
        props: {
            selectedCount: 42,
            isDomainSelected: true,
            totalCount: 42,
        },
    });
    await animationFrame();

    expect(".o_selected_count").toHaveText("42");
    expect(".is-floating-bar-badge .badge.bg-secondary").toHaveText("(All in domain)");
});

test("@insilos_theme_genesis/floating_action_bar/triggers export, archive, delete, discard callbacks", async () => {
    const events = [];
    await mountWithCleanup(FloatingBatchActionBar, {
        props: {
            selectedCount: 3,
            totalCount: 10,
            canExport: true,
            canArchive: true,
            canDelete: true,
            onExport: () => events.push("export"),
            onArchive: () => events.push("archive"),
            onDelete: () => events.push("delete"),
            onDiscard: () => events.push("discard"),
        },
    });
    await animationFrame();

    expect(".is-floating-btn-export").toHaveCount(1);
    expect(".is-floating-btn-archive").toHaveCount(1);
    expect(".is-floating-btn-delete").toHaveCount(1);
    expect(".is-floating-btn-close").toHaveCount(1);

    await contains(".is-floating-btn-export").click();
    expect(events).toEqual(["export"]);

    await contains(".is-floating-btn-archive").click();
    expect(events).toEqual(["export", "archive"]);

    await contains(".is-floating-btn-delete").click();
    expect(events).toEqual(["export", "archive", "delete"]);

    await contains(".is-floating-btn-close").click();
    expect(events).toEqual(["export", "archive", "delete", "discard"]);
});

test("@insilos_theme_genesis/floating_action_bar/respects permission gates", async () => {
    await mountWithCleanup(FloatingBatchActionBar, {
        props: {
            selectedCount: 2,
            canPrint: false,
            canExport: false,
            canArchive: false,
            canDelete: false,
            onExport: () => {},
            onArchive: () => {},
            onDelete: () => {},
        },
    });
    await animationFrame();

    expect(".is-floating-btn-print").toHaveCount(0);
    expect(".is-floating-btn-export").toHaveCount(0);
    expect(".is-floating-btn-archive").toHaveCount(0);
    expect(".is-floating-btn-delete").toHaveCount(0);
});

test("@insilos_theme_genesis/user_menu/applyTheme toggles dark and light mode classes and attributes", () => {
    const userMenuProto = UserMenu.prototype;
    expect(typeof userMenuProto.applyTheme).toBe("function");

    // Apply dark mode
    userMenuProto.applyTheme("dark");
    expect(document.body.classList.contains("o_dark_mode")).toBe(true);
    expect(document.documentElement.classList.contains("o_dark_mode")).toBe(true);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-bs-theme")).toBe("dark");

    // Apply light mode
    userMenuProto.applyTheme("light");
    expect(document.body.classList.contains("o_dark_mode")).toBe(false);
    expect(document.documentElement.classList.contains("o_dark_mode")).toBe(false);
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(document.documentElement.getAttribute("data-bs-theme")).toBe("light");
});

test("@insilos_theme_genesis/design_tokens/sovereign dark mode tokens architecture", () => {
    const rootStyle = getComputedStyle(document.documentElement);
    expect(typeof rootStyle.getPropertyValue).toBe("function");
});

test("@insilos_theme_genesis/runtime_error_reporting/POST https://report.insilos.com/api/v1/runtime-report dispatches error and updates UI", async () => {
    assignDialogTestEnv();

    const prevInsilos = window.insilos;
    window.insilos = {
        ...(prevInsilos || {}),
        session_info: {
            ...(prevInsilos?.session_info || {}),
            allow_external_telemetry: true,
        },
    };

    const fetchCalls = [];
    const origFetch = browser.fetch;
    const mockFetch = async (url, options) => {
        fetchCalls.push({ url, options });
        if (url === "/insilos/runtime_error/relay") {
            // Simulate local relay down to verify fallback to central production gateway
            return { ok: false, status: 502, json: async () => ({ error: "Relay offline" }) };
        }
        if (url === "https://report.insilos.com/api/v1/runtime-report") {
            return {
                ok: true,
                status: 201,
                json: async () => ({
                    status: "created",
                    incident_code: "INC-2026-99123",
                    asset: "O20",
                    message: "Incident ingested, verified and registered successfully.",
                }),
            };
        }
        return origFetch ? origFetch(url, options) : { ok: false };
    };

    Object.defineProperty(browser, "fetch", { value: mockFetch, configurable: true, writable: true });

    try {
        await mountWithCleanup(ErrorDialog, {
            props: {
                message: "Critical UI Rendering Failure",
                name: "RenderingCrash",
                traceback: "Error: Crash\n    at eval (owl.js:100:12)",
                close() {},
            },
        });
        await animationFrame();

        expect(".o_insilos_share_error_btn").toHaveCount(1);
        expect(".o_insilos_share_error_btn").toHaveText("⚡ Send Incident Report");

        await contains(".o_insilos_share_error_btn").click();
        await animationFrame();

        // Filter specifically for error reporting calls
        const reportCalls = fetchCalls.filter(c => c.url.includes("runtime"));
        expect(reportCalls.length).toBe(2);
        expect(reportCalls[0].url).toBe("/insilos/runtime_error/relay");
        expect(reportCalls[1].url).toBe("https://report.insilos.com/api/v1/runtime-report");
        expect(reportCalls[1].options.method).toBe("POST");
        expect(reportCalls[1].options.headers["Content-Type"]).toBe("application/json");

        const sentPayload = JSON.parse(reportCalls[1].options.body);
        expect(sentPayload.name).toBe("RenderingCrash");
        expect(sentPayload.message).toBe("Critical UI Rendering Failure");

        // Assert UI confirmation reflecting incident code from report.insilos.com
        expect(".o_insilos_share_error_btn").toHaveText("Đã gửi báo cáo (INC-2026-99123)");
        expect(".o_insilos_share_error_btn .fa-check").toHaveCount(1);
    } finally {
        window.insilos = prevInsilos;
        Object.defineProperty(browser, "fetch", { value: origFetch, configurable: true, writable: true });
    }
});

