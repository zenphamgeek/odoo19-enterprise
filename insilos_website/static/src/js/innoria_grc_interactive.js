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

        // SVG Circuit Topology Elements
        var lineFeeder4 = section.querySelector('#lineFeeder4');
        var svgNode4 = section.querySelector('#svgNode4');
        var svgNode4Rect = section.querySelector('#svgNode4Rect');
        var svgNode4Title = section.querySelector('#svgNode4Title');
        var svgNode4Sub = section.querySelector('#svgNode4Sub');
        var labelFeeder4Source = section.querySelector('#labelFeeder4Source');
        var vesselStatusFrame = section.querySelector('#vesselStatusFrame');
        var vesselHazardWarning = section.querySelector('#vesselHazardWarning');
        var topologyOverallStatus = section.querySelector('#topologyOverallStatus');
        var gasValLel = section.querySelector('#gasValLel');
        var gasValPress = section.querySelector('#gasValPress');

        var ptwCountdownTimer = null;

        function updateSvgTopologyState(point4Locked) {
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
                    svgNode4Title.textContent = '🔒 V-109 (L-8824)';
                    svgNode4Title.setAttribute('fill', '#A7F3D0');
                }
                if (svgNode4Sub) {
                    svgNode4Sub.textContent = 'Khí Trơ: ĐÃ KHÓA';
                    svgNode4Sub.setAttribute('fill', '#6EE7B7');
                }
                if (labelFeeder4Source) {
                    labelFeeder4Source.textContent = 'KHÍ TRƠ N2 ĐÃ CÔ LẬP KHÓA HÃM';
                    labelFeeder4Source.setAttribute('fill', '#10B981');
                }
                if (vesselStatusFrame) {
                    vesselStatusFrame.setAttribute('stroke', '#10B981');
                }
                if (vesselHazardWarning) {
                    vesselHazardWarning.textContent = '🛡️ ZERO ENERGY VERIFIED';
                    vesselHazardWarning.setAttribute('fill', '#34D399');
                }
                if (topologyOverallStatus) {
                    topologyOverallStatus.className = 'badge px-2 py-1 font-monospace';
                    topologyOverallStatus.style.background = 'rgba(16, 185, 129, 0.2)';
                    topologyOverallStatus.style.color = '#6EE7B7';
                    topologyOverallStatus.style.border = '1px solid #10B981';
                    topologyOverallStatus.textContent = '4/4 ĐÃ CÔ LẬP · AN TOÀN';
                }
                if (gasValLel) {
                    gasValLel.textContent = '0.0% LEL';
                    gasValLel.className = 'fw-bold font-monospace text-success';
                }
                if (gasValPress) {
                    gasValPress.textContent = '0.00 bar';
                    gasValPress.className = 'fw-bold font-monospace text-success';
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
                if (vesselStatusFrame) {
                    vesselStatusFrame.setAttribute('stroke', '#EF4444');
                }
                if (vesselHazardWarning) {
                    vesselHazardWarning.textContent = '⛔ CÒN NĂNG LƯỢNG N2';
                    vesselHazardWarning.setAttribute('fill', '#EF4444');
                }
                if (topologyOverallStatus) {
                    topologyOverallStatus.className = 'badge px-2 py-1 font-monospace';
                    topologyOverallStatus.style.background = 'rgba(239, 68, 68, 0.2)';
                    topologyOverallStatus.style.color = '#FDA4AF';
                    topologyOverallStatus.style.border = '1px solid #EF4444';
                    topologyOverallStatus.textContent = '3/4 CÔ LẬP · CÒN NGUY HIỂM';
                }
                if (gasValLel) {
                    gasValLel.textContent = '1.4% LEL';
                    gasValLel.className = 'fw-bold font-monospace text-warning';
                }
                if (gasValPress) {
                    gasValPress.textContent = '0.35 bar';
                    gasValPress.className = 'fw-bold font-monospace text-danger';
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

        lotoPoints.forEach(function (pt) {
            var toggleBtn = pt.querySelector('.btn-loto-toggle');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', function () {
                    togglePointItem(pt);
                });
            }
        });

        // Click directly on SVG Node 4 to toggle Point 4
        if (svgNode4) {
            svgNode4.addEventListener('click', function () {
                var pt4 = section.querySelector('.loto-point-item[data-point-id="4"]');
                if (pt4) {
                    togglePointItem(pt4);
                }
            });
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
