/**
 * Innoria 3D Interactive Architecture Deck Controller
 * File: innoria_deck_3d.js
 * Host Target: innoria.insilos.com (Insilos Sovereign Web Platform)
 * 
 * Upgraded via Claude Opus 5.5 & Sonnet 5.5 Physics Architecture:
 * - 60/120 FPS Frame-rate Independent 2nd-Order Spring Dynamics (dt-scaled harmonic oscillator)
 * - Pure Isometric Drawer Extraction Vector (+Y forward along isometric axis, +Z elevation)
 * - Decoupled Pointer Drag Momentum with Exponential Decay Inertia
 * - Drag-Hover Conflict Lock (Slab hover locked during active orbit drag)
 * - Unified Pointer Events API with setPointerCapture (Full Mobile/Touch/Desktop parity)
 * - 4-Layer Stack Synchronized HUD, Deep Architecture Panels, Exploded Deck, and Auto-Tour
 */

(function () {
    'use strict';

    var DRAG_THRESHOLD = 5;
    var SPRING_STIFFNESS = 190;
    var SPRING_DAMPING = 22;
    var ORBIT_FRICTION = 2.8; // Exponential velocity decay rate
    var MAX_DT = 0.0333; // 30 FPS floor for numerical stability

    function clamp(val, min, max) {
        return Math.max(min, Math.min(max, val));
    }

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

        var slabs = [
            container.querySelector("#slab-0"),
            container.querySelector("#slab-1"),
            container.querySelector("#slab-2"),
            container.querySelector("#slab-3")
        ];

        var activeIndex = null;
        var isExploded = false;
        var autoTourActive = false;
        var tourInterval = null;

        // ---------------------------------------------------------------------
        // 2nd-Order Spring Dynamics State (Slab Pull-Out)
        // ---------------------------------------------------------------------
        var slabSprings = [
            { value: 0, velocity: 0 },
            { value: 0, velocity: 0 },
            { value: 0, velocity: 0 },
            { value: 0, velocity: 0 }
        ];

        // ---------------------------------------------------------------------
        // Orbit Rotation & Inertia State
        // ---------------------------------------------------------------------
        var DEFAULT_ROT_X = 58;
        var DEFAULT_ROT_Z = -38;

        var orbitRotX = DEFAULT_ROT_X;
        var orbitRotZ = DEFAULT_ROT_Z;
        var targetRotX = DEFAULT_ROT_X;
        var targetRotZ = DEFAULT_ROT_Z;
        var currentRotX = DEFAULT_ROT_X;
        var currentRotZ = DEFAULT_ROT_Z;

        var parallaxTiltX = 0;
        var parallaxTiltZ = 0;
        var currentParallaxX = 0;
        var currentParallaxZ = 0;

        var velX = 0;
        var velZ = 0;

        var isDragging = false;
        var pointerId = null;
        var downX = 0;
        var downY = 0;
        var lastX = 0;
        var lastY = 0;
        var lastTime = performance.now();

        // ---------------------------------------------------------------------
        // 60/120 FPS Frame-rate Independent Physics Engine Loop
        // ---------------------------------------------------------------------
        var previousTickTime = performance.now();

        function physicsTick(now) {
            var rawDt = (now - previousTickTime) / 1000;
            var dt = Math.min(rawDt > 0 ? rawDt : 0.016, MAX_DT);
            previousTickTime = now;

            // 1. Orbit Inertia & Momentum Physics
            if (!isDragging) {
                if (Math.abs(velX) > 0.05 || Math.abs(velZ) > 0.05) {
                    var damping = Math.exp(-ORBIT_FRICTION * dt);
                    velX *= damping;
                    velZ *= damping;
                    orbitRotX += velX * dt;
                    orbitRotZ += velZ * dt;
                    orbitRotX = clamp(orbitRotX, 18, 85);
                } else {
                    velX = 0;
                    velZ = 0;
                }
            }

            // 2. Smooth Parallax Micro-tilt Transition
            currentParallaxX += (parallaxTiltX - currentParallaxX) * (1 - Math.exp(-10 * dt));
            currentParallaxZ += (parallaxTiltZ - currentParallaxZ) * (1 - Math.exp(-10 * dt));

            targetRotX = clamp(orbitRotX + currentParallaxX, 18, 85);
            targetRotZ = orbitRotZ + currentParallaxZ;

            // 3. Fast-Tracking during Drag vs Smooth Damping on Release
            var rotFollowRate = isDragging ? (1 - Math.exp(-32 * dt)) : (1 - Math.exp(-12 * dt));
            currentRotX += (targetRotX - currentRotX) * rotFollowRate;
            currentRotZ += (targetRotZ - currentRotZ) * rotFollowRate;

            if (deckContainer) {
                deckContainer.style.transform = "rotateX(" + currentRotX.toFixed(2) + "deg) rotateZ(" + currentRotZ.toFixed(2) + "deg) translateY(-15px)";
            }

            // 4. 2nd-Order Critically-Damped Spring Dynamics for Slabs
            for (var i = 0; i < 4; i++) {
                var slab = slabs[i];
                if (!slab) continue;

                var spring = slabSprings[i];
                var target = (i === activeIndex) ? 1.0 : 0.0;

                // F = -k*x - c*v
                var accel = (target - spring.value) * SPRING_STIFFNESS - spring.velocity * SPRING_DAMPING;
                spring.velocity += accel * dt;
                spring.value += spring.velocity * dt;

                // Clean resting snap
                if (Math.abs(target - spring.value) < 0.001 && Math.abs(spring.velocity) < 0.001) {
                    spring.value = target;
                    spring.velocity = 0;
                }

                // Apply true isometric drawer extraction vector strictly matching R1 specification:
                // +Y (70px) pulls forward along isometric axis
                // +Z (28px) elevates slab above the stack
                // +X (75px) balances visual perspective convergence
                var pullY = spring.value * 70.0;
                var pullZ = spring.value * 28.0;
                var pullX = spring.value * 75.0;
                var scale = 1.0 + spring.value * 0.035;

                slab.style.setProperty("--pull-y", pullY.toFixed(2) + "px");
                slab.style.setProperty("--pull-z", pullZ.toFixed(2) + "px");
                slab.style.setProperty("--pull-x", pullX.toFixed(2) + "px");
                slab.style.setProperty("--scale", scale.toFixed(3));
            }

            requestAnimationFrame(physicsTick);
        }

        // Ignite the physics loop
        requestAnimationFrame(physicsTick);

        // ---------------------------------------------------------------------
        // Layer Activation & State Synchronization
        // ---------------------------------------------------------------------
        function setActiveLayer(idx) {
            activeIndex = idx;

            // 1. Update 3D Slabs Visual State
            layers.forEach(function (l, i) {
                var slab = slabs[i];
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
                    layerBadge.style.boxShadow = "0 0 14px " + layers[idx].color + "50";
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

        // ---------------------------------------------------------------------
        // Attach Listeners to Slabs and Summary Cards (with Drag Conflict Lock)
        // ---------------------------------------------------------------------
        layers.forEach(function (l, i) {
            var slab = slabs[i];
            var card = container.querySelector("#card-" + i);

            if (slab) {
                slab.addEventListener("mouseenter", function () {
                    if (isDragging) return; // Ignore hover while user is dragging orbit
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
                    if (isDragging) return;
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

        // ---------------------------------------------------------------------
        // Unified Pointer Drag Orbit & Inertia Physics Handlers
        // ---------------------------------------------------------------------
        if (stageCard) {
            stageCard.addEventListener("pointerdown", function (e) {
                if (e.button !== undefined && e.button !== 0) return;
                stopAutoTour();

                touchActive = false;
                touchId = null;
                pointerId = e.pointerId;
                downX = e.clientX;
                downY = e.clientY;
                lastX = e.clientX;
                lastY = e.clientY;
                lastTime = performance.now();

                velX = 0;
                velZ = 0;
                isDragging = false;

                if (stageCard.setPointerCapture) {
                    try { stageCard.setPointerCapture(e.pointerId); } catch (err) {}
                }
            });

            stageCard.addEventListener("pointermove", function (e) {
                if (pointerId !== null && e.pointerId === pointerId) {
                    var now = performance.now();
                    var dt = Math.max((now - lastTime) / 1000, 0.001);

                    var dx = e.clientX - lastX;
                    var dy = e.clientY - lastY;
                    var totalX = e.clientX - downX;
                    var totalY = e.clientY - downY;

                    if (!isDragging && Math.hypot(totalX, totalY) >= DRAG_THRESHOLD) {
                        isDragging = true;
                        stageCard.classList.add("is-dragging");
                    }

                    if (isDragging) {
                        var sens = (e.pointerType === "touch") ? 0.42 : 0.32;

                        // Immediate direct angular update (zero lag)
                        orbitRotZ += dx * sens;
                        orbitRotX -= dy * sens;
                        orbitRotX = clamp(orbitRotX, 18, 85);

                        // Track instantaneous velocity for smooth release momentum
                        velZ = (dx * sens) / dt;
                        velX = (-dy * sens) / dt;

                        lastX = e.clientX;
                        lastY = e.clientY;
                        lastTime = now;
                    }
                    return;
                }

                // Passive gentle parallax when hovering over stage
                if (!isDragging) {
                    var rect = stageCard.getBoundingClientRect();
                    var cx = rect.left + rect.width / 2;
                    var cy = rect.top + rect.height / 2;
                    var tiltX = (e.clientY - cy) / (rect.height / 2);
                    var tiltY = (e.clientX - cx) / (rect.width / 2);
                    parallaxTiltX = -tiltX * 4.5;
                    parallaxTiltZ = tiltY * 5.5;
                }
            });

            function endPointer(e) {
                if (pointerId !== null && e.pointerId === pointerId) {
                    // Tap detection: if not dragged beyond threshold, check if clicked on a slab
                    if (!isDragging) {
                        var targetSlab = e.target.closest ? e.target.closest(".slab-layer") : null;
                        if (targetSlab) {
                            var idxAttr = targetSlab.getAttribute("data-layer-idx");
                            if (idxAttr !== null) {
                                setActiveLayer(parseInt(idxAttr, 10));
                            }
                        }
                    }

                    isDragging = false;
                    pointerId = null;
                    stageCard.classList.remove("is-dragging");

                    if (stageCard.releasePointerCapture) {
                        try { stageCard.releasePointerCapture(e.pointerId); } catch (err) {}
                    }
                }
            }

            stageCard.addEventListener("pointerup", endPointer);
            stageCard.addEventListener("pointercancel", endPointer);

            stageCard.addEventListener("pointerleave", function (e) {
                if (!isDragging) {
                    parallaxTiltX = 0;
                    parallaxTiltZ = 0;
                }
            });

            // -----------------------------------------------------------------
            // Explicit Mobile Touch Handlers (Guaranteed Cross-Browser Support)
            // -----------------------------------------------------------------
            var touchActive = false;
            var touchId = null;

            function onTouchStart(e) {
                if (e.touches.length !== 1) return;
                stopAutoTour();
                if (pointerId !== null) return;

                var touch = e.touches[0];
                touchActive = true;
                touchId = touch.identifier;
                downX = touch.clientX;
                downY = touch.clientY;
                lastX = touch.clientX;
                lastY = touch.clientY;
                lastTime = performance.now();

                velX = 0;
                velZ = 0;
                isDragging = false;
            }

            function onTouchMove(e) {
                if (!touchActive || pointerId !== null) return;
                if (e._touchHandled) return;
                e._touchHandled = true;

                for (var i = 0; i < e.changedTouches.length; i++) {
                    var touch = e.changedTouches[i];
                    if (touch.identifier === touchId) {
                        var now = performance.now();
                        var dt = Math.max((now - lastTime) / 1000, 0.001);

                        var dx = touch.clientX - lastX;
                        var dy = touch.clientY - lastY;
                        var totalX = touch.clientX - downX;
                        var totalY = touch.clientY - downY;

                        if (!isDragging && Math.hypot(totalX, totalY) >= DRAG_THRESHOLD) {
                            isDragging = true;
                            stageCard.classList.add("is-dragging");
                        }

                        if (isDragging) {
                            var sens = 0.42;

                            orbitRotZ += dx * sens;
                            orbitRotX -= dy * sens;
                            orbitRotX = clamp(orbitRotX, 18, 85);

                            velZ = (dx * sens) / dt;
                            velX = (-dy * sens) / dt;

                            lastX = touch.clientX;
                            lastY = touch.clientY;
                            lastTime = now;
                        }
                        break;
                    }
                }
            }

            function onTouchEnd(e) {
                if (!touchActive) return;
                if (e._touchEndHandled) return;
                e._touchEndHandled = true;

                for (var i = 0; i < e.changedTouches.length; i++) {
                    var touch = e.changedTouches[i];
                    if (touch.identifier === touchId) {
                        if (!isDragging) {
                            var targetElem = document.elementFromPoint(touch.clientX, touch.clientY);
                            var targetSlab = targetElem && targetElem.closest ? targetElem.closest(".slab-layer") : null;
                            if (targetSlab) {
                                var idxAttr = targetSlab.getAttribute("data-layer-idx");
                                if (idxAttr !== null) {
                                    setActiveLayer(parseInt(idxAttr, 10));
                                }
                            }
                        }

                        isDragging = false;
                        touchActive = false;
                        touchId = null;
                        stageCard.classList.remove("is-dragging");
                        break;
                    }
                }
            }

            stageCard.addEventListener("touchstart", onTouchStart, { passive: true });
            stageCard.addEventListener("touchmove", onTouchMove, { passive: true });
            stageCard.addEventListener("touchend", onTouchEnd, { passive: true });
            stageCard.addEventListener("touchcancel", onTouchEnd, { passive: true });

            window.addEventListener("touchmove", onTouchMove, { passive: true });
            window.addEventListener("touchend", onTouchEnd, { passive: true });
            window.addEventListener("touchcancel", onTouchEnd, { passive: true });
        }

        // ---------------------------------------------------------------------
        // Action Controls (Explode, Reset, Auto Tour)
        // ---------------------------------------------------------------------
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

        if (btnResetView && deckContainer) {
            btnResetView.addEventListener("click", function () {
                stopAutoTour();
                orbitRotX = DEFAULT_ROT_X;
                orbitRotZ = DEFAULT_ROT_Z;
                parallaxTiltX = 0;
                parallaxTiltZ = 0;
                currentParallaxX = 0;
                currentParallaxZ = 0;
                velX = 0;
                velZ = 0;
                setActiveLayer(null);
            });
        }

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

        // Initialize Auto Tour to OFF so user has uninterrupted inspection
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

            var rafPending = false;
            var rotX = 0;
            var rotY = 0;

            function updateCardTilt() {
                card.style.transform = 'perspective(1000px) rotateX(' + rotX.toFixed(2) + 'deg) rotateY(' + rotY.toFixed(2) + 'deg) translateZ(10px)';
                rafPending = false;
            }

            card.addEventListener('mousemove', function (e) {
                var rect = card.getBoundingClientRect();
                var x = e.clientX - rect.left;
                var y = e.clientY - rect.top;
                var centerX = rect.width / 2;
                var centerY = rect.height / 2;
                rotX = ((y - centerY) / centerY) * -9;
                rotY = ((x - centerX) / centerX) * 9;

                if (!rafPending) {
                    rafPending = true;
                    requestAnimationFrame(updateCardTilt);
                }
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
