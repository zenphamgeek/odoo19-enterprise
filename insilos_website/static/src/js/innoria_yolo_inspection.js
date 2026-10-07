/**
 * ============================================================================
 * INNORIA AI VISION — REAL-TIME YOLO DEFECT INSPECTION SIMULATOR
 * ============================================================================
 * File: enterprise/insilos_website/static/src/js/innoria_yolo_inspection.js
 * Host Target: https://innoria.insilos.com/industries
 *
 * Capabilities:
 *  1. Multi-Target Industrial Inspection Switching:
 *     - PCB SMT Electronics (Solder Bridge Short vs Component Alignment)
 *     - Automotive Stamping (Surface Dent Deviation vs Flange Radius)
 *     - Solar Silicon Wafer (Micro-Crack Dislocation vs Busbar Grid)
 *     - Robotic Weld Seam SS400 (Porosity Blowhole vs Bead Profile)
 *  2. Sub-Pixel YOLO Bounding Boxes with Monospace Precision Coordinates
 *  3. Real-Time Telemetry HUD Stream: Latency (11.4ms P99), 60 FPS, Optical Resolution
 *  4. Interactive Defect Injection Toggle (Pass / Fail Triage Simulation)
 *  5. Real-Time Confidence Threshold Slider (70% - 99% Dynamic Gating)
 *  6. Single-Frame Laser Scan Trigger with High-Tech Web Audio Synthesis
 *  7. 100% Transparent, Card-Free Layout on High-Tech Dark Palette (#0d1523)
 * ============================================================================
 */

(function () {
    'use strict';

    /**
     * Subtle Web Audio Acoustic Synthesizer for Industrial Laser Scan Chirp
     */
    class YoloInspectionAudio {
        constructor() {
            this.ctx = null;
            this.enabled = true;
        }

        initContext() {
            if (!this.ctx && typeof window !== 'undefined') {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (AudioCtx) {
                    this.ctx = new AudioCtx();
                }
            }
            if (this.ctx && this.ctx.state === 'suspended') {
                this.ctx.resume().catch(() => {});
            }
        }

        playScanChirp() {
            if (!this.enabled) return;
            try {
                this.initContext();
                if (!this.ctx) return;

                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();

                const now = this.ctx.currentTime;
                osc.type = 'sine';
                osc.frequency.setValueAtTime(980, now);
                osc.frequency.exponentialRampToValueAtTime(1640, now + 0.045);

                gain.gain.setValueAtTime(0.04, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.045);

                osc.connect(gain);
                gain.connect(this.ctx.destination);

                osc.start(now);
                osc.stop(now + 0.05);
            } catch (e) {
                // Audio synthesis optional, fails silently if user blocked audio
            }
        }

        playAlarmBlip() {
            if (!this.enabled) return;
            try {
                this.initContext();
                if (!this.ctx) return;

                const now = this.ctx.currentTime;
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();

                osc.type = 'triangle';
                osc.frequency.setValueAtTime(440, now);
                osc.frequency.setValueAtTime(880, now + 0.05);

                gain.gain.setValueAtTime(0.05, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);

                osc.connect(gain);
                gain.connect(this.ctx.destination);

                osc.start(now);
                osc.stop(now + 0.13);
            } catch (e) {}
        }
    }

    /**
     * Detailed Industrial Inspection Scenarios Registry
     */
    const INSPECTION_SCENARIOS = {
        'pcb': {
            id: 'pcb',
            name: 'PCB SMT Electronics',
            targetCode: 'INSP-PCB-SMT-A82',
            modelName: 'YOLOv11x-SMT-QC',
            resolution: 'SONY IMX586 48MP // 50mm TELECENTRIC',
            defectClass: 'SOLDER_BRIDGE_SHORT',
            defectConfidence: 0.9942,
            defectDescription: 'Pin 14-15 solder bridge detected. Short circuit hazard > 99.8%.',
            passDescription: '100% SMT IC pins aligned. Solder meniscus nominal. Zero defects.',
            defectAction: 'REJECT GATEWAY · PLC PIN 04 ACTIVATED',
            passAction: 'BUFFER CONVEYOR #02 · BATCH ACCEPTED',
            stats: {
                latency: '11.4ms',
                precision: '99.42%',
                fps: '60.0',
                resolution: '0.015mm'
            },
            svgGraphic: `
                <svg viewBox="0 0 800 500" class="w-100 h-100" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="pcbBg" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#041812"/>
                            <stop offset="100%" stop-color="#08281C"/>
                        </linearGradient>
                        <pattern id="gridCopper" width="40" height="40" patternUnits="userSpaceOnUse">
                            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#00F0FF" stroke-width="0.5" stroke-opacity="0.15"/>
                        </pattern>
                        <filter id="glowRed" x="-20%" y="-20%" width="140%" height="140%">
                            <feGaussianBlur stdDeviation="6" result="blur" />
                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                        </filter>
                    </defs>
                    <!-- PCB Board Substrate -->
                    <rect width="800" height="500" fill="url(#pcbBg)" rx="16"/>
                    <rect width="800" height="500" fill="url(#gridCopper)"/>
                    
                    <!-- Copper Traces -->
                    <g stroke="#00F0FF" stroke-width="2" stroke-opacity="0.35" fill="none">
                        <path d="M 60 80 L 180 80 L 240 140 L 300 140"/>
                        <path d="M 60 120 L 160 120 L 210 170 L 300 170"/>
                        <path d="M 60 420 L 200 420 L 270 350 L 310 350"/>
                        <path d="M 740 80 L 620 80 L 560 140 L 500 140"/>
                        <path d="M 740 420 L 600 420 L 530 350 L 490 350"/>
                        <path d="M 400 60 L 400 130"/>
                        <path d="M 400 440 L 400 370"/>
                    </g>

                    <!-- Surface Capacitors and Resistors -->
                    <!-- C0805 Capacitor -->
                    <g transform="translate(130, 290)">
                        <rect x="-30" y="-18" width="60" height="36" fill="#78350F" rx="4"/>
                        <rect x="-30" y="-18" width="12" height="36" fill="#CBD5E1"/>
                        <rect x="18" y="-18" width="12" height="36" fill="#CBD5E1"/>
                        <text x="0" y="32" fill="#94A3B8" font-size="10" font-family="monospace" text-anchor="middle">C0805_10uF</text>
                    </g>
                    <!-- Resistor R0603 -->
                    <g transform="translate(610, 290)">
                        <rect x="-24" y="-14" width="48" height="28" fill="#1E293B" stroke="#475569" rx="3"/>
                        <rect x="-24" y="-14" width="10" height="28" fill="#E2E8F0"/>
                        <rect x="14" y="-14" width="10" height="28" fill="#E2E8F0"/>
                        <text x="0" y="5" fill="#38BDF8" font-size="10" font-family="monospace" text-anchor="middle">1002</text>
                        <text x="0" y="30" fill="#94A3B8" font-size="10" font-family="monospace" text-anchor="middle">R0603_10k</text>
                    </g>
                    <!-- Fiducial Marker -->
                    <g transform="translate(100, 80)">
                        <circle r="12" fill="none" stroke="#EAB308" stroke-width="2"/>
                        <circle r="5" fill="#EAB308"/>
                    </g>

                    <!-- Central QFP-32 IC Package -->
                    <g transform="translate(400, 250)">
                        <!-- IC Body -->
                        <rect x="-110" y="-110" width="220" height="220" fill="#0B1322" stroke="#1E293B" stroke-width="3" rx="10"/>
                        <!-- Pin 1 Dot -->
                        <circle cx="-90" cy="-90" r="7" fill="#334155"/>
                        <!-- IC Laser Engraving -->
                        <text x="0" y="-20" fill="#E2E8F0" font-size="15" font-family="monospace" font-weight="bold" text-anchor="middle" letter-spacing="2">INNORIA-AI</text>
                        <text x="0" y="10" fill="#38BDF8" font-size="13" font-family="monospace" text-anchor="middle">QFP-32 SMT</text>
                        <text x="0" y="32" fill="#64748B" font-size="10" font-family="monospace" text-anchor="middle">LOT #2609-VN</text>

                        <!-- North / South / East / West Pins -->
                        <!-- North Pins -->
                        <g fill="#E2E8F0" stroke="#94A3B8" stroke-width="1">
                            <rect x="-85" y="-134" width="10" height="24" rx="2"/>
                            <rect x="-65" y="-134" width="10" height="24" rx="2"/>
                            <rect x="-45" y="-134" width="10" height="24" rx="2"/>
                            <rect x="-25" y="-134" width="10" height="24" rx="2"/>
                            <rect x="-5" y="-134" width="10" height="24" rx="2"/>
                            <rect x="15" y="-134" width="10" height="24" rx="2"/>
                            <rect x="35" y="-134" width="10" height="24" rx="2"/>
                            <rect x="55" y="-134" width="10" height="24" rx="2"/>
                            <rect x="75" y="-134" width="10" height="24" rx="2"/>
                        </g>
                        <!-- South Pins -->
                        <g fill="#E2E8F0" stroke="#94A3B8" stroke-width="1">
                            <rect x="-85" y="110" width="10" height="24" rx="2"/>
                            <rect x="-65" y="110" width="10" height="24" rx="2"/>
                            <rect x="-45" y="110" width="10" height="24" rx="2"/>
                            <rect x="-25" y="110" width="10" height="24" rx="2"/>
                            <rect x="-5" y="110" width="10" height="24" rx="2"/>
                            <rect x="15" y="110" width="10" height="24" rx="2"/>
                            <rect x="35" y="110" width="10" height="24" rx="2"/>
                            <rect x="55" y="110" width="10" height="24" rx="2"/>
                            <rect x="75" y="110" width="10" height="24" rx="2"/>
                        </g>
                        <!-- West Pins -->
                        <g fill="#E2E8F0" stroke="#94A3B8" stroke-width="1">
                            <rect x="-134" y="-85" width="24" height="10" rx="2"/>
                            <rect x="-134" y="-65" width="24" height="10" rx="2"/>
                            <rect x="-134" y="-45" width="24" height="10" rx="2"/>
                            <rect x="-134" y="-25" width="24" height="10" rx="2"/>
                            <rect x="-134" y="-5" width="24" height="10" rx="2"/>
                            <rect x="-134" y="15" width="24" height="10" rx="2"/>
                            <rect x="-134" y="35" width="24" height="10" rx="2"/>
                            <rect x="-134" y="55" width="24" height="10" rx="2"/>
                            <rect x="-134" y="75" width="24" height="10" rx="2"/>
                        </g>
                        <!-- East Pins (Includes Solder Bridge Defect on Pins 14-15) -->
                        <g fill="#E2E8F0" stroke="#94A3B8" stroke-width="1">
                            <rect x="110" y="-85" width="24" height="10" rx="2"/>
                            <rect x="110" y="-65" width="24" height="10" rx="2"/>
                            <rect x="110" y="-45" width="24" height="10" rx="2"/>
                            <!-- Pin 14 -->
                            <rect x="110" y="-25" width="24" height="10" rx="2"/>
                            <!-- Pin 15 -->
                            <rect x="110" y="-5" width="24" height="10" rx="2"/>
                            <rect x="110" y="15" width="24" height="10" rx="2"/>
                            <rect x="110" y="35" width="24" height="10" rx="2"/>
                            <rect x="110" y="55" width="24" height="10" rx="2"/>
                            <rect x="110" y="75" width="24" height="10" rx="2"/>
                        </g>

                        <!-- DEFECT ANOMALY: SOLDER BRIDGE BLOB (Visible when defect active) -->
                        <g class="ins-defect-graphic" transform="translate(112, -22)">
                            <!-- Red Glowing Solder Bridge across pin 14-15 -->
                            <ellipse cx="12" cy="13" rx="14" ry="16" fill="#EF4444" opacity="0.88" filter="url(#glowRed)"/>
                            <ellipse cx="12" cy="13" rx="9" ry="11" fill="#FFAA00" opacity="0.95"/>
                            <circle cx="12" cy="13" r="4" fill="#FFFFFF"/>
                        </g>
                    </g>
                </svg>
            `,
            boxes: [
                {
                    id: 'pcb_box_defect',
                    label: 'DEFECT: SOLDER_BRIDGE #04',
                    conf: 0.994,
                    isDefect: true,
                    x: 50.5,
                    y: 39.0,
                    w: 16.5,
                    h: 15.0,
                    coordsText: '[X: 0.505, Y: 0.390, W: 0.165, H: 0.150]'
                },
                {
                    id: 'pcb_box_ic',
                    label: 'PASS: QFP-32_IC_ALIGNED',
                    conf: 0.998,
                    isDefect: false,
                    x: 36.0,
                    y: 27.0,
                    w: 28.0,
                    h: 46.0,
                    coordsText: '[X: 0.360, Y: 0.270, W: 0.280, H: 0.460]'
                },
                {
                    id: 'pcb_box_cap',
                    label: 'PASS: C0805_CAP_OK',
                    conf: 0.991,
                    isDefect: false,
                    x: 12.0,
                    y: 53.0,
                    w: 16.0,
                    h: 19.0,
                    coordsText: '[X: 0.120, Y: 0.530, W: 0.160, H: 0.190]'
                },
                {
                    id: 'pcb_box_res',
                    label: 'PASS: R0603_RES_OK',
                    conf: 0.995,
                    isDefect: false,
                    x: 72.0,
                    y: 53.0,
                    w: 15.0,
                    h: 19.0,
                    coordsText: '[X: 0.720, Y: 0.530, W: 0.150, H: 0.190]'
                },
                {
                    id: 'pcb_box_fid',
                    label: 'PASS: FIDUCIAL_MARK_01',
                    conf: 0.999,
                    isDefect: false,
                    x: 10.0,
                    y: 12.0,
                    w: 10.0,
                    h: 15.0,
                    coordsText: '[X: 0.100, Y: 0.120, W: 0.100, H: 0.150]'
                }
            ]
        },

        'auto_stamping': {
            id: 'auto_stamping',
            name: 'Automotive Stamping',
            targetCode: 'INSP-AUTO-STAMP-C14',
            modelName: 'YOLOv11x-METROLOGY',
            resolution: 'KEYENCE 3D LASER PROFILER // 0.01mm',
            defectClass: 'SURFACE_DENT_DEVIATION',
            defectConfidence: 0.9885,
            defectDescription: '0.85mm localized surface depression exceeding Class-A tolerance (0.20mm).',
            passDescription: 'Class-A surface contour verified. Flange radii within ±0.05mm. Zero dents.',
            defectAction: 'TRIP STAMPING INTERLOCK · SCRAP HOPPER DIVERTER',
            passAction: 'TRANSFER TO ROBOTIC WELD CELL #01',
            stats: {
                latency: '12.1ms',
                precision: '99.28%',
                fps: '60.0',
                resolution: '0.010mm'
            },
            svgGraphic: `
                <svg viewBox="0 0 800 500" class="w-100 h-100" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="metalBody" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#1E293B"/>
                            <stop offset="35%" stop-color="#334155"/>
                            <stop offset="70%" stop-color="#1E293B"/>
                            <stop offset="100%" stop-color="#0F172A"/>
                        </linearGradient>
                        <linearGradient id="bevelLight" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#94A3B8" stop-opacity="0.8"/>
                            <stop offset="100%" stop-color="#334155" stop-opacity="0.2"/>
                        </linearGradient>
                        <filter id="dentGlow" x="-30%" y="-30%" width="160%" height="160%">
                            <feGaussianBlur stdDeviation="8" result="blur" />
                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                        </filter>
                    </defs>
                    <!-- Automotive Sheet Metal Body -->
                    <rect width="800" height="500" fill="#0A0F1D"/>
                    <path d="M 60 70 L 740 70 L 700 430 L 100 430 Z" fill="url(#metalBody)" stroke="#475569" stroke-width="2"/>
                    
                    <!-- Structural Embossments / Flanges -->
                    <path d="M 120 120 L 680 120 L 650 380 L 150 380 Z" fill="none" stroke="url(#bevelLight)" stroke-width="4"/>
                    <path d="M 220 170 L 580 170" stroke="#00F0FF" stroke-width="1.5" stroke-dasharray="6,4" stroke-opacity="0.5"/>
                    <path d="M 200 330 L 600 330" stroke="#00F0FF" stroke-width="1.5" stroke-dasharray="6,4" stroke-opacity="0.5"/>

                    <!-- Pilot Holes / Assembly Punches -->
                    <g fill="#050B14" stroke="#64748B" stroke-width="2">
                        <circle cx="160" cy="250" r="26"/>
                        <circle cx="640" cy="250" r="26"/>
                    </g>
                    <g fill="#00F0FF" opacity="0.8">
                        <circle cx="160" cy="250" r="3"/>
                        <circle cx="640" cy="250" r="3"/>
                    </g>

                    <!-- Technical Contour Lines (CAD Surface) -->
                    <g stroke="#38BDF8" stroke-width="0.8" stroke-opacity="0.25" fill="none">
                        <path d="M 200 200 Q 400 170 600 200"/>
                        <path d="M 190 230 Q 400 190 610 230"/>
                        <path d="M 180 260 Q 400 210 620 260"/>
                        <path d="M 190 290 Q 400 240 610 290"/>
                    </g>

                    <!-- DEFECT: STAMPING DENT ANOMALY -->
                    <g class="ins-defect-graphic" transform="translate(380, 240)">
                        <ellipse cx="0" cy="0" rx="55" ry="38" fill="#EF4444" opacity="0.3" filter="url(#dentGlow)"/>
                        <!-- Contour Deformation Rings -->
                        <ellipse cx="0" cy="0" rx="44" ry="28" fill="none" stroke="#EF4444" stroke-width="2" stroke-dasharray="4,2"/>
                        <ellipse cx="0" cy="0" rx="28" ry="18" fill="none" stroke="#FFAA00" stroke-width="2.5"/>
                        <ellipse cx="0" cy="0" rx="14" ry="9" fill="#FF0000" opacity="0.85"/>
                        <!-- Anomaly Crosshair -->
                        <line x1="-18" y1="0" x2="18" y2="0" stroke="#FFFFFF" stroke-width="1.5"/>
                        <line x1="0" y1="-12" x2="0" y2="12" stroke="#FFFFFF" stroke-width="1.5"/>
                    </g>
                </svg>
            `,
            boxes: [
                {
                    id: 'auto_box_defect',
                    label: 'DEFECT: STAMPING_DENT #02',
                    conf: 0.988,
                    isDefect: true,
                    x: 41.0,
                    y: 36.0,
                    w: 22.0,
                    h: 22.0,
                    coordsText: '[X: 0.410, Y: 0.360, W: 0.220, H: 0.220]'
                },
                {
                    id: 'auto_box_flange',
                    label: 'PASS: FLANGE_RADIUS_OK',
                    conf: 0.996,
                    isDefect: false,
                    x: 10.0,
                    y: 18.0,
                    w: 20.0,
                    h: 56.0,
                    coordsText: '[X: 0.100, Y: 0.180, W: 0.200, H: 0.560]'
                },
                {
                    id: 'auto_box_hole',
                    label: 'PASS: PILOT_HOLE_PUNCH',
                    conf: 0.997,
                    isDefect: false,
                    x: 74.0,
                    y: 38.0,
                    w: 14.0,
                    h: 22.0,
                    coordsText: '[X: 0.740, Y: 0.380, W: 0.140, H: 0.220]'
                },
                {
                    id: 'auto_box_contour',
                    label: 'PASS: CONTOUR_GAUGE_OK',
                    conf: 0.992,
                    isDefect: false,
                    x: 34.0,
                    y: 68.0,
                    w: 36.0,
                    h: 18.0,
                    coordsText: '[X: 0.340, Y: 0.680, W: 0.360, H: 0.180]'
                }
            ]
        },

        'solar_wafer': {
            id: 'solar_wafer',
            name: 'Solar Silicon Wafer',
            targetCode: 'INSP-PV-WAFER-M10',
            modelName: 'YOLOv11x-PHOTOVOLTAIC',
            resolution: 'ELECTROLUMINESCENCE NIR 1100nm SENSOR',
            defectClass: 'MICRO_CRACK_DISLOCATION',
            defectConfidence: 0.9924,
            defectDescription: '14.2mm sub-surface dislocation along [110] slip plane. EL emission drop 42%.',
            passDescription: 'Monocrystalline lattice uniform. 16/16 busbars intact. EL emission 99.8%.',
            defectAction: 'PNEUMATIC SUCTION SORTER // RETRACT TO BIN C',
            passAction: 'FORWARD TO STRINGING & LAYUP CONVEYOR',
            stats: {
                latency: '10.8ms',
                precision: '99.55%',
                fps: '60.0',
                resolution: '0.012mm'
            },
            svgGraphic: `
                <svg viewBox="0 0 800 500" class="w-100 h-100" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="waferBlue" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#07152B"/>
                            <stop offset="50%" stop-color="#0E274D"/>
                            <stop offset="100%" stop-color="#061224"/>
                        </linearGradient>
                        <pattern id="fingerGrid" width="10" height="6" patternUnits="userSpaceOnUse">
                            <line x1="0" y1="3" x2="10" y2="3" stroke="#38BDF8" stroke-width="0.35" stroke-opacity="0.3"/>
                        </pattern>
                        <filter id="crackGlow" x="-30%" y="-30%" width="160%" height="160%">
                            <feGaussianBlur stdDeviation="6" result="blur"/>
                            <feComposite in="SourceGraphic" in2="blur" operator="over"/>
                        </filter>
                    </defs>
                    <rect width="800" height="500" fill="#040812"/>

                    <!-- Pseudo-Square Silicon Wafer Body (182mm standard) -->
                    <g transform="translate(180, 40)">
                        <!-- Beveled Wafer Outline -->
                        <polygon points="50,0 390,0 440,50 440,370 390,420 50,420 0,370 0,50" fill="url(#waferBlue)" stroke="#1E3A8A" stroke-width="2"/>
                        <!-- Fine Finger Grid Pattern -->
                        <polygon points="50,0 390,0 440,50 440,370 390,420 50,420 0,370 0,50" fill="url(#fingerGrid)"/>

                        <!-- Vertical Silver Busbars (Multi-Busbar MBB) -->
                        <g stroke="#E2E8F0" stroke-width="3" opacity="0.85">
                            <line x1="60" y1="10" x2="60" y2="410"/>
                            <line x1="120" y1="5" x2="120" y2="415"/>
                            <line x1="180" y1="5" x2="180" y2="415"/>
                            <line x1="240" y1="5" x2="240" y2="415"/>
                            <line x1="300" y1="5" x2="300" y2="415"/>
                            <line x1="360" y1="5" x2="360" y2="415"/>
                            <line x1="400" y1="20" x2="400" y2="400"/>
                        </g>

                        <!-- DEFECT: MICRO-CRACK ALONG CRYSTAL PLANE -->
                        <g class="ins-defect-graphic" transform="translate(245, 110)">
                            <!-- Glowing Aura -->
                            <path d="M 0 0 L 25 18 L 45 42 L 75 58 L 90 95" fill="none" stroke="#EF4444" stroke-width="6" opacity="0.8" filter="url(#crackGlow)"/>
                            <!-- Core Crack Line -->
                            <path d="M 0 0 L 25 18 L 45 42 L 75 58 L 90 95" fill="none" stroke="#FFAA00" stroke-width="2.5"/>
                            <path d="M 0 0 L 25 18 L 45 42 L 75 58 L 90 95" fill="none" stroke="#FFFFFF" stroke-width="1"/>
                            <!-- Crack Nodes -->
                            <circle cx="0" cy="0" r="3" fill="#FFFFFF"/>
                            <circle cx="45" cy="42" r="3.5" fill="#EF4444"/>
                            <circle cx="90" cy="95" r="3" fill="#FFFFFF"/>
                        </g>
                    </g>
                </svg>
            `,
            boxes: [
                {
                    id: 'solar_box_defect',
                    label: 'DEFECT: MICRO_CRACK #01',
                    conf: 0.992,
                    isDefect: true,
                    x: 52.0,
                    y: 26.0,
                    w: 20.0,
                    h: 26.0,
                    coordsText: '[X: 0.520, Y: 0.260, W: 0.200, H: 0.260]'
                },
                {
                    id: 'solar_box_bb1',
                    label: 'PASS: BUSBAR_01_INTEGRITY',
                    conf: 0.999,
                    isDefect: false,
                    x: 27.0,
                    y: 12.0,
                    w: 10.0,
                    h: 76.0,
                    coordsText: '[X: 0.270, Y: 0.120, W: 0.100, H: 0.760]'
                },
                {
                    id: 'solar_box_bb2',
                    label: 'PASS: BUSBAR_02_INTEGRITY',
                    conf: 0.998,
                    isDefect: false,
                    x: 68.0,
                    y: 12.0,
                    w: 10.0,
                    h: 76.0,
                    coordsText: '[X: 0.680, Y: 0.120, W: 0.100, H: 0.760]'
                },
                {
                    id: 'solar_box_chamfer',
                    label: 'PASS: WAFER_CHAMFER_OK',
                    conf: 0.995,
                    isDefect: false,
                    x: 21.0,
                    y: 10.0,
                    w: 12.0,
                    h: 16.0,
                    coordsText: '[X: 0.210, Y: 0.100, W: 0.120, H: 0.160]'
                }
            ]
        },

        'weld_seam': {
            id: 'weld_seam',
            name: 'Weld Seam SS400',
            targetCode: 'INSP-WELD-SS400-J08',
            modelName: 'YOLOv11x-WELD-AUDIT',
            resolution: 'COAXIAL 200 FPS HIGH-SPEED LASER VISION',
            defectClass: 'POROSITY_BLOWHOLE_CLUSTER',
            defectConfidence: 0.9892,
            defectDescription: 'Gas porosity cluster > 1.2mm. AWS D1.1 structural welding tolerance exceeded.',
            passDescription: 'Weld bead scallop uniform. Full penetration verified. HAZ within specification.',
            defectAction: 'ROBOT CONTROLLER HOLD · FLAGGED FOR RE-WELD',
            passAction: 'RELEASED TO ULTRASONIC NDT TESTING STATION',
            stats: {
                latency: '11.8ms',
                precision: '99.35%',
                fps: '60.0',
                resolution: '0.020mm'
            },
            svgGraphic: `
                <svg viewBox="0 0 800 500" class="w-100 h-100" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="plateSteel" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#1E293B"/>
                            <stop offset="50%" stop-color="#334155"/>
                            <stop offset="100%" stop-color="#1E293B"/>
                        </linearGradient>
                        <linearGradient id="hazGradientTop" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#334155"/>
                            <stop offset="60%" stop-color="#7C3AED" stop-opacity="0.35"/>
                            <stop offset="100%" stop-color="#F59E0B" stop-opacity="0.45"/>
                        </linearGradient>
                        <linearGradient id="hazGradientBottom" x1="0%" y1="100%" x2="0%" y2="0%">
                            <stop offset="0%" stop-color="#334155"/>
                            <stop offset="60%" stop-color="#7C3AED" stop-opacity="0.35"/>
                            <stop offset="100%" stop-color="#F59E0B" stop-opacity="0.45"/>
                        </linearGradient>
                        <filter id="porosityGlow" x="-30%" y="-30%" width="160%" height="160%">
                            <feGaussianBlur stdDeviation="7" result="blur"/>
                            <feComposite in="SourceGraphic" in2="blur" operator="over"/>
                        </filter>
                    </defs>
                    <rect width="800" height="500" fill="#070C16"/>

                    <!-- Top Steel Plate SS400 (12mm) -->
                    <rect x="50" y="40" width="700" height="150" fill="url(#plateSteel)" stroke="#475569" stroke-width="1.5"/>
                    <rect x="50" y="140" width="700" height="50" fill="url(#hazGradientTop)"/>

                    <!-- Bottom Steel Plate SS400 (12mm) -->
                    <rect x="50" y="310" width="700" height="150" fill="url(#plateSteel)" stroke="#475569" stroke-width="1.5"/>
                    <rect x="50" y="310" width="700" height="50" fill="url(#hazGradientBottom)"/>

                    <!-- Center Robotic Weld Bead (GMAW Ripples) -->
                    <g fill="#94A3B8" stroke="#475569" stroke-width="1.5">
                        <!-- Repeated Scalloped Weld Bead Ripples -->
                        <path d="M 60 190 Q 75 250 60 310 L 90 310 Q 105 250 90 190 Z" fill="#64748B"/>
                        <path d="M 85 190 Q 100 250 85 310 L 115 310 Q 130 250 115 190 Z" fill="#94A3B8"/>
                        <path d="M 110 190 Q 125 250 110 310 L 140 310 Q 155 250 140 190 Z" fill="#64748B"/>
                        <path d="M 135 190 Q 150 250 135 310 L 165 310 Q 180 250 165 190 Z" fill="#CBD5E1"/>
                        <path d="M 160 190 Q 175 250 160 310 L 190 310 Q 205 250 190 190 Z" fill="#94A3B8"/>
                        <path d="M 185 190 Q 200 250 185 310 L 215 310 Q 230 250 215 190 Z" fill="#64748B"/>
                        <path d="M 210 190 Q 225 250 210 310 L 240 310 Q 255 250 240 190 Z" fill="#CBD5E1"/>
                        <path d="M 235 190 Q 250 250 235 310 L 265 310 Q 280 250 265 190 Z" fill="#94A3B8"/>
                        <path d="M 260 190 Q 275 250 260 310 L 290 310 Q 305 250 290 190 Z" fill="#64748B"/>
                        <path d="M 285 190 Q 300 250 285 310 L 315 310 Q 330 250 315 190 Z" fill="#CBD5E1"/>
                        <path d="M 310 190 Q 325 250 310 310 L 340 310 Q 355 250 340 190 Z" fill="#94A3B8"/>
                        <path d="M 335 190 Q 350 250 335 310 L 365 310 Q 380 250 365 190 Z" fill="#64748B"/>
                        <!-- Central section -->
                        <path d="M 360 190 Q 375 250 360 310 L 440 310 Q 455 250 440 190 Z" fill="#94A3B8"/>
                        <path d="M 435 190 Q 450 250 435 310 L 465 310 Q 480 250 465 190 Z" fill="#CBD5E1"/>
                        <path d="M 460 190 Q 475 250 460 310 L 490 310 Q 505 250 490 190 Z" fill="#64748B"/>
                        <path d="M 485 190 Q 500 250 485 310 L 515 310 Q 530 250 515 190 Z" fill="#94A3B8"/>
                        <path d="M 510 190 Q 525 250 510 310 L 540 310 Q 555 250 540 190 Z" fill="#CBD5E1"/>
                        <path d="M 535 190 Q 550 250 535 310 L 565 310 Q 580 250 565 190 Z" fill="#64748B"/>
                        <path d="M 560 190 Q 575 250 560 310 L 590 310 Q 605 250 590 190 Z" fill="#94A3B8"/>
                        <path d="M 585 190 Q 600 250 585 310 L 615 310 Q 630 250 615 190 Z" fill="#CBD5E1"/>
                        <path d="M 610 190 Q 625 250 610 310 L 640 310 Q 655 250 640 190 Z" fill="#64748B"/>
                        <path d="M 635 190 Q 650 250 635 310 L 665 310 Q 680 250 665 190 Z" fill="#94A3B8"/>
                        <path d="M 660 190 Q 675 250 660 310 L 740 310 Q 750 250 740 190 Z" fill="#64748B"/>
                    </g>

                    <!-- DEFECT: POROSITY BLOWHOLE CLUSTER (Center of Bead) -->
                    <g class="ins-defect-graphic" transform="translate(400, 250)">
                        <!-- Heat Glow -->
                        <ellipse cx="0" cy="0" rx="35" ry="30" fill="#EF4444" opacity="0.35" filter="url(#porosityGlow)"/>
                        <!-- Deep Gas Blowhole Pores -->
                        <circle cx="-10" cy="-6" r="6" fill="#000000" stroke="#EF4444" stroke-width="2"/>
                        <circle cx="8" cy="-2" r="8" fill="#000000" stroke="#EF4444" stroke-width="2.5"/>
                        <circle cx="-4" cy="10" r="5" fill="#000000" stroke="#FFAA00" stroke-width="2"/>
                        <circle cx="14" cy="9" r="4" fill="#000000" stroke="#EF4444" stroke-width="1.5"/>
                    </g>
                </svg>
            `,
            boxes: [
                {
                    id: 'weld_box_defect',
                    label: 'DEFECT: POROSITY_CLUSTER',
                    conf: 0.989,
                    isDefect: true,
                    x: 44.0,
                    y: 38.0,
                    w: 18.0,
                    h: 18.0,
                    coordsText: '[X: 0.440, Y: 0.380, W: 0.180, H: 0.180]'
                },
                {
                    id: 'weld_box_bead',
                    label: 'PASS: BEAD_WIDTH_14MM',
                    conf: 0.995,
                    isDefect: false,
                    x: 16.0,
                    y: 32.0,
                    w: 24.0,
                    h: 34.0,
                    coordsText: '[X: 0.160, Y: 0.320, W: 0.240, H: 0.340]'
                },
                {
                    id: 'weld_box_toe',
                    label: 'PASS: TOE_BLEND_PROFILE',
                    conf: 0.993,
                    isDefect: false,
                    x: 64.0,
                    y: 32.0,
                    w: 24.0,
                    h: 34.0,
                    coordsText: '[X: 0.640, Y: 0.320, W: 0.240, H: 0.340]'
                },
                {
                    id: 'weld_box_haz',
                    label: 'PASS: HAZ_TEMPERATURE_OK',
                    conf: 0.997,
                    isDefect: false,
                    x: 32.0,
                    y: 16.0,
                    w: 36.0,
                    h: 15.0,
                    coordsText: '[X: 0.320, Y: 0.160, W: 0.360, H: 0.150]'
                }
            ]
        }
    };

    /**
     * Main Controller for YOLO Inspection Simulator
     */
    class InnoriaYoloInspectionSimulator {
        constructor(rootEl) {
            this.root = rootEl;
            this.activeScenarioKey = 'pcb';
            this.defectInjected = true;
            this.confidenceThreshold = 85; // %
            this.audio = new YoloInspectionAudio();
            this.rafId = null;

            this.cacheDomElements();
            this.bindEvents();
            this.initClock();
            this.applyScenario(this.activeScenarioKey);
        }

        cacheDomElements() {
            // Viewport & HUD Elements
            this.viewport = this.root.querySelector('.ins-yolo-viewport');
            this.canvasContainer = this.root.querySelector('.ins-yolo-canvas-container');
            this.overlayLayer = this.root.querySelector('.ins-yolo-overlay-layer');
            this.laserBeam = this.root.querySelector('.ins-yolo-laser-beam');
            this.statusPill = this.root.querySelector('.ins-yolo-status-pill');
            this.statusText = this.root.querySelector('.ins-yolo-status-text');
            this.statusDot = this.root.querySelector('.ins-yolo-status-dot');
            this.clockEl = this.root.querySelector('.ins-yolo-clock');

            // Telemetry Readouts
            this.targetEl = this.root.querySelector('.ins-telemetry-target');
            this.bboxEl = this.root.querySelector('.ins-telemetry-bbox');
            this.confEl = this.root.querySelector('.ins-telemetry-conf');
            this.latencyEl = this.root.querySelector('.ins-telemetry-latency');
            this.fpsEl = this.root.querySelector('.ins-telemetry-fps');
            this.actionEl = this.root.querySelector('.ins-telemetry-action');

            // Left Side Controls & Detail Callouts
            this.scenarioButtons = this.root.querySelectorAll('[data-inspection-target]');
            this.defectToggle = this.root.querySelector('#toggleDefectInjection');
            this.thresholdSlider = this.root.querySelector('#confidenceThresholdSlider');
            this.thresholdValueEl = this.root.querySelector('#confidenceThresholdValue');
            this.scanTriggerBtn = this.root.querySelector('#btnTriggerScan');
            this.defectDetailBox = this.root.querySelector('.ins-defect-detail-box');
            this.defectDetailText = this.root.querySelector('.ins-defect-detail-text');
            this.modelBadge = this.root.querySelector('.ins-yolo-model-badge');
            this.sensorBadge = this.root.querySelector('.ins-yolo-sensor-badge');
        }

        bindEvents() {
            // Scenario switcher buttons
            if (this.scenarioButtons) {
                this.scenarioButtons.forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        const targetKey = btn.getAttribute('data-inspection-target');
                        if (targetKey && INSPECTION_SCENARIOS[targetKey]) {
                            this.switchScenario(targetKey);
                        }
                    });
                });
            }

            // Defect toggle switch
            if (this.defectToggle) {
                this.defectToggle.addEventListener('change', () => {
                    this.defectInjected = this.defectToggle.checked;
                    this.updateInspectionState();
                    if (this.defectInjected) {
                        this.audio.playAlarmBlip();
                    } else {
                        this.audio.playScanChirp();
                    }
                });
            }

            // Confidence threshold slider
            if (this.thresholdSlider) {
                this.thresholdSlider.addEventListener('input', () => {
                    this.confidenceThreshold = parseInt(this.thresholdSlider.value, 10) || 85;
                    if (this.thresholdValueEl) {
                        this.thresholdValueEl.textContent = this.confidenceThreshold + '%';
                    }
                    this.filterBoundingBoxes();
                });
            }

            // Single-frame laser scan trigger button
            if (this.scanTriggerBtn) {
                this.scanTriggerBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.triggerScan();
                });
            }
        }

        initClock() {
            let startTime = performance.now();
            const tick = () => {
                const elapsed = (performance.now() - startTime) / 1000;
                const m = Math.floor(elapsed / 60);
                const s = Math.floor(elapsed % 60);
                const ms = Math.floor((elapsed % 1) * 1000);
                if (this.clockEl) {
                    this.clockEl.textContent = 
                        String(m).padStart(2, '0') + ':' + 
                        String(s).padStart(2, '0') + '.' + 
                        String(ms).padStart(3, '0');
                }
                this.rafId = requestAnimationFrame(tick);
            };
            this.rafId = requestAnimationFrame(tick);
        }

        switchScenario(scenarioKey) {
            if (this.activeScenarioKey === scenarioKey) return;
            this.activeScenarioKey = scenarioKey;

            // Update active button state
            this.scenarioButtons.forEach(btn => {
                const k = btn.getAttribute('data-inspection-target');
                if (k === scenarioKey) {
                    btn.classList.add('is-active');
                } else {
                    btn.classList.remove('is-active');
                }
            });

            this.applyScenario(scenarioKey);
            this.triggerScan();
        }

        applyScenario(scenarioKey) {
            const scenario = INSPECTION_SCENARIOS[scenarioKey];
            if (!scenario) return;

            // Render SVG Target graphic
            if (this.canvasContainer) {
                this.canvasContainer.innerHTML = scenario.svgGraphic;
            }

            // Update model and sensor metadata badges
            if (this.modelBadge) {
                this.modelBadge.textContent = scenario.modelName;
            }
            if (this.sensorBadge) {
                this.sensorBadge.textContent = scenario.resolution;
            }

            // Render Bounding Boxes
            this.renderBoundingBoxes(scenario.boxes);

            // Update inspection state (Defect vs Pass)
            this.updateInspectionState();
        }

        renderBoundingBoxes(boxes) {
            if (!this.overlayLayer) return;
            this.overlayLayer.innerHTML = '';

            boxes.forEach(box => {
                const boxEl = document.createElement('div');
                boxEl.className = 'ins-yolo-box';
                boxEl.id = box.id;
                boxEl.setAttribute('data-conf', box.conf);
                boxEl.setAttribute('data-is-defect', box.isDefect ? 'true' : 'false');
                boxEl.setAttribute('data-coords', box.coordsText);

                // Position box with percentages
                boxEl.style.left = box.x + '%';
                boxEl.style.top = box.y + '%';
                boxEl.style.width = box.w + '%';
                boxEl.style.height = box.h + '%';

                if (box.isDefect) {
                    boxEl.classList.add('is-defect');
                } else {
                    boxEl.classList.add('is-pass');
                }

                // Tag badge
                const tagEl = document.createElement('span');
                tagEl.className = 'ins-yolo-box-tag';
                tagEl.textContent = box.label;
                boxEl.appendChild(tagEl);

                // Corner Reticles for authentic YOLO HUD styling
                const cTL = document.createElement('span'); cTL.className = 'yolo-box-corner corner-tl';
                const cTR = document.createElement('span'); cTR.className = 'yolo-box-corner corner-tr';
                const cBL = document.createElement('span'); cBL.className = 'yolo-box-corner corner-bl';
                const cBR = document.createElement('span'); cBR.className = 'yolo-box-corner corner-br';
                boxEl.appendChild(cTL);
                boxEl.appendChild(cTR);
                boxEl.appendChild(cBL);
                boxEl.appendChild(cBR);

                this.overlayLayer.appendChild(boxEl);
            });

            this.filterBoundingBoxes();
        }

        updateInspectionState() {
            const scenario = INSPECTION_SCENARIOS[this.activeScenarioKey];
            if (!scenario) return;

            const defectGraphic = this.root.querySelector('.ins-defect-graphic');
            const defectBoxes = this.root.querySelectorAll('.ins-yolo-box[data-is-defect="true"]');

            if (this.defectInjected) {
                // DEFECT STATE
                if (defectGraphic) defectGraphic.style.display = '';
                defectBoxes.forEach(b => {
                    b.classList.remove('is-hidden');
                    b.classList.add('is-defect');
                    b.classList.remove('is-pass');
                    const tag = b.querySelector('.ins-yolo-box-tag');
                    if (tag) tag.textContent = 'DEFECT: ' + scenario.defectClass + ' · ' + (scenario.defectConfidence * 100).toFixed(1) + '%';
                });

                // Top Status HUD
                if (this.statusPill) {
                    this.statusPill.className = 'ins-yolo-status-pill is-defect d-inline-flex align-items-center gap-2 px-3 py-1 rounded-pill';
                }
                if (this.statusDot) {
                    this.statusDot.className = 'ins-yolo-status-dot is-defect';
                }
                if (this.statusText) {
                    this.statusText.textContent = 'DEFECT DETECTED · REJECT GATE ACTIVATED';
                }

                // Telemetry
                if (this.targetEl) this.targetEl.textContent = scenario.targetCode;
                if (this.bboxEl) this.bboxEl.textContent = (scenario.boxes.find(b => b.isDefect) || {}).coordsText || '[X: 0.50, Y: 0.40, W: 0.18, H: 0.15]';
                if (this.confEl) this.confEl.textContent = (scenario.defectConfidence * 100).toFixed(2) + '%';
                if (this.confEl) this.confEl.className = 'ins-telemetry-conf text-danger fw-bold';
                if (this.actionEl) this.actionEl.textContent = scenario.defectAction;
                if (this.actionEl) this.actionEl.className = 'ins-telemetry-action text-danger fw-bold';

                // Left detail box
                if (this.defectDetailText) {
                    this.defectDetailText.textContent = scenario.defectDescription;
                }
                if (this.defectDetailBox) {
                    this.defectDetailBox.className = 'ins-defect-detail-box p-3 rounded-3 mt-3 border border-danger border-opacity-40 bg-danger bg-opacity-10';
                }

            } else {
                // NOMINAL PASS STATE
                if (defectGraphic) defectGraphic.style.display = 'none';
                defectBoxes.forEach(b => {
                    b.classList.remove('is-defect');
                    b.classList.add('is-pass');
                    const tag = b.querySelector('.ins-yolo-box-tag');
                    if (tag) tag.textContent = 'PASS: ZONE_NOMINAL · 99.8%';
                });

                // Top Status HUD
                if (this.statusPill) {
                    this.statusPill.className = 'ins-yolo-status-pill is-pass d-inline-flex align-items-center gap-2 px-3 py-1 rounded-pill';
                }
                if (this.statusDot) {
                    this.statusDot.className = 'ins-yolo-status-dot is-pass';
                }
                if (this.statusText) {
                    this.statusText.textContent = 'NOMINAL INSPECTION · BATCH ACCEPTED';
                }

                // Telemetry
                if (this.targetEl) this.targetEl.textContent = scenario.targetCode;
                if (this.bboxEl) this.bboxEl.textContent = '[X: 0.00, Y: 0.00, W: 1.00, H: 1.00]';
                if (this.confEl) this.confEl.textContent = '99.85%';
                if (this.confEl) this.confEl.className = 'ins-telemetry-conf text-emerald fw-bold';
                if (this.actionEl) this.actionEl.textContent = scenario.passAction;
                if (this.actionEl) this.actionEl.className = 'ins-telemetry-action text-emerald fw-bold';

                // Left detail box
                if (this.defectDetailText) {
                    this.defectDetailText.textContent = scenario.passDescription;
                }
                if (this.defectDetailBox) {
                    this.defectDetailBox.className = 'ins-defect-detail-box p-3 rounded-3 mt-3 border border-success border-opacity-40 bg-success bg-opacity-10';
                }
            }
        }

        filterBoundingBoxes() {
            const boxes = this.root.querySelectorAll('.ins-yolo-box');
            const threshold = this.confidenceThreshold / 100;

            boxes.forEach(boxEl => {
                const conf = parseFloat(boxEl.getAttribute('data-conf')) || 0.99;
                if (conf < threshold) {
                    boxEl.classList.add('is-below-threshold');
                } else {
                    boxEl.classList.remove('is-below-threshold');
                }
            });
        }

        triggerScan() {
            // Restart laser sweep animation
            if (this.laserBeam) {
                this.laserBeam.classList.remove('is-scanning');
                void this.laserBeam.offsetWidth; // Force reflow
                this.laserBeam.classList.add('is-scanning');
            }

            // Audio chirp
            this.audio.playScanChirp();

            // Simulate micro-jitter on latency
            if (this.latencyEl) {
                const base = parseFloat(INSPECTION_SCENARIOS[this.activeScenarioKey].stats.latency) || 11.4;
                const jitter = (base + (Math.random() * 0.8 - 0.4)).toFixed(1);
                this.latencyEl.textContent = jitter + 'ms';
            }

            // Flash viewport reticle
            const reticle = this.root.querySelector('.ins-yolo-reticle');
            if (reticle) {
                reticle.classList.add('is-pulse');
                setTimeout(() => reticle.classList.remove('is-pulse'), 350);
            }
        }

        destroy() {
            if (this.rafId) {
                cancelAnimationFrame(this.rafId);
                this.rafId = null;
            }
        }
    }

    /**
     * Auto-mount on DOM
     */
    function initInnoriaYoloSimulators() {
        const nodes = document.querySelectorAll('.s_innoria_yolo_inspection');
        nodes.forEach(node => {
            if (!node._yoloSimulator) {
                node._yoloSimulator = new InnoriaYoloInspectionSimulator(node);
            }
        });
    }

    window.InnoriaYoloInspectionSimulator = InnoriaYoloInspectionSimulator;
    window.initInnoriaYoloSimulators = initInnoriaYoloSimulators;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initInnoriaYoloSimulators());
    } else {
        initInnoriaYoloSimulators();
    }

    window.addEventListener('website_snippets_loaded', () => initInnoriaYoloSimulators());
    document.addEventListener('snippet_cloned', () => initInnoriaYoloSimulators());

})();
