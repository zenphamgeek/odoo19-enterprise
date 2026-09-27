import subprocess, time, json, urllib.request, websocket, base64

def run_suite():
    print("[1] Launching Headless Chrome with CDP...")
    chrome = subprocess.Popen([
        "google-chrome",
        "--headless=new",
        "--remote-debugging-port=9229",
        "--remote-allow-origins=*",
        "--disable-extensions",
        "--no-sandbox",
        "--disable-gpu",
        "--window-size=1920,1080",
        "http://localhost:28069/"
    ])
    time.sleep(2.5)

    try:
        with urllib.request.urlopen("http://127.0.0.1:9229/json") as r:
            tabs = json.loads(r.read())
        ws_url = None
        for t in tabs:
            if t.get("type") == "page" and "localhost:28069" in t.get("url", ""):
                ws_url = t["webSocketDebuggerUrl"]
                break
        if not ws_url:
            for t in tabs:
                if t.get("type") == "page":
                    ws_url = t["webSocketDebuggerUrl"]
                    break
        assert ws_url, f"No page tab found in {tabs}"
        print("Connected to Page WS:", ws_url)
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

        print("Waiting for page readyState == complete...")
        for _ in range(25):
            st = cdp_eval("document.readyState")
            if st == "complete":
                break
            time.sleep(0.5)

        # Allow scripts to initialize
        time.sleep(1.5)

        # 1. Verify Hero 3D Cockpit Deck initial state
        print("\n[TEST 1] Verifying 3D Isometric Cockpit Deck...")
        val = cdp_eval("""(() => {
            const deck = document.getElementById("ins_3d_cockpit_deck");
            if (!deck) return { error: "No deck" };
            const card1 = deck.querySelector("[data-layer='1']");
            const tap1 = document.querySelector(".ins-bus-tap-1");
            const branch1 = document.querySelector(".ins-bus-branch-1");
            const dock1 = document.querySelector(".ins-bus-dock-1");
            const body = deck.querySelector(".ins-cockpit-body");
            return {
                deckFound: !!deck,
                card1Active: card1.classList.contains("ins-act-highlight"),
                tap1Active: tap1 && tap1.classList.contains("active"),
                branch1Active: branch1 && branch1.classList.contains("active"),
                dock1Active: dock1 && dock1.classList.contains("active"),
                bodyPaddingLeft: window.getComputedStyle(body).paddingLeft,
                card1Transform: window.getComputedStyle(card1).transform
            };
        })()""")
        print("  • Hero 3D Deck Initial State:", val)
        assert val.get("deckFound"), f"Deck not found: {val}"
        assert val["card1Active"], "Card 1 should be highlighted"
        assert val["tap1Active"], "Bus Tap 1 should be active"
        assert val["branch1Active"], "Bus Branch 1 should be active"
        assert val["dock1Active"], "Bus Dock 1 should be active"
        print("  ✅ [PASS] 3D Hero Cockpit with Signal Bus Tap/Branch/Dock is operational!")

        # Screenshot Hero ISO
        scr = cdp_send("Page.captureScreenshot", {"format": "png"})
        with open("/tmp/verify_hero_3d_iso.png", "wb") as f:
            f.write(base64.b64decode(scr["data"]))
        print("  📸 Captured /tmp/verify_hero_3d_iso.png")

        # 2. Click Layer 2 Card to test Act synchronization
        print("\n[TEST 2] Clicking Layer 2 Card (Act 2 Synchronization)...")
        cdp_eval("document.querySelector(\"[data-layer='2']\").click()")
        time.sleep(0.8)
        val2 = cdp_eval("""(() => {
            const card2 = document.querySelector("[data-layer='2']");
            const tap2 = document.querySelector(".ins-bus-tap-2");
            const branch2 = document.querySelector(".ins-bus-branch-2");
            const dock2 = document.querySelector(".ins-bus-dock-2");
            return {
                card2Active: card2.classList.contains("ins-act-highlight"),
                tap2Active: tap2 && tap2.classList.contains("active"),
                branch2Active: branch2 && branch2.classList.contains("active"),
                dock2Active: dock2 && dock2.classList.contains("active"),
                animName: window.getComputedStyle(card2).animationName
            };
        })()""")
        print("  • Act 2 Sync State:", val2)
        assert val2["card2Active"], "Card 2 should be active"
        assert val2["tap2Active"], "Bus Tap 2 should be active"
        assert val2["branch2Active"], "Bus Branch 2 should be active"
        assert val2["dock2Active"], "Bus Dock 2 should be active"
        print("  ✅ [PASS] Act 2 synchronized across Cards, Signal Bus Spine, Branch & Dock!")

        scr = cdp_send("Page.captureScreenshot", {"format": "png"})
        with open("/tmp/verify_hero_3d_act2.png", "wb") as f:
            f.write(base64.b64decode(scr["data"]))
        print("  📸 Captured /tmp/verify_hero_3d_act2.png")

        # 3. Toggle Exploded Mode
        print("\n[TEST 3] Toggling Exploded Mode...")
        cdp_eval("document.getElementById('btn_mode_exploded').click()")
        time.sleep(0.8)
        val3 = cdp_eval("""(() => {
            const deck = document.getElementById("ins_3d_cockpit_deck");
            const card2 = document.querySelector("[data-layer='2']");
            return {
                isExploded: deck.classList.contains("ins-exploded-mode"),
                card2Active: card2.classList.contains("ins-act-highlight"),
                card2Anim: window.getComputedStyle(card2).animationName,
                card2BoxShadow: window.getComputedStyle(card2).boxShadow
            };
        })()""")
        print("  • Exploded Mode State:", val3)
        assert val3["isExploded"], "Deck should have ins-exploded-mode class"
        assert val3["card2Active"], "Card 2 should remain active in exploded mode"
        assert "ins-3d-breathe-exp" in val3["card2Anim"], f"Card 2 should animate in exploded mode, got {val3['card2Anim']}"
        print("  ✅ [PASS] Exploded mode active and layer breathing correctly without specificity conflict!")

        scr = cdp_send("Page.captureScreenshot", {"format": "png"})
        with open("/tmp/verify_hero_exploded.png", "wb") as f:
            f.write(base64.b64decode(scr["data"]))
        print("  📸 Captured /tmp/verify_hero_exploded.png")

        # 4. Test Mouse Parallax
        print("\n[TEST 4] Testing 3D Mouse Parallax via CSS Variables...")
        val4 = cdp_eval("""(() => {
            const viewport = document.querySelector(".ins-3d-cockpit-viewport");
            const deck = document.getElementById("ins_3d_cockpit_deck");
            viewport.dispatchEvent(new MouseEvent("mousemove", { clientX: 1300, clientY: 450, bubbles: true }));
            return {
                tiltX: deck.style.getPropertyValue("--tilt-x"),
                tiltY: deck.style.getPropertyValue("--tilt-y")
            };
        })()""")
        print("  • Tilt Computed Variables:", val4)
        assert val4["tiltX"] and val4["tiltY"], "Tilt CSS variables should be set by mousemove"
        print("  ✅ [PASS] Mouse parallax smoothly updates --tilt-x and --tilt-y!")

        # 5. Scroll to Code Studio and test Deployment Mode Switch
        print("\n[TEST 5] Testing Code Studio Deployment Mode Toggle...")
        cdp_eval("document.getElementById('insilos_code_studio').scrollIntoView({ behavior: 'instant', block: 'center' })")
        time.sleep(0.6)

        # Switch to cloud
        val5 = cdp_eval("""(() => {
            const cloudBtn = document.querySelector(".ins-code-mode-btn[data-mode='cloud']");
            cloudBtn.click();
            const codeText = document.querySelector(".ins-code-pane.active pre").innerText;
            const env = document.querySelector(".ins-code-env-badge").innerText;
            return {
                cloudBtnActive: cloudBtn.classList.contains("active"),
                envBadge: env,
                hasFederated: codeText.includes("FederatedMesh") || codeText.includes("APAC_FEDERATED_CLOUD"),
                hasEdgeGw: codeText.includes("edge-gw.insilos.io")
            };
        })()""")
        print("  • Cloud Deployment Switch Result:", val5)
        assert val5["cloudBtnActive"], "Cloud button should be active"
        assert val5["hasEdgeGw"], "Code should update to edge-gw.insilos.io endpoint"
        print("  ✅ [PASS] Code Studio dynamically updates code content when switching to Hybrid Cloud!")

        # Switch to airgap
        val6 = cdp_eval("""(() => {
            const airgapBtn = document.querySelector(".ins-code-mode-btn[data-mode='airgap']");
            airgapBtn.click();
            const codeText = document.querySelector(".ins-code-pane.active pre").innerText;
            const env = document.querySelector(".ins-code-env-badge").innerText;
            return {
                airgapBtnActive: airgapBtn.classList.contains("active"),
                envBadge: env,
                hasMerkle: codeText.includes("MerkleAirGapValidator"),
                hasLocalOpc: codeText.includes("10.24.8.1:4840")
            };
        })()""")
        print("  • Airgap Deployment Switch Result:", val6)
        assert val6["airgapBtnActive"], "Airgap button should be active"
        assert val6["hasLocalOpc"], "Code should update to local 10.24.8.1:4840 endpoint"
        print("  ✅ [PASS] Code Studio dynamically restores on-prem code when switching to Air-Gapped!")

        # 6. Test Pipeline Execution and Stage Flow Indicator
        print("\n[TEST 6] Triggering Code Studio Live Execution...")
        cdp_eval("document.querySelector('.ins-run-pipeline-btn').click()")

        time.sleep(0.4)
        val7 = cdp_eval("""(() => {
            const status = document.querySelector(".ins-exec-status-badge").innerText;
            const activeStages = document.querySelectorAll(".ins-stage-node.active").length;
            const logs = document.querySelectorAll(".ins-log-line").length;
            return { status, activeStages, logs };
        })()""")
        print("  • Running State (at 400ms):", val7)
        assert val7["status"] == "RUNNING...", f"Expected RUNNING..., got {val7['status']}"
        assert val7["logs"] > 0, "Log stream should have lines"

        scr = cdp_send("Page.captureScreenshot", {"format": "png"})
        with open("/tmp/verify_code_studio_running.png", "wb") as f:
            f.write(base64.b64decode(scr["data"]))
        print("  📸 Captured /tmp/verify_code_studio_running.png")

        # Wait for execution completion
        time.sleep(1.2)
        val8 = cdp_eval("""(() => {
            const status = document.querySelector(".ins-exec-status-badge").innerText;
            const activeStages = document.querySelectorAll(".ins-stage-node.active").length;
            const logs = Array.from(document.querySelectorAll(".ins-log-line")).map(l => l.innerText);
            const btnText = document.querySelector(".ins-run-pipeline-btn").innerText;
            return { status, activeStages, totalLogs: logs.length, btnText, lastLog: logs[logs.length - 1] };
        })()""")
        print("  • Completed State:", val8)
        assert "COMPLETED" in val8["status"], f"Expected COMPLETED status, got {val8['status']}"
        assert val8["totalLogs"] == 6, f"Expected exactly 6 logs without duplicates, got {val8['totalLogs']}"
        assert val8["activeStages"] == 4, f"Expected all 4 stages active, got {val8['activeStages']}"
        assert "REPLAY" in val8["btnText"], f"Expected REPLAY in button text, got {val8['btnText']}"
        print("  ✅ [PASS] Pipeline execution completed with all 4 stages illuminated and 0 duplicates!")

        scr = cdp_send("Page.captureScreenshot", {"format": "png"})
        with open("/tmp/verify_code_studio_completed.png", "wb") as f:
            f.write(base64.b64decode(scr["data"]))
        print("  📸 Captured /tmp/verify_code_studio_completed.png")

        ws.close()
        print("\n" + "="*65)
        print("🎉 ALL DEEP INTERACTION AND VERIFICATION TESTS PASSED 100%!")
        print("="*65)

    finally:
        chrome.kill()

if __name__ == "__main__":
    run_suite()
