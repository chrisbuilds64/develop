// The editor over a text file (REQ-001 S-14 – S-16, SW-2026-004). On a Shipyard case: the task opens in the editor from the
// reader; Esc without changes closes at once; ⌘B, ⌘I and ⌘K wrap the selection and ⌘K opens no search; a criteria line
// broken on purpose is named with its line before saving; Esc with changes asks, and "keep editing" keeps them; saving
// writes the next version, the reader shows it and the comparison names the changed lines. The thread offers no editor and
// the core refuses a save to it. Then on a PressRoom draft: the editor with the preview beside it, and the saved version
// in the reader. A screenshot per step; exit 1 on the first thing that does not hold.
// usage: node walks/text-editor-shot.mjs <base> <outdir> [shipyard workspace] [pressroom workspace]
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
const BROKEN = "- AC-9 · ENTW · maybe — x";

// select a word in the editor by its text
const select = (word) => area.evaluate((el, w) => { const i = el.value.indexOf(w); el.focus(); el.setSelectionRange(i, i + w.length); }, word);
// as "du" where the world has that person, else as the first person it names
const sign = async (w) => {
  await page.goto(`${base}/w/${w}/`, { waitUntil: "networkidle" });
  const people = (await (await page.request.get(`${base}/w/${w}/api/config`)).json()).people.filter((p) => p.kind === "human");
  const person = (people.find((p) => p.id === "du") ?? people[0]).id;
  must((await page.request.post(`${base}/w/${w}/api/session`, { data: { person } })).ok(), `cannot sign in to ${w} as ${person}`);
  await page.request.post(`${base}/w/${w}/api/session/lang`, { data: { lang: "en" } });
};

try {
  at = "open the task in the editor";
  await sign(ws);
  await page.goto(`${base}/w/${ws}/case/${CASE}`, { waitUntil: "networkidle" });
  await page.locator('.doc[data-file="task.md"]').click();
  await page.locator(".reader").waitFor({ timeout: 5000 });
  await page.locator(".ed-open").click();
  await sheet.waitFor({ timeout: 5000 });
  await page.waitForFunction(() => document.querySelector(".ed-sheet textarea")?.value.includes("Another sample"), null, { timeout: 5000 });

  at = "Esc without changes";
  await page.keyboard.press("Escape");
  await sheet.waitFor({ state: "hidden", timeout: 3000 });
  must(await page.locator(".reader").isVisible(), "Esc in an unchanged editor also closed the reader");
  must(page.url().includes("/case/"), "Esc in an unchanged editor left the case");

  at = "⌘B ⌘I ⌘K";
  await page.locator(".ed-open").click();
  await sheet.waitFor({ timeout: 5000 });
  await page.waitForFunction(() => document.querySelector(".ed-sheet textarea")?.value.includes("Another sample"), null, { timeout: 5000 });
  await area.evaluate((el) => { el.focus(); el.setSelectionRange(el.value.length, el.value.length); });
  await page.keyboard.type("\nbold italic link\n\n## Acceptance criteria\n\n- AC-1 · ENTW · yes/no — It opens.\n" + BROKEN + "\n");
  await select("bold"); await page.keyboard.press("ControlOrMeta+b");
  await select("italic"); await page.keyboard.press("ControlOrMeta+i");
  await select("link"); await page.keyboard.press("ControlOrMeta+k");
  const v = await area.inputValue();
  must(v.includes("**bold**"), "⌘B did not make the selection bold");
  must(v.includes("_italic_"), "⌘I did not make the selection italic");
  must(v.includes("[link](https://)"), "⌘K did not make the selection a link");
  must(await page.locator(".rail-search input:focus").count() === 0 && await sheet.isVisible(), "⌘K opened the search");

  at = "the broken criteria line";
  const bad = page.locator(".ed-bad-line");
  await bad.first().waitFor({ timeout: 5000 });
  const lineNo = (await area.inputValue()).split("\n").indexOf(BROKEN) + 1;
  const said = await bad.first().innerText();
  must(said.includes(`Line ${lineNo}`) && said.includes("maybe"), `the mark reads "${said}", not line ${lineNo} with its reason`);
  must(await page.locator(".ed-preview strong").first().innerText() === "bold", "the preview does not show the bold word");
  await shot("editor-marks");

  at = "Esc with changes";
  await page.keyboard.press("Escape");
  await page.locator(".ed-ask").waitFor({ timeout: 3000 });
  must(await sheet.isVisible(), "Esc with changes closed the editor without asking");
  await shot("asks");
  await page.locator(".ed-ask .ghost").first().click();                     // keep editing
  must((await area.inputValue()).includes("**bold**"), "keep editing lost the text");

  at = "fix the line and save";
  await area.evaluate((el, b) => { const i = el.value.indexOf(b); el.focus(); el.setSelectionRange(i, i + b.length); }, BROKEN);
  await page.keyboard.type("- AC-2 · TEST · evidence — A screenshot.");
  await bad.first().waitFor({ state: "detached", timeout: 5000 });
  const saved = page.waitForResponse((r) => r.request().method() === "POST" && /\/edit$/.test(r.url()), { timeout: 10000 });
  await page.keyboard.press("ControlOrMeta+s");
  const r = await saved;
  must(r.ok(), `saving was refused: ${r.status()} ${await r.text()}`);
  must((await r.json()).name === "task.v2.md", "saving did not write task.v2.md");
  await sheet.waitFor({ state: "hidden", timeout: 3000 });
  await page.locator(".reader-meta .versions [role=tab]").nth(1).waitFor({ timeout: 5000 });
  must((await page.locator(".reader-meta .versions [aria-selected=true]").innerText()).includes("2"), "the reader does not show the new version");
  await shot("saved-v2");

  at = "compare";
  await page.locator(".diff-toggle").click();
  await page.locator(".diff").waitFor({ timeout: 5000 });
  const removed = await page.locator(".diff-line.del").count();
  const added = await page.locator(".diff-line.add").allInnerTexts();
  must(removed === 0 && added.some((t) => t.includes("**bold**")) && added.some((t) => t.includes("AC-2")), `the comparison shows −${removed} and +${added.length}`);
  await shot("compare");

  at = "the thread is not editable";
  const refused = await page.request.post(`${base}/w/${ws}/api/cases/${CASE}/edit`, { data: { file: "review.md", text: "x", step_id: `walk-${Date.now()}` } });
  must(refused.status() === 403, `a save to review.md answered ${refused.status()}`);
  const slots = (await (await page.request.get(`${base}/w/${ws}/api/cases/${CASE}`)).json()).slots;
  must(!slots.some((s) => ["review.md", "meta.json"].includes(s.file) && s.editable), "the thread or meta.json is offered for editing");

  at = "a PressRoom draft with the preview beside it";
  await sign(press);
  const groups = await (await page.request.get(`${base}/w/${press}/api/cases`)).json();
  let draft = null;
  for (const id of [...new Set(groups.flatMap((g) => g.cases.map((c) => c.id)))]) {
    const cv = await (await page.request.get(`${base}/w/${press}/api/cases/${encodeURIComponent(id)}`)).json();
    const s = cv.slots.find((x) => x.present && x.editable && x.file.endsWith(".md"));
    if (s) { draft = { id, file: s.file }; break; }
  }
  must(draft, "no PressRoom case with an editable draft");
  await page.goto(`${base}/w/${press}/case/${encodeURIComponent(draft.id)}`, { waitUntil: "networkidle" });
  await page.locator(`.doc[data-file="${draft.file}"]`).click();
  await page.locator(".ed-open").click();
  await sheet.waitFor({ timeout: 5000 });
  await area.evaluate((el) => { el.focus(); el.setSelectionRange(0, 0); });
  await page.keyboard.type("**An edited opening line.**\n\n");
  await page.waitForFunction(() => document.querySelector(".ed-preview strong")?.textContent === "An edited opening line.", null, { timeout: 5000 });
  const [w1, w2] = await Promise.all([".ed-write", ".ed-preview"].map((s) => page.locator(s).boundingBox()));
  must(w1 && w2 && w2.x >= w1.x + w1.width - 1, "the preview is not beside the text on a wide screen");
  await shot("pressroom-editor-preview");
  await page.keyboard.press("ControlOrMeta+s");
  await sheet.waitFor({ state: "hidden", timeout: 5000 });
  await page.waitForFunction(() => document.querySelector(".reader-body .prose strong")?.textContent === "An edited opening line.", null, { timeout: 5000 });
  await shot("pressroom-v2-in-reader");
} catch (e) {
  issues.push(`${at}: ${e.message.split("\n")[0]}`);
  await shot("broken").catch(() => undefined);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
