// The canon as a document, and the decluttered question. usage: node canon-shot.mjs <base> <outdir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
const [base, out] = process.argv.slice(2); mkdirSync(out, { recursive: true });
const b = await chromium.launch(); const issues = [];
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, baseURL: base, locale: "de-DE" });
const p = await ctx.newPage(); p.on("pageerror", (e) => issues.push(e.message)); p.on("response", (r) => { if (r.status() >= 400) issues.push(`${r.status()} ${r.url()}`); });
await p.request.post("/api/session", { data: { person: "du" } });
await p.goto("/case/ERH-2026-01-rechnungsstellung/kanon", { waitUntil: "networkidle" }); await p.waitForTimeout(500);
await p.screenshot({ path: join(out, "1-canon.png") });
await p.goto("/case/ERH-2026-02-projektabwicklung/ergebnis", { waitUntil: "networkidle" });
for (let i = 0; i < 6; i++) { const x = p.getByRole("button", { name: /Annehmen/ }).first(); if (await x.count() === 0) break; await x.click(); await p.waitForTimeout(350); }
await p.getByRole("button", { name: /Kanon freigeben/ }).click(); await p.waitForTimeout(1800);
await p.locator(".seal-sheet .btn.seal").click(); await p.waitForTimeout(800);
await p.screenshot({ path: join(out, "2-canon-b.png") });
await p.locator(".canon-chapter").nth(1).scrollIntoViewIfNeeded(); await p.waitForTimeout(300);
await p.screenshot({ path: join(out, "3-canon-rules.png") });
await p.emulateMedia({ colorScheme: "dark" }); await p.waitForTimeout(300);
await p.screenshot({ path: join(out, "4-canon-dark.png") }); await p.emulateMedia({ colorScheme: "light" });
await p.goto("/case/ERH-2026-03-angebotsprozess/gespraech", { waitUntil: "networkidle" });
await p.locator(".talk-anchor input").fill("Angebot Ärztehaus Süd"); await p.locator(".talk-anchor .btn").click(); await p.waitForTimeout(600);
await p.screenshot({ path: join(out, "5-question-empty.png") });
await p.locator(".talk-area").fill("Die Excel-Vorlage."); await p.waitForTimeout(200);
await p.getByRole("button", { name: /^Weiter/ }).click(); await p.waitForTimeout(400);
await p.screenshot({ path: join(out, "6-question-typed.png") });
await p.setViewportSize({ width: 390, height: 844 }); await p.goto("/case/ERH-2026-02-projektabwicklung/kanon", { waitUntil: "networkidle" }); await p.waitForTimeout(500);
await p.screenshot({ path: join(out, "7-canon-phone.png") });
console.log(issues.join("\n") || "no issues"); await b.close();
