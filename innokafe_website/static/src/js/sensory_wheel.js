/** @odoo-module **/

/**
 * Innokafe 6-Axis Interactive Sensory Radar Chart (SCA Specialty Coffee Grade)
 * ===========================================================================
 * Precision polar coordinate radar engine with:
 * 1. Interactive direct node dragging and spoke click tuning.
 * 2. Real-time SCA Cupping Score calculation & classification.
 * 3. Dual-polygon comparison mode (User Target Profile vs Bean Actual Cupping).
 * 4. Micro-interactions with tactile glow, tooltips, and smooth cubic Bézier morphing.
 *
 * Axes:
 * - Aroma (-90°, top)
 * - Acidity (-30°, top-right)
 * - Body (30°, bottom-right)
 * - Sweetness (90°, bottom)
 * - Clean Cup (150°, bottom-left)
 * - Aftertaste (210°, top-left)
 */

export class InnokafeSensoryWheel {
    constructor(container, scores = {}, options = {}) {
        this.container = typeof container === "string" ? document.querySelector(container) : container;
        if (!this.container) return;

        this.options = Object.assign(
            {
                width: 300,
                height: 300,
                centerX: 150,
                centerY: 150,
                radius: 100,
                color: "#D48842",
                darkColor: "#1E120B",
                textColor: "#F7F2EA",
                accentColor: "#00F2FE",
                interactive: true,
                showLabels: true,
                showScoreBadge: true,
                secondaryScores: null,
                onChange: null,
            },
            options
        );

        this.axes = [
            { key: "aroma", label: "Aroma (Hương)", angle: -Math.PI / 2 },
            { key: "acidity", label: "Acidity (Chua)", angle: -Math.PI / 6 },
            { key: "body", label: "Body (Thể chất)", angle: Math.PI / 6 },
            { key: "sweetness", label: "Sweetness (Ngọt)", angle: Math.PI / 2 },
            { key: "cleancup", label: "Clean Cup (Trong)", angle: (5 * Math.PI) / 6 },
            { key: "aftertaste", label: "Aftertaste (Hậu)", angle: (7 * Math.PI) / 6 },
        ];

        this.scores = this._normalizeScores(scores);
        this.secondaryScores = this.options.secondaryScores ? this._normalizeScores(this.options.secondaryScores) : null;
        this.svg = null;
        this.polygon = null;
        this.secondaryPolygon = null;
        this.dots = [];
        this.scoreBadge = null;
        this._isDragging = false;
        this._activeDragAxis = null;

        this.init();
    }

    _normalizeScores(scores) {
        scores = scores || {};
        const parseScore = (val, fallback) => {
            if (val === undefined || val === null || val === "" || isNaN(Number(val))) {
                return fallback;
            }
            return Math.min(10.0, Math.max(1.0, Math.round(parseFloat(val) * 10) / 10));
        };

        return {
            aroma: parseScore(scores.aroma, 8.0),
            acidity: parseScore(scores.acidity, 5.0),
            body: parseScore(scores.body, 8.0),
            sweetness: parseScore(scores.sweetness, 8.0),
            cleancup: parseScore(scores.cleancup, 8.5),
            aftertaste: parseScore(scores.aftertaste, 8.0),
        };
    }

    calculateSCAScore(scores = this.scores) {
        const sum = (scores.aroma || 0) + (scores.acidity || 0) + (scores.body || 0) +
                    (scores.sweetness || 0) + (scores.cleancup || 0) + (scores.aftertaste || 0);
        // Base 40 + sum * 0.76 (e.g. sum 50 => 78, sum 55 => 81.8, sum 60 => 85.6)
        const sca = Math.min(95.0, Math.max(75.0, 40.0 + (sum * 0.76)));
        const rounded = Math.round(sca * 100) / 100;

        let classification = "Specialty Coffee";
        let badgeColor = "#D48842";
        if (rounded >= 90.0) {
            classification = "Super Specialty (90+)";
            badgeColor = "#00F2FE";
        } else if (rounded >= 85.0) {
            classification = "Exemplary Specialty (85+)";
            badgeColor = "#E5A93C";
        } else if (rounded >= 80.0) {
            classification = "Fine Specialty (80+)";
            badgeColor = "#10B981";
        }

        return {
            score: rounded,
            classification,
            badgeColor,
        };
    }

    _calculatePoints(scores) {
        const { centerX, centerY, radius } = this.options;
        return this.axes.map((axis) => {
            const val = typeof scores[axis.key] === "number" ? scores[axis.key] : 5.0;
            const r = radius * (val / 10.0);
            const x = Math.round((centerX + r * Math.cos(axis.angle)) * 10) / 10;
            const y = Math.round((centerY + r * Math.sin(axis.angle)) * 10) / 10;
            return { x, y, val, key: axis.key, label: axis.label, angle: axis.angle };
        });
    }

    _pointsToString(points) {
        return points.map((p) => `${p.x},${p.y}`).join(" ");
    }

    init() {
        if (!this.container) return;
        this.container.innerHTML = "";

        const { width, height, centerX, centerY, radius, color, darkColor, textColor, accentColor } = this.options;
        const currentPoints = this._calculatePoints(this.scores);
        const pointsStr = this._pointsToString(currentPoints);

        const svgNS = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(svgNS, "svg");
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.setAttribute("class", "innokafe-sensory-wheel-svg");
        svg.setAttribute("style", "width: 100%; height: 100%; overflow: visible; display: block; user-select: none;");

        // Defs (Gradients & Glow Filters)
        const defs = document.createElementNS(svgNS, "defs");
        const uniqueId = Math.random().toString(36).substr(2, 9);
        const gradId = "sensoryGrad_" + uniqueId;
        const glowId = "sensoryGlow_" + uniqueId;
        const secGradId = "sensorySecGrad_" + uniqueId;

        defs.innerHTML = `
            <radialGradient id="${gradId}" cx="50%" cy="50%" r="65%">
                <stop offset="0%" stop-color="${color}" stop-opacity="0.65"/>
                <stop offset="100%" stop-color="${darkColor}" stop-opacity="0.25"/>
            </radialGradient>
            <radialGradient id="${secGradId}" cx="50%" cy="50%" r="65%">
                <stop offset="0%" stop-color="${accentColor}" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="${accentColor}" stop-opacity="0.05"/>
            </radialGradient>
            <filter id="${glowId}" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="2.5" result="blur"/>
                <feComposite in="SourceGraphic" in2="blur" operator="over"/>
            </filter>
        `;
        svg.appendChild(defs);

        // Concentric Web Grid (Rings 2, 4, 6, 8, 10)
        [2, 4, 6, 8, 10].forEach((ringScore) => {
            const ringR = radius * (ringScore / 10.0);
            const ringPoints = this.axes.map((axis) => {
                const rx = Math.round((centerX + ringR * Math.cos(axis.angle)) * 10) / 10;
                const ry = Math.round((centerY + ringR * Math.sin(axis.angle)) * 10) / 10;
                return `${rx},${ry}`;
            }).join(" ");

            const ring = document.createElementNS(svgNS, "polygon");
            ring.setAttribute("points", ringPoints);
            ring.setAttribute("fill", "none");
            ring.setAttribute(
                "stroke",
                ringScore === 10 ? "rgba(212, 136, 66, 0.45)" : "rgba(247, 242, 234, 0.12)"
            );
            ring.setAttribute("stroke-width", ringScore === 10 ? "1.5" : "1");
            svg.appendChild(ring);
        });

        // Radial Axis Spoke Lines (Clickable / Interactive)
        this.axes.forEach((axis) => {
            const x2 = centerX + radius * Math.cos(axis.angle);
            const y2 = centerY + radius * Math.sin(axis.angle);

            const line = document.createElementNS(svgNS, "line");
            line.setAttribute("x1", centerX);
            line.setAttribute("y1", centerY);
            line.setAttribute("x2", x2);
            line.setAttribute("y2", y2);
            line.setAttribute("stroke", "rgba(247, 242, 234, 0.22)");
            line.setAttribute("stroke-dasharray", "2,3");
            line.setAttribute("stroke-width", "1");
            svg.appendChild(line);

            // Invisible wide clickable hit area for tuning axis values
            if (this.options.interactive) {
                const hitLine = document.createElementNS(svgNS, "line");
                hitLine.setAttribute("x1", centerX);
                hitLine.setAttribute("y1", centerY);
                hitLine.setAttribute("x2", x2);
                hitLine.setAttribute("y2", y2);
                hitLine.setAttribute("stroke", "transparent");
                hitLine.setAttribute("stroke-width", "18");
                hitLine.setAttribute("style", "cursor: pointer;");
                hitLine.setAttribute("data-axis", axis.key);

                hitLine.addEventListener("click", (e) => {
                    const rect = svg.getBoundingClientRect();
                    const clickX = e.clientX - rect.left;
                    const clickY = e.clientY - rect.top;
                    const scaleX = width / rect.width;
                    const scaleY = height / rect.height;
                    const svgX = clickX * scaleX;
                    const svgY = clickY * scaleY;

                    const dx = svgX - centerX;
                    const dy = svgY - centerY;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    const newVal = Math.min(10.0, Math.max(1.0, Math.round((dist / radius) * 10 * 10) / 10));
                    this.updateScore(axis.key, newVal);
                });

                svg.appendChild(hitLine);
            }
        });

        // Secondary Reference Polygon (Optional Comparison Overlay)
        if (this.secondaryScores) {
            const secPoints = this._calculatePoints(this.secondaryScores);
            const secPointsStr = this._pointsToString(secPoints);

            const secPolygon = document.createElementNS(svgNS, "polygon");
            secPolygon.setAttribute("points", secPointsStr);
            secPolygon.setAttribute("fill", `url(#${secGradId})`);
            secPolygon.setAttribute("stroke", accentColor);
            secPolygon.setAttribute("stroke-width", "1.5");
            secPolygon.setAttribute("stroke-dasharray", "4,3");
            secPolygon.setAttribute("stroke-linejoin", "round");
            secPolygon.setAttribute("style", "transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);");
            svg.appendChild(secPolygon);
            this.secondaryPolygon = secPolygon;
        }

        // Primary Sensory Data Polygon
        const polygon = document.createElementNS(svgNS, "polygon");
        polygon.setAttribute("points", pointsStr);
        polygon.setAttribute("fill", `url(#${gradId})`);
        polygon.setAttribute("stroke", color);
        polygon.setAttribute("stroke-width", "2.5");
        polygon.setAttribute("stroke-linejoin", "round");
        polygon.setAttribute("filter", `url(#${glowId})`);
        polygon.setAttribute("style", "transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);");
        svg.appendChild(polygon);
        this.polygon = polygon;

        // Interactive Data Dots
        this.dots = [];
        currentPoints.forEach((pt) => {
            const dot = document.createElementNS(svgNS, "circle");
            dot.setAttribute("cx", pt.x);
            dot.setAttribute("cy", pt.y);
            dot.setAttribute("r", "5");
            dot.setAttribute("fill", "#FAF6F0");
            dot.setAttribute("stroke", color);
            dot.setAttribute("stroke-width", "2.5");
            dot.setAttribute("style", this.options.interactive ? "cursor: grab; transition: r 0.2s ease, fill 0.2s ease;" : "transition: all 0.3s ease;");
            dot.setAttribute("data-axis", pt.key);
            dot.setAttribute("data-val", pt.val);

            // Hover effects & Tooltip
            dot.addEventListener("mouseenter", (e) => {
                dot.setAttribute("r", "7.5");
                dot.setAttribute("fill", color);
                this._showTooltip(e, pt.label, pt.val);
            });
            dot.addEventListener("mouseleave", () => {
                if (!this._isDragging) {
                    dot.setAttribute("r", "5");
                    dot.setAttribute("fill", "#FAF6F0");
                    this._hideTooltip();
                }
            });

            // Interactive Drag to Adjust Score
            if (this.options.interactive) {
                dot.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    this._isDragging = true;
                    this._activeDragAxis = pt.key;
                    dot.style.cursor = "grabbing";
                });
            }

            svg.appendChild(dot);
            this.dots.push(dot);
        });

        // Global mousemove and mouseup on SVG for dragging
        if (this.options.interactive) {
            svg.addEventListener("mousemove", (e) => {
                if (!this._isDragging || !this._activeDragAxis) return;
                const rect = svg.getBoundingClientRect();
                const svgX = (e.clientX - rect.left) * (width / rect.width);
                const svgY = (e.clientY - rect.top) * (height / rect.height);

                const dx = svgX - centerX;
                const dy = svgY - centerY;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const newVal = Math.min(10.0, Math.max(1.0, Math.round((dist / radius) * 10 * 10) / 10));
                this.updateScore(this._activeDragAxis, newVal);
            });

            const stopDrag = () => {
                if (this._isDragging) {
                    this._isDragging = false;
                    this._activeDragAxis = null;
                    this._hideTooltip();
                }
            };
            window.addEventListener("mouseup", stopDrag);
            svg.addEventListener("mouseleave", stopDrag);
        }

        // Axis Metric Labels
        if (this.options.showLabels) {
            const labelDist = radius + 22;
            this.axes.forEach((axis) => {
                const lx = centerX + labelDist * Math.cos(axis.angle);
                const ly = centerY + labelDist * Math.sin(axis.angle);

                const text = document.createElementNS(svgNS, "text");
                text.setAttribute("x", lx);
                text.setAttribute("y", ly + 4);
                text.setAttribute("fill", textColor);
                text.setAttribute("font-size", "10.5px");
                text.setAttribute("font-weight", "600");
                text.setAttribute("font-family", "monospace, sans-serif");

                if (Math.abs(axis.angle - -Math.PI / 2) < 0.1 || Math.abs(axis.angle - Math.PI / 2) < 0.1) {
                    text.setAttribute("text-anchor", "middle");
                } else if (lx > centerX) {
                    text.setAttribute("text-anchor", "start");
                } else {
                    text.setAttribute("text-anchor", "end");
                }

                text.textContent = axis.label;
                svg.appendChild(text);
            });
        }

        // Center / Top SCA Cupping Score Badge
        if (this.options.showScoreBadge) {
            const scaData = this.calculateSCAScore();
            const badgeG = document.createElementNS(svgNS, "g");
            badgeG.setAttribute("class", "sca-score-badge");
            badgeG.innerHTML = `
                <rect x="${centerX - 42}" y="${height - 24}" width="84" height="20" rx="10"
                      fill="rgba(30, 18, 11, 0.85)" stroke="${scaData.badgeColor}" stroke-width="1"/>
                <text x="${centerX}" y="${height - 10}" fill="#FAF6F0" font-size="10px" font-weight="700"
                      font-family="monospace" text-anchor="middle">SCA: ${scaData.score.toFixed(1)}</text>
            `;
            svg.appendChild(badgeG);
            this.scoreBadge = badgeG;
        }

        this.svg = svg;
        this.container.appendChild(svg);
    }

    updateScore(axisKey, value) {
        if (!this.scores.hasOwnProperty(axisKey)) return;
        this.scores[axisKey] = Math.min(10.0, Math.max(1.0, value));

        const newPoints = this._calculatePoints(this.scores);
        const pointsStr = this._pointsToString(newPoints);

        if (this.polygon) {
            this.polygon.setAttribute("points", pointsStr);
        }

        if (this.dots && this.dots.length === newPoints.length) {
            newPoints.forEach((pt, idx) => {
                const dot = this.dots[idx];
                if (dot) {
                    dot.setAttribute("cx", pt.x);
                    dot.setAttribute("cy", pt.y);
                    dot.setAttribute("data-val", pt.val);
                }
            });
        }

        if (this.scoreBadge) {
            const scaData = this.calculateSCAScore();
            const rect = this.scoreBadge.querySelector("rect");
            const text = this.scoreBadge.querySelector("text");
            if (rect) rect.setAttribute("stroke", scaData.badgeColor);
            if (text) text.textContent = `SCA: ${scaData.score.toFixed(1)}`;
        }

        // Callback and DOM Event Dispatch
        if (typeof this.options.onChange === "function") {
            this.options.onChange(this.scores, this.calculateSCAScore());
        }

        if (this.container) {
            this.container.dispatchEvent(new CustomEvent("innokafe-sensory-change", {
                bubbles: true,
                detail: {
                    scores: this.scores,
                    sca: this.calculateSCAScore(),
                }
            }));
        }
    }

    update(newScores, secondaryScores = null) {
        this.scores = this._normalizeScores(newScores);
        if (secondaryScores) {
            this.secondaryScores = this._normalizeScores(secondaryScores);
        }

        const newPoints = this._calculatePoints(this.scores);
        const pointsStr = this._pointsToString(newPoints);

        if (this.polygon) {
            this.polygon.setAttribute("points", pointsStr);
        }

        if (this.secondaryPolygon && this.secondaryScores) {
            const secPoints = this._calculatePoints(this.secondaryScores);
            this.secondaryPolygon.setAttribute("points", this._pointsToString(secPoints));
        }

        if (this.dots && this.dots.length === newPoints.length) {
            newPoints.forEach((pt, idx) => {
                const dot = this.dots[idx];
                if (dot) {
                    dot.setAttribute("cx", pt.x);
                    dot.setAttribute("cy", pt.y);
                    dot.setAttribute("data-val", pt.val);
                }
            });
        }

        if (this.scoreBadge) {
            const scaData = this.calculateSCAScore();
            const rect = this.scoreBadge.querySelector("rect");
            const text = this.scoreBadge.querySelector("text");
            if (rect) rect.setAttribute("stroke", scaData.badgeColor);
            if (text) text.textContent = `SCA: ${scaData.score.toFixed(1)}`;
        }
    }

    _showTooltip(e, label, val) {
        let tooltip = document.getElementById("innokafe-sensory-tooltip");
        if (!tooltip) {
            tooltip = document.createElement("div");
            tooltip.id = "innokafe-sensory-tooltip";
            tooltip.style.position = "fixed";
            tooltip.style.padding = "6px 12px";
            tooltip.style.background = "rgba(30, 18, 11, 0.95)";
            tooltip.style.border = "1px solid #D48842";
            tooltip.style.color = "#FAF6F0";
            tooltip.style.borderRadius = "6px";
            tooltip.style.fontSize = "12px";
            tooltip.style.fontWeight = "600";
            tooltip.style.pointerEvents = "none";
            tooltip.style.zIndex = "9999";
            tooltip.style.boxShadow = "0 4px 14px rgba(0,0,0,0.4)";
            tooltip.style.transition = "opacity 0.15s ease";
            document.body.appendChild(tooltip);
        }
        tooltip.innerHTML = `<span>${label}:</span> <strong style="color: #E6A15C; margin-left: 4px;">${val}/10</strong>`;
        tooltip.style.left = `${e.clientX + 12}px`;
        tooltip.style.top = `${e.clientY - 28}px`;
        tooltip.style.opacity = "1";
    }

    _hideTooltip() {
        const tooltip = document.getElementById("innokafe-sensory-tooltip");
        if (tooltip) {
            tooltip.style.opacity = "0";
        }
    }
}

// Window global registration for universal access
if (typeof window !== "undefined") {
    window.InnokafeSensoryWheel = InnokafeSensoryWheel;

    const initSensoryWheels = () => {
        document.querySelectorAll("[data-sensory-wheel]").forEach((el) => {
            if (el.__innokafe_wheel_initialized) return;
            try {
                const raw = el.getAttribute("data-sensory-wheel");
                const scores = raw ? JSON.parse(raw) : {};
                el.__innokafe_wheel_initialized = true;
                new InnokafeSensoryWheel(el, scores);
            } catch (err) {
                console.warn("Sensory wheel auto-init error:", err);
            }
        });
    };
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSensoryWheels);
    } else {
        initSensoryWheels();
    }
}

export default InnokafeSensoryWheel;
