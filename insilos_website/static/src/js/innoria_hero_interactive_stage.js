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
            camPos: { x: 0.0, y: 3.5, z: 15.0 },
            lookAt: { x: 0.0, y: 0.0, z: 0.0 },
            fov: 55,
            particleColor: 0x42E6C3,
            morphState: 0
        },
        {
            index: 1,
            id: 'ai-swarm',
            name: '[Autonomous AI Swarm]',
            nodeKey: 'MOJO_AI',
            accent: '#FF8000',
            glow: 'rgba(255, 128, 0, 0.4)',
            gradient: 'linear-gradient(135deg, #FF8000 0%, #F59E0B 100%)',
            camPos: { x: 3.8, y: 2.0, z: 11.5 },
            lookAt: { x: 0.0, y: 0.2, z: 0.0 },
            fov: 40,
            particleColor: 0x00F2FE,
            morphState: 1
        },
        {
            index: 2,
            id: 'smart-erp',
            name: '[INSILOS ERP]',
            nodeKey: 'INSILOS',
            accent: '#00F0FF',
            glow: 'rgba(0, 240, 255, 0.4)',
            gradient: 'linear-gradient(135deg, #0284C7 0%, #00F0FF 100%)',
            camPos: { x: 0.0, y: 4.5, z: 14.0 },
            lookAt: { x: 0.0, y: 0.0, z: 0.0 },
            fov: 35,
            particleColor: 0x0284C7,
            morphState: 2
        },
        {
            index: 3,
            id: 'trust-security',
            name: '[ZENCODE-ENT Sovereign OS]',
            nodeKey: 'ZENCODE_ENT',
            accent: '#42E6C3',
            glow: 'rgba(66, 230, 195, 0.4)',
            gradient: 'linear-gradient(135deg, #10B981 0%, #42E6C3 100%)',
            camPos: { x: -3.0, y: -1.5, z: 12.0 },
            lookAt: { x: -0.5, y: -0.2, z: 0.0 },
            fov: 45,
            particleColor: 0x42E6C3,
            morphState: 3
        }
    ];

    function InnoriaHeroInteractiveStage(container) {
        if (!container || container.__innoria_hero_stage_initialized || container.__innoria_hero_slider_initialized) return;
        container.__innoria_hero_stage_initialized = true;
        container.__innoria_hero_slider_initialized = true;

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

        // 2. If Three.js is available but no manager, hook or initialize full engine
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

        // 3. Mathematical Wave & Morphing Engine Constants
        var MAX_PARTICLES = 3600; // 60 x 60 grid
        var GRID_COLS = 60;
        var GRID_ROWS = 60;
        var width = this.viewport3D ? this.viewport3D.clientWidth : window.innerWidth;
        var height = this.viewport3D ? this.viewport3D.clientHeight : 820;
        if (!width) width = window.innerWidth || 1440;
        if (!height) height = 820;

        var dpr = Math.min(window.devicePixelRatio || 1.0, 2.0);

        var renderer;
        try {
            renderer = new THREE.WebGLRenderer({
                canvas: this.canvas3D,
                alpha: true,
                antialias: true,
                powerPreference: 'high-performance',
                stencil: false,
                depth: true
            });
        } catch (e) {
            console.error('[InnoriaHeroInteractiveStage] WebGL initialization failed:', e);
            return;
        }

        renderer.setSize(width, height, false);
        renderer.setPixelRatio(dpr);
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.05;

        var scene = new THREE.Scene();
        var initialMode = SCENE_MODES[0];
        var camera = new THREE.PerspectiveCamera(initialMode.fov || 55, width / height, 0.1, 1000);
        camera.position.set(initialMode.camPos.x, initialMode.camPos.y, initialMode.camPos.z);
        var currentLookAt = new THREE.Vector3(initialMode.lookAt.x, initialMode.lookAt.y, initialMode.lookAt.z);
        camera.lookAt(currentLookAt);

        // Lighting Rig
        var ambLight = new THREE.AmbientLight(0x0A1424, 2.4);
        var mainPointLight = new THREE.PointLight(0x0ABBDB, 3.8, 30);
        mainPointLight.position.set(0, 2, 4);
        var dirLight = new THREE.DirectionalLight(0x00F2FE, 1.6);
        dirLight.position.set(8, 12, 10);
        var amberLight = new THREE.PointLight(0xFF8000, 2.5, 20);
        amberLight.position.set(0, 1, -2);
        scene.add(ambLight, mainPointLight, dirLight, amberLight);

        // Disposables collection for zero GPU leak
        var disposables = new Set();
        function track(item) {
            if (item) disposables.add(item);
            return item;
        }

        // =====================================================================
        // FEATURE #7 & #8: MATHEMATICAL PARTICLE WAVE & 4-STATE MORPHING SPHERE
        // =====================================================================
        var posArray = new Float32Array(MAX_PARTICLES * 3);
        var colorArray = new Float32Array(MAX_PARTICLES * 3);
        var state0Base = new Float32Array(MAX_PARTICLES * 3); // Wave Surface Base Grid
        var state1Base = new Float32Array(MAX_PARTICLES * 3); // Fibonacci Digital Sphere
        var state2Base = new Float32Array(MAX_PARTICLES * 3); // Toroidal Core Swarm Ring
        var state3Base = new Float32Array(MAX_PARTICLES * 3); // Quantum Hex Matrix

        var goldenAngle = Math.PI * (3 - Math.sqrt(5)); // ~2.399963 rad
        var sphereRadius = 4.2;
        var torusMajorR = 4.6;
        var torusMinorR = 1.6;
        var hexSpacing = 0.72;

        for (var i = 0; i < MAX_PARTICLES; i++) {
            var col = i % GRID_COLS;
            var row = Math.floor(i / GRID_COLS);

            // State 0: Responsive Wave Surface Grid spanning [-14, 14]
            var gx = (col / (GRID_COLS - 1) - 0.5) * 28.0;
            var gz = (row / (GRID_ROWS - 1) - 0.5) * 28.0;
            state0Base[i * 3] = gx;
            state0Base[i * 3 + 1] = 0.0;
            state0Base[i * 3 + 2] = gz;

            // State 1: Fibonacci Digital Sphere (r = 4.2)
            var yNorm = 1.0 - (i / (MAX_PARTICLES - 1)) * 2.0;
            var radAtY = Math.sqrt(Math.max(0.0, 1.0 - yNorm * yNorm)) * sphereRadius;
            var phi = i * goldenAngle;
            state1Base[i * 3] = Math.cos(phi) * radAtY;
            state1Base[i * 3 + 1] = yNorm * sphereRadius;
            state1Base[i * 3 + 2] = Math.sin(phi) * radAtY;

            // State 2: Toroidal Core Swarm Ring (R = 4.6, r = 1.6)
            var uTor = (i / MAX_PARTICLES) * Math.PI * 6.0;
            var vTor = ((i * 0.6180339887) % 1.0) * Math.PI * 2.0;
            state2Base[i * 3] = (torusMajorR + torusMinorR * Math.cos(vTor)) * Math.cos(uTor);
            state2Base[i * 3 + 1] = torusMinorR * Math.sin(vTor);
            state2Base[i * 3 + 2] = (torusMajorR + torusMinorR * Math.cos(vTor)) * Math.sin(uTor);

            // State 3: Quantum Hex Matrix (4 elevated isometric layers)
            var layerIdx = (i % 4) - 1.5;
            var qHex = (i % 30) - 15;
            var rHex = (Math.floor(i / 30) % 30) - 15;
            state3Base[i * 3] = hexSpacing * Math.sqrt(3.0) * (qHex + rHex / 2.0);
            state3Base[i * 3 + 1] = layerIdx * 1.35;
            state3Base[i * 3 + 2] = hexSpacing * 1.5 * rHex;

            // Initial positions: State 0
            posArray[i * 3] = state0Base[i * 3];
            posArray[i * 3 + 1] = state0Base[i * 3 + 1];
            posArray[i * 3 + 2] = state0Base[i * 3 + 2];

            // Liquid Aurora Palette: Mint (#42E6C3) to Cyan (#00F2FE) gradient
            var tGrad = (gx + 14.0) / 28.0;
            var rCol = 0.259 * (1.0 - tGrad) + 0.000 * tGrad;
            var gCol = 0.902 * (1.0 - tGrad) + 0.949 * tGrad;
            var bCol = 0.765 * (1.0 - tGrad) + 0.996 * tGrad;
            colorArray[i * 3] = rCol;
            colorArray[i * 3 + 1] = gCol;
            colorArray[i * 3 + 2] = bCol;
        }

        var particleGeo = track(new THREE.BufferGeometry());
        particleGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
        particleGeo.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));

        // Dynamic particle scaling: 1,600 on mobile, 2,500 on tablet, 3,600 on desktop
        var getTargetParticleCount = function () {
            var winW = window.innerWidth || 1440;
            if (winW < 768) return 1600;
            if (winW < 992) return 2500;
            return 3600;
        };
        var activeParticleCount = getTargetParticleCount();
        particleGeo.setDrawRange(0, activeParticleCount);

        var particleMat = track(new THREE.PointsMaterial({
            size: 0.08,
            vertexColors: true,
            transparent: true,
            opacity: 0.88,
            blending: THREE.AdditiveBlending
        }));
        var particleSystem = new THREE.Points(particleGeo, particleMat);
        scene.add(particleSystem);

        // =====================================================================
        // CORE SCULPTURES & STORYTELLING CHAPTER ASSETS
        // =====================================================================
        var rootCoreGroup = new THREE.Group();
        scene.add(rootCoreGroup);

        // A. Central Parametric Core (Möbius / TorusKnot)
        var coreGeo = track(new THREE.TorusKnotGeometry(2.0, 0.26, 128, 24, 2, 3));
        var coreMat = track(new THREE.MeshStandardMaterial({
            color: 0x0ABBDB,
            emissive: 0x0284C7,
            emissiveIntensity: 0.75,
            metalness: 0.92,
            roughness: 0.15
        }));
        var coreMesh = new THREE.Mesh(coreGeo, coreMat);
        rootCoreGroup.add(coreMesh);

        // B. Chapter 1: Orbiting Glowing Comets (#FF8000)
        var cometGroup = new THREE.Group();
        var cometMat = track(new THREE.MeshStandardMaterial({
            color: 0xFF8000,
            emissive: 0xFF8000,
            emissiveIntensity: 1.0,
            roughness: 0.1
        }));
        var comets = [];
        for (var c = 0; c < 3; c++) {
            var cMesh = new THREE.Mesh(track(new THREE.SphereGeometry(0.18, 16, 16)), cometMat);
            cometGroup.add(cMesh);
            comets.push({
                mesh: cMesh,
                radius: 3.2 + c * 0.7,
                speed: 0.8 + c * 0.35,
                angle: c * (Math.PI * 2 / 3),
                tilt: 0.35 * (c - 1)
            });
        }
        cometGroup.visible = false;
        rootCoreGroup.add(cometGroup);

        // C. Chapter 2: Exploded View 4 Volumetric Isometric Slabs & Glowing Data Buses
        var explodedGroup = new THREE.Group();
        var explodedLayers = [];
        var layerColors = [0x0ABBDB, 0xFF8000, 0x0284C7, 0x42E6C3];
        for (var lyr = 0; lyr < 4; lyr++) {
            var slabGeo = track(new THREE.BoxGeometry(3.2, 0.16, 3.2));
            var slabMat = track(new THREE.MeshStandardMaterial({
                color: layerColors[lyr],
                emissive: layerColors[lyr],
                emissiveIntensity: 0.45,
                metalness: 0.85,
                roughness: 0.20,
                transparent: true,
                opacity: 0.88
            }));
            var slabMesh = new THREE.Mesh(slabGeo, slabMat);
            slabMesh.position.y = (lyr - 1.5) * 0.35;
            explodedGroup.add(slabMesh);
            explodedLayers.push({
                mesh: slabMesh,
                baseY: (lyr - 1.5) * 0.35,
                expandedY: (lyr - 1.5) * 1.85,
                expandedX: (lyr - 1.5) * 0.45,
                expandedZ: -(lyr - 1.5) * 0.35
            });
        }

        // Leader Lines connecting isometric layers at corners
        var leaderLinesGroup = new THREE.Group();
        var leaderLineMat = track(new THREE.LineBasicMaterial({
            color: 0x00F2FE,
            transparent: true,
            opacity: 0.65
        }));
        var cornerOffsets = [
            [-1.5, -1.5], [1.5, -1.5], [1.5, 1.5], [-1.5, 1.5]
        ];
        var leaderLines = [];
        cornerOffsets.forEach(function (cnr) {
            var lGeo = track(new THREE.BufferGeometry());
            var lPos = new Float32Array([
                cnr[0], -2.8, cnr[1],
                cnr[0], 2.8, cnr[1]
            ]);
            lGeo.setAttribute('position', new THREE.BufferAttribute(lPos, 3));
            var lLine = new THREE.Line(lGeo, leaderLineMat);
            leaderLinesGroup.add(lLine);
            leaderLines.push({ line: lLine, cnr: cnr });
        });
        explodedGroup.add(leaderLinesGroup);

        // Glowing packet particles traversing data buses
        var dataPacketGroup = new THREE.Group();
        var packetMat = track(new THREE.MeshBasicMaterial({ color: 0x00F2FE }));
        var dataPackets = [];
        for (var pk = 0; pk < 8; pk++) {
            var pkMesh = new THREE.Mesh(track(new THREE.SphereGeometry(0.08, 8, 8)), packetMat);
            dataPacketGroup.add(pkMesh);
            dataPackets.push({
                mesh: pkMesh,
                progress: pk * 0.125,
                speed: 0.65,
                cornerIndex: pk % 4
            });
        }
        explodedGroup.add(dataPacketGroup);
        explodedGroup.visible = false;
        rootCoreGroup.add(explodedGroup);

        // D. Chapter 3: Blueprint Wireframe to Photorealistic PBR Mesh Morphing
        var shieldGroup = new THREE.Group();
        var shieldGeo = track(new THREE.IcosahedronGeometry(2.2, 1));
        var blueprintWireMat = track(new THREE.MeshBasicMaterial({
            color: 0x00F2FE,
            wireframe: true,
            transparent: true,
            opacity: 0.85
        }));
        var pbrMetallicMat = track(new THREE.MeshStandardMaterial({
            color: 0x0ABBDB,
            emissive: 0x0284C7,
            emissiveIntensity: 0.6,
            metalness: 0.92,
            roughness: 0.15,
            transparent: true,
            opacity: 0.0
        }));
        var wireMesh = new THREE.Mesh(shieldGeo, blueprintWireMat);
        var pbrMesh = new THREE.Mesh(shieldGeo, pbrMetallicMat);
        shieldGroup.add(wireMesh);
        shieldGroup.add(pbrMesh);

        // Zero-Trust Perimeter Ring
        var perimeterRingGeo = track(new THREE.TorusGeometry(3.2, 0.035, 16, 64));
        var perimeterRingMat = track(new THREE.MeshBasicMaterial({
            color: 0x42E6C3,
            transparent: true,
            opacity: 0.85
        }));
        var perimeterRing = new THREE.Mesh(perimeterRingGeo, perimeterRingMat);
        perimeterRing.rotation.x = Math.PI / 2.3;
        shieldGroup.add(perimeterRing);
        shieldGroup.visible = false;
        rootCoreGroup.add(shieldGroup);

        // =====================================================================
        // FEATURE #12: 360° KINETIC ORBIT WITH INERTIA DAMPING & PITCH CLAMP
        // =====================================================================
        var orbitState = {
            isDragging: false,
            prevX: 0,
            prevY: 0,
            yaw: 0.0,
            pitch: 0.65, // ~37 degrees resting inclination
            velYaw: 0.0,
            velPitch: 0.0,
            lambda: 3.2, // Exponential decay rate
            pitchMin: 15.0 * Math.PI / 180.0, // 15 deg floor clamp
            pitchMax: 85.0 * Math.PI / 180.0  // 85 deg ceiling clamp
        };

        // Pointer Ripples Array
        var activeRipples = [];
        var mouseWorldPos = { x: 0.0, z: 0.0 };

        // Container Pointer Drag Orbit Listeners
        var onPointerDown = function (e) {
            if (e.target && e.target.closest('button, a, input, select, .hero-product-tab-btn, .hero-scene-nav-item, .hero-control-btn, .tab-progress-track')) {
                return;
            }
            orbitState.isDragging = true;
            orbitState.prevX = e.clientX;
            orbitState.prevY = e.clientY;
            orbitState.velYaw = 0.0;
            orbitState.velPitch = 0.0;

            // Trigger click ripple impulse in wave field
            activeRipples.push({
                x: mouseWorldPos.x,
                z: mouseWorldPos.z,
                startTime: performance.now() / 1000.0,
                amplitude: 1.8
            });
            if (activeRipples.length > 6) activeRipples.shift();
        };

        var onPointerMove = function (e) {
            // Update ground plane mouse projection
            var nx = (e.clientX / window.innerWidth) * 2.0 - 1.0;
            var ny = -(e.clientY / window.innerHeight) * 2.0 + 1.0;
            mouseWorldPos.x = nx * 14.0;
            mouseWorldPos.z = -ny * 14.0;

            if (self.threeEngine && self.threeEngine.mouseOffset) {
                self.threeEngine.mouseOffset.x = nx * 0.45;
                self.threeEngine.mouseOffset.y = ny * 0.35;
            }

            if (orbitState.isDragging) {
                var dx = e.clientX - orbitState.prevX;
                var dy = e.clientY - orbitState.prevY;
                orbitState.prevX = e.clientX;
                orbitState.prevY = e.clientY;

                orbitState.velYaw = dx * 0.005;
                orbitState.velPitch = dy * 0.005;

                orbitState.yaw += orbitState.velYaw;
                orbitState.pitch = Math.max(orbitState.pitchMin, Math.min(orbitState.pitchMax, orbitState.pitch + orbitState.velPitch));
            }
        };

        var onPointerUp = function () {
            orbitState.isDragging = false;
        };

        this.container.addEventListener('pointerdown', onPointerDown, { passive: true });
        window.addEventListener('pointermove', onPointerMove, { passive: true });
        window.addEventListener('pointerup', onPointerUp, { passive: true });
        window.addEventListener('pointercancel', onPointerUp, { passive: true });

        // =====================================================================
        // STORYTELLING TRANSITION STATE MACHINE
        // =====================================================================
        var storyState = {
            currentChapter: 0,
            targetChapter: 0,
            morphProgress: 1.0,
            fromMorphState: 0,
            toMorphState: 0,
            targetFov: initialMode.fov || 55,
            explodedProgress: 0.0,
            wireframeMorphProgress: 0.0
        };

        var setChapter = function (chapterIdx) {
            if (chapterIdx < 0 || chapterIdx >= SCENE_MODES.length) return;
            var mode = SCENE_MODES[chapterIdx];

            storyState.fromMorphState = storyState.toMorphState;
            storyState.targetChapter = chapterIdx;
            storyState.toMorphState = mode.morphState !== undefined ? mode.morphState : chapterIdx;
            storyState.morphProgress = 0.0;
            storyState.targetFov = mode.fov || 45;

            // Visibility & Mode Activation
            cometGroup.visible = (chapterIdx === 1);
            explodedGroup.visible = (chapterIdx === 2 || storyState.currentChapter === 2);
            shieldGroup.visible = (chapterIdx === 3 || storyState.currentChapter === 3);

            if (chapterIdx === 3) {
                storyState.wireframeMorphProgress = 0.0;
            }

            self.threeEngine.targetCamPos.set(mode.camPos.x, mode.camPos.y, mode.camPos.z);
            self.threeEngine.targetLookAt.set(mode.lookAt.x, mode.lookAt.y, mode.lookAt.z);

            if (coreMat) {
                coreMat.color.setHex(mode.particleColor);
                coreMat.emissive.setHex(mode.particleColor);
            }
        };

        // Engine Bundle Object
        this.threeEngine = {
            renderer: renderer,
            scene: scene,
            camera: camera,
            coreGroup: rootCoreGroup,
            coreMesh: coreMesh,
            coreMat: coreMat,
            cometGroup: cometGroup,
            explodedGroup: explodedGroup,
            shieldGroup: shieldGroup,
            particleSystem: particleSystem,
            mainPointLight: mainPointLight,
            targetCamPos: new THREE.Vector3(initialMode.camPos.x, initialMode.camPos.y, initialMode.camPos.z),
            targetLookAt: currentLookAt.clone(),
            currentLookAt: currentLookAt.clone(),
            targetFov: initialMode.fov || 55,
            lerpSpeed: 0.06,
            lastTime: performance.now(),
            mouseOffset: { x: 0, y: 0 },
            setChapter: setChapter,
            disposables: disposables,
            orbitState: orbitState
        };

        // Window resize handler
        window.addEventListener('resize', function () {
            if (!self.viewport3D || !self.threeEngine || !self.threeEngine.renderer) return;
            var w = self.viewport3D.clientWidth || window.innerWidth;
            var h = self.viewport3D.clientHeight || 820;
            self.threeEngine.camera.aspect = w / h;
            self.threeEngine.camera.updateProjectionMatrix();
            self.threeEngine.renderer.setSize(w, h, false);
            self.threeEngine.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1.0, 2.0));

            // Dynamic particle count update on responsive resize
            var newCount = getTargetParticleCount();
            particleGeo.setDrawRange(0, newCount);
            activeParticleCount = newCount;
        });

        // WebGL Context Guard Handlers
        this.canvas3D.addEventListener('webglcontextlost', function (event) {
            event.preventDefault();
            console.warn('[InnoriaHeroInteractiveStage] WebGL Context Lost! Pausing render loop.');
            self.isContextLost = true;
        }, false);

        this.canvas3D.addEventListener('webglcontextrestored', function () {
            console.info('[InnoriaHeroInteractiveStage] WebGL Context Restored! Rebuilding stage.');
            self.isContextLost = false;
            self._init3DStage();
        }, false);

        // =====================================================================
        // RAF 60 FPS ANIMATION LOOP
        // =====================================================================
        function animate(now) {
            if (!self.isOffscreen && !self.isContextLost && self.threeEngine && self.threeEngine.renderer) {
                var eng = self.threeEngine;
                var delta = Math.min((now - eng.lastTime) / 1000.0, 0.1);
                eng.lastTime = now;
                var elapsed = now / 1000.0;

                // 1. Kinetic Orbit Inertia Damping (lambda = 3.2)
                if (!orbitState.isDragging) {
                    var decay = Math.exp(-orbitState.lambda * delta);
                    orbitState.velYaw *= decay;
                    orbitState.velPitch *= decay;
                    orbitState.yaw += orbitState.velYaw;
                    orbitState.pitch = Math.max(orbitState.pitchMin, Math.min(orbitState.pitchMax, orbitState.pitch + orbitState.velPitch));
                }

                // Apply 360 kinetic rotation
                rootCoreGroup.rotation.y = orbitState.yaw + elapsed * 0.12;
                rootCoreGroup.rotation.x = orbitState.pitch - 0.65;

                // 2. Dynamic Camera Focal Length Zoom (Feature #13)
                if (Math.abs(eng.camera.fov - storyState.targetFov) > 0.05) {
                    eng.camera.fov += (storyState.targetFov - eng.camera.fov) * Math.min(delta * 3.5, 0.15);
                    eng.camera.updateProjectionMatrix();
                }

                // 3. Kinetic Camera LERP Transition with Mouse Parallax
                var camTargetWithParallax = eng.targetCamPos.clone();
                camTargetWithParallax.x += eng.mouseOffset.x;
                camTargetWithParallax.y += eng.mouseOffset.y;

                eng.camera.position.lerp(camTargetWithParallax, eng.lerpSpeed);
                eng.currentLookAt.lerp(eng.targetLookAt, eng.lerpSpeed);
                eng.camera.lookAt(eng.currentLookAt);

                // 4. Cubic Hermite Curve Morphing (Feature #8)
                if (storyState.morphProgress < 1.0) {
                    storyState.morphProgress = Math.min(1.0, storyState.morphProgress + delta * 1.4);
                }
                var alpha = storyState.morphProgress;
                var sHermite = 3.0 * alpha * alpha - 2.0 * alpha * alpha * alpha; // s = 3a^2 - 2a^3

                var fromBase = storyState.fromMorphState === 1 ? state1Base :
                               (storyState.fromMorphState === 2 ? state2Base :
                               (storyState.fromMorphState === 3 ? state3Base : state0Base));
                var toBase = storyState.toMorphState === 1 ? state1Base :
                             (storyState.toMorphState === 2 ? state2Base :
                             (storyState.toMorphState === 3 ? state3Base : state0Base));

                // 5. Mathematical Particle Wave Equation & Pointer Repulsion (Feature #7)
                var positions = particleGeo.attributes.position.array;
                var waveWeight = (1.0 - sHermite) * (storyState.fromMorphState === 0 ? 1.0 : 0.0) +
                                 sHermite * (storyState.toMorphState === 0 ? 1.0 : 0.0);

                // Filter expired ripples
                activeRipples = activeRipples.filter(function (rp) {
                    return (elapsed - rp.startTime) < 3.5;
                });

                for (var p = 0; p < activeParticleCount; p++) {
                    var idx3 = p * 3;
                    var fx = fromBase[idx3];
                    var fy = fromBase[idx3 + 1];
                    var fz = fromBase[idx3 + 2];

                    var tx = toBase[idx3];
                    var ty = toBase[idx3 + 1];
                    var tz = toBase[idx3 + 2];

                    // Blend with cubic Hermite curve
                    var px = (1.0 - sHermite) * fx + sHermite * tx;
                    var py = (1.0 - sHermite) * fy + sHermite * ty;
                    var pz = (1.0 - sHermite) * fz + sHermite * tz;

                    // If wave state is active or transitioning, apply 2D wave equations
                    if (waveWeight > 0.01) {
                        var rxz = Math.sqrt(px * px + pz * pz);
                        var waveY = 0.65 * Math.sin(0.4 * px + 1.2 * elapsed) * Math.cos(0.4 * pz + 0.9 * elapsed) +
                                    0.45 * Math.sin(0.8 * rxz - 1.8 * elapsed);

                        // Cursor repulsion displacement
                        var dPtrX = px - mouseWorldPos.x;
                        var dPtrZ = pz - mouseWorldPos.z;
                        var distSq = dPtrX * dPtrX + dPtrZ * dPtrZ;
                        var repY = 1.6 * Math.exp(-distSq / (2.0 * 3.2 * 3.2));

                        // Click ripple impulses
                        var rippleY = 0.0;
                        for (var rIdx = 0; rIdx < activeRipples.length; rIdx++) {
                            var rip = activeRipples[rIdx];
                            var dt = elapsed - rip.startTime;
                            if (dt > 0.0 && dt < 3.5) {
                                var distToRip = Math.sqrt((px - rip.x) * (px - rip.x) + (pz - rip.z) * (pz - rip.z));
                                var waveFront = distToRip - 6.5 * dt;
                                rippleY += rip.amplitude * Math.exp(-1.4 * dt) * Math.exp(-waveFront * waveFront / 4.5) *
                                           Math.sin(1.3 * distToRip - 4.2 * dt);
                            }
                        }

                        py += (waveY + repY + rippleY) * waveWeight;
                    }

                    positions[idx3] = px;
                    positions[idx3 + 1] = py;
                    positions[idx3 + 2] = pz;
                }
                particleGeo.attributes.position.needsUpdate = true;

                // 6. Chapter 1: Orbiting Comets Dynamics
                if (cometGroup.visible) {
                    comets.forEach(function (c) {
                        c.angle += delta * c.speed;
                        c.mesh.position.set(
                            Math.cos(c.angle) * c.radius,
                            Math.sin(c.angle * 2.0) * 0.8 + c.tilt,
                            Math.sin(c.angle) * c.radius
                        );
                    });
                }

                // 7. Chapter 2: Exploded View Transition & Data Buses (Feature #10)
                if (storyState.targetChapter === 2) {
                    storyState.explodedProgress = Math.min(1.0, storyState.explodedProgress + delta * 2.0);
                } else {
                    storyState.explodedProgress = Math.max(0.0, storyState.explodedProgress - delta * 2.5);
                }

                if (storyState.explodedProgress > 0.01) {
                    explodedGroup.visible = true;
                    var expP = storyState.explodedProgress;
                    var sExp = 3.0 * expP * expP - 2.0 * expP * expP * expP;

                    explodedLayers.forEach(function (el) {
                        el.mesh.position.y = (1.0 - sExp) * el.baseY + sExp * el.expandedY;
                        el.mesh.position.x = sExp * el.expandedX;
                        el.mesh.position.z = sExp * el.expandedZ;
                    });

                    // Update data packets traveling between layers
                    dataPackets.forEach(function (dp) {
                        dp.progress = (dp.progress + delta * dp.speed) % 1.0;
                        var cnr = cornerOffsets[dp.cornerIndex];
                        dp.mesh.position.set(
                            cnr[0] * 0.85,
                            -2.5 + dp.progress * 5.0,
                            cnr[1] * 0.85
                        );
                    });
                } else if (storyState.targetChapter !== 2) {
                    explodedGroup.visible = false;
                }

                // 8. Chapter 3: Blueprint Wireframe to Photorealistic PBR Mesh Morphing (Feature #11)
                if (storyState.targetChapter === 3) {
                    storyState.wireframeMorphProgress = Math.min(1.0, storyState.wireframeMorphProgress + delta * 0.85);
                    shieldGroup.visible = true;
                    var wProg = storyState.wireframeMorphProgress;
                    var sPbr = 3.0 * wProg * wProg - 2.0 * wProg * wProg * wProg;

                    // Morph from wireframe (0.0) -> translucent X-ray (0.5) -> photorealistic metallic PBR (1.0)
                    blueprintWireMat.opacity = Math.max(0.05, 0.85 * (1.0 - sPbr));
                    pbrMetallicMat.opacity = Math.min(1.0, sPbr * 1.0);
                    pbrMetallicMat.roughness = 0.45 * (1.0 - sPbr) + 0.15 * sPbr;
                    pbrMetallicMat.metalness = 0.50 * (1.0 - sPbr) + 0.92 * sPbr;

                    perimeterRing.rotation.z += delta * 0.85;
                } else {
                    shieldGroup.visible = false;
                }

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
            if (typeof activeController.selectChapter === 'function') {
                activeController.selectChapter(targetIdx);
            }
        }
        if (this.threeEngine) {
            if (typeof this.threeEngine.setChapter === 'function') {
                this.threeEngine.setChapter(targetIdx);
            } else if (this.threeEngine.targetCamPos) {
                this.threeEngine.targetCamPos.set(mode.camPos.x, mode.camPos.y, mode.camPos.z);
                this.threeEngine.targetLookAt.set(mode.lookAt.x, mode.lookAt.y, mode.lookAt.z);
                if (this.threeEngine.coreMat) {
                    this.threeEngine.coreMat.color.setHex(mode.particleColor);
                    this.threeEngine.coreMat.emissive.setHex(mode.particleColor);
                }
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
