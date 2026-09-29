/**
 * ============================================================================
 * INSILOS ENTERPRISE — HSE SOP & INDUSTRIAL FORMS VAULT CLIENT CONTROLLER
 * ============================================================================
 * Handles filtering, search, SHA-256 copy, and dynamic full-text modal viewing.
 * 100% Sovereign Insilos Branding.
 * ============================================================================
 */
(function () {
    'use strict';

    const MANIFEST_URL = '/insilos_website/static/src/docs/hse/manifest.json';
    let docManifest = null;

    async function loadManifest() {
        if (docManifest) return docManifest;
        try {
            const res = await fetch(MANIFEST_URL);
            if (res.ok) {
                docManifest = await res.json();
            }
        } catch (e) {
            console.warn('Could not prefetch HSE manifest:', e);
        }
        return docManifest || {};
    }

    function initHseVault() {
        const vaultSection = document.getElementById('hse-sop-vault');
        if (!vaultSection) return;

        loadManifest();

        // 1. Filter tabs (All, SOPs, Forms)
        const filterBtns = vaultSection.querySelectorAll('.ins-vault-filter-btn');
        const docCards = vaultSection.querySelectorAll('.ins-doc-card');
        const searchInput = vaultSection.getElementById ? vaultSection.getElementById('ins-vault-search') : vaultSection.querySelector('#ins-vault-search');

        function applyVaultFilter() {
            const activeFilter = vaultSection.querySelector('.ins-vault-filter-btn.active')?.dataset.filter || 'all';
            const query = (searchInput?.value || '').trim().toLowerCase();

            docCards.forEach(card => {
                const category = card.dataset.category; // 'sop' or 'form'
                const code = (card.dataset.code || '').toLowerCase();
                const title = (card.dataset.title || '').toLowerCase();
                const summary = (card.dataset.summary || '').toLowerCase();

                const matchesFilter = (activeFilter === 'all') || (category === activeFilter);
                const matchesQuery = !query || code.includes(query) || title.includes(query) || summary.includes(query);

                if (matchesFilter && matchesQuery) {
                    card.classList.remove('d-none');
                } else {
                    card.classList.add('d-none');
                }
            });
        }

        filterBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                applyVaultFilter();
            });
        });

        if (searchInput) {
            searchInput.addEventListener('input', applyVaultFilter);
        }

        // 2. SHA-256 Copy Trigger
        const copyBtns = vaultSection.querySelectorAll('.ins-copy-sha256-btn');
        copyBtns.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                const hash = btn.dataset.sha256;
                if (!hash) return;
                try {
                    await navigator.clipboard.writeText(hash);
                    const originalText = btn.innerHTML;
                    btn.classList.add('btn-success');
                    btn.classList.remove('btn-outline-secondary');
                    btn.innerHTML = '<span>ĐÃ SAO CHÉP SHA-256</span>';
                    setTimeout(() => {
                        btn.classList.remove('btn-success');
                        btn.classList.add('btn-outline-secondary');
                        btn.innerHTML = originalText;
                    }, 2000);
                } catch (err) {
                    console.error('Clipboard copy failed:', err);
                }
            });
        });

        // 3. View Document Modal Trigger
        const viewBtns = vaultSection.querySelectorAll('.ins-view-doc-btn');
        const modal = document.getElementById('insHseDocModal');
        const modalTitle = document.getElementById('insHseDocModalTitle');
        const modalCode = document.getElementById('insHseDocModalCode');
        const modalHash = document.getElementById('insHseDocModalHash');
        const modalBody = document.getElementById('insHseDocModalBody');
        const modalDownload = document.getElementById('insHseDocModalDownload');
        const modalCopyHash = document.getElementById('insHseDocModalCopyHash');

        viewBtns.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const fileUrl = btn.dataset.url;
                const docCode = btn.dataset.code;
                const docTitle = btn.dataset.title;
                const docHash = btn.dataset.sha256;

                if (modalTitle) modalTitle.textContent = docTitle;
                if (modalCode) modalCode.textContent = docCode;
                if (modalHash) modalHash.textContent = docHash;
                if (modalDownload) modalDownload.href = fileUrl;
                if (modalCopyHash) modalCopyHash.dataset.sha256 = docHash;

                if (modalBody) {
                    modalBody.innerHTML = '<div class="text-center py-5 text-secondary"><div class="spinner-border text-cyan mb-3"></div><p>Đang tải nội dung văn bản kiểm định từ kho lưu trữ...</p></div>';
                }

                // Show Bootstrap modal
                if (window.bootstrap && window.bootstrap.Modal) {
                    const bsModal = window.bootstrap.Modal.getOrCreateInstance(modal);
                    bsModal.show();
                } else if (modal) {
                    modal.style.display = 'block';
                    modal.classList.add('show');
                }

                try {
                    const res = await fetch(fileUrl);
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    const text = await res.text();
                    if (modalBody) {
                        // Render formatted text
                        modalBody.innerHTML = '<pre class="bg-dark p-4 rounded text-white-50 font-monospace small" style="white-space: pre-wrap; word-break: break-word; max-height: 60vh; overflow-y: auto;">' + escapeHtml(text) + '</pre>';
                    }
                } catch (err) {
                    if (modalBody) {
                        modalBody.innerHTML = '<div class="alert alert-danger">Không thể tải nội dung tài liệu: ' + escapeHtml(err.message) + '</div>';
                    }
                }
            });
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;')
                  .replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;')
                  .replace(/'/g, '&#039;');
    }

    function initE2eRuntime() {
        const e2eSection = document.getElementById('e2e-erp-grc-runtime');
        if (!e2eSection) return;

        const tabBtns = e2eSection.querySelectorAll('.ins-e2e-tab-btn');
        const panes = e2eSection.querySelectorAll('.ins-e2e-pane');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const flowId = btn.dataset.flow;
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                panes.forEach(pane => {
                    if (pane.id === `ins-e2e-pane-${flowId}`) {
                        pane.classList.remove('d-none');
                        pane.classList.add('active');
                    } else {
                        pane.classList.add('d-none');
                        pane.classList.remove('active');
                    }
                });
            });
        });
    }

    function initAll() {
        initHseVault();
        initE2eRuntime();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
    window.addEventListener('website_snippets_loaded', initAll);
})();

