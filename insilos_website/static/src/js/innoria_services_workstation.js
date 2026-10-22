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
            'CHẾ ĐỘ 01 · LUỒNG TÍCH HỢP API, OCR/IDP & RAG THỜI GIAN THỰC',
            'CHẾ ĐỘ 02 · CLEAN-CORE ERP & HẠCH TOÁN VAS TT200 (SAI SỐ: 0.00%)',
            'CHẾ ĐỘ 03 · KUBERNETES CLUSTER & BÀN GIAO TRỌN GÓI 5-GATE',
            'CHẾ ĐỘ 04 · ĐỘI NGŨ KỸ SƯ CHUYÊN TRÁCH (TT 13/2020 & ISO 27001)'
        ];

        var conciergeServices = ['ai', 'erp', 'sw_turnkey', 'sw_squad'];
        var conciergePrompts = [
            'Tư vấn tích hợp Dịch Vụ AI & Tác Tử Tự Chủ (Mojo AIaaS, Grounded RAG & IDP)?',
            'Tư vấn Chuyển Đổi Số & Lõi ERP Tự Hành (VAS TT 200 & HĐĐT Nghị định 70/2025/NĐ-CP)?',
            'Tư vấn và dự toán Phát Triển Phần Mềm Trọn Gói (Turnkey Software Package chuẩn Enterprise Activate 5-Gate)?',
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
        // 4-MODE 3D ISOMETRIC CUTAWAY CAD & SCENARIO CONTROLLER (Modes 01 - 04)
        // -------------------------------------------------------------
        var ANATOMY_META = {
            aiaas_ingest: {
                pane: 0,
                badge: '01 · AIAAS.OAUTH2_INGEST',
                spec: 'Cổng thu thập đa luồng OAuth2/mTLS 1.3 · Nhận HĐĐT XML/PDF 1C26TAA, G-Code CNC & RTSP H.265 (250 MB/s)',
                l1: 'Bus PCIe Gen5 x16 · 64GB/s DMA Ring',
                l2: '24-Core Zero-Copy TLS 1.3 Demuxer',
                l3: 'Thấu kính Sapphire + HUD [250 MB/s]'
            },
            aiaas_ocr_prism: {
                pane: 0,
                badge: '02 · VISIONX.OCR_PRISM',
                spec: 'Bóc tách 28 trường HĐĐT 1C26TAA (NĐ 70/2025) & nhận diện PPE 60FPS · Độ chính xác 99.84%',
                l1: 'Đế tản nhiệt Vapor-Chamber · 8-Ch Tensor',
                l2: 'Lăng kính Quang học + 64×64 FP8 NPU',
                l3: 'Cảm biến Laser Quét 28 Trường HĐĐT'
            },
            aiaas_rag_vector: {
                pane: 0,
                badge: '03 · HYBRID.RAG_HNSW',
                spec: 'Lõi truy xuất kép BM25 Sparse + pgvector HNSW (ef=128) & Cross-Encoder Rerank · 100% trích dẫn nguồn',
                l1: 'Cụm NVMe RAID-0 + HBM3e 1536-dim',
                l2: 'Lưới đồ thị đa diện HNSW (ef=128)',
                l3: 'Vòm hội tụ Cross-Encoder Rerank'
            },
            aiaas_vpc_gate: {
                pane: 0,
                badge: '04 · AIRGAP.VPC_GATE',
                spec: 'Khóa kiểm chứng 3 chiều & cô lập Private VPC · Zero External Data Retention · ACL ISO/IEC 27701',
                l1: ' lồng Faraday Titanium · Optical Diode',
                l2: 'Cổng khóa Enclave 3 chiều PO-GRN-Bill',
                l3: 'Khiên chữ ký số SHA-256 · Zero Leak'
            },
            dx_threeway: {
                pane: 1,
                badge: '01 · DX.3WAY_MANIFOLD',
                spec: 'Cụm van đối soát 3 chiều tự động PO-0842 ⇄ WH/IN/0519 ⇄ Bill INV-88412 · Khớp 100% trong 2.8 giây',
                l1: 'Đế góp 3 đường ống PO · WH/IN · Bill',
                l2: 'Buồng trộn đối chiếu tự động 100% dòng',
                l3: 'Nắp kính đo áp suất sai lệch 0.00%'
            },
            dx_hsm_einvoice: {
                pane: 1,
                badge: '02 · DX.HSM_1C26TAA',
                spec: 'Trạm ký số Cloud HSM & cấp mã CQT thời gian thực (<300ms) chuẩn Nghị định 70/2025/NĐ-CP',
                l1: 'Mạch chống cạy phá FIPS 140-3 Level 3',
                l2: 'Lõi mật mã RSA-4096 / ECDSA P-384',
                l3: 'Vòm niêm phong XML 1C26TAA (<300ms)'
            },
            dx_vas_ledger: {
                pane: 1,
                badge: '03 · DX.VAS_LEDGER',
                spec: 'Bộ vi sai định khoản kép tự động Nợ TK 152/621/1331 ⇄ Có TK 331 · Khóa sổ cân bằng Δ = 0.00 VNĐ',
                l1: 'Khung bánh răng vi sai Nợ ⇄ Có VAS',
                l2: 'Lõi định khoản TT200 & TT99/2025/TT-BTC',
                l3: 'Cầu cân bằng quang học Δ = 0.00 VNĐ'
            },
            dx_payroll_vcb: {
                pane: 1,
                badge: '04 · DX.PAYROLL_VCB',
                spec: 'Lương chuẩn mã đơn vị TZ0857G (BHXH 8%, BHYT 1.5%, BHTN 1%, TNCN 5 bậc) & Ủy nhiệm chi Ngân hàng số Doanh nghiệp',
                l1: 'Đế phân luồng BHXH 8% · BHYT 1.5% · BHTN 1%',
                l2: 'Bộ tính thuế TNCN 5 bậc & mã TZ0857G',
                l3: 'Cổng xuất 11 cột Ngân hàng số Doanh nghiệp (@Text)'
            },
            k8s_envoy_ingress: {
                pane: 2,
                badge: '01 · K8S.ENVOY_INGRESS',
                spec: 'Cổng điều phối Envoy TLS 1.3 Multi-AZ · Cân bằng tải Anycast 12,500 → 50,000 RPS',
                l1: 'Khung Anycast BGP + NIC 100GbE SFP28',
                l2: 'Ma trận L7 Envoy Proxy + eBPF XDP',
                l3: 'Vòm phân kỳ TLS 1.3 (50,000 RPS)'
            },
            k8s_worker_pods: {
                pane: 2,
                badge: '02 · K8S.WORKER_PODS',
                spec: '5 cụm Pod tự động co giãn HPA (auth-iam, order, stock, billing, ai-inference) · Zero-Downtime Rolling Deploy',
                l1: 'Đế Cgroup v2 + Kubelet CRI-O Runtime',
                l2: '5 Phiến Blade Pod (3 → 24 Replicas HPA)',
                l3: 'Màn chắn Istio mTLS + Liveness Probe'
            },
            k8s_kafka_wal: {
                pane: 2,
                badge: '03 · K8S.KAFKA_SHARDING',
                spec: 'Đường trục sự kiện bất đồng bộ Kafka & cụm PostgreSQL Sharding WAL · Packet Loss 0.00%',
                l1: 'Đế NVMe ZFS Mirror + Wal-G Archive',
                l2: '3 Ống dẫn Kafka Partition + PG 16 WAL',
                l3: 'Cầu đồng bộ Raft Consensus (Loss 0%)'
            },
            k8s_five_gate_vault: {
                pane: 2,
                badge: '04 · K8S.5GATE_VAULT',
                spec: 'Khoang bàn giao 5-Gate Enterprise Activate · 100% Source Code + Cổng Tài liệu RBAC + Bảo hành 12 tháng',
                l1: 'Khung két 5-Gate Enterprise Activate (G1→G5)',
                l2: 'Lõi Git Repo + Kho Tài liệu RBAC',
                l3: 'Nắp khóa chứng nhận 100% IP Ownership'
            },
            odc_hanoi_tower: {
                pane: 3,
                badge: '01 · ODC.HANOI_AI_LAB',
                spec: '45 Senior Engineers & AI Researchers · Huấn luyện LLM & Thị giác máy tính · Đồng bộ Git/Jira về /my',
                l1: 'Đế trạm Bắc Bộ · MPLS Dual-Fiber Ring',
                l2: 'Cụm GPU AI/CV Lab + 45 Senior Engineers',
                l3: 'Vòm cầu truyền dẫn Telemetry Hà Nội'
            },
            odc_danang_tower: {
                pane: 3,
                badge: '02 · ODC.DANANG_CLOUD_HUB',
                spec: '60 Chuyên gia Cloud-Native, Kubernetes Multi-AZ & DevOps · Vận hành hạ tầng chịu tải cao 24/7',
                l1: 'Đế trạm Trung Bộ · Trục cáp biển APG/A2A',
                l2: 'Trung tâm K8s Multi-AZ + 60 Cloud Experts',
                l3: 'Đài điều phối SRE 24/7 Đà Nẵng Hub'
            },
            odc_hcm_tower: {
                pane: 3,
                badge: '03 · ODC.HCM_ERP_HUB',
                spec: '55 Chuyên gia ERP Lõi, HĐĐT 1C26TAA (NĐ 70/2025) & Chuẩn 7 công đoạn Thông tư 13/2020/TT-BTTTT',
                l1: 'Đế trạm Nam Bộ · Core FinTech & ERP Backbone',
                l2: '55 Chuyên gia ERP, HĐĐT & TT 13/2020',
                l3: 'Cổng kết nối Ngân hàng & Thuế TP.HCM'
            },
            odc_portal_vault: {
                pane: 3,
                badge: '04 · ODC.PORTAL_CLEANROOM',
                spec: 'Cổng nghiệm thu trực tuyến /my/timesheets & /my/software-portal · Air-Gapped Cleanroom · 100% IP Ownership',
                l1: 'Phòng sạch Air-Gapped ISO/IEC 27001',
                l2: 'Sổ cái đối soát /my/timesheets & Git PR',
                l3: 'Khiên bàn giao 100% Mã nguồn & Sở hữu Trí tuệ'
            }
        };

        var PANE_SEQUENCE_KEYS = {
            0: ['aiaas_ingest', 'aiaas_ocr_prism', 'aiaas_rag_vector', 'aiaas_vpc_gate'],
            1: ['dx_threeway', 'dx_hsm_einvoice', 'dx_vas_ledger', 'dx_payroll_vcb'],
            2: ['k8s_envoy_ingress', 'k8s_worker_pods', 'k8s_kafka_wal', 'k8s_five_gate_vault'],
            3: ['odc_hanoi_tower', 'odc_danang_tower', 'odc_hcm_tower', 'odc_portal_vault']
        };

        var playTimers = {};

        function selectAnatomyPart(paneIdx, partKey) {
            var stage = section.querySelector('#sandboxAnatomyRig' + paneIdx);
            if (!stage) return;
            stage.setAttribute('data-active-part', partKey);

            var explodeBtn = stage.querySelector('.sandbox-explode-btn');
            var isExploded = explodeBtn && explodeBtn.classList.contains('active');

            var nodes = stage.querySelectorAll('.iso-part-node');
            nodes.forEach(function (node) {
                var key = node.getAttribute('data-anatomy-part');
                var isMatch = (key === partKey);
                node.classList.toggle('is-lifted', Boolean(isExploded || isMatch));
                node.classList.toggle('is-highlighted', Boolean(isMatch));
            });

            var pills = stage.querySelectorAll('.sandbox-part-pill');
            pills.forEach(function (pill) {
                pill.classList.toggle('active', pill.getAttribute('data-part-target') === partKey);
            });

            var meta = ANATOMY_META[partKey];
            if (meta) {
                var badgeEl = section.querySelector('#anatomyBadge' + paneIdx);
                var specEl = section.querySelector('#anatomySpec' + paneIdx);
                var l1El = section.querySelector('#anatomyLayer1_' + paneIdx);
                var l2El = section.querySelector('#anatomyLayer2_' + paneIdx);
                var l3El = section.querySelector('#anatomyLayer3_' + paneIdx);
                if (badgeEl) badgeEl.textContent = meta.badge;
                if (specEl) specEl.textContent = meta.spec;
                if (l1El && meta.l1) l1El.textContent = meta.l1;
                if (l2El && meta.l2) l2El.textContent = meta.l2;
                if (l3El && meta.l3) l3El.textContent = meta.l3;
            }
        }

        function stopRigScenario(paneIdx) {
            if (playTimers[paneIdx]) {
                clearInterval(playTimers[paneIdx]);
                playTimers[paneIdx] = null;
            }
            var stage = section.querySelector('#sandboxAnatomyRig' + paneIdx);
            if (!stage) return;
            stage.removeAttribute('data-rig-playing');
            var playBtn = stage.querySelector('.sandbox-play-btn');
            if (playBtn) {
                playBtn.classList.remove('active');
                playBtn.textContent = '▶ KỊCH BẢN';
            }
        }

        // Bind part pills, SVG 3D nodes, X-Ray, Explode, and Scenario Sequencer across all 4 modes
        [0, 1, 2, 3].forEach(function (paneIdx) {
            var stage = section.querySelector('#sandboxAnatomyRig' + paneIdx);
            if (!stage) return;

            stage.querySelectorAll('.sandbox-part-pill').forEach(function (pill) {
                pill.addEventListener('click', function () {
                    stopRigScenario(paneIdx);
                    var target = pill.getAttribute('data-part-target');
                    if (target) selectAnatomyPart(paneIdx, target);
                });
            });

            stage.querySelectorAll('.iso-part-node').forEach(function (node) {
                node.addEventListener('click', function () {
                    stopRigScenario(paneIdx);
                    var partKey = node.getAttribute('data-anatomy-part');
                    if (partKey) selectAnatomyPart(paneIdx, partKey);

                    // Bi-directional sync for Mode 04 Hub towers
                    var hubSync = node.getAttribute('data-hub-sync');
                    if (hubSync && paneIdx === 3) {
                        var hubBtn = section.querySelector('.odc-hub-btn[data-hub="' + hubSync + '"]');
                        if (hubBtn) hubBtn.click();
                    }
                });
            });

            var xrayBtn = stage.querySelector('.sandbox-xray-btn');
            if (xrayBtn) {
                xrayBtn.addEventListener('click', function () {
                    var nowXray = !xrayBtn.classList.contains('active');
                    xrayBtn.classList.toggle('active', nowXray);
                    if (nowXray) {
                        stage.setAttribute('data-rig-xray', 'true');
                    } else {
                        stage.removeAttribute('data-rig-xray');
                    }
                });
            }

            var explodeBtn = stage.querySelector('.sandbox-explode-btn');
            if (explodeBtn) {
                explodeBtn.addEventListener('click', function () {
                    var nowExploded = !explodeBtn.classList.contains('active');
                    explodeBtn.classList.toggle('active', nowExploded);
                    explodeBtn.textContent = nowExploded ? 'THU GỌN 3D' : 'PHÂN RÃ 3D';
                    var activePart = stage.getAttribute('data-active-part') || '';
                    selectAnatomyPart(paneIdx, activePart);
                });
            }

            var playBtn = stage.querySelector('.sandbox-play-btn');
            if (playBtn) {
                playBtn.addEventListener('click', function () {
                    if (playTimers[paneIdx]) {
                        stopRigScenario(paneIdx);
                        return;
                    }
                    var keys = PANE_SEQUENCE_KEYS[paneIdx] || [];
                    if (!keys.length) return;

                    playBtn.classList.add('active');
                    playBtn.textContent = '⏹ DỪNG';
                    stage.setAttribute('data-rig-playing', 'true');

                    // Auto-activate Explode 3D & X-Ray during live scenario playback
                    if (explodeBtn && !explodeBtn.classList.contains('active')) {
                        explodeBtn.classList.add('active');
                        explodeBtn.textContent = 'THU GỌN 3D';
                    }
                    if (xrayBtn && !xrayBtn.classList.contains('active')) {
                        xrayBtn.classList.add('active');
                        stage.setAttribute('data-rig-xray', 'true');
                    }

                    var stepIdx = 0;
                    selectAnatomyPart(paneIdx, keys[stepIdx]);

                    playTimers[paneIdx] = setInterval(function () {
                        stepIdx = (stepIdx + 1) % keys.length;
                        var nextKey = keys[stepIdx];
                        selectAnatomyPart(paneIdx, nextKey);

                        if (paneIdx === 3) {
                            var targetNode = stage.querySelector('.iso-part-node[data-anatomy-part="' + nextKey + '"]');
                            var hubSync = targetNode && targetNode.getAttribute('data-hub-sync');
                            if (hubSync) {
                                var hubBtn = section.querySelector('.odc-hub-btn[data-hub="' + hubSync + '"]');
                                if (hubBtn) hubBtn.click();
                            }
                        }
                    }, 1200);
                });
            }
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
                part: 'aiaas_ocr_prism',
                latency: '11.8ms',
                tokens: '4,680 tok/s',
                json: '{\n  "service": "AIaaS_Vision_OCR",\n  "status": 200,\n  "confidence": 0.9984,\n  "matched_doc": "VAT_INVOICE_ND70_1C26TAA",\n  "fields_extracted": 28,\n  "validation": "PASS_3_WAY_MATCH"\n}'
            },
            cnc: {
                part: 'aiaas_rag_vector',
                latency: '14.2ms',
                tokens: '5,210 tok/s',
                json: '{\n  "service": "AI_Agent_MPS_Scheduler",\n  "status": 200,\n  "optimized_stations": 6,\n  "oee_forecast": "96.4%",\n  "lead_time_saving": "42%",\n  "dispatch": "DISPATCH_AUTHORIZED"\n}'
            },
            hse: {
                part: 'aiaas_vpc_gate',
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

                    if (res.part) {
                        selectAnatomyPart(0, res.part);
                    }

                    // Animate flow nodes if present
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
        var dxSpecLedger = section.querySelector('#dxSpecLedger');
        var dxSpecEinvoice = section.querySelector('#dxSpecEinvoice');
        var dxSpecWms = section.querySelector('#dxSpecWms');
        var dxLedgerPreview = section.querySelector('#dxLedgerPreview');
        var dxPipelineBadge = section.querySelector('#dxPipelineBadge');
        var sandboxAnatomyRig1 = section.querySelector('#sandboxAnatomyRig1');
        var anatomyBadge1 = section.querySelector('#anatomyBadge1');
        var anatomySpec1 = section.querySelector('#anatomySpec1');

        if (dxToggleButtons.length > 0) {
            dxToggleButtons.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    dxToggleButtons.forEach(function (b) { b.classList.remove('active'); });
                    btn.classList.add('active');

                    var state = btn.getAttribute('data-dx-state');
                    if (state === 'legacy') {
                        if (sandboxAnatomyRig1) sandboxAnatomyRig1.setAttribute('data-rig-state', 'legacy');
                        if (anatomyBadge1) anatomyBadge1.textContent = 'CẢNH BÁO · NGHẼN MẠCH THỦ CÔNG';
                        if (anatomySpec1) anatomySpec1.textContent = 'Nhập liệu Excel rời rạc · Lệch đối chiếu PO-Kho-Hóa đơn 4.8% · Chậm khóa sổ 5-7 ngày';
                        if (dxMetricTime) dxMetricTime.textContent = '180 Phút / Đơn';
                        if (dxMetricError) dxMetricError.textContent = '4.8% Sai Số Nhập';
                        if (dxMetricOpex) dxMetricOpex.textContent = '125,000,000 đ/tháng';
                        if (dxPipelineDiagram) dxPipelineDiagram.setAttribute('data-state', 'legacy');
                        if (dxPipelineBadge) {
                            dxPipelineBadge.textContent = 'MANUAL SILO';
                            dxPipelineBadge.className = 'badge bg-warning text-dark';
                        }
                        if (dxSpecLedger) dxSpecLedger.textContent = 'Nhập lại Excel thủ công · Trễ khóa sổ 5-7 ngày cuối tháng';
                        if (dxSpecEinvoice) dxSpecEinvoice.textContent = 'Tra cứu XML rời rạc · Rủi ro lệch MST & ký hiệu hóa đơn';
                        if (dxSpecWms) dxSpecWms.textContent = 'Kiểm đếm giấy · Chênh lệch tồn kho thực tế vs sổ sách > 6%';
                        if (dxLedgerPreview) {
                            dxLedgerPreview.textContent = '{\n  "journal_entry": "MANUAL_EXCEL_IMPORT",\n  "einvoice_symbol": "UNVERIFIED_XML",\n  "three_way_match": "PENDING_MANUAL_CHECK (3-5 DAYS)",\n  "vas_accounts": "WARNING: Unbalanced Draft / Discrepancy Risk"\n}';
                        }
                    } else {
                        if (sandboxAnatomyRig1) sandboxAnatomyRig1.setAttribute('data-rig-state', 'ai');
                        selectAnatomyPart(1, 'dx_vas_ledger');
                        if (dxMetricTime) dxMetricTime.textContent = '2.8 Giây (Giảm 98.4%)';
                        if (dxMetricError) dxMetricError.textContent = '0.00% (Khử Triệt Để)';
                        if (dxMetricOpex) dxMetricOpex.textContent = '18,500,000 đ (Tiết kiệm 85%)';
                        if (dxPipelineDiagram) dxPipelineDiagram.setAttribute('data-state', 'ai');
                        if (dxPipelineBadge) {
                            dxPipelineBadge.textContent = 'AUTONOMOUS';
                            dxPipelineBadge.className = 'badge bg-success text-dark';
                        }
                        if (dxSpecLedger) dxSpecLedger.textContent = 'Tự động kết chuyển Nợ/Có 100% · Độ lệch Δ = 0.00 VNĐ';
                        if (dxSpecEinvoice) dxSpecEinvoice.textContent = 'Ký số HSM 1C26TAA thời gian thực · Truy xuất lô FEFO';
                        if (dxSpecWms) dxSpecWms.textContent = 'Truy xuất lô/Date FEFO · Cảnh báo tồn kho an toàn tự động';
                        if (dxLedgerPreview) {
                            dxLedgerPreview.textContent = '{\n  "journal_entry": "BILL/2026/10/0842",\n  "einvoice_symbol": "1C26TAA",\n  "three_way_match": "PO-0842 == WH/IN/0519 == INV-88412 (100% MATCH)",\n  "vas_accounts": "Dr 152/621/1331 | Cr 331 (Delta: 0.00 VND)"\n}';
                        }
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
        var sandboxAnatomyRig2 = section.querySelector('#sandboxAnatomyRig2');
        var anatomyBadge2 = section.querySelector('#anatomyBadge2');
        var anatomySpec2 = section.querySelector('#anatomySpec2');
        var k8sStressRunning = false;

        if (k8sStressBtn) {
            k8sStressBtn.addEventListener('click', function () {
                if (k8sStressRunning) return;
                k8sStressRunning = true;
                k8sStressBtn.disabled = true;
                k8sStressBtn.innerHTML = '<span class="spinner-grow spinner-grow-sm me-2 text-cyan"></span>ĐANG BUNG TẦNG 3D HPA · 50,000 RPS...';

                if (k8sRpsVal) k8sRpsVal.textContent = '50,000 RPS';
                if (k8sLatencyVal) k8sLatencyVal.textContent = '34ms (P99)';
                if (k8sPodGrid) k8sPodGrid.classList.add('scaled-up');
                if (sandboxAnatomyRig2) sandboxAnatomyRig2.setAttribute('data-rig-burst', 'true');
                if (anatomyBadge2) anatomyBadge2.textContent = 'HPA BURST · 50,000 RPS ACTIVE';
                if (anatomySpec2) anatomySpec2.textContent = 'Tự động nhân bản 5 cụm Pod Microservices · Cân bằng tải Envoy Multi-AZ · Packet Loss 0.00%';

                setTimeout(function () {
                    k8sStressBtn.disabled = false;
                    k8sStressBtn.innerHTML = '<svg class="ph-bold ph-lightning me-1" style="width: 15px; height: 15px;"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-lightning"/></svg>KÍCH HOẠT PHỤ TẢI ĐỈNH 50,000 RPS (BUNG TẦNG 3D HPA)';
                    if (sandboxAnatomyRig2) sandboxAnatomyRig2.removeAttribute('data-rig-burst');
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
                part: 'odc_hanoi_tower',
                headcount: '45 Senior Engineers & AI Researchers',
                focus: 'Cognitive LLM Fine-Tuning & Computer Vision Lab',
                lead: 'Principal AI Architect (Ph.D in Machine Intelligence)'
            },
            danang: {
                part: 'odc_danang_tower',
                headcount: '60 Cloud-Native & DevOps Specialists',
                focus: 'High-Throughput Microservices & Global Infrastructure',
                lead: 'VP of Infrastructure (Ex-AWS Principal Engineer)'
            },
            hcm: {
                part: 'odc_hcm_tower',
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

                    if (d.part) {
                        selectAnatomyPart(3, d.part);
                    }
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
