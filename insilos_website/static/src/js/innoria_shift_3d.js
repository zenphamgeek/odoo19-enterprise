/**
 * Innoria 3D ERP Shift: Legacy vs AI Comparison Engine
 * File: enterprise/insilos_website/static/src/js/innoria_shift_3d.js
 * Host Target: https://innoria.insilos.com/solutions
 *
 * Scenarios:
 * 1) Speed & Throughput: 48h Batch Queue vs < 1.2s Real-Time Event Bus
 * 2) Learning Curve & Intent: 450+ T-Codes (3 Months) vs Conversational Copilot (Zero Training)
 * 3) Accuracy & Integrity: 4.2% Manual Rekeying Error vs 99.98% Autonomous 3-Way Match
 * 4) Sovereign TCO: High CapEx Consulting Drag vs -65% Operating Drag & Pure Independence
 *
 * Architecture:
 * - 60 FPS 2nd-order harmonic spring dynamics for volumetric tier extraction
 * - Dual-Core 3D Isometric Viewport with momentum drag-orbit & exponential decay damping
 * - Mode Switcher: "legacy", "dual" (default), "ai"
 * - 2-Way Bidirectional Synchronization between 3D scene and comparison table
 * - 100% Transparent container, zero card wrappers, zero borders, zero instructional text
 */

(function () {
    'use strict';

    var DRAG_THRESHOLD = 5;
    var SPRING_STIFFNESS = 180;
    var SPRING_DAMPING = 22;
    var ORBIT_FRICTION = 3.6;
    var MAX_DT = 0.0333;

    var DEFAULT_ROT_X = 56;
    var DEFAULT_ROT_Z = -34;
    var MIN_ROT_X = 30;
    var MAX_ROT_X = 75;
    var MIN_ROT_Z = -80;
    var MAX_ROT_Z = 15;

    var METRIC_TELEMETRY = {
        speed: {
            text: 'TỐC ĐỘ: 48h Batch Queue ➔ Real-Time Event Bus (< 1.2s)',
            accent: '#0ABBDB'
        },
        learning: {
            text: 'ĐÀO TẠO: 450+ T-Codes (3 Tháng) ➔ Conversational Copilot (0 Giờ)',
            accent: '#2563EB'
        },
        error: {
            text: 'TỶ LỆ LỖI: 4.2% Sai Sót Gõ Tay ➔ 99.98% Autonomous 3-Way Match',
            accent: '#10B981'
        },
        tco: {
            text: 'TCO & VẬN HÀNH: Khóa License Cứng ➔ Giảm 65% Chi Phí TCO Tự Chủ',
            accent: '#D97706'
        }
    };

    var METRICS_ORDER = ['speed', 'learning', 'error', 'tco'];

    function clamp(val, min, max) {
        return Math.max(min, Math.min(max, val));
    }

    function initInnoriaShift3D(container) {
        if (!container || container.__innoria_shift_3d_initialized) return;
        container.__innoria_shift_3d_initialized = true;

        var viewport = container.querySelector('.erp-shift-viewport');
        var deck = container.querySelector('#erpShiftDeck');
        var legacyCore = container.querySelector('#shift-core-legacy');
        var aiCore = container.querySelector('#shift-core-ai');
        var telemetryChip = container.querySelector('#shiftTelemetryChip');
        var telemetryText = container.querySelector('#shiftTelemetryText');

        var parentSection = container.closest('section') || document;
        var modeBtns = parentSection.querySelectorAll('.shift-mode-btn');
        var tableRows = parentSection.querySelectorAll('.shift-table-row');

        var aiTiers = {
            speed: container.querySelector('#shift-tier-speed'),
            learning: container.querySelector('#shift-tier-learning'),
            error: container.querySelector('#shift-tier-error'),
            tco: container.querySelector('#shift-tier-tco')
        };

        var conduits = {
            speed: container.querySelector('.conduit-stream.stream-speed'),
            learning: container.querySelector('.conduit-stream.stream-learning'),
            error: container.querySelector('.conduit-stream.stream-error'),
            tco: container.querySelector('.conduit-stream.stream-tco')
        };

        if (!viewport || !deck) return;

        var currentMode = 'dual'; // 'legacy', 'dual', 'ai'
        var activeMetric = 'speed';
        var isDragging = false;
        var isHovering = false;
        var startPointerX = 0;
        var startPointerY = 0;
        var lastPointerX = 0;
        var lastPointerY = 0;
        var hasMoved = false;
        var hoverDebounceTimer = null;

        // Springs for the 4 tiers of Innoria AI fabric
        var tierSprings = {
            speed: { value: 1.0, velocity: 0, target: 1.0 },
            learning: { value: 0.0, velocity: 0, target: 0.0 },
            error: { value: 0.0, velocity: 0, target: 0.0 },
            tco: { value: 0.0, velocity: 0, target: 0.0 }
        };

        // Rotation & Camera Lerp
        var currentRotX = DEFAULT_ROT_X;
        var currentRotZ = DEFAULT_ROT_Z;
        var targetRotX = DEFAULT_ROT_X;
        var targetRotZ = DEFAULT_ROT_Z;
        var velRotX = 0;
        var velRotZ = 0;
        var idleClock = 0;

        // 1. Set Active Metric (Bi-directionally synced with Table & 3D)
        function setActiveMetric(metricKey) {
            if (!METRIC_TELEMETRY[metricKey]) return;
            activeMetric = metricKey;

            // Update Spring targets
            METRICS_ORDER.forEach(function (m) {
                tierSprings[m].target = (m === activeMetric) ? 1.0 : 0.0;
                var tierEl = aiTiers[m];
                var conduitEl = conduits[m];

                if (tierEl) {
                    if (m === activeMetric) {
                        tierEl.classList.add('pulled-out');
                        tierEl.classList.remove('dimmed');
                    } else {
                        tierEl.classList.remove('pulled-out');
                        tierEl.classList.add('dimmed');
                    }
                }

                if (conduitEl) {
                    if (m === activeMetric) {
                        conduitEl.classList.add('active');
                    } else {
                        conduitEl.classList.remove('active');
                    }
                }
            });

            // Update Table Row Highlights
            tableRows.forEach(function (row) {
                var rowMetric = row.getAttribute('data-metric');
                if (rowMetric === activeMetric) {
                    row.classList.add('table-row-active');
                } else {
                    row.classList.remove('table-row-active');
                }
            });

            // Update Telemetry Badge
            if (telemetryText && METRIC_TELEMETRY[activeMetric]) {
                telemetryText.textContent = METRIC_TELEMETRY[activeMetric].text;
            }
            if (telemetryChip && METRIC_TELEMETRY[activeMetric]) {
                telemetryChip.style.borderColor = METRIC_TELEMETRY[activeMetric].accent;
                telemetryChip.style.boxShadow = '0 0 16px ' + METRIC_TELEMETRY[activeMetric].accent + '40';
            }
        }

        // 2. Set Active Mode ('legacy', 'dual', 'ai')
        function setShiftMode(mode) {
            currentMode = mode;
            deck.setAttribute('data-active-mode', mode);

            modeBtns.forEach(function (btn) {
                if (btn.getAttribute('data-shift-mode') === mode) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            if (mode === 'legacy') {
                targetRotX = 52;
                targetRotZ = -18;
                if (legacyCore) legacyCore.classList.add('focus-core');
                if (aiCore) aiCore.classList.remove('focus-core');
            } else if (mode === 'ai') {
                targetRotX = 60;
                targetRotZ = -48;
                if (aiCore) aiCore.classList.add('focus-core');
                if (legacyCore) legacyCore.classList.remove('focus-core');
            } else {
                targetRotX = DEFAULT_ROT_X;
                targetRotZ = DEFAULT_ROT_Z;
                if (legacyCore) legacyCore.classList.remove('focus-core');
                if (aiCore) aiCore.classList.remove('focus-core');
            }

            // Sync with parent table styling
            if (parentSection) {
                parentSection.classList.remove('mode-focus-legacy', 'mode-focus-ai', 'mode-focus-dual');
                parentSection.classList.add('mode-focus-' + mode);
            }
        }

        // Initialize default active state
        setActiveMetric('speed');
        setShiftMode('dual');

        // Mode switch buttons
        modeBtns.forEach(function (btn) {
            function triggerMode(e) {
                if (e) e.preventDefault();
                var mode = btn.getAttribute('data-shift-mode');
                if (mode) setShiftMode(mode);
            }
            btn.addEventListener('click', triggerMode);
            btn.addEventListener('pointerup', triggerMode);
        });

        // Comparison Table Rows Click & Hover bindings
        tableRows.forEach(function (row) {
            var m = row.getAttribute('data-metric');
            if (!m) return;

            function trigger(e) {
                setActiveMetric(m);
            }

            row.addEventListener('click', trigger);
            row.addEventListener('mouseenter', trigger);
            row.querySelectorAll('td').forEach(function (cell) {
                cell.addEventListener('click', trigger);
            });
        });

        // 3D Pointer Orbit Drag & Tap
        function onPointerDown(e) {
            if (e.button !== undefined && e.button !== 0) return;
            isDragging = false;
            hasMoved = false;
            startPointerX = e.clientX;
            startPointerY = e.clientY;
            lastPointerX = e.clientX;
            lastPointerY = e.clientY;
            velRotX = 0;
            velRotZ = 0;

            if (viewport.setPointerCapture) {
                try { viewport.setPointerCapture(e.pointerId); } catch (err) {}
            }
        }

        function onPointerMove(e) {
            var totalDx = e.clientX - startPointerX;
            var totalDy = e.clientY - startPointerY;

            if (!isDragging && Math.hypot(totalDx, totalDy) >= DRAG_THRESHOLD) {
                isDragging = true;
                hasMoved = true;
                viewport.classList.add('is-dragging');
            }

            if (isDragging) {
                var dx = e.clientX - lastPointerX;
                var dy = e.clientY - lastPointerY;
                lastPointerX = e.clientX;
                lastPointerY = e.clientY;

                var sensitivity = (e.pointerType === 'touch') ? 0.42 : 0.32;
                targetRotZ += dx * sensitivity;
                targetRotX -= dy * sensitivity;

                targetRotX = clamp(targetRotX, MIN_ROT_X, MAX_ROT_X);
                targetRotZ = clamp(targetRotZ, MIN_ROT_Z, MAX_ROT_Z);

                velRotZ = dx * 12;
                velRotX = -dy * 12;
            }
        }

        function onPointerUp(e) {
            if (viewport.releasePointerCapture) {
                try { viewport.releasePointerCapture(e.pointerId); } catch (err) {}
            }
            viewport.classList.remove('is-dragging');

            // Tap detection on 3D elements
            if (!hasMoved) {
                var elem = document.elementFromPoint(e.clientX, e.clientY);
                if (elem) {
                    var tierEl = elem.closest('.shift-tier-layer');
                    if (tierEl) {
                        var metric = tierEl.getAttribute('data-metric');
                        if (metric) setActiveMetric(metric);
                    } else if (elem.closest('#shift-core-legacy')) {
                        setShiftMode('legacy');
                    } else if (elem.closest('#shift-core-ai')) {
                        setShiftMode('ai');
                    }
                }
            }

            isDragging = false;
        }

        viewport.addEventListener('pointerdown', onPointerDown);
        viewport.addEventListener('pointermove', onPointerMove);
        viewport.addEventListener('pointerup', onPointerUp);
        viewport.addEventListener('pointercancel', onPointerUp);

        viewport.addEventListener('pointerenter', function () {
            isHovering = true;
        });
        viewport.addEventListener('pointerleave', function () {
            isHovering = false;
            clearTimeout(hoverDebounceTimer);
        });

        // 3D Tiers Hover & Click
        Object.keys(aiTiers).forEach(function (m) {
            var tier = aiTiers[m];
            if (!tier) return;

            tier.addEventListener('pointerenter', function () {
                tier.classList.add('tier-hovered');
                if (!isDragging) {
                    clearTimeout(hoverDebounceTimer);
                    hoverDebounceTimer = setTimeout(function () {
                        if (!isDragging && tier.classList.contains('tier-hovered')) {
                            setActiveMetric(m);
                        }
                    }, 120);
                }
            });

            tier.addEventListener('pointerleave', function () {
                tier.classList.remove('tier-hovered');
                clearTimeout(hoverDebounceTimer);
            });

            tier.addEventListener('click', function (e) {
                if (!hasMoved) {
                    e.stopPropagation();
                    clearTimeout(hoverDebounceTimer);
                    setActiveMetric(m);
                }
            });
        });

        // 60 FPS Physics Simulation Loop
        var lastTime = performance.now();

        function physicsTick(now) {
            var dt = (now - lastTime) / 1000;
            lastTime = now;
            dt = Math.min(dt > 0 ? dt : 0.016, MAX_DT);

            // Orbit Inertia & Damping
            if (!isDragging) {
                if (Math.abs(velRotX) > 0.01 || Math.abs(velRotZ) > 0.01) {
                    targetRotX += velRotX * dt;
                    targetRotZ += velRotZ * dt;
                    targetRotX = clamp(targetRotX, MIN_ROT_X, MAX_ROT_X);
                    targetRotZ = clamp(targetRotZ, MIN_ROT_Z, MAX_ROT_Z);

                    velRotX -= velRotX * ORBIT_FRICTION * dt;
                    velRotZ -= velRotZ * ORBIT_FRICTION * dt;
                } else if (!isHovering) {
                    // Gentle subtle idle sway when resting
                    idleClock += dt;
                    var idleOffsetZ = Math.sin(idleClock * 0.75) * 1.4;
                    var idleOffsetX = Math.cos(idleClock * 0.55) * 0.7;
                    targetRotX = (currentMode === 'legacy' ? 52 : (currentMode === 'ai' ? 60 : DEFAULT_ROT_X)) + idleOffsetX;
                    targetRotZ = (currentMode === 'legacy' ? -18 : (currentMode === 'ai' ? -48 : DEFAULT_ROT_Z)) + idleOffsetZ;
                }
            }

            // Smooth rotational LERP
            var rotLerpRate = isDragging ? 18 : 8;
            currentRotX += (targetRotX - currentRotX) * Math.min(rotLerpRate * dt, 1.0);
            currentRotZ += (targetRotZ - currentRotZ) * Math.min(rotLerpRate * dt, 1.0);

            // Apply deck rotation
            deck.style.transform = 'rotateX(' + currentRotX.toFixed(2) + 'deg) rotateZ(' + currentRotZ.toFixed(2) + 'deg)';

            // 2nd-order harmonic spring for each tier extraction
            METRICS_ORDER.forEach(function (m) {
                var s = tierSprings[m];
                var force = -SPRING_STIFFNESS * (s.value - s.target) - SPRING_DAMPING * s.velocity;
                s.velocity += force * dt;
                s.value += s.velocity * dt;

                if (Math.abs(s.target - s.value) < 0.001 && Math.abs(s.velocity) < 0.001) {
                    s.value = s.target;
                    s.velocity = 0;
                }

                // Drawer vector along isometric axis
                var pullX = s.value * 52;
                var pullY = s.value * 48;
                var pullZ = s.value * 18;

                var tierEl = aiTiers[m];
                if (tierEl) {
                    tierEl.style.setProperty('--pull-x', pullX.toFixed(2) + 'px');
                    tierEl.style.setProperty('--pull-y', pullY.toFixed(2) + 'px');
                    tierEl.style.setProperty('--pull-z', pullZ.toFixed(2) + 'px');
                }
            });

            requestAnimationFrame(physicsTick);
        }

        requestAnimationFrame(physicsTick);
    }

    // Auto-mount
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            document.querySelectorAll('.s_innoria_3d_erp_shift, .innoria-shift-3d-stage').forEach(initInnoriaShift3D);
        });
    } else {
        document.querySelectorAll('.s_innoria_3d_erp_shift, .innoria-shift-3d-stage').forEach(initInnoriaShift3D);
    }

    if (typeof window !== 'undefined') {
        window.initInnoriaShift3D = initInnoriaShift3D;
    }
})();
