// Free notes in every case (REQ-001 S-17, SW-2026-006). On a Shipyard case: "New note" asks for a title and opens the
// editor empty; saving shows the note in its own "Notes" group and in the reader; a second save shows version 2 beside
// version 1 and the comparison names the added line; the moves the case offers, and why they are blocked, are the same
// as before the note. Then the same on a PressRoom case. A screenshot per step; exit 1 on the first thing that does not hold.
// usage: node walks/notes-shot.mjs <base> <outdir> [shipyard workspace] [pressroom workspace]
import { chromium } from "playwright";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ws = "shipyard-muster", press = "pressroom-muster"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = existsSync(cache) && readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const pinned = shell && join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell");
const browser = await chromium.launch(pinned && existsSync(pinned) ? { executablePath: pinned } : {});
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "en-GB" })).newPage();
const issues = [];
page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`pageerror: ${e.message}`); });
let at = "start";
let n = 0;
const shot = async (what) => { n += 1; await page.screenshot({ path: join(out, `${String(n).padStart(2, "0")}-${what}.png`) }); console.log(n, what); };
const must = (ok, what) => { if (!ok) throw new Error(what); };
const sheet = page.locator(".ed-sheet");
const area = page.locator(".ed-sheet textarea");
const CASE = "SW-2026-002-another-sample";
const stamp = Date.now().toString(36);

const sign = async (w) => {
  await page.goto(`${base}/w/${w}/`, { waitUntil: "networkidle" });
  const people = (await (await page.request.get(`${base}/w/${w}/api/config`)).json()).people.filter((p) => p.kind === "human");
  const person = (people.find((p) => p.id === "du") ?? people[0]).id;
  must((await page.request.post(`${base}/w/${w}/api/session`, { data: { person } })).ok(), `cannot sign in to ${w} as ${person}`);
  await page.request.post(`${base}/w/${w}/api/session/lang`, { data: { lang: "en" } });
};
const moves = async (w, id) => {
  const v = await (await page.request.get(`${base}/w/${w}/api/cases/${encodeURIComponent(id)}`)).json();
  return JSON.stringify(v.turns.map((t) => [t.action, t.actor, t.blocked_by]));
};
const saveAs = async (want) => {
  const saved = page.waitForResponse((r) => r.request().method() === "POST" && /\/edit$/.test(r.url()), { timeout: 10000 });
  await page.keyboard.press("ControlOrMeta+s");
  const r = await saved;
  must(r.ok(), `saving was refused: ${r.status()} ${await r.text()}`);
  must((await r.json()).name === want, `saving did not write ${want}`);
  await sheet.waitFor({ state: "hidden", timeout: 5000 });
};
// "New note" with a title, the empty editor, the first save: the note stands in its group and opens in the reader
const firstNote = async (w, id, title, file) => {
  await page.goto(`${base}/w/${w}/case/${encodeURIComponent(id)}`, { waitUntil: "networkidle" });
  await page.locator(".c-notes .nn-open").click();
  await page.locator(".nn-form input").fill(title);
  await page.keyboard.press("Enter");
  await sheet.waitFor({ timeout: 5000 });
  must(await area.inputValue() === "", "the editor of a new note is not empty");
  await page.keyboard.type(`# ${title}\n\nFirst thought.`);
  await saveAs(file);
  await page.waitForFunction(() => document.querySelector(".reader-body .prose")?.textContent?.includes("First thought."), null, { timeout: 5000 });
};

try {
  at = "a new note in a Shipyard case";
  await sign(ws);
  const before = await moves(ws, CASE);
  const title = `Walk note ${stamp}`;
  const file = `notes/walk-note-${stamp}.md`;
  await page.goto(`${base}/w/${ws}/case/${CASE}`, { waitUntil: "networkidle" });
  await page.locator(".c-notes").waitFor({ timeout: 5000 });
  await shot("notes-group");
  await firstNote(ws, CASE, title, file);
  await shot("note-v1-in-reader");

  at = "the note in its group";
  await page.keyboard.press("Escape");
  const tile = page.locator(`.c-notes .doc[data-file="${file}"]`);
  await tile.waitFor({ timeout: 5000 });
  must((await tile.innerText()).includes(title), "the note's tile does not carry its title");

  at = "a second version";
  await tile.click();
  await page.locator(".ed-open").click();
  await sheet.waitFor({ timeout: 5000 });
  await page.waitForFunction(() => document.querySelector(".ed-sheet textarea")?.value.includes("First thought."), null, { timeout: 5000 });
  await area.evaluate((el) => { el.focus(); el.setSelectionRange(el.value.length, el.value.length); });
  await page.keyboard.type("\n\nSecond thought.");
  await saveAs(file.replace(/\.md$/, ".v2.md"));
  await page.locator(".reader-meta .versions [role=tab]").nth(1).waitFor({ timeout: 5000 });
  must(await page.locator(".reader-meta .versions [role=tab]").count() === 2, "the reader does not show two versions");
  must((await page.locator(".reader-meta .versions [aria-selected=true]").innerText()).includes("2"), "the reader does not show version 2");
  await page.locator(".diff-toggle").click();
  await page.locator(".diff").waitFor({ timeout: 5000 });
  const added = await page.locator(".diff-line.add").allInnerTexts();
  must(added.some((t) => t.includes("Second thought.")) && await page.locator(".diff-line.del").count() === 0, "the comparison does not show the added line");
  await shot("note-v2-compare");

  at = "the note changes no move";
  must(await moves(ws, CASE) === before, "a note changed the moves the case offers or why they are blocked");
  const view = await (await page.request.get(`${base}/w/${ws}/api/cases/${CASE}`)).json();
  must(!view.slots.some((s) => s.file.startsWith("notes/")), "a note shows up among the slots");

  at = "a new note in a PressRoom case";
  await sign(press);
  const groups = await (await page.request.get(`${base}/w/${press}/api/cases`)).json();
  const pid = groups.flatMap((g) => g.cases.map((c) => c.id))[0];
  must(pid, "no PressRoom case");
  const pbefore = await moves(press, pid);
  await firstNote(press, pid, title, file);
  await page.keyboard.press("Escape");
  await page.locator(`.c-notes .doc[data-file="${file}"]`).waitFor({ timeout: 5000 });
  must(await moves(press, pid) === pbefore, "a note changed the moves of the PressRoom case");
  await shot("pressroom-note");
} catch (e) {
  issues.push(`${at}: ${e.message.split("\n")[0]}`);
  await shot("broken").catch(() => undefined);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
