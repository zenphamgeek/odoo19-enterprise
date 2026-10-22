/**
 * Innoria Sovereign Multi-Agent AI & Cloud Topology 3D Engine
 * File: innoria_topology_3d.js
 * Host Target: innoria.insilos.com (Insilos Sovereign Three.js Suite)
 * 
 * Architectural Concept:
 * 1. Centerpiece: Authentic 3D Kinetic Sculpture of the Innoria Logo
 *    - Continuous Parametric Möbius Ribbon / Helix Vortex in Electric Cyan (#0ABBDB / #00F2FE)
 *    - 3 Signature Orbiting Orange Comets (#FF8000) tracing genuine logo orbital paths
 *    - Central Quantum Luminescence Core
 * 
 * 2. 4 Sovereign Service Architecture Pods (Kiến Trúc Dịch Vụ):
 *    - DIGIFORCE: No-Code/Low-Code Hyper-App Matrix (4 Cascading Stepped Tiers: 3h -> 3d -> 3w -> 3m)
 *    - MOJO AI: Autonomous Neural Swarm Core (VLM See-Detect-Analyze-Adapt with 6 synapsing agent nodes)
 *    - MOJOVERSE: Enterprise Blockchain Trust Monolith (Interlocking Hash-Chain Blocks & Consensus Rings)
 *    - INTELLIGENT ERP: Enterprise Cloud Hub (4 Architecture Pillars, Unified Data Sphere & Supply Chain Conduits)
 * 
 * 3. Dual-Mode Architecture View:
 *    - Mode 'topology': Orbital Logo Sculpture & Swarm Constellation
 *    - Mode 'stack': Isometric 3D Multi-Tier Service Architecture Stack (Cloud Infra -> Core Engines -> Enterprise Apps)
 * 
 * Performance: 60 FPS, WebGL 2.0 / 1.0 Fallback, Garbage-Collection Free Render Loop
 * Accessibility: WCAG AAA High Contrast Overlays, Keyboard & Pointer Safe, Responsive Viewports
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['three'], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('three'));
    } else {
        root.InnoriaTopologyEngine = factory(root.THREE || (root.InsilosThreeBundle && root.InsilosThreeBundle.THREE));
    }
}(typeof self !== 'undefined' ? self : this, function (THREE) {
    'use strict';

    if (!THREE) {
        console.error('[InnoriaTopology3D] Fatal: Three.js library not detected in global scope.');
        return null;
    }

    // =========================================================================
    // 1. BRAND PALETTE & ARCHITECTURAL CONTRACTS
    // =========================================================================

    const BRAND_PALETTE = {
        electricSapphire: 0x0284C7, // Corporate ocean blue (#0284C7)
        mintCyan: 0x0ABBDB,         // Official Innoria Cyan (#0ABBDB)
        techCyan: 0x00F2FE,         // High-intensity neon cyan (#00F2FE)
        vividAzure: 0x38BDF8,       // Light sky cyan (#38BDF8)
        warmAmber: 0xFF8000,        // Official Innoria Logo Orange (#FF8000)
        warmAmberGlow: 0xF59E0B,    // Radiant golden amber (#F59E0B)
        emeraldGreen: 0x10B981,     // Industrial telemetry emerald (#10B981)
        darkObsidian: 0x070B14,     // Cyber Dark base canvas (#070B14)
        deepSlate: 0x0F1E36,        // Deep card background (#0F1E36)
        pedestalBase: 0x0A1424,     // Architecture pedestal surface (#0A1424)
        gridLines: 0x0F294A,        // Deep blue coordinate grid (#0F294A)
        whiteHighContrast: 0xFFFFFF // Crisp white (#FFFFFF)
    };

    const TOPOLOGY_NODES_DATA = [
        {
            id: 'node_digiforce',
            key: 'DIGIFORCE',
            name: 'DIGIFORCE Sovereign Platform',
            category: 'No-Code / Low-Code Hyper-App Engine',
            color: BRAND_PALETTE.mintCyan,
            accentColor: BRAND_PALETTE.electricSapphire,
            orbitAngle: 0.15, // Approx 9 deg
            radius: 6.8,
            stackPos: new THREE.Vector3(-3.8, 2.2, 0), // Upper left in architecture stack
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
            color: BRAND_PALETTE.techCyan,
            accentColor: BRAND_PALETTE.vividAzure,
            orbitAngle: Math.PI * 0.55, // Approx 99 deg
            radius: 6.8,
            stackPos: new THREE.Vector3(3.8, 2.2, 0), // Upper right in architecture stack
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
            color: '#42E6C3',
            accentColor: '#00F0FF',
            orbitAngle: Math.PI * 1.15, // Approx 207 deg
            radius: 6.8,
            stackPos: new THREE.Vector3(-3.8, -1.8, 0), // Lower left in architecture stack
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
            color: BRAND_PALETTE.electricCyan,
            accentColor: BRAND_PALETTE.emeraldGreen,
            orbitAngle: Math.PI * 1.65, // Approx 297 deg
            radius: 6.8,
            stackPos: new THREE.Vector3(3.8, -1.8, 0), // Lower right in architecture stack
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
            deepLink: '/insilos-erp'
        }
    ];

    // =========================================================================
    // 2. PROCEDURAL INNORIA LOGO MÖBIUS CURVE
    // =========================================================================

    function createInnoriaLogoHelixCurve() {
        const points = [];
        const segments = 128;
        // Asymmetric 3D Möbius / Infinity vortex representing the Innoria 'i' loop
        for (let i = 0; i <= segments; i++) {
            const u = (i / segments) * Math.PI * 2;
            const x = 2.3 * Math.sin(u) + 0.65 * Math.sin(2 * u);
            const y = 1.7 * Math.cos(u) + 0.4 * Math.sin(3 * u);
            const z = 1.15 * Math.sin(2 * u) * Math.cos(u);
            points.push(new THREE.Vector3(x, y, z));
        }
        const CurveClass = THREE.CatmullRomCurve3 || THREE.CatmullRomCurve3D;
        return new CurveClass(points, true);
    }

    // =========================================================================
    // 3. MAIN TOPOLOGY ENGINE CLASS
    // =========================================================================

    class InnoriaTopologyEngine {
        constructor(container, options = {}) {
            if (!container) {
                throw new Error('[InnoriaTopology3D] Target container element is null or undefined.');
            }

            this.container = container;
            this.options = Object.assign({
                autoRotate: true,
                autoRotateSpeed: 0.5,
                particleCount: 500,
                pulsePacketCount: 16,
                hudElementId: 'innoriaTopologyHUD',
                architectureMode: false // 'topology' (orbital) vs 'stack' (layered)
            }, options);

            this.currentMode = this.options.architectureMode ? 'stack' : 'topology';
            this._animFrameId = null;
            this._clock = new THREE.Clock();
            this._listeners = {};

            this._hoveredNode = null;
            this._selectedNode = null;
            this._pointerDownPos = new THREE.Vector2();

            this._initRenderer();
            this._initScene();
            this._initCameraAndControls();
            this._initLights();

            // Construct 3D Visual Architecture
            this._buildCentralLogoSculpture();
            this._buildArchitecturalServicePods();
            this._buildDataConduits();
            this._buildCosmicDust();
            this._buildArchitectureStackPlates();

            this._initRaycasting();
            this._bindDOMHUD();
            this._bindControlButtons();

            this._onResize = this._handleResize.bind(this);
            window.addEventListener('resize', this._onResize, { passive: true });

            this.start();
        }

        // ---------------------------------------------------------------------
        // INITIALIZATION: RENDERER, SCENE, CAMERA, LIGHTS
        // ---------------------------------------------------------------------

        _initRenderer() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 520;

            this.renderer = new THREE.WebGLRenderer({
                antialias: (window.devicePixelRatio || 1) < 2,
                powerPreference: 'high-performance',
                alpha: true,
                precision: 'mediump'
            });

            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.0));
            this.renderer.setSize(width, height);
            this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
            this.renderer.toneMappingExposure = 1.35;

            this.domElement = this.renderer.domElement;
            this.domElement.className = 'innoria-topology-canvas w-100 h-100 position-relative';
            this.domElement.setAttribute('role', 'img');
            this.domElement.setAttribute('aria-label', 'Innoria 3D Sovereign Logo Sculpture & Service Architecture Topology');
            this.container.appendChild(this.domElement);
        }

        _initScene() {
            this.scene = new THREE.Scene();
            this.scene.fog = new THREE.FogExp2(BRAND_PALETTE.darkObsidian, 0.016);

            // Ground Coordinate Grid (XZ Plane)
            const grid = new THREE.GridHelper(34, 48, BRAND_PALETTE.mintCyan, BRAND_PALETTE.gridLines);
            grid.position.y = -3.8;
            grid.material.opacity = 0.55;
            grid.material.transparent = true;
            this.scene.add(grid);

            // Orbital boundary coordinate ring (15 degree inclination)
            const outerRingGeo = new THREE.RingGeometry(6.75, 6.85, 96);
            const outerRingMat = new THREE.MeshBasicMaterial({
                color: BRAND_PALETTE.mintCyan,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.28
            });
            this.orbitalPlaneMesh = new THREE.Mesh(outerRingGeo, outerRingMat);
            this.orbitalPlaneMesh.rotation.x = Math.PI / 2 + 0.22;
            this.scene.add(this.orbitalPlaneMesh);
        }

        _initCameraAndControls() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 520;
            const aspect = width / height;

            this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 100);
            this.defaultCameraPos = new THREE.Vector3(0, 2.2, 14.2);
            this.stackCameraPos = new THREE.Vector3(0, 3.8, 15.6);
            this.camera.position.copy(this.defaultCameraPos);

            this.controlsTarget = new THREE.Vector3(0, 0, 0);

            if (THREE.OrbitControls) {
                this.controls = new THREE.OrbitControls(this.camera, this.domElement);
                this.controls.enableDamping = true;
                this.controls.dampingFactor = 0.05;
                this.controls.minDistance = 4.5;
                this.controls.maxDistance = 28.0;
                this.controls.maxPolarAngle = Math.PI / 2 + 0.12;
                this.controls.autoRotate = this.options.autoRotate;
                this.controls.autoRotateSpeed = this.options.autoRotateSpeed;
                this.controls.target.copy(this.controlsTarget);
            }
        }

        _initLights() {
            const ambient = new THREE.AmbientLight(0x0F1E36, 2.2);
            this.scene.add(ambient);

            // Core Point Lights (Dual Tone Cyan & Warm Amber)
            const coreCyanLight = new THREE.PointLight(BRAND_PALETTE.mintCyan, 4.8, 28);
            coreCyanLight.position.set(0, 0, 1.2);
            this.scene.add(coreCyanLight);

            const coreAmberLight = new THREE.PointLight(BRAND_PALETTE.warmAmber, 3.2, 22);
            coreAmberLight.position.set(0, 0.8, -1.5);
            this.scene.add(coreAmberLight);

            // Directional Rim Lights for Sculptural Lustre
            const rim1 = new THREE.DirectionalLight(BRAND_PALETTE.techCyan, 2.0);
            rim1.position.set(10, 14, 12);
            this.scene.add(rim1);

            const rim2 = new THREE.DirectionalLight(BRAND_PALETTE.warmAmberGlow, 1.4);
            rim2.position.set(-12, -6, -10);
            this.scene.add(rim2);
        }

        // ---------------------------------------------------------------------
        // 4. THE INNORIA LOGO 3D KINETIC SCULPTURE (CENTERPIECE)
        // ---------------------------------------------------------------------

        _buildCentralLogoSculpture() {
            this.logoGroup = new THREE.Group();
            this.logoGroup.name = 'Innoria_3D_Logo_Sculpture';

            const logoCurve = createInnoriaLogoHelixCurve();
            this.logoCurve = logoCurve;

            // 1. Primary Glass-Metallic Ribbon
            const mainTubeGeo = new THREE.TubeGeometry(logoCurve, 128, 0.17, 16, true);
            this.logoMainMat = new THREE.MeshStandardMaterial({
                color: BRAND_PALETTE.mintCyan,
                emissive: BRAND_PALETTE.electricSapphire,
                emissiveIntensity: 0.85,
                metalness: 0.92,
                roughness: 0.12
            });
            this.logoMainMesh = new THREE.Mesh(mainTubeGeo, this.logoMainMat);
            this.logoGroup.add(this.logoMainMesh);

            // 2. High-Luminescence Inner Laser Filament
            const laserTubeGeo = new THREE.TubeGeometry(logoCurve, 128, 0.05, 8, true);
            const laserMat = new THREE.MeshBasicMaterial({
                color: BRAND_PALETTE.techCyan,
                transparent: true,
                opacity: 0.95
            });
            this.logoLaserMesh = new THREE.Mesh(laserTubeGeo, laserMat);
            this.logoGroup.add(this.logoLaserMesh);

            // 3. Cybernetic Holographic Wireframe Envelope
            const wireTubeGeo = new THREE.TubeGeometry(logoCurve, 64, 0.30, 6, true);
            const wireMat = new THREE.MeshBasicMaterial({
                color: BRAND_PALETTE.mintCyan,
                wireframe: true,
                transparent: true,
                opacity: 0.28
            });
            this.logoWireMesh = new THREE.Mesh(wireTubeGeo, wireMat);
            this.logoGroup.add(this.logoWireMesh);

            // 4. Central Quantum Energy Nucleus (Prism at center of loop)
            const nucleusGeo = new THREE.OctahedronGeometry(0.72, 1);
            const nucleusMat = new THREE.MeshStandardMaterial({
                color: BRAND_PALETTE.techCyan,
                emissive: BRAND_PALETTE.mintCyan,
                emissiveIntensity: 0.9,
                metalness: 0.85,
                roughness: 0.15
            });
            this.nucleusMesh = new THREE.Mesh(nucleusGeo, nucleusMat);
            this.logoGroup.add(this.nucleusMesh);

            // 5. The 3 Signature Orbiting Orange Logo Comets (#FF8000)
            this.logoComets = [];

            // Comet 1: Inner Curve Glider (travels directly on the Möbius spline)
            const c1Geo = new THREE.SphereGeometry(0.24, 16, 16);
            const c1Mat = new THREE.MeshStandardMaterial({
                color: BRAND_PALETTE.warmAmber,
                emissive: BRAND_PALETTE.warmAmber,
                emissiveIntensity: 1.0,
                roughness: 0.1
            });
            const comet1 = new THREE.Mesh(c1Geo, c1Mat);
            this.logoGroup.add(comet1);
            this.logoComets.push({ mesh: comet1, type: 'spline', progress: 0.0, speed: 0.18 });

            // Comet 2: Apex Orbital Halo (orbits at top apex)
            const c2Geo = new THREE.SphereGeometry(0.19, 16, 16);
            const comet2 = new THREE.Mesh(c2Geo, c1Mat.clone());
            this.logoGroup.add(comet2);
            this.logoComets.push({ mesh: comet2, type: 'orbit_apex', angle: 0.0, radius: 2.7, height: 1.2, speed: 0.32 });

            // Comet 3: Sweeping Equatorial Spark (sweeps around base vortex)
            const c3Geo = new THREE.SphereGeometry(0.16, 16, 16);
            const comet3 = new THREE.Mesh(c3Geo, c1Mat.clone());
            this.logoGroup.add(comet3);
            this.logoComets.push({ mesh: comet3, type: 'orbit_base', angle: Math.PI, radius: 3.2, height: -0.8, speed: 0.24 });

            // Light Halos for the comets
            this.cometLight = new THREE.PointLight(BRAND_PALETTE.warmAmber, 2.5, 8);
            this.logoGroup.add(this.cometLight);

            this.scene.add(this.logoGroup);
        }

        // ---------------------------------------------------------------------
        // 5. THE 4 SERVICE ARCHITECTURE PODS (KIẾN TRÚC DỊCH VỤ)
        // ---------------------------------------------------------------------

        _buildArchitecturalServicePods() {
            this.satelliteNodes = [];
            this.interactiveObjects = [];

            TOPOLOGY_NODES_DATA.forEach((data, index) => {
                const podGroup = new THREE.Group();
                podGroup.name = data.id;
                podGroup.userData = {
                    nodeData: data,
                    isPod: true,
                    index: index,
                    orbitAngle: data.orbitAngle,
                    radius: data.radius,
                    stackPos: data.stackPos
                };

                // 1. High-Tech Hexagonal Glass Pedestal Base
                const pedestalGeo = new THREE.CylinderGeometry(1.25, 1.45, 0.18, 6);
                const pedestalMat = new THREE.MeshStandardMaterial({
                    color: BRAND_PALETTE.pedestalBase,
                    emissive: data.color,
                    emissiveIntensity: 0.32,
                    metalness: 0.85,
                    roughness: 0.25
                });
                const pedestal = new THREE.Mesh(pedestalGeo, pedestalMat);
                pedestal.position.y = -0.55;
                podGroup.add(pedestal);

                // Neon Edge Bevel on Pedestal
                const pedestalEdgeGeo = new THREE.RingGeometry(1.26, 1.34, 6);
                const pedestalEdgeMat = new THREE.MeshBasicMaterial({
                    color: data.color,
                    side: THREE.DoubleSide,
                    transparent: true,
                    opacity: 0.75
                });
                const pedestalEdge = new THREE.Mesh(pedestalEdgeGeo, pedestalEdgeMat);
                pedestalEdge.rotation.x = Math.PI / 2;
                pedestalEdge.position.y = -0.45;
                podGroup.add(pedestalEdge);

                // 2. Specialized Semantic Micro-Architecture
                const architectureCore = new THREE.Group();

                switch (data.key) {
                    case 'DIGIFORCE': {
                        // 4 Stepped Cascading Glass Slabs (3h -> 3d -> 3w -> 3m)
                        for (let s = 0; s < 4; s++) {
                            const slabWidth = 1.1 - (s * 0.15);
                            const slabGeo = new THREE.BoxGeometry(slabWidth, 0.10, slabWidth);
                            const slabMat = new THREE.MeshStandardMaterial({
                                color: (s % 2 === 0) ? data.color : BRAND_PALETTE.electricSapphire,
                                emissive: data.color,
                                emissiveIntensity: 0.45 + (s * 0.12),
                                metalness: 0.8,
                                roughness: 0.2,
                                transparent: true,
                                opacity: 0.88
                            });
                            const slab = new THREE.Mesh(slabGeo, slabMat);
                            slab.position.y = -0.3 + (s * 0.22);
                            slab.rotation.y = s * (Math.PI / 8);
                            architectureCore.add(slab);
                        }
                        // Top Lightning / Rapid Synth Node
                        const topGlyphGeo = new THREE.OctahedronGeometry(0.28, 0);
                        const topGlyphMat = new THREE.MeshBasicMaterial({ color: BRAND_PALETTE.techCyan });
                        const topGlyph = new THREE.Mesh(topGlyphGeo, topGlyphMat);
                        topGlyph.position.y = 0.75;
                        architectureCore.add(topGlyph);
                        break;
                    }

                    case 'MOJO_AI': {
                        // Neural Multi-Agent Swarm Core & VLM Vision Sensor
                        const brainGeo = new THREE.IcosahedronGeometry(0.72, 1);
                        const brainMat = new THREE.MeshStandardMaterial({
                            color: data.color,
                            emissive: BRAND_PALETTE.electricSapphire,
                            emissiveIntensity: 0.65,
                            metalness: 0.9,
                            roughness: 0.15
                        });
                        const brain = new THREE.Mesh(brainGeo, brainMat);
                        architectureCore.add(brain);

                        // 6 Orbiting Swarm Micro-Agents
                        podGroup.userData.swarmAgents = [];
                        for (let a = 0; a < 6; a++) {
                            const agentGeo = new THREE.SphereGeometry(0.09, 8, 8);
                            const agentMat = new THREE.MeshBasicMaterial({ color: BRAND_PALETTE.techCyan });
                            const agentMesh = new THREE.Mesh(agentGeo, agentMat);
                            architectureCore.add(agentMesh);
                            podGroup.userData.swarmAgents.push({
                                mesh: agentMesh,
                                radius: 1.15,
                                angleOffset: a * (Math.PI / 3),
                                speed: 0.8 + (a * 0.15)
                            });
                        }
                        break;
                    }

                    case 'ZENCODE_ENT':
                    case 'MOJOVERSE': {
                        // Interlocking Cryptographic Hash-Chain Blocks & Consensus Rings
                        for (let b = 0; b < 3; b++) {
                            const bGeo = new THREE.BoxGeometry(0.55, 0.55, 0.55);
                            const bMat = new THREE.MeshStandardMaterial({
                                color: '#42E6C3',
                                emissive: '#00F0FF',
                                emissiveIntensity: 0.6,
                                metalness: 0.85,
                                roughness: 0.2
                            });
                            const block = new THREE.Mesh(bGeo, bMat);
                            block.position.set((b - 1) * 0.42, (b - 1) * 0.32, (b - 1) * 0.2);
                            block.rotation.set(b * 0.2, b * 0.3, b * 0.1);
                            architectureCore.add(block);
                        }

                        // Rotating Consensus Torus Ring
                        const consensusGeo = new THREE.TorusGeometry(1.05, 0.022, 16, 48);
                        const consensusMat = new THREE.MeshBasicMaterial({
                            color: '#42E6C3',
                            transparent: true,
                            opacity: 0.85
                        });
                        const consensusRing = new THREE.Mesh(consensusGeo, consensusMat);
                        consensusRing.rotation.x = Math.PI / 2.5;
                        architectureCore.add(consensusRing);
                        podGroup.userData.consensusRing = consensusRing;
                        break;
                    }

                    case 'INSILOS':
                    case 'INTELLIGENT_ERP': {
                        // 4 Enterprise Architecture Pillars supporting Unified Data Core
                        for (let p = 0; p < 4; p++) {
                            const angle = p * (Math.PI / 2);
                            const pillarGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.85, 8);
                            const pillarMat = new THREE.MeshStandardMaterial({
                                color: BRAND_PALETTE.pedestalBase,
                                emissive: BRAND_PALETTE.emeraldGreen,
                                emissiveIntensity: 0.4,
                                metalness: 0.9,
                                roughness: 0.2
                            });
                            const pillar = new THREE.Mesh(pillarGeo, pillarMat);
                            pillar.position.set(Math.cos(angle) * 0.65, 0, Math.sin(angle) * 0.65);
                            architectureCore.add(pillar);
                        }

                        // Floating Central Sovereign Data Sphere (Single Source of Truth)
                        const erpCoreGeo = new THREE.SphereGeometry(0.48, 16, 16);
                        const erpCoreMat = new THREE.MeshStandardMaterial({
                            color: BRAND_PALETTE.electricSapphire,
                            emissive: BRAND_PALETTE.emeraldGreen,
                            emissiveIntensity: 0.7,
                            metalness: 0.8,
                            roughness: 0.2
                        });
                        const erpCore = new THREE.Mesh(erpCoreGeo, erpCoreMat);
                        architectureCore.add(erpCore);

                        // Latitudinal telemetry ring
                        const teleRingGeo = new THREE.RingGeometry(0.68, 0.72, 32);
                        const teleRingMat = new THREE.MeshBasicMaterial({
                            color: BRAND_PALETTE.emeraldGreen,
                            side: THREE.DoubleSide,
                            transparent: true,
                            opacity: 0.75
                        });
                        const teleRing = new THREE.Mesh(teleRingGeo, teleRingMat);
                        teleRing.rotation.x = Math.PI / 2;
                        architectureCore.add(teleRing);
                        break;
                    }
                }

                podGroup.add(architectureCore);
                podGroup.userData.architectureCore = architectureCore;

                // 3. Status Beacon Ring
                const beaconGeo = new THREE.RingGeometry(1.4, 1.48, 32);
                const beaconMat = new THREE.MeshBasicMaterial({
                    color: data.color,
                    side: THREE.DoubleSide,
                    transparent: true,
                    opacity: 0.55
                });
                const beacon = new THREE.Mesh(beaconGeo, beaconMat);
                beacon.rotation.x = Math.PI / 2;
                beacon.position.y = -0.52;
                podGroup.add(beacon);

                // 4. Invisible Expanded Raycaster Hit Sphere (Smooth interaction on Mobile & Desktop)
                const hitSphereGeo = new THREE.SphereGeometry(1.8, 16, 16);
                const hitSphereMat = new THREE.MeshBasicMaterial({ visible: false });
                const hitSphere = new THREE.Mesh(hitSphereGeo, hitSphereMat);
                hitSphere.userData = { parentGroup: podGroup, nodeData: data };
                podGroup.add(hitSphere);

                this.scene.add(podGroup);
                this.satelliteNodes.push(podGroup);
                this.interactiveObjects.push(hitSphere);
            });
        }

        // ---------------------------------------------------------------------
        // 6. DUAL DATA CONDUITS (CYBERNETIC BUSES)
        // ---------------------------------------------------------------------

        _buildDataConduits() {
            this.conduitBuses = [];
            this.packetParticles = [];

            TOPOLOGY_NODES_DATA.forEach((data, index) => {
                const targetPos = this._calculateOrbitalPosition(data.orbitAngle, data.radius, 0);

                // Quadratic Bezier Conduit from Logo Core to Pod
                const midPoint = new THREE.Vector3(
                    targetPos.x * 0.45,
                    targetPos.y * 0.45 + 1.4,
                    targetPos.z * 0.45
                );

                const curve = new THREE.QuadraticBezierCurve3(
                    new THREE.Vector3(0, 0, 0),
                    midPoint,
                    targetPos
                );

                // Translucent Glass Conduit Tube
                const tubeGeo = new THREE.TubeGeometry(curve, 36, 0.032, 8, false);
                const tubeMat = new THREE.MeshBasicMaterial({
                    color: data.color,
                    transparent: true,
                    opacity: 0.32
                });
                const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
                this.scene.add(tubeMesh);

                this.conduitBuses.push({
                    curve: curve,
                    tubeMesh: tubeMesh,
                    nodeIndex: index,
                    targetPos: targetPos
                });

                // Discrete Glowing Data Packets
                for (let p = 0; p < this.options.pulsePacketCount; p++) {
                    const packetGeo = new THREE.SphereGeometry(0.075, 8, 8);
                    const packetMat = new THREE.MeshBasicMaterial({
                        color: (p % 2 === 0) ? BRAND_PALETTE.techCyan : data.color,
                        transparent: true,
                        opacity: 0.95
                    });
                    const packetMesh = new THREE.Mesh(packetGeo, packetMat);
                    this.scene.add(packetMesh);

                    this.packetParticles.push({
                        mesh: packetMesh,
                        curveIndex: index,
                        progress: p / this.options.pulsePacketCount,
                        speed: 0.09 + (index * 0.015)
                    });
                }
            });
        }

        // ---------------------------------------------------------------------
        // 7. ARCHITECTURE STACK PLATES (ISOMETRIC MULTI-TIER MODE)
        // ---------------------------------------------------------------------

        _buildArchitectureStackPlates() {
            this.stackPlatesGroup = new THREE.Group();
            this.stackPlatesGroup.name = 'Innoria_Architecture_Stack_Plates';
            this.stackPlatesGroup.visible = false;

            const tiers = [
                { y: 3.2, label: 'TẦNG 3: GIẢI PHÁP VẬN HÀNH & AI AGENTS', color: BRAND_PALETTE.mintCyan },
                { y: 0.0, label: 'TẦNG 2: 4 ĐỘNG CƠ CÔNG NGHỆ LÕI (CORE ENGINES)', color: BRAND_PALETTE.electricSapphire },
                { y: -3.2, label: 'TẦNG 1: NỀN TẢNG CLOUD, K8S & AIR-GAPPED DB', color: BRAND_PALETTE.gridLines }
            ];

            tiers.forEach((t) => {
                const plateGeo = new THREE.PlaneGeometry(16, 7);
                const plateMat = new THREE.MeshBasicMaterial({
                    color: t.color,
                    transparent: true,
                    opacity: 0.08,
                    side: THREE.DoubleSide
                });
                const plateMesh = new THREE.Mesh(plateGeo, plateMat);
                plateMesh.rotation.x = Math.PI / 2;
                plateMesh.position.y = t.y;
                this.stackPlatesGroup.add(plateMesh);

                // Wireframe perimeter
                const borderGeo = new THREE.EdgesGeometry(plateGeo);
                const borderMat = new THREE.LineBasicMaterial({
                    color: t.color,
                    transparent: true,
                    opacity: 0.4
                });
                const border = new THREE.LineSegments(borderGeo, borderMat);
                border.rotation.x = Math.PI / 2;
                border.position.y = t.y;
                this.stackPlatesGroup.add(border);
            });

            this.scene.add(this.stackPlatesGroup);
        }

        _buildCosmicDust() {
            const count = this.options.particleCount;
            const geometry = new THREE.BufferGeometry();
            const positions = new Float32Array(count * 3);
            const colors = new Float32Array(count * 3);

            const cSapphire = new THREE.Color(BRAND_PALETTE.electricSapphire);
            const cMint = new THREE.Color(BRAND_PALETTE.mintCyan);
            const cAmber = new THREE.Color(BRAND_PALETTE.warmAmber);

            for (let i = 0; i < count; i++) {
                const phi = Math.acos(-1 + (2 * i) / count);
                const theta = Math.sqrt(count * Math.PI) * phi;
                const r = 4.5 + Math.random() * 18.0;

                positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
                positions[i * 3 + 1] = (Math.random() - 0.5) * 14.0;
                positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);

                const col = (i % 3 === 0) ? cSapphire : ((i % 3 === 1) ? cMint : cAmber);
                colors[i * 3] = col.r;
                colors[i * 3 + 1] = col.g;
                colors[i * 3 + 2] = col.b;
            }

            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

            const material = new THREE.PointsMaterial({
                size: 0.11,
                vertexColors: true,
                transparent: true,
                opacity: 0.60,
                blending: THREE.AdditiveBlending
            });

            this.cosmicDust = new THREE.Points(geometry, material);
            this.scene.add(this.cosmicDust);
        }

        // ---------------------------------------------------------------------
        // 8. INTERACTIVE RAYCASTING & EVENTS
        // ---------------------------------------------------------------------

        _initRaycasting() {
            this.raycaster = new THREE.Raycaster();
            this.pointer = new THREE.Vector2();

            const onPointerMove = (e) => {
                const rect = this.domElement.getBoundingClientRect();
                this.pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
                this.pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

                this.raycaster.setFromCamera(this.pointer, this.camera);
                const intersects = this.raycaster.intersectObjects(this.interactiveObjects, false);

                if (intersects.length > 0) {
                    const hit = intersects[0];
                    const nodeGroup = hit.object.userData.parentGroup;
                    const nodeData = hit.object.userData.nodeData;

                    if (this._hoveredNode !== nodeGroup) {
                        this._setHoverState(nodeGroup, true);
                        this.domElement.style.cursor = 'pointer';
                        this.emit('node_hover', { node: nodeData, screenPos: { x: e.clientX, y: e.clientY } });
                    }
                } else {
                    if (this._hoveredNode) {
                        this._setHoverState(this._hoveredNode, false);
                        this.domElement.style.cursor = 'default';
                        this.emit('node_unhover', {});
                    }
                }
            };

            const onPointerDown = (e) => {
                this._pointerDownPos.set(e.clientX, e.clientY);
            };

            const onPointerUp = (e) => {
                const dist = Math.hypot(e.clientX - this._pointerDownPos.x, e.clientY - this._pointerDownPos.y);
                if (dist > 5.0) return; // Disregard drags

                const rect = this.domElement.getBoundingClientRect();
                this.pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
                this.pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

                this.raycaster.setFromCamera(this.pointer, this.camera);
                const intersects = this.raycaster.intersectObjects(this.interactiveObjects, false);

                if (intersects.length > 0) {
                    const nodeGroup = intersects[0].object.userData.parentGroup;
                    const nodeData = intersects[0].object.userData.nodeData;
                    this.selectNode(nodeGroup, nodeData);
                } else {
                    this.resetView();
                }
            };

            this.domElement.addEventListener('pointermove', onPointerMove, { passive: true });
            this.domElement.addEventListener('pointerdown', onPointerDown, { passive: true });
            this.domElement.addEventListener('pointerup', onPointerUp, { passive: true });

            this._unbindEvents = () => {
                this.domElement.removeEventListener('pointermove', onPointerMove);
                this.domElement.removeEventListener('pointerdown', onPointerDown);
                this.domElement.removeEventListener('pointerup', onPointerUp);
            };
        }

        _setHoverState(nodeGroup, isHovered) {
            this._hoveredNode = isHovered ? nodeGroup : null;
            if (!nodeGroup) return;

            const targetScale = isHovered ? 1.22 : 1.0;
            nodeGroup.scale.set(targetScale, targetScale, targetScale);
        }

        selectNode(nodeGroup, nodeData) {
            this._selectedNode = nodeGroup;

            const nodeWorldPos = new THREE.Vector3();
            nodeGroup.getWorldPosition(nodeWorldPos);

            const offsetDir = nodeWorldPos.clone().normalize();
            const targetCamPos = nodeWorldPos.clone().add(offsetDir.multiplyScalar(4.5)).add(new THREE.Vector3(0, 1.6, 0));

            this._startCameraLerp(targetCamPos, nodeWorldPos);

            if (this.controls) {
                this.controls.autoRotate = false;
            }

            this.emit('node_select', { node: nodeData, worldPosition: nodeWorldPos });
            this.updateHUD(nodeData);
        }

        resetView() {
            this._selectedNode = null;
            const targetCamPos = (this.currentMode === 'stack') ? this.stackCameraPos : this.defaultCameraPos;
            this._startCameraLerp(targetCamPos, this.controlsTarget);

            if (this.controls) {
                this.controls.autoRotate = (this.currentMode === 'topology') ? this.options.autoRotate : false;
            }

            this.emit('node_deselect', {});
            this.hideHUD();
        }

        focusNodeByKey(nodeKey) {
            if (!this.satelliteNodes || !this.satelliteNodes.length) return;
            const targetGroup = this.satelliteNodes.find(g => {
                const nd = g.userData && g.userData.nodeData;
                return nd && (nd.key === nodeKey || nd.id === nodeKey || (nd.aliases && nd.aliases.includes(nodeKey)) || (nd.key && nd.key.toLowerCase() === (nodeKey || '').toLowerCase()));
            });
            if (targetGroup) {
                this.selectNode(targetGroup, targetGroup.userData.nodeData);
            }
        }

        toggleArchitectureMode() {
            if (this.currentMode === 'topology') {
                this.setMode('stack');
            } else {
                this.setMode('topology');
            }
        }

        setMode(mode) {
            this.currentMode = (mode === 'stack') ? 'stack' : 'topology';

            if (this.currentMode === 'stack') {
                // Show architectural tiers, hide orbital ring
                if (this.stackPlatesGroup) this.stackPlatesGroup.visible = true;
                if (this.orbitalPlaneMesh) this.orbitalPlaneMesh.visible = false;
                if (this.logoGroup) this.logoGroup.position.set(0, 0, -2.5); // Center behind stack

                if (this.controls) this.controls.autoRotate = false;
                this._startCameraLerp(this.stackCameraPos, this.controlsTarget);
            } else {
                // Topology view: orbital ring visible, stack plates hidden
                if (this.stackPlatesGroup) this.stackPlatesGroup.visible = false;
                if (this.orbitalPlaneMesh) this.orbitalPlaneMesh.visible = true;
                if (this.logoGroup) this.logoGroup.position.set(0, 0, 0);

                if (this.controls) this.controls.autoRotate = this.options.autoRotate;
                this._startCameraLerp(this.defaultCameraPos, this.controlsTarget);
            }

            const toggleBtn = document.getElementById('innoriaModeToggleBtn') || document.querySelector('[data-action="toggle-mode"]');
            if (toggleBtn) {
                toggleBtn.innerHTML = (this.currentMode === 'stack') ? '<span>🌌 Quỹ Đạo Logo</span>' : '<span>🏛️ Kiến Trúc Dịch Vụ</span>';
            }

            this.emit('mode_change', { mode: this.currentMode });
        }

        // ---------------------------------------------------------------------
        // 9. HUD TELEMETRY PANEL
        // ---------------------------------------------------------------------

        _bindDOMHUD() {
            let hud = document.getElementById(this.options.hudElementId);
            if (!hud) {
                hud = document.createElement('aside');
                hud.id = this.options.hudElementId;
                hud.className = 'innoria-topology-hud card position-absolute p-4 shadow-lg';
                hud.style.cssText = `
                    display: none;
                    top: 2rem;
                    right: 2rem;
                    max-width: 440px;
                    width: calc(100% - 4rem);
                    background: rgba(7, 11, 20, 0.94);
                    backdrop-filter: blur(20px);
                    -webkit-backdrop-filter: blur(20px);
                    border: 1px solid rgba(10, 187, 219, 0.35);
                    border-radius: 14px;
                    color: #FFFFFF;
                    z-index: 1000;
                    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.75), 0 0 24px rgba(10, 187, 219, 0.25);
                    font-family: system-ui, -apple-system, sans-serif;
                `;
                this.container.style.position = 'relative';
                this.container.appendChild(hud);
            }
            this.hudElement = hud;
        }

        updateHUD(nodeData) {
            if (!this.hudElement) return;

            const hexColor = '#' + nodeData.color.toString(16).padStart(6, '0');
            
            const metricsHtml = nodeData.metrics.map(m => `
                <div class="d-flex justify-content-between align-items-center py-2 border-bottom" style="border-color: rgba(255,255,255,0.08) !important;">
                    <span style="font-size: 0.85rem; color: #CBD5E1;">${m.label}</span>
                    <span class="badge" style="background: rgba(10,187,219,0.18); border: 1px solid ${hexColor}; color: #FFFFFF; font-weight: 600; font-size: 0.82rem; padding: 0.25rem 0.65rem; border-radius: 6px;">
                        ${m.value}
                    </span>
                </div>
            `).join('');

            this.hudElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <div class="text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.08em; color: ${hexColor}; font-weight: 700;">
                            ${nodeData.category}
                        </div>
                        <h3 class="m-0 mt-1" style="font-size: 1.35rem; font-weight: 800; color: #FFFFFF;">
                            ${nodeData.name}
                        </h3>
                    </div>
                    <button type="button" class="btn-close btn-close-white" aria-label="Close telemetry view" style="opacity: 0.85;"></button>
                </div>
                
                <p style="font-size: 0.88rem; line-height: 1.45; color: #E2E8F0; margin-bottom: 1.2rem;">
                    ${nodeData.tagline}
                </p>

                <div class="metrics-grid mb-3">
                    ${metricsHtml}
                </div>

                <div class="d-flex gap-2 mt-3 pt-2">
                    <a href="${nodeData.deepLink}" class="btn w-100 py-2 text-center text-decoration-none fw-bold" style="background: ${hexColor}; color: #070B14; border-radius: 8px; font-size: 0.9rem; transition: opacity 0.2s ease;">
                        Khám Phá Chi Tiết &rarr;
                    </a>
                </div>
            `;

            const closeBtn = this.hudElement.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.resetView();
                };
            }

            this.hudElement.style.display = 'block';
            document.querySelectorAll('.innoria-hud-btn').forEach(btn => {
                const k = btn.getAttribute('data-node-key');
                btn.classList.toggle('active', k === nodeData.key || k === nodeData.id);
            });
        }

        hideHUD() {
            if (this.hudElement) {
                this.hudElement.style.display = 'none';
            }
            document.querySelectorAll('.innoria-hud-btn').forEach(btn => {
                btn.classList.remove('active');
            });
        }

        _bindControlButtons() {
            const hudBars = document.querySelectorAll('.innoria-hud-control-bar');
            hudBars.forEach(hudBar => {
                let toggleBtn = hudBar.querySelector('[data-action="toggle-mode"]');
                if (!toggleBtn) {
                    toggleBtn = document.createElement('button');
                    toggleBtn.type = 'button';
                    toggleBtn.className = 'innoria-hud-btn';
                    toggleBtn.id = 'innoriaModeToggleBtn';
                    toggleBtn.setAttribute('data-action', 'toggle-mode');
                    toggleBtn.innerHTML = '<span>🏛️ Kiến Trúc Dịch Vụ</span>';
                    const resetBtn = hudBar.querySelector('[data-action="reset-view"]');
                    if (resetBtn) {
                        hudBar.insertBefore(toggleBtn, resetBtn);
                    } else {
                        hudBar.appendChild(toggleBtn);
                    }
                }

                const buttons = hudBar.querySelectorAll('.innoria-hud-btn');
                buttons.forEach(btn => {
                    if (btn.__innoriaBound) return;
                    btn.__innoriaBound = true;

                    const action = btn.getAttribute('data-action');
                    const nodeKey = btn.getAttribute('data-node-key');

                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        if (action === 'focus-node' && nodeKey) {
                            this.focusNodeByKey(nodeKey);
                        } else if (action === 'reset-view') {
                            this.resetView();
                        } else if (action === 'toggle-mode') {
                            this.toggleArchitectureMode();
                        }
                    });
                });
            });
        }

        // ---------------------------------------------------------------------
        // 10. RENDER LOOP (60 FPS) & DYNAMIC ANIMATIONS
        // ---------------------------------------------------------------------

        start() {
            if (this._animFrameId) return;

            const tick = () => {
                this._animFrameId = requestAnimationFrame(tick);
                this._render();
            };

            this._clock.start();
            this._animFrameId = requestAnimationFrame(tick);
        }

        stop() {
            if (this._animFrameId) {
                cancelAnimationFrame(this._animFrameId);
                this._animFrameId = null;
            }
            this._clock.stop();
        }

        _calculateOrbitalPosition(angle, radius, elapsed) {
            const inclination = 0.22;
            const currentAngle = angle + (elapsed * 0.08);
            return new THREE.Vector3(
                Math.cos(currentAngle) * radius,
                Math.sin(currentAngle) * radius * Math.sin(inclination) + Math.sin(elapsed * 1.5) * 0.2,
                Math.sin(currentAngle) * radius * Math.cos(inclination)
            );
        }

        _render() {
            const delta = this._clock.getDelta();
            const elapsed = this._clock.getElapsedTime();

            // 1. Central Innoria Logo Dynamics
            if (this.logoGroup) {
                this.logoGroup.rotation.y = elapsed * 0.18;
                this.logoGroup.rotation.z = Math.sin(elapsed * 0.4) * 0.08;

                // Pulsing nucleus
                const scalePulse = 1.0 + 0.08 * Math.sin(elapsed * 2.8);
                if (this.nucleusMesh) {
                    this.nucleusMesh.scale.set(scalePulse, scalePulse, scalePulse);
                    this.nucleusMesh.rotation.y = elapsed * 0.45;
                }

                // Animate the 3 Signature Orange Comets along their Logo Trajectories
                if (this.logoComets && this.logoCurve) {
                    this.logoComets.forEach((c) => {
                        if (c.type === 'spline') {
                            c.progress = (c.progress + delta * c.speed) % 1.0;
                            const pt = this.logoCurve.getPointAt(c.progress);
                            c.mesh.position.copy(pt);
                            if (this.cometLight) this.cometLight.position.copy(pt);
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

            // 2. Service Architecture Pod Motions & Transitions
            this.satelliteNodes.forEach((podGroup) => {
                const data = podGroup.userData.nodeData;
                let targetPos;

                if (this.currentMode === 'stack') {
                    // Isometric Layered Architecture Stack
                    targetPos = data.stackPos;
                } else {
                    // Orbital Logo Constellation Mode
                    targetPos = this._calculateOrbitalPosition(data.orbitAngle, data.radius, elapsed);
                }

                // Smooth position lerp
                podGroup.position.lerp(targetPos, 0.06);

                // Self rotation & micro-architecture dynamics
                const archCore = podGroup.userData.architectureCore;
                if (archCore) {
                    archCore.rotation.y = elapsed * 0.35;
                }

                // MOJO AI Micro-Agent Swarm Dynamics
                if (podGroup.userData.swarmAgents) {
                    podGroup.userData.swarmAgents.forEach((ag) => {
                        const agAngle = (elapsed * ag.speed) + ag.angleOffset;
                        ag.mesh.position.set(
                            Math.cos(agAngle) * ag.radius,
                            Math.sin(agAngle * 2) * 0.35,
                            Math.sin(agAngle) * ag.radius
                        );
                    });
                }

                // MOJOVERSE Consensus Ring Rotation
                if (podGroup.userData.consensusRing) {
                    podGroup.userData.consensusRing.rotation.z = elapsed * 0.75;
                }
            });

            // 3. Cybernetic Data Conduit Pulses
            if (this.packetParticles && this.conduitBuses) {
                this.packetParticles.forEach((pkt) => {
                    const conduit = this.conduitBuses[pkt.curveIndex];
                    if (!conduit) return;

                    pkt.progress = (pkt.progress + delta * pkt.speed) % 1.0;
                    
                    // When in stack mode, packet moves toward stack position; otherwise orbital
                    const targetNode = this.satelliteNodes[pkt.curveIndex];
                    if (targetNode) {
                        const start = new THREE.Vector3(0, 0, 0);
                        const end = targetNode.position;
                        const mid = new THREE.Vector3(end.x * 0.5, end.y * 0.5 + 1.2, end.z * 0.5);
                        const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
                        const pt = curve.getPointAt(pkt.progress);
                        pkt.mesh.position.copy(pt);
                    }
                });
            }

            // 4. Ambient Cosmic Dust Drift
            if (this.cosmicDust) {
                this.cosmicDust.rotation.y = elapsed * 0.02;
            }

            // 5. Smooth Camera Lerp on Target Selection
            if (this._cameraLerping) {
                this._camLerpAlpha += delta * 1.8;
                const alpha = Math.min(this._camLerpAlpha, 1.0);
                const smoothAlpha = 0.5 - 0.5 * Math.cos(alpha * Math.PI); // Ease in-out sine

                this.camera.position.lerpVectors(this._camLerpStart, this._camLerpEnd, smoothAlpha);
                if (this.controls) {
                    this.controls.target.lerpVectors(this._targetLerpStart, this._targetLerpEnd, smoothAlpha);
                    this.controls.update();
                }

                if (alpha >= 1.0) {
                    this._cameraLerping = false;
                }
            } else if (this.controls) {
                this.controls.update();
            }

            this.renderer.render(this.scene, this.camera);
        }

        _startCameraLerp(endPos, endTarget) {
            this._cameraLerping = true;
            this._camLerpAlpha = 0.0;
            this._camLerpStart = this.camera.position.clone();
            this._camLerpEnd = endPos.clone();
            this._targetLerpStart = this.controls ? this.controls.target.clone() : new THREE.Vector3(0, 0, 0);
            this._targetLerpEnd = endTarget.clone();
        }

        _handleResize() {
            if (!this.container || !this.renderer || !this.camera) return;
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 520;

            this.camera.aspect = width / height;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.0));
        }

        // ---------------------------------------------------------------------
        // 11. EVENT EMITTER INTERFACE
        // ---------------------------------------------------------------------

        on(event, handler) {
            if (!this._listeners[event]) this._listeners[event] = [];
            this._listeners[event].push(handler);
            return this;
        }

        off(event, handler) {
            if (!this._listeners[event]) return this;
            this._listeners[event] = this._listeners[event].filter(h => h !== handler);
            return this;
        }

        emit(event, data) {
            if (!this._listeners[event]) return;
            this._listeners[event].forEach(handler => {
                try { handler(data); } catch (e) { console.error('[InnoriaTopology3D] Listener error:', e); }
            });
        }

        destroy() {
            this.stop();
            window.removeEventListener('resize', this._onResize);
            if (this._unbindEvents) this._unbindEvents();

            if (this.renderer && this.renderer.domElement && this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
            if (this.controls && this.controls.dispose) {
                this.controls.dispose();
            }
            if (this.hudElement && this.hudElement.parentNode) {
                this.hudElement.parentNode.removeChild(this.hudElement);
            }
            this.scene = null;
            this.camera = null;
            this.renderer = null;
        }
    }

    // Auto-init fallback for standalone topology viewports
    if (typeof document !== 'undefined') {
        const autoInitTopology = () => {
            const viewports = document.querySelectorAll('[data-innoria-3d="topology"], #innoriaTopologyViewport');
            viewports.forEach(vp => {
                if (!vp.querySelector('canvas') && !vp.__innoriaTopologyEngine && !vp.__innoriaHeroManager) {
                    try {
                        vp.__innoriaTopologyEngine = new InnoriaTopologyEngine(vp);
                    } catch (e) {
                        console.warn('[InnoriaTopology3D] Auto-init skipped or deferred:', e);
                    }
                }
            });
        };
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', autoInitTopology);
        } else {
            setTimeout(autoInitTopology, 50);
        }
    }

    return InnoriaTopologyEngine;
}));
