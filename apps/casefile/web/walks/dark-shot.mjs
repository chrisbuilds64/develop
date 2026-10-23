// dark mode + phone bar after the panels. usage: node dark-shot.mjs <base> <outdir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
const [base, out] = process.argv.slice(2);
const PFX = process.env.BASE_PATH || "";
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
for (const [w, h, tag, scheme] of [[1440, 900, "desktop-dark", "dark"], [390, 844, "phone-dark", "dark"], [390, 844, "phone-light", "light"]]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, baseURL: base, ignoreHTTPSErrors: true, locale: "de-DE", colorScheme: scheme, isMobile: w < 600, hasTouch: w < 600 });
  const page = await ctx.newPage();
  await page.request.post(PFX + "/api/demo/session", { data: { world: "claims" } });
  await page.goto(`${PFX}/case/HR-2026-0417-wasserschaden-badezimmer`, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await page.screenshot({ path: join(out, `${tag}.png`) });
  await ctx.close();
}
await browser.close();
