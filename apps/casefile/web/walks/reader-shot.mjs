// The case, the reader on a text, the reader on a PDF, the arrow walk, the pop-out window, and the phone. usage: node reader-shot.mjs <base> <outdir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
const [base, out] = process.argv.slice(2);
const PFX = process.env.BASE_PATH || "";
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const issues = [];
const CASE = "HR-2026-0417-wasserschaden-badezimmer";
for (const [w, h, tag] of [[1440, 900, "desktop"], [390, 844, "phone"]]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, baseURL: base, ignoreHTTPSErrors: true, locale: "de-DE", isMobile: w < 600, hasTouch: w < 600 });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => issues.push(`${tag} ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error") issues.push(`${tag} console: ${m.text()}`); });
  page.on("response", (r) => { if (r.status() >= 400) issues.push(`${tag} ${r.status()} ${r.url()}`); });
  await page.request.post(PFX + "/api/demo/session", { data: { world: "claims" } });
  await page.goto(`${PFX}/case/${CASE}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await page.screenshot({ path: join(out, `${tag}-1-case.png`) });
  await page.getByRole("button", { name: /^Schadenmeldung/ }).first().click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: join(out, `${tag}-2-reader-text.png`) });
  const tabs = await page.getByRole("tab").allInnerTexts();
  console.log(tag, "tabs:", tabs.join(" | "));
  await page.keyboard.press("ArrowRight");
  await page.waitForTimeout(400);
  console.log(tag, "after →:", await page.getByRole("tab", { selected: true }).innerText());
  await page.getByRole("tab", { name: "Gutachten" }).click();
  await page.waitForTimeout(900);
  await page.screenshot({ path: join(out, `${tag}-3-reader-pdf.png`) });
  await page.keyboard.press("Escape");
  await page.waitForTimeout(300);
  const back = await page.getByRole("button", { name: /^Schadenmeldung/ }).count();
  console.log(tag, "escape returns to desk:", back > 0);
  if (tag === "desktop") {
    // the pop-out: the reader as its own window
    await page.getByRole("button", { name: /^Schadenmeldung/ }).first().click();
    await page.waitForTimeout(300);
    const [popup] = await Promise.all([ctx.waitForEvent("page"), page.getByRole("button", { name: "Als Fenster lösen" }).click()]);
    await popup.waitForLoadState("networkidle");
    await popup.setViewportSize({ width: 880, height: 1000 });
    await popup.waitForTimeout(600);
    console.log("popup url:", popup.url(), "title:", await popup.title());
    await popup.screenshot({ path: join(out, "desktop-4-popout.png") });
    await popup.keyboard.press("ArrowRight");
    await popup.waitForTimeout(400);
    console.log("popup after →:", popup.url());
    const readerGone = await page.getByRole("tab").count();
    console.log("case shows desk again after pop-out:", readerGone === 0);
  }
  await ctx.close();
}
// the versions: the assessment has two, the chips leaf through them
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, baseURL: base, ignoreHTTPSErrors: true, locale: "de-DE" });
  const page = await ctx.newPage();
  await page.request.post(PFX + "/api/demo/session", { data: { world: "claims" } });
  await page.goto(`${PFX}/case/${CASE}`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Gutachten/ }).first().click();
  await page.waitForTimeout(500);
  const vs = page.locator(".reader-meta .versions [role=tab]");
  console.log("version chips:", (await vs.allInnerTexts()).join(" | "), "| selected:", await page.locator(".reader-meta .versions [aria-selected=true]").innerText());
  await vs.first().click();
  await page.waitForTimeout(400);
  console.log("after click Fassung 1:", await page.locator(".reader-meta .versions [aria-selected=true]").innerText(), "| file:", await page.locator(".reader-meta .mono").last().innerText());
  await page.screenshot({ path: join(out, "desktop-5-versions.png") });
  await ctx.close();
}
await browser.close();
console.log(`ISSUES (${issues.length}): ${issues.join("; ") || "none"}`);
