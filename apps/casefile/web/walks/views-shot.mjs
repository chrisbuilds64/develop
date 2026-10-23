// The three views. usage: node views-shot.mjs <base> <outdir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
const [base, out] = process.argv.slice(2);
const PFX = process.env.BASE_PATH || "";
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const issues = [];
for (const [w, h, tag] of [[1440, 900, "desktop"], [390, 844, "phone"]]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, baseURL: base, ignoreHTTPSErrors: true, locale: "de-DE", isMobile: w < 600, hasTouch: w < 600 });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => issues.push(`${tag} ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error") issues.push(`${tag} console: ${m.text().slice(0, 120)}`); });
  page.on("response", (r) => { if (r.status() >= 400) issues.push(`${tag} ${r.status()} ${r.url()}`); });
  for (const world of ["claims", "pressroom"]) {
    await page.request.post(PFX + "/api/demo/session", { data: { world } });
    for (const v of ["board", "list"]) {
      await page.goto(`${PFX}/${v}`, { waitUntil: "networkidle" });
      await page.waitForTimeout(600);
      await page.screenshot({ path: join(out, `${tag}-${world}-${v}.png`) });
    }
    if (tag === "desktop" && world === "claims") {
      // switch views through the menu, open a case from the board
      await page.goto(`${PFX}/board`, { waitUntil: "networkidle" });
      await page.getByRole("tab", { name: "Liste" }).click(); await page.waitForTimeout(300);
      console.log("list via switch:", await page.locator("h1").first().innerText());
      await page.getByRole("tab", { name: "Kanban" }).click(); await page.waitForTimeout(300);
      await page.locator(".kanban .card").first().click(); await page.waitForTimeout(500);
      console.log("case from board:", await page.locator(".case-head h1").innerText());
      await page.locator(".stack-scroll, .kanban").count();
    }
  }
  await ctx.close();
}
await browser.close();
console.log(`ISSUES (${issues.length}): ${issues.join("; ") || "none"}`);
