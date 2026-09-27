#!/usr/bin/env python3
"""
Fetch Curated High-Impact Enterprise Industrial Photography from Pexels
for Insilos C3.ai Enterprise Redesign.
"""

import os
import io
import urllib.request
import urllib.parse
import json
from PIL import Image

API_KEYS = [
    "OQZQERHkBgdiTKi43vFU4gfOCluV32tNhJMueofbl0wTwurnmFxECs9L",
    "afF23F6EM9CarLV6KZwOuT2V70bBTm6buPWt0hjx81FTPqFm8RWiP0GI",
    "Wo0Wx2nEpYdCl02Ya7iyD3cvzIWUqNAtVaeupS2V7nA0DX7b4TN3rlL2",
]

TARGET_DIR = "/home/zen/O20/enterprise/insilos_website/static/src/img/c3ai"
os.makedirs(TARGET_DIR, exist_ok=True)

CURATED_SHOTS = [
    # Hero & Core Panoramas
    {
        "name": "c3ai_hero_robotics",
        "query": "industrial robotic arm factory automation",
        "description": "Smart factory robotic arms precision welding"
    },
    {
        "name": "c3ai_hero_energy",
        "query": "offshore wind turbine sunset energy",
        "description": "Clean energy offshore turbines at dusk"
    },
    {
        "name": "c3ai_hero_maritime",
        "query": "container ship cargo port crane sunset",
        "description": "Deep-water container vessel under gantry cranes"
    },
    {
        "name": "c3ai_hero_datacenter",
        "query": "server room data center blue lights",
        "description": "High density supercomputer data center"
    },
    {
        "name": "c3ai_hero_control_room",
        "query": "control room screens operations center",
        "description": "High-tech mission control operations center"
    },
    
    # 4 Core Pillar Cards & Platform Bento
    {
        "name": "c3ai_card_idp",
        "query": "warehouse logistics automation barcode scanner",
        "description": "Intelligent automated freight logistics facility"
    },
    {
        "name": "c3ai_card_knowledge_graph",
        "query": "abstract technology glowing network data",
        "description": "Enterprise unified semantic graph topology"
    },
    {
        "name": "c3ai_card_supply_chain",
        "query": "shipping cargo container terminal aerial port",
        "description": "Intermodal global supply chain container yard"
    },
    {
        "name": "c3ai_card_fsm",
        "query": "engineer tablet inspecting machinery factory",
        "description": "Field service mobility engineer inspecting turbine"
    },
    
    # Industry & Application Showcases
    {
        "name": "c3ai_card_predictive_maint",
        "query": "airplane jet engine maintenance mechanic",
        "description": "Aerospace propulsion maintenance & reliability"
    },
    {
        "name": "c3ai_card_oil_gas",
        "query": "petrochemical plant refinery night lights",
        "description": "Downstream refinery process optimization"
    },
    {
        "name": "c3ai_card_smart_grid",
        "query": "power plant transmission tower high voltage",
        "description": "Grid reliability & distributed energy resources"
    },
    {
        "name": "c3ai_card_cleanroom",
        "query": "semiconductor cleanroom manufacturing silicon wafer",
        "description": "Semiconductor fab & pharmaceutical cleanroom"
    },
    {
        "name": "c3ai_card_automotive",
        "query": "car manufacturing assembly line welding robots",
        "description": "Automotive body assembly robotics"
    },
    {
        "name": "c3ai_card_soc_security",
        "query": "cybersecurity operations center monitors security analyst",
        "description": "Zero-trust SOC cyber surveillance console"
    },
    {
        "name": "c3ai_card_financial",
        "query": "modern glass office building skyscraper night architecture",
        "description": "Global enterprise headquarters and financial center"
    },
    {
        "name": "c3ai_card_esg",
        "query": "solar panels green energy landscape mountains",
        "description": "Enterprise decarbonization & ESG telemetry"
    },
    {
        "name": "c3ai_card_mining",
        "query": "large mining dump truck quarry heavy equipment",
        "description": "Autonomous heavy machinery and extractive mining"
    },
]

def search_and_download():
    current_key_idx = 0
    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    for shot in CURATED_SHOTS:
        out_path = os.path.join(TARGET_DIR, f"{shot['name']}.webp")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 40000:
            print(f"⏩ [EXISTS] {shot['name']}.webp ({os.path.getsize(out_path)} bytes)")
            continue

        print(f"🔍 Searching Pexels for: '{shot['query']}'...")
        query_encoded = urllib.parse.quote(shot['query'])
        url = f"https://api.pexels.com/v1/search?query={query_encoded}&per_page=5&orientation=landscape"
        
        success = False
        attempts = 0
        while not success and attempts < len(API_KEYS):
            api_key = API_KEYS[current_key_idx]
            headers = {
                "Authorization": api_key,
                "User-Agent": ua
            }
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    photos = data.get("photos", [])
                    if not photos:
                        print(f"  ❌ No photos found for '{shot['query']}'")
                        break
                    
                    # Choose a high-res photo
                    photo = photos[0]
                    img_url = photo["src"].get("large2x") or photo["src"].get("large") or photo["src"].get("original")
                    photographer = photo.get("photographer", "Pexels")
                    print(f"  📥 Downloading photo by {photographer}...")

                    img_req = urllib.request.Request(img_url, headers={"User-Agent": ua})
                    with urllib.request.urlopen(img_req, timeout=25) as img_resp:
                        img_bytes = img_resp.read()
                        img = Image.open(io.BytesIO(img_bytes))
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        
                        # Resize to standard web-optimized 1600px width (or 1920px for heroes)
                        max_w = 1920 if "hero" in shot["name"] else 1280
                        w, h = img.size
                        if w > max_w:
                            new_h = int(h * (max_w / w))
                            img = img.resize((max_w, new_h), Image.Resampling.LANCZOS)

                        img.save(out_path, "WEBP", quality=86, method=6)
                        print(f"  ✅ Saved: {shot['name']}.webp ({os.path.getsize(out_path)} bytes, {img.size[0]}x{img.size[1]})")
                        success = True
            except Exception as e:
                print(f"  ⚠️ Error with key {current_key_idx}: {e}")
                current_key_idx = (current_key_idx + 1) % len(API_KEYS)
                attempts += 1

if __name__ == "__main__":
    search_and_download()
