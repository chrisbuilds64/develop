// Who holds a case, and the way back by name (REQ-001 T-08, S-19; SW-2026-014). In German, in two applications.
// Shipyard: work handed out of a case (a deploy) shows as "Deploy auf ENTW läuft · seit HH:MM", with no "Liegt bei" and no
// "Erinnern"; once it ends, the case is the developer's again. "Zurücknehmen" and "Zurückholen" name the stage by its short
// name ("Release", "PROD"), never by its status sentence. Schadenakte: the same buttons name "Meldung", and a case a person
// holds still offers "Erinnern". A screenshot per step; exit 1 on the first thing that does not hold.
// usage: node walks/held-case-shot.mjs <base> <outdir> [shipyard workspace] [claims workspace]
import { chromium } from "playwright";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ship = "shipyard-muster", claims = "schadenakte-muster"] = process.argv.slice(2);
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

const sign = async (ws, person) => {
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  must((await page.request.post(`${base}/w/${ws}/api/session`, { data: { person } })).ok(), `cannot sign in as ${person}`);
  await page.request.post(`${base}/w/${ws}/api/session/lang`, { data: { lang: "de" } });
};
const open = async (ws, id) => {
  await page.goto(`${base}/w/${ws}/case/${encodeURIComponent(id)}`, { waitUntil: "networkidle" });
  await page.locator(".c-stub").waitFor({ timeout: 5000 });
};
const stepOn = async (ws, id, action, payload = {}) => {
  const r = await page.request.post(`${base}/w/${ws}/api/cases/${encodeURIComponent(id)}/steps`, { data: { action, step_id: `walk-${action}-${Date.now()}`, payload } });
  const doc = await r.json().catch(() => ({}));
  must(r.ok() && doc.ok !== false, `${action} was refused: ${doc.reason ?? r.status()}`);
};
const card = () => page.locator(".card.plain");
const buttons = async () => (await card().locator("button").allTextContents()).map((t) => t.trim());

try {
  at = "outside work shows like a helper at work";
  const BUILD = "SW-2026-002-another-sample";
  await sign(ship, "dev");
  await stepOn(ship, BUILD, "outside", { what: "deploy_entw" });
  await open(ship, BUILD);
  const stub = (await page.locator(".c-stub").textContent())?.trim() ?? "";
  must(/^Deploy auf ENTW läuft · seit \d{2}:\d{2}$/.test(stub), `the case line reads "${stub}"`);
  must((await card().textContent())?.includes("Deploy auf ENTW läuft"), "the card does not say what runs outside");
  must(!(await card().textContent())?.includes("Liegt bei"), "somebody holds the case while the deploy runs");
  must(!(await buttons()).includes("Erinnern"), "a reminder is offered while the deploy runs");
  await shot("deploy-running");

  at = "the report ends it";
  await stepOn(ship, BUILD, "outside_end");
  await open(ship, BUILD);
  must(!(await page.locator(".c-stub").textContent())?.includes("läuft"), "the deploy still shows after it ended");
  await shot("deploy-ended");

  at = "take back names the stage (Shipyard)";
  await open(ship, "SW-2026-003-ready-on-entw");
  const take = (await buttons()).find((b) => b.startsWith("Zurücknehmen"));
  must(take === "Zurücknehmen · Release", `the take-back button reads "${take}"`);
  await shot("take-back-release");

  at = "move back names the stage (Shipyard)";
  await sign(ship, "du");
  await open(ship, "SW-2026-001-sample-change");
  const back = (await buttons()).find((b) => b.startsWith("Zurückholen"));
  must(back && /^Zurückholen · \S+$/.test(back) && !back.includes("abgeschlossen"), `the move-back button reads "${back}"`);
  await shot("move-back");

  at = "a second application: the stage's short name and the reminder to a person";
  await sign(claims, "du");
  await open(claims, "WG-2026-0425-glasbruch-wintergarten");
  const words = await buttons();
  must(words.includes("Zurücknehmen · Meldung"), `the take-back button reads "${words.find((b) => b.startsWith("Zurücknehmen"))}"`);
  must(words.includes("Erinnern"), "a case a person holds no longer offers a reminder");
  must((await card().textContent())?.includes("Liegt bei Gutachter Berger"), "the holder is not named");
  await shot("claims-held");
} catch (e) {
  issues.push(`${at}: ${e.message.split("\n")[0]}`);
  await page.screenshot({ path: join(out, "broken.png") }).catch(() => undefined);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
