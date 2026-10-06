/**
 * Innoria 3D Interactive Architecture Deck Controller
 * File: innoria_deck_3d.js
 * Host Target: innoria.insilos.com (Insilos Sovereign Web Platform)
 * 
 * Features:
 * - 4-Layer Isometric 3D Stack:
 *   L0: No-Code Platform (App Studio, Workflow Designer, Automation)
 *   L1: Platform Services (Architecture | Security | Admin | Deployment)
 *   L2: Artificial Intelligent (Generative AI, Explainable AI, Human-Machine Understanding)
 *   L3: Data Lake & Core ERP (ERP, GRC, IIoT, Sovereign DB)
 * - Signature "Kéo ra khỏi Deck" Pull-Out Animation on Hover/Click
 * - Dynamic Full Column Description Expansion with Tech Specs & Metrics
 * - Mouse Drag 3D Orbit / Parallax
 * - Exploded Deck Mode (Phân rã trục Z)
 * - Auto Demo Tour Mode (3.4s pacing)
 * - 60 FPS Hardware-Accelerated CSS 3D Engine (Zero external dependencies)
 */

(function () {
    'use strict';

    function initInnoria3DDeck(container) {
        if (!container || container.__innoria_deck_initialized) return;
        container.__innoria_deck_initialized = true;

        var layers = [
            { id: 0, name: "No-Code Platform", color: "#0284c7" },
            { id: 1, name: "Platform Services", color: "#1d4ed8" },
            { id: 2, name: "Artificial Intelligence", color: "#7c3aed" },
            { id: 3, name: "Data Lake & Core ERP", color: "#d97706" }
        ];

        var deckContainer = container.querySelector(".deck-container-3d");
        var stageCard = container.querySelector(".stage-card");
        var badgeLayerName = container.querySelector("#badgeLayerName");
        var layerBadge = container.querySelector("#layerBadge");
        var btnExplode = container.querySelector("#btnExplode");
        var btnExplodeText = container.querySelector("#btnExplodeText");
        var btnResetView = container.querySelector("#btnResetView");
        var btnAutoTour = container.querySelector("#btnAutoTour");
        var btnAutoTourText = container.querySelector("#btnAutoTourText");

        var summaryCardsContainer = container.querySelector("#summaryCardsContainer");
        var deepPanels = [
            container.querySelector("#deep-panel-0"),
            container.querySelector("#deep-panel-1"),
            container.querySelector("#deep-panel-2"),
            container.querySelector("#deep-panel-3")
        ];

        var activeIndex = null;
        var isExploded = false;
        var autoTourActive = true;
        var tourInterval = null;
        var isDragging = false;
        var startX = 0, startY = 0;
        var rotX = 58, rotZ = -38;
        var baseRotX = 58, baseRotZ = -38;

        function setActiveLayer(idx) {
            activeIndex = idx;

            // 1. Update 3D Slabs
            layers.forEach(function (l, i) {
                var slab = container.querySelector("#slab-" + i);
                var card = container.querySelector("#card-" + i);

                if (slab) {
                    if (idx === null) {
                        slab.classList.remove("pulled-out", "dimmed");
                    } else if (i === idx) {
                        slab.classList.add("pulled-out");
                        slab.classList.remove("dimmed");
                    } else {
                        slab.classList.remove("pulled-out");
                        slab.classList.add("dimmed");
                    }
                }

                if (card) {
                    if (idx === null) {
                        card.classList.remove("active-summary");
                    } else if (i === idx) {
                        card.classList.add("active-summary");
                    } else {
                        card.classList.remove("active-summary");
                    }
                }
            });

            // 2. Update HUD Badge
            if (badgeLayerName && layerBadge) {
                if (idx !== null) {
                    badgeLayerName.textContent = layers[idx].name.toUpperCase();
                    layerBadge.style.color = layers[idx].color;
                    layerBadge.style.borderColor = layers[idx].color;
                } else {
                    badgeLayerName.textContent = "ALL LAYERS";
                    layerBadge.style.color = "#0052ff";
                    layerBadge.style.borderColor = "rgba(0, 82, 255, 0.3)";
                }
            }

            // 3. Switch between Summary List and Deep Architecture Panel
            if (summaryCardsContainer) {
                if (idx !== null) {
                    summaryCardsContainer.style.display = "none";
                    deepPanels.forEach(function (panel, i) {
                        if (panel) {
                            if (i === idx) {
                                panel.classList.add("visible");
                            } else {
                                panel.classList.remove("visible");
                            }
                        }
                    });
                } else {
                    summaryCardsContainer.style.display = "flex";
                    deepPanels.forEach(function (panel) {
                        if (panel) panel.classList.remove("visible");
                    });
                }
            }
        }

        // Attach Hover & Click Listeners to Slabs and Summary Cards
        layers.forEach(function (l, i) {
            var slab = container.querySelector("#slab-" + i);
            var card = container.querySelector("#card-" + i);

            if (slab) {
                slab.addEventListener("mouseenter", function () {
                    stopAutoTour();
                    setActiveLayer(i);
                });
                slab.addEventListener("click", function (e) {
                    e.stopPropagation();
                    stopAutoTour();
                    setActiveLayer(i);
                });
            }

            if (card) {
                card.addEventListener("mouseenter", function () {
                    stopAutoTour();
                    setActiveLayer(i);
                });
                card.addEventListener("click", function () {
                    stopAutoTour();
                    setActiveLayer(i);
                });
            }
        });

        // Quick Selector Tabs in Deep Panels
        container.querySelectorAll(".tab-item").forEach(function (tab) {
            tab.addEventListener("click", function (e) {
                e.stopPropagation();
                stopAutoTour();
                var targetLayer = parseInt(tab.getAttribute("data-tab-layer"), 10);
                setActiveLayer(targetLayer);
            });
        });

        // Stage Card Mouse Leave
        if (stageCard) {
            stageCard.addEventListener("mouseleave", function () {
                if (!autoTourActive) {
                    setActiveLayer(null);
                }
            });

            // Mouse Drag Orbit
            stageCard.addEventListener("mousedown", function (e) {
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
            });

            window.addEventListener("mouseup", function () {
                isDragging = false;
            });

            stageCard.addEventListener("mousemove", function (e) {
                if (!deckContainer) return;
                if (isDragging) {
                    var dx = e.clientX - startX;
                    var dy = e.clientY - startY;
                    rotZ = baseRotZ + dx * 0.25;
                    rotX = Math.max(25, Math.min(85, baseRotX - dy * 0.25));
                    deckContainer.style.transform = "rotateX(" + rotX + "deg) rotateZ(" + rotZ + "deg) translateY(-15px)";
                } else {
                    var rect = stageCard.getBoundingClientRect();
                    var cx = rect.left + rect.width / 2;
                    var cy = rect.top + rect.height / 2;
                    var tiltX = (e.clientY - cy) / (rect.height / 2);
                    var tiltY = (e.clientX - cx) / (rect.width / 2);
                    var dynRotX = rotX - tiltX * 4;
                    var dynRotZ = rotZ + tiltY * 5;
                    deckContainer.style.transform = "rotateX(" + dynRotX + "deg) rotateZ(" + dynRotZ + "deg) translateY(-15px)";
                }
            });
        }

        // Explode Button
        if (btnExplode && deckContainer) {
            btnExplode.addEventListener("click", function () {
                isExploded = !isExploded;
                if (isExploded) {
                    deckContainer.classList.add("deck-exploded");
                    if (btnExplodeText) btnExplodeText.textContent = "Thu Gọn Deck";
                    btnExplode.classList.add("active");
                } else {
                    deckContainer.classList.remove("deck-exploded");
                    if (btnExplodeText) btnExplodeText.textContent = "Phân Rã Deck";
                    btnExplode.classList.remove("active");
                }
            });
        }

        // Reset View Button
        if (btnResetView && deckContainer) {
            btnResetView.addEventListener("click", function () {
                rotX = baseRotX;
                rotZ = baseRotZ;
                deckContainer.style.transform = "rotateX(" + baseRotX + "deg) rotateZ(" + baseRotZ + "deg) translateY(-15px)";
                setActiveLayer(null);
            });
        }

        // Auto Demo Tour
        function startAutoTour() {
            autoTourActive = true;
            if (btnAutoTourText) btnAutoTourText.textContent = "Auto Demo: ON";
            if (btnAutoTour) btnAutoTour.classList.remove("opacity-50");
            var step = 0;
            clearInterval(tourInterval);
            tourInterval = setInterval(function () {
                setActiveLayer(step % layers.length);
                step++;
            }, 3400);
        }

        function stopAutoTour() {
            if (!autoTourActive) return;
            autoTourActive = false;
            clearInterval(tourInterval);
            if (btnAutoTourText) btnAutoTourText.textContent = "Auto Demo: OFF";
            if (btnAutoTour) btnAutoTour.classList.add("opacity-50");
        }

        if (btnAutoTour) {
            btnAutoTour.addEventListener("click", function () {
                if (autoTourActive) {
                    stopAutoTour();
                    setActiveLayer(null);
                } else {
                    startAutoTour();
                }
            });
        }

        // Initialize Auto Tour
        startAutoTour();
    }

    // -------------------------------------------------------------------------
    // Innoria 4-Pillars 3D Interactive Card Tilt Engine
    // -------------------------------------------------------------------------
    function initInnoriaPillars3D() {
        var cards = document.querySelectorAll('.pillar-card');
        cards.forEach(function (card) {
            if (card.__pillars_3d_initialized) return;
            card.__pillars_3d_initialized = true;

            card.addEventListener('mousemove', function (e) {
                var rect = card.getBoundingClientRect();
                var x = e.clientX - rect.left;
                var y = e.clientY - rect.top;
                var centerX = rect.width / 2;
                var centerY = rect.height / 2;
                var rotX = ((y - centerY) / centerY) * -9;
                var rotY = ((x - centerX) / centerX) * 9;

                card.style.transform = 'perspective(1000px) rotateX(' + rotX.toFixed(2) + 'deg) rotateY(' + rotY.toFixed(2) + 'deg) translateZ(10px)';
            });

            card.addEventListener('mouseleave', function () {
                card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
            });
        });
    }

    // Auto-mount on DOM ready or Odoo Website loading
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            document.querySelectorAll('.deck-app-container').forEach(initInnoria3DDeck);
            initInnoriaPillars3D();
        });
    } else {
        document.querySelectorAll('.deck-app-container').forEach(initInnoria3DDeck);
        initInnoriaPillars3D();
    }

    // Expose to window
    if (typeof window !== 'undefined') {
        window.initInnoria3DDeck = initInnoria3DDeck;
        window.initInnoriaPillars3D = initInnoriaPillars3D;
    }
})();

