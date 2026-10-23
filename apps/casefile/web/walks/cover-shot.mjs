// Covers on the cards: both worlds, list + case head, desktop + phone; and the person select after a world switch. usage: node cover-shot.mjs <base> <outdir>
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
  page.on("console", (m) => { if (m.type() === "error") issues.push(`${tag} console: ${m.text()}`); });
  page.on("response", (r) => { if (r.status() >= 400) issues.push(`${tag} ${r.status()} ${r.url()}`); });
  await page.request.post(PFX + "/api/demo/session", { data: { world: "pressroom" } });
  await page.goto(PFX + "/", { waitUntil: "networkidle" });
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(out, `${tag}-pressroom-list.png`) });
  if (tag === "desktop") {
    console.log("pressroom person select:", await page.locator("select.person-switch").inputValue(), "| options:", (await page.locator("select.person-switch option").allInnerTexts()).join(","));
    // switch the world through the menu, then read the select again
    await page.getByRole("button", { name: /Zur Schadenakte|To the claims file/ }).click();
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800);
    console.log("after switch:", await page.locator("select.person-switch").count() ? await page.locator("select.person-switch").inputValue() : "(no select)", "| product:", await page.title());
    await page.getByRole("button", { name: /Zum PressRoom|To the PressRoom/ }).click();
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800);
    console.log("after switch back:", await page.locator("select.person-switch").inputValue(), "| options:", (await page.locator("select.person-switch option").allInnerTexts()).join(","));
    await page.screenshot({ path: join(out, `${tag}-pressroom-after-switch.png`) });
  }
  await page.request.post(PFX + "/api/demo/session", { data: { world: "claims" } });
  await page.goto(PFX + "/case/HR-2026-0417-wasserschaden-badezimmer", { waitUntil: "networkidle" });
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(out, `${tag}-claims-case.png`) });
  await ctx.close();
}
await browser.close();
console.log(`ISSUES (${issues.length}): ${issues.join("; ") || "none"}`);
