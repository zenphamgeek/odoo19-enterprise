/** @odoo-module **/

import { expect, test } from "@insilos/hoot";
import "@insilos_website/js/innoria_i18n_unified";

test("@insilos_website/i18n/exposes global semantic phrase dictionary and header CTA mappings", () => {
    expect(Boolean(window.innoriaI18n)).toBe(true);
    expect(window.INNORIA_SEMANTIC_PHRASES["Đăng nhập"]).toBe("Sign in");
    expect(window.INNORIA_SEMANTIC_PHRASES["Liên hệ"]).toBe("Contact us");
    expect(window.INNORIA_REVERSE_PHRASES["contact us"]).toBe("Liên hệ");
    expect(window.INNORIA_REVERSE_PHRASES["sign in"]).toBe("Đăng nhập");
});

test("@insilos_website/i18n/translates data-i18n-vi and data-i18n-en attributes and placeholders bi-directionally", () => {
    const container = document.createElement("div");
    container.innerHTML = `<span class="login-lbl" data-i18n-vi="Đăng nhập" data-i18n-en="Sign in">Đăng nhập</span><span class="cta-lbl" data-i18n-vi="Liên hệ" data-i18n-en="Contact us">Liên hệ</span><input class="email-inp" data-i18n-placeholder-vi="Nhập email..." data-i18n-placeholder-en="Enter email..." placeholder="Nhập email..."/>`;

    window.innoriaI18n.translatePage("en", container);

    expect(container.querySelector(".login-lbl").textContent).toBe("Sign in");
    expect(container.querySelector(".cta-lbl").textContent).toBe("Contact us");
    expect(container.querySelector(".email-inp").getAttribute("placeholder")).toBe("Enter email...");

    window.innoriaI18n.translatePage("vi", container);

    expect(container.querySelector(".login-lbl").textContent).toBe("Đăng nhập");
    expect(container.querySelector(".cta-lbl").textContent).toBe("Liên hệ");
    expect(container.querySelector(".email-inp").getAttribute("placeholder")).toBe("Nhập email...");
});

test("@insilos_website/i18n/translates semantic text blocks across VI and EN without corrupting child SVG icons", () => {
    const container = document.createElement("div");
    container.innerHTML = `<a class="btn"><svg class="ph-duotone ph-sign-in"><use href="#ph-sign-in"/></svg><span class="lbl">Sản Phẩm</span></a><p class="desc">Hệ thống tài khoản Thông tư 200, quyết toán thuế minh bạch</p>`;

    window.innoriaI18n.translatePage("en", container);

    expect(container.querySelector(".lbl").textContent).toBe("Products");
    expect(container.querySelector(".desc").textContent).toBe(
        "Circular 200/2014 chart of accounts, IFRS mapping, and transparent tax reconciliation"
    );
    expect(container.querySelectorAll("svg.ph-duotone.ph-sign-in").length).toBe(1);

    window.innoriaI18n.translatePage("vi", container);

    expect(container.querySelector(".lbl").textContent).toBe("Sản Phẩm");
    expect(container.querySelector(".desc").textContent).toBe(
        "Hệ thống tài khoản Thông tư 200, quyết toán thuế minh bạch"
    );
    expect(container.querySelectorAll("svg.ph-duotone.ph-sign-in").length).toBe(1);
});

test("@insilos_website/dropzone/wires priority file attachment dropzone and updates SLA status badge", () => {
    const container = document.createElement("div");
    container.className = "innoria-priority-dropzone";
    container.innerHTML = `<span class="innoria-dropzone-status-badge"></span><div class="innoria-attached-files-summary d-none"></div><input type="file" class="innoria-file-input" name="quote_attachments"/>`;

    window.innoriaI18n.wirePriorityFileDropzones(container);

    const input = container.querySelector(".innoria-file-input");
    const summaryEl = container.querySelector(".innoria-attached-files-summary");
    const badgeEl = container.querySelector(".innoria-dropzone-status-badge");

    const testFile = new File(["rfp content"], "RFP_Spec.pdf", { type: "application/pdf" });
    Object.defineProperty(input, "files", {
        value: [testFile],
        configurable: true,
    });

    input.dispatchEvent(new Event("change"));

    expect(!summaryEl.classList.contains("d-none")).toBe(true);
    expect(summaryEl.textContent.includes("RFP_Spec.pdf")).toBe(true);
    expect(badgeEl.querySelector("svg.ph-duotone.ph-check-circle") !== null).toBe(true);
});

test("@insilos_website/i18n/setLanguage updates currentLang and dispatches innoria:i18n:switched event", () => {
    let switchedLang = null;
    const handler = (ev) => {
        switchedLang = ev.detail && ev.detail.lang;
    };
    window.addEventListener("innoria:i18n:switched", handler);

    try {
        window.innoriaI18n.setLanguage("en");
        expect(switchedLang).toBe("en");
        expect(window.innoriaI18n.currentLang).toBe("en");
    } finally {
        window.removeEventListener("innoria:i18n:switched", handler);
        window.innoriaI18n.setLanguage("vi");
    }
});
