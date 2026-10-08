/** @odoo-module **/

import { InnokafeSensoryWheel } from "./sensory_wheel";

/**
 * Innokafe Interactive Coffee Taste Profiler Engine
 * Implements the 7D Euclidean Vector Matchmaking Algorithm
 * Runs completely in-page without reload.
 */

const WEIGHTS = {
    body: 1.2,
    acidity: 1.3,
    sweetness: 1.0,
    caffeine: 1.1,
    nutty_choco: 1.0,
    fruity_floral: 1.0,
    balance: 0.9,
};
const D_MAX = 24.6475; // sqrt(sum(w_j * 9^2))

export const CLIENT_SIGNATURE_SKUS = [
    {
        sku_code: "INNO-ROBUSTA-NAT-01",
        name: "Đắk Lắk Highland Fine Robusta Natural",
        tagline: "Bản sắc đại ngàn — Vị đậm đà ngút ngàn, ngọt sâu hậu vị",
        origin: "Cư M'gar, Đắk Lắk (Độ cao 750m)",
        varietal: "Robusta Sẻ thuần chủng",
        process: "Natural (Phơi khô nguyên quả 28 ngày trên giàn)",
        roast_level: "Medium-Dark (Agtron 48)",
        cupping_score: 84.50,
        tasting_notes: ["Sô-cô-la đen 85%", "Hạt dẻ nướng", "Mật mía", "Gỗ sồi"],
        vector: { body: 9.5, acidity: 3.5, sweetness: 8.5, caffeine: 9.5, nutty_choco: 9.0, fruity_floral: 3.0, balance: 7.5 },
        sensory_scores: { aroma: 8.5, acidity: 3.5, body: 9.5, sweetness: 8.5, cleancup: 8.0, aftertaste: 9.0 },
        price_250g: 125000,
        price_500g: 235000,
        price_1kg: 440000,
        best_brew: ["phin", "espresso"],
        best_brew_labels: ["Phin truyền thống", "Cà phê sữa đá", "Espresso"],
        image_url: "/innokafe_website/static/src/img/beans_robusta_natural.svg",
    },
    {
        sku_code: "INNO-ARABICA-WASH-02",
        name: "Cầu Đất Mountain Bourbon Washed",
        tagline: "Tinh hoa sương mù — Chua thanh hoa nhài, trong trẻo tao nhã",
        origin: "Trạm Hành, Cầu Đất, Lâm Đồng (Độ cao 1.620m)",
        varietal: "Arabica Bourbon & Catimor",
        process: "Fully Washed (Lên men kiểm soát 32 giờ, phơi giàn 14 ngày)",
        roast_level: "Light-Medium (Agtron 72)",
        cupping_score: 86.75,
        tasting_notes: ["Hoa nhài trắng", "Cam Bergamot", "Táo xanh", "Trà Earl Grey"],
        vector: { body: 6.0, acidity: 9.0, sweetness: 8.0, caffeine: 3.5, nutty_choco: 3.0, fruity_floral: 9.5, balance: 8.5 },
        sensory_scores: { aroma: 9.5, acidity: 9.0, body: 6.0, sweetness: 8.0, cleancup: 9.5, aftertaste: 8.5 },
        price_250g: 185000,
        price_500g: 350000,
        price_1kg: 660000,
        best_brew: ["pourover", "dripbag", "coldbrew"],
        best_brew_labels: ["Pour-over V60", "Cold Brew", "Drip Bag"],
        image_url: "/innokafe_website/static/src/img/beans_arabica_washed.svg",
    },
    {
        sku_code: "INNO-SIGNATURE-HONEY-03",
        name: "Innokafe Heritage Signature Red Honey",
        tagline: "Khúc giao hòa đỉnh cao — Ngọt ngào mật ong rừng, kem bơ sánh quyện",
        origin: "Blend 70% Cầu Đất Arabica x 30% Cư M'gar Robusta",
        varietal: "Catimor x Robusta Sẻ",
        process: "Red Honey (Giữ 75% lớp nhầy đường, phơi chậm 18 ngày)",
        roast_level: "Medium Roast (Agtron 58)",
        cupping_score: 85.50,
        tasting_notes: ["Mật ong rừng", "Caramel bơ", "Táo đỏ", "Hạnh nhân"],
        vector: { body: 8.0, acidity: 6.8, sweetness: 9.2, caffeine: 6.5, nutty_choco: 7.5, fruity_floral: 7.0, balance: 9.0 },
        sensory_scores: { aroma: 9.0, acidity: 6.8, body: 8.0, sweetness: 9.2, cleancup: 8.8, aftertaste: 8.8 },
        price_250g: 155000,
        price_500g: 295000,
        price_1kg: 550000,
        best_brew: ["espresso", "phin", "pourover", "dripbag"],
        best_brew_labels: ["Espresso", "Phin hiện đại", "Americano", "Pour-over"],
        image_url: "/innokafe_website/static/src/img/beans_heritage_honey.svg",
    },
    {
        sku_code: "INNO-DRIP-EXPLORER-04",
        name: "Hộp Drip Bag Khám Phá Nghệ Nhân (Artisan Box 10 Gói)",
        tagline: "Tiện lợi mọi lúc mọi nơi — Đẳng cấp cà phê phin giấy lọc Nhật Bản",
        origin: "Đa vùng trồng (Cầu Đất, Đắk Lắk)",
        varietal: "Tuyển tập Arabica & Fine Robusta",
        process: "Phối trộn 3 phương pháp sơ chế",
        roast_level: "Medium (Agtron 62)",
        cupping_score: 85.00,
        tasting_notes: ["Caramel", "Hạt dẻ", "Quả mọng", "Hương hoa"],
        vector: { body: 7.5, acidity: 7.0, sweetness: 8.2, caffeine: 6.0, nutty_choco: 7.0, fruity_floral: 7.0, balance: 8.5 },
        sensory_scores: { aroma: 8.8, acidity: 7.0, body: 7.5, sweetness: 8.2, cleancup: 9.0, aftertaste: 8.2 },
        price_250g: 165000,
        price_500g: 165000,
        price_1kg: 165000,
        best_brew: ["dripbag"],
        best_brew_labels: ["Phin giấy Drip Bag", "Pha nhanh văn phòng"],
        image_url: "/innokafe_website/static/src/img/beans_drip_bag.svg",
    },
    {
        sku_code: "INNO-COLDBREW-CITRUS-05",
        name: "Innokafe Cold Brew Blend Summer Citrus",
        tagline: "Sảng khoái mùa hè — Chua ngọt bùng nổ, ủ lạnh 24h ngọt ngào",
        origin: "Cầu Đất, Lâm Đồng (Độ cao 1.550m)",
        varietal: "100% Arabica Catimor",
        process: "Natural x Washed Blend",
        roast_level: "Light (Agtron 78)",
        cupping_score: 86.00,
        tasting_notes: ["Cam vàng Valencia", "Đào chín", "Mật hoa dại", "Hương chanh"],
        vector: { body: 5.5, acidity: 8.5, sweetness: 9.0, caffeine: 4.5, nutty_choco: 3.5, fruity_floral: 9.0, balance: 8.5 },
        sensory_scores: { aroma: 9.2, acidity: 8.5, body: 5.5, sweetness: 9.0, cleancup: 9.2, aftertaste: 8.0 },
        price_250g: 175000,
        price_500g: 330000,
        price_1kg: 620000,
        best_brew: ["coldbrew", "pourover", "dripbag"],
        best_brew_labels: ["Ủ lạnh Cold Brew", "Espresso Tonic", "Pour-over"],
        image_url: "/innokafe_website/static/src/img/beans_coldbrew_citrus.svg",
    },
    {
        sku_code: "INNO-HORECA-BARISTA-06",
        name: "Innokafe Espresso Barista Master 80/20",
        tagline: "Chuẩn mực quầy bar chuyên nghiệp — Crema dày mịn, ổn định chiết xuất",
        origin: "80% Cư M'gar Robusta Sẻ x 20% Cầu Đất Arabica",
        varietal: "Fine Robusta & Catimor",
        process: "Honey & Natural",
        roast_level: "Medium-Dark (Agtron 50)",
        cupping_score: 84.00,
        tasting_notes: ["Ca cao đắng 70%", "Bơ đậu phộng", "Caramel khói", "Vỏ cam sấy"],
        vector: { body: 9.2, acidity: 4.0, sweetness: 8.0, caffeine: 8.8, nutty_choco: 8.8, fruity_floral: 4.0, balance: 8.0 },
        sensory_scores: { aroma: 8.2, acidity: 4.0, body: 9.2, sweetness: 8.0, cleancup: 8.2, aftertaste: 8.8 },
        price_250g: 135000,
        price_500g: 245000,
        price_1kg: 380000,
        best_brew: ["espresso", "phin"],
        best_brew_labels: ["Máy pha Espresso", "Latte / Cappuccino", "Phin quán"],
        image_url: "/innokafe_website/static/src/img/beans_espresso_barista.svg",
    },
];

export class InnokafeTasteProfiler {
    constructor(rootElement) {
        this.root = typeof rootElement === "string" ? document.querySelector(rootElement) : rootElement;
        if (!this.root) return;

        this.currentStep = 1;
        this.answers = {
            habit: "phin_dam",
            gear: "phin",
            flavor: "nutty_choco",
            caffeine: "high",
        };

        this.skus = this._loadSkus();
        this.sensoryWheelInstance = null;
        this.init();
    }

    _loadSkus() {
        const rawJsonEl = document.getElementById("innokafe-skus-data");
        if (rawJsonEl && rawJsonEl.textContent) {
            try {
                return JSON.parse(rawJsonEl.textContent);
            } catch (e) {
                console.warn("Failed to parse embedded SKUs data, using default:", e);
            }
        }
        return CLIENT_SIGNATURE_SKUS;
    }

    init() {
        this._bindOptionClicks();
        this._bindNavButtons();
        this._updateStepView();
    }

    _bindOptionClicks() {
        const optionCards = this.root.querySelectorAll(".profiler-option-card");
        optionCards.forEach((card) => {
            card.addEventListener("click", (e) => {
                const step = parseInt(card.getAttribute("data-step"), 10);
                const key = card.getAttribute("data-key");
                const val = card.getAttribute("data-value");

                // Update selected UI inside this step
                const parentStep = card.closest(".profiler-step-content");
                if (parentStep) {
                    parentStep.querySelectorAll(".profiler-option-card").forEach((c) => {
                        c.classList.remove("active");
                    });
                }
                card.classList.add("active");

                // Save answer
                this.answers[key] = val;

                // Tactile feedback & Auto-advance after 350ms
                card.style.transform = "scale(0.98)";
                setTimeout(() => {
                    card.style.transform = "";
                    if (step < 4) {
                        this.goToStep(step + 1);
                    } else if (step === 4) {
                        this.calculateAndShowResult();
                    }
                }, 350);
            });
        });
    }

    _bindNavButtons() {
        const prevBtns = this.root.querySelectorAll(".btn-profiler-prev");
        prevBtns.forEach((btn) => {
            btn.addEventListener("click", () => {
                if (this.currentStep > 1) {
                    this.goToStep(this.currentStep - 1);
                }
            });
        });

        const resetBtn = this.root.querySelector(".btn-profiler-restart");
        if (resetBtn) {
            resetBtn.addEventListener("click", () => {
                this.goToStep(1);
            });
        }
    }

    goToStep(step) {
        this.currentStep = step;
        this._updateStepView();
    }

    _updateStepView() {
        // Update Step visibility
        const stepPanels = this.root.querySelectorAll(".profiler-step-content");
        stepPanels.forEach((panel) => {
            const stepNum = parseInt(panel.getAttribute("data-step-panel"), 10);
            if (stepNum === this.currentStep) {
                panel.classList.remove("d-none");
                panel.style.opacity = "1";
                panel.style.transform = "none";
            } else {
                panel.classList.add("d-none");
            }
        });

        // Hide result cockpit if navigating steps 1-4
        const resultCockpit = this.root.querySelector(".profiler-result-cockpit");
        if (resultCockpit) {
            if (this.currentStep === 5) {
                resultCockpit.classList.remove("d-none");
            } else {
                resultCockpit.classList.add("d-none");
            }
        }

        // Update Progress Indicator
        const progressBar = this.root.querySelector(".profiler-progress-bar");
        const progressText = this.root.querySelector(".profiler-progress-text");
        if (progressBar) {
            const pct = Math.min(100, Math.round(((this.currentStep - 1) / 4) * 100));
            progressBar.style.width = `${pct}%`;
        }
        if (progressText) {
            if (this.currentStep <= 4) {
                progressText.textContent = `Bước ${this.currentStep} / 4`;
            } else {
                progressText.textContent = "Hoàn tất kết quả";
            }
        }

        // Scroll to quiz container smoothly
        const topEl = this.root.querySelector(".profiler-quiz-container");
        if (topEl && this.currentStep > 1) {
            topEl.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    calculateClientSide() {
        const u = {
            body: 5.0,
            acidity: 5.0,
            sweetness: 5.0,
            caffeine: 5.0,
            nutty_choco: 5.0,
            fruity_floral: 5.0,
            balance: 5.0,
        };

        // Routine
        const { habit, gear, flavor, caffeine } = this.answers;
        if (habit === "phin_dam") {
            u.body += 4.0;
            u.caffeine += 3.0;
            u.acidity -= 2.0;
            u.nutty_choco += 3.0;
        } else if (habit === "sua_da") {
            u.sweetness += 4.0;
            u.body += 3.0;
            u.nutty_choco += 4.0;
            u.acidity -= 3.0;
        } else if (habit === "den_thanh") {
            u.acidity += 4.0;
            u.fruity_floral += 4.0;
            u.body -= 2.0;
            u.balance += 2.0;
        } else if (habit === "coldbrew_sangtao") {
            u.sweetness += 3.0;
            u.fruity_floral += 3.0;
            u.balance += 3.0;
            u.acidity += 1.0;
        }

        // Flavor
        if (flavor === "nutty_choco") {
            u.nutty_choco += 4.0;
            u.body += 2.0;
            u.acidity -= 2.0;
        } else if (flavor === "fruity_floral") {
            u.fruity_floral += 4.5;
            u.acidity += 3.5;
            u.balance += 1.0;
        } else if (flavor === "honey_balanced") {
            u.sweetness += 4.0;
            u.balance += 4.0;
            u.body += 1.0;
        }

        // Caffeine
        if (caffeine === "high") u.caffeine = 9.5;
        else if (caffeine === "medium") u.caffeine = 6.0;
        else if (caffeine === "low") u.caffeine = 3.0;

        // Clamp user vector
        for (const k in u) {
            u[k] = Math.max(1.0, Math.min(10.0, u[k]));
        }

        // Match against SKUs
        const ranked = this.skus.map((item) => {
            const pVec = item.vector || { body: 8, acidity: 5, sweetness: 8, caffeine: 7, nutty_choco: 7, fruity_floral: 5, balance: 8 };
            let distSq = 0;
            for (const dim in WEIGHTS) {
                const diff = (u[dim] || 5.0) - (pVec[dim] || 5.0);
                distSq += WEIGHTS[dim] * diff * diff;
            }
            const dist = Math.sqrt(distSq);

            const isGearMatch = !gear || (item.best_brew && item.best_brew.includes(gear));
            const gamma = isGearMatch ? 1.0 : 0.88;

            const baseSim = (1.0 - dist / D_MAX) * 100.0 * gamma;
            const matchScore = Math.min(94.0, Math.max(85.0, baseSim * 0.285 + 68.35));

            return Object.assign({}, item, {
                match_score: Math.round(matchScore * 10) / 10,
                dist: Math.round(dist * 10) / 10,
            });
        });

        ranked.sort((a, b) => b.match_score - a.match_score);
        return {
            top1: ranked[0],
            top2: ranked[1] || ranked[0],
            all_ranked: ranked,
            user_vector: u,
        };
    }

    async calculateAndShowResult() {
        // Show step 5 (Cockpit)
        this.goToStep(5);

        let result = null;
        try {
            // Try fetching from server JSON endpoint
            const res = await fetch("/taste-profiler/match", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: this.answers,
                }),
            });
            const data = await res.json();
            if (data && data.result && data.result.top1) {
                result = data.result;
            }
        } catch (e) {
            console.warn("Backend match RPC fallback to client calculation:", e);
        }

        if (!result) {
            result = this.calculateClientSide();
        }

        this._renderResultCockpit(result);
    }

    _renderResultCockpit(result) {
        const { top1, top2 } = result;

        // Render Top 1 (Perfect Match) Card
        const top1ScoreEl = this.root.querySelector(".top1-match-badge");
        if (top1ScoreEl) {
            top1ScoreEl.textContent = `${top1.match_score}% Tương thích`;
        }

        const top1NameEl = this.root.querySelector(".top1-product-name");
        if (top1NameEl) top1NameEl.textContent = top1.name;

        const top1TaglineEl = this.root.querySelector(".top1-product-tagline");
        if (top1TaglineEl) top1TaglineEl.textContent = top1.tagline || "";

        const top1OriginEl = this.root.querySelector(".top1-product-origin");
        if (top1OriginEl) top1OriginEl.textContent = top1.origin || "";

        const top1CuppingEl = this.root.querySelector(".top1-product-cupping");
        if (top1CuppingEl) top1CuppingEl.textContent = top1.cupping_score ? `${top1.cupping_score} điểm SCA` : "Specialty";

        const top1ProcessEl = this.root.querySelector(".top1-product-process");
        if (top1ProcessEl) top1ProcessEl.textContent = top1.process || "";

        const top1PriceEl = this.root.querySelector(".top1-product-price");
        if (top1PriceEl) {
            top1PriceEl.textContent = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(
                top1.price_250g || 145000
            );
        }

        const top1NotesEl = this.root.querySelector(".top1-product-notes");
        if (top1NotesEl && top1.tasting_notes) {
            top1NotesEl.innerHTML = top1.tasting_notes
                .map((n) => `<span class="badge bg-espresso-subtle text-amber rounded-pill px-3 py-1 me-1 mb-1 border border-subtle">${n}</span>`)
                .join("");
        }

        // Render Top 2 (Discovery Match) Card
        if (top2) {
            const top2BadgeEl = this.root.querySelector(".top2-match-badge");
            if (top2BadgeEl) top2BadgeEl.textContent = `${top2.match_score}% Khám phá`;

            const top2NameEl = this.root.querySelector(".top2-product-name");
            if (top2NameEl) top2NameEl.textContent = top2.name;

            const top2TaglineEl = this.root.querySelector(".top2-product-tagline");
            if (top2TaglineEl) top2TaglineEl.textContent = top2.tagline || "";

            const top2PriceEl = this.root.querySelector(".top2-product-price");
            if (top2PriceEl) {
                top2PriceEl.textContent = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(
                    top2.price_250g || 155000
                );
            }
        }

        // Render Sensory Wheel Radar
        const wheelContainer = this.root.querySelector(".profiler-sensory-wheel-target");
        if (wheelContainer && top1.sensory_scores) {
            wheelContainer.innerHTML = "";
            this.sensoryWheelInstance = new InnokafeSensoryWheel(wheelContainer, top1.sensory_scores, {
                width: 280,
                height: 280,
                centerX: 140,
                centerY: 140,
                radius: 88,
            });
        }

        // Bind Add-to-Cart Action
        const top1CartBtn = this.root.querySelector(".btn-top1-add-to-cart");
        if (top1CartBtn) {
            top1CartBtn.onclick = (e) => {
                e.preventDefault();
                this._addToCart(
                    top1.product_id || 1,
                    top1.product_tmpl_id || top1.product_id || 1,
                    1,
                    top1.name
                );
            };
        }

        const top2CartBtn = this.root.querySelector(".btn-top2-add-to-cart");
        if (top2CartBtn && top2) {
            top2CartBtn.onclick = (e) => {
                e.preventDefault();
                this._addToCart(
                    top2.product_id || 1,
                    top2.product_tmpl_id || top2.product_id || 1,
                    1,
                    top2.name
                );
            };
        }
    }

    async _addToCart(productId, productTemplateId, quantity, productName) {
        const toastEl = document.getElementById("innokafe-cart-toast");
        const showToast = (msg, success = true) => {
            if (!toastEl) {
                alert(msg);
                return;
            }
            toastEl.textContent = msg;
            toastEl.className = `alert alert-${success ? "success" : "warning"} position-fixed bottom-0 end-0 m-3 shadow-lg`;
            toastEl.style.zIndex = "9999";
            toastEl.classList.remove("d-none");
            setTimeout(() => toastEl.classList.add("d-none"), 3500);
        };

        try {
            const response = await fetch("/shop/cart/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {
                        product_template_id: parseInt(productTemplateId || productId, 10),
                        product_id: parseInt(productId, 10),
                        quantity: parseInt(quantity, 10),
                    },
                }),
            });
            const data = await response.json();
            if (data.result || !data.error) {
                showToast(`✓ Đã thêm "${productName}" vào giỏ hàng thành công!`);
                // Update badge if website cart counter exists
                const badge = document.querySelector(".my_cart_quantity");
                if (badge) {
                    const current = parseInt(badge.textContent || "0", 10);
                    badge.textContent = current + 1;
                }
            } else {
                window.location.href = `/shop/cart?add_product=${productId}`;
            }
        } catch (err) {
            console.warn("Cart AJAX fallback:", err);
            // Fallback: direct form navigation
            window.location.href = `/shop/cart?add_product=${productId}`;
        }
    }
}

export function initInnokafeProfiler() {
    if (typeof document === "undefined") return;
    const profilerRoot = document.querySelector(".innokafe-profiler-root");
    if (profilerRoot && !profilerRoot.__innokafe_profiler_init) {
        profilerRoot.__innokafe_profiler_init = true;
        new InnokafeTasteProfiler(profilerRoot);
    }
}

if (typeof window !== "undefined") {
    window.InnokafeTasteProfiler = InnokafeTasteProfiler;
    window.initInnokafeProfiler = initInnokafeProfiler;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initInnokafeProfiler);
    } else {
        initInnokafeProfiler();
    }
    window.addEventListener("load", initInnokafeProfiler);
}

export default InnokafeTasteProfiler;
