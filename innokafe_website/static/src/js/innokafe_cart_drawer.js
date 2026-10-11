/** @odoo-module **/
/**
 * InnoKafe Specialty Coffee: Client-Side Interactive Slide-over Cart Drawer Engine
 * ===============================================================================
 * Provides high-performance offcanvas cart drawer state management, dynamic line item
 * steppers, 500k Freeship progress bar calculation, synchronized pack/grind selectors,
 * and seamless checkout trust integration for InnoKafe Enterprise.
 */

(function () {
    'use strict';

    var STORAGE_KEY = 'innokafe_cart_items_v1';
    var FREESHIP_THRESHOLD = 500000;
    var BASE_SHIPPING_FEE = 30000;

    var SKU_DEFAULTS = {
        'INNO-ROBUSTA-NAT-01': {
            name: 'Đắk Lắk Highland Fine Robusta Natural',
            img: '/innokafe_website/static/src/img/beans_robusta_natural.svg',
            prices: { '250': 125000, '500': 235000, '1000': 440000 },
            productId: 1
        },
        'INNO-ARABICA-WASH-02': {
            name: 'Cầu Đất Mountain Bourbon Washed',
            img: '/innokafe_website/static/src/img/beans_arabica_washed.svg',
            prices: { '250': 185000, '500': 350000, '1000': 660000 },
            productId: 2
        },
        'INNO-SIGNATURE-HONEY-03': {
            name: 'Innokafe Heritage Signature Red Honey',
            img: '/innokafe_website/static/src/img/beans_heritage_honey.svg',
            prices: { '250': 155000, '500': 295000, '1000': 550000 },
            productId: 3
        },
        'INNO-DRIP-EXPLORER-04': {
            name: 'Hộp Drip Bag Khám Phá Nghệ Nhân (10 Gói)',
            img: '/innokafe_website/static/src/img/beans_drip_bag.svg',
            prices: { '250': 165000, '500': 310000, '1000': 580000 },
            productId: 4
        },
        'INNO-COLDBREW-CITRUS-05': {
            name: 'Innokafe Cold Brew Blend Summer Citrus',
            img: '/innokafe_website/static/src/img/beans_coldbrew_citrus.svg',
            prices: { '250': 175000, '500': 330000, '1000': 620000 },
            productId: 5
        },
        'INNO-HORECA-BARISTA-06': {
            name: 'Innokafe Espresso Barista Master 80/20',
            img: '/innokafe_website/static/src/img/beans_espresso_barista.svg',
            prices: { '250': 135000, '500': 245000, '1000': 380000 },
            productId: 6
        }
    };

    var GRIND_LABELS = {
        'whole': 'Nguyên Hạt Mộc (Whole Bean)',
        'coldbrew': 'Cold Brew / French Press (900μm)',
        'v60': 'V60 / Drip Bag (800μm)',
        'phin': 'Phin Truyền Thống (650μm)',
        'espresso': 'Espresso (250μm)'
    };

    var PACK_LABELS = {
        '250': 'Túi 250g (Van 1 chiều)',
        '500': 'Túi 500g (Tiết kiệm 12%)',
        '1000': 'Gói 1kg (Tiết kiệm)'
    };

    function loadCart() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    function saveCart(items) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
        } catch (e) {
            // Storage quota or private browsing fallback
        }
    }

    function formatVND(amount) {
        return Number(amount || 0).toLocaleString('vi-VN') + ' đ';
    }

    var InnokafeCartEngine = {
        items: [],

        init: function () {
            this.items = loadCart();
            this.bindEvents();
            this.render();
            this.initCardPriceWatchers();
        },

        bindEvents: function () {
            var self = this;

            // Global delegation for Add to Cart buttons
            document.addEventListener('click', function (e) {
                var addBtn = e.target.closest('.inno-add-cart-btn');
                if (addBtn) {
                    e.preventDefault();
                    self.handleAddBtnClick(addBtn);
                    return;
                }

                // Drawer Close triggers
                if (e.target.closest('.inno-cart-close-btn') || e.target.id === 'inno_cart_backdrop') {
                    e.preventDefault();
                    self.close();
                    return;
                }

                // Stepper quantity increment
                var plusBtn = e.target.closest('.inno-qty-plus');
                if (plusBtn) {
                    e.preventDefault();
                    var lineId = plusBtn.getAttribute('data-line-id');
                    if (lineId) self.updateQty(lineId, 1);
                    return;
                }

                // Stepper quantity decrement
                var minusBtn = e.target.closest('.inno-qty-minus');
                if (minusBtn) {
                    e.preventDefault();
                    var lineId = minusBtn.getAttribute('data-line-id');
                    if (lineId) self.updateQty(lineId, -1);
                    return;
                }

                // Line item remove button
                var removeBtn = e.target.closest('.inno-remove-btn');
                if (removeBtn) {
                    e.preventDefault();
                    var lineId = removeBtn.getAttribute('data-line-id');
                    if (lineId) self.removeItem(lineId);
                    return;
                }

                // Header / Navbar Cart Link interception to open drawer smoothly
                var cartNav = e.target.closest('a[href="/shop/cart"], .o_wsale_my_cart, .my_cart_quantity');
                if (cartNav && !e.target.closest('#innokafe_cart_drawer')) {
                    // If on homepage or products, open drawer instead of redirecting
                    if (window.location.pathname === '/' || window.location.pathname === '/products') {
                        e.preventDefault();
                        self.open();
                    }
                }
            });

            // Escape key closes drawer
            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape' || e.keyCode === 27) {
                    self.close();
                }
            });
        },

        initCardPriceWatchers: function () {
            // Live price display update on pack size change across cards
            document.querySelectorAll('.inno-weight-select').forEach(function (select) {
                select.addEventListener('change', function (e) {
                    var card = e.target.closest('.inno-product-card');
                    if (!card) return;
                    var weight = e.target.value;
                    var price = card.getAttribute('data-price-' + weight);
                    if (price) {
                        var display = card.querySelector('.inno-price-display');
                        if (display) {
                            display.textContent = formatVND(price);
                        }
                    }
                });
            });
        },

        handleAddBtnClick: function (btn) {
            var card = btn.closest('.inno-product-card');
            var sku = btn.getAttribute('data-sku') || (card ? card.getAttribute('data-sku') : 'INNO-ROBUSTA-NAT-01');
            var defaults = SKU_DEFAULTS[sku] || SKU_DEFAULTS['INNO-ROBUSTA-NAT-01'];

            var name = (card && card.getAttribute('data-name')) ||
                       (card && card.querySelector('h3') ? card.querySelector('h3').textContent.trim() : defaults.name);

            var img = (card && card.getAttribute('data-img')) || defaults.img;

            var weightSelect = card ? card.querySelector('.inno-weight-select') : null;
            var pack = weightSelect ? weightSelect.value : '250';
            var packLabel = (weightSelect && weightSelect.options[weightSelect.selectedIndex]) ?
                            weightSelect.options[weightSelect.selectedIndex].text.split(/[-\u2014,]/)[0].trim() :
                            (PACK_LABELS[pack] || pack + 'g');

            var grindSelect = card ? card.querySelector('.inno-grind-select') : null;
            var grind = grindSelect ? grindSelect.value : 'whole';
            var grindLabel = (grindSelect && grindSelect.options[grindSelect.selectedIndex]) ?
                             grindSelect.options[grindSelect.selectedIndex].text.trim() :
                             (GRIND_LABELS[grind] || 'Nguyên Hạt');

            var priceAttr = card ? card.getAttribute('data-price-' + pack) : null;
            var unitPrice = priceAttr ? parseInt(priceAttr, 10) : (defaults.prices[pack] || defaults.prices['250']);
            var productId = parseInt(btn.getAttribute('data-product-id') || (card ? card.getAttribute('data-product-id') : '1'), 10);

            this.addItem({
                sku: sku,
                productId: productId,
                name: name,
                pack: pack,
                packLabel: packLabel,
                grind: grind,
                grindLabel: grindLabel,
                unitPrice: unitPrice,
                img: img,
                quantity: 1
            });

            // Button feedback animation
            var originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="fa fa-check text-dark"></i> <span>Đã Thêm!</span>';
            btn.classList.add('inno-added-pulse');
            setTimeout(function () {
                btn.innerHTML = originalHTML;
                btn.classList.remove('inno-added-pulse');
            }, 1400);

            // Automatically open drawer
            this.open();
        },

        addItem: function (item) {
            var lineId = [item.sku, item.pack, item.grind].join('_');
            var existing = null;
            for (var i = 0; i < this.items.length; i++) {
                if (this.items[i].lineId === lineId) {
                    existing = this.items[i];
                    break;
                }
            }

            if (existing) {
                existing.quantity += (item.quantity || 1);
                if (existing.quantity > 99) existing.quantity = 99;
            } else {
                this.items.push({
                    lineId: lineId,
                    sku: item.sku,
                    productId: item.productId || 1,
                    name: item.name,
                    pack: item.pack,
                    packLabel: item.packLabel,
                    grind: item.grind,
                    grindLabel: item.grindLabel,
                    unitPrice: item.unitPrice,
                    img: item.img,
                    quantity: item.quantity || 1
                });
            }

            saveCart(this.items);
            this.render();
            this.syncOdooBackendCart(item.productId, item.quantity || 1);
        },

        updateQty: function (lineId, delta) {
            for (var i = 0; i < this.items.length; i++) {
                if (this.items[i].lineId === lineId) {
                    this.items[i].quantity += delta;
                    if (this.items[i].quantity <= 0) {
                        this.items.splice(i, 1);
                    } else if (this.items[i].quantity > 99) {
                        this.items[i].quantity = 99;
                    }
                    break;
                }
            }
            saveCart(this.items);
            this.render();
        },

        removeItem: function (lineId) {
            this.items = this.items.filter(function (item) {
                return item.lineId !== lineId;
            });
            saveCart(this.items);
            this.render();
        },

        clear: function () {
            this.items = [];
            saveCart(this.items);
            this.render();
        },

        getCart: function () {
            return this.items;
        },

        getFreeshipProgress: function () {
            var subtotal = 0;
            var totalCount = 0;
            for (var i = 0; i < this.items.length; i++) {
                subtotal += this.items[i].unitPrice * this.items[i].quantity;
                totalCount += this.items[i].quantity;
            }

            var isFreeship = subtotal >= FREESHIP_THRESHOLD;
            var remaining = isFreeship ? 0 : Math.max(0, FREESHIP_THRESHOLD - subtotal);
            var percent = subtotal === 0 ? 0 : Math.min(100, Math.round((subtotal / FREESHIP_THRESHOLD) * 100));
            var shippingFee = (subtotal === 0 || isFreeship) ? 0 : BASE_SHIPPING_FEE;
            var total = subtotal + shippingFee;

            return {
                threshold: FREESHIP_THRESHOLD,
                subtotal: subtotal,
                remaining: remaining,
                percent: percent,
                isFreeship: isFreeship,
                shippingFee: shippingFee,
                total: total,
                totalCount: totalCount
            };
        },

        render: function () {
            var progress = this.getFreeshipProgress();
            var container = document.getElementById('inno_cart_items_container');
            var emptyState = document.getElementById('inno_cart_empty_state');
            var drawer = document.getElementById('innokafe_cart_drawer');

            // Update badge counters across the entire page
            document.querySelectorAll('.inno-cart-badge-count, .my_cart_quantity').forEach(function (el) {
                el.textContent = progress.totalCount;
            });

            // Update Freeship Progress Bar & Text
            var freeshipBar = document.querySelector('.inno-freeship-bar');
            var freeshipPercent = document.querySelector('.inno-freeship-percent');
            var freeshipMsg = document.querySelector('.inno-freeship-msg');

            if (freeshipBar) {
                freeshipBar.style.width = progress.percent + '%';
                freeshipBar.setAttribute('aria-valuenow', progress.percent);
            }
            if (freeshipPercent) {
                freeshipPercent.textContent = progress.percent + '%';
            }
            if (freeshipMsg) {
                if (progress.subtotal === 0) {
                    freeshipMsg.innerHTML = 'Mua thêm <strong>' + formatVND(FREESHIP_THRESHOLD) + '</strong> để được <strong>Miễn Phí Vận Chuyển</strong>';
                } else if (progress.isFreeship) {
                    freeshipMsg.innerHTML = '🎉 Đã đủ điều kiện <strong>Miễn Phí Vận Chuyển Toàn Quốc!</strong>';
                } else {
                    freeshipMsg.innerHTML = 'Mua thêm <strong>' + formatVND(progress.remaining) + '</strong> để được <strong>Miễn Phí Vận Chuyển</strong>';
                }
            }

            // Update Subtotal, Shipping, Total in Footer
            var subtotalEl = document.querySelector('.inno-cart-subtotal');
            var shippingEl = document.querySelector('.inno-cart-shipping');
            var totalEl = document.querySelector('.inno-cart-total');

            if (subtotalEl) subtotalEl.textContent = formatVND(progress.subtotal);
            if (shippingEl) shippingEl.textContent = progress.shippingFee === 0 ? 'Miễn phí (0 đ)' : formatVND(progress.shippingFee);
            if (totalEl) totalEl.textContent = formatVND(progress.total);

            // Render items list or empty state
            if (!container) return;

            if (this.items.length === 0) {
                container.innerHTML = '';
                if (emptyState) emptyState.style.display = 'block';
            } else {
                if (emptyState) emptyState.style.display = 'none';

                var html = '';
                for (var j = 0; j < this.items.length; j++) {
                    var it = this.items[j];
                    var lineTotal = it.unitPrice * it.quantity;

                    html += '<div class="inno-cart-item p-3 rounded-3 bg-black bg-opacity-40 border border-secondary border-opacity-20 d-flex gap-3 align-items-center" data-line-id="' + it.lineId + '">' +
                        '<img src="' + it.img + '" alt="' + it.name + '" class="inno-cart-item-thumb rounded-3 border border-secondary border-opacity-25" style="width: 58px; height: 58px; object-fit: contain; background: rgba(0,0,0,0.5); padding: 4px;" />' +
                        '<div class="flex-grow-1 min-w-0">' +
                            '<div class="d-flex justify-content-between align-items-start mb-1">' +
                                '<h6 class="text-white fw-bold mb-0 text-truncate pe-2" style="font-size: 0.9rem;" title="' + it.name + '">' + it.name + '</h6>' +
                                '<button type="button" class="btn btn-link p-0 text-secondary inno-remove-btn text-decoration-none" data-line-id="' + it.lineId + '" aria-label="Xóa sản phẩm" style="font-size: 1.2rem; line-height: 1;">&times;</button>' +
                            '</div>' +
                            '<div class="d-flex flex-wrap gap-1 mb-2">' +
                                '<span class="badge rounded-pill inno-badge-pack small" style="background: rgba(212, 136, 66, 0.2); color: #E5A93C; border: 1px solid rgba(212, 136, 66, 0.35); font-size: 0.72rem; padding: 2px 7px;">' + it.packLabel + '</span>' +
                                '<span class="badge rounded-pill inno-badge-grind small" style="background: rgba(255, 255, 255, 0.08); color: #F7F2EA; border: 1px solid rgba(255, 255, 255, 0.15); font-size: 0.72rem; padding: 2px 7px;">' + it.grindLabel + '</span>' +
                            '</div>' +
                            '<div class="d-flex justify-content-between align-items-center">' +
                                '<div class="inno-qty-stepper d-inline-flex align-items-center border border-secondary border-opacity-30 rounded-pill bg-black bg-opacity-50 px-2 py-1">' +
                                    '<button type="button" class="btn btn-sm btn-link text-white p-0 inno-qty-minus text-decoration-none" data-line-id="' + it.lineId + '" style="width: 22px; height: 22px; line-height: 1;">-</button>' +
                                    '<span class="px-2 text-white fw-bold small inno-qty-val">' + it.quantity + '</span>' +
                                    '<button type="button" class="btn btn-sm btn-link text-white p-0 inno-qty-plus text-decoration-none" data-line-id="' + it.lineId + '" style="width: 22px; height: 22px; line-height: 1;">+</button>' +
                                '</div>' +
                                '<div class="text-end">' +
                                    '<strong class="inno-amber-text small fw-bold">' + formatVND(lineTotal) + '</strong>' +
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
                }
                container.innerHTML = html;
            }
        },

        open: function () {
            var drawer = document.getElementById('innokafe_cart_drawer');
            var backdrop = document.getElementById('inno_cart_backdrop');
            if (drawer) drawer.classList.add('inno-drawer-open');
            if (backdrop) backdrop.classList.add('inno-backdrop-open');
            document.body.classList.add('inno-cart-opened');
            this.render();
        },

        close: function () {
            var drawer = document.getElementById('innokafe_cart_drawer');
            var backdrop = document.getElementById('inno_cart_backdrop');
            if (drawer) drawer.classList.remove('inno-drawer-open');
            if (backdrop) backdrop.classList.remove('inno-backdrop-open');
            document.body.classList.remove('inno-cart-opened');
        },

        toggle: function () {
            var drawer = document.getElementById('innokafe_cart_drawer');
            if (drawer && drawer.classList.contains('inno-drawer-open')) {
                this.close();
            } else {
                this.open();
            }
        },

        syncOdooBackendCart: function (productId, qty) {
            // Asynchronously dispatch JSON-RPC payload to Odoo website_sale endpoint
            try {
                if (window.fetch) {
                    window.fetch('/shop/cart/add', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify({
                            jsonrpc: '2.0',
                            method: 'call',
                            params: {
                                product_id: productId || 1,
                                add_qty: qty || 1
                            }
                        })
                    }).catch(function () {
                        // Soft-fail: Client localStorage maintains state locally
                    });
                }
            } catch (err) {
                // Ignore background sync errors
            }
        }
    };

    // Expose Global Public API on window
    window.InnokafeCart = InnokafeCartEngine;

    // Auto-initialize on DOM Ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            InnokafeCartEngine.init();
        });
    } else {
        InnokafeCartEngine.init();
    }
})();
