/**
 * Innoria Unified Hero Breakthrough Interactive Stage & Scene Switcher
 * File: innoria_hero_interactive_stage.js
 * Host Target: innoria.insilos.com (Insilos Sovereign Web Platform / Odoo 20)
 *
 * Milestone 2 - Homepage Breakthrough Interactive Hero Stage
 *
 * 4 Dynamic Interactive Modes:
 * 0. cloud-fabric   - [Cloud & Data Fabric]
 * 1. ai-swarm       - [Autonomous AI Swarm]
 * 2. smart-erp      - [Intelligent ERP]
 * 3. trust-security - [Enterprise Trust & Security]
 *
 * Capabilities:
 * - 60 FPS High-Performance Three.js WebGL Stage with kinetic camera LERP transitions
 * - Dynamic particle field pulse bursts on mode switching
 * - Clamped Device Pixel Ratio: Math.min(window.devicePixelRatio, 2.0)
 * - Auto-pause when offscreen via IntersectionObserver (ratio <= 0.02)
 * - Seamless dual-buffered video crossfade blend
 * - Mode switcher crossfade with micro-interactions & progress line
 * - VIP CTA "Trải Nghiệm Live Proof-of-Concept 3 Giờ" smooth anchor to #innoria_contact_section
 * - Zero instructional text in DOM
 * - Backward compatibility with window.innoriaHeroSlider
 */

(function () {
    'use strict';

    var SCENE_MODES = [
        {
            index: 0,
            id: 'cloud-fabric',
            name: '[Cloud & Data Fabric]',
            nodeKey: 'DIGIFORCE',
            accent: '#00F0FF',
            glow: 'rgba(0, 240, 255, 0.4)',
            gradient: 'linear-gradient(135deg, #0ABBDB 0%, #00F0FF 100%)',
            camPos: { x: -3.8, y: 2.2, z: 13.5 },
            lookAt: { x: -1.0, y: 0.4, z: 0.0 },
            particleColor: 0x00F0FF
        },
        {
            index: 1,
            id: 'ai-swarm',
            name: '[Autonomous AI Swarm]',
            nodeKey: 'MOJO_AI',
            accent: '#FF8000',
            glow: 'rgba(255, 128, 0, 0.4)',
            gradient: 'linear-gradient(135deg, #FF8000 0%, #F59E0B 100%)',
            camPos: { x: 4.2, y: 2.6, z: 12.8 },
            lookAt: { x: 1.2, y: 0.6, z: 0.0 },
            particleColor: 0xFF8000
        },
        {
            index: 2,
            id: 'smart-erp',
            name: '[Intelligent ERP]',
            nodeKey: 'INTELLIGENT_ERP',
            accent: '#3B82F6',
            glow: 'rgba(59, 130, 246, 0.4)',
            gradient: 'linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)',
            camPos: { x: 0.0, y: 4.6, z: 14.8 },
            lookAt: { x: 0.0, y: -0.2, z: 0.0 },
            particleColor: 0x3B82F6
        },
        {
            index: 3,
            id: 'trust-security',
            name: '[Enterprise Trust & Security]',
            nodeKey: 'MOJOVERSE',
            accent: '#10B981',
            glow: 'rgba(16, 185, 129, 0.4)',
            gradient: 'linear-gradient(135deg, #10B981 0%, #00F5A0 100%)',
            camPos: { x: -3.2, y: -1.8, z: 13.0 },
            lookAt: { x: -0.8, y: -0.6, z: 0.0 },
            particleColor: 0x10B981
        }
    ];

    function InnoriaHeroInteractiveStage(container) {
        if (!container || container.__innoria_hero_stage_initialized) return;
        container.__innoria_hero_stage_initialized = true;

        this.container = container;
        this.videoLayers = Array.prototype.slice.call(container.querySelectorAll('.video-slide-layer'));
        this.slideItems = Array.prototype.slice.call(container.querySelectorAll('.hero-slide-item'));
        this.tabBtns = Array.prototype.slice.call(container.querySelectorAll('.hero-product-tab-btn, .hero-scene-nav-item'));
        this.progressFills = Array.prototype.slice.call(container.querySelectorAll('.tab-progress-fill'));
        this.ambientGlow = container.querySelector('#heroAmbientGlow');
        this.hudCounter = container.querySelector('#heroSlideCounter');
        this.prevBtn = container.querySelector('#heroPrevBtn');
        this.nextBtn = container.querySelector('#heroNextBtn');
        this.playPauseBtn = container.querySelector('#heroPlayPauseBtn');
        this.playPauseIcon = container.querySelector('#heroPlayPauseIcon');
        this.muteBtn = container.querySelector('#heroMuteBtn');
        this.muteIcon = container.querySelector('#heroMuteIcon');
        this.contentStage = container.querySelector('.hero-content-stage');
        this.viewport3D = container.querySelector('#heroInteractive3DStage, .innoria-hero-3d-viewport');
        this.canvas3D = container.querySelector('#heroInteractiveCanvas, canvas.innoria-webgl-canvas');

        this.totalSlides = 4;
        this.currentIndex = 0;
        this.slideDuration = 6500; // ms
        this.isPlaying = true;
        this.isMuted = true;
        this.isHoverPaused = false;
        this.isOffscreen = false;

        this.startTime = null;
        this.pausedProgress = 0;
        this.rafId = null;

        // Three.js 3D WebGL Engine Integration
        this.threeEngine = null;
        this.threeManager = null;

        this._initIntersectionObserver();
        this._init3DStage();
        this._initVideos();
        this._bindEvents();
        this.switchMode(0, true);
        this._startCycle();
    }

    // =========================================================================
    // 1. THREE.JS 3D WEBGL ENGINE INTEGRATION WITH 60 FPS LERP
    // =========================================================================
    InnoriaHeroInteractiveStage.prototype._init3DStage = function () {
        var self = this;
        var THREE = window.THREE || (window.InsilosThreeBundle && window.InsilosThreeBundle.THREE);

        // 1. Check if InnoriaHero3DManager already manages this or has an instance
        if (this.viewport3D && this.viewport3D.__innoriaHeroManager) {
            this.threeManager = this.viewport3D.__innoriaHeroManager;
            this.threeEngine = this.threeManager.activeController || this.threeManager;
            return;
        }

        // 2. If Three.js is available but no manager, hook or initialize lightweight single engine
        if (!THREE || !this.canvas3D) return;

        // If manager exists on window, attach
        if (window.InnoriaHero3DManager && window.InnoriaHero3DManager.instances && window.InnoriaHero3DManager.instances.size > 0) {
            var firstMgr = Array.from(window.InnoriaHero3DManager.instances)[0];
            if (firstMgr) {
                this.threeManager = firstMgr;
                this.threeEngine = firstMgr.activeController || firstMgr;
                return;
            }
        }

        // Standalone lightweight single-canvas 60 FPS renderer
        var width = this.viewport3D ? this.viewport3D.clientWidth : window.innerWidth;
        var height = this.viewport3D ? this.viewport3D.clientHeight : 820;
        if (!width) width = window.innerWidth;
        if (!height) height = 820;

        var dpr = Math.min(window.devicePixelRatio || 1.0, 2.0);

        var renderer;
        try {
            renderer = new THREE.WebGLRenderer({
                canvas: this.canvas3D,
                alpha: true,
                antialias: true,
                powerPreference: 'high-performance'
            });
        } catch (e) {
            return;
        }

        renderer.setSize(width, height);
        renderer.setPixelRatio(dpr);

        var scene = new THREE.Scene();
        var camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
        var initialMode = SCENE_MODES[0];
        camera.position.set(initialMode.camPos.x, initialMode.camPos.y, initialMode.camPos.z);
        var currentLookAt = new THREE.Vector3(initialMode.lookAt.x, initialMode.lookAt.y, initialMode.lookAt.z);
        camera.lookAt(currentLookAt);

        // Lighting Rig
        var ambLight = new THREE.AmbientLight(0x0A1424, 2.4);
        var mainPointLight = new THREE.PointLight(0x0ABBDB, 3.8, 30);
        mainPointLight.position.set(0, 2, 4);
        var dirLight = new THREE.DirectionalLight(0x00F2FE, 1.6);
        dirLight.position.set(8, 12, 10);
        scene.add(ambLight, mainPointLight, dirLight);

        // Parametric Core Group
        var coreGroup = new THREE.Group();
        var coreGeo = new THREE.TorusKnotGeometry(2.2, 0.28, 128, 24, 2, 3);
        var coreMat = new THREE.MeshStandardMaterial({
            color: 0x0ABBDB,
            emissive: 0x0284C7,
            emissiveIntensity: 0.65,
            metalness: 0.9,
            roughness: 0.15
        });
        var coreMesh = new THREE.Mesh(coreGeo, coreMat);
        coreGroup.add(coreMesh);
        scene.add(coreGroup);

        // Ambient Particle System
        var particleCount = 200;
        var particleGeo = new THREE.BufferGeometry();
        var particlePos = new Float32Array(particleCount * 3);
        for (var p = 0; p < particleCount; p++) {
            particlePos[p * 3] = (Math.random() - 0.5) * 26;
            particlePos[p * 3 + 1] = (Math.random() - 0.5) * 16;
            particlePos[p * 3 + 2] = (Math.random() - 0.5) * 20;
        }
        particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePos, 3));
        var particleMat = new THREE.PointsMaterial({
            color: 0x38BDF8,
            size: 0.08,
            transparent: true,
            opacity: 0.6
        });
        var particleSystem = new THREE.Points(particleGeo, particleMat);
        scene.add(particleSystem);

        this.threeEngine = {
            renderer: renderer,
            scene: scene,
            camera: camera,
            coreGroup: coreGroup,
            coreMat: coreMat,
            mainPointLight: mainPointLight,
            particleSystem: particleSystem,
            targetCamPos: new THREE.Vector3(initialMode.camPos.x, initialMode.camPos.y, initialMode.camPos.z),
            targetLookAt: currentLookAt.clone(),
            currentLookAt: currentLookAt.clone(),
            lerpSpeed: 0.06,
            lastTime: performance.now(),
            mouseOffset: { x: 0, y: 0 }
        };

        // Window resize
        window.addEventListener('resize', function () {
            if (!self.viewport3D || !self.threeEngine || !self.threeEngine.renderer) return;
            var w = self.viewport3D.clientWidth || window.innerWidth;
            var h = self.viewport3D.clientHeight || 820;
            self.threeEngine.camera.aspect = w / h;
            self.threeEngine.camera.updateProjectionMatrix();
            self.threeEngine.renderer.setSize(w, h);
            self.threeEngine.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1.0, 2.0));
        });

        // Mouse Parallax Micro-Interactions
        window.addEventListener('mousemove', function (e) {
            if (self.isOffscreen || !self.threeEngine || !self.threeEngine.mouseOffset) return;
            var nx = (e.clientX / window.innerWidth) * 2 - 1;
            var ny = -(e.clientY / window.innerHeight) * 2 + 1;
            self.threeEngine.mouseOffset.x = nx * 0.4;
            self.threeEngine.mouseOffset.y = ny * 0.3;
        });

        // Run Animation Loop
        function animate(now) {
            if (!self.isOffscreen && self.threeEngine && self.threeEngine.renderer) {
                var eng = self.threeEngine;
                var delta = Math.min((now - eng.lastTime) / 1000, 0.1);
                eng.lastTime = now;

                eng.coreGroup.rotation.y += delta * 0.22;
                eng.particleSystem.rotation.y += delta * 0.03;

                // Kinetic Camera LERP Transition
                var camTargetWithParallax = eng.targetCamPos.clone();
                camTargetWithParallax.x += eng.mouseOffset.x;
                camTargetWithParallax.y += eng.mouseOffset.y;

                eng.camera.position.lerp(camTargetWithParallax, eng.lerpSpeed);
                eng.currentLookAt.lerp(eng.targetLookAt, eng.lerpSpeed);
                eng.camera.lookAt(eng.currentLookAt);

                eng.renderer.render(eng.scene, eng.camera);
            }
            requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);
    };

    // =========================================================================
    // 2. INTERSECTION OBSERVER (AUTO-PAUSE WHEN OFFSCREEN)
    // =========================================================================
    InnoriaHeroInteractiveStage.prototype._initIntersectionObserver = function () {
        var self = this;
        if (!('IntersectionObserver' in window)) return;

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.intersectionRatio <= 0.02) {
                    self.isOffscreen = true;
                } else if (entry.intersectionRatio >= 0.10) {
                    self.isOffscreen = false;
                    self.startTime = performance.now();
                }
            });
        }, {
            threshold: [0.0, 0.02, 0.10, 0.25, 0.5]
        });

        observer.observe(this.container);
    };

    // =========================================================================
    // 3. VIDEO BACKGROUND INITIALIZATION
    // =========================================================================
    InnoriaHeroInteractiveStage.prototype._initVideos = function () {
        var self = this;
        this.videoLayers.forEach(function (video) {
            video.muted = self.isMuted;
            video.playsInline = true;
            video.loop = true;
            video.preload = 'auto';

            var playPromise = video.play();
            if (playPromise !== undefined) {
                playPromise.catch(function () {});
            }
        });
    };

    // =========================================================================
    // 4. MODE SWITCHING WITH CAMERA LERP & CONTENT CROSSFADE
    // =========================================================================
    InnoriaHeroInteractiveStage.prototype.switchMode = function (targetIdx, immediate) {
        if (targetIdx < 0) targetIdx = this.totalSlides - 1;
        if (targetIdx >= this.totalSlides) targetIdx = 0;

        this.currentIndex = targetIdx;
        var mode = SCENE_MODES[targetIdx] || SCENE_MODES[0];

        // 1. Crossfade Video Layers
        this.videoLayers.forEach(function (vid, idx) {
            if (idx === targetIdx) {
                vid.classList.add('active');
                if (vid.paused) {
                    try { vid.play().catch(function () {}); } catch (e) {}
                }
            } else {
                vid.classList.remove('active');
            }
        });

        // 2. Crossfade Slide Content Panes
        this.slideItems.forEach(function (slide, idx) {
            if (idx === targetIdx) {
                slide.classList.add('active');
            } else {
                slide.classList.remove('active');
            }
        });

        // 3. Update Ambient Glow
        if (this.ambientGlow) {
            this.ambientGlow.style.background = 'radial-gradient(circle, ' + mode.glow + ' 0%, transparent 70%)';
        }

        // 4. Update Navigation Tabs / Mode Switcher Buttons
        this.tabBtns.forEach(function (tab) {
            var tabIdx = parseInt(tab.getAttribute('data-tab-target'), 10);
            var sceneId = tab.getAttribute('data-scene-id');
            if (tabIdx === targetIdx || sceneId === mode.id) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // 5. Reset All Progress Bars
        this.progressFills.forEach(function (fill) {
            fill.style.width = '0%';
        });

        // 6. Update HUD Counter
        if (this.hudCounter) {
            var currStr = (targetIdx + 1) < 10 ? '0' + (targetIdx + 1) : (targetIdx + 1);
            var totalStr = this.totalSlides < 10 ? '0' + this.totalSlides : this.totalSlides;
            this.hudCounter.textContent = currStr + ' / ' + totalStr;
        }

        // 7. Kinetic 3D Camera LERP Transition & Controller Integration
        // Check if InnoriaHero3DManager / SovereignCoreController is active
        var activeController = null;
        if (this.threeManager && this.threeManager.activeController) {
            activeController = this.threeManager.activeController;
        } else if (window.InnoriaHero3DManager && window.InnoriaHero3DManager.instances && window.InnoriaHero3DManager.instances.size > 0) {
            var mgr = Array.from(window.InnoriaHero3DManager.instances)[0];
            if (mgr && mgr.activeController) activeController = mgr.activeController;
        }

        if (activeController && activeController.satelliteNodes && activeController.satelliteNodes.length > targetIdx) {
            var targetPod = activeController.satelliteNodes[targetIdx];
            if (targetPod && targetPod.userData && targetPod.userData.nodeData) {
                activeController.selectNode(targetPod, targetPod.userData.nodeData);
            }
        } else if (this.threeEngine && this.threeEngine.targetCamPos) {
            this.threeEngine.targetCamPos.set(mode.camPos.x, mode.camPos.y, mode.camPos.z);
            this.threeEngine.targetLookAt.set(mode.lookAt.x, mode.lookAt.y, mode.lookAt.z);
            if (this.threeEngine.coreMat) {
                this.threeEngine.coreMat.color.setHex(mode.particleColor);
                this.threeEngine.coreMat.emissive.setHex(mode.particleColor);
            }
        }

        // 8. Restart Progress Timer
        this.pausedProgress = 0;
        this.startTime = performance.now();
    };

    // Backward-compatible alias
    InnoriaHeroInteractiveStage.prototype.goToSlide = function (targetIdx, immediate) {
        this.switchMode(targetIdx, immediate);
    };

    InnoriaHeroInteractiveStage.prototype.nextSlide = function () {
        this.switchMode((this.currentIndex + 1) % this.totalSlides);
    };

    InnoriaHeroInteractiveStage.prototype.prevSlide = function () {
        this.switchMode((this.currentIndex - 1 + this.totalSlides) % this.totalSlides);
    };

    InnoriaHeroInteractiveStage.prototype.togglePlayPause = function () {
        this.isPlaying = !this.isPlaying;

        if (this.isPlaying) {
            this.startTime = performance.now();
            if (this.playPauseIcon) {
                this.playPauseIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-pause"/>';
            }
            if (this.playPauseBtn) this.playPauseBtn.title = 'Tạm dừng';
            var activeVideo = this.videoLayers[this.currentIndex];
            if (activeVideo && activeVideo.paused) {
                activeVideo.play().catch(function () {});
            }
            this._startCycle();
        } else {
            if (this.playPauseIcon) {
                this.playPauseIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-play"/>';
            }
            if (this.playPauseBtn) this.playPauseBtn.title = 'Tiếp tục phát';
            var currVideo = this.videoLayers[this.currentIndex];
            if (currVideo && !currVideo.paused) {
                currVideo.pause();
            }
        }
    };

    InnoriaHeroInteractiveStage.prototype.toggleMute = function () {
        this.isMuted = !this.isMuted;
        var self = this;

        this.videoLayers.forEach(function (video) {
            video.muted = self.isMuted;
        });

        if (this.muteIcon) {
            if (this.isMuted) {
                this.muteIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-speaker-slash"/>';
                if (this.muteBtn) this.muteBtn.title = 'Bật âm thanh';
            } else {
                this.muteIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-speaker-high"/>';
                if (this.muteBtn) this.muteBtn.title = 'Tắt âm thanh';
            }
        }
    };

    // =========================================================================
    // 5. PROGRESS BAR ANIMATION CYCLE
    // =========================================================================
    InnoriaHeroInteractiveStage.prototype._startCycle = function () {
        var self = this;
        if (this.rafId) cancelAnimationFrame(this.rafId);

        function tick(now) {
            if (!self.startTime) self.startTime = now;

            if (self.isPlaying && !self.isHoverPaused && !self.isOffscreen) {
                var elapsed = now - self.startTime + (self.pausedProgress * self.slideDuration);
                var progress = Math.min(elapsed / self.slideDuration, 1.0);

                var activeFill = self.container.querySelector('#tabProgress' + self.currentIndex);
                if (activeFill) {
                    activeFill.style.width = (progress * 100) + '%';
                }

                if (progress >= 1.0) {
                    self.nextSlide();
                    return;
                }
            }

            self.rafId = requestAnimationFrame(tick);
        }

        this.rafId = requestAnimationFrame(tick);
    };

    // =========================================================================
    // 6. EVENT LISTENERS & VIP CTA SMOOTH ANCHOR
    // =========================================================================
    InnoriaHeroInteractiveStage.prototype._bindEvents = function () {
        var self = this;

        // Mode Switcher Buttons
        this.tabBtns.forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                var targetIdx = parseInt(btn.getAttribute('data-tab-target'), 10);
                if (isNaN(targetIdx)) {
                    var sceneId = btn.getAttribute('data-scene-id');
                    var found = SCENE_MODES.find(function (m) { return m.id === sceneId; });
                    if (found) targetIdx = found.index;
                }
                if (!isNaN(targetIdx)) {
                    self.switchMode(targetIdx);
                }
            });
        });

        // HUD Controls
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', function (e) {
                e.preventDefault();
                self.prevSlide();
            });
        }

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', function (e) {
                e.preventDefault();
                self.nextSlide();
            });
        }

        if (this.playPauseBtn) {
            this.playPauseBtn.addEventListener('click', function (e) {
                e.preventDefault();
                self.togglePlayPause();
            });
        }

        if (this.muteBtn) {
            this.muteBtn.addEventListener('click', function (e) {
                e.preventDefault();
                self.toggleMute();
            });
        }

        // Reading Pause on Content Hover
        if (this.contentStage) {
            this.contentStage.addEventListener('mouseenter', function () {
                self.isHoverPaused = true;
            });
            this.contentStage.addEventListener('mouseleave', function () {
                self.isHoverPaused = false;
                self.startTime = performance.now();
            });
        }

        // VIP CTA Smooth Anchor to #innoria_contact_section with Context Population
        var vipButtons = this.container.querySelectorAll('.btn-hero-vip-poc, a[href="#innoria_contact_section"]');
        vipButtons.forEach(function (pocBtn) {
            pocBtn.addEventListener('click', function (e) {
                e.preventDefault();
                var targetSection = document.getElementById('innoria_contact_section') ||
                                    document.querySelector('#innoria_contact_section, .s_call_to_action');
                if (targetSection) {
                    targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

                    var activeMode = SCENE_MODES[self.currentIndex] || SCENE_MODES[0];
                    var contactInput = targetSection.querySelector('textarea, input[name="description"], input[name="subject"]');
                    if (contactInput && !contactInput.value) {
                        contactInput.value = 'Đăng ký Trải nghiệm Live Proof-of-Concept 3 Giờ: ' + activeMode.name;
                    }
                }
            });
        });

        // Keyboard Navigation
        window.addEventListener('keydown', function (e) {
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
            if (e.key === 'ArrowRight') {
                self.nextSlide();
            } else if (e.key === 'ArrowLeft') {
                self.prevSlide();
            }
        });
    };

    // Auto-Mount on DOM Ready
    function autoInitHeroInteractiveStage() {
        var heroEl = document.querySelector('#innoria_hero_cover, .innoria-hero-slider-section, .innoria-hero-interactive-stage');
        if (heroEl && !heroEl.__innoria_hero_stage_initialized) {
            var instance = new InnoriaHeroInteractiveStage(heroEl);
            window.innoriaHeroInteractiveStage = instance;
            window.innoriaHeroSlider = instance;
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoInitHeroInteractiveStage);
    } else {
        autoInitHeroInteractiveStage();
    }

    // Expose to window
    if (typeof window !== 'undefined') {
        window.InnoriaHeroInteractiveStage = InnoriaHeroInteractiveStage;
        window.INNORIA_SCENE_MODES = SCENE_MODES;
    }
})();
