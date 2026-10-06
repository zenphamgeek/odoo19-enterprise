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
 * - 60 FPS RequestAnimationFrame Physics Engine (Spring LERP + Friction Momentum)
 * - True 6-Face Airtight 3D Box Geometry (Zero hollow clipping)
 * - Relative Z-Layer Extraction Vector (Preserves vertical hierarchy on pull-out)
 * - Buttery Smooth Mouse Orbit Drag & Passive Parallax
 * - Exploded Deck Mode (Phân rã trục Z)
 * - Auto Demo Tour Mode (3.4s pacing)
 * - Non-ghost Volumetric Dimming (All layers maintain physical presence)
 */

(function () {
    'use strict';

    function initInnoria3DDeck(container) {
        if (!container || container.__innoria_deck_initialized) return;
        container.__innoria_deck_initialized = true;

        var layers = [
            { id: 0, name: "No-Code Platform", color: "#00F0FF" },
            { id: 1, name: "Platform Services", color: "#3B82F6" },
            { id: 2, name: "Artificial Intelligence", color: "#F59E0B" },
            { id: 3, name: "Data Lake & Core ERP", color: "#10B981" }
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
        var autoTourActive = false;
        var tourInterval = null;

        // ---------------------------------------------------------------------
        // 60 FPS Spring & Inertia Physics Engine
        // ---------------------------------------------------------------------
        var orbitRotX = 58;
        var orbitRotZ = -38;
        var parallaxTiltX = 0;
        var parallaxTiltZ = 0;
        var currentParallaxX = 0;
        var currentParallaxZ = 0;
        var targetRotX = 58;
        var targetRotZ = -38;
        var currentRotX = 58;
        var currentRotZ = -38;
        var velX = 0;
        var velZ = 0;
        var isDragging = false;
        var lastMouseX = 0;
        var lastMouseY = 0;
        var springTension = 0.085;
        var friction = 0.88;
        var mouseSens = 0.35;
        var rafId = null;

        function physicsTick() {
            if (!isDragging) {
                // Apply inertia momentum friction to persistent orbit rotation
                if (Math.abs(velX) > 0.005 || Math.abs(velZ) > 0.005) {
                    velX *= friction;
                    velZ *= friction;
                    orbitRotX -= velX;
                    orbitRotZ += velZ;
                    orbitRotX = Math.max(18, Math.min(85, orbitRotX));
                } else {
                    velX = 0;
                    velZ = 0;
                }
            }

            // Smooth parallax micro-tilt transition
            currentParallaxX += (parallaxTiltX - currentParallaxX) * 0.12;
            currentParallaxZ += (parallaxTiltZ - currentParallaxZ) * 0.12;

            // Combine persistent orbit orientation with gentle passive parallax
            targetRotX = Math.max(18, Math.min(85, orbitRotX + currentParallaxX));
            targetRotZ = orbitRotZ + currentParallaxZ;

            // Spring LERP interpolation for buttery smooth 60 FPS rotation
            currentRotX += (targetRotX - currentRotX) * springTension;
            currentRotZ += (targetRotZ - currentRotZ) * springTension;

            if (deckContainer) {
                deckContainer.style.transform = "rotateX(" + currentRotX.toFixed(2) + "deg) rotateZ(" + currentRotZ.toFixed(2) + "deg) translateY(-15px)";
            }

            rafId = requestAnimationFrame(physicsTick);
        }

        // Ignite the physics loop
        physicsTick();

        // ---------------------------------------------------------------------
        // Layer Activation & State Synchronization
        // ---------------------------------------------------------------------
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
                    layerBadge.style.boxShadow = "0 0 12px " + layers[idx].color + "40";
                } else {
                    badgeLayerName.textContent = "ALL LAYERS";
                    layerBadge.style.color = "#0ABBDB";
                    layerBadge.style.borderColor = "rgba(10, 187, 219, 0.4)";
                    layerBadge.style.boxShadow = "none";
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

            // 4. Synchronize all tab selectors
            if (idx !== null) {
                container.querySelectorAll(".tab-item").forEach(function (tab) {
                    var tabLayer = parseInt(tab.getAttribute("data-tab-layer"), 10);
                    if (tabLayer === idx) {
                        tab.classList.add("active");
                    } else {
                        tab.classList.remove("active");
                    }
                });
            }
        }

        // Attach Hover, Click & Touch Listeners to Slabs and Summary Cards
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
                slab.addEventListener("touchstart", function (e) {
                    e.stopPropagation();
                    stopAutoTour();
                    setActiveLayer(i);
                }, { passive: true });
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
                card.addEventListener("touchstart", function () {
                    stopAutoTour();
                    setActiveLayer(i);
                }, { passive: true });
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

        // ---------------------------------------------------------------------
        // Mouse & Touch Drag Orbit & Passive Parallax Handlers
        // ---------------------------------------------------------------------
        if (stageCard) {
            stageCard.addEventListener("mousedown", function (e) {
                stopAutoTour();
                isDragging = true;
                lastMouseX = e.clientX;
                lastMouseY = e.clientY;
                velX = 0;
                velZ = 0;
                if (stageCard.style) stageCard.style.cursor = "grabbing";
            });

            window.addEventListener("mouseup", function () {
                if (isDragging) {
                    isDragging = false;
                    if (stageCard && stageCard.style) stageCard.style.cursor = "";
                }
            });

            window.addEventListener("mousemove", function (e) {
                if (isDragging) {
                    var dx = e.clientX - lastMouseX;
                    var dy = e.clientY - lastMouseY;
                    velZ = dx * mouseSens;
                    velX = dy * mouseSens;
                    orbitRotZ += velZ;
                    orbitRotX -= velX;
                    orbitRotX = Math.max(18, Math.min(85, orbitRotX));
                    lastMouseX = e.clientX;
                    lastMouseY = e.clientY;
                }
            });

            // Touch Drag Orbit for Mobile / Tablet
            stageCard.addEventListener("touchstart", function (e) {
                if (e.touches && e.touches.length === 1) {
                    stopAutoTour();
                    isDragging = true;
                    lastMouseX = e.touches[0].clientX;
                    lastMouseY = e.touches[0].clientY;
                    velX = 0;
                    velZ = 0;
                    parallaxTiltX = 0;
                    parallaxTiltZ = 0;
                }
            }, { passive: true });

            window.addEventListener("touchmove", function (e) {
                if (isDragging && e.touches && e.touches.length === 1) {
                    var dx = e.touches[0].clientX - lastMouseX;
                    var dy = e.touches[0].clientY - lastMouseY;
                    velZ = dx * mouseSens;
                    velX = dy * mouseSens;
                    orbitRotZ += velZ;
                    orbitRotX -= velX;
                    orbitRotX = Math.max(18, Math.min(85, orbitRotX));
                    lastMouseX = e.touches[0].clientX;
                    lastMouseY = e.touches[0].clientY;
                }
            }, { passive: true });

            window.addEventListener("touchend", function () {
                if (isDragging) {
                    isDragging = false;
                }
            }, { passive: true });

            window.addEventListener("touchcancel", function () {
                if (isDragging) {
                    isDragging = false;
                }
            }, { passive: true });

            // Passive gentle parallax when hovering over stage
            stageCard.addEventListener("mousemove", function (e) {
                if (isDragging) return;
                var rect = stageCard.getBoundingClientRect();
                var cx = rect.left + rect.width / 2;
                var cy = rect.top + rect.height / 2;
                var tiltX = (e.clientY - cy) / (rect.height / 2);
                var tiltY = (e.clientX - cx) / (rect.width / 2);
                parallaxTiltX = -tiltX * 5.5;
                parallaxTiltZ = tiltY * 6.5;
            });

            stageCard.addEventListener("mouseleave", function () {
                parallaxTiltX = 0;
                parallaxTiltZ = 0;
            });
        }

        // Explode Button
        if (btnExplode && deckContainer) {
            btnExplode.addEventListener("click", function () {
                stopAutoTour();
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

        // Reset View Button (Smooth spring LERP back to default 58deg / -38deg)
        if (btnResetView && deckContainer) {
            btnResetView.addEventListener("click", function () {
                stopAutoTour();
                orbitRotX = 58;
                orbitRotZ = -38;
                parallaxTiltX = 0;
                parallaxTiltZ = 0;
                currentParallaxX = 0;
                currentParallaxZ = 0;
                velX = 0;
                velZ = 0;
                setActiveLayer(null);
            });
        }

        // Auto Demo Tour (3.4s cycle, auto-interrupt on user interaction)
        function startAutoTour() {
            autoTourActive = true;
            if (btnAutoTourText) btnAutoTourText.textContent = "Auto Demo: ON";
            if (btnAutoTour) {
                btnAutoTour.classList.remove("opacity-50");
                btnAutoTour.classList.add("active");
            }
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
            if (btnAutoTour) {
                btnAutoTour.classList.add("opacity-50");
                btnAutoTour.classList.remove("active");
            }
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

        // Initialize Auto Tour (defaults to OFF so user has uninterrupted inspection)
        stopAutoTour();
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
