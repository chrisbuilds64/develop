// The moments: a chapter clicking shut, the counter to the gate, the seal, the sealed band, a respondent's anonymous view. usage: node moments-shot.mjs <base> <outdir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
const [base, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const issues = [];
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, baseURL: base, locale: "de-DE" });
const page = await ctx.newPage();
page.on("pageerror", (e) => issues.push(e.message));
page.on("response", (r) => { if (r.status() >= 400) issues.push(`${r.status()} ${r.url()}`); });
const as = async (p) => page.request.post("/api/session", { data: { person: p } });
const A = "ERH-2026-03-angebotsprozess", B = "ERH-2026-02-projektabwicklung";
await as("du");
await page.goto(`/case/${A}?present=1`, { waitUntil: "networkidle" }); await page.waitForTimeout(500);
await page.screenshot({ path: join(out, "1-case-line.png") });
await page.goto(`/case/${A}/gespraech`, { waitUntil: "networkidle" });
await page.locator(".talk-anchor input").fill("Angebot Ärztehaus Süd"); await page.locator(".talk-anchor .btn").click(); await page.waitForTimeout(600);
await page.screenshot({ path: join(out, "2-first-question.png") });
// the last chapter has 3 questions: answer all three
await page.locator(".chapter").nth(6).locator(".chapter-head").click(); await page.waitForTimeout(300);
for (const t of ["Honorare und Kalkulationen. Heikel sind die Bauherren-Mails.", "In einer Excel-Datei auf dem Server.", "Dann wüssten alle unsere Stundensätze."]) {
  await page.locator(".talk-area").fill(t); await page.getByRole("radio", { name: /So ist es heute/ }).click();
  if (t.startsWith("Dann")) { await page.locator(".dots .qdot").nth(0).click(); } else { await page.getByRole("button", { name: /^Weiter/ }).click(); }
  await page.waitForTimeout(250);
}
await page.waitForTimeout(500);
await page.screenshot({ path: join(out, "3-chapter-done.png") });
await as("falk");
await page.goto(`/case/${A}/gespraech`, { waitUntil: "networkidle" }); await page.waitForTimeout(600);
await page.screenshot({ path: join(out, "4-respondent-anon.png") });
await as("du");
await page.goto(`/case/${B}/ergebnis`, { waitUntil: "networkidle" }); await page.waitForTimeout(600);
await page.locator(".draft").scrollIntoViewIfNeeded();
await page.screenshot({ path: join(out, "5-counter.png") });
for (let i = 0; i < 6; i++) { const b = page.getByRole("button", { name: /Annehmen/ }).first(); if (await b.count() === 0) break; await b.click(); await page.waitForTimeout(400); }
await page.waitForTimeout(400);
await page.screenshot({ path: join(out, "6-ready.png") });
await page.getByRole("button", { name: /Kanon freigeben/ }).click(); await page.waitForTimeout(1800);
await page.screenshot({ path: join(out, "7-seal.png") });
await page.keyboard.press("Escape"); await page.locator(".seal-stage").click({ position: { x: 10, y: 10 } }); await page.waitForTimeout(600);
await page.screenshot({ path: join(out, "8-sealed.png") });
await page.emulateMedia({ colorScheme: "dark" }); await page.reload({ waitUntil: "networkidle" }); await page.waitForTimeout(600);
await page.screenshot({ path: join(out, "9-sealed-dark.png") });
console.log(issues.length ? issues.join("\n") : "no issues");
await browser.close();
