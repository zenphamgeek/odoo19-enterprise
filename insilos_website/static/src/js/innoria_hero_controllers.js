/**
 * Innoria Unified 3D Interactive Hero Banner Engine - 8 Route Scene Controllers
 * File: innoria_hero_controllers.js
 * Host Target: innoria.insilos.com (Insilos Sovereign Web Platform / Odoo 20)
 *
 * Controllers Specification:
 * 1. SovereignCoreController      (route: '/', sceneId: 'sovereign_core')
 * 2. AscendingHeritageController  (route: '/about', sceneId: 'ascending_heritage')
 * 3. EnterpriseBrainController    (route: '/platform', sceneId: 'enterprise_brain', Midnight Space #070B14)
 * 4. BuildersCanvasController     (route: '/no-code-platform', sceneId: 'builders_canvas')
 * 5. ImmutableLedgerController    (route: '/blockchain', sceneId: 'immutable_ledger')
 * 6. SmartFactoryTwinController   (route: '/solutions', sceneId: 'smart_factory')
 * 7. BionicEyeController          (route: '/industries', sceneId: 'bionic_eye')
 * 8. GlobalAdvisoryDeskController (route: '/contactus', sceneId: 'global_advisory')
 *
 * Performance Budget: 60 FPS | Strict <= 15 Draw Calls per Scene | Zero Memory Leaks
 */

(function (root, factory) {
    var THREE = root.THREE || (root.InsilosThreeBundle && root.InsilosThreeBundle.THREE) || (typeof window !== 'undefined' && (window.THREE || (window.InsilosThreeBundle && window.InsilosThreeBundle.THREE)));
    var Manager = root.InnoriaHero3DManager || (typeof window !== 'undefined' && window.InnoriaHero3DManager);

    if (typeof module === 'object' && module.exports) {
        module.exports = factory(THREE || require('three'), Manager || require('./innoria_hero_3d_manager'));
    } else {
        root.InnoriaHeroControllers = factory(THREE, Manager);
    }
}(typeof self !== 'undefined' ? self : this, function (THREE, InnoriaHero3DManager) {
    'use strict';

    if (!THREE) {
        console.error('[InnoriaHeroControllers] Fatal: Three.js library not detected.');
        return null;
    }

    var PALETTE = {
        cyan: 0x0ABBDB,
        bluePrimary: 0x0284C7,
        blueDark: 0x0369A1,
        blueIce: 0xBAE6FD,
        orange: 0xFF8000,
        orangeDark: 0xEA580C,
        purple: 0x8B5CF6,
        green: 0x10B981,
        red: 0xEF4444,
        darkSpace: 0x070B14,
        white: 0xFFFFFF,
        slate: 0x0F172A
    };

    // =========================================================================
    // BASE CONTROLLER CLASS
    // =========================================================================
    function BaseHeroSceneController(manager, sceneId, sceneName) {
        this.manager = manager;
        this.sceneId = sceneId;
        this.sceneName = sceneName;
        this.scene = null;
        this.camera = null;
        this.canvas = null;
        this.config = {};
        this.raycaster = new THREE.Raycaster();
        this.mouseNDC = new THREE.Vector2(0, 0);
        this.interactiveObjects = [];
        this.disposables = new Set();
        this.rootGroup = null;
    }

    BaseHeroSceneController.prototype.init = function (canvas, config) {
        this.canvas = canvas;
        this.config = config || {};
        this.scene = new THREE.Scene();
        this.rootGroup = new THREE.Group();
        this.scene.add(this.rootGroup);

        var aspect = (canvas.clientWidth || window.innerWidth) / (canvas.clientHeight || window.innerHeight);
        var camConfig = this.config.camera || {};
        var fov = camConfig.fov || 45;
        var near = camConfig.near || 0.1;
        var far = camConfig.far || 1000;

        this.camera = new THREE.PerspectiveCamera(fov, aspect, near, far);
        var initPos = camConfig.initialPosition || [0, 2, 10];
        this.camera.position.set(initPos[0], initPos[1], initPos[2]);
        var lookAt = camConfig.lookAt || [0, 0, 0];
        this.targetLookAt = new THREE.Vector3(lookAt[0], lookAt[1], lookAt[2]);
        this.camera.lookAt(this.targetLookAt);
        this.cameraInitialPos = this.camera.position.clone();

        return this.buildScene();
    };

    BaseHeroSceneController.prototype.buildScene = function () {
        return Promise.resolve();
    };

    BaseHeroSceneController.prototype.onPointerMove = function (normX, normY) {
        this.mouseNDC.set(normX, normY);
        // Subtle parallax camera tilt preserving custom framing
        if (this.camera && this.cameraInitialPos) {
            this.camera.position.x = this.cameraInitialPos.x + normX * 0.45;
            this.camera.position.y = this.cameraInitialPos.y + normY * 0.35;
            this.camera.lookAt(this.targetLookAt || new THREE.Vector3(0, 0, 0));
        }
    };

    BaseHeroSceneController.prototype.updateHUDNode = function (title, desc) {
        var titleEl = document.getElementById('innoria_active_node_title');
        var descEl = document.getElementById('innoria_active_node_desc');
        if (titleEl && title) titleEl.textContent = title;
        if (descEl && desc) descEl.textContent = desc;
    };

    BaseHeroSceneController.prototype.onInteract = function (event) {
        // Override in subclasses for click/tap raycasting
    };

    BaseHeroSceneController.prototype.onResize = function (width, height, dpr) {
        if (this.camera) {
            var safeHeight = (height > 0) ? height : (window.innerHeight || 1);
            this.camera.aspect = width / safeHeight;
            this.camera.updateProjectionMatrix();
        }
    };

    BaseHeroSceneController.prototype.trackDisposable = function (item) {
        if (item) this.disposables.add(item);
        return item;
    };

    BaseHeroSceneController.prototype.dispose = function () {
        if (this.scene) {
            this.scene.traverse(function (obj) {
                if (obj.geometry && typeof obj.geometry.dispose === 'function') {
                    obj.geometry.dispose();
                }
                if (obj.material) {
                    if (Array.isArray(obj.material)) {
                        obj.material.forEach(function (m) { m.dispose(); });
                    } else if (typeof obj.material.dispose === 'function') {
                        obj.material.dispose();
                    }
                }
            });
        }

        this.disposables.forEach(function (item) {
            if (item && typeof item.dispose === 'function') {
                try { item.dispose(); } catch (e) {}
            }
        });

        this.disposables.clear();
        this.interactiveObjects = [];
        this.scene = null;
        this.camera = null;
        this.rootGroup = null;
    };

    // =========================================================================
    // 1. SOVEREIGN CORE CONTROLLER (Route: '/', sceneId: 'sovereign_core')
    // Centerpiece: Authentic 3D Innoria Logo Kinetic Sculpture & Service Architecture
    // =========================================================================

    function createInnoriaLogoHelixCurve() {
        var points = [];
        var segments = 128;
        for (var i = 0; i <= segments; i++) {
            var u = (i / segments) * Math.PI * 2;
            var x = 2.3 * Math.sin(u) + 0.65 * Math.sin(2 * u);
            var y = 1.7 * Math.cos(u) + 0.4 * Math.sin(3 * u);
            var z = 1.15 * Math.sin(2 * u) * Math.cos(u);
            points.push(new THREE.Vector3(x, y, z));
        }
        var CurveClass = THREE.CatmullRomCurve3 || THREE.CatmullRomCurve3D;
        return new CurveClass(points, true);
    }

    var SOVEREIGN_NODES_DATA = [
        {
            id: 'node_digiforce',
            key: 'DIGIFORCE',
            name: 'DIGIFORCE Sovereign Platform',
            category: 'No-Code / Low-Code Hyper-App Engine',
            color: 0x0ABBDB, // Mint Cyan
            accentColor: 0x0284C7,
            orbitAngle: 0.15,
            radius: 6.8,
            stackPos: new THREE.Vector3(-3.8, 2.2, 0),
            tagline: 'Kiến tạo ứng dụng doanh nghiệp siêu tốc theo chuẩn 3h -> 3d -> 3w -> 3m',
            metrics: [
                { label: 'Rapid Prototype (BƯỚC 1)', value: '3 Giờ', badge: 'Sprint' },
                { label: 'Pilot MVP (BƯỚC 2)', value: '3 Ngày', badge: 'Validated' },
                { label: 'Enterprise Rollout (BƯỚC 3)', value: '3 Tuần', badge: 'Production' },
                { label: 'Multi-Site Maturity (BƯỚC 4)', value: '3 Tháng', badge: 'Sovereign' }
            ],
            architecture: {
                engine: 'Visual Workflow & Logic Synthesizer',
                governance: 'Multi-Tenant Sandbox Isolation',
                integration: 'OpenAPI 3.1 & Insilos Data Mesh Connector'
            },
            deepLink: '/no-code-platform'
        },
        {
            id: 'node_mojo_ai',
            key: 'MOJO_AI',
            name: 'MOJO AI Multi-Agent Swarm',
            category: 'Autonomous Multi-Modal Agent Mesh',
            color: 0x00F2FE, // Tech Cyan
            accentColor: 0x38BDF8,
            orbitAngle: Math.PI * 0.55,
            radius: 6.8,
            stackPos: new THREE.Vector3(3.8, 2.2, 0),
            tagline: 'VLM Perception & Dual-Loop Cognitive Autonomous Execution',
            metrics: [
                { label: 'Vòng Nhận Thức (VLM)', value: 'See-Detect-Analyze-Adapt', badge: 'VLM Active' },
                { label: 'Vòng Thực Thi (Swarm)', value: 'Reason-Solve-Plan-Execute', badge: 'Clef DAG' },
                { label: 'Quy Mô Agent Hoạt Động', value: '16 Sovereign Nodes', badge: 'Healthy' },
                { label: 'Độ Trễ Suy Luận (p95)', value: '184 ms', badge: 'Optimal' }
            ],
            architecture: {
                engine: 'Clef DAG Scheduler & Hybrid Reasoning Core',
                guardrails: 'Zero-Evasion Verification & Anti-Hallucination Gate',
                telemetry: 'Passive Quota Ledger & Autonomous Token Saver'
            },
            deepLink: '/ai-solutions'
        },
        {
            id: 'node_zencode',
            key: 'ZENCODE_ENT',
            aliases: ['MOJOVERSE', 'node_mojoverse', 'ZENCODE'],
            name: 'ZENCODE-ENT Autonomous OS',
            category: 'Sovereign Autonomous Engineering OS',
            color: 0x42E6C3, // Mint
            accentColor: 0x00F0FF,
            orbitAngle: Math.PI * 1.15,
            radius: 6.8,
            stackPos: new THREE.Vector3(-3.8, -1.8, 0),
            tagline: 'Hệ Điều Hành Kỹ Nghệ Tự Trị Cho Ngân Hàng & Doanh Nghiệp Chủ Quyền',
            metrics: [
                { label: 'Mô Hình Swarm PDCA', value: '5 Vai Trò Tự Trị', badge: 'Active Swarm' },
                { label: 'Quyền Phủ Quyết Nhị Phân', value: 'Binary Veto = 0', badge: 'Forensic Gate' },
                { label: 'Chủ Quyền Dữ Liệu', value: 'Zero Outbound Telemetry', badge: 'Air-Gapped' },
                { label: 'Hiện Đại Hóa Monolith', value: 'Strangler-Fig Pattern', badge: 'Zero Downtime' }
            ],
            architecture: {
                engine: 'Clef ONNX DAG Inference & Deterministic Latency',
                isolation: 'Per-Node Egress Proxy & Passive Quota Ledger',
                compliance: 'SBV Banking Regulations & Financial Invariants'
            },
            deepLink: '/zencode'
        },
        {
            id: 'node_insilos',
            key: 'INSILOS',
            aliases: ['INTELLIGENT_ERP', 'node_intelligent_erp', 'smart-erp'],
            name: 'INSILOS Enterprise Platform',
            category: 'Autonomous Enterprise Operations & VAS Core',
            color: 0x00F0FF, // Tech Cyan
            accentColor: 0x10B981,
            orbitAngle: Math.PI * 1.65,
            radius: 6.8,
            stackPos: new THREE.Vector3(3.8, -1.8, 0),
            tagline: 'Lõi Quản Trị Vận Hành Doanh Nghiệp Hợp Nhất Trí Tuệ Nhân Tạo',
            metrics: [
                { label: 'Quy Trình Nghiệp Vụ SAP', value: 'MM, SD, FI/CO, PP, MES', badge: 'Unified' },
                { label: 'Bản Địa Hóa Việt Nam', value: 'TT78 HĐĐT & TT200 VAS', badge: 'Certified' },
                { label: 'Hiệu Suất Nhà Máy (OEE)', value: '>= 95% Khả Dụng', badge: 'Live MES' },
                { label: 'Đội Xe Drayage & Depot', value: 'Giảm -88% Phí DET/DEM', badge: 'Telematics' }
            ],
            architecture: {
                core: 'Modern QWeb & Owl 20 Enterprise Web Client',
                compliance: 'Circular 78/2021/TT-BTC & Decree 123/2020/ND-CP',
                integration: 'Direct SAP RFC / EDI / REST Microservices Gateway'
            },
            deepLink: '/insilos'
        }
    ];

    function SovereignCoreController(manager) {
        BaseHeroSceneController.call(this, manager, 'sovereign_core', 'The Sovereign Core');
        this.currentMode = 'topology';
        this.defaultCameraPos = new THREE.Vector3(0, 2.2, 14.2);
        this.stackCameraPos = new THREE.Vector3(0, 3.8, 15.6);
        this.controlsTarget = new THREE.Vector3(0, 0, 0);

        this.logoGroup = null;
        this.logoCurve = null;
        this.logoComets = [];
        this.nucleusMesh = null;
        this.cometLight = null;

        this.satelliteNodes = [];
        this.conduitBuses = [];
        this.packetParticles = [];
        this.stackPlatesGroup = null;
        this.orbitalPlaneMesh = null;
        this.cosmicDust = null;

        this._cameraLerping = false;
        this._camLerpAlpha = 0.0;
        this._camLerpStart = new THREE.Vector3();
        this._camLerpEnd = new THREE.Vector3();
        this._targetLerpStart = new THREE.Vector3();
        this._targetLerpEnd = new THREE.Vector3();
        this._selectedNode = null;
        this._boundButtons = [];
    }
    SovereignCoreController.prototype = Object.create(BaseHeroSceneController.prototype);
    SovereignCoreController.prototype.constructor = SovereignCoreController;

    SovereignCoreController.prototype.buildScene = function () {
        var self = this;

        // Camera setup
        this.camera.position.copy(this.defaultCameraPos);
        this.targetLookAt = this.controlsTarget.clone();
        this.camera.lookAt(this.targetLookAt);
        this.cameraInitialPos = this.camera.position.clone();

        // 1. Lighting Rig
        var ambLight = new THREE.AmbientLight(0x0F1E36, 2.2);
        var coreCyanLight = new THREE.PointLight(0x0ABBDB, 4.8, 28);
        coreCyanLight.position.set(0, 0, 1.2);
        var coreAmberLight = new THREE.PointLight(0xFF8000, 3.2, 22);
        coreAmberLight.position.set(0, 0.8, -1.5);
        var rim1 = new THREE.DirectionalLight(0x00F2FE, 2.0);
        rim1.position.set(10, 14, 12);
        var rim2 = new THREE.DirectionalLight(0xF59E0B, 1.4);
        rim2.position.set(-12, -6, -10);

        this.scene.add(ambLight, coreCyanLight, coreAmberLight, rim1, rim2);

        // 2. Cybernetic Coordinate Grid
        var grid = new THREE.GridHelper(34, 48, 0x0ABBDB, 0x0F294A);
        grid.position.y = -3.8;
        grid.material.opacity = 0.55;
        grid.material.transparent = true;
        this.trackDisposable(grid.geometry);
        this.trackDisposable(grid.material);
        this.rootGroup.add(grid);

        // 3. Orbital Boundary Ring (15 deg inclination)
        var outerRingGeo = this.trackDisposable(new THREE.RingGeometry(6.75, 6.85, 96));
        var outerRingMat = this.trackDisposable(new THREE.MeshBasicMaterial({
            color: 0x0ABBDB,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.28
        }));
        this.orbitalPlaneMesh = new THREE.Mesh(outerRingGeo, outerRingMat);
        this.orbitalPlaneMesh.rotation.x = Math.PI / 2 + 0.22;
        this.rootGroup.add(this.orbitalPlaneMesh);

        // 4. THE AUTHENTIC 3D INNORIA LOGO SCULPTURE (Centerpiece)
        this.logoGroup = new THREE.Group();
        this.logoGroup.name = 'Innoria_3D_Logo_Sculpture';
        this.logoCurve = createInnoriaLogoHelixCurve();

        // 4.1 Primary Glass-Metallic Ribbon in Electric Cyan
        var mainTubeGeo = this.trackDisposable(new THREE.TubeGeometry(this.logoCurve, 128, 0.17, 16, true));
        var logoMainMat = this.trackDisposable(new THREE.MeshStandardMaterial({
            color: 0x0ABBDB,
            emissive: 0x0284C7,
            emissiveIntensity: 0.85,
            metalness: 0.92,
            roughness: 0.12
        }));
        var logoMainMesh = new THREE.Mesh(mainTubeGeo, logoMainMat);
        this.logoGroup.add(logoMainMesh);

        // 4.2 High-Luminescence Inner Laser Core
        var laserTubeGeo = this.trackDisposable(new THREE.TubeGeometry(this.logoCurve, 128, 0.05, 8, true));
        var laserMat = this.trackDisposable(new THREE.MeshBasicMaterial({
            color: 0x00F2FE,
            transparent: true,
            opacity: 0.95
        }));
        var logoLaserMesh = new THREE.Mesh(laserTubeGeo, laserMat);
        this.logoGroup.add(logoLaserMesh);

        // 4.3 Cybernetic Holographic Wireframe Envelope
        var wireTubeGeo = this.trackDisposable(new THREE.TubeGeometry(this.logoCurve, 64, 0.30, 6, true));
        var wireMat = this.trackDisposable(new THREE.MeshBasicMaterial({
            color: 0x0ABBDB,
            wireframe: true,
            transparent: true,
            opacity: 0.28
        }));
        var logoWireMesh = new THREE.Mesh(wireTubeGeo, wireMat);
        this.logoGroup.add(logoWireMesh);

        // 4.4 Central Quantum Energy Nucleus (Octahedron Prism)
        var nucleusGeo = this.trackDisposable(new THREE.OctahedronGeometry(0.72, 1));
        var nucleusMat = this.trackDisposable(new THREE.MeshStandardMaterial({
            color: 0x00F2FE,
            emissive: 0x0ABBDB,
            emissiveIntensity: 0.9,
            metalness: 0.85,
            roughness: 0.15
        }));
        this.nucleusMesh = new THREE.Mesh(nucleusGeo, nucleusMat);
        this.logoGroup.add(this.nucleusMesh);

        // 4.5 The 3 Signature Orbiting Orange Logo Comets (#FF8000)
        this.logoComets = [];
        var cMat = this.trackDisposable(new THREE.MeshStandardMaterial({
            color: 0xFF8000,
            emissive: 0xFF8000,
            emissiveIntensity: 1.0,
            roughness: 0.1
        }));

        // Comet 1: Spline Glider (travels directly along the Möbius spline)
        var c1Geo = this.trackDisposable(new THREE.SphereGeometry(0.24, 16, 16));
        var comet1 = new THREE.Mesh(c1Geo, cMat);
        this.logoGroup.add(comet1);
        this.logoComets.push({ mesh: comet1, type: 'spline', progress: 0.0, speed: 0.18 });

        // Comet 2: Apex Halo
        var c2Geo = this.trackDisposable(new THREE.SphereGeometry(0.19, 16, 16));
        var comet2 = new THREE.Mesh(c2Geo, cMat);
        this.logoGroup.add(comet2);
        this.logoComets.push({ mesh: comet2, type: 'orbit_apex', angle: 0.0, radius: 2.7, height: 1.2, speed: 0.32 });

        // Comet 3: Base Vortex
        var c3Geo = this.trackDisposable(new THREE.SphereGeometry(0.16, 16, 16));
        var comet3 = new THREE.Mesh(c3Geo, cMat);
        this.logoGroup.add(comet3);
        this.logoComets.push({ mesh: comet3, type: 'orbit_base', angle: Math.PI, radius: 3.2, height: -0.8, speed: 0.24 });

        this.cometLight = new THREE.PointLight(0xFF8000, 2.5, 8);
        this.logoGroup.add(this.cometLight);
        this.rootGroup.add(this.logoGroup);

        // 5. THE 4 SERVICE ARCHITECTURE PODS (KIẾN TRÚC DỊCH VỤ)
        this.satelliteNodes = [];
        SOVEREIGN_NODES_DATA.forEach(function (data, index) {
            var podGroup = new THREE.Group();
            podGroup.name = data.id;
            podGroup.userData = {
                nodeData: data,
                isPod: true,
                index: index,
                orbitAngle: data.orbitAngle,
                radius: data.radius,
                stackPos: data.stackPos
            };

            // Hexagonal Pedestal Base
            var pedestalGeo = self.trackDisposable(new THREE.CylinderGeometry(1.25, 1.45, 0.18, 6));
            var pedestalMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                color: 0x0A1424,
                emissive: data.color,
                emissiveIntensity: 0.32,
                metalness: 0.85,
                roughness: 0.25
            }));
            var pedestal = new THREE.Mesh(pedestalGeo, pedestalMat);
            pedestal.position.y = -0.55;
            podGroup.add(pedestal);

            // Neon Edge Bevel on Pedestal
            var edgeGeo = self.trackDisposable(new THREE.RingGeometry(1.26, 1.34, 6));
            var edgeMat = self.trackDisposable(new THREE.MeshBasicMaterial({
                color: data.color,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.75
            }));
            var edge = new THREE.Mesh(edgeGeo, edgeMat);
            edge.rotation.x = Math.PI / 2;
            edge.position.y = -0.45;
            podGroup.add(edge);

            // Semantic Architecture Micro-Core
            var archCore = new THREE.Group();

            if (data.key === 'DIGIFORCE') {
                // 4 Cascading Stepped Glass Slabs (3h -> 3d -> 3w -> 3m)
                for (var s = 0; s < 4; s++) {
                    var w = 1.1 - (s * 0.15);
                    var slabGeo = self.trackDisposable(new THREE.BoxGeometry(w, 0.10, w));
                    var slabMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                        color: (s % 2 === 0) ? data.color : 0x0284C7,
                        emissive: data.color,
                        emissiveIntensity: 0.45 + (s * 0.12),
                        metalness: 0.8,
                        roughness: 0.2,
                        transparent: true,
                        opacity: 0.88
                    }));
                    var slab = new THREE.Mesh(slabGeo, slabMat);
                    slab.position.y = -0.3 + (s * 0.22);
                    slab.rotation.y = s * (Math.PI / 8);
                    archCore.add(slab);
                }
                var glyphGeo = self.trackDisposable(new THREE.OctahedronGeometry(0.28, 0));
                var glyphMat = self.trackDisposable(new THREE.MeshBasicMaterial({ color: 0x00F2FE }));
                var topGlyph = new THREE.Mesh(glyphGeo, glyphMat);
                topGlyph.position.y = 0.75;
                archCore.add(topGlyph);
            } else if (data.key === 'MOJO_AI') {
                // Neural Swarm Core + 6 Orbiting Micro-Agents
                var brainGeo = self.trackDisposable(new THREE.IcosahedronGeometry(0.72, 1));
                var brainMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                    color: data.color,
                    emissive: 0x0284C7,
                    emissiveIntensity: 0.65,
                    metalness: 0.9,
                    roughness: 0.15
                }));
                archCore.add(new THREE.Mesh(brainGeo, brainMat));

                podGroup.userData.swarmAgents = [];
                for (var a = 0; a < 6; a++) {
                    var agGeo = self.trackDisposable(new THREE.SphereGeometry(0.09, 8, 8));
                    var agMat = self.trackDisposable(new THREE.MeshBasicMaterial({ color: 0x00F2FE }));
                    var agMesh = new THREE.Mesh(agGeo, agMat);
                    archCore.add(agMesh);
                    podGroup.userData.swarmAgents.push({
                        mesh: agMesh,
                        radius: 1.15,
                        angleOffset: a * (Math.PI / 3),
                        speed: 0.8 + (a * 0.15)
                    });
                }
            } else if (data.key === 'ZENCODE_ENT' || data.key === 'MOJOVERSE') {
                // Interlocking Cryptographic Hash-Chain Blocks & Consensus Torus Ring
                for (var b = 0; b < 3; b++) {
                    var bGeo = self.trackDisposable(new THREE.BoxGeometry(0.55, 0.55, 0.55));
                    var bMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                        color: 0x42E6C3,
                        emissive: 0x00F0FF,
                        emissiveIntensity: 0.6,
                        metalness: 0.85,
                        roughness: 0.2
                    }));
                    var block = new THREE.Mesh(bGeo, bMat);
                    block.position.set((b - 1) * 0.42, (b - 1) * 0.32, (b - 1) * 0.2);
                    block.rotation.set(b * 0.2, b * 0.3, b * 0.1);
                    archCore.add(block);
                }
                var cRingGeo = self.trackDisposable(new THREE.TorusGeometry(1.05, 0.022, 16, 48));
                var cRingMat = self.trackDisposable(new THREE.MeshBasicMaterial({
                    color: 0x42E6C3,
                    transparent: true,
                    opacity: 0.85
                }));
                var consensusRing = new THREE.Mesh(cRingGeo, cRingMat);
                consensusRing.rotation.x = Math.PI / 2.5;
                archCore.add(consensusRing);
                podGroup.userData.consensusRing = consensusRing;
            } else if (data.key === 'INSILOS' || data.key === 'INTELLIGENT_ERP') {
                // 4 Enterprise Architecture Pillars + Central Unified Data Core
                for (var p = 0; p < 4; p++) {
                    var ang = p * (Math.PI / 2);
                    var pGeo = self.trackDisposable(new THREE.CylinderGeometry(0.08, 0.08, 0.85, 8));
                    var pMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                        color: 0x0A1424,
                        emissive: 0x10B981,
                        emissiveIntensity: 0.4,
                        metalness: 0.9,
                        roughness: 0.2
                    }));
                    var pillar = new THREE.Mesh(pGeo, pMat);
                    pillar.position.set(Math.cos(ang) * 0.65, 0, Math.sin(ang) * 0.65);
                    archCore.add(pillar);
                }
                var erpGeo = self.trackDisposable(new THREE.SphereGeometry(0.48, 16, 16));
                var erpMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                    color: 0x0284C7,
                    emissive: 0x10B981,
                    emissiveIntensity: 0.7,
                    metalness: 0.8,
                    roughness: 0.2
                }));
                archCore.add(new THREE.Mesh(erpGeo, erpMat));

                var teleGeo = self.trackDisposable(new THREE.RingGeometry(0.68, 0.72, 32));
                var teleMat = self.trackDisposable(new THREE.MeshBasicMaterial({
                    color: 0x10B981,
                    side: THREE.DoubleSide,
                    transparent: true,
                    opacity: 0.75
                }));
                var teleRing = new THREE.Mesh(teleGeo, teleMat);
                teleRing.rotation.x = Math.PI / 2;
                archCore.add(teleRing);
            }

            podGroup.add(archCore);
            podGroup.userData.architectureCore = archCore;

            // Invisible Hit Sphere for Precision Raycasting
            var hitGeo = self.trackDisposable(new THREE.SphereGeometry(1.6, 8, 8));
            var hitMat = self.trackDisposable(new THREE.MeshBasicMaterial({ visible: false }));
            var hitSphere = new THREE.Mesh(hitGeo, hitMat);
            hitSphere.userData = { parentPod: podGroup, nodeData: data };
            podGroup.add(hitSphere);

            // Initial Position
            var initialPos = self._calcOrbitPos(data.orbitAngle, data.radius, 0);
            podGroup.position.copy(initialPos);

            self.rootGroup.add(podGroup);
            self.satelliteNodes.push(podGroup);
            self.interactiveObjects.push(hitSphere);
        });

        // 6. Data Conduits & Flowing Packet Particles
        this.conduitBuses = [];
        this.packetParticles = [];
        var conduitMat = this.trackDisposable(new THREE.LineDashedMaterial({
            color: 0x0ABBDB,
            dashSize: 0.35,
            gapSize: 0.15,
            transparent: true,
            opacity: 0.42
        }));

        for (var c = 0; c < 4; c++) {
            var cGeo = this.trackDisposable(new THREE.BufferGeometry());
            var cLine = new THREE.Line(cGeo, conduitMat);
            this.rootGroup.add(cLine);
            this.conduitBuses.push({ line: cLine, curveIndex: c });

            for (var pkt = 0; pkt < 4; pkt++) {
                var pktGeo = this.trackDisposable(new THREE.SphereGeometry(0.08, 8, 8));
                var pktMat = this.trackDisposable(new THREE.MeshBasicMaterial({ color: 0x00F2FE }));
                var pktMesh = new THREE.Mesh(pktGeo, pktMat);
                this.rootGroup.add(pktMesh);
                this.packetParticles.push({
                    mesh: pktMesh,
                    curveIndex: c,
                    progress: (pkt * 0.25),
                    speed: 0.45 + (pkt * 0.08)
                });
            }
        }

        // 7. Ambient Cosmic Dust
        var dustCount = 380;
        var dustGeo = this.trackDisposable(new THREE.BufferGeometry());
        var dustPos = new Float32Array(dustCount * 3);
        for (var d = 0; d < dustCount; d++) {
            dustPos[d * 3] = (Math.random() - 0.5) * 32;
            dustPos[d * 3 + 1] = (Math.random() - 0.5) * 16;
            dustPos[d * 3 + 2] = (Math.random() - 0.5) * 28;
        }
        dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
        var dustMat = this.trackDisposable(new THREE.PointsMaterial({
            color: 0x38BDF8,
            size: 0.06,
            transparent: true,
            opacity: 0.55
        }));
        this.cosmicDust = new THREE.Points(dustGeo, dustMat);
        this.rootGroup.add(this.cosmicDust);

        // 8. Architecture Stack Plates (for 'stack' mode)
        this.stackPlatesGroup = new THREE.Group();
        this.stackPlatesGroup.visible = false;
        var tiers = [
            { y: 2.2, label: 'Lớp 1: Synthesis & Agents', color: 0x0ABBDB },
            { y: -1.8, label: 'Lớp 2: Ledger & ERP Core', color: 0x0284C7 }
        ];
        tiers.forEach(function (tier) {
            var plateGeo = self.trackDisposable(new THREE.BoxGeometry(11.5, 0.08, 4.8));
            var plateMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                color: 0x0A1424,
                emissive: tier.color,
                emissiveIntensity: 0.2,
                metalness: 0.9,
                roughness: 0.2,
                transparent: true,
                opacity: 0.65
            }));
            var plate = new THREE.Mesh(plateGeo, plateMat);
            plate.position.set(0, tier.y - 0.7, 0);
            self.stackPlatesGroup.add(plate);
        });
        this.rootGroup.add(this.stackPlatesGroup);

        // Bind DOM HUD & Buttons
        this._bindHUDControls();

        return Promise.resolve();
    };

    SovereignCoreController.prototype._calcOrbitPos = function (angle, radius, elapsed) {
        var inclination = 0.22;
        var curAngle = angle + (elapsed * 0.08);
        return new THREE.Vector3(
            Math.cos(curAngle) * radius,
            Math.sin(curAngle) * radius * Math.sin(inclination) + Math.sin(elapsed * 1.5) * 0.2,
            Math.sin(curAngle) * radius * Math.cos(inclination)
        );
    };

    SovereignCoreController.prototype.update = function (delta, elapsed) {
        var self = this;

        // 1. Central Innoria Logo Dynamics
        if (this.logoGroup) {
            this.logoGroup.rotation.y = elapsed * 0.18;
            this.logoGroup.rotation.z = Math.sin(elapsed * 0.4) * 0.08;

            if (this.nucleusMesh) {
                var scalePulse = 1.0 + 0.08 * Math.sin(elapsed * 2.8);
                this.nucleusMesh.scale.set(scalePulse, scalePulse, scalePulse);
                this.nucleusMesh.rotation.y = elapsed * 0.45;
            }

            // 3 Signature Orange Comets Orbiting along authentic logo trajectories
            if (this.logoComets && this.logoCurve) {
                this.logoComets.forEach(function (c) {
                    if (c.type === 'spline') {
                        c.progress = (c.progress + delta * c.speed) % 1.0;
                        var pt = self.logoCurve.getPointAt(c.progress);
                        c.mesh.position.copy(pt);
                        if (self.cometLight) self.cometLight.position.copy(pt);
                    } else if (c.type === 'orbit_apex') {
                        c.angle += delta * c.speed;
                        c.mesh.position.set(
                            Math.cos(c.angle) * c.radius,
                            c.height + Math.sin(c.angle * 2) * 0.3,
                            Math.sin(c.angle) * c.radius
                        );
                    } else if (c.type === 'orbit_base') {
                        c.angle -= delta * c.speed;
                        c.mesh.position.set(
                            Math.cos(c.angle) * c.radius,
                            c.height + Math.cos(c.angle * 2) * 0.25,
                            Math.sin(c.angle) * c.radius
                        );
                    }
                });
            }
        }

        // 2. Service Architecture Pod Motions
        this.satelliteNodes.forEach(function (podGroup) {
            var data = podGroup.userData.nodeData;
            var targetPos;

            if (self.currentMode === 'stack') {
                targetPos = data.stackPos;
            } else {
                targetPos = self._calcOrbitPos(data.orbitAngle, data.radius, elapsed);
            }

            podGroup.position.lerp(targetPos, 0.06);

            var archCore = podGroup.userData.architectureCore;
            if (archCore) {
                archCore.rotation.y = elapsed * 0.35;
            }

            // Swarm Agents Dynamics
            if (podGroup.userData.swarmAgents) {
                podGroup.userData.swarmAgents.forEach(function (ag) {
                    var agAngle = (elapsed * ag.speed) + ag.angleOffset;
                    ag.mesh.position.set(
                        Math.cos(agAngle) * ag.radius,
                        Math.sin(agAngle * 2) * 0.35,
                        Math.sin(agAngle) * ag.radius
                    );
                });
            }

            // Consensus Ring Rotation
            if (podGroup.userData.consensusRing) {
                podGroup.userData.consensusRing.rotation.z = elapsed * 0.75;
            }
        });

        // 3. Cybernetic Data Conduit Pulses
        if (this.packetParticles && this.conduitBuses) {
            this.packetParticles.forEach(function (pkt) {
                pkt.progress = (pkt.progress + delta * pkt.speed) % 1.0;
                var targetNode = self.satelliteNodes[pkt.curveIndex];
                if (targetNode) {
                    var start = new THREE.Vector3(0, 0, 0);
                    var end = targetNode.position;
                    var mid = new THREE.Vector3(end.x * 0.5, end.y * 0.5 + 1.2, end.z * 0.5);
                    var curve = new THREE.QuadraticBezierCurve3(start, mid, end);
                    var pt = curve.getPointAt(pkt.progress);
                    pkt.mesh.position.copy(pt);
                }
            });
        }

        // 4. Ambient Cosmic Dust
        if (this.cosmicDust) {
            this.cosmicDust.rotation.y = elapsed * 0.02;
        }

        // 5. Smooth Camera Lerp on Selection / Mode Change
        if (this._cameraLerping) {
            this._camLerpAlpha += delta * 1.8;
            var alpha = Math.min(this._camLerpAlpha, 1.0);
            var smoothAlpha = 0.5 - 0.5 * Math.cos(alpha * Math.PI); // Sine ease

            this.camera.position.lerpVectors(this._camLerpStart, this._camLerpEnd, smoothAlpha);
            this.targetLookAt.lerpVectors(this._targetLerpStart, this._targetLerpEnd, smoothAlpha);
            this.camera.lookAt(this.targetLookAt);

            if (alpha >= 1.0) {
                this._cameraLerping = false;
            }
        }
    };

    SovereignCoreController.prototype.onPointerMove = function (normX, normY) {
        BaseHeroSceneController.prototype.onPointerMove.call(this, normX, normY);

        if (!this.camera || !this.interactiveObjects.length) return;
        this.raycaster.setFromCamera(this.mouseNDC, this.camera);
        var intersects = this.raycaster.intersectObjects(this.interactiveObjects);

        if (intersects.length > 0) {
            var hit = intersects[0].object;
            var podGroup = hit.userData.parentPod;
            if (podGroup && podGroup !== this._selectedNode) {
                podGroup.scale.set(1.08, 1.08, 1.08);
            }
            if (this.canvas) this.canvas.style.cursor = 'pointer';
        } else {
            this.satelliteNodes.forEach(function (pod) {
                if (pod !== this._selectedNode) {
                    pod.scale.set(1.0, 1.0, 1.0);
                }
            }.bind(this));
            if (this.canvas) this.canvas.style.cursor = 'default';
        }
    };

    SovereignCoreController.prototype.onInteract = function (event) {
        if (!this.camera || !this.interactiveObjects.length) return;
        this.raycaster.setFromCamera(this.mouseNDC, this.camera);
        var intersects = this.raycaster.intersectObjects(this.interactiveObjects);

        if (intersects.length > 0) {
            var hit = intersects[0].object;
            var podGroup = hit.userData.parentPod;
            var nodeData = hit.userData.nodeData;
            if (podGroup && nodeData) {
                this.selectNode(podGroup, nodeData);
            }
        }
    };

    SovereignCoreController.prototype.selectNode = function (podGroup, nodeData) {
        this._selectedNode = podGroup;

        var worldPos = new THREE.Vector3();
        podGroup.getWorldPosition(worldPos);

        var offset = worldPos.clone().normalize().multiplyScalar(4.5).add(new THREE.Vector3(0, 1.6, 0));
        var targetCamPos = worldPos.clone().add(offset);

        this._startCameraLerp(targetCamPos, worldPos);
        this.showHUD(nodeData);

        // Update active state in HUD buttons
        var buttons = document.querySelectorAll('.innoria-hud-btn');
        buttons.forEach(function (b) {
            b.classList.toggle('active', b.getAttribute('data-node-key') === nodeData.key);
        });
    };

    SovereignCoreController.prototype.resetView = function () {
        this._selectedNode = null;
        var targetCamPos = (this.currentMode === 'stack') ? this.stackCameraPos : this.defaultCameraPos;
        this._startCameraLerp(targetCamPos, this.controlsTarget);
        this.hideHUD();

        var buttons = document.querySelectorAll('.innoria-hud-btn');
        buttons.forEach(function (b) { b.classList.remove('active'); });
    };

    SovereignCoreController.prototype.setMode = function (mode) {
        this.currentMode = (mode === 'stack') ? 'stack' : 'topology';

        if (this.currentMode === 'stack') {
            if (this.stackPlatesGroup) this.stackPlatesGroup.visible = true;
            if (this.orbitalPlaneMesh) this.orbitalPlaneMesh.visible = false;
            if (this.logoGroup) this.logoGroup.position.set(0, 0, -2.5);
            this._startCameraLerp(this.stackCameraPos, this.controlsTarget);
        } else {
            if (this.stackPlatesGroup) this.stackPlatesGroup.visible = false;
            if (this.orbitalPlaneMesh) this.orbitalPlaneMesh.visible = true;
            if (this.logoGroup) this.logoGroup.position.set(0, 0, 0);
            this._startCameraLerp(this.defaultCameraPos, this.controlsTarget);
        }

        var toggleBtn = document.getElementById('innoriaModeToggleBtn') || document.querySelector('[data-action="toggle-mode"]');
        if (toggleBtn) {
            toggleBtn.innerHTML = (this.currentMode === 'stack') ? '<span>🌌 Quỹ Đạo Logo</span>' : '<span>🏛️ Kiến Trúc Dịch Vụ</span>';
        }
    };

    SovereignCoreController.prototype.toggleArchitectureMode = function () {
        this.setMode(this.currentMode === 'topology' ? 'stack' : 'topology');
    };

    SovereignCoreController.prototype._startCameraLerp = function (endPos, endTarget) {
        this._cameraLerping = true;
        this._camLerpAlpha = 0.0;
        this._camLerpStart = this.camera.position.clone();
        this._camLerpEnd = endPos.clone();
        this._targetLerpStart = this.targetLookAt.clone();
        this._targetLerpEnd = endTarget.clone();
    };

    SovereignCoreController.prototype._bindHUDControls = function () {
        var self = this;
        var hudBar = document.querySelector('.innoria-hud-control-bar');
        if (!hudBar) return;

        // Check if toggle mode button already exists, if not add it
        var toggleBtn = hudBar.querySelector('[data-action="toggle-mode"]');
        if (!toggleBtn) {
            toggleBtn = document.createElement('button');
            toggleBtn.type = 'button';
            toggleBtn.className = 'innoria-hud-btn';
            toggleBtn.id = 'innoriaModeToggleBtn';
            toggleBtn.setAttribute('data-action', 'toggle-mode');
            toggleBtn.innerHTML = '<span>🏛️ Kiến Trúc Dịch Vụ</span>';
            var resetBtn = hudBar.querySelector('[data-action="reset-view"]');
            if (resetBtn) {
                hudBar.insertBefore(toggleBtn, resetBtn);
            } else {
                hudBar.appendChild(toggleBtn);
            }
        }

        // Bind all HUD buttons
        var buttons = hudBar.querySelectorAll('.innoria-hud-btn');
        buttons.forEach(function (btn) {
            var action = btn.getAttribute('data-action');
            var nodeKey = btn.getAttribute('data-node-key');

            var handler = function (e) {
                e.preventDefault();
                if (action === 'focus-node' && nodeKey) {
                    var targetPod = self.satelliteNodes.find(function (p) {
                        return p.userData && p.userData.nodeData && p.userData.nodeData.key === nodeKey;
                    });
                    if (targetPod) {
                        self.selectNode(targetPod, targetPod.userData.nodeData);
                    }
                } else if (action === 'reset-view') {
                    self.resetView();
                } else if (action === 'toggle-mode') {
                    self.toggleArchitectureMode();
                }
            };
            btn.addEventListener('click', handler);
            self._boundButtons.push({ el: btn, handler: handler });
        });
    };

    SovereignCoreController.prototype.showHUD = function (nodeData) {
        var container = this.canvas ? this.canvas.parentElement : document.getElementById('innoriaTopologyViewport');
        if (!container) return;

        var hud = document.getElementById('innoriaTopologyHUD');
        if (!hud) {
            hud = document.createElement('aside');
            hud.id = 'innoriaTopologyHUD';
            hud.className = 'innoria-topology-hud card position-absolute p-4 shadow-lg';
            hud.style.cssText = 'display:none;top:1.5rem;right:1.5rem;max-width:440px;width:calc(100% - 3rem);background:rgba(7,11,20,0.94);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid rgba(10,187,219,0.35);border-radius:14px;color:#FFFFFF;z-index:1000;box-shadow:0 16px 40px rgba(0,0,0,0.75),0 0 24px rgba(10,187,219,0.25);font-family:system-ui,-apple-system,sans-serif;';
            container.style.position = 'relative';
            container.appendChild(hud);
        }

        var hexColor = '#' + nodeData.color.toString(16).padStart(6, '0');
        var metricsHtml = (nodeData.metrics || []).map(function (m) {
            return '<div class="d-flex justify-content-between align-items-center py-2 border-bottom" style="border-color: rgba(255,255,255,0.08) !important;">' +
                   '<span style="font-size:0.85rem;color:#CBD5E1;">' + m.label + '</span>' +
                   '<span class="badge" style="background:rgba(10,187,219,0.18);border:1px solid ' + hexColor + ';color:#FFFFFF;font-weight:600;font-size:0.82rem;padding:0.25rem 0.65rem;border-radius:6px;">' +
                   m.value + '</span></div>';
        }).join('');

        hud.innerHTML =
            '<div class="d-flex justify-content-between align-items-start mb-2">' +
                '<div>' +
                    '<div class="text-uppercase" style="font-size:0.72rem;letter-spacing:0.08em;color:' + hexColor + ';font-weight:700;">' + nodeData.category + '</div>' +
                    '<h3 class="m-0 mt-1" style="font-size:1.35rem;font-weight:800;color:#FFFFFF;">' + nodeData.name + '</h3>' +
                '</div>' +
                '<button type="button" class="btn-close btn-close-white" aria-label="Close telemetry view" style="opacity:0.85;"></button>' +
            '</div>' +
            '<p style="font-size:0.88rem;line-height:1.45;color:#E2E8F0;margin-bottom:1.2rem;">' + nodeData.tagline + '</p>' +
            '<div class="metrics-grid mb-3">' + metricsHtml + '</div>' +
            '<div class="d-flex gap-2 mt-3 pt-2">' +
                '<a href="' + nodeData.deepLink + '" class="btn w-100 py-2 text-center text-decoration-none fw-bold" style="background:' + hexColor + ';color:#070B14;border-radius:8px;font-size:0.9rem;transition:opacity 0.2s ease;">' +
                    'Khám Phá Chi Tiết &rarr;' +
                '</a>' +
            '</div>';

        var self = this;
        var closeBtn = hud.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.onclick = function (e) {
                e.stopPropagation();
                self.resetView();
            };
        }
        hud.style.display = 'block';
    };

    SovereignCoreController.prototype.hideHUD = function () {
        var hud = document.getElementById('innoriaTopologyHUD');
        if (hud) hud.style.display = 'none';
    };

    // =========================================================================
    // 2. ASCENDING HERITAGE CONTROLLER (Route: '/about', sceneId: 'ascending_heritage')
    // =========================================================================
    function AscendingHeritageController(manager) {
        BaseHeroSceneController.call(this, manager, 'ascending_heritage', 'The Ascending Heritage');
        this.milestones = [];
        this.helixGroup = null;
        this.stardust = null;
        this.scrollOffset = 0;
    }
    AscendingHeritageController.prototype = Object.create(BaseHeroSceneController.prototype);
    AscendingHeritageController.prototype.constructor = AscendingHeritageController;

    AscendingHeritageController.prototype.buildScene = function () {
        this.camera.position.set(2.8, 3.5, 9.8);
        this.targetLookAt = new THREE.Vector3(0, 1.2, 0);
        this.camera.lookAt(this.targetLookAt);
        this.cameraInitialPos = this.camera.position.clone();

        var ambLight = new THREE.AmbientLight(0xFFFFFF, 1.4);
        var keyLight = new THREE.DirectionalLight(PALETTE.bluePrimary, 2.0);
        keyLight.position.set(4, 10, 6);
        var rimLight = new THREE.DirectionalLight(PALETTE.orange, 1.2);
        rimLight.position.set(-5, 2, -4);
        this.scene.add(ambLight, keyLight, rimLight);

        this.helixGroup = new THREE.Group();
        this.rootGroup.add(this.helixGroup);

        // Double Helix Strands & Cross Rungs
        var turns = 3.2;
        var height = 12.0;
        var radius = 2.8;
        var steps = 180;
        var strand1Points = [];
        var strand2Points = [];
        var rungPoints = [];

        for (var i = 0; i <= steps; i++) {
            var t = i / steps;
            var angle = t * Math.PI * 2 * turns;
            var y = (t - 0.5) * height;
            var x1 = Math.cos(angle) * radius;
            var z1 = Math.sin(angle) * radius;
            var x2 = Math.cos(angle + Math.PI) * radius;
            var z2 = Math.sin(angle + Math.PI) * radius;

            var p1 = new THREE.Vector3(x1, y, z1);
            var p2 = new THREE.Vector3(x2, y, z2);
            strand1Points.push(p1);
            strand2Points.push(p2);

            if (i % 6 === 0) {
                rungPoints.push(p1, p2);
            }
        }

        var strandGeo1 = this.trackDisposable(new THREE.BufferGeometry().setFromPoints(strand1Points));
        var strandGeo2 = this.trackDisposable(new THREE.BufferGeometry().setFromPoints(strand2Points));
        var rungGeo = this.trackDisposable(new THREE.BufferGeometry().setFromPoints(rungPoints));

        var strandMat1 = this.trackDisposable(new THREE.LineBasicMaterial({ color: PALETTE.bluePrimary, transparent: true, opacity: 0.6 }));
        var strandMat2 = this.trackDisposable(new THREE.LineBasicMaterial({ color: PALETTE.cyan, transparent: true, opacity: 0.6 }));
        var rungMat = this.trackDisposable(new THREE.LineBasicMaterial({ color: PALETTE.orange, transparent: true, opacity: 0.45 }));

        this.helixGroup.add(new THREE.Line(strandGeo1, strandMat1));
        this.helixGroup.add(new THREE.Line(strandGeo2, strandMat2));
        this.helixGroup.add(new THREE.LineSegments(rungGeo, rungMat));

        // 7 Milestone Crystals
        var milestoneData = [
            { year: '2008', title: 'Khởi Nguyên R&D', tech: 'Core Systems', y: -4.0 },
            { year: '2012', title: 'Kiến Trúc Cloud', tech: 'Distributed Cloud', y: -2.5 },
            { year: '2016', title: 'Hệ Thống ERP', tech: 'Enterprise ERP', y: -1.0 },
            { year: '2020', title: 'DIGIFORCE No-Code', tech: 'Rapid App Engine', y: 0.8 },
            { year: '2023', title: 'MOJO AI Foundation', tech: 'Cognitive RAG', y: 2.5 },
            { year: '2024', title: 'MOJOVERSE Web3', tech: 'Ledger & Trust', y: 4.2 },
            { year: '2026', title: 'Sovereign Swarm', tech: 'Multi-Agent ERP', y: 5.8 }
        ];

        var crystalGeo = this.trackDisposable(new THREE.OctahedronGeometry(0.35, 0));
        var crystalMat = this.trackDisposable(new THREE.MeshStandardMaterial({
            color: PALETTE.orange,
            emissive: PALETTE.orangeDark,
            emissiveIntensity: 0.5,
            roughness: 0.2,
            metalness: 0.8
        }));

        var self = this;
        milestoneData.forEach(function (m) {
            var crystal = new THREE.Mesh(crystalGeo, crystalMat);
            var tNorm = (m.y + 6.0) / 12.0;
            var angle = tNorm * Math.PI * 2 * turns;
            crystal.position.set(Math.cos(angle) * radius, m.y, Math.sin(angle) * radius);
            crystal.userData = m;
            self.helixGroup.add(crystal);
            self.milestones.push(crystal);
            self.interactiveObjects.push(crystal);
        });

        // Upward Floating Stardust
        var dustCount = 200;
        var dustGeo = this.trackDisposable(new THREE.BufferGeometry());
        var dustPositions = new Float32Array(dustCount * 3);
        for (var d = 0; d < dustCount; d++) {
            dustPositions[d * 3] = (Math.random() - 0.5) * 7.0;
            dustPositions[d * 3 + 1] = (Math.random() - 0.5) * 12.0;
            dustPositions[d * 3 + 2] = (Math.random() - 0.5) * 7.0;
        }
        dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3));
        var dustMat = this.trackDisposable(new THREE.PointsMaterial({
            color: PALETTE.blueIce,
            size: 0.09,
            transparent: true,
            opacity: 0.6
        }));
        this.stardust = new THREE.Points(dustGeo, dustMat);
        this.helixGroup.add(this.stardust);

        return Promise.resolve();
    };

    AscendingHeritageController.prototype.onInteract = function (event) {
        if (event.type === 'scroll_progress' && typeof event.deltaY === 'number') {
            this.scrollOffset += event.deltaY * 0.002;
            this.scrollOffset = Math.max(-2.5, Math.min(2.5, this.scrollOffset));
        }
    };

    AscendingHeritageController.prototype.update = function (delta, elapsed) {
        if (this.helixGroup) {
            this.helixGroup.rotation.y += delta * 0.15;
            this.helixGroup.position.y = -this.scrollOffset;
        }

        // Ascending stardust loop
        if (this.stardust) {
            var pos = this.stardust.geometry.attributes.position.array;
            for (var i = 1; i < pos.length; i += 3) {
                pos[i] += delta * 0.8;
                if (pos[i] > 6.0) pos[i] = -6.0;
            }
            this.stardust.geometry.attributes.position.needsUpdate = true;
        }

        // Milestone rotation
        this.milestones.forEach(function (m) {
            m.rotation.y += delta * 0.8;
            m.rotation.x += delta * 0.4;
        });
    };

    // =========================================================================
    // 3. ENTERPRISE BRAIN CONTROLLER (Route: '/platform', sceneId: 'enterprise_brain')
    // =========================================================================
    function EnterpriseBrainController(manager) {
        BaseHeroSceneController.call(this, manager, 'enterprise_brain', 'The Enterprise Brain');
        this.cube = null;
        this.synapseNodes = null;
        this.synapseLines = null;
        this.injectionBeam = null;
        this.pulseTime = 0;
    }
    EnterpriseBrainController.prototype = Object.create(BaseHeroSceneController.prototype);
    EnterpriseBrainController.prototype.constructor = EnterpriseBrainController;

    EnterpriseBrainController.prototype.buildScene = function () {
        this.camera.position.set(0, 1.8, 10.2);
        this.camera.lookAt(0, 0, 0);
        this.cameraInitialPos = this.camera.position.clone();

        var ambLight = new THREE.AmbientLight(0x0A101D, 0.8);
        var keyLight = new THREE.DirectionalLight(0x00F0FF, 3.0);
        keyLight.position.set(6, 6, 8);
        var rimLight = new THREE.DirectionalLight(PALETTE.purple, 2.4);
        rimLight.position.set(-6, -4, -6);
        this.scene.add(ambLight, keyLight, rimLight);

        // Sovereign Frosted Crystal Cube (Outer Boundary)
        var cubeGeo = this.trackDisposable(new THREE.BoxGeometry(5.4, 5.4, 5.4));
        var cubeMat = this.trackDisposable(new THREE.MeshPhysicalMaterial({
            color: 0x071526,
            transmission: 0.92,
            roughness: 0.12,
            transparent: true,
            opacity: 0.45,
            wireframe: false,
            depthWrite: false
        }));
        this.cube = new THREE.Mesh(cubeGeo, cubeMat);
        this.rootGroup.add(this.cube);

        // Wireframe edges on the cube
        var edgeGeo = this.trackDisposable(new THREE.BoxGeometry(5.42, 5.42, 5.42));
        var edgeMat = this.trackDisposable(new THREE.MeshBasicMaterial({
            color: 0x00F0FF,
            wireframe: true,
            transparent: true,
            opacity: 0.35
        }));
        this.rootGroup.add(new THREE.Mesh(edgeGeo, edgeMat));

        // Synaptic Neural Network (4 Layers: 16, 24, 24, 8 = 72 Nodes via InstancedMesh!)
        var totalNodes = 72;
        var nodeGeo = this.trackDisposable(new THREE.SphereGeometry(0.12, 12, 12));
        var nodeMat = this.trackDisposable(new THREE.MeshBasicMaterial({ color: 0x00F0FF }));
        this.synapseNodes = new THREE.InstancedMesh(nodeGeo, nodeMat, totalNodes);

        var layerCounts = [16, 24, 24, 8];
        var layerX = [-2.0, -0.67, 0.67, 2.0];
        var nodePositions = [];
        var dummy = new THREE.Object3D();
        var nodeIdx = 0;

        for (var l = 0; l < layerCounts.length; l++) {
            var count = layerCounts[l];
            for (var n = 0; n < count; n++) {
                var y = (Math.random() - 0.5) * 4.2;
                var z = (Math.random() - 0.5) * 4.2;
                var x = layerX[l] + (Math.random() - 0.5) * 0.4;
                var pos = new THREE.Vector3(x, y, z);
                nodePositions.push(pos);

                dummy.position.copy(pos);
                dummy.updateMatrix();
                this.synapseNodes.setMatrixAt(nodeIdx++, dummy.matrix);
            }
        }
        this.synapseNodes.instanceMatrix.needsUpdate = true;
        this.rootGroup.add(this.synapseNodes);

        // Synapse Connection Lines
        var linePoints = [];
        var currentOffset = 0;
        for (var l2 = 0; l2 < layerCounts.length - 1; l2++) {
            var c1 = layerCounts[l2];
            var c2 = layerCounts[l2 + 1];
            var nextOffset = currentOffset + c1;

            for (var i = 0; i < c1; i++) {
                var connectCount = 2 + Math.floor(Math.random() * 3);
                for (var k = 0; k < connectCount; k++) {
                    var targetIdx = nextOffset + Math.floor(Math.random() * c2);
                    linePoints.push(nodePositions[currentOffset + i], nodePositions[targetIdx]);
                }
            }
            currentOffset = nextOffset;
        }

        var lineGeo = this.trackDisposable(new THREE.BufferGeometry().setFromPoints(linePoints));
        var lineMat = this.trackDisposable(new THREE.LineBasicMaterial({
            color: PALETTE.bluePrimary,
            transparent: true,
            opacity: 0.35
        }));
        this.synapseLines = new THREE.LineSegments(lineGeo, lineMat);
        this.rootGroup.add(this.synapseLines);

        // Prompt Injection Beam (Center axis laser beam)
        var beamGeo = this.trackDisposable(new THREE.CylinderGeometry(0.04, 0.04, 8.0, 16));
        beamGeo.rotateZ(Math.PI / 2);
        var beamMat = this.trackDisposable(new THREE.MeshBasicMaterial({
            color: PALETTE.orange,
            transparent: true,
            opacity: 0.8
        }));
        this.injectionBeam = new THREE.Mesh(beamGeo, beamMat);
        this.rootGroup.add(this.injectionBeam);

        return Promise.resolve();
    };

    EnterpriseBrainController.prototype.onInteract = function (event) {
        if (event.type === 'click' || event.type === 'pointer_down') {
            this.pulseTime = 1.0; // Trigger cognitive reasoning pulse
        }
    };

    EnterpriseBrainController.prototype.update = function (delta, elapsed) {
        if (this.rootGroup) {
            this.rootGroup.rotation.y = elapsed * 0.12;
            this.rootGroup.rotation.x = Math.sin(elapsed * 0.2) * 0.08;
        }

        // Pulse injection beam (length along X, pulse thickness in Y and Z)
        if (this.injectionBeam) {
            var pulse = Math.sin(elapsed * 4.0) * 0.2 + 0.8;
            if (this.pulseTime > 0) {
                pulse += this.pulseTime * 0.8;
                this.pulseTime -= delta * 1.5;
            }
            this.injectionBeam.scale.set(1.0, pulse, pulse);
        }
    };

    // =========================================================================
    // 4. BUILDERS CANVAS CONTROLLER (Route: '/no-code-platform', sceneId: 'builders_canvas')
    // =========================================================================
    function BuildersCanvasController(manager) {
        BaseHeroSceneController.call(this, manager, 'builders_canvas', "The Builder's Canvas");
        this.blocks = [];
        this.rippleMesh = null;
        this.rippleRadius = 0.2;
    }
    BuildersCanvasController.prototype = Object.create(BaseHeroSceneController.prototype);
    BuildersCanvasController.prototype.constructor = BuildersCanvasController;

    BuildersCanvasController.prototype.buildScene = function () {
        this.camera.position.set(4.2, 5.0, 8.8);
        this.camera.lookAt(0, 0.4, 0);
        this.cameraInitialPos = this.camera.position.clone();

        var ambLight = new THREE.AmbientLight(0xF8FAFC, 1.3);
        var keyLight = new THREE.DirectionalLight(PALETTE.bluePrimary, 2.2);
        keyLight.position.set(7, 12, 6);
        var rimLight = new THREE.DirectionalLight(PALETTE.orange, 1.4);
        rimLight.position.set(-5, -2, -4);
        this.scene.add(ambLight, keyLight, rimLight);

        // 3D Isometric Coordinate Blueprint Grid
        var grid = this.trackDisposable(new THREE.GridHelper(16, 32, PALETTE.bluePrimary, PALETTE.blueIce));
        grid.position.y = 0;
        this.rootGroup.add(grid);

        // Modular Logic Blocks (DataModel, WorkflowEngine, OmniUI)
        var blockConfigs = [
            { id: 'blk_data', name: 'DataModel Module', pos: [-2.2, 0.5, -1.0], size: [1.5, 0.9, 1.3], color: PALETTE.bluePrimary },
            { id: 'blk_logic', name: 'Workflow Engine', pos: [0.0, 0.8, 0.0], size: [1.7, 1.1, 1.5], color: PALETTE.cyan },
            { id: 'blk_ui', name: 'OmniUI Studio', pos: [2.2, 0.5, 1.0], size: [1.5, 0.9, 1.3], color: PALETTE.orange }
        ];

        var self = this;
        blockConfigs.forEach(function (cfg) {
            var bGeo = self.trackDisposable(new THREE.BoxGeometry(cfg.size[0], cfg.size[1], cfg.size[2]));
            var bMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                color: cfg.color,
                roughness: 0.3,
                metalness: 0.6
            }));
            var mesh = new THREE.Mesh(bGeo, bMat);
            mesh.position.set(cfg.pos[0], cfg.pos[1], cfg.pos[2]);
            mesh.userData = cfg;
            mesh.userData.baseY = cfg.pos[1];

            // Wireframe edge accent
            var edgeGeo = self.trackDisposable(new THREE.BoxGeometry(cfg.size[0] * 1.01, cfg.size[1] * 1.01, cfg.size[2] * 1.01));
            var edgeMat = self.trackDisposable(new THREE.MeshBasicMaterial({ color: PALETTE.white, wireframe: true, transparent: true, opacity: 0.4 }));
            mesh.add(new THREE.Mesh(edgeGeo, edgeMat));

            self.rootGroup.add(mesh);
            self.blocks.push(mesh);
            self.interactiveObjects.push(mesh);
        });

        // Connecting Pipelines (Lines linking Block 1 -> 2 -> 3)
        var pipePoints = [
            new THREE.Vector3(-2.2, 0.5, -1.0),
            new THREE.Vector3(0.0, 0.8, 0.0),
            new THREE.Vector3(0.0, 0.8, 0.0),
            new THREE.Vector3(2.2, 0.5, 1.0)
        ];
        var pipeGeo = this.trackDisposable(new THREE.BufferGeometry().setFromPoints(pipePoints));
        var pipeMat = this.trackDisposable(new THREE.LineBasicMaterial({ color: PALETTE.cyan, transparent: true, opacity: 0.65 }));
        this.rootGroup.add(new THREE.LineSegments(pipeGeo, pipeMat));

        // Deployment Ripple Mesh (Ground concentric circle pulse)
        var ripGeo = this.trackDisposable(new THREE.RingGeometry(0.1, 0.25, 48));
        ripGeo.rotateX(-Math.PI / 2);
        var ripMat = this.trackDisposable(new THREE.MeshBasicMaterial({
            color: PALETTE.orange,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.7
        }));
        this.rippleMesh = new THREE.Mesh(ripGeo, ripMat);
        this.rippleMesh.position.y = 0.02;
        this.rootGroup.add(this.rippleMesh);

        return Promise.resolve();
    };

    BuildersCanvasController.prototype.update = function (delta, elapsed) {
        // Expand deployment ripple
        if (this.rippleMesh) {
            this.rippleRadius += delta * 2.2;
            if (this.rippleRadius > 7.5) {
                this.rippleRadius = 0.2;
            }
            this.rippleMesh.scale.set(this.rippleRadius, this.rippleRadius, this.rippleRadius);
            this.rippleMesh.material.opacity = Math.max(0, 0.75 * (1.0 - this.rippleRadius / 7.5));
        }

        // Raycast hover check
        this.raycaster.setFromCamera(this.mouseNDC, this.camera);
        var intersects = this.raycaster.intersectObjects(this.interactiveObjects);
        var hoveredObj = intersects.length > 0 ? intersects[0].object : null;

        this.blocks.forEach(function (b) {
            var targetY = (b === hoveredObj) ? b.userData.baseY + 0.35 : b.userData.baseY;
            b.position.y += (targetY - b.position.y) * 0.1;
        });
    };

    // =========================================================================
    // 5. IMMUTABLE LEDGER CONTROLLER (Route: '/blockchain', sceneId: 'immutable_ledger')
    // =========================================================================
    function ImmutableLedgerController(manager) {
        BaseHeroSceneController.call(this, manager, 'immutable_ledger', 'The Immutable Ledger');
        this.hexInstanced = null;
        this.scanPlane = null;
        this.scanX = -6.0;
        this.hexCount = 19;
    }
    ImmutableLedgerController.prototype = Object.create(BaseHeroSceneController.prototype);
    ImmutableLedgerController.prototype.constructor = ImmutableLedgerController;

    ImmutableLedgerController.prototype.buildScene = function () {
        this.camera.position.set(0, 2.0, 10.5);
        this.camera.lookAt(0, 0, 0);
        this.cameraInitialPos = this.camera.position.clone();

        var ambLight = new THREE.AmbientLight(0xF0F9FF, 1.2);
        var keyLight = new THREE.DirectionalLight(PALETTE.purple, 2.4);
        keyLight.position.set(5, 8, 7);
        var rimLight = new THREE.DirectionalLight(PALETTE.cyan, 1.6);
        rimLight.position.set(-5, -4, -5);
        this.scene.add(ambLight, keyLight, rimLight);

        // 19 Hexagonal Cryptographic Shields (Honeycomb Grid via InstancedMesh - 1 draw call!)
        var hexGeo = this.trackDisposable(new THREE.CylinderGeometry(1.0, 1.0, 0.35, 6));
        hexGeo.rotateX(Math.PI / 2);
        var hexMat = this.trackDisposable(new THREE.MeshStandardMaterial({
            color: PALETTE.purple,
            roughness: 0.3,
            metalness: 0.7
        }));
        this.hexInstanced = new THREE.InstancedMesh(hexGeo, hexMat, this.hexCount);

        // Arrange in honeycomb (radius spacing = 1.85)
        var coords = [
            [0, 0],
            // Ring 1 (6 hexes)
            [1.6, 0.92], [0, 1.85], [-1.6, 0.92], [-1.6, -0.92], [0, -1.85], [1.6, -0.92],
            // Ring 2 (12 hexes)
            [3.2, 1.85], [1.6, 2.77], [0, 3.7], [-1.6, 2.77], [-3.2, 1.85], [-3.2, 0],
            [-3.2, -1.85], [-1.6, -2.77], [0, -3.7], [1.6, -2.77], [3.2, -1.85], [3.2, 0]
        ];

        this.hexPositions = [];
        var dummy = new THREE.Object3D();
        var defaultColor = new THREE.Color(PALETTE.purple);

        for (var i = 0; i < this.hexCount; i++) {
            var cx = coords[i][0] * 0.9;
            var cy = coords[i][1] * 0.9;
            this.hexPositions.push(new THREE.Vector2(cx, cy));

            dummy.position.set(cx, cy, 0);
            dummy.updateMatrix();
            this.hexInstanced.setMatrixAt(i, dummy.matrix);
            this.hexInstanced.setColorAt(i, defaultColor);
        }
        this.hexInstanced.instanceMatrix.needsUpdate = true;
        this.hexInstanced.instanceColor.needsUpdate = true;
        this.rootGroup.add(this.hexInstanced);

        // Verification Laser Scan Line
        var scanGeo = this.trackDisposable(new THREE.PlaneGeometry(0.12, 8.5));
        var scanMat = this.trackDisposable(new THREE.MeshBasicMaterial({
            color: PALETTE.green,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.85
        }));
        this.scanPlane = new THREE.Mesh(scanGeo, scanMat);
        this.scanPlane.position.z = 0.25;
        this.rootGroup.add(this.scanPlane);

        return Promise.resolve();
    };

    ImmutableLedgerController.prototype.update = function (delta, elapsed) {
        // Laser Sweep
        if (this.scanPlane && this.hexInstanced) {
            this.scanX += delta * 2.8;
            if (this.scanX > 6.0) this.scanX = -6.0;
            this.scanPlane.position.x = this.scanX;

            // Flash blocks green as scanline sweeps over them
            var greenColor = new THREE.Color(PALETTE.green);
            var purpleColor = new THREE.Color(PALETTE.purple);
            var needsColorUpdate = false;

            for (var i = 0; i < this.hexCount; i++) {
                var dist = Math.abs(this.hexPositions[i].x - this.scanX);
                if (dist < 0.6) {
                    this.hexInstanced.setColorAt(i, greenColor);
                    needsColorUpdate = true;
                } else {
                    this.hexInstanced.setColorAt(i, purpleColor);
                    needsColorUpdate = true;
                }
            }
            if (needsColorUpdate) {
                this.hexInstanced.instanceColor.needsUpdate = true;
            }
        }
    };

    // =========================================================================
    // 6. SMART FACTORY TWIN CONTROLLER (Route: '/solutions', sceneId: 'smart_factory')
    // =========================================================================
    function SmartFactoryTwinController(manager) {
        BaseHeroSceneController.call(this, manager, 'smart_factory', 'The Smart Factory Twin');
        this.agvs = [];
        this.conveyors = [];
        this.hotspots = [];
    }
    SmartFactoryTwinController.prototype = Object.create(BaseHeroSceneController.prototype);
    SmartFactoryTwinController.prototype.constructor = SmartFactoryTwinController;

    SmartFactoryTwinController.prototype.buildScene = function () {
        this.camera.position.set(4.8, 6.2, 9.5);
        this.camera.lookAt(0, 0.5, 0);
        this.cameraInitialPos = this.camera.position.clone();

        var ambLight = new THREE.AmbientLight(0xF8FAFC, 1.3);
        var keyLight = new THREE.DirectionalLight(PALETTE.bluePrimary, 2.2);
        keyLight.position.set(8, 14, 8);
        var rimLight = new THREE.DirectionalLight(PALETTE.orangeDark, 1.2);
        rimLight.position.set(-6, 3, -6);
        this.scene.add(ambLight, keyLight, rimLight);

        // Facility Floor Plane
        var floorGeo = this.trackDisposable(new THREE.PlaneGeometry(14, 10));
        floorGeo.rotateX(-Math.PI / 2);
        var floorMat = this.trackDisposable(new THREE.MeshStandardMaterial({
            color: 0xF0F4F8,
            roughness: 0.6,
            metalness: 0.1
        }));
        this.rootGroup.add(new THREE.Mesh(floorGeo, floorMat));

        // 3 Conveyor Lanes
        for (var c = -2.5; c <= 2.5; c += 2.5) {
            var cGeo = this.trackDisposable(new THREE.BoxGeometry(10, 0.2, 0.8));
            var cMat = this.trackDisposable(new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.4 }));
            var lane = new THREE.Mesh(cGeo, cMat);
            lane.position.set(0, 0.1, c);
            this.rootGroup.add(lane);
            this.conveyors.push(lane);
        }

        // 4 AGV Vehicles patrolling
        var agvGeo = this.trackDisposable(new THREE.BoxGeometry(0.8, 0.4, 0.6));
        var agvMat = this.trackDisposable(new THREE.MeshStandardMaterial({ color: PALETTE.orange, roughness: 0.3 }));

        for (var a = 0; a < 4; a++) {
            var agv = new THREE.Mesh(agvGeo, agvMat);
            agv.userData = { angle: (a * Math.PI) / 2, speed: 0.5 + a * 0.1 };
            this.rootGroup.add(agv);
            this.agvs.push(agv);
        }

        // Telemetry Hotspots
        var spotConfigs = [
            { id: 'spot_press', label: 'Máy Dập Thủy Lực', mtbf: '4,200h', rul: '98.4%', pos: [-3, 1, -2] },
            { id: 'spot_pack', label: 'Dây Chuyền Đóng Gói', mtbf: '6,100h', rul: '99.1%', pos: [2, 1, 1] }
        ];

        var self = this;
        spotConfigs.forEach(function (sc) {
            var sGeo = self.trackDisposable(new THREE.RingGeometry(0.2, 0.35, 24));
            sGeo.rotateX(-Math.PI / 2);
            var sMat = self.trackDisposable(new THREE.MeshBasicMaterial({ color: PALETTE.cyan, side: THREE.DoubleSide }));
            var ring = new THREE.Mesh(sGeo, sMat);
            ring.position.set(sc.pos[0], sc.pos[1], sc.pos[2]);
            ring.userData = sc;
            self.rootGroup.add(ring);
            self.hotspots.push(ring);
            self.interactiveObjects.push(ring);
        });

        return Promise.resolve();
    };

    SmartFactoryTwinController.prototype.update = function (delta, elapsed) {
        // Patrol AGVs in loop
        this.agvs.forEach(function (agv) {
            agv.userData.angle += delta * agv.userData.speed;
            var rx = 4.2;
            var rz = 2.8;
            agv.position.x = Math.sin(agv.userData.angle) * rx;
            agv.position.z = Math.cos(agv.userData.angle) * rz;
            agv.position.y = 0.3;
            agv.rotation.y = agv.userData.angle + Math.PI / 2;
        });

        // Pulse Hotspots
        this.hotspots.forEach(function (h) {
            var scale = 1.0 + Math.sin(elapsed * 4.0) * 0.15;
            h.scale.set(scale, scale, scale);
        });
    };

    // =========================================================================
    // 7. BIONIC EYE CONTROLLER (Route: '/industries', sceneId: 'bionic_eye')
    // =========================================================================
    function BionicEyeController(manager) {
        BaseHeroSceneController.call(this, manager, 'bionic_eye', 'The Bionic Eye');
        this.gimbalGroup = null;
        this.irisBlades = [];
        this.reticleBox = null;
    }
    BionicEyeController.prototype = Object.create(BaseHeroSceneController.prototype);
    BionicEyeController.prototype.constructor = BionicEyeController;

    BionicEyeController.prototype.buildScene = function () {
        this.camera.position.set(0, 1.2, 8.5);
        this.camera.lookAt(0, 0, 0);
        this.cameraInitialPos = this.camera.position.clone();

        var ambLight = new THREE.AmbientLight(0xF0F9FF, 1.2);
        var keyLight = new THREE.DirectionalLight(PALETTE.cyan, 2.6);
        keyLight.position.set(5, 7, 6);
        var rimLight = new THREE.DirectionalLight(PALETTE.red, 1.1);
        rimLight.position.set(-5, -3, -5);
        this.scene.add(ambLight, keyLight, rimLight);

        this.gimbalGroup = new THREE.Group();
        this.rootGroup.add(this.gimbalGroup);

        // 5 Concentric Optical Lens Rings
        var radii = [2.2, 1.8, 1.4, 1.0, 0.6];
        var self = this;
        radii.forEach(function (r, idx) {
            var rGeo = self.trackDisposable(new THREE.TorusGeometry(r, 0.04, 16, 64));
            var rMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                color: (idx === 0) ? PALETTE.bluePrimary : PALETTE.cyan,
                roughness: 0.2,
                metalness: 0.8
            }));
            var ring = new THREE.Mesh(rGeo, rMat);
            ring.userData = { rotSpeed: (idx + 1) * 0.12 * (idx % 2 === 0 ? 1 : -1) };
            self.gimbalGroup.add(ring);
        });

        // 8 Iris Aperture Blades
        var bladeGeo = this.trackDisposable(new THREE.BoxGeometry(0.5, 0.08, 0.02));
        var bladeMat = this.trackDisposable(new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.4 }));
        for (var b = 0; b < 8; b++) {
            var blade = new THREE.Mesh(bladeGeo, bladeMat);
            var bAngle = (b / 8) * Math.PI * 2;
            blade.position.set(Math.cos(bAngle) * 0.45, Math.sin(bAngle) * 0.45, 0);
            blade.rotation.z = bAngle + 0.3;
            this.gimbalGroup.add(blade);
            this.irisBlades.push(blade);
        }

        // Laser Scanning Reticle Corners
        var boxGeo = this.trackDisposable(new THREE.BoxGeometry(3.2, 3.2, 0.2));
        var boxMat = this.trackDisposable(new THREE.MeshBasicMaterial({ color: PALETTE.cyan, wireframe: true, transparent: true, opacity: 0.5 }));
        this.reticleBox = new THREE.Mesh(boxGeo, boxMat);
        this.rootGroup.add(this.reticleBox);

        return Promise.resolve();
    };

    BionicEyeController.prototype.update = function (delta, elapsed) {
        // Track pointer directly
        if (this.gimbalGroup) {
            var targetRotX = -this.mouseNDC.y * 0.45;
            var targetRotY = this.mouseNDC.x * 0.55;
            this.gimbalGroup.rotation.x += (targetRotX - this.gimbalGroup.rotation.x) * 0.1;
            this.gimbalGroup.rotation.y += (targetRotY - this.gimbalGroup.rotation.y) * 0.1;
        }

        if (this.reticleBox) {
            this.reticleBox.position.x = this.mouseNDC.x * 1.5;
            this.reticleBox.position.y = this.mouseNDC.y * 1.0;
        }
    };

    // =========================================================================
    // 8. GLOBAL ADVISORY DESK CONTROLLER (Route: '/contactus', sceneId: 'global_advisory')
    // =========================================================================
    function GlobalAdvisoryDeskController(manager) {
        BaseHeroSceneController.call(this, manager, 'global_advisory', 'The Global Advisory Desk');
        this.globeGroup = null;
        this.centerPins = [];
        this.globeRadius = 3.0;
    }
    GlobalAdvisoryDeskController.prototype = Object.create(BaseHeroSceneController.prototype);
    GlobalAdvisoryDeskController.prototype.constructor = GlobalAdvisoryDeskController;

    GlobalAdvisoryDeskController.prototype.buildScene = function () {
        this.camera.position.set(0, 2.0, 9.8);
        this.camera.lookAt(0, 0, 0);
        this.cameraInitialPos = this.camera.position.clone();

        var ambLight = new THREE.AmbientLight(0xF8FAFC, 1.25);
        var keyLight = new THREE.DirectionalLight(PALETTE.bluePrimary, 2.5);
        keyLight.position.set(8, 10, 8);
        var solarLight = new THREE.DirectionalLight(PALETTE.orange, 1.5);
        solarLight.position.set(-8, 2, -6);
        this.scene.add(ambLight, keyLight, solarLight);

        this.globeGroup = new THREE.Group();
        this.rootGroup.add(this.globeGroup);

        // Holographic Wireframe Earth Globe
        var sphereGeo = this.trackDisposable(new THREE.SphereGeometry(this.globeRadius, 28, 28));
        var sphereMat = this.trackDisposable(new THREE.MeshBasicMaterial({
            color: PALETTE.blueIce,
            wireframe: true,
            transparent: true,
            opacity: 0.18
        }));
        this.globeGroup.add(new THREE.Mesh(sphereGeo, sphereMat));

        // 2,400 HoloEarth Dots
        var dotCount = 2400;
        var dotGeo = this.trackDisposable(new THREE.BufferGeometry());
        var dotPositions = new Float32Array(dotCount * 3);

        for (var i = 0; i < dotCount; i++) {
            var phi = Math.acos(-1 + (2 * i) / dotCount);
            var theta = Math.sqrt(dotCount * Math.PI) * phi;
            dotPositions[i * 3] = this.globeRadius * Math.cos(theta) * Math.sin(phi);
            dotPositions[i * 3 + 1] = this.globeRadius * Math.sin(theta) * Math.sin(phi);
            dotPositions[i * 3 + 2] = this.globeRadius * Math.cos(phi);
        }
        dotGeo.setAttribute('position', new THREE.BufferAttribute(dotPositions, 3));
        var dotMat = this.trackDisposable(new THREE.PointsMaterial({
            color: PALETTE.bluePrimary,
            size: 0.05,
            transparent: true,
            opacity: 0.75
        }));
        this.globeGroup.add(new THREE.Points(dotGeo, dotMat));

        // 5 Global R&D Center Pins (HAN, DAD, SGN, SIN, FRA)
        var centers = [
            { key: 'HAN', name: 'Hà Nội HQ', lat: 21.0285, lon: 105.8542, color: PALETTE.orange, sla: '15m' },
            { key: 'DAD', name: 'Đà Nẵng R&D', lat: 16.0544, lon: 108.2022, color: PALETTE.cyan, sla: '15m' },
            { key: 'SGN', name: 'TP. Hồ Chí Minh', lat: 10.8231, lon: 106.6297, color: PALETTE.bluePrimary, sla: '15m' },
            { key: 'SIN', name: 'Singapore Hub', lat: 1.3521, lon: 103.8198, color: PALETTE.purple, sla: '30m' },
            { key: 'FRA', name: 'Frankfurt Desk', lat: 50.1109, lon: 8.6821, color: PALETTE.green, sla: '1h' }
        ];

        var self = this;
        centers.forEach(function (c) {
            var phi = (90 - c.lat) * (Math.PI / 180);
            var theta = (c.lon + 180) * (Math.PI / 180);
            var x = -(self.globeRadius * Math.sin(phi) * Math.cos(theta));
            var z = self.globeRadius * Math.sin(phi) * Math.sin(theta);
            var y = self.globeRadius * Math.cos(phi);

            // Beacon pin sphere
            var pinGeo = self.trackDisposable(new THREE.SphereGeometry(0.14, 16, 16));
            var pinMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                color: c.color,
                emissive: c.color,
                emissiveIntensity: 0.5
            }));
            var pinMesh = new THREE.Mesh(pinGeo, pinMat);
            pinMesh.position.set(x, y, z);
            pinMesh.userData = c;

            // Vertical beacon riser
            var beamGeo = self.trackDisposable(new THREE.CylinderGeometry(0.02, 0.02, 0.8, 8));
            var beamMat = self.trackDisposable(new THREE.MeshBasicMaterial({ color: c.color, transparent: true, opacity: 0.7 }));
            var beamMesh = new THREE.Mesh(beamGeo, beamMat);
            beamMesh.position.copy(pinMesh.position).multiplyScalar(1.1);
            beamMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), pinMesh.position.clone().normalize());

            self.globeGroup.add(pinMesh);
            self.globeGroup.add(beamMesh);
            self.centerPins.push(pinMesh);
            self.interactiveObjects.push(pinMesh);
        });

        return Promise.resolve();
    };

    GlobalAdvisoryDeskController.prototype.update = function (delta, elapsed) {
        if (this.globeGroup) {
            this.globeGroup.rotation.y += delta * 0.12;
        }

        this.centerPins.forEach(function (p) {
            var pulse = 1.0 + Math.sin(elapsed * 5.0) * 0.2;
            p.scale.set(pulse, pulse, pulse);
        });
    };

    // =========================================================================
    // AUTOMATIC REGISTRATION INTO INNORIA HERO 3D MANAGER
    // =========================================================================
    if (InnoriaHero3DManager && typeof InnoriaHero3DManager.registerController === 'function') {
        InnoriaHero3DManager.registerController('sovereign_core', SovereignCoreController);
        InnoriaHero3DManager.registerController('/', SovereignCoreController);

        InnoriaHero3DManager.registerController('ascending_heritage', AscendingHeritageController);
        InnoriaHero3DManager.registerController('/about', AscendingHeritageController);

        InnoriaHero3DManager.registerController('enterprise_brain', EnterpriseBrainController);
        InnoriaHero3DManager.registerController('/platform', EnterpriseBrainController);

        InnoriaHero3DManager.registerController('builders_canvas', BuildersCanvasController);
        InnoriaHero3DManager.registerController('/no-code-platform', BuildersCanvasController);

        InnoriaHero3DManager.registerController('immutable_ledger', ImmutableLedgerController);
        InnoriaHero3DManager.registerController('/blockchain', ImmutableLedgerController);

        InnoriaHero3DManager.registerController('smart_factory', SmartFactoryTwinController);
        InnoriaHero3DManager.registerController('/solutions', SmartFactoryTwinController);

        InnoriaHero3DManager.registerController('bionic_eye', BionicEyeController);
        InnoriaHero3DManager.registerController('/industries', BionicEyeController);

        InnoriaHero3DManager.registerController('global_advisory', GlobalAdvisoryDeskController);
        InnoriaHero3DManager.registerController('/contactus', GlobalAdvisoryDeskController);
    }

    // Expose all controllers
    var ControllersBundle = {
        BaseHeroSceneController: BaseHeroSceneController,
        SovereignCoreController: SovereignCoreController,
        AscendingHeritageController: AscendingHeritageController,
        EnterpriseBrainController: EnterpriseBrainController,
        BuildersCanvasController: BuildersCanvasController,
        ImmutableLedgerController: ImmutableLedgerController,
        SmartFactoryTwinController: SmartFactoryTwinController,
        BionicEyeController: BionicEyeController,
        GlobalAdvisoryDeskController: GlobalAdvisoryDeskController
    };

    if (typeof window !== 'undefined') {
        window.InnoriaHeroControllers = ControllersBundle;
    }

    return ControllersBundle;
}));

// =========================================================================
// INNORIA HERO VIDEO SLIDER AUTO-INITIALIZER (BUNDLE SAFEGUARD)
// =========================================================================
(function () {
    if (typeof window === 'undefined') return;

    var THEMES = [
        { index: 0, name: 'DIGIFORCE', accent: '#00F0FF', glow: 'rgba(0, 240, 255, 0.4)' },
        { index: 1, name: 'MOJO AI', accent: '#FF8000', glow: 'rgba(255, 128, 0, 0.4)' },
        { index: 2, name: 'ZENCODE-ENT', accent: '#42E6C3', glow: 'rgba(66, 230, 195, 0.4)' },
        { index: 3, name: 'INSILOS ERP', accent: '#00F0FF', glow: 'rgba(0, 240, 255, 0.4)' }
    ];

    function InnoriaHeroVideoSlider(container) {
        if (!container || container.__innoria_hero_slider_initialized) return;
        container.__innoria_hero_slider_initialized = true;

        this.container = container;
        this.videoLayers = Array.prototype.slice.call(container.querySelectorAll('.video-slide-layer'));
        this.slideItems = Array.prototype.slice.call(container.querySelectorAll('.hero-slide-item'));
        this.tabBtns = Array.prototype.slice.call(container.querySelectorAll('.hero-product-tab-btn'));
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

        this.totalSlides = Math.max(this.slideItems.length, this.videoLayers.length, 4);
        this.currentIndex = 0;
        this.slideDuration = 6500;
        this.isPlaying = true;
        this.isMuted = true;
        this.isHoverPaused = false;
        this.startTime = null;
        this.pausedProgress = 0;
        this.rafId = null;

        this._bindEvents();
        this._initVideos();
        this.goToSlide(0, true);
        this._startCycle();
    }

    InnoriaHeroVideoSlider.prototype._initVideos = function () {
        var self = this;
        this.videoLayers.forEach(function (video) {
            video.muted = self.isMuted;
            video.playsInline = true;
            video.loop = true;
            video.preload = 'auto';
            var p = video.play();
            if (p !== undefined) p.catch(function () {});
        });
    };

    InnoriaHeroVideoSlider.prototype.goToSlide = function (targetIdx, immediate) {
        var self = this;
        if (targetIdx < 0) targetIdx = this.totalSlides - 1;
        if (targetIdx >= this.totalSlides) targetIdx = 0;

        this.currentIndex = targetIdx;
        var theme = THEMES[targetIdx] || THEMES[0];

        this.videoLayers.forEach(function (vid, idx) {
            if (idx === targetIdx) {
                vid.classList.add('active');
                if (vid.paused && self.isPlaying) {
                    try { vid.play().catch(function () {}); } catch (e) {}
                }
            } else {
                vid.classList.remove('active');
            }
        });

        this.slideItems.forEach(function (slide, idx) {
            if (idx === targetIdx) {
                slide.classList.add('active');
            } else {
                slide.classList.remove('active');
            }
        });

        if (this.ambientGlow) {
            this.ambientGlow.style.background = 'radial-gradient(circle, ' + theme.glow + ' 0%, transparent 70%)';
        }

        this.tabBtns.forEach(function (tab, idx) {
            if (idx === targetIdx) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        this.progressFills.forEach(function (fill) {
            fill.style.width = '0%';
        });

        if (this.hudCounter) {
            var currStr = (targetIdx + 1) < 10 ? '0' + (targetIdx + 1) : (targetIdx + 1);
            var totalStr = this.totalSlides < 10 ? '0' + this.totalSlides : this.totalSlides;
            this.hudCounter.textContent = currStr + ' / ' + totalStr;
        }

        this.pausedProgress = 0;
        this.startTime = performance.now();
    };

    InnoriaHeroVideoSlider.prototype._startCycle = function () {
        var self = this;
        if (this.rafId) cancelAnimationFrame(this.rafId);

        function tick(now) {
            if (!self.startTime) self.startTime = now;

            if (self.isPlaying && !self.isHoverPaused) {
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

    InnoriaHeroVideoSlider.prototype.nextSlide = function () {
        this.goToSlide((this.currentIndex + 1) % this.totalSlides);
    };

    InnoriaHeroVideoSlider.prototype.prevSlide = function () {
        this.goToSlide((this.currentIndex - 1 + this.totalSlides) % this.totalSlides);
    };

    InnoriaHeroVideoSlider.prototype.togglePlayPause = function () {
        this.isPlaying = !this.isPlaying;
        if (this.isPlaying) {
            this.startTime = performance.now();
            if (this.playPauseIcon) {
                this.playPauseIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-pause"/>';
            }
            if (this.playPauseBtn) this.playPauseBtn.title = 'Tạm dừng';
            var activeVideo = this.videoLayers[this.currentIndex];
            if (activeVideo && activeVideo.paused) activeVideo.play().catch(function () {});
            this._startCycle();
        } else {
            if (this.playPauseIcon) {
                this.playPauseIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-play"/>';
            }
            if (this.playPauseBtn) this.playPauseBtn.title = 'Tiếp tục phát';
            var currVideo = this.videoLayers[this.currentIndex];
            if (currVideo && !currVideo.paused) currVideo.pause();
        }
    };

    InnoriaHeroVideoSlider.prototype.toggleMute = function () {
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

    InnoriaHeroVideoSlider.prototype._bindEvents = function () {
        var self = this;
        this.tabBtns.forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                var targetIdx = parseInt(btn.getAttribute('data-tab-target'), 10);
                if (!isNaN(targetIdx)) self.goToSlide(targetIdx);
            });
        });

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
        if (this.contentStage) {
            this.contentStage.addEventListener('mouseenter', function () {
                self.isHoverPaused = true;
            });
            this.contentStage.addEventListener('mouseleave', function () {
                self.isHoverPaused = false;
                self.startTime = performance.now();
            });
        }
    };

    function autoMount() {
        var heroEl = document.querySelector('#innoria_hero_cover, .innoria-hero-slider-section');
        if (heroEl && !heroEl.__innoria_hero_slider_initialized) {
            window.innoriaHeroSlider = new InnoriaHeroVideoSlider(heroEl);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoMount);
    } else {
        autoMount();
    }

    window.InnoriaHeroVideoSlider = InnoriaHeroVideoSlider;
})();

