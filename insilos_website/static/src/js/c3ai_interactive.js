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

    // 6. Interactive ROI & Volume Calculator
    document.querySelectorAll(".ins-roi-calculator").forEach((calc) => {
        const pills = calc.querySelectorAll(".ins-calc-pill");
        const valSavings = calc.querySelector(".ins-calc-val-savings");
        const valHours = calc.querySelector(".ins-calc-val-hours");
        const valStp = calc.querySelector(".ins-calc-val-stp");
        const valUnit = calc.querySelector(".ins-calc-val-unit");

        const dataTiers = {
            "5k": {
                savings: "₫38,500,000",
                hours: "140 Giờ / Tháng",
                stp: "99.2%",
                unit: "0.05 Credits"
            },
            "25k": {
                savings: "₫192,500,000",
                hours: "710 Giờ / Tháng",
                stp: "99.82%",
                unit: "0.038 Credits"
            },
            "100k": {
                savings: "₫770,000,000",
                hours: "2,840 Giờ / Tháng",
                stp: "99.95%",
                unit: "0.024 Credits"
            },
            "500k": {
                savings: "₫3,850,000,000",
                hours: "14,200 Giờ / Tháng",
                stp: "99.99%",
                unit: "0.015 Credits"
            }
        };

        pills.forEach((pill) => {
            pill.addEventListener("click", () => {
                pills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                const vol = pill.getAttribute("data-vol");
                const data = dataTiers[vol];
                if (data) {
                    const metricEls = [valSavings, valHours, valStp, valUnit].filter(Boolean);
                    metricEls.forEach(el => {
                        el.style.opacity = "0.35";
                        el.style.transform = "translateY(2px)";
                        el.style.transition = "all 0.12s ease";
                    });
                    setTimeout(() => {
                        if (valSavings) valSavings.innerText = data.savings;
                        if (valHours) valHours.innerText = data.hours;
                        if (valStp) valStp.innerText = data.stp;
                        if (valUnit) valUnit.innerText = data.unit;
                        metricEls.forEach(el => {
                            el.style.opacity = "1";
                            el.style.transform = "none";
                        });
                    }, 120);
                }
            });
        });
    });

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
        const fxButtons = heroShowcase.querySelectorAll(".ins-btn-fx");

        const FX_MODES = ["blade", "glitch", "iris", "warp", "luma", "shutter"];

        // 6-Mode Active Effects Rotation Cycle (Full Rotation across all 6 modes)
        const FX_ROTATION_CYCLE = ["blade", "glitch", "iris", "warp", "luma", "shutter"];
        let fxCycleStep = 0;

        const ACT_FX_MAP = {
            1: "iris",     // Radial Iris Bloom returning to home base
            2: "blade",    // 45° Laser Blade Angled Slice Wipe
            3: "glitch",   // Cybernetic Glitch & RGB Split
            4: "warp",     // Quantum Warp Hyper-Zoom
            5: "luma",     // Anamorphic Luma Light Leak & Solar Flare
            6: "shutter"   // Bi-Directional Vault Shutter
        };

        const FX_NAMES = {
            cycle: "AUTO-CYCLE",
            blade: "BLADE WIPE",
            glitch: "CYBER GLITCH",
            iris: "RADIAL IRIS",
            warp: "QUANTUM WARP",
            luma: "LUMA FLARE",
            shutter: "VAULT SHUTTER"
        };

        const FX_ELEMENTS = {
            blade: document.getElementById("ins_blade_beam"),
            glitch: document.getElementById("ins_glitch_overlay"),
            iris: document.getElementById("ins_iris_ring"),
            warp: document.getElementById("ins_warp_tunnel"),
            luma: document.getElementById("ins_luma_flare"),
            shutter: document.getElementById("ins_shutter_line")
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
                shutter: 1150
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

        // Scene Transition FX Buttons (CYCLE, BLADE, GLITCH, IRIS, WARP, LUMA, SHUTTER)
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
<span class="token-keyword">async def</span> <span class="token-function">ingest_high_frequency_telemetry</span>(node_id: <span class="token-class">str</span> = <span class="token-string">"GENCO3_TURBINE_04"</span>):
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
<span class="token-keyword">async def</span> <span class="token-function">ingest_federated_telemetry</span>(node_id: <span class="token-class">str</span> = <span class="token-string">"GENCO3_TURBINE_04"</span>):
    client = EdgeGatewayClient.<span class="token-function">connect</span>(endpoint=<span class="token-string">"wss://edge-gw.insilos.io:8443"</span>, tls_token=<span class="token-string">"/etc/insilos/pki/cloud_token.jwt"</span>)
    stream = client.<span class="token-function">subscribe_stream</span>(channel=<span class="token-string">"telemetry.live.genco3"</span>, compression=<span class="token-string">"zstd"</span>)
    
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

    initGoldMasterSuite();
    initPlatformTopology();
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
