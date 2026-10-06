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
    // =========================================================================
    function SovereignCoreController(manager) {
        BaseHeroSceneController.call(this, manager, 'sovereign_core', 'The Sovereign Core');
        this.satellites = [];
        this.laserLines = null;
        this.coreMesh = null;
        this.pulseShell = null;
        this.photonCloud = null;
    }
    SovereignCoreController.prototype = Object.create(BaseHeroSceneController.prototype);
    SovereignCoreController.prototype.constructor = SovereignCoreController;

    SovereignCoreController.prototype.buildScene = function () {
        // Lights
        var ambLight = new THREE.AmbientLight(0xF0F9FF, 1.3);
        var keyLight = new THREE.DirectionalLight(PALETTE.bluePrimary, 2.2);
        keyLight.position.set(5, 8, 7);
        var rimLight = new THREE.DirectionalLight(PALETTE.cyan, 1.8);
        rimLight.position.set(-6, -3, -5);
        this.scene.add(ambLight, keyLight, rimLight);

        // Core Nucleus (Inner Icosahedron + Outer Quantum Shell)
        var coreGeo = this.trackDisposable(new THREE.IcosahedronGeometry(1.4, 3));
        var coreMat = this.trackDisposable(new THREE.MeshStandardMaterial({
            color: PALETTE.bluePrimary,
            emissive: PALETTE.cyan,
            emissiveIntensity: 0.55,
            roughness: 0.25,
            metalness: 0.8
        }));
        this.coreMesh = new THREE.Mesh(coreGeo, coreMat);
        this.rootGroup.add(this.coreMesh);

        var shellGeo = this.trackDisposable(new THREE.IcosahedronGeometry(1.7, 2));
        var shellMat = this.trackDisposable(new THREE.MeshBasicMaterial({
            color: PALETTE.cyan,
            wireframe: true,
            transparent: true,
            opacity: 0.35
        }));
        this.pulseShell = new THREE.Mesh(shellGeo, shellMat);
        this.rootGroup.add(this.pulseShell);

        // 4 Satellites Data
        var satData = [
            { id: 'sat_erp', name: 'AI-Enhanced ERP', radius: 4.4, speed: 0.22, color: PALETTE.bluePrimary, size: 0.42, desc: 'Hệ thống ERP lõi chuẩn VAS 200/133 kết nối chuỗi cung ứng.' },
            { id: 'sat_mojo', name: 'MOJO AI Swarm', radius: 5.6, speed: 0.16, color: PALETTE.cyan, size: 0.50, desc: 'Mạng lưới đa tác tử tự trị suy luận đa tầng < 280ms.' },
            { id: 'sat_digiforce', name: 'DIGIFORCE No-Code', radius: 6.8, speed: 0.12, color: PALETTE.orange, size: 0.44, desc: 'Nền tảng đóng gói ứng dụng siêu tốc 3h -> 3d -> 3w -> 3m.' },
            { id: 'sat_mojoverse', name: 'MOJOVERSE Blockchain', radius: 8.0, speed: 0.09, color: PALETTE.purple, size: 0.38, desc: 'Sổ cái bất biến xác thực e-CO và chống giả mạo chuỗi cung ứng.' }
        ];

        var self = this;
        satData.forEach(function (data, idx) {
            // Orbit Ring (Thin circular trail)
            var ringGeo = self.trackDisposable(new THREE.BufferGeometry());
            var points = [];
            var segments = 64;
            for (var i = 0; i <= segments; i++) {
                var theta = (i / segments) * Math.PI * 2;
                points.push(new THREE.Vector3(Math.cos(theta) * data.radius, 0, Math.sin(theta) * data.radius));
            }
            ringGeo.setFromPoints(points);
            var ringMat = self.trackDisposable(new THREE.LineBasicMaterial({
                color: data.color,
                transparent: true,
                opacity: 0.28
            }));
            var orbitLine = new THREE.Line(ringGeo, ringMat);
            orbitLine.rotation.x = 0.25 * (idx % 2 === 0 ? 1 : -1);
            self.rootGroup.add(orbitLine);

            // Satellite Mesh
            var satGeo = self.trackDisposable(new THREE.SphereGeometry(data.size, 16, 16));
            var satMat = self.trackDisposable(new THREE.MeshStandardMaterial({
                color: data.color,
                emissive: data.color,
                emissiveIntensity: 0.4,
                roughness: 0.3,
                metalness: 0.7
            }));
            var satMesh = new THREE.Mesh(satGeo, satMat);
            satMesh.userData = data;
            satMesh.userData.angle = (idx * Math.PI) / 2;
            satMesh.userData.orbitTilt = orbitLine.rotation.x;
            self.rootGroup.add(satMesh);
            self.satellites.push(satMesh);
            self.interactiveObjects.push(satMesh);
        });

        // Dynamic Optical Laser Beams (LineSegments connecting core to 4 satellites)
        var laserGeo = this.trackDisposable(new THREE.BufferGeometry());
        var laserPositions = new Float32Array(4 * 2 * 3); // 4 lines * 2 vertices * 3 coords
        laserGeo.setAttribute('position', new THREE.BufferAttribute(laserPositions, 3));
        var laserMat = this.trackDisposable(new THREE.LineBasicMaterial({
            color: PALETTE.cyan,
            transparent: true,
            opacity: 0.65
        }));
        this.laserLines = new THREE.LineSegments(laserGeo, laserMat);
        this.rootGroup.add(this.laserLines);

        // Instanced Photon Particles (240 flowing points)
        var photonCount = 240;
        var photonGeo = this.trackDisposable(new THREE.BufferGeometry());
        var photonPositions = new Float32Array(photonCount * 3);
        this.photonAngles = new Float32Array(photonCount);
        this.photonRadii = new Float32Array(photonCount);
        this.photonSpeeds = new Float32Array(photonCount);

        for (var p = 0; p < photonCount; p++) {
            this.photonAngles[p] = Math.random() * Math.PI * 2;
            this.photonRadii[p] = 2.0 + Math.random() * 6.5;
            this.photonSpeeds[p] = 0.1 + Math.random() * 0.25;
            photonPositions[p * 3] = Math.cos(this.photonAngles[p]) * this.photonRadii[p];
            photonPositions[p * 3 + 1] = (Math.random() - 0.5) * 1.5;
            photonPositions[p * 3 + 2] = Math.sin(this.photonAngles[p]) * this.photonRadii[p];
        }
        photonGeo.setAttribute('position', new THREE.BufferAttribute(photonPositions, 3));
        var photonMat = this.trackDisposable(new THREE.PointsMaterial({
            color: PALETTE.cyan,
            size: 0.08,
            transparent: true,
            opacity: 0.75
        }));
        this.photonCloud = new THREE.Points(photonGeo, photonMat);
        this.rootGroup.add(this.photonCloud);

        return Promise.resolve();
    };

    SovereignCoreController.prototype.update = function (delta, elapsed) {
        // Rotate Core Nucleus
        if (this.coreMesh) {
            this.coreMesh.rotation.y += delta * 0.35;
            this.coreMesh.rotation.x += delta * 0.2;
        }
        if (this.pulseShell) {
            this.pulseShell.rotation.y -= delta * 0.25;
            var scale = 1.0 + Math.sin(elapsed * 2.5) * 0.06;
            this.pulseShell.scale.set(scale, scale, scale);
        }

        // Update Satellites along Orbits
        var laserPos = this.laserLines.geometry.attributes.position.array;
        var self = this;
        this.satellites.forEach(function (sat, i) {
            var data = sat.userData;
            data.angle += data.speed * delta;
            var x = Math.cos(data.angle) * data.radius;
            var z = Math.sin(data.angle) * data.radius;
            var y = Math.sin(data.angle * 2) * 0.35;

            // Apply tilt
            var tilt = data.orbitTilt;
            sat.position.set(x, y * Math.cos(tilt) - z * Math.sin(tilt), y * Math.sin(tilt) + z * Math.cos(tilt));

            // Laser beam endpoints: from core (0,0,0) to sat
            var baseIdx = i * 6;
            laserPos[baseIdx] = 0;
            laserPos[baseIdx + 1] = 0;
            laserPos[baseIdx + 2] = 0;
            laserPos[baseIdx + 3] = sat.position.x;
            laserPos[baseIdx + 4] = sat.position.y;
            laserPos[baseIdx + 5] = sat.position.z;
        });
        this.laserLines.geometry.attributes.position.needsUpdate = true;

        // Flow Photon Particles
        if (this.photonCloud) {
            var pPos = this.photonCloud.geometry.attributes.position.array;
            for (var p = 0; p < this.photonAngles.length; p++) {
                this.photonAngles[p] += this.photonSpeeds[p] * delta;
                pPos[p * 3] = Math.cos(this.photonAngles[p]) * this.photonRadii[p];
                pPos[p * 3 + 2] = Math.sin(this.photonAngles[p]) * this.photonRadii[p];
            }
            this.photonCloud.geometry.attributes.position.needsUpdate = true;
        }

        // Hover Raycast
        this.raycaster.setFromCamera(this.mouseNDC, this.camera);
        var intersects = this.raycaster.intersectObjects(this.interactiveObjects);
        if (intersects.length > 0) {
            var hit = intersects[0].object;
            this.highlightNode(hit.userData);
        }
    };

    SovereignCoreController.prototype.highlightNode = function (nodeData) {
        if (!nodeData || !nodeData.name) return;
        var titleEl = document.getElementById('innoria_active_node_title');
        var descEl = document.getElementById('innoria_active_node_desc');
        if (titleEl) titleEl.textContent = nodeData.name;
        if (descEl) descEl.textContent = nodeData.desc;
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
