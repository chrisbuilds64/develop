// The round trip, clicked like a claims handler would: the claim orders the assessment, the order appears in the e-report world,
// the e-report is approved and sent, the claim receives it and the AI reconciles. usage: node loop-shot.mjs <base> <outdir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
const [base, out] = process.argv.slice(2);
const PFX = process.env.BASE_PATH || "";
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const issues = [];
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, baseURL: base, ignoreHTTPSErrors: true, locale: "de-DE" });
const page = await ctx.newPage();
page.on("pageerror", (e) => issues.push(e.message));
page.on("console", (m) => { if (m.type() === "error") issues.push(`console: ${m.text().slice(0, 160)}`); });
page.on("response", (r) => { if (r.status() >= 400) issues.push(`${r.status()} ${r.url()}`); });
// 1 · the claim, newly reported, orders its assessment
await page.goto(`${PFX}/`, { waitUntil: "networkidle" });
await page.goto(`${PFX}/case/KFZ-2026-0815-parkschaden-tiefgarage`, { waitUntil: "networkidle" });
await page.waitForTimeout(600);
console.log("1 claim:", await page.locator(".case-head .stub").innerText(), "| button:", await page.locator(".foot .btn").innerText());
await page.screenshot({ path: join(out, "1-claim-new.png") });
await page.locator('input[type="date"]').fill("2026-10-24");
await page.locator(".foot .btn").click();
await page.waitForTimeout(800);
console.log("   after order:", await page.locator(".case-head .stub").innerText());
await page.screenshot({ path: join(out, "2-claim-ordered.png") });
// 2 · switch to the e-report world through the menu: the order is there
await page.getByRole("button", { name: /Zur Gutachtenakte/ }).click();
await page.waitForLoadState("networkidle"); await page.waitForTimeout(800);
const ids = await page.locator(".list .card .num").allInnerTexts();
console.log("2 e-report list:", ids.join(", "));
await page.screenshot({ path: join(out, "3-egut-list.png") });
await page.goto(`${PFX}/case/KH-2026-0815-parkschaden-tiefgarage`, { waitUntil: "networkidle" });
await page.waitForTimeout(600);
console.log("   new order:", await page.locator(".case-head .stub").innerText(), "| files:", (await page.locator(".desk-grid .file .name").allInnerTexts()).join(", "));
await page.screenshot({ path: join(out, "4-egut-order.png") });
// 3 · the e-report that waits for approval: approve, letter is drafted, send
await page.goto(`${PFX}/case/KH-2026-1182-auffahrunfall-a3-kleinwagen`, { waitUntil: "networkidle" });
await page.locator(".foot .btn").click();
await page.waitForTimeout(6500);
console.log("3 approved:", await page.locator(".foot .btn").innerText());
await page.locator(".foot .btn").click();
await page.waitForTimeout(1200);
console.log("   sent:", await page.locator(".case-head .stub").innerText());
await page.screenshot({ path: join(out, "5-egut-sent.png") });
// 4 · back in the claims world: the claim has the e-report and the AI reconciles
await page.getByRole("button", { name: /Zur Schadenakte/ }).click();
await page.waitForLoadState("networkidle"); await page.waitForTimeout(800);
await page.goto(`${PFX}/case/KFZ-2026-0811-auffahrunfall-a3-kleinwagen`, { waitUntil: "networkidle" });
await page.waitForTimeout(600);
console.log("4 claim after return:", await page.locator(".case-head .stub").innerText(), "| files:", (await page.locator(".desk-grid .file .name").allInnerTexts()).join(", "));
await page.screenshot({ path: join(out, "6-claim-received.png") });
await page.waitForTimeout(7000);
console.log("   after reconcile:", await page.locator(".case-head .stub").innerText(), "| button:", await page.locator(".foot .btn").innerText());
await page.screenshot({ path: join(out, "7-claim-reconciled.png") });
console.log("   0815 still ordered:", (await page.goto(`${PFX}/case/KFZ-2026-0815-parkschaden-tiefgarage`, { waitUntil: "networkidle" }), await page.locator(".case-head .stub").innerText()));
await ctx.close(); await browser.close();
console.log(`ISSUES (${issues.length}): ${issues.join("; ") || "none"}`);
