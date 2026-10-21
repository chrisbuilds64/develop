// The claims path, clicked through like a visitor: open the file, put the sample invoice in, watch the AI reconcile,
// enter the amount, approve, see the file move. Screenshots at each beat. usage: node walk.mjs <base> <outdir>
import { chromium } from "playwright";
import { mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out] = process.argv.slice(2);
const PFX = process.env.BASE_PATH || "";
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const exe = join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell");
const browser = await chromium.launch({ executablePath: exe });
const issues = [];
let n = 0;
async function beat(page, tag, name) { n += 1; const f = join(out, `${String(n).padStart(2, "0")}-${name}-${tag}.png`); await page.screenshot({ path: f, fullPage: false }); console.log(f); }

for (const [w, h, tag] of [[1440, 900, "desktop"], [390, 844, "phone"]]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, baseURL: base, isMobile: w < 600, hasTouch: w < 600, locale: "de-DE", ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") issues.push(`${tag} console: ${m.text()}`); });
  page.on("pageerror", (e) => issues.push(`${tag} pageerror: ${e.message}`));
  await page.request.post(PFX + "/api/demo/session", { data: { world: "claims" } }).catch(() => {});
  await page.request.post(PFX + "/api/session", { data: { person: "du" } });
  await page.goto(PFX + "/", { waitUntil: "networkidle" });
  await beat(page, tag, "start");
  await page.goto(PFX + "/case/HR-2026-0417-wasserschaden-badezimmer", { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  await beat(page, tag, "akte");
  const sample = page.getByRole("button", { name: /Beispiel einlegen/ });
  if (await sample.count()) { await sample.first().evaluate((el) => el.scrollIntoView({ block: "center" })); await page.waitForTimeout(150); await sample.first().click(); } else { issues.push(`${tag}: no sample button`); }
  await page.waitForTimeout(800);
  await beat(page, tag, "rechnung-drin");
  await page.waitForTimeout(6000);
  await page.waitForLoadState("networkidle");
  await beat(page, tag, "abgleich-da");
  const amount = page.locator("label.money input");
  if (await amount.count()) { await amount.first().fill("4.370 €"); }
  const btn = page.getByRole("button", { name: /Freigeben und zur Regulierung/ });
  if (await btn.count()) { await btn.first().click(); } else { issues.push(`${tag}: no approve button`); }
  await page.waitForTimeout(900);
  await beat(page, tag, "freigegeben");
  await page.goto(PFX + "/", { waitUntil: "networkidle" });
  await beat(page, tag, "danach");
  await ctx.close();
}
await browser.close();
console.log(`ISSUES (${issues.length}):\n${issues.join("\n") || "none"}`);
