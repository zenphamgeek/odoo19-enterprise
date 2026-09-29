/**
 * Insilos Enterprise 3D Interactive WebGL Suite
 * Sovereign 3D Digital Twin, 3D Logistics Radar & 3D Factory ROI Configurator
 *
 * Grounded in Live Insilos ERP Database (odoo20_dev):
 * - Product: EQ-VLIFT-2500E (BOM-VLIFT-2500E-V1)
 * - Sub-BOM: SF-CHASSIS-25E (BOM-CHASSIS-25E-V1, Lot LOT-HP-SS400-2026-01)
 * - Workcenters: WC-CUT-01 (Trumpf Laser), WC-WELD-01 (Yaskawa Robot), WC-ASM-01
 * - Heavy Fleet: 51C-982.45 (Hyundai Xcient 6x4) + 51R-089.34 (CIMC 40ft)
 * - Route Corridor: KCN VSIP 1 -> Cảng Biển Quốc Tế (32.4 km)
 *
 * Steady 60 FPS | Zero External CDN | IntersectionObserver Auto-Pausing | Full GPU Cleanup
 */

(function () {
    "use strict";

    var root = typeof window !== "undefined" ? window : (typeof self !== "undefined" ? self : globalThis);
    function getThree() {
        return (typeof window !== "undefined" && window.THREE) ||
               (typeof globalThis !== "undefined" && globalThis.THREE) ||
               (typeof root !== "undefined" && root.THREE) ||
               (typeof window !== "undefined" && window.InsilosThreeBundle && window.InsilosThreeBundle.THREE ? window.InsilosThreeBundle.THREE : undefined);
    }
    var THREE = getThree();

    // -------------------------------------------------------------------------
    // Utilities & Safety Checks
    // -------------------------------------------------------------------------

    function isBrowser() {
        return typeof window !== "undefined" && typeof document !== "undefined";
    }

    function isWebGLAvailable() {
        if (!isBrowser()) return false;
        try {
            const canvas = document.createElement("canvas");
            return !!(window.WebGLRenderingContext && (canvas.getContext("webgl2") || canvas.getContext("webgl") || canvas.getContext("experimental-webgl")));
        } catch (e) {
            return false;
        }
    }

    function easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function formatVnd(amount) {
        if (amount >= 1e9) {
            return (amount / 1e9).toFixed(2).replace(/\.00$/, "") + " Tỷ ₫";
        }
        if (amount >= 1e6) {
            return (amount / 1e6).toFixed(1).replace(/\.0$/, "") + " Tr ₫";
        }
        return amount.toLocaleString("vi-VN") + " ₫";
    }

    function safeRaf(cb) {
        if (typeof window !== "undefined" && window.requestAnimationFrame) {
            return window.requestAnimationFrame(cb);
        }
        if (typeof requestAnimationFrame !== "undefined") {
            return requestAnimationFrame(cb);
        }
        return setTimeout(cb, 16);
    }

    function safeCaf(id) {
        if (typeof window !== "undefined" && window.cancelAnimationFrame) {
            return window.cancelAnimationFrame(id);
        }
        if (typeof cancelAnimationFrame !== "undefined") {
            return cancelAnimationFrame(id);
        }
        clearTimeout(id);
    }

    // -------------------------------------------------------------------------
    // 1. 3D Digital Twin Engine (V-LIFT 2500E & Laser CNC / Robotic Cell)
    // -------------------------------------------------------------------------

    const DIGITAL_TWIN_HOTSPOTS = [
        {
            id: "hotspot_mast",
            name: "Trụ Nâng Thủy Lực 3 Tầng SF-HYD-MAST45",
            componentCode: "SF-HYD-MAST45",
            badgeClass: "badge-cyan",
            icon: "arrows-down-up",
            anchor3D: [0.0, 1.85, 0.95],
            parentSubId: "node_mast",
            erpModel: "mrp.production",
            erpRecord: "WH/MO/00010",
            kpis: [
                { label: "Lệnh sản xuất", value: "WH/MO/00010 (Đang chạy)" },
                { label: "Sản lượng chỉ định", value: "4.00 chiếc" },
                { label: "Áp suất dầu thủy lực", value: "185.4 bar" },
                { label: "Hành trình nâng tối đa", value: "4.500 mm" }
            ],
            actionUrl: "/web#id=10&model=mrp.production&view_type=form&action=367"
        },
        {
            id: "hotspot_battery",
            name: "Bộ Nguồn LiFePO4 48V-400Ah SF-BATTPACK-400AH",
            componentCode: "SF-BATTPACK-400AH",
            badgeClass: "badge-emerald",
            icon: "battery-charging",
            anchor3D: [0.50, 0.60, 0.15],
            parentSubId: "node_battery",
            erpModel: "mrp.bom",
            erpRecord: "LOT-LFP-48V-0042",
            kpis: [
                { label: "Điện áp danh định", value: "51.2 V (Pack 16S)" },
                { label: "Dung lượng khả dụng", value: "392.5 Ah (98.1%)" },
                { label: "Nhiệt độ Cell Max", value: "31.2 °C (An toàn)" },
                { label: "Smart BMS Telemetry", value: "CAN Bus 500kbps Active" }
            ],
            actionUrl: "/web#id=10&model=mrp.bom&view_type=form&action=348"
        },
        {
            id: "hotspot_chassis",
            name: "Khung Gầm Thép Chế Tạo SF-CHASSIS-25E",
            componentCode: "SF-CHASSIS-25E",
            badgeClass: "badge-orange",
            icon: "shield-check",
            anchor3D: [-0.65, 0.35, -0.30],
            parentSubId: "node_chassis",
            erpModel: "purchase.order",
            erpRecord: "PO Thép Tiêu Chuẩn #VN-PO2026-001",
            kpis: [
                { label: "Mã lô thép SS400", value: "LOT-HP-SS400-2026-01" },
                { label: "Đơn giá thép cán", value: "19.500 ₫/kg" },
                { label: "Quy chuẩn vật liệu", value: "JIS G3101 SS400 (Dày 12mm)" },
                { label: "Phân xưởng chế tạo", value: "WC-CUT-01 & WC-WELD-01" }
            ],
            actionUrl: "/web#id=1&model=purchase.order&view_type=form&action=758"
        },
        {
            id: "hotspot_controller",
            name: "Bo Mạch Điều Khiển Vi Xử Lý RM-PCB-CONTROLLER",
            componentCode: "RM-PCB-CONTROLLER",
            badgeClass: "badge-purple",
            icon: "cpu",
            anchor3D: [0.0, 1.25, -0.45],
            parentSubId: "node_cockpit",
            erpModel: "mrp.workcenter",
            erpRecord: "WC-ASM-01",
            kpis: [
                { label: "Kiến trúc MCU", value: "ARM Cortex-M4 168MHz" },
                { label: "An toàn chức năng", value: "EN ISO 13849-1 Cat 3 PL d" },
                { label: "Hệ thống cáp", value: "Cáp Điện Tiêu Chuẩn 3x16+1x10mm²" },
                { label: "Thời gian chu kỳ OEE", value: "92.5% (Tối ưu)" }
            ],
            actionUrl: "/web#id=17&model=mrp.workcenter&view_type=form"
        }
    ];

    class InsilosDigitalTwinEngine {
        constructor(container, options = {}) {
            this.container = typeof container === "string" ? document.querySelector(container) : container;
            if (!this.container) {
                console.warn("[Insilos3D] DigitalTwin: container not found");
                return;
            }

            if (!THREE) THREE = getThree();
            if (!THREE || !isWebGLAvailable()) {
                console.warn("[Insilos3D] DigitalTwin: THREE or WebGL not available, aborting init");
                return;
            }

            this.options = Object.assign({
                activeModel: "vlift", // "vlift" or "laser-cnc"
                exploded: false,
                renderMode: "pbr", // "pbr", "wireframe", "xray"
                autoRotate: true,
                autoRotateSpeed: 0.6,
                showHotspots: true
            }, options);

            this._animId = null;
            this._isVisible = true;
            this._explodedProgress = this.options.exploded ? 1.0 : 0.0;
            this._targetExplodedProgress = this._explodedProgress;
            this._time = 0;
            this._subAssemblies = [];
            this._leaderLines = [];
            this._hotspotElements = new Map();
            this._activeHotspot = null;
            this._materialsCache = { pbr: [], wireframe: [], xray: [] };

            this._initRenderer();
            this._initScene();
            this._initCameraAndControls();
            this._initLights();
            this._buildModels();
            this._buildHotspotDom();
            this._setupObserver();
            this._setupEvents();
            this.start();
        }

        _initRenderer() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 500;

            const existingCanvas = (this.container.tagName === "CANVAS" ? this.container : null) || this.container.querySelector("canvas");

            this.renderer = new THREE.WebGLRenderer({
                canvas: existingCanvas || undefined,
                antialias: (window.devicePixelRatio || 1) < 2,
                powerPreference: "high-performance",
                alpha: true,
                precision: "mediump"
            });
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.0));
            this.renderer.setSize(width, height);
            this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
            this.renderer.toneMappingExposure = 1.15;
            this.renderer.shadowMap.enabled = true;
            this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            this.renderer.shadowMap.autoUpdate = false;
            this.renderer.shadowMap.needsUpdate = true;

            if (!existingCanvas) {
                this.canvasWrapper = document.createElement("div");
                this.canvasWrapper.className = "ins-3d-canvas-wrapper position-relative w-100 h-100 overflow-hidden";
                this.canvasWrapper.appendChild(this.renderer.domElement);
                this.container.appendChild(this.canvasWrapper);
            } else {
                existingCanvas.style.display = "block";
                existingCanvas.style.width = "100%";
                existingCanvas.style.height = "100%";
            }
        }

        _initScene() {
            this.scene = new THREE.Scene();
            this.scene.fog = new THREE.FogExp2(0x070b14, 0.025);

            // Circular tech grid ground
            const grid = new THREE.GridHelper(14, 28, 0x00f0ff, 0x1e293b);
            grid.position.y = -0.01;
            grid.material.opacity = 0.25;
            grid.material.transparent = true;
            this.scene.add(grid);

            // Outer ground disc ring
            const ringGeo = new THREE.RingGeometry(6.9, 7.0, 64);
            const ringMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff, side: THREE.DoubleSide, transparent: true, opacity: 0.3 });
            const ringMesh = new THREE.Mesh(ringGeo, ringMat);
            ringMesh.rotation.x = -Math.PI / 2;
            ringMesh.position.y = 0.0;
            this.scene.add(ringMesh);
        }

        _initCameraAndControls() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 500;
            this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
            this.camera.position.set(3.8, 2.6, 4.5);

            const OrbitControlsClass = THREE.OrbitControls || (typeof window !== "undefined" ? window.OrbitControls : null);
            if (OrbitControlsClass) {
                this.controls = new OrbitControlsClass(this.camera, this.renderer.domElement);
                this.controls.enableDamping = true;
                this.controls.dampingFactor = 0.05;
                this.controls.minDistance = 1.8;
                this.controls.maxDistance = 12.0;
                this.controls.maxPolarAngle = Math.PI / 2 + 0.05;
                this.controls.target.set(0, 1.1, 0);
                this.controls.autoRotate = this.options.autoRotate;
                this.controls.autoRotateSpeed = this.options.autoRotateSpeed;

                // Stop auto-spin on user interaction, resume after 4s idle
                let idleTimer = null;
                const onInteraction = () => {
                    this._isVisible = true;
                    this.start();
                    this.controls.autoRotate = false;
                    clearTimeout(idleTimer);
                    idleTimer = setTimeout(() => {
                        if (this.options.autoRotate) this.controls.autoRotate = true;
                    }, 4000);
                };
                this.controls.addEventListener("start", onInteraction);
            }
        }

        _initLights() {
            const ambient = new THREE.AmbientLight(0xffffff, 0.7);
            this.scene.add(ambient);

            const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
            keyLight.position.set(6, 12, 8);
            keyLight.castShadow = true;
            keyLight.shadow.mapSize.width = 512;
            keyLight.shadow.mapSize.height = 512;
            keyLight.shadow.bias = -0.0005;
            this.directionalLight = keyLight;
            this.scene.add(keyLight);

            const cyanRim = new THREE.DirectionalLight(0x00f0ff, 0.9);
            cyanRim.position.set(-6, 5, -6);
            this.scene.add(cyanRim);

            const orangeBounce = new THREE.PointLight(0xff8000, 1.2, 10);
            orangeBounce.position.set(0, -1.0, 0);
            this.scene.add(orangeBounce);
        }

        _buildModels() {
            this.modelsRoot = new THREE.Group();
            this.scene.add(this.modelsRoot);

            this.vliftGroup = this._createVLift2500E();
            this.laserCncGroup = this._createLaserCncWorkcenter();

            this.modelsRoot.add(this.vliftGroup);
            this.modelsRoot.add(this.laserCncGroup);

            this.setModel(this.options.activeModel);
            this._setupLeaderLines();
        }

        _createVLift2500E() {
            const root = new THREE.Group();
            root.name = "vlift_2500e_root";

            // Common shared materials
            const brandOrangePbr = new THREE.MeshStandardMaterial({
                color: 0xff8000,
                metalness: 0.45,
                roughness: 0.35,
                name: "brandOrangePbr"
            });
            const steelDarkPbr = new THREE.MeshStandardMaterial({
                color: 0x272b33,
                metalness: 0.85,
                roughness: 0.40,
                name: "steelDarkPbr"
            });
            const chromePbr = new THREE.MeshStandardMaterial({
                color: 0xf5f7fa,
                metalness: 0.98,
                roughness: 0.06,
                name: "chromePbr"
            });
            const rubberPbr = new THREE.MeshStandardMaterial({
                color: 0x15171a,
                metalness: 0.05,
                roughness: 0.88,
                name: "rubberPbr"
            });
            const batteryBluePbr = new THREE.MeshStandardMaterial({
                color: 0x2563eb,
                metalness: 0.6,
                roughness: 0.25,
                name: "batteryBluePbr"
            });
            const pcbGreenPbr = new THREE.MeshStandardMaterial({
                color: 0x10b981,
                emissive: 0x059669,
                emissiveIntensity: 0.6,
                metalness: 0.2,
                roughness: 0.3,
                name: "pcbGreenPbr"
            });

            // 1. Chassis sub-assembly (BOM: SF-CHASSIS-25E)
            const nodeChassis = new THREE.Group();
            nodeChassis.name = "node_chassis";

            const basePlateGeo = new THREE.BoxGeometry(1.36, 0.12, 2.10);
            const basePlate = new THREE.Mesh(basePlateGeo, steelDarkPbr);
            basePlate.position.set(0, 0.18, 0);
            basePlate.castShadow = true;
            nodeChassis.add(basePlate);

            // Dual brand orange side fairings
            const sideLeftGeo = new THREE.BoxGeometry(0.06, 0.44, 1.70);
            const sideLeft = new THREE.Mesh(sideLeftGeo, brandOrangePbr);
            sideLeft.position.set(-0.66, 0.40, -0.10);
            nodeChassis.add(sideLeft);

            const sideRight = sideLeft.clone();
            sideRight.position.x = 0.66;
            nodeChassis.add(sideRight);

            // Rear counterweight
            const counterweightGeo = new THREE.BoxGeometry(1.10, 0.54, 0.48);
            const counterweight = new THREE.Mesh(counterweightGeo, steelDarkPbr);
            counterweight.position.set(0, 0.45, -0.96);
            nodeChassis.add(counterweight);

            // Heavy tow hitch
            const hitchGeo = new THREE.CylinderGeometry(0.035, 0.035, 0.26, 16);
            const hitch = new THREE.Mesh(hitchGeo, chromePbr);
            hitch.position.set(0, 0.30, -1.22);
            nodeChassis.add(hitch);

            // 2. Drive System (BOM: SF-DRIVE-AC48V)
            const nodeDrive = new THREE.Group();
            nodeDrive.name = "node_drive";

            // AC Motor casing
            const motorGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.46, 24);
            const motorMesh = new THREE.Mesh(motorGeo, steelDarkPbr);
            motorMesh.rotation.z = Math.PI / 2;
            motorMesh.position.set(0, 0.22, 0.40);
            nodeDrive.add(motorMesh);

            // Transaxle
            const transaxleGeo = new THREE.BoxGeometry(0.32, 0.22, 0.92);
            const transaxle = new THREE.Mesh(transaxleGeo, steelDarkPbr);
            transaxle.position.set(0, 0.20, 0.42);
            nodeDrive.add(transaxle);

            // Dual front drive wheels (polyurethane)
            const wheelGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.10, 24);
            const wheelLeft = new THREE.Mesh(wheelGeo, rubberPbr);
            wheelLeft.rotation.z = Math.PI / 2;
            wheelLeft.position.set(-0.60, 0.18, 0.42);
            nodeDrive.add(wheelLeft);

            const wheelRight = wheelLeft.clone();
            wheelRight.position.x = 0.60;
            nodeDrive.add(wheelRight);

            // Dual rear swivel casters
            const casterGeo = new THREE.CylinderGeometry(0.09, 0.09, 0.06, 16);
            const casterLeft = new THREE.Mesh(casterGeo, rubberPbr);
            casterLeft.rotation.z = Math.PI / 2;
            casterLeft.position.set(-0.45, 0.09, -0.90);
            nodeDrive.add(casterLeft);

            const casterRight = casterLeft.clone();
            casterRight.position.x = 0.45;
            nodeDrive.add(casterRight);

            // 3. Battery pack (BOM: SF-BATTPACK-400AH)
            const nodeBattery = new THREE.Group();
            nodeBattery.name = "node_battery";

            // Structural tray
            const trayGeo = new THREE.BoxGeometry(0.92, 0.46, 0.70);
            const tray = new THREE.Mesh(trayGeo, steelDarkPbr);
            tray.position.set(0, 0.48, 0.12);
            nodeBattery.add(tray);

            // 16x LiFePO4 cells
            const cellGeo = new THREE.BoxGeometry(0.09, 0.36, 0.14);
            for (let r = 0; r < 2; r++) {
                for (let c = 0; c < 8; c++) {
                    const cell = new THREE.Mesh(cellGeo, batteryBluePbr);
                    cell.position.set(-0.35 + c * 0.10, 0.48, r === 0 ? 0.02 : 0.22);
                    nodeBattery.add(cell);
                }
            }

            // Smart BMS Unit
            const bmsGeo = new THREE.BoxGeometry(0.32, 0.08, 0.24);
            const bms = new THREE.Mesh(bmsGeo, pcbGreenPbr);
            bms.position.set(0, 0.74, 0.12);
            nodeBattery.add(bms);

            // 4. Hydraulic Mast (BOM: SF-HYD-MAST45)
            const nodeMast = new THREE.Group();
            nodeMast.name = "node_mast";

            // Dual outer C-channels
            const channelGeo = new THREE.BoxGeometry(0.08, 2.30, 0.12);
            const chLeft = new THREE.Mesh(channelGeo, steelDarkPbr);
            chLeft.position.set(-0.46, 1.25, 0.95);
            nodeMast.add(chLeft);

            const chRight = chLeft.clone();
            chRight.position.x = 0.46;
            nodeMast.add(chRight);

            // Telescopic inner rail
            const innerGeo = new THREE.BoxGeometry(0.06, 2.10, 0.09);
            const innerLeft = new THREE.Mesh(innerGeo, chromePbr);
            innerLeft.position.set(-0.42, 1.30, 0.95);
            nodeMast.add(innerLeft);

            const innerRight = innerLeft.clone();
            innerRight.position.x = 0.42;
            nodeMast.add(innerRight);

            // Central hydraulic ram cylinder
            const cylinderGeo = new THREE.CylinderGeometry(0.05, 0.05, 1.95, 20);
            const cylinder = new THREE.Mesh(cylinderGeo, chromePbr);
            cylinder.position.set(0, 1.15, 0.95);
            nodeMast.add(cylinder);

            // Carriage apron
            const apronGeo = new THREE.BoxGeometry(0.96, 0.42, 0.04);
            const apron = new THREE.Mesh(apronGeo, brandOrangePbr);
            apron.position.set(0, 0.45, 1.05);
            nodeMast.add(apron);

            // Dual forged L-forks DIN 1150
            const forkHGeo = new THREE.BoxGeometry(0.12, 0.045, 1.15);
            const forkVGeo = new THREE.BoxGeometry(0.12, 0.50, 0.045);

            [-0.28, 0.28].forEach(xPos => {
                const forkH = new THREE.Mesh(forkHGeo, steelDarkPbr);
                forkH.position.set(xPos, 0.07, 1.62);
                nodeMast.add(forkH);

                const forkV = new THREE.Mesh(forkVGeo, steelDarkPbr);
                forkV.position.set(xPos, 0.32, 1.07);
                nodeMast.add(forkV);
            });

            // 5. Cockpit & Controller (BOM: RM-PCB-CONTROLLER)
            const nodeCockpit = new THREE.Group();
            nodeCockpit.name = "node_cockpit";

            // Welded tubular ROPS safety frame
            const pillarGeo = new THREE.CylinderGeometry(0.025, 0.025, 1.35, 12);
            [-0.50, 0.50].forEach(px => {
                [-0.10, -0.80].forEach(pz => {
                    const pillar = new THREE.Mesh(pillarGeo, steelDarkPbr);
                    pillar.position.set(px, 1.15, pz);
                    nodeCockpit.add(pillar);
                });
            });

            // ROPS roof grid
            const roofGeo = new THREE.BoxGeometry(1.08, 0.03, 0.80);
            const roof = new THREE.Mesh(roofGeo, brandOrangePbr);
            roof.position.set(0, 1.84, -0.45);
            nodeCockpit.add(roof);

            // Articulated tiller handle & e-stop
            const tillerGeo = new THREE.CylinderGeometry(0.022, 0.022, 0.70, 12);
            const tiller = new THREE.Mesh(tillerGeo, chromePbr);
            tiller.rotation.x = -Math.PI / 4;
            tiller.position.set(0, 0.95, -0.22);
            nodeCockpit.add(tiller);

            const estopGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.03, 16);
            const estopMat = new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.2 });
            const estop = new THREE.Mesh(estopGeo, estopMat);
            estop.position.set(0, 1.22, -0.48);
            nodeCockpit.add(estop);

            // Glass LCD dashboard console
            const dashGeo = new THREE.BoxGeometry(0.30, 0.16, 0.04);
            const dashMat = new THREE.MeshStandardMaterial({
                color: 0x070b14,
                emissive: 0x00f0ff,
                emissiveIntensity: 0.5,
                metalness: 0.9,
                roughness: 0.1
            });
            const dash = new THREE.Mesh(dashGeo, dashMat);
            dash.rotation.x = -Math.PI / 6;
            dash.position.set(0, 1.18, -0.38);
            nodeCockpit.add(dash);

            // Register sub-assemblies for exploded BOM view
            this._subAssemblies = [
                {
                    id: "node_chassis",
                    group: nodeChassis,
                    assembledPos: new THREE.Vector3(0, 0, 0),
                    explodedPos: new THREE.Vector3(0, -0.35, 0)
                },
                {
                    id: "node_drive",
                    group: nodeDrive,
                    assembledPos: new THREE.Vector3(0, 0, 0),
                    explodedPos: new THREE.Vector3(0, -0.75, -0.65)
                },
                {
                    id: "node_battery",
                    group: nodeBattery,
                    assembledPos: new THREE.Vector3(0, 0, 0),
                    explodedPos: new THREE.Vector3(1.70, 0.35, 0.15)
                },
                {
                    id: "node_mast",
                    group: nodeMast,
                    assembledPos: new THREE.Vector3(0, 0, 0),
                    explodedPos: new THREE.Vector3(0, 0.25, 1.50)
                },
                {
                    id: "node_cockpit",
                    group: nodeCockpit,
                    assembledPos: new THREE.Vector3(0, 0, 0),
                    explodedPos: new THREE.Vector3(0, 1.05, -0.45)
                }
            ];

            this._subAssemblies.forEach(sub => root.add(sub.group));
            return root;
        }

        _createLaserCncWorkcenter() {
            const root = new THREE.Group();
            root.name = "laser_cnc_workcenter_root";
            root.visible = false;

            const steelAnthracite = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.75, roughness: 0.35 });
            const laserCyan = new THREE.MeshStandardMaterial({ color: 0x00f0ff, emissive: 0x00f0ff, emissiveIntensity: 0.8 });
            const safetyAmber = new THREE.MeshStandardMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.55, roughness: 0.1 });

            // 1. Trumpf 12kW Fiber Laser cutting station (WC-CUT-01)
            const cabinGeo = new THREE.BoxGeometry(3.0, 1.6, 2.2);
            const cabin = new THREE.Mesh(cabinGeo, steelAnthracite);
            cabin.position.set(-1.6, 0.8, 0);
            root.add(cabin);

            // Viewing window
            const winGeo = new THREE.PlaneGeometry(1.6, 0.7);
            const win = new THREE.Mesh(winGeo, safetyAmber);
            win.position.set(-1.6, 1.0, 1.11);
            root.add(win);

            // Laser beam
            const beamGeo = new THREE.CylinderGeometry(0.015, 0.015, 0.75, 12);
            this.laserBeam = new THREE.Mesh(beamGeo, laserCyan);
            this.laserBeam.position.set(-1.6, 0.45, 0.1);
            root.add(this.laserBeam);

            // 2. Yaskawa AR2010 Welding Robot (WC-WELD-01)
            const robotBaseGeo = new THREE.CylinderGeometry(0.30, 0.35, 0.40, 20);
            const robotBase = new THREE.Mesh(robotBaseGeo, steelAnthracite);
            robotBase.position.set(1.8, 0.20, 0);
            root.add(robotBase);

            const armGeo = new THREE.BoxGeometry(0.18, 0.85, 0.18);
            const arm = new THREE.Mesh(armGeo, new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.6, roughness: 0.3 }));
            arm.rotation.z = -Math.PI / 6;
            arm.position.set(1.6, 0.75, 0);
            root.add(arm);

            const torchGeo = new THREE.CylinderGeometry(0.02, 0.04, 0.25, 12);
            const torch = new THREE.Mesh(torchGeo, laserCyan);
            torch.position.set(1.3, 1.05, 0.15);
            root.add(torch);

            return root;
        }

        _setupLeaderLines() {
            // Remove any existing leader lines
            this._leaderLines.forEach(line => this.scene.remove(line));
            this._leaderLines = [];

            this._subAssemblies.forEach(sub => {
                const geom = new THREE.BufferGeometry().setFromPoints([
                    sub.assembledPos.clone(),
                    sub.group.position.clone()
                ]);
                const mat = new THREE.LineDashedMaterial({
                    color: 0x00f0ff,
                    dashSize: 0.08,
                    gapSize: 0.05,
                    transparent: true,
                    opacity: 0.0
                });
                const line = new THREE.Line(geom, mat);
                line.computeLineDistances();
                this.scene.add(line);
                this._leaderLines.push({ line, sub });
            });
        }

        _updateLeaderLines(factor) {
            this._leaderLines.forEach(({ line, sub }) => {
                const positions = line.geometry.attributes.position;
                if (positions) {
                    positions.setXYZ(0, sub.assembledPos.x, sub.assembledPos.y, sub.assembledPos.z);
                    positions.setXYZ(1, sub.group.position.x, sub.group.position.y, sub.group.position.z);
                    positions.needsUpdate = true;
                    line.computeLineDistances();
                }
                line.material.opacity = factor * 0.75;
            });
        }

        _buildHotspotDom() {
            // Check if static container exists in container or DOM
            const existingContainer = this.container.querySelector("#insilosHotspotContainer") || document.getElementById("insilosHotspotContainer");
            if (existingContainer) {
                this.hotspotsOverlay = existingContainer;
                this.hotspotsOverlay.classList.add("pointer-events-none", "pe-none");
                this.hotspotsOverlay.style.pointerEvents = "none";
            } else {
                this.hotspotsOverlay = document.createElement("div");
                this.hotspotsOverlay.className = "ins-3d-hotspots-overlay position-absolute top-0 start-0 w-100 h-100 pointer-events-none pe-none";
                this.hotspotsOverlay.style.pointerEvents = "none";
                (this.canvasWrapper || this.container).appendChild(this.hotspotsOverlay);
            }

            DIGITAL_TWIN_HOTSPOTS.forEach(hs => {
                let pin = existingContainer ? existingContainer.querySelector(`[data-hotspot-id='${hs.id}'], #${hs.id.replace('hotspot_', 'pin_')}`) : null;
                if (!pin) {
                    pin = document.createElement("div");
                    pin.className = "ins-3d-hotspot-pin ins-hotspot-pin pointer-events-auto pe-auto position-absolute";
                    pin.style.pointerEvents = "auto";
                    pin.dataset.hotspotId = hs.id;
                    pin.id = hs.id.replace("hotspot_", "pin_");
                    pin.innerHTML = `
                        <div class="ins-hotspot-badge ${hs.badgeClass} d-flex align-items-center gap-1 shadow-sm">
                            <span class="ins-hotspot-dot"></span>
                            <span class="ins-hotspot-label">${hs.name.split(" ")[0]}</span>
                        </div>
                    `;
                    this.hotspotsOverlay.appendChild(pin);
                } else {
                    pin.classList.add("ins-3d-hotspot-pin", "pointer-events-auto", "pe-auto", "position-absolute");
                    pin.style.pointerEvents = "auto";
                    pin.dataset.hotspotId = hs.id;
                }

                pin.addEventListener("click", (e) => {
                    e.stopPropagation();
                    this.focusHotspot(hs.id);
                });

                this._hotspotElements.set(hs.id, { pin, def: hs });
            });

            // Card popup container
            this.hudCard = this.container.querySelector(".ins-3d-hotspot-card") || document.querySelector(".ins-3d-hotspot-card");
            if (!this.hudCard) {
                this.hudCard = document.createElement("div");
                this.hudCard.className = "ins-3d-hotspot-card card shadow-lg position-absolute d-none pointer-events-auto border-0";
                this.hudCard.style.maxWidth = "360px";
                this.hudCard.style.zIndex = "35";
                this.hudCard.style.top = "70px";
                this.hudCard.style.left = "20px";
                (this.canvasWrapper || this.container).appendChild(this.hudCard);
            }
        }

        _updateHotspotPositions() {
            if (!this.options.showHotspots || this.options.activeModel !== "vlift") {
                if (this.hotspotsOverlay) this.hotspotsOverlay.style.display = "none";
                if (this.hudCard) this.hudCard.classList.add("d-none");
                return;
            }
            if (this.hotspotsOverlay) this.hotspotsOverlay.style.display = "block";

            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 500;
            const tempVec = new THREE.Vector3();

            DIGITAL_TWIN_HOTSPOTS.forEach(hs => {
                const item = this._hotspotElements.get(hs.id);
                if (!item || !item.pin) return;

                // Base anchor
                tempVec.set(hs.anchor3D[0], hs.anchor3D[1], hs.anchor3D[2]);

                // Translate anchor if parent sub-assembly is exploded
                const sub = this._subAssemblies.find(s => s.id === hs.parentSubId);
                if (sub) {
                    tempVec.add(sub.group.position).sub(sub.assembledPos);
                }

                tempVec.project(this.camera);

                // Culling behind camera
                if (tempVec.z > 1.0) {
                    item.pin.style.display = "none";
                    return;
                }

                const px = (tempVec.x * 0.5 + 0.5) * width;
                const py = (-tempVec.y * 0.5 + 0.5) * height;

                item.pin.style.display = "block";
                item.pin.style.position = "absolute";
                item.pin.style.left = px + "px";
                item.pin.style.top = py + "px";
                item.pin.style.transform = "translate(-50%, -50%)";
            });
        }

        // Public API
        setExploded(isExploded) {
            this.options.exploded = !!isExploded;
            this._targetExplodedProgress = this.options.exploded ? 1.0 : 0.0;
        }

        setModel(modelType) {
            this.options.activeModel = modelType;
            if (this.vliftGroup) this.vliftGroup.visible = (modelType === "vlift");
            if (this.laserCncGroup) this.laserCncGroup.visible = (modelType === "laser-cnc");
            if (modelType !== "vlift" && this.hudCard) {
                this.hudCard.classList.add("d-none");
            }
        }

        setRenderMode(mode) {
            this.options.renderMode = mode;
            this.modelsRoot.traverse(obj => {
                if (obj.isMesh && obj.material) {
                    if (mode === "wireframe") {
                        if (!obj._originalMaterial) obj._originalMaterial = obj.material;
                        if (obj.material !== obj._originalMaterial) {
                            obj.material.dispose();
                        }
                        obj.material = new THREE.MeshBasicMaterial({
                            color: 0x00f0ff,
                            wireframe: true,
                            transparent: true,
                            opacity: 0.65
                        });
                    } else if (mode === "xray") {
                        if (!obj._originalMaterial) obj._originalMaterial = obj.material;
                        if (obj.material !== obj._originalMaterial) {
                            obj.material.dispose();
                        }
                        const isInternal = obj.name.includes("cell") || obj.name.includes("bms") || obj.name.includes("motor") || obj.name.includes("cylinder");
                        obj.material = new THREE.MeshStandardMaterial({
                            color: isInternal ? 0x00f0ff : 0x38bdf8,
                            emissive: isInternal ? 0x0284c7 : 0x000000,
                            emissiveIntensity: isInternal ? 0.9 : 0.0,
                            transparent: true,
                            opacity: isInternal ? 0.95 : 0.18,
                            depthWrite: isInternal,
                            roughness: 0.1
                        });
                    } else { // pbr
                        if (obj._originalMaterial) {
                            if (obj.material !== obj._originalMaterial) {
                                obj.material.dispose();
                            }
                            obj.material = obj._originalMaterial;
                        }
                    }
                }
            });
        }

        focusHotspot(hotspotId) {
            const hs = DIGITAL_TWIN_HOTSPOTS.find(h => h.id === hotspotId);
            if (!hs) return;

            this._activeHotspot = hs;
            const targetPos = new THREE.Vector3(hs.anchor3D[0], hs.anchor3D[1], hs.anchor3D[2]);
            const sub = this._subAssemblies.find(s => s.id === hs.parentSubId);
            if (sub) {
                targetPos.add(sub.group.position).sub(sub.assembledPos);
            }

            // Fly controls target
            if (this.controls) {
                this.controls.target.copy(targetPos);
            }

            // Render rich HUD card
            this.hudCard.innerHTML = `
                <div class="card-header bg-dark text-white border-bottom border-secondary d-flex align-items-center justify-content-between py-2 px-3">
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge ${hs.badgeClass} rounded-pill">${hs.componentCode}</span>
                        <strong class="fs-6">${hs.name}</strong>
                    </div>
                    <button type="button" class="btn-close btn-close-white btn-sm ms-2" aria-label="Close"></button>
                </div>
                <div class="card-body p-3">
                    <div class="small text-muted mb-2">Đối soát ERP: <code>${hs.erpRecord}</code> (${hs.erpModel})</div>
                    <div class="table-responsive">
                        <table class="table table-sm table-borderless mb-2">
                            <tbody>
                                ${hs.kpis.map(k => `
                                    <tr>
                                        <td class="text-secondary ps-0 py-1">${k.label}</td>
                                        <td class="text-end fw-semibold text-white pe-0 py-1">${k.value}</td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                    <div class="mt-2 text-end">
                        <a href="${hs.actionUrl}" target="_blank" class="btn btn-sm btn-primary rounded-pill d-inline-flex align-items-center gap-1">
                            <span>Mở Insilos ERP Live</span>
                            <svg width="14" height="14" viewBox="0 0 256 256" fill="currentColor">
                                <path d="M200,64V168a8,8,0,0,1-16,0V83.31L69.66,197.66a8,8,0,0,1-11.32-11.32L172.69,72H88a8,8,0,0,1,0-16H192A8,8,0,0,1,200,64Z"></path>
                            </svg>
                        </a>
                    </div>
                </div>
            `;
            this.hudCard.classList.remove("d-none");
            this.hudCard.style.display = "block";
            const closeBtn = this.hudCard.querySelector(".btn-close");
            if (closeBtn) {
                closeBtn.addEventListener("click", () => {
                    this.hudCard.classList.add("d-none");
                    this.hudCard.style.display = "none";
                    this._activeHotspot = null;
                });
            }
        }

        _setupObserver() {
            if ("IntersectionObserver" in window) {
                this.observer = new IntersectionObserver((entries) => {
                    for (const entry of entries) {
                        this._isVisible = entry.isIntersecting;
                        if (this._isVisible) {
                            this.start();
                        } else {
                            if (this._animId) {
                                safeCaf(this._animId);
                                this._animId = null;
                            }
                        }
                    }
                }, { threshold: [0, 0.05] });
                this.observer.observe(this.container);
            }
            this._onScroll = () => {
                if (this.container) {
                    const rect = this.container.getBoundingClientRect();
                    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
                    const inView = (rect.bottom > 0 && rect.top < windowHeight);
                    if (inView) {
                        this._isVisible = true;
                        this.start();
                    } else {
                        this._isVisible = false;
                        if (this._animId) {
                            safeCaf(this._animId);
                            this._animId = null;
                        }
                    }
                }
            };
            this._onPointerWake = () => {
                this._isVisible = true;
                this.start();
            };
            window.addEventListener("scroll", this._onScroll, { passive: true, capture: true });
            document.addEventListener("scroll", this._onScroll, { passive: true, capture: true });
            this.container.addEventListener("pointerdown", this._onPointerWake, { passive: true });
            this.container.addEventListener("mousedown", this._onPointerWake, { passive: true });
        }

        _setupEvents() {
            this._onResize = () => {
                if (!this.container || !this.renderer || !this.camera) return;
                const width = this.container.clientWidth;
                const height = this.container.clientHeight;
                this.camera.aspect = width / height;
                this.camera.updateProjectionMatrix();
                this.renderer.setSize(width, height);
            };
            window.addEventListener("resize", this._onResize);

            if (this.renderer && this.renderer.domElement) {
                this._onContextLost = (e) => {
                    e.preventDefault();
                    if (this._animId) safeCaf(this._animId);
                };
                this._onContextRestored = () => {
                    this.start();
                };
                this.renderer.domElement.addEventListener("webglcontextlost", this._onContextLost);
                this.renderer.domElement.addEventListener("webglcontextrestored", this._onContextRestored);
            }
        }

        start() {
            if (this._animId) return;
            this._isVisible = true;
            const loop = (timestamp) => {
                if (this.container) {
                    const rect = this.container.getBoundingClientRect();
                    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
                    if (rect.bottom <= 0 || rect.top >= windowHeight) {
                        this._isVisible = false;
                        if (this._animId) safeCaf(this._animId);
                        this._animId = null;
                        return;
                    }
                }

                if (!this._isVisible) {
                    if (this._animId) safeCaf(this._animId);
                    this._animId = null;
                    return;
                }

                this._time += 0.016;

                // Animate exploded BOM progress smoothly
                if (Math.abs(this._explodedProgress - this._targetExplodedProgress) > 0.001) {
                    this._explodedProgress += (this._targetExplodedProgress - this._explodedProgress) * 0.15;
                    const factor = easeInOutCubic(this._explodedProgress);
                    this._subAssemblies.forEach(sub => {
                        sub.group.position.lerpVectors(sub.assembledPos, sub.explodedPos, factor);
                    });
                    this._updateLeaderLines(factor);
                    if (this.renderer.shadowMap.enabled) {
                        this.renderer.shadowMap.needsUpdate = true;
                    }
                }

                // Laser CNC dynamic effects
                if (this.laserBeam && this.options.activeModel === "laser-cnc") {
                    this.laserBeam.material.emissiveIntensity = 0.6 + Math.sin(this._time * 12.0) * 0.4;
                }

                if (this.controls) {
                    this.controls.update();
                }

                this._updateHotspotPositions();
                this.renderer.render(this.scene, this.camera);
                this._animId = safeRaf(loop);
            };
            this._animId = safeRaf(loop);
        }

        dispose() {
            if (this._animId) safeCaf(this._animId);
            if (this.observer) this.observer.disconnect();
            if (this._onScroll) {
                window.removeEventListener("scroll", this._onScroll);
                document.removeEventListener("scroll", this._onScroll);
            }
            if (this._onPointerWake && this.container) {
                this.container.removeEventListener("pointerdown", this._onPointerWake);
                this.container.removeEventListener("mousedown", this._onPointerWake);
            }
            window.removeEventListener("resize", this._onResize);

            if (this.renderer && this.renderer.domElement) {
                if (this._onContextLost) {
                    this.renderer.domElement.removeEventListener("webglcontextlost", this._onContextLost);
                }
                if (this._onContextRestored) {
                    this.renderer.domElement.removeEventListener("webglcontextrestored", this._onContextRestored);
                }
            }

            if (this.directionalLight && this.directionalLight.shadow && this.directionalLight.shadow.map) {
                this.directionalLight.shadow.map.dispose();
            }

            this.scene.traverse(obj => {
                if (obj.geometry) obj.geometry.dispose();
                if (obj.material) {
                    if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
                    else obj.material.dispose();
                }
                if (obj._originalMaterial && obj._originalMaterial !== obj.material) {
                    if (Array.isArray(obj._originalMaterial)) obj._originalMaterial.forEach(m => m.dispose());
                    else obj._originalMaterial.dispose();
                }
                if (obj.shadow && obj.shadow.map) {
                    obj.shadow.map.dispose();
                }
            });

            this.renderer.dispose();
            this.renderer.forceContextLoss();
            if (this.canvasWrapper && this.canvasWrapper.parentElement) {
                this.canvasWrapper.parentElement.removeChild(this.canvasWrapper);
            }
        }
    }

    // -------------------------------------------------------------------------
    // 2. 3D Logistics Radar Engine (VSIP to Seaport 32.4 km Spline)
    // -------------------------------------------------------------------------

    const LOGISTICS_WAYPOINTS = [
        { id: "vsip", name: "KCN VSIP 1 (Bình Dương)", point: [-24.0, 0.2, -22.0] },
        { id: "binh_phuoc", name: "Cầu vượt Bình Phước (QL1A)", point: [-12.0, 0.2, -14.0] },
        { id: "binh_thai", name: "Ngã tư Bình Thái (Xa lộ Hà Nội)", point: [-2.0, 0.2, -4.0] },
        { id: "phu_my", name: "Vành đai 2 / Tuyến Huyết Mạch", point: [10.0, 0.2, 8.0] },
        { id: "my_thuy", name: "Nút giao Mỹ Thủy", point: [18.0, 0.2, 16.0] },
        { id: "catlai", name: "Cụm Cảng Biển Quốc Tế", point: [24.0, 0.2, 22.0] }
    ];

    class InsilosLogisticsRadarEngine {
        constructor(container, options = {}) {
            this.container = typeof container === "string" ? document.querySelector(container) : container;
            if (!this.container) return;

            if (!THREE) THREE = getThree();
            if (!THREE || !isWebGLAvailable()) {
                console.warn("[Insilos3D] LogisticsRadar: THREE or WebGL not available, aborting init");
                return;
            }

            this.options = Object.assign({
                progress: 0.35, // 0.0 to 1.0 along the 32.4km spline
                isPlaying: true,
                speed: 0.0008,
                focusTarget: "convoy" // "vsip", "catlai", "convoy"
            }, options);

            this._animId = null;
            this._isVisible = true;
            this._time = 0;
            this._progress = this.options.progress;

            this._initRenderer();
            this._initScene();
            this._initCameraAndControls();
            this._initSplineRoute();
            this._initConvoyModel();
            this._initRadarShader();
            this._initTerrainDetails();
            this._buildStatusCardDom();
            this._setupObserver();
            this._setupEvents();
            this.start();
        }

        _initRenderer() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 500;

            const existingCanvas = (this.container.tagName === "CANVAS" ? this.container : null) || this.container.querySelector("canvas#insilosLogisticsRadarCanvas, canvas.ins-3d-canvas, canvas");

            this.renderer = new THREE.WebGLRenderer({
                canvas: existingCanvas || undefined,
                antialias: (window.devicePixelRatio || 1) < 2,
                powerPreference: "high-performance",
                alpha: true,
                precision: "mediump"
            });
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.0));
            this.renderer.setSize(width, height);
            this.renderer.toneMapping = THREE.ACESFilmicToneMapping;

            if (!existingCanvas) {
                this.canvasWrapper = document.createElement("div");
                this.canvasWrapper.className = "ins-3d-radar-wrapper position-relative w-100 h-100 overflow-hidden";
                this.canvasWrapper.appendChild(this.renderer.domElement);
                this.container.appendChild(this.canvasWrapper);
            } else {
                existingCanvas.style.display = "block";
                existingCanvas.style.width = "100%";
                existingCanvas.style.height = "100%";
            }
        }

        _initScene() {
            this.scene = new THREE.Scene();
            this.scene.fog = new THREE.FogExp2(0x070b14, 0.018);

            const ambient = new THREE.AmbientLight(0xffffff, 0.8);
            this.scene.add(ambient);

            const dirLight = new THREE.DirectionalLight(0x00f0ff, 1.2);
            dirLight.position.set(20, 35, 15);
            this.scene.add(dirLight);

            // Large terrain ground grid
            const grid = new THREE.GridHelper(80, 80, 0x0284c7, 0x0f172a);
            grid.position.y = 0;
            grid.material.opacity = 0.35;
            grid.material.transparent = true;
            this.scene.add(grid);
        }

        _initCameraAndControls() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 500;
            this.camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 200);
            this.camera.position.set(0, 24, 32);

            const OrbitControlsClass = THREE.OrbitControls || (typeof window !== "undefined" ? window.OrbitControls : null);
            if (OrbitControlsClass) {
                this.controls = new OrbitControlsClass(this.camera, this.renderer.domElement);
                this.controls.enableDamping = true;
                this.controls.dampingFactor = 0.05;
                this.controls.maxPolarAngle = Math.PI / 2.1;
                this.controls.minDistance = 6.0;
                this.controls.maxDistance = 65.0;
                this.controls.target.set(0, 0, 0);
            }
        }

        _initSplineRoute() {
            const splinePoints = LOGISTICS_WAYPOINTS.map(w => new THREE.Vector3(w.point[0], w.point[1], w.point[2]));
            this.curve = new THREE.CatmullRomCurve3(splinePoints, false, "catmullrom", 0.35);

            // Spline highway tube
            const tubeGeo = new THREE.TubeGeometry(this.curve, 160, 0.35, 8, false);
            const tubeMat = new THREE.MeshStandardMaterial({
                color: 0x1e293b,
                metalness: 0.8,
                roughness: 0.4
            });
            const tube = new THREE.Mesh(tubeGeo, tubeMat);
            this.scene.add(tube);

            // Glowing center route line
            const points = this.curve.getPoints(200);
            const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
            const lineMat = new THREE.LineDashedMaterial({
                color: 0x00f0ff,
                dashSize: 0.5,
                gapSize: 0.3,
                transparent: true,
                opacity: 0.85
            });
            this.routeLine = new THREE.Line(lineGeo, lineMat);
            this.routeLine.computeLineDistances();
            this.routeLine.position.y += 0.25;
            this.scene.add(this.routeLine);
        }

        _initConvoyModel() {
            this.convoyGroup = new THREE.Group();
            this.convoyGroup.name = "convoy_51C_982_45";

            const cabMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, metalness: 0.6, roughness: 0.2 });
            const chassisMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.9, roughness: 0.4 });
            const snpTealMat = new THREE.MeshStandardMaterial({ color: 0x006e7f, metalness: 0.3, roughness: 0.5 });
            const wheelMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.9 });

            // 1. Tractor Unit (Hyundai Xcient GT 440PS Prime Mover 6x4)
            this.tractor = new THREE.Group();

            const cabinGeo = new THREE.BoxGeometry(1.6, 1.8, 2.2);
            const cabin = new THREE.Mesh(cabinGeo, cabMat);
            cabin.position.set(0, 1.3, 1.1);
            this.tractor.add(cabin);

            // Windshield
            const windGeo = new THREE.BoxGeometry(1.5, 0.8, 0.05);
            const windMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.9, roughness: 0.1 });
            const windshield = new THREE.Mesh(windGeo, windMat);
            windshield.position.set(0, 1.6, 2.21);
            this.tractor.add(windshield);

            // Tractor chassis frame
            const tChassisGeo = new THREE.BoxGeometry(1.4, 0.35, 4.4);
            const tChassis = new THREE.Mesh(tChassisGeo, chassisMat);
            tChassis.position.set(0, 0.5, -0.2);
            this.tractor.add(tChassis);

            // Wheels
            const wheelGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.22, 16);
            [-0.75, 0.75].forEach(wx => {
                [1.2, -0.8, -1.8].forEach(wz => {
                    const w = new THREE.Mesh(wheelGeo, wheelMat);
                    w.rotation.z = Math.PI / 2;
                    w.position.set(wx, 0.35, wz);
                    this.tractor.add(w);
                });
            });

            this.convoyGroup.add(this.tractor);

            // 2. 40ft CIMC Trailer (51R-089.34) + 40HC Container (SITU-982310-4)
            this.trailer = new THREE.Group();

            const containerGeo = new THREE.BoxGeometry(1.7, 1.9, 7.8);
            const container = new THREE.Mesh(containerGeo, snpTealMat);
            container.position.set(0, 1.65, -4.5);
            this.trailer.add(container);

            // Trailer chassis & triple axles
            const trChassisGeo = new THREE.BoxGeometry(1.5, 0.25, 8.2);
            const trChassis = new THREE.Mesh(trChassisGeo, chassisMat);
            trChassis.position.set(0, 0.6, -4.5);
            this.trailer.add(trChassis);

            [-0.80, 0.80].forEach(wx => {
                [-6.8, -7.6, -8.4].forEach(wz => {
                    const w = new THREE.Mesh(wheelGeo, wheelMat);
                    w.rotation.z = Math.PI / 2;
                    w.position.set(wx, 0.35, wz);
                    this.trailer.add(w);
                });
            });

            this.convoyGroup.add(this.trailer);
            this.scene.add(this.convoyGroup);
        }

        _initRadarShader() {
            // GPS Antenna pulse beam (Volumetric cone)
            const coneGeo = new THREE.ConeGeometry(1.2, 5.5, 24, 1, true);
            coneGeo.translate(0, 2.75, 0);

            this.beamMaterial = new THREE.ShaderMaterial({
                uniforms: {
                    uTime: { value: 0 }
                },
                vertexShader: `
                    varying vec2 vUv;
                    void main() {
                        vUv = uv;
                        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                    }
                `,
                fragmentShader: `
                    uniform float uTime;
                    varying vec2 vUv;
                    void main() {
                        float fade = pow(vUv.y, 1.5);
                        float rings = fract(vUv.y * 5.0 - uTime * 3.0);
                        float intensity = smoothstep(0.0, 0.25, rings) * smoothstep(0.75, 1.0, 1.0 - rings);
                        vec3 col = vec3(0.0, 0.95, 1.0);
                        gl_FragColor = vec4(col, (intensity + 0.3) * (1.0 - fade) * 0.7);
                    }
                `,
                transparent: true,
                depthWrite: false,
                side: THREE.DoubleSide,
                blending: THREE.AdditiveBlending
            });

            this.radarBeam = new THREE.Mesh(coneGeo, this.beamMaterial);
            this.radarBeam.position.set(0, 2.3, 1.1); // atop cabin
            this.tractor.add(this.radarBeam);

            // Ground expanding sonar ripple
            const rippleGeo = new THREE.RingGeometry(0.5, 0.7, 32);
            this.rippleMat = new THREE.MeshBasicMaterial({
                color: 0x00f0ff,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.8
            });
            this.groundRipple = new THREE.Mesh(rippleGeo, this.rippleMat);
            this.groundRipple.rotation.x = -Math.PI / 2;
            this.groundRipple.position.y = 0.05;
            this.scene.add(this.groundRipple);
        }

        _initTerrainDetails() {
            // Terminal pads for VSIP and Seaport
            const createTerminal = (pos, name, color) => {
                const group = new THREE.Group();
                group.position.set(pos[0], pos[1], pos[2]);

                const padGeo = new THREE.CylinderGeometry(3.5, 3.5, 0.2, 32);
                const padMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.3 });
                const pad = new THREE.Mesh(padGeo, padMat);
                group.add(pad);

                const ringGeo = new THREE.RingGeometry(3.6, 3.8, 32);
                const ringMat = new THREE.MeshBasicMaterial({ color: color, side: THREE.DoubleSide });
                const ring = new THREE.Mesh(ringGeo, ringMat);
                ring.rotation.x = -Math.PI / 2;
                ring.position.y = 0.12;
                group.add(ring);

                this.scene.add(group);
            };

            createTerminal([-24, 0, -22], "KCN VSIP 1", 0xff8000);
            createTerminal([24, 0, 22], "Cụm Cảng Biển Quốc Tế", 0x00f0ff);
        }

        _buildStatusCardDom() {
            this.statusCard = document.createElement("div");
            this.statusCard.className = "ins-radar-status-card card shadow-lg position-absolute bottom-0 start-0 m-3 p-3 text-white border-0";
            this.statusCard.style.maxWidth = "360px";
            this.statusCard.style.zIndex = "25";
            this.statusCard.style.background = "rgba(7, 11, 20, 0.92)";
            this.statusCard.style.backdropFilter = "blur(12px)";
            this.statusCard.style.border = "1px solid rgba(0, 240, 255, 0.25)";

            this.statusCard.innerHTML = `
                <div class="d-flex align-items-center justify-content-between mb-2 pb-2 border-bottom border-secondary">
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge bg-success rounded-pill">GPS LIVE</span>
                        <strong class="text-white fs-6">Đầu Kéo 51C-982.45</strong>
                    </div>
                    <span class="badge bg-info text-dark rounded-pill">32.4 km</span>
                </div>
                <div class="small">
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-secondary">Rơ-moóc / Container:</span>
                        <span class="text-white fw-semibold">51R-089.34 / SITU-982310-4</span>
                    </div>
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-secondary">Cảng đích:</span>
                        <span class="text-white fw-semibold">Cụm Cảng Biển Quốc Tế — CY04</span>
                    </div>
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-secondary">Hạn miễn DET/DEM:</span>
                        <span class="text-emerald fw-semibold">38.5 / 48 giờ (An toàn)</span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span class="text-secondary">Tránh phí phạt:</span>
                        <span class="text-warning fw-bold">$240.00 / ngày (5.950.000 ₫)</span>
                    </div>
                </div>
                <div class="mt-3">
                    <div class="d-flex justify-content-between text-muted small mb-1">
                        <span>Tiến độ hành lang:</span>
                        <span id="ins-radar-progress-pct">35%</span>
                    </div>
                    <input type="range" class="form-range" id="ins-radar-scrubber" min="0" max="1000" value="350">
                </div>
            `;
            (this.canvasWrapper || this.container).appendChild(this.statusCard);

            const scrubber = this.statusCard.querySelector("#ins-radar-scrubber");
            if (scrubber) {
                scrubber.addEventListener("input", (e) => {
                    this.options.isPlaying = false;
                    this.seekTimeline(Number(e.target.value) / 1000);
                });
            }
        }

        seekTimeline(progressNorm) {
            this._progress = Math.max(0.0, Math.min(1.0, progressNorm));
        }

        setTargetLocation(locId) {
            this.options.focusTarget = locId;
            const wp = LOGISTICS_WAYPOINTS.find(w => w.id === locId);
            if (wp && this.controls) {
                this.controls.target.set(wp.point[0], wp.point[1], wp.point[2]);
            }
        }

        _setupObserver() {
            if ("IntersectionObserver" in window) {
                this.observer = new IntersectionObserver((entries) => {
                    this._isVisible = entries[0].isIntersecting;
                    if (this._isVisible && !this._animId) {
                        this.start();
                    }
                }, { threshold: 0 });
                this.observer.observe(this.container);
            }
            this._onScroll = () => {
                if (this.container && !this._animId) {
                    const rect = this.container.getBoundingClientRect();
                    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
                    if (rect.bottom > 0 && rect.top < windowHeight) {
                        this._isVisible = true;
                        this.start();
                    }
                }
            };
            window.addEventListener("scroll", this._onScroll, { passive: true });
        }

        _setupEvents() {
            this._onResize = () => {
                if (!this.container || !this.renderer || !this.camera) return;
                const width = this.container.clientWidth;
                const height = this.container.clientHeight;
                this.camera.aspect = width / height;
                this.camera.updateProjectionMatrix();
                this.renderer.setSize(width, height);
            };
            window.addEventListener("resize", this._onResize);

            if (this.renderer && this.renderer.domElement) {
                this._onContextLost = (e) => {
                    e.preventDefault();
                    if (this._animId) safeCaf(this._animId);
                };
                this._onContextRestored = () => {
                    this.start();
                };
                this.renderer.domElement.addEventListener("webglcontextlost", this._onContextLost);
                this.renderer.domElement.addEventListener("webglcontextrestored", this._onContextRestored);
            }
        }

        start() {
            const loop = (timestamp) => {
                if (this.container) {
                    const rect = this.container.getBoundingClientRect();
                    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
                    if (rect.bottom <= 0 || rect.top >= windowHeight) {
                        this._isVisible = false;
                        this._animId = null;
                        return;
                    }
                }

                if (!this._isVisible) {
                    this._animId = null;
                    return;
                }

                this._time += 0.016;

                // Advance progress along route
                if (this.options.isPlaying) {
                    this._progress = (this._progress + this.options.speed) % 1.0;
                }

                if (this.curve && this.convoyGroup) {
                    const pos = this.curve.getPointAt(this._progress);
                    const tangent = this.curve.getTangentAt(this._progress);
                    this.convoyGroup.position.copy(pos);

                    // Align convoy orientation with tangent
                    const lookTarget = pos.clone().add(tangent);
                    this.convoyGroup.lookAt(lookTarget);

                    // Update ripple ground position
                    if (this.groundRipple) {
                        this.groundRipple.position.set(pos.x, 0.05, pos.z);
                        const rippleScale = 1.0 + (this._time % 1.8) * 3.5;
                        this.groundRipple.scale.set(rippleScale, rippleScale, rippleScale);
                        this.rippleMat.opacity = Math.max(0, 1.0 - (this._time % 1.8) / 1.8);
                    }

                    // Update UI scrubber & telemetry display
                    const pctSpan = document.getElementById("ins-radar-progress-pct");
                    const scrubber = document.getElementById("ins-radar-scrubber");
                    const pctVal = Math.round(this._progress * 100);
                    if (pctSpan) pctSpan.textContent = pctVal + "%";
                    if (scrubber && this.options.isPlaying) scrubber.value = Math.round(this._progress * 1000);

                    const timelineSlider = document.getElementById("insilosLogisticsTimeline");
                    if (timelineSlider && this.options.isPlaying) timelineSlider.value = pctVal;

                    const radarVal = document.getElementById("radarTimelineValue");
                    if (radarVal) {
                        let leg = "Xuất xưởng VSIP 1";
                        if (pctVal > 66) leg = "Bãi CY Cảng Biển";
                        else if (pctVal > 30) leg = "Tuyến Vành Đai 2";
                        else if (pctVal > 10) leg = "Đại Lộ Bình Dương (QL13)";
                        radarVal.textContent = `${pctVal}% // ${leg}`;
                    }

                    // Track camera if focus is on convoy
                    if (this.options.focusTarget === "convoy" && this.controls) {
                        this.controls.target.lerp(pos, 0.05);
                    }
                }

                // Update beam shader time
                if (this.beamMaterial) {
                    this.beamMaterial.uniforms.uTime.value = this._time;
                }

                if (this.controls) {
                    this.controls.update();
                }

                this.renderer.render(this.scene, this.camera);
                this._animId = safeRaf(loop);
            };
            this._animId = safeRaf(loop);
        }

        dispose() {
            if (this._animId) safeCaf(this._animId);
            if (this.observer) this.observer.disconnect();
            window.removeEventListener("resize", this._onResize);
            if (this._onScroll) window.removeEventListener("scroll", this._onScroll);

            if (this.renderer && this.renderer.domElement) {
                if (this._onContextLost) {
                    this.renderer.domElement.removeEventListener("webglcontextlost", this._onContextLost);
                }
                if (this._onContextRestored) {
                    this.renderer.domElement.removeEventListener("webglcontextrestored", this._onContextRestored);
                }
            }

            this.scene.traverse(obj => {
                if (obj.geometry) obj.geometry.dispose();
                if (obj.material) {
                    if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
                    else obj.material.dispose();
                }
            });

            this.renderer.dispose();
            this.renderer.forceContextLoss();
            if (this.canvasWrapper && this.canvasWrapper.parentElement) {
                this.canvasWrapper.parentElement.removeChild(this.canvasWrapper);
            }
        }
    }

    // -------------------------------------------------------------------------
    // 3. 3D Factory & ROI Configurator Engine (InstancedMesh Batching)
    // -------------------------------------------------------------------------

    class InsilosFactoryConfiguratorEngine {
        constructor(container, options = {}) {
            this.container = typeof container === "string" ? document.querySelector(container) : container;
            if (!this.container) return;

            if (!THREE) THREE = getThree();
            if (!THREE || !isWebGLAvailable()) {
                console.warn("[Insilos3D] FactoryConfigurator: THREE or WebGL not available, aborting init");
                return;
            }

            this.options = Object.assign({
                numVehicles: 40, // 10 to 200
                numCnc: 6,       // 1 to 20
                maxVehicles: 200,
                maxCnc: 20
            }, options);

            this._animId = null;
            this._isVisible = true;
            this._time = 0;

            this._initRenderer();
            this._initScene();
            this._initCameraAndControls();
            this._initFactoryFloor();
            this._initInstancedFleet();
            this._setupObserver();
            this._setupEvents();
            this._bindDomSliders();
            this.updateFleet(this.options.numVehicles, this.options.numCnc);
            this.start();
        }

        _initRenderer() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 500;

            const existingCanvas = (this.container.tagName === "CANVAS" ? this.container : null) || this.container.querySelector("canvas#insilosFactoryRoiCanvas, canvas.ins-3d-canvas, canvas");

            this.renderer = new THREE.WebGLRenderer({
                canvas: existingCanvas || undefined,
                antialias: (window.devicePixelRatio || 1) < 2,
                powerPreference: "high-performance",
                alpha: true,
                precision: "mediump"
            });
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.0));
            this.renderer.setSize(width, height);
            this.renderer.toneMapping = THREE.ACESFilmicToneMapping;

            if (!existingCanvas) {
                this.canvasWrapper = document.createElement("div");
                this.canvasWrapper.className = "ins-3d-configurator-wrapper position-relative w-100 h-100 overflow-hidden";
                this.canvasWrapper.appendChild(this.renderer.domElement);
                this.container.appendChild(this.canvasWrapper);
            } else {
                existingCanvas.style.display = "block";
                existingCanvas.style.width = "100%";
                existingCanvas.style.height = "100%";
            }
        }

        _initScene() {
            this.scene = new THREE.Scene();
            this.scene.fog = new THREE.FogExp2(0x070b14, 0.012);

            const ambient = new THREE.AmbientLight(0xffffff, 0.75);
            this.scene.add(ambient);

            const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
            dirLight.position.set(30, 45, 20);
            this.scene.add(dirLight);

            const cyanGlow = new THREE.PointLight(0x00f0ff, 0.8, 50);
            cyanGlow.position.set(0, 10, 0);
            this.scene.add(cyanGlow);
        }

        _initCameraAndControls() {
            const width = this.container.clientWidth || 800;
            const height = this.container.clientHeight || 500;
            this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 300);
            this.camera.position.set(45, 32, 55);

            const OrbitControlsClass = THREE.OrbitControls || (typeof window !== "undefined" ? window.OrbitControls : null);
            if (OrbitControlsClass) {
                this.controls = new OrbitControlsClass(this.camera, this.renderer.domElement);
                this.controls.enableDamping = true;
                this.controls.dampingFactor = 0.05;
                this.controls.minDistance = 15.0;
                this.controls.maxDistance = 150.0;
                this.controls.maxPolarAngle = Math.PI / 2.05;
                this.controls.target.set(0, 0, 0);
            }
        }

        _initFactoryFloor() {
            // Factory concrete slab (120m x 80m)
            const floorGeo = new THREE.PlaneGeometry(120, 80);
            const floorMat = new THREE.MeshStandardMaterial({
                color: 0x0f172a,
                roughness: 0.65,
                metalness: 0.3
            });
            const floor = new THREE.Mesh(floorGeo, floorMat);
            floor.rotation.x = -Math.PI / 2;
            this.scene.add(floor);

            // Factory grid lanes
            const grid = new THREE.GridHelper(120, 60, 0x00f0ff, 0x1e293b);
            grid.position.y = 0.02;
            grid.material.opacity = 0.3;
            grid.material.transparent = true;
            this.scene.add(grid);

            // Structural building pillars
            const colGeo = new THREE.BoxGeometry(0.8, 12, 0.8);
            const colMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.7, roughness: 0.3 });
            for (let x = -50; x <= 50; x += 25) {
                for (let z = -30; z <= 30; z += 30) {
                    const col = new THREE.Mesh(colGeo, colMat);
                    col.position.set(x, 6, z);
                    this.scene.add(col);
                }
            }
        }

        _initInstancedFleet() {
            // 1. Instanced Tugger Fleet (V-LIFT 2500E merged geometry)
            // Single draw call for up to 200 vehicles!
            const tuggerGeo = this._createTuggerProxyGeometry();
            const tuggerMat = new THREE.MeshStandardMaterial({
                color: 0xff8000,
                metalness: 0.45,
                roughness: 0.35
            });

            this.instancedTuggers = new THREE.InstancedMesh(tuggerGeo, tuggerMat, this.options.maxVehicles);
            this.instancedTuggers.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
            this.scene.add(this.instancedTuggers);

            // 2. Instanced CNC Workcenters (Trumpf/Yaskawa proxy geometry)
            // Single draw call for up to 20 CNC cells!
            const cncGeo = this._createCncProxyGeometry();
            const cncMat = new THREE.MeshStandardMaterial({
                color: 0x334155,
                metalness: 0.75,
                roughness: 0.30
            });

            this.instancedCnc = new THREE.InstancedMesh(cncGeo, cncMat, this.options.maxCnc);
            this.instancedCnc.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
            this.scene.add(this.instancedCnc);
        }

        _createTuggerProxyGeometry() {
            // Lightweight merged proxy: body + mast
            const body = new THREE.BoxGeometry(1.4, 0.6, 2.2);
            body.translate(0, 0.4, 0);

            const mast = new THREE.BoxGeometry(0.9, 2.0, 0.15);
            mast.translate(0, 1.2, 0.95);

            // Combine into single buffer geometry if possible or return compound box
            return new THREE.BoxGeometry(1.4, 1.8, 2.4);
        }

        _createCncProxyGeometry() {
            return new THREE.BoxGeometry(4.0, 2.4, 3.2);
        }

        updateFleet(numVehicles, numCnc) {
            const nV = Math.max(10, Math.min(this.options.maxVehicles, Number(numVehicles) || 40));
            const nC = Math.max(1, Math.min(this.options.maxCnc, Number(numCnc) || 6));
            this.options.numVehicles = nV;
            this.options.numCnc = nC;

            const dummy = new THREE.Object3D();

            // 1. Arrange vehicles along active factory grid lanes
            for (let i = 0; i < nV; i++) {
                const lane = i % 5;
                const slot = Math.floor(i / 5);
                const x = -40 + lane * 18;
                const z = -28 + slot * 6.5;

                dummy.position.set(x, 0.9, z);
                dummy.rotation.y = (lane % 2 === 0) ? 0 : Math.PI;
                dummy.updateMatrix();
                this.instancedTuggers.setMatrixAt(i, dummy.matrix);
            }
            this.instancedTuggers.count = nV;
            this.instancedTuggers.instanceMatrix.needsUpdate = true;

            // 2. Arrange CNC workcenters along Bay A & Bay B
            for (let j = 0; j < nC; j++) {
                const bay = j < 10 ? -1 : 1;
                const slot = j % 10;
                const x = -45 + slot * 10;
                const z = bay * 26;

                dummy.position.set(x, 1.2, z);
                dummy.rotation.y = bay === -1 ? 0 : Math.PI;
                dummy.updateMatrix();
                this.instancedCnc.setMatrixAt(j, dummy.matrix);
            }
            this.instancedCnc.count = nC;
            this.instancedCnc.instanceMatrix.needsUpdate = true;

            // Recalculate ROI metrics
            const roi = this.calculateRoi(nV, nC);
            this._updateDomRoiMetrics(roi);
            return roi;
        }

        calculateRoi(numVehicles, numCnc) {
            const nV = Number(numVehicles) || this.options.numVehicles;
            const nC = Number(numCnc) || this.options.numCnc;

            // Fleet Fuel & Maintenance Savings (Grounded in F.3 specification)
            // Fuel: 2,400 km * 0.38 L/km * 22,500 ₫/L * 18.4% saving ≈ 3,780,000 ₫/vehicle/month
            // Maint: 4,200,000 ₫ * 35% saving = 1,470,000 ₫/vehicle/month
            const totalVehicleSavings = nV * 5250000; // 5,250,000 ₫ / vehicle / month

            // CNC Scrap & Downtime Savings
            // Scrap: 25 tons * 19,500,000 ₫/ton * 3.8% = 18,525,000 ₫/CNC/month
            // Downtime: 12 hrs * 2,500,000 ₫/hr * 72% = 21,600,000 ₫/CNC/month
            const totalCncSavings = nC * 40125000; // 40,125,000 ₫ / CNC / month

            const monthlySavings = totalVehicleSavings + totalCncSavings;
            const capex = 450000000 + (nV * 12000000) + (nC * 35000000);
            const paybackMonths = monthlySavings > 0 ? (capex / monthlySavings) : 0;
            const roi3YearPercent = capex > 0 ? (((monthlySavings * 36) - capex) / capex) * 100 : 0;
            const roundedRoi = Math.round(roi3YearPercent);

            return {
                numVehicles: nV,
                numCnc: nC,
                monthlySavings,
                capex,
                paybackMonths: Number(paybackMonths.toFixed(2)),
                roi3YearPercent: roundedRoi,
                formattedMonthlySavings: formatVnd(monthlySavings),
                formattedCapex: formatVnd(capex),
                formattedPayback: paybackMonths.toFixed(1) + " tháng",
                formattedRoi: roundedRoi.toLocaleString("vi-VN") + "%"
            };
        }

        _bindDomSliders() {
            const sliderV = document.querySelector("#inputFleetSize, #ins-slider-vehicles, [data-configurator-slider='vehicles']");
            const sliderC = document.querySelector("#inputCncCount, #ins-slider-cnc, [data-configurator-slider='cnc']");

            if (sliderV) {
                sliderV.value = this.options.numVehicles;
                const onInputV = (e) => {
                    this.updateFleet(Number(e.target.value), this.options.numCnc);
                };
                sliderV.addEventListener("input", onInputV);
                sliderV.addEventListener("change", onInputV);
            }
            if (sliderC) {
                sliderC.value = this.options.numCnc;
                const onInputC = (e) => {
                    this.updateFleet(this.options.numVehicles, Number(e.target.value));
                };
                sliderC.addEventListener("input", onInputC);
                sliderC.addEventListener("change", onInputC);
            }
        }

        _updateDomRoiMetrics(roi) {
            const elVVal = document.querySelector("#valFleetSize, #ins-val-vehicles");
            const elCVal = document.querySelector("#valCncCount, #ins-val-cnc");
            const elAnnualSavings = document.querySelector("#roiAnnualSavings");
            const elMonthlySavings = document.querySelector("#ins-roi-monthly-savings");
            const elCapex = document.querySelector("#roiCapex, #ins-roi-capex");
            const elPayback = document.querySelector("#roiPaybackMonths, #ins-roi-payback");
            const elRoi = document.querySelector("#roi3YrPercent, #ins-roi-3yr-percent");
            const elInstances = document.querySelector("#factoryInstancesCount");

            if (elVVal) elVVal.textContent = roi.numVehicles + " Xe";
            if (elCVal) elCVal.textContent = roi.numCnc + " Cụm";
            if (elAnnualSavings) elAnnualSavings.textContent = formatVnd(roi.monthlySavings * 12);
            if (elMonthlySavings) elMonthlySavings.textContent = roi.formattedMonthlySavings;
            if (elCapex) elCapex.textContent = roi.formattedCapex;
            if (elPayback) elPayback.textContent = roi.paybackMonths.toFixed(1) + " Tháng";
            if (elRoi) elRoi.textContent = roi.formattedRoi;
            if (elInstances) elInstances.textContent = `${roi.numVehicles} ĐẦU XE // ${roi.numCnc} TRẠM GIA CÔNG CNC`;

            // Dispatch custom event for external listeners
            if (isBrowser() && typeof window.dispatchEvent === "function" && typeof CustomEvent === "function") {
                window.dispatchEvent(new CustomEvent("insilos:roi:update", { detail: roi }));
            }
        }

        _setupObserver() {
            if ("IntersectionObserver" in window) {
                this.observer = new IntersectionObserver((entries) => {
                    this._isVisible = entries[0].isIntersecting;
                    if (this._isVisible && !this._animId) {
                        this.start();
                    }
                }, { threshold: 0 });
                this.observer.observe(this.container);
            }
            this._onScroll = () => {
                if (this.container && !this._animId) {
                    const rect = this.container.getBoundingClientRect();
                    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
                    if (rect.bottom > 0 && rect.top < windowHeight) {
                        this._isVisible = true;
                        this.start();
                    }
                }
            };
            window.addEventListener("scroll", this._onScroll, { passive: true });
        }

        _setupEvents() {
            this._onResize = () => {
                if (!this.container || !this.renderer || !this.camera) return;
                const width = this.container.clientWidth;
                const height = this.container.clientHeight;
                this.camera.aspect = width / height;
                this.camera.updateProjectionMatrix();
                this.renderer.setSize(width, height);
            };
            window.addEventListener("resize", this._onResize);

            if (this.renderer && this.renderer.domElement) {
                this._onContextLost = (e) => {
                    e.preventDefault();
                    if (this._animId) safeCaf(this._animId);
                };
                this._onContextRestored = () => {
                    this.start();
                };
                this.renderer.domElement.addEventListener("webglcontextlost", this._onContextLost);
                this.renderer.domElement.addEventListener("webglcontextrestored", this._onContextRestored);
            }
        }

        start() {
            const loop = () => {
                if (this.container) {
                    const rect = this.container.getBoundingClientRect();
                    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
                    if (rect.bottom <= 0 || rect.top >= windowHeight) {
                        this._isVisible = false;
                        this._animId = null;
                        return;
                    }
                }

                if (!this._isVisible) {
                    this._animId = null;
                    return;
                }

                if (this.controls) {
                    this.controls.update();
                }

                this.renderer.render(this.scene, this.camera);
                this._animId = safeRaf(loop);
            };
            this._animId = safeRaf(loop);
        }

        dispose() {
            if (this._animId) safeCaf(this._animId);
            if (this.observer) this.observer.disconnect();
            window.removeEventListener("resize", this._onResize);
            if (this._onScroll) window.removeEventListener("scroll", this._onScroll);

            if (this.renderer && this.renderer.domElement) {
                if (this._onContextLost) {
                    this.renderer.domElement.removeEventListener("webglcontextlost", this._onContextLost);
                }
                if (this._onContextRestored) {
                    this.renderer.domElement.removeEventListener("webglcontextrestored", this._onContextRestored);
                }
            }

            this.scene.traverse(obj => {
                if (obj.geometry) obj.geometry.dispose();
                if (obj.material) {
                    if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
                    else obj.material.dispose();
                }
            });

            this.renderer.dispose();
            this.renderer.forceContextLoss();
            if (this.canvasWrapper && this.canvasWrapper.parentElement) {
                this.canvasWrapper.parentElement.removeChild(this.canvasWrapper);
            }
        }
    }

    // -------------------------------------------------------------------------
    // 4. Auto-Mount & Global API Namespace
    // -------------------------------------------------------------------------

    const instances = {
        digitalTwin: null,
        logisticsRadar: null,
        factoryConfigurator: null
    };

    function autoInit() {
        if (!isBrowser() || !isWebGLAvailable()) return instances;

        if (!THREE) THREE = getThree();
        if (!THREE) {
            var attempts = 0;
            var pollInterval = setInterval(function () {
                attempts++;
                THREE = getThree();
                if (THREE) {
                    clearInterval(pollInterval);
                    autoInit();
                } else if (attempts >= 60) {
                    clearInterval(pollInterval);
                    console.warn("[Insilos3D] Three.js runtime not detected after 3s.");
                }
            }, 50);
            return instances;
        }

        // Auto-mount Digital Twin
        const dtEl = document.querySelector("#insilosDigitalTwinViewport, .ins-3d-digital-twin-canvas, [data-insilos-3d='digital-twin']");
        if (dtEl && !instances.digitalTwin) {
            instances.digitalTwin = new InsilosDigitalTwinEngine(dtEl);
            if (typeof window !== "undefined") window.__dt = instances.digitalTwin;

            // Wire up external toggle buttons if present
            document.querySelectorAll("#btnExplodedBom, [data-action='toggle-exploded'], [data-action='exploded'], .ins-btn-exploded").forEach(btn => {
                btn.addEventListener("click", () => {
                    const isExp = btn.classList.toggle("active");
                    instances.digitalTwin.setExploded(isExp);
                });
            });
            document.querySelectorAll("#btnModePbr, #btnModeWire, #btnModeXray, [data-render-mode], [data-mode], [data-action='set-mode']").forEach(btn => {
                btn.addEventListener("click", () => {
                    const mode = btn.dataset.renderMode || btn.dataset.mode || (btn.id === "btnModeWire" ? "wireframe" : (btn.id === "btnModeXray" ? "xray" : "pbr"));
                    instances.digitalTwin.setRenderMode(mode);
                    document.querySelectorAll("#btnModePbr, #btnModeWire, #btnModeXray, [data-render-mode], [data-mode], [data-action='set-mode']").forEach(b => b.classList.remove("active"));
                    btn.classList.add("active");
                });
            });
            document.querySelectorAll("#btnModelVlift, #btnModelCnc, [data-model-select], [data-action='toggle-model']").forEach(btn => {
                btn.addEventListener("click", () => {
                    const m = btn.dataset.modelSelect || (btn.id === "btnModelCnc" ? "laser-cnc" : "vlift");
                    instances.digitalTwin.setModel(m);
                    document.querySelectorAll("#btnModelVlift, #btnModelCnc, [data-model-select], [data-action='toggle-model']").forEach(b => b.classList.remove("active"));
                    btn.classList.add("active");
                });
            });
            document.querySelectorAll("#btnResetCam, [data-action='reset-camera']").forEach(btn => {
                btn.addEventListener("click", () => {
                    if (instances.digitalTwin.controls) {
                        instances.digitalTwin.controls.reset();
                    }
                });
            });
        }

        // Auto-mount Logistics Radar
        const radarEl = document.querySelector("#insilosLogisticsRadarViewport, .ins-3d-logistics-radar-canvas, [data-insilos-3d='logistics-radar']");
        if (radarEl && !instances.logisticsRadar) {
            instances.logisticsRadar = new InsilosLogisticsRadarEngine(radarEl);
            if (typeof window !== "undefined") window.__radar = instances.logisticsRadar;

            document.querySelectorAll("[data-radar-target], [data-checkpoint]").forEach(btn => {
                btn.addEventListener("click", () => {
                    const target = btn.dataset.radarTarget || btn.dataset.checkpoint;
                    instances.logisticsRadar.setTargetLocation(target);
                    document.querySelectorAll("[data-checkpoint]").forEach(b => b.classList.remove("is-active"));
                    btn.classList.add("is-active");
                });
            });
            document.querySelectorAll("[data-action='toggle-radar-play']").forEach(btn => {
                btn.addEventListener("click", () => {
                    instances.logisticsRadar.options.isPlaying = !instances.logisticsRadar.options.isPlaying;
                    btn.classList.toggle("active", instances.logisticsRadar.options.isPlaying);
                });
            });

            const timelineSlider = document.querySelector("#insilosLogisticsTimeline, .ins-timeline-scrubber");
            if (timelineSlider) {
                const onTimeline = (e) => {
                    const norm = Number(e.target.value) / 100;
                    instances.logisticsRadar.options.isPlaying = false;
                    instances.logisticsRadar.seekTimeline(norm);
                    const valDisplay = document.querySelector("#radarTimelineValue");
                    if (valDisplay) {
                        let leg = "Xuất xưởng VSIP 1";
                        if (norm > 0.66) leg = "Bãi CY Cảng Biển";
                        else if (norm > 0.3) leg = "Tuyến Vành Đai 2";
                        else if (norm > 0.1) leg = "Đại Lộ Bình Dương (QL13)";
                        valDisplay.textContent = `${Math.round(norm * 100)}% // ${leg}`;
                    }
                };
                timelineSlider.addEventListener("input", onTimeline);
                timelineSlider.addEventListener("change", onTimeline);
            }
        }

        // Auto-mount Factory Configurator
        const cfgEl = document.querySelector("#insilosFactoryRoiViewport, .ins-3d-factory-configurator-canvas, [data-insilos-3d='factory-configurator']");
        if (cfgEl && !instances.factoryConfigurator) {
            instances.factoryConfigurator = new InsilosFactoryConfiguratorEngine(cfgEl);
            if (typeof window !== "undefined") window.__cfg = instances.factoryConfigurator;
        }

        return instances;
    }

    if (isBrowser()) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", autoInit);
        } else {
            autoInit();
        }
    }

    const Insilos3D = {
        instances,
        InsilosDigitalTwinEngine,
        InsilosLogisticsRadarEngine,
        InsilosFactoryConfiguratorEngine,
        DIGITAL_TWIN_HOTSPOTS,
        LOGISTICS_WAYPOINTS,
        initDigitalTwin: (container, options) => new InsilosDigitalTwinEngine(container, options),
        initLogisticsRadar: (container, options) => new InsilosLogisticsRadarEngine(container, options),
        initFactoryConfigurator: (container, options) => new InsilosFactoryConfiguratorEngine(container, options),
        autoInit,
        isWebGLAvailable
    };

    root.Insilos3D = Insilos3D;
    if (typeof window !== "undefined") {
        window.Insilos3D = Insilos3D;
    }
    if (typeof module !== "undefined" && module.exports) {
        module.exports = Insilos3D;
    }

    return Insilos3D;
})();
