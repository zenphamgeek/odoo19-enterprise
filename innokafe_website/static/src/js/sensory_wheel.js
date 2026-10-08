/** @odoo-module **/

/**
 * Innokafe 6-Axis Interactive Sensory Radar Chart
 * Renders SCA Specialty Coffee sensory radar charts in polar coordinates:
 * Axes: Aroma (-90°), Acidity (-30°), Body (30°), Sweetness (90°), Clean Cup (150°), Aftertaste (210°)
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
                interactive: true,
                showLabels: true,
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
        this.svg = null;
        this.polygon = null;
        this.dots = [];
        this.init();
    }

    _normalizeScores(scores) {
        scores = scores || {};
        const parseScore = (val, fallback) => {
            if (val === undefined || val === null || val === "" || isNaN(Number(val))) {
                return fallback;
            }
            return Math.min(10.0, Math.max(1.0, parseFloat(val)));
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

    _calculatePoints(scores) {
        const { centerX, centerY, radius } = this.options;
        return this.axes.map((axis) => {
            const val = typeof scores[axis.key] === "number" ? scores[axis.key] : 5.0;
            const r = radius * (val / 10.0);
            const x = Math.round((centerX + r * Math.cos(axis.angle)) * 10) / 10;
            const y = Math.round((centerY + r * Math.sin(axis.angle)) * 10) / 10;
            return { x, y, val, key: axis.key, label: axis.label };
        });
    }

    _pointsToString(points) {
        return points.map((p) => `${p.x},${p.y}`).join(" ");
    }

    init() {
        if (!this.container) return;
        this.container.innerHTML = "";

        const { width, height, centerX, centerY, radius, color, darkColor, textColor } = this.options;
        const currentPoints = this._calculatePoints(this.scores);
        const pointsStr = this._pointsToString(currentPoints);

        const svgNS = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(svgNS, "svg");
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.setAttribute("class", "innokafe-sensory-wheel-svg");
        svg.setAttribute("style", "width: 100%; height: 100%; overflow: visible; display: block;");

        // Defs (Gradients & Glow Filters)
        const defs = document.createElementNS(svgNS, "defs");
        const gradId = "sensoryGrad_" + Math.random().toString(36).substr(2, 9);
        const glowId = "sensoryGlow_" + Math.random().toString(36).substr(2, 9);

        defs.innerHTML = `
            <radialGradient id="${gradId}" cx="50%" cy="50%" r="65%">
                <stop offset="0%" stop-color="${color}" stop-opacity="0.65"/>
                <stop offset="100%" stop-color="${darkColor}" stop-opacity="0.25"/>
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

        // Radial Axis Spoke Lines
        this.axes.forEach((axis) => {
            const line = document.createElementNS(svgNS, "line");
            line.setAttribute("x1", centerX);
            line.setAttribute("y1", centerY);
            line.setAttribute("x2", centerX + radius * Math.cos(axis.angle));
            line.setAttribute("y2", centerY + radius * Math.sin(axis.angle));
            line.setAttribute("stroke", "rgba(247, 242, 234, 0.22)");
            line.setAttribute("stroke-dasharray", "2,3");
            line.setAttribute("stroke-width", "1");
            svg.appendChild(line);
        });

        // The Sensory Data Polygon
        const polygon = document.createElementNS(svgNS, "polygon");
        polygon.setAttribute("points", pointsStr);
        polygon.setAttribute("fill", `url(#${gradId})`);
        polygon.setAttribute("stroke", color);
        polygon.setAttribute("stroke-width", "2.5");
        polygon.setAttribute("stroke-linejoin", "round");
        polygon.setAttribute("filter", `url(#${glowId})`);
        polygon.setAttribute("style", "transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);");
        svg.appendChild(polygon);
        this.polygon = polygon;

        // Interactive Data Dots
        this.dots = [];
        currentPoints.forEach((pt) => {
            const dot = document.createElementNS(svgNS, "circle");
            dot.setAttribute("cx", pt.x);
            dot.setAttribute("cy", pt.y);
            dot.setAttribute("r", "4.5");
            dot.setAttribute("fill", "#FAF6F0");
            dot.setAttribute("stroke", color);
            dot.setAttribute("stroke-width", "2");
            dot.setAttribute("style", "cursor: pointer; transition: all 0.3s ease;");
            dot.setAttribute("data-axis", pt.key);
            dot.setAttribute("data-val", pt.val);

            // Hover effects & Tooltip
            dot.addEventListener("mouseenter", (e) => {
                dot.setAttribute("r", "7");
                dot.setAttribute("fill", color);
                this._showTooltip(e, pt.label, pt.val);
            });
            dot.addEventListener("mouseleave", () => {
                dot.setAttribute("r", "4.5");
                dot.setAttribute("fill", "#FAF6F0");
                this._hideTooltip();
            });

            svg.appendChild(dot);
            this.dots.push(dot);
        });

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
                text.setAttribute("font-size", "11px");
                text.setAttribute("font-weight", "600");
                text.setAttribute("font-family", "Plus Jakarta Sans, sans-serif");

                // Text alignment based on angle
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

        this.svg = svg;
        this.container.appendChild(svg);
    }

    update(newScores) {
        this.scores = this._normalizeScores(newScores);
        const newPoints = this._calculatePoints(this.scores);
        const pointsStr = this._pointsToString(newPoints);

        if (this.polygon) {
            this.polygon.setAttribute("points", pointsStr);
        }

        // Update dots positions
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

    // Auto-init for any elements with [data-sensory-wheel]
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
