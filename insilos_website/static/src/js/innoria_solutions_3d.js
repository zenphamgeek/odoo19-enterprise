/**
 * Innoria 3D Autonomous ERP Core Interactive Controller
 * File: enterprise/insilos_website/static/src/js/innoria_solutions_3d.js
 * Host Target: https://innoria.insilos.com/solutions
 *
 * Visualizes the 4 Core Pillars of Autonomous Enterprise:
 * 1) Autonomous Procurement & Demand Sensing (Tech Cyan #0ABBDB)
 * 2) Smart MES & Shop Floor Synchronization (Electric Blue #2563EB)
 * 3) Continuous Financial Audit & Triple-Entry Ledger (Vivid Emerald #10B981)
 * 4) Mojo AI Swarm Copilot (Deep Amber #D97706)
 *
 * Architecture:
 * - 60 FPS Frame-rate independent 2nd-order harmonic spring dynamics for slab drawer slide
 * - Isometric orbit inspection with pointer drag momentum and exponential decay damping
 * - Clean Light Minimalist design: 100% transparent container, zero card wrappers, zero borders
 * - Synchronized pillar telemetry chips and volumetric slab drawer states
 * - Exactly ZERO instructional text in DOM
 */

(function () {
    'use strict';

    var DRAG_THRESHOLD = 4;
    var SPRING_STIFFNESS = 180;
    var SPRING_DAMPING = 20;
    var ORBIT_FRICTION = 3.2;
    var MAX_DT = 0.0333; // 30 FPS floor for numerical integration stability

    var DEFAULT_ROT_X = 58;
    var DEFAULT_ROT_Z = -38;
    var MIN_ROT_X = 35;
    var MAX_ROT_X = 75;
    var MIN_ROT_Z = -80;
    var MAX_ROT_Z = 10;

    function clamp(val, min, max) {
        return Math.max(min, Math.min(max, val));
    }

    function initInnoriaSolutions3D(container) {
        if (!container || container.__innoria_solutions_3d_initialized) return;
        container.__innoria_solutions_3d_initialized = true;

        var viewport = container.querySelector('.erp-3d-scene-viewport');
        var deck = container.querySelector('#solutionsDeckContainer');
        var chips = container.querySelectorAll('.erp-pillar-chip');
        var slabs = [
            container.querySelector('#erp-slab-0'),
            container.querySelector('#erp-slab-1'),
            container.querySelector('#erp-slab-2'),
            container.querySelector('#erp-slab-3')
        ];

        if (!viewport || !deck) return;

        var activeIndex = 0; // Default active on top pillar (Procurement)
        var isDragging = false;
        var startPointerX = 0;
        var startPointerY = 0;
        var hasMoved = false;

        // Spring dynamics for 4 volumetric slabs (pull-out drawer progress: 0.0 -> 1.0)
        var slabSprings = [
            { value: 1.0, velocity: 0, target: 1.0 },
            { value: 0.0, velocity: 0, target: 0.0 },
            { value: 0.0, velocity: 0, target: 0.0 },
            { value: 0.0, velocity: 0, target: 0.0 }
        ];

        // Orbit rotation state
        var currentRotX = DEFAULT_ROT_X;
        var currentRotZ = DEFAULT_ROT_Z;
        var targetRotX = DEFAULT_ROT_X;
        var targetRotZ = DEFAULT_ROT_Z;
        var velRotX = 0;
        var velRotZ = 0;
        var lastPointerX = 0;
        var lastPointerY = 0;

        // Idle micro-animation time
        var idleClock = 0;

        function setActivePillar(index) {
            activeIndex = clamp(index, 0, 3);
            for (var i = 0; i < 4; i++) {
                slabSprings[i].target = (i === activeIndex) ? 1.0 : 0.0;
                if (slabs[i]) {
                    if (i === activeIndex) {
                        slabs[i].classList.add('pulled-out');
                        slabs[i].classList.remove('dimmed');
                    } else {
                        slabs[i].classList.remove('pulled-out');
                        slabs[i].classList.add('dimmed');
                    }
                }
            }

            chips.forEach(function (chip, idx) {
                if (idx === activeIndex) {
                    chip.classList.add('active');
                } else {
                    chip.classList.remove('active');
                }
            });
        }

        // Initialize default pillar state
        setActivePillar(0);

        // Pointer Events (Mobile Touch + Desktop Mouse unified)
        function onPointerDown(e) {
            isDragging = true;
            hasMoved = false;
            startPointerX = e.clientX;
            startPointerY = e.clientY;
            lastPointerX = e.clientX;
            lastPointerY = e.clientY;
            velRotX = 0;
            velRotZ = 0;

            if (viewport.setPointerCapture) {
                try {
                    viewport.setPointerCapture(e.pointerId);
                } catch (err) {
                    // Ignore capture errors on unsupported browsers
                }
            }
            viewport.classList.add('is-dragging');
        }

        function onPointerMove(e) {
            if (!isDragging) return;

            var dx = e.clientX - lastPointerX;
            var dy = e.clientY - lastPointerY;
            lastPointerX = e.clientX;
            lastPointerY = e.clientY;

            if (Math.abs(e.clientX - startPointerX) > DRAG_THRESHOLD || Math.abs(e.clientY - startPointerY) > DRAG_THRESHOLD) {
                hasMoved = true;
            }

            // Sensible rotation speed: horizontal drags orbit Z, vertical drags pitch X
            var sensitivity = 0.35;
            targetRotZ += dx * sensitivity;
            targetRotX -= dy * sensitivity;

            targetRotX = clamp(targetRotX, MIN_ROT_X, MAX_ROT_X);
            targetRotZ = clamp(targetRotZ, MIN_ROT_Z, MAX_ROT_Z);

            velRotZ = dx * 12;
            velRotX = -dy * 12;
        }

        function onPointerUp(e) {
            if (!isDragging) return;
            isDragging = false;
            viewport.classList.remove('is-dragging');

            if (viewport.releasePointerCapture) {
                try {
                    viewport.releasePointerCapture(e.pointerId);
                } catch (err) {
                    // Ignore
                }
            }
        }

        viewport.addEventListener('pointerdown', onPointerDown);
        viewport.addEventListener('pointermove', onPointerMove);
        viewport.addEventListener('pointerup', onPointerUp);
        viewport.addEventListener('pointercancel', onPointerUp);

        // Slab hover and click bindings
        slabs.forEach(function (slab, idx) {
            if (!slab) return;

            slab.addEventListener('pointerenter', function () {
                if (!isDragging) {
                    setActivePillar(idx);
                }
            });

            slab.addEventListener('click', function (e) {
                if (!hasMoved) {
                    e.stopPropagation();
                    setActivePillar(idx);
                }
            });
        });

        // HUD Chip bindings
        chips.forEach(function (chip, idx) {
            chip.addEventListener('click', function (e) {
                e.preventDefault();
                setActivePillar(idx);
            });
        });

        // 60 FPS Physics Simulation Loop
        var lastTime = performance.now();

        function physicsTick(now) {
            var dt = (now - lastTime) / 1000;
            lastTime = now;
            dt = Math.min(dt, MAX_DT);

            // Orbit Inertia & Damping
            if (!isDragging) {
                if (Math.abs(velRotX) > 0.01 || Math.abs(velRotZ) > 0.01) {
                    targetRotX += velRotX * dt;
                    targetRotZ += velRotZ * dt;
                    targetRotX = clamp(targetRotX, MIN_ROT_X, MAX_ROT_X);
                    targetRotZ = clamp(targetRotZ, MIN_ROT_Z, MAX_ROT_Z);

                    velRotX -= velRotX * ORBIT_FRICTION * dt;
                    velRotZ -= velRotZ * ORBIT_FRICTION * dt;
                } else {
                    // Gentle subtle idle sway
                    idleClock += dt;
                    var idleOffsetZ = Math.sin(idleClock * 0.8) * 1.8;
                    var idleOffsetX = Math.cos(idleClock * 0.6) * 0.9;
                    targetRotX = DEFAULT_ROT_X + idleOffsetX;
                    targetRotZ = DEFAULT_ROT_Z + idleOffsetZ;
                }
            }

            // Smooth rotational LERP
            var rotLerpRate = isDragging ? 18 : 6;
            currentRotX += (targetRotX - currentRotX) * Math.min(rotLerpRate * dt, 1.0);
            currentRotZ += (targetRotZ - currentRotZ) * Math.min(rotLerpRate * dt, 1.0);

            // Apply deck rotation
            deck.style.transform = 'rotateX(' + currentRotX.toFixed(2) + 'deg) rotateZ(' + currentRotZ.toFixed(2) + 'deg)';

            // 2nd-order harmonic spring for slab drawer extraction
            for (var i = 0; i < 4; i++) {
                var s = slabSprings[i];
                var force = -SPRING_STIFFNESS * (s.value - s.target) - SPRING_DAMPING * s.velocity;
                s.velocity += force * dt;
                s.value += s.velocity * dt;

                // Drawer vector: +X forward, +Y forward along isometric axis, +Z slight lift
                var pullX = s.value * 68;
                var pullY = s.value * 64;
                var pullZ = s.value * 22;

                if (slabs[i]) {
                    slabs[i].style.setProperty('--pull-x', pullX.toFixed(2) + 'px');
                    slabs[i].style.setProperty('--pull-y', pullY.toFixed(2) + 'px');
                    slabs[i].style.setProperty('--pull-z', pullZ.toFixed(2) + 'px');
                }
            }

            requestAnimationFrame(physicsTick);
        }

        requestAnimationFrame(physicsTick);
    }

    // Auto-mount on DOM ready or Odoo Website loading
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            document.querySelectorAll('.s_innoria_3d_solutions_erp, .innoria-solutions-3d-stage').forEach(initInnoriaSolutions3D);
        });
    } else {
        document.querySelectorAll('.s_innoria_3d_solutions_erp, .innoria-solutions-3d-stage').forEach(initInnoriaSolutions3D);
    }

    // Expose to window for dynamic view injection or Odoo frontend re-render
    if (typeof window !== 'undefined') {
        window.initInnoriaSolutions3D = initInnoriaSolutions3D;
    }
})();
