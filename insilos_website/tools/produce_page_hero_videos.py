#!/usr/bin/env python3
"""
INSILOS PRODUCTION ENGINE: MULTI-PAGE HERO VIDEO GENERATOR (OPTIMIZED)
Parallel harness for producing 15 C3.ai-grade HUD Telemetry Videos and WebP Posters
for all core routes on the Insilos Enterprise Website.

Features:
- Fast 8.0s looping background video clips (2MB - 4MB per video)
- Authentic Pexels & C3.ai 1080p footage
- High-tech HUD telemetry overlays burned in with sub-second latency
- High quality WebP poster generation for mobile/instant display
"""

import os
import sys
import time
import subprocess
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_OUT_DIR = os.path.join(BASE_DIR, "static", "src", "video")
TEMP_HUD_DIR = "/tmp/insilos_page_huds"

os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
os.makedirs(TEMP_HUD_DIR, exist_ok=True)

# Typography
FONT_MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_MONO_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# Color Palette (C3.ai / Insilos Industrial Theme)
COLOR_ORANGE = (255, 128, 0, 240)       # #FF8000 Insilos Brand Orange
COLOR_CYAN = (0, 229, 255, 230)          # #00E5FF High-Tech Cyan
COLOR_GREEN = (16, 185, 129, 230)        # #10B981 Emerald Verified
COLOR_WHITE = (255, 255, 255, 245)
COLOR_MUTED = (160, 174, 192, 220)
COLOR_BG_DARK = (11, 19, 43, 220)        # Semi-transparent dark slate
COLOR_BG_BAR = (7, 11, 20, 215)
COLOR_BORDER_ORANGE = (255, 128, 0, 180)
COLOR_BORDER_CYAN = (0, 229, 255, 140)

def draw_corner_reticle(draw, x1, y1, x2, y2, color, length=28, width=3):
    """Draw high-tech corner brackets around bounding box."""
    # Top-Left
    draw.line([(x1, y1), (x1 + length, y1)], fill=color, width=width)
    draw.line([(x1, y1), (x1, y1 + length)], fill=color, width=width)
    # Top-Right
    draw.line([(x2, y1), (x2 - length, y1)], fill=color, width=width)
    draw.line([(x2, y1), (x2, y1 + length)], fill=color, width=width)
    # Bottom-Left
    draw.line([(x1, y2), (x1 + length, y2)], fill=color, width=width)
    draw.line([(x1, y2), (x1, y2 - length)], fill=color, width=width)
    # Bottom-Right
    draw.line([(x2, y2), (x2 - length, y2)], fill=color, width=width)
    draw.line([(x2, y2), (x2 - length, y2)], fill=color, width=width)

def draw_center_crosshair(draw, cx, cy, size=10, color=COLOR_ORANGE):
    """Draw small crosshair reticle."""
    draw.line([(cx - size, cy), (cx + size, cy)], fill=color, width=1)
    draw.line([(cx, cy - size), (cx, cy + size)], fill=color, width=1)

def draw_hud_badge(draw, x, y, title, subtitle=None, color_accent=COLOR_ORANGE, border_color=COLOR_BORDER_ORANGE):
    """Draw target telemetry badge with primary and secondary tags."""
    font_bold = get_font(FONT_MONO_BOLD, 14)
    font_reg = get_font(FONT_MONO_REG, 12)
    
    bbox_title = font_bold.getbbox(title)
    w_title = bbox_title[2] - bbox_title[0]
    
    w_sub = 0
    if subtitle:
        bbox_sub = font_reg.getbbox(subtitle)
        w_sub = bbox_sub[2] - bbox_sub[0]
    
    badge_w = max(w_title, w_sub) + 24
    badge_h = 28 + (20 if subtitle else 0)
    
    draw.rectangle([(x, y), (x + badge_w, y + badge_h)], fill=COLOR_BG_DARK, outline=border_color, width=1)
    draw.line([(x, y), (x, y + badge_h)], fill=color_accent, width=3)
    
    draw.text((x + 10, y + 6), title, fill=COLOR_WHITE, font=font_bold)
    if subtitle:
        draw.text((x + 10, y + 26), subtitle, fill=color_accent, font=font_reg)
    
    return x + badge_w, y + badge_h

def draw_system_header(draw, title, category="SOVEREIGN AI-OS", accent_color=COLOR_ORANGE):
    """Draw top-left enterprise header badge."""
    font_cat = get_font(FONT_MONO_BOLD, 11)
    font_title = get_font(FONT_SANS_BOLD, 15)
    
    x, y = 36, 32
    draw.rectangle([(x, y), (x + 580, y + 48)], fill=COLOR_BG_BAR, outline=(255, 255, 255, 30), width=1)
    draw.rectangle([(x, y), (x + 4, y + 48)], fill=accent_color)
    
    draw.text((x + 14, y + 8), f"INSILOS // {category}", fill=accent_color, font=font_cat)
    draw.text((x + 14, y + 24), title, fill=COLOR_WHITE, font=font_title)

def draw_top_right_status(draw, text, tag="VERIFIED", tag_color=COLOR_GREEN):
    """Draw top-right mission clock and verification badge."""
    font_bold = get_font(FONT_MONO_BOLD, 12)
    font_tag = get_font(FONT_MONO_BOLD, 11)
    
    tag_str = f"● {tag}"
    bbox_tag = font_tag.getbbox(tag_str)
    w_tag = (bbox_tag[2] - bbox_tag[0]) + 16
    
    bbox_text = font_bold.getbbox(text)
    w_text = bbox_text[2] - bbox_text[0]
    
    total_w = w_tag + w_text + 36
    x = 1920 - 36 - total_w
    y = 32
    
    draw.rectangle([(x, y), (x + total_w, y + 44)], fill=COLOR_BG_BAR, outline=(255, 255, 255, 40), width=1)
    draw.rectangle([(x + 10, y + 10), (x + 10 + w_tag, y + 34)], fill=(16, 185, 129, 200), outline=(52, 211, 153, 255), width=1)
    draw.text((x + 18, y + 13), tag_str, fill=(255, 255, 255, 255), font=font_tag)
    draw.text((x + 10 + w_tag + 12, y + 14), text, fill=COLOR_WHITE, font=font_bold)

def draw_bottom_telemetry_bar(draw, telemetry_text, protocol_text, accent_color=COLOR_CYAN):
    """Draw lower telemetry ribbon spanning bottom of viewport."""
    font_mono = get_font(FONT_MONO_BOLD, 12)
    font_proto = get_font(FONT_MONO_REG, 11)
    
    draw.rectangle([(36, 1016), (780, 1052)], fill=COLOR_BG_BAR, outline=COLOR_BORDER_CYAN, width=1)
    draw.text((50, 1026), telemetry_text, fill=accent_color, font=font_mono)
    
    draw.rectangle([(1260, 1016), (1884, 1052)], fill=COLOR_BG_BAR, outline=(255, 255, 255, 30), width=1)
    draw.text((1276, 1027), protocol_text, fill=COLOR_MUTED, font=font_proto)

def generate_hud_overlay(page_key, title, category, target_box, target_label, sub_box, sub_label, status_tag, status_text, telemetry_text, protocol_text):
    img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Primary Target
    if target_box:
        x1, y1, x2, y2 = target_box
        draw_corner_reticle(draw, x1, y1, x2, y2, COLOR_ORANGE, length=32, width=3)
        draw_center_crosshair(draw, (x1 + x2)//2, (y1 + y2)//2, size=12, color=COLOR_ORANGE)
        if target_label:
            lbl_title, lbl_sub = target_label
            draw_hud_badge(draw, x1, max(100, y1 - 50), lbl_title, lbl_sub, color_accent=COLOR_ORANGE)
            
    # Secondary Target
    if sub_box:
        sx1, sy1, sx2, sy2 = sub_box
        draw_corner_reticle(draw, sx1, sy1, sx2, sy2, COLOR_CYAN, length=22, width=2)
        draw_center_crosshair(draw, (sx1 + sx2)//2, (sy1 + sy2)//2, size=8, color=COLOR_CYAN)
        if sub_label:
            slbl_title, slbl_sub = sub_label
            draw_hud_badge(draw, sx1, max(100, sy1 - 50), slbl_title, slbl_sub, color_accent=COLOR_CYAN, border_color=COLOR_BORDER_CYAN)
            
    # Headers & Ribbons
    draw_system_header(draw, title, category, COLOR_ORANGE)
    draw_top_right_status(draw, status_text, status_tag, COLOR_GREEN)
    draw_bottom_telemetry_bar(draw, telemetry_text, protocol_text, COLOR_CYAN)
    
    path = os.path.join(TEMP_HUD_DIR, f"hud_{page_key}.png")
    img.save(path)
    return path

# 15 High-Impact Video Configurations
CONFIGS = [
    {
        "key": "platform",
        "raw_source": "/tmp/pexels_eval/act3_noc.mp4",
        "ss": "00:00:02",
        "out_name": "hero_platform_opt",
        "duration": 8.0,
        "title": "SOVEREIGN OPERATIONAL AI PLATFORM",
        "category": "MISSION CONTROL AI-OS",
        "target_box": (720, 240, 1380, 720),
        "target_label": ("MISSION CONTROL NOC // 4 TIERS ACTIVE", "INGESTION · GRAPH · AGENTS · EXECUTION"),
        "sub_box": (1420, 520, 1820, 780),
        "sub_label": ("TELEMETRY CLUSTER // P99: 8.2ms", "100+ INDUSTRIAL CONNECTORS"),
        "status_tag": "AIR-GAPPED",
        "status_text": "SOC 2 TYPE II // ISO 27001",
        "telemetry_text": "● KERNEL: ACTIVE // 100K TPS MERKLE DAG // 0 CLOUD EGRESS",
        "protocol_text": "OPC-UA / IEC 62443 / FIPS 140-3 HSM // BLUEPRINT OK"
    },
    {
        "key": "solutions",
        "raw_source": "/tmp/pexels_eval/act1_robot100.mp4",
        "ss": "00:00:02",
        "out_name": "hero_solutions_opt",
        "duration": 8.0,
        "title": "ENTERPRISE OPERATIONAL SOLUTIONS DIRECTORY",
        "category": "SOLUTIONS HUB",
        "target_box": (680, 200, 1340, 680),
        "target_label": ("4 ENTERPRISE PILLARS // APAC DEPLOYED", "IDP · KNOWLEDGE GRAPH · TRADE · FSM"),
        "sub_box": (1400, 480, 1800, 740),
        "sub_label": ("CLOSED-LOOP AUTOMATION", "ERP WRITE-BACK // HUMAN IN THE LOOP"),
        "status_tag": "PRODUCTION",
        "status_text": "99.8% PRECISION // <15ms GRAPH",
        "telemetry_text": "● CROSS-SYSTEM PIPELINE: ACTIVE // EVN · MOBIFONE · SWAROVSKI",
        "protocol_text": "MULTI-TENANT GOVERNED ARCHITECTURE // 2026.3 RELEASE"
    },
    {
        "key": "idp",
        "raw_source": "/tmp/pexels_eval/act2_auto_terminal.mp4",
        "ss": "00:00:02",
        "out_name": "hero_idp_opt",
        "duration": 8.0,
        "title": "VERTICAL INTELLIGENT DOCUMENT PROCESSING (IDP)",
        "category": "LOGISTICS & TRADE OCR",
        "target_box": (600, 180, 1320, 700),
        "target_label": ("OCR PIPELINE // MULTI-MODAL EXTRACTION", "BILL OF LADING · COMMERCIAL INVOICE · C/O"),
        "sub_box": (1360, 440, 1800, 700),
        "sub_label": ("3-WAY RECONCILIATION // 99.8% MATCH", "VNACCS/VCIS EDI · CIRCULAR 78"),
        "status_tag": "STP NOMINAL",
        "status_text": "STP: 0.38s // ACCURACY: 99.8%",
        "telemetry_text": "● MULTI-PAGE PARSER: ACTIVE // 1,420 DOCS/HOUR // 0 RECTIFY",
        "protocol_text": "WCO SAFE FRAMEWORK // XML/EDIFACT AUTOMATION"
    },
    {
        "key": "graph",
        "raw_source": "/tmp/pexels_eval/act3_lights.mp4",
        "ss": "00:00:01",
        "out_name": "hero_graph_opt",
        "duration": 8.0,
        "title": "ENTERPRISE KNOWLEDGE GRAPH & DIGITAL TWINS",
        "category": "SEMANTIC ONTOLOGY ENGINE",
        "target_box": (640, 180, 1360, 720),
        "target_label": ("SEMANTIC KNOWLEDGE FABRIC // 2.8M TRIPLES", "OWL/RDF ONTOLOGY · DOMINO BOTTLENECK PREDICTION"),
        "sub_box": (1400, 500, 1820, 760),
        "sub_label": ("SUB-15ms GRAPH TRAVERSAL", "MULTI-HOP CONTEXTUAL REASONING"),
        "status_tag": "SYNCED",
        "status_text": "2.8M ENTERPRISE TRIPLES // <15ms",
        "telemetry_text": "● LIVING GRAPH: ACTIVE // LINEAGE AUDIT 100% // 0 SILOS",
        "protocol_text": "W3C SPARQL / OPENCYPHER / REAL-TIME TWIN REPLICATION"
    },
    {
        "key": "trade",
        "raw_source": "/tmp/pexels_eval/act2_caimep_port.mp4",
        "ss": "00:00:04",
        "out_name": "hero_trade_opt",
        "duration": 8.0,
        "title": "TRADE COMPLIANCE & CUSTOMS INTELLIGENCE",
        "category": "REGULATORY TARIFF AUTOMATION",
        "target_box": (580, 220, 1300, 720),
        "target_label": ("HS 8-10 DIGIT CLASSIFIER // FTA RULES", "EVFTA · CPTPP · RCEP · RVC/CTC ALGORITHM"),
        "sub_box": (1340, 480, 1780, 740),
        "sub_label": ("POST-CLEARANCE AUDIT DOSSIER", "MERKLE DAG PROOF OF ORIGIN"),
        "status_tag": "AUDIT READY",
        "status_text": "ZERO CUSTOMS DELAY // 100% FTA",
        "telemetry_text": "● TARIFF ENGINE: NOMINAL // 0 CUSTOMS PENALTIES // 98% RISK REDUCTION",
        "protocol_text": "WCO HARMONIZED SYSTEM 2026 // VNACCS INTEGRATED"
    },
    {
        "key": "fsm",
        "raw_source": "/tmp/pexels_eval/act4_field.mp4",
        "ss": "00:00:02",
        "out_name": "hero_fsm_opt",
        "duration": 8.0,
        "title": "FIELD SERVICE & INTELLIGENT ASSET OPERATIONS",
        "category": "PREDICTIVE FSM ENGINE",
        "target_box": (620, 200, 1340, 720),
        "target_label": ("FSM DISPATCH NODE // FTFR: 94.8%", "IOT VIBRATION TELEMETRY · AUTOMATED WORK ORDER"),
        "sub_box": (1380, 520, 1820, 780),
        "sub_label": ("MEAN TIME TO REPAIR: -65%", "IEC 61850 TECHNICIAN CERT MATCH"),
        "status_tag": "DISPATCH LIVE",
        "status_text": "FTFR: 94.8% // -65% MTTR",
        "telemetry_text": "● ASSET HEALTH MONITOR: 50.02 Hz // ZERO UNPLANNED DOWNTIME",
        "protocol_text": "IEC 61850 / ISO 55000 ASSET MANAGEMENT STANDARD"
    },
    {
        "key": "industries",
        "raw_source": "/tmp/pexels_eval/act1_welding.mp4",
        "ss": "00:00:01",
        "out_name": "hero_industries_opt",
        "duration": 8.0,
        "title": "101+ VERTICAL INDUSTRY SOVEREIGN SOLUTIONS",
        "category": "INDUSTRIAL SECTORS",
        "target_box": (660, 200, 1360, 720),
        "target_label": ("101 INDUSTRIAL PACKS // VAS 200/133", "PORTS · PHARMA · ENERGY · TELECOM · HEAVY INDUSTRY"),
        "sub_box": (1400, 500, 1820, 760),
        "sub_label": ("7-14 DAYS RAPID GO-LIVE", "PRE-BUILT GRC RISK CONTROLS"),
        "status_tag": "VERIFIED",
        "status_text": "101 INDUSTRY PACKS // 100% VAS",
        "telemetry_text": "● ENTERPRISE CONNECTORS: SAP S/4HANA · ORACLE CLOUD · SCADA",
        "protocol_text": "CIRCULAR 78 / VAS 200 / GRC SOD ENFORCEMENT"
    },
    {
        "key": "logistics",
        "raw_source": "/tmp/pexels_eval/act2_caimep_port.mp4",
        "ss": "00:00:08",
        "out_name": "hero_logistics_opt",
        "duration": 8.0,
        "title": "CÁI MÉP - THỊ VẢI DEEPWATER MARITIME TERMINAL",
        "category": "PORT & SUPPLY CHAIN AI",
        "target_box": (600, 180, 1320, 700),
        "target_label": ("INTERMODAL PORT TERMINAL // 14,200 TEU", "STS QUAY CRANE AUTO-DISPATCH · DEMURRAGE -88%"),
        "sub_box": (1360, 460, 1800, 720),
        "sub_label": ("VNACCS MANIFEST 99.8% MATCH", "AIS LIVE TRACKING // 0 INLINE BOTTLENECK"),
        "status_tag": "PORT LIVE",
        "status_text": "LAT: 10.518° N, LON: 107.022° E",
        "telemetry_text": "● MARITIME CORRIDOR: NOMINAL // 0 DEMURRAGE PENALTIES // WCO SAFE",
        "protocol_text": "VNACCS/VCIS EDI // CIRCULAR 78/2021/TT-BTC VERIFIED"
    },
    {
        "key": "pharma",
        "raw_source": "/tmp/pexels_eval/act3_datacenter.mp4",
        "ss": "00:00:05",
        "out_name": "hero_pharma_opt",
        "duration": 8.0,
        "title": "PHARMA MANUFACTURING & WHO-GMP AUTOMATION",
        "category": "GXP BIOREACTION & CLEANROOM",
        "target_box": (620, 220, 1340, 720),
        "target_label": ("GOLDEN BATCH AI // CLEANROOM PROCESS", "FDA 21 CFR PART 11 · GAMP 5 · DEVIATION -70%"),
        "sub_box": (1380, 500, 1820, 760),
        "sub_label": ("99.9% BATCH CONSISTENCY", "+14.2% YIELD OPTIMIZATION"),
        "status_tag": "GxP COMPLIANT",
        "status_text": "WHO-GMP // FDA 21 CFR PART 11",
        "telemetry_text": "● PROCESS TELEMETRY: REAL-TIME PAT // MERKLE AUDIT TRAIL 100%",
        "protocol_text": "GAMP 5 VALIDATED // ELECTRONIC BATCH RECORDING (EBR)"
    },
    {
        "key": "energy",
        "raw_source": "/tmp/pexels_eval/act4_turbines.mp4",
        "ss": "00:00:03",
        "out_name": "hero_energy_opt",
        "duration": 8.0,
        "title": "OFFSHORE WIND & RENEWABLE SMART GRID",
        "category": "EVN & CLEAN ENERGY AI",
        "target_box": (640, 220, 1360, 720),
        "target_label": ("OFFSHORE TURBINE CLUSTER // 400 MW", "IEC 61850 SUBSTATION TELEMETRY · 98.2% YIELD FORECAST"),
        "sub_box": (1400, 520, 1820, 780),
        "sub_label": ("UNPLANNED DOWNTIME: -62%", "SPOT MARKET BIDDING DISPATCH"),
        "status_tag": "GRID STABLE",
        "status_text": "50.02 Hz NOMINAL // 98.2% FORECAST",
        "telemetry_text": "● EVN GRID TELEMETRY: 2.4 kHz // P99: 11.2ms // DISPATCH READY",
        "protocol_text": "IEC 61850 / IEC 60870-5-104 / ISO 55000 CERTIFIED"
    },
    {
        "key": "fsm_industry",
        "raw_source": "/tmp/pexels_eval/act4_offshore.mp4",
        "ss": "00:00:02",
        "out_name": "hero_fsm_industry_opt",
        "duration": 8.0,
        "title": "TELECOM BTS & SUBSTATION FIELD MOBILITY",
        "category": "WORKFORCE DISPATCH",
        "target_box": (620, 220, 1340, 720),
        "target_label": ("WORKFORCE DISPATCH FABRIC // MOBIFONE", "GPS ROUTE OPTIMIZATION · FIRST-TIME FIX: 94.8%"),
        "sub_box": (1380, 520, 1820, 780),
        "sub_label": ("MTTR: -65% // SMR: 99.4%", "DIGITAL SOP 2026.3 IN FIELD"),
        "status_tag": "MOBILITY LIVE",
        "status_text": "FTFR: 94.8% // -40% TRANSIT",
        "telemetry_text": "● FIELD MOBILITY MESH: ACTIVE // 1,200 TECHNICIANS DEPLOYED",
        "protocol_text": "IEC 61850 CERTIFIED / ISO 9001 WORKFLOW ENGINE"
    },
    {
        "key": "pricing",
        "raw_source": "/tmp/pexels_eval/act3_noc.mp4",
        "ss": "00:00:04",
        "out_name": "hero_pricing_opt",
        "duration": 8.0,
        "title": "TRANSPARENT ENTERPRISE MICRO-LEDGER BILLING",
        "category": "COMMERCIAL TRUST & SLA",
        "target_box": (660, 240, 1360, 720),
        "target_label": ("AI CREDIT LEDGER // REAL-TIME METERING", "100% AUDITABLE METERING · 0 HIDDEN CHARGES"),
        "sub_box": (1400, 520, 1820, 780),
        "sub_label": ("PILOT 4 WEEKS RAPID PROOF", "100% SLA REFUND GUARANTEE"),
        "status_tag": "SLA VERIFIED",
        "status_text": "100% AUDIT REFUND GUARANTEE",
        "telemetry_text": "● MICRO-LEDGER: STAMPED // BILLING TRANSPARENCY 100% // P99 AUDIT",
        "protocol_text": "CRYPTO LEDGER MERKLE ATTESTATION // SOC 2 TYPE II"
    },
    {
        "key": "about",
        "raw_source": "/tmp/pexels_eval/act3_lights.mp4",
        "ss": "00:00:01",
        "out_name": "hero_about_opt",
        "duration": 8.0,
        "title": "SOVEREIGN OPERATIONAL AI ENGINEERING DNA",
        "category": "APAC HEADQUARTERS & R&D",
        "target_box": (640, 220, 1340, 720),
        "target_label": ("INSILOS R&D LABS // HANOI & HCMC", "ZERO CLOUD EGRESS · 100% DATA RESIDENCY"),
        "sub_box": (1380, 500, 1820, 760),
        "sub_label": ("SOVEREIGN AI RESEARCH", "APPLIED INDUSTRIAL MATHEMATICS"),
        "status_tag": "APAC SOVEREIGN",
        "status_text": "HANOI & HCMC R&D LABS",
        "telemetry_text": "● ENGINEERING MESH: ACTIVE // ISO 27001 & SOC 2 COMPLIANT",
        "protocol_text": "AIR-GAPPED COMPLIANCE // NATIONAL SOVEREIGN ARCHITECTURE"
    },
    {
        "key": "resources",
        "raw_source": "/tmp/pexels_eval/act3_datacenter.mp4",
        "ss": "00:00:02",
        "out_name": "hero_resources_opt",
        "duration": 8.0,
        "title": "KNOWLEDGE & GOVERNANCE ARCHITECTURE HUB",
        "category": "TECHNICAL WHITEPAPERS",
        "target_box": (640, 200, 1340, 700),
        "target_label": ("12 ENTERPRISE ARCHITECTURE WHITEPAPERS", "IDP · KNOWLEDGE GRAPH · IEC 61850 · VAS 200 GRC"),
        "sub_box": (1380, 500, 1820, 760),
        "sub_label": ("AUDIT EVIDENCE REPOSITORY", "SOC 2 TYPE II ATTESTATION"),
        "status_tag": "ARCHIVE LIVE",
        "status_text": "SOC 2 TYPE II // ISO 27001",
        "telemetry_text": "● BLUEPRINT REPOSITORY: ONLINE // PEER-REVIEWED ARCHITECTURE",
        "protocol_text": "W3C / IEC / WCO / FDA 21 CFR STANDARDS ALIGNED"
    },
    {
        "key": "demo",
        "raw_source": "/tmp/pexels_eval/act3_noc.mp4",
        "ss": "00:00:01",
        "out_name": "hero_demo_opt",
        "duration": 8.0,
        "title": "LIVE ARCHITECTURE BLUEPRINT DEMO SCHEDULING",
        "category": "TECHNICAL WALKTHROUGH",
        "target_box": (660, 220, 1360, 720),
        "target_label": ("1-ON-1 DISCOVERY & ARCHITECTURE REVIEW", "TAILORED TO YOUR ERP, WMS, SCADA & GRC POLICIES"),
        "sub_box": (1400, 520, 1820, 780),
        "sub_label": ("45-MINUTE FOCUSED SESSION", "ZERO SALES PITCH · PURE ENGINEERING"),
        "status_tag": "SCHEDULE LIVE",
        "status_text": "45-MIN ARCHITECT SESSION",
        "telemetry_text": "● DEMO ENGINE: READY // SECURE NDA PROTECTED // AIR-GAP DEMO",
        "protocol_text": "ENTERPRISE ARCHITECT DIRECT DISCOVERY // 2026.3 RELEASE"
    }
]

def render_single_hero(cfg):
    key = cfg["key"]
    raw_src = cfg["raw_source"]
    out_name = cfg["out_name"]
    duration = cfg.get("duration", 8.0)
    ss = cfg.get("ss", "00:00:01")
    
    mp4_out = os.path.join(VIDEO_OUT_DIR, f"{out_name}.mp4")
    webp_out = os.path.join(VIDEO_OUT_DIR, f"{out_name}_poster.webp")
    
    t0 = time.time()
    if not os.path.exists(raw_src):
        print(f"❌ Missing source file for {key}: {raw_src}")
        return False
        
    # 1. Generate HUD Overlay PNG
    hud_png = generate_hud_overlay(
        key, cfg["title"], cfg["category"],
        cfg["target_box"], cfg["target_label"],
        cfg["sub_box"], cfg["sub_label"],
        cfg["status_tag"], cfg["status_text"],
        cfg["telemetry_text"], cfg["protocol_text"]
    )
    
    # 2. Render MP4 with Burned HUD
    # Safe Filter: Scale + Crop + Color Tune + Overlay HUD (fps=30)
    vf = (
        "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        "fps=30,eq=brightness=-0.08:contrast=1.12:saturation=1.15[base];"
        "[base][1:v]overlay=0:0[vout]"
    )
    
    cmd_mp4 = [
        "ffmpeg", "-y",
        "-ss", ss,
        "-i", raw_src,
        "-i", hud_png,
        "-filter_complex", vf,
        "-map", "[vout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        "-t", str(duration),
        "-movflags", "+faststart",
        mp4_out
    ]
    
    res = subprocess.run(cmd_mp4, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0:
        print(f"❌ FFmpeg video error on {key}")
        return False
        
    # 3. Extract crisp frame as WebP poster (at ss=0.5s)
    cmd_poster = [
        "ffmpeg", "-y",
        "-ss", "00:00:00.5",
        "-i", mp4_out,
        "-vframes", "1",
        "-c:v", "libwebp",
        "-lossless", "0",
        "-q:v", "90",
        webp_out
    ]
    subprocess.run(cmd_poster, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    dur_sec = time.time() - t0
    size_mb = os.path.getsize(mp4_out) / (1024*1024)
    poster_kb = os.path.getsize(webp_out) / 1024 if os.path.exists(webp_out) else 0
    print(f"  ✓ {key:12} rendered in {dur_sec:4.1f}s | MP4: {size_mb:4.1f}MB | Poster: {poster_kb:4.0f}KB")
    return True

def main():
    print("="*70)
    print("INSILOS HERO VIDEO PRODUCTION HARNESS (PARALLEL EXECUTION)")
    print(f"Target Directory: {VIDEO_OUT_DIR}")
    print(f"Total Page Videos to Produce: {len(CONFIGS)}")
    print("="*70)
    
    t_start = time.time()
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(render_single_hero, CONFIGS))
        
    total_time = time.time() - t_start
    success_count = sum(1 for r in results if r)
    print("="*70)
    print(f"🏆 ALL RENDERING COMPLETE: {success_count}/{len(CONFIGS)} Videos Produced in {total_time:.1f}s!")
    print("="*70)

if __name__ == "__main__":
    main()
