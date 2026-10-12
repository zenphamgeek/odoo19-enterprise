# -*- coding: utf-8 -*-
import json
import logging
import math
import time
from markupsafe import Markup
from odoo import http
from odoo.http import request, Request
from odoo.addons.website.controllers.main import Website

_logger = logging.getLogger(__name__)

# Ensure backward-compatible request.website attribute access in Odoo 20 QWeb templates
if not hasattr(Request, "website"):
    def _get_req_website(self):
        if hasattr(self, "_website_instance"):
            return self._website_instance
        try:
            if hasattr(self, "env") and self.env and "website" in self.env:
                return self.env["website"].get_current_website()
        except Exception:
            pass
        return None

    def _set_req_website(self, val):
        self._website_instance = val

    Request.website = property(_get_req_website, _set_req_website)

# ==============================================================================
# INNOKAFE SIGNATURE SPECIALTY COFFEE CATALOGUE & SENSORY SPECIFICATIONS
# ==============================================================================

WEIGHTS = {
    "body": 1.2,
    "acidity": 1.3,
    "sweetness": 1.0,
    "caffeine": 1.1,
    "nutty_choco": 1.0,
    "fruity_floral": 1.0,
    "balance": 0.9,
}
D_MAX = math.sqrt(sum(w * (9.0 ** 2) for w in WEIGHTS.values()))  # ~24.6475


def parse_cart_quantity(quantity, default=1, max_qty=1000):
    """
    Parses and sanitizes cart item quantity for specialty coffee packages.
    Ensures quantity is a positive whole integer within retail limits.
    """
    if quantity is None:
        return default
    if isinstance(quantity, bool):
        raise TypeError("Quantity cannot be boolean")
    if isinstance(quantity, str):
        s = quantity.strip()
        if not s:
            return default
        try:
            quantity = float(s)
        except ValueError:
            raise ValueError(f"Invalid non-numeric quantity: {quantity}")
    if isinstance(quantity, float):
        if not quantity.is_integer():
            raise ValueError(f"Fractional quantities not allowed for package units: {quantity}")
        quantity = int(quantity)
    if not isinstance(quantity, int):
        raise TypeError(f"Quantity must be integer, got {type(quantity).__name__}")
    if quantity <= 0:
        raise ValueError(f"Cart quantity must be strictly positive: {quantity}")
    if quantity > max_qty:
        raise ValueError(
            f"Quantity {quantity} exceeds maximum retail cart limit of {max_qty}. "
            "Please contact B2B wholesale at /solutions-b2b for bulk orders."
        )
    return quantity


def validate_cart_payload(payload, sku_catalog=None):
    """
    Validates add-to-cart payload schema and parameters.
    Ensures product_id is a positive integer and quantity is valid.
    """
    if not isinstance(payload, dict):
        raise TypeError("Cart payload must be a dictionary")
    if "product_id" not in payload and "product_template_id" not in payload:
        raise KeyError("Missing required field: product_id")

    pid = payload.get("product_id") if payload.get("product_id") is not None else payload.get("product_template_id")
    if isinstance(pid, bool) or not isinstance(pid, int):
        raise TypeError(f"product_id must be integer, got {type(pid).__name__}")
    if pid <= 0:
        raise ValueError(f"product_id must be a positive database ID, got {pid}")

    raw_qty = payload.get("quantity", payload.get("add_qty", 1))
    qty = parse_cart_quantity(raw_qty)

    if sku_catalog:
        valid_pids = {s.get("product_id") for s in sku_catalog if s.get("product_id")}
        if valid_pids and pid not in valid_pids:
            raise LookupError(f"Product ID {pid} not found in signature SKU catalog")

    return {"product_id": pid, "quantity": qty}


def compute_radar_points(sensory_scores, center_x=150, center_y=150, radius=100):
    """
    Computes SVG polygon points for a 6-axis radar chart in SCA order:
    0: Aroma (-90 deg), 1: Acidity (-30 deg), 2: Body (30 deg),
    3: Sweetness (90 deg), 4: Clean Cup (150 deg), 5: Aftertaste (210 deg).
    """
    axes = ["aroma", "acidity", "body", "sweetness", "cleancup", "aftertaste"]
    coords = []
    sensory_scores = sensory_scores or {}
    for i, axis in enumerate(axes):
        raw_val = sensory_scores.get(axis)
        try:
            score = float(raw_val) if raw_val is not None else 5.0
        except (ValueError, TypeError):
            score = 5.0
        clamped_score = min(10.0, max(1.0, score))
        angle = -math.pi / 2.0 + i * (math.pi / 3.0)
        r = radius * (clamped_score / 10.0)
        x = round(center_x + r * math.cos(angle), 1)
        y = round(center_y + r * math.sin(angle), 1)
        coords.append(f"{x},{y}")
    return " ".join(coords)


SIGNATURE_SKUS = [
    {
        "sku_code": "INNO-ROBUSTA-NAT-01",
        "name": "Đắk Lắk Highland Fine Robusta Natural",
        "tagline": "Bản sắc đại ngàn, vị đậm đà sâu lắng, ngọt sâu hậu vị",
        "origin": "Cư M'gar, Đắk Lắk (Độ cao 750m)",
        "varietal": "Robusta Sẻ thuần chủng",
        "process": "Natural (Phơi khô nguyên quả 28 ngày trên giàn)",
        "roast_level": "Medium-Dark (Agtron 48)",
        "cupping_score": 84.50,
        "tasting_notes": ["Sô-cô-la đen 85%", "Hạt dẻ nướng", "Mật mía", "Gỗ sồi"],
        "tasting_notes_str": "Sô-cô-la đen 85%, Hạt dẻ nướng, Mật mía, Gỗ sồi",
        "vector": {
            "body": 9.5,
            "acidity": 3.5,
            "sweetness": 8.5,
            "caffeine": 9.5,
            "nutty_choco": 9.0,
            "fruity_floral": 3.0,
            "balance": 7.5,
        },
        "sensory_scores": {
            "aroma": 8.5,
            "acidity": 3.5,
            "body": 9.5,
            "sweetness": 8.5,
            "cleancup": 8.0,
            "aftertaste": 9.0,
        },
        "price_250g": 125000,
        "price_500g": 235000,
        "price_1kg": 440000,
        "best_brew": ["phin", "espresso"],
        "best_brew_labels": ["Phin truyền thống", "Cà phê sữa đá", "Espresso"],
        "image_url": "/innokafe_website/static/src/img/beans_robusta_natural.svg",
    },
    {
        "sku_code": "INNO-ARABICA-WASH-02",
        "name": "Cầu Đất Mountain Bourbon Washed",
        "tagline": "Tinh hoa sương mù, chua thanh hoa nhài, trong trẻo tao nhã",
        "origin": "Trạm Hành, Cầu Đất, Lâm Đồng (Độ cao 1.620m)",
        "varietal": "Arabica Bourbon & Catimor",
        "process": "Fully Washed (Lên men kiểm soát 32 giờ, phơi giàn 14 ngày)",
        "roast_level": "Light-Medium (Agtron 72)",
        "cupping_score": 86.75,
        "tasting_notes": ["Hoa nhài trắng", "Cam Bergamot", "Táo xanh", "Trà Earl Grey"],
        "tasting_notes_str": "Hoa nhài trắng, Cam Bergamot, Táo xanh, Trà Earl Grey",
        "vector": {
            "body": 6.0,
            "acidity": 9.0,
            "sweetness": 8.0,
            "caffeine": 3.5,
            "nutty_choco": 3.0,
            "fruity_floral": 9.5,
            "balance": 8.5,
        },
        "sensory_scores": {
            "aroma": 9.5,
            "acidity": 9.0,
            "body": 6.0,
            "sweetness": 8.0,
            "cleancup": 9.5,
            "aftertaste": 8.5,
        },
        "price_250g": 185000,
        "price_500g": 350000,
        "price_1kg": 660000,
        "best_brew": ["pourover", "dripbag", "coldbrew"],
        "best_brew_labels": ["Pour-over V60", "Cold Brew", "Drip Bag"],
        "image_url": "/innokafe_website/static/src/img/beans_arabica_washed.svg",
    },
    {
        "sku_code": "INNO-SIGNATURE-HONEY-03",
        "name": "Innokafe Heritage Signature Red Honey",
        "tagline": "Khúc giao hòa đỉnh cao, ngọt ngào mật ong rừng, kem bơ sánh quyện",
        "origin": "Blend 70% Cầu Đất Arabica x 30% Cư M'gar Robusta",
        "varietal": "Catimor x Robusta Sẻ",
        "process": "Red Honey (Giữ 75% lớp nhầy đường, phơi chậm 18 ngày)",
        "roast_level": "Medium Roast (Agtron 58)",
        "cupping_score": 85.50,
        "tasting_notes": ["Mật ong rừng", "Caramel bơ", "Táo đỏ", "Hạnh nhân"],
        "tasting_notes_str": "Mật ong rừng, Caramel bơ, Táo đỏ, Hạnh nhân",
        "vector": {
            "body": 8.0,
            "acidity": 6.8,
            "sweetness": 9.2,
            "caffeine": 6.5,
            "nutty_choco": 7.5,
            "fruity_floral": 7.0,
            "balance": 9.0,
        },
        "sensory_scores": {
            "aroma": 9.0,
            "acidity": 6.8,
            "body": 8.0,
            "sweetness": 9.2,
            "cleancup": 8.8,
            "aftertaste": 8.8,
        },
        "price_250g": 155000,
        "price_500g": 295000,
        "price_1kg": 550000,
        "best_brew": ["espresso", "phin", "pourover", "dripbag"],
        "best_brew_labels": ["Espresso", "Phin hiện đại", "Americano", "Pour-over"],
        "image_url": "/innokafe_website/static/src/img/beans_heritage_honey.svg",
    },
    {
        "sku_code": "INNO-DRIP-EXPLORER-04",
        "name": "Hộp Drip Bag Khám Phá Nghệ Nhân (Artisan Box 10 Gói)",
        "tagline": "Tiện lợi mọi lúc mọi nơi, đẳng cấp cà phê phin giấy lọc Nhật Bản",
        "origin": "Đa vùng trồng (Cầu Đất, Đắk Lắk)",
        "varietal": "Tuyển tập Arabica & Fine Robusta",
        "process": "Phối trộn 3 phương pháp sơ chế",
        "roast_level": "Medium (Agtron 62)",
        "cupping_score": 85.00,
        "tasting_notes": ["Caramel", "Hạt dẻ", "Quả mọng", "Hương hoa"],
        "tasting_notes_str": "Caramel, Hạt dẻ, Quả mọng, Hương hoa",
        "vector": {
            "body": 7.5,
            "acidity": 7.0,
            "sweetness": 8.2,
            "caffeine": 6.0,
            "nutty_choco": 7.0,
            "fruity_floral": 7.0,
            "balance": 8.5,
        },
        "sensory_scores": {
            "aroma": 8.8,
            "acidity": 7.0,
            "body": 7.5,
            "sweetness": 8.2,
            "cleancup": 9.0,
            "aftertaste": 8.2,
        },
        "price_250g": 165000,
        "price_500g": 165000,
        "price_1kg": 165000,
        "best_brew": ["dripbag"],
        "best_brew_labels": ["Phin giấy Drip Bag", "Pha nhanh văn phòng"],
        "image_url": "/innokafe_website/static/src/img/beans_drip_bag.svg",
    },
    {
        "sku_code": "INNO-COLDBREW-CITRUS-05",
        "name": "Innokafe Cold Brew Blend Summer Citrus",
        "tagline": "Sảng khoái mùa hè, chua ngọt bùng nổ, ủ lạnh 24h ngọt ngào",
        "origin": "Cầu Đất, Lâm Đồng (Độ cao 1.550m)",
        "varietal": "100% Arabica Catimor",
        "process": "Natural x Washed Blend",
        "roast_level": "Light (Agtron 78)",
        "cupping_score": 86.00,
        "tasting_notes": ["Cam vàng Valencia", "Đào chín", "Mật hoa dại", "Hương chanh"],
        "tasting_notes_str": "Cam vàng Valencia, Đào chín, Mật hoa dại, Hương chanh",
        "vector": {
            "body": 5.5,
            "acidity": 8.5,
            "sweetness": 9.0,
            "caffeine": 4.5,
            "nutty_choco": 3.5,
            "fruity_floral": 9.0,
            "balance": 8.5,
        },
        "sensory_scores": {
            "aroma": 9.2,
            "acidity": 8.5,
            "body": 5.5,
            "sweetness": 9.0,
            "cleancup": 9.2,
            "aftertaste": 8.0,
        },
        "price_250g": 175000,
        "price_500g": 330000,
        "price_1kg": 620000,
        "best_brew": ["coldbrew", "pourover", "dripbag"],
        "best_brew_labels": ["Ủ lạnh Cold Brew", "Espresso Tonic", "Pour-over"],
        "image_url": "/innokafe_website/static/src/img/beans_coldbrew_citrus.svg",
    },
    {
        "sku_code": "INNO-HORECA-BARISTA-06",
        "name": "Innokafe Espresso Barista Master 80/20",
        "tagline": "Chuẩn mực quầy bar chuyên nghiệp, crema dày mịn, ổn định chiết xuất",
        "origin": "80% Cư M'gar Robusta Sẻ x 20% Cầu Đất Arabica",
        "varietal": "Fine Robusta & Catimor",
        "process": "Honey & Natural",
        "roast_level": "Medium-Dark (Agtron 50)",
        "cupping_score": 84.00,
        "tasting_notes": ["Ca cao đắng 70%", "Bơ đậu phộng", "Caramel khói", "Vỏ cam sấy"],
        "tasting_notes_str": "Ca cao đắng 70%, Bơ đậu phộng, Caramel khói, Vỏ cam sấy",
        "vector": {
            "body": 9.2,
            "acidity": 4.0,
            "sweetness": 8.0,
            "caffeine": 8.8,
            "nutty_choco": 8.8,
            "fruity_floral": 4.0,
            "balance": 8.0,
        },
        "sensory_scores": {
            "aroma": 8.2,
            "acidity": 4.0,
            "body": 9.2,
            "sweetness": 8.0,
            "cleancup": 8.2,
            "aftertaste": 8.8,
        },
        "price_250g": 135000,
        "price_500g": 245000,
        "price_1kg": 380000,
        "best_brew": ["espresso", "phin"],
        "best_brew_labels": ["Máy pha Espresso", "Latte / Cappuccino", "Phin quán"],
        "image_url": "/innokafe_website/static/src/img/beans_espresso_barista.svg",
    },
]

# Enrich pre-computed polygon points
for item in SIGNATURE_SKUS:
    item["radar_points"] = compute_radar_points(item["sensory_scores"])


def calculate_match_scores(habit, gear, flavor, caffeine):
    """
    7D Euclidean Vector Matchmaking Algorithm
    Matches user answers to the 6 Specialty Coffee SKUs.
    Yields calibrated match scores in the range 85% - 94%.
    """
    u = {
        "body": 5.0,
        "acidity": 5.0,
        "sweetness": 5.0,
        "caffeine": 5.0,
        "nutty_choco": 5.0,
        "fruity_floral": 5.0,
        "balance": 5.0,
    }

    # Step 1: Routine / Habit impact
    if habit == "phin_dam":
        u["body"] += 4.0
        u["caffeine"] += 3.0
        u["acidity"] -= 2.0
        u["nutty_choco"] += 3.0
    elif habit == "sua_da":
        u["sweetness"] += 4.0
        u["body"] += 3.0
        u["nutty_choco"] += 4.0
        u["acidity"] -= 3.0
    elif habit == "den_thanh":
        u["acidity"] += 4.0
        u["fruity_floral"] += 4.0
        u["body"] -= 2.0
        u["balance"] += 2.0
    elif habit == "coldbrew_sangtao":
        u["sweetness"] += 3.0
        u["fruity_floral"] += 3.0
        u["balance"] += 3.0
        u["acidity"] += 1.0

    # Step 3: Flavor Preference impact
    if flavor == "nutty_choco":
        u["nutty_choco"] += 4.0
        u["body"] += 2.0
        u["acidity"] -= 2.0
    elif flavor == "fruity_floral":
        u["fruity_floral"] += 4.5
        u["acidity"] += 3.5
        u["balance"] += 1.0
    elif flavor == "honey_balanced":
        u["sweetness"] += 4.0
        u["balance"] += 4.0
        u["body"] += 1.0

    # Step 4: Caffeine Sensitivity impact
    if caffeine == "high":
        u["caffeine"] = 9.5
    elif caffeine == "medium":
        u["caffeine"] = 6.0
    elif caffeine == "low":
        u["caffeine"] = 3.0

    # Clamping user vector dimensions to [1.0, 10.0]
    for k in u:
        u[k] = max(1.0, min(10.0, u[k]))

    ranked = []
    for item in SIGNATURE_SKUS:
        p_vec = item["vector"]
        dist_sq = sum(WEIGHTS[dim] * ((u[dim] - p_vec[dim]) ** 2) for dim in WEIGHTS)
        dist = math.sqrt(dist_sq)

        gamma = 1.0 if (not gear or gear in item["best_brew"]) else 0.88
        base_sim = (1.0 - (dist / D_MAX)) * 100.0 * gamma
        match_score = min(94.0, max(85.0, base_sim * 0.285 + 68.35))

        entry = dict(item)
        entry["dist"] = round(dist, 2)
        entry["match_score"] = round(match_score, 1)
        ranked.append(entry)

    ranked.sort(key=lambda x: x["match_score"], reverse=True)
    return ranked, u


# ==============================================================================
# MAIN CONTROLLER CLASS
# ==============================================================================

class InnokafeMainController(Website):

    def _base_values(self):
        website = request.env["website"].get_current_website() if "website" in request.env else None
        return {
            "company": request.env.company,
            "website": website,
            "signature_skus": SIGNATURE_SKUS,
        }

    def _lookup_db_products(self):
        """Lookup database products for real product IDs if seeded."""
        product_map = {}
        try:
            ProductTemplate = request.env["product.template"].sudo()
            codes = [p["sku_code"] for p in SIGNATURE_SKUS]
            records = ProductTemplate.search([("default_code", "in", codes)])
            for rec in records:
                if rec.default_code:
                    product_map[rec.default_code] = rec
        except Exception as e:
            _logger.warning("Could not lookup product templates: %s", e)
        return product_map

    # --------------------------------------------------------------------------
    # CANONICAL URL ROUTING: PURGE /en, /en/en, AND /vi PREFIXES
    # --------------------------------------------------------------------------

    @http.route([
        "/en", "/en/", "/en/<path:subpath>",
        "/vi", "/vi/", "/vi/<path:subpath>",
    ], type="http", auth="public", website=True)
    def clean_language_redirect(self, subpath="", **kwargs):
        """
        Enforces canonical Vietnamese root routing.
        Permanently 301-redirects legacy /en, /en/en, /vi, and /vi/* prefixes to
        clean canonical routes (e.g. /en -> /, /en/story -> /story).
        """
        ws = getattr(request, 'website', None)
        if ws and ('innokafe' in (ws.domain or '') or 'innokafe' in (ws.name or '').lower()):
            clean_path = (subpath or "").strip("/")
            while clean_path.startswith("en/") or clean_path.startswith("vi/"):
                clean_path = clean_path[3:].lstrip("/")
            if clean_path in ("en", "vi"):
                clean_path = ""
            target = f"/{clean_path}" if clean_path else "/"
            qs = request.httprequest.query_string.decode("utf-8") if request.httprequest.query_string else ""
            if qs:
                target = f"{target}?{qs}"
            return request.redirect(target, code=301)
        return request.not_found()

    # --------------------------------------------------------------------------
    # PUBLIC ROUTES
    # --------------------------------------------------------------------------

    @http.route(["/"], type="http", auth="public", website=True, sitemap=True)
    def index(self, **kwargs):
        ws = getattr(request, 'website', None)
        if not (ws and ('innokafe' in (ws.domain or '') or 'innokafe' in (ws.name or '').lower())):
            return super().index(**kwargs)
        values = self._base_values()
        try:
            products = request.env["product.template"].sudo().search([
                ("is_published", "=", True),
            ], limit=6)
            values["featured_products"] = products
        except Exception:
            values["featured_products"] = []
        return request.render("innokafe_website.homepage", values)

    @http.route(["/story"], type="http", auth="public", website=True, sitemap=True)
    def story(self, **kwargs):
        values = self._base_values()
        return request.render("innokafe_website.story_page", values)

    @http.route(["/products"], type="http", auth="public", website=True, sitemap=True)
    def products(self, **kwargs):
        values = self._base_values()
        try:
            categories = request.env["product.public.category"].sudo().search([])
            products = request.env["product.template"].sudo().search([
                ("is_published", "=", True),
            ])
            values["categories"] = categories
            values["products"] = products
        except Exception:
            values["categories"] = []
            values["products"] = []
        return request.render("innokafe_website.products_page", values)

    @http.route(
        [
            "/taste-profiler",
            "/taste-profiler/",
            "/taste-profiler/quiz",
            "/taste-profiler/start",
            "/taste-profiler/step/<int:step_id>",
            "/taste-profiler/result",
            "/taste-profiler/result/<string:sku_code>",
            "/taste-profiler/sku/<string:sku_code>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def taste_profiler(self, step_id=None, sku_code=None, **kwargs):
        values = self._base_values()
        db_map = self._lookup_db_products()
        # Merge database IDs into signature skus for add-to-cart
        hydrated_skus = []
        for sku in SIGNATURE_SKUS:
            item = dict(sku)
            db_prod = db_map.get(sku["sku_code"])
            if db_prod:
                item["product_id"] = db_prod.product_variant_id.id if db_prod.product_variant_id else db_prod.id
                item["product_tmpl_id"] = db_prod.id
            else:
                item["product_id"] = 1
                item["product_tmpl_id"] = 1
            hydrated_skus.append(item)
        values["signature_skus"] = hydrated_skus
        values["skus_json"] = Markup(json.dumps(hydrated_skus))

        # Check for deep-linked SKU or direct quiz parameters
        target_sku = sku_code or kwargs.get("sku") or kwargs.get("sku_code")
        habit = kwargs.get("habit")
        gear = kwargs.get("gear")
        flavor = kwargs.get("flavor")
        caffeine = kwargs.get("caffeine")

        # Determine route context
        path = request.httprequest.path.rstrip("/")
        is_result_path = path.endswith("/result") or "/result/" in path or "/sku/" in path

        top1 = None
        top2 = None
        user_vector = None
        initial_step = 1

        if step_id is not None:
            if 1 <= step_id <= 4:
                initial_step = step_id
            elif step_id >= 5:
                initial_step = 5
            else:
                initial_step = 1

        if habit and gear and flavor and caffeine:
            ranked_skus, user_vector = calculate_match_scores(habit, gear, flavor, caffeine)
            for item in ranked_skus:
                db_prod = db_map.get(item["sku_code"])
                if db_prod:
                    item["product_id"] = db_prod.product_variant_id.id if db_prod.product_variant_id else db_prod.id
                    item["product_tmpl_id"] = db_prod.id
                else:
                    item["product_id"] = 1
                    item["product_tmpl_id"] = 1
            top1 = ranked_skus[0] if ranked_skus else None
            top2 = ranked_skus[1] if len(ranked_skus) > 1 else None
            initial_step = 5
        elif target_sku:
            clean_sku = target_sku.strip().upper().replace("_", "-")
            matched = [s for s in hydrated_skus if s["sku_code"].upper().replace("_", "-") == clean_sku]
            if matched:
                top1 = dict(matched[0])
                top1["match_score"] = 96.5
                others = [s for s in hydrated_skus if s["sku_code"] != top1["sku_code"]]
                top2 = dict(others[0]) if others else None
                if top2:
                    top2["match_score"] = 89.5
                initial_step = 5
                user_vector = top1.get("vector")
            else:
                top1 = dict(hydrated_skus[0])
                top1["match_score"] = 94.5
                top2 = dict(hydrated_skus[1])
                top2["match_score"] = 89.0
                initial_step = 5
                user_vector = top1.get("vector")
        elif is_result_path:
            top1 = dict(hydrated_skus[0])
            top1["match_score"] = 94.5
            top2 = dict(hydrated_skus[1])
            top2["match_score"] = 89.0
            initial_step = 5
            user_vector = top1.get("vector")

        # Step metadata and tailored SEO / OpenGraph / Hero parameters per route
        step_meta_details = {
            1: {
                "badge": "BƯỚC 1 / 4 • THÓI QUEN THƯỞNG THỨC",
                "title": "Khoảnh Khắc Cà Phê Lý Tưởng Trong Ngày",
                "lead": "Bạn tìm kiếm điều gì trong ly cà phê mỗi sáng? Chọn phong cách phản ánh đúng thói quen, nhịp sống và cảm xúc thưởng thức của bạn nhất.",
                "breadcrumb": "Bước 1: Phong Cách Thưởng Thức",
                "meta_title": "Bước 1: Phong Cách Thưởng Thức | Trắc Nghiệm Cảm Quan SCA | InnoKafe",
                "meta_desc": "Khám phá phong cách thưởng thức cà phê phù hợp với thói quen và khẩu vị của bạn qua trắc nghiệm cảm quan 4 bước chuẩn SCA.",
            },
            2: {
                "badge": "BƯỚC 2 / 4 • THIẾT BỊ CHIẾT XUẤT",
                "title": "Phương Pháp & Thiết Bị Pha Chế",
                "lead": "Dụng cụ chiết xuất quyết định áp suất, thời gian ngâm ủ và kích thước bột xay tối ưu. InnoKafe sẽ căn chỉnh cỡ rang và độ trích ly tương thích tuyệt đối.",
                "breadcrumb": "Bước 2: Thiết Bị Pha Chế",
                "meta_title": "Bước 2: Thiết Bị Pha Chế | Trắc Nghiệm Cảm Quan SCA | InnoKafe",
                "meta_desc": "Thiết bị chiết xuất (Phin, Espresso, V60, Drip Bag) quyết định độ trích ly và hồ sơ hương vị tối ưu.",
            },
            3: {
                "badge": "BƯỚC 3 / 4 • BẢN ĐỒ KHỨU GIÁC",
                "title": "Tông Hương Vị Độc Bản Cuốn Hút Nhất",
                "lead": "Khứu giác và vị giác của bạn tìm kiếm nốt hương nào? Chocolate đen 85% ấm nồng, hoa quả tươi sáng hay mật ong caramel ngọt ngào?",
                "breadcrumb": "Bước 3: Tông Hương Vị",
                "meta_title": "Bước 3: Tông Hương Vị Yêu Thích | Trắc Nghiệm Cảm Quan SCA | InnoKafe",
                "meta_desc": "Xác định bản đồ nốt hương khứu giác và khẩu vị riêng biệt trong tách specialty coffee rang mộc tự nhiên.",
            },
            4: {
                "badge": "BƯỚC 4 / 4 • CƯỜNG ĐỘ NĂNG LƯỢNG",
                "title": "Mức Độ Tiếp Nhận Caffeine & Độ Đậm Đặc",
                "lead": "Bạn cần cú bừng tỉnh mạnh mẽ từ Fine Robusta Cư M'gar, năng lượng êm dịu cân bằng từ Robusta/Arabica blend, hay sự thanh tao từ 100% Arabica núi sương?",
                "breadcrumb": "Bước 4: Mức Độ Caffeine",
                "meta_title": "Bước 4: Mức Độ Tiếp Nhận Caffeine | Trắc Nghiệm Cảm Quan SCA | InnoKafe",
                "meta_desc": "Định vị hàm lượng caffeine lý tưởng từ Robusta Cư M'gar đậm đà đến Arabica Cầu Đất dịu êm.",
            },
        }

        if initial_step == 5 and top1:
            hero_badge = f"HỒ SƠ CẢM QUAN • TƯƠNG THÍCH {top1.get('match_score', 96.5)}%"
            hero_title = f"Dòng Hạt Dành Cho Bạn: {top1.get('name')}"
            hero_lead = f"{top1.get('tagline')}. Dựa trên bản đồ vị giác và thói quen pha chế của bạn, InnoKafe tự hào giới thiệu dòng specialty rang mộc chuẩn SCA này."
            breadcrumb_step = top1.get("name")
            meta_title = f"{top1.get('name')} | Hồ Sơ Cảm Quan Gu Cà Phê | InnoKafe"
            meta_desc = f"{top1.get('tagline')} - Nốt hương: {top1.get('tasting_notes_str', '')}. Vùng trồng: {top1.get('origin', '')}. Điểm SCA: {top1.get('cupping_score')}."
            meta_image = top1.get("image_url", "/innokafe_website/static/src/img/beans_robusta_natural.svg")
            meta_url = f"https://innokafe.com/taste-profiler/result/{top1.get('sku_code')}"
        elif initial_step in step_meta_details:
            detail = step_meta_details[initial_step]
            hero_badge = detail["badge"]
            hero_title = detail["title"]
            hero_lead = detail["lead"]
            breadcrumb_step = detail["breadcrumb"]
            meta_title = detail["meta_title"]
            meta_desc = detail["meta_desc"]
            meta_image = "/innokafe_website/static/src/img/beans_robusta_natural.svg"
            meta_url = f"https://innokafe.com/taste-profiler/step/{initial_step}"
        else:
            hero_badge = "CÁ NHÂN HÓA TRẢI NGHIỆM THƯỞNG THỨC"
            hero_title = "Tìm Gu Cà Phê Của Bạn Trong 60 Giây"
            hero_lead = "Mỗi người sở hữu một bản đồ vị giác độc nhất. Chỉ 60 giây với 4 câu hỏi trắc nghiệm cảm quan chuẩn SCA, InnoKafe sẽ gợi ý chính xác dòng hạt rang mộc lý tưởng cho bạn."
            breadcrumb_step = None
            meta_title = "Tìm Gu Cà Phê Của Bạn | Trắc Nghiệm Cảm Quan SCA | InnoKafe"
            meta_desc = "Mỗi người sở hữu một bản đồ vị giác độc nhất. 60 giây với 4 câu hỏi trắc nghiệm cảm quan để tìm ra dòng hạt specialty rang mộc lý tưởng."
            meta_image = "/innokafe_website/static/src/img/beans_robusta_natural.svg"
            meta_url = "https://innokafe.com/taste-profiler"

        values["initial_step"] = initial_step
        values["hero_badge"] = hero_badge
        values["hero_title"] = hero_title
        values["hero_lead"] = hero_lead
        values["breadcrumb_step"] = breadcrumb_step
        values["meta_title"] = meta_title
        values["meta_desc"] = meta_desc
        values["meta_image"] = meta_image
        values["meta_url"] = meta_url
        values["top1"] = top1
        values["top2"] = top2
        values["discovery_box"] = next((s for s in hydrated_skus if s.get("sku_code") == "INNO-DRIP-EXPLORER-04"), None)
        values["user_vector"] = user_vector
        values["radar_points"] = compute_radar_points(top1.get("sensory_scores")) if top1 else ""
        return request.render("innokafe_website.taste_profiler_page", values)

    @http.route(
        "/taste-profiler/share/<string:sku_code>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def taste_profiler_share(self, sku_code=None, **kwargs):
        """Social sharing redirect / preview landing endpoint."""
        target_sku = (sku_code or "").strip().upper()
        return request.redirect(f"/taste-profiler/result/{target_sku}", code=302)

    @http.route(
        ["/taste-profiler/api/skus", "/taste-profiler/catalog"],
        type="http",
        auth="public",
        methods=["GET"],
        website=True,
        csrf=False,
    )
    def taste_profiler_catalog_api(self, **kwargs):
        """
        Public JSON API returning the 6 signature specialty coffee SKUs
        with complete 7D vectors, 6-axis SCA cupping scores, prices, tasting notes,
        and pre-computed SVG radar points.
        """
        db_map = self._lookup_db_products()
        hydrated_skus = []
        for sku in SIGNATURE_SKUS:
            item = dict(sku)
            db_prod = db_map.get(sku["sku_code"])
            if db_prod:
                item["product_id"] = db_prod.product_variant_id.id if db_prod.product_variant_id else db_prod.id
                item["product_tmpl_id"] = db_prod.id
            else:
                item["product_id"] = 1
                item["product_tmpl_id"] = 1
            hydrated_skus.append(item)
        return request.make_response(
            json.dumps({"status": "success", "count": len(hydrated_skus), "skus": hydrated_skus}, ensure_ascii=False),
            headers=[("Content-Type", "application/json; charset=utf-8"), ("Access-Control-Allow-Origin", "*")],
        )

    @http.route(
        ["/taste-profiler/cart/add", "/innokafe/cart/add"],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def taste_profiler_cart_add(self, product_id=None, product_template_id=None, quantity=1, **kwargs):
        """
        Adds selected taste-profiler specialty coffee product to shopping cart.
        """
        try:
            qty = int(quantity or 1)
            pid = int(product_id or product_template_id or 1)
            order_sudo = request.cart or request.website._create_cart()

            # Verify product exists in database
            product = request.env["product.product"].sudo().browse(pid).exists()
            if not product:
                product = request.env["product.product"].sudo().search([("sale_ok", "=", True)], limit=1)
                if product:
                    pid = product.id

            if product:
                order_sudo.with_context(skip_cart_verification=True)._cart_add(
                    product_id=pid,
                    quantity=qty,
                )
                return {
                    "status": "success",
                    "cart_quantity": order_sudo.cart_quantity,
                    "product_name": product.name,
                    "product_id": pid,
                }
            return {
                "status": "error",
                "message": "Không tìm thấy sản phẩm trong hệ thống.",
            }
        except Exception as e:
            _logger.warning("Error adding taste-profiler product to cart: %s", e)
            return {
                "status": "error",
                "message": str(e),
            }

    @http.route(["/solutions-b2b"], type="http", auth="public", website=True, sitemap=True)
    def solutions_b2b(self, **kwargs):
        values = self._base_values()
        values["submitted"] = kwargs.get("submitted") in ("1", "true", "True")
        return request.render("innokafe_website.solutions_b2b_page", values)

    @http.route(["/contactus"], type="http", auth="public", website=True, sitemap=True)
    def contactus(self, **kwargs):
        values = self._base_values()
        values["submitted"] = kwargs.get("submitted") in ("1", "true", "True")
        return request.render("innokafe_website.contactus_page", values)

    # --------------------------------------------------------------------------
    # FORM SUBMISSION HANDLERS
    # --------------------------------------------------------------------------

    @http.route(
        ["/solutions-b2b/submit", "/innokafe/b2b-submit"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def solutions_b2b_submit(self, **post):
        contact_name = (post.get("contact_name") or post.get("name") or "").strip()
        partner_name = (post.get("partner_name") or post.get("company_name") or "").strip()
        email = (post.get("email_from") or post.get("email") or "").strip()
        phone = (post.get("phone") or "").strip()
        job_position = (post.get("job_position") or post.get("function") or "").strip()
        street = (post.get("street") or post.get("address") or "").strip()
        business_type = (post.get("business_type") or "").strip()

        # Handle multiple checkboxes for service interest
        service_interest = post.get("service_interest", "")
        if isinstance(service_interest, list):
            service_interest_str = ", ".join(service_interest)
        else:
            service_interest_str = str(service_interest)

        monthly_volume = (post.get("estimated_monthly_volume") or post.get("volume") or "").strip()
        notes = (post.get("description") or post.get("notes") or "").strip()

        try:
            CRMLead = request.env["crm.lead"].sudo()
            CRMTag = request.env["crm.tag"].sudo()

            tag = CRMTag.search([("name", "=", "Innokafe B2B")], limit=1)
            if not tag:
                try:
                    tag = CRMTag.create({"name": "Innokafe B2B", "color": 8})
                except Exception:
                    tag = False

            partner_or_contact = partner_name or contact_name or "Khách hàng B2B"
            lead_name = f"Innokafe B2B: {partner_or_contact} - {service_interest_str or 'Horeca Inquiry'}"
            desc_lines = [
                "=== THÔNG TIN ĐĂNG KÝ GIẢI PHÁP B2B INNOKAFE ===",
                f"Người đại diện: {contact_name}",
                f"Chức danh: {job_position}",
                f"Tên doanh nghiệp / Quán: {partner_name}",
                f"Số điện thoại: {phone}",
                f"Email: {email}",
                f"Địa chỉ nhận mẫu thử: {street}",
                f"Mô hình kinh doanh: {business_type}",
                f"Nhu cầu quan tâm: {service_interest_str}",
                f"Sản lượng tiêu thụ dự kiến: {monthly_volume}",
                f"Ghi chú chi tiết: {notes}",
                "Nguồn: https://innokafe.com/solutions-b2b",
            ]

            lead_vals = {
                "name": lead_name,
                "partner_name": partner_name,
                "contact_name": contact_name,
                "email_from": email,
                "phone": phone,
                "street": street,
                "function": job_position,
                "description": "<br/>".join(desc_lines),
                "type": "opportunity",
            }
            if hasattr(request, "website") and request.website and request.website.company_id:
                lead_vals["company_id"] = request.website.company_id.id
            elif request.env.company:
                lead_vals["company_id"] = request.env.company.id

            if tag:
                lead_vals["tag_ids"] = [(4, tag.id)]

            lead = CRMLead.create(lead_vals)
            _logger.info("Successfully created Innokafe B2B CRM Lead #%s for %s", lead.id, contact_name)
        except Exception as e:
            _logger.error("Failed to create B2B CRM Lead: %s", e)

        return request.redirect("/solutions-b2b?submitted=1#b2b_form")

    @http.route(
        ["/contactus/submit", "/innokafe/contact-submit"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def contactus_submit(self, **post):
        name = (post.get("contact_name") or post.get("name") or "").strip()
        email = (post.get("email_from") or post.get("email") or "").strip()
        phone = (post.get("phone") or "").strip()
        subject = (post.get("subject") or "Lời nhắn từ khách hàng website").strip()
        message = (post.get("message") or post.get("description") or "").strip()

        try:
            CRMLead = request.env["crm.lead"].sudo()
            CRMTag = request.env["crm.tag"].sudo()

            tag = CRMTag.search([("name", "=", "Innokafe Contact")], limit=1)
            if not tag:
                try:
                    tag = CRMTag.create({"name": "Innokafe Contact", "color": 3})
                except Exception:
                    tag = False

            display_name = name or "Khách hàng Website"
            lead_name = f"Innokafe Contact: {subject} - {display_name}"
            desc_lines = [
                "=== THÔNG TIN LIÊN HỆ SHOWROOM & ROASTERY ===",
                f"Họ tên: {name}",
                f"Email: {email}",
                f"Số điện thoại: {phone}",
                f"Chủ đề: {subject}",
                f"Lời nhắn:<br/>{message}",
                "Nguồn: https://innokafe.com/contactus",
            ]

            lead_vals = {
                "name": lead_name,
                "contact_name": name,
                "email_from": email,
                "phone": phone,
                "description": "<br/>".join(desc_lines),
                "type": "lead",
            }
            if hasattr(request, "website") and request.website and request.website.company_id:
                lead_vals["company_id"] = request.website.company_id.id
            elif request.env.company:
                lead_vals["company_id"] = request.env.company.id

            if tag:
                lead_vals["tag_ids"] = [(4, tag.id)]

            lead = CRMLead.create(lead_vals)
            _logger.info("Successfully created Innokafe Contact Lead #%s for %s", lead.id, name)
        except Exception as e:
            _logger.error("Failed to create Contact Lead: %s", e)

        return request.redirect("/contactus?submitted=1#contact_form")

    # --------------------------------------------------------------------------
    # INNOKAFE CLUB SUBSCRIPTION HANDLERS
    # --------------------------------------------------------------------------

    @http.route(
        ["/innokafe/subscription/submit", "/club/subscribe"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def subscription_submit(self, **post):
        """
        Receives 3-step Artisan Subscription Club configurator payload,
        creates a CRM Opportunity with structured subscription metadata,
        and dispatches an executive confirmation email to the subscriber.
        """
        member_name = (post.get("member_name") or post.get("name") or post.get("contact_name") or "").strip() or "Hội viên InnoKafe"
        email = (post.get("email_from") or post.get("email") or "").strip()
        phone = (post.get("phone") or "").strip()
        shipping_address = (post.get("shipping_address") or post.get("street") or post.get("address") or "").strip()
        taste_preference = (post.get("taste_preference") or "dam_ban_sac").strip()
        weight_tier = (post.get("weight_tier") or "500g").strip()
        frequency = (post.get("frequency") or "monthly").strip()
        grind_size = (post.get("grind_size") or "whole_bean").strip()
        notes = (post.get("notes") or "").strip()
        payment_method = (post.get("payment_method") or "cod").strip()

        # Generate unique Membership ID conforming to INNO-CLUB-2026-XXXXX
        sub_id = f"INNO-CLUB-2026-{int(time.time() * 1000) % 100000:05d}"

        # Standard human-readable labels
        taste_labels = {
            "dam_ban_sac": "Gu Đậm Bản Sắc (Fine Robusta Natural & Honey)",
            "thanh_tuoi_moi": "Gu Thanh Tươi Mới (Specialty Arabica Bourbon Washed)",
            "mix_kham_pha": "Mix Khám Phá Hàng Tháng (Discovery Flight Rotation)",
        }
        freq_labels = {
            "biweekly": "Mỗi 2 tuần (Bi-weekly)",
            "monthly": "Mỗi tháng (Monthly)",
        }
        grind_labels = {
            "whole_bean": "Nguyên hạt mộc (Whole Bean)",
            "phin": "Xay Phin truyền thống (650 μm)",
            "espresso": "Xay Máy Espresso (250 μm)",
            "v60": "Xay Pour-over V60 (800 μm)",
            "coldbrew": "Xay Ủ lạnh Cold Brew (1000 μm)",
        }

        taste_title = taste_labels.get(taste_preference, taste_preference)
        freq_title = freq_labels.get(frequency, frequency)
        grind_title = grind_labels.get(grind_size, grind_size)
        price_per_cycle = "390.000 đ" if weight_tier == "500g" else "690.000 đ"

        lead_id = None
        try:
            CRMLead = request.env["crm.lead"].sudo()
            CRMTag = request.env["crm.tag"].sudo()

            tag = CRMTag.search([("name", "=", "Innokafe Club Subscription")], limit=1)
            if not tag:
                try:
                    tag = CRMTag.create({"name": "Innokafe Club Subscription", "color": 4})
                except Exception:
                    tag = False

            desc_lines = [
                "=== ĐĂNG KÝ HỘI VIÊN INNOKAFE ARTISAN COFFEE CLUB ===",
                f"Mã hội viên: {sub_id}",
                f"Họ tên thành viên: {member_name}",
                f"Số điện thoại: {phone}",
                f"Email: {email}",
                f"Địa chỉ nhận cà phê: {shipping_address}",
                "--- CẤU HÌNH GÓI ĐỊNH KỲ ---",
                f"Hồ sơ khẩu vị: {taste_title}",
                f"Khối lượng gói: {weight_tier}",
                f"Chu kỳ nhận hàng: {freq_title}",
                f"Cỡ xay yêu cầu: {grind_title}",
                f"Định phí ước tính: {price_per_cycle} / chu kỳ",
                f"Hình thức thanh toán kỳ đầu: {payment_method.upper()}",
                "--- QUÀ TẶNG KÈM CHÀO MỪNG (WELCOME GIFTS) ---",
                "✓ Tặng 01 Phin nhôm nghệ nhân InnoKafe anodized 1.2mm dập logo",
                "✓ Tặng 01 Voucher nếm thử Flagship Tasting Bar (150.000đ)",
                "✓ Tặng Cẩm nang pha chế Specialty Coffee song ngữ",
                f"Ghi chú giao hàng: {notes}",
                "Nguồn đăng ký: https://innokafe.com/ (InnoKafe Club Wizard)",
            ]

            lead_vals = {
                "name": f"InnoKafe Club: {member_name} - {weight_tier} ({freq_title}) [#{sub_id}]",
                "contact_name": member_name,
                "email_from": email,
                "phone": phone,
                "street": shipping_address,
                "description": "<br/>".join(desc_lines),
                "type": "opportunity",
            }
            if hasattr(request, "website") and request.website and request.website.company_id:
                lead_vals["company_id"] = request.website.company_id.id
            elif request.env.company:
                lead_vals["company_id"] = request.env.company.id

            if tag:
                lead_vals["tag_ids"] = [(4, tag.id)]

            lead = CRMLead.create(lead_vals)
            lead_id = lead.id
            _logger.info("Successfully created InnoKafe Club Opportunity #%s for %s", lead_id, member_name)

            # Automated Confirmation Email Dispatch via mail.mail
            if email:
                try:
                    mail_vals = {
                        "subject": f"[InnoKafe Club] Chào mừng Hội viên Artisan Coffee Club - Xác nhận gói #{sub_id}",
                        "email_from": request.env.company.email or "club@innokafe.com",
                        "email_to": email,
                        "body_html": f"""
                            <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #1E120B; color: #F7F2EA; border: 1px solid rgba(212,136,66,0.3); border-radius: 12px; overflow: hidden;">
                                <div style="background: linear-gradient(135deg, #2C1810 0%, #1E120B 100%); padding: 32px 24px; text-align: center; border-bottom: 2px solid #D48842;">
                                    <h1 style="color: #D48842; margin: 0 0 8px 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px;">InnoKafe Artisan Club</h1>
                                    <p style="color: #F7F2EA; margin: 0; font-size: 14px;">Xác Nhận Đăng Ký Hội Viên &amp; Giao Cà Phê Mộc Định Kỳ</p>
                                </div>
                                <div style="padding: 28px 24px;">
                                    <p style="font-size: 15px; line-height: 1.6;">Xin chào <strong>{member_name}</strong>,</p>
                                    <p style="font-size: 14px; line-height: 1.6; color: #aaa;">Chào mừng bạn gia nhập cộng đồng những người sành cà phê đặc sản tại <strong>InnoKafe Club</strong>. Gói cà phê mộc định kỳ của bạn đã được kích hoạt thành công với thông số như sau:</p>
                                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 13px;">
                                        <tr style="border-bottom: 1px solid rgba(247,242,234,0.1);"><td style="padding: 8px 0; color: #888;">Mã hội viên:</td><td style="padding: 8px 0; font-weight: bold; color: #D48842;">{sub_id}</td></tr>
                                        <tr style="border-bottom: 1px solid rgba(247,242,234,0.1);"><td style="padding: 8px 0; color: #888;">Gu thưởng thức:</td><td style="padding: 8px 0; color: #fff;">{taste_title}</td></tr>
                                        <tr style="border-bottom: 1px solid rgba(247,242,234,0.1);"><td style="padding: 8px 0; color: #888;">Quy cách đóng gói:</td><td style="padding: 8px 0; color: #fff;">{weight_tier} / {freq_title}</td></tr>
                                        <tr style="border-bottom: 1px solid rgba(247,242,234,0.1);"><td style="padding: 8px 0; color: #888;">Cỡ xay:</td><td style="padding: 8px 0; color: #fff;">{grind_title}</td></tr>
                                        <tr style="border-bottom: 1px solid rgba(247,242,234,0.1);"><td style="padding: 8px 0; color: #888;">Định phí mỗi kỳ:</td><td style="padding: 8px 0; font-weight: bold; color: #D48842;">{price_per_cycle}</td></tr>
                                        <tr style="border-bottom: 1px solid rgba(247,242,234,0.1);"><td style="padding: 8px 0; color: #888;">Địa chỉ giao hàng:</td><td style="padding: 8px 0; color: #fff;">{shipping_address}</td></tr>
                                    </table>
                                    <div style="background: rgba(212,136,66,0.1); border-left: 4px solid #D48842; padding: 14px; border-radius: 4px; margin: 20px 0;">
                                        <strong style="color: #D48842; display: block; margin-bottom: 6px;">🎁 Quà Tặng Kèm Đơn Đầu Tiên:</strong>
                                        <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #ddd;">
                                            <li>01 Phin nhôm nghệ nhân InnoKafe anodized 1.2mm dập logo (Trị giá 120.000đ)</li>
                                            <li>01 Voucher nếm thử Flagship Tasting Bar (150.000đ)</li>
                                            <li>01 Cẩm nang pha chế Specialty Coffee song ngữ</li>
                                        </ul>
                                    </div>
                                    <p style="font-size: 13px; color: #aaa; line-height: 1.5;">Mẻ rang đầu tiên của bạn sẽ được đóng gói giao tươi trong vòng <strong>48 giờ</strong>. Mọi thắc mắc vui lòng liên hệ hotline: <strong>+84 28 7300 6688</strong>.</p>
                                </div>
                            </div>
                        """,
                    }
                    mail = request.env["mail.mail"].sudo().create(mail_vals)
                    try:
                        mail.send()
                    except Exception as mail_send_err:
                        _logger.info("Mail queued (direct send deferred): %s", mail_send_err)
                    _logger.info("Dispatched InnoKafe Club Welcome Email to %s", email)
                except Exception as mail_err:
                    _logger.error("Failed to compose or queue welcome email: %s", mail_err)

        except Exception as e:
            _logger.error("Failed to process InnoKafe Club subscription: %s", e)

        # Handle AJAX JSON response or standard redirect
        is_ajax = post.get("is_ajax") in ("1", "true", True) or request.httprequest.headers.get("X-Requested-With") == "XMLHttpRequest"
        if is_ajax:
            return request.make_response(
                json.dumps({
                    "status": "success",
                    "sub_id": sub_id,
                    "lead_id": lead_id,
                    "member_name": member_name,
                    "price": price_per_cycle,
                    "taste_preference": taste_title,
                    "weight_tier": weight_tier,
                    "frequency": freq_title,
                    "grind_size": grind_title,
                }),
                headers=[("Content-Type", "application/json")]
            )

        return request.redirect(f"/?club_submitted=1&sub_id={sub_id}#inno_subscription_wizard")

    # --------------------------------------------------------------------------
    # TASTE PROFILER JSON API (7D EUCLIDEAN MATCHMAKING)
    # --------------------------------------------------------------------------

    @http.route("/taste-profiler/match", type="jsonrpc", auth="public", methods=["POST"], website=True)
    def taste_profiler_match(self, **payload):
        """
        Receives quiz selections, executes 7D Euclidean vector matchmaking,
        and returns Top 1, Top 2, all rankings, and computed radar points.
        """
        habit = payload.get("habit", "phin_dam")
        gear = payload.get("gear", "phin")
        flavor = payload.get("flavor", "nutty_choco")
        caffeine = payload.get("caffeine", "high")

        ranked_skus, user_vector = calculate_match_scores(habit, gear, flavor, caffeine)

        db_map = self._lookup_db_products()
        for item in ranked_skus:
            db_prod = db_map.get(item["sku_code"])
            if db_prod:
                item["product_id"] = db_prod.product_variant_id.id if db_prod.product_variant_id else db_prod.id
                item["product_tmpl_id"] = db_prod.id
            else:
                item["product_id"] = 1
                item["product_tmpl_id"] = 1

        top1 = ranked_skus[0] if ranked_skus else None
        top2 = ranked_skus[1] if len(ranked_skus) > 1 else None

        return {
            "status": "success",
            "top1": top1,
            "top2": top2,
            "all_ranked": ranked_skus,
            "user_vector": user_vector,
        }
