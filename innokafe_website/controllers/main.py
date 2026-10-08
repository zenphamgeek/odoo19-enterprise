# -*- coding: utf-8 -*-
import json
import logging
import math
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

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
        "tagline": "Bản sắc đại ngàn — Vị đậm đà ngút ngàn, ngọt sâu hậu vị",
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
        "tagline": "Tinh hoa sương mù — Chua thanh hoa nhài, trong trẻo tao nhã",
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
        "tagline": "Khúc giao hòa đỉnh cao — Ngọt ngào mật ong rừng, kem bơ sánh quyện",
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
        "tagline": "Tiện lợi mọi lúc mọi nơi — Đẳng cấp cà phê phin giấy lọc Nhật Bản",
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
        "tagline": "Sảng khoái mùa hè — Chua ngọt bùng nổ, ủ lạnh 24h ngọt ngào",
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
        "tagline": "Chuẩn mực quầy bar chuyên nghiệp — Crema dày mịn, ổn định chiết xuất",
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

class InnokafeMainController(http.Controller):

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
    # PUBLIC ROUTES
    # --------------------------------------------------------------------------

    @http.route(["/"], type="http", auth="public", website=True, sitemap=True)
    def index(self, **kwargs):
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

    @http.route(["/taste-profiler"], type="http", auth="public", website=True, sitemap=True)
    def taste_profiler(self, **kwargs):
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
        values["skus_json"] = json.dumps(hydrated_skus)
        return request.render("innokafe_website.taste_profiler_page", values)

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
                "Nguồn: https://innokafe.insilos.com/solutions-b2b",
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
                "Nguồn: https://innokafe.insilos.com/contactus",
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
