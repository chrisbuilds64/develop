// The content story, clicked through: Chris approves the script; as Akhil, fill the thumbnail frame; as Chris, approve the visual.
// usage: node walk-pressroom.mjs <base> <outdir>
import { chromium } from "playwright";
import { mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const exe = join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell");
const browser = await chromium.launch({ executablePath: exe });
const issues = [];
let n = 0;
async function beat(page, tag, name) { n += 1; const f = join(out, `${String(n).padStart(2, "0")}-${name}-${tag}.png`); await page.screenshot({ path: f, fullPage: false }); console.log(f); }

for (const [w, h, tag] of [[1440, 900, "desktop"], [390, 844, "phone"]]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, baseURL: base, isMobile: w < 600, hasTouch: w < 600 });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") issues.push(`${tag} console: ${m.text()}`); });
  page.on("pageerror", (e) => issues.push(`${tag} pageerror: ${e.message}`));
  const me = await (await page.request.post("/api/demo/session", { data: { world: "pressroom" } })).json();
  if (me.world !== "pressroom" || me.person !== "chris") issues.push(`${tag}: session ${JSON.stringify(me)}`);
  await page.goto("/", { waitUntil: "networkidle" });
  await beat(page, tag, "chris-start");
  await page.goto("/case/POD-ARC-02-the-arc-spoken", { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  await beat(page, tag, "chris-arc02");
  const approve = page.getByRole("button", { name: /Approve and send to Akhil/ });
  if (await approve.count()) await approve.first().click(); else issues.push(`${tag}: no approve button`);
  await page.waitForTimeout(900);
  await beat(page, tag, "chris-approved");
  // Akhil's turn
  await page.request.post("/api/session", { data: { person: "akhil" } });
  await page.goto("/", { waitUntil: "networkidle" });
  await beat(page, tag, "akhil-start");
  await page.goto("/case/POD-ARC-02-the-arc-spoken", { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  await beat(page, tag, "akhil-frames");
  const sample = page.getByRole("button", { name: /Put in a sample thumbnail/i });
  if (await sample.count()) await sample.first().click(); else issues.push(`${tag}: no thumbnail sample`);
  await page.waitForTimeout(900);
  await beat(page, tag, "akhil-thumbnail-in");
  // back to Chris
  await page.request.post("/api/session", { data: { person: "chris" } });
  await page.goto("/case/POD-ARC-02-the-arc-spoken", { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  await beat(page, tag, "chris-visual");
  const ok = page.getByRole("button", { name: /Approve the visual/ });
  if (await ok.count()) await ok.first().click(); else issues.push(`${tag}: no approve-visual button`);
  await page.waitForTimeout(900);
  await beat(page, tag, "chris-visual-approved");
  await ctx.close();
}
await browser.close();
console.log(`ISSUES (${issues.length}):\n${issues.join("\n") || "none"}`);
