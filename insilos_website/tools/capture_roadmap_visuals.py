import asyncio
import os
from playwright.async_api import async_playwright

async def capture_roadmap():
    output_dir = "/home/zen/.gemini/antigravity/brain/fb5ae76a-1408-4c4b-a022-402bc164561b/screenshots"
    os.makedirs(output_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 2400})
        page = await context.new_page()
        
        print("Navigating to http://localhost:28069/ ...")
        await page.goto("http://localhost:28069/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)
        
        # Locate roadmap section
        roadmap_section = page.locator(".s_ins_3d_roadmap")
        await roadmap_section.scroll_into_view_if_needed()
        await page.wait_for_timeout(800)
        
        # 1. Capture full roadmap section in default state (Phase 1)
        path1 = os.path.join(output_dir, "roadmap_3d_phase1_default.png")
        await roadmap_section.screenshot(path=path1)
        print(f"Captured default roadmap screenshot: {path1}")
        
        # 2. Click Milestone 2 (Tuần 02)
        milestone2 = page.locator('.ins-milestone-node[data-phase="2"]')
        await milestone2.click()
        await page.wait_for_timeout(600)
        
        path2 = os.path.join(output_dir, "roadmap_3d_phase2_active.png")
        await roadmap_section.screenshot(path=path2)
        print(f"Captured Phase 2 screenshot: {path2}")
        
        # 3. Click Milestone 3 (Tuần 03)
        milestone3 = page.locator('.ins-milestone-node[data-phase="3"]')
        await milestone3.click()
        await page.wait_for_timeout(600)
        
        path3 = os.path.join(output_dir, "roadmap_3d_phase3_active.png")
        await roadmap_section.screenshot(path=path3)
        print(f"Captured Phase 3 screenshot: {path3}")

        # 4. Click Milestone 4 (Tuần 04 - Nghiệm thu ROI)
        milestone4 = page.locator('.ins-milestone-node[data-phase="4"]')
        await milestone4.click()
        await page.wait_for_timeout(600)
        
        path4 = os.path.join(output_dir, "roadmap_3d_phase4_active.png")
        await roadmap_section.screenshot(path=path4)
        print(f"Captured Phase 4 screenshot: {path4}")
        
        # 5. Click Mode button 'Chế Độ Lưới Phẳng'
        flat_btn = page.locator('.ins-mode-btn[data-mode="flat"]')
        await flat_btn.click()
        await page.wait_for_timeout(500)
        
        path_flat = os.path.join(output_dir, "roadmap_3d_flat_mode.png")
        await roadmap_section.screenshot(path=path_flat)
        print(f"Captured Flat Mode screenshot: {path_flat}")

        await browser.close()
        print("All screenshots captured cleanly!")

if __name__ == "__main__":
    asyncio.run(capture_roadmap())
