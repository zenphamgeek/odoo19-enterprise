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
        tagline: "Bản sắc đại ngàn, vị đậm đà sâu lắng, ngọt sâu hậu vị",
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
        tagline: "Hạt Arabica Cầu Đất, chua thanh hoa nhài, trong trẻo tao nhã",
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
        tagline: "Dòng hạt Heritage Red Honey, mật ong rừng, kem bơ sánh quyện",
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
        tagline: "Phin giấy lọc tiện lợi, cà phê mộc nguyên bản chuẩn Nhật Bản",
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
        tagline: "Hương cam chanh tươi mát, vị ngọt dịu êm sau 24h ủ lạnh",
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
        tagline: "Phối trộn chuyên biệt cho quầy bar, crema dày mịn, chiết xuất ổn định",
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

export const SKU_ALIASES = {
    "inno-heritage-honey-03": "inno-signature-honey-03",
    "heritage-honey-03": "inno-signature-honey-03",
    "heritage-honey": "inno-signature-honey-03",
    "honey-03": "inno-signature-honey-03",
    "inno-espresso-bar-06": "inno-horeca-barista-06",
    "inno-espresso-barista-06": "inno-horeca-barista-06",
    "espresso-bar-06": "inno-horeca-barista-06",
    "espresso-bar": "inno-horeca-barista-06",
    "barista-06": "inno-horeca-barista-06",
    "inno-robusta-nat-01": "inno-robusta-nat-01",
    "robusta-nat-01": "inno-robusta-nat-01",
    "robusta-01": "inno-robusta-nat-01",
    "inno-arabica-wash-02": "inno-arabica-wash-02",
    "arabica-wash-02": "inno-arabica-wash-02",
    "arabica-02": "inno-arabica-wash-02",
    "inno-drip-explorer-04": "inno-drip-explorer-04",
    "drip-explorer-04": "inno-drip-explorer-04",
    "drip-04": "inno-drip-explorer-04",
    "inno-coldbrew-citrus-05": "inno-coldbrew-citrus-05",
    "coldbrew-citrus-05": "inno-coldbrew-citrus-05",
    "coldbrew-05": "inno-coldbrew-citrus-05",
    "1": "inno-robusta-nat-01",
    "2": "inno-arabica-wash-02",
    "3": "inno-signature-honey-03",
    "4": "inno-drip-explorer-04",
    "5": "inno-coldbrew-citrus-05",
    "6": "inno-horeca-barista-06",
};

export function resolveCanonicalSku(code) {
    if (!code) return "";
    const clean = code.trim().toLowerCase().replace(/_/g, "-");
    return SKU_ALIASES[clean] || clean;
}

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
        this.currentResult = null;
        this._toastTimeout = null;
        this.init();
    }

    _loadSkus() {
        const rawJsonEl = document.getElementById("innokafe-skus-data");
        if (rawJsonEl && rawJsonEl.textContent) {
            try {
                let text = rawJsonEl.textContent.trim();
                if (text.includes("&")) {
                    const txt = document.createElement("textarea");
                    txt.innerHTML = text;
                    text = txt.value;
                }
                return JSON.parse(text);
            } catch (e) {
                console.warn("Failed to parse embedded SKUs data, using default:", e);
            }
        }
        return CLIENT_SIGNATURE_SKUS;
    }

    init() {
        this._bindOptionClicks();
        this._bindNavButtons();
        this._bindShareAndCartButtons();
        this._bindPopState();
        this._parseInitialRoute();
    }

    _parseInitialRoute() {
        if (typeof window === "undefined") return;

        const pathname = window.location.pathname;
        const urlParams = new URLSearchParams(window.location.search);
        const hash = window.location.hash || "";

        // Check path-based step routing: /taste-profiler/step/:step
        const stepMatch = pathname.match(/\/taste-profiler\/step\/(\d+)/);
        // Check path-based SKU routing: /taste-profiler/result/:sku or /taste-profiler/sku/:sku
        const resultSkuMatch = pathname.match(/\/taste-profiler\/(?:result|sku)\/([A-Za-z0-9_-]+)/);

        // 1. Direct SKU target param or path
        const rawTargetSku = (resultSkuMatch ? resultSkuMatch[1] : null) || urlParams.get("sku") || urlParams.get("sku_code") || this.root.getAttribute("data-initial-top1");
        if (rawTargetSku) {
            const cleanTarget = resolveCanonicalSku(rawTargetSku);
            const matched = this.skus.find((s) => s.sku_code && s.sku_code.toLowerCase().replace(/_/g, "-") === cleanTarget);
            if (matched) {
                const others = this.skus.filter((s) => s.sku_code !== matched.sku_code);
                const top2 = others[0] || matched;
                this.currentResult = {
                    top1: Object.assign({}, matched, { match_score: 96.5 }),
                    top2: Object.assign({}, top2, { match_score: 89.5 }),
                    all_ranked: this.skus,
                    user_vector: matched.vector,
                };
                this.goToStep(5, false);
                this._renderResultCockpit(this.currentResult);
                return;
            }
        }

        // 2. Direct quiz answers in query params
        const habit = urlParams.get("habit");
        const gear = urlParams.get("gear");
        const flavor = urlParams.get("flavor");
        const caffeine = urlParams.get("caffeine");
        if (habit) this.answers.habit = habit;
        if (gear) this.answers.gear = gear;
        if (flavor) this.answers.flavor = flavor;
        if (caffeine) this.answers.caffeine = caffeine;
        this._syncActiveCards();

        // 3. Step or Result Route
        const initialStepAttr = parseInt(this.root.getAttribute("data-initial-step"), 10);
        const isResultRoute = hash === "#result" || pathname.endsWith("/result") || initialStepAttr === 5;

        if (isResultRoute || (habit && gear && flavor && caffeine)) {
            this.calculateAndShowResult(false);
            return;
        }

        if (stepMatch) {
            const stepNum = parseInt(stepMatch[1], 10);
            if (stepNum >= 1 && stepNum <= 4) {
                this.goToStep(stepNum, false);
                return;
            }
        }

        if (hash.startsWith("#step-")) {
            const stepNum = parseInt(hash.replace("#step-", ""), 10);
            if (stepNum >= 1 && stepNum <= 4) {
                this.goToStep(stepNum, false);
                return;
            }
        }

        const stepToInit = (initialStepAttr >= 1 && initialStepAttr <= 4) ? initialStepAttr : 1;
        this.goToStep(stepToInit, false);
    }

    _syncActiveCards() {
        const optionCards = this.root.querySelectorAll(".profiler-option-card");
        optionCards.forEach((card) => {
            const key = card.getAttribute("data-key");
            const val = card.getAttribute("data-value");
            if (this.answers[key] === val) {
                card.classList.add("active");
            } else {
                card.classList.remove("active");
            }
        });
    }

    _bindPopState() {
        window.addEventListener("popstate", (e) => {
            const pathname = window.location.pathname;
            const stepMatch = pathname.match(/\/taste-profiler\/step\/(\d+)/);
            const resultSkuMatch = pathname.match(/\/taste-profiler\/(?:result|sku)\/([A-Za-z0-9_-]+)/);

            if (resultSkuMatch) {
                const targetSku = resolveCanonicalSku(resultSkuMatch[1]);
                const matched = this.skus.find((s) => s.sku_code && s.sku_code.toLowerCase().replace(/_/g, "-") === targetSku);
                if (matched) {
                    const others = this.skus.filter((s) => s.sku_code !== matched.sku_code);
                    this.currentResult = {
                        top1: Object.assign({}, matched, { match_score: 96.5 }),
                        top2: Object.assign({}, others[0] || matched, { match_score: 89.5 }),
                        all_ranked: this.skus,
                        user_vector: matched.vector,
                    };
                    this.goToStep(5, false);
                    this._renderResultCockpit(this.currentResult);
                    return;
                }
            } else if (stepMatch) {
                const stepNum = parseInt(stepMatch[1], 10);
                if (stepNum >= 1 && stepNum <= 4) {
                    this.goToStep(stepNum, false);
                    return;
                }
            } else if (pathname.endsWith("/result") || (e.state && e.state.step === 5)) {
                if (e.state && e.state.answers) {
                    this.answers = Object.assign({}, this.answers, e.state.answers);
                    this._syncActiveCards();
                }
                this.calculateAndShowResult(false);
                return;
            } else if (pathname === "/taste-profiler" || pathname === "/taste-profiler/" || pathname.endsWith("/quiz") || pathname.endsWith("/start")) {
                this.goToStep(1, false);
                return;
            }

            if (e.state && typeof e.state.step === "number") {
                this.goToStep(e.state.step, false);
                if (e.state.step === 5) {
                    if (e.state.answers) {
                        this.answers = Object.assign({}, this.answers, e.state.answers);
                        this._syncActiveCards();
                    }
                    this.calculateAndShowResult(false);
                }
            } else {
                const hash = window.location.hash || "";
                if (hash.startsWith("#step-")) {
                    const stepNum = parseInt(hash.replace("#step-", ""), 10);
                    if (stepNum >= 1 && stepNum <= 4) {
                        this.goToStep(stepNum, false);
                    }
                } else if (hash === "#result") {
                    this.calculateAndShowResult(false);
                } else {
                    this.goToStep(1, false);
                }
            }
        });
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

        const stepPills = this.root.querySelectorAll(".profiler-step-pill");
        stepPills.forEach((pill) => {
            pill.addEventListener("click", (e) => {
                e.preventDefault();
                const step = parseInt(pill.getAttribute("data-goto-step"), 10);
                if (step >= 1 && step <= 4) {
                    this.goToStep(step);
                } else if (step === 5) {
                    this.calculateAndShowResult();
                }
            });
        });
    }

    _bindShareAndCartButtons() {
        // Copy Link
        const copyBtn = this.root.querySelector(".btn-copy-result-link");
        if (copyBtn) {
            copyBtn.addEventListener("click", () => {
                const top1Code = this.currentResult && this.currentResult.top1
                    ? (this.currentResult.top1.sku_code || this.currentResult.top1.code)
                    : "";
                let shareUrl;
                if (top1Code) {
                    shareUrl = `${window.location.origin}/taste-profiler/result/${top1Code}`;
                } else {
                    const params = new URLSearchParams({
                        habit: this.answers.habit,
                        gear: this.answers.gear,
                        flavor: this.answers.flavor,
                        caffeine: this.answers.caffeine,
                    });
                    shareUrl = `${window.location.origin}/taste-profiler/result?${params.toString()}`;
                }

                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(shareUrl).then(() => {
                        this._showToast("Đã sao chép liên kết hồ sơ vị giác vào bộ nhớ tạm!");
                    }).catch(() => {
                        this._fallbackCopyText(shareUrl);
                    });
                } else {
                    this._fallbackCopyText(shareUrl);
                }
            });
        }

        // Native Web Share API
        const nativeShareBtn = this.root.querySelector(".btn-native-share");
        if (nativeShareBtn && typeof navigator !== "undefined" && navigator.share) {
            nativeShareBtn.classList.remove("d-none");
            nativeShareBtn.addEventListener("click", () => {
                const top1 = this.currentResult && this.currentResult.top1;
                const top1Name = top1 ? top1.name : "Cà Phê Đặc Sản InnoKafe";
                const top1Code = top1 ? (top1.sku_code || top1.code) : "";
                const shareUrl = top1Code
                    ? `${window.location.origin}/taste-profiler/result/${top1Code}`
                    : `${window.location.origin}/taste-profiler/result`;
                navigator.share({
                    title: `Hồ Sơ Vị Giác InnoKafe - ${top1Name}`,
                    text: `Khám phá dòng cà phê mộc phù hợp với khẩu vị của tôi: ${top1Name}`,
                    url: shareUrl,
                }).catch(() => {});
            });
        }

        // Discovery Box Add to Cart
        const discoveryBoxBtn = this.root.querySelector(".btn-discovery-box-add");
        if (discoveryBoxBtn) {
            discoveryBoxBtn.addEventListener("click", (e) => {
                e.preventDefault();
                const pid = parseInt(discoveryBoxBtn.getAttribute("data-product-id") || 4, 10);
                const name = discoveryBoxBtn.getAttribute("data-name") || "Hộp Drip Bag Khám Phá Nghệ Nhân";
                this._addToCart(pid, pid, 1, name);
            });
        }
    }

    _fallbackCopyText(text) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand("copy");
            this._showToast("Đã sao chép liên kết hồ sơ vị giác vào bộ nhớ tạm!");
        } catch (e) {
            this._showToast("Không thể sao chép liên kết, vui lòng copy từ thanh địa chỉ.", false);
        }
        document.body.removeChild(textarea);
    }

    goToStep(step, updateHistory = true) {
        this.currentStep = step;
        this._updateStepView();

        if (updateHistory && typeof window !== "undefined" && window.history) {
            if (step >= 1 && step <= 4) {
                const url = `/taste-profiler/step/${step}`;
                window.history.pushState({ step }, "", url);
            } else if (step === 5) {
                const top1Code = this.currentResult && this.currentResult.top1
                    ? (this.currentResult.top1.sku_code || this.currentResult.top1.code)
                    : "";
                let url;
                if (top1Code) {
                    url = `/taste-profiler/result/${top1Code}`;
                } else {
                    const params = new URLSearchParams({
                        habit: this.answers.habit,
                        gear: this.answers.gear,
                        flavor: this.answers.flavor,
                        caffeine: this.answers.caffeine,
                    });
                    url = `/taste-profiler/result?${params.toString()}`;
                }
                window.history.pushState({ step: 5, answers: this.answers }, "", url);
            }
        }
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

        // Update Step Details (Hero, Breadcrumb, Document Title)
        const stepMeta = {
            1: {
                badge: "BƯỚC 1 / 4 • THÓI QUEN THƯỞNG THỨC",
                title: "Khoảnh Khắc Cà Phê Lý Tưởng Trong Ngày",
                lead: "Bạn tìm kiếm điều gì trong ly cà phê mỗi sáng? Chọn phong cách phản ánh đúng thói quen, nhịp sống và cảm xúc thưởng thức của bạn nhất.",
                breadcrumb: "Bước 1: Phong Cách Thưởng Thức",
                docTitle: "Bước 1: Phong Cách Thưởng Thức | Trắc Nghiệm Cảm Quan SCA | InnoKafe",
                pct: 25,
            },
            2: {
                badge: "BƯỚC 2 / 4 • THIẾT BỊ CHIẾT XUẤT",
                title: "Phương Pháp & Thiết Bị Pha Chế",
                lead: "Dụng cụ chiết xuất quyết định áp suất, thời gian ngâm ủ và kích thước bột xay tối ưu. InnoKafe sẽ căn chỉnh cỡ rang và độ trích ly tương thích tuyệt đối.",
                breadcrumb: "Bước 2: Thiết Bị Pha Chế",
                docTitle: "Bước 2: Thiết Bị Pha Chế | Trắc Nghiệm Cảm Quan SCA | InnoKafe",
                pct: 50,
            },
            3: {
                badge: "BƯỚC 3 / 4 • BẢN ĐỒ KHỨU GIÁC",
                title: "Tông Hương Vị Độc Bản Cuốn Hút Nhất",
                lead: "Khứu giác và vị giác của bạn tìm kiếm nốt hương nào? Chocolate đen 85% ấm nồng, hoa quả tươi sáng hay mật ong caramel ngọt ngào?",
                breadcrumb: "Bước 3: Tông Hương Vị",
                docTitle: "Bước 3: Tông Hương Vị Yêu Thích | Trắc Nghiệm Cảm Quan SCA | InnoKafe",
                pct: 75,
            },
            4: {
                badge: "BƯỚC 4 / 4 • CƯỜNG ĐỘ NĂNG LƯỢNG",
                title: "Mức Độ Tiếp Nhận Caffeine & Độ Đậm Đặc",
                lead: "Bạn cần cú bừng tỉnh mạnh mẽ từ Fine Robusta Cư M'gar, năng lượng êm dịu cân bằng từ Robusta/Arabica blend, hay sự thanh tao từ 100% Arabica núi sương?",
                breadcrumb: "Bước 4: Mức Độ Caffeine",
                docTitle: "Bước 4: Mức Độ Tiếp Nhận Caffeine | Trắc Nghiệm Cảm Quan SCA | InnoKafe",
                pct: 100,
            },
        };

        const heroBadge = document.querySelector(".profiler-hero-badge");
        const heroTitle = document.querySelector(".profiler-hero-title");
        const heroLead = document.querySelector(".profiler-hero-lead");
        const breadcrumbCurrent = document.querySelector(".profiler-breadcrumb-current");

        if (this.currentStep <= 4 && stepMeta[this.currentStep]) {
            const meta = stepMeta[this.currentStep];
            if (heroBadge) heroBadge.textContent = meta.badge;
            if (heroTitle) heroTitle.textContent = meta.title;
            if (heroLead) heroLead.textContent = meta.lead;
            if (breadcrumbCurrent) breadcrumbCurrent.textContent = meta.breadcrumb;
            document.title = meta.docTitle;
        } else if (this.currentStep === 5 && this.currentResult && this.currentResult.top1) {
            const top1 = this.currentResult.top1;
            if (heroBadge) heroBadge.textContent = `HỒ SƠ CẢM QUAN • TƯƠNG THÍCH ${top1.match_score || 96.5}%`;
            if (heroTitle) heroTitle.textContent = `Dòng Hạt Dành Cho Bạn: ${top1.name}`;
            if (heroLead) heroLead.textContent = `${top1.tagline || ""}. Dựa trên bản đồ vị giác và thói quen pha chế của bạn, InnoKafe tự hào giới thiệu dòng specialty rang mộc chuẩn SCA này.`;
            if (breadcrumbCurrent) breadcrumbCurrent.textContent = top1.name;
            document.title = `${top1.name} | Hồ Sơ Cảm Quan Gu Cà Phê | InnoKafe`;
        }

        // Update Step Pills active state
        const stepPills = this.root.querySelectorAll(".profiler-step-pill");
        stepPills.forEach((pill) => {
            const stepNum = parseInt(pill.getAttribute("data-goto-step"), 10);
            if (stepNum === this.currentStep) {
                pill.className = "btn btn-sm flex-fill rounded-pill py-1 px-2 font-monospace profiler-step-pill btn-warning text-dark fw-bold shadow-sm";
            } else if (stepNum < this.currentStep) {
                pill.className = "btn btn-sm flex-fill rounded-pill py-1 px-2 font-monospace profiler-step-pill btn-outline-warning text-warning";
            } else {
                pill.className = "btn btn-sm flex-fill rounded-pill py-1 px-2 font-monospace profiler-step-pill btn-outline-secondary text-secondary";
            }
        });

        // Update Progress Indicator
        const progressBar = this.root.querySelector(".profiler-progress-bar");
        const progressText = this.root.querySelector(".profiler-progress-text");
        if (progressBar) {
            const pct = this.currentStep <= 4 ? this.currentStep * 20 : 100;
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

    async calculateAndShowResult(updateHistory = true) {
        // Show step 5 (Cockpit)
        this.goToStep(5, updateHistory);

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

        this.currentResult = result;
        this._renderResultCockpit(result);
    }

    _renderResultCockpit(result) {
        this.currentResult = result;
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
                top1.price_250g || 125000
            );
        }

        const top1NotesEl = this.root.querySelector(".top1-product-notes");
        if (top1NotesEl && top1.tasting_notes) {
            top1NotesEl.innerHTML = top1.tasting_notes
                .map((n) => `<span class="badge rounded-pill px-3 py-1 inno-inner-panel text-warning border-0">${n}</span>`)
                .join("");
        }

        const top1BrewsEl = this.root.querySelector(".top1-product-brews");
        if (top1BrewsEl && top1.best_brew_labels) {
            top1BrewsEl.innerHTML = top1.best_brew_labels
                .map((b) => `<span class="badge rounded-pill px-3 py-1 bg-dark text-warning border border-secondary">${b}</span>`)
                .join("");
        }

        // Top 1 Product Link
        const top1LinkEl = this.root.querySelector(".top1-product-link");
        if (top1LinkEl && (top1.sku_code || top1.code)) {
            top1LinkEl.href = `/products#${top1.sku_code || top1.code}`;
        }

        // Render Top 2 (Discovery Match) Card
        if (top2) {
            const top2BadgeEl = this.root.querySelector(".top2-match-badge");
            if (top2BadgeEl) top2BadgeEl.textContent = `${top2.match_score}% Khám phá đổi vị`;

            const top2NameEl = this.root.querySelector(".top2-product-name");
            if (top2NameEl) top2NameEl.textContent = top2.name;

            const top2TaglineEl = this.root.querySelector(".top2-product-tagline");
            if (top2TaglineEl) top2TaglineEl.textContent = top2.tagline || "";

            const top2PriceEl = this.root.querySelector(".top2-product-price");
            if (top2PriceEl) {
                top2PriceEl.textContent = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(
                    top2.price_250g || 135000
                );
            }

            // Top 2 Product Link
            const top2LinkEl = this.root.querySelector(".top2-product-link");
            if (top2LinkEl && (top2.sku_code || top2.code)) {
                top2LinkEl.href = `/products#${top2.sku_code || top2.code}`;
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

    _showToast(msg, isSuccess = true, linkHref = null, linkText = null) {
        let toastEl = document.getElementById("innokafe-cart-toast");
        if (!toastEl) {
            toastEl = document.createElement("div");
            toastEl.id = "innokafe-cart-toast";
            document.body.appendChild(toastEl);
        }
        toastEl.className = `alert alert-${isSuccess ? "success" : "warning"} position-fixed bottom-0 end-0 m-3 shadow-lg d-flex align-items-center gap-3`;
        toastEl.style.zIndex = "99999";
        toastEl.style.maxWidth = "480px";

        let html = `<span>${msg}</span>`;
        if (linkHref && linkText) {
            html += `<a href="${linkHref}" class="btn btn-sm btn-light fw-bold text-nowrap ms-auto">${linkText}</a>`;
        }
        toastEl.innerHTML = html;
        toastEl.classList.remove("d-none");
        clearTimeout(this._toastTimeout);
        this._toastTimeout = setTimeout(() => {
            toastEl.classList.add("d-none");
        }, 4500);
    }

    async _addToCart(productId, productTemplateId, quantity, productName) {
        const pid = parseInt(productId, 10);
        const qty = parseInt(quantity || 1, 10);
        const ptid = parseInt(productTemplateId || productId, 10);

        // Try primary /taste-profiler/cart/add endpoint
        try {
            const response = await fetch("/taste-profiler/cart/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {
                        product_id: pid,
                        product_template_id: ptid,
                        quantity: qty,
                    },
                }),
            });
            const data = await response.json();
            if (data && data.result && data.result.status === "success") {
                this._showToast(`Đã thêm "${productName}" vào giỏ hàng!`, true, "/shop/cart", "Xem giỏ hàng →");
                const badge = document.querySelector(".my_cart_quantity");
                if (badge) {
                    badge.textContent = data.result.cart_quantity || (parseInt(badge.textContent || "0", 10) + qty);
                }
                return;
            }
        } catch (err) {
            console.warn("RPC /taste-profiler/cart/add error, trying fallback:", err);
        }

        // Secondary fallback: /shop/cart/add
        try {
            const fallbackResp = await fetch("/shop/cart/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {
                        product_template_id: ptid,
                        product_id: pid,
                        quantity: qty,
                    },
                }),
            });
            const fallbackData = await fallbackResp.json();
            if (fallbackData && (fallbackData.result || !fallbackData.error)) {
                this._showToast(`Đã thêm "${productName}" vào giỏ hàng!`, true, "/shop/cart", "Xem giỏ hàng →");
                const badge = document.querySelector(".my_cart_quantity");
                if (badge) {
                    const current = parseInt(badge.textContent || "0", 10);
                    badge.textContent = current + qty;
                }
                return;
            }
        } catch (err2) {
            console.warn("Fallback cart AJAX failed:", err2);
        }

        // Direct navigation fallback
        window.location.href = `/shop/cart?add_product=${pid}`;
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
