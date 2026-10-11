/** @odoo-module **/

/**
 * ============================================================================
 * INNOKAFE SPECIALTY COFFEE ARTISAN CLUB — 3-STEP SUBSCRIPTION WIZARD
 * Platform: Insilos 20 / Odoo 20 Enterprise (innokafe.insilos.com)
 * ============================================================================
 * State machine managing the 3-step Artisan Subscription Club configurator:
 * - Step 1: Taste Profile Selection (Gu Đậm, Gu Thanh, Mix Khám Phá)
 * - Step 2: Weight Tier, Frequency & Grind Size with Live Pricing Calculations
 * - Step 3: Delivery Information & Welcome Gifts Claim Form
 * - Confirmed State: Executive Member Cockpit with Member ID & Active Specs
 * ============================================================================
 */

export const TASTE_PREFERENCES = {
    dam_ban_sac: {
        code: "dam_ban_sac",
        title: "Gu Đậm Bản Sắc",
        badge: "Fine Robusta Cư M'gar Natural & Honey",
        notes: "Sô-cô-la đen 85%, mật mía nướng, hậu vị bùi béo",
        suitableFor: "Phin truyền thống, Cà phê sữa, Espresso",
    },
    thanh_tuoi_moi: {
        code: "thanh_tuoi_moi",
        title: "Gu Thanh Tươi Mới",
        badge: "Specialty Arabica Cầu Đất Fully Washed",
        notes: "Hoa nhài trắng, cam Bergamot, chua thanh thanh khiết",
        suitableFor: "Pour-over V60, Cold Brew, Drip Bag",
    },
    mix_kham_pha: {
        code: "mix_kham_pha",
        title: "Mix Khám Phá Hàng Tháng",
        badge: "Discovery Flight Rotation",
        notes: "Luân phiên hạt đặc tuyển & Micro-lots độc bản",
        suitableFor: "Người sành muốn thử nghiệm đa tầng hương vị",
    },
};

export const PRICING_TIERS = {
    "500g": {
        price: 390000,
        formatted: "390.000đ",
        label: "500g",
        desc: "2 túi 250g van 1 chiều",
    },
    "1kg": {
        price: 690000,
        formatted: "690.000đ",
        label: "1.000g (1kg)",
        desc: "4 túi 250g hoặc gói 1kg",
    },
};

export const FREQUENCY_LABELS = {
    biweekly: "Mỗi 2 tuần (Bi-weekly)",
    monthly: "Mỗi tháng (Monthly)",
};

export const GRIND_LABELS = {
    whole_bean: "Nguyên hạt mộc (Whole Bean)",
    phin: "Xay Phin truyền thống (650 μm)",
    espresso: "Xay Máy Espresso (250 μm)",
    v60: "Xay Pour-over V60 (800 μm)",
    coldbrew: "Xay Ủ lạnh Cold Brew (1000 μm)",
};

export class InnokafeSubscriptionWizard {
    /**
     * @param {HTMLElement} rootElement - The wizard container element
     */
    constructor(rootElement) {
        this.root = rootElement;
        this.form = rootElement.querySelector("#inno_club_subscription_form");
        this.cockpit = rootElement.querySelector("#inno_subscription_cockpit");
        this.steps = Array.from(rootElement.querySelectorAll(".inno-wizard-step"));
        this.indicators = Array.from(rootElement.querySelectorAll(".inno-step-indicator"));
        this.progressBar = rootElement.querySelector("#inno_wizard_progress_bar");

        // Dynamic price cockpit elements
        this.priceDisplay = rootElement.querySelector("#inno_wizard_price_display");
        this.cycleDisplay = rootElement.querySelector("#inno_wizard_cycle_display");
        this.planBadge = rootElement.querySelector("#inno_summary_plan_badge");

        // Member cockpit confirmation elements
        this.cockpitMemberId = rootElement.querySelector("#inno_cockpit_member_id");
        this.cockpitMemberName = rootElement.querySelector("#inno_cockpit_member_name");
        this.cockpitPrice = rootElement.querySelector("#inno_cockpit_price");
        this.cockpitTaste = rootElement.querySelector("#inno_cockpit_taste");
        this.cockpitSchedule = rootElement.querySelector("#inno_cockpit_schedule");
        this.cockpitGrind = rootElement.querySelector("#inno_cockpit_grind");
        this.cockpitReconfigBtn = rootElement.querySelector("#inno_cockpit_reconfig_btn");
        this.submitBtn = rootElement.querySelector("#inno_club_submit_btn");

        // State Machine variables
        this.currentStep = 1;
        this.maxStepUnlocked = 1;

        this.initEventListeners();
        this.calculatePricing();
        this.checkUrlForSubmittedState();
    }

    /**
     * Attach interactive event listeners
     */
    initEventListeners() {
        if (!this.root) return;

        // 1. Step 1 Taste Card Selection
        const tasteCards = this.root.querySelectorAll(".inno-choice-card");
        tasteCards.forEach((card) => {
            card.addEventListener("click", () => {
                const radio = card.querySelector("input[type='radio']");
                if (radio) {
                    radio.checked = true;
                    this.updateTasteCardStyles();
                }
            });
        });

        // 2. Step 2 Weight & Frequency Radio Changes
        const weightRadios = this.root.querySelectorAll(".inno-radio-weight");
        weightRadios.forEach((r) => {
            r.addEventListener("change", () => {
                this.updateTierBoxStyles();
                this.calculatePricing();
            });
        });

        const freqRadios = this.root.querySelectorAll(".inno-radio-freq");
        freqRadios.forEach((r) => {
            r.addEventListener("change", () => {
                this.updateFreqBoxStyles();
                this.calculatePricing();
            });
        });

        // 3. Navigation Buttons (Next / Prev)
        const nextBtns = this.root.querySelectorAll(".inno-wizard-next-btn");
        nextBtns.forEach((btn) => {
            btn.addEventListener("click", () => {
                const targetStep = parseInt(btn.getAttribute("data-next-step") || (this.currentStep + 1), 10);
                if (this.validateCurrentStep()) {
                    this.goToStep(targetStep);
                }
            });
        });

        const prevBtns = this.root.querySelectorAll(".inno-wizard-prev-btn");
        prevBtns.forEach((btn) => {
            btn.addEventListener("click", () => {
                const targetStep = parseInt(btn.getAttribute("data-prev-step") || (this.currentStep - 1), 10);
                this.goToStep(targetStep);
            });
        });

        // 4. Stepper Header Indicator Clicks (Allow jump if unlocked)
        this.indicators.forEach((ind) => {
            ind.addEventListener("click", () => {
                const targetStep = parseInt(ind.getAttribute("data-indicator-step"), 10);
                if (targetStep <= this.maxStepUnlocked) {
                    this.goToStep(targetStep);
                }
            });
        });

        // 5. AJAX Form Submission
        if (this.form) {
            this.form.addEventListener("submit", (e) => this.handleFormSubmit(e));
        }

        // 6. Cockpit Re-configuration Button
        if (this.cockpitReconfigBtn) {
            this.cockpitReconfigBtn.addEventListener("click", () => {
                if (this.cockpit) this.cockpit.style.display = "none";
                if (this.form) this.form.style.display = "block";
                this.goToStep(1);
            });
        }
    }

    /**
     * Update active visual borders and glow on Taste choice cards
     */
    updateTasteCardStyles() {
        const tasteCards = this.root.querySelectorAll(".inno-choice-card");
        tasteCards.forEach((card) => {
            const radio = card.querySelector("input[type='radio']");
            const icon = card.querySelector(".inno-check-glow i");
            if (radio && radio.checked) {
                card.classList.remove("border-secondary", "border-opacity-25");
                card.classList.add("border-warning");
                if (icon) {
                    icon.className = "fa fa-check-circle text-warning";
                }
            } else {
                card.classList.remove("border-warning");
                card.classList.add("border-secondary", "border-opacity-25");
                if (icon) {
                    icon.className = "fa fa-circle-thin text-secondary";
                }
            }
        });
    }

    /**
     * Update active visual styling on Weight tier boxes
     */
    updateTierBoxStyles() {
        const tierBoxes = this.root.querySelectorAll(".inno-tier-box");
        tierBoxes.forEach((box) => {
            const radio = box.querySelector("input[type='radio']");
            if (radio && radio.checked) {
                box.classList.remove("border-secondary", "border-opacity-25");
                box.classList.add("border-warning");
            } else {
                box.classList.remove("border-warning");
                box.classList.add("border-secondary", "border-opacity-25");
            }
        });
    }

    /**
     * Update active visual styling on Frequency boxes
     */
    updateFreqBoxStyles() {
        const freqBoxes = this.root.querySelectorAll(".inno-freq-box");
        freqBoxes.forEach((box) => {
            const radio = box.querySelector("input[type='radio']");
            if (radio && radio.checked) {
                box.classList.remove("border-secondary", "border-opacity-25");
                box.classList.add("border-warning");
            } else {
                box.classList.remove("border-warning");
                box.classList.add("border-secondary", "border-opacity-25");
            }
        });
    }

    /**
     * Computes recurring subscription price per cycle and updates HUD readouts
     */
    calculatePricing() {
        const selectedWeightRadio = this.root.querySelector(".inno-radio-weight:checked");
        const selectedFreqRadio = this.root.querySelector(".inno-radio-freq:checked");

        const weightKey = selectedWeightRadio ? selectedWeightRadio.value : "500g";
        const freqKey = selectedFreqRadio ? selectedFreqRadio.value : "monthly";

        const tierInfo = PRICING_TIERS[weightKey] || PRICING_TIERS["500g"];
        const freqLabel = FREQUENCY_LABELS[freqKey] || "Mỗi tháng";

        if (this.priceDisplay) {
            this.priceDisplay.textContent = tierInfo.formatted;
        }
        if (this.cycleDisplay) {
            this.cycleDisplay.textContent = "/ kỳ";
        }
        if (this.planBadge) {
            this.planBadge.textContent = `${tierInfo.label} // ${freqLabel.split(" ")[0]} ${freqLabel.split(" ")[1] || ""}`;
        }

        return {
            priceFormatted: tierInfo.formatted,
            priceValue: tierInfo.price,
            weightKey,
            freqKey,
        };
    }

    /**
     * Validate fields in the currently active step
     * @returns {boolean}
     */
    validateCurrentStep() {
        if (this.currentStep === 1) {
            const checkedTaste = this.root.querySelector(".inno-radio-taste:checked");
            return !!checkedTaste;
        }

        if (this.currentStep === 2) {
            const checkedWeight = this.root.querySelector(".inno-radio-weight:checked");
            const checkedFreq = this.root.querySelector(".inno-radio-freq:checked");
            return !!(checkedWeight && checkedFreq);
        }

        if (this.currentStep === 3) {
            const nameInput = this.root.querySelector("#inno_member_name");
            const phoneInput = this.root.querySelector("#inno_phone");
            const emailInput = this.root.querySelector("#inno_email");
            const addrInput = this.root.querySelector("#inno_shipping_address");

            let isValid = true;
            [nameInput, phoneInput, emailInput, addrInput].forEach((inp) => {
                if (inp) {
                    inp.classList.remove("is-invalid");
                    if (!inp.value.trim()) {
                        inp.classList.add("is-invalid");
                        isValid = false;
                    }
                }
            });

            if (emailInput && emailInput.value.trim() && !emailInput.value.includes("@")) {
                emailInput.classList.add("is-invalid");
                isValid = false;
            }

            if (phoneInput && phoneInput.value.trim() && phoneInput.value.trim().length < 8) {
                phoneInput.classList.add("is-invalid");
                isValid = false;
            }

            return isValid;
        }

        return true;
    }

    /**
     * Navigate to specific step (1, 2, or 3)
     * @param {number} stepNumber
     */
    goToStep(stepNumber) {
        if (stepNumber < 1 || stepNumber > 3) return;

        this.currentStep = stepNumber;
        if (stepNumber > this.maxStepUnlocked) {
            this.maxStepUnlocked = stepNumber;
        }

        // 1. Update Step Containers Visibility
        this.steps.forEach((stepEl) => {
            const sNum = parseInt(stepEl.getAttribute("data-step"), 10);
            if (sNum === stepNumber) {
                stepEl.style.display = "block";
            } else {
                stepEl.style.display = "none";
            }
        });

        // 2. Update Header Stepper Indicators
        this.indicators.forEach((ind) => {
            const iNum = parseInt(ind.getAttribute("data-indicator-step"), 10);
            const badge = ind.querySelector(".badge");
            const title = ind.querySelector(".fw-bold.small");

            if (iNum === stepNumber) {
                ind.classList.add("active", "border-warning", "bg-dark");
                ind.classList.remove("border-secondary", "border-opacity-25", "bg-black");
                if (badge) {
                    badge.className = "badge bg-warning text-dark rounded-circle px-2 py-1 fw-bold";
                }
                if (title) {
                    title.className = "fw-bold small text-uppercase text-white d-none d-sm-inline";
                }
            } else if (iNum < stepNumber) {
                ind.classList.remove("active", "border-warning", "bg-dark");
                ind.classList.add("border-secondary", "border-opacity-25", "bg-black");
                if (badge) {
                    badge.className = "badge bg-success text-white rounded-circle px-2 py-1 fw-bold";
                }
                if (title) {
                    title.className = "fw-bold small text-uppercase text-white d-none d-sm-inline";
                }
            } else {
                ind.classList.remove("active", "border-warning", "bg-dark");
                ind.classList.add("border-secondary", "border-opacity-25", "bg-black");
                if (badge) {
                    badge.className = "badge bg-secondary text-white rounded-circle px-2 py-1 fw-bold";
                }
                if (title) {
                    title.className = "fw-bold small text-uppercase text-secondary d-none d-sm-inline";
                }
            }
        });

        // 3. Update Progress Bar Line
        if (this.progressBar) {
            const pct = stepNumber === 1 ? 33 : (stepNumber === 2 ? 66 : 100);
            this.progressBar.style.width = `${pct}%`;
            this.progressBar.setAttribute("aria-valuenow", String(pct));
        }

        // Smooth scroll to top of wizard on mobile
        if (window.innerWidth < 768) {
            this.root.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    /**
     * Intercept and handle AJAX form submission
     * @param {Event} e
     */
    async handleFormSubmit(e) {
        e.preventDefault();

        if (!this.validateCurrentStep()) {
            return;
        }

        // Set Loading State on Submit Button
        const originalBtnHtml = this.submitBtn ? this.submitBtn.innerHTML : "";
        if (this.submitBtn) {
            this.submitBtn.disabled = true;
            this.submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Đang Kích Hoạt...';
        }

        const formData = new FormData(this.form);
        formData.set("is_ajax", "1");

        try {
            const response = await fetch(this.form.action || "/innokafe/subscription/submit", {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (response.ok) {
                const data = await response.json();
                if (data.status === "success") {
                    this.showCockpit(data);
                } else {
                    alert("Có lỗi xảy ra trong quá trình kích hoạt: " + (data.message || "Vui lòng thử lại"));
                    if (this.submitBtn) {
                        this.submitBtn.disabled = false;
                        this.submitBtn.innerHTML = originalBtnHtml;
                    }
                }
            } else {
                // Fallback standard submit if server returns non-JSON or error
                this.form.submit();
            }
        } catch (err) {
            console.warn("AJAX submission network fallback:", err);
            // Submit form natively
            this.form.submit();
        }
    }

    /**
     * Transition smoothly to Member Cockpit Confirmation State
     * @param {Object} data - Response payload from controller
     */
    showCockpit(data) {
        if (this.form) {
            this.form.style.display = "none";
        }

        if (this.cockpit) {
            this.cockpit.style.display = "block";

            if (this.cockpitMemberId) {
                this.cockpitMemberId.textContent = data.sub_id || "INNO-CLUB-2026-CONFIRMED";
            }
            if (this.cockpitMemberName) {
                this.cockpitMemberName.textContent = data.member_name || "Thành Viên InnoKafe";
            }
            if (this.cockpitPrice) {
                this.cockpitPrice.textContent = `${data.price || "390.000 đ"} / kỳ`;
            }
            if (this.cockpitTaste) {
                this.cockpitTaste.textContent = data.taste_preference || "Gu Đậm Bản Sắc";
            }
            if (this.cockpitSchedule) {
                this.cockpitSchedule.textContent = `${data.weight_tier || "500g"} // ${data.frequency || "Mỗi tháng"}`;
            }
            if (this.cockpitGrind) {
                this.cockpitGrind.textContent = data.grind_size || "Nguyên hạt mộc (Whole Bean)";
            }

            this.cockpit.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }

    /**
     * Check URL query parameters for confirmed state upon redirect
     */
    checkUrlForSubmittedState() {
        if (typeof window === "undefined" || !window.location) return;

        const params = new URLSearchParams(window.location.search);
        if (params.get("club_submitted") === "1") {
            const subId = params.get("sub_id") || "INNO-CLUB-2026-ONLINE";
            this.showCockpit({
                sub_id: subId,
                member_name: "Thành Viên InnoKafe",
                price: "390.000 đ",
                taste_preference: "Gu Đậm Bản Sắc",
                weight_tier: "500g",
                frequency: "Mỗi tháng",
                grind_size: "Nguyên hạt mộc",
            });
        }
    }

    /**
     * Scan and initialize all Subscription Wizard instances on the page
     * @param {Document|HTMLElement} [rootNode=document]
     */
    static initAll(rootNode = document) {
        const wizardElements = rootNode.querySelectorAll(".inno-subscription-wizard-section, #inno_subscription_wizard");
        wizardElements.forEach((el) => {
            if (!el.__innoSubscriptionWizardInstance) {
                el.__innoSubscriptionWizardInstance = new InnokafeSubscriptionWizard(el);
            }
        });
    }
}

// Auto-initialize when DOM is ready
if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => InnokafeSubscriptionWizard.initAll());
    } else {
        InnokafeSubscriptionWizard.initAll();
    }
}

export default InnokafeSubscriptionWizard;
