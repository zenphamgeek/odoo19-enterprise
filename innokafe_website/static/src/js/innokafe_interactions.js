/** @odoo-module **/

/**
 * ============================================================================
 * INNOKAFE SPECIALTY COFFEE BREW LAB: INTERACTIVE ENGINE
 * Council of Barista Master & Odoo Snippets Web Architect
 * ============================================================================
 * Cung cấp khả năng tính toán định lượng chiết xuất động theo thời gian thực:
 * - 5 phương pháp pha chế Specialty tiêu chuẩn SCA
 * - Tự động cập nhật dải thông số (Tỷ lệ, Độ mịn micron, Nhiệt độ, Thời gian, TDS)
 * - Tự động tính toán: Lượng hạt (g), Nước ủ Bloom (ml), Tổng nước (ml), Thể tích ly (ml)
 * ============================================================================
 */

export const BREWING_METHODS = {
    phin: {
        name: "1. Phin Nhôm Nghệ Nhân",
        badge: "PHIN NHÔM NGHỆ NHÂN",
        title: "Nghi Thức Bản Địa, Tinh Hoa Đậm Sánh",
        ratio: 4,
        ratioText: "1 : 4",
        grind: "650 μm (Medium-Fine)",
        temp: "93°C – 95°C",
        time: "4m 30s",
        tds: "TDS: 2.5% – 3.0%",
        defaultGrams: 25,
        minGrams: 15,
        maxGrams: 40,
        bloomMultiplier: 1.2,
        desc: "Từng giọt cà phê rơi chậm rãi qua đáy phin nhôm dày 1.2mm, chắt lọc trọn vẹn vị nguyên bản đượm đà của Fine Robusta Đắk Lắk. Lớp thể chất dày dặn hòa quyện nốt socola đắng ngọt và caramel nướng sâu lắng."
    },
    espresso: {
        name: "2. Espresso 9 Bar",
        badge: "ESPRESSO 9 BAR",
        title: "Áp Suất Hoàng Kim, Lớp Crema Dày Đậm",
        ratio: 2,
        ratioText: "1 : 2",
        grind: "250 μm (Fine)",
        temp: "92°C – 93°C",
        time: "28s – 30s",
        tds: "TDS: 8.0% – 10.0%",
        defaultGrams: 18,
        minGrams: 14,
        maxGrams: 22,
        bloomMultiplier: 0,
        desc: "Chiết xuất dưới áp suất tiêu chuẩn 9 bar, giải phóng lớp crema vàng óng ả dày dặn. Thể chất tròn đầy bùng nổ hương caramel, hạnh nhân rang và kết thúc ngọt hậu kéo dài."
    },
    v60: {
        name: "3. Pour-Over V60",
        badge: "POUR-OVER V60",
        title: "Chiết Xuất Trọng Lực, Thanh Tao Tinh Khiết",
        ratio: 15,
        ratioText: "1 : 15",
        grind: "800 μm (Medium)",
        temp: "90°C – 92°C",
        time: "2m 45s",
        tds: "TDS: 1.2% – 1.4%",
        defaultGrams: 15,
        minGrams: 12,
        maxGrams: 30,
        bloomMultiplier: 2.5,
        desc: "Dòng nước xoắn ốc luồn qua phễu nón 60 độ, chắt chiu độ chua thanh citric rực rỡ và hương hoa nhài tinh tế của Arabica Cầu Đất trên nền nước trong veo, tinh tế."
    },
    coldbrew: {
        name: "4. Cold Brew 24H",
        badge: "COLD BREW 24H",
        title: "Ủ Lạnh Chậm Rãi, Ngọt Dịu Thanh Mát",
        ratio: 10,
        ratioText: "1 : 10",
        grind: "1100 μm (Coarse)",
        temp: "4°C – 8°C (Tủ mát)",
        time: "24 Giờ",
        tds: "TDS: 1.5% – 2.0%",
        defaultGrams: 50,
        minGrams: 30,
        maxGrams: 100,
        bloomMultiplier: 0,
        desc: "Ngâm ủ 24 giờ trong nước lạnh tinh khiết, triệt tiêu axit gắt và vị đắng chát, tôn vinh vị ngọt mật ong tự nhiên, êm mượt và sảng khoái đánh thức tinh thần."
    },
    aeropress: {
        name: "5. Aeropress Inverted",
        badge: "AEROPRESS INVERTED",
        title: "Áp Lực Khí Nén, Thể Chất Đa Tầng",
        ratio: 12,
        ratioText: "1 : 12",
        grind: "600 μm (Medium-Fine)",
        temp: "85°C – 88°C",
        time: "1m 45s",
        tds: "TDS: 1.4% – 1.8%",
        defaultGrams: 15,
        minGrams: 12,
        maxGrams: 25,
        bloomMultiplier: 2.0,
        desc: "Phương pháp ngâm ủ ngược kết hợp lực ép pit-tông khí nén độc đáo, tạo nên tách cà phê tròn trịa, cân bằng giữa độ trong trẻo của pour-over và độ đậm đà của phin."
    }
};

export class InnokafeBrewLab {
    /**
     * Khởi tạo một phiên bản tương tác Brew Lab trên container cụ thể.
     * @param {HTMLElement} rootEl - Phần tử chứa snippet .inno-brew-lab-section
     */
    constructor(rootEl) {
        this.rootEl = rootEl;
        this.currentMethodKey = "phin";

        // DOM Elements
        this.methodButtons = Array.from(this.rootEl.querySelectorAll(".inno-brew-method-btn"));
        this.slider = this.rootEl.querySelector(".inno-calc-slider");
        this.badgeEl = this.rootEl.querySelector(".inno-method-badge");
        this.titleEl = this.rootEl.querySelector(".inno-method-title");
        this.tdsEl = this.rootEl.querySelector(".inno-method-tds");
        this.ratioEl = this.rootEl.querySelector(".inno-param-ratio");
        this.grindEl = this.rootEl.querySelector(".inno-param-grind");
        this.tempEl = this.rootEl.querySelector(".inno-param-temp");
        this.timeEl = this.rootEl.querySelector(".inno-param-time");
        this.descEl = this.rootEl.querySelector(".inno-method-desc");

        // Calculation Display Elements
        this.calcGramsEl = this.rootEl.querySelector(".inno-calc-grams");
        this.calcBloomEl = this.rootEl.querySelector(".inno-calc-bloom");
        this.calcWaterEl = this.rootEl.querySelector(".inno-calc-water");
        this.calcYieldEl = this.rootEl.querySelector(".inno-calc-yield");

        this.init();
    }

    /**
     * Gắn kết các sự kiện và kích hoạt trạng thái mặc định ban đầu.
     */
    init() {
        if (!this.slider && this.methodButtons.length === 0) {
            return;
        }

        // Lắng nghe sự kiện click trên các nút phương pháp pha chế
        this.methodButtons.forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const methodKey = btn.dataset.method;
                if (methodKey && BREWING_METHODS[methodKey]) {
                    this.selectMethod(methodKey, btn);
                }
            });
        });

        // Lắng nghe sự kiện trượt slider điều chỉnh khối lượng hạt cà phê
        if (this.slider) {
            this.slider.addEventListener("input", (e) => {
                const grams = parseFloat(e.target.value) || 0;
                this.updateCalculations(grams);
            });
        }

        // Kích hoạt phương pháp mặc định ban đầu (hoặc nút đang có class active)
        const initialActiveBtn = this.methodButtons.find((btn) => btn.classList.contains("active")) || this.methodButtons[0];
        const initialMethodKey = initialActiveBtn ? initialActiveBtn.dataset.method : "phin";
        this.selectMethod(initialMethodKey, initialActiveBtn);
    }

    /**
     * Chuyển đổi phương pháp pha chế được chọn và cập nhật toàn bộ DOM & Slider.
     * @param {string} methodKey - Khóa phương pháp (phin, espresso, v60, coldbrew, aeropress)
     * @param {HTMLElement} [targetBtn] - Nút button tương ứng vừa được click
     */
    selectMethod(methodKey, targetBtn) {
        const methodData = BREWING_METHODS[methodKey];
        if (!methodData) return;

        this.currentMethodKey = methodKey;

        // 1. Chuyển đổi trạng thái class trên các nút điều hướng
        this.methodButtons.forEach((btn) => {
            btn.classList.remove("active", "border-warning", "text-warning");
            btn.classList.add("border-secondary", "border-opacity-25");
            btn.setAttribute("aria-selected", "false");
        });

        const activeBtn = targetBtn || this.methodButtons.find((btn) => btn.dataset.method === methodKey);
        if (activeBtn) {
            activeBtn.classList.remove("border-secondary", "border-opacity-25");
            activeBtn.classList.add("active", "border-warning", "text-warning");
            activeBtn.setAttribute("aria-selected", "true");
        }

        // 2. Cập nhật các thông số khoa học vào DOM
        if (this.badgeEl) this.badgeEl.textContent = methodData.badge;
        if (this.titleEl) this.titleEl.textContent = methodData.title;
        if (this.tdsEl) this.tdsEl.textContent = methodData.tds;
        if (this.ratioEl) this.ratioEl.textContent = methodData.ratioText;
        if (this.grindEl) this.grindEl.textContent = methodData.grind;
        if (this.tempEl) this.tempEl.textContent = methodData.temp;
        if (this.timeEl) this.timeEl.textContent = methodData.time;
        if (this.descEl) this.descEl.textContent = methodData.desc;

        // 3. Cập nhật slider theo thông số của phương pháp mới
        if (this.slider) {
            this.slider.min = methodData.minGrams;
            this.slider.max = methodData.maxGrams;
            this.slider.value = methodData.defaultGrams;
        }

        // 4. Tính toán và cập nhật lại các chỉ số định lượng
        this.updateCalculations(methodData.defaultGrams);
    }

    /**
     * Tính toán định lượng chiết xuất và hiển thị kết quả ra giao diện.
     * @param {number} coffeeGrams - Khối lượng hạt cà phê (g)
     */
    updateCalculations(coffeeGrams) {
        const methodData = BREWING_METHODS[this.currentMethodKey];
        if (!methodData) return;

        const coffee = Math.round(coffeeGrams);

        // a) Lượng nước ủ nở (Bloom)
        let bloomText = "";
        if (methodData.bloomMultiplier === 0) {
            bloomText = "Không cần ủ (0 ml)";
        } else {
            const bloomWater = Math.round(coffee * methodData.bloomMultiplier);
            bloomText = `${bloomWater} ml`;
        }

        // b) Tổng lượng nước rót (Total Water)
        const totalWater = Math.round(coffee * methodData.ratio);

        // c) Thể tích ly thành phẩm (Cup Yield)
        // Vật lý chiết xuất: Bã cà phê giữ lại lượng nước xấp xỉ 2 lần trọng lượng hạt khô
        let cupYield = 0;
        if (this.currentMethodKey === "espresso") {
            cupYield = Math.round(coffee * 2);
        } else {
            cupYield = Math.max(0, Math.round(totalWater - coffee * 2));
        }

        // Cập nhật DOM
        if (this.calcGramsEl) {
            this.calcGramsEl.textContent = `${coffee}g`;
        }
        if (this.calcBloomEl) {
            this.calcBloomEl.textContent = bloomText;
        }
        if (this.calcWaterEl) {
            this.calcWaterEl.textContent = `${totalWater} ml`;
        }
        if (this.calcYieldEl) {
            this.calcYieldEl.textContent = `~${cupYield} ml`;
        }
    }

    /**
     * Quét và khởi tạo toàn bộ các section Brew Lab trên trang hiện tại.
     * @param {Document|HTMLElement} [rootNode=document]
     */
    static initAll(rootNode = document) {
        const sections = rootNode.querySelectorAll(".inno-brew-lab-section");
        sections.forEach((section) => {
            if (!section.__innoBrewLabInstance) {
                section.__innoBrewLabInstance = new InnokafeBrewLab(section);
            }
        });
    }
}

// Tự động kích hoạt khi DOM hoàn tất nạp (Auto-init)
if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => InnokafeBrewLab.initAll());
    } else {
        InnokafeBrewLab.initAll();
    }
}

export default InnokafeBrewLab;
