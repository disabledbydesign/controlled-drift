/**
 * Screenshot the running app. Used for the live-verify gates in
 * docs/superpowers/plans/2026-07-18-track-a-component-port.md.
 *
 * ⚠ WHY THIS EXISTS: `agent-browser screenshot` HANGS INDEFINITELY in this environment
 * (2026-07-18). It hangs on raw CDP `Page.captureScreenshot` too, on a fresh headless Chrome
 * against a plain `data:text/html` page — so it is the environment, not the app, and not
 * something to debug in-app. Navigation, DOM reads, clicks and computed-style reads over
 * agent-browser still work fine; only screenshots are affected. Playwright works. Use this.
 *
 *   cd app && node scripts/shot.mjs                     # defaults
 *   cd app && node scripts/shot.mjs today,map hardware  # tabs, theme
 *
 * Requires the dev server: `cd app && npx vite` (serves at http://localhost:5173/app/).
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const URL = process.env.CD_APP_URL || 'http://localhost:5173/app/';
const OUT = process.env.CD_SHOT_DIR || '/tmp/cd-shots';
const tabs = (process.argv[2] || 'today').split(',').filter(Boolean);
const themes = (process.argv[3] || 'celestial,hardware').split(',').filter(Boolean);

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
// Phone-shaped by default — this surface is mobile-first. Pass CD_WIDTH for the desktop path.
const page = await browser.newPage({
  viewport: { width: Number(process.env.CD_WIDTH || 420), height: Number(process.env.CD_HEIGHT || 900) },
});

for (const theme of themes) {
  for (const tab of tabs) {
    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.evaluate((t) => localStorage.setItem('cd_theme', t), theme);
    await page.reload({ waitUntil: 'networkidle' });

    if (tab !== 'today') {
      const btn = page.getByRole('button', { name: new RegExp(`^${tab}`, 'i') }).first();
      if (await btn.count()) await btn.click();
    }
    await page.waitForTimeout(400); // let the nav animation settle

    const path = `${OUT}/${theme}-${tab}.png`;
    await page.screenshot({ path });
    console.log(path);
  }
}

await browser.close();
