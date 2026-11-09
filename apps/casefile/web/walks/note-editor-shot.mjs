// The note editor (REQ-001 S-09): open it by a click, write two lines, close with Esc and stay on the case, reopen with ⌘J
// and find the draft, find it again after a reload, find no draft on another case, send with ⌘Enter and see the note in
// the thread. A screenshot per step; exit 1 on the first thing that does not hold.
// usage: node walks/note-editor-shot.mjs <base> <outdir> [workspace]
import { chromium } from "playwright";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ws = "posteingang-muster"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = existsSync(cache) && readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const pinned = shell && join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell");
const browser = await chromium.launch(pinned && existsSync(pinned) ? { executablePath: pinned } : {});
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "de-DE" })).newPage();
const issues = [];
page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`pageerror: ${e.message}`); });
let n = 0;
const shot = async (what) => { n += 1; await page.screenshot({ path: join(out, `${String(n).padStart(2, "0")}-${what}.png`) }); console.log(n, what); };
const sheet = page.locator(".nf-sheet");
const area = page.locator(".nf-sheet textarea");
const must = (ok, what) => { if (!ok) throw new Error(what); };
const DRAFT = "Walk note, line one\nline two";

try {
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  await page.request.post(`${base}/w/${ws}/api/session`, { data: { person: "du" } });
  const groups = await (await page.request.get(`${base}/w/${ws}/api/cases`)).json();
  const ids = [...new Set(groups.flatMap((g) => g.cases.map((c) => c.id)))];
  must(ids.length >= 2, `two cases needed, found ${ids.length}`);
  const open = (id) => page.goto(`${base}/w/${ws}/case/${encodeURIComponent(id)}`, { waitUntil: "networkidle" });

  await open(ids[0]);
  await page.locator(".i-ask .ask-open").click();
  await sheet.waitFor({ timeout: 5000 });
  must(await area.evaluate((el) => el === document.activeElement), "the editor opened without the cursor in it");
  await page.keyboard.type("Walk note, line one");
  await page.keyboard.press("Enter");
  await page.keyboard.type("line two");
  must(await sheet.isVisible(), "Enter closed the editor instead of starting a new line");
  must((await area.inputValue()) === DRAFT, "the two lines are not in the editor");
  await shot("written");

  await page.keyboard.press("Escape");
  await sheet.waitFor({ state: "hidden", timeout: 3000 });
  must(page.url().includes("/case/"), "Esc in the editor left the case");
  await shot("closed");

  await page.keyboard.press("ControlOrMeta+j");
  await sheet.waitFor({ timeout: 3000 });
  must((await area.inputValue()) === DRAFT, "⌘J reopened the editor without the draft");
  await page.keyboard.press("Escape");

  await page.reload({ waitUntil: "networkidle" });
  await page.keyboard.press("ControlOrMeta+j");
  await sheet.waitFor({ timeout: 3000 });
  must((await area.inputValue()) === DRAFT, "the draft did not survive the reload");
  await shot("after-reload");
  await page.keyboard.press("Escape");

  await open(ids[1]);
  await page.keyboard.press("ControlOrMeta+j");
  await sheet.waitFor({ timeout: 3000 });
  must((await area.inputValue()) === "", "another case shows this case's draft");
  await page.keyboard.press("Escape");

  await open(ids[0]);
  await page.keyboard.press("ControlOrMeta+j");
  await sheet.waitFor({ timeout: 3000 });
  const sent = page.waitForResponse((r) => r.request().method() === "POST" && /\/api\/cases\/[^/]+\/(runs|steps)$/.test(r.url()), { timeout: 10000 });
  await page.keyboard.press("ControlOrMeta+Enter");
  const r = await sent;
  must(r.ok(), `sending was refused: ${r.status()} ${await r.text()}`);
  await sheet.waitFor({ state: "hidden", timeout: 3000 });
  await page.waitForFunction(() => document.querySelector(".i-thread")?.textContent?.includes("line two"), null, { timeout: 10000 });
  await shot("sent");
  await page.keyboard.press("ControlOrMeta+j");
  await sheet.waitFor({ timeout: 3000 });
  must((await area.inputValue()) === "", "the draft was not cleared after sending");
} catch (e) {
  issues.push(e.message);
  await shot("broken").catch(() => undefined);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
