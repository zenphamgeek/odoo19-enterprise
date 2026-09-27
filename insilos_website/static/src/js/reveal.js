import { whenReady } from '@odoo/owl';

document.documentElement.classList.add("ins-js");

whenReady(() => {
    const elements = [...document.querySelectorAll(".insilos-site [data-ins-reveal]")];
    if (!elements.length) {
        return;
    }

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion || !("IntersectionObserver" in window)) {
        elements.forEach((element) => element.classList.add("is-visible"));
        return;
    }

    elements.forEach((element) => {
        const delay = Number.parseInt(element.dataset.insDelay || "0", 10);
        element.style.setProperty("--ins-delay", `${Number.isFinite(delay) ? delay : 0}ms`);
    });

    const observer = new IntersectionObserver(
        (entries) => {
            for (const entry of entries) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            }
        },
        { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );

    elements.forEach((element) => observer.observe(element));
});
