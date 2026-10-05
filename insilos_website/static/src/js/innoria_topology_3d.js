/**
 * Innoria Multi-Agent AI & Cloud Topology 3D Engine
 * File: innoria_topology_3d.js
 * Host Target: innoria.insilos.com (Insilos Sovereign Three.js Suite)
 * 
 * Core Topology:
 * - Central Core: Innoria Sovereign AI Kernel & Cloud Hub
 * - 4 Orbital Satellite Nodes:
 *   1. DIGIFORCE (No-Code/Low-Code, 4-step deployment: 3h -> 3d -> 3w -> 3m)
 *   2. MOJO AI (Multi-Agent Swarm, VLM See-Detect-Analyze-Adapt, Reason-Solve-Plan-Execute)
 *   3. MOJOVERSE (Enterprise Blockchain & Web3, Supply Chain Trust & Digital ID)
 *   4. Enterprise Intelligent ERP (AI-Powered GRC, EHS, RCM, e-CO)
 *
 * Performance Budget: 60 FPS | Instanced Cosmic Dust | Shader Glow Bloom Simulation
 * WCAG AAA Contrast Overlays | Full GPU Resource Disposal
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
    // 1. BRAND PALETTE & TELEMETRY CONTRACTS
    // =========================================================================

    const BRAND_PALETTE = {
        electricSapphire: 0x2F80ED, // Primary brand blue (#2F80ED)
        mintCyan: 0xB2FFDA,         // High-contrast mint cyan (#B2FFDA)
        techCyan: 0x0ABBDB,         // Vivid tech cyan (#0ABBDB)
        warmAmber: 0xFF9C00,        // Blockchain warm amber (#FF9C00)
        warmAmberAccent: 0xFE8B20,  // Deep amber (#FE8B20)
        darkBase: 0x05101E,         // Deep space dark base (#05101E)
        gridLines: 0x112740,        // Subtle coordinate grid (#112740)
        whiteHighContrast: 0xFFFFFF // High contrast white
    };

    const TOPOLOGY_NODES_DATA = [
        {
            id: 'node_digiforce',
            key: 'DIGIFORCE',
            name: 'DIGIFORCE Sovereign Platform',
            category: 'No-Code / Low-Code Hyper-App Engine',
            color: BRAND_PALETTE.mintCyan,
            accentColor: BRAND_PALETTE.electricSapphire,
            orbitAngle: 0, // 0 rad (0 deg)
            radius: 6.2,
            orbitSpeed: 0.12,
            scale: 1.15,
            tagline: 'Rapid Enterprise Application Deployment (3h -> 3d -> 3w -> 3m)',
            metrics: [
                { label: 'Rapid Prototype (Step 1)', value: '3 Hours', badge: 'Sprint' },
                { label: 'Pilot MVP (Step 2)', value: '3 Days', badge: 'Validated' },
                { label: 'Enterprise Rollout (Step 3)', value: '3 Weeks', badge: 'Production' },
                { label: 'Multi-Site Maturity (Step 4)', value: '3 Months', badge: 'Sovereign' }
            ],
            architecture: {
                engine: 'Visual Workflow & Logic Synthesizer',
                governance: 'Multi-Tenant Sandbox Isolation',
                integration: 'OpenAPI 3.1 & Insilos Data Mesh Connector'
            },
            deepLink: '/platform/digiforce'
        },
        {
            id: 'node_mojo_ai',
            key: 'MOJO_AI',
            name: 'MOJO AI Multi-Agent Swarm',
            category: 'Autonomous Multi-Modal Agent Mesh',
            color: BRAND_PALETTE.techCyan,
            accentColor: BRAND_PALETTE.electricSapphire,
            orbitAngle: Math.PI * 0.5, // 90 deg
            radius: 6.2,
            orbitSpeed: 0.15,
            scale: 1.25,
            tagline: 'VLM Perception & Dual-Loop Cognitive Autonomous Execution',
            metrics: [
                { label: 'Perception Loop', value: 'See-Detect-Analyze-Adapt', badge: 'VLM Active' },
                { label: 'Execution Loop', value: 'Reason-Solve-Plan-Execute', badge: 'Swarm CPM' },
                { label: 'Active Agent Nodes', value: '16 Sovereign Nodes', badge: 'Healthy' },
                { label: 'Inference Latency', value: '184 ms (p95)', badge: 'Optimal' }
            ],
            architecture: {
                engine: 'Clef DAG Scheduler & Hybrid Reasoning Core',
                guardrails: 'Zero-Evasion Verification & Anti-Hallucination Gate',
                telemetry: 'Passive Quota Ledger & Autonomous Token Saver'
            },
            deepLink: '/platform/mojo-ai'
        },
        {
            id: 'node_mojoverse',
            key: 'MOJOVERSE',
            name: 'MOJOVERSE Enterprise Web3',
            category: 'Decentralized Trust & Supply Chain Ledger',
            color: BRAND_PALETTE.warmAmber,
            accentColor: BRAND_PALETTE.warmAmberAccent,
            orbitAngle: Math.PI, // 180 deg
            radius: 6.2,
            orbitSpeed: 0.10,
            scale: 1.18,
            tagline: 'Enterprise Blockchain, Digital Product Passports & Sovereign ID',
            metrics: [
                { label: 'Consensus Proof', value: 'PoA Sovereign Consortium', badge: 'Finalized' },
                { label: 'Supply Chain Passports', value: '142,800+ Minted', badge: 'Tamper-Proof' },
                { label: 'Block Time / Finality', value: '1.2s Instant Finality', badge: 'Zero-Gas' },
                { label: 'Smart Contract Audit', value: 'Formal Verification PASS', badge: 'SOC-2 / ISO' }
            ],
            architecture: {
                ledger: 'EVM-Compatible Sovereign State Machine',
                identity: 'W3C Verifiable Credentials & DID Hub',
                interop: 'Cross-Border Customs & e-CO Gateway'
            },
            deepLink: '/platform/mojoverse'
        },
        {
            id: 'node_erp_intelligent',
            key: 'INTELLIGENT_ERP',
            name: 'Enterprise Intelligent ERP',
            category: 'Autonomous Corporate Operational Backbone',
            color: BRAND_PALETTE.electricSapphire,
            accentColor: BRAND_PALETTE.mintCyan,
            orbitAngle: Math.PI * 1.5, // 270 deg
            radius: 6.2,
            orbitSpeed: 0.11,
            scale: 1.20,
            tagline: 'AI-Native Governance, Risk, Compliance & Asset Health',
            metrics: [
                { label: 'GRC Engine', value: 'Autonomous Regulatory Audit', badge: '100% PASS' },
                { label: 'EHS & Safety', value: 'Zero-Harm IoT & CCTV AI', badge: 'Active' },
                { label: 'RCM Asset Health', value: 'Predictive Vibration FFT', badge: '99.98% OEE' },
                { label: 'e-CO Certificate', value: 'Real-time Digital Origin Proof', badge: 'FTAs Ready' }
            ],
            architecture: {
                foundation: 'Odoo 20 Enterprise Hardened Core',
                database: 'Distributed PostgreSQL + In-Memory Vector Store',
                compliance: 'IFRS, US GAAP, ESG Scope 1-3 Embedded'
            },
            deepLink: '/platform/intelligent-erp'
        }
    ];

    // =========================================================================
    // 2. SHADER BLOOM SIMULATOR (LIGHTWEIGHT 60 FPS GLOW)
    // =========================================================================

    const GlowShaderMaterial = {
        vertexShader: `
            varying vec3 vNormal;
            varying vec3 vPositionWorld;
            void main() {
                vNormal = normalize(normalMatrix * normal);
                vec4 worldPos = modelMatrix * vec4(position, 1.0);
                vPositionWorld = worldPos.xyz;
                gl_Position = projectionMatrix * viewMatrix * worldPos;
            }
        `,
        fragmentShader: `
            uniform vec3 glowColor;
            uniform float coefficient;
            uniform float power;
            uniform float time;
            varying vec3 vNormal;
            varying vec3 vPositionWorld;
            void main() {
                vec3 viewDirection = normalize(cameraPosition - vPositionWorld);
                float intensity = clamp(dot(viewDirection, vNormal), 0.0, 1.0);
                float fresnel = pow(1.0 - intensity, power) * coefficient;
                float pulse = 0.85 + 0.15 * sin(time * 2.8);
                gl_FragColor = vec4(glowColor * pulse, fresnel * pulse);
            }
        `
    };

    // =========================================================================
    // 3. TOPOLOGY ENGINE MAIN CLASS
    // =========================================================================

    class InnoriaTopologyEngine {
        constructor(container, options = {}) {
            this.container = typeof container === 'string' ? document.querySelector(container) : container;
            if (!this.container) {
                throw new Error('[InnoriaTopologyEngine] Container element not found: ' + container);
            }

            this.options = Object.assign({
                autoRotate: true,
                autoRotateSpeed: 0.45,
                enableControls: true,
                hudElementId: 'innoria-topology-hud',
                particleCount: 500,
                pulsePacketCount: 16
            }, options);

            this._listeners = new Map();
            this._animFrameId = null;
            this._clock = new THREE.Clock();
            this._selectedNode = null;
            this._hoveredNode = null;
            this._orbitAngleOffset = 0;
            this._isInteracting = false;
            this._pointerDownPos = new THREE.Vector2();

            // Camera focus animation state
            this._cameraLerp = {
                active: false,
                startTime: 0,
                duration: 1.2,
                fromPos: new THREE.Vector3(),
                toPos: new THREE.Vector3(),
                fromTarget: new THREE.Vector3(),
                toTarget: new THREE.Vector3()
            };

            this._initRenderer();
            this._initScene();
            this._initCameraAndControls();
            this._initLights();
            this._buildCentralCore();
            this._buildOrbitalSatellites();
            this._buildParticleBridges();
            this._buildCosmicDust();
            this._initRaycasting();
            this._bindDOMHUD();
            this._setupResizeHandler();
            this._setupVisibilityObserver();

            this.start();
        }

        // ---------------------------------------------------------------------
        // RENDERER & SCENE SETUP
        // ---------------------------------------------------------------------

        _initRenderer() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 500;

            this.renderer = new THREE.WebGLRenderer({
                antialias: (window.devicePixelRatio || 1) < 2,
                powerPreference: 'high-performance',
                alpha: true,
                precision: 'mediump'
            });

            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.0));
            this.renderer.setSize(width, height);
            this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
            this.renderer.toneMappingExposure = 1.25;

            this.domElement = this.renderer.domElement;
            this.domElement.className = 'innoria-topology-canvas w-100 h-100 position-relative';
            this.domElement.setAttribute('role', 'img');
            this.domElement.setAttribute('aria-label', 'Innoria Sovereign Multi-Agent AI and Cloud Topology 3D interactive viewport');
            this.container.appendChild(this.domElement);
        }

        _initScene() {
            this.scene = new THREE.Scene();
            this.scene.fog = new THREE.FogExp2(BRAND_PALETTE.darkBase, 0.035);

            // Sovereign Grid Plane (XZ Plane)
            const grid = new THREE.GridHelper(24, 48, BRAND_PALETTE.electricSapphire, BRAND_PALETTE.gridLines);
            grid.position.y = -2.8;
            grid.material.opacity = 0.22;
            grid.material.transparent = true;
            this.scene.add(grid);

            // Orbital boundary coordinate rings
            const outerRingGeo = new THREE.RingGeometry(6.15, 6.25, 96);
            const outerRingMat = new THREE.MeshBasicMaterial({
                color: BRAND_PALETTE.electricSapphire,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.18
            });
            this.orbitalPlaneMesh = new THREE.Mesh(outerRingGeo, outerRingMat);
            this.orbitalPlaneMesh.rotation.x = Math.PI / 2 + 0.2618; // 15 degree inclination
            this.scene.add(this.orbitalPlaneMesh);
        }

        _initCameraAndControls() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 500;
            const aspect = width / height;

            this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 100);
            this.defaultCameraPos = new THREE.Vector3(0, 7.5, 15.0);
            this.camera.position.copy(this.defaultCameraPos);

            this.controlsTarget = new THREE.Vector3(0, 0, 0);

            if (THREE.OrbitControls) {
                this.controls = new THREE.OrbitControls(this.camera, this.domElement);
                this.controls.enableDamping = true;
                this.controls.dampingFactor = 0.05;
                this.controls.minDistance = 4.0;
                this.controls.maxDistance = 28.0;
                this.controls.maxPolarAngle = Math.PI / 2 + 0.15; // Don't go too far under grid
                this.controls.autoRotate = this.options.autoRotate;
                this.controls.autoRotateSpeed = this.options.autoRotateSpeed;
                this.controls.target.copy(this.controlsTarget);
            }
        }

        _initLights() {
            // Ambient base
            const ambient = new THREE.AmbientLight(0x0e1c31, 1.8);
            this.scene.add(ambient);

            // Sovereign Core Key Light
            const coreLight = new THREE.PointLight(BRAND_PALETTE.electricSapphire, 3.5, 20);
            coreLight.position.set(0, 0, 0);
            this.scene.add(coreLight);

            // Directional Rim Lights
            const rimLight1 = new THREE.DirectionalLight(BRAND_PALETTE.mintCyan, 1.4);
            rimLight1.position.set(8, 12, 10);
            this.scene.add(rimLight1);

            const rimLight2 = new THREE.DirectionalLight(BRAND_PALETTE.warmAmber, 0.9);
            rimLight2.position.set(-10, -5, -8);
            this.scene.add(rimLight2);
        }

        // ---------------------------------------------------------------------
        // 4. TOPOLOGY OBJECT GENERATION
        // ---------------------------------------------------------------------

        _buildCentralCore() {
            this.coreGroup = new THREE.Group();
            this.coreGroup.name = 'Innoria_Sovereign_AI_Kernel';

            // 1. Inner pulsating energy plasma
            const plasmaGeo = new THREE.SphereGeometry(1.2, 32, 32);
            this.plasmaMat = new THREE.MeshStandardMaterial({
                color: BRAND_PALETTE.electricSapphire,
                emissive: BRAND_PALETTE.electricSapphire,
                emissiveIntensity: 0.85,
                roughness: 0.15,
                metalness: 0.9
            });
            this.plasmaMesh = new THREE.Mesh(plasmaGeo, this.plasmaMat);
            this.coreGroup.add(this.plasmaMesh);

            // 2. Geodesic wireframe containment lattice
            const latticeGeo = new THREE.IcosahedronGeometry(1.65, 2);
            const latticeMat = new THREE.MeshBasicMaterial({
                color: BRAND_PALETTE.mintCyan,
                wireframe: true,
                transparent: true,
                opacity: 0.45
            });
            this.latticeMesh = new THREE.Mesh(latticeGeo, latticeMat);
            this.coreGroup.add(this.latticeMesh);

            // 3. Counter-rotating equatorial quantum rings
            const ringGeo1 = new THREE.TorusGeometry(2.1, 0.025, 16, 100);
            const ringMat1 = new THREE.MeshBasicMaterial({
                color: BRAND_PALETTE.techCyan,
                transparent: true,
                opacity: 0.75
            });
            this.ringMesh1 = new THREE.Mesh(ringGeo1, ringMat1);
            this.ringMesh1.rotation.x = Math.PI * 0.35;
            this.coreGroup.add(this.ringMesh1);

            const ringGeo2 = new THREE.TorusGeometry(2.35, 0.02, 16, 100);
            const ringMat2 = new THREE.MeshBasicMaterial({
                color: BRAND_PALETTE.mintCyan,
                transparent: true,
                opacity: 0.55
            });
            this.ringMesh2 = new THREE.Mesh(ringGeo2, ringMat2);
            this.ringMesh2.rotation.y = Math.PI * 0.45;
            this.coreGroup.add(this.ringMesh2);

            // 4. Core Fresnel Shader Glow Aura
            this.coreGlowUniforms = {
                glowColor: { value: new THREE.Color(BRAND_PALETTE.electricSapphire) },
                coefficient: { value: 1.0 },
                power: { value: 2.2 },
                time: { value: 0.0 }
            };
            const coreGlowMat = new THREE.ShaderMaterial({
                vertexShader: GlowShaderMaterial.vertexShader,
                fragmentShader: GlowShaderMaterial.fragmentShader,
                uniforms: this.coreGlowUniforms,
                side: THREE.BackSide,
                blending: THREE.AdditiveBlending,
                transparent: true
            });
            const coreGlowGeo = new THREE.SphereGeometry(2.0, 32, 32);
            this.coreGlowMesh = new THREE.Mesh(coreGlowGeo, coreGlowMat);
            this.coreGroup.add(this.coreGlowMesh);

            this.scene.add(this.coreGroup);
        }

        _buildOrbitalSatellites() {
            this.satelliteNodes = [];
            this.interactiveObjects = [];

            TOPOLOGY_NODES_DATA.forEach((data, index) => {
                const group = new THREE.Group();
                group.name = data.id;
                group.userData = { nodeData: data, isSatellite: true, index: index };

                let geometry, material;

                // Specialized Visual Geometries representing each platform capability
                switch (data.key) {
                    case 'DIGIFORCE':
                        // Truncated Octahedron with 4 step rings (3h -> 3d -> 3w -> 3m)
                        geometry = new THREE.OctahedronGeometry(0.85, 1);
                        material = new THREE.MeshStandardMaterial({
                            color: data.color,
                            emissive: data.accentColor,
                            emissiveIntensity: 0.45,
                            metalness: 0.8,
                            roughness: 0.2
                        });
                        break;

                    case 'MOJO_AI':
                        // Dual nested Icosahedron with neural gyroscopic sensors
                        geometry = new THREE.IcosahedronGeometry(0.9, 1);
                        material = new THREE.MeshStandardMaterial({
                            color: data.color,
                            emissive: data.accentColor,
                            emissiveIntensity: 0.55,
                            metalness: 0.85,
                            roughness: 0.15
                        });
                        break;

                    case 'MOJOVERSE':
                        // Interlocking Hexagonal Prism Lattice (Enterprise Blockchain & Web3)
                        geometry = new THREE.CylinderGeometry(0.7, 0.7, 1.1, 6);
                        material = new THREE.MeshStandardMaterial({
                            color: data.color,
                            emissive: data.accentColor,
                            emissiveIntensity: 0.6,
                            metalness: 0.9,
                            roughness: 0.25
                        });
                        break;

                    case 'INTELLIGENT_ERP':
                        // Quad-pillar Monolith (GRC, EHS, RCM, e-CO)
                        geometry = new THREE.DodecahedronGeometry(0.88, 0);
                        material = new THREE.MeshStandardMaterial({
                            color: data.color,
                            emissive: data.accentColor,
                            emissiveIntensity: 0.5,
                            metalness: 0.75,
                            roughness: 0.3
                        });
                        break;

                    default:
                        geometry = new THREE.SphereGeometry(0.8, 24, 24);
                        material = new THREE.MeshStandardMaterial({ color: data.color });
                }

                const mesh = new THREE.Mesh(geometry, material);
                mesh.castShadow = true;
                group.add(mesh);

                // Wireframe protective boundary
                const wireGeo = geometry.clone();
                const wireMat = new THREE.MeshBasicMaterial({
                    color: data.color,
                    wireframe: true,
                    transparent: true,
                    opacity: 0.35
                });
                const wireMesh = new THREE.Mesh(wireGeo, wireMat);
                wireMesh.scale.set(1.22, 1.22, 1.22);
                group.add(wireMesh);

                // Halo status beacon ring
                const beaconGeo = new THREE.RingGeometry(1.25, 1.32, 32);
                const beaconMat = new THREE.MeshBasicMaterial({
                    color: data.color,
                    side: THREE.DoubleSide,
                    transparent: true,
                    opacity: 0.65
                });
                const beacon = new THREE.Mesh(beaconGeo, beaconMat);
                beacon.rotation.x = Math.PI / 2;
                group.add(beacon);

                // Invisible expanded bounding sphere for easy raycaster picking on mobile/desktop
                const hitSphereGeo = new THREE.SphereGeometry(1.6, 16, 16);
                const hitSphereMat = new THREE.MeshBasicMaterial({ visible: false });
                const hitSphere = new THREE.Mesh(hitSphereGeo, hitSphereMat);
                hitSphere.userData = { parentGroup: group, nodeData: data };
                group.add(hitSphere);

                this.scene.add(group);
                this.satelliteNodes.push(group);
                this.interactiveObjects.push(hitSphere);
            });
        }

        _buildParticleBridges() {
            this.bridgeCurves = [];
            this.packetParticles = [];

            const inclination = 0.2618; // 15 degrees tilt

            TOPOLOGY_NODES_DATA.forEach((data, index) => {
                const angle = data.orbitAngle;
                const r = data.radius;
                
                // Nominal 3D endpoint on inclined orbital plane
                const targetPos = new THREE.Vector3(
                    Math.cos(angle) * r,
                    Math.sin(angle) * r * Math.sin(inclination) + Math.sin(index * 1.5) * 0.4,
                    Math.sin(angle) * r * Math.cos(inclination)
                );

                // Curve with arch factor h = 1.6
                const midPoint = new THREE.Vector3(
                    targetPos.x * 0.5,
                    targetPos.y * 0.5 + 1.6,
                    targetPos.z * 0.5
                );

                const curve = new THREE.QuadraticBezierCurve3(
                    new THREE.Vector3(0, 0, 0),
                    midPoint,
                    targetPos
                );

                // Translucent energy spline tube
                const tubeGeo = new THREE.TubeGeometry(curve, 40, 0.028, 8, false);
                const tubeMat = new THREE.MeshBasicMaterial({
                    color: data.color,
                    transparent: true,
                    opacity: 0.28
                });
                const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
                this.scene.add(tubeMesh);

                this.bridgeCurves.push({
                    curve: curve,
                    tubeMesh: tubeMesh,
                    nodeIndex: index,
                    targetPos: targetPos
                });

                // Discrete flowing energy packets along spline
                for (let p = 0; p < this.options.pulsePacketCount; p++) {
                    const packetGeo = new THREE.SphereGeometry(0.065, 8, 8);
                    const packetMat = new THREE.MeshBasicMaterial({
                        color: (p % 2 === 0) ? BRAND_PALETTE.mintCyan : data.color,
                        transparent: true,
                        opacity: 0.95
                    });
                    const packetMesh = new THREE.Mesh(packetGeo, packetMat);
                    this.scene.add(packetMesh);

                    this.packetParticles.push({
                        mesh: packetMesh,
                        curveIndex: index,
                        progress: p / this.options.pulsePacketCount,
                        speed: 0.08 + (index * 0.015)
                    });
                }
            });
        }

        _buildCosmicDust() {
            // Instanced point cloud for 60fps ambient atmospheric depth (<1 draw call)
            const count = this.options.particleCount;
            const geometry = new THREE.BufferGeometry();
            const positions = new Float32Array(count * 3);
            const colors = new Float32Array(count * 3);

            const cSapphire = new THREE.Color(BRAND_PALETTE.electricSapphire);
            const cMint = new THREE.Color(BRAND_PALETTE.mintCyan);
            const cAmber = new THREE.Color(BRAND_PALETTE.warmAmber);

            for (let i = 0; i < count; i++) {
                // Fibonacci sphere volume distribution (Radius 22.0)
                const phi = Math.acos(-1 + (2 * i) / count);
                const theta = Math.sqrt(count * Math.PI) * phi;
                const r = 4.0 + Math.random() * 18.0;

                positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
                positions[i * 3 + 1] = (Math.random() - 0.5) * 12.0;
                positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);

                // Mix palette colors
                let col = (i % 3 === 0) ? cSapphire : ((i % 3 === 1) ? cMint : cAmber);
                colors[i * 3] = col.r;
                colors[i * 3 + 1] = col.g;
                colors[i * 3 + 2] = col.b;
            }

            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

            const material = new THREE.PointsMaterial({
                size: 0.12,
                vertexColors: true,
                transparent: true,
                opacity: 0.65,
                blending: THREE.AdditiveBlending
            });

            this.cosmicDust = new THREE.Points(geometry, material);
            this.scene.add(this.cosmicDust);
        }

        // ---------------------------------------------------------------------
        // 5. RAYCASTER & EVENT BUS INTERACTION
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
                // Ensure drag threshold (<4px) to distinguish drag from deliberate click
                const dist = Math.hypot(e.clientX - this._pointerDownPos.x, e.clientY - this._pointerDownPos.y);
                if (dist > 4.0) return;

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

            const targetScale = isHovered ? 1.25 : 1.0;
            nodeGroup.scale.set(targetScale, targetScale, targetScale);
        }

        selectNode(nodeGroup, nodeData) {
            this._selectedNode = nodeGroup;

            // Compute camera destination: offset position oriented outward from center
            const nodeWorldPos = new THREE.Vector3();
            nodeGroup.getWorldPosition(nodeWorldPos);

            const offsetDir = nodeWorldPos.clone().normalize();
            const targetCamPos = nodeWorldPos.clone().add(offsetDir.multiplyScalar(4.2)).add(new THREE.Vector3(0, 1.8, 0));

            this._startCameraLerp(targetCamPos, nodeWorldPos);

            if (this.controls) {
                this.controls.autoRotate = false;
            }

            this.emit('node_select', { node: nodeData, worldPosition: nodeWorldPos });
            this.updateHUD(nodeData);
        }

        resetView() {
            this._selectedNode = null;
            this._startCameraLerp(this.defaultCameraPos, this.controlsTarget);

            if (this.controls) {
                this.controls.autoRotate = this.options.autoRotate;
            }

            this.emit('node_deselect', {});
            this.hideHUD();
        }

        focusNodeByKey(nodeKey) {
            if (!this.satelliteNodes || !this.satelliteNodes.length) return;
            const targetGroup = this.satelliteNodes.find(g => {
                const nd = g.userData && g.userData.nodeData;
                return nd && (nd.key === nodeKey || nd.id === nodeKey || (nd.key && nd.key.toLowerCase() === (nodeKey || '').toLowerCase()));
            });
            if (targetGroup) {
                this.selectNode(targetGroup, targetGroup.userData.nodeData);
            }
        }

        _startCameraLerp(toPos, toTarget) {
            this._cameraLerp.active = true;
            this._cameraLerp.startTime = this._clock.getElapsedTime();
            this._cameraLerp.fromPos.copy(this.camera.position);
            this._cameraLerp.toPos.copy(toPos);
            this._cameraLerp.fromTarget.copy(this.controls ? this.controls.target : this.controlsTarget);
            this._cameraLerp.toTarget.copy(toTarget);
        }

        // Cubic ease-in-out easing for cinematic camera movement
        _easeInOutCubic(t) {
            return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        }

        // ---------------------------------------------------------------------
        // 6. EVENT BUS ARCHITECTURE (PUB/SUB)
        // ---------------------------------------------------------------------

        on(event, handler) {
            if (!this._listeners.has(event)) {
                this._listeners.set(event, []);
            }
            this._listeners.get(event).push(handler);
            return this;
        }

        off(event, handler) {
            if (!this._listeners.has(event)) return this;
            const list = this._listeners.get(event).filter(cb => cb !== handler);
            this._listeners.set(event, list);
            return this;
        }

        emit(event, payload) {
            if (!this._listeners.has(event)) return;
            this._listeners.get(event).forEach(cb => {
                try {
                    cb(payload);
                } catch (err) {
                    console.error('[InnoriaTopology3D] Event handler error (' + event + '):', err);
                }
            });
        }

        // ---------------------------------------------------------------------
        // 7. HUD DOM BINDINGS (WCAG AAA COMPLIANT)
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
                    background: rgba(5, 16, 30, 0.94);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    border: 1px solid rgba(47, 128, 237, 0.35);
                    border-radius: 12px;
                    color: #FFFFFF;
                    z-index: 1000;
                    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.65), 0 0 20px rgba(47, 128, 237, 0.2);
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
                    <span class="badge" style="background: rgba(47,128,237,0.18); border: 1px solid ${hexColor}; color: #FFFFFF; font-weight: 600; font-size: 0.82rem; padding: 0.25rem 0.65rem; border-radius: 6px;">
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
                    <button type="button" class="btn-close btn-close-white" aria-label="Close telemetry view" style="opacity: 0.8;"></button>
                </div>
                
                <p style="font-size: 0.88rem; line-height: 1.4; color: #E2E8F0; margin-bottom: 1.2rem;">
                    ${nodeData.tagline}
                </p>

                <div class="metrics-grid mb-3">
                    ${metricsHtml}
                </div>

                <div class="d-flex gap-2 mt-3 pt-2">
                    <a href="${nodeData.deepLink}" class="btn w-100 py-2 text-center text-decoration-none fw-bold" style="background: ${hexColor}; color: #05101E; border-radius: 8px; font-size: 0.9rem; transition: opacity 0.2s ease;">
                        Inspect Architecture &rarr;
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
        }

        hideHUD() {
            if (this.hudElement) {
                this.hudElement.style.display = 'none';
            }
        }

        // ---------------------------------------------------------------------
        // 8. ANIMATION & 60 FPS RENDER LOOP
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

        _render() {
            const delta = this._clock.getDelta();
            const elapsed = this._clock.getElapsedTime();

            // 1. Central Core Dynamics
            if (this.coreGroup) {
                this.coreGroup.rotation.y = elapsed * 0.22;
                this.latticeMesh.rotation.x = elapsed * -0.15;
                this.latticeMesh.rotation.z = elapsed * 0.12;

                this.ringMesh1.rotation.z = elapsed * 0.45;
                this.ringMesh2.rotation.z = -elapsed * 0.35;

                // Pulsate plasma
                const scalePulse = 1.0 + 0.06 * Math.sin(elapsed * 2.5);
                this.plasmaMesh.scale.set(scalePulse, scalePulse, scalePulse);

                // Update glow shader uniform
                if (this.coreGlowUniforms) {
                    this.coreGlowUniforms.time.value = elapsed;
                }
            }

            // 2. Orbital Satellite Motions
            const inclination = 0.2618;
            this.satelliteNodes.forEach((nodeGroup, i) => {
                const data = nodeGroup.userData.nodeData;
                
                // Steady orbital drift
                const currentAngle = data.orbitAngle + (elapsed * data.orbitSpeed * 0.35);
                const r = data.radius;

                const posX = Math.cos(currentAngle) * r;
                const posY = Math.sin(currentAngle) * r * Math.sin(inclination) + Math.sin(elapsed * 1.8 + i) * 0.22;
                const posZ = Math.sin(currentAngle) * r * Math.cos(inclination);

                nodeGroup.position.set(posX, posY, posZ);

                // Self rotation
                nodeGroup.children[0].rotation.y = elapsed * 0.6;
                nodeGroup.children[0].rotation.x = elapsed * 0.3;

                // Update spline endpoint
                if (this.bridgeCurves[i]) {
                    this.bridgeCurves[i].targetPos.set(posX, posY, posZ);
                }
            });

            // 3. Flowing Energy Packets Along Splines
            this.packetParticles.forEach(p => {
                p.progress += delta * p.speed;
                if (p.progress > 1.0) p.progress = 0.0;

                const bridge = this.bridgeCurves[p.curveIndex];
                if (bridge) {
                    const pos = bridge.curve.getPointAt(p.progress);
                    p.mesh.position.copy(pos);
                }
            });

            // 4. Cosmic Dust Gyroscopic Rotation
            if (this.cosmicDust) {
                this.cosmicDust.rotation.y = elapsed * 0.02;
                this.cosmicDust.rotation.x = elapsed * 0.01;
            }

            // 5. Camera Interpolation
            if (this._cameraLerp.active) {
                const progress = (elapsed - this._cameraLerp.startTime) / this._cameraLerp.duration;
                if (progress >= 1.0) {
                    this._cameraLerp.active = false;
                    this.camera.position.copy(this._cameraLerp.toPos);
                    if (this.controls) this.controls.target.copy(this._cameraLerp.toTarget);
                } else {
                    const t = this._easeInOutCubic(progress);
                    this.camera.position.lerpVectors(this._cameraLerp.fromPos, this._cameraLerp.toPos, t);
                    if (this.controls) {
                        this.controls.target.lerpVectors(this._cameraLerp.fromTarget, this._cameraLerp.toTarget, t);
                    }
                }
            }

            // 6. OrbitControls Update
            if (this.controls && !this._cameraLerp.active) {
                this.controls.update();
            }

            this.renderer.render(this.scene, this.camera);
        }

        // ---------------------------------------------------------------------
        // 9. RESIZE & INTERSECTION OBSERVER (AUTO-PAUSE FOR BATTERY / 60 FPS)
        // ---------------------------------------------------------------------

        _setupResizeHandler() {
            this._resizeObserver = new ResizeObserver(entries => {
                for (let entry of entries) {
                    const width = entry.contentRect.width;
                    const height = entry.contentRect.height;
                    if (width > 0 && height > 0) {
                        this.camera.aspect = width / height;
                        this.camera.updateProjectionMatrix();
                        this.renderer.setSize(width, height);
                    }
                }
            });
            this._resizeObserver.observe(this.container);
        }

        _setupVisibilityObserver() {
            if ('IntersectionObserver' in window) {
                this._intersectionObserver = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            this.start();
                        } else {
                            this.stop();
                        }
                    });
                }, { threshold: 0.05 });
                this._intersectionObserver.observe(this.container);
            }
        }

        // ---------------------------------------------------------------------
        // 10. CLEANUP & MEMORY DISPOSAL
        // ---------------------------------------------------------------------

        dispose() {
            this.stop();

            if (this._resizeObserver) this._resizeObserver.disconnect();
            if (this._intersectionObserver) this._intersectionObserver.disconnect();
            if (this._unbindEvents) this._unbindEvents();
            if (this.controls) this.controls.dispose();

            // Recursive GPU buffer and material cleanup
            this.scene.traverse(object => {
                if (object.geometry) {
                    object.geometry.dispose();
                }
                if (object.material) {
                    if (Array.isArray(object.material)) {
                        object.material.forEach(mat => mat.dispose());
                    } else {
                        object.material.dispose();
                    }
                }
            });

            this.renderer.dispose();
            if (this.domElement && this.domElement.parentNode) {
                this.domElement.parentNode.removeChild(this.domElement);
            }

            if (this.hudElement && this.hudElement.parentNode) {
                this.hudElement.parentNode.removeChild(this.hudElement);
            }

            this._listeners.clear();
            console.log('[InnoriaTopology3D] Disposed successfully with zero memory leak.');
        }
    }

    // Auto-initialization for Odoo Website / DOM
    function autoInit() {
        if (typeof document === 'undefined') return;
        const viewports = document.querySelectorAll('#innoriaTopologyViewport, [data-innoria-3d="topology"], .innoria-topology-container');
        viewports.forEach(vp => {
            if (!vp.__innoriaEngine) {
                try {
                    const engine = new InnoriaTopologyEngine(vp);
                    vp.__innoriaEngine = engine;
                    if (typeof window !== 'undefined') {
                        window.__innoriaTopology = engine;
                    }

                    // Wire up external or internal data-action buttons
                    const bindButtons = (rootEl) => {
                        const btns = rootEl.querySelectorAll('[data-action="focus-node"], [data-action="reset-view"]');
                        btns.forEach(btn => {
                            btn.addEventListener('click', (e) => {
                                e.preventDefault();
                                const action = btn.getAttribute('data-action');
                                if (action === 'focus-node') {
                                    const key = btn.getAttribute('data-node-key');
                                    engine.focusNodeByKey(key);
                                    btns.forEach(b => b.classList.remove('active'));
                                    btn.classList.add('active');
                                } else if (action === 'reset-view') {
                                    engine.resetView();
                                    btns.forEach(b => b.classList.remove('active'));
                                }
                            });
                        });
                    };

                    bindButtons(vp);
                    const section = vp.closest('section');
                    if (section) bindButtons(section);
                } catch (err) {
                    console.error('[InnoriaTopology3D] AutoInit error:', err);
                }
            }
        });
    }

    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', autoInit);
        } else {
            autoInit();
        }
        window.InnoriaTopologyEngine = InnoriaTopologyEngine;
        window.InnoriaTopology3D = {
            InnoriaTopologyEngine,
            autoInit,
            BRAND_PALETTE,
            TOPOLOGY_NODES_DATA
        };
    }

    InnoriaTopologyEngine.autoInit = autoInit;
    InnoriaTopologyEngine.BRAND_PALETTE = BRAND_PALETTE;
    InnoriaTopologyEngine.TOPOLOGY_NODES_DATA = TOPOLOGY_NODES_DATA;

    return InnoriaTopologyEngine;
}));
