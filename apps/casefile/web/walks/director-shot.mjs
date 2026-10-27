// The director, played like a presenter: open the list, pick a flow, press → until the end. A screenshot per step; errors
// the panel shows are collected; exit 1 when the flow breaks. usage: node walks/director-shot.mjs <base> <outdir> <title regex> [workspace] [flow id]
import { chromium } from "playwright";
import { mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, title, ws = "posteingang-muster", flowId] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const browser = await chromium.launch({ executablePath: join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell") });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "de-DE" })).newPage();
const issues = [];
page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`pageerror: ${e.message}`); });   // headless has no view transitions
await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
await page.request.post(`${base}/w/${ws}/api/session`, { data: { person: "du" } });
await page.reload({ waitUntil: "networkidle" });
await page.click(".cf-dir-launch");
if (flowId) await page.click(`[data-flow="${flowId}"]`); else await page.getByRole("button", { name: new RegExp(title) }).click();
await page.waitForSelector(".cf-dir-panel", { timeout: 20000 });
for (let n = 1; n < 60; n++) {
  await page.waitForTimeout(800);
  const count = await page.locator(".cf-dir-count").textContent({ timeout: 5000 }).catch(() => "");
  await page.screenshot({ path: join(out, `${String(n).padStart(2, "0")}.png`) });
  const errs = page.locator(".cf-dir-panel .cf-dir-error");
  const err = (await errs.count()) ? await errs.first().textContent() : null;
  console.log(n, count, err ? `ERROR ${err}` : "");
  if (err) issues.push(`${count}: ${err}`);
  if (/fertig/.test(count ?? "") || err) break;
  await page.keyboard.press("ArrowRight");
  await page.waitForFunction(() => { const b = document.querySelector(".cf-dir-next"); return b && !b.disabled; }, null, { timeout: 70000 }).catch(() => issues.push(`stuck at ${count}`));
  await page.waitForTimeout(400);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
