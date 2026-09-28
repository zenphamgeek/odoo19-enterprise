// Satisfy 'three' AMD module dependency for Odoo asset loader
if (typeof odoo !== "undefined" && typeof odoo.define === "function") {
    try {
        odoo.define("three", [], function () {
            return window.THREE || (typeof InsilosThreeBundle !== "undefined" ? InsilosThreeBundle.THREE : {}) || {};
        });
    } catch (_) {}
}
if (typeof define === "function" && define.amd) {
    try {
        define("three", [], function () {
            return window.THREE || (typeof InsilosThreeBundle !== "undefined" ? InsilosThreeBundle.THREE : {}) || {};
        });
    } catch (_) {}
}

function initInsilosInteractive() {
    window.__insilos_init = true;
    // 1. Solution Matrix Tab Switcher
    const tabs = document.querySelectorAll(".ins-matrix-tab");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.getAttribute("data-target");
            const container = tab.closest(".ins-matrix-container");
            if (!container || !target) return;

            container.querySelectorAll(".ins-matrix-tab").forEach(t => t.classList.remove("active"));
            container.querySelectorAll(".ins-matrix-pane").forEach(p => p.classList.remove("active"));

            tab.classList.add("active");
            const pane = container.querySelector(`#${target}`);
            if (pane) {
                pane.classList.add("active");
            }
        });
    });

    // 2. Industry Cluster Filter
    const clusterBtns = document.querySelectorAll(".ins-cluster-btn");
    const indCards = document.querySelectorAll(".ins-ind-item");
    clusterBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            clusterBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const cluster = btn.getAttribute("data-cluster");

            indCards.forEach((card) => {
                const cardClusters = (card.getAttribute("data-cluster") || "").split(" ");
                const isVisible = (cluster === "all") ? cardClusters.includes("flagship") : cardClusters.includes(cluster);
                card.classList.toggle("d-none", !isVisible);
                card.style.display = "";
            });
        });
    });

    // 3. Fallback: Upgrade any <i class="ph-duotone ph-xxx"> to SVG <use>
    const iIcons = document.querySelectorAll("i.ph-duotone");
    iIcons.forEach((el) => {
        const classes = Array.from(el.classList);
        const nameClass = classes.find(c => c.startsWith("ph-") && c !== "ph-duotone" && !c.startsWith("ph-sm") && !c.startsWith("ph-md") && !c.startsWith("ph-lg") && !c.startsWith("ph-xl") && !c.startsWith("ph-2x") && !c.startsWith("ph-3x"));
        if (nameClass) {
            const iconName = nameClass.replace("ph-", "");
            const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("class", el.className);
            svg.setAttribute("viewBox", "0 0 256 256");
            const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
            use.setAttribute("href", `/insilos_website/static/src/icons/phosphor-duotone.svg#ph-${iconName}`);
            svg.appendChild(use);
            el.replaceWith(svg);
        }
    });

    // 4. Interactive Terminal Command Console Tabs & Copy Controller
    document.querySelectorAll(".ins-command-box").forEach((box) => {
        const consoleTabs = box.querySelectorAll(".ins-console-tab");
        const panes = box.querySelectorAll(".ins-console-pane");
        const copyBtn = box.querySelector(".ins-copy-btn");

        consoleTabs.forEach((tab) => {
            tab.addEventListener("click", () => {
                const targetTab = tab.getAttribute("data-tab");
                consoleTabs.forEach(t => t.classList.remove("active"));
                tab.classList.add("active");

                panes.forEach((pane) => {
                    if (pane.getAttribute("data-pane") === targetTab) {
                        pane.classList.add("active");
                    } else {
                        pane.classList.remove("active");
                    }
                });
            });
        });

        if (copyBtn) {
            copyBtn.addEventListener("click", () => {
                const activePane = box.querySelector(".ins-console-pane.active") || box.querySelector(".ins-console-body");
                if (activePane) {
                    navigator.clipboard.writeText(activePane.innerText.trim()).then(() => {
                        const originalText = copyBtn.innerText;
                        copyBtn.innerText = "COPIED! ✔";
                        copyBtn.classList.add("btn-orange");
                        setTimeout(() => {
                            copyBtn.innerText = originalText;
                            copyBtn.classList.remove("btn-orange");
                        }, 2000);
                    }).catch(() => {
                        copyBtn.innerText = "COPIED! ✔";
                        setTimeout(() => { copyBtn.innerText = "COPY"; }, 2000);
                    });
                }
            });
        }
    });

    // 5. Interactive Radar Topology & Node Highlight Inspector
    document.querySelectorAll(".ins-radar-topology").forEach((radar) => {
        const blips = radar.querySelectorAll(".ins-radar-blip");
        const nodeCards = radar.querySelectorAll(".ins-node-card");
        const latencyBadge = radar.querySelector(".ins-live-latency");

        function activateNode(nodeKey) {
            blips.forEach(b => {
                if (b.getAttribute("data-node") === nodeKey) {
                    b.classList.add("active");
                } else {
                    b.classList.remove("active");
                }
            });
            nodeCards.forEach(c => {
                if (c.getAttribute("data-node") === nodeKey) {
                    c.classList.add("active");
                    const latency = c.getAttribute("data-latency");
                    if (latencyBadge && latency) {
                        latencyBadge.innerText = latency;
                    }
                } else {
                    c.classList.remove("active");
                }
            });
        }

        blips.forEach((blip) => {
            blip.addEventListener("mouseenter", () => {
                activateNode(blip.getAttribute("data-node"));
            });
            blip.addEventListener("click", () => {
                activateNode(blip.getAttribute("data-node"));
            });
        });

        nodeCards.forEach((card) => {
            card.addEventListener("mouseenter", () => {
                activateNode(card.getAttribute("data-node"));
            });
            card.addEventListener("click", () => {
                activateNode(card.getAttribute("data-node"));
            });
        });
    });

    // 6. Interactive Multi-Slider ROI & TCO Engine
    function initRoiCalculator() {
        const calculators = document.querySelectorAll(".ins-roi-calculator, #roi-calculator, .ins-calculator-wrapper");
        if (!calculators.length) return;

        calculators.forEach((calc) => {
            if (calc.__roi_initialized) return;
            calc.__roi_initialized = true;

            // Sliders & inputs (harmonized for #ins-calc-* in home.xml and fallback variants)
            const sliderIntegrations = calc.querySelector("#ins-calc-erp, #ins_slider_integrations, input[name='integrations'], .ins-slider-integrations");
            const sliderVolume = calc.querySelector("#ins-calc-volume, #ins_slider_volume, input[name='volume'], .ins-slider-volume");
            const sliderError = calc.querySelector("#ins-calc-error, #ins_slider_error, input[name='error_rate'], .ins-slider-error");

            // Value badge indicators
            const badgeIntegrations = calc.querySelector("#ins-calc-val-erp-display, #ins_badge_integrations, .ins-badge-integrations");
            const badgeVolume = calc.querySelector("#ins-calc-val-vol-display, #ins_badge_volume, .ins-badge-volume");
            const badgeError = calc.querySelector("#ins-calc-val-err-display, #ins_badge_error, .ins-badge-error");

            // Currency toggle
            let currentCurrency = "VND"; // "VND" or "USD"
            const currencyBtns = calc.querySelectorAll(".ins-currency-pill-btn, .ins-calc-currency-btn, .ins-calc-curr-btn, [data-currency]");

            // Output metrics elements
            const valSavings = calc.querySelector("#ins-calc-net-savings, .ins-calc-val-savings, #ins_roi_annual_savings");
            const valHours = calc.querySelector("#ins-calc-hours-saved, .ins-calc-val-hours, #ins_roi_hours_saved");
            const valStp = calc.querySelector(".ins-calc-val-stp, #ins_roi_stp_rate");
            const valUnit = calc.querySelector(".ins-calc-val-unit, #ins_roi_unit_cost");
            const valPayback = calc.querySelector("#ins-calc-payback-months, .ins-calc-val-payback, #ins_roi_payback, .ins-payback-val");

            // Legacy pills compatibility (5k, 25k, 100k, 500k)
            const pills = calc.querySelectorAll(".ins-calc-pill");
            let legacyVolume = 25000;
            const pillVolMap = { "5k": 5000, "25k": 25000, "100k": 100000, "500k": 500000 };

            const hasSliders = !!(sliderIntegrations && sliderVolume && sliderError);

            function getActiveCurrency() {
                const activeBtn = calc.querySelector(".ins-calc-curr-btn.active, .ins-currency-pill-btn.active, [data-currency].active");
                if (activeBtn) {
                    return (activeBtn.getAttribute("data-currency") || (activeBtn.id && activeBtn.id.includes("usd") ? "USD" : "VND")).toUpperCase();
                }
                return currentCurrency;
            }

            function calculateAndRender() {
                if (typeof window.updateROI === "function" && window.updateROI !== calculateAndRender) {
                    window.updateROI();
                    return;
                }

                if (hasSliders) {
                    const integrations = parseInt(sliderIntegrations.value, 10);
                    const volume = parseInt(sliderVolume.value, 10);
                    const errorRate = parseFloat(sliderError.value);

                    // Update badge numbers if elements exist
                    if (badgeIntegrations) badgeIntegrations.textContent = `${integrations} ERPs`;
                    if (badgeVolume) badgeVolume.textContent = `${volume.toLocaleString('vi-VN')} Tài Liệu`;
                    if (badgeError) badgeError.textContent = `${errorRate.toFixed(1)}%`;

                    const monthlyHours = volume * 0.2375;
                    const annualHours = Math.round(monthlyHours * 12);

                    const monthlyErrorsAvoided = volume * (errorRate / 100) * 0.98;
                    const monthlyErrorCostVND = monthlyErrorsAvoided * 400000;
                    const monthlyLaborVND = (volume * 5000) + (integrations * 15000000);
                    const monthlyTotalVND = monthlyLaborVND + monthlyErrorCostVND;
                    const annualSavingsVND = monthlyTotalVND * 12;

                    const v1 = integrations;
                    const dynamicCapex = 1200000000 + (v1 * 400000000);
                    let payback = monthlyTotalVND > 0 ? (dynamicCapex / monthlyTotalVND) : 3.2;
                    if (payback < 1.2) payback = 1.2;
                    if (payback > 8.5) payback = 8.5;

                    if (valHours) {
                        valHours.textContent = annualHours.toLocaleString('vi-VN') + ' Giờ / Năm';
                    }
                    if (valPayback) {
                        valPayback.textContent = payback.toFixed(1) + ' Tháng';
                    }

                    const curr = getActiveCurrency();
                    if (valSavings) {
                        if (curr === "VND") {
                            if (annualSavingsVND >= 1000000000) {
                                const billions = (annualSavingsVND / 1000000000).toFixed(2);
                                valSavings.textContent = '₫' + billions + ' Tỷ / Năm';
                            } else {
                                valSavings.textContent = '₫' + Math.round(annualSavingsVND).toLocaleString('vi-VN') + ' / Năm';
                            }
                        } else {
                            const annualSavingsUSD = annualSavingsVND / 25000;
                            valSavings.textContent = '$' + Math.round(annualSavingsUSD).toLocaleString('en-US') + ' / Year';
                        }
                    }
                    return;
                }

                // Fallback for legacy pill-only calculators (without sliders)
                const integrations = 3;
                const volume = legacyVolume || 25000;
                const errorRate = 4.5;

                // Update badge numbers if elements exist
                if (badgeIntegrations) badgeIntegrations.textContent = `${integrations} ERPs`;
                if (badgeVolume) badgeVolume.textContent = `${volume.toLocaleString()} vận đơn/th`;
                if (badgeError) badgeError.textContent = `${errorRate.toFixed(1)}%`;

                // Formula:
                // Labor: 0.08h per doc at 45,000 VND/h eliminated by 95%
                const monthlyLaborSavings = volume * 0.08 * 45000 * 0.95;
                // Errors: 350,000 VND per error resolved by 98%
                const monthlyErrorSavings = volume * (errorRate / 100) * 350000 * 0.98;
                // ERP integration maintenance: 15,000,000 VND per system per month
                const monthlyIntegrationSavings = integrations * 15000000;
                const totalMonthlyVnd = Math.round(monthlyLaborSavings + monthlyErrorSavings + monthlyIntegrationSavings);
                const totalAnnualVnd = totalMonthlyVnd * 12;
                const totalAnnualUsd = Math.round(totalAnnualVnd / 25000);

                const monthlyHoursSaved = Math.round((volume * 0.08 * 0.95) + (volume * (errorRate / 100) * 1.5 * 0.98));
                const stpRate = Math.min(99.99, (98.2 + (volume >= 50000 ? 1.4 : 0.9) + (errorRate <= 3.0 ? 0.35 : 0.1))).toFixed(2) + "%";
                const creditRate = (volume >= 100000 ? "0.018" : volume >= 25000 ? "0.032" : "0.045") + " Credits";
                const paybackMonths = Math.max(1.8, Math.min(6.2, 450000000 / (totalMonthlyVnd * 0.35))).toFixed(1);

                const curr = getActiveCurrency();
                if (valSavings) {
                    valSavings.textContent = (curr === "USD")
                        ? `$${totalAnnualUsd.toLocaleString()} USD / Năm`
                        : `₫${totalAnnualVnd.toLocaleString()} / Năm`;
                }
                if (valHours) valHours.textContent = `${monthlyHoursSaved.toLocaleString()} Giờ / Tháng`;
                if (valStp) valStp.textContent = stpRate;
                if (valUnit) valUnit.textContent = creditRate;
                if (valPayback) valPayback.textContent = `${paybackMonths} Tháng`;
            }

            // Expose globally so external scripts/tests can synchronize
            if (hasSliders && typeof window.updateROI !== "function") {
                window.updateROI = calculateAndRender;
            }

            // Slider listeners for real-time reactivity
            [sliderIntegrations, sliderVolume, sliderError].forEach((slider) => {
                if (slider) {
                    slider.addEventListener("input", calculateAndRender);
                    slider.addEventListener("change", calculateAndRender);
                }
            });

            // Currency toggle listeners
            currencyBtns.forEach((btn) => {
                btn.addEventListener("click", () => {
                    const c = btn.getAttribute("data-currency") || (btn.id && btn.id.includes("usd") ? "USD" : "VND");
                    currentCurrency = c.toUpperCase();
                    currencyBtns.forEach(b => b.classList.remove("active"));
                    btn.classList.add("active");
                    if (typeof window.updateROI === "function" && window.updateROI !== calculateAndRender) {
                        window.updateROI();
                    } else {
                        calculateAndRender();
                    }
                });
            });

            // Legacy pill buttons mapping
            pills.forEach((pill) => {
                if (pill.classList.contains("active")) {
                    const vk = pill.getAttribute("data-vol");
                    if (pillVolMap[vk]) legacyVolume = pillVolMap[vk];
                }
                pill.addEventListener("click", () => {
                    pills.forEach(p => p.classList.remove("active"));
                    pill.classList.add("active");
                    const volKey = pill.getAttribute("data-vol");
                    if (pillVolMap[volKey]) {
                        legacyVolume = pillVolMap[volKey];
                        if (sliderVolume) {
                            sliderVolume.value = pillVolMap[volKey];
                            sliderVolume.dispatchEvent(new Event("input"));
                        }
                        calculateAndRender();
                    }
                });
            });

            // Initial calculation
            calculateAndRender();
        });
    }
    initRoiCalculator();

    // 7. Tactical Card Mouse-Tracking Spotlight Effect (Vercel/Stripe Sheen)
    const spotlightCards = document.querySelectorAll(
        ".card, .ins-dossier-card, .ins-bento-card, .ins-anchor-card, .ins-command-box, .ins-roi-calculator, .ins-node-card"
    );
    spotlightCards.forEach((card) => {
        let rafPending = false;
        let mouseX = 0;
        let mouseY = 0;

        card.addEventListener("mousemove", (e) => {
            const rect = card.getBoundingClientRect();
            mouseX = e.clientX - rect.left;
            mouseY = e.clientY - rect.top;

            if (!rafPending) {
                rafPending = true;
                card.style.setProperty("--mouse-x", `${mouseX}px`);
                card.style.setProperty("--mouse-y", `${mouseY}px`);
                requestAnimationFrame(() => {
                    card.style.setProperty("--mouse-x", `${mouseX}px`);
                    card.style.setProperty("--mouse-y", `${mouseY}px`);
                    rafPending = false;
                });
            }
        }, { passive: true });
    });

    // 8. C3.ai Style Dual-Buffer Video Engine & 4-Act Storyboard Orchestrator
    const heroShowcase = document.getElementById("insilos_hero_showcase");
    if (heroShowcase && !heroShowcase.__video_engine_initialized) {
        heroShowcase.__video_engine_initialized = true;
        const videoA = document.getElementById("ins-hero-video-a");
        const videoB = document.getElementById("ins-hero-video-b");
        const posterEl = document.getElementById("ins-hero-poster");
        const badgeTag = document.getElementById("ins-hero-badge-tag");
        const actPanes = heroShowcase.querySelectorAll(".ins-hero-act-pane");
        const stepperTabs = heroShowcase.querySelectorAll(".ins-stepper-tab");
        const cockpitCards = heroShowcase.querySelectorAll(".ins-cockpit-card");

        const HERO_ACTS = [
            {
                act: 1,
                video: "/insilos_website/static/src/video/hero_act1_opt.mp4",
                poster: "/insilos_website/static/src/video/hero_act1_poster.webp",
                tag: "SOVEREIGN OPERATIONAL AI // APAC INFRASTRUCTURE",
                cockpitTarget: "1"
            },
            {
                act: 2,
                video: "/insilos_website/static/src/video/hero_act2_opt.mp4",
                poster: "/insilos_website/static/src/video/hero_act2_poster.webp",
                tag: "VERTICAL IDP // 99.8% PRECISION AUTOMATION",
                cockpitTarget: "2"
            },
            {
                act: 3,
                video: "/insilos_website/static/src/video/hero_act3_opt.mp4",
                poster: "/insilos_website/static/src/video/hero_act3_poster.webp",
                tag: "ENTERPRISE KNOWLEDGE GRAPH // MERKLE AIR-GAPPED",
                cockpitTarget: "3"
            },
            {
                act: 4,
                video: "/insilos_website/static/src/video/hero_act4_opt.mp4",
                poster: "/insilos_website/static/src/video/hero_act4_poster.webp",
                tag: "INTELLIGENT FSM // 0H UNPLANNED DOWNTIME",
                cockpitTarget: "4"
            }
        ];

        let currentAct = 1;
        let activeBuffer = "A"; // "A" or "B"
        let timer = null;
        let isPaused = false;
        const CYCLE_DURATION = 8000;

        // Scene Transition Engine State (Blade, Glitch, Iris, Warp, Luma, Shutter)
        let currentFxMode = "cycle";
        let isTransitioning = false;
        let transitionTimeout = null;
        let transitionTimerIds = [];

        const fxBadge = document.getElementById("ins-current-fx-badge");
        let fxButtons = heroShowcase.querySelectorAll(".ins-btn-fx");

        const FX_MODES = ["blade", "glitch", "iris", "warp", "luma", "shutter", "matrix", "circuit"];

        // 8-Mode Active Effects Rotation Cycle (Full Rotation across all 8 modes)
        const FX_ROTATION_CYCLE = ["blade", "glitch", "iris", "warp", "luma", "shutter", "matrix", "circuit"];
        let fxCycleStep = 0;

        const ACT_FX_MAP = {
            1: "iris",     // Radial Iris Bloom returning to home base
            2: "blade",    // 45° Laser Blade Angled Slice Wipe
            3: "glitch",   // Cybernetic Glitch & RGB Split
            4: "warp",     // Quantum Warp Hyper-Zoom
            5: "luma",     // Anamorphic Luma Light Leak & Solar Flare
            6: "shutter",  // Bi-Directional Vault Shutter
            7: "matrix",   // Digital Rain Matrix Cascade
            8: "circuit"   // Circuit Trace Conductive Route Wipe
        };

        const FX_NAMES = {
            cycle: "AUTO-CYCLE",
            blade: "BLADE WIPE",
            glitch: "CYBER GLITCH",
            iris: "RADIAL IRIS",
            warp: "QUANTUM WARP",
            luma: "LUMA FLARE",
            shutter: "VAULT SHUTTER",
            matrix: "DIGITAL RAIN",
            circuit: "CIRCUIT TRACE"
        };

        // Ensure transition overlay stage elements exist for matrix and circuit
        const stageEl = document.getElementById("ins_scene_transition_stage");
        if (stageEl) {
            if (!document.getElementById("ins_matrix_cascade")) {
                const matrixNode = document.createElement("div");
                matrixNode.className = "ins-matrix-rain-cascade";
                matrixNode.id = "ins_matrix_cascade";
                stageEl.appendChild(matrixNode);
            }
            if (!document.getElementById("ins_circuit_trace")) {
                const circuitNode = document.createElement("div");
                circuitNode.className = "ins-circuit-trace-grid";
                circuitNode.id = "ins_circuit_trace";
                stageEl.appendChild(circuitNode);
            }
        }

        const FX_ELEMENTS = {
            blade: document.getElementById("ins_blade_beam"),
            glitch: document.getElementById("ins_glitch_overlay"),
            iris: document.getElementById("ins_iris_ring"),
            warp: document.getElementById("ins_warp_tunnel"),
            luma: document.getElementById("ins_luma_flare"),
            shutter: document.getElementById("ins_shutter_line"),
            matrix: document.getElementById("ins_matrix_cascade"),
            circuit: document.getElementById("ins_circuit_trace")
        };

        function clearAllTransitionTimers() {
            if (transitionTimeout) {
                clearTimeout(transitionTimeout);
                transitionTimeout = null;
            }
            transitionTimerIds.forEach(id => {
                if (id) clearTimeout(id);
            });
            transitionTimerIds = [];
        }

        function clearAllFxOverlays() {
            Object.values(FX_ELEMENTS).forEach(el => {
                if (el) el.classList.remove("active");
            });
            if (videoA && videoB) {
                FX_MODES.forEach(mode => {
                    videoA.classList.remove(`ins-fx-${mode}-in`, `ins-fx-${mode}-out`);
                    videoB.classList.remove(`ins-fx-${mode}-in`, `ins-fx-${mode}-out`);
                });
            }
        }

        function abortCurrentTransition() {
            clearAllTransitionTimers();
            if (isTransitioning) {
                if (videoA && videoB) {
                    const currentVideo = (activeBuffer === "A") ? videoA : videoB;
                    const nextVideo = (activeBuffer === "A") ? videoB : videoA;
                    currentVideo.classList.remove("active");
                    nextVideo.classList.add("active");
                    activeBuffer = (activeBuffer === "A") ? "B" : "A";
                }
                isTransitioning = false;
            }
            clearAllFxOverlays();
        }

        function executeSceneTransition(currentVideo, nextVideo, effectName) {
            clearAllTransitionTimers();
            clearAllFxOverlays();

            if (!effectName || !FX_MODES.includes(effectName)) {
                effectName = "blade";
            }

            const inClass = `ins-fx-${effectName}-in`;
            const outClass = `ins-fx-${effectName}-out`;
            const fxEl = FX_ELEMENTS[effectName];

            // 1. Activate overlay element
            if (fxEl) {
                void fxEl.offsetWidth; // Force CSS reflow
                fxEl.classList.add("active");
            }

            // 2. Apply transition animations
            currentVideo.classList.add(outClass);
            nextVideo.classList.add(inClass);
            nextVideo.classList.add("active");

            isTransitioning = true;

            // Duration tuned per effect
            const durationMap = {
                glitch: 850,
                iris: 1200,
                warp: 1050,
                blade: 1100,
                luma: 1100,
                shutter: 1150,
                matrix: 950,
                circuit: 1100
            };
            const duration = durationMap[effectName] || 1100;

            transitionTimeout = setTimeout(() => {
                currentVideo.classList.remove("active", outClass);
                nextVideo.classList.remove(inClass);
                if (fxEl) {
                    fxEl.classList.remove("active");
                }
                activeBuffer = (activeBuffer === "A") ? "B" : "A";
                isTransitioning = false;
                transitionTimeout = null;
            }, duration);
            transitionTimerIds.push(transitionTimeout);
        }

        // Ensure videos are strictly muted & playsinline for browser autoplay approval
        [videoA, videoB].forEach(v => {
            if (v) {
                v.muted = true;
                v.defaultMuted = true;
                v.playsInline = true;
                v.setAttribute("muted", "");
                v.setAttribute("playsinline", "");
            }
        });
        if (videoA) {
            videoA.play().catch(() => {});
        }

        function switchAct(actNumber, forceManual = false, overrideEffect = null) {
            if (actNumber === currentAct && !forceManual) return;
            const targetData = HERO_ACTS.find(item => item.act === actNumber);
            if (!targetData) return;

            // Systematically abort any in-flight transitions and clear all pending timers
            abortCurrentTransition();

            currentAct = actNumber;

            // Determine effect to use (Full 6-mode rotation including luma and shutter)
            let selectedEffect = overrideEffect;
            if (!selectedEffect) {
                if (currentFxMode === "cycle") {
                    selectedEffect = FX_ROTATION_CYCLE[fxCycleStep % FX_ROTATION_CYCLE.length];
                    fxCycleStep++;
                } else {
                    selectedEffect = currentFxMode;
                }
            }

            // 1. Diverse Scene Transition Video Buffer
            if (videoA && videoB) {
                const currentVideo = (activeBuffer === "A") ? videoA : videoB;
                const nextVideo = (activeBuffer === "A") ? videoB : videoA;

                nextVideo.muted = true;
                nextVideo.defaultMuted = true;
                nextVideo.playsInline = true;
                nextVideo.setAttribute("muted", "");
                nextVideo.setAttribute("playsinline", "");
                nextVideo.src = targetData.video;
                nextVideo.load();

                const playPromise = nextVideo.play();
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        executeSceneTransition(currentVideo, nextVideo, selectedEffect);
                    }).catch(() => {
                        executeSceneTransition(currentVideo, nextVideo, selectedEffect);
                    });
                } else {
                    executeSceneTransition(currentVideo, nextVideo, selectedEffect);
                }
            }

            // 2. Poster Fallback for Mobile / Instant LCP
            if (posterEl) {
                posterEl.style.backgroundImage = `url('${targetData.poster}')`;
            }

            // 3. Switch Content Text Panes
            actPanes.forEach(pane => {
                const actId = parseInt(pane.getAttribute("data-act"), 10);
                if (actId === actNumber) {
                    pane.classList.add("active");
                } else {
                    pane.classList.remove("active");
                }
            });

            // 4. Update Tag Badge
            if (badgeTag && targetData.tag) {
                badgeTag.innerText = targetData.tag;
            }

            // 5. Update Stepper Tabs
            stepperTabs.forEach(tab => {
                const actId = parseInt(tab.getAttribute("data-act"), 10);
                const barInner = tab.querySelector(".ins-stepper-bar-inner");
                if (actId === actNumber) {
                    tab.classList.add("active");
                    if (barInner) {
                        barInner.style.animation = "none";
                        void barInner.offsetWidth;
                        barInner.style.animation = `insStepperFill ${CYCLE_DURATION}ms linear forwards`;
                    }
                } else {
                    tab.classList.remove("active");
                    if (barInner) {
                        barInner.style.animation = "none";
                        barInner.style.width = (actId < actNumber) ? "100%" : "0%";
                    }
                }
            });

            // 6. Synchronize Cockpit Card Highlight & SVG Signal Bus Tap Highlights
            cockpitCards.forEach(card => {
                const targetAct = card.getAttribute("data-act-target");
                if (targetAct === String(actNumber)) {
                    card.classList.add("ins-act-highlight");
                } else {
                    card.classList.remove("ins-act-highlight");
                }
            });

            const busTaps = heroShowcase.querySelectorAll(".ins-bus-tap");
            busTaps.forEach(tap => {
                tap.classList.toggle("active", tap.classList.contains(`ins-bus-tap-${actNumber}`));
            });

            const busBranches = heroShowcase.querySelectorAll(".ins-bus-branch");
            busBranches.forEach(branch => {
                branch.classList.toggle("active", branch.classList.contains(`ins-bus-branch-${actNumber}`));
            });

            const busDocks = heroShowcase.querySelectorAll(".ins-bus-dock");
            busDocks.forEach(dock => {
                dock.classList.toggle("active", dock.classList.contains(`ins-bus-dock-${actNumber}`));
            });
        }

        function startCycle() {
            stopCycle();
            timer = setInterval(() => {
                if (!isPaused) {
                    const nextAct = (currentAct % HERO_ACTS.length) + 1;
                    switchAct(nextAct);
                }
            }, CYCLE_DURATION);
        }

        function stopCycle() {
            if (timer) {
                clearInterval(timer);
                timer = null;
            }
        }

        // Act Pane Clicks
        actPanes.forEach(pane => {
            pane.addEventListener("click", () => {
                const targetAct = parseInt(pane.getAttribute("data-act"), 10);
                if (targetAct) {
                    abortCurrentTransition();
                    switchAct(targetAct, true);
                    startCycle();
                }
            });
        });

        // Stepper Tab Clicks
        stepperTabs.forEach(tab => {
            tab.addEventListener("click", () => {
                const targetAct = parseInt(tab.getAttribute("data-act"), 10);
                if (targetAct) {
                    abortCurrentTransition();
                    switchAct(targetAct, true);
                    startCycle();
                }
            });
        });

        // Cockpit Card Clicks
        cockpitCards.forEach(card => {
            card.addEventListener("click", () => {
                const targetAct = parseInt(card.getAttribute("data-act-target"), 10);
                if (targetAct) {
                    abortCurrentTransition();
                    switchAct(targetAct, true);
                    startCycle();
                }
            });
        });

        // Scene Transition FX Buttons (CYCLE, BLADE, GLITCH, IRIS, WARP, LUMA, SHUTTER, MATRIX, CIRCUIT)
        const fxControlsGroup = heroShowcase.querySelector("#ins_scene_fx_controls");
        if (fxControlsGroup) {
            if (!fxControlsGroup.querySelector('[data-fx="matrix"]')) {
                const btnM = document.createElement("button");
                btnM.type = "button";
                btnM.className = "btn ins-btn-fx";
                btnM.setAttribute("data-fx", "matrix");
                btnM.title = "Mưa ma trận Digital Rain Matrix Cascade";
                btnM.textContent = "MATRIX";
                fxControlsGroup.appendChild(btnM);
            }
            if (!fxControlsGroup.querySelector('[data-fx="circuit"]')) {
                const btnC = document.createElement("button");
                btnC.type = "button";
                btnC.className = "btn ins-btn-fx";
                btnC.setAttribute("data-fx", "circuit");
                btnC.title = "Đường dẫn mạch quang PCB Circuit Trace Wipe";
                btnC.textContent = "CIRCUIT";
                fxControlsGroup.appendChild(btnC);
            }
            fxButtons = heroShowcase.querySelectorAll(".ins-btn-fx");
        }

        fxButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                const mode = btn.getAttribute("data-fx");
                if (!mode) return;

                currentFxMode = mode;
                fxButtons.forEach(b => b.classList.toggle("active", b === btn));
                if (fxBadge) {
                    fxBadge.innerText = FX_NAMES[mode] || mode.toUpperCase();
                }

                // Immediately abort any in-flight transitions and trigger preview transition with the chosen effect
                abortCurrentTransition();
                const nextAct = (currentAct % HERO_ACTS.length) + 1;
                switchAct(nextAct, true, (mode === "cycle" ? null : mode));
                startCycle();
            });
        });

        // 3D Mode Toggles (Isometric Stack vs Exploded View)
        const btnIsometric = document.getElementById("btn_mode_isometric");
        const btnExploded = document.getElementById("btn_mode_exploded");
        const cockpitDeck = document.getElementById("ins_3d_cockpit_deck");
        if (btnIsometric && btnExploded && cockpitDeck) {
            btnIsometric.addEventListener("click", () => {
                cockpitDeck.classList.remove("ins-exploded-mode");
                btnIsometric.classList.add("active");
                btnExploded.classList.remove("active");
            });
            btnExploded.addEventListener("click", () => {
                cockpitDeck.classList.add("ins-exploded-mode");
                btnExploded.classList.add("active");
                btnIsometric.classList.remove("active");
            });
        }

        // Pause cycle when executive hovers over Hero section
        heroShowcase.addEventListener("mouseenter", () => {
            isPaused = true;
        });
        heroShowcase.addEventListener("mouseleave", () => {
            isPaused = false;
        });

        // 3D Gyroscope Mouse Parallax on Cockpit Deck throttled via requestAnimationFrame (60 FPS leak-free)
        const viewport3D = heroShowcase.querySelector(".ins-3d-cockpit-viewport");
        if (cockpitDeck && viewport3D) {
            let tiltRafPending = false;
            let latestTiltX = "0deg";
            let latestTiltY = "0deg";

            viewport3D.addEventListener("mousemove", (e) => {
                if (window.innerWidth < 992) return;
                const rect = viewport3D.getBoundingClientRect();
                const normX = (e.clientX - rect.left) / rect.width - 0.5;
                const normY = (e.clientY - rect.top) / rect.height - 0.5;
                const tiltX = (-normY * 12).toFixed(2);
                const tiltY = (normX * 14).toFixed(2);
                latestTiltX = `${tiltX}deg`;
                latestTiltY = `${tiltY}deg`;

                if (!tiltRafPending) {
                    tiltRafPending = true;
                    cockpitDeck.style.setProperty("--tilt-x", latestTiltX);
                    cockpitDeck.style.setProperty("--tilt-y", latestTiltY);
                    requestAnimationFrame(() => {
                        cockpitDeck.style.setProperty("--tilt-x", latestTiltX);
                        cockpitDeck.style.setProperty("--tilt-y", latestTiltY);
                        tiltRafPending = false;
                    });
                }
            }, { passive: true });

            viewport3D.addEventListener("mouseleave", () => {
                tiltRafPending = false;
                cockpitDeck.style.setProperty("--tilt-x", "0deg");
                cockpitDeck.style.setProperty("--tilt-y", "0deg");
            });
        }

        // 60 FPS Leak-Free Performance Hardening: IntersectionObserver for off-screen video pausing
        if ("IntersectionObserver" in window) {
            let wasHeroVisible = true;
            const videoObserver = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    const activeVid = (activeBuffer === "A") ? videoA : videoB;
                    if (!entry.isIntersecting) {
                        wasHeroVisible = false;
                        // Pause off-screen video elements to free GPU decoding buffers & memory
                        if (videoA && !videoA.paused) {
                            videoA.pause();
                        }
                        if (videoB && !videoB.paused) {
                            videoB.pause();
                        }
                    } else {
                        // Resumed in viewport: restart playback on the active video buffer
                        if (!wasHeroVisible) {
                            wasHeroVisible = true;
                            if (activeVid && activeVid.paused) {
                                activeVid.play().catch(() => {});
                            }
                        }
                    }
                });
            }, {
                threshold: 0.05
            });
            videoObserver.observe(heroShowcase);
        }

        // Start cycle
        startCycle();

        // Global interaction fallback for strict browser autoplay policies
        const triggerAutoplay = () => {
            const activeVid = (activeBuffer === "A") ? videoA : videoB;
            if (activeVid && activeVid.paused) {
                activeVid.play().catch(() => {});
            }
        };
        document.addEventListener("click", triggerAutoplay, { once: true, passive: true });
        document.addEventListener("scroll", triggerAutoplay, { once: true, passive: true });
        document.addEventListener("touchstart", triggerAutoplay, { once: true, passive: true });
    }

    // 8. Universal 3D Cockpit Deck Controller for All Page Heroes
    function initAllPage3DCockpits() {
        const viewports = document.querySelectorAll(".ins-3d-cockpit-viewport");
        viewports.forEach((vp) => {
            if (vp.closest("#ins_hero_c3_showcase") || vp.closest("#insilos_hero_showcase")) return; // Homepage handled separately
            if (vp.__cockpit_initialized) return;
            vp.__cockpit_initialized = true;
            // Setup MutationObserver for Snippet Options dynamically updating content
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === "attributes" && mutation.attributeName.startsWith("data-l")) {
                        const attr = mutation.attributeName; // e.g. data-l1-title
                        const match = attr.match(/^data-l(\d)-(.*)$/);
                        if (match) {
                            const layerNum = match[1];
                            const field = match[2];
                            const val = vp.getAttribute(attr);
                            const card = vp.querySelector(`.ins-cockpit-card[data-layer="${layerNum}"]`);
                            if (card && val !== null) {
                                if (field === 'title') {
                                    const el = card.querySelector('.ins-cockpit-title');
                                    if (el) el.innerText = val;
                                } else if (field === 'icon') {
                                    const el = card.querySelector('use');
                                    if (el) el.setAttribute('href', `/insilos_website/static/src/icons/phosphor-duotone.svg#ph-${val}`);
                                } else if (field === 'badge') {
                                    const el = card.querySelector('.ins-cockpit-badge');
                                    if (el) el.innerText = val;
                                } else if (field === 'metric') {
                                    const el = card.querySelector('.fw-medium.font-monospace.small');
                                    if (el) el.innerText = val;
                                } else if (field === 'desc') {
                                    const el = card.querySelector('.d-flex.justify-content-between.text-secondary.small span:first-child');
                                    if (el) el.innerText = val;
                                }
                            }
                        }
                    }
                });
            });
            observer.observe(vp, { attributes: true });

            const deck = vp.querySelector(".ins-cloud-cockpit");
            if (!deck) return;

            // 3D Mode Toggles (Isometric Stack vs Exploded View)
            const btnIso = vp.querySelector(".ins-btn-3d-isometric");
            const btnExp = vp.querySelector(".ins-btn-3d-exploded");
            if (btnIso && btnExp) {
                btnIso.addEventListener("click", () => {
                    deck.classList.remove("ins-exploded-mode");
                    btnIso.classList.add("active");
                    btnExp.classList.remove("active");
                });
                btnExp.addEventListener("click", () => {
                    deck.classList.add("ins-exploded-mode");
                    btnExp.classList.add("active");
                    btnIso.classList.remove("active");
                });
            }

            // 3D Gyroscope Mouse Parallax on Cockpit Deck throttled via requestAnimationFrame (60 FPS leak-free)
            let tiltRafPending = false;
            let latestTiltX = "0deg";
            let latestTiltY = "0deg";

            vp.addEventListener("mousemove", (e) => {
                if (window.innerWidth < 992) return;
                const rect = vp.getBoundingClientRect();
                const normX = (e.clientX - rect.left) / rect.width - 0.5;
                const normY = (e.clientY - rect.top) / rect.height - 0.5;
                const tiltX = (-normY * 12).toFixed(2);
                const tiltY = (normX * 14).toFixed(2);
                latestTiltX = `${tiltX}deg`;
                latestTiltY = `${tiltY}deg`;

                if (!tiltRafPending) {
                    tiltRafPending = true;
                    deck.style.setProperty("--tilt-x", latestTiltX);
                    deck.style.setProperty("--tilt-y", latestTiltY);
                    requestAnimationFrame(() => {
                        deck.style.setProperty("--tilt-x", latestTiltX);
                        deck.style.setProperty("--tilt-y", latestTiltY);
                        tiltRafPending = false;
                    });
                }
            }, { passive: true });

            vp.addEventListener("mouseleave", () => {
                tiltRafPending = false;
                deck.style.setProperty("--tilt-x", "0deg");
                deck.style.setProperty("--tilt-y", "0deg");
            });

            // 2-Way Layer Binding: Cockpit Cards <-> Hero Act Panes <-> Hero Pills <-> Steppers
            const heroSection = vp.closest(".s_cover") || vp.closest("section") || vp.closest(".container");
            const cards = deck.querySelectorAll(".ins-cockpit-card");
            const branches = deck.querySelectorAll(".ins-bus-branch");
            const taps = deck.querySelectorAll(".ins-bus-tap");
            const docks = deck.querySelectorAll(".ins-bus-dock");

            const actPanes = heroSection ? heroSection.querySelectorAll(".ins-hero-act-pane") : [];
            const pills = heroSection ? heroSection.querySelectorAll(".ins-hero-pill") : [];
            const steppers = heroSection ? heroSection.querySelectorAll(".ins-stepper-tab") : [];

            function activateLayer(layerNum) {
                const layerStr = String(layerNum);

                // 1. Cockpit Card Highlight
                cards.forEach(c => {
                    const l = c.getAttribute("data-layer") || c.getAttribute("data-act-target");
                    c.classList.toggle("ins-act-highlight", l === layerStr);
                });

                // 2. SVG Bus elements
                branches.forEach(b => b.classList.remove("active"));
                taps.forEach(t => t.classList.remove("active"));
                docks.forEach(d => d.classList.remove("active"));

                const activeBranch = deck.querySelector(`.ins-bus-branch-${layerStr}`);
                const activeTap = deck.querySelector(`.ins-bus-tap-${layerStr}`);
                const activeDock = deck.querySelector(`.ins-bus-dock-${layerStr}`);
                if (activeBranch) activeBranch.classList.add("active");
                if (activeTap) activeTap.classList.add("active");
                if (activeDock) activeDock.classList.add("active");

                // 3. Left Column Act Panes
                actPanes.forEach(pane => {
                    const act = pane.getAttribute("data-act");
                    pane.classList.toggle("active", act === layerStr);
                });

                // 4. Left Column Pill Navigation
                pills.forEach(pill => {
                    const target = pill.getAttribute("data-layer-target") || pill.getAttribute("data-act");
                    pill.classList.toggle("active", target === layerStr);
                });

                // 5. Stepper Tabs (if present)
                steppers.forEach(step => {
                    const act = step.getAttribute("data-act");
                    step.classList.toggle("active", act === layerStr);
                });
            }

            // Act Pane Clicks
            actPanes.forEach((pane) => {
                pane.addEventListener("click", () => {
                    const act = pane.getAttribute("data-act");
                    if (act) activateLayer(act);
                });
            });

            // Layer Card Clicks
            cards.forEach((card) => {
                card.addEventListener("click", () => {
                    const layer = card.getAttribute("data-layer") || card.getAttribute("data-act-target");
                    if (layer) activateLayer(layer);
                });
            });

            // Hero Pill Clicks
            pills.forEach((pill) => {
                pill.addEventListener("click", () => {
                    const target = pill.getAttribute("data-layer-target") || pill.getAttribute("data-act");
                    if (target) activateLayer(target);
                });
            });

            // Stepper Clicks
            steppers.forEach((step) => {
                step.addEventListener("click", () => {
                    const act = step.getAttribute("data-act");
                    if (act) activateLayer(act);
                });
            });

            // Smooth Auto-Cycle when multiple act panes exist (pauses on user hover & off-screen)
            if (actPanes.length > 1) {
                let currentLayer = 1;
                let isHovered = false;
                let isIntersecting = true;
                const cycleDuration = 7000;

                function startCockpitCycle() {
                    stopCockpitCycle();
                    vp.__cockpitCycleTimer = setInterval(() => {
                        if (!isHovered && isIntersecting) {
                            currentLayer = (currentLayer % 4) + 1;
                            activateLayer(currentLayer);
                        }
                    }, cycleDuration);
                }

                function stopCockpitCycle() {
                    if (vp.__cockpitCycleTimer) {
                        clearInterval(vp.__cockpitCycleTimer);
                        vp.__cockpitCycleTimer = null;
                    }
                }

                startCockpitCycle();

                if (heroSection) {
                    heroSection.addEventListener("mouseenter", () => { isHovered = true; }, { passive: true });
                    heroSection.addEventListener("mouseleave", () => { isHovered = false; }, { passive: true });

                    if ("IntersectionObserver" in window) {
                        if (vp.__cockpitObserver) {
                            vp.__cockpitObserver.disconnect();
                        }
                        vp.__cockpitObserver = new IntersectionObserver((entries) => {
                            entries.forEach((entry) => {
                                isIntersecting = entry.isIntersecting;
                                if (!isIntersecting) {
                                    stopCockpitCycle();
                                } else {
                                    startCockpitCycle();
                                }
                            });
                        }, { threshold: 0.05 });
                        vp.__cockpitObserver.observe(heroSection);
                    }
                }
            }
        });
    }
    initAllPage3DCockpits();

    // 9. C3.ai Enterprise Architecture & Code Studio Controller
    document.querySelectorAll(".ins-code-studio-box").forEach((studio) => {
        if (studio.__studio_initialized) return;
        studio.__studio_initialized = true;
        const tabs = studio.querySelectorAll(".ins-code-tab");
        const panes = studio.querySelectorAll(".ins-code-pane");
        const langTag = studio.querySelector(".ins-code-lang-tag");
        const envBadge = studio.querySelector(".ins-code-env-badge");
        const modeBtns = studio.querySelectorAll(".ins-code-mode-btn");
        const copyBtn = studio.querySelector(".ins-copy-code-btn");
        const runBtn = studio.querySelector(".ins-run-pipeline-btn");
        const statusBadge = studio.querySelector(".ins-exec-status-badge");
        const logStream = studio.querySelector("#ins_exec_log_stream");

        let currentMode = "airgap";
        let activePaneId = "scada";

        const langMap = {
            "scada": "Python 3.12 (OPC-UA)",
            "idp": "Python 3.12 (Multimodal)",
            "graph": "Cypher (W3C OWL)",
            "fsm": "Python 3.12 (FSM Engine)"
        };

        const codeSnippets = {
            "scada": {
                "airgap": `<pre class="m-0"><code><span class="token-comment"># Insilos Sovereign OS — Layer 1: Sovereign Industrial SCADA &amp; Anomaly FFT</span>
<span class="token-keyword">from</span> insilos.scada <span class="token-keyword">import</span> OPCUAClient, SensorStream, AnomalyDetector
<span class="token-keyword">from</span> insilos.security <span class="token-keyword">import</span> MerkleAirGapValidator

<span class="token-decorator">@pipeline</span>(layer=<span class="token-string">"SCADA_L1"</span>, frequency_hz=<span class="token-number">50.0</span>, airgap_enforced=<span class="token-keyword">True</span>)
<span class="token-keyword">async def</span> <span class="token-function">ingest_high_frequency_telemetry</span>(node_id: <span class="token-class">str</span> = <span class="token-string">"ENERGY_TURBINE_04"</span>):
    client = OPCUAClient.<span class="token-function">connect</span>(endpoint=<span class="token-string">"opc.tcp://10.24.8.1:4840"</span>, tls_cert=<span class="token-string">"/etc/insilos/pki/hsm.crt"</span>)
    stream = client.<span class="token-function">subscribe_telemetry</span>(metrics=[<span class="token-string">"vibration_rms"</span>, <span class="token-string">"stator_temp"</span>, <span class="token-string">"oil_pressure"</span>])
    
    <span class="token-keyword">async for</span> packet <span class="token-keyword">in</span> stream:
        <span class="token-comment"># Validate cryptographic Merkle root hash on inbound sensor frames</span>
        MerkleAirGapValidator.<span class="token-function">verify_packet_hash</span>(packet)
        
        <span class="token-comment"># Real-time Fast Fourier Transform (FFT) vibration harmonic detection</span>
        fft_spectrum = AnomalyDetector.<span class="token-function">spectral_fft</span>(packet.vibration_rms)
        <span class="token-keyword">if</span> fft_spectrum.harmonic_peak &gt; <span class="token-number">4.25</span>:  <span class="token-comment"># Exceeds ISO 10816 severe threshold</span>
            <span class="token-keyword">await</span> <span class="token-function">emit_event</span>(<span class="token-string">"CRITICAL_VIBRATION_DETECTED"</span>, payload=packet.<span class="token-function">to_dict</span>())
            <span class="token-keyword">return</span> {<span class="token-string">"status"</span>: <span class="token-string">"DISPATCH_REQUIRED"</span>, <span class="token-string">"target_layer"</span>: <span class="token-string">"L4_FSM"</span>, <span class="token-string">"latency_ms"</span>: <span class="token-number">11.8</span>}</code></pre>`,
                "cloud": `<pre class="m-0"><code><span class="token-comment"># Insilos Sovereign OS — Layer 1: Hybrid Cloud Federated Telemetry Ingestion</span>
<span class="token-keyword">from</span> insilos.scada <span class="token-keyword">import</span> EdgeGatewayClient, StreamBuffer, AnomalyDetector
<span class="token-keyword">from</span> insilos.cloud <span class="token-keyword">import</span> ZeroKnowledgeProofValidator, FederatedMesh

<span class="token-decorator">@pipeline</span>(layer=<span class="token-string">"SCADA_L1"</span>, frequency_hz=<span class="token-number">50.0</span>, target=<span class="token-string">"APAC_FEDERATED_CLOUD"</span>)
<span class="token-keyword">async def</span> <span class="token-function">ingest_federated_telemetry</span>(node_id: <span class="token-class">str</span> = <span class="token-string">"ENERGY_TURBINE_04"</span>):
    client = EdgeGatewayClient.<span class="token-function">connect</span>(endpoint=<span class="token-string">"wss://edge-gw.insilos.io:8443"</span>, tls_token=<span class="token-string">"/etc/insilos/pki/cloud_token.jwt"</span>)
    stream = client.<span class="token-function">subscribe_stream</span>(channel=<span class="token-string">"telemetry.live.power_grid"</span>, compression=<span class="token-string">"zstd"</span>)
    
    <span class="token-keyword">async for</span> packet <span class="token-keyword">in</span> stream:
        <span class="token-comment"># Zero-Knowledge cryptographic verification without decrypting payload</span>
        ZeroKnowledgeProofValidator.<span class="token-function">verify_federated_envelope</span>(packet)
        
        <span class="token-comment"># Real-time Fast Fourier Transform (FFT) anomaly detection</span>
        fft_spectrum = AnomalyDetector.<span class="token-function">spectral_fft</span>(packet.vibration_rms)
        <span class="token-keyword">if</span> fft_spectrum.harmonic_peak &gt; <span class="token-number">4.25</span>:
            <span class="token-keyword">await</span> FederatedMesh.<span class="token-function">broadcast</span>(<span class="token-string">"CRITICAL_VIBRATION_DETECTED"</span>, payload=packet.<span class="token-function">to_dict</span>())
            <span class="token-keyword">return</span> {<span class="token-string">"status"</span>: <span class="token-string">"DISPATCH_REQUIRED"</span>, <span class="token-string">"target_layer"</span>: <span class="token-string">"L4_FSM"</span>, <span class="token-string">"latency_ms"</span>: <span class="token-number">14.2</span>}</code></pre>`
            },
            "idp": {
                "airgap": `<pre class="m-0"><code><span class="token-comment"># Insilos Sovereign OS — Layer 2: Sovereign Vertical IDP &amp; WCO SAFE Trade Engine</span>
<span class="token-keyword">from</span> insilos.idp <span class="token-keyword">import</span> MultimodalParser, CustomsRuleEngine
<span class="token-keyword">from</span> insilos.compliance <span class="token-keyword">import</span> EVFTA_Matrix, VNACCS_Reconciler

<span class="token-decorator">@agent_action</span>(layer=<span class="token-string">"IDP_L2"</span>, accuracy_sla=<span class="token-number">0.998</span>, airgap_enforced=<span class="token-keyword">True</span>)
<span class="token-keyword">def</span> <span class="token-function">process_customs_dossier</span>(dossier_pdf: <span class="token-class">bytes</span>, bl_number: <span class="token-class">str</span>) -&gt; <span class="token-class">dict</span>:
    <span class="token-comment"># Multimodal OCR Extraction (Bill of Lading, Commercial Invoice, Packing List)</span>
    extracted = MultimodalParser.<span class="token-function">extract</span>(dossier_pdf, schema=<span class="token-string">"VNACCS_E_CUSTOMS_V4"</span>, onprem_vllm=<span class="token-keyword">True</span>)
    
    <span class="token-comment"># 3-Way Cross-Reconciliation against ERP Purchase Order &amp; Port Ledger</span>
    reconciliation = VNACCS_Reconciler.<span class="token-function">match_triad</span>(
        bill_of_lading=extracted.<span class="token-function">get</span>(<span class="token-string">"bill_of_lading"</span>),
        invoice_items=extracted.<span class="token-function">get</span>(<span class="token-string">"line_items"</span>),
        erp_po_ref=<span class="token-string">"PO-2026-8891"</span>
    )
    <span class="token-keyword">assert</span> reconciliation.variance == <span class="token-number">0.0</span>, <span class="token-string">"Discrepancy detected in customs valuation"</span>
    
    compliance_proof = EVFTA_Matrix.<span class="token-function">validate_co_origin</span>(extracted.hs_code, origin_country=<span class="token-string">"VN"</span>)
    <span class="token-keyword">return</span> {<span class="token-string">"status"</span>: <span class="token-string">"STRAIGHT_THROUGH_PROCESSED"</span>, <span class="token-string">"hs_code"</span>: extracted.hs_code, <span class="token-string">"preferential_tariff"</span>: compliance_proof.duty_rate, <span class="token-string">"processing_time_sec"</span>: <span class="token-number">0.382</span>}</code></pre>`,
                "cloud": `<pre class="m-0"><code><span class="token-comment"># Insilos Sovereign OS — Layer 2: Hybrid Cloud Vertical IDP &amp; Global Clearing</span>
<span class="token-keyword">from</span> insilos.idp <span class="token-keyword">import</span> MultimodalParser, CloudCustomsEngine
<span class="token-keyword">from</span> insilos.compliance <span class="token-keyword">import</span> EVFTA_Matrix, GlobalTradeClearing

<span class="token-decorator">@agent_action</span>(layer=<span class="token-string">"IDP_L2"</span>, accuracy_sla=<span class="token-number">0.998</span>, target=<span class="token-string">"APAC_FEDERATED_CLOUD"</span>)
<span class="token-keyword">def</span> <span class="token-function">process_customs_dossier_cloud</span>(dossier_pdf: <span class="token-class">bytes</span>, bl_number: <span class="token-class">str</span>) -&gt; <span class="token-class">dict</span>:
    <span class="token-comment"># Multimodal OCR Extraction via distributed regional inference cluster</span>
    extracted = MultimodalParser.<span class="token-function">extract</span>(dossier_pdf, schema=<span class="token-string">"VNACCS_E_CUSTOMS_V4"</span>, federated_mesh=<span class="token-keyword">True</span>)
    
    <span class="token-comment"># Cloud Cross-Reconciliation against Global ERP (SAP / Oracle / NetSuite)</span>
    reconciliation = GlobalTradeClearing.<span class="token-function">match_triad</span>(
        bill_of_lading=extracted.<span class="token-function">get</span>(<span class="token-string">"bill_of_lading"</span>),
        invoice_items=extracted.<span class="token-function">get</span>(<span class="token-string">"line_items"</span>),
        erp_po_ref=<span class="token-string">"PO-2026-8891"</span>
    )
    <span class="token-keyword">assert</span> reconciliation.variance == <span class="token-number">0.0</span>, <span class="token-string">"Discrepancy detected in customs valuation"</span>
    
    compliance_proof = EVFTA_Matrix.<span class="token-function">validate_co_origin</span>(extracted.hs_code, origin_country=<span class="token-string">"VN"</span>)
    <span class="token-keyword">return</span> {<span class="token-string">"status"</span>: <span class="token-string">"STRAIGHT_THROUGH_PROCESSED"</span>, <span class="token-string">"hs_code"</span>: extracted.hs_code, <span class="token-string">"preferential_tariff"</span>: compliance_proof.duty_rate, <span class="token-string">"processing_time_sec"</span>: <span class="token-number">0.415</span>}</code></pre>`
            },
            "graph": {
                "airgap": `<pre class="m-0"><code><span class="token-comment">// Insilos Sovereign OS — Layer 3: Sovereign Knowledge Graph Domino Risk Traversal</span>
<span class="token-comment">// Queries 1.4M Enterprise Nodes with &lt;15ms response under Merkle DAG</span>
<span class="token-keyword">MATCH</span> (plant:<span class="token-class">ManufacturingPlant</span> {id: <span class="token-string">"PLANT_BINH_DUONG"</span>, airgap: <span class="token-keyword">true</span>})-[:<span class="token-function">OPERATES</span>]-&gt;(line:<span class="token-class">ProductionLine</span>)
<span class="token-keyword">MATCH</span> (line)-[:<span class="token-function">DEPENDS_ON</span>]-&gt;(component:<span class="token-class">CriticalComponent</span>)
<span class="token-keyword">MATCH</span> (component)-[:<span class="token-function">SUPPLIED_BY</span>]-&gt;(vendor:<span class="token-class">Supplier</span>)
<span class="token-keyword">MATCH</span> (vendor)-[:<span class="token-function">SHIPS_VIA</span>]-&gt;(vessel:<span class="token-class">ContainerVessel</span>)-[:<span class="token-function">SCHEDULED_PORT</span>]-&gt;(port:<span class="token-class">SeaPort</span> {un_locode: <span class="token-string">"VNHPH"</span>})
<span class="token-keyword">WHERE</span> vessel.weather_risk_index &gt; <span class="token-number">0.75</span> <span class="token-keyword">OR</span> component.predicted_wear_rate &gt; <span class="token-number">0.85</span>
<span class="token-keyword">RETURN</span> 
    plant.name <span class="token-keyword">AS</span> Facility,
    component.serial_number <span class="token-keyword">AS</span> Component,
    vessel.estimated_delay_hours <span class="token-keyword">AS</span> TransitDelay,
    (vessel.weather_risk_index * component.downtime_cost_per_hour) <span class="token-keyword">AS</span> ProjectedRiskUSD
<span class="token-keyword">ORDER BY</span> ProjectedRiskUSD <span class="token-keyword">DESC</span>
<span class="token-keyword">LIMIT</span> <span class="token-number">10</span>;</code></pre>`,
                "cloud": `<pre class="m-0"><code><span class="token-comment">// Insilos Sovereign OS — Layer 3: Federated Hybrid Cloud Knowledge Graph Traversal</span>
<span class="token-comment">// Queries 12.8M APAC Enterprise Nodes across Singapore &amp; Vietnam Multi-Region Edges</span>
<span class="token-keyword">MATCH</span> (plant:<span class="token-class">ManufacturingPlant</span> {id: <span class="token-string">"PLANT_BINH_DUONG"</span>})-[:<span class="token-function">FEDERATED_EDGE</span>]-&gt;(hub:<span class="token-class">GlobalTradeNode</span>)
<span class="token-keyword">MATCH</span> (hub)-[:<span class="token-function">DEPENDS_ON</span>]-&gt;(component:<span class="token-class">CriticalComponent</span>)
<span class="token-keyword">MATCH</span> (component)-[:<span class="token-function">GLOBAL_SOURCING</span>]-&gt;(vendor:<span class="token-class">Supplier</span>)
<span class="token-keyword">MATCH</span> (vendor)-[:<span class="token-function">SHIPS_VIA</span>]-&gt;(vessel:<span class="token-class">ContainerVessel</span>)-[:<span class="token-function">PORT_OF_CALL</span>]-&gt;(port:<span class="token-class">SeaPort</span> {un_locode: <span class="token-string">"VNHPH"</span>})
<span class="token-keyword">WHERE</span> vessel.weather_risk_index &gt; <span class="token-number">0.70</span> <span class="token-keyword">OR</span> component.lead_time_days &gt; <span class="token-number">14</span>
<span class="token-keyword">RETURN</span> 
    hub.region <span class="token-keyword">AS</span> ClusterRegion,
    component.serial_number <span class="token-keyword">AS</span> Component,
    vessel.estimated_delay_hours <span class="token-keyword">AS</span> TransitDelay,
    (vessel.weather_risk_index * component.downtime_cost_per_hour) <span class="token-keyword">AS</span> ProjectedRiskUSD
<span class="token-keyword">ORDER BY</span> ProjectedRiskUSD <span class="token-keyword">DESC</span>
<span class="token-keyword">LIMIT</span> <span class="token-number">10</span>;</code></pre>`
            },
            "fsm": {
                "airgap": `<pre class="m-0"><code><span class="token-comment"># Insilos Sovereign OS — Layer 4: Sovereign FSM Dispatch &amp; Zero-Downtime</span>
<span class="token-keyword">from</span> insilos.fsm <span class="token-keyword">import</span> DispatchEngine, MobileFieldHub
<span class="token-keyword">from</span> insilos.erp <span class="token-keyword">import</span> ERPConnector

<span class="token-decorator">@workflow</span>(layer=<span class="token-string">"FSM_L4"</span>, target_sla_minutes=<span class="token-number">45</span>, airgap_mesh=<span class="token-keyword">True</span>)
<span class="token-keyword">def</span> <span class="token-function">orchestrate_predictive_repair</span>(alert_event: <span class="token-class">dict</span>):
    <span class="token-comment"># Match best technician by certifications (IEC 61850), live GPS &amp; van inventory</span>
    assigned_tech = DispatchEngine.<span class="token-function">find_optimal_technician</span>(
        required_cert=<span class="token-string">"HIGH_VOLTAGE_SPECIALIST_L3"</span>,
        required_parts=[<span class="token-string">"BEARING_SKF_6314_2RS1"</span>],
        max_eta_minutes=<span class="token-number">60</span>
    )
    
    <span class="token-comment"># Auto-generate ERP Work Order &amp; Reserved Spares in SAP/Odoo on-prem</span>
    work_order = ERPConnector.<span class="token-function">create_maintenance_order</span>(
        asset_id=alert_event[<span class="token-string">"asset_id"</span>],
        technician_id=assigned_tech.id,
        urgency=<span class="token-string">"HIGH_PRIORITY_PREDICTIVE"</span>
    )
    
    <span class="token-comment"># Push encrypted job pack to field engineer's mobile device via sovereign BLE/Wi-Fi mesh</span>
    MobileFieldHub.<span class="token-function">push_job</span>(assigned_tech.device_id, work_order.pack)
    <span class="token-keyword">return</span> {<span class="token-string">"work_order_id"</span>: work_order.number, <span class="token-string">"ftfr_probability"</span>: <span class="token-number">0.948</span>, <span class="token-string">"status"</span>: <span class="token-string">"DISPATCHED"</span>}</code></pre>`,
                "cloud": `<pre class="m-0"><code><span class="token-comment"># Insilos Sovereign OS — Layer 4: Federated Cloud FSM Dispatch &amp; Fleet Routing</span>
<span class="token-keyword">from</span> insilos.fsm <span class="token-keyword">import</span> CloudDispatchEngine, FleetTelemetryHub
<span class="token-keyword">from</span> insilos.erp <span class="token-keyword">import</span> CloudERPConnector

<span class="token-decorator">@workflow</span>(layer=<span class="token-string">"FSM_L4"</span>, target_sla_minutes=<span class="token-number">45</span>, deployment=<span class="token-string">"APAC_HYBRID_CLOUD"</span>)
<span class="token-keyword">def</span> <span class="token-function">orchestrate_predictive_repair_cloud</span>(alert_event: <span class="token-class">dict</span>):
    <span class="token-comment"># Dynamic Fleet Dispatch via real-time satellite GPS &amp; regional spares depot</span>
    assigned_tech = CloudDispatchEngine.<span class="token-function">find_optimal_technician</span>(
        required_cert=<span class="token-string">"HIGH_VOLTAGE_SPECIALIST_L3"</span>,
        required_parts=[<span class="token-string">"BEARING_SKF_6314_2RS1"</span>],
        max_eta_minutes=<span class="token-number">45</span>
    )
    
    <span class="token-comment"># Synchronize Work Order to Cloud ERP &amp; Regional Logistics Hub</span>
    work_order = CloudERPConnector.<span class="token-function">create_maintenance_order</span>(
        asset_id=alert_event[<span class="token-string">"asset_id"</span>],
        technician_id=assigned_tech.id,
        urgency=<span class="token-string">"CRITICAL_HIGH"</span>
    )
    
    <span class="token-comment"># Push job via zero-trust mobile tunnel to engineer app</span>
    FleetTelemetryHub.<span class="token-function">push_job_cloud</span>(assigned_tech.device_id, work_order.pack)
    <span class="token-keyword">return</span> {<span class="token-string">"work_order_id"</span>: work_order.number, <span class="token-string">"ftfr_probability"</span>: <span class="token-number">0.962</span>, <span class="token-string">"status"</span>: <span class="token-string">"DISPATCHED"</span>}</code></pre>`
            }
        };

        function renderActiveCode() {
            panes.forEach(p => {
                const paneId = p.getAttribute("data-pane");
                if (paneId === activePaneId) {
                    p.classList.add("active");
                    if (codeSnippets[paneId] && codeSnippets[paneId][currentMode]) {
                        p.innerHTML = codeSnippets[paneId][currentMode];
                    }
                } else {
                    p.classList.remove("active");
                }
            });
            if (langTag && langMap[activePaneId]) {
                langTag.innerText = langMap[activePaneId];
            }
        }

        tabs.forEach(tab => {
            tab.addEventListener("click", () => {
                activePaneId = tab.getAttribute("data-pane") || "scada";
                tabs.forEach(t => t.classList.remove("active"));
                tab.classList.add("active");
                renderActiveCode();
            });
        });

        modeBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                modeBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                currentMode = btn.getAttribute("data-mode") || "airgap";
                if (envBadge) {
                    if (currentMode === "airgap") {
                        envBadge.innerHTML = '<span class="ins-live-ping ins-live-ping--emerald me-1"></span> AIR-GAPPED ON-PREM';
                        envBadge.className = "badge bg-secondary bg-opacity-25 text-mint font-monospace small ins-code-env-badge";
                    } else {
                        envBadge.innerHTML = '<span class="ins-live-ping me-1"></span> APAC HYBRID CLOUD';
                        envBadge.className = "badge bg-secondary bg-opacity-25 text-cyan font-monospace small ins-code-env-badge";
                    }
                }
                renderActiveCode();
            });
        });

        if (copyBtn) {
            copyBtn.addEventListener("click", () => {
                const activePane = studio.querySelector(".ins-code-pane.active");
                if (activePane) {
                    const text = activePane.innerText.trim();
                    navigator.clipboard.writeText(text).then(() => {
                        const original = copyBtn.innerText;
                        copyBtn.innerText = "COPIED! ✔";
                        setTimeout(() => { copyBtn.innerText = original; }, 2000);
                    }).catch(() => {
                        copyBtn.innerText = "COPIED! ✔";
                        setTimeout(() => { copyBtn.innerText = "COPY"; }, 2000);
                    });
                }
            });
        }

        let execTimers = [];
        let isExecuting = false;

        function clearExecTimers() {
            execTimers.forEach(id => clearTimeout(id));
            execTimers = [];
        }

        if (runBtn && logStream) {
            runBtn.addEventListener("click", () => {
                if (isExecuting) return;
                isExecuting = true;
                clearExecTimers();

                runBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span><span>ĐANG THỰC THI...</span>';
                if (statusBadge) {
                    statusBadge.innerText = "RUNNING...";
                    statusBadge.className = "badge bg-warning bg-opacity-25 text-warning font-monospace small ins-exec-status-badge";
                }

                // Reset stage indicator nodes
                const stageNodes = studio.querySelectorAll(".ins-stage-node");
                stageNodes.forEach(node => node.classList.remove("active"));

                logStream.innerHTML = "";

                const airgapLogs = [
                    { time: "00:00:00.012", tag: "[CONNECT]", msg: "Handshake with Sovereign Cluster (10.24.8.1:4840) ... OK (TLS 1.3 / FIPS 140-3 HSM)", color: "text-secondary", stage: 1 },
                    { time: "00:00:00.084", tag: "[INGEST] ", msg: "Inbound Stream: 12,400 sensor frames/s · Merkle hash match: 0x9f4a...e12b", color: "text-mint", stage: 1 },
                    { time: "00:00:00.198", tag: "[MODEL]  ", msg: "Multimodal Inference: 14 fields extracted (99.84% accuracy) · WCO SAFE verified", color: "text-cyan", stage: 2 },
                    { time: "00:00:00.295", tag: "[GRAPH]  ", msg: "Cypher Traversal: 1,420,000 nodes queried in 11.8ms · 0 circular dependencies", color: "text-cyan", stage: 3 },
                    { time: "00:00:00.382", tag: "[FSM]    ", msg: "Automated Dispatch: Work Order #WO-2026-9041 committed to ERP · SLA Met", color: "text-warning", stage: 4 },
                    { time: "00:00:00.410", tag: "[SUCCESS]", msg: "Pipeline execution complete in 382ms. 0 errors. Audit proof saved to Merkle DAG.", color: "text-mint fw-bold", stage: null }
                ];

                const cloudLogs = [
                    { time: "00:00:00.015", tag: "[CONNECT]", msg: "Handshake with APAC Gateway (wss://edge-gw.insilos.io:8443) ... OK (mTLS 1.3)", color: "text-secondary", stage: 1 },
                    { time: "00:00:00.092", tag: "[INGEST] ", msg: "Federated Ingest: 12,400 frames/s · Zero-Knowledge Proof verified", color: "text-cyan", stage: 1 },
                    { time: "00:00:00.210", tag: "[MODEL]  ", msg: "Regional Inference: 14 fields extracted (99.82% accuracy) · Global Clearing OK", color: "text-cyan", stage: 2 },
                    { time: "00:00:00.315", tag: "[GRAPH]  ", msg: "Multi-Region Graph: 12.8M nodes traversed across SG/VN in 14.2ms", color: "text-cyan", stage: 3 },
                    { time: "00:00:00.395", tag: "[FSM]    ", msg: "Fleet Dispatch: Technician assigned with SLA 45m · Push notification sent", color: "text-warning", stage: 4 },
                    { time: "00:00:00.425", tag: "[SUCCESS]", msg: "Federated Pipeline execution complete in 425ms. Audit proof synced to Mesh.", color: "text-mint fw-bold", stage: null }
                ];

                const logs = (currentMode === "airgap") ? airgapLogs : cloudLogs;

                logs.forEach((log, index) => {
                    const timerId = setTimeout(() => {
                        const logLine = document.createElement("div");
                        logLine.className = `ins-log-line ${log.color}`;
                        logLine.innerHTML = `<span class="text-secondary">${log.time}</span> <span class="fw-bold">${log.tag}</span> ${log.msg}`;
                        logStream.appendChild(logLine);
                        logStream.scrollTop = logStream.scrollHeight;

                        if (log.stage) {
                            stageNodes.forEach(node => {
                                const s = parseInt(node.getAttribute("data-stage"), 10);
                                if (s <= log.stage) {
                                    node.classList.add("active");
                                }
                            });
                        }

                        if (index === logs.length - 1) {
                            isExecuting = false;
                            runBtn.innerHTML = '<svg class="ph-duotone ph-arrow-clockwise ph-xs me-1"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-arrow-clockwise"/></svg><span>CHẠY LẠI (REPLAY)</span>';
                            if (statusBadge) {
                                const ms = (currentMode === "airgap") ? "382ms" : "425ms";
                                statusBadge.innerText = `COMPLETED (${ms}) ✔`;
                                statusBadge.className = "badge bg-success bg-opacity-25 text-mint font-monospace small ins-exec-status-badge";
                            }
                        }
                    }, (index + 1) * 140);
                    execTimers.push(timerId);
                });
            });
        }
    });

    // ── Platform Topology Interactive Controller ──────────────────────────
    function initPlatformTopology() {
        document.querySelectorAll('.ins-platform-topology').forEach(topo => {
            if (topo.__topo_initialized) return;
            topo.__topo_initialized = true;

            // Accordion click behavior
            topo.querySelectorAll('.ins-topology-row-header').forEach(header => {
                header.addEventListener('click', () => {
                    const row = header.closest('.ins-topology-row');
                    const wasExpanded = row.classList.contains('ins-topology-row--expanded');
                    // Collapse all rows
                    topo.querySelectorAll('.ins-topology-row--expanded').forEach(r => {
                        r.classList.remove('ins-topology-row--expanded');
                    });
                    // Toggle clicked row
                    if (!wasExpanded) {
                        row.classList.add('ins-topology-row--expanded');
                    }
                });
            });

            // MutationObserver for Customize Panel sync
            const topoObserver = new MutationObserver(mutations => {
                mutations.forEach(mutation => {
                    if (mutation.type !== 'attributes') return;
                    const attr = mutation.attributeName;
                    const val = topo.getAttribute(attr);
                    if (val === null) return;

                    if (attr === 'data-topology-title') {
                        const el = topo.querySelector('.ins-topology-eyebrow');
                        if (el) el.textContent = val;
                    }

                    const rowMatch = attr.match(/^data-row(\d)-(label|tag|icon|items)$/);
                    if (rowMatch) {
                        const rowNum = rowMatch[1];
                        const field = rowMatch[2];
                        const row = topo.querySelector(`.ins-topology-row[data-topo-row="${rowNum}"]`);
                        if (!row) return;

                        if (field === 'label') {
                            const el = row.querySelector('.ins-topology-row-label');
                            if (el) el.textContent = val;
                        } else if (field === 'tag') {
                            const el = row.querySelector('.ins-topology-row-tag');
                            if (el) el.textContent = val;
                        } else if (field === 'icon') {
                            const el = row.querySelector('use');
                            if (el) el.setAttribute('href', `/insilos_website/static/src/icons/phosphor-duotone.svg#ph-${val}`);
                        } else if (field === 'items') {
                            const items = val.split(',').map(s => s.trim()).filter(Boolean);
                            const grid = row.querySelector('.ins-topology-grid') || row.querySelector('.ins-topology-cloud-grid');
                            if (grid) {
                                const isCloud = grid.classList.contains('ins-topology-cloud-grid');
                                const cls = isCloud ? 'ins-topology-cloud-tile' : 'ins-topology-item';
                                grid.innerHTML = items.map(item => `<div class="${cls}">${item}</div>`).join('');
                            }
                        }
                    }
                });
            });
            topoObserver.observe(topo, { attributes: true });
        });
    }
    
    // ── Insilos 12 Gold Master Suite Controller & Cinema Theater Modal ──
    function initGoldMasterSuite() {
        const suite = document.querySelector('#insilos-gold-suite');
        if (!suite) return;

        // 1. Domain Category Filter Tabs
        const filterBtns = suite.querySelectorAll('.ins-gold-filter-btn');
        const cardCols = suite.querySelectorAll('.ins-gold-card-col');

        filterBtns.forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const targetCategory = btn.getAttribute('data-filter') || 'all';

                cardCols.forEach((col) => {
                    const cardCategory = col.getAttribute('data-category');
                    if (targetCategory === 'all' || cardCategory === targetCategory) {
                        col.classList.remove('d-none');
                        col.classList.add('ins-card-visible');
                    } else {
                        col.classList.add('d-none');
                        col.classList.remove('ins-card-visible');
                    }
                });
            });
        });

        // 2. Cinema Theater Video Modal Controller
        const modalEl = document.getElementById('insilosGoldVideoModal');
        if (!modalEl) return;

        const modalVideo = document.getElementById('insilosGoldVideoPlayer');
        const modalSource = document.getElementById('insilosGoldVideoSource');
        const modalEpisode = document.getElementById('ins-gold-modal-episode');
        const modalIndustryText = document.getElementById('ins-gold-modal-industry-text');
        const modalTitle = document.getElementById('insilosGoldVideoModalLabel');
        const modalMetricText = document.getElementById('ins-gold-modal-metric-text');
        const modalLufsText = document.getElementById('ins-gold-modal-lufs-text');
        const modalDesc = document.getElementById('ins-gold-modal-desc');

        function openCinemaModal(card) {
            if (!card) return;
            const videoSrc = card.getAttribute('data-video-src');
            const poster = card.getAttribute('data-poster');
            const episode = card.getAttribute('data-episode');
            const title = card.getAttribute('data-title');
            const industry = card.getAttribute('data-industry');
            const metric = card.getAttribute('data-metric');
            const lufs = card.getAttribute('data-lufs');
            const desc = card.getAttribute('data-desc');

            if (modalEpisode && episode) modalEpisode.textContent = episode;
            if (modalIndustryText && industry) modalIndustryText.textContent = industry;
            if (modalTitle && title) modalTitle.textContent = title;
            if (modalMetricText && metric) modalMetricText.textContent = metric;
            if (modalLufsText && lufs) modalLufsText.textContent = lufs;
            if (modalDesc && desc) modalDesc.textContent = desc;

            if (modalVideo && videoSrc) {
                if (poster) {
                    modalVideo.setAttribute('poster', poster);
                } else {
                    modalVideo.removeAttribute('poster');
                }
                if (modalSource) {
                    modalSource.setAttribute('src', videoSrc);
                } else {
                    modalVideo.setAttribute('src', videoSrc);
                }
                modalVideo.load();
                const playPromise = modalVideo.play();
                if (playPromise !== undefined) {
                    playPromise.catch((err) => {
                        console.warn('Cinema modal autoplay prevented or deferred:', err);
                    });
                }
            }

            if (window.bootstrap && window.bootstrap.Modal) {
                const modalInstance = window.bootstrap.Modal.getOrCreateInstance(modalEl);
                modalInstance.show();
            } else {
                modalEl.classList.add('show');
                modalEl.style.display = 'block';
                document.body.classList.add('modal-open');
            }
        }

        // Card & Theater Trigger Clicks
        const cards = suite.querySelectorAll('.ins-gold-card');
        cards.forEach((card) => {
            const trigger = card.querySelector('.ins-theater-trigger');
            const cardTitle = card.querySelector('.card-title');

            if (trigger) {
                trigger.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    openCinemaModal(card);
                });
                trigger.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        openCinemaModal(card);
                    }
                });
            }

            if (cardTitle) {
                cardTitle.style.cursor = 'pointer';
                cardTitle.addEventListener('click', (e) => {
                    e.preventDefault();
                    openCinemaModal(card);
                });
            }
        });

        // Modal hidden event -> pause, reset playback, clear src
        modalEl.addEventListener('hidden.bs.modal', () => {
            if (modalVideo) {
                modalVideo.pause();
                modalVideo.currentTime = 0;
                if (modalSource) {
                    modalSource.removeAttribute('src');
                }
                modalVideo.removeAttribute('src');
                modalVideo.load();
            }
        });

        // Close on dismiss buttons
        modalEl.querySelectorAll('[data-bs-dismiss="modal"]').forEach((btn) => {
            btn.addEventListener('click', () => {
                if (modalVideo) {
                    modalVideo.pause();
                    modalVideo.currentTime = 0;
                }
                if (!window.bootstrap || !window.bootstrap.Modal) {
                    modalEl.classList.remove('show');
                    modalEl.style.display = 'none';
                    document.body.classList.remove('modal-open');
                }
            });
        });

        // Close on backdrop click (if manual fallback)
        modalEl.addEventListener('click', (e) => {
            if (e.target === modalEl) {
                if (modalVideo) {
                    modalVideo.pause();
                    modalVideo.currentTime = 0;
                }
                if (!window.bootstrap || !window.bootstrap.Modal) {
                    modalEl.classList.remove('show');
                    modalEl.style.display = 'none';
                    document.body.classList.remove('modal-open');
                }
            }
        });

        // Close on ESC key (if manual fallback)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modalEl.classList.contains('show')) {
                if (modalVideo) {
                    modalVideo.pause();
                    modalVideo.currentTime = 0;
                }
                if (!window.bootstrap || !window.bootstrap.Modal) {
                    modalEl.classList.remove('show');
                    modalEl.style.display = 'none';
                    document.body.classList.remove('modal-open');
                }
            }
        });
    }

    // ── Interactive Pricing Configurator Controller ────────────────────────
    function initPricingConfigurator() {
        const configurators = document.querySelectorAll(
            ".ins-modular-configurator, #ins_pricing_configurator, .ins-pricing-section, #pricing"
        );
        if (!configurators.length) return;

        configurators.forEach((cfg) => {
            if (cfg.__pricing_initialized) return;
            cfg.__pricing_initialized = true;

            const billingBtns = cfg.querySelectorAll(".ins-billing-btn, [data-billing]");
            const moduleCheckboxes = cfg.querySelectorAll(".ins-mod-check, input[type='checkbox'][data-price-month]");
            const dynPriceVnd = cfg.querySelector(".ins-dyn-price, #ins_pricing_total_vnd");
            const dynPriceUsd = cfg.querySelector(".ins-dyn-price-usd, #ins_pricing_total_usd");
            const dynSavings = cfg.querySelector(".ins-dyn-savings, #ins_pricing_net_savings");
            const paybackLabel = cfg.querySelector(".ins-payback-label, #ins_pricing_payback_label");
            const roiProgressFill = cfg.querySelector(".ins-roi-progress-fill, #ins_pricing_roi_bar");

            let billingCycle = "monthly"; // "monthly" or "annual"

            function updatePricing() {
                let monthlyBase = 0;
                let activeCount = 0;

                moduleCheckboxes.forEach((chk) => {
                    const price = parseInt(chk.getAttribute("data-price-month") || "0", 10);
                    const card = chk.closest(".ins-module-card") || chk.closest("label");
                    if (chk.checked) {
                        monthlyBase += price;
                        activeCount++;
                        if (card) card.classList.add("ins-module-card--active");
                    } else {
                        if (card) card.classList.remove("ins-module-card--active");
                    }
                });

                // Fallback baseline if no checkboxes are placed on the page
                if (monthlyBase === 0 && moduleCheckboxes.length === 0) {
                    monthlyBase = 42000000;
                }

                const multiplier = (billingCycle === "annual") ? 0.8 : 1.0;
                const effectiveMonthly = Math.round(monthlyBase * multiplier);
                const usdEquiv = Math.round(effectiveMonthly / 25000);
                const annualSavings = Math.round(effectiveMonthly * 4.4 * 12);

                const paybackMonths = (3.2 * (monthlyBase / 42000000)).toFixed(1);
                const roiPercent = Math.min(95, Math.max(35, Math.round(85 - (monthlyBase / 80000000) * 20)));

                if (dynPriceVnd) {
                    dynPriceVnd.textContent = `₫${effectiveMonthly.toLocaleString()}`;
                }
                if (dynPriceUsd) {
                    dynPriceUsd.textContent = `$${usdEquiv.toLocaleString()} USD/mo`;
                }
                if (dynSavings) {
                    dynSavings.textContent = `₫${annualSavings.toLocaleString()} VNĐ`;
                }
                if (paybackLabel) {
                    paybackLabel.innerHTML = `Điểm hòa vốn: <strong>${paybackMonths} Tháng</strong>`;
                }
                if (roiProgressFill) {
                    roiProgressFill.style.width = `${roiPercent}%`;
                    roiProgressFill.setAttribute("aria-valuenow", roiPercent);
                }
            }

            // Billing switch listeners
            billingBtns.forEach((btn) => {
                btn.addEventListener("click", (e) => {
                    e.preventDefault();
                    billingBtns.forEach(b => b.classList.remove("active"));
                    btn.classList.add("active");
                    const cycle = btn.getAttribute("data-billing") || "monthly";
                    billingCycle = cycle;
                    updatePricing();
                });
            });

            // Checkbox listeners
            moduleCheckboxes.forEach((chk) => {
                chk.addEventListener("change", updatePricing);
            });

            updatePricing();
        });
    }

    // ── Filterable Resource Hub Controller ─────────────────────────────────
    function initResourceFilters() {
        const filterBars = document.querySelectorAll(
            ".ins-resource-filter-group, [data-name='Resources Category Filter'], #resources-grid"
        );
        if (!filterBars.length) return;

        const filterBtns = document.querySelectorAll(".ins-res-filter-btn, [data-filter]");
        const searchInput = document.getElementById("ins_resource_search") || document.querySelector(".ins-resource-search-input");
        const cards = document.querySelectorAll(
            ".ins-resource-card, .ins-dossier-card, .ins-thumbnail-card, .ins-download-gate-card, [data-category]"
        );

        let activeFilter = "all";
        let searchQuery = "";

        function applyFilters() {
            cards.forEach((card) => {
                const category = (card.getAttribute("data-category") || "").toLowerCase();
                const cardText = (card.textContent || "").toLowerCase();
                const container = card.closest(".col-lg-4, .col-md-6, .col-12, .col") || card;

                const matchesCategory = (activeFilter === "all") || (category === activeFilter) || category.includes(activeFilter);
                const matchesSearch = (!searchQuery) || cardText.includes(searchQuery);

                if (matchesCategory && matchesSearch) {
                    container.classList.remove("d-none");
                    card.classList.add("ins-card-visible");
                } else {
                    container.classList.add("d-none");
                    card.classList.remove("ins-card-visible");
                }
            });
        }

        filterBtns.forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                filterBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                activeFilter = (btn.getAttribute("data-filter") || "all").toLowerCase();
                applyFilters();
            });
        });

        if (searchInput) {
            let debounceTimer = null;
            searchInput.addEventListener("input", (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    searchQuery = e.target.value.trim().toLowerCase();
                    applyFilters();
                }, 150);
            });
        }
    }

    // ── 3-Step Demo Request Wizard Controller ──────────────────────────────
    function initDemoWizard() {
        const wizardForms = document.querySelectorAll(
            ".ins-step-wizard, #ins_demo_wizard, form[action='/request-demo']"
        );
        if (!wizardForms.length) return;

        wizardForms.forEach((root) => {
            const form = root.tagName === "FORM" ? root : root.querySelector("form") || document.querySelector("form[action='/request-demo']");
            if (!form || form.__wizard_initialized) return;
            form.__wizard_initialized = true;

            const stepItems = document.querySelectorAll(".ins-step-item[data-step]");
            const stepPanes = form.querySelectorAll(".ins-step-pane[data-step]");
            const nextBtns = form.querySelectorAll(".ins-btn-step-next, [data-action='next-step']");
            const prevBtns = form.querySelectorAll(".ins-btn-step-prev, [data-action='prev-step']");

            if (!stepPanes.length) return;

            let currentStep = 1;
            const totalSteps = stepPanes.length;

            function showStep(stepNum) {
                currentStep = stepNum;
                stepPanes.forEach((pane) => {
                    const s = parseInt(pane.getAttribute("data-step"), 10);
                    pane.classList.toggle("active", s === currentStep);
                    pane.classList.toggle("d-none", s !== currentStep);
                });

                stepItems.forEach((item) => {
                    const s = parseInt(item.getAttribute("data-step"), 10);
                    item.classList.toggle("active", s === currentStep);
                    item.classList.toggle("completed", s < currentStep);
                });
            }

            function validateStep(stepNum) {
                const pane = form.querySelector(`.ins-step-pane[data-step='${stepNum}']`);
                if (!pane) return true;
                const requiredInputs = pane.querySelectorAll("input[required], select[required], textarea[required]");
                let isValid = true;
                requiredInputs.forEach((input) => {
                    if (!input.value.trim()) {
                        isValid = false;
                        input.classList.add("is-invalid");
                        input.addEventListener("input", () => input.classList.remove("is-invalid"), { once: true });
                    }
                });
                return isValid;
            }

            nextBtns.forEach((btn) => {
                btn.addEventListener("click", (e) => {
                    e.preventDefault();
                    if (validateStep(currentStep)) {
                        if (currentStep < totalSteps) {
                            showStep(currentStep + 1);
                        }
                    }
                });
            });

            prevBtns.forEach((btn) => {
                btn.addEventListener("click", (e) => {
                    e.preventDefault();
                    if (currentStep > 1) {
                        showStep(currentStep - 1);
                    }
                });
            });

            stepItems.forEach((item) => {
                item.addEventListener("click", () => {
                    const targetStep = parseInt(item.getAttribute("data-step"), 10);
                    if (targetStep < currentStep || validateStep(currentStep)) {
                        showStep(targetStep);
                    }
                });
            });

            showStep(1);
        });
    }

    // ── Animated Tech Proof Counters Controller ────────────────────────────
    function initAnimatedCounters() {
        const counterEls = document.querySelectorAll(
            ".ins-counter-val, [data-counter-target], .ins-tech-stat-val, .ins-proof-stat, .ins-metric-val"
        );
        if (!counterEls.length) return;

        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    obs.unobserve(el);

                    const originalText = (el.getAttribute("data-counter-target") || el.textContent || "").trim();
                    // Match prefix, numeric portion, and suffix
                    const match = originalText.match(/^([<>\-\+~]*)?\s*([\d\.,]+)\s*([%a-zA-Z\+\/]*)$/);
                    if (!match) return;

                    const prefix = match[1] ? match[1] + " " : "";
                    const rawNumStr = match[2].replace(/,/g, ".");
                    const suffix = match[3] || "";
                    const targetNum = parseFloat(rawNumStr);
                    if (isNaN(targetNum)) return;

                    const isDecimal = rawNumStr.includes(".");
                    const decimals = isDecimal ? (rawNumStr.split(".")[1] || "").length : 0;
                    const duration = 1800; // ms
                    const startTime = performance.now();

                    function updateFrame(now) {
                        const elapsed = now - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        // EaseOutCubic: 1 - pow(1 - x, 3)
                        const easeProgress = 1 - Math.pow(1 - progress, 3);
                        const currentVal = (targetNum * easeProgress).toFixed(decimals);

                        el.textContent = `${prefix}${currentVal}${suffix}`;

                        if (progress < 1) {
                            requestAnimationFrame(updateFrame);
                        } else {
                            el.textContent = originalText;
                        }
                    }

                    requestAnimationFrame(updateFrame);
                }
            });
        }, { threshold: 0.15 });

        counterEls.forEach(el => observer.observe(el));
    }

    initGoldMasterSuite();
    initPlatformTopology();
    initPricingConfigurator();
    initResourceFilters();
    initDemoWizard();
    initAnimatedCounters();
    initSovereignTrustCenter();
    initIndustrialSandbox();
    initFsmConsole();
    initIdpWorkbench();
    initKnowledgeGraphVisualizer();
    initHsCodeRecommender();
    initRoiEngineeringStudio();
    initDigitalTwinSimulator();
}

// =========================================================================
// CYCLE 3 INTERACTIVE SUITE INITIALIZERS
// =========================================================================

function initSovereignTrustCenter() {
    const trustSection = document.querySelector('[data-snippet="s_insilos_merkle_dossier"]') ||
                         document.querySelector('.ins-merkle-dag') ||
                         document.getElementById('ins-merkle-console');
    if (!trustSection) return;
    if (trustSection.__ins_merkle_init) return;
    trustSection.__ins_merkle_init = true;

    // Ensure the Merkle DAG ledger console card in col-lg-7 is targeted by .ins-glass-card
    // and theory cards in col-lg-5 don't shadow transaction leaves for querySelector('.vstack .p-3.border')
    document.querySelectorAll('.ins-glass-card').forEach(c => {
        if (!trustSection.contains(c)) {
            c.classList.remove('ins-glass-card');
            c.classList.add('ins-glass-panel');
        }
    });
    const theoryVstack = trustSection.querySelector('.col-lg-5 .vstack');
    if (theoryVstack) {
        theoryVstack.classList.remove('vstack');
        theoryVstack.classList.add('d-flex', 'flex-column');
    }

    // Inject interactive tamper & verify toolbar if not statically present
    const consoleCard = trustSection.querySelector('.ins-glass-card') || trustSection;
    let toolbar = trustSection.querySelector('.ins-merkle-toolbar');
    if (!toolbar && consoleCard) {
        toolbar = document.createElement('div');
        toolbar.className = 'd-flex flex-wrap align-items-center gap-2 mt-4 pt-3 border-top border-secondary border-opacity-25 ins-merkle-toolbar';
        toolbar.innerHTML = `
            <button type="button" class="btn btn-sm btn-outline-danger rounded-pill font-monospace d-inline-flex align-items-center gap-2" id="ins-btn-simulate-tamper">
                <svg class="ph-duotone ph-warning-circle ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-warning-circle"/></svg>
                <span>Giả Lập Tấn Công Sửa Đổi Dữ Liệu</span>
            </button>
            <button type="button" class="btn btn-sm btn-primary rounded-pill font-monospace d-inline-flex align-items-center gap-2" id="ins-btn-verify-merkle">
                <svg class="ph-duotone ph-shield-check ph-sm"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-shield-check"/></svg>
                <span>Xác Minh &amp; Tái Tính Toán Merkle Root</span>
            </button>
            <div id="ins-merkle-alert" class="w-100 mt-2 d-none"></div>
        `;
        const footerNote = consoleCard.querySelector('.pt-3.mt-3.border-top') || consoleCard.lastElementChild;
        if (footerNote && footerNote.parentNode === consoleCard) {
            consoleCard.insertBefore(toolbar, footerNote);
        } else {
            consoleCard.appendChild(toolbar);
        }
    }

    const tamperBtn = trustSection.querySelector('#ins-btn-simulate-tamper');
    const verifyBtn = trustSection.querySelector('#ins-btn-verify-merkle');
    const alertBox = trustSection.querySelector('#ins-merkle-alert');
    const rootContainer = trustSection.querySelector('.border-warning') || trustSection.querySelector('.ins-merkle-root');
    const rootHashEl = rootContainer ? rootContainer.querySelector('.text-white.font-monospace') : null;
    const rootStatusEl = rootContainer ? rootContainer.querySelector('.text-secondary.small.font-monospace') : null;
    const leafCards = consoleCard ? consoleCard.querySelectorAll('.vstack .p-3.border') : trustSection.querySelectorAll('.vstack .p-3.border');
    const originalRootHash = rootHashEl ? rootHashEl.textContent.trim() : '0x7A8E29BC04D791F610AC8392B740EF582D01E9B2';

    const originalLeaves = [];
    leafCards.forEach(leaf => {
        const hashEl = leaf.querySelector('.text-secondary.small.font-monospace');
        const badgeEl = leaf.querySelector('.badge');
        originalLeaves.push({
            element: leaf,
            hashText: hashEl ? hashEl.textContent : '',
            badgeText: badgeEl ? badgeEl.textContent : '',
            badgeClass: badgeEl ? badgeEl.className : ''
        });
    });

    if (tamperBtn) {
        tamperBtn.addEventListener('click', () => {
            if (leafCards.length > 0) {
                const firstLeaf = leafCards[0];
                const hashEl = firstLeaf.querySelector('.text-secondary.small.font-monospace');
                const badgeEl = firstLeaf.querySelector('.badge');
                firstLeaf.classList.add('border-danger', 'bg-danger-subtle');
                if (hashEl) {
                    hashEl.innerHTML = '<span class="text-danger fw-bold">Leaf Hash: 0xBAD00000000000... [VIOLATION: PO 537.5M &rarr; 990.0M]</span>';
                }
                if (badgeEl) {
                    badgeEl.className = 'badge bg-danger text-white small font-monospace';
                    badgeEl.textContent = 'HASH MISMATCH';
                }
            }

            if (rootContainer) {
                rootContainer.className = 'p-3 border border-danger rounded-3 bg-danger bg-opacity-10 d-inline-block w-100';
            }
            if (rootHashEl) {
                rootHashEl.innerHTML = '<span class="text-danger fw-bold">0xDEADBEEF9901442A000000000000000000000000</span>';
            }
            if (rootStatusEl) {
                rootStatusEl.innerHTML = '<span class="text-danger font-monospace fw-bold">Xác thực: 0.0012s // Trạng thái: CẢNH BÁO SỤP ĐỔ CHUỖI BĂM</span>';
            }

            if (alertBox) {
                alertBox.className = 'w-100 mt-2 p-3 bg-danger bg-opacity-25 border border-danger rounded-3 text-white font-monospace small';
                alertBox.innerHTML = '<div class="d-flex align-items-center gap-2 mb-1"><svg class="ph-duotone ph-warning ph-sm text-danger"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-warning"/></svg><strong class="text-danger">[CẢNH BÁO MẬT MÃ HỌC]</strong> Phát hiện dữ liệu chứng từ bị sửa đổi trái phép!</div><div>Cây băm Merkle DAG sụp đổ, Root Digest không khớp với Sổ cái Bất biến. Giao dịch bị đóng băng ngay lập tức.</div>';
                alertBox.classList.remove('d-none');
            }
        });
    }

    if (verifyBtn) {
        verifyBtn.addEventListener('click', () => {
            leafCards.forEach((leaf, idx) => {
                leaf.classList.remove('border-danger', 'bg-danger-subtle');
                if (originalLeaves[idx]) {
                    const hashEl = leaf.querySelector('.text-secondary.small.font-monospace');
                    const badgeEl = leaf.querySelector('.badge');
                    if (hashEl) hashEl.textContent = originalLeaves[idx].hashText;
                    if (badgeEl) {
                        badgeEl.className = originalLeaves[idx].badgeClass;
                        badgeEl.textContent = originalLeaves[idx].badgeText;
                    }
                }
            });

            if (rootContainer) {
                rootContainer.className = 'p-3 border border-warning border-opacity-50 rounded-3 bg-dark-subtle d-inline-block w-100';
            }
            if (rootHashEl) {
                rootHashEl.textContent = originalRootHash;
            }
            if (rootStatusEl) {
                rootStatusEl.textContent = 'Xác thực: 0.0034s // Trạng thái: Hợp lệ 100%';
            }

            if (alertBox) {
                alertBox.className = 'w-100 mt-2 p-3 bg-success bg-opacity-25 border border-success rounded-3 text-white font-monospace small';
                alertBox.innerHTML = '<div class="d-flex align-items-center gap-2 mb-1"><svg class="ph-duotone ph-check-circle ph-sm text-mint"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-check-circle"/></svg><strong class="text-mint">[XÁC MINH MẬT MÃ THÀNH CÔNG]</strong> Đã đối soát Zero-Knowledge Audit với 4 PoP quốc gia trong 3.4ms.</div><div>Toàn bộ 100% block đạt tính toàn vẹn bất biến SHA-256. Không có dấu hiệu can thiệp.</div>';
                alertBox.classList.remove('d-none');
            }
        });
    }

    // Telemetry micro-jitter simulation on Regional PoP pings
    const popCards = document.querySelectorAll('.s_numbers[data-snippet="s_insilos_uptime_monitor"] .col-lg-3 .text-secondary.font-monospace');
    if (popCards && popCards.length > 0) {
        const basePings = [3.8, 6.2, 4.1, 7.9];
        setInterval(() => {
            popCards.forEach((el, i) => {
                const base = basePings[i] || 4.5;
                const jitter = ((Math.random() - 0.5) * 0.4).toFixed(1);
                const ping = (base + parseFloat(jitter)).toFixed(1);
                const tier = i === 3 ? 'Edge Node' : 'Tier III';
                el.textContent = `Ping: ${ping}ms // ${tier}`;
            });
        }, 4000);
    }
}

function initIndustrialSandbox() {
    const sandboxNav = document.getElementById('ins-sandbox-tabs');
    if (!sandboxNav) return;
    if (sandboxNav.__ins_sandbox_init) return;
    sandboxNav.__ins_sandbox_init = true;

    const tabBtns = sandboxNav.querySelectorAll('button[data-bs-toggle="pill"], button[data-bs-target]');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetSelector = btn.getAttribute('data-bs-target') || btn.getAttribute('href');
            if (!targetSelector) return;
            const targetPane = document.querySelector(targetSelector);
            if (!targetPane) return;

            tabBtns.forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-selected', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-selected', 'true');

            const tabContainer = targetPane.closest('.tab-content') || document.getElementById('ins-sandbox-tab-content');
            if (tabContainer) {
                tabContainer.querySelectorAll('.tab-pane').forEach(p => {
                    p.classList.remove('show', 'active');
                });
                targetPane.classList.add('show', 'active');
            }
        });
    });

    initFsmConsole();
}

function initFsmConsole() {
    const fsmPane = document.getElementById('ins-tool-fsm');
    if (!fsmPane) return;
    if (fsmPane.__ins_fsm_init) return;
    fsmPane.__ins_fsm_init = true;

    const triggerBtn = document.getElementById('btn-sandbox-fsm-trigger');
    const ackBtn = document.getElementById('btn-sandbox-fsm-ack');

    if (triggerBtn) {
        triggerBtn.addEventListener('click', () => {
            const now = new Date();
            const timeStr = now.toTimeString().split(' ')[0];
            const randomSuffix = Math.floor(1000 + Math.random() * 9000);
            const ticketId = `#FSM-2026-EMERG-${randomSuffix}`;

            const ticketEl = document.getElementById('ins-fsm-ticket-code');
            if (ticketEl) ticketEl.textContent = ticketId;

            const statusBadge = document.getElementById('ins-fsm-ticket-status');
            if (statusBadge) {
                statusBadge.className = 'badge bg-danger text-white font-monospace small';
                statusBadge.textContent = 'DISPATCHED // KHẨN CẤP';
            }

            const etaEl = document.getElementById('ins-fsm-eta');
            if (etaEl) {
                etaEl.className = 'text-warning fw-bold';
                etaEl.textContent = '15 Phút (Đội Phản Ứng Nhanh Đã Xuất Phát)';
            }

            const devEl = document.getElementById('ins-fsm-target-device');
            if (devEl) {
                devEl.textContent = 'Trumpf TruLaser 5030 (12kW) — BÁO ĐỘNG RUNG TRỤC';
            }

            const btnSpan = triggerBtn.querySelector('span');
            if (btnSpan) btnSpan.textContent = '✓ Đã Kích Hoạt Phiếu Khẩn Cấp';

            const feedback = document.getElementById('ins-fsm-live-feedback');
            if (feedback) {
                feedback.classList.remove('d-none');
                feedback.className = 'mb-3 p-2 rounded-2 border border-warning bg-warning bg-opacity-10 font-monospace small';
                feedback.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center text-warning">
                        <span><span class="ins-live-ping me-1"/> ĐÃ PHÁT LỆNH ĐIỀU ĐỘ KHẨN CẤP LÚC ${timeStr}</span>
                        <span class="badge bg-warning text-black font-monospace">${ticketId}</span>
                    </div>
                `;
            }
        });
    }

    if (ackBtn) {
        ackBtn.addEventListener('click', () => {
            const now = new Date();
            const timeStr = now.toTimeString().split(' ')[0];

            const statusBadge = document.getElementById('ins-fsm-ticket-status');
            if (statusBadge) {
                statusBadge.className = 'badge bg-mint text-black font-monospace small';
                statusBadge.textContent = 'ACKNOWLEDGED // ĐÃ TIẾP NHẬN';
            }

            const techEl = document.getElementById('ins-fsm-technician');
            if (techEl) {
                techEl.className = 'text-mint fw-bold';
                techEl.textContent = 'Kỹ Sư Trưởng Nguyễn Văn An (ISO Cat III) — ĐÃ NHẬN LỆNH';
            }

            const etaEl = document.getElementById('ins-fsm-eta');
            if (etaEl) {
                etaEl.className = 'text-mint fw-bold';
                etaEl.textContent = '12 Phút (Đang Di Chuyển Đến Xưởng Cơ Khí #2)';
            }

            const btnSpan = ackBtn.querySelector('span');
            if (btnSpan) btnSpan.textContent = '✓ Đã Tiếp Nhận & Đang Di Chuyển';
            ackBtn.classList.remove('btn-primary');
            ackBtn.classList.add('btn-outline-secondary');

            const feedback = document.getElementById('ins-fsm-live-feedback');
            if (feedback) {
                feedback.classList.remove('d-none');
                feedback.className = 'mb-3 p-2 rounded-2 border border-mint bg-mint bg-opacity-10 font-monospace small';
                feedback.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center text-mint">
                        <span><svg class="ph-duotone ph-check-circle ph-sm me-1"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-check-circle"/></svg>KỸ THUẬT VIÊN ĐÃ XÁC NHẬN NHẬN LỆNH LÚC ${timeStr}</span>
                        <span class="badge bg-mint text-black font-monospace">ETA: 12 PHÚT</span>
                    </div>
                `;
            }
        });
    }
}

function initIdpWorkbench() {
    const idpPane = document.getElementById('ins-tool-idp');
    if (!idpPane) return;
    if (idpPane.__ins_idp_init) return;
    idpPane.__ins_idp_init = true;

    const docData = {
        hq01: {
            title: "TỜ KHAI HẢI QUAN ĐIỆN TỬ (NHẬP KHẨU)",
            sub: "MẪU SỐ: HQ-01/NK/2026 · VNACCS/VCIS",
            boxes: [
                { field: "declaration_no", label: "01. Số tờ khai hải quan:", value: "105829104820/NK", conf: "STP 99.9%", border: "border-warning", bg: "bg-warning", sub: "" },
                { field: "importer", label: "02. Người nhập khẩu:", value: "TẬP ĐOÀN THÉP CÔNG NGHIỆP DUNG QUẤT", conf: "STP 99.8%", border: "border-info", bg: "bg-info", sub: "MST: 0100779774-001 · KCN Dung Quất, Quảng Ngãi" },
                { field: "hs_code", label: "03. Mã HS & Tên hàng hóa:", value: "7208.38.00 — THÉP TẤM CÁN NÓNG HỢP KIM SS400", conf: "STP 99.7%", border: "border-success", bg: "bg-success", sub: "Số lượng: 25.000 KG · Xuất xứ: VN · Đơn giá: 21.500 ₫/kg" },
                { field: "tax_value", label: "04. Trị giá tính thuế & Tiền thuế:", value: "537.500.000 VNĐ · Thuế GTGT 8%: 43.000.000 VNĐ", conf: "STP 99.9%", border: "border-warning", bg: "bg-warning", sub: "Phân luồng kiểm tra: LUỒNG XANH (THÔNG QUAN TỰ ĐỘNG)" }
            ],
            table: [
                { key: "declaration_no", val: "105829104820/NK", conf: "99.9%", highlight: false },
                { key: "importer_name", val: "STEEL_CORP_SS400", conf: "99.8%", highlight: false },
                { key: "importer_vat", val: "0100779774-001", conf: "100.0%", highlight: false },
                { key: "hs_code", val: "7208.38.00", conf: "99.7%", highlight: true, color: "text-cyan" },
                { key: "net_weight_kg", val: "25,000.00", conf: "99.8%", highlight: false },
                { key: "cif_amount_vnd", val: "537,500,000", conf: "99.9%", highlight: true, color: "text-mint" },
                { key: "customs_status", val: "CLEARED_GREEN_CHANNEL", conf: "99.9%", highlight: true, color: "text-mint" }
            ],
            json: {
                model: "customs.declaration",
                declaration_no: "105829104820/NK",
                hs_code: "7208.38.00",
                cif_amount: 537500000,
                currency: "VND",
                merkle_digest: "0x8fa37c19a02d",
                stp_status: true
            }
        },
        invoice: {
            title: "COMMERCIAL INVOICE // TÀI CHÍNH QUỐC TẾ",
            sub: "INVOICE NO: INV-2026-EU-0891 · CIP SEAPORT TERMINAL",
            boxes: [
                { field: "declaration_no", label: "01. Số hóa đơn thương mại:", value: "INV-2026-EU-0891", conf: "STP 99.9%", border: "border-warning", bg: "bg-warning", sub: "Ngày phát hành: 18/09/2026 · Currency: EUR" },
                { field: "importer", label: "02. Người thụ hưởng & Người mua:", value: "TRUMPF WERKZEUGMASCHINEN SE / INSILOS CORP", conf: "STP 99.8%", border: "border-info", bg: "bg-info", sub: "Ditzingen, Germany &rarr; TP. Hồ Chí Minh, Vietnam" },
                { field: "hs_code", label: "03. Mô tả thiết bị công nghiệp:", value: "8456.11.00 — MÁY CẮT LASER TRUTOPIC 12KW", conf: "STP 99.8%", border: "border-success", bg: "bg-success", sub: "Serial: TRU-5030-2026 · Công suất nguồn quang 12kW" },
                { field: "tax_value", label: "04. Tổng giá trị thương mại:", value: "EUR 385,000.00 (Tương đương 10.45 Tỷ VNĐ)", conf: "STP 100.0%", border: "border-warning", bg: "bg-warning", sub: "Điều kiện Incoterms: CIP Cảng Biển Quốc Tế · Thanh toán L/C" }
            ],
            table: [
                { key: "invoice_number", val: "INV-2026-EU-0891", conf: "99.9%", highlight: false },
                { key: "seller_name", val: "TRUMPF_SE_GERMANY", conf: "99.8%", highlight: false },
                { key: "buyer_name", val: "INSILOS_VIETNAM_CORP", conf: "99.8%", highlight: false },
                { key: "hs_code", val: "8456.11.00", conf: "99.8%", highlight: true, color: "text-cyan" },
                { key: "invoice_currency", val: "EUR", conf: "100.0%", highlight: false },
                { key: "total_amount", val: "385,000.00", conf: "100.0%", highlight: true, color: "text-mint" },
                { key: "payment_terms", val: "LC_AT_SIGHT_CONFIRMED", conf: "99.9%", highlight: true, color: "text-mint" }
            ],
            json: {
                model: "account.move",
                move_type: "in_invoice",
                invoice_number: "INV-2026-EU-0891",
                partner_id: "TRUMPF_SE_GERMANY",
                hs_code: "8456.11.00",
                total_amount_eur: 385000.00,
                merkle_digest: "0x4e29b1178c02",
                stp_status: true
            }
        },
        coa: {
            title: "CERTIFICATE OF ANALYSIS (COA) // KIỂM NGHIỆM DƯỢC",
            sub: "WHO-GMP SPECIFICATION · LOT-2026-VAX42",
            boxes: [
                { field: "declaration_no", label: "01. Số kiểm nghiệm & Mã lô:", value: "LOT: VAX-LFP-80V-BATCH42", conf: "STP 99.9%", border: "border-warning", bg: "bg-warning", sub: "Ngày thử nghiệm: 22/09/2026 · Tiêu chuẩn Dược điển VN V" },
                { field: "importer", label: "02. Đơn vị sản xuất / Viện kiểm nghiệm:", value: "VIỆN CÔNG NGHỆ SINH HỌC & DƯỢC PHẨM", conf: "STP 99.8%", border: "border-info", bg: "bg-info", sub: "Phòng kiểm nghiệm đạt chuẩn ISO/IEC 17025:2017" },
                { field: "hs_code", label: "03. Hoạt chất & Hàm lượng:", value: "3002.41.00 — VẮC-XIN TINH KHIẾT LIỀU CAO", conf: "STP 99.9%", border: "border-success", bg: "bg-success", sub: "Chỉ số độ tinh khiết: 99.85% HPLC · Tạp chất liên quan < 0.1%" },
                { field: "tax_value", label: "04. Kết luận kiểm nghiệm:", value: "ĐẠT TIÊU CHUẨN XUẤT XƯỞNG WHO-GMP", conf: "STP 100.0%", border: "border-warning", bg: "bg-warning", sub: "Nội độc tố vi khuẩn: < 0.05 EU/ml (Ngưỡng an toàn < 0.5 EU/ml)" }
            ],
            table: [
                { key: "batch_lot_no", val: "VAX-LFP-80V-BATCH42", conf: "99.9%", highlight: false },
                { key: "test_method", val: "HPLC_CHROMATOGRAPHY", conf: "99.8%", highlight: false },
                { key: "purity_percent", val: "99.85%", conf: "99.9%", highlight: true, color: "text-mint" },
                { key: "hs_code", val: "3002.41.00", conf: "99.9%", highlight: true, color: "text-cyan" },
                { key: "endotoxin_level", val: "<0.05 EU/ml", conf: "99.8%", highlight: false },
                { key: "release_status", val: "WHO_GMP_APPROVED", conf: "100.0%", highlight: true, color: "text-mint" },
                { key: "ebr_electronic_sign", val: "SHA256_VALIDATED", conf: "100.0%", highlight: true, color: "text-mint" }
            ],
            json: {
                model: "quality.check",
                lot_name: "VAX-LFP-80V-BATCH42",
                standard: "WHO-GMP / Dược điển V",
                purity_rate: 0.9985,
                hs_code: "3002.41.00",
                qa_decision: "pass",
                merkle_digest: "0x117a09c2e4f8",
                stp_status: true
            }
        },
        tt78: {
            title: "HÓA ĐƠN GIÁ TRỊ GIA TĂNG ĐIỆN TỬ // THÔNG TƯ 78",
            sub: "MẪU 1/001 · KÝ HIỆU: C26TAA · SỐ HÓA ĐƠN: 00048291",
            boxes: [
                { field: "declaration_no", label: "01. Số hóa đơn & Mã CQT:", value: "HĐ: 00048291 · MÃ CQT: TCT-2026-9912048", conf: "STP 100.0%", border: "border-warning", bg: "bg-warning", sub: "Ngày ký số: 25/09/2026 · Hợp lệ theo Thông tư 78/2021/TT-BTC" },
                { field: "importer", label: "02. Đơn vị phát hành:", value: "TỔNG CÔNG TY TIẾP VẬN CẢNG BIỂN QUỐC TẾ", conf: "STP 99.8%", border: "border-info", bg: "bg-info", sub: "MST: 0300446975 · Cụm Cảng Biển Quốc Tế, TP. Thủ Đức" },
                { field: "hs_code", label: "03. Nội dung dịch vụ logistics:", value: "DỊCH VỤ NÂNG HẠ CONTAINER & LƯU BÃI CẢNG BIỂN", conf: "STP 99.8%", border: "border-success", bg: "bg-success", sub: "Vận đơn số: PORT_BL_8912 · Đoàn xe vận tải: 51C-982.45" },
                { field: "tax_value", label: "04. Tổng tiền thanh toán & Thuế GTGT:", value: "18.675.000.000 VNĐ · THUẾ GTGT: 1.494.000.000 VNĐ", conf: "STP 100.0%", border: "border-warning", bg: "bg-warning", sub: "Trạng thái CQT: ĐÃ CẤP MÃ HỢP LỆ (KHÔNG SAI LỆCH)" }
            ],
            table: [
                { key: "invoice_number", val: "00048291_C26TAA", conf: "100.0%", highlight: false },
                { key: "tax_authority_code", val: "TCT-2026-9912048", conf: "100.0%", highlight: true, color: "text-mint" },
                { key: "seller_vat", val: "0300446975", conf: "100.0%", highlight: false },
                { key: "service_desc", val: "PORT_DRAYAGE_TERMINAL", conf: "99.8%", highlight: false },
                { key: "pre_tax_amount", val: "18,675,000,000", conf: "100.0%", highlight: true, color: "text-mint" },
                { key: "vat_amount_8pct", val: "1,494,000,000", conf: "100.0%", highlight: false },
                { key: "circular_compliance", val: "TT78_TT200_VALIDATED", conf: "100.0%", highlight: true, color: "text-mint" }
            ],
            json: {
                model: "account.move",
                move_type: "out_invoice",
                invoice_number: "00048291",
                cqt_code: "TCT-2026-9912048",
                seller_tax_id: "0300446975",
                total_vnd: 20169000000,
                merkle_digest: "0x32da90812fe4",
                stp_status: true
            }
        },
        bl_maersk: {
            title: "VẬN ĐƠN ĐƯỜNG BIỂN QUỐC TẾ // BILL OF LADING",
            sub: "B/L NO: PORT_BL_8912 · MAERSK LINE OCEAN FREIGHT",
            boxes: [
                { field: "declaration_no", label: "01. Số Vận Đơn & Hãng Tàu:", value: "B/L: PORT_BL_8912 · MAERSK LINE", conf: "STP 100.0%", border: "border-warning", bg: "bg-warning", sub: "Vessel: MAERSK MC-KINNEY MOLLER · Voyage: 2609W" },
                { field: "importer", label: "02. Số Container & Số Chì (Seal):", value: "CONTAINER: MSKU9012384 · SEAL: ML-VN2026", conf: "STP 99.9%", border: "border-info", bg: "bg-info", sub: "Loại Cont: 40' High Cube Dry · Tình trạng: FCL/FCL" },
                { field: "hs_code", label: "03. Cảng Xếp Hàng & Cảng Dỡ Hàng:", value: "POL: Cát Lái VNCLI &rarr; POD: Rotterdam NLRTM", conf: "STP 99.8%", border: "border-success", bg: "bg-success", sub: "Thời gian rời bến: 28/09/2026 · Phương thức: CY-CY" },
                { field: "tax_value", label: "04. Trọng Lượng & Điều Kiện Cước:", value: "24,850 KG (GROSS WEIGHT) · FREIGHT PREPAID", conf: "STP 99.9%", border: "border-warning", bg: "bg-warning", sub: "Mô tả: THIẾT BỊ CƠ KHÍ & XE KÉO ĐIỆN V-LIFT 2500E (4 CỤM)" }
            ],
            table: [
                { key: "bl_number", val: "PORT_BL_8912", conf: "100.0%", highlight: false },
                { key: "carrier_name", val: "MAERSK_LINE_A/S", conf: "99.9%", highlight: false },
                { key: "vessel_name", val: "MAERSK MC-KINNEY MOLLER", conf: "99.8%", highlight: true, color: "text-cyan" },
                { key: "container_number", val: "MSKU9012384", conf: "99.9%", highlight: true, color: "text-mint" },
                { key: "seal_number", val: "ML-VN2026", conf: "100.0%", highlight: false },
                { key: "gross_weight", val: "24,850 kg", conf: "99.9%", highlight: true, color: "text-mint" },
                { key: "port_of_loading", val: "Cát Lái VNCLI", conf: "99.8%", highlight: false },
                { key: "port_of_discharge", val: "Rotterdam NLRTM", conf: "99.8%", highlight: false },
                { key: "freight_payment", val: "Freight Prepaid", conf: "100.0%", highlight: true, color: "text-mint" }
            ],
            json: {
                model: "stock.picking",
                bl_number: "PORT_BL_8912",
                carrier: "MAERSK_LINE",
                vessel_name: "MAERSK MC-KINNEY MOLLER",
                container_number: "MSKU9012384",
                seal_number: "ML-VN2026",
                gross_weight_kg: 24850,
                port_of_loading: "Cát Lái VNCLI",
                port_of_discharge: "Rotterdam NLRTM",
                freight_terms: "Freight Prepaid",
                merkle_digest: "0x9c417e882b01",
                stp_status: true
            }
        }
    };

    function renderDoc(docKey) {
        const data = docData[docKey] || docData.hq01;
        const docPane = idpPane.querySelector('.ins-idp-document-pane');
        if (docPane) {
            let boxesHtml = `
                <div class="text-center mb-3 border-bottom border-secondary border-opacity-25 pb-2">
                    <div class="text-secondary small font-monospace">${data.sub}</div>
                    <h5 class="text-white fw-bold mb-0 font-monospace">${data.title}</h5>
                </div>
            `;
            data.boxes.forEach((b, i) => {
                boxesHtml += `
                    <div class="ins-idp-bounding-box ${i === 0 ? 'active' : ''} p-2 rounded-2 mb-2 border ${b.border} ${b.bg} bg-opacity-10 position-relative" data-field="${b.field}">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-secondary small font-monospace">${b.label}</span>
                            <span class="badge bg-secondary bg-opacity-50 text-mint font-monospace small">${b.conf}</span>
                        </div>
                        <div class="text-white fw-bold font-monospace">${b.value}</div>
                        ${b.sub ? `<div class="text-secondary small font-monospace">${b.sub}</div>` : ''}
                    </div>
                `;
            });
            docPane.innerHTML = boxesHtml;
        }

        const tbody = idpPane.querySelector('table tbody');
        if (tbody) {
            tbody.innerHTML = data.table.map(row => `
                <tr data-row-key="${row.key}">
                    <td class="text-secondary">${row.key}</td>
                    <td class="text-white fw-bold ${row.color || ''}">${row.val}</td>
                    <td class="text-mint text-end">${row.conf}</td>
                </tr>
            `).join('');
        }

        const jsonBlock = idpPane.querySelector('.overflow-auto');
        if (jsonBlock) {
            const formattedJson = JSON.stringify(data.json, null, 2);
            jsonBlock.innerHTML = `
                <div class="text-secondary small mb-1">// ERP REST API PAYLOAD (Odoo 20 Model: ${data.json.model})</div>
                <pre class="text-mint mb-0 font-monospace small">${formattedJson}</pre>
            `;
        }

        bindHoverInteractions();
    }

    function bindHoverInteractions() {
        const boxes = idpPane.querySelectorAll('.ins-idp-bounding-box');
        const rows = idpPane.querySelectorAll('table tbody tr');

        boxes.forEach(box => {
            box.addEventListener('mouseenter', () => {
                boxes.forEach(b => b.classList.remove('active'));
                box.classList.add('active');
            });
        });

        rows.forEach(row => {
            row.addEventListener('mouseenter', () => {
                row.classList.add('table-active');
            });
            row.addEventListener('mouseleave', () => {
                row.classList.remove('table-active');
            });
        });
    }

    const selectors = idpPane.querySelectorAll('.ins-idp-doc-selector');
    selectors.forEach(btn => {
        btn.addEventListener('click', () => {
            selectors.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const target = btn.getAttribute('data-doc-target') || 'hq01';
            renderDoc(target);
        });
    });

    const exportBtn = idpPane.querySelector('button.btn-primary');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            const activeSel = idpPane.querySelector('.ins-idp-doc-selector.active');
            const docKey = activeSel ? activeSel.getAttribute('data-doc-target') : 'hq01';
            const data = docData[docKey] || docData.hq01;
            const jsonText = JSON.stringify(data.json, null, 2);

            const labelSpan = exportBtn.querySelector('span');
            if (labelSpan) labelSpan.textContent = 'Đã Sao Chép JSON!';

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(jsonText).catch(() => {});
            }
            setTimeout(() => {
                if (labelSpan) labelSpan.textContent = 'Xuất JSON / ERP Payload';
            }, 6000);
        });
    }

    const pushBtn = document.getElementById('btn-sandbox-idp-push');
    if (pushBtn) {
        pushBtn.addEventListener('click', () => {
            const activeSel = idpPane.querySelector('.ins-idp-doc-selector.active');
            const docKey = activeSel ? activeSel.getAttribute('data-doc-target') : 'hq01';
            const data = docData[docKey] || docData.hq01;
            const txHash = '0x' + Array.from({length: 24}, () => Math.floor(Math.random()*16).toString(16)).join('');
            const recordId = Math.floor(10000 + Math.random() * 90000);

            const pushSpan = pushBtn.querySelector('span');
            if (pushSpan) pushSpan.textContent = `✓ Đã Đẩy Vào Odoo 20 (ID: #${recordId})`;

            const toast = document.getElementById('ins-idp-sync-toast');
            if (toast) {
                toast.classList.remove('d-none');
                toast.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center text-mint">
                        <span><span class="ins-live-ping ins-live-ping--emerald me-1"/> ODOO 20 LIVE SYNC // STATUS 200 OK</span>
                        <span class="badge bg-mint text-black font-monospace">RECORD #${recordId}</span>
                    </div>
                    <div class="text-secondary small mt-1 font-monospace">
                        TX HASH: <span class="text-white">${txHash}</span> · MODEL: <span class="text-cyan">${data.json.model}</span> · MERKLE: <span class="text-warning">${data.json.merkle_digest || '0x8fa37c19a02d'}</span>
                    </div>
                `;
            }
        });
    }

    renderDoc('hq01');
}

function initKnowledgeGraphVisualizer() {
    const kgPane = document.getElementById('ins-tool-kg');
    if (!kgPane) return;
    if (kgPane.__ins_kg_init) return;
    kgPane.__ins_kg_init = true;

    const entityData = {
        supplier: {
            title: "THÉP CÔNG NGHIỆP DUNG QUẤT",
            type: "IndustrialSupplierCorp",
            props: [
                { label: "Mã PO Mua Hàng:", val: "#VN-PO2026-001", color: "text-white" },
                { label: "Nhà Cung Cấp:", val: "Tập Đoàn Thép Công Nghiệp Dung Quất", color: "text-white" },
                { label: "Trọng Lượng Nhập:", val: "25,000 KG (Thép Cuộn Cán Nóng)", color: "text-white" },
                { label: "Lệnh Sản Xuất:", val: "WH/MO/00010 (TruLaser 12kW)", color: "text-cyan" },
                { label: "Hợp Đồng Đầu Ra:", val: "#VN-SO2026-001 (Tiếp Vận Cảng Biển)", color: "text-mint" },
                { label: "Chứng Từ Cảng:", val: "PORT-SEAPORT-BL8912", color: "text-white" }
            ]
        },
        lot: {
            title: "SS400-LOT902",
            type: "IndustrialMaterialLot",
            props: [
                { label: "Mã Lô Vật Tư:", val: "LOT-HP-SS400-2026-01", color: "text-white" },
                { label: "Quy Cách Kỹ Thuật:", val: "Thép Tấm SS400 Chiều Dày 12mm", color: "text-white" },
                { label: "Thử Nghiệm Cơ Tính:", val: "Yield 420 MPa // Tensile 510 MPa", color: "text-mint" },
                { label: "Định Mức Cấp Phát:", val: "BOM Level 2: Chassis V-LIFT", color: "text-cyan" },
                { label: "Vị Trí Lưu Kho:", val: "Kho Thép Tấm Phân Xưởng Cơ Khí #2", color: "text-white" },
                { label: "Mã Băm Merkle:", val: "0x77C8302198DF12", color: "text-warning" }
            ]
        },
        machine: {
            title: "TRUMPF TRULASER 5030",
            type: "WorkcenterMachineCNC",
            props: [
                { label: "Mã Trạm Máy MES:", val: "MC-CNC-LASER-12KW", color: "text-white" },
                { label: "Công Suất Nguồn:", val: "12,000W Fiber Optic Resonator", color: "text-white" },
                { label: "Hiệu Suất OEE:", val: "92.5% (Vận Hành 3 Ca Liên Tục)", color: "text-mint" },
                { label: "Lệnh Đang Chạy:", val: "WH/MO/00010 — Cắt Tấm Khung Xe", color: "text-cyan" },
                { label: "Cảm Biến IoT:", val: "ISO-Vibe 1.8 mm/s · Temp 52°C", color: "text-mint" },
                { label: "Lịch Bảo Trì Gần Nhất:", val: "Đạt 4,200 giờ · Lịch FSM T11/2026", color: "text-white" }
            ]
        },
        product: {
            title: "V-LIFT 2500E",
            type: "FinishedIndustrialProduct",
            props: [
                { label: "Dòng Sản Phẩm:", val: "Xe Kéo Điện Nhà Xưởng 2.5 Tấn", color: "text-white" },
                { label: "Hệ Thống Pin:", val: "LFP Lithium Iron Phosphate 80V 400Ah", color: "text-cyan" },
                { label: "Động Cơ Truyền Động:", val: "Động Cơ Điện Xoay Chiều AC 75kW", color: "text-white" },
                { label: "Nghiệm Thu Xuất Xưởng:", val: "100% Đạt Chuẩn KCS & An Toàn", color: "text-mint" },
                { label: "Đơn Đặt Hàng B2B:", val: "PO Tiếp Vận Cảng-PO-2026-89", color: "text-white" },
                { label: "Chứng Nhận Xuất Xứ:", val: "C/O Form D Hợp Lệ (RVC 52%)", color: "text-mint" }
            ]
        },
        order: {
            title: "PORT-CONTRACT-18.6B",
            type: "EnterpriseCommercialContract",
            props: [
                { label: "Số Hợp Đồng B2B:", val: "#VN-SO2026-001 / PORT-LOGISTICS", color: "text-white" },
                { label: "Khách Hàng Mục Tiêu:", val: "Tổng Công Ty Tiếp Vận Cảng Biển Quốc Tế", color: "text-white" },
                { label: "Trị Giá Gói Thầu:", val: "18.675 Tỷ VNĐ", color: "text-mint" },
                { label: "Quy Mô Cung Cấp:", val: "08 Xe V-LIFT 2500E + Trạm Sạc Nhanh", color: "text-cyan" },
                { label: "Hóa Đơn TT78:", val: "00048291 · Ký Hiệu C26TAA", color: "text-white" },
                { label: "Trạng Thái Giao Hàng:", val: "Đang Bốc Dỡ Tại Cụm Cảng Biển Quốc Tế", color: "text-mint" }
            ]
        },
        bol: {
            title: "PORT-SEAPORT-BL8912",
            type: "SeaportBillOfLading",
            props: [
                { label: "Số Vận Đơn Hải Cảng:", val: "PORT_BL_8912", color: "text-white" },
                { label: "Cảng Đích & Cổng Bãi:", val: "Cụm Cảng Biển Quốc Tế · Gate 2", color: "text-white" },
                { label: "Đoàn Xe Vận Tải:", val: "Xe Đầu Kéo 51C-982.45 (GPS Online)", color: "text-cyan" },
                { label: "Tình Trạng Lưu Bãi:", val: "Giải Phóng Bãi Trong 4.2 Giờ (0 DET/DEM)", color: "text-mint" },
                { label: "Đơn Vị Tiếp Nhận:", val: "Xí Nghiệp Cơ Giới Cảng Biển Quốc Tế", color: "text-white" },
                { label: "Đối Soát Merkle Ledger:", val: "Block #2026-0928 · Đã Khớp CQT", color: "text-mint" }
            ]
        }
    };

    const nodes = kgPane.querySelectorAll('.ins-kg-node');
    const titleEl = document.getElementById('ins-kg-entity-title');
    const inspectorCard = kgPane.querySelector('.ins-kg-inspector-card');
    const badgeEl = inspectorCard ? inspectorCard.querySelector('.badge.bg-white-10') : null;
    const propsContainer = inspectorCard ? inspectorCard.querySelector('.font-monospace.small.mb-3') : null;

    if (titleEl) {
        titleEl.style.contain = 'layout paint';
        titleEl.style.whiteSpace = 'nowrap';
        titleEl.style.minHeight = '1.5rem';
    }

    // Cache node element mapping and active node pointer for fast O(1) state transitions
    const nodeMap = new Map();
    nodes.forEach(n => {
        const key = n.getAttribute('data-node');
        if (key) nodeMap.set(key, n);
    });
    let activeNodeEl = null;

    // Pre-create and cache DOM row references in propsContainer to avoid innerHTML thrashing & reflows
    const propRows = [];
    if (propsContainer) {
        propsContainer.innerHTML = '';
        for (let i = 0; i < 6; i++) {
            const row = document.createElement('div');
            row.className = `d-flex justify-content-between py-1 ${i < 5 ? 'border-bottom border-secondary border-opacity-25' : ''}`;
            const labelSpan = document.createElement('span');
            labelSpan.className = 'text-secondary';
            const valSpan = document.createElement('span');
            valSpan.className = 'fw-bold';
            row.appendChild(labelSpan);
            row.appendChild(valSpan);
            propsContainer.appendChild(row);
            propRows.push({ row, labelSpan, valSpan });
        }
    }

    const canvasContainer = kgPane.querySelector('.ins-kg-canvas-container');
    if (canvasContainer) {
        canvasContainer.style.contain = 'layout paint';
    }

    function selectNode(nodeKey) {
        const data = entityData[nodeKey] || entityData.lot;

        // Toggle active class only on changed nodes (previous and target)
        const targetNodeEl = nodeMap.get(nodeKey) || (nodes.length ? nodes[0] : null);
        if (activeNodeEl && activeNodeEl !== targetNodeEl) {
            activeNodeEl.classList.remove('ins-kg-node--active');
        }
        if (targetNodeEl) {
            targetNodeEl.classList.add('ins-kg-node--active');
            activeNodeEl = targetNodeEl;
        }

        if (titleEl && titleEl.textContent !== data.title) {
            titleEl.textContent = data.title;
        }

        if (inspectorCard) {
            const typeStr = `Type: ${data.type}`;
            if (badgeEl && badgeEl.textContent !== typeStr) {
                badgeEl.textContent = typeStr;
            }

            if (propRows.length > 0 && data.props) {
                const props = data.props;
                const len = propRows.length;
                for (let i = 0; i < len; i++) {
                    const item = propRows[i];
                    if (i < props.length) {
                        const p = props[i];
                        if (item.labelSpan.textContent !== p.label) {
                            item.labelSpan.textContent = p.label;
                        }
                        if (item.valSpan.textContent !== p.val) {
                            item.valSpan.textContent = p.val;
                        }
                        const cls = `${p.color} fw-bold`;
                        if (item.valSpan.className !== cls) {
                            item.valSpan.className = cls;
                        }
                    }
                }
            }
        }
    }

    nodes.forEach(n => {
        n.style.cursor = 'pointer';
        n.addEventListener('click', (e) => {
            if (e && e.stopPropagation) e.stopPropagation();
            const nodeKey = n.getAttribute('data-node');
            selectNode(nodeKey);
        });
    });

    const presetBtns = kgPane.querySelectorAll('.ins-kg-preset-btn');
    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            presetBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const q = btn.getAttribute('data-kg-query');
            if (q === 'supplier_lot') selectNode('supplier');
            else if (q === 'mrp_vlift') selectNode('machine');
            else if (q === 'port_bl') selectNode('order');
        });
    });

    selectNode('lot');
}

function initHsCodeRecommender() {
    const hsPane = document.getElementById('ins-tool-hscode');
    if (!hsPane) return;
    if (hsPane.__ins_hscode_init) return;
    hsPane.__ins_hscode_init = true;

    const input = document.getElementById('ins-hscode-search-input');
    const chips = hsPane.querySelectorAll('.ins-hscode-chip');
    const rows = hsPane.querySelectorAll('table tbody tr');

    function filterTable(query) {
        const q = (query || '').toLowerCase().trim();
        const tokens = q.split(/\s+/).filter(t => t.length > 0);
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const isMatch = !q || text.includes(q) || (tokens.length > 1 && tokens.every(tok => text.includes(tok)));
            row.style.display = isMatch ? '' : 'none';
            if (isMatch && q) {
                row.classList.add('table-primary');
            } else {
                row.classList.remove('table-primary');
            }
        });
    }

    if (input) {
        input.addEventListener('input', (e) => {
            filterTable(e.target.value);
            chips.forEach(chip => chip.classList.remove('active'));
        });
    }

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            const query = chip.getAttribute('data-hscode-query') || chip.textContent;
            if (input) input.value = query;
            filterTable(query);
        });
    });
}

function initRoiEngineeringStudio() {
    const studio = document.getElementById('insilos_value_engineering_section');
    if (!studio) return;
    if (studio.__ins_roi_init) return;
    studio.__ins_roi_init = true;

    const industryPresets = {
        manufacturing: {
            name: "Sản Xuất Chế Tạo & Cơ Khí",
            c0_vnd: 2.40,
            param1: { label: "Sản lượng gia công hàng tháng:", min: 100, max: 2000, step: 50, val: 500, unit: "Tấn", factor: 0.0035 },
            param2: { label: "Tỷ lệ hao hụt phế liệu BOM hiện tại:", min: 1, max: 10, step: 0.1, val: 4.8, unit: "%", factor: 0.45 },
            param3: { label: "Hiệu suất thiết bị tổng thể OEE hiện tại:", min: 50, max: 90, step: 0.5, val: 68.0, unit: "%", factor: 0.08 },
            param4: { label: "Giờ công nhập liệu thủ công hàng tháng:", min: 100, max: 2000, step: 20, val: 640, unit: "Giờ", factor: 0.0006 }
        },
        logistics: {
            name: "Logistics & Khai Thác Cảng Biển",
            c0_vnd: 2.80,
            param1: { label: "Quy mô đội xe đầu kéo container:", min: 50, max: 1000, step: 10, val: 180, unit: "Xe", factor: 0.012 },
            param2: { label: "Tỷ lệ chi phí lưu bãi container DET/DEM:", min: 1, max: 15, step: 0.2, val: 6.2, unit: "%", factor: 0.35 },
            param3: { label: "Hệ số vòng quay đội xe (Turns/Month):", min: 5, max: 40, step: 1, val: 18, unit: "Vòng", factor: 0.14 },
            param4: { label: "Giờ công lập chứng từ điều độ vận tải:", min: 200, max: 3000, step: 50, val: 820, unit: "Giờ", factor: 0.0007 }
        },
        energy: {
            name: "Năng Lượng & Lưới Điện Thông Minh",
            c0_vnd: 3.50,
            param1: { label: "Công suất trạm truyền tải điện năng:", min: 50, max: 1000, step: 25, val: 320, unit: "MWh", factor: 0.0085 },
            param2: { label: "Tỷ lệ tổn thất điện năng đường dây:", min: 0.5, max: 8, step: 0.1, val: 3.4, unit: "%", factor: 0.55 },
            param3: { label: "Độ tin cậy vận hành lưới (SAIFI/SAIDI):", min: 70, max: 99, step: 0.5, val: 88.5, unit: "%", factor: 0.09 },
            param4: { label: "Giờ tuần tra kiểm tra trạm biến áp:", min: 100, max: 1500, step: 20, val: 450, unit: "Giờ", factor: 0.0008 }
        },
        pharma: {
            name: "Dược Phẩm Sinh Học WHO-GMP",
            c0_vnd: 3.20,
            param1: { label: "Sản lượng mẻ vắc-xin WHO-GMP:", min: 10, max: 200, step: 5, val: 45, unit: "Mẻ", factor: 0.075 },
            param2: { label: "Tỷ lệ mẻ lỗi sai lệch quy trình:", min: 0.2, max: 5, step: 0.1, val: 2.1, unit: "%", factor: 0.95 },
            param3: { label: "Tuân thủ hồ sơ lô điện tử (eBR):", min: 60, max: 95, step: 0.5, val: 76.0, unit: "%", factor: 0.07 },
            param4: { label: "Giờ công thẩm định kiểm nghiệm COA:", min: 300, max: 2500, step: 20, val: 960, unit: "Giờ", factor: 0.0006 }
        }
    };

    let currentIndustry = "manufacturing";
    let isVnd = true;
    const FX_USD = 25450;

    const slVolume = document.getElementById('ins-param-volume');
    const slWaste = document.getElementById('ins-param-waste');
    const slOee = document.getElementById('ins-param-oee');
    const slLabor = document.getElementById('ins-param-labor');

    const lblVolume = document.getElementById('ins-lbl-param-volume');
    const lblWaste = document.getElementById('ins-lbl-param-waste');
    const lblOee = document.getElementById('ins-lbl-param-oee');
    const lblLabor = document.getElementById('ins-lbl-param-labor');

    const valVolume = document.getElementById('ins-val-param-volume');
    const valWaste = document.getElementById('ins-val-param-waste');
    const valOee = document.getElementById('ins-val-param-oee');
    const valLabor = document.getElementById('ins-val-param-labor');

    const outNpv = document.getElementById('ins-fin-npv');
    const outIrr = document.getElementById('ins-fin-irr');
    const outPayback = document.getElementById('ins-fin-payback');
    const outRoi = document.getElementById('ins-fin-roi');

    function calculateIRR(c0, s1, s2, s3) {
        let r = 0.5;
        for (let iter = 0; iter < 40; iter++) {
            const npv = -c0 + s1 / (1 + r) + s2 / Math.pow(1 + r, 2) + s3 / Math.pow(1 + r, 3);
            const dNpv = -s1 / Math.pow(1 + r, 2) - 2 * s2 / Math.pow(1 + r, 3) - 3 * s3 / Math.pow(1 + r, 4);
            const nextR = r - npv / dNpv;
            if (Math.abs(nextR - r) < 0.0001) {
                return Math.max(0, nextR * 100);
            }
            r = nextR;
            if (r < -0.9) r = -0.9;
        }
        return Math.max(0, r * 100);
    }

    function recalculate() {
        if (!slVolume || !slWaste || !slOee || !slLabor) return;
        const ind = industryPresets[currentIndustry] || industryPresets.manufacturing;
        const v1 = parseFloat(slVolume.value);
        const v2 = parseFloat(slWaste.value);
        const v3 = parseFloat(slOee.value);
        const v4 = parseFloat(slLabor.value);

        if (valVolume) valVolume.textContent = `${v1} ${ind.param1.unit}`;
        if (valWaste) valWaste.textContent = `${v2}${ind.param2.unit}`;
        if (valOee) valOee.textContent = `${v3}${ind.param3.unit}`;
        if (valLabor) valLabor.textContent = `${v4} ${ind.param4.unit}`;

        const savingsWaste = v1 * (v2 / 100) * ind.param2.factor * 1.5;
        const savingsTurnaround = (v3 * 1.5) * ind.param3.factor;
        const savingsLabor = (v4 * 12 * 120000 * 0.75) / 1e9;
        const baseVolumeSavings = v1 * ind.param1.factor;

        const s1 = Math.max(1.5, baseVolumeSavings + savingsWaste + savingsTurnaround + savingsLabor);
        const s2 = s1 * 1.20;
        const s3 = s1 * 1.50;

        const c0 = ind.c0_vnd;
        const annualMaint = c0 * 0.20;

        const net1 = s1 - annualMaint;
        const net2 = s2 - annualMaint;
        const net3 = s3 - annualMaint;

        const rHurdle = 0.10;
        const npvVnd = -c0 + (net1 / (1 + rHurdle)) + (net2 / Math.pow(1 + rHurdle, 2)) + (net3 / Math.pow(1 + rHurdle, 3));
        const paybackMonths = Math.min(36, Math.max(1.5, (c0 / (net1 / 12))));
        const totalNetBenefit = net1 + net2 + net3;
        const roiPercent = Math.max(50, ((totalNetBenefit - c0) / c0) * 100);
        const irrPercent = calculateIRR(c0, net1, net2, net3);

        if (isVnd) {
            if (outNpv) outNpv.textContent = `${npvVnd.toFixed(2)} Tỷ ₫`;
            if (outIrr) outIrr.textContent = `${irrPercent.toFixed(1)}%`;
            if (outPayback) outPayback.textContent = `${paybackMonths.toFixed(1)} Tháng`;
            if (outRoi) outRoi.textContent = `${Math.round(roiPercent)}%`;
        } else {
            const npvUsd = (npvVnd * 1e9) / FX_USD;
            if (outNpv) outNpv.textContent = `$${(npvUsd / 1000).toFixed(0)}K`;
            if (outIrr) outIrr.textContent = `${irrPercent.toFixed(1)}%`;
            if (outPayback) outPayback.textContent = `${paybackMonths.toFixed(1)} Mo`;
            if (outRoi) outRoi.textContent = `${Math.round(roiPercent)}%`;
        }

        const tableRows = studio.querySelectorAll('table tbody tr');
        if (tableRows && tableRows.length >= 3) {
            const fmt = (vnd) => isVnd ? `${vnd.toFixed(2)} Tỷ ₫` : `$${Math.round((vnd * 1e9 / FX_USD) / 1000)}K`;
            const r0Cells = tableRows[0].querySelectorAll('td');
            if (r0Cells.length >= 5) {
                r0Cells[1].textContent = isVnd ? `-${c0.toFixed(2)} Tỷ ₫` : `-$${Math.round((c0 * 1e9 / FX_USD) / 1000)}K`;
                r0Cells[2].textContent = isVnd ? `-${annualMaint.toFixed(2)} Tỷ ₫` : `-$${Math.round((annualMaint * 1e9 / FX_USD) / 1000)}K`;
                r0Cells[3].textContent = isVnd ? `-${annualMaint.toFixed(2)} Tỷ ₫` : `-$${Math.round((annualMaint * 1e9 / FX_USD) / 1000)}K`;
                r0Cells[4].textContent = isVnd ? `-${annualMaint.toFixed(2)} Tỷ ₫` : `-$${Math.round((annualMaint * 1e9 / FX_USD) / 1000)}K`;
            }
            const r1Cells = tableRows[1].querySelectorAll('td');
            if (r1Cells.length >= 5) {
                r1Cells[2].textContent = `+${fmt(s1)}`;
                r1Cells[3].textContent = `+${fmt(s2)}`;
                r1Cells[4].textContent = `+${fmt(s3)}`;
            }
            const r2Cells = tableRows[2].querySelectorAll('td');
            if (r2Cells.length >= 5) {
                r2Cells[1].textContent = isVnd ? `-${c0.toFixed(2)} Tỷ ₫` : `-$${Math.round((c0 * 1e9 / FX_USD) / 1000)}K`;
                r2Cells[2].textContent = `+${fmt(net1)}`;
                r2Cells[3].textContent = `+${fmt(net2)}`;
                r2Cells[4].textContent = `+${fmt(net3)}`;
            }
        }
    }

    function switchIndustry(targetKey) {
        currentIndustry = targetKey;
        const ind = industryPresets[targetKey] || industryPresets.manufacturing;

        if (lblVolume) lblVolume.textContent = ind.param1.label;
        if (slVolume) {
            slVolume.min = ind.param1.min;
            slVolume.max = ind.param1.max;
            slVolume.step = ind.param1.step;
            slVolume.value = ind.param1.val;
        }

        if (lblWaste) lblWaste.textContent = ind.param2.label;
        if (slWaste) {
            slWaste.min = ind.param2.min;
            slWaste.max = ind.param2.max;
            slWaste.step = ind.param2.step;
            slWaste.value = ind.param2.val;
        }

        if (lblOee) lblOee.textContent = ind.param3.label;
        if (slOee) {
            slOee.min = ind.param3.min;
            slOee.max = ind.param3.max;
            slOee.step = ind.param3.step;
            slOee.value = ind.param3.val;
        }

        if (lblLabor) lblLabor.textContent = ind.param4.label;
        if (slLabor) {
            slLabor.min = ind.param4.min;
            slLabor.max = ind.param4.max;
            slLabor.step = ind.param4.step;
            slLabor.value = ind.param4.val;
        }

        recalculate();
    }

    [slVolume, slWaste, slOee, slLabor].forEach(sl => {
        if (sl) sl.addEventListener('input', recalculate);
    });

    const indBtns = studio.querySelectorAll('.ins-roi-ind-selector');
    indBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            indBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const target = btn.getAttribute('data-industry-target') || 'manufacturing';
            switchIndustry(target);
        });
    });

    const btnVnd = document.getElementById('ins-cur-vnd');
    const btnUsd = document.getElementById('ins-cur-usd');
    if (btnVnd && btnUsd) {
        btnVnd.addEventListener('click', () => {
            isVnd = true;
            btnVnd.classList.add('active');
            btnUsd.classList.remove('active');
            recalculate();
        });
        btnUsd.addEventListener('click', () => {
            isVnd = false;
            btnUsd.classList.add('active');
            btnVnd.classList.remove('active');
            recalculate();
        });
    }

    switchIndustry('manufacturing');
}

function initDigitalTwinSimulator() {
    const twinSection = document.getElementById('insilos_digital_twin_section');
    if (!twinSection) return;
    if (twinSection.__ins_dtwin_init) return;
    twinSection.__ins_dtwin_init = true;

    const assetConfigs = {
        substation: {
            title: "ISOMETRIC SCHEMATIC // 110KV SUBSTATION",
            baseVibe: 1.8,
            baseTemp: 52,
            baseLoad: 74,
            baseThd: 2.4,
            vibeMax: 10,
            tempMax: 120,
            loadMax: 100,
            thdMax: 10,
            vibeLabel: "ISO-VIBE",
            pinPos: {
                vibe: { x: 300, y: 180 },
                temp: { x: 380, y: 110 },
                load: { x: 220, y: 90 }
            }
        },
        crane: {
            title: "ISOMETRIC SCHEMATIC // STS CRANE SEAPORT TERMINAL",
            baseVibe: 2.2,
            baseTemp: 58,
            baseLoad: 82,
            baseThd: 3.1,
            vibeMax: 10,
            tempMax: 120,
            loadMax: 100,
            thdMax: 10,
            vibeLabel: "HOIST-VIBE",
            pinPos: {
                vibe: { x: 320, y: 175 },
                temp: { x: 165, y: 70 },
                load: { x: 420, y: 85 }
            }
        },
        robot: {
            title: "ISOMETRIC SCHEMATIC // WELDING ROBOT CELL",
            baseVibe: 1.4,
            baseTemp: 46,
            baseLoad: 65,
            baseThd: 1.8,
            vibeMax: 10,
            tempMax: 120,
            loadMax: 100,
            thdMax: 10,
            vibeLabel: "AXIS-VIBE",
            pinPos: {
                vibe: { x: 250, y: 140 },
                temp: { x: 210, y: 220 },
                load: { x: 415, y: 140 }
            }
        }
    };

    let currentAsset = "substation";

    const slider = document.getElementById('ins-anomaly-slider');
    const sliderValBadge = document.getElementById('ins-anomaly-slider-val');
    const statusBadge = document.getElementById('ins-dtwin-status-badge');
    const fsmContainer = document.getElementById('ins-live-fsm-ticket-container');
    const resetBtn = document.getElementById('ins-btn-reset-anomaly');

    const gVibe = document.getElementById('ins-gauge-vibration');
    const gTemp = document.getElementById('ins-gauge-temp');
    const gLoad = document.getElementById('ins-gauge-load');
    const gThd = document.getElementById('ins-gauge-thd');

    const pVibe = document.getElementById('ins-progress-vibration');
    const pTemp = document.getElementById('ins-progress-temp');
    const pLoad = document.getElementById('ins-progress-load');
    const pThd = document.getElementById('ins-progress-thd');

    const pinVibe = document.getElementById('ins-pin-vibe');
    const pinTemp = document.getElementById('ins-pin-temp');

    const svgVibe = document.getElementById('ins-dt-svg-vibe');
    const svgTemp = document.getElementById('ins-dt-svg-temp');
    const svgLoad = document.getElementById('ins-dt-svg-load');

    const pinVibeGroup = document.getElementById('ins-dt-pin-vibe');
    const pinTempGroup = document.getElementById('ins-dt-pin-temp');
    const pinLoadGroup = document.getElementById('ins-dt-pin-load');

    function updateSimulation(val) {
        const anomalyVal = parseInt(val, 10) || 0;
        const cfg = assetConfigs[currentAsset] || assetConfigs.substation;

        if (sliderValBadge) sliderValBadge.textContent = `${anomalyVal}%`;

        const currentVibe = parseFloat((cfg.baseVibe * (1 + anomalyVal / 100)).toFixed(1));
        const currentTemp = Math.round(cfg.baseTemp + anomalyVal * 0.25);
        const currentLoad = Math.min(100, Math.round(cfg.baseLoad + anomalyVal * 0.15));
        const currentThd = parseFloat((cfg.baseThd * (1 + anomalyVal / 50)).toFixed(1));

        if (gVibe) gVibe.textContent = currentVibe;
        if (gTemp) gTemp.textContent = currentTemp;
        if (gLoad) gLoad.textContent = currentLoad;
        if (gThd) gThd.textContent = currentThd;

        // Synchronize SVG telemetry text elements with gauges
        const vibeLabel = cfg.vibeLabel || 'ISO-VIBE';
        if (svgVibe) svgVibe.textContent = `${vibeLabel}: ${currentVibe} mm/s`;
        if (svgTemp) svgTemp.textContent = `TEMP: ${currentTemp}°C`;
        if (svgLoad) svgLoad.textContent = `LOAD: ${currentLoad}%`;

        if (pVibe) pVibe.style.width = `${Math.min(100, (currentVibe / cfg.vibeMax) * 100)}%`;
        if (pTemp) pTemp.style.width = `${Math.min(100, (currentTemp / cfg.tempMax) * 100)}%`;
        if (pLoad) pLoad.style.width = `${Math.min(100, currentLoad)}%`;
        if (pThd) pThd.style.width = `${Math.min(100, (currentThd / cfg.thdMax) * 100)}%`;

        if (currentVibe < 2.8 && anomalyVal < 75) {
            if (statusBadge) {
                statusBadge.className = 'badge bg-secondary bg-opacity-25 text-mint font-monospace small';
                statusBadge.textContent = 'TRẠNG THÁI: BÌNH THƯỜNG';
            }
            if (fsmContainer) fsmContainer.classList.add('d-none');
            if (pinVibe) pinVibe.setAttribute('fill', '#10B981');
            if (pinTemp) pinTemp.setAttribute('fill', '#42E6C3');
            if (svgVibe) svgVibe.setAttribute('fill', '#10B981');
        } else if (currentVibe >= 2.8 && currentVibe < 4.5 && anomalyVal < 100) {
            if (statusBadge) {
                statusBadge.className = 'badge bg-warning bg-opacity-25 text-warning font-monospace small';
                statusBadge.textContent = 'CẢNH BÁO: RUNG ĐỘNG VƯỢT NGƯỠNG ISO';
            }
            if (fsmContainer) {
                fsmContainer.classList.remove('d-none');
                fsmContainer.className = 'mt-3 p-3 bg-black bg-opacity-75 border border-warning rounded-3';
            }
            if (pinVibe) pinVibe.setAttribute('fill', '#F59E0B');
            if (pinTemp) pinTemp.setAttribute('fill', '#F59E0B');
            if (svgVibe) svgVibe.setAttribute('fill', '#F59E0B');
        } else {
            if (statusBadge) {
                statusBadge.className = 'badge bg-danger bg-opacity-25 text-danger font-monospace small';
                statusBadge.textContent = 'SỰ CỐ KHẨN CẤP: NGUY CƠ HỎNG Ổ BI';
            }
            if (fsmContainer) {
                fsmContainer.classList.remove('d-none');
                fsmContainer.className = 'mt-3 p-3 bg-danger bg-opacity-25 border border-danger rounded-3';
            }
            if (pinVibe) pinVibe.setAttribute('fill', '#EF4444');
            if (pinTemp) pinTemp.setAttribute('fill', '#EF4444');
            if (svgVibe) svgVibe.setAttribute('fill', '#EF4444');
        }
    }

    function switchDigitalTwinAsset(targetKey) {
        currentAsset = targetKey;
        const cfg = assetConfigs[currentAsset] || assetConfigs.substation;

        const schematicTitle = twinSection.querySelector('.text-white.font-monospace.small.fw-bold');
        if (schematicTitle) {
            schematicTitle.textContent = cfg.title;
        }

        // Switch active SVG schematic
        const schematics = twinSection.querySelectorAll('.ins-dt-asset-schematic');
        schematics.forEach(svgG => {
            const assetName = svgG.getAttribute('data-asset') || svgG.id.replace('ins-dt-schematic-', '');
            if (assetName === currentAsset) {
                svgG.classList.remove('d-none');
            } else {
                svgG.classList.add('d-none');
            }
        });

        // Reposition pins to match asset geometry
        if (cfg.pinPos) {
            if (pinVibeGroup && cfg.pinPos.vibe) {
                pinVibeGroup.setAttribute('transform', `translate(${cfg.pinPos.vibe.x}, ${cfg.pinPos.vibe.y})`);
            }
            if (pinTempGroup && cfg.pinPos.temp) {
                pinTempGroup.setAttribute('transform', `translate(${cfg.pinPos.temp.x}, ${cfg.pinPos.temp.y})`);
            }
            if (pinLoadGroup && cfg.pinPos.load) {
                pinLoadGroup.setAttribute('transform', `translate(${cfg.pinPos.load.x}, ${cfg.pinPos.load.y})`);
            }
        }

        const currentVal = slider ? slider.value : 45;
        updateSimulation(currentVal);
    }

    if (slider) {
        slider.addEventListener('input', (e) => {
            updateSimulation(e.target.value);
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            if (slider) slider.value = 45;
            updateSimulation(45);
        });
    }

    const assetBtns = twinSection.querySelectorAll('.ins-dtwin-asset-selector');
    assetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            assetBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const target = btn.getAttribute('data-dtwin-target') || 'substation';
            switchDigitalTwinAsset(target);
        });
    });

    switchDigitalTwinAsset('substation');
}

if (!window.__insilos_bootstrap_registered) {
    window.__insilos_bootstrap_registered = true;
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initInsilosInteractive);
    } else {
        initInsilosInteractive();
    }
}
window.insilosInitInteractive = initInsilosInteractive;
window.initRoiCalculator = function() {
    if (typeof window.insilosInitInteractive === "function") window.insilosInitInteractive();
};
window.initPricingConfigurator = function() {
    if (typeof window.insilosInitInteractive === "function") window.insilosInitInteractive();
};
window.initResourceFilters = function() {
    if (typeof window.insilosInitInteractive === "function") window.insilosInitInteractive();
};
window.initDemoWizard = function() {
    if (typeof window.insilosInitInteractive === "function") window.insilosInitInteractive();
};
window.initAnimatedCounters = function() {
    if (typeof window.insilosInitInteractive === "function") window.insilosInitInteractive();
};
window.initSovereignTrustCenter = initSovereignTrustCenter;
window.initIndustrialSandbox = initIndustrialSandbox;
window.initFsmConsole = initFsmConsole;
window.initIdpWorkbench = initIdpWorkbench;
window.initKnowledgeGraphVisualizer = initKnowledgeGraphVisualizer;
window.initHsCodeRecommender = initHsCodeRecommender;
window.initRoiEngineeringStudio = initRoiEngineeringStudio;
window.initDigitalTwinSimulator = initDigitalTwinSimulator;

