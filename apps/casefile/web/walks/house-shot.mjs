// The house canon: the matrix, one document opened with its trail, the phone. usage: node house-shot.mjs <base> <outdir> <person> <doc title>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
const [base, out, person, title] = process.argv.slice(2); mkdirSync(out, { recursive: true });
const b = await chromium.launch(); const issues = [];
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, baseURL: base, locale: "de-DE" });
const p = await ctx.newPage(); p.on("pageerror", (e) => issues.push(e.message)); p.on("response", (r) => { if (r.status() >= 400) issues.push(`${r.status()} ${r.url()}`); });
await p.request.post("/api/session", { data: { person } });
await p.goto("/kanon", { waitUntil: "networkidle" }); await p.waitForTimeout(500);
await p.screenshot({ path: join(out, "1-house.png") }); await p.locator(".house-legend").scrollIntoViewIfNeeded(); await p.waitForTimeout(300); await p.screenshot({ path: join(out, "1b-house-bottom.png") });
await p.locator(".hm-chip", { hasText: title }).first().click(); await p.waitForTimeout(700);
await p.screenshot({ path: join(out, "2-doc.png") });
await p.emulateMedia({ colorScheme: "dark" }); await p.keyboard.press("Escape"); await p.waitForTimeout(300);
await p.screenshot({ path: join(out, "3-dark.png") }); await p.emulateMedia({ colorScheme: "light" });
await p.setViewportSize({ width: 390, height: 844 }); await p.goto("/kanon", { waitUntil: "networkidle" }); await p.waitForTimeout(400);
await p.screenshot({ path: join(out, "4-phone.png") });
console.log(`ISSUES (${issues.length})\n` + issues.join("\n")); await b.close();
