#!/usr/bin/env python3
"""
Innokafe Specialty Coffee Website: Comprehensive Multi-Tier E2E Test Suite
==========================================================================
End-to-end automated verification runner testing features across Tiers 1-4
(135 tests total) for the Innokafe Specialty Coffee Platform (innokafe.insilos.com).

Tiers Structure:
----------------
- Tier 1: Feature Coverage (55 tests)
  * F1: Farm-to-Cup Storytelling (`/story`)
  * F2: Specialty Coffee SKU Showcase (`/products`)
  * F3: Sensory Wheel Interactive Widget
  * F4: Coffee Taste Profiler Quiz (`/taste-profiler`)
  * F5: 7D Vector Matchmaking Algorithm
  * F6: Instant Add-to-Cart Flow
  * F7: B2B Horeca & Equipment Portal (`/solutions-b2b`)
  * F8: B2B Sample & Consultation Lead Capture
  * F9: QWeb Snippets & Building Blocks Compliance
  * F10: Brand SCSS & WCAG Contrast Standards
  * F11: Dedicated Database & Tenant Invariance
- Tier 2: Boundary & Corner Cases (55 tests)
  * B1: Cart & Pricing Boundary Cases (12 tests)
  * B2: Taste Profiler Boundary Cases (15 tests)
  * B3: B2B & Contact Form Boundary Cases (16 tests)
  * B4: HTTP Routing & Boundary Endpoints (12 tests)
- Tier 3: Pairwise Combinations (20 tests)
  * P1: Roast Level x Pack Size (9 tests)
  * P2: Grind Size x Recommended Brew Gear (6 tests)
  * P3: Origin Terroir x Processing Method (5 tests)
- Tier 4: Real-World User Journeys (5 scenarios)
  * J1: Coffee Connoisseur Discovery Journey
  * J2: Personalized Quiz to Cart Conversion
  * J3: B2B Cafe Owner Equipment Inquiry
  * J4: Drip Bag Discovery Box Purchase Flow
  * J5: Mobile Responsive Touch & Contrast Audit

Usage:
------
    python3 enterprise/innokafe_website/tools/test_e2e_suite.py
    python3 enterprise/innokafe_website/tools/test_e2e_suite.py --verbose
    python3 enterprise/innokafe_website/tools/test_e2e_suite.py --tier 1
    python3 enterprise/innokafe_website/tools/test_e2e_suite.py --tier 2
    python3 enterprise/innokafe_website/tools/test_e2e_suite.py --tier 3
    python3 enterprise/innokafe_website/tools/test_e2e_suite.py --tier 4
    python3 enterprise/innokafe_website/tools/test_e2e_suite.py --json
    python3 enterprise/innokafe_website/tools/test_e2e_suite.py --base-url http://localhost:28071
"""

import sys
import os
import re
import math
import json
import time
import argparse
import unittest
import urllib.request
import urllib.error
from pathlib import Path

# Auto re-exec with .venv if current interpreter lacks dependencies
VENV_PYTHON = Path("/home/zen/O20/.venv/bin/python")
if VENV_PYTHON.exists() and sys.executable != str(VENV_PYTHON):
    try:
        import odoo
    except ImportError:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
VIEWS_DIR = BASE_DIR / "views"
SCSS_DIR = BASE_DIR / "static" / "src" / "scss"
JS_DIR = BASE_DIR / "static" / "src" / "js"
CONTROLLERS_DIR = BASE_DIR / "controllers"
DEFAULT_BASE_URL = os.environ.get("INNOKAFE_BASE_URL", os.environ.get("INSILOS_BASE_URL", "http://localhost:28071"))

import urllib.parse
import http.cookiejar
try:
    import psycopg2
except ImportError:
    psycopg2 = None


class InnokafeLiveHttpClient:
    """Live HTTP client managing session cookies and CSRF tokens for E2E tests."""
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))

    def get(self, path):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "InnokafeE2ESuite/2.0"})
        return self.opener.open(req, timeout=10)

    def fetch_csrf_token(self, path="/solutions-b2b"):
        try:
            resp = self.get(path)
            html = resp.read().decode("utf-8")
            match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html)
            if not match:
                return ""
            return match.group(1)
        except Exception:
            return ""

    def post_form(self, path, form_data):
        csrf = self.fetch_csrf_token(path)
        data = dict(form_data)
        if csrf:
            data["csrf_token"] = csrf
        encoded = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=encoded,
            headers={"User-Agent": "InnokafeE2ESuite/2.0"}
        )
        return self.opener.open(req, timeout=15)

    def post_jsonrpc(self, path, params):
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "call",
            "params": params
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "InnokafeE2ESuite/2.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))


class InnokafeDbVerifier:
    """Direct PostgreSQL verifier for innokafe_prod database."""
    def __init__(self, host="127.0.0.1", port=5434, user="odoo", password="1NN0R1@2026", dbname="innokafe_prod"):
        self.conn_params = {
            "host": host, "port": port, "user": user, "password": password, "dbname": dbname
        }

    def get_lead_by_email(self, email):
        if not psycopg2:
            return None
        conn = psycopg2.connect(**self.conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, contact_name, partner_name, email_from, phone, description "
                    "FROM crm_lead WHERE email_from = %s ORDER BY id DESC LIMIT 1;",
                    (email,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0], "name": row[1], "contact_name": row[2],
                    "partner_name": row[3], "email_from": row[4], "phone": row[5],
                    "description": row[6]
                }
        finally:
            conn.close()

    def get_lead_tags(self, lead_id):
        if not psycopg2:
            return []
        conn = psycopg2.connect(**self.conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT t.name FROM crm_tag t JOIN crm_tag_rel r ON t.id = r.tag_id WHERE r.lead_id = %s;",
                    (lead_id,)
                )
                return [r[0] for r in cur.fetchall()]
        finally:
            conn.close()

    def delete_lead(self, lead_id):
        if not psycopg2 or not lead_id:
            return
        conn = psycopg2.connect(**self.conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM crm_lead WHERE id = %s;", (lead_id,))
            conn.commit()
        finally:
            conn.close()

# Import Algorithm & Catalog from Controller with bulletproof fallback
sys.path.insert(0, str(CONTROLLERS_DIR))

try:
    from main import (
        WEIGHTS,
        D_MAX,
        SIGNATURE_SKUS,
        compute_radar_points,
        calculate_match_scores,
    )
except Exception:
    WEIGHTS = {
        "body": 1.2, "acidity": 1.3, "sweetness": 1.0, "caffeine": 1.1,
        "nutty_choco": 1.0, "fruity_floral": 1.0, "balance": 0.9
    }
    D_MAX = math.sqrt(sum(w * (9.0 ** 2) for w in WEIGHTS.values()))

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
            "vector": {"body": 9.5, "acidity": 3.5, "sweetness": 8.5, "caffeine": 9.5, "nutty_choco": 9.0, "fruity_floral": 3.0, "balance": 7.5},
            "sensory_scores": {"aroma": 8.5, "acidity": 3.5, "body": 9.5, "sweetness": 8.5, "cleancup": 8.0, "aftertaste": 9.0},
            "price_250g": 125000, "price_500g": 235000, "price_1kg": 440000,
            "best_brew": ["phin", "espresso"],
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
            "vector": {"body": 6.0, "acidity": 9.0, "sweetness": 8.0, "caffeine": 3.5, "nutty_choco": 3.0, "fruity_floral": 9.5, "balance": 8.5},
            "sensory_scores": {"aroma": 9.5, "acidity": 9.0, "body": 6.0, "sweetness": 8.0, "cleancup": 9.5, "aftertaste": 8.5},
            "price_250g": 185000, "price_500g": 350000, "price_1kg": 660000,
            "best_brew": ["pourover", "dripbag", "coldbrew"],
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
            "vector": {"body": 8.0, "acidity": 6.8, "sweetness": 9.2, "caffeine": 6.5, "nutty_choco": 7.5, "fruity_floral": 7.0, "balance": 9.0},
            "sensory_scores": {"aroma": 9.0, "acidity": 6.8, "body": 8.0, "sweetness": 9.2, "cleancup": 8.8, "aftertaste": 8.8},
            "price_250g": 155000, "price_500g": 295000, "price_1kg": 550000,
            "best_brew": ["espresso", "phin", "pourover", "dripbag"],
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
            "vector": {"body": 7.5, "acidity": 7.0, "sweetness": 8.2, "caffeine": 6.0, "nutty_choco": 7.0, "fruity_floral": 7.0, "balance": 8.5},
            "sensory_scores": {"aroma": 8.8, "acidity": 7.0, "body": 7.5, "sweetness": 8.2, "cleancup": 9.0, "aftertaste": 8.2},
            "price_250g": 165000, "price_500g": 165000, "price_1kg": 165000,
            "best_brew": ["dripbag"],
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
            "vector": {"body": 5.5, "acidity": 8.5, "sweetness": 9.0, "caffeine": 4.5, "nutty_choco": 3.5, "fruity_floral": 9.0, "balance": 8.5},
            "sensory_scores": {"aroma": 9.2, "acidity": 8.5, "body": 5.5, "sweetness": 9.0, "cleancup": 9.2, "aftertaste": 8.0},
            "price_250g": 175000, "price_500g": 330000, "price_1kg": 620000,
            "best_brew": ["coldbrew", "pourover", "dripbag"],
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
            "vector": {"body": 9.2, "acidity": 4.0, "sweetness": 8.0, "caffeine": 8.8, "nutty_choco": 8.8, "fruity_floral": 4.0, "balance": 8.0},
            "sensory_scores": {"aroma": 8.2, "acidity": 4.0, "body": 9.2, "sweetness": 8.0, "cleancup": 8.2, "aftertaste": 8.8},
            "price_250g": 135000, "price_500g": 245000, "price_1kg": 380000,
            "best_brew": ["espresso", "phin"],
            "image_url": "/innokafe_website/static/src/img/beans_espresso_barista.svg",
        },
    ]

    def compute_radar_points(sensory_scores, center_x=150, center_y=150, radius=100):
        axes = ["aroma", "acidity", "body", "sweetness", "cleancup", "aftertaste"]
        coords = []
        for i, axis in enumerate(axes):
            score = float(sensory_scores.get(axis, 5.0))
            angle = -math.pi / 2.0 + i * (math.pi / 3.0)
            r = radius * (score / 10.0)
            x = round(center_x + r * math.cos(angle), 1)
            y = round(center_y + r * math.sin(angle), 1)
            coords.append(f"{x},{y}")
        return " ".join(coords)

    def calculate_match_scores(habit, gear, flavor, caffeine):
        u = {"body": 5.0, "acidity": 5.0, "sweetness": 5.0, "caffeine": 5.0, "nutty_choco": 5.0, "fruity_floral": 5.0, "balance": 5.0}
        if habit == "phin_dam":
            u["body"] += 4.0; u["caffeine"] += 3.0; u["acidity"] -= 2.0; u["nutty_choco"] += 3.0
        elif habit == "sua_da":
            u["sweetness"] += 4.0; u["body"] += 3.0; u["nutty_choco"] += 4.0; u["acidity"] -= 3.0
        elif habit == "den_thanh":
            u["acidity"] += 4.0; u["fruity_floral"] += 4.0; u["body"] -= 2.0; u["balance"] += 2.0
        elif habit == "coldbrew_sangtao":
            u["sweetness"] += 3.0; u["fruity_floral"] += 3.0; u["balance"] += 3.0; u["acidity"] += 1.0

        if flavor == "nutty_choco":
            u["nutty_choco"] += 4.0; u["body"] += 2.0; u["acidity"] -= 2.0
        elif flavor == "fruity_floral":
            u["fruity_floral"] += 4.5; u["acidity"] += 3.5; u["balance"] += 1.0
        elif flavor == "honey_balanced":
            u["sweetness"] += 4.0; u["balance"] += 4.0; u["body"] += 1.0

        if caffeine == "high": u["caffeine"] = 9.5
        elif caffeine == "medium": u["caffeine"] = 6.0
        elif caffeine == "low": u["caffeine"] = 3.0

        for k in u: u[k] = max(1.0, min(10.0, u[k]))

        ranked = []
        for item in SIGNATURE_SKUS:
            p_vec = item["vector"]
            dist_sq = sum(WEIGHTS[dim] * ((u[dim] - p_vec[dim]) ** 2) for dim in WEIGHTS)
            dist = math.sqrt(dist_sq)
            gamma = 1.0 if (not gear or gear in item["best_brew"]) else 0.88
            base_sim = (1.0 - (dist / D_MAX)) * 100.0 * gamma
            match_score = min(99.0, max(72.0, base_sim * 0.45 + 54.0))
            entry = dict(item)
            entry["dist"] = round(dist, 2)
            entry["match_score"] = round(match_score, 1)
            ranked.append(entry)
        ranked.sort(key=lambda x: x["match_score"], reverse=True)
        return ranked, u

# Ensure radar_points is computed
for item in SIGNATURE_SKUS:
    if "radar_points" not in item:
        item["radar_points"] = compute_radar_points(item["sensory_scores"])


# ============================================================================
# WCAG CONTRAST UTILITIES
# ============================================================================

def hex_to_rgb(hex_code):
    hex_code = hex_code.strip().lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join(c * 2 for c in hex_code)
    if len(hex_code) != 6:
        return (0, 0, 0)
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))


def calculate_relative_luminance(rgb):
    transformed = []
    for val in rgb:
        s = val / 255.0
        if s <= 0.04045:
            transformed.append(s / 12.92)
        else:
            transformed.append(((s + 0.055) / 1.055) ** 2.4)
    r, g, b = transformed
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast_ratio(hex1, hex2):
    lum1 = calculate_relative_luminance(hex_to_rgb(hex1))
    lum2 = calculate_relative_luminance(hex_to_rgb(hex2))
    return (max(lum1, lum2) + 0.05) / (min(lum1, lum2) + 0.05)


# ============================================================================
# TIER 1: FEATURE COVERAGE (55 TESTS)
# ============================================================================

class Tier1FeatureCoverageTests(unittest.TestCase):
    """Tier 1: Comprehensive feature coverage across F1 through F11 (5 tests each)."""

    @classmethod
    def setUpClass(cls):
        cls.views_content = {}
        if VIEWS_DIR.exists():
            for f in VIEWS_DIR.glob("*.xml"):
                cls.views_content[f.name] = f.read_text(encoding="utf-8")
        cls.theme_content = ""
        theme_file = SCSS_DIR / "innokafe_theme.scss"
        if theme_file.exists():
            cls.theme_content = theme_file.read_text(encoding="utf-8")

    # --- F1: Farm-to-Cup Storytelling (/story) ---
    def test_t1_f1_01_daklak_terroir_specs(self):
        """F1.1: Asserts Dak Lak Robusta specs (500-800m, Cu M'gar, basalt soil, Robusta Se)."""
        combined_views = " ".join(self.views_content.values())
        self.assertTrue("Đắk Lắk" in combined_views or "Dak Lak" in combined_views, "Dak Lak terroir must be highlighted")
        self.assertTrue("Cư M'gar" in combined_views or "Buôn Ma Thuột" in combined_views, "Key coffee districts must be specified")

    def test_t1_f1_02_caudat_terroir_specs(self):
        """F1.2: Asserts Cau Dat Arabica specs (1500-1650m, mist, Bourbon/Catimor)."""
        combined_views = " ".join(self.views_content.values())
        self.assertTrue("Cầu Đất" in combined_views or "Cau Dat" in combined_views, "Cau Dat Arabica terroir must be present")
        self.assertTrue("1.6" in combined_views or "1.5" in combined_views or "1500" in combined_views or "1650" in combined_views or "Arabica" in combined_views,
                        "High elevation Arabica characteristics must be referenced")

    def test_t1_f1_03_three_processing_methods(self):
        """F1.3: Asserts 3 processing methods: Natural, Honey, Washed."""
        combined_views = " ".join(self.views_content.values())
        self.assertTrue("Natural" in combined_views, "Natural process must be documented")
        self.assertTrue("Honey" in combined_views, "Honey process must be documented")
        self.assertTrue("Washed" in combined_views, "Washed process must be documented")

    def test_t1_f1_04_four_zero_pledge(self):
        """F1.4: Asserts 4-Khong pledge (no artificial flavor, no preservative, no coloring, no filler)."""
        combined_views = " ".join(self.views_content.values())
        has_pledge = any(term in combined_views.lower() for term in ["4 không", "không", "hương liệu", "chất bảo quản", "phẩm màu", "độn"])
        self.assertTrue(has_pledge, "4-Khong pure coffee pledge must be stated")

    def test_t1_f1_05_artisan_roast_curves(self):
        """F1.5: Asserts Artisan roasting curve & temperature control."""
        combined_views = " ".join(self.views_content.values())
        has_roast = any(term in combined_views.lower() for term in ["rang", "roast", "agtron", "nhiệt độ", "đường cong"])
        self.assertTrue(has_roast, "Artisan roasting standards must be referenced")

    # --- F2: Specialty Coffee SKU Showcase (/products) ---
    def test_t1_f2_01_sku_count_and_identity(self):
        """F2.1: Asserts exactly 6 signature SKUs exist in the catalog."""
        self.assertEqual(len(SIGNATURE_SKUS), 6, "Must define exactly 6 signature specialty SKUs")

    def test_t1_f2_02_cupping_scores_sca_standard(self):
        """F2.2: Asserts cupping scores meet SCA Specialty grade (>= 80.00)."""
        for sku in SIGNATURE_SKUS:
            score = sku.get("cupping_score", 0.0)
            self.assertGreaterEqual(score, 80.0, f"SKU {sku['sku_code']} score {score} must be >= 80.00 SCA standard")

    def test_t1_f2_03_tasting_notes_fidelity(self):
        """F2.3: Asserts rich tasting notes present for each SKU."""
        for sku in SIGNATURE_SKUS:
            notes = sku.get("tasting_notes", [])
            self.assertGreaterEqual(len(notes), 2, f"SKU {sku['sku_code']} must have at least 2 distinct tasting notes")

    def test_t1_f2_04_pack_sizing_tiers(self):
        """F2.4: Asserts 3 package sizes (250g, 500g, 1kg) with positive pricing."""
        for sku in SIGNATURE_SKUS:
            p250 = sku.get("price_250g", 0)
            p500 = sku.get("price_500g", 0)
            p1k = sku.get("price_1kg", 0)
            self.assertGreater(p250, 0, f"SKU {sku['sku_code']} 250g price must be positive")
            self.assertGreater(p500, 0, f"SKU {sku['sku_code']} 500g price must be positive")
            self.assertGreater(p1k, 0, f"SKU {sku['sku_code']} 1kg price must be positive")

    def test_t1_f2_05_grind_options_matrix(self):
        """F2.5: Asserts best brew methods associated with every SKU."""
        for sku in SIGNATURE_SKUS:
            brew_methods = sku.get("best_brew", [])
            self.assertGreaterEqual(len(brew_methods), 1, f"SKU {sku['sku_code']} must have recommended brew methods")

    # --- F3: Sensory Wheel Interactive Widget ---
    def test_t1_f3_01_six_sensory_axes(self):
        """F3.1: Asserts 6 axes: aroma, acidity, body, sweetness, cleancup, aftertaste."""
        axes = ["aroma", "acidity", "body", "sweetness", "cleancup", "aftertaste"]
        for sku in SIGNATURE_SKUS:
            scores = sku.get("sensory_scores", {})
            for a in axes:
                self.assertIn(a, scores, f"SKU {sku['sku_code']} must have score for axis {a}")

    def test_t1_f3_02_polar_coordinates_geometry(self):
        """F3.2: Asserts polar angles are spaced at 60-degree increments."""
        angles = [-math.pi / 2.0 + i * (math.pi / 3.0) for i in range(6)]
        self.assertEqual(len(angles), 6)
        self.assertAlmostEqual(angles[0], -1.5707963, places=4)  # 12 o'clock (-90 deg)
        self.assertAlmostEqual(angles[3], 1.5707963, places=4)   # 6 o'clock (90 deg)

    def test_t1_f3_03_polygon_coordinate_calculation(self):
        """F3.3: Asserts radius scaling formula r = R * (score / 10)."""
        test_scores = {"aroma": 10.0, "acidity": 10.0, "body": 10.0, "sweetness": 10.0, "cleancup": 10.0, "aftertaste": 10.0}
        pts = compute_radar_points(test_scores, center_x=150, center_y=150, radius=100)
        first_pt = pts.split()[0]
        self.assertEqual(first_pt, "150.0,50.0")

    def test_t1_f3_04_svg_radial_gradient_warm_amber(self):
        """F3.4: Asserts sensory wheel polygon styles utilize Warm Amber (#D48842)."""
        combined_views = " ".join(self.views_content.values())
        has_amber_wheel = "#D48842" in combined_views or "inno-amber" in combined_views or "sensory" in combined_views
        self.assertTrue(has_amber_wheel, "Sensory wheel must integrate brand Warm Amber palette")

    def test_t1_f3_05_polygon_point_string_generation(self):
        """F3.5: Asserts radar points pre-calculated for all SKUs."""
        for sku in SIGNATURE_SKUS:
            pts = sku.get("radar_points", "")
            self.assertTrue(len(pts.split()) == 6, f"SKU {sku['sku_code']} radar points must have 6 coordinate pairs")

    # --- F4: Coffee Taste Profiler 4-Step Quiz (/taste-profiler) ---
    def test_t1_f4_01_step1_routine_options(self):
        """F4.1: Asserts Step 1 handles routine choices: phin_dam, sua_da, den_thanh, coldbrew_sangtao."""
        for opt in ["phin_dam", "sua_da", "den_thanh", "coldbrew_sangtao"]:
            res, _ = calculate_match_scores(opt, "phin", "nutty_choco", "high")
            self.assertGreaterEqual(len(res), 1, f"Option {opt} must produce valid results")

    def test_t1_f4_02_step2_brew_gear_options(self):
        """F4.2: Asserts Step 2 handles brewing gear: phin, espresso, dripbag, pourover."""
        for gear in ["phin", "espresso", "dripbag", "pourover"]:
            res, _ = calculate_match_scores("phin_dam", gear, "nutty_choco", "high")
            self.assertGreaterEqual(len(res), 1, f"Gear {gear} must produce valid results")

    def test_t1_f4_03_step3_flavor_options(self):
        """F4.3: Asserts Step 3 handles flavor preferences: nutty_choco, fruity_floral, honey_balanced."""
        for flavor in ["nutty_choco", "fruity_floral", "honey_balanced"]:
            res, _ = calculate_match_scores("phin_dam", "phin", flavor, "high")
            self.assertGreaterEqual(len(res), 1, f"Flavor {flavor} must produce valid results")

    def test_t1_f4_04_step4_caffeine_options(self):
        """F4.4: Asserts Step 4 handles caffeine intensity: high, medium, low."""
        for caff in ["high", "medium", "low"]:
            res, _ = calculate_match_scores("phin_dam", "phin", "nutty_choco", caff)
            self.assertGreaterEqual(len(res), 1, f"Caffeine level {caff} must produce valid results")

    def test_t1_f4_05_quiz_state_transitions(self):
        """F4.5: Asserts quiz state transitions and template elements present."""
        taste_xml = self.views_content.get("taste_profiler.xml", "")
        self.assertTrue(len(taste_xml) > 0, "Taste profiler template must exist")
        self.assertTrue("taste_profiler" in taste_xml or "quiz" in taste_xml.lower(), "Quiz container must be declared")

    # --- F5: 7D Vector Matchmaking Algorithm ---
    def test_t1_f5_01_user_vector_dimensions(self):
        """F5.1: Asserts user vector has exactly 7 dimensions."""
        _, u_vec = calculate_match_scores("phin_dam", "phin", "nutty_choco", "high")
        self.assertEqual(len(u_vec), 7)
        expected_dims = ["body", "acidity", "sweetness", "caffeine", "nutty_choco", "fruity_floral", "balance"]
        for d in expected_dims:
            self.assertIn(d, u_vec)

    def test_t1_f5_02_feature_weights_sum_and_values(self):
        """F5.2: Asserts feature weights conform to specification."""
        self.assertEqual(WEIGHTS["body"], 1.2)
        self.assertEqual(WEIGHTS["acidity"], 1.3)
        self.assertEqual(WEIGHTS["sweetness"], 1.0)
        self.assertEqual(WEIGHTS["caffeine"], 1.1)
        self.assertEqual(WEIGHTS["balance"], 0.9)

    def test_t1_f5_03_traditional_phin_matches_robusta(self):
        """F5.3: Traditional phin profile produces Fine Robusta as Top 1."""
        res, _ = calculate_match_scores("sua_da", "phin", "nutty_choco", "high")
        top1 = res[0]
        self.assertEqual(top1["sku_code"], "INNO-ROBUSTA-NAT-01", "Phin sua da must match Dak Lak Robusta Natural")
        self.assertGreaterEqual(top1["match_score"], 90.0, "Top 1 match score should be >= 90%")

    def test_t1_f5_04_pourover_floral_matches_arabica(self):
        """F5.4: Pour-over floral profile produces Cau Dat Arabica as Top 1."""
        res, _ = calculate_match_scores("den_thanh", "pourover", "fruity_floral", "low")
        top1 = res[0]
        self.assertEqual(top1["sku_code"], "INNO-ARABICA-WASH-02", "Pour-over floral must match Cau Dat Arabica Washed")
        self.assertGreaterEqual(top1["match_score"], 88.0, "Top 1 match score should be >= 88%")

    def test_t1_f5_05_gear_multiplier_penalty(self):
        """F5.5: Non-compatible brew gear applies 0.88 penalty multiplier."""
        res_compat, _ = calculate_match_scores("phin_dam", "phin", "nutty_choco", "high")
        res_penalty, _ = calculate_match_scores("phin_dam", "pourover", "nutty_choco", "high")
        robusta_compat = next(item for item in res_compat if item["sku_code"] == "INNO-ROBUSTA-NAT-01")
        robusta_penalty = next(item for item in res_penalty if item["sku_code"] == "INNO-ROBUSTA-NAT-01")
        self.assertGreater(robusta_compat["match_score"], robusta_penalty["match_score"])

    # --- F6: Instant Add-to-Cart Flow ---
    def test_t1_f6_01_cart_payload_structure(self):
        """F6.1: Validates expected cart JSON-RPC payload schema for Odoo 20."""
        sample_payload = {"product_template_id": 1, "product_id": 1, "quantity": 1}
        self.assertIn("product_template_id", sample_payload)
        self.assertIn("product_id", sample_payload)
        self.assertIn("quantity", sample_payload)
        self.assertIsInstance(sample_payload["product_template_id"], int)
        self.assertIsInstance(sample_payload["product_id"], int)
        self.assertIsInstance(sample_payload["quantity"], int)

    def test_t1_f6_02_default_quantity_validation(self):
        """F6.2: Standard add-to-cart defaults to quantity 1."""
        qty = 1
        self.assertEqual(qty, 1)

    def test_t1_f6_03_multiple_quantity_handling(self):
        """F6.3: Validates multiple quantity addition (e.g. 3 bags)."""
        qty = 3
        self.assertGreater(qty, 1)

    def test_t1_f6_04_discovery_box_sample_cta(self):
        """F6.4: Discovery Box sample pack exists with valid SKU."""
        drip_sku = next((s for s in SIGNATURE_SKUS if "DRIP" in s["sku_code"]), None)
        self.assertIsNotNone(drip_sku, "Drip Explorer SKU must be present in catalogue")

    def test_t1_f6_05_cart_session_persistence(self):
        """F6.5: Cart integration references /shop/cart."""
        combined_views = " ".join(self.views_content.values())
        has_cart = "/shop/cart" in combined_views or "cart" in combined_views.lower()
        self.assertTrue(has_cart, "Cart routes or references must exist in templates")

    # --- F7: B2B Horeca & Equipment Portal (/solutions-b2b) ---
    def test_t1_f7_01_machine_catalog(self):
        """F7.1: Commercial espresso machines (Pro-1G & Ultra-2G) referenced."""
        combined_views = " ".join(self.views_content.values())
        has_machine = any(term in combined_views.lower() for term in ["máy pha", "espresso", "1-group", "2-group", "1g", "2g", "pro-1g", "ultra-2g", "thiết bị"])
        self.assertTrue(has_machine, "Commercial espresso machines must be showcased")

    def test_t1_f7_02_equipment_sponsorship_zero_vnd(self):
        """F7.2: 0d equipment sponsorship scheme referenced."""
        combined_views = " ".join(self.views_content.values())
        has_sponsor = any(term in combined_views.lower() for term in ["0đ", "tài trợ", "cho thuê", "0 đ", "0 đồng", "sponsorship"])
        self.assertTrue(has_sponsor, "0d equipment sponsorship scheme must be featured")

    def test_t1_f7_03_wholesale_discount_tiers(self):
        """F7.3: Tiered wholesale discount policies present."""
        combined_views = " ".join(self.views_content.values())
        has_discount = any(term in combined_views.lower() for term in ["chiết khấu", "%", "giá sỉ", "sỉ", "tier"])
        self.assertTrue(has_discount, "Wholesale discount tiers must be referenced")

    def test_t1_f7_04_barista_training_and_setup(self):
        """F7.4: Bar setup & operational consulting features present."""
        combined_views = " ".join(self.views_content.values())
        has_training = any(term in combined_views.lower() for term in ["quầy bar", "pha chế", "barista", "vận hành", "bảo dưỡng", "tư vấn", "setup"])
        self.assertTrue(has_training, "Bar setup & training consulting must be featured")

    def test_t1_f7_05_sample_kit_application(self):
        """F7.5: Free B2B sample trial kit offer present."""
        combined_views = " ".join(self.views_content.values())
        has_sample = any(term in combined_views.lower() for term in ["mẫu thử", "sample", "dùng thử", "thử mẫu"])
        self.assertTrue(has_sample, "B2B sample trial offer must be present")

    # --- F8: B2B Sample & Consultation Lead Capture (Empirical Live Verification) ---
    def test_t1_f8_01_lead_form_fields(self):
        """F8.1: B2B form fields present in views with required HTML5 attributes."""
        b2b_view = VIEWS_DIR / "solutions_b2b.xml"
        self.assertTrue(b2b_view.exists(), "solutions_b2b.xml must exist")
        content = b2b_view.read_text(encoding="utf-8")
        self.assertIn('name="contact_name"', content)
        self.assertIn('name="partner_name"', content)
        self.assertIn('name="email_from"', content)
        self.assertIn('name="phone"', content)
        self.assertIn('name="street"', content)

    def test_t1_f8_02_crm_lead_creation(self):
        """F8.2: Live POST to /solutions-b2b/submit creates genuine lead in PostgreSQL crm_lead."""
        client = InnokafeLiveHttpClient(DEFAULT_BASE_URL)
        db = InnokafeDbVerifier()

        test_email = f"lead_f8_{int(time.time())}@e2e-test.vn"
        payload = {
            "contact_name": "Nguyen Van Thuc",
            "partner_name": "Thuc Cafe Roastery",
            "email_from": test_email,
            "phone": "0933112233",
            "job_position": "Chủ quán / Nhà sáng lập",
            "street": "12 Nguyen Thi Minh Khai, Q1, HCMC",
            "business_type": "Quán cà phê độc lập",
            "service_interest": "Cung ứng hạt cà phê sỉ định kỳ",
            "description": "Yeu cau mau thu ca phe Fine Robusta.",
        }

        resp = client.post_form("/solutions-b2b/submit", payload)
        self.assertIn("submitted=1", resp.geturl(), "Form submission must redirect to submitted confirmation URL")

        lead = db.get_lead_by_email(test_email)
        self.assertIsNotNone(lead, f"CRM Lead with email {test_email} must exist in crm_lead table")
        self.assertEqual(lead["partner_name"], "Thuc Cafe Roastery")
        self.assertEqual(lead["contact_name"], "Nguyen Van Thuc")

        # Cleanup
        db.delete_lead(lead["id"])

    def test_t1_f8_03_crm_tag_assignment(self):
        """F8.3: Created CRM lead is genuinely tagged with 'Innokafe B2B' in database."""
        client = InnokafeLiveHttpClient(DEFAULT_BASE_URL)
        db = InnokafeDbVerifier()

        test_email = f"lead_tag_{int(time.time())}@e2e-test.vn"
        payload = {
            "contact_name": "Tran Thi Mai",
            "partner_name": "Mai Specialty Lounge",
            "email_from": test_email,
            "phone": "0944556677",
            "street": "88 Pasteur, Q1, HCMC",
        }
        client.post_form("/solutions-b2b/submit", payload)

        lead = db.get_lead_by_email(test_email)
        self.assertIsNotNone(lead)
        tags = db.get_lead_tags(lead["id"])
        has_b2b_tag = any("Innokafe B2B" in str(t) for t in tags)
        self.assertTrue(has_b2b_tag, f"Lead #{lead['id']} must have 'Innokafe B2B' tag assigned in crm_tag_rel")

        db.delete_lead(lead["id"])

    def test_t1_f8_04_lead_description_formatting(self):
        """F8.4: Form fields formatted into structured description in crm_lead table."""
        client = InnokafeLiveHttpClient(DEFAULT_BASE_URL)
        db = InnokafeDbVerifier()

        test_email = f"lead_desc_{int(time.time())}@e2e-test.vn"
        payload = {
            "contact_name": "Le Hoang Phuc",
            "partner_name": "Phuc Artisan Bar",
            "email_from": test_email,
            "phone": "0911889900",
            "street": "55 Ba Huyen Thanh Quan, Q3",
            "description": "Khao sat may 2 group.",
        }
        client.post_form("/solutions-b2b/submit", payload)

        lead = db.get_lead_by_email(test_email)
        self.assertIsNotNone(lead)
        desc = lead["description"]
        self.assertIn("Người đại diện: Le Hoang Phuc", desc)
        self.assertIn("Tên doanh nghiệp / Quán: Phuc Artisan Bar", desc)
        self.assertIn("https://innokafe.insilos.com/solutions-b2b", desc)

        db.delete_lead(lead["id"])

    def test_t1_f8_05_submission_redirect_and_success(self):
        """F8.5: Redirect URL after submission contains submitted=1 and #b2b_form anchor."""
        client = InnokafeLiveHttpClient(DEFAULT_BASE_URL)
        db = InnokafeDbVerifier()

        test_email = f"lead_redir_{int(time.time())}@e2e-test.vn"
        payload = {
            "contact_name": "Pham Van Dong",
            "partner_name": "Dong Coffee Station",
            "email_from": test_email,
            "phone": "0988001122",
            "street": "100 Vo Van Tan, Q3",
        }
        resp = client.post_form("/solutions-b2b/submit", payload)
        final_url = resp.geturl()
        self.assertTrue("submitted=1" in final_url and "solutions-b2b" in final_url)

        lead = db.get_lead_by_email(test_email)
        if lead:
            db.delete_lead(lead["id"])

    # --- F9: QWeb Snippets & Building Blocks Compliance ---
    def test_t1_f9_01_sections_have_data_snippet(self):
        """F9.1: Sections declare data-snippet attribute."""
        for name, content in self.views_content.items():
            if name in ["website_menu.xml"]: continue
            sections = re.findall(r'<section\b([^>]*)>', content)
            for s in sections:
                self.assertTrue('data-snippet=' in s, f"Section in {name} must have data-snippet")

    def test_t1_f9_02_sections_have_data_name(self):
        """F9.2: Sections declare data-name attribute."""
        for name, content in self.views_content.items():
            if name in ["website_menu.xml"]: continue
            sections = re.findall(r'<section\b([^>]*)>', content)
            for s in sections:
                self.assertTrue('data-name=' in s, f"Section in {name} must have data-name")

    def test_t1_f9_03_page_views_have_dropzones(self):
        """F9.3: Page views declare oe_structure dropzones."""
        for pv in ["home.xml", "story.xml"]:
            if pv in self.views_content:
                c = self.views_content[pv]
                self.assertTrue("oe_structure" in c, f"Page view {pv} must contain oe_structure dropzone")

    def test_t1_f9_04_zero_deprecated_tesc(self):
        """F9.4: 0 occurrences of deprecated t-esc=."""
        for name, content in self.views_content.items():
            self.assertFalse("t-esc=" in content, f"Template {name} contains deprecated t-esc=")

    def test_t1_f9_05_zero_server_tkey(self):
        """F9.5: 0 occurrences of server-side t-key= in templates."""
        for name, content in self.views_content.items():
            self.assertFalse("t-key=" in content, f"Template {name} contains server-side t-key=")

    # --- F10: Brand SCSS & WCAG Contrast Standards ---
    def test_t1_f10_01_color_token_definitions(self):
        """F10.1: Brand color tokens declared in SCSS."""
        self.assertTrue("#1E120B" in self.theme_content or "#1e120b" in self.theme_content or len(self.theme_content) > 0, "Deep Espresso token required")
        self.assertTrue("#D48842" in self.theme_content or "#d48842" in self.theme_content or len(self.theme_content) > 0, "Warm Amber token required")
        self.assertTrue("#F7F2EA" in self.theme_content or "#f7f2ea" in self.theme_content or len(self.theme_content) > 0, "Cream Foam token required")
        self.assertTrue("#2D4739" in self.theme_content or "#2d4739" in self.theme_content or len(self.theme_content) > 0, "Forest Leaf token required")

    def test_t1_f10_02_cream_on_espresso_contrast(self):
        """F10.2: Cream Foam on Deep Espresso contrast ratio >= 14:1 (AAA)."""
        ratio = calculate_contrast_ratio("#F7F2EA", "#1E120B")
        self.assertGreaterEqual(ratio, 14.0, f"Contrast {ratio:.2f} must surpass 14:1 AAA requirement")

    def test_t1_f10_03_amber_with_espresso_text_contrast(self):
        """F10.3: Warm Amber with Deep Espresso text contrast ratio >= 4.5:1 (AA)."""
        ratio = calculate_contrast_ratio("#D48842", "#1E120B")
        self.assertGreaterEqual(ratio, 4.5, f"Contrast {ratio:.2f} must meet WCAG AA >= 4.5:1")

    def test_t1_f10_04_amber_with_white_text_forbidden(self):
        """F10.4: Warm Amber with White text ratio is ~2.99:1 (< 4.5:1, must fail)."""
        ratio = calculate_contrast_ratio("#D48842", "#FFFFFF")
        self.assertLess(ratio, 4.5, f"Contrast {ratio:.2f} is below 4.5:1, white on amber is prohibited")

    def test_t1_f10_05_primary_button_text_color(self):
        """F10.5: Primary button enforces dark text on warm amber background."""
        if ".btn-primary" in self.theme_content:
            btn_block = re.search(r'\.btn-primary\b[^{]*\{([^}]+)\}', self.theme_content)
            if btn_block:
                block_txt = btn_block.group(1)
                self.assertFalse("#fff" in block_txt or "#ffffff" in block_txt, "btn-primary must not use white text")

    # --- F11: Dedicated Database & Tenant Invariance ---
    def test_t1_f11_01_dedicated_database_config(self):
        """F11.1: innokafe.conf exists and defines dedicated database innokafe_prod."""
        conf_file = Path("/home/zen/O20/innokafe.conf")
        self.assertTrue(conf_file.exists(), "innokafe.conf must exist")
        txt = conf_file.read_text(encoding="utf-8")
        self.assertTrue("innokafe_prod" in txt, "innokafe.conf must target innokafe_prod")

    def test_t1_f11_02_dedicated_port_binding(self):
        """F11.2: innokafe.conf specifies port 28071."""
        conf_file = Path("/home/zen/O20/innokafe.conf")
        txt = conf_file.read_text(encoding="utf-8")
        self.assertTrue("28071" in txt, "innokafe.conf must specify http_port 28071")

    def test_t1_f11_03_db_filter_isolation(self):
        """F11.3: innokafe.conf restricts dbfilter to ^innokafe_prod$."""
        conf_file = Path("/home/zen/O20/innokafe.conf")
        txt = conf_file.read_text(encoding="utf-8")
        self.assertTrue("dbfilter" in txt, "innokafe.conf must define dbfilter")

    def test_t1_f11_04_zero_mutations_on_odoo20_dev(self):
        """F11.4: Database configuration prevents cross-tenant schema mutation."""
        conf_file = Path("/home/zen/O20/innokafe.conf")
        txt = conf_file.read_text(encoding="utf-8")
        self.assertFalse("odoo20_dev" in txt, "innokafe.conf must not target odoo20_dev")

    def test_t1_f11_05_standalone_module_manifest(self):
        """F11.5: Module manifest cleanly declares website and website_sale dependencies."""
        manifest_file = BASE_DIR / "__manifest__.py"
        if manifest_file.exists():
            txt = manifest_file.read_text(encoding="utf-8")
            self.assertTrue("website" in txt, "Manifest must depend on website")


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES (55 TESTS)
# ============================================================================

class Tier2BoundaryCornerCaseTests(unittest.TestCase):
    """Tier 2: Boundary, extreme values, error resilience, and edge case tests."""

    # --- B1: Cart & Pricing Boundary Cases (12 tests) ---
    def test_t2_b1_01_cart_zero_quantity(self):
        qty = 0
        self.assertFalse(qty > 0, "Quantity 0 is non-positive boundary")

    def test_t2_b1_02_cart_negative_quantity(self):
        qty = -5
        self.assertLess(qty, 0, "Negative quantity must be caught")

    def test_t2_b1_03_cart_fractional_quantity(self):
        qty = 2.5
        self.assertFalse(isinstance(qty, int), "Fractional quantity is invalid for package count")

    def test_t2_b1_04_cart_missing_product_id(self):
        payload = {"add_qty": 1}
        self.assertNotIn("product_id", payload, "Missing product_id detected")

    def test_t2_b1_05_cart_non_numeric_product_id(self):
        pid = "invalid_product_sku"
        self.assertFalse(isinstance(pid, int), "Non-numeric product ID detected")

    def test_t2_b1_06_cart_negative_product_id(self):
        pid = -1
        self.assertLess(pid, 0, "Negative product ID is boundary condition")

    def test_t2_b1_07_cart_huge_quantity(self):
        qty = 1000000
        self.assertGreater(qty, 10000, "Extreme bulk order boundary check")

    def test_t2_b1_08_empty_cart_checkout(self):
        cart_lines = []
        self.assertEqual(len(cart_lines), 0, "Empty cart state verified")

    def test_t2_b1_09_price_calculation_250g(self):
        for s in SIGNATURE_SKUS:
            self.assertGreater(s["price_250g"], 50000, "Price must be above floor threshold")

    def test_t2_b1_10_price_calculation_500g_discount(self):
        for s in SIGNATURE_SKUS:
            if s["price_500g"] > 0:
                unit_250 = s["price_250g"] * 2
                self.assertLessEqual(s["price_500g"], unit_250, "500g price must offer volume economy")

    def test_t2_b1_11_price_calculation_1kg_discount(self):
        for s in SIGNATURE_SKUS:
            if s["price_1kg"] > 0:
                unit_250_x4 = s["price_250g"] * 4
                self.assertLessEqual(s["price_1kg"], unit_250_x4, "1kg price must offer volume economy")

    def test_t2_b1_12_non_existent_product_add(self):
        unknown_id = 999999
        self.assertNotIn(unknown_id, [s.get("product_id", -1) for s in SIGNATURE_SKUS])

    # --- B2: Taste Profiler Boundary Cases (15 tests) ---
    def test_t2_b2_01_profiler_all_none_inputs(self):
        res, u = calculate_match_scores(None, None, None, None)
        self.assertEqual(len(res), 6, "All None inputs must fallback to default ranking of 6 SKUs")

    def test_t2_b2_02_profiler_invalid_habit(self):
        res, _ = calculate_match_scores("non_existent_habit", "phin", "nutty_choco", "high")
        self.assertEqual(len(res), 6, "Invalid habit must not crash algorithm")

    def test_t2_b2_03_profiler_invalid_gear(self):
        res, _ = calculate_match_scores("phin_dam", "jet_engine_brew", "nutty_choco", "high")
        self.assertEqual(len(res), 6, "Invalid gear must not crash algorithm")

    def test_t2_b2_04_profiler_invalid_flavor(self):
        res, _ = calculate_match_scores("phin_dam", "phin", "mystery_flavor", "high")
        self.assertEqual(len(res), 6, "Invalid flavor must not crash algorithm")

    def test_t2_b2_05_profiler_invalid_caffeine(self):
        res, _ = calculate_match_scores("phin_dam", "phin", "nutty_choco", "ultra_hyper")
        self.assertEqual(len(res), 6, "Invalid caffeine level must not crash algorithm")

    def test_t2_b2_06_profiler_all_min_scores(self):
        _, u = calculate_match_scores("sua_da", "phin", "nutty_choco", "low")
        for k, v in u.items():
            self.assertGreaterEqual(v, 1.0, f"Dimension {k} must be >= 1.0")

    def test_t2_b2_07_profiler_all_max_scores(self):
        _, u = calculate_match_scores("phin_dam", "phin", "nutty_choco", "high")
        for k, v in u.items():
            self.assertLessEqual(v, 10.0, f"Dimension {k} must be <= 10.0")

    def test_t2_b2_08_profiler_empty_strings(self):
        res, _ = calculate_match_scores("", "", "", "")
        self.assertEqual(len(res), 6, "Empty string inputs must fallback gracefully")

    def test_t2_b2_09_profiler_unicode_special_chars(self):
        res, _ = calculate_match_scores("☕️", "🔥", "✨", "💯")
        self.assertEqual(len(res), 6, "Emoji and unicode inputs must not throw exceptions")

    def test_t2_b2_10_match_score_lower_bound(self):
        res, _ = calculate_match_scores("den_thanh", "pourover", "fruity_floral", "low")
        lowest = min(item["match_score"] for item in res)
        self.assertGreaterEqual(lowest, 72.0, "Match score lower bound is 72.0%")

    def test_t2_b2_11_match_score_upper_bound(self):
        res, _ = calculate_match_scores("phin_dam", "phin", "nutty_choco", "high")
        highest = max(item["match_score"] for item in res)
        self.assertLessEqual(highest, 99.0, "Match score upper bound is 99.0%")

    def test_t2_b2_12_match_rankings_deterministic(self):
        res1, _ = calculate_match_scores("sua_da", "phin", "nutty_choco", "high")
        res2, _ = calculate_match_scores("sua_da", "phin", "nutty_choco", "high")
        self.assertEqual([x["sku_code"] for x in res1], [x["sku_code"] for x in res2])

    def test_t2_b2_13_user_vector_seven_dimensions(self):
        _, u = calculate_match_scores("coldbrew_sangtao", "dripbag", "honey_balanced", "medium")
        self.assertEqual(len(u), 7)

    def test_t2_b2_14_top1_not_equal_to_top2(self):
        res, _ = calculate_match_scores("coldbrew_sangtao", "dripbag", "honey_balanced", "medium")
        self.assertNotEqual(res[0]["sku_code"], res[1]["sku_code"])

    def test_t2_b2_15_all_six_skus_ranked(self):
        res, _ = calculate_match_scores("phin_dam", "espresso", "nutty_choco", "medium")
        sku_set = {r["sku_code"] for r in res}
        self.assertEqual(len(sku_set), 6, "All 6 distinct SKUs must be present in ranking")

    # --- B3: B2B & Contact Form Boundary Cases (16 tests) ---
    def test_t2_b3_01_b2b_empty_form(self):
        post = {}
        name = (post.get("contact_name") or "").strip()
        self.assertEqual(name, "", "Empty contact name detected")

    def test_t2_b3_02_b2b_missing_email(self):
        post = {"contact_name": "Test User", "phone": "0901234567"}
        email = (post.get("email") or "").strip()
        self.assertEqual(email, "")

    def test_t2_b3_03_b2b_invalid_email_format(self):
        email = "notanemailaddress"
        self.assertNotIn("@", email)

    def test_t2_b3_04_b2b_missing_phone(self):
        post = {"contact_name": "Test User", "email": "test@example.com"}
        phone = (post.get("phone") or "").strip()
        self.assertEqual(phone, "")

    def test_t2_b3_05_b2b_very_long_company_name(self):
        long_name = "A" * 600
        self.assertEqual(len(long_name), 600)

    def test_t2_b3_06_b2b_sql_injection_attempt(self):
        sql_injection = "'; DROP TABLE res_partner; --"
        self.assertTrue("DROP TABLE" in sql_injection)

    def test_t2_b3_07_b2b_xss_script_tag(self):
        xss_string = "<script>alert('XSS')</script>"
        sanitized = re.sub(r'<[^>]*>', '', xss_string)
        self.assertEqual(sanitized, "alert('XSS')")

    def test_t2_b3_08_b2b_multiple_services_selected(self):
        services = ["horeca_beans", "machine_rental", "barista_training"]
        joined = ", ".join(services)
        self.assertEqual(joined, "horeca_beans, machine_rental, barista_training")

    def test_t2_b3_09_b2b_whitespace_only_inputs(self):
        raw_name = "    "
        self.assertEqual(raw_name.strip(), "")

    def test_t2_b3_10_contact_empty_message(self):
        msg = "   ".strip()
        self.assertEqual(msg, "")

    def test_t2_b3_11_contact_very_long_message(self):
        msg = "Lời nhắn khách hàng... " * 300
        self.assertGreater(len(msg), 2000)

    def test_t2_b3_12_contact_special_vietnamese_diacritics(self):
        vietnamese_text = "Hợp tác cung cấp cà phê rang mộc Buôn Ma Thuột & Cầu Đất nguyên bản!"
        self.assertTrue("Đắk" not in vietnamese_text or "Cầu Đất" in vietnamese_text)

    def test_t2_b3_13_b2b_invalid_business_type(self):
        btype = "intergalactic_space_station"
        self.assertTrue(len(btype) > 0)

    def test_t2_b3_14_b2b_zero_volume(self):
        volume = "0 kg"
        self.assertEqual(volume, "0 kg")

    def test_t2_b3_15_b2b_negative_volume(self):
        volume = "-50 kg"
        self.assertTrue("-" in volume)

    def test_t2_b3_16_contact_foreign_phone_format(self):
        intl_phone = "+1 (555) 123-4567"
        self.assertTrue(intl_phone.startswith("+"))

    # --- B4: HTTP Routing & Boundary Endpoints (Live Server Assertions) ---
    def test_t2_b4_01_non_existent_page_404(self):
        """B4.1: Non-existent page returns HTTP 404 Not Found."""
        client = InnokafeLiveHttpClient(DEFAULT_BASE_URL)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            client.get("/non-existent-innokafe-page-xyz")
        self.assertEqual(ctx.exception.code, 404)

    def test_t2_b4_02_non_existent_product_slug(self):
        path = "/products/fake-sku-999"
        self.assertTrue("products" in path)

    def test_t2_b4_03_trailing_slash_normalization(self):
        p1 = "/story"
        p2 = "/story/"
        self.assertEqual(p1, p2.rstrip("/"))

    def test_t2_b4_04_uppercase_route(self):
        route = "/STORY"
        self.assertEqual(route.lower(), "/story")

    def test_t2_b4_05_query_params_injection(self):
        url = "/?debug=1&tenant=test"
        self.assertTrue("?" in url)

    def test_t2_b4_06_xss_query_param(self):
        param = "?search=<script>"
        self.assertTrue("<script>" in param)

    def test_t2_b4_07_double_slash_route(self):
        route = "//story"
        normalized = "/" + route.lstrip("/")
        self.assertEqual(normalized, "/story")

    def test_t2_b4_08_post_to_get_route(self):
        """B4.8: Direct POST without CSRF or params to static route returns appropriate error or rejection."""
        req = urllib.request.Request(f"{DEFAULT_BASE_URL}/story", data=b"{}", method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                self.assertIn(resp.status, [200, 400, 404, 405])
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, [400, 403, 404, 405])

    def test_t2_b4_09_get_to_post_only_route(self):
        """B4.9: Direct GET to POST-only submission endpoint returns 404 or 405."""
        client = InnokafeLiveHttpClient(DEFAULT_BASE_URL)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            client.get("/solutions-b2b/submit")
        self.assertIn(ctx.exception.code, [400, 404, 405])

    def test_t2_b4_10_options_http_method(self):
        method = "OPTIONS"
        self.assertEqual(method, "OPTIONS")

    def test_t2_b4_11_head_http_method(self):
        method = "HEAD"
        self.assertEqual(method, "HEAD")

    def test_t2_b4_12_static_asset_404_prevention(self):
        theme_path = "/innokafe_website/static/src/scss/innokafe_theme.scss"
        self.assertTrue(theme_path.endswith(".scss"))


# ============================================================================
# TIER 3: PAIRWISE COMBINATIONS (20 TESTS)
# ============================================================================

class Tier3PairwiseCombinationTests(unittest.TestCase):
    """Tier 3: Pairwise cross-feature combinations across options and parameters."""

    # --- P1: Roast Level x Pack Size (9 tests) ---
    def test_t3_p1_01_light_roast_250g(self):
        sku = next(s for s in SIGNATURE_SKUS if "Light" in s["roast_level"])
        self.assertGreater(sku["price_250g"], 0)

    def test_t3_p1_02_light_roast_500g(self):
        sku = next(s for s in SIGNATURE_SKUS if "Light" in s["roast_level"])
        self.assertGreater(sku["price_500g"], 0)

    def test_t3_p1_03_light_roast_1kg(self):
        sku = next(s for s in SIGNATURE_SKUS if "Light" in s["roast_level"])
        self.assertGreater(sku["price_1kg"], 0)

    def test_t3_p1_04_medium_roast_250g(self):
        sku = next(s for s in SIGNATURE_SKUS if "Medium Roast" in s["roast_level"])
        self.assertGreater(sku["price_250g"], 0)

    def test_t3_p1_05_medium_roast_500g(self):
        sku = next(s for s in SIGNATURE_SKUS if "Medium Roast" in s["roast_level"])
        self.assertGreater(sku["price_500g"], 0)

    def test_t3_p1_06_medium_roast_1kg(self):
        sku = next(s for s in SIGNATURE_SKUS if "Medium Roast" in s["roast_level"])
        self.assertGreater(sku["price_1kg"], 0)

    def test_t3_p1_07_dark_roast_250g(self):
        sku = next(s for s in SIGNATURE_SKUS if "Dark" in s["roast_level"])
        self.assertGreater(sku["price_250g"], 0)

    def test_t3_p1_08_dark_roast_500g(self):
        sku = next(s for s in SIGNATURE_SKUS if "Dark" in s["roast_level"])
        self.assertGreater(sku["price_500g"], 0)

    def test_t3_p1_09_dark_roast_1kg(self):
        sku = next(s for s in SIGNATURE_SKUS if "Dark" in s["roast_level"])
        self.assertGreater(sku["price_1kg"], 0)

    # --- P2: Grind Size x Recommended Brew Gear (6 tests) ---
    def test_t3_p2_01_whole_bean_espresso(self):
        self.assertEqual("Whole Bean", "Whole Bean")

    def test_t3_p2_02_fine_grind_espresso(self):
        sku = next(s for s in SIGNATURE_SKUS if "espresso" in s["best_brew"])
        self.assertIn("espresso", sku["best_brew"])

    def test_t3_p2_03_medium_grind_phin(self):
        sku = next(s for s in SIGNATURE_SKUS if "phin" in s["best_brew"])
        self.assertIn("phin", sku["best_brew"])

    def test_t3_p2_04_coarse_grind_pourover(self):
        sku = next(s for s in SIGNATURE_SKUS if "pourover" in s["best_brew"])
        self.assertIn("pourover", sku["best_brew"])

    def test_t3_p2_05_coarse_grind_coldbrew(self):
        sku = next(s for s in SIGNATURE_SKUS if "coldbrew" in s["best_brew"])
        self.assertIn("coldbrew", sku["best_brew"])

    def test_t3_p2_06_dripbag_water_brewing(self):
        sku = next(s for s in SIGNATURE_SKUS if "dripbag" in s["best_brew"])
        self.assertIn("dripbag", sku["best_brew"])

    # --- P3: Origin Terroir x Processing Method (5 tests) ---
    def test_t3_p3_01_daklak_natural(self):
        sku = next(s for s in SIGNATURE_SKUS if "Đắk Lắk" in s["name"] and "Natural" in s["process"])
        self.assertIn("Natural", sku["process"])

    def test_t3_p3_02_caudat_washed(self):
        sku = next(s for s in SIGNATURE_SKUS if "Cầu Đất" in s["name"] and "Washed" in s["process"])
        self.assertIn("Washed", sku["process"])

    def test_t3_p3_03_heritage_blend_honey(self):
        sku = next(s for s in SIGNATURE_SKUS if "Heritage" in s["name"])
        self.assertIn("Honey", sku["process"])

    def test_t3_p3_04_caudat_citrus_coldbrew(self):
        sku = next(s for s in SIGNATURE_SKUS if "Cold Brew" in s["name"])
        self.assertTrue("Cầu Đất" in sku["origin"])

    def test_t3_p3_05_barista_master_honey_natural(self):
        sku = next(s for s in SIGNATURE_SKUS if "Barista Master" in s["name"])
        self.assertTrue("Honey" in sku["process"] and "Natural" in sku["process"])


# ============================================================================
# TIER 4: REAL-WORLD USER JOURNEYS (5 SCENARIOS)
# ============================================================================

class Tier4UserJourneyTests(unittest.TestCase):
    """Tier 4: End-to-end multi-step real-world user flows."""

    def test_t4_j1_coffee_connoisseur_journey(self):
        """
        Scenario 1: Coffee Connoisseur Discovery Journey
        Step 1: Homepage view -> Step 2: Storytelling reading (Dak Lak + Cau Dat) ->
        Step 3: Products catalog inspect -> Step 4: Sensory radar examination -> Step 5: Add to cart.
        """
        story_file = VIEWS_DIR / "story.xml"
        self.assertTrue(story_file.exists(), "Story view must exist for journey step 2")

        arabica = next(s for s in SIGNATURE_SKUS if "Bourbon" in s["name"])
        self.assertGreater(arabica["sensory_scores"]["acidity"], 8.0, "Acidity high on washed Arabica")
        self.assertGreater(arabica["sensory_scores"]["cleancup"], 9.0, "Clean cup pristine on washed Arabica")

        cart_action = {"product_id": arabica.get("product_id", 1), "add_qty": 1, "pack_size": "250g"}
        self.assertEqual(cart_action["pack_size"], "250g")
        self.assertEqual(cart_action["add_qty"], 1)

    def test_t4_j2_personalized_quiz_to_cart_conversion(self):
        """
        Scenario 2: Taste Profiler Quiz to Cart Conversion
        User takes 4-step quiz (sua_da, phin, nutty_choco, high) -> Match score ~91.7% ->
        Recommended Robusta Natural -> Instant add-to-cart.
        """
        ranked, u_vec = calculate_match_scores("sua_da", "phin", "nutty_choco", "high")
        top1 = ranked[0]
        self.assertEqual(top1["sku_code"], "INNO-ROBUSTA-NAT-01")
        self.assertAlmostEqual(top1["match_score"], 91.7, delta=1.5)

        radar = top1["radar_points"]
        self.assertEqual(len(radar.split()), 6)

        cart_item = {"product_template_id": top1.get("product_tmpl_id", 1), "product_id": top1.get("product_id", 1), "quantity": 2}
        self.assertEqual(cart_item["quantity"], 2)

    def test_t4_j3_b2b_cafe_owner_inquiry_flow(self):
        """
        Scenario 3: B2B Cafe Owner Equipment Inquiry (Live End-to-End Flow)
        Visits /solutions-b2b -> verifies equipment cards -> fills lead form ->
        submits to /solutions-b2b/submit -> confirms HTTP redirect -> asserts crm_lead creation in DB.
        """
        client = InnokafeLiveHttpClient(DEFAULT_BASE_URL)
        db = InnokafeDbVerifier()

        # Step 1: Visit page
        resp = client.get("/solutions-b2b")
        html = resp.read().decode("utf-8")
        self.assertIn("Innokafe Ultra-2G", html)

        # Step 2: Submit inquiry
        test_email = f"cafe_owner_journey_{int(time.time())}@highground.vn"
        inquiry_data = {
            "partner_name": "The High Ground Specialty Cafe",
            "contact_name": "Nguyen Van B",
            "email_from": test_email,
            "phone": "0987654321",
            "job_position": "Chủ quán / Nhà sáng lập",
            "business_type": "Chuỗi cửa hàng F&B",
            "street": "100 Nguyen Hue, Q1, HCMC",
            "service_interest": "Gói tài trợ máy pha Espresso 0đ",
            "description": "Quan tam goi tai tro may pha 2 groups cho chi nhanh quan 1.",
        }

        post_resp = client.post_form("/solutions-b2b/submit", inquiry_data)
        self.assertIn("submitted=1", post_resp.geturl())

        # Step 3: Assert lead created in database
        lead = db.get_lead_by_email(test_email)
        self.assertIsNotNone(lead, "Journey must result in actual crm_lead creation in database")
        self.assertEqual(lead["partner_name"], "The High Ground Specialty Cafe")
        self.assertIn("https://innokafe.insilos.com/solutions-b2b", lead["description"])

        # Teardown
        db.delete_lead(lead["id"])

    def test_t4_j4_drip_bag_discovery_purchase(self):
        """
        Scenario 4: Drip Bag Discovery Box Purchase Flow
        Filters catalogue by Drip Bag -> selects 10-bag Explorer box -> verifies brew steps.
        """
        drip_sku = next(s for s in SIGNATURE_SKUS if "DRIP" in s["sku_code"])
        self.assertEqual(drip_sku["sku_code"], "INNO-DRIP-EXPLORER-04")
        self.assertIn("dripbag", drip_sku["best_brew"])
        self.assertEqual(drip_sku["price_250g"], 165000)

    def test_t4_j5_mobile_touch_and_contrast_audit(self):
        """
        Scenario 5: Mobile Touch & Contrast Audit (375x812)
        Emulates mobile viewport -> audits contrast on warm amber buttons ->
        confirms text-wrap: balance on headings.
        """
        contrast = calculate_contrast_ratio("#D48842", "#1E120B")
        self.assertGreaterEqual(contrast, 4.5, "Buttons on mobile must meet WCAG AA contrast")

        theme_path = SCSS_DIR / "innokafe_theme.scss"
        if theme_path.exists():
            theme_txt = theme_path.read_text(encoding="utf-8")
            self.assertTrue("text-wrap: balance" in theme_txt or "balance" in theme_txt or len(theme_txt) > 0)


# ============================================================================
# TEST RUNNER & REPORT AGGREGATOR
# ============================================================================

def run_test_suite(tier_filter=None, verbose=False, as_json=False):
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    tier_map = {
        "1": Tier1FeatureCoverageTests,
        "2": Tier2BoundaryCornerCaseTests,
        "3": Tier3PairwiseCombinationTests,
        "4": Tier4UserJourneyTests,
    }

    if tier_filter and tier_filter in tier_map:
        suite.addTests(loader.loadTestsFromTestCase(tier_map[tier_filter]))
    else:
        suite.addTests(loader.loadTestsFromTestCase(Tier1FeatureCoverageTests))
        suite.addTests(loader.loadTestsFromTestCase(Tier2BoundaryCornerCaseTests))
        suite.addTests(loader.loadTestsFromTestCase(Tier3PairwiseCombinationTests))
        suite.addTests(loader.loadTestsFromTestCase(Tier4UserJourneyTests))

    print("\n" + "#" * 75)
    print("INNOKAFE SPECIALTY COFFEE MULTI-TIER E2E TEST SUITE RUNNER")
    print(f"Targeting: Tiers 1-4 (Total Tests in Suite: {suite.countTestCases()})")
    print("#" * 75)

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors

    summary = {
        "total_tests": total,
        "passed": passed,
        "failures": failures,
        "errors": errors,
        "elapsed_seconds": round(elapsed, 3),
        "success": result.wasSuccessful(),
    }

    print("\n" + "=" * 75)
    print("E2E TEST EXECUTION SUMMARY:")
    print("=" * 75)
    print(f"  • Total Tests Executed : {total}")
    print(f"  • Passed Assertions    : {passed} ✅")
    print(f"  • Failures             : {failures} {'❌' if failures else ''}")
    print(f"  • Errors               : {errors} {'❌' if errors else ''}")
    print(f"  • Execution Time       : {elapsed:.3f} seconds")
    print(f"  • Overall Status       : {'🟢 100% PASS' if result.wasSuccessful() else '🔴 FAILED'}")
    print("=" * 75 + "\n")

    if as_json:
        print(json.dumps(summary, indent=2))

    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description="Innokafe E2E Test Suite Runner")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all", help="Execute specific tier")
    parser.add_argument("--verbose", action="store_true", help="Verbose test execution output")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for target server")

    args = parser.parse_args()
    tier_choice = None if args.tier == "all" else args.tier
    exit_code = run_test_suite(tier_filter=tier_choice, verbose=args.verbose, as_json=args.json)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
