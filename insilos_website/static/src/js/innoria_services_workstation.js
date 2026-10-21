/**
 * Innoria High-Precision Engineering Services Workstation
 * File: enterprise/insilos_website/static/src/js/innoria_services_workstation.js
 * 
 * Interactive Controllers:
 * 1) Mode 0: AI as a Service (Neural Pipeline & Live Query Simulator)
 * 2) Mode 1: Digital Transformation (Interactive Before vs After Matrix)
 * 3) Mode 2: Development Services (Cloud-Native Monolith Decomposition & Stress Test)
 * 4) Mode 3: Dedicated ODC & Web3 (Tri-Hub Engineering Grid & Security Matrix)
 */

(function () {
    'use strict';

    function initServicesWorkstation() {
        var section = document.getElementById('innoria_engineering_services');
        if (!section || section.dataset.workstationInitialized === 'true') {
            return;
        }
        section.dataset.workstationInitialized = 'true';

        // Elements
        var rails = section.querySelectorAll('.service-rail-item');
        var sandboxes = section.querySelectorAll('.service-sandbox-pane');
        var telemetryStatus = section.querySelector('#servicesTelemetryStatus');
        var sandboxConciergeBtn = section.querySelector('#sandboxConciergeBtn');

        var currentMode = 0;
        var autoCycleTimer = null;
        var isUserInteracting = false;

        // Telemetry status texts
        var statusTexts = [
            'MODE 01 // NEURAL AI GATEWAY ACTIVE (INFERENCE: 11.4ms)',
            'MODE 02 // CLEAN-CORE DX & VAS TT200 SYNCHRONIZED (ERROR: 0.00%)',
            'MODE 03 // TURNKEY K8S CLUSTER RUNNING (SAP ACTIVATE 5-GATE)',
            'MODE 04 // CO-ENGINEERING SQUAD ENGAGED (TT 13/2020 & ISO 27001)'
        ];

        var conciergeServices = ['ai', 'erp', 'sw_turnkey', 'sw_squad'];
        var conciergePrompts = [
            'Tư vấn tích hợp Dịch Vụ AI & Tác Tử Tự Chủ (Mojo AIaaS, Grounded RAG & IDP)?',
            'Tư vấn Chuyển Đổi Số & Lõi ERP Tự Hành (VAS TT 200 & HĐĐT Nghị định 70/2025/NĐ-CP)?',
            'Tư vấn và dự toán Phát Triển Phần Mềm Trọn Gói (Turnkey Software Package chuẩn SAP Activate 5-Gate)?',
            'Tư vấn cử Đội Ngũ Kỹ Sư Đồng Phát Triển (Co-Engineering Squad chuẩn Thông tư 13/2020/TT-BTTTT)?'
        ];

        function switchMode(index, manual) {
            if (manual) {
                isUserInteracting = true;
                if (autoCycleTimer) {
                    clearInterval(autoCycleTimer);
                    autoCycleTimer = null;
                }
            }

            currentMode = index;

            // Update rails
            rails.forEach(function (rail, i) {
                if (i === index) {
                    rail.classList.add('active');
                } else {
                    rail.classList.remove('active');
                }
            });

            // Update sandbox panes
            sandboxes.forEach(function (pane, i) {
                if (i === index) {
                    pane.classList.add('active');
                } else {
                    pane.classList.remove('active');
                }
            });

            // Update header telemetry bar
            if (telemetryStatus && statusTexts[index]) {
                telemetryStatus.textContent = statusTexts[index];
                telemetryStatus.style.animation = 'none';
                void telemetryStatus.offsetWidth; // trigger reflow
                telemetryStatus.style.animation = 'innoriaHudFadeIn 0.3s ease-out';
            }

            // Update active AI Concierge button attributes
            if (sandboxConciergeBtn) {
                sandboxConciergeBtn.setAttribute('data-concierge-service', conciergeServices[index] || 'ai');
                if (conciergePrompts[index]) {
                    sandboxConciergeBtn.setAttribute('data-concierge-prompt', conciergePrompts[index]);
                }
            }
        }

        // Attach click listeners to rails
        rails.forEach(function (rail, index) {
            rail.addEventListener('click', function (e) {
                e.preventDefault();
                switchMode(index, true);
            });
            rail.addEventListener('mouseenter', function () {
                // Subtle preview on hover if not mobile
                if (window.innerWidth > 991 && !isUserInteracting) {
                    switchMode(index, false);
                }
            });
        });

        // -------------------------------------------------------------
        // SANDBOX 1: AIaaS Interactive Query Simulator
        // -------------------------------------------------------------
        var queryButtons = section.querySelectorAll('.aiaas-query-btn');
        var aiaasJsonOutput = section.querySelector('#aiaasJsonOutput');
        var aiaasLatencyVal = section.querySelector('#aiaasLatencyVal');
        var aiaasTokenVal = section.querySelector('#aiaasTokenVal');
        var aiaasFlowNodes = section.querySelectorAll('.aiaas-flow-node');

        var queryResponses = {
            ocr: {
                latency: '11.8ms',
                tokens: '4,680 tok/s',
                json: '{\n  "service": "AIaaS_Vision_OCR",\n  "status": 200,\n  "confidence": 0.9984,\n  "matched_doc": "VAT_INVOICE_ND70_1C26TAA",\n  "fields_extracted": 28,\n  "validation": "PASS_3_WAY_MATCH"\n}'
            },
            cnc: {
                latency: '14.2ms',
                tokens: '5,210 tok/s',
                json: '{\n  "service": "AI_Agent_MPS_Scheduler",\n  "status": 200,\n  "optimized_stations": 6,\n  "oee_forecast": "96.4%",\n  "lead_time_saving": "42%",\n  "dispatch": "DISPATCH_AUTHORIZED"\n}'
            },
            hse: {
                latency: '9.6ms',
                tokens: '6,100 tok/s',
                json: '{\n  "service": "YOLO_HSE_Stream_Inspector",\n  "status": 200,\n  "camera_fps": 60,\n  "ppe_compliance": "100%",\n  "hazard_detected": false,\n  "alert_level": "NOMINAL_GREEN"\n}'
            }
        };

        if (queryButtons.length > 0) {
            queryButtons.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    queryButtons.forEach(function (b) { b.classList.remove('active'); });
                    btn.classList.add('active');

                    var qType = btn.getAttribute('data-query') || 'ocr';
                    var res = queryResponses[qType] || queryResponses.ocr;

                    // Animate flow nodes
                    aiaasFlowNodes.forEach(function (node, idx) {
                        node.classList.remove('pulse-active');
                        setTimeout(function () {
                            node.classList.add('pulse-active');
                        }, idx * 120);
                    });

                    // Update metrics
                    if (aiaasLatencyVal) aiaasLatencyVal.textContent = res.latency;
                    if (aiaasTokenVal) aiaasTokenVal.textContent = res.tokens;
                    if (aiaasJsonOutput) {
                        aiaasJsonOutput.textContent = res.json;
                        aiaasJsonOutput.classList.remove('flash-glow');
                        void aiaasJsonOutput.offsetWidth;
                        aiaasJsonOutput.classList.add('flash-glow');
                    }
                });
            });
        }

        // -------------------------------------------------------------
        // SANDBOX 2: Digital Transformation Before vs After Toggle
        // -------------------------------------------------------------
        var dxToggleButtons = section.querySelectorAll('.dx-toggle-btn');
        var dxMetricTime = section.querySelector('#dxMetricTime');
        var dxMetricError = section.querySelector('#dxMetricError');
        var dxMetricOpex = section.querySelector('#dxMetricOpex');
        var dxPipelineDiagram = section.querySelector('#dxPipelineDiagram');

        if (dxToggleButtons.length > 0) {
            dxToggleButtons.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    dxToggleButtons.forEach(function (b) { b.classList.remove('active'); });
                    btn.classList.add('active');

                    var state = btn.getAttribute('data-dx-state');
                    if (state === 'legacy') {
                        if (dxMetricTime) dxMetricTime.textContent = '180 Phút / Đơn';
                        if (dxMetricError) dxMetricError.textContent = '4.8% Sai Số Nhập';
                        if (dxMetricOpex) dxMetricOpex.textContent = '125,000,000 đ/tháng';
                        if (dxPipelineDiagram) dxPipelineDiagram.setAttribute('data-state', 'legacy');
                    } else {
                        if (dxMetricTime) dxMetricTime.textContent = '2.8 Giây (Giảm 98.4%)';
                        if (dxMetricError) dxMetricError.textContent = '0.00% (Khử Triệt Để)';
                        if (dxMetricOpex) dxMetricOpex.textContent = '18,500,000 đ (Tiết kiệm 85%)';
                        if (dxPipelineDiagram) dxPipelineDiagram.setAttribute('data-state', 'ai');
                    }
                });
            });
        }

        // -------------------------------------------------------------
        // SANDBOX 3: Cloud-Native K8s Stress Test Simulator
        // -------------------------------------------------------------
        var k8sStressBtn = section.querySelector('#k8sStressBtn');
        var k8sRpsVal = section.querySelector('#k8sRpsVal');
        var k8sLatencyVal = section.querySelector('#k8sLatencyVal');
        var k8sPodGrid = section.querySelector('#k8sPodGrid');
        var k8sStressRunning = false;

        if (k8sStressBtn) {
            k8sStressBtn.addEventListener('click', function () {
                if (k8sStressRunning) return;
                k8sStressRunning = true;
                k8sStressBtn.disabled = true;
                k8sStressBtn.innerHTML = '<span class="spinner-grow spinner-grow-sm me-2 text-cyan"></span>ĐANG PHỤ TẢI 50,000 RPS...';

                if (k8sRpsVal) k8sRpsVal.textContent = '50,000 RPS';
                if (k8sLatencyVal) k8sLatencyVal.textContent = '34ms (P99)';
                if (k8sPodGrid) k8sPodGrid.classList.add('scaled-up');

                setTimeout(function () {
                    k8sStressBtn.disabled = false;
                    k8sStressBtn.innerHTML = '<svg class="ph-bold ph-lightning me-1"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-lightning"/></svg>KÍCH HOẠT PHỤ TẢI ĐỈNH 50,000 RPS';
                    k8sStressRunning = false;
                }, 3500);
            });
        }

        // -------------------------------------------------------------
        // SANDBOX 4: ODC Tri-Hub Engineering Selector
        // -------------------------------------------------------------
        var odcHubButtons = section.querySelectorAll('.odc-hub-btn');
        var odcHeadcountVal = section.querySelector('#odcHeadcountVal');
        var odcFocusVal = section.querySelector('#odcFocusVal');
        var odcLeadVal = section.querySelector('#odcLeadVal');

        var hubData = {
            hanoi: {
                headcount: '45 Senior Engineers & AI Researchers',
                focus: 'Cognitive LLM Fine-Tuning & Computer Vision Lab',
                lead: 'Principal AI Architect (Ph.D in Machine Intelligence)'
            },
            danang: {
                headcount: '60 Cloud-Native & DevOps Specialists',
                focus: 'High-Throughput Microservices & Global Infrastructure',
                lead: 'VP of Infrastructure (Ex-AWS Principal Engineer)'
            },
            hcm: {
                headcount: '55 Enterprise Solution & ERP Consultants',
                focus: 'Enterprise Core ERP, Nghị định 70/2025 (1C26TAA) & Thông tư 13/2020 Compliance',
                lead: 'Chief Solutions Architect (18+ Years Enterprise)'
            }
        };

        if (odcHubButtons.length > 0) {
            odcHubButtons.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    odcHubButtons.forEach(function (b) { b.classList.remove('active'); });
                    btn.classList.add('active');

                    var hub = btn.getAttribute('data-hub') || 'hanoi';
                    var d = hubData[hub] || hubData.hanoi;

                    if (odcHeadcountVal) odcHeadcountVal.textContent = d.headcount;
                    if (odcFocusVal) odcFocusVal.textContent = d.focus;
                    if (odcLeadVal) odcLeadVal.textContent = d.lead;
                });
            });
        }

        // Optional gentle auto-rotation every 9s if user hasn't clicked
        autoCycleTimer = setInterval(function () {
            if (!isUserInteracting && window.innerWidth > 991) {
                var next = (currentMode + 1) % 4;
                switchMode(next, false);
            }
        }, 9000);
    }

    // Initialize on DOMContentLoaded or immediate if ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initServicesWorkstation);
    } else {
        initServicesWorkstation();
    }
})();
