/**
 * Innoria Unified 3D Interactive Hero Banner Engine - Core Orchestrator
 * File: innoria_hero_3d_manager.js
 * Host Target: innoria.insilos.com (Insilos Sovereign Web Platform / Odoo 20)
 *
 * Architectural Invariants:
 * - 60 FPS Performance Budget | Strict Draw Call Budget <= 15 per route
 * - Clamped Device Pixel Ratio: Math.min(window.devicePixelRatio, 2.0)
 * - IntersectionObserver: 0% pause RAF, >= 15% resume RAF
 * - WebGL Context Lost & Restored Lifecycle Handlers
 * - Full GPU Memory Garbage Collection (Geometries, Materials, Textures)
 * - Multi-Scene Controller Polymorphism across 8 Flagship Routes
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['three'], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('three'));
    } else {
        root.InnoriaHero3DManager = factory(root.THREE || (root.InsilosThreeBundle && root.InsilosThreeBundle.THREE));
    }
}(typeof self !== 'undefined' ? self : this, function (THREE) {
    'use strict';

    if (!THREE) {
        console.error('[InnoriaHero3DManager] Fatal: Three.js library not detected in global scope.');
        return null;
    }

    // =========================================================================
    // 1. BRAND PALETTE & DEFAULT METRICS
    // =========================================================================
    var BRAND_PALETTE = {
        canvasBg: 0xFFFFFF,
        canvasIce: 0xF0F9FF,
        canvasSubtle: 0xF8FAFC,
        cyan: 0x0ABBDB,
        cyanRgb: '10, 187, 219',
        bluePrimary: 0x0284C7,
        blueDark: 0x0369A1,
        blueDeep: 0x075985,
        blueIce: 0xBAE6FD,
        orange: 0xFF8000,
        orangeDark: 0xEA580C,
        purple: 0x8B5CF6,
        green: 0x10B981,
        red: 0xEF4444,
        darkSpace: 0x070B14,
        textSlate: 0x0F172A
    };

    var ROUTE_SCENE_MAP = {
        '/': 'sovereign_core',
        '/about': 'ascending_heritage',
        '/platform': 'enterprise_brain',
        '/no-code-platform': 'builders_canvas',
        '/blockchain': 'immutable_ledger',
        '/solutions': 'smart_factory',
        '/industries': 'bionic_eye',
        '/contactus': 'global_advisory'
    };

    // Controller Class Registry
    var CONTROLLER_REGISTRY = new Map();

    // =========================================================================
    // 2. INNORIA HERO 3D MANAGER CLASS
    // =========================================================================
    function InnoriaHero3DManager(container, options) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        if (!this.container) {
            throw new Error('[InnoriaHero3DManager] Target container element not found.');
        }

        this.options = options || {};
        this.sceneId = this.container.getAttribute('data-3d-scene') ||
                       this.container.getAttribute('data-scene-id') ||
                       ROUTE_SCENE_MAP[this.container.getAttribute('data-route')] ||
                       'sovereign_core';

        this.themeMode = this.container.getAttribute('data-theme') ||
                         (this.sceneId === 'enterprise_brain' ? 'midnight_space' : 'white_blue');

        var dprAttr = parseFloat(this.container.getAttribute('data-dpr-clamp'));
        this.dprClamp = (!isNaN(dprAttr) && dprAttr > 0) ? dprAttr : 2.0;

        var fpsAttr = parseInt(this.container.getAttribute('data-fps-budget'), 10);
        this.targetFps = (!isNaN(fpsAttr) && fpsAttr > 0) ? fpsAttr : 60;

        this.interactiveMode = this.container.getAttribute('data-interactive-mode') || 'orbit';
        this.telemetryEnabled = this.container.getAttribute('data-telemetry-hud') !== 'false';

        // Core Three.js runtime properties
        this.canvas = null;
        this.renderer = null;
        this.activeController = null;
        this.clock = new THREE.Clock();
        this.animationFrameId = null;
        this.isPaused = false;
        this.isContextLost = false;
        this.isDisposed = false;

        // Pointer state & NDC coordinates [-1.0, 1.0]
        this.pointer = new THREE.Vector2(0, 0);
        this.targetPointer = new THREE.Vector2(0, 0);
        this.isPointerInside = false;

        // Telemetry stats
        this.telemetry = {
            fps: 60,
            frameTimeMs: 16.6,
            drawCalls: 0,
            triangles: 0,
            geometriesInMemory: 0,
            texturesInMemory: 0,
            activeNodeId: '',
            gpuTier: 'high'
        };

        this._lastTime = performance.now();
        this._frameCount = 0;
        this._fpsInterval = 500; // Recalculate every 500ms
        this._lastFpsUpdate = performance.now();

        // Event handler bindings for clean removal
        this._onPointerMove = this._onPointerMove.bind(this);
        this._onPointerLeave = this._onPointerLeave.bind(this);
        this._onPointerDown = this._onPointerDown.bind(this);
        this._onPointerUp = this._onPointerUp.bind(this);
        this._onWheel = this._onWheel.bind(this);
        this._onWindowResize = this._onWindowResize.bind(this);
        this._onContextLost = this._onContextLost.bind(this);
        this._onContextRestored = this._onContextRestored.bind(this);
        this._tick = this._tick.bind(this);

        this._init();
    }

    // =========================================================================
    // 3. INITIALIZATION & LIFECYCLE
    // =========================================================================
    InnoriaHero3DManager.prototype._init = function () {
        this._initCanvas();
        this._initRenderer();
        this._setupEvents();
        this._setupIntersectionObserver();
        this.loadScene(this.sceneId);
    };

    InnoriaHero3DManager.prototype._initCanvas = function () {
        var viewport = this.container.querySelector('.innoria-hero-3d-viewport') || this.container;
        this.viewportElement = viewport;

        var existingCanvas = viewport.querySelector('canvas.innoria-webgl-canvas') || viewport.querySelector('canvas');
        if (existingCanvas) {
            this.canvas = existingCanvas;
        } else {
            this.canvas = document.createElement('canvas');
            this.canvas.className = 'innoria-webgl-canvas w-100 h-100 d-block';
            this.canvas.setAttribute('aria-label', '3D Interactive Hero Canvas');
            viewport.appendChild(this.canvas);
        }

        // Style canvas to fill viewport smoothly without layout shifts
        this.canvas.style.display = 'block';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.outline = 'none';
    };

    InnoriaHero3DManager.prototype._initRenderer = function () {
        if (this.renderer) {
            try { this.renderer.dispose(); } catch (e) {}
        }

        var width = this.viewportElement.clientWidth || window.innerWidth;
        var height = this.viewportElement.clientHeight || window.innerHeight;
        var dpr = Math.min(window.devicePixelRatio || 1.0, this.dprClamp);

        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance',
            stencil: false,
            depth: true
        });

        this.renderer.setSize(width, height, false);
        this.renderer.setPixelRatio(dpr);

        // Tone Mapping & Color Encoding Standard
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.05;
        if (THREE.sRGBEncoding !== undefined) {
            this.renderer.outputEncoding = THREE.sRGBEncoding;
        }

        // Background color based on theme
        var clearColor = this.themeMode === 'midnight_space' ? BRAND_PALETTE.darkSpace : BRAND_PALETTE.canvasBg;
        var clearAlpha = this.themeMode === 'midnight_space' ? 1.0 : 0.0;
        this.renderer.setClearColor(clearColor, clearAlpha);
    };

    InnoriaHero3DManager.prototype._setupEvents = function () {
        var target = this.canvas;

        target.addEventListener('pointermove', this._onPointerMove, { passive: true });
        target.addEventListener('pointerleave', this._onPointerLeave, { passive: true });
        target.addEventListener('pointerdown', this._onPointerDown, { passive: false });
        target.addEventListener('pointerup', this._onPointerUp, { passive: true });
        target.addEventListener('wheel', this._onWheel, { passive: true });

        window.addEventListener('resize', this._onWindowResize, { passive: true });

        // WebGL Context Guard Handlers
        target.addEventListener('webglcontextlost', this._onContextLost, false);
        target.addEventListener('webglcontextrestored', this._onContextRestored, false);
    };

    InnoriaHero3DManager.prototype._setupIntersectionObserver = function () {
        if (!('IntersectionObserver' in window)) return;

        var self = this;
        var options = {
            root: null,
            threshold: [0, 0.05, 0.15, 0.5, 1.0]
        };

        this.visibilityObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.target === self.container) {
                    if (entry.isIntersecting && entry.intersectionRatio >= 0.15) {
                        self.resume();
                    } else if (!entry.isIntersecting || entry.intersectionRatio <= 0.02) {
                        self.pause();
                    }
                }
            });
        }, options);

        this.visibilityObserver.observe(this.container);
    };

    // =========================================================================
    // 4. SCENE CONTROLLER DISPATCH & SWITCHING
    // =========================================================================
    InnoriaHero3DManager.prototype.loadScene = function (sceneIdOrRoute, customConfig) {
        var sceneId = ROUTE_SCENE_MAP[sceneIdOrRoute] || sceneIdOrRoute || 'sovereign_core';
        var ControllerClass = CONTROLLER_REGISTRY.get(sceneId) || CONTROLLER_REGISTRY.get('sovereign_core');

        if (!ControllerClass) {
            console.warn('[InnoriaHero3DManager] Scene controller not yet registered for: ' + sceneId + '. Waiting for controllers bundle.');
            return Promise.resolve(null);
        }

        // Dispose previous controller if any
        if (this.activeController) {
            try {
                this.activeController.dispose();
            } catch (err) {
                console.error('[InnoriaHero3DManager] Error disposing active controller:', err);
            }
            this.activeController = null;
        }

        this.sceneId = sceneId;
        var config = Object.assign({
            sceneId: sceneId,
            routeId: this.container.getAttribute('data-route') || '/',
            themeMode: this.themeMode,
            dprClamping: this.dprClamp,
            targetFps: this.targetFps,
            interactiveMode: this.interactiveMode,
            telemetryEnabled: this.telemetryEnabled
        }, customConfig || {});

        var controllerInstance = new ControllerClass(this);
        this.activeController = controllerInstance;

        var self = this;
        return Promise.resolve(controllerInstance.init(this.canvas, config))
            .then(function () {
                self.handleResize();
                self.startLoop();
                console.info('[InnoriaHero3DManager] Scene "' + sceneId + '" initialized successfully.');
                return controllerInstance;
            })
            .catch(function (err) {
                console.error('[InnoriaHero3DManager] Failed to initialize scene "' + sceneId + '":', err);
            });
    };

    // =========================================================================
    // 5. ANIMATION LOOP & TELEMETRY
    // =========================================================================
    InnoriaHero3DManager.prototype.startLoop = function () {
        if (this.animationFrameId === null && !this.isDisposed && !this.isContextLost) {
            this.clock.start();
            this.isPaused = false;
            this._lastTime = performance.now();
            this._tick();
        }
    };

    InnoriaHero3DManager.prototype.stopLoop = function () {
        if (this.animationFrameId !== null) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    };

    InnoriaHero3DManager.prototype.pause = function () {
        if (!this.isPaused) {
            this.isPaused = true;
            this.stopLoop();
        }
    };

    InnoriaHero3DManager.prototype.resume = function () {
        if (this.isPaused && !this.isDisposed && !this.isContextLost) {
            this.isPaused = false;
            this.clock.start();
            this._lastTime = performance.now();
            this.startLoop();
        }
    };

    InnoriaHero3DManager.prototype._tick = function () {
        if (this.isPaused || this.isDisposed || this.isContextLost) {
            this.animationFrameId = null;
            return;
        }

        var now = performance.now();
        var frameInterval = 1000 / this.targetFps;
        var elapsedSinceLast = now - (this._lastRenderTime || 0);

        // Clamp rendering to target FPS budget (e.g. 60 FPS) to prevent GPU overload on 120Hz/144Hz displays
        if (elapsedSinceLast < frameInterval - 1.5) {
            this.animationFrameId = requestAnimationFrame(this._tick);
            return;
        }
        this._lastRenderTime = now - (elapsedSinceLast % frameInterval);

        var delta = Math.min(this.clock.getDelta(), 0.1); // Clamp delta to avoid leaps
        var elapsed = this.clock.getElapsedTime();

        // Smooth pointer interpolation
        this.pointer.x += (this.targetPointer.x - this.pointer.x) * 0.08;
        this.pointer.y += (this.targetPointer.y - this.pointer.y) * 0.08;

        if (this.activeController && this.activeController.scene && this.activeController.camera) {
            // Forward normalized coordinates to controller
            this.activeController.onPointerMove(this.pointer.x, this.pointer.y);
            this.activeController.update(delta, elapsed);

            // WebGL Render Call
            this.renderer.render(this.activeController.scene, this.activeController.camera);
        }

        // Telemetry & FPS Calculation
        this._frameCount++;
        if (now - this._lastFpsUpdate >= this._fpsInterval) {
            var actualFps = (this._frameCount * 1000) / (now - this._lastFpsUpdate);
            this.telemetry.fps = Math.round(actualFps * 10) / 10;
            this.telemetry.frameTimeMs = Math.round((1000 / actualFps) * 10) / 10;

            if (this.renderer && this.renderer.info) {
                this.telemetry.drawCalls = this.renderer.info.render.calls;
                this.telemetry.triangles = this.renderer.info.render.triangles;
                this.telemetry.geometriesInMemory = this.renderer.info.memory.geometries;
                this.telemetry.texturesInMemory = this.renderer.info.memory.textures;
            }

            this._updateHUD();
            this._frameCount = 0;
            this._lastFpsUpdate = now;
        }

        this.animationFrameId = requestAnimationFrame(this._tick);
    };

    InnoriaHero3DManager.prototype._updateHUD = function () {
        if (!this.telemetryEnabled) return;

        var drawsEl = document.getElementById('innoria_live_drawcalls');
        if (drawsEl) {
            drawsEl.textContent = 'Draws: ' + this.telemetry.drawCalls + '/15';
            if (this.telemetry.drawCalls > 15) {
                drawsEl.classList.remove('text-muted');
                drawsEl.classList.add('text-danger');
            } else {
                drawsEl.classList.remove('text-danger');
                drawsEl.classList.add('text-muted');
            }
        }

        var fpsEl = document.getElementById('innoria_live_fps');
        if (fpsEl) {
            fpsEl.textContent = this.telemetry.fps + ' FPS';
        }
    };

    // =========================================================================
    // 6. EVENT HANDLERS
    // =========================================================================
    InnoriaHero3DManager.prototype._onPointerMove = function (event) {
        var rect = this.canvas.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        var clientX = event.clientX;
        var clientY = event.clientY;

        // Map client coordinates to NDC [-1.0, 1.0]
        var normX = ((clientX - rect.left) / rect.width) * 2 - 1;
        var normY = -(((clientY - rect.top) / rect.height) * 2 - 1);

        this.targetPointer.set(normX, normY);
        this.isPointerInside = true;
    };

    InnoriaHero3DManager.prototype._onPointerLeave = function () {
        this.targetPointer.set(0, 0);
        this.isPointerInside = false;
    };

    InnoriaHero3DManager.prototype._onPointerDown = function (event) {
        if (!this.activeController) return;

        var rect = this.canvas.getBoundingClientRect();
        var normX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        var normY = -(((event.clientY - rect.top) / rect.height) * 2 - 1);

        this.activeController.onInteract({
            type: 'pointer_down',
            clientX: event.clientX,
            clientY: event.clientY,
            normalizedX: normX,
            normalizedY: normY
        });
    };

    InnoriaHero3DManager.prototype._onPointerUp = function (event) {
        if (!this.activeController) return;

        var rect = this.canvas.getBoundingClientRect();
        var normX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        var normY = -(((event.clientY - rect.top) / rect.height) * 2 - 1);

        this.activeController.onInteract({
            type: 'click',
            clientX: event.clientX,
            clientY: event.clientY,
            normalizedX: normX,
            normalizedY: normY
        });
    };

    InnoriaHero3DManager.prototype._onWheel = function (event) {
        if (!this.activeController) return;

        // Forward scroll/wheel event for scroll_scrub modes (e.g. Ascending Heritage)
        if (this.interactiveMode === 'scroll_scrub' || this.sceneId === 'ascending_heritage') {
            this.activeController.onInteract({
                type: 'scroll_progress',
                deltaY: event.deltaY,
                normalizedX: this.pointer.x,
                normalizedY: this.pointer.y
            });
        }
    };

    InnoriaHero3DManager.prototype._onWindowResize = function () {
        this.handleResize();
    };

    InnoriaHero3DManager.prototype.handleResize = function () {
        if (!this.viewportElement || !this.renderer) return;

        var width = this.viewportElement.clientWidth || window.innerWidth;
        var rawHeight = this.viewportElement.clientHeight || window.innerHeight;
        var height = rawHeight > 0 ? rawHeight : 1;
        var dpr = Math.min(window.devicePixelRatio || 1.0, this.dprClamp);

        this.renderer.setSize(width, height, false);
        this.renderer.setPixelRatio(dpr);

        if (this.activeController && typeof this.activeController.onResize === 'function') {
            this.activeController.onResize(width, height, dpr);
        }
    };

    InnoriaHero3DManager.prototype._onContextLost = function (event) {
        event.preventDefault();
        console.warn('[InnoriaHero3DManager] WebGL Context Lost! Pausing rendering loop.');
        this.isContextLost = true;
        this.stopLoop();
    };

    InnoriaHero3DManager.prototype._onContextRestored = function () {
        console.info('[InnoriaHero3DManager] WebGL Context Restored! Rebuilding scene.');
        this.isContextLost = false;
        this._initRenderer();
        this.clock.start();
        this.loadScene(this.sceneId);
    };

    // =========================================================================
    // 7. CLEANUP & DISPOSAL
    // =========================================================================
    InnoriaHero3DManager.prototype.dispose = function () {
        this.isDisposed = true;
        this.stopLoop();

        if (this.visibilityObserver) {
            this.visibilityObserver.disconnect();
            this.visibilityObserver = null;
        }

        if (this.canvas) {
            this.canvas.removeEventListener('pointermove', this._onPointerMove);
            this.canvas.removeEventListener('pointerleave', this._onPointerLeave);
            this.canvas.removeEventListener('pointerdown', this._onPointerDown);
            this.canvas.removeEventListener('pointerup', this._onPointerUp);
            this.canvas.removeEventListener('wheel', this._onWheel);
            this.canvas.removeEventListener('webglcontextlost', this._onContextLost);
            this.canvas.removeEventListener('webglcontextrestored', this._onContextRestored);
        }

        window.removeEventListener('resize', this._onWindowResize);

        if (this.activeController) {
            try {
                this.activeController.dispose();
            } catch (err) {
                console.error('[InnoriaHero3DManager] Error during controller disposal:', err);
            }
            this.activeController = null;
        }

        if (this.renderer) {
            try {
                this.renderer.dispose();
                if (this.renderer.forceContextLoss) {
                    this.renderer.forceContextLoss();
                }
            } catch (err) {}
            this.renderer = null;
        }

        InnoriaHero3DManager.instances.delete(this);
        console.info('[InnoriaHero3DManager] Successfully disposed with zero memory leak.');
    };

    // =========================================================================
    // 8. STATIC REGISTRY & AUTO-INIT
    // =========================================================================
    InnoriaHero3DManager.instances = new Set();

    InnoriaHero3DManager.registerController = function (sceneIdOrRoute, ControllerClass) {
        if (!sceneIdOrRoute || !ControllerClass) return;
        CONTROLLER_REGISTRY.set(sceneIdOrRoute, ControllerClass);

        // Notify any active instances waiting for this controller
        var mappedScene = ROUTE_SCENE_MAP[sceneIdOrRoute] || sceneIdOrRoute;
        InnoriaHero3DManager.instances.forEach(function (manager) {
            if (!manager.activeController && (manager.sceneId === mappedScene || manager.sceneId === sceneIdOrRoute)) {
                manager.loadScene(manager.sceneId);
            }
        });
    };

    InnoriaHero3DManager.getController = function (sceneIdOrRoute) {
        return CONTROLLER_REGISTRY.get(sceneIdOrRoute) || null;
    };

    InnoriaHero3DManager.autoInit = function () {
        if (typeof document === 'undefined') return;

        var roots = document.querySelectorAll('section.innoria-hero-root, .innoria-hero-3d-viewport, [data-3d-scene]');
        roots.forEach(function (rootEl) {
            var container = rootEl.classList.contains('innoria-hero-root') ? rootEl : rootEl.closest('section.innoria-hero-root') || rootEl;
            if (!container.__innoriaHeroManager) {
                try {
                    var manager = new InnoriaHero3DManager(container);
                    container.__innoriaHeroManager = manager;
                    InnoriaHero3DManager.instances.add(manager);
                } catch (err) {
                    console.error('[InnoriaHero3DManager] Auto-initialization error on container:', container, err);
                }
            }
        });
    };

    // Global Window Bridge
    if (typeof window !== 'undefined') {
        window.InnoriaHero3DManager = InnoriaHero3DManager;
        window.InnoriaHero3DBrandPalette = BRAND_PALETTE;

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', InnoriaHero3DManager.autoInit);
        } else {
            // Slight defer to allow DOM and controller scripts to finish executing
            setTimeout(InnoriaHero3DManager.autoInit, 0);
        }
    }

    return InnoriaHero3DManager;
}));
