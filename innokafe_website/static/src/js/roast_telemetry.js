/** @odoo-module **/

/**
 * ============================================================================
 * INNOKAFE SPECIALTY COFFEE ROASTING TELEMETRY & ROR CURVE ENGINE
 * Council of Roaster Guru, SCA Barista Master & Odoo Snippets Web Architect
 * ============================================================================
 * Physics-calibrated dual-curve simulation engine:
 * 1. Bean Temperature (BT) curve with amber glow (#D48842)
 * 2. Rate of Rise (RoR) central-difference derivative curve (#00F2FE)
 * 3. 4 Roasting phases: Drying (0-4m), Maillard (4-8m30s), Development (DTR 15.8%), Cooling
 * 4. 3 Master roast presets: Fine Robusta, Arabica Bourbon, Espresso Blend
 * 5. 60 FPS requestAnimationFrame simulation loop with timeline scrubber
 * ============================================================================
 */

export const ROAST_PRESETS = {
    fine_robusta: {
        id: "fine_robusta",
        name: "Fine Robusta Natural (Medium-Dark)",
        badge_name: "Fine Robusta Cư M'gar",
        agtron: 48,
        roast_level: "Medium-Dark (Agtron 48)",
        charge_temp: 190.0,
        turning_point: { time_s: 90, temp_c: 96.0 },
        dry_end: { time_s: 240, temp_c: 150.0 },
        first_crack: { time_s: 510, temp_c: 196.0 }, // 8m30s @ 196°C
        drop: { time_s: 606, temp_c: 208.0 },       // 10m06s @ 208°C
        dtr_pct: 15.84,                             // (606-510)/606 = 15.84% ~ 15.8%
        lot_no: "LOT-DKL-2026-R849",
        master_roaster: "Nguyễn Văn An (SCA Roaster Level 2)",
        roast_date: "08/10/2026",
        tasting_notes: ["Sô-cô-la đen 85%", "Hạt dẻ nướng", "Mật mía", "Gỗ sồi"],
        description: "Robusta thượng hạng lên men tự nhiên 28 ngày tại Cư M'gar, rang khí nóng đối lưu ở mức Medium-Dark nhằm tối ưu độ ngọt mật mía và thể chất dày êm ái.",
    },
    arabica_bourbon: {
        id: "arabica_bourbon",
        name: "Arabica Bourbon Washed (Light-Medium)",
        badge_name: "Arabica Cầu Đất Đơn Lô",
        agtron: 72,
        roast_level: "Light-Medium (Agtron 72)",
        charge_temp: 180.0,
        turning_point: { time_s: 80, temp_c: 92.0 },
        dry_end: { time_s: 230, temp_c: 148.0 },
        first_crack: { time_s: 495, temp_c: 194.0 }, // 8m15s @ 194°C
        drop: { time_s: 588, temp_c: 202.0 },       // 9m48s @ 202°C
        dtr_pct: 15.82,                             // (588-495)/588 = 15.82% ~ 15.8%
        lot_no: "LOT-CDT-2026-A412",
        master_roaster: "Lê Thùy Dương (Q Processing Professional)",
        roast_date: "07/10/2026",
        tasting_notes: ["Hoa nhài trắng", "Cam Bergamot", "Táo xanh", "Trà Earl Grey"],
        description: "Arabica Bourbon thuần chủng từ độ cao 1.650m Cầu Đất, chế biến ướt tinh khiết, rang Light-Medium bảo toàn trọn vẹn axit hữu cơ sáng và hương hoa nhài.",
    },
    espresso_blend: {
        id: "espresso_blend",
        name: "Espresso Barista Blend Omni (Medium-Dark)",
        badge_name: "Espresso Signature Blend",
        agtron: 50,
        roast_level: "Medium-Dark (Agtron 50)",
        charge_temp: 188.0,
        turning_point: { time_s: 85, temp_c: 94.0 },
        dry_end: { time_s: 240, temp_c: 149.0 },
        first_crack: { time_s: 505, temp_c: 195.0 }, // 8m25s @ 195°C
        drop: { time_s: 600, temp_c: 206.0 },       // 10m00s @ 206°C
        dtr_pct: 15.83,                             // (600-505)/600 = 15.83% ~ 15.8%
        lot_no: "LOT-BLD-2026-E105",
        master_roaster: "Trần Hữu Long (Head Roaster InnoKafe)",
        roast_date: "09/10/2026",
        tasting_notes: ["Ca cao đắng 70%", "Bơ đậu phộng", "Caramel khói", "Vỏ cam sấy"],
        description: "Tỉ lệ vàng 70% Fine Robusta & 30% Arabica Cầu Đất, tối ưu hóa cho máy pha espresso áp suất 9 bar với lớp crema bền chặt và hậu vị hạt dẻ nướng.",
    },
};

/**
 * Calculates Bean Temperature (BT) in °C at time_s for a given preset
 * using a physics-calibrated fluid-bed convection model.
 */
export function evaluateBeanTemp(presetKey, time_s) {
    const p = ROAST_PRESETS[presetKey] || ROAST_PRESETS["fine_robusta"];
    const tp_t = p.turning_point.time_s;
    const tp_temp = p.turning_point.temp_c;
    const chg_temp = p.charge_temp;
    const de_t = p.dry_end.time_s;
    const de_temp = p.dry_end.temp_c;
    const fc_t = p.first_crack.time_s;
    const fc_temp = p.first_crack.temp_c;
    const drop_t = p.drop.time_s;
    const drop_temp = p.drop.temp_c;

    if (time_s <= 0) {
        return chg_temp;
    } else if (time_s <= tp_t) {
        const ratio = time_s / tp_t;
        return chg_temp + (tp_temp - chg_temp) * Math.pow(ratio, 0.8);
    } else if (time_s <= de_t) {
        const ratio = (time_s - tp_t) / (de_t - tp_t);
        return tp_temp + (de_temp - tp_temp) * Math.pow(ratio, 0.95);
    } else if (time_s <= fc_t) {
        const ratio = (time_s - de_t) / (fc_t - de_t);
        return de_temp + (fc_temp - de_temp) * Math.pow(ratio, 0.9);
    } else if (time_s <= drop_t) {
        const ratio = (time_s - fc_t) / (drop_t - fc_t);
        return fc_temp + (drop_temp - fc_temp) * Math.pow(ratio, 0.85);
    } else {
        return Math.max(25.0, drop_temp - (time_s - drop_t) * 1.5);
    }
}

/**
 * Computes Rate of Rise (RoR) in °C/min at time_s via central difference derivative.
 */
export function evaluateRateOfRise(presetKey, time_s, dt = 5.0) {
    const t1 = Math.max(0.0, time_s - dt);
    const t2 = time_s + dt;
    const bt1 = evaluateBeanTemp(presetKey, t1);
    const bt2 = evaluateBeanTemp(presetKey, t2);
    return Math.round(((bt2 - bt1) / (t2 - t1)) * 60.0 * 100) / 100;
}

/**
 * Classifies the active roasting phase for a given preset and timestamp.
 */
export function getRoastPhase(presetKey, time_s) {
    const p = ROAST_PRESETS[presetKey] || ROAST_PRESETS["fine_robusta"];
    if (time_s <= 0) {
        return {
            key: "charge",
            name_vi: "Nạp Hạt (Charge)",
            name_en: "Charge",
            badgeClass: "bg-warning text-dark",
            color: "#D48842",
        };
    } else if (time_s < p.turning_point.time_s) {
        return {
            key: "turning",
            name_vi: "Hồi Nhiệt (Turning Point)",
            name_en: "Turning Point",
            badgeClass: "bg-secondary text-white",
            color: "#D48842",
        };
    } else if (time_s < p.dry_end.time_s) {
        return {
            key: "drying",
            name_vi: "Giai Đoạn Sấy Khô (Drying)",
            name_en: "Drying Phase",
            badgeClass: "bg-success text-white",
            color: "#2D4739",
        };
    } else if (time_s < p.first_crack.time_s) {
        return {
            key: "maillard",
            name_vi: "Phản Ứng Maillard",
            name_en: "Maillard Phase",
            badgeClass: "bg-warning text-dark",
            color: "#D48842",
        };
    } else if (time_s <= p.drop.time_s) {
        return {
            key: "development",
            name_vi: "Pha Phát Triển (DTR 15.8%)",
            name_en: "Development Phase",
            badgeClass: "bg-danger text-white",
            color: "#FF8000",
        };
    } else {
        return {
            key: "cooling",
            name_vi: "Làm Nguội Nhanh (Cooling)",
            name_en: "Rapid Cooling",
            badgeClass: "bg-info text-dark",
            color: "#00F2FE",
        };
    }
}

/**
 * Formats seconds into MM:SS display format.
 */
export function formatTime(seconds) {
    const clamped = Math.max(0, Math.round(seconds));
    const mins = Math.floor(clamped / 60);
    const secs = clamped % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Coordinate mapping constants for SVG viewBox="0 0 600 280".
 */
const SVG_GEOMETRY = {
    xStart: 45,
    xEnd: 555,
    yTop: 25,
    yBottom: 245,
    timeMax: 660,     // 11 minutes total window
    tempMax: 220,     // 0 to 220 °C
    rorMax: 20,       // 0 to 20 °C/min
};

function mapTimeToX(time_s) {
    const t = Math.max(0, Math.min(SVG_GEOMETRY.timeMax, time_s));
    const width = SVG_GEOMETRY.xEnd - SVG_GEOMETRY.xStart;
    return SVG_GEOMETRY.xStart + (t / SVG_GEOMETRY.timeMax) * width;
}

function mapTempToY(temp_c) {
    const temp = Math.max(0, Math.min(SVG_GEOMETRY.tempMax, temp_c));
    const height = SVG_GEOMETRY.yBottom - SVG_GEOMETRY.yTop;
    return SVG_GEOMETRY.yBottom - (temp / SVG_GEOMETRY.tempMax) * height;
}

function mapRoRToY(ror) {
    const r = Math.max(0, Math.min(SVG_GEOMETRY.rorMax, ror));
    const height = SVG_GEOMETRY.yBottom - SVG_GEOMETRY.yTop;
    return SVG_GEOMETRY.yBottom - (r / SVG_GEOMETRY.rorMax) * height;
}

/**
 * Main Interactive Telemetry Engine Component
 */
export class InnokafeRoastTelemetry {
    constructor(rootElement) {
        if (!rootElement) return;
        this.root = rootElement;

        // State Machine
        this.currentPreset = "fine_robusta";
        this.currentTime = 510; // Default to First Crack (8m30s) for high impact on load
        this.isPlaying = false;
        this.playbackSpeed = 2; // 2x playback speed by default
        this.animFrameId = null;
        this.lastTimestamp = null;

        // Query DOM Elements
        this.cacheDom();

        // Bind Event Listeners
        this.bindEvents();

        // Initial Render
        this.setPreset(this.currentPreset);
    }

    cacheDom() {
        // Controls & Inputs
        this.presetButtons = this.root.querySelectorAll(".inno-preset-btn");
        this.scrubberInput = this.root.querySelector("#inno_telemetry_scrubber");
        this.scrubberDisplay = this.root.querySelector("#inno_scrubber_display");
        this.playBtn = this.root.querySelector("#inno_telemetry_play_btn");
        this.playText = this.root.querySelector("#inno_telemetry_play_text");
        this.resetBtn = this.root.querySelector("#inno_telemetry_reset_btn");
        this.jumpButtons = this.root.querySelectorAll(".inno-jump-btn");
        this.speedButtons = this.root.querySelectorAll(".inno-speed-btn");

        // Digital HUD Displays
        this.hudBt = this.root.querySelector("#inno_hud_bt");
        this.hudRor = this.root.querySelector("#inno_hud_ror");
        this.hudPhase = this.root.querySelector("#inno_hud_phase");
        this.hudTime = this.root.querySelector("#inno_hud_time");
        this.activePresetBadge = this.root.querySelector("#inno_telemetry_active_preset_badge");

        // External Transparency Badges (may be inside root or in parent section)
        const parentSection = this.root.closest("section") || document;
        this.badgeRoastDate = parentSection.querySelector("#inno_badge_roast_date");
        this.badgeLotNo = parentSection.querySelector("#inno_badge_lot_no");
        this.badgeMasterRoaster = parentSection.querySelector("#inno_badge_master_roaster");
        this.badgeTastingNotes = parentSection.querySelector("#inno_badge_tasting_notes");

        // SVG Visual Elements
        this.svgEl = this.root.querySelector("#inno_telemetry_svg");
        this.pathBt = this.root.querySelector("#inno_telemetry_path_bt");
        this.pathRor = this.root.querySelector("#inno_telemetry_path_ror");
        this.milestonesGroup = this.root.querySelector("#inno_telemetry_milestones");
        this.cursorGroup = this.root.querySelector("#inno_telemetry_cursor_group");
        this.cursorDotBt = this.root.querySelector("#inno_cursor_dot_bt");
        this.cursorDotRor = this.root.querySelector("#inno_cursor_dot_ror");

        // Phase Bands
        this.bandDrying = this.root.querySelector(".inno-phase-band-drying");
        this.bandMaillard = this.root.querySelector(".inno-phase-band-maillard");
        this.bandDev = this.root.querySelector(".inno-phase-band-dev");
        this.bandCooling = this.root.querySelector(".inno-phase-band-cooling");
    }

    bindEvents() {
        // Preset Switching
        this.presetButtons.forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const presetKey = btn.dataset.preset;
                if (presetKey && ROAST_PRESETS[presetKey]) {
                    this.setPreset(presetKey);
                }
            });
        });

        // Scrubber Dragging / Scrubbing
        if (this.scrubberInput) {
            this.scrubberInput.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                this.seekTo(val, false);
            });
            this.scrubberInput.addEventListener("change", (e) => {
                const val = parseFloat(e.target.value);
                this.seekTo(val, false);
            });
        }

        // Quick Milestone Jumps
        this.jumpButtons.forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const time = parseFloat(btn.dataset.time);
                if (!isNaN(time)) {
                    this.seekTo(time, true);
                }
            });
        });

        // Simulation Play / Pause
        if (this.playBtn) {
            this.playBtn.addEventListener("click", (e) => {
                e.preventDefault();
                this.togglePlay();
            });
        }

        // Reset
        if (this.resetBtn) {
            this.resetBtn.addEventListener("click", (e) => {
                e.preventDefault();
                this.reset();
            });
        }

        // Speed Toggle
        this.speedButtons.forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const spd = parseFloat(btn.dataset.speed);
                if (!isNaN(spd)) {
                    this.setSpeed(spd);
                }
            });
        });
    }

    setPreset(presetKey) {
        if (!ROAST_PRESETS[presetKey]) return;
        this.currentPreset = presetKey;
        const p = ROAST_PRESETS[presetKey];

        // Update Preset Buttons Active State
        this.presetButtons.forEach((btn) => {
            const isActive = btn.dataset.preset === presetKey;
            btn.classList.toggle("active", isActive);
            btn.setAttribute("aria-pressed", isActive ? "true" : "false");
        });

        // Update Active Preset Badge
        if (this.activePresetBadge) {
            this.activePresetBadge.textContent = `Mẻ Rang: ${p.name}`;
        }

        // Update Dynamic Transparency Badges
        if (this.badgeRoastDate) this.badgeRoastDate.textContent = p.roast_date;
        if (this.badgeLotNo) this.badgeLotNo.textContent = p.lot_no;
        if (this.badgeMasterRoaster) this.badgeMasterRoaster.textContent = p.master_roaster;
        if (this.badgeTastingNotes) {
            this.badgeTastingNotes.textContent = p.tasting_notes.join(" • ");
        }

        // Update Quick Jump Button times for dynamic preset milestones
        this.updateMilestoneButtons(p);

        // Update Phase Bands in SVG
        this.updatePhaseBands(p);

        // Render SVG Curves & Milestone Markers
        this.renderCurves();

        // Update HUD & Cursor at current position
        this.updateHUD(this.currentTime);
    }

    updateMilestoneButtons(p) {
        this.jumpButtons.forEach((btn) => {
            const timeAttr = btn.dataset.time;
            if (timeAttr === "90" || btn.textContent.includes("TP")) {
                btn.dataset.time = p.turning_point.time_s.toString();
                btn.textContent = `${formatTime(p.turning_point.time_s)} Đảo Chiều (TP)`;
            } else if (timeAttr === "240" || btn.textContent.includes("Sấy")) {
                btn.dataset.time = p.dry_end.time_s.toString();
                btn.textContent = `${formatTime(p.dry_end.time_s)} Sấy Xong`;
            } else if (timeAttr === "510" || btn.textContent.includes("First Crack")) {
                btn.dataset.time = p.first_crack.time_s.toString();
                btn.innerHTML = `<i class="fa fa-bolt me-1"></i>${formatTime(p.first_crack.time_s)} First Crack`;
            } else if (timeAttr === "606" || btn.textContent.includes("Drop")) {
                btn.dataset.time = p.drop.time_s.toString();
                btn.innerHTML = `<i class="fa fa-flag-checkered me-1"></i>${formatTime(p.drop.time_s)} Drop (${p.dtr_pct.toFixed(1)}%)`;
            }
        });
    }

    updatePhaseBands(p) {
        const xDryingStart = mapTimeToX(0);
        const xDryingEnd = mapTimeToX(p.dry_end.time_s);
        const xMaillardEnd = mapTimeToX(p.first_crack.time_s);
        const xDropEnd = mapTimeToX(p.drop.time_s);
        const xMax = mapTimeToX(SVG_GEOMETRY.timeMax);

        if (this.bandDrying) {
            this.bandDrying.setAttribute("x", xDryingStart.toFixed(1));
            this.bandDrying.setAttribute("width", (xDryingEnd - xDryingStart).toFixed(1));
        }
        if (this.bandMaillard) {
            this.bandMaillard.setAttribute("x", xDryingEnd.toFixed(1));
            this.bandMaillard.setAttribute("width", (xMaillardEnd - xDryingEnd).toFixed(1));
        }
        if (this.bandDev) {
            this.bandDev.setAttribute("x", xMaillardEnd.toFixed(1));
            this.bandDev.setAttribute("width", (xDropEnd - xMaillardEnd).toFixed(1));
        }
        if (this.bandCooling) {
            this.bandCooling.setAttribute("x", xDropEnd.toFixed(1));
            this.bandCooling.setAttribute("width", (xMax - xDropEnd).toFixed(1));
        }
    }

    renderCurves() {
        const presetKey = this.currentPreset;
        let btPathStr = "";
        let rorPathStr = "";

        // Sample curves every 4 seconds from 0 to 660s for silky smooth vector lines
        for (let t = 0; t <= SVG_GEOMETRY.timeMax; t += 4) {
            const x = mapTimeToX(t);
            const bt = evaluateBeanTemp(presetKey, t);
            const ror = evaluateRateOfRise(presetKey, t);
            const yBt = mapTempToY(bt);
            const yRor = mapRoRToY(ror);

            const prefix = t === 0 ? "M " : " L ";
            btPathStr += `${prefix}${x.toFixed(1)},${yBt.toFixed(1)}`;
            rorPathStr += `${prefix}${x.toFixed(1)},${yRor.toFixed(1)}`;
        }

        if (this.pathBt) {
            this.pathBt.setAttribute("d", btPathStr);
        }
        if (this.pathRor) {
            this.pathRor.setAttribute("d", rorPathStr);
        }

        // Render Milestones Pins
        this.renderMilestones();
    }

    renderMilestones() {
        if (!this.milestonesGroup) return;
        const p = ROAST_PRESETS[this.currentPreset];

        const milestones = [
            {
                label: `TP ${p.turning_point.temp_c}°C`,
                time_s: p.turning_point.time_s,
                temp_c: p.turning_point.temp_c,
                color: "#D48842",
                r: 5,
                yOffset: 20,
            },
            {
                label: `Maillard ${p.dry_end.temp_c}°C`,
                time_s: p.dry_end.time_s,
                temp_c: p.dry_end.temp_c,
                color: "#D48842",
                r: 5.5,
                yOffset: -12,
            },
            {
                label: `First Crack ${p.first_crack.temp_c}°C`,
                time_s: p.first_crack.time_s,
                temp_c: p.first_crack.temp_c,
                color: "#FF8000",
                r: 7,
                yOffset: -14,
                bold: true,
            },
            {
                label: `Drop ${p.drop.temp_c}°C (DTR ${p.dtr_pct.toFixed(1)}%)`,
                time_s: p.drop.time_s,
                temp_c: p.drop.temp_c,
                color: "#FFFFFF",
                r: 7,
                yOffset: -14,
                bold: true,
            },
        ];

        let html = "";
        milestones.forEach((m) => {
            const cx = mapTimeToX(m.time_s).toFixed(1);
            const cy = mapTempToY(m.temp_c).toFixed(1);
            const textY = (parseFloat(cy) + m.yOffset).toFixed(1);
            const weight = m.bold ? "font-weight='bold'" : "";

            html += `
                <g class="inno-milestone-pin" data-time="${m.time_s}">
                    <circle cx="${cx}" cy="${cy}" r="${m.r}" fill="${m.color}" stroke="#1E120B" stroke-width="2"/>
                    <text x="${cx}" y="${textY}" fill="${m.color}" font-size="9" text-anchor="middle" ${weight}>
                        ${m.label}
                    </text>
                </g>
            `;
        });

        this.milestonesGroup.innerHTML = html;
    }

    updateHUD(time) {
        const clamped = Math.max(0, Math.min(SVG_GEOMETRY.timeMax, time));
        const presetKey = this.currentPreset;
        const p = ROAST_PRESETS[presetKey];

        const bt = evaluateBeanTemp(presetKey, clamped);
        const ror = evaluateRateOfRise(presetKey, clamped);
        const phase = getRoastPhase(presetKey, clamped);

        // Readout Updates
        if (this.hudBt) this.hudBt.textContent = `${bt.toFixed(1)}°C`;
        if (this.hudRor) {
            const prefix = ror > 0 ? "+" : "";
            this.hudRor.textContent = `${prefix}${ror.toFixed(1)}°/m`;
        }
        if (this.hudPhase) {
            this.hudPhase.textContent = phase.name_vi;
            this.hudPhase.title = `${phase.name_vi} (${phase.name_en})`;
        }
        if (this.hudTime) {
            this.hudTime.textContent = `${formatTime(clamped)}`;
        }
        if (this.scrubberDisplay) {
            this.scrubberDisplay.textContent = formatTime(clamped);
        }
        if (this.scrubberInput && Math.abs(parseFloat(this.scrubberInput.value) - clamped) > 0.5) {
            this.scrubberInput.value = clamped.toFixed(0);
        }

        // SVG Cursor Group Position
        if (this.cursorGroup) {
            const x = mapTimeToX(clamped);
            this.cursorGroup.setAttribute("transform", `translate(${x.toFixed(1)}, 0)`);
        }
        if (this.cursorDotBt) {
            const yBt = mapTempToY(bt);
            this.cursorDotBt.setAttribute("cy", yBt.toFixed(1));
        }
        if (this.cursorDotRor) {
            const yRor = mapRoRToY(ror);
            this.cursorDotRor.setAttribute("cy", yRor.toFixed(1));
        }
    }

    seekTo(time, forcePause = false) {
        this.currentTime = Math.max(0, Math.min(SVG_GEOMETRY.timeMax, time));
        if (forcePause && this.isPlaying) {
            this.pause();
        }
        this.updateHUD(this.currentTime);
    }

    setSpeed(speed) {
        this.playbackSpeed = speed;
        this.speedButtons.forEach((btn) => {
            const isMatch = parseFloat(btn.dataset.speed) === speed;
            btn.classList.toggle("active", isMatch);
            btn.classList.toggle("btn-outline-warning", isMatch);
            btn.classList.toggle("btn-outline-secondary", !isMatch);
        });
    }

    togglePlay() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    play() {
        if (this.isPlaying) return;
        this.isPlaying = true;

        if (this.currentTime >= SVG_GEOMETRY.timeMax) {
            this.currentTime = 0;
        }

        if (this.playBtn) {
            this.playBtn.innerHTML = `<i class="fa fa-pause"></i> <span id="inno_telemetry_play_text">Tạm Dừng</span>`;
            this.playBtn.classList.add("inno-playing");
        }

        this.lastTimestamp = performance.now();
        this.animFrameId = requestAnimationFrame(this.loop.bind(this));
    }

    pause() {
        this.isPlaying = false;
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }

        if (this.playBtn) {
            this.playBtn.innerHTML = `<i class="fa fa-play"></i> <span id="inno_telemetry_play_text">Phát Mô Phỏng</span>`;
            this.playBtn.classList.remove("inno-playing");
        }
    }

    reset() {
        this.pause();
        this.seekTo(0);
    }

    loop(timestamp) {
        if (!this.isPlaying) return;

        if (this.lastTimestamp === null) {
            this.lastTimestamp = timestamp;
        }

        const deltaMs = timestamp - this.lastTimestamp;
        this.lastTimestamp = timestamp;

        // Advance simulation time:
        // 1 real second = (10 * playbackSpeed) simulation seconds
        const deltaSeconds = (deltaMs / 1000) * 12 * this.playbackSpeed;
        this.currentTime += deltaSeconds;

        if (this.currentTime >= SVG_GEOMETRY.timeMax) {
            this.currentTime = SVG_GEOMETRY.timeMax;
            this.updateHUD(this.currentTime);
            this.pause();
            return;
        }

        this.updateHUD(this.currentTime);
        this.animFrameId = requestAnimationFrame(this.loop.bind(this));
    }

    destroy() {
        this.pause();
        if (this.root && this.root.__innoRoastTelemetry) {
            delete this.root.__innoRoastTelemetry;
        }
    }

    /**
     * Initializes all telemetry components across the document.
     */
    static initAll(rootNode = document) {
        try {
            const containers = rootNode.querySelectorAll("#innokafe_roast_telemetry_container, .inno-roast-telemetry-container");
            containers.forEach((container) => {
                if (!container.__innoRoastTelemetry) {
                    container.__innoRoastTelemetry = new InnokafeRoastTelemetry(container);
                }
            });
        } catch (err) {
            if (typeof console !== "undefined" && console.warn) {
                console.warn("[InnoKafe] Roast Telemetry initialization notice:", err);
            }
        }
    }
}

// Auto-initialize when document is ready
if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => InnokafeRoastTelemetry.initAll());
    } else {
        InnokafeRoastTelemetry.initAll();
    }
}

export default InnokafeRoastTelemetry;
