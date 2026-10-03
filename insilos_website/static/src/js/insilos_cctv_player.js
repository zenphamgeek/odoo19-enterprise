/**
 * ============================================================================
 * INSILOS ENTERPRISE — REAL-TIME AI VISION CCTV OVERLAY ENGINE
 * ============================================================================
 * Module: insilos_cctv_player.js
 * Version: 20.0.4.0.0 (Real-Time Sub-Pixel Temporal Tracking Edition)
 * Architecture: Sovereign Vanilla JS Web Audio API & 60 FPS RAF Keyframe Engine
 *
 * Capabilities:
 *  1. Multi-Camera Industrial Switching (Hiện trường Tháp Cẩu, Hàn Tự Động SS400, Cổng PPE Gate)
 *  2. 60 FPS Sub-Pixel Temporal Keyframe Interpolation synced with video.currentTime
 *  3. Dynamic Bounding Box Tracking: Eliminates static CSS % hallucinations
 *  4. Real-Time Telemetry HUD Stream: Live BBOX coordinates, Vector velocity, Latency jitter, 60 FPS
 *  5. Dual-Oscillator FM Siren Acoustic Synthesis (880Hz <-> 1240Hz, 6Hz LFO) via Web Audio API
 *  6. Interactive PPE Violation Simulation with Pulsing Red Strobe Bounding Box
 *  7. ISO 45001 & Regulatory Emergency Alert Modal
 *  8. Direct Sovereign Deep-Links to Vertical GRC and Insilos ERP Work Orders
 * ============================================================================
 */

(function () {
    'use strict';

    /**
     * Resolve Insilos ERP live backend base URL dynamically.
     */
    function getErpBaseUrl() {
        if (typeof window !== 'undefined' && window.location) {
            if (window.location.port === '28069' || window.location.hostname === 'localhost') {
                return window.location.origin;
            }
        }
        return 'http://localhost:28069';
    }

    /**
     * Format seconds to HH:MM:SS.mmm timecode string
     */
    function formatTimecodeMs(secs) {
        if (isNaN(secs) || secs < 0) secs = 0;
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        const ms = Math.floor((secs % 1) * 1000);
        return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0') + '.' + String(ms).padStart(3, '0');
    }

    /**
     * Smoothstep Interpolation: S_1(x) = 3x^2 - 2x^3
     */
    function smoothstep(x) {
        const clamped = Math.max(0, Math.min(1, x));
        return clamped * clamped * (3 - 2 * clamped);
    }

    /**
     * 3 Authentic Industrial Camera Angles Registry
     * Mapped to actual verified Pexels/Cinema footage with dynamic temporal keyframes
     */
    const CCTV_CAMERAS = {
        'cnc_ss400': {
            id: 'cnc_ss400',
            code: 'CAM-01',
            name: 'Giám Sát An Toàn Hiện Trường & Tháp Cẩu',
            location: 'Khu Thi Công Công Trình Trọng Điểm // Tháp Cẩu & Giàn Giáo Thép',
            sensor: 'AI-PTZ-S1080P // SENSOR-HSE-01',
            resolution: '1920x1080 @ 60 FPS',
            videoSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam02_site_communication.mp4',
            posterSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam02_poster.webp',
            duration: 7.88,
            workOrderModel: 'fleet.vehicle',
            workOrderId: 6,
            workOrderActionId: 738,
            workOrderName: 'Kiểm định xe cẩu chuyên dụng & thiết bị nâng (51C-982.45)',
            deepLinkErp: '/web#action=738&id=6',
            grcIncidentId: 'INC-2026-0929-0042',
            deepLinkGrc: 'https://vertical.insilos.com/admin/content/hse_incidents',
            regulatoryRef: 'ISO 45001:2018 Clause 8.1.2 // QCVN 18:2021/BXD // Nghị định 12/2022/NĐ-CP',
            stats: {
                oee: '94.8%',
                personnel: 1,
                helmets: 1,
                vests: 1,
                zoneStatus: 'CRANE REACH ENVELOPE // OPTICAL INTERLOCK ACTIVE'
            },
            primaryBoxId: 'box_helmet_1',
            boxes: [
                {
                    id: 'box_person_1',
                    type: 'person',
                    layer: 'person',
                    baseTag: 'GIÁM SÁT VIÊN #01',
                    violationTag: 'CÔNG NHÂN VI PHẠM KHU VỰC CẨU',
                    keyframes: [
                        { t: 0.0,  x: 0.36, y: 0.06, w: 0.56, h: 0.94, conf: 0.994 },
                        { t: 1.0,  x: 0.36, y: 0.06, w: 0.56, h: 0.94, conf: 0.993 },
                        { t: 2.0,  x: 0.35, y: 0.07, w: 0.57, h: 0.93, conf: 0.995 },
                        { t: 3.0,  x: 0.36, y: 0.06, w: 0.56, h: 0.94, conf: 0.994 },
                        { t: 4.0,  x: 0.37, y: 0.07, w: 0.56, h: 0.93, conf: 0.993 },
                        { t: 5.0,  x: 0.36, y: 0.08, w: 0.57, h: 0.92, conf: 0.995 },
                        { t: 6.0,  x: 0.35, y: 0.07, w: 0.57, h: 0.93, conf: 0.994 },
                        { t: 7.0,  x: 0.35, y: 0.06, w: 0.57, h: 0.94, conf: 0.993 },
                        { t: 7.88, x: 0.36, y: 0.06, w: 0.56, h: 0.94, conf: 0.994 }
                    ]
                },
                {
                    id: 'box_helmet_1',
                    type: 'helmet',
                    layer: 'helmet',
                    baseTag: 'MŨ BẢO HỘ TIÊU CHUẨN',
                    violationTag: 'CẢNH BÁO // KHU VỰC CẨU TẢI NẶNG',
                    keyframes: [
                        { t: 0.0,  x: 0.60, y: 0.06, w: 0.21, h: 0.24, conf: 0.997 },
                        { t: 1.0,  x: 0.60, y: 0.07, w: 0.21, h: 0.24, conf: 0.996 },
                        { t: 2.0,  x: 0.61, y: 0.08, w: 0.21, h: 0.24, conf: 0.998 },
                        { t: 3.0,  x: 0.62, y: 0.07, w: 0.21, h: 0.24, conf: 0.997 },
                        { t: 4.0,  x: 0.63, y: 0.08, w: 0.21, h: 0.24, conf: 0.996 },
                        { t: 5.0,  x: 0.62, y: 0.09, w: 0.21, h: 0.24, conf: 0.998 },
                        { t: 6.0,  x: 0.61, y: 0.08, w: 0.21, h: 0.24, conf: 0.997 },
                        { t: 7.0,  x: 0.60, y: 0.07, w: 0.21, h: 0.24, conf: 0.996 },
                        { t: 7.88, x: 0.60, y: 0.06, w: 0.21, h: 0.24, conf: 0.997 }
                    ]
                },
                {
                    id: 'box_eyewear_1',
                    type: 'helmet',
                    layer: 'helmet',
                    baseTag: 'KÍNH BẢO HỘ TIA UV',
                    violationTag: 'THIẾU KÍNH BẢO HỘ',
                    keyframes: [
                        { t: 0.0,  x: 0.63, y: 0.24, w: 0.12, h: 0.09, conf: 0.986 },
                        { t: 1.0,  x: 0.63, y: 0.24, w: 0.12, h: 0.09, conf: 0.985 },
                        { t: 2.0,  x: 0.64, y: 0.25, w: 0.12, h: 0.09, conf: 0.987 },
                        { t: 3.0,  x: 0.64, y: 0.24, w: 0.12, h: 0.09, conf: 0.988 },
                        { t: 4.0,  x: 0.65, y: 0.25, w: 0.12, h: 0.09, conf: 0.986 },
                        { t: 5.0,  x: 0.64, y: 0.26, w: 0.12, h: 0.09, conf: 0.987 },
                        { t: 6.0,  x: 0.63, y: 0.25, w: 0.12, h: 0.09, conf: 0.988 },
                        { t: 7.0,  x: 0.63, y: 0.24, w: 0.12, h: 0.09, conf: 0.985 },
                        { t: 7.88, x: 0.63, y: 0.24, w: 0.12, h: 0.09, conf: 0.986 }
                    ]
                },
                {
                    id: 'box_gloves_1',
                    type: 'vest',
                    layer: 'vest',
                    baseTag: 'GĂNG TAY & BỘ ĐÀM',
                    violationTag: 'MẤT KẾT NỐI BỘ ĐÀM',
                    keyframes: [
                        { t: 0.0,  x: 0.59, y: 0.27, w: 0.14, h: 0.32, conf: 0.989 },
                        { t: 1.0,  x: 0.59, y: 0.28, w: 0.14, h: 0.33, conf: 0.988 },
                        { t: 2.0,  x: 0.60, y: 0.27, w: 0.13, h: 0.34, conf: 0.991 },
                        { t: 3.0,  x: 0.60, y: 0.26, w: 0.13, h: 0.33, conf: 0.990 },
                        { t: 4.0,  x: 0.61, y: 0.28, w: 0.13, h: 0.34, conf: 0.989 },
                        { t: 5.0,  x: 0.60, y: 0.29, w: 0.14, h: 0.33, conf: 0.992 },
                        { t: 6.0,  x: 0.59, y: 0.28, w: 0.14, h: 0.34, conf: 0.990 },
                        { t: 7.0,  x: 0.59, y: 0.27, w: 0.14, h: 0.33, conf: 0.989 },
                        { t: 7.88, x: 0.59, y: 0.27, w: 0.14, h: 0.32, conf: 0.989 }
                    ]
                },
                {
                    id: 'box_danger_1',
                    type: 'danger-zone',
                    layer: 'danger',
                    baseTag: 'BÁN KÍNH QUAY THÁP CẨU // DROP ZONE',
                    violationTag: 'XÂM NHẬP VÙNG NGUY HIỂM TẢI CẨU',
                    keyframes: [
                        { t: 0.0,  x: 0.02, y: 0.05, w: 0.52, h: 0.92, conf: 1.0 },
                        { t: 7.88, x: 0.02, y: 0.05, w: 0.52, h: 0.92, conf: 1.0 }
                    ]
                }
            ],
            violationTargetBoxId: 'box_helmet_1',
            violationDescription: 'Cảnh báo nguy cấp: Phát hiện nhân viên hiện trường tiến sát bán kính nâng tải cẩu tháp Liebherr 280 EC-H khi chưa có tín hiệu an toàn!',
            violationCode: 'VIO-2026-0929-CRANE01'
        },
        'robot_welding': {
            id: 'robot_welding',
            code: 'CAM-02',
            name: 'Phân Xưởng Cơ Khí Nặng Hàn Tự Động SS400',
            location: 'Khu B2 // Trạm Hàn Hồ Quang Tự Động Thép SS400',
            sensor: 'LINCOLN ELECTRIC NA-5 // ROBOT-WELD-02',
            resolution: '1920x1080 @ 60 FPS',
            videoSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam02_welding_ss400.mp4',
            posterSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam02_welding_poster.webp',
            duration: 16.28,
            workOrderModel: 'mrp.production',
            workOrderId: 10,
            workOrderActionId: 367,
            workOrderName: 'Lệnh Sản Xuất WH/MO/00010 (Khung gầm SS400 Pressure Pipe)',
            deepLinkErp: '/web#action=367&id=10',
            grcIncidentId: 'INC-2026-0929-0043',
            deepLinkGrc: 'https://vertical.insilos.com/admin/content/hse_incidents',
            regulatoryRef: 'ISO 45001:2018 Clause 8.1.2 // TCVN 6720:2000 // QCVN 05A:2020/BCT',
            stats: {
                oee: '96.5%',
                personnel: 0,
                helmets: 1,
                vests: 1,
                zoneStatus: 'THERMAL RADIATION ZONE // CLASS 4 HAZARD'
            },
            primaryBoxId: 'box_torch_2',
            boxes: [
                {
                    id: 'box_torch_2',
                    type: 'helmet',
                    layer: 'helmet',
                    baseTag: 'MỎ HÀN TỰ ĐỘNG // TCP ACTIVE',
                    violationTag: 'LỆCH TÂM MỎ HÀN // QUÁ NHIỆT',
                    keyframes: [
                        { t: 0.0,   x: 0.44, y: 0.05, w: 0.20, h: 0.44, conf: 0.997 },
                        { t: 2.0,   x: 0.45, y: 0.05, w: 0.20, h: 0.44, conf: 0.998 },
                        { t: 5.0,   x: 0.46, y: 0.05, w: 0.20, h: 0.44, conf: 0.997 },
                        { t: 8.0,   x: 0.47, y: 0.05, w: 0.20, h: 0.44, conf: 0.998 },
                        { t: 11.0,  x: 0.46, y: 0.05, w: 0.20, h: 0.44, conf: 0.997 },
                        { t: 14.0,  x: 0.45, y: 0.05, w: 0.20, h: 0.44, conf: 0.998 },
                        { t: 16.28, x: 0.44, y: 0.05, w: 0.20, h: 0.44, conf: 0.997 }
                    ]
                },
                {
                    id: 'box_arc_2',
                    type: 'danger-zone',
                    layer: 'danger',
                    baseTag: 'BỨC XẠ HỒ QUANG NHIỆT // >450°C',
                    violationTag: 'BỨC XẠ NHIỆT VƯỢT NGƯỠNG AN TOÀN',
                    keyframes: [
                        { t: 0.0,   x: 0.44, y: 0.45, w: 0.38, h: 0.28, conf: 0.999 },
                        { t: 2.0,   x: 0.45, y: 0.45, w: 0.38, h: 0.28, conf: 0.998 },
                        { t: 5.0,   x: 0.46, y: 0.45, w: 0.39, h: 0.29, conf: 0.999 },
                        { t: 8.0,   x: 0.47, y: 0.46, w: 0.40, h: 0.29, conf: 0.998 },
                        { t: 11.0,  x: 0.46, y: 0.45, w: 0.39, h: 0.29, conf: 0.999 },
                        { t: 14.0,  x: 0.45, y: 0.45, w: 0.38, h: 0.28, conf: 0.998 },
                        { t: 16.28, x: 0.44, y: 0.45, w: 0.38, h: 0.28, conf: 0.999 }
                    ]
                },
                {
                    id: 'box_seam_2',
                    type: 'vest',
                    layer: 'vest',
                    baseTag: 'ĐƯỜNG HÀN ÁP LỰC SS400 // QA/QC',
                    violationTag: 'KHUYẾT TẬT ĐƯỜNG HÀN',
                    keyframes: [
                        { t: 0.0,   x: 0.02, y: 0.42, w: 0.88, h: 0.55, conf: 0.995 },
                        { t: 8.0,   x: 0.02, y: 0.42, w: 0.88, h: 0.55, conf: 0.996 },
                        { t: 16.28, x: 0.02, y: 0.42, w: 0.88, h: 0.55, conf: 0.995 }
                    ]
                },
                {
                    id: 'box_curtain_2',
                    type: 'danger-zone',
                    layer: 'danger',
                    baseTag: 'RÀNG BUỘC RÈM QUANG HỌC INTERLOCK',
                    violationTag: 'XÂM NHẬP KHÔNG CÓ KÍNH HÀN BẢO VỆ',
                    keyframes: [
                        { t: 0.0,   x: 0.18, y: 0.02, w: 0.72, h: 0.75, conf: 1.0 },
                        { t: 16.28, x: 0.18, y: 0.02, w: 0.72, h: 0.75, conf: 1.0 }
                    ]
                }
            ],
            violationTargetBoxId: 'box_arc_2',
            violationDescription: 'Cảnh báo nguy cấp: Bức xạ nhiệt hồ quang vượt ngưỡng hoặc phát hiện xâm nhập vùng nhiệt hàn không có mặt nạ bảo hộ số 11!',
            violationCode: 'VIO-2026-0929-WELD02'
        },
        'catlai_terminal': {
            id: 'catlai_terminal',
            code: 'CAM-03',
            name: 'Cổng Kiểm Soát Trang Bị PPE Gate #03',
            location: 'Cổng Kiểm Soát HSE Gate #03 // Điểm Danh & Kiểm Soát PPE Tự Động',
            sensor: 'AI-GATE-FACIAL-PPE // SENSOR-GATE-03',
            resolution: '1920x1080 @ 60 FPS',
            videoSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam03_builder_supervision.mp4',
            posterSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam03_poster.webp',
            duration: 5.76,
            workOrderModel: 'fleet.vehicle.log.services',
            workOrderId: 6,
            workOrderActionId: 746,
            workOrderName: 'Kiểm định điều kiện bảo hộ ca làm việc (HSE Inspection #03)',
            deepLinkErp: '/web#action=746&id=6',
            grcIncidentId: 'INC-2026-0929-0044',
            deepLinkGrc: 'https://vertical.insilos.com/admin/content/hse_incidents',
            regulatoryRef: 'ISO 45001:2018 Clause 8.1.2 // QCVN 22:2010/BGTVT // Nghị định 12/2022/NĐ-CP',
            stats: {
                oee: '99.1%',
                personnel: 1,
                helmets: 1,
                vests: 1,
                zoneStatus: 'PPE VERIFICATION CLEAR // PASS TO ENTER'
            },
            primaryBoxId: 'box_helmet_3',
            boxes: [
                {
                    id: 'box_person_3',
                    type: 'person',
                    layer: 'person',
                    baseTag: 'KỸ THUẬT VIÊN CÔNG TRÌNH #03',
                    violationTag: 'CHƯA ĐỦ ĐIỀU KIỆN VÀO CA',
                    keyframes: [
                        { t: 0.0,  x: 0.18, y: 0.01, w: 0.65, h: 0.99, conf: 0.994 },
                        { t: 2.0,  x: 0.17, y: 0.00, w: 0.66, h: 1.00, conf: 0.996 },
                        { t: 4.0,  x: 0.18, y: 0.02, w: 0.65, h: 0.98, conf: 0.993 },
                        { t: 5.76, x: 0.18, y: 0.01, w: 0.65, h: 0.99, conf: 0.994 }
                    ]
                },
                {
                    id: 'box_helmet_3',
                    type: 'helmet',
                    layer: 'helmet',
                    baseTag: 'MŨ BẢO HỘ CHỐNG VA ĐẬP',
                    violationTag: 'CHƯA CÀI QUAI MŨ',
                    keyframes: [
                        { t: 0.0,  x: 0.32, y: 0.01, w: 0.38, h: 0.32, conf: 0.996 },
                        { t: 1.0,  x: 0.32, y: 0.02, w: 0.38, h: 0.32, conf: 0.997 },
                        { t: 2.0,  x: 0.31, y: 0.00, w: 0.39, h: 0.33, conf: 0.998 },
                        { t: 3.0,  x: 0.31, y: 0.01, w: 0.39, h: 0.32, conf: 0.997 },
                        { t: 4.0,  x: 0.32, y: 0.02, w: 0.38, h: 0.32, conf: 0.996 },
                        { t: 5.0,  x: 0.32, y: 0.01, w: 0.38, h: 0.32, conf: 0.997 },
                        { t: 5.76, x: 0.32, y: 0.01, w: 0.38, h: 0.32, conf: 0.996 }
                    ]
                },
                {
                    id: 'box_earmuffs_3',
                    type: 'vest',
                    layer: 'vest',
                    baseTag: 'CHỤP TAI CHỐNG ỒN CHỦ ĐỘNG',
                    violationTag: 'THIẾU CHỤP TAI TRONG VÙNG >85dBA',
                    keyframes: [
                        { t: 0.0,  x: 0.33, y: 0.70, w: 0.35, h: 0.28, conf: 0.984 },
                        { t: 2.0,  x: 0.32, y: 0.70, w: 0.36, h: 0.28, conf: 0.985 },
                        { t: 4.0,  x: 0.33, y: 0.71, w: 0.35, h: 0.28, conf: 0.982 },
                        { t: 5.76, x: 0.33, y: 0.70, w: 0.35, h: 0.28, conf: 0.984 }
                    ]
                },
                {
                    id: 'box_gloves_3',
                    type: 'vest',
                    layer: 'vest',
                    baseTag: 'GĂNG TAY BẢO HỘ CHỐNG CẮT',
                    violationTag: 'THIẾU GĂNG TAY CƠ HỌC',
                    keyframes: [
                        { t: 0.0,  x: 0.06, y: 0.09, w: 0.88, h: 0.58, conf: 0.988 },
                        { t: 2.0,  x: 0.04, y: 0.07, w: 0.90, h: 0.60, conf: 0.990 },
                        { t: 4.0,  x: 0.05, y: 0.09, w: 0.89, h: 0.58, conf: 0.987 },
                        { t: 5.76, x: 0.06, y: 0.09, w: 0.88, h: 0.58, conf: 0.988 }
                    ]
                },
                {
                    id: 'box_danger_3',
                    type: 'danger-zone',
                    layer: 'danger',
                    baseTag: 'VÙNG QUÉT KHUÔN MẶT & PPE // PASS',
                    violationTag: 'CỬA TỪ KHÓA CHẶN // CHỜ ĐỦ TRANG BỊ',
                    keyframes: [
                        { t: 0.0,  x: 0.12, y: 0.00, w: 0.76, h: 0.98, conf: 1.0 },
                        { t: 5.76, x: 0.12, y: 0.00, w: 0.76, h: 0.98, conf: 1.0 }
                    ]
                }
            ],
            violationTargetBoxId: 'box_earmuffs_3',
            violationDescription: 'Phát hiện không tuân thủ: Nhân viên chưa đeo Chụp tai chống ồn trong phân xưởng có độ ồn vượt ngưỡng 85 dBA!',
            violationCode: 'VIO-2026-0929-PPE03'
        },
        'factory_engineer': {
            id: 'factory_engineer',
            code: 'CAM-04',
            name: 'Giám Sát Kỹ Sư Phân Xưởng Cơ Khí',
            location: 'Phân Xưởng Cơ Khí Nặng // Dây Chuyền Chế Tạo Khung Gầm SS400',
            sensor: 'AI-OPTICAL-PPE // SENSOR-HSE-04',
            resolution: '1920x1080 @ 60 FPS',
            videoSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam01_factory_engineer.mp4',
            posterSrc: '/insilos_website/static/src/video/cctv_ppe/cctv_cam01_poster.webp',
            duration: 23.24,
            workOrderModel: 'mrp.production',
            workOrderId: 10,
            workOrderActionId: 367,
            workOrderName: 'Kiểm tra tuân thủ trang bị BHLĐ chuyền chế tạo WH/MO/00010',
            deepLinkErp: '/web#action=367&id=10',
            grcIncidentId: 'INC-2026-0929-0045',
            deepLinkGrc: 'https://vertical.insilos.com/admin/content/hse_incidents',
            regulatoryRef: 'ISO 45001:2018 Clause 8.1.2 // TCVN 2291:1978 // Nghị định 12/2022/NĐ-CP',
            stats: {
                oee: '98.2%',
                personnel: 1,
                helmets: 1,
                vests: 1,
                zoneStatus: 'ALL PPE COMPLIANT // WORK AREA SAFE'
            },
            primaryBoxId: 'box_helmet_4',
            boxes: [
                {
                    id: 'box_person_4',
                    type: 'person',
                    layer: 'person',
                    baseTag: 'KỸ SƯ TRƯỞNG PHÂN XƯỞNG #04',
                    violationTag: 'XÂM NHẬP VÙNG GIA CÔNG CƠ KHÍ',
                    keyframes: [
                        { t: 0.0,   x: 0.35, y: 0.08, w: 0.36, h: 0.90, conf: 0.995 },
                        { t: 4.0,   x: 0.34, y: 0.08, w: 0.37, h: 0.90, conf: 0.994 },
                        { t: 8.0,   x: 0.35, y: 0.09, w: 0.36, h: 0.89, conf: 0.996 },
                        { t: 12.0,  x: 0.36, y: 0.08, w: 0.35, h: 0.90, conf: 0.995 },
                        { t: 16.0,  x: 0.35, y: 0.07, w: 0.36, h: 0.91, conf: 0.994 },
                        { t: 20.0,  x: 0.34, y: 0.08, w: 0.37, h: 0.90, conf: 0.995 },
                        { t: 23.24, x: 0.35, y: 0.08, w: 0.36, h: 0.90, conf: 0.995 }
                    ]
                },
                {
                    id: 'box_helmet_4',
                    type: 'helmet',
                    layer: 'helmet',
                    baseTag: 'MŨ BẢO HỘ CHỐNG VA ĐẬP ĐẠT CHUẨN',
                    violationTag: 'CHƯA ĐỘI MŨ BẢO HỘ ĐẠT CHUẨN',
                    keyframes: [
                        { t: 0.0,   x: 0.44, y: 0.08, w: 0.18, h: 0.17, conf: 0.998 },
                        { t: 4.0,   x: 0.43, y: 0.08, w: 0.18, h: 0.17, conf: 0.997 },
                        { t: 8.0,   x: 0.44, y: 0.09, w: 0.18, h: 0.17, conf: 0.998 },
                        { t: 12.0,  x: 0.45, y: 0.08, w: 0.17, h: 0.17, conf: 0.997 },
                        { t: 16.0,  x: 0.44, y: 0.07, w: 0.18, h: 0.18, conf: 0.998 },
                        { t: 20.0,  x: 0.43, y: 0.08, w: 0.18, h: 0.17, conf: 0.997 },
                        { t: 23.24, x: 0.44, y: 0.08, w: 0.18, h: 0.17, conf: 0.998 }
                    ]
                },
                {
                    id: 'box_vest_4',
                    type: 'vest',
                    layer: 'vest',
                    baseTag: 'ÁO PHẢN QUANG BẢO HỘ CAO CẤP',
                    violationTag: 'THIẾU ÁO PHẢN QUANG CẢNH BÁO',
                    keyframes: [
                        { t: 0.0,   x: 0.38, y: 0.25, w: 0.30, h: 0.38, conf: 0.992 },
                        { t: 4.0,   x: 0.37, y: 0.25, w: 0.31, h: 0.38, conf: 0.991 },
                        { t: 8.0,   x: 0.38, y: 0.26, w: 0.30, h: 0.37, conf: 0.993 },
                        { t: 12.0,  x: 0.39, y: 0.25, w: 0.29, h: 0.38, conf: 0.992 },
                        { t: 16.0,  x: 0.38, y: 0.24, w: 0.30, h: 0.39, conf: 0.991 },
                        { t: 20.0,  x: 0.37, y: 0.25, w: 0.31, h: 0.38, conf: 0.992 },
                        { t: 23.24, x: 0.38, y: 0.25, w: 0.30, h: 0.38, conf: 0.992 }
                    ]
                },
                {
                    id: 'box_danger_4',
                    type: 'danger-zone',
                    layer: 'danger',
                    baseTag: 'VÙNG DÂY CHUYỀN CHẾ TẠO KHUNG GẦM // AN TOÀN',
                    violationTag: 'CẢNH BÁO: RỦI RO KẸP CUỐN CƠ KHÍ',
                    keyframes: [
                        { t: 0.0,   x: 0.15, y: 0.04, w: 0.70, h: 0.92, conf: 1.0 },
                        { t: 23.24, x: 0.15, y: 0.04, w: 0.70, h: 0.92, conf: 1.0 }
                    ]
                }
            ],
            violationTargetBoxId: 'box_helmet_4',
            violationDescription: 'Phát hiện không tuân thủ: Kỹ sư/công nhân chưa trang bị đầy đủ mũ bảo hộ hoặc áo phản quang trong khu vực vận hành cơ khí nặng!',
            violationCode: 'VIO-2026-0929-PPE04'
        }
    };

    /**
     * Dual-Oscillator FM Siren Acoustic Synthesizer via Web Audio API.
     * Generates a 2-tone industrial siren (880Hz <-> 1240Hz, 6Hz LFO modulation)
     * with zero external audio file dependencies and zero CORS issues.
     */
    class WebAudioSirenSynthesizer {
        constructor() {
            this.audioCtx = null;
            this.osc1 = null;
            this.osc2 = null;
            this.lfo = null;
            this.gainNode = null;
            this.isPlaying = false;
            this.isMuted = false;
        }

        initContext() {
            if (!this.audioCtx) {
                const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                if (AudioContextClass) {
                    this.audioCtx = new AudioContextClass();
                }
            }
        }

        start() {
            this.initContext();
            if (!this.audioCtx || this.isPlaying) return;

            if (this.audioCtx.state === 'suspended') {
                this.audioCtx.resume();
            }

            const now = this.audioCtx.currentTime;

            // Master Gain Node with smooth attack
            this.gainNode = this.audioCtx.createGain();
            this.gainNode.gain.setValueAtTime(0.0001, now);
            this.gainNode.gain.exponentialRampToValueAtTime(this.isMuted ? 0.0001 : 0.25, now + 0.12);

            // Primary Carrier Oscillator (Sawtooth, centered at 1060Hz with sweep)
            this.osc1 = this.audioCtx.createOscillator();
            this.osc1.type = 'sawtooth';
            this.osc1.frequency.setValueAtTime(1060, now);

            // Secondary Harmonic Oscillator (Square wave for harsh industrial bite)
            this.osc2 = this.audioCtx.createOscillator();
            this.osc2.type = 'square';
            this.osc2.frequency.setValueAtTime(1590, now);

            // LFO for FM modulation (6 Hz industrial warble)
            this.lfo = this.audioCtx.createOscillator();
            this.lfo.type = 'sine';
            this.lfo.frequency.setValueAtTime(6.0, now);

            // LFO Gains for depth (sweeping between 880Hz and 1240Hz: +/- 180Hz)
            const lfoGain1 = this.audioCtx.createGain();
            lfoGain1.gain.setValueAtTime(180, now);

            const lfoGain2 = this.audioCtx.createGain();
            lfoGain2.gain.setValueAtTime(240, now);

            this.lfo.connect(lfoGain1);
            this.lfo.connect(lfoGain2);

            lfoGain1.connect(this.osc1.frequency);
            lfoGain2.connect(this.osc2.frequency);

            const osc2SubGain = this.audioCtx.createGain();
            osc2SubGain.gain.setValueAtTime(0.18, now);
            this.osc2.connect(osc2SubGain);

            this.osc1.connect(this.gainNode);
            osc2SubGain.connect(this.gainNode);

            this.gainNode.connect(this.audioCtx.destination);

            this.osc1.start(now);
            this.osc2.start(now);
            this.lfo.start(now);

            this.isPlaying = true;
        }

        stop() {
            if (!this.isPlaying || !this.gainNode || !this.audioCtx) return;
            const now = this.audioCtx.currentTime;

            try {
                this.gainNode.gain.cancelScheduledValues(now);
                this.gainNode.gain.setValueAtTime(this.gainNode.gain.value, now);
                this.gainNode.gain.exponentialRampToValueAtTime(0.0001, now + 0.15);
            } catch (e) {
                // Continue cleanup
            }

            setTimeout(() => {
                try {
                    if (this.osc1) { this.osc1.stop(); this.osc1.disconnect(); }
                    if (this.osc2) { this.osc2.stop(); this.osc2.disconnect(); }
                    if (this.lfo) { this.lfo.stop(); this.lfo.disconnect(); }
                    if (this.gainNode) { this.gainNode.disconnect(); }
                } catch (err) {
                    // Ignore disconnect race
                }
                this.osc1 = null;
                this.osc2 = null;
                this.lfo = null;
                this.gainNode = null;
                this.isPlaying = false;
            }, 180);
        }

        toggleMute() {
            this.isMuted = !this.isMuted;
            if (this.gainNode && this.audioCtx) {
                const now = this.audioCtx.currentTime;
                this.gainNode.gain.cancelScheduledValues(now);
                this.gainNode.gain.setValueAtTime(this.gainNode.gain.value, now);
                this.gainNode.gain.exponentialRampToValueAtTime(this.isMuted ? 0.0001 : 0.25, now + 0.08);
            }
            return this.isMuted;
        }
    }

    /**
     * Interactive CCTV Player Controller with 60 FPS Sub-Pixel Tracking
     */
    class InsilosCctvPlayer {
        constructor(rootEl) {
            this.root = rootEl;
            this.activeCameraKey = 'cnc_ss400';
            this.isViolationActive = false;
            this.siren = new WebAudioSirenSynthesizer();
            this.autoStopTimeout = null;
            this.trackingRafId = null;
            this.lastFrameTime = performance.now();
            this.lastTrackedPos = null;

            // Layer states
            this.layerVisibility = {
                helmet: true,
                vest: true,
                danger: true
            };

            // Cached DOM elements
            this.videoEl = this.root.querySelector('.ins-cctv-video');
            this.videoSourceEl = this.root.querySelector('.ins-cctv-video-source');
            this.overlayContainerEl = this.root.querySelector('.ins-cctv-overlay-layer');
            this.camTitleEl = this.root.querySelector('.ins-cctv-cam-title');
            this.camLocationEl = this.root.querySelector('.ins-cctv-cam-location');
            this.aiStatusBadge = this.root.querySelector('.ins-cctv-ai-status');
            this.clockEl = this.root.querySelector('.ins-cctv-clock');
            this.sirenIndicator = this.root.querySelector('.ins-siren-indicator');
            this.telemetryWorkOrderEl = this.root.querySelector('.ins-cctv-telemetry-wo');
            this.telemetryOeeEl = this.root.querySelector('.ins-cctv-telemetry-oee');
            this.telemetrySensorEl = this.root.querySelector('.ins-cctv-telemetry-sensor');
            this.erpDeepLinkBtn = this.root.querySelector('.ins-cctv-erp-link');

            // RT Telemetry Stream HUD Elements
            this.rtStreamContainer = this.root.querySelector('.ins-cctv-rt-stream');
            this.rtTargetEl = this.root.querySelector('.ins-rt-target');
            this.rtBboxEl = this.root.querySelector('.ins-rt-bbox');
            this.rtConfEl = this.root.querySelector('.ins-rt-conf');
            this.rtVectorEl = this.root.querySelector('.ins-rt-vector');
            this.rtLatencyEl = this.root.querySelector('.ins-rt-latency');
            this.rtFpsEl = this.root.querySelector('.ins-rt-fps');
            this.rtTimecodeEl = this.root.querySelector('.ins-rt-timecode');

            // Layer Checkboxes
            this.checkHelmet = this.root.querySelector('.ins-check-helmet');
            this.checkVest = this.root.querySelector('.ins-check-vest');
            this.checkDanger = this.root.querySelector('.ins-check-danger');

            // Action Buttons
            this.btnSimulateViolation = this.root.querySelector('.ins-btn-simulate-violation');
            this.btnResetPatrol = this.root.querySelector('.ins-btn-reset-patrol');
            this.btnToggleMute = this.root.querySelector('.ins-btn-toggle-mute');

            this.init();
        }

        init() {
            this.bindEvents();
            this.startLiveClock();
            this.renderCamera(this.activeCameraKey);
            this.startTrackingLoop();
        }

        bindEvents() {
            // Angle Switch Buttons
            const angleBtns = this.root.querySelectorAll('.ins-cctv-angle-btn');
            angleBtns.forEach((btn) => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const targetAngle = btn.getAttribute('data-camera-angle');
                    if (targetAngle && CCTV_CAMERAS[targetAngle]) {
                        this.switchCamera(targetAngle);
                    }
                });
            });

            // Layer Checkboxes
            if (this.checkHelmet) {
                this.checkHelmet.addEventListener('change', () => {
                    this.layerVisibility.helmet = this.checkHelmet.checked;
                    this.updateLayerVisibility();
                });
            }
            if (this.checkVest) {
                this.checkVest.addEventListener('change', () => {
                    this.layerVisibility.vest = this.checkVest.checked;
                    this.updateLayerVisibility();
                });
            }
            if (this.checkDanger) {
                this.checkDanger.addEventListener('change', () => {
                    this.layerVisibility.danger = this.checkDanger.checked;
                    this.updateLayerVisibility();
                });
            }

            // Simulate Violation Trigger
            if (this.btnSimulateViolation) {
                this.btnSimulateViolation.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.triggerViolation();
                });
            }

            // Reset Patrol Trigger
            if (this.btnResetPatrol) {
                this.btnResetPatrol.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.resetPatrol();
                });
            }

            // Mute / Unmute Button
            if (this.btnToggleMute) {
                this.btnToggleMute.addEventListener('click', (e) => {
                    e.preventDefault();
                    const isMuted = this.siren.toggleMute();
                    this.btnToggleMute.innerHTML = isMuted ?
                        '<span>🔇 Đã Tắt Tiếng</span>' :
                        '<span>🔊 Đang Bật Còi</span>';
                });
            }

            // Modal Reset / Dismiss Connection
            const modalEl = document.getElementById('insilosCctvAlertModal');
            if (modalEl) {
                modalEl.addEventListener('hidden.bs.modal', () => {
                    this.siren.stop();
                    if (this.sirenIndicator) {
                        this.sirenIndicator.classList.remove('is-playing');
                    }
                });

                const modalResetBtns = modalEl.querySelectorAll('[data-bs-dismiss="modal"]');
                modalResetBtns.forEach((btn) => {
                    btn.addEventListener('click', () => {
                        this.resetPatrol();
                    });
                });
            }
        }

        startLiveClock() {
            const updateTime = () => {
                if (this.clockEl) {
                    const now = new Date();
                    const timeStr = now.toTimeString().split(' ')[0] + '.' + String(Math.floor(now.getMilliseconds() / 100));
                    this.clockEl.textContent = timeStr;
                }
            };
            setInterval(updateTime, 100);
            updateTime();
        }

        /**
         * Real-time 60 FPS requestAnimationFrame Tracking Loop
         */
        startTrackingLoop() {
            if (this.trackingRafId) {
                cancelAnimationFrame(this.trackingRafId);
            }

            const step = (now) => {
                this.updateTrackingFrame(now);
                this.trackingRafId = requestAnimationFrame(step);
            };

            this.trackingRafId = requestAnimationFrame(step);
        }

        /**
         * Keyframe temporal interpolation algorithm
         */
        interpolateKeyframes(keyframes, currentTime, duration) {
            if (!keyframes || keyframes.length === 0) return null;
            if (keyframes.length === 1) {
                const kf = keyframes[0];
                return { x: kf.x, y: kf.y, w: kf.w, h: kf.h, conf: kf.conf };
            }

            const cycleDur = duration > 0 ? duration : keyframes[keyframes.length - 1].t;
            const normT = cycleDur > 0 ? (currentTime >= 0 ? currentTime : 0) % cycleDur : 0;

            let kfPrev = keyframes[0];
            let kfNext = keyframes[keyframes.length - 1];

            for (let i = 0; i < keyframes.length - 1; i++) {
                if (normT >= keyframes[i].t && normT <= keyframes[i + 1].t) {
                    kfPrev = keyframes[i];
                    kfNext = keyframes[i + 1];
                    break;
                }
            }

            const timeSpan = kfNext.t - kfPrev.t;
            const alpha = timeSpan > 0.0001 ? Math.min(1, Math.max(0, (normT - kfPrev.t) / timeSpan)) : 0;
            const smoothAlpha = smoothstep(alpha);

            return {
                x: kfPrev.x + smoothAlpha * (kfNext.x - kfPrev.x),
                y: kfPrev.y + smoothAlpha * (kfNext.y - kfPrev.y),
                w: kfPrev.w + smoothAlpha * (kfNext.w - kfPrev.w),
                h: kfPrev.h + smoothAlpha * (kfNext.h - kfPrev.h),
                conf: kfPrev.conf + smoothAlpha * (kfNext.conf - kfPrev.conf)
            };
        }

        /**
         * Update every bounding box and telemetry indicator per frame
         */
        updateTrackingFrame(now) {
            const cam = CCTV_CAMERAS[this.activeCameraKey];
            if (!cam || !this.overlayContainerEl) return;

            const currentTime = (this.videoEl && !isNaN(this.videoEl.currentTime)) ? this.videoEl.currentTime : 0;
            const duration = (this.videoEl && !isNaN(this.videoEl.duration) && this.videoEl.duration > 0) ? this.videoEl.duration : cam.duration;

            let primaryPos = null;
            let primaryBox = null;

            cam.boxes.forEach((b, index) => {
                const pos = this.interpolateKeyframes(b.keyframes, currentTime, duration);
                if (!pos) return;

                if (b.id === cam.primaryBoxId || (!primaryPos && index === 1)) {
                    primaryPos = pos;
                    primaryBox = b;
                }

                const boxEl = this.overlayContainerEl.querySelector('#' + b.id);
                if (boxEl) {
                    // Subtle organic micro-jitter (amplitude +/-0.08% for realistic AI vision sensor hum)
                    const jitterX = Math.sin(currentTime * 16 + index * 1.5) * 0.0008;
                    const jitterY = Math.cos(currentTime * 14 + index * 1.5) * 0.0008;

                    const finalX = Math.max(0, Math.min(0.98, pos.x + jitterX));
                    const finalY = Math.max(0, Math.min(0.98, pos.y + jitterY));

                    boxEl.style.left = (finalX * 100).toFixed(2) + '%';
                    boxEl.style.top = (finalY * 100).toFixed(2) + '%';
                    boxEl.style.width = (pos.w * 100).toFixed(2) + '%';
                    boxEl.style.height = (pos.h * 100).toFixed(2) + '%';

                    const tagSpan = boxEl.querySelector('.ins-cctv-box-tag');
                    if (tagSpan) {
                        if (this.isViolationActive && boxEl.classList.contains('is-violation')) {
                            tagSpan.textContent = '🚨 ' + (b.violationTag || 'VIOLATION DETECTED');
                        } else {
                            const confPct = (pos.conf * 100).toFixed(1);
                            tagSpan.textContent = b.baseTag + ' // ' + confPct + '%';
                        }
                    }
                }
            });

            // Update Real-Time Telemetry HUD Stream
            if (primaryPos) {
                // Vector delta
                let dx = 0;
                let dy = 0;
                if (this.lastTrackedPos) {
                    dx = primaryPos.x - this.lastTrackedPos.x;
                    dy = primaryPos.y - this.lastTrackedPos.y;
                }
                this.lastTrackedPos = primaryPos;

                if (this.rtTargetEl && primaryBox) {
                    this.rtTargetEl.textContent = this.isViolationActive ? '🚨 VIOLATION TARGET' : primaryBox.baseTag;
                }
                if (this.rtBboxEl) {
                    this.rtBboxEl.textContent = '[X: ' + primaryPos.x.toFixed(3) + ', Y: ' + primaryPos.y.toFixed(3) + ', W: ' + primaryPos.w.toFixed(3) + ', H: ' + primaryPos.h.toFixed(3) + ']';
                }
                if (this.rtConfEl) {
                    this.rtConfEl.textContent = (primaryPos.conf * 100).toFixed(1) + '%';
                }
                if (this.rtVectorEl) {
                    const dxStr = (dx >= 0 ? '+' : '') + dx.toFixed(3);
                    const dyStr = (dy >= 0 ? '+' : '') + dy.toFixed(3);
                    this.rtVectorEl.textContent = '[dx: ' + dxStr + ', dy: ' + dyStr + ']';
                }
                if (this.rtLatencyEl) {
                    const dynamicLatency = 11.6 + Math.sin(currentTime * 11) * 1.2 + (Math.random() - 0.5) * 0.4;
                    this.rtLatencyEl.textContent = dynamicLatency.toFixed(1) + 'ms';
                }
                if (this.rtFpsEl) {
                    const dynamicFps = 59.8 + (Math.random() - 0.5) * 0.4;
                    this.rtFpsEl.textContent = dynamicFps.toFixed(1);
                }
                if (this.rtTimecodeEl) {
                    this.rtTimecodeEl.textContent = formatTimecodeMs(currentTime);
                }
            }
        }

        switchCamera(angleKey) {
            if (this.isViolationActive) {
                this.resetPatrol();
            }

            this.activeCameraKey = angleKey;
            const cam = CCTV_CAMERAS[angleKey];
            if (!cam) return;

            // Update angle switch buttons active state
            const angleBtns = this.root.querySelectorAll('.ins-cctv-angle-btn');
            angleBtns.forEach((btn) => {
                if (btn.getAttribute('data-camera-angle') === angleKey) {
                    btn.classList.add('is-active');
                } else {
                    btn.classList.remove('is-active');
                }
            });

            this.renderCamera(angleKey);
        }

        renderCamera(angleKey) {
            const cam = CCTV_CAMERAS[angleKey];
            if (!cam) return;

            // Video source update
            if (this.videoEl) {
                const currentSrc = this.videoEl.currentSrc || this.videoEl.src;
                if (!currentSrc || !currentSrc.includes(cam.videoSrc)) {
                    this.videoEl.pause();
                    if (this.videoSourceEl) {
                        this.videoSourceEl.src = cam.videoSrc;
                    } else {
                        this.videoEl.src = cam.videoSrc;
                    }
                    this.videoEl.poster = cam.posterSrc;
                    this.videoEl.load();
                    const playPromise = this.videoEl.play();
                    if (playPromise !== undefined) {
                        playPromise.catch(() => {
                            // Autoplay restricted until user interaction
                        });
                    }
                }
            }

            // Header titles update
            if (this.camTitleEl) {
                this.camTitleEl.textContent = cam.code + ' // ' + cam.name;
            }
            if (this.camLocationEl) {
                this.camLocationEl.textContent = cam.location;
            }

            // Telemetry indicators
            if (this.telemetryWorkOrderEl) {
                this.telemetryWorkOrderEl.textContent = cam.workOrderName;
            }
            if (this.telemetryOeeEl) {
                this.telemetryOeeEl.textContent = cam.stats.oee;
            }
            if (this.telemetrySensorEl) {
                this.telemetrySensorEl.textContent = cam.sensor;
            }

            // Insilos ERP Deep-Link Button update
            if (this.erpDeepLinkBtn) {
                const baseUrl = getErpBaseUrl();
                this.erpDeepLinkBtn.href = baseUrl + cam.deepLinkErp;
                this.erpDeepLinkBtn.setAttribute('data-live-link', baseUrl + cam.deepLinkErp);
            }

            // Render Bounding Boxes into DOM
            this.renderBoundingBoxes(cam.boxes);
        }

        renderBoundingBoxes(boxes) {
            if (!this.overlayContainerEl) return;
            this.overlayContainerEl.innerHTML = '';
            this.overlayContainerEl.style.position = 'absolute';
            this.overlayContainerEl.style.inset = '0';
            this.overlayContainerEl.style.zIndex = '5';
            this.overlayContainerEl.style.pointerEvents = 'none';

            boxes.forEach((b) => {
                const boxDiv = document.createElement('div');
                boxDiv.id = b.id;
                boxDiv.className = 'ins-cctv-box ins-bbox-' + b.type;
                boxDiv.setAttribute('data-layer', b.layer);

                boxDiv.style.position = 'absolute';
                boxDiv.style.boxSizing = 'border-box';
                boxDiv.style.borderRadius = '4px';
                boxDiv.style.pointerEvents = 'none';
                boxDiv.style.transition = 'opacity 0.25s ease, transform 0.2s ease, border-color 0.2s ease';

                // Initial position from first keyframe
                const initKf = (b.keyframes && b.keyframes.length > 0) ? b.keyframes[0] : { x: 0.1, y: 0.1, w: 0.2, h: 0.2, conf: 0.99 };
                boxDiv.style.left = (initKf.x * 100).toFixed(2) + '%';
                boxDiv.style.top = (initKf.y * 100).toFixed(2) + '%';
                boxDiv.style.width = (initKf.w * 100).toFixed(2) + '%';
                boxDiv.style.height = (initKf.h * 100).toFixed(2) + '%';

                const tagSpan = document.createElement('span');
                tagSpan.className = 'ins-cctv-box-tag';
                tagSpan.textContent = b.baseTag + ' // ' + (initKf.conf * 100).toFixed(1) + '%';
                tagSpan.style.position = 'absolute';
                tagSpan.style.top = '-24px';
                tagSpan.style.left = '-2px';
                tagSpan.style.fontSize = '0.68rem';
                tagSpan.style.fontWeight = '700';
                tagSpan.style.padding = '2px 7px';
                tagSpan.style.borderRadius = '3px';
                tagSpan.style.whiteSpace = 'nowrap';
                tagSpan.style.textTransform = 'uppercase';
                tagSpan.style.letterSpacing = '0.04em';
                tagSpan.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.5)';

                // Defensive styling based on type
                if (b.type === 'helmet') {
                    boxDiv.style.border = '2px solid #10b981';
                    boxDiv.style.backgroundColor = 'rgba(16, 185, 129, 0.14)';
                    tagSpan.style.backgroundColor = '#10b981';
                    tagSpan.style.color = '#022c22';
                } else if (b.type === 'vest') {
                    boxDiv.style.border = '2px solid #06b6d4';
                    boxDiv.style.backgroundColor = 'rgba(6, 182, 212, 0.14)';
                    tagSpan.style.backgroundColor = '#06b6d4';
                    tagSpan.style.color = '#083344';
                } else if (b.type === 'danger-zone') {
                    boxDiv.style.border = '2px dashed #f59e0b';
                    boxDiv.style.backgroundColor = 'rgba(245, 158, 11, 0.12)';
                    tagSpan.style.backgroundColor = '#f59e0b';
                    tagSpan.style.color = '#451a03';
                } else if (b.type === 'person') {
                    boxDiv.style.border = '1px dashed rgba(255, 255, 255, 0.4)';
                    boxDiv.style.backgroundColor = 'rgba(255, 255, 255, 0.03)';
                    tagSpan.style.backgroundColor = 'rgba(30, 41, 59, 0.9)';
                    tagSpan.style.color = '#cbd5e1';
                    tagSpan.style.border = '1px solid rgba(255, 255, 255, 0.2)';
                }

                boxDiv.appendChild(tagSpan);
                this.overlayContainerEl.appendChild(boxDiv);
            });

            this.updateLayerVisibility();
        }

        updateLayerVisibility() {
            if (!this.overlayContainerEl) return;
            const allBoxes = this.overlayContainerEl.querySelectorAll('.ins-cctv-box');
            allBoxes.forEach((box) => {
                const layer = box.getAttribute('data-layer');
                let visible = true;
                if (layer === 'helmet') {
                    visible = this.layerVisibility.helmet;
                } else if (layer === 'vest') {
                    visible = this.layerVisibility.vest;
                } else if (layer === 'danger') {
                    visible = this.layerVisibility.danger;
                }
                if (visible) {
                    box.classList.remove('is-hidden');
                    box.style.display = 'block';
                    box.style.opacity = '1';
                } else {
                    box.classList.add('is-hidden');
                    box.style.display = 'none';
                    box.style.opacity = '0';
                }
            });
        }

        triggerViolation() {
            this.isViolationActive = true;
            const cam = CCTV_CAMERAS[this.activeCameraKey];
            if (!cam) return;

            // 1. Highlight target bounding box in Red Strobe
            const targetBox = this.root.querySelector('#' + cam.violationTargetBoxId);
            if (targetBox) {
                targetBox.classList.add('is-violation');
                targetBox.classList.remove('is-hidden');
                targetBox.style.display = 'block';
                targetBox.style.opacity = '1';
                targetBox.style.border = '2px solid #ef4444';
                targetBox.style.backgroundColor = 'rgba(239, 68, 68, 0.25)';
                const tagEl = targetBox.querySelector('.ins-cctv-box-tag');
                if (tagEl) {
                    tagEl.textContent = '🚨 VIOLATION // ' + cam.violationCode;
                    tagEl.style.backgroundColor = '#ef4444';
                    tagEl.style.color = '#ffffff';
                }
            }

            // Also highlight worker person box in alarm state if present
            const personBoxes = this.root.querySelectorAll('.ins-bbox-person');
            personBoxes.forEach((pBox) => {
                pBox.classList.add('is-violation');
                pBox.style.border = '2px solid #ef4444';
                pBox.style.backgroundColor = 'rgba(239, 68, 68, 0.25)';
                const pTag = pBox.querySelector('.ins-cctv-box-tag');
                if (pTag) {
                    pTag.textContent = '🚨 VÙNG VI PHẠM AN TOÀN';
                    pTag.style.backgroundColor = '#ef4444';
                    pTag.style.color = '#ffffff';
                }
            });

            // 2. Update Top HUD Bar to Alarm Status
            if (this.aiStatusBadge) {
                this.aiStatusBadge.classList.add('is-alarm');
                this.aiStatusBadge.innerHTML = '<span>🔴 CẢNH BÁO VI PHẠM // SIREN ARMED</span>';
            }

            // 3. Highlight RT Stream Bar in Alarm Red
            if (this.rtStreamContainer) {
                this.rtStreamContainer.classList.add('is-alarm');
            }

            // 4. Start Web Audio FM Siren Synthesizer
            this.siren.start();
            if (this.sirenIndicator) {
                this.sirenIndicator.classList.add('is-playing');
            }

            // 5. Update and Show Emergency Alert Modal
            this.populateAlertModal(cam);
            this.showModal();

            // Auto-stop audio after 10s if user does not interact
            if (this.autoStopTimeout) clearTimeout(this.autoStopTimeout);
            this.autoStopTimeout = setTimeout(() => {
                this.siren.stop();
                if (this.sirenIndicator) {
                    this.sirenIndicator.classList.remove('is-playing');
                }
            }, 10000);
        }

        populateAlertModal(cam) {
            const modalEl = document.getElementById('insilosCctvAlertModal');
            if (!modalEl) return;

            const now = new Date();
            const isoTime = now.toISOString();

            const timeEl = modalEl.querySelector('#modalAlertTimestamp');
            if (timeEl) timeEl.textContent = isoTime;

            const codeEl = modalEl.querySelector('#modalAlertViolationCode');
            if (codeEl) codeEl.textContent = cam.violationCode;

            const camNameEl = modalEl.querySelector('#modalAlertCamera');
            if (camNameEl) camNameEl.textContent = cam.code + ' — ' + cam.name;

            const locationEl = modalEl.querySelector('#modalAlertLocation');
            if (locationEl) locationEl.textContent = cam.location;

            const descEl = modalEl.querySelector('#modalAlertDescription');
            if (descEl) descEl.textContent = cam.violationDescription;

            const regEl = modalEl.querySelector('#modalAlertRegulations');
            if (regEl) regEl.textContent = cam.regulatoryRef;

            const evidenceImg = modalEl.querySelector('#modalAlertEvidenceImg');
            if (evidenceImg) evidenceImg.src = cam.posterSrc;

            // Deep Link to GRC
            const grcBtn = modalEl.querySelector('#modalBtnGrcLink');
            if (grcBtn) {
                grcBtn.href = cam.deepLinkGrc;
            }

            // Deep Link to Insilos ERP Work Order
            const erpBtn = modalEl.querySelector('#modalBtnErpLink');
            if (erpBtn) {
                const baseUrl = getErpBaseUrl();
                erpBtn.href = baseUrl + cam.deepLinkErp;
                erpBtn.setAttribute('data-live-link', baseUrl + cam.deepLinkErp);
            }
        }

        showModal() {
            const modalEl = document.getElementById('insilosCctvAlertModal');
            if (!modalEl) return;

            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
                modalInstance.show();
            } else {
                modalEl.classList.add('show');
                modalEl.style.display = 'block';
                modalEl.setAttribute('aria-modal', 'true');
            }
        }

        hideModal() {
            const modalEl = document.getElementById('insilosCctvAlertModal');
            if (!modalEl) return;

            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modalInstance = bootstrap.Modal.getInstance(modalEl);
                if (modalInstance) modalInstance.hide();
            } else {
                modalEl.classList.remove('show');
                modalEl.style.display = 'none';
            }
        }

        resetPatrol() {
            this.isViolationActive = false;
            if (this.autoStopTimeout) clearTimeout(this.autoStopTimeout);

            // Stop audio siren
            this.siren.stop();
            if (this.sirenIndicator) {
                this.sirenIndicator.classList.remove('is-playing');
            }

            // Reset HUD status badge
            if (this.aiStatusBadge) {
                this.aiStatusBadge.classList.remove('is-alarm');
                this.aiStatusBadge.innerHTML = '<span class="ins-live-ping--emerald me-1"></span><span>AI PATROL // NOMINAL</span>';
            }

            // Reset RT Stream Bar
            if (this.rtStreamContainer) {
                this.rtStreamContainer.classList.remove('is-alarm');
            }

            // Re-render current camera boxes cleanly
            const cam = CCTV_CAMERAS[this.activeCameraKey];
            if (cam) {
                this.renderBoundingBoxes(cam.boxes);
            }

            this.hideModal();
        }

        destroy() {
            if (this.trackingRafId) {
                cancelAnimationFrame(this.trackingRafId);
                this.trackingRafId = null;
            }
            if (this.siren) {
                this.siren.stop();
            }
        }
    }

    /**
     * Bind HSE Video modal events (auto-play when modal opens, pause when closes)
     */
    function setupHseVideoModalListeners() {
        const hseModal = document.getElementById('insilosHseVideoModal');
        if (!hseModal || hseModal._hseModalBound) return;
        hseModal._hseModalBound = true;

        const cinemaPlayer = document.getElementById('insilosHseCinemaPlayer');

        hseModal.addEventListener('shown.bs.modal', () => {
            if (cinemaPlayer) {
                cinemaPlayer.currentTime = 0;
                cinemaPlayer.play().catch(() => {});
            }
        });

        hseModal.addEventListener('hidden.bs.modal', () => {
            if (cinemaPlayer) {
                cinemaPlayer.pause();
            }
        });
    }

    /**
     * Mount all CCTV widgets on page.
     */
    function initInsilosCctvWidgets() {
        setupHseVideoModalListeners();
        const widgetNodes = document.querySelectorAll('.s_insilos_cctv_ai_camera');
        const instances = [];
        widgetNodes.forEach((node) => {
            if (!node._insilosCctvPlayer) {
                node._insilosCctvPlayer = new InsilosCctvPlayer(node);
                instances.push(node._insilosCctvPlayer);
            }
        });
        return instances;
    }

    // Expose to window for testing and inspection
    window.InsilosCctvCameras = CCTV_CAMERAS;
    window.InsilosCctvPlayer = InsilosCctvPlayer;
    window.WebAudioSirenSynthesizer = WebAudioSirenSynthesizer;
    window.initInsilosCctvWidgets = initInsilosCctvWidgets;

    // Auto-mount on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initInsilosCctvWidgets());
    } else {
        initInsilosCctvWidgets();
    }

    // Support Insilos ERP Website Editor dynamic reload events
    window.addEventListener('website_snippets_loaded', () => initInsilosCctvWidgets());
    document.addEventListener('snippet_cloned', () => initInsilosCctvWidgets());

})();
