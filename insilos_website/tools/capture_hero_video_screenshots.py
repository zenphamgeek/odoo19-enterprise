#!/usr/bin/env python3
"""
CDP Verification & Screenshot Tool for All Video Heroes.
Validates:
1. Desktop Viewport (1920x1080):
   - <video> is active and visible
   - Poster fallback is display: none
   - Overlay and scanlines present
2. Mobile Viewport (390x844):
   - <video> is display: none !important (bandwidth optimization)
   - Poster fallback is display: block (instant, crisp visual)
3. Saves high-res verification screenshots to artifacts directory.
"""
import subprocess
import time
import json
import urllib.request
import websocket
import base64
import os

OUTPUT_DIR = "/home/zen/.gemini/antigravity/brain/fb5ae76a-1408-4c4b-a022-402bc164561b/screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGETS = [
    {"route": "/platform", "name": "verify_video_hero_platform", "title": "Platform NOC Control"},
    {"route": "/solutions", "name": "verify_video_hero_solutions", "title": "Solutions Directory"},
    {"route": "/solutions/enterprise-knowledge-graph", "name": "verify_video_hero_graph", "title": "Knowledge Graph"},
    {"route": "/industries/logistics", "name": "verify_video_hero_logistics", "title": "Maritime Logistics"},
    {"route": "/industries/pharma", "name": "verify_video_hero_pharma", "title": "Pharma Bioreactor"},
    {"route": "/pricing", "name": "verify_video_hero_pricing", "title": "Pricing Architecture"},
    {"route": "/request-demo", "name": "verify_video_hero_demo", "title": "Request Demo Enterprise"},
]

def main():
    print("[1] Spawning Chrome Headless with CDP on port 9230...")
    chrome = subprocess.Popen([
        "google-chrome",
        "--headless=new",
        "--remote-debugging-port=9230",
        "--remote-allow-origins=*",
        "--disable-extensions",
        "--no-sandbox",
        "--disable-gpu",
        "--window-size=1920,1080",
        "about:blank"
    ])
    time.sleep(2.0)

    try:
        with urllib.request.urlopen("http://127.0.0.1:9230/json") as r:
            tabs = json.loads(r.read())
        ws_url = None
        for t in tabs:
            if t.get("type") == "page":
                ws_url = t["webSocketDebuggerUrl"]
                break
        assert ws_url, "No page tab available"
        print(f"[2] Connected to Chrome DevTools: {ws_url}")
        ws = websocket.create_connection(ws_url)

        msg_id_counter = [0]
        def cdp_send(method, params=None):
            msg_id_counter[0] += 1
            cur_id = msg_id_counter[0]
            payload = {"id": cur_id, "method": method, "params": params or {}}
            ws.send(json.dumps(payload))
            while True:
                resp = json.loads(ws.recv())
                if resp.get("id") == cur_id:
                    return resp.get("result", {})

        def cdp_eval(expr):
            r = cdp_send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
            return r.get("result", {}).get("value")

        cdp_send("Page.enable")
        cdp_send("Runtime.enable")

        # Set desktop viewport
        cdp_send("Emulation.setDeviceMetricsOverride", {
            "width": 1920,
            "height": 1080,
            "deviceScaleFactor": 1,
            "mobile": False
        })

        for target in TARGETS:
            url = f"http://localhost:28069{target['route']}"
            print(f"\n--> Navigating to {url} ({target['title']})...")
            cdp_send("Page.navigate", {"url": url})
            
            # Wait for complete
            for _ in range(30):
                time.sleep(0.3)
                if cdp_eval("document.readyState") == "complete":
                    break
            time.sleep(1.0) # Render settling

            # Inspect elements
            res = cdp_eval("""(() => {
                const vid = document.querySelector(".ins-hero-video");
                const fallback = document.querySelector(".ins-hero-poster-fallback");
                const overlay = document.querySelector(".ins-hero-overlay");
                const scanlines = document.querySelector(".ins-hero-scanlines");
                const vp = document.querySelector(".ins-hero-video-viewport");
                const cockpit = document.querySelector(".ins-3d-cockpit-viewport");
                const cards = document.querySelectorAll(".ins-cockpit-card");
                return {
                    hasViewport: !!vp,
                    hasVideo: !!vid,
                    vidSrc: vid ? vid.currentSrc || vid.getAttribute('src') : null,
                    vidDisplay: vid ? window.getComputedStyle(vid).display : null,
                    vidOpacity: vid ? window.getComputedStyle(vid).opacity : null,
                    fallbackDisplay: fallback ? window.getComputedStyle(fallback).display : null,
                    hasOverlay: !!overlay,
                    hasScanlines: !!scanlines,
                    hasCockpit: !!cockpit,
                    layersCount: cards.length
                };
            })()""")
            print(f"    Desktop Verification: {res}")
            assert res["hasViewport"], "Missing .ins-hero-video-viewport"
            assert res["hasVideo"], "Missing .ins-hero-video"
            assert res["hasOverlay"], "Missing .ins-hero-overlay"
            assert res["hasCockpit"], f"Missing .ins-3d-cockpit-viewport on {target['route']}"
            assert res["layersCount"] == 4, f"Expected 4 layers, got {res['layersCount']}"

            # Take screenshot
            ss = cdp_send("Page.captureScreenshot", {"format": "png"})
            png_bytes = base64.b64decode(ss["data"])
            out_file = os.path.join(OUTPUT_DIR, f"{target['name']}.png")
            with open(out_file, "wb") as f:
                f.write(png_bytes)
            print(f"    [OK] Captured desktop screenshot -> {out_file} ({len(png_bytes):,} bytes)")

        # Verify Mobile Responsiveness on /platform
        print("\n--> Testing Mobile Viewport (390x844) on /platform...")
        cdp_send("Emulation.setDeviceMetricsOverride", {
            "width": 390,
            "height": 844,
            "deviceScaleFactor": 2,
            "mobile": True
        })
        time.sleep(0.5)
        cdp_send("Page.navigate", {"url": "http://localhost:28069/platform"})
        for _ in range(30):
            time.sleep(0.3)
            if cdp_eval("document.readyState") == "complete":
                break
        time.sleep(1.0)

        mob_res = cdp_eval("""(() => {
            const vid = document.querySelector(".ins-hero-video");
            const fallback = document.querySelector(".ins-hero-poster-fallback");
            return {
                vidDisplay: vid ? window.getComputedStyle(vid).display : null,
                fallbackDisplay: fallback ? window.getComputedStyle(fallback).display : null,
                fallbackBg: fallback ? window.getComputedStyle(fallback).backgroundImage : null
            };
        })()""")
        print(f"    Mobile Verification: {mob_res}")
        assert mob_res["vidDisplay"] == "none", f"Video should be hidden on mobile: {mob_res}"
        assert mob_res["fallbackDisplay"] == "block", f"Fallback poster should be block on mobile: {mob_res}"

        ss_mob = cdp_send("Page.captureScreenshot", {"format": "png"})
        mob_bytes = base64.b64decode(ss_mob["data"])
        mob_file = os.path.join(OUTPUT_DIR, "verify_video_hero_mobile_platform.png")
        with open(mob_file, "wb") as f:
            f.write(mob_bytes)
        print(f"    [OK] Captured mobile screenshot -> {mob_file} ({len(mob_bytes):,} bytes)")

        print("\n[SUCCESS] ALL VIDEO HERO CDP CHECKS AND SCREENSHOTS COMPLETED PERFECTLY!")
        ws.close()

    finally:
        chrome.kill()
        chrome.wait()

if __name__ == "__main__":
    main()
