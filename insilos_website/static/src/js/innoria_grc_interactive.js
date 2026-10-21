/**
 * INNORIA Governance, Risk & Compliance (GRC) Interactive Engine
 * File: enterprise/insilos_website/static/src/js/innoria_grc_interactive.js
 * 
 * Interactive Suites:
 * 1. Trade Compliance Intelligence (Doc Reconciliation, C/O Management, Chemical Compliance)
 * 2. Operational Compliance Intelligence (Permit to Work & LOTO, Shift Handover Logbook)
 * 3. Logistics Operations Solutions (Forwarder Jobfile & Cost Reconciliation)
 */

(function () {
    'use strict';

    function initTradeComplianceInteractive() {
        var section = document.getElementById('innoria_trade_compliance_interactive');
        if (!section || section.dataset.grcTradeInit === 'true') {
            return;
        }
        section.dataset.grcTradeInit = 'true';

        // Tab Navigation
        var tabBtns = section.querySelectorAll('.grc-trade-tab-btn');
        var tabPanes = section.querySelectorAll('.grc-trade-tab-pane');

        tabBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var targetId = btn.getAttribute('data-target-pane');
                tabBtns.forEach(function (b) { b.classList.remove('active'); });
                tabPanes.forEach(function (p) { p.classList.remove('active'); });

                btn.classList.add('active');
                var activePane = section.querySelector('#' + targetId);
                if (activePane) {
                    activePane.classList.add('active');
                }
            });
        });

        // Sub-Suite 1: Doc Reconciliation Engine
        var runRulesBtn = section.querySelector('#btnRunReconRules');
        var reconStatusBadge = section.querySelector('#reconStatusBadge');
        var reconCounterMatched = section.querySelector('#reconCounterMatched');
        var reconCounterExceptions = section.querySelector('#reconCounterExceptions');
        var reconRows = section.querySelectorAll('.recon-table-row');
        var auditTrailLog = section.querySelector('#reconAuditTrailLog');
        var btnApproveRecon = section.querySelector('#btnApproveRecon');

        if (runRulesBtn) {
            runRulesBtn.addEventListener('click', function () {
                runRulesBtn.disabled = true;
                runRulesBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Đang Đối Chiếu 5 Chứng Từ...';

                setTimeout(function () {
                    runRulesBtn.disabled = false;
                    runRulesBtn.innerHTML = '<svg class="ph-duotone ph-check-circle me-1" width="16" height="16"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-check-circle"/></svg> Đã Kiểm Tra 4/4 Dòng Hàng';
                    
                    reconRows.forEach(function (row) {
                        row.classList.add('scanned');
                    });

                    if (reconStatusBadge) {
                        reconStatusBadge.className = 'badge bg-warning bg-opacity-25 text-warning border border-warning px-3 py-2 fw-semibold';
                        reconStatusBadge.innerHTML = '⚠️ Phát Hiện 2 Ngoại Lệ Cần Thẩm Định';
                    }
                    if (reconCounterMatched) reconCounterMatched.textContent = '2 Dòng Khớp (100%)';
                    if (reconCounterExceptions) reconCounterExceptions.textContent = '2 Ngoại Lệ (UOM & HS Code)';

                    // Append to audit trail
                    if (auditTrailLog) {
                        var now = new Date();
                        var timeStr = now.toISOString().replace('T', ' ').substring(0, 19);
                        var entry = document.createElement('div');
                        entry.className = 'audit-entry p-2 rounded-2 mb-2 bg-dark bg-opacity-50 border border-secondary border-opacity-25 small font-monospace';
                        entry.innerHTML = '<span class="text-info">[' + timeStr + ' UTC]</span> <span class="text-warning">RULE_ENGINE</span>: Scanned 4 line items across PO #PO-8821, INV #IV-9921, PK #PK-04, ECUS #1049281, BL #MSKU8841. Flagged 2 exceptions.';
                        auditTrailLog.prepend(entry);
                    }

                    if (btnApproveRecon) {
                        btnApproveRecon.disabled = false;
                        btnApproveRecon.classList.remove('btn-secondary');
                        btnApproveRecon.classList.add('btn-primary');
                    }
                }, 750);
            });
        }

        if (btnApproveRecon) {
            btnApproveRecon.addEventListener('click', function () {
                var now = new Date();
                var timeStr = now.toISOString().replace('T', ' ').substring(0, 19);
                var hash = 'SHA256:' + Math.random().toString(16).substring(2, 10) + Math.random().toString(16).substring(2, 10);
                
                reconRows.forEach(function (row) {
                    var statusCell = row.querySelector('.recon-status-cell');
                    if (statusCell && row.classList.contains('has-exception')) {
                        statusCell.innerHTML = '<span class="badge bg-success bg-opacity-25 text-success border border-success">Đã Giải Trình &amp; Khóa</span>';
                    }
                });

                if (reconStatusBadge) {
                    reconStatusBadge.className = 'badge bg-success bg-opacity-25 text-success border border-success px-3 py-2 fw-semibold';
                    reconStatusBadge.innerHTML = '✅ Hồ Sơ Khớp &amp; Đã Ký Phê Duyệt';
                }

                if (auditTrailLog) {
                    var entry = document.createElement('div');
                    entry.className = 'audit-entry p-2 rounded-2 mb-2 bg-success bg-opacity-10 border border-success border-opacity-25 small font-monospace';
                    entry.innerHTML = '<span class="text-success">[' + timeStr + ' UTC]</span> <span class="text-success fw-bold">APPROVAL_SEAL</span>: Compliance Lead Nguyen Van Thang signed off with tolerance justification. Immutable Seal: <span class="text-info">' + hash + '</span>';
                    auditTrailLog.prepend(entry);
                }

                btnApproveRecon.disabled = true;
                btnApproveRecon.innerHTML = '✅ Đã Ký Số &amp; Lưu Bằng Chứng';
            });
        }

        // Sub-Suite 1b: Legal Authority Cascade Override Simulation (CSP-compliant event listeners)
        var btnSimulateOverride = section.querySelector('#btnSimulateOverride');
        var btnResetOverride = section.querySelector('#btnResetOverride');
        var cascadeAlertBox = section.querySelector('#cascadeAlertBox');
        var cascadeTierP4 = section.querySelector('#cascadeTierP4');

        if (btnSimulateOverride) {
            btnSimulateOverride.addEventListener('click', function () {
                if (cascadeAlertBox) cascadeAlertBox.classList.remove('d-none');
                if (cascadeTierP4) cascadeTierP4.classList.add('border-danger', 'bg-danger', 'bg-opacity-10');
                if (auditTrailLog) {
                    var now = new Date();
                    var timeStr = now.toISOString().replace('T', ' ').substring(0, 19);
                    var entry = document.createElement('div');
                    entry.className = 'audit-entry p-2 rounded-2 mb-2 bg-danger bg-opacity-25 border border-danger small font-monospace text-danger';
                    entry.innerHTML = '[' + timeStr + ' UTC] <strong>SECURITY INVARIANT BREACH</strong>: P4/P5 Tax Override Rejected. HS 7219.33.00 (3.2%) cannot override Statutory Decree P1 HS 7219.34 (12%). Flagged for Compliance Officer review.';
                    auditTrailLog.appendChild(entry);
                }
                btnSimulateOverride.classList.add('d-none');
                if (btnResetOverride) btnResetOverride.classList.remove('d-none');
            });
        }

        if (btnResetOverride) {
            btnResetOverride.addEventListener('click', function () {
                if (cascadeAlertBox) cascadeAlertBox.classList.add('d-none');
                if (cascadeTierP4) cascadeTierP4.classList.remove('border-danger', 'bg-danger', 'bg-opacity-10');
                btnResetOverride.classList.add('d-none');
                if (btnSimulateOverride) btnSimulateOverride.classList.remove('d-none');
            });
        }

        // Sub-Suite 2: C/O Management Calculator
        var rvcFobInput = section.querySelector('#coRvcFob');
        var rvcVnmInput = section.querySelector('#coRvcVnm');
        var rvcResultVal = section.querySelector('#coRvcResultVal');
        var rvcStatusBadge = section.querySelector('#coRvcStatusBadge');
        var coFormPreviewModal = section.querySelector('#coFormPreviewModal');
        var btnToggleCoPreview = section.querySelector('#btnToggleCoPreview');

        function updateRvcCalc() {
            if (!rvcFobInput || !rvcVnmInput || !rvcResultVal || !rvcStatusBadge) return;
            var fob = parseFloat(rvcFobInput.value) || 0;
            var vnm = parseFloat(rvcVnmInput.value) || 0;
            if (fob <= 0) return;

            var rvc = ((fob - vnm) / fob) * 100;
            rvc = Math.max(0, Math.min(100, rvc));
            rvcResultVal.textContent = rvc.toFixed(2) + '%';

            if (rvc >= 40.0) {
                rvcStatusBadge.className = 'badge bg-success bg-opacity-25 text-success border border-success px-3 py-2 fw-semibold';
                rvcStatusBadge.innerHTML = '✅ ĐẠT TIÊU CHÍ RVC (≥ 40%) — Hợp Lệ C/O Form D / E';
            } else {
                rvcStatusBadge.className = 'badge bg-danger bg-opacity-25 text-danger border border-danger px-3 py-2 fw-semibold';
                rvcStatusBadge.innerHTML = '❌ KHÔNG ĐẠT RVC (&lt; 40%) — Không Được Hưởng Ưu Đãi';
            }
        }

        if (rvcFobInput && rvcVnmInput) {
            rvcFobInput.addEventListener('input', updateRvcCalc);
            rvcVnmInput.addEventListener('input', updateRvcCalc);
        }

        if (btnToggleCoPreview && coFormPreviewModal) {
            btnToggleCoPreview.addEventListener('click', function () {
                var isHidden = coFormPreviewModal.classList.contains('d-none');
                if (isHidden) {
                    coFormPreviewModal.classList.remove('d-none');
                    btnToggleCoPreview.textContent = 'Đóng Xem Trước Dữ Liệu C/O';
                } else {
                    coFormPreviewModal.classList.add('d-none');
                    btnToggleCoPreview.textContent = 'Xem Dự Thảo Biểu Mẫu C/O & Khấu Trừ BOM';
                }
            });
        }

        // Sub-Suite 3: Chemical Trade Compliance Filter
        var chemSearchInput = section.querySelector('#chemSearchInput');
        var chemFilterSelect = section.querySelector('#chemFilterSelect');
        var chemRows = section.querySelectorAll('.chem-data-row');
        var btnExportChemDossier = section.querySelector('#btnExportChemDossier');
        var chemAlertBox = section.querySelector('#chemExportAlert');

        function filterChemRows() {
            var query = (chemSearchInput ? chemSearchInput.value : '').toLowerCase().trim();
            var category = chemFilterSelect ? chemFilterSelect.value : 'all';

            chemRows.forEach(function (row) {
                var rowText = row.textContent.toLowerCase();
                var rowCat = row.getAttribute('data-chem-category') || '';

                var matchQuery = !query || rowText.indexOf(query) !== -1;
                var matchCat = category === 'all' || rowCat === category;

                if (matchQuery && matchCat) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        if (chemSearchInput) chemSearchInput.addEventListener('input', filterChemRows);
        if (chemFilterSelect) chemFilterSelect.addEventListener('change', filterChemRows);

        if (btnExportChemDossier && chemAlertBox) {
            btnExportChemDossier.addEventListener('click', function () {
                chemAlertBox.classList.remove('d-none');
                chemAlertBox.innerHTML = '<strong>[ĐÃ XUẤT DATASET HỒ SƠ]</strong> Tổng hợp thành công 3 mã hóa chất theo quy định Nghị định 113 &amp; Tiền chất công nghiệp. File XML đã sẵn sàng đồng bộ Cổng Thông Tin Một Cửa Quốc Gia.';
                setTimeout(function () {
                    chemAlertBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 100);
            });
        }

        // Sub-Suite 4: Legal Authority Cascade & Tax Override Simulator (SEC-02 Remediated)
        var btnSimulateOverride = section.querySelector('#btnSimulateOverride, .js_simulate_override');
        var btnResetOverride = section.querySelector('#btnResetOverride, .js_reset_override');

        if (btnSimulateOverride) {
            btnSimulateOverride.addEventListener('click', function () {
                var alertSel = btnSimulateOverride.getAttribute('data-target-alert') || '#cascadeAlertBox';
                var tierSel = btnSimulateOverride.getAttribute('data-target-tier') || '#cascadeTierP4';
                var logSel = btnSimulateOverride.getAttribute('data-target-log') || '#reconAuditTrailLog';

                var alertBox = section.querySelector(alertSel) || document.querySelector(alertSel);
                var tierP4 = section.querySelector(tierSel) || document.querySelector(tierSel);
                var auditLog = section.querySelector(logSel) || document.querySelector(logSel);

                if (alertBox) {
                    alertBox.classList.remove('d-none');
                }
                if (tierP4) {
                    tierP4.classList.add('border-danger', 'bg-danger', 'bg-opacity-10');
                }
                if (auditLog) {
                    var entry = document.createElement('div');
                    entry.className = 'audit-entry p-2 rounded-2 mb-2 bg-danger bg-opacity-25 border border-danger small font-monospace text-danger';
                    entry.innerHTML = '[2026-10-10 08:00:22 UTC] <strong>SECURITY INVARIANT BREACH</strong>: P4/P5 Tax Override Rejected. HS 7219.33.00 (3.2%) cannot override Statutory Decree P1 HS 7219.34 (12%). Flagged for Compliance Officer review.';
                    auditLog.appendChild(entry);
                }

                btnSimulateOverride.classList.add('d-none');
                if (btnResetOverride) {
                    btnResetOverride.classList.remove('d-none');
                }
            });
        }

        if (btnResetOverride) {
            btnResetOverride.addEventListener('click', function () {
                var alertSel = btnResetOverride.getAttribute('data-target-alert') || '#cascadeAlertBox';
                var tierSel = btnResetOverride.getAttribute('data-target-tier') || '#cascadeTierP4';

                var alertBox = section.querySelector(alertSel) || document.querySelector(alertSel);
                var tierP4 = section.querySelector(tierSel) || document.querySelector(tierSel);

                if (alertBox) {
                    alertBox.classList.add('d-none');
                }
                if (tierP4) {
                    tierP4.classList.remove('border-danger', 'bg-danger', 'bg-opacity-10');
                }

                btnResetOverride.classList.add('d-none');
                if (btnSimulateOverride) {
                    btnSimulateOverride.classList.remove('d-none');
                }
            });
        }
    }

    function initOperationalComplianceInteractive() {
        var section = document.getElementById('innoria_operational_compliance_interactive');
        if (!section || section.dataset.grcOpsInit === 'true') {
            return;
        }
        section.dataset.grcOpsInit = 'true';

        // Tab Navigation
        var tabBtns = section.querySelectorAll('.grc-ops-tab-btn');
        var tabPanes = section.querySelectorAll('.grc-ops-tab-pane');

        tabBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var targetId = btn.getAttribute('data-target-pane');
                tabBtns.forEach(function (b) { b.classList.remove('active'); });
                tabPanes.forEach(function (p) { p.classList.remove('active'); });

                btn.classList.add('active');
                var activePane = section.querySelector('#' + targetId);
                if (activePane) {
                    activePane.classList.add('active');
                }
            });
        });

        // PTW & LOTO Isolation Points & SVG Topology Sync
        var lotoPoints = section.querySelectorAll('.loto-point-item');
        var ptwGasStatus = section.querySelector('#ptwGasStatus');
        var ptwStatusBanner = section.querySelector('#ptwStatusBanner');
        var btnSignPtw = section.querySelector('#btnSignPtw');
        var ptwCountdownBadge = section.querySelector('#ptwCountdownBadge');
        var ptwBilateralStamps = section.querySelector('#ptwBilateralStamps');

        // SVG & 3D HUD Circuit Topology Elements
        var lineFeeder4 = section.querySelector('#lineFeeder4');
        var svgNode4 = section.querySelector('#svgNode4');
        var svgNode4Rect = section.querySelector('#svgNode4Rect');
        var svgNode4Title = section.querySelector('#svgNode4Title');
        var svgNode4Sub = section.querySelector('#svgNode4Sub');
        var labelFeeder4Source = section.querySelector('#labelFeeder4Source');
        var hudNode4 = section.querySelector('#hudNode4');
        var hudFeeder4Source = section.querySelector('#hudFeeder4Source');
        var hudNode4Title = section.querySelector('#hudNode4Title');
        var hudNode4Sub = section.querySelector('#hudNode4Sub');
        var vesselStatusFrame = section.querySelector('#vesselStatusFrame');
        var vesselHazardWarning = section.querySelector('#vesselHazardWarning');
        var topologyOverallStatus = section.querySelector('#topologyOverallStatus');
        var gasValLel = section.querySelector('#gasValLel');
        var gasValPress = section.querySelector('#gasValPress');
        var loto3dCanvas = section.querySelector('#loto3dCanvas');
        var camModeBtns = section.querySelectorAll('.loto-3d-cam-btn');

        var ptwCountdownTimer = null;
        var loto3dState = {
            point4Locked: false,
            yaw: 0.48,
            pitch: 0.36,
            targetYaw: 0.48,
            targetPitch: 0.36,
            xrayMode: false,
            dragging: false,
            lastX: 0,
            lastY: 0,
            tick: 0,
            valve4ScreenPos: { x: 0, y: 0, r: 28 }
        };

        function updateSvgTopologyState(point4Locked) {
            loto3dState.point4Locked = !!point4Locked;
            if (point4Locked) {
                if (lineFeeder4) {
                    lineFeeder4.classList.remove('feeder-hazard-pulse');
                    lineFeeder4.classList.add('feeder-isolated-safe');
                    lineFeeder4.setAttribute('stroke', '#10B981');
                    lineFeeder4.removeAttribute('filter');
                }
                if (svgNode4Rect) {
                    svgNode4Rect.setAttribute('fill', '#064E3B');
                    svgNode4Rect.setAttribute('stroke', '#10B981');
                    svgNode4Rect.removeAttribute('filter');
                }
                if (svgNode4Title) {
                    svgNode4Title.textContent = '🔒 [LOCKED] V-109 (L-8824)';
                    svgNode4Title.setAttribute('fill', '#A7F3D0');
                }
                if (svgNode4Sub) {
                    svgNode4Sub.textContent = 'Khí Trơ N2: ĐÃ KHÓA CÔ LẬP';
                    svgNode4Sub.setAttribute('fill', '#6EE7B7');
                }
                if (labelFeeder4Source) {
                    labelFeeder4Source.textContent = 'KHÍ TRƠ N2 ĐÃ CÔ LẬP KHÓA HÃM';
                    labelFeeder4Source.setAttribute('fill', '#10B981');
                }
                if (hudNode4) {
                    hudNode4.classList.remove('is-hazard-interactive');
                    hudNode4.classList.add('is-safe-locked');
                }
                if (hudFeeder4Source) {
                    hudFeeder4Source.textContent = 'KHÍ TRƠ N2 ĐÃ CÔ LẬP KHÓA HÃM';
                    hudFeeder4Source.style.color = '#6EE7B7';
                }
                if (hudNode4Title) {
                    hudNode4Title.className = 'hud-lock-pill is-safe';
                    hudNode4Title.textContent = '🔒 [LOCKED] V-109 (#L-8824)';
                }
                if (hudNode4Sub) {
                    hudNode4Sub.textContent = 'Van Khí Trơ N2: Đã Khóa An Toàn';
                    hudNode4Sub.style.color = '#6EE7B7';
                }
                if (vesselStatusFrame) {
                    vesselStatusFrame.setAttribute('stroke', '#10B981');
                }
                if (vesselHazardWarning) {
                    vesselHazardWarning.textContent = '🛡️ ZERO ENERGY VERIFIED';
                    vesselHazardWarning.setAttribute('fill', '#34D399');
                }
                if (topologyOverallStatus) {
                    topologyOverallStatus.className = 'badge px-2 py-1';
                    topologyOverallStatus.style.background = 'rgba(16, 185, 129, 0.2)';
                    topologyOverallStatus.style.color = '#6EE7B7';
                    topologyOverallStatus.style.border = '1px solid #10B981';
                    topologyOverallStatus.textContent = '4/4 ĐÃ CÔ LẬP · AN TOÀN';
                }
                if (gasValLel) {
                    gasValLel.textContent = '0.0% LEL';
                    gasValLel.className = 'fw-bold text-success';
                }
                if (gasValPress) {
                    gasValPress.textContent = '0.00 bar';
                    gasValPress.className = 'fw-bold text-success';
                }
            } else {
                if (lineFeeder4) {
                    lineFeeder4.classList.remove('feeder-isolated-safe');
                    lineFeeder4.classList.add('feeder-hazard-pulse');
                    lineFeeder4.setAttribute('stroke', '#EF4444');
                    lineFeeder4.setAttribute('filter', 'url(#glowHazard)');
                }
                if (svgNode4Rect) {
                    svgNode4Rect.setAttribute('fill', '#7F1D1D');
                    svgNode4Rect.setAttribute('stroke', '#EF4444');
                    svgNode4Rect.setAttribute('filter', 'url(#glowHazard)');
                }
                if (svgNode4Title) {
                    svgNode4Title.textContent = '⚠️ V-109 (CHƯA KHÓA)';
                    svgNode4Title.setAttribute('fill', '#FDA4AF');
                }
                if (svgNode4Sub) {
                    svgNode4Sub.textContent = 'Bấm Để Gắn Khóa LOTO';
                    svgNode4Sub.setAttribute('fill', '#FCA5A5');
                }
                if (labelFeeder4Source) {
                    labelFeeder4Source.textContent = 'KHÍ TRƠ N2 ÁP SUẤT CAO 10 BAR';
                    labelFeeder4Source.setAttribute('fill', '#EF4444');
                }
                if (hudNode4) {
                    hudNode4.classList.remove('is-safe-locked');
                    hudNode4.classList.add('is-hazard-interactive');
                }
                if (hudFeeder4Source) {
                    hudFeeder4Source.textContent = 'KHÍ TRƠ N2 ÁP SUẤT CAO 10 BAR';
                    hudFeeder4Source.style.color = '#FDA4AF';
                }
                if (hudNode4Title) {
                    hudNode4Title.className = 'hud-lock-pill is-hazard';
                    hudNode4Title.textContent = '⚠️ V-109 (CHƯA KHÓA)';
                }
                if (hudNode4Sub) {
                    hudNode4Sub.textContent = 'Bấm Để Gắn Khóa LOTO #L-8824';
                    hudNode4Sub.style.color = '#FCA5A5';
                }
                if (vesselStatusFrame) {
                    vesselStatusFrame.setAttribute('stroke', '#EF4444');
                }
                if (vesselHazardWarning) {
                    vesselHazardWarning.textContent = '⛔ CÒN NĂNG LƯỢNG N2';
                    vesselHazardWarning.setAttribute('fill', '#EF4444');
                }
                if (topologyOverallStatus) {
                    topologyOverallStatus.className = 'badge px-2 py-1';
                    topologyOverallStatus.style.background = 'rgba(239, 68, 68, 0.2)';
                    topologyOverallStatus.style.color = '#FDA4AF';
                    topologyOverallStatus.style.border = '1px solid #EF4444';
                    topologyOverallStatus.textContent = '3/4 CÔ LẬP · CÒN NGUY HIỂM';
                }
                if (gasValLel) {
                    gasValLel.textContent = '1.4% LEL';
                    gasValLel.className = 'fw-bold text-warning';
                }
                if (gasValPress) {
                    gasValPress.textContent = '0.35 bar';
                    gasValPress.className = 'fw-bold text-danger';
                }
            }
        }

        function checkLotoCompletion() {
            var allLocked = true;
            var pt4Locked = false;
            lotoPoints.forEach(function (pt) {
                var pId = pt.getAttribute('data-point-id');
                var isLock = pt.getAttribute('data-locked') === 'true';
                if (!isLock) {
                    allLocked = false;
                }
                if (pId === '4' && isLock) {
                    pt4Locked = true;
                }
            });

            updateSvgTopologyState(pt4Locked);

            if (allLocked) {
                if (ptwGasStatus) {
                    ptwGasStatus.className = 'badge bg-success bg-opacity-25 text-success border border-success px-3 py-2 fw-semibold';
                    ptwGasStatus.innerHTML = '✅ Khí An Toàn (O2: 20.9%, LEL: 0.0%, H2S: 0ppm) — Đủ Điều Kiện Cấp Phép';
                }
                if (btnSignPtw) {
                    btnSignPtw.disabled = false;
                    btnSignPtw.classList.remove('btn-secondary');
                    btnSignPtw.classList.add('btn-primary');
                }
                if (ptwStatusBanner) {
                    ptwStatusBanner.className = 'alert alert-info border border-info border-opacity-50 p-3 rounded-3 mb-3';
                    ptwStatusBanner.innerHTML = '<strong>ĐÃ CÔ LẬP 4/4 NGUỒN NĂNG LƯỢNG (LOTO VERIFIED):</strong> Tất cả van và cầu dao đã khóa thẻ an toàn. Người phê duyệt có thể ký duyệt số để kích hoạt giấy phép làm việc.';
                }
            } else {
                if (ptwGasStatus) {
                    ptwGasStatus.className = 'badge bg-warning bg-opacity-25 text-warning border border-warning px-3 py-2 fw-semibold';
                    ptwGasStatus.innerHTML = '⚠️ Đang Chờ Cô Lập Điểm LOTO Số 04';
                }
                if (btnSignPtw) {
                    btnSignPtw.disabled = true;
                    btnSignPtw.classList.remove('btn-primary');
                    btnSignPtw.classList.add('btn-secondary');
                }
                if (ptwStatusBanner) {
                    ptwStatusBanner.className = 'alert alert-warning border border-warning border-opacity-50 p-3 rounded-3 mb-3';
                    ptwStatusBanner.innerHTML = '<strong>YÊU CẦU AN TOÀN BẮT BUỘC:</strong> Giấy phép làm việc chỉ được phép ký duyệt số khi tất cả 4 điểm cô lập nguồn năng lượng (van khí, van xả, cầu dao điện) đã được gắn Khóa LOTO và Thẻ Cảnh Báo An Toàn.';
                }
            }
        }

        function togglePointItem(pt) {
            var isLocked = pt.getAttribute('data-locked') === 'true';
            var statusBadge = pt.querySelector('.loto-status-badge');
            var toggleBtn = pt.querySelector('.btn-loto-toggle');

            if (isLocked) {
                pt.setAttribute('data-locked', 'false');
                pt.classList.remove('is-locked');
                pt.classList.add('is-unlocked');
                if (statusBadge) {
                    statusBadge.className = 'badge bg-danger bg-opacity-25 text-danger border border-danger loto-status-badge';
                    statusBadge.textContent = 'CHƯA KHÓA HÃM';
                }
                if (toggleBtn) {
                    toggleBtn.className = 'btn btn-sm btn-outline-danger btn-loto-toggle w-100';
                    toggleBtn.textContent = 'Gắn Khóa LOTO';
                }
            } else {
                pt.setAttribute('data-locked', 'true');
                pt.classList.remove('is-unlocked');
                pt.classList.add('is-locked');
                if (statusBadge) {
                    statusBadge.className = 'badge bg-success bg-opacity-25 text-success border border-success loto-status-badge';
                    statusBadge.textContent = 'ĐÃ KHÓA (LOCK #L-8824)';
                }
                if (toggleBtn) {
                    toggleBtn.className = 'btn btn-sm btn-outline-success btn-loto-toggle w-100';
                    toggleBtn.textContent = 'Mở Khóa';
                }
            }
            checkLotoCompletion();
        }

        function triggerPoint4Toggle() {
            var pt4 = section.querySelector('.loto-point-item[data-point-id="4"]');
            if (pt4) {
                togglePointItem(pt4);
            }
        }

        lotoPoints.forEach(function (pt) {
            var toggleBtn = pt.querySelector('.btn-loto-toggle');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', function () {
                    togglePointItem(pt);
                });
            }
        });

        // Click directly on SVG Node 4 or 3D HUD Node 4 to toggle Point 4
        if (svgNode4) {
            svgNode4.addEventListener('click', triggerPoint4Toggle);
        }
        if (hudNode4) {
            hudNode4.addEventListener('click', triggerPoint4Toggle);
        }

        // Interactive 3D Digital Twin Anatomy Canvas Engine for Reactor R-201
        if (loto3dCanvas && loto3dCanvas.getContext) {
            var ctx3d = loto3dCanvas.getContext('2d');

            camModeBtns.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    var mode = btn.getAttribute('data-cam-mode');
                    camModeBtns.forEach(function (b) {
                        b.classList.remove('active');
                        b.style.background = 'rgba(15, 23, 42, 0.8)';
                        b.style.color = '#94A3B8';
                        b.style.borderColor = 'rgba(255, 255, 255, 0.15)';
                    });
                    btn.classList.add('active');
                    btn.style.background = 'rgba(56, 189, 248, 0.18)';
                    btn.style.color = '#38BDF8';
                    btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';

                    if (mode === 'iso') {
                        loto3dState.targetYaw = 0.48;
                        loto3dState.targetPitch = 0.36;
                        loto3dState.xrayMode = false;
                    } else if (mode === 'xray') {
                        loto3dState.targetYaw = -0.35;
                        loto3dState.targetPitch = 0.22;
                        loto3dState.xrayMode = true;
                    } else if (mode === 'top') {
                        loto3dState.targetYaw = 0.0;
                        loto3dState.targetPitch = 1.18;
                        loto3dState.xrayMode = false;
                    }
                });
            });

            loto3dCanvas.addEventListener('mousedown', function (e) {
                loto3dState.dragging = true;
                loto3dState.lastX = e.clientX;
                loto3dState.lastY = e.clientY;
                loto3dCanvas.style.cursor = 'grabbing';
            });
            window.addEventListener('mousemove', function (e) {
                if (!loto3dState.dragging) return;
                var dx = e.clientX - loto3dState.lastX;
                var dy = e.clientY - loto3dState.lastY;
                loto3dState.lastX = e.clientX;
                loto3dState.lastY = e.clientY;
                loto3dState.targetYaw += dx * 0.008;
                loto3dState.targetPitch = Math.max(0.08, Math.min(1.35, loto3dState.targetPitch + dy * 0.006));
            });
            window.addEventListener('mouseup', function () {
                if (loto3dState.dragging) {
                    loto3dState.dragging = false;
                    loto3dCanvas.style.cursor = 'grab';
                }
            });
            loto3dCanvas.addEventListener('click', function (e) {
                var rect = loto3dCanvas.getBoundingClientRect();
                var scaleX = loto3dCanvas.width / Math.max(rect.width, 1);
                var scaleY = loto3dCanvas.height / Math.max(rect.height, 1);
                var cx = (e.clientX - rect.left) * scaleX;
                var cy = (e.clientY - rect.top) * scaleY;
                var dx = cx - loto3dState.valve4ScreenPos.x;
                var dy = cy - loto3dState.valve4ScreenPos.y;
                if (Math.sqrt(dx * dx + dy * dy) <= loto3dState.valve4ScreenPos.r) {
                    triggerPoint4Toggle();
                }
            });

            function project3D(x, y, z, w, h, yaw, pitch) {
                var cosY = Math.cos(yaw), sinY = Math.sin(yaw);
                var x1 = x * cosY - z * sinY;
                var z1 = x * sinY + z * cosY;
                var cosP = Math.cos(pitch), sinP = Math.sin(pitch);
                var y2 = y * cosP - z1 * sinP;
                var z2 = y * sinP + z1 * cosP;
                var fov = 620;
                var scale = fov / Math.max(fov + z2 + 240, 120);
                return {
                    x: w * 0.5 + x1 * scale,
                    y: h * 0.52 + y2 * scale,
                    scale: scale,
                    z: z2
                };
            }

            function renderLoto3dFrame() {
                loto3dState.tick += 1;
                if (!loto3dState.dragging && !loto3dState.xrayMode) {
                    loto3dState.targetYaw += 0.0024;
                }
                loto3dState.yaw += (loto3dState.targetYaw - loto3dState.yaw) * 0.085;
                loto3dState.pitch += (loto3dState.targetPitch - loto3dState.pitch) * 0.085;

                var w = loto3dCanvas.width;
                var h = loto3dCanvas.height;
                var yaw = loto3dState.yaw;
                var pitch = loto3dState.pitch;
                var isSafe = loto3dState.point4Locked;
                var isXray = loto3dState.xrayMode;
                ctx3d.clearRect(0, 0, w, h);

                // 0. Subtle Volumetric Ambient Glow Behind Reactor Core
                var center3D = project3D(0, 0, 0, w, h, yaw, pitch);
                var ambientGrad = ctx3d.createRadialGradient(center3D.x, center3D.y, 12, center3D.x, center3D.y, 230);
                if (isSafe) {
                    ambientGrad.addColorStop(0, 'rgba(16, 185, 129, 0.20)');
                    ambientGrad.addColorStop(0.5, 'rgba(56, 189, 248, 0.08)');
                    ambientGrad.addColorStop(1, 'rgba(4, 9, 20, 0)');
                } else {
                    ambientGrad.addColorStop(0, 'rgba(239, 68, 68, 0.22)');
                    ambientGrad.addColorStop(0.5, 'rgba(56, 189, 248, 0.08)');
                    ambientGrad.addColorStop(1, 'rgba(4, 9, 20, 0)');
                }
                ctx3d.fillStyle = ambientGrad;
                ctx3d.fillRect(0, 0, w, h);

                // 1. 3D Isometric Blueprint Floor Grid + Circular Containment Pad
                ctx3d.lineWidth = 1;
                ctx3d.strokeStyle = 'rgba(56, 189, 248, 0.09)';
                for (var g = -280; g <= 280; g += 40) {
                    var pA = project3D(g, 102, -200, w, h, yaw, pitch);
                    var pB = project3D(g, 102, 200, w, h, yaw, pitch);
                    ctx3d.beginPath();
                    ctx3d.moveTo(pA.x, pA.y);
                    ctx3d.lineTo(pB.x, pB.y);
                    ctx3d.stroke();

                    var pC = project3D(-280, 102, g * 0.72, w, h, yaw, pitch);
                    var pD = project3D(280, 102, g * 0.72, w, h, yaw, pitch);
                    ctx3d.beginPath();
                    ctx3d.moveTo(pC.x, pC.y);
                    ctx3d.lineTo(pD.x, pD.y);
                    ctx3d.stroke();
                }

                // Circular Floor Containment Pad & Shadow beneath Reactor R-201
                ctx3d.beginPath();
                for (var sPad = 0; sPad <= 36; sPad++) {
                    var aPad = (sPad / 36) * Math.PI * 2;
                    var ptPad = project3D(Math.cos(aPad) * 105, 102, Math.sin(aPad) * 105, w, h, yaw, pitch);
                    if (sPad === 0) ctx3d.moveTo(ptPad.x, ptPad.y);
                    else ctx3d.lineTo(ptPad.x, ptPad.y);
                }
                ctx3d.fillStyle = 'rgba(2, 6, 23, 0.65)';
                ctx3d.fill();
                ctx3d.lineWidth = 1.5;
                ctx3d.strokeStyle = isSafe ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.40)';
                ctx3d.stroke();

                // 2. 4 Structural Steel Support Legs Anchored to Floor Pad
                var legAngles = [Math.PI * 0.25, Math.PI * 0.75, Math.PI * 1.25, Math.PI * 1.75];
                legAngles.forEach(function (la) {
                    var legTop = project3D(Math.cos(la) * 64, 58, Math.sin(la) * 64, w, h, yaw, pitch);
                    var legBot = project3D(Math.cos(la) * 76, 102, Math.sin(la) * 76, w, h, yaw, pitch);
                    ctx3d.beginPath();
                    ctx3d.moveTo(legTop.x, legTop.y);
                    ctx3d.lineTo(legBot.x, legBot.y);
                    ctx3d.lineWidth = 6;
                    ctx3d.lineCap = 'round';
                    ctx3d.strokeStyle = '#1E293B';
                    ctx3d.stroke();
                    ctx3d.lineWidth = 2;
                    ctx3d.strokeStyle = '#64748B';
                    ctx3d.stroke();
                });

                // 3. Volumetric 3D Shaded Cylindrical Vessel Shell & Elliptical Domes (PBR Metallic Shading)
                var radius = 74;
                var topY = -66;
                var botY = 66;
                var leftEdge = project3D(-radius, 0, 0, w, h, yaw, pitch);
                var rightEdge = project3D(radius, 0, 0, w, h, yaw, pitch);
                var topCenter = project3D(0, topY, 0, w, h, yaw, pitch);
                var botCenter = project3D(0, botY, 0, w, h, yaw, pitch);
                var rx = Math.abs(rightEdge.x - leftEdge.x) * 0.5;
                var ryTop = Math.max(14, rx * Math.sin(Math.max(0.18, pitch)) * 0.52);
                var ryBot = Math.max(16, rx * Math.sin(Math.max(0.18, pitch)) * 0.55);

                // Cylindrical Metallic PBR Gradient (Back-to-Front Pass)
                var shellGrad = ctx3d.createLinearGradient(topCenter.x - rx, 0, topCenter.x + rx, 0);
                var alphaShell = isXray ? 0.26 : 0.84;
                shellGrad.addColorStop(0.0, 'rgba(8, 17, 34, ' + alphaShell + ')');
                shellGrad.addColorStop(0.22, 'rgba(23, 49, 82, ' + alphaShell + ')');
                shellGrad.addColorStop(0.38, 'rgba(56, 189, 248, ' + (isXray ? 0.22 : 0.48) + ')');
                shellGrad.addColorStop(0.52, 'rgba(15, 35, 62, ' + alphaShell + ')');
                shellGrad.addColorStop(0.82, 'rgba(10, 22, 42, ' + alphaShell + ')');
                shellGrad.addColorStop(1.0, 'rgba(30, 64, 105, ' + alphaShell + ')');

                ctx3d.save();
                ctx3d.beginPath();
                ctx3d.ellipse(topCenter.x, topCenter.y, rx, ryTop, 0, Math.PI, 0, false);
                ctx3d.lineTo(botCenter.x + rx, botCenter.y);
                ctx3d.ellipse(botCenter.x, botCenter.y, rx, ryBot, 0, 0, Math.PI, false);
                ctx3d.closePath();
                ctx3d.fillStyle = shellGrad;
                ctx3d.fill();
                ctx3d.lineWidth = 2;
                ctx3d.strokeStyle = isSafe ? 'rgba(56, 189, 248, 0.65)' : 'rgba(248, 113, 113, 0.72)';
                ctx3d.stroke();
                ctx3d.restore();

                // 4. Internal Volumetric Chemical Liquid Column & Animated Meniscus Wave
                var liqTopY = 6 + Math.sin(loto3dState.tick * 0.05) * 2.5;
                var liqTopCenter = project3D(0, liqTopY, 0, w, h, yaw, pitch);
                var rxLiq = rx * 0.91;
                var ryLiq = ryTop * 0.88;
                var liqGrad = ctx3d.createLinearGradient(liqTopCenter.x - rxLiq, liqTopCenter.y, liqTopCenter.x + rxLiq, botCenter.y);
                if (isSafe) {
                    liqGrad.addColorStop(0, 'rgba(16, 185, 129, 0.42)');
                    liqGrad.addColorStop(0.5, 'rgba(6, 182, 212, 0.52)');
                    liqGrad.addColorStop(1, 'rgba(4, 120, 87, 0.68)');
                } else {
                    liqGrad.addColorStop(0, 'rgba(245, 158, 11, 0.48)');
                    liqGrad.addColorStop(0.5, 'rgba(239, 68, 68, 0.56)');
                    liqGrad.addColorStop(1, 'rgba(153, 27, 27, 0.74)');
                }
                ctx3d.beginPath();
                ctx3d.ellipse(liqTopCenter.x, liqTopCenter.y, rxLiq, ryLiq, 0, Math.PI, 0, false);
                ctx3d.lineTo(botCenter.x + rxLiq, botCenter.y - 3);
                ctx3d.ellipse(botCenter.x, botCenter.y - 3, rxLiq, ryBot * 0.88, 0, 0, Math.PI, false);
                ctx3d.closePath();
                ctx3d.fillStyle = liqGrad;
                ctx3d.fill();

                // Liquid Top Meniscus Surface Ring
                ctx3d.beginPath();
                ctx3d.ellipse(liqTopCenter.x, liqTopCenter.y, rxLiq, ryLiq, 0, 0, Math.PI * 2);
                ctx3d.fillStyle = isSafe ? 'rgba(52, 211, 153, 0.32)' : 'rgba(251, 113, 133, 0.38)';
                ctx3d.fill();
                ctx3d.lineWidth = 1.4;
                ctx3d.strokeStyle = isSafe ? '#34D399' : '#FB7185';
                ctx3d.stroke();

                // Rising Micro-Bubbles inside Chemical Liquid
                for (var bIdx = 0; bIdx < 8; bIdx++) {
                    var bPhase = ((loto3dState.tick * (isSafe ? 0.008 : 0.028) + bIdx * 0.13) % 1);
                    var bY = botY - 8 - bPhase * (botY - liqTopY - 10);
                    var bAng = bIdx * 1.7 + loto3dState.tick * 0.02;
                    var bRad = 16 + (bIdx % 3) * 14;
                    var bPt = project3D(Math.cos(bAng) * bRad, bY, Math.sin(bAng) * bRad, w, h, yaw, pitch);
                    ctx3d.beginPath();
                    ctx3d.arc(bPt.x, bPt.y, 2.2 + (bIdx % 2), 0, Math.PI * 2);
                    ctx3d.fillStyle = isSafe ? 'rgba(167, 243, 208, 0.65)' : 'rgba(254, 205, 211, 0.80)';
                    ctx3d.fill();
                }

                // 5. Internal Brushed Stainless Steel Helical Cooling Coil
                ctx3d.beginPath();
                var coilSteps = 44;
                for (var cStep = 0; cStep <= coilSteps; cStep++) {
                    var cFrac = cStep / coilSteps;
                    var cAngle = cFrac * Math.PI * 6 + yaw;
                    var cY = -36 + cFrac * 86;
                    var cPt = project3D(Math.cos(cAngle) * 52, cY, Math.sin(cAngle) * 52, w, h, yaw, pitch);
                    if (cStep === 0) ctx3d.moveTo(cPt.x, cPt.y);
                    else ctx3d.lineTo(cPt.x, cPt.y);
                }
                ctx3d.lineWidth = 3.2;
                ctx3d.strokeStyle = 'rgba(148, 163, 184, 0.42)';
                ctx3d.stroke();
                ctx3d.lineWidth = 1.2;
                ctx3d.strokeStyle = 'rgba(226, 232, 240, 0.68)';
                ctx3d.stroke();

                // 6. Central Agitator Shaft & Dual 6-Blade Rushton Turbine Impellers
                var shaftTop = project3D(0, -96, 0, w, h, yaw, pitch);
                var shaftBot = project3D(0, 54, 0, w, h, yaw, pitch);
                ctx3d.beginPath();
                ctx3d.moveTo(shaftTop.x, shaftTop.y);
                ctx3d.lineTo(shaftBot.x, shaftBot.y);
                ctx3d.lineWidth = 6;
                ctx3d.strokeStyle = '#334155';
                ctx3d.stroke();
                ctx3d.lineWidth = 2.2;
                ctx3d.strokeStyle = '#E2E8F0';
                ctx3d.stroke();

                var spinAngle = isSafe ? 0.65 : loto3dState.tick * 0.075;
                [-8, 34].forEach(function (impY, impIdx) {
                    var bladeRadius = impIdx === 0 ? 38 : 48;
                    var hubPt = project3D(0, impY, 0, w, h, yaw, pitch);
                    for (var b = 0; b < 6; b++) {
                        var ba = spinAngle + (b * Math.PI / 3);
                        var tip1 = project3D(Math.cos(ba - 0.16) * bladeRadius, impY - 4, Math.sin(ba - 0.16) * bladeRadius, w, h, yaw, pitch);
                        var tip2 = project3D(Math.cos(ba + 0.16) * bladeRadius, impY + 4, Math.sin(ba + 0.16) * bladeRadius, w, h, yaw, pitch);
                        ctx3d.beginPath();
                        ctx3d.moveTo(hubPt.x, hubPt.y);
                        ctx3d.lineTo(tip1.x, tip1.y);
                        ctx3d.lineTo(tip2.x, tip2.y);
                        ctx3d.closePath();
                        ctx3d.fillStyle = isSafe ? 'rgba(52, 211, 153, 0.55)' : 'rgba(56, 189, 248, 0.62)';
                        ctx3d.fill();
                        ctx3d.lineWidth = 1.2;
                        ctx3d.strokeStyle = isSafe ? '#6EE7B7' : '#7DD3FC';
                        ctx3d.stroke();
                    }
                    // Center Turbine Hub Ring
                    ctx3d.beginPath();
                    ctx3d.arc(hubPt.x, hubPt.y, 6, 0, Math.PI * 2);
                    ctx3d.fillStyle = '#0F172A';
                    ctx3d.fill();
                    ctx3d.lineWidth = 2;
                    ctx3d.strokeStyle = '#38BDF8';
                    ctx3d.stroke();
                });

                // 7. 5 Bolted Flange Rings with 3D Hex Bolt Rivets & Vertical Longitudinal Ribs
                for (var r = 0; r < 12; r++) {
                    var ang = (r / 12) * Math.PI * 2;
                    if (isXray && Math.sin(ang + yaw) > 0.15) continue;
                    var topP = project3D(Math.cos(ang) * radius, topY, Math.sin(ang) * radius, w, h, yaw, pitch);
                    var botP = project3D(Math.cos(ang) * radius, botY, Math.sin(ang) * radius, w, h, yaw, pitch);
                    ctx3d.beginPath();
                    ctx3d.moveTo(topP.x, topP.y);
                    ctx3d.lineTo(botP.x, botP.y);
                    ctx3d.lineWidth = 1.1;
                    ctx3d.strokeStyle = isSafe ? 'rgba(56, 189, 248, 0.22)' : 'rgba(248, 113, 113, 0.24)';
                    ctx3d.stroke();
                }

                var ringsY = [-66, -33, 0, 33, 66];
                ringsY.forEach(function (ry, idx) {
                    var isMainFlange = (idx === 0 || idx === 2 || idx === ringsY.length - 1);
                    ctx3d.beginPath();
                    for (var s = 0; s <= 32; s++) {
                        var a = (s / 32) * Math.PI * 2;
                        var p = project3D(Math.cos(a) * (radius + (isMainFlange ? 3 : 0)), ry, Math.sin(a) * (radius + (isMainFlange ? 3 : 0)), w, h, yaw, pitch);
                        if (s === 0) ctx3d.moveTo(p.x, p.y);
                        else ctx3d.lineTo(p.x, p.y);
                    }
                    ctx3d.lineWidth = isMainFlange ? 3.2 : 1.5;
                    ctx3d.strokeStyle = isSafe
                        ? (idx === 2 ? 'rgba(16, 185, 129, 0.78)' : 'rgba(56, 189, 248, 0.52)')
                        : (idx === 2 ? 'rgba(239, 68, 68, 0.82)' : 'rgba(56, 189, 248, 0.45)');
                    ctx3d.stroke();

                    // 3D Hex Bolt Rivets along main flanges
                    if (isMainFlange) {
                        for (var bRiv = 0; bRiv < 12; bRiv++) {
                            var bAng = (bRiv / 12) * Math.PI * 2;
                            var bPt = project3D(Math.cos(bAng) * (radius + 3), ry, Math.sin(bAng) * (radius + 3), w, h, yaw, pitch);
                            if (bPt.z < 20) {
                                ctx3d.beginPath();
                                ctx3d.arc(bPt.x, bPt.y, 2.1, 0, Math.PI * 2);
                                ctx3d.fillStyle = '#E2E8F0';
                                ctx3d.fill();
                            }
                        }
                    }
                });

                // Top 45kW Explosion-Proof Motor Housing & Cooling Fins
                var motorW = 46, motorH = 26;
                var motorGrad = ctx3d.createLinearGradient(shaftTop.x - motorW / 2, shaftTop.y - motorH, shaftTop.x + motorW / 2, shaftTop.y);
                motorGrad.addColorStop(0, '#0F172A');
                motorGrad.addColorStop(0.5, '#334155');
                motorGrad.addColorStop(1, '#0F172A');
                ctx3d.fillStyle = motorGrad;
                ctx3d.strokeStyle = '#38BDF8';
                ctx3d.lineWidth = 1.8;
                ctx3d.beginPath();
                ctx3d.roundRect(shaftTop.x - motorW / 2, shaftTop.y - motorH, motorW, motorH, 5);
                ctx3d.fill();
                ctx3d.stroke();
                // Cooling fins on motor
                for (var f = -14; f <= 14; f += 7) {
                    ctx3d.beginPath();
                    ctx3d.moveTo(shaftTop.x + f, shaftTop.y - motorH + 4);
                    ctx3d.lineTo(shaftTop.x + f, shaftTop.y - 4);
                    ctx3d.lineWidth = 1.2;
                    ctx3d.strokeStyle = 'rgba(148, 163, 184, 0.55)';
                    ctx3d.stroke();
                }

                // 8. 4 3-Pass Volumetric Pipe Manifolds, Flanged Nozzles & Valve Handwheels
                var pipes = [
                    {
                        id: 1,
                        label: 'V-101 · HƠI NÓNG',
                        locked: true,
                        pts: [[-330, -64, -75], [-195, -64, -38], [-74, -36, 0]],
                        hudAnchor: [165, 58],
                        pillDx: -16,
                        pillDy: -34,
                        valveIdx: 1
                    },
                    {
                        id: 2,
                        label: 'CB-201 · MOTOR 45KW',
                        locked: true,
                        pts: [[330, -64, -75], [195, -64, -38], [74, -36, 0]],
                        hudAnchor: [w - 165, 58],
                        pillDx: 16,
                        pillDy: -34,
                        valveIdx: 1
                    },
                    {
                        id: 3,
                        label: 'V-105 · AXIT H2SO4',
                        locked: true,
                        pts: [[-330, 52, 75], [-195, 52, 38], [-74, 36, 0]],
                        hudAnchor: [165, h - 58],
                        pillDx: -48,
                        pillDy: 16,
                        valveIdx: 1
                    },
                    {
                        id: 4,
                        label: 'V-109 · XẢ ÁP N2',
                        locked: isSafe,
                        pts: [[330, 52, 75], [195, 52, 38], [74, 36, 0]],
                        hudAnchor: [w - 165, h - 58],
                        pillDx: 48,
                        pillDy: 16,
                        valveIdx: 1
                    }
                ];

                pipes.forEach(function (pipe) {
                    var projPts = pipe.pts.map(function (pt) {
                        return project3D(pt[0], pt[1], pt[2], w, h, yaw, pitch);
                    });

                    // Pass 1: Outer Pipe Shadow Casing
                    ctx3d.beginPath();
                    ctx3d.moveTo(projPts[0].x, projPts[0].y);
                    ctx3d.lineTo(projPts[1].x, projPts[1].y);
                    ctx3d.lineTo(projPts[2].x, projPts[2].y);
                    ctx3d.lineCap = 'round';
                    ctx3d.lineJoin = 'round';
                    ctx3d.lineWidth = 14;
                    ctx3d.strokeStyle = 'rgba(15, 23, 42, 0.92)';
                    ctx3d.stroke();

                    // Pass 2: Metallic Pipe Body
                    ctx3d.lineWidth = 10;
                    ctx3d.strokeStyle = pipe.locked ? 'rgba(16, 185, 129, 0.38)' : 'rgba(239, 68, 68, 0.52)';
                    ctx3d.stroke();

                    // Pass 3: Anisotropic Specular Core Highlight
                    ctx3d.lineWidth = 3.6;
                    ctx3d.strokeStyle = pipe.locked ? '#34D399' : '#FB7185';
                    ctx3d.stroke();

                    // Vessel Nozzle Collar Ring at projPts[2]
                    ctx3d.beginPath();
                    ctx3d.arc(projPts[2].x, projPts[2].y, 7, 0, Math.PI * 2);
                    ctx3d.fillStyle = '#1E293B';
                    ctx3d.fill();
                    ctx3d.lineWidth = 2;
                    ctx3d.strokeStyle = pipe.locked ? '#10B981' : '#EF4444';
                    ctx3d.stroke();

                    // If unlocked (Feeder 4 hazard), stream pressurized N2 gas particles into the reactor
                    if (!pipe.locked) {
                        for (var k = 0; k < 6; k++) {
                            var frac = ((loto3dState.tick * 0.028 + k * 0.166) % 1);
                            var segX, segY;
                            if (frac < 0.5) {
                                var t1 = frac * 2;
                                segX = projPts[0].x + (projPts[1].x - projPts[0].x) * t1;
                                segY = projPts[0].y + (projPts[1].y - projPts[0].y) * t1;
                            } else {
                                var t2 = (frac - 0.5) * 2;
                                segX = projPts[1].x + (projPts[2].x - projPts[1].x) * t2;
                                segY = projPts[1].y + (projPts[2].y - projPts[1].y) * t2;
                            }
                            ctx3d.beginPath();
                            ctx3d.arc(segX, segY, 4.2, 0, Math.PI * 2);
                            ctx3d.fillStyle = '#FFE4E6';
                            ctx3d.fill();
                        }
                    }

                    // 3D Isolation Valve & Spoke Handwheel at elbow
                    var vPt = projPts[pipe.valveIdx];
                    if (pipe.id === 4) {
                        loto3dState.valve4ScreenPos = { x: vPt.x, y: vPt.y, r: 34 };
                        if (!pipe.locked) {
                            var pulseR = 16 + ((loto3dState.tick * 0.45) % 18);
                            ctx3d.beginPath();
                            ctx3d.arc(vPt.x, vPt.y, pulseR, 0, Math.PI * 2);
                            ctx3d.lineWidth = 1.8;
                            ctx3d.strokeStyle = 'rgba(251, 113, 133, ' + Math.max(0, 1 - (pulseR - 16) / 18) + ')';
                            ctx3d.stroke();
                        }
                    }

                    // Subtle Leader Callout Line to HUD Corner Card
                    ctx3d.save();
                    ctx3d.setLineDash([3, 4]);
                    ctx3d.beginPath();
                    ctx3d.moveTo(vPt.x, vPt.y);
                    ctx3d.lineTo(pipe.hudAnchor[0], pipe.hudAnchor[1]);
                    ctx3d.lineWidth = 1.1;
                    ctx3d.strokeStyle = pipe.locked ? 'rgba(52, 211, 153, 0.28)' : 'rgba(251, 113, 133, 0.45)';
                    ctx3d.stroke();
                    ctx3d.restore();

                    // Valve Body & Handwheel Rim
                    var vRadius = pipe.id === 4 && !pipe.locked ? 14 + Math.sin(loto3dState.tick * 0.14) * 2 : 12;
                    ctx3d.beginPath();
                    ctx3d.arc(vPt.x, vPt.y, vRadius, 0, Math.PI * 2);
                    ctx3d.fillStyle = pipe.locked ? '#064E3B' : '#881337';
                    ctx3d.fill();
                    ctx3d.lineWidth = 2.6;
                    ctx3d.strokeStyle = pipe.locked ? '#34D399' : '#FDA4AF';
                    ctx3d.stroke();

                    // Valve Handwheel Spokes
                    for (var sp = 0; sp < 4; sp++) {
                        var spA = (sp * Math.PI * 0.5) + (pipe.locked ? 0 : loto3dState.tick * 0.04);
                        ctx3d.beginPath();
                        ctx3d.moveTo(vPt.x - Math.cos(spA) * (vRadius - 3), vPt.y - Math.sin(spA) * (vRadius - 3));
                        ctx3d.lineTo(vPt.x + Math.cos(spA) * (vRadius - 3), vPt.y + Math.sin(spA) * (vRadius - 3));
                        ctx3d.lineWidth = 1.6;
                        ctx3d.strokeStyle = pipe.locked ? '#A7F3D0' : '#FFE4E6';
                        ctx3d.stroke();
                    }

                    // High-Contrast Valve Label Pill (offset outward so zero overlap)
                    var pillText = (pipe.locked ? '🔒 ' : '⚠️ ') + pipe.label;
                    ctx3d.font = '700 10px Poppins, sans-serif';
                    var pillW = Math.max(114, ctx3d.measureText(pillText).width + 16);
                    var pillH = 20;
                    var pillX = vPt.x + (pipe.pillDx || 0) - pillW / 2;
                    var pillY = vPt.y + pipe.pillDy;
                    ctx3d.fillStyle = 'rgba(7, 14, 28, 0.92)';
                    ctx3d.strokeStyle = pipe.locked ? 'rgba(52, 211, 153, 0.65)' : 'rgba(251, 113, 133, 0.85)';
                    ctx3d.lineWidth = 1.2;
                    ctx3d.beginPath();
                    ctx3d.roundRect(pillX, pillY, pillW, pillH, 4);
                    ctx3d.fill();
                    ctx3d.stroke();
                    ctx3d.textAlign = 'center';
                    ctx3d.fillStyle = pipe.locked ? '#A7F3D0' : '#FFE4E6';
                    ctx3d.fillText(pillText, pillX + pillW / 2, pillY + 13.5);
                });

                // 9. Bottom-Center Docked 3D Reactor Core Status Readout Tag (Unobstructed Vessel View)
                var tagCenterX = w * 0.5;
                var tagCenterY = h - 32;
                var tagW = 296, tagH = 46;
                ctx3d.fillStyle = 'rgba(6, 12, 24, 0.94)';
                ctx3d.strokeStyle = isSafe ? '#10B981' : '#EF4444';
                ctx3d.lineWidth = 1.6;
                ctx3d.beginPath();
                ctx3d.roundRect(tagCenterX - tagW / 2, tagCenterY - tagH / 2, tagW, tagH, 6);
                ctx3d.fill();
                ctx3d.stroke();

                ctx3d.font = '700 10px Poppins, sans-serif';
                ctx3d.textAlign = 'center';
                ctx3d.fillStyle = '#F8FAFC';
                ctx3d.fillText('BỒN PHẢN ỨNG R-201 · DIGITAL TWIN · ' + (isSafe ? 'RPM: 0 · 28.4°C' : 'RPM: 145 · 64.2°C'), tagCenterX, tagCenterY - 5);
                ctx3d.font = '700 9.5px Poppins, sans-serif';
                ctx3d.fillStyle = isSafe ? '#34D399' : '#FDA4AF';
                ctx3d.fillText(isSafe ? '🛡️ ZERO ENERGY VERIFIED · ÁP SUẤT 0.00 BAR (AN TOÀN MỞ BỒN)' : '⛔ ÁP SUẤT DƯ N2: 0.35 BAR · CẤM MỞ MANHOLE R-201', tagCenterX, tagCenterY + 11);

                requestAnimationFrame(renderLoto3dFrame);
            }

            requestAnimationFrame(renderLoto3dFrame);
        }

        if (btnSignPtw) {
            btnSignPtw.addEventListener('click', function () {
                btnSignPtw.disabled = true;
                btnSignPtw.innerHTML = '✅ ĐÃ KÝ DUYỆT SỐ KÉP (Bilateral Signed)';
                btnSignPtw.classList.remove('btn-primary');
                btnSignPtw.classList.add('btn-success');

                if (ptwStatusBanner) {
                    ptwStatusBanner.className = 'alert alert-success border border-success p-3 rounded-3 mb-3';
                    ptwStatusBanner.innerHTML = '<strong>GIẤY PHÉP e-PTW-2026-0412 ĐÃ CÓ HIỆU LỰC:</strong> Đội công tác (5 nhân sự) được phép tiếp cận bồn phản ứng R-201. Chứng chỉ ký duyệt kép đã được lưu vào sổ cái kiểm toán bất biến.';
                }

                // Reveal Bilateral Stamps
                if (ptwBilateralStamps) {
                    ptwBilateralStamps.classList.remove('d-none');
                    var now = new Date();
                    var timeStr = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
                    var stampTimeEhs = section.querySelector('#stampTimeEhs');
                    var stampTimePlant = section.querySelector('#stampTimePlant');
                    if (stampTimeEhs) stampTimeEhs.textContent = 'TIMESTAMP: ' + timeStr;
                    if (stampTimePlant) stampTimePlant.textContent = 'TIMESTAMP: ' + timeStr;
                }

                // Start Live Countdown Timer
                if (ptwCountdownBadge) {
                    ptwCountdownBadge.classList.remove('d-none');
                    ptwCountdownBadge.className = 'badge bg-success bg-opacity-25 text-success border border-success px-3 py-2 fw-semibold';
                    var totalSeconds = 8 * 3600 - 15; // 07:59:45
                    if (ptwCountdownTimer) clearInterval(ptwCountdownTimer);
                    ptwCountdownTimer = setInterval(function () {
                        if (totalSeconds <= 0) {
                            clearInterval(ptwCountdownTimer);
                            return;
                        }
                        totalSeconds--;
                        var h = Math.floor(totalSeconds / 3600);
                        var m = Math.floor((totalSeconds % 3600) / 60);
                        var s = totalSeconds % 60;
                        var hStr = (h < 10 ? '0' : '') + h;
                        var mStr = (m < 10 ? '0' : '') + m;
                        var sStr = (s < 10 ? '0' : '') + s;
                        ptwCountdownBadge.innerHTML = '⏱️ Giấy Phép Hiệu Lực: ' + hStr + ':' + mStr + ':' + sStr;
                    }, 1000);
                }
            });
        }

        // Shift Handover Console
        var shiftEvents = section.querySelectorAll('.shift-log-item');
        var eventFilterBtns = section.querySelectorAll('.btn-shift-filter');
        var btnSignCa1 = section.querySelector('#btnSignCa1');
        var btnSignCa2 = section.querySelector('#btnSignCa2');
        var handoverStatusBadge = section.querySelector('#handoverStatusBadge');

        eventFilterBtns.forEach(function (fBtn) {
            fBtn.addEventListener('click', function () {
                var priority = fBtn.getAttribute('data-priority');
                eventFilterBtns.forEach(function (b) { b.classList.remove('active'); });
                fBtn.classList.add('active');

                shiftEvents.forEach(function (ev) {
                    var evPriority = ev.getAttribute('data-priority');
                    if (priority === 'all' || evPriority === priority) {
                        ev.style.display = '';
                    } else {
                        ev.style.display = 'none';
                    }
                });
            });
        });

        var ca1Signed = false;
        var ca2Signed = false;

        if (btnSignCa1) {
            btnSignCa1.addEventListener('click', function () {
                ca1Signed = true;
                btnSignCa1.disabled = true;
                btnSignCa1.innerHTML = '✅ Ca Trưởng Ca 1 Đã Ký Giao';
                if (btnSignCa2) {
                    btnSignCa2.disabled = false;
                    btnSignCa2.classList.remove('btn-secondary');
                    btnSignCa2.classList.add('btn-primary');
                }
                if (handoverStatusBadge) {
                    handoverStatusBadge.className = 'badge bg-info bg-opacity-25 text-info border border-info px-3 py-2 fw-semibold';
                    handoverStatusBadge.innerHTML = 'Đang Chờ Ca Trưởng Ca 2 Ký Nhận Bàn Giao';
                }
            });
        }

        if (btnSignCa2) {
            btnSignCa2.addEventListener('click', function () {
                ca2Signed = true;
                btnSignCa2.disabled = true;
                btnSignCa2.innerHTML = '✅ Ca Trưởng Ca 2 Đã Ký Nhận';
                if (handoverStatusBadge) {
                    handoverStatusBadge.className = 'badge bg-success bg-opacity-25 text-success border border-success px-3 py-2 fw-semibold';
                    handoverStatusBadge.innerHTML = '✅ BÀN GIAO CA HOÀN TẤT &amp; KHÓA AUDIT TRAIL [REF: LOG-20261010-C1C2]';
                }
            });
        }
    }

    function initLogisticsJobfileInteractive() {
        var section = document.getElementById('innoria_logistics_jobfile_interactive');
        if (!section || section.dataset.grcLogisticsInit === 'true') {
            return;
        }
        section.dataset.grcLogisticsInit = 'true';

        var btnDisputeDem = section.querySelector('#btnDisputeDem');
        var disputeNoticeBox = section.querySelector('#disputeNoticeBox');

        if (btnDisputeDem && disputeNoticeBox) {
            btnDisputeDem.addEventListener('click', function () {
                var isHidden = disputeNoticeBox.classList.contains('d-none');
                if (isHidden) {
                    disputeNoticeBox.classList.remove('d-none');
                    btnDisputeDem.innerHTML = '<svg class="ph-duotone ph-file-text me-1" width="16" height="16"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-file-text"/></svg> Đóng Văn Bản Khiếu Nại Cước';
                    disputeNoticeBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    disputeNoticeBox.classList.add('d-none');
                    btnDisputeDem.innerHTML = '<svg class="ph-duotone ph-warning-circle me-1" width="16" height="16"><use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-warning-circle"/></svg> Sinh Thư Kháng Nghị Chi Phí Bất Thường';
                }
            });
        }
    }

    function initWaterfallInteractive() {
        var btnWaterfallEvfta = document.getElementById('btnWaterfallEvfta');
        var btnWaterfallMfn = document.getElementById('btnWaterfallMfn');

        if (btnWaterfallEvfta && !btnWaterfallEvfta.dataset.evftaBound) {
            btnWaterfallEvfta.dataset.evftaBound = 'true';
            btnWaterfallEvfta.addEventListener('click', function () {
                document.querySelectorAll('.inn-waterfall-stage.stage--mfn').forEach(function(el) { el.style.display = 'none'; });
                document.querySelectorAll('.inn-waterfall-stage.stage--fta').forEach(function(el) { el.style.display = 'flex'; });
                var b1 = document.getElementById('barMfnDuty');
                if (b1) b1.style.display = 'none';
                var b2 = document.getElementById('barTariffSaved');
                if (b2) b2.style.display = 'flex';
                var tc = document.getElementById('waterfallTotalCost');
                if (tc) tc.innerText = '$4,220.00';
                var sb = document.getElementById('waterfallSavingsBadge');
                if (sb) sb.style.display = 'inline-flex';
                btnWaterfallEvfta.classList.add('active');
                if (btnWaterfallMfn) btnWaterfallMfn.classList.remove('active');
            });
        }

        if (btnWaterfallMfn && !btnWaterfallMfn.dataset.mfnBound) {
            btnWaterfallMfn.dataset.mfnBound = 'true';
            btnWaterfallMfn.addEventListener('click', function () {
                document.querySelectorAll('.inn-waterfall-stage.stage--mfn').forEach(function(el) { el.style.display = 'flex'; });
                document.querySelectorAll('.inn-waterfall-stage.stage--fta').forEach(function(el) { el.style.display = 'none'; });
                var b1 = document.getElementById('barMfnDuty');
                if (b1) b1.style.display = 'flex';
                var b2 = document.getElementById('barTariffSaved');
                if (b2) b2.style.display = 'none';
                var tc = document.getElementById('waterfallTotalCost');
                if (tc) tc.innerText = '$4,700.00';
                var sb = document.getElementById('waterfallSavingsBadge');
                if (sb) sb.style.display = 'none';
                btnWaterfallMfn.classList.add('active');
                if (btnWaterfallEvfta) btnWaterfallEvfta.classList.remove('active');
            });
        }
    }

    function initAllGrcEngines() {
        initTradeComplianceInteractive();
        initOperationalComplianceInteractive();
        initLogisticsJobfileInteractive();
        initWaterfallInteractive();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAllGrcEngines);
    } else {
        initAllGrcEngines();
    }

    window.addEventListener('load', initAllGrcEngines);
})();
