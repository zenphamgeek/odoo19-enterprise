/** @odoo-module **/
/**
 * Insilos Executive Glassmorphism Mega-Menu & Interactive Header Effects
 * -----------------------------------------------------------------------
 * Handles:
 * 1. Dynamic indicator sheen smoothly tracking active / hovered nav links.
 * 2. 80ms debounced hover preview card switching for Solutions & Industries.
 * 3. Mouse spotlight radial gradient coordinate injection (--mouse-x, --mouse-y).
 * 4. Graceful 150ms exit fade dismissal and keyboard (Escape) controls.
 */

(function () {
    'use strict';

    let isInitialized = false;

    function initMegaMenu() {
        const topMenu = document.getElementById('top_menu');
        const indicator = document.getElementById('ins_nav_indicator');
        if (!topMenu) return;

        // Prevent double binding
        if (topMenu.dataset.megamenuInitialized === 'true') return;
        topMenu.dataset.megamenuInitialized = 'true';

        // -----------------------------------------------------------------
        // 1. Dynamic Indicator Sheen (Interpolating Pill)
        // -----------------------------------------------------------------
        const navLinks = topMenu.querySelectorAll('.ins-nav-item > .nav-link');
        let activeLink = null;
        const currentPath = window.location.pathname.replace(/\/$/, '') || '/';

        navLinks.forEach((link) => {
            const href = (link.getAttribute('href') || '').replace(/\/$/, '') || '/';
            if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
                link.classList.add('active');
                if (!activeLink) activeLink = link;
            }
        });

        function positionIndicator(target) {
            if (!indicator || !target) return;
            const linkRect = target.getBoundingClientRect();
            const parent = indicator.offsetParent || target.closest('.ins-nav-wrapper') || target.parentElement;
            const parentRect = parent.getBoundingClientRect();
            
            const left = linkRect.left - parentRect.left;
            const top = linkRect.top - parentRect.top;
            const width = linkRect.width;
            const height = linkRect.height;

            indicator.style.left = `${left}px`;
            indicator.style.top = `${top}px`;
            indicator.style.width = `${width}px`;
            indicator.style.height = `${height}px`;
            indicator.style.opacity = '1';
        }

        function resetIndicator() {
            if (!indicator) return;
            if (activeLink) {
                positionIndicator(activeLink);
            } else {
                indicator.style.opacity = '0';
            }
        }

        // Initialize indicator position
        requestAnimationFrame(() => {
            resetIndicator();
        });

        navLinks.forEach((link) => {
            link.addEventListener('mouseenter', () => {
                positionIndicator(link);
            });
        });

        topMenu.closest('.ins-nav-wrapper')?.addEventListener('mouseleave', () => {
            resetIndicator();
        });

        window.addEventListener('resize', () => {
            resetIndicator();
        });
        window.addEventListener('scroll', () => {
            resetIndicator();
        }, { passive: true });

        // -----------------------------------------------------------------
        // 2. Mega-Menu Open / Close Coordination (Solutions & Industries)
        // -----------------------------------------------------------------
        const megaItems = document.querySelectorAll('.ins-has-megamenu');
        const megaDropdowns = document.querySelectorAll('.ins-megamenu-dropdown');
        let closeTimer = null;
        let activeDropdown = null;

        function closeAllMegaMenus() {
            megaItems.forEach((item) => {
                item.classList.remove('is-open');
                const trigger = item.querySelector('.ins-megamenu-trigger');
                if (trigger) trigger.setAttribute('aria-expanded', 'false');
            });
            megaDropdowns.forEach((dropdown) => {
                dropdown.classList.remove('is-open');
            });
            activeDropdown = null;
        }

        function openMegaMenu(item) {
            clearTimeout(closeTimer);
            const menuName = item.dataset.megamenu;
            const targetDropdown = document.getElementById(`ins_megamenu_${menuName}`);

            megaItems.forEach((other) => {
                if (other !== item) {
                    other.classList.remove('is-open');
                    const otherTrigger = other.querySelector('.ins-megamenu-trigger');
                    if (otherTrigger) otherTrigger.setAttribute('aria-expanded', 'false');
                }
            });

            megaDropdowns.forEach((dropdown) => {
                if (dropdown !== targetDropdown) {
                    dropdown.classList.remove('is-open');
                }
            });

            item.classList.add('is-open');
            const trigger = item.querySelector('.ins-megamenu-trigger');
            if (trigger) trigger.setAttribute('aria-expanded', 'true');

            if (targetDropdown) {
                targetDropdown.classList.add('is-open');
                activeDropdown = targetDropdown;
            }
        }

        function scheduleClose() {
            clearTimeout(closeTimer);
            closeTimer = setTimeout(() => {
                closeAllMegaMenus();
            }, 180);
        }

        megaItems.forEach((item) => {
            const trigger = item.querySelector('.ins-megamenu-trigger');

            item.addEventListener('mouseenter', () => {
                openMegaMenu(item);
            });

            item.addEventListener('mouseleave', () => {
                scheduleClose();
            });

            if (trigger) {
                trigger.addEventListener('focus', () => {
                    openMegaMenu(item);
                });
                trigger.addEventListener('click', (e) => {
                    // On desktop, clicking the trigger also opens/toggles the dropdown
                    if (window.innerWidth >= 992) {
                        e.preventDefault();
                        if (item.classList.contains('is-open')) {
                            closeAllMegaMenus();
                        } else {
                            openMegaMenu(item);
                        }
                    }
                });
            }
        });

        megaDropdowns.forEach((dropdown) => {
            dropdown.addEventListener('mouseenter', () => {
                clearTimeout(closeTimer);
            });
            dropdown.addEventListener('mouseleave', () => {
                scheduleClose();
            });
        });

        // Close on Escape or click outside
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeAllMegaMenus();
                resetIndicator();
            }
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.ins-has-megamenu') && !e.target.closest('.ins-megamenu-dropdown')) {
                closeAllMegaMenus();
            }
        });

        // -----------------------------------------------------------------
        // 3. Hover Preview Card Switching (80ms Debounce)
        // -----------------------------------------------------------------
        let previewDebounceTimer = null;

        function setupPreviewCards(containerSelector, cardId, prefix) {
            const container = document.querySelector(containerSelector);
            if (!container) return;

            const card = document.getElementById(cardId);
            if (!card) return;

            const items = container.querySelectorAll('.ins-menu-link-item');
            if (!items.length) return;

            // Cache card elements
            const badgeEl = card.querySelector(`.${prefix}-preview-badge`);
            const titleEl = card.querySelector(`.${prefix}-preview-title`);
            const descEl = card.querySelector(`.${prefix}-preview-desc`);
            const iconSvgUse = card.querySelector(`.${prefix}-preview-icon use`);
            const m1Val = card.querySelector(`.${prefix}-m1-val`);
            const m1Lbl = card.querySelector(`.${prefix}-m1-lbl`);
            const m2Val = card.querySelector(`.${prefix}-m2-val`);
            const m2Lbl = card.querySelector(`.${prefix}-m2-lbl`);
            const m3Val = card.querySelector(`.${prefix}-m3-val`);
            const m3Lbl = card.querySelector(`.${prefix}-m3-lbl`);
            const btnEl = card.querySelector(`.${prefix}-preview-btn`);

            function updateCard(item) {
                const badge = item.dataset.badge || '';
                const title = item.dataset.title || '';
                const desc = item.dataset.desc || '';
                const icon = item.dataset.icon || 'ph-cube';
                const m1v = item.dataset.m1Val || '';
                const m1l = item.dataset.m1Lbl || '';
                const m2v = item.dataset.m2Val || '';
                const m2l = item.dataset.m2Lbl || '';
                const m3v = item.dataset.m3Val || '';
                const m3l = item.dataset.m3Lbl || '';
                const href = item.dataset.href || item.getAttribute('href') || '/';

                // Subtle micro-fade transition
                card.style.opacity = '0.4';
                card.style.transform = 'translateY(2px)';

                setTimeout(() => {
                    if (badgeEl) badgeEl.textContent = badge;
                    if (titleEl) titleEl.textContent = title;
                    if (descEl) descEl.textContent = desc;
                    if (iconSvgUse) {
                        iconSvgUse.setAttribute('href', `/insilos_website/static/src/icons/phosphor-duotone.svg#${icon}`);
                    }
                    if (m1Val) m1Val.textContent = m1v;
                    if (m1Lbl) m1Lbl.textContent = m1l;
                    if (m2Val) m2Val.textContent = m2v;
                    if (m2Lbl) m2Lbl.textContent = m2l;
                    if (m3Val) m3Val.textContent = m3v;
                    if (m3Lbl) m3Lbl.textContent = m3l;
                    if (btnEl) btnEl.setAttribute('href', href);

                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';

                    // Emit custom interface contract event
                    document.dispatchEvent(new CustomEvent('insilos-menu-preview-change', {
                        detail: { title, badge, description: desc, href, icon }
                    }));
                }, 60);

                items.forEach((it) => it.classList.remove('is-active'));
                item.classList.add('is-active');
            }

            items.forEach((item) => {
                item.addEventListener('mouseenter', () => {
                    clearTimeout(previewDebounceTimer);
                    previewDebounceTimer = setTimeout(() => {
                        updateCard(item);
                    }, 80);
                });
            });
        }

        setupPreviewCards('.ins-megamenu-solutions', 'ins_sol_preview_card', 'ins-sol');
        setupPreviewCards('.ins-megamenu-industries', 'ins_ind_preview_card', 'ins-ind');

        // -----------------------------------------------------------------
        // 4. Cursor Tracking & Mouse Spotlight Radial Gradient
        // -----------------------------------------------------------------
        const previewCards = document.querySelectorAll('.ins-preview-card');
        previewCards.forEach((card) => {
            let rafId = null;
            card.addEventListener('mousemove', (e) => {
                if (rafId) cancelAnimationFrame(rafId);
                rafId = requestAnimationFrame(() => {
                    const rect = card.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    card.style.setProperty('--mouse-x', `${x}px`);
                    card.style.setProperty('--mouse-y', `${y}px`);
                });
            });
        });

        // Window resize repositioning
        window.addEventListener('resize', () => {
            resetIndicator();
            if (window.innerWidth < 992) {
                closeAllMegaMenus();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMegaMenu);
    } else {
        initMegaMenu();
    }

    // Re-init on Odoo navigation / OWL events
    window.addEventListener('load', initMegaMenu);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) initMegaMenu();
    });
})();
