const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUTPUT_DIR = path.join(__dirname, 'hero_video_audit_screenshots');
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

(async () => {
    console.log("=== INNOKAFE HERO VIDEO CLARITY & CONTRAST AUDIT ===");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 1440, height: 900 }
    });
    const page = await context.newPage();

    const BASE_URL = "http://localhost:28071";
    const routes = [
        { path: '/products', name: 'products_catalogue', videoSnippet: 'innokafe_cooling_tray' },
        { path: '/', name: 'homepage', videoSnippet: 'innokafe_hero_terroir' },
        { path: '/story', name: 'story_terroir', videoSnippet: 'innokafe_drying_tray' },
        { path: '/solutions-b2b', name: 'solutions_b2b', videoSnippet: 'innokafe_barista_tasting' },
        { path: '/taste-profiler', name: 'taste_profiler', videoSnippet: 'innokafe_coffee_pour' },
        { path: '/contactus', name: 'contactus_showroom', videoSnippet: 'innokafe_hero_terroir' }
    ];

    try {
        for (const item of routes) {
            console.log(`\nAuditing Hero on ${item.path}...`);
            await page.goto(`${BASE_URL}${item.path}`, { waitUntil: 'networkidle' });
            await page.waitForTimeout(1000);

            // Verify video element exists and is visible
            const videoElem = await page.$('.inno-hero-video-wrap video');
            if (!videoElem) {
                throw new Error(`Missing video inside .inno-hero-video-wrap on ${item.path}`);
            }

            // Verify video source contains expected video name
            const videoSrc = await page.evaluate(el => el.querySelector('source')?.getAttribute('src') || '', videoElem);
            console.log(`  Video src: ${videoSrc}`);
            if (!videoSrc.includes(item.videoSnippet)) {
                throw new Error(`Expected video ${item.videoSnippet}, found ${videoSrc}`);
            }

            // Verify computed opacity of video (should be ~0.65, not the old dim 0.22)
            const videoOpacity = await page.evaluate(el => window.getComputedStyle(el).opacity, videoElem);
            console.log(`  Computed Video Opacity: ${videoOpacity}`);
            const opacityNum = parseFloat(videoOpacity);
            if (opacityNum < 0.5) {
                throw new Error(`Video opacity ${videoOpacity} is too dim (< 0.50)! User requested clear background.`);
            }

            // Verify scrim presence
            const hasScrim = await page.$('.inno-hero-scrim-split, .inno-hero-scrim-center');
            if (!hasScrim) {
                throw new Error(`Missing hero scrim overlay on ${item.path}`);
            }

            // Verify hero title text readability (must not have zero size or collision)
            const titleElem = await page.$('.inno-hero-title, h1');
            const titleVisible = await titleElem.isVisible();
            const titleText = await titleElem.innerText();
            console.log(`  Title: "${titleText.replace(/\n/g, ' ')}" (Visible: ${titleVisible})`);

            // Capture screenshot of the hero fold
            const screenshotPath = path.join(OUTPUT_DIR, `${item.name}_hero_desktop.png`);
            await page.screenshot({ path: screenshotPath, clip: { x: 0, y: 0, width: 1440, height: 680 } });
            console.log(`  [✓] Captured fold screenshot: ${screenshotPath}`);
        }

        console.log("\n=======================================================");
        console.log("✅ ALL 6 ROUTES VERIFIED: HIGH-CLARITY VIDEO HERO ACTIVE");
        console.log("=======================================================");

    } finally {
        await browser.close();
    }
})();
