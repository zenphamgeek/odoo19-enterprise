#!/usr/bin/env python3
"""
INSILOS PRODUCTION ENGINE: C3.AI-STYLE PEXELS VIDEO PRODUCER
Parallel harness for rendering 4-Act C3.ai Telemetry HUD Videos from Pexels footages.

Acts:
- Act 1: Industrial Robotics & SCADA Precision Assembly (Pexels ID 32386518)
- Act 2: Cái Mép - Thị Vải Deepwater Maritime Port & Customs IDP (Pexels ID 29904000)
- Act 3: Enterprise Mission Control NOC & Semantic Knowledge Graph (Pexels ID 38779100)
- Act 4: Offshore Wind Turbines & Clean Energy Grid (Pexels ID 13395532)

Output:
- enterprise/insilos_website/static/src/video/hero_act1_opt.mp4
- enterprise/insilos_website/static/src/video/hero_act2_opt.mp4
- enterprise/insilos_website/static/src/video/hero_act3_opt.mp4
- enterprise/insilos_website/static/src/video/hero_act4_opt.mp4
- Corresponding .webp posters
"""

import os
import sys
import time
import subprocess
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_OUT_DIR = os.path.join(BASE_DIR, "static", "src", "video")
RAW_FOOTAGE_DIR = "/tmp/pexels_eval"
TEMP_HUD_DIR = "/tmp/insilos_huds"

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
COLOR_ORANGE = (255, 128, 0, 240)       # #FF8000
COLOR_ORANGE_SUB = (255, 150, 40, 200)
COLOR_CYAN = (0, 229, 255, 230)          # #00E5FF
COLOR_GREEN = (16, 185, 129, 230)        # #10B981
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
    draw.line([(x2, y2), (x2, y2 - length)], fill=color, width=width)

def draw_center_crosshair(draw, cx, cy, size=10, color=COLOR_ORANGE):
    """Draw small crosshair reticle."""
    draw.line([(cx - size, cy), (cx + size, cy)], fill=color, width=1)
    draw.line([(cx, cy - size), (cx, cy + size)], fill=color, width=1)

def draw_hud_badge(draw, x, y, title, subtitle=None, color_accent=COLOR_ORANGE, border_color=COLOR_BORDER_ORANGE):
    """Draw target telemetry badge with primary and secondary tags."""
    font_bold = get_font(FONT_MONO_BOLD, 14)
    font_reg = get_font(FONT_MONO_REG, 12)
    
    # Calculate dimensions
    bbox_title = font_bold.getbbox(title)
    w_title = bbox_title[2] - bbox_title[0]
    h_title = bbox_title[3] - bbox_title[1]
    
    w_sub = 0
    h_sub = 0
    if subtitle:
        bbox_sub = font_reg.getbbox(subtitle)
        w_sub = bbox_sub[2] - bbox_sub[0]
        h_sub = bbox_sub[3] - bbox_sub[1]
    
    badge_w = max(w_title, w_sub) + 24
    badge_h = 28 + (20 if subtitle else 0)
    
    # Background Pill
    draw.rectangle([(x, y), (x + badge_w, y + badge_h)], fill=COLOR_BG_DARK, outline=border_color, width=1)
    # Left accent indicator
    draw.line([(x, y), (x, y + badge_h)], fill=color_accent, width=3)
    
    # Text
    draw.text((x + 10, y + 6), title, fill=COLOR_WHITE, font=font_bold)
    if subtitle:
        draw.text((x + 10, y + 26), subtitle, fill=color_accent, font=font_reg)
    
    return x + badge_w, y + badge_h

def draw_system_header(draw, title, category="SOVEREIGN AI-OS", accent_color=COLOR_ORANGE):
    """Draw top-left enterprise header badge."""
    font_cat = get_font(FONT_MONO_BOLD, 11)
    font_title = get_font(FONT_SANS_BOLD, 15)
    
    # Header card top-left [36, 32]
    x, y = 36, 32
    draw.rectangle([(x, y), (x + 580, y + 48)], fill=COLOR_BG_BAR, outline=(255, 255, 255, 30), width=1)
    # Accent indicator
    draw.rectangle([(x, y), (x + 4, y + 48)], fill=accent_color)
    
    # Text
    draw.text((x + 14, y + 8), f"INSILOS // {category}", fill=accent_color, font=font_cat)
    draw.text((x + 14, y + 24), title, fill=COLOR_WHITE, font=font_title)

def draw_top_right_status(draw, text, tag="VERIFIED", tag_color=COLOR_GREEN):
    """Draw top-right mission clock and verification badge with dynamic width."""
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
    
    # Outer card
    draw.rectangle([(x, y), (x + total_w, y + 44)], fill=COLOR_BG_BAR, outline=(255, 255, 255, 40), width=1)
    
    # Tag pill (solid green with crisp white text)
    draw.rectangle([(x + 10, y + 10), (x + 10 + w_tag, y + 34)], fill=(16, 185, 129, 200), outline=(52, 211, 153, 255), width=1)
    draw.text((x + 18, y + 13), tag_str, fill=(255, 255, 255, 255), font=font_tag)
    
    # Status text
    draw.text((x + 10 + w_tag + 12, y + 14), text, fill=COLOR_WHITE, font=font_bold)

def draw_bottom_telemetry_bar(draw, telemetry_text, protocol_text, accent_color=COLOR_CYAN):
    """Draw lower telemetry ribbon spanning bottom of viewport."""
    font_mono = get_font(FONT_MONO_BOLD, 12)
    font_proto = get_font(FONT_MONO_REG, 11)
    
    # Bottom Left [36, 1020]
    draw.rectangle([(36, 1016), (720, 1052)], fill=COLOR_BG_BAR, outline=COLOR_BORDER_CYAN, width=1)
    draw.text((50, 1026), telemetry_text, fill=accent_color, font=font_mono)
    
    # Bottom Right [1320, 1016]
    draw.rectangle([(1320, 1016), (1884, 1052)], fill=COLOR_BG_BAR, outline=(255, 255, 255, 30), width=1)
    draw.text((1336, 1027), protocol_text, fill=COLOR_MUTED, font=font_proto)

# =========================================================================
# ACT HUD DEFINITIONS
# =========================================================================

def build_act1_hud():
    """Act 1: Industrial Robotics & SCADA Precision Assembly"""
    img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Primary Target: 6-Axis Robot Gripper / Tool Center Point
    draw_corner_reticle(draw, 700, 220, 1340, 760, COLOR_ORANGE, length=32, width=3)
    draw_center_crosshair(draw, 1020, 490, size=12, color=COLOR_ORANGE)
    draw_hud_badge(draw, 700, 170, "SCADA NODE #04 // AUTONOMOUS NOMINAL", 
                   "POSITION ERR: ±0.018mm | CYCLE: 1.84s", color_accent=COLOR_ORANGE)
    
    # Secondary Target: Right Automated Feeder Jig
    draw_corner_reticle(draw, 1380, 520, 1780, 760, COLOR_CYAN, length=22, width=2)
    draw_center_crosshair(draw, 1580, 640, size=8, color=COLOR_CYAN)
    draw_hud_badge(draw, 1380, 480, "FEEDER CELL #02 // ACTIVE", 
                   "THROUGHPUT: 1,950 UPH | TEMP: 41.2°C", color_accent=COLOR_CYAN, border_color=COLOR_BORDER_CYAN)
    
    # Top Badges
    draw_system_header(draw, "AUTONOMOUS SCADA ROBOTIC WORKCELL", "MANUFACTURING AI-OS", COLOR_ORANGE)
    draw_top_right_status(draw, "MERKLE DAG: STAMPED // 100K TPS", "AIR-GAPPED", COLOR_GREEN)
    
    # Bottom Bars
    draw_bottom_telemetry_bar(draw, "● SCADA TELEMETRY: 2.4 kHz // P99: 8.2ms // 0 CLOUD EGRESS",
                              "OPC-UA / IEC 62443 CERTIFIED // HASH: 0x7E3A9F", COLOR_CYAN)
    
    path = os.path.join(TEMP_HUD_DIR, "hud_act1.png")
    img.save(path)
    return path

def build_act2_hud():
    """Act 2: Cái Mép - Thị Vải Deepwater Maritime Port & Customs IDP"""
    img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Primary Target: Container Bay on vessel
    draw_corner_reticle(draw, 340, 200, 920, 530, COLOR_ORANGE, length=32, width=3)
    draw_center_crosshair(draw, 630, 365, size=12, color=COLOR_ORANGE)
    draw_hud_badge(draw, 340, 150, "CONTAINER BAY #34 // 14,200 TEU", 
                   "VNACCS MANIFEST: 99.8% MATCH // HS 8471 CLEARED", color_accent=COLOR_ORANGE)
    
    # Secondary Target: Quay Crane QC-02
    draw_corner_reticle(draw, 980, 30, 1260, 840, COLOR_CYAN, length=24, width=2)
    draw_center_crosshair(draw, 1120, 435, size=8, color=COLOR_CYAN)
    draw_hud_badge(draw, 1020, 850, "STS QUAY CRANE QC-02 // STS AUTO-DISPATCH", 
                   "LOAD: 41.2T // HOIST SPEED: 1.6 m/s", color_accent=COLOR_CYAN, border_color=COLOR_BORDER_CYAN)
    
    # Top Badges
    draw_system_header(draw, "CÁI MÉP - THỊ VẢI INTERNATIONAL TERMINAL", "MARITIME LOGISTICS HUB", COLOR_ORANGE)
    draw_top_right_status(draw, "LAT: 10.518° N, LON: 107.022° E", "AIS LIVE", COLOR_GREEN)
    
    # Bottom Bars
    draw_bottom_telemetry_bar(draw, "● WCO SAFE FRAMEWORK // STP LATENCY: 1.2s // 0 INLINE BOTTLENECK",
                              "VNACCS/VCIS EDI // CIRCULAR 78/2021/TT-BTC // AUTH OK", COLOR_CYAN)
    
    path = os.path.join(TEMP_HUD_DIR, "hud_act2.png")
    img.save(path)
    return path

def build_act3_hud():
    """Act 3: Enterprise Mission Control NOC & Knowledge Graph"""
    img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Primary Target: Center Video Wall Monitoring Grid
    draw_corner_reticle(draw, 440, 130, 1480, 520, COLOR_ORANGE, length=36, width=3)
    draw_center_crosshair(draw, 960, 325, size=14, color=COLOR_ORANGE)
    draw_hud_badge(draw, 440, 80, "SEMANTIC KNOWLEDGE GRAPH // 1,420,890 ENTITIES", 
                   "OWL/RDF REASONING ENGINE // SUB-SECOND FEDERATED QUERY", color_accent=COLOR_ORANGE)
    
    # Secondary Target: Operator Dispatch Station Left
    draw_corner_reticle(draw, 20, 430, 390, 680, COLOR_CYAN, length=20, width=2)
    draw_center_crosshair(draw, 205, 555, size=8, color=COLOR_CYAN)
    draw_hud_badge(draw, 20, 690, "MISSION CONTROL CONSOLE #01 // NOMINAL", 
                   "MULTI-SITE TELEMETRY // SOC 2 TYPE II AUDIT ACTIVE", color_accent=COLOR_CYAN, border_color=COLOR_BORDER_CYAN)
    
    # Top Badges
    draw_system_header(draw, "UNIFIED ENTERPRISE MISSION CONTROL NOC", "ENTERPRISE COCKPIT", COLOR_ORANGE)
    draw_top_right_status(draw, "AIR-GAPPED ROOT: 0x9B4A...F82C", "SOC 2 TYPE II", COLOR_GREEN)
    
    # Bottom Bars
    draw_bottom_telemetry_bar(draw, "● ON-PREM PIPELINE // 0 DATA RESIDENCY VIOLATIONS // ACTIVE SYNC",
                              "HNSW VECTOR GRAPH 1536-D // CLUSTER HEALTH: 100%", COLOR_CYAN)
    
    path = os.path.join(TEMP_HUD_DIR, "hud_act3.png")
    img.save(path)
    return path

def build_act4_hud():
    """Act 4: Offshore Wind Turbines & Clean Energy Grid"""
    img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Primary Target: Central Offshore Wind Turbine
    draw_corner_reticle(draw, 1020, 100, 1440, 670, COLOR_ORANGE, length=34, width=3)
    draw_center_crosshair(draw, 1230, 385, size=12, color=COLOR_ORANGE)
    draw_hud_badge(draw, 980, 105, "TURBINE EVN-OFFSHORE #03 // 4.2 MW RATED", 
                   "ROTOR: 14.2 RPM | FFT VIBRATION: NORMAL | FTFR: 94.8%", color_accent=COLOR_ORANGE)
    
    # Secondary Target: Far Left Turbine on breakwater
    draw_corner_reticle(draw, 30, 200, 240, 520, COLOR_CYAN, length=20, width=2)
    draw_center_crosshair(draw, 135, 360, size=8, color=COLOR_CYAN)
    draw_hud_badge(draw, 30, 530, "TURBINE EVN-OFFSHORE #01 // YAW: 218°", 
                   "WIND: 11.4 m/s | PITCH: +2.1° | ONLINE", color_accent=COLOR_CYAN, border_color=COLOR_BORDER_CYAN)
    
    # Top Badges
    draw_system_header(draw, "OFFSHORE RENEWABLE CLUSTER & SUBSTATION", "CLEAN ENERGY AI-OS", COLOR_ORANGE)
    draw_top_right_status(draw, "GRID FREQ: 50.02 Hz // 42 NODES", "IEC 61850", COLOR_GREEN)
    
    # Bottom Bars
    draw_bottom_telemetry_bar(draw, "● IEC 61850 SUBSTATION AUTOMATION // PREDICTIVE BEARING LIFE: 18.4Kh",
                              "SCADA DNP3 / MODBUS TCP // CAPACITY FACTOR: 96.2%", COLOR_CYAN)
    
    path = os.path.join(TEMP_HUD_DIR, "hud_act4.png")
    img.save(path)
    return path

# =========================================================================
# VIDEO ENCODING HARNESS
# =========================================================================

def render_act_video(act_num, input_video, start_time, duration, hud_png, output_mp4, output_poster):
    """Render single Act video with HUD overlay and extract high-res poster frame."""
    t0 = time.time()
    print(f"[Act {act_num}] Starting render from {input_video} (ss={start_time}, t={duration})...")
    
    # Filter complex:
    # 1. Scale input to 1920:1080 (force original aspect ratio increase, crop exact 1920:1080)
    # 2. Overlay HUD PNG at 0:0
    # 3. Output 30fps h264 yuv420p with faststart, exactly 8.0 seconds
    cmd_video = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", input_video,
        "-i", hud_png,
        "-filter_complex",
        "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30[v0];[v0][1:v]overlay=0:0[vout]",
        "-map", "[vout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        "-t", str(duration),
        "-movflags", "+faststart",
        output_mp4
    ]
    
    res = subprocess.run(cmd_video, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        print(f"[Act {act_num}] ERROR rendering video: {res.stderr.decode('utf-8', errors='ignore')[-500:]}")
        return False
        
    # Extract 1st frame as WebP poster (at ss=0.5s for motion stability)
    cmd_poster = [
        "ffmpeg", "-y",
        "-ss", "00:00:00.5",
        "-i", output_mp4,
        "-vframes", "1",
        "-c:v", "libwebp",
        "-lossless", "0",
        "-q:v", "90",
        output_poster
    ]
    res_p = subprocess.run(cmd_poster, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res_p.returncode != 0:
        print(f"[Act {act_num}] WARNING creating poster: {res_p.stderr.decode('utf-8', errors='ignore')[-300:]}")
    
    elapsed = time.time() - t0
    size_mb = os.path.getsize(output_mp4) / (1024 * 1024)
    print(f"[Act {act_num}] COMPLETE in {elapsed:.2f}s! Video Size: {size_mb:.2f} MB -> {output_mp4}")
    return True

def run_task(args):
    return render_act_video(*args)

def main():
    print("=" * 70)
    print("INSILOS INDUSTRIAL AI: C3.AI-STYLE PEXELS VIDEO PRODUCTION HARNESS")
    print("=" * 70)
    
    # 1. Build 4 HUD PNGs
    print("\n[Step 1/3] Generating 4 Custom C3.ai Telemetry HUD Overlays...")
    huds = {
        1: build_act1_hud(),
        2: build_act2_hud(),
        3: build_act3_hud(),
        4: build_act4_hud()
    }
    for act, path in huds.items():
        print(f"  ✓ Act {act} HUD: {path} ({os.path.getsize(path):,} bytes)")
        
    # 2. Prepare Task List
    tasks = [
        (
            1,
            os.path.join(RAW_FOOTAGE_DIR, "act1_robot100.mp4"),
            "00:00:01",
            8.0,
            huds[1],
            os.path.join(VIDEO_OUT_DIR, "hero_act1_opt.mp4"),
            os.path.join(VIDEO_OUT_DIR, "hero_act1_poster.webp")
        ),
        (
            2,
            os.path.join(RAW_FOOTAGE_DIR, "act2_caimep_port.mp4"),
            "00:00:03",
            8.0,
            huds[2],
            os.path.join(VIDEO_OUT_DIR, "hero_act2_opt.mp4"),
            os.path.join(VIDEO_OUT_DIR, "hero_act2_poster.webp")
        ),
        (
            3,
            os.path.join(RAW_FOOTAGE_DIR, "act3_noc.mp4"),
            "00:00:02",
            8.0,
            huds[3],
            os.path.join(VIDEO_OUT_DIR, "hero_act3_opt.mp4"),
            os.path.join(VIDEO_OUT_DIR, "hero_act3_poster.webp")
        ),
        (
            4,
            os.path.join(RAW_FOOTAGE_DIR, "act4_offshore.mp4"),
            "00:00:03",
            8.0,
            huds[4],
            os.path.join(VIDEO_OUT_DIR, "hero_act4_opt.mp4"),
            os.path.join(VIDEO_OUT_DIR, "hero_act4_poster.webp")
        )
    ]
    
    # 3. Execute in Parallel (Harness Optimization)
    print("\n[Step 2/3] Executing Parallel Render with ProcessPoolExecutor (4 workers)...")
    start_total = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(run_task, tasks))
        
    total_elapsed = time.time() - start_total
    print(f"\n[Step 3/3] All Renders Finished in {total_elapsed:.2f} seconds!")
    
    # Summary Check
    success = all(results)
    if success:
        print("\nSUCCESS: All 4 Hero Act Videos and Posters generated successfully!")
        for t in tasks:
            act_num = t[0]
            v_path = t[5]
            p_path = t[6]
            v_size = os.path.getsize(v_path) / (1024 * 1024)
            p_size = os.path.getsize(p_path) / 1024
            print(f"  Act {act_num}: Video {v_size:.2f} MB ({v_path}) | Poster {p_size:.1f} KB ({p_path})")
    else:
        print("\nERROR: One or more video tasks failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
