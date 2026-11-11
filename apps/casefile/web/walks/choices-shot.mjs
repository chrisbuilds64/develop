// A question's numbered choices as buttons (REQ-001 A-06, SW-2026-018). In German, in Shipyard's sample world.
// A question with three numbered choices shows three buttons on the case card and in the conversation, each in the choice's
// words, and no "Helfer erneut beauftragen" beside them; pressing one answers the question with that line. A question
// without choices still offers "Antworten" and "Erledigt"; "Etwas anderes …" keeps the free answer on one with choices.
// The same card at phone width. A screenshot per step; exit 1 on the first thing that does not hold.
// usage: node walks/choices-shot.mjs <base> <outdir> [shipyard workspace]
import { chromium } from "playwright";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ship = "shipyard-muster"] = process.argv.slice(2);
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

const CASE = "SW-2026-002-another-sample";
const CHOICES = ["Die Wörter so lassen", "Die kürzeren Wörter nehmen", "Den Knopf weglassen"];
const sign = async (person) => {
  await page.goto(`${base}/w/${ship}/`, { waitUntil: "networkidle" });
  must((await page.request.post(`${base}/w/${ship}/api/session`, { data: { person } })).ok(), `cannot sign in as ${person}`);
  await page.request.post(`${base}/w/${ship}/api/session/lang`, { data: { lang: "de" } });
};
const ask = async (text) => {
  const r = await page.request.post(`${base}/w/${ship}/api/cases/${encodeURIComponent(CASE)}/entries`,
    { data: { kind: "note", step_id: `walk-ask-${Date.now()}`, for: "Du", title: "Eine Entscheidung", text } });
  const doc = await r.json().catch(() => ({}));
  must(r.ok() && doc.ok !== false, `the question was refused: ${doc.reason ?? r.status()}`);
};
const open = async () => {
  await page.goto(`${base}/w/${ship}/case/${encodeURIComponent(CASE)}`, { waitUntil: "networkidle" });
  await page.locator(".c-stub").waitFor({ timeout: 5000 });
};
const question = () => page.locator(".msg.oq").last();
const texts = async (loc) => (await loc.allTextContents()).map((t) => t.trim());

try {
  at = "a question with three choices";
  await sign("dev");
  await ask(`Welche Wörter soll der Knopf tragen?\n\n${CHOICES.map((c, i) => `${i + 1}. ${c} — dann geht es so weiter`).join("\n")}\n`);
  await sign("du");
  await open();
  const onCard = await texts(page.locator(".c-choices button[data-choice]"));
  must(JSON.stringify(onCard) === JSON.stringify(CHOICES), `the card offers ${JSON.stringify(onCard)}`);
  must(await page.locator(".c-again").count() === 0, "\"Helfer erneut beauftragen\" stands beside the choices");
  must((await page.locator(".c-choices").textContent())?.includes("Etwas anderes"), "the card has no way to the free answer");
  const inThread = await texts(question().locator(".mq.choices button"));
  must(JSON.stringify(inThread) === JSON.stringify(CHOICES), `the conversation offers ${JSON.stringify(inThread)}`);
  must(!(await texts(question().locator("button"))).includes("Antworten"), "the conversation still offers \"Antworten\" beside the choices");
  await shot("choices");

  at = "the same at phone width";
  await page.setViewportSize({ width: 390, height: 844 });
  await open();
  must(await page.locator(".c-choices button[data-choice]").count() === 3, "the phone card does not show three buttons");
  await shot("choices-phone");
  await page.setViewportSize({ width: 1440, height: 900 });
  await open();

  at = "pressing a choice answers with it";
  await page.locator(".c-choices button[data-choice]", { hasText: CHOICES[1] }).click();
  await page.waitForLoadState("networkidle");
  await page.waitForFunction(() => !document.querySelector(".c-choices"), null, { timeout: 5000 });
  const last = (await page.locator(".msg").last().textContent()) ?? "";
  must(last.includes(CHOICES[1]), `the newest entry reads "${last.slice(0, 120)}"`);
  must(await page.locator(".msg.oq").count() === 0, "the question is still open");
  await shot("chosen");

  at = "a question without choices keeps Antworten and Erledigt";
  await sign("dev");
  await ask("Stimmt der Titel so?");
  await sign("du");
  await open();
  const plain = await texts(question().locator(".mq button"));
  must(plain.includes("Antworten") && plain.includes("Erledigt"), `the plain question offers ${JSON.stringify(plain)}`);
  must(await question().locator(".mq.choices").count() === 0, "a question without choices shows choice buttons");
  await question().locator(".mq button", { hasText: "Erledigt" }).click();
  await page.waitForFunction(() => !document.querySelector(".msg.oq"), null, { timeout: 5000 });
  await shot("plain-question");

  at = "Etwas anderes keeps the free answer";
  await sign("dev");
  await ask("Wie weiter?\n\n1. Die Wörter so lassen\n2. Den Knopf weglassen\n");
  await sign("du");
  await open();
  await question().locator(".m-else").click();
  await question().locator(".m-form input").fill("Erst mit dem Team sprechen");
  await question().locator(".m-form button[type=submit]").click();
  await page.waitForFunction(() => !document.querySelector(".msg.oq"), null, { timeout: 5000 });
  must(((await page.locator(".msg").last().textContent()) ?? "").includes("Erst mit dem Team sprechen"), "the free answer is not in the conversation");
  await shot("something-else");
} catch (e) {
  issues.push(`${at}: ${e.message.split("\n")[0]}`);
  await page.screenshot({ path: join(out, "broken.png") }).catch(() => undefined);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
