// A new case from the editor (REQ-001 S-18, C-09; REQ-002 SW-15; SW-2026-007). In Shipyard, PressRoom and Schadenakte the
// button is in the bar at 1280 px and at 390 px, and a person without a role that starts cases does not see it. In
// Shipyard: the rail's entry opens the same editor; a title, a Markdown description and two screenshots pasted with ⌘V
// (both called "image.png" by the browser) become two files of different names; the case opens in Shipyard, the first
// entry shows the picture, and the first action offered is the task helper. In PressRoom a case made the same way opens
// there and is offered nothing extra. A screenshot per step; exit 1 on the first thing that does not hold.
// usage: node walks/new-case-shot.mjs <base> <outdir> [shipyard workspace] [pressroom workspace] [claims workspace]
import { chromium } from "playwright";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ship = "shipyard-muster", press = "pressroom-muster", claims = "schadenakte-muster"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = existsSync(cache) && readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const pinned = shell && join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell");
const browser = await chromium.launch(pinned && existsSync(pinned) ? { executablePath: pinned } : {});
const context = await browser.newContext({ viewport: { width: 1280, height: 860 }, locale: "en-GB" });
const page = await context.newPage();
const issues = [];
page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`pageerror: ${e.message}`); });
let at = "start";
let n = 0;
const shot = async (what) => { n += 1; await page.screenshot({ path: join(out, `${String(n).padStart(2, "0")}-${what}.png`) }); console.log(n, what); };
const must = (ok, what) => { if (!ok) throw new Error(what); };
const PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==";
const button = page.locator(".nc-open:visible");
const sheet = page.locator(".nc-sheet");

// as `who`, else "du" where the world has that person, else as the first person it names
const sign = async (w, who) => {
  await page.goto(`${base}/w/${w}/`, { waitUntil: "networkidle" });
  const people = (await (await page.request.get(`${base}/w/${w}/api/config`)).json()).people.filter((p) => p.kind === "human");
  const person = who ?? (people.find((p) => p.id === "du") ?? people[0]).id;
  must((await page.request.post(`${base}/w/${w}/api/session`, { data: { person } })).ok(), `cannot sign in to ${w} as ${person}`);
  await page.request.post(`${base}/w/${w}/api/session/lang`, { data: { lang: "en" } });
};
const list = async (w) => { await page.goto(`${base}/w/${w}/group/you`, { waitUntil: "networkidle" }); };
// a picture on the clipboard, pasted where the cursor is — what ⌘V does with a screenshot
const paste = () => page.locator(".nc-sheet textarea").evaluate((el, b64) => {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const dt = new DataTransfer();
  dt.items.add(new File([bytes], "image.png", { type: "image/png" }));
  el.focus();
  el.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
}, PNG);

try {
  for (const w of [ship, press, claims]) {
    at = `the button in ${w}`;
    await sign(w);
    for (const [width, height] of [[1280, 860], [390, 844]]) {
      await page.setViewportSize({ width, height });
      await list(w);
      await button.first().waitFor({ timeout: 5000 });
      const box = await button.first().boundingBox();
      must(box && box.x >= 0 && box.x + box.width <= width + 1, `the button is outside the bar at ${width} px in ${w}`);
      await shot(`button-${w}-${width}`);
    }
    await page.setViewportSize({ width: 1280, height: 860 });
  }

  at = "no role, no button";
  await sign(claims, "gutachter");
  await list(claims);
  must(await page.locator(".nc-open").count() === 0, "a person without a role that starts cases sees the button");
  await shot("no-button-without-role");

  at = "the rail opens the same editor";
  await sign(ship);
  await list(ship);
  await page.locator('.cf-rail [data-help="cf.new-case"]').click();
  await sheet.waitFor({ timeout: 3000 });
  must(await page.locator(".rail-new").count() === 0, "the rail still has its own form");
  await page.keyboard.press("Escape");
  await sheet.waitFor({ state: "hidden", timeout: 3000 });
  must(page.url().includes("/group/"), "Esc in an empty editor left the page");

  at = "title, description, two pasted screenshots";
  await button.first().click();
  await sheet.waitFor({ timeout: 3000 });
  await page.keyboard.type("Paste a screenshot");
  await page.locator(".nc-sheet textarea").click();
  await page.keyboard.type("What I saw, **twice**:\n\n");
  await paste();
  await paste();
  const v = await page.locator(".nc-sheet textarea").inputValue();
  must(v.includes("![](screenshot.png)") && v.includes("![](screenshot-2.png)"), `the pasted pictures are not in the text: ${v}`);
  must(await page.locator(".nc-file").count() === 2, "two pasted pictures are not two files");
  await page.locator(".ed-preview .md-img").first().waitFor({ timeout: 3000 });
  must(await page.locator(".ed-preview strong").first().innerText() === "twice", "the preview does not render the Markdown");
  await shot("editor-with-pictures");

  at = "create in Shipyard";
  await page.keyboard.press("ControlOrMeta+Enter");
  await page.waitForURL(new RegExp(`/w/${ship}/case/SW-`), { timeout: 8000 });
  const first = page.locator(".msg").first();
  await first.locator(".md-img").first().waitFor({ timeout: 5000 });
  must(await first.locator(".md-img").first().evaluate((img) => img.complete && img.naturalWidth > 0), "the picture in the first entry does not load");
  must((await first.locator(".m-files").innerText()).includes("screenshot-2.png"), "the first entry does not list the files");
  const cid = decodeURIComponent(page.url().split("/case/")[1].split("?")[0]);
  const files = (await (await page.request.get(`${base}/w/${ship}/api/cases/${encodeURIComponent(cid)}`)).json()).entries[0].files;
  must(JSON.stringify(files) === JSON.stringify(["screenshot.png", "screenshot-2.png"]), `the case's files are ${files}`);
  const offered = page.locator("button.primary[data-action]").first();
  await offered.waitFor({ timeout: 5000 });
  must(await offered.getAttribute("data-action") === "draft_task", `the first action offered is ${await offered.getAttribute("data-action")}`);
  await shot("shipyard-case-opened");

  at = "create in PressRoom";
  await sign(press);
  await list(press);
  await button.first().click();
  await sheet.waitFor({ timeout: 3000 });
  await page.keyboard.type("A post about gates");
  await page.locator(".nc-sheet .nc-make").click();
  await page.waitForURL(new RegExp(`/w/${press}/case/`), { timeout: 8000 });
  const pid = decodeURIComponent(page.url().split("/case/")[1].split("?")[0]);
  const view = await (await page.request.get(`${base}/w/${press}/api/cases/${encodeURIComponent(pid)}`)).json();
  must(view.entries[0].text === "A post about gates", "a title-only case does not start with its title");
  const natural = view.my_turns.filter((t) => !["answer", "wait"].includes(t.action))[0]?.action;
  const shown = await page.locator("button.primary[data-action]").first().getAttribute("data-action").catch(() => undefined);
  must(!natural || shown === natural, `PressRoom offers ${shown}, its own first move is ${natural}`);
  await shot("pressroom-case-opened");

  must(issues.length === 0, issues.join("; "));
  console.log("clean");
} catch (e) {
  await shot("failed").catch(() => undefined);
  console.log(`failed at "${at}": ${e.message}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
