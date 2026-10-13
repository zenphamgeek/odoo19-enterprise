/** @odoo-module **/

/**
 * InnoKafe B2B Solutions Interactive Engine & Wholesale ROI Calculator
 * ====================================================================
 * 1. Dynamic Volume & Blend Pricing Calculator
 * 2. Real-time Tier Evaluation & Cost-per-Cup Estimation
 * 3. Equipment Sponsorship & Monthly ROI Savings Projection
 * 4. Seamless Pre-selection & Two-Way Binding with B2B Lead Form
 */

const TIERS = [
    {
        tier: 1,
        name: "Tier 1: Bronze",
        badge: "Tier 1: Bronze (-18%)",
        minVol: 10,
        maxVol: 29,
        discount: 0.18,
        badgeBg: "#3D2B1F",
        badgeBorder: "#D48842",
        formVol: "Dưới 20 kg/tháng",
        formService: "Đăng ký nhận Mẫu Thử B2B Miễn Phí",
        perks: [
            "Túi 1kg van một chiều Thụy Sĩ tiêu chuẩn specialty",
            "Chứng nhận nguồn gốc nông trại & an toàn thực phẩm",
            "Giao hàng định kỳ hàng tuần ổn định"
        ]
    },
    {
        tier: 2,
        name: "Tier 2: Silver",
        badge: "Tier 2: Silver (-25%)",
        minVol: 30,
        maxVol: 79,
        discount: 0.25,
        badgeBg: "#1F382B",
        badgeBorder: "#10B981",
        formVol: "20 - 50 kg/tháng",
        formService: "Gói tài trợ máy pha Espresso 0đ",
        perks: [
            "Tài trợ máy pha 1-Group 0đ (Nuova Simonelli / Expobar)",
            "Miễn phí vận chuyển nội thành hàng tuần",
            "Tặng bộ Barista Pro trị giá 3.500.000đ"
        ]
    },
    {
        tier: 3,
        name: "Tier 3: Gold",
        badge: "Tier 3: Gold (-32%)",
        minVol: 80,
        maxVol: 199,
        discount: 0.32,
        badgeBg: "#3D2808",
        badgeBorder: "#E5A93C",
        formVol: "50 - 100 kg/tháng",
        formService: "Gói tài trợ máy pha Espresso 0đ",
        perks: [
            "Tài trợ máy pha 2-Groups 0đ (Sanremo / La Marzocco)",
            "Bảo dưỡng định kỳ miễn phí hàng tháng",
            "Đào tạo Barista miễn phí trọn đời cho nhân sự quán"
        ]
    },
    {
        tier: 4,
        name: "Tier 4: Platinum",
        badge: "Tier 4: Platinum (-38%)",
        minVol: 200,
        maxVol: 9999,
        discount: 0.38,
        badgeBg: "#0C2E3B",
        badgeBorder: "#00F2FE",
        formVol: "Trên 100 kg/tháng",
        formService: "Gói tài trợ máy pha Espresso 0đ",
        perks: [
            "Tài trợ trọn gói hệ thống máy pha 2-3 Groups + máy xay Mythos",
            "Thiết kế riêng Roast Profile độc quyền cho thương hiệu",
            "In ấn logo Co-branding chuyên nghiệp trên bao bì"
        ]
    }
];

function formatVND(amount) {
    return new Intl.NumberFormat('vi-VN').format(Math.round(amount)) + ' đ';
}

function initB2BCalculator() {
    const calcSection = document.getElementById('b2b_calculator');
    if (!calcSection) return;

    const volumeSlider = document.getElementById('b2b_calc_volume');
    const volLabel = document.getElementById('b2b_calc_vol_label');
    const tierBadge = document.getElementById('b2b_calc_tier_badge');
    const netPriceEl = document.getElementById('b2b_calc_net_price');
    const basePriceEl = document.getElementById('b2b_calc_base_price');
    const costPerCupEl = document.getElementById('b2b_calc_cost_per_cup');
    const monthlyCostEl = document.getElementById('b2b_calc_monthly_cost');
    const monthlySavingsEl = document.getElementById('b2b_calc_monthly_savings');
    const perksEl = document.getElementById('b2b_calc_perks');
    const applyBtn = document.getElementById('b2b_calc_apply_btn');
    const presetButtons = document.querySelectorAll('.b2b-preset-vol');
    const blendCards = document.querySelectorAll('.b2b-blend-card');

    let currentVolume = parseInt(volumeSlider ? volumeSlider.value : 50, 10) || 50;
    let currentBasePrice = 350000;
    let currentBlendName = "Heritage Red Honey";

    function getTier(vol) {
        for (let i = TIERS.length - 1; i >= 0; i--) {
            if (vol >= TIERS[i].minVol) {
                return TIERS[i];
            }
        }
        return TIERS[0];
    }

    function recalculate() {
        const tier = getTier(currentVolume);
        const netPrice = currentBasePrice * (1 - tier.discount);
        const costPerCup = netPrice * 0.018; // 18g espresso dose
        const monthlyCost = netPrice * currentVolume;
        const monthlySavings = (currentBasePrice * currentVolume) - monthlyCost;

        // Update Volume Label
        if (volLabel) {
            volLabel.textContent = `${currentVolume} kg / tháng`;
        }

        // Update Tier Badge
        if (tierBadge) {
            tierBadge.textContent = tier.badge;
            tierBadge.style.backgroundColor = tier.badgeBg;
            tierBadge.style.borderColor = tier.badgeBorder;
        }

        // Update Prices
        if (netPriceEl) {
            netPriceEl.innerHTML = `${formatVND(netPrice)}<span class="small fs-6 fw-normal text-muted">/kg</span>`;
        }
        if (basePriceEl) {
            basePriceEl.textContent = formatVND(currentBasePrice);
        }
        if (costPerCupEl) {
            costPerCupEl.innerHTML = `${formatVND(costPerCup)}<span class="small fs-6 fw-normal text-muted">/tách</span>`;
        }
        if (monthlyCostEl) {
            monthlyCostEl.textContent = formatVND(monthlyCost);
        }
        if (monthlySavingsEl) {
            monthlySavingsEl.textContent = `+${formatVND(monthlySavings)}`;
        }

        // Update Perks
        if (perksEl) {
            perksEl.innerHTML = tier.perks.map(p => `<i class="fa fa-check text-warning me-2"></i>${p}`).join("<br/>");
        }

        // Update Preset Buttons Active State
        presetButtons.forEach(btn => {
            const btnVol = parseInt(btn.getAttribute('data-vol'), 10);
            if (btnVol === currentVolume) {
                btn.classList.add('active');
                btn.style.backgroundColor = '#D48842';
                btn.style.borderColor = '#D48842';
                btn.style.color = '#1E120B';
            } else {
                btn.classList.remove('active');
                btn.style.backgroundColor = 'transparent';
                btn.style.borderColor = 'rgba(255,255,255,0.4)';
                btn.style.color = '#FAF6F0';
            }
        });
    }

    // Volume Slider Event
    if (volumeSlider) {
        volumeSlider.addEventListener('input', (e) => {
            currentVolume = parseInt(e.target.value, 10);
            recalculate();
        });
    }

    // Preset Buttons
    presetButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const vol = parseInt(btn.getAttribute('data-vol'), 10);
            if (vol) {
                currentVolume = vol;
                if (volumeSlider) volumeSlider.value = vol;
                recalculate();
            }
        });
    });

    // Blend Selection Cards
    blendCards.forEach(card => {
        card.addEventListener('click', () => {
            blendCards.forEach(c => {
                c.classList.remove('active');
                c.style.borderColor = 'rgba(212,136,66,0.3)';
                c.style.background = 'transparent';
            });
            card.classList.add('active');
            card.style.borderColor = '#D48842';
            card.style.background = 'rgba(212,136,66,0.15)';

            currentBasePrice = parseInt(card.getAttribute('data-base-price'), 10) || 350000;
            currentBlendName = card.getAttribute('data-name') || "Heritage Red Honey";
            recalculate();
        });
    });

    // Apply to Lead Form Action
    function applyToForm() {
        const tier = getTier(currentVolume);
        const formSection = document.getElementById('b2b_form');
        if (!formSection) return;

        // Auto-select Volume in form
        const volSelect = formSection.querySelector('select[name="estimated_monthly_volume"]');
        if (volSelect) {
            for (let opt of volSelect.options) {
                if (opt.value === tier.formVol || opt.text.includes(tier.formVol)) {
                    volSelect.value = opt.value;
                    break;
                }
            }
        }

        // Auto-select Service in form
        const serviceSelect = formSection.querySelector('select[name="service_interest"]');
        if (serviceSelect) {
            for (let opt of serviceSelect.options) {
                if (opt.value === tier.formService || opt.text.includes(tier.formService)) {
                    serviceSelect.value = opt.value;
                    break;
                }
            }
        }

        // Auto-fill Description note with calculated plan
        const descTextarea = formSection.querySelector('textarea[name="description"]');
        if (descTextarea) {
            const note = `[Dự Toán B2B]: Dự kiến sản lượng ${currentVolume} kg/tháng (${tier.name} - Chiết khấu ${Math.round(tier.discount * 100)}%). Dòng hạt quan tâm: ${currentBlendName}. Mong muốn nhận hộp mẫu thử và tư vấn chính sách tài trợ thiết bị.`;
            descTextarea.value = note;
        }

        // Smooth scroll to form with attention highlight
        formSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        const formCard = formSection.querySelector('.inno-spatial-layer');
        if (formCard) {
            formCard.style.boxShadow = '0 0 35px rgba(212, 136, 66, 0.6)';
            formCard.style.transition = 'box-shadow 0.6s ease';
            setTimeout(() => {
                formCard.style.boxShadow = '';
            }, 2500);
        }
    }

    if (applyBtn) {
        applyBtn.addEventListener('click', applyToForm);
    }

    // Connect Wholesale Matrix "Chọn gói" buttons to Calculator & Form
    document.querySelectorAll('.s_innokafe_b2b_wholesale_tiers a[href="#b2b_form"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const tierCard = btn.closest('.inno-spatial-layer');
            const tierText = tierCard ? tierCard.innerText : "";
            
            if (tierText.includes("Tier 1") || tierText.includes("Bronze")) {
                currentVolume = 20;
            } else if (tierText.includes("Tier 2") || tierText.includes("Silver")) {
                currentVolume = 50;
            } else if (tierText.includes("Tier 3") || tierText.includes("Gold")) {
                currentVolume = 100;
            } else if (tierText.includes("Tier 4") || tierText.includes("Platinum")) {
                currentVolume = 250;
            }

            if (volumeSlider) volumeSlider.value = currentVolume;
            recalculate();
            applyToForm();
        });
    });

    // Run initial calculation
    recalculate();
}

if (typeof window !== "undefined") {
    window.initB2BCalculator = initB2BCalculator;
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initB2BCalculator);
    } else {
        initB2BCalculator();
    }
    window.addEventListener("load", initB2BCalculator);
}

export default { initB2BCalculator };
