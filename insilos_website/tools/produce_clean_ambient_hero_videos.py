#!/usr/bin/env python3
"""
INNORIA / INSILOS PRODUCTION ENGINE: CLEAN AMBIENT HERO VIDEO PRODUCER
Generates 100% text-free, cinematic ambient industrial background video loops
and WebP poster frames. Eliminates all burned-in HUD telemetry, titles, and
competing text layers to guarantee zero text collision with foreground HTML typography.

Harness Optimization: Parallel ProcessPoolExecutor rendering with FFmpeg.
"""

import os
import sys
import time
import subprocess
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_OUT_DIR = os.path.join(BASE_DIR, "static", "src", "video")
RAW_DIR = "/tmp/pexels_clean_raw"

os.makedirs(VIDEO_OUT_DIR, exist_ok=True)

# Clean footage catalog mapped to thematic enterprise modes
VIDEO_JOBS = [
    # --- 4 Dedicated Innoria Hero Modes ---
    {
        "out_name": "hero_innoria_cloud_ambient",
        "raw_source": os.path.join(RAW_DIR, "act3_datacenter.mp4"),
        "ss": "00:00:02",
        "duration": 8.0,
        "description": "Mode 0: Cloud & Data Fabric (Clean Data Center / Network Fabric)"
    },
    {
        "out_name": "hero_innoria_ai_ambient",
        "raw_source": os.path.join(RAW_DIR, "act1_robotics.mp4"),
        "ss": "00:00:01",
        "duration": 8.0,
        "description": "Mode 1: Autonomous AI Swarm (Clean Precision Robotic Automation)"
    },
    {
        "out_name": "hero_innoria_erp_ambient",
        "raw_source": os.path.join(RAW_DIR, "act2_port.mp4"),
        "ss": "00:00:04",
        "duration": 8.0,
        "description": "Mode 2: Intelligent ERP (Clean Maritime Port & Supply Chain)"
    },
    {
        "out_name": "hero_innoria_security_ambient",
        "raw_source": os.path.join(RAW_DIR, "act4_energy.mp4"),
        "ss": "00:00:03",
        "duration": 8.0,
        "description": "Mode 3: Sovereign Trust & Security (Clean Offshore Energy Infrastructure)"
    },

    # --- Clean Drop-in Replacements for General Routes ---
    {
        "out_name": "hero_platform_opt",
        "raw_source": os.path.join(RAW_DIR, "act3_datacenter.mp4"),
        "ss": "00:00:02",
        "duration": 8.0,
        "description": "Platform Hero: Clean Data Center Flow"
    },
    {
        "out_name": "hero_solutions_opt",
        "raw_source": os.path.join(RAW_DIR, "act1_robotics.mp4"),
        "ss": "00:00:01",
        "duration": 8.0,
        "description": "Solutions Hero: Clean Robotic Workcell"
    },
    {
        "out_name": "hero_act1_opt",
        "raw_source": os.path.join(RAW_DIR, "act1_robotics.mp4"),
        "ss": "00:00:01",
        "duration": 8.0,
        "description": "Act 1: Clean Precision Robotics"
    },
    {
        "out_name": "hero_act2_opt",
        "raw_source": os.path.join(RAW_DIR, "act2_port.mp4"),
        "ss": "00:00:04",
        "duration": 8.0,
        "description": "Act 2: Clean Maritime Deepwater Port"
    },
    {
        "out_name": "hero_act3_opt",
        "raw_source": os.path.join(RAW_DIR, "act3_datacenter.mp4"),
        "ss": "00:00:02",
        "duration": 8.0,
        "description": "Act 3: Clean Mission Control NOC"
    },
    {
        "out_name": "hero_act4_opt",
        "raw_source": os.path.join(RAW_DIR, "act4_energy.mp4"),
        "ss": "00:00:03",
        "duration": 8.0,
        "description": "Act 4: Clean Offshore Wind Energy"
    },
    {
        "out_name": "hero_industries_opt",
        "raw_source": os.path.join(RAW_DIR, "act1_robotics.mp4"),
        "ss": "00:00:02",
        "duration": 8.0,
        "description": "Industries: Clean Industrial Automation"
    },
    {
        "out_name": "hero_logistics_opt",
        "raw_source": os.path.join(RAW_DIR, "act2_port.mp4"),
        "ss": "00:00:08",
        "duration": 8.0,
        "description": "Logistics: Clean Container Terminal"
    },
    {
        "out_name": "hero_energy_opt",
        "raw_source": os.path.join(RAW_DIR, "act4_energy.mp4"),
        "ss": "00:00:03",
        "duration": 8.0,
        "description": "Energy: Clean Wind Turbine Grid"
    },
    {
        "out_name": "hero_resources_opt",
        "raw_source": os.path.join(RAW_DIR, "act3_datacenter.mp4"),
        "ss": "00:00:02",
        "duration": 8.0,
        "description": "Resources: Clean Data Architecture"
    },
    {
        "out_name": "hero_pricing_opt",
        "raw_source": os.path.join(RAW_DIR, "act3_datacenter.mp4"),
        "ss": "00:00:04",
        "duration": 8.0,
        "description": "Pricing: Clean Cloud Infrastructure"
    },
    {
        "out_name": "hero_about_opt",
        "raw_source": os.path.join(RAW_DIR, "act3_datacenter.mp4"),
        "ss": "00:00:01",
        "duration": 8.0,
        "description": "About: Clean Engineering DNA"
    },
    {
        "out_name": "hero_demo_opt",
        "raw_source": os.path.join(RAW_DIR, "act3_datacenter.mp4"),
        "ss": "00:00:01",
        "duration": 8.0,
        "description": "Demo: Clean Mission Control"
    }
]

def render_clean_video(job):
    out_name = job["out_name"]
    raw_source = job["raw_source"]
    ss = job.get("ss", "00:00:01")
    duration = job.get("duration", 8.0)
    desc = job.get("description", out_name)

    mp4_out = os.path.join(VIDEO_OUT_DIR, f"{out_name}.mp4")
    webp_out = os.path.join(VIDEO_OUT_DIR, f"{out_name}_poster.webp")

    t0 = time.time()
    if not os.path.exists(raw_source):
        print(f"❌ Missing raw footage for {out_name}: {raw_source}")
        return False

    # Filter: Scale + Center-Crop to exact 1920:1080 + 30fps + Cinematic Ambient Tone
    # No HUD overlays, no text, no reticles
    vf = (
        "scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,"
        "fps=30,"
        "eq=brightness=-0.06:contrast=1.10:saturation=1.12"
    )

    cmd_mp4 = [
        "ffmpeg", "-y",
        "-ss", ss,
        "-i", raw_source,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-an",
        "-t", str(duration),
        "-movflags", "+faststart",
        mp4_out
    ]

    res = subprocess.run(cmd_mp4, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0:
        print(f"❌ FFmpeg error on {out_name}")
        return False

    # Extract high-res WebP poster frame at ss=0.5s for instant paint
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

    dur = time.time() - t0
    size_mb = os.path.getsize(mp4_out) / (1024 * 1024)
    poster_kb = os.path.getsize(webp_out) / 1024 if os.path.exists(webp_out) else 0
    print(f"  ✓ {out_name:30} in {dur:4.1f}s | {size_mb:4.1f}MB | Poster: {poster_kb:4.0f}KB | {desc}")
    return True

def main():
    print("=" * 80)
    print("INNORIA CLEAN AMBIENT HERO VIDEO PRODUCTION (PARALLEL HARNESS)")
    print(f"Destination: {VIDEO_OUT_DIR}")
    print(f"Total Videos to Produce: {len(VIDEO_JOBS)}")
    print("=" * 80)

    t_start = time.time()
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(render_clean_video, VIDEO_JOBS))

    total_time = time.time() - t_start
    success = sum(1 for r in results if r)
    print("=" * 80)
    print(f"🏆 COMPLETE: {success}/{len(VIDEO_JOBS)} Clean Ambient Videos Produced in {total_time:.1f}s!")
    print("=" * 80)

if __name__ == "__main__":
    main()
