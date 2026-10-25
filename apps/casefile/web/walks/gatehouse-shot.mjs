// Gatehouse: the case, the anchor, a question answered with its marker, a chapter left (follow-ups arrive), Jana's finished
// conversation with tension and drafts, the outcome with decisions, the phone. usage: node gatehouse-shot.mjs <base> <outdir>
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
const [base, out] = process.argv.slice(2);
const PFX = process.env.BASE_PATH || "";
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const issues = [];
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, baseURL: base, locale: "de-DE" });
const page = await ctx.newPage();
page.on("pageerror", (e) => issues.push(e.message));
page.on("console", (m) => { if (m.type() === "error") issues.push(`console: ${m.text().slice(0, 160)}`); });
page.on("response", (r) => { if (r.status() >= 400) issues.push(`${r.status()} ${r.url()}`); });
const as = async (person) => { await page.request.post(PFX + "/api/session", { data: { person } }); };
const A = "ERH-2026-03-angebotsprozess", B = "ERH-2026-02-projektabwicklung";
await as("du");
await page.goto(`${PFX}/case/${A}`, { waitUntil: "networkidle" }); await page.waitForTimeout(600);
await page.screenshot({ path: join(out, "1-case.png") });
await page.locator(".foot .btn").click(); await page.waitForTimeout(600);
await page.screenshot({ path: join(out, "2-anchor.png") });
await page.locator(".talk-anchor input").fill("Angebot Ärztehaus Süd");
await page.locator(".talk-anchor .btn").click(); await page.waitForTimeout(800);
await page.locator(".talk-area").fill("Eigentlich die Excel-Vorlage und die Ordner auf dem Server. Normalerweise reicht das.");
await page.waitForTimeout(300);
await page.screenshot({ path: join(out, "3-question-nomarker.png") });
await page.getByRole("radio", { name: /So ist es heute/ }).click();
await page.getByRole("button", { name: /^Weiter/ }).click(); await page.waitForTimeout(500);
await page.screenshot({ path: join(out, "4-after-first.png") });
// leave chapter 0 → follow-ups ordered (replay, 5 s)
await page.locator(".chapter").nth(1).locator(".chapter-head").click(); await page.waitForTimeout(400);
await page.locator(".talk-area").fill("Ein unterschriebenes Angebot beim Bauherrn.");
await page.getByRole("radio", { name: /So ist es heute/ }).click();
await page.getByRole("button", { name: /^Weiter/ }).click(); await page.waitForTimeout(300);
await page.locator(".talk-area").fill("Zwei Sorten: Honorarangebote und Nachtragsangebote.");
await page.getByRole("radio", { name: /So sollte es sein/ }).click();
await page.getByRole("button", { name: /^Weiter/ }).click(); await page.waitForTimeout(7500);
await page.screenshot({ path: join(out, "5-followup.png") });
// Jana: finished, with tension and drafts
await as("falk");
await page.goto(`${PFX}/case/${A}/gespraech`, { waitUntil: "networkidle" }); await page.waitForTimeout(800);
await page.locator(".qdot").nth(10).click(); await page.waitForTimeout(500);
await page.screenshot({ path: join(out, "6-jana.png") });
// the outcome
await as("du");
await page.goto(`${PFX}/case/${B}/ergebnis`, { waitUntil: "networkidle" }); await page.waitForTimeout(800);
await page.screenshot({ path: join(out, "7-outcome.png") });
await page.locator(".draft").scrollIntoViewIfNeeded(); await page.waitForTimeout(300);
await page.screenshot({ path: join(out, "8-draft.png") });
// dark
await page.emulateMedia({ colorScheme: "dark" });
await page.goto(`${PFX}/case/${A}/gespraech`, { waitUntil: "networkidle" }); await page.waitForTimeout(800);
await page.screenshot({ path: join(out, "9-dark.png") });
await page.emulateMedia({ colorScheme: "light" });
// phone
await page.setViewportSize({ width: 390, height: 844 });
await page.goto(`${PFX}/case/${A}/gespraech`, { waitUntil: "networkidle" }); await page.waitForTimeout(800);
await page.screenshot({ path: join(out, "10-phone.png"), fullPage: true });
console.log(issues.length ? "issues:\n" + issues.join("\n") : "no issues");
await browser.close();
