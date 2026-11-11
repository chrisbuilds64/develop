// Skipping a whole gate protocol (REQ-003 GP-09, GP-43, GP-44; SW-2026-015). On a Shipyard case at the ENTW gate, in
// German: a developer without the gate's role sees no "Fragebogen überspringen"; the product owner does, on the questionnaire
// not yet started. Without a reason the surface does not send it and the core refuses it; with a reason the card says
// "Übersprungen von …" with the reason, the button is gone, the thread names the skip, the record beside it says skipped
// and "not checked", and "approve_test" is no longer blocked — with no item answered. A screenshot per step; exit 1 on
// the first thing that does not hold.
// usage: node walks/protocol-skip-shot.mjs <base> <outdir> [shipyard workspace]
import { chromium } from "playwright";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ws = "shipyard-muster"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = existsSync(cache) && readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const pinned = shell && join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell");
const browser = await chromium.launch(pinned && existsSync(pinned) ? { executablePath: pinned } : {});
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "de-DE" })).newPage();
const issues = [];
page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`pageerror: ${e.message}`); });
let at = "start";
let n = 0;
const shot = async (what) => { n += 1; await page.screenshot({ path: join(out, `${String(n).padStart(2, "0")}-${what}.png`) }); console.log(n, what); };
const must = (ok, what) => { if (!ok) throw new Error(what); };
const CASE = "SW-2026-003-ready-on-entw";
const api = `${base}/w/${ws}/api/cases/${encodeURIComponent(CASE)}`;
const card = page.locator('.pc[data-help="cf.protocol"]').first();
const skipButton = card.locator(".pc-skip");

const sign = async (person) => {
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  must((await page.request.post(`${base}/w/${ws}/api/session`, { data: { person } })).ok(), `cannot sign in as ${person}`);
  await page.request.post(`${base}/w/${ws}/api/session/lang`, { data: { lang: "de" } });
  await page.goto(`${base}/w/${ws}/case/${encodeURIComponent(CASE)}`, { waitUntil: "networkidle" });
  await card.waitFor({ timeout: 5000 });
};
const approve = async () => (await (await page.request.get(api)).json()).turns.find((t) => t.action === "approve_test");

try {
  at = "no gate role, no button";
  await sign("dev");
  must(await skipButton.count() === 0, "a developer without the gate's role sees the skip button");
  await shot("no-button-without-role");

  at = "the gate is closed before";
  await sign("du");
  must((await approve())?.blocked_by?.includes("protocol:entw"), "approve_test is not blocked by the questionnaire before the skip");
  must(await skipButton.isVisible(), "the product owner does not see the skip button on the questionnaire");
  must((await skipButton.textContent())?.trim() === "Fragebogen überspringen", `the button reads "${await skipButton.textContent()}"`);
  await shot("button");

  at = "no reason, no skip";
  await skipButton.click();
  const why = card.locator(".pc-answer input");
  const go = card.locator(".pc-answer button.ghost");
  await why.waitFor({ timeout: 5000 });
  must(await go.isDisabled(), "the skip can be sent without a reason");
  const refused = await page.request.post(`${api}/protocols/entw/skip`, { data: { step_id: "walk-skip-empty", reason: "  " } });
  must(refused.status() === 409, `an empty reason was not refused by the core (${refused.status()})`);
  await shot("asks-why");

  at = "skipped with a reason";
  await why.fill("Nur Doku geändert, nichts auszuprobieren");
  const sent = page.waitForResponse((r) => r.request().method() === "POST" && /\/protocols\/entw\/skip$/.test(r.url()), { timeout: 10000 });
  await go.click();
  must((await sent).ok(), "the skip was refused");
  await page.waitForFunction(() => document.querySelector('.pc[data-help="cf.protocol"] .hint')?.textContent?.includes("Übersprungen von"), null, { timeout: 5000 });
  const line = await card.locator(".hint").first().textContent();
  must(line.includes("Nur Doku geändert"), `the card does not show the reason: ${line}`);
  must(await skipButton.count() === 0, "the skip button stays after the skip");
  await page.waitForFunction(() => document.querySelector(".i-thread")?.textContent?.includes("Fragebogen übersprungen"), null, { timeout: 5000 });
  await shot("skipped");

  at = "the gate is open, nothing answered";
  const t = await approve();
  must(t && !t.blocked_by.includes("protocol:entw"), `approve_test is still blocked: ${JSON.stringify(t?.blocked_by)}`);
  const v = await (await page.request.get(api)).json();
  const doc = v.protocols.find((p) => p.template === "entw").doc;
  must(Object.keys(doc.answers).length === 0 && doc.skipped?.reason, "the protocol carries answers or no skip");
  const record = await (await page.request.get(`${api}/files/protocol-entw.md`)).text();
  must(record.includes("Skipped by du") && record.includes("not checked"), `the record does not say skipped: ${record.slice(0, 200)}`);
} catch (e) {
  issues.push(`${at}: ${e.message.split("\n")[0]}`);
  await page.screenshot({ path: join(out, "broken.png") }).catch(() => undefined);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
