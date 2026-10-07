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
     * Detailed Industrial Inspection Scenarios Registry (Dual-Mode Architecture)
     * Mode A: Real Industrial CCTV Video Feed (Welding robot cell, Crane heavy lift, PPE Gate)
     * Mode B: Micro-Metrology Synthetic Inspection (PCB SMT, Auto Stamping, Solar Wafer, Weld Seam)
     */
    const INSPECTION_SCENARIOS = {
        'cctv_welding': {
            id: 'cctv_welding',
            mode: 'video',
            name: 'Hàn Robot SS400 (CAM-02)',
            targetCode: 'INSP-WELD-ROBOT-CAM02',
            modelName: 'YOLOv11x-WELD-VISION',
            resolution: '1920x1080 @ 60 FPS // 4K OPTICAL',
            videoSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam02_welding_ss400.mp4',
            posterSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam02_welding_poster.webp',
            duration: 16.28,
            defectClass: 'THERMAL_ARC_RADIATION_CLASS_4',
            defectConfidence: 0.9942,
            defectDescription: 'Bức xạ nhiệt hồ quang vượt ngưỡng hoặc mỏ hàn lệch tâm quỹ đạo SS400.',
            passDescription: 'Quỹ đạo hàn TCP danh định. Độ thấu ngấu 100%. Không phát hiện rỗ khí.',
            defectAction: 'PLC INTERLOCK ENGAGED · CLUSTER FLAG #02',
            passAction: 'ROBOT CELL CLEAR · CONTINUOUS BEAD PASS',
            stats: {
                latency: '11.2ms',
                precision: '99.42%',
                fps: '60.0',
                resolution: '0.015mm'
            },
            boxes: [
                {
                    id: 'weld_v_defect',
                    label: 'DEFECT 99.42%: THERMAL_ARC_RADIATION',
                    conf: 0.9942,
                    isDefect: true,
                    x: 44.0, y: 45.0, w: 38.0, h: 28.0,
                    coordsText: '[X: 0.440, Y: 0.450, W: 0.380, H: 0.280]',
                    keyframes: [
                        { t: 0.0, x: 0.44, y: 0.45, w: 0.38, h: 0.28, conf: 0.994 },
                        { t: 5.0, x: 0.46, y: 0.45, w: 0.39, h: 0.29, conf: 0.995 },
                        { t: 11.0, x: 0.46, y: 0.45, w: 0.39, h: 0.29, conf: 0.994 },
                        { t: 16.28, x: 0.44, y: 0.45, w: 0.38, h: 0.28, conf: 0.994 }
                    ]
                },
                {
                    id: 'weld_v_torch',
                    label: 'PASS: TCP_TORCH_ACTIVE // 99.8%',
                    conf: 0.998,
                    isDefect: false,
                    x: 44.0, y: 5.0, w: 20.0, h: 44.0,
                    coordsText: '[X: 0.440, Y: 0.050, W: 0.200, H: 0.440]',
                    keyframes: [
                        { t: 0.0, x: 0.44, y: 0.05, w: 0.20, h: 0.44, conf: 0.997 },
                        { t: 5.0, x: 0.46, y: 0.05, w: 0.20, h: 0.44, conf: 0.998 },
                        { t: 11.0, x: 0.46, y: 0.05, w: 0.20, h: 0.44, conf: 0.997 },
                        { t: 16.28, x: 0.44, y: 0.05, w: 0.20, h: 0.44, conf: 0.998 }
                    ]
                },
                {
                    id: 'weld_v_seam',
                    label: 'PASS: SS400_PRESSURE_SEAM_QA',
                    conf: 0.995,
                    isDefect: false,
                    x: 2.0, y: 42.0, w: 88.0, h: 55.0,
                    coordsText: '[X: 0.020, Y: 0.420, W: 0.880, H: 0.550]',
                    keyframes: [
                        { t: 0.0, x: 0.02, y: 0.42, w: 0.88, h: 0.55, conf: 0.995 },
                        { t: 16.28, x: 0.02, y: 0.42, w: 0.88, h: 0.55, conf: 0.995 }
                    ]
                }
            ]
        },

        'cctv_crane': {
            id: 'cctv_crane',
            mode: 'video',
            name: 'Tháp Cẩu & Giàn Giáo (CAM-01)',
            targetCode: 'INSP-CRANE-LIFT-CAM02',
            modelName: 'YOLOv11x-SITE-SAFETY',
            resolution: '1920x1080 @ 60 FPS // PTZ OPTICAL',
            videoSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam02_site_communication.mp4',
            posterSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam02_poster.webp',
            duration: 7.88,
            defectClass: 'NO HELMET / RESTRICTED_ZONE_INTRUSION',
            defectConfidence: 0.9942,
            defectDescription: 'Phát hiện nhân sự bước vào bán kính quay cẩu tải nặng khi chưa có tín hiệu an toàn.',
            passDescription: 'Mũ bảo hộ & áo phản quang đầy đủ. Bán kính nâng tải cẩu thông thoáng an toàn.',
            defectAction: 'CÒI HÚ HIỆN TRƯỜNG KÍCH HOẠT · E-STOP ARMED',
            passAction: 'GIẤY PHÉP LÀM VIỆC e-PTW HỢP LỆ · VẬN HÀNH TIẾP',
            stats: {
                latency: '11.2ms',
                precision: '99.42%',
                fps: '60.0',
                resolution: '0.015mm'
            },
            boxes: [
                {
                    id: 'crane_v_helmet',
                    label: 'NO HELMET // DEFECT 99.42%',
                    conf: 0.9942,
                    isDefect: true,
                    x: 60.0, y: 6.0, w: 21.0, h: 24.0,
                    coordsText: '[X: 0.600, Y: 0.060, W: 0.210, H: 0.240]',
                    keyframes: [
                        { t: 0.0, x: 0.60, y: 0.06, w: 0.21, h: 0.24, conf: 0.994 },
                        { t: 3.0, x: 0.62, y: 0.07, w: 0.21, h: 0.24, conf: 0.995 },
                        { t: 5.0, x: 0.62, y: 0.09, w: 0.21, h: 0.24, conf: 0.994 },
                        { t: 7.88, x: 0.60, y: 0.06, w: 0.21, h: 0.24, conf: 0.994 }
                    ]
                },
                {
                    id: 'crane_v_supervisor',
                    label: 'PASS: GIÁM SÁT VIÊN #01',
                    conf: 0.994,
                    isDefect: false,
                    x: 36.0, y: 6.0, w: 56.0, h: 94.0,
                    coordsText: '[X: 0.360, Y: 0.060, W: 0.560, H: 0.940]',
                    keyframes: [
                        { t: 0.0, x: 0.36, y: 0.06, w: 0.56, h: 0.94, conf: 0.994 },
                        { t: 3.0, x: 0.36, y: 0.06, w: 0.56, h: 0.94, conf: 0.994 },
                        { t: 5.0, x: 0.36, y: 0.08, w: 0.57, h: 0.92, conf: 0.995 },
                        { t: 7.88, x: 0.36, y: 0.06, w: 0.56, h: 0.94, conf: 0.994 }
                    ]
                },
                {
                    id: 'crane_v_danger',
                    label: 'PASS: BÁN KÍNH TẢI CẨU AN TOÀN',
                    conf: 1.0,
                    isDefect: false,
                    x: 2.0, y: 5.0, w: 52.0, h: 92.0,
                    coordsText: '[X: 0.020, Y: 0.050, W: 0.520, H: 0.920]',
                    keyframes: [
                        { t: 0.0, x: 0.02, y: 0.05, w: 0.52, h: 0.92, conf: 1.0 },
                        { t: 7.88, x: 0.02, y: 0.05, w: 0.52, h: 0.92, conf: 1.0 }
                    ]
                }
            ]
        },

        'cctv_ppe_gate': {
            id: 'cctv_ppe_gate',
            mode: 'video',
            name: 'Cổng Kiểm Soát PPE Gate (CAM-03)',
            targetCode: 'INSP-PPE-GATE-CAM03',
            modelName: 'YOLOv11x-PPE-GATE',
            resolution: '1920x1080 @ 60 FPS // FACIAL AI',
            videoSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam03_builder_supervision.mp4',
            posterSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam03_poster.webp',
            duration: 5.76,
            defectClass: 'NO HELMET // PPE GATE NON-COMPLIANCE',
            defectConfidence: 0.9942,
            defectDescription: 'Kỹ thuật viên chưa đội hoặc chưa cài quai Mũ bảo hộ khi bước qua cổng quét.',
            passDescription: '100% trang bị BHLĐ (Mũ, Chụp tai, Găng tay) đầy đủ. Cửa từ mở tự động.',
            defectAction: 'KHÓA CỬA TỪ TỰ ĐỘNG · ĐẨY BIÊN BẢN GRC',
            passAction: 'MỞ CỬA TỪ · ĐIỂM DANH CA LÀM VIỆC ERP',
            stats: {
                latency: '11.2ms',
                precision: '99.42%',
                fps: '60.0',
                resolution: '0.015mm'
            },
            boxes: [
                {
                    id: 'gate_v_helmet',
                    label: 'NO HELMET // DEFECT 99.42%',
                    conf: 0.9942,
                    isDefect: true,
                    x: 32.0, y: 1.0, w: 38.0, h: 32.0,
                    coordsText: '[X: 0.320, Y: 0.010, W: 0.380, H: 0.320]',
                    keyframes: [
                        { t: 0.0, x: 0.32, y: 0.01, w: 0.38, h: 0.32, conf: 0.994 },
                        { t: 2.0, x: 0.31, y: 0.00, w: 0.39, h: 0.33, conf: 0.995 },
                        { t: 5.76, x: 0.32, y: 0.01, w: 0.38, h: 0.32, conf: 0.994 }
                    ]
                },
                {
                    id: 'gate_v_person',
                    label: 'PASS: KỸ THUẬT VIÊN #03',
                    conf: 0.996,
                    isDefect: false,
                    x: 18.0, y: 1.0, w: 65.0, h: 99.0,
                    coordsText: '[X: 0.180, Y: 0.010, W: 0.650, H: 0.990]',
                    keyframes: [
                        { t: 0.0, x: 0.18, y: 0.01, w: 0.65, h: 0.99, conf: 0.996 },
                        { t: 5.76, x: 0.18, y: 0.01, w: 0.65, h: 0.99, conf: 0.996 }
                    ]
                },
                {
                    id: 'gate_v_gloves',
                    label: 'PASS: GĂNG TAY CHỐNG CẮT',
                    conf: 0.988,
                    isDefect: false,
                    x: 6.0, y: 9.0, w: 88.0, h: 58.0,
                    coordsText: '[X: 0.060, Y: 0.090, W: 0.880, H: 0.580]',
                    keyframes: [
                        { t: 0.0, x: 0.06, y: 0.09, w: 0.88, h: 0.58, conf: 0.988 },
                        { t: 5.76, x: 0.06, y: 0.09, w: 0.88, h: 0.58, conf: 0.988 }
                    ]
                }
            ]
        },

        'pcb': {
            id: 'pcb',
            mode: 'synthetic',
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
                latency: '11.2ms',
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
            mode: 'synthetic',
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
            mode: 'synthetic',
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
            mode: 'synthetic',
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
     * Dual-Mode Viewport: Mode A (Real Industrial CCTV Video) & Mode B (Micro-Metrology)
     */
    class InnoriaYoloInspectionSimulator {
        constructor(rootEl) {
            this.root = rootEl;
            this.activeScenarioKey = 'cctv_welding';
            this.currentMode = 'video';
            this.defectInjected = true;
            this.confidenceThreshold = 85; // %
            this.audio = new YoloInspectionAudio();
            this.rafId = null;
            this.startTime = performance.now();
            this.renderedBoxes = [];

            this.cacheDomElements();
            this.ensureHudVisualOverlays();
            this.setupModeSwitcher();
            this.bindEvents();
            this.startTelemetryStreamLoop();
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

            // 4-Metric Real-Time Telemetry Stat Bar Elements
            const statBlocks = this.root.querySelectorAll('.col-6.col-sm-3');
            statBlocks.forEach(block => {
                const label = block.querySelector('span');
                const val = block.querySelector('strong');
                if (label && val) {
                    const text = label.textContent.trim().toUpperCase();
                    if (text.includes('INFERENCE')) this.statLatencyEl = val;
                    else if (text.includes('PRECISION')) this.statPrecisionEl = val;
                    else if (text.includes('STREAM')) this.statFpsEl = val;
                    else if (text.includes('OPTICS')) {
                        this.statOpticsEl = val;
                        val.style.color = '#42E6C3';
                    }
                }
            });
        }

        ensureHudVisualOverlays() {
            if (!this.viewport) return;

            // Viewport styling: Deep Obsidian & Liquid Aurora
            this.viewport.style.backgroundColor = '#050811';
            this.viewport.style.border = '1px solid rgba(66, 230, 195, 0.28)';
            this.viewport.style.boxShadow = '0 25px 60px rgba(0, 0, 0, 0.95), 0 0 35px rgba(0, 242, 254, 0.12), inset 0 0 30px rgba(5, 8, 17, 0.8)';

            // Ensure Video Element for Mode A
            this.videoEl = this.viewport.querySelector('.ins-yolo-video');
            if (!this.videoEl) {
                this.videoEl = document.createElement('video');
                this.videoEl.className = 'ins-yolo-video';
                this.videoEl.setAttribute('playsinline', 'playsinline');
                this.videoEl.setAttribute('webkit-playsinline', 'webkit-playsinline');
                this.videoEl.muted = true;
                this.videoEl.defaultMuted = true;
                this.videoEl.loop = true;
                this.videoEl.autoplay = true;
                this.videoEl.preload = 'auto';
                this.videoEl.style.cssText = 'position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 2; display: none; background: #050811;';
                if (this.canvasContainer) {
                    this.viewport.insertBefore(this.videoEl, this.canvasContainer.nextSibling);
                } else {
                    this.viewport.appendChild(this.videoEl);
                }
            }

            // Ensure Optical Calibration Grid Overlay
            this.calibrationGrid = this.viewport.querySelector('.ins-yolo-calibration-grid');
            if (!this.calibrationGrid) {
                this.calibrationGrid = document.createElement('div');
                this.calibrationGrid.className = 'ins-yolo-calibration-grid';
                this.calibrationGrid.style.cssText = 'position: absolute; inset: 0; pointer-events: none; z-index: 3; background-image: radial-gradient(rgba(66, 230, 195, 0.12) 1px, transparent 1px), linear-gradient(rgba(0, 242, 254, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 242, 254, 0.03) 1px, transparent 1px); background-size: 20px 20px, 40px 40px, 40px 40px; opacity: 0.75;';
                this.viewport.appendChild(this.calibrationGrid);
            }

            // Ensure Laser Beam has glowing cyan/mint beam with trailing gradient
            if (this.laserBeam) {
                this.laserBeam.style.background = 'linear-gradient(90deg, transparent 0%, rgba(66, 230, 195, 0.75) 20%, #FFFFFF 50%, rgba(0, 242, 254, 0.85) 80%, transparent 100%)';
                this.laserBeam.style.boxShadow = '0 0 16px rgba(0, 242, 254, 0.95), 0 0 30px rgba(66, 230, 195, 0.85)';
            }

            // Ensure Optical calibration readout in bottom telemetry stream
            const rtStream = this.viewport.querySelector('.ins-yolo-rt-stream');
            if (rtStream) {
                this.rtOpticsEl = rtStream.querySelector('.ins-telemetry-optics');
                if (!this.rtOpticsEl) {
                    const secondRow = rtStream.children[1] || rtStream;
                    const opticsSpan = document.createElement('span');
                    opticsSpan.className = 'd-none d-lg-inline text-secondary';
                    opticsSpan.innerHTML = '<span class="text-secondary">OPTICS: </span><strong class="ins-telemetry-optics" style="color: #42E6C3;">0.015 mm/px</strong>';
                    secondRow.insertBefore(opticsSpan, secondRow.firstChild);
                    this.rtOpticsEl = opticsSpan.querySelector('.ins-telemetry-optics');
                }
            }
        }

        setupModeSwitcher() {
            const scenarioBtnContainer = this.root.querySelector('.d-flex.flex-wrap.gap-2');
            if (!scenarioBtnContainer) return;

            // Check if mode tabs already exist
            let modeTabs = this.root.querySelector('.ins-yolo-mode-tabs');
            if (!modeTabs) {
                modeTabs = document.createElement('div');
                modeTabs.className = 'ins-yolo-mode-tabs d-flex gap-2 mb-3';
                modeTabs.innerHTML = `
                    <button type="button" class="btn btn-sm font-monospace rounded-pill ins-mode-tab-btn" data-mode="video" style="padding: 6px 14px; font-size: 0.76rem; font-weight: 600; letter-spacing: 0.03em; transition: all 0.25s ease;">
                        <span>📹 Chế Độ A: CCTV Hiện Trường</span>
                    </button>
                    <button type="button" class="btn btn-sm font-monospace rounded-pill ins-mode-tab-btn" data-mode="synthetic" style="padding: 6px 14px; font-size: 0.76rem; font-weight: 600; letter-spacing: 0.03em; transition: all 0.25s ease;">
                        <span>🔬 Chế Độ B: Vi Đo Lường SMT</span>
                    </button>
                `;
                scenarioBtnContainer.parentNode.insertBefore(modeTabs, scenarioBtnContainer);
            }

            // Ensure Mode A buttons exist in scenarioBtnContainer
            const existingButtons = Array.from(scenarioBtnContainer.querySelectorAll('[data-inspection-target]'));
            const existingKeys = existingButtons.map(b => b.getAttribute('data-inspection-target'));

            const modeAScenarios = [
                { key: 'cctv_welding', label: 'Hàn Áp Lực SS400 (CAM-02)' },
                { key: 'cctv_crane', label: 'Tháp Cẩu & Giàn Giáo (CAM-01)' },
                { key: 'cctv_ppe_gate', label: 'Cổng Quét PPE Gate (CAM-03)' }
            ];

            modeAScenarios.forEach(sc => {
                if (!existingKeys.includes(sc.key)) {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'btn ins-yolo-scenario-btn';
                    btn.setAttribute('data-inspection-target', sc.key);
                    btn.setAttribute('data-scenario-mode', 'video');
                    btn.innerHTML = `<span>${sc.label}</span>`;
                    scenarioBtnContainer.appendChild(btn);
                }
            });

            // Tag existing synthetic buttons with data-scenario-mode="synthetic"
            existingButtons.forEach(btn => {
                const k = btn.getAttribute('data-inspection-target');
                const sc = INSPECTION_SCENARIOS[k];
                if (sc && sc.mode) {
                    btn.setAttribute('data-scenario-mode', sc.mode);
                } else {
                    btn.setAttribute('data-scenario-mode', 'synthetic');
                }
            });

            // Re-cache scenario buttons
            this.scenarioButtons = this.root.querySelectorAll('[data-inspection-target]');

            // Bind mode tab clicks
            const tabBtns = modeTabs.querySelectorAll('.ins-mode-tab-btn');
            tabBtns.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    e.preventDefault();
                    const mode = tab.getAttribute('data-mode');
                    this.setModeTab(mode, true);
                });
            });

            // Initialize mode tab based on activeScenarioKey
            const currentScenario = INSPECTION_SCENARIOS[this.activeScenarioKey];
            const initialMode = (currentScenario && currentScenario.mode) || 'video';
            this.setModeTab(initialMode, false);
        }

        setModeTab(mode, autoSelectFirst = true) {
            this.currentMode = mode;
            const modeTabs = this.root.querySelectorAll('.ins-mode-tab-btn');
            modeTabs.forEach(tab => {
                const isSelected = tab.getAttribute('data-mode') === mode;
                if (isSelected) {
                    tab.style.background = 'linear-gradient(135deg, rgba(66, 230, 195, 0.25), rgba(0, 242, 254, 0.25))';
                    tab.style.borderColor = 'rgba(66, 230, 195, 0.6)';
                    tab.style.color = '#FFFFFF';
                    tab.style.boxShadow = '0 0 14px rgba(66, 230, 195, 0.35)';
                } else {
                    tab.style.background = 'rgba(15, 23, 42, 0.6)';
                    tab.style.borderColor = 'rgba(255, 255, 255, 0.12)';
                    tab.style.color = '#94A3B8';
                    tab.style.boxShadow = 'none';
                }
            });

            // Show/hide scenario buttons matching mode
            let firstScenarioInMode = null;
            this.scenarioButtons.forEach(btn => {
                const btnMode = btn.getAttribute('data-scenario-mode') || 'synthetic';
                if (btnMode === mode) {
                    btn.style.display = '';
                    if (!firstScenarioInMode) {
                        firstScenarioInMode = btn.getAttribute('data-inspection-target');
                    }
                } else {
                    btn.style.display = 'none';
                }
            });

            if (autoSelectFirst && firstScenarioInMode) {
                this.switchScenario(firstScenarioInMode);
            }
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

        interpolateKeyframes(keyframes, currentTime) {
            if (!keyframes || keyframes.length === 0) return null;
            if (keyframes.length === 1) {
                return {
                    x: keyframes[0].x * 100,
                    y: keyframes[0].y * 100,
                    w: keyframes[0].w * 100,
                    h: keyframes[0].h * 100,
                    conf: keyframes[0].conf || 0.99
                };
            }

            const t = currentTime;
            if (t <= keyframes[0].t) {
                return {
                    x: keyframes[0].x * 100,
                    y: keyframes[0].y * 100,
                    w: keyframes[0].w * 100,
                    h: keyframes[0].h * 100,
                    conf: keyframes[0].conf || 0.99
                };
            }
            const last = keyframes[keyframes.length - 1];
            if (t >= last.t) {
                return {
                    x: last.x * 100,
                    y: last.y * 100,
                    w: last.w * 100,
                    h: last.h * 100,
                    conf: last.conf || 0.99
                };
            }

            let k0 = keyframes[0];
            let k1 = keyframes[1];
            for (let i = 0; i < keyframes.length - 1; i++) {
                if (t >= keyframes[i].t && t <= keyframes[i + 1].t) {
                    k0 = keyframes[i];
                    k1 = keyframes[i + 1];
                    break;
                }
            }

            const dt = k1.t - k0.t;
            if (dt <= 0.0001) {
                return {
                    x: k0.x * 100,
                    y: k0.y * 100,
                    w: k0.w * 100,
                    h: k0.h * 100,
                    conf: k0.conf || 0.99
                };
            }

            const alpha = Math.max(0, Math.min(1, (t - k0.t) / dt));
            const smoothAlpha = alpha * alpha * (3 - 2 * alpha);

            // Natural micro-jitter simulating sensor sub-pixel bounding box tracking
            const jitterX = Math.sin(t * 12.0) * 0.0005;
            const jitterY = Math.cos(t * 14.5) * 0.0005;

            return {
                x: (k0.x + (k1.x - k0.x) * smoothAlpha + jitterX) * 100,
                y: (k0.y + (k1.y - k0.y) * smoothAlpha + jitterY) * 100,
                w: (k0.w + (k1.w - k0.w) * smoothAlpha) * 100,
                h: (k0.h + (k1.h - k0.h) * smoothAlpha) * 100,
                conf: (k0.conf || 0.99) + ((k1.conf || 0.99) - (k0.conf || 0.99)) * smoothAlpha
            };
        }

        startTelemetryStreamLoop() {
            const tick = () => {
                const now = performance.now();
                const elapsed = (now - this.startTime) / 1000;
                const m = Math.floor(elapsed / 60);
                const s = Math.floor(elapsed % 60);
                const ms = Math.floor((elapsed % 1) * 1000);

                // High-precision clock ticker
                if (this.clockEl) {
                    this.clockEl.textContent = 
                        String(m).padStart(2, '0') + ':' + 
                        String(s).padStart(2, '0') + '.' + 
                        String(ms).padStart(3, '0');
                }

                // Dynamic video keyframe tracking
                const scenario = INSPECTION_SCENARIOS[this.activeScenarioKey];
                if (scenario && scenario.mode === 'video' && this.videoEl && !this.videoEl.paused) {
                    const curTime = this.videoEl.currentTime || 0;
                    if (this.renderedBoxes && this.renderedBoxes.length > 0) {
                        this.renderedBoxes.forEach(item => {
                            if (item.box && item.box.keyframes) {
                                const interp = this.interpolateKeyframes(item.box.keyframes, curTime);
                                if (interp) {
                                    item.el.style.left = interp.x.toFixed(2) + '%';
                                    item.el.style.top = interp.y.toFixed(2) + '%';
                                    item.el.style.width = interp.w.toFixed(2) + '%';
                                    item.el.style.height = interp.h.toFixed(2) + '%';
                                    const cText = '[X: ' + (interp.x / 100).toFixed(3) + ', Y: ' + (interp.y / 100).toFixed(3) + ', W: ' + (interp.w / 100).toFixed(3) + ', H: ' + (interp.h / 100).toFixed(3) + ']';
                                    item.el.setAttribute('data-coords', cText);
                                    if (item.box.isDefect && this.defectInjected) {
                                        if (this.bboxEl) this.bboxEl.textContent = cText;
                                        if (this.confEl) this.confEl.textContent = (interp.conf * 100).toFixed(2) + '%';
                                    }
                                }
                            }
                        });
                    }
                }

                // Natural live telemetry stream fluctuations at 60 FPS
                const tSec = elapsed;
                // Latency: 11.2 +- 0.4 ms
                const latencyVal = 11.2 + Math.sin(tSec * 4.2) * 0.3 + (Math.sin(tSec * 11.5) * 0.1);
                const latencyStr = latencyVal.toFixed(1) + 'ms';
                if (this.latencyEl) this.latencyEl.textContent = latencyStr;
                if (this.statLatencyEl) this.statLatencyEl.textContent = latencyStr;

                // Stream FPS: 60.0 +- 0.5 FPS
                const fpsVal = 60.0 + Math.sin(tSec * 2.8) * 0.35 + (Math.sin(tSec * 9.1) * 0.15);
                if (this.fpsEl) this.fpsEl.textContent = fpsVal.toFixed(1);
                if (this.statFpsEl) this.statFpsEl.textContent = fpsVal.toFixed(1) + ' FPS';

                // Precision: 99.42 +- 0.15 %
                const precVal = 99.42 + Math.sin(tSec * 1.5) * 0.1 + (Math.sin(tSec * 5.7) * 0.05);
                if (this.statPrecisionEl) this.statPrecisionEl.textContent = precVal.toFixed(2) + '%';
                if (this.confEl && !this.defectInjected) {
                    this.confEl.textContent = precVal.toFixed(2) + '%';
                }

                // Optical resolution: 0.015 mm/px
                if (this.statOpticsEl) this.statOpticsEl.textContent = '0.015mm';
                if (this.rtOpticsEl) this.rtOpticsEl.textContent = '0.015 mm/px';

                this.rafId = requestAnimationFrame(tick);
            };
            this.rafId = requestAnimationFrame(tick);
        }

        switchScenario(scenarioKey) {
            if (this.activeScenarioKey === scenarioKey) return;
            this.activeScenarioKey = scenarioKey;

            const scenario = INSPECTION_SCENARIOS[scenarioKey];
            if (scenario && scenario.mode && scenario.mode !== this.currentMode) {
                this.setModeTab(scenario.mode, false);
            }

            // Update active button state
            this.scenarioButtons.forEach(btn => {
                const k = btn.getAttribute('data-inspection-target');
                if (k === scenarioKey) {
                    btn.classList.add('is-active');
                    btn.style.background = 'linear-gradient(135deg, rgba(66, 230, 195, 0.25), rgba(0, 242, 254, 0.25))';
                    btn.style.borderColor = 'rgba(66, 230, 195, 0.6)';
                    btn.style.color = '#FFFFFF';
                    btn.style.boxShadow = '0 0 12px rgba(66, 230, 195, 0.3)';
                } else {
                    btn.classList.remove('is-active');
                    btn.style.background = 'rgba(15, 23, 42, 0.6)';
                    btn.style.borderColor = 'rgba(255, 255, 255, 0.12)';
                    btn.style.color = '#94A3B8';
                    btn.style.boxShadow = 'none';
                }
            });

            this.applyScenario(scenarioKey);
            this.triggerScan();
        }

        applyScenario(scenarioKey) {
            const scenario = INSPECTION_SCENARIOS[scenarioKey];
            if (!scenario) return;

            // Handle Dual Mode (Mode A: Real Industrial CCTV Video vs Mode B: Micro-Metrology)
            if (scenario.mode === 'video') {
                if (this.canvasContainer) {
                    this.canvasContainer.style.display = 'none';
                }
                if (this.videoEl) {
                    this.videoEl.style.display = 'block';
                    if (this.videoEl.getAttribute('data-active-src') !== scenario.videoSrc) {
                        this.videoEl.setAttribute('data-active-src', scenario.videoSrc);
                        this.videoEl.src = scenario.videoSrc;
                        if (scenario.posterSrc) {
                            this.videoEl.poster = scenario.posterSrc;
                        }
                        this.videoEl.muted = true;
                        this.videoEl.defaultMuted = true;
                        this.videoEl.playsInline = true;
                        this.videoEl.loop = true;
                        this.videoEl.load();
                        const playPromise = this.videoEl.play();
                        if (playPromise !== undefined) {
                            playPromise.catch(err => {
                                console.warn('[YOLO Simulator] Autoplay prevented:', err);
                            });
                        }
                    }
                }
            } else {
                // Mode B: Synthetic micro-metrology
                if (this.videoEl) {
                    this.videoEl.pause();
                    this.videoEl.style.display = 'none';
                    this.videoEl.removeAttribute('data-active-src');
                }
                if (this.canvasContainer) {
                    this.canvasContainer.style.display = 'block';
                    this.canvasContainer.innerHTML = scenario.svgGraphic || '';
                }
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
            this.renderedBoxes = [];

            (boxes || []).forEach(box => {
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
                this.renderedBoxes.push({ box, el: boxEl });
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
                    this.statusText.textContent = scenario.mode === 'video' ? 'CẢNH BÁO AN TOÀN · E-STOP KÍCH HOẠT' : 'DEFECT DETECTED · REJECT GATE ACTIVATED';
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
                    this.statusText.textContent = scenario.mode === 'video' ? 'GIÁM SÁT AN TOÀN · VẬN HÀNH TIẾP' : 'NOMINAL INSPECTION · BATCH ACCEPTED';
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
                const base = parseFloat((INSPECTION_SCENARIOS[this.activeScenarioKey] && INSPECTION_SCENARIOS[this.activeScenarioKey].stats && INSPECTION_SCENARIOS[this.activeScenarioKey].stats.latency) || 11.2);
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
            if (this.videoEl) {
                this.videoEl.pause();
                this.videoEl.src = '';
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
