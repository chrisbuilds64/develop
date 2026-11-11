// A case's reference where people look for it (REQ-001 S-20; SW-2026-023). Shipyard at phone width: every row of the three
// tabs shows its reference beside the kind, under the title; the case head shows it beside the kind on a phone and on a
// desktop; every board card carries it; the search finds a case by its reference whole, in lower case and in part. A second
// application (PressRoom) shows references in list, board and head without pushing the title off the first line.
// A screenshot per step; exit 1 on the first thing that does not hold.
// usage: node walks/case-ref-shot.mjs <base> <outdir> [shipyard workspace] [second workspace]
import { chromium } from "playwright";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ship = "shipyard-muster", other = "pressroom-muster"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = existsSync(cache) && readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const pinned = shell && join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell");
const browser = await chromium.launch(pinned && existsSync(pinned) ? { executablePath: pinned } : {});
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: "de-DE" });
const page = await context.newPage();
const issues = [];
page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`pageerror: ${e.message}`); });
let at = "start";
let n = 0;
const shot = async (what) => { n += 1; await page.screenshot({ path: join(out, `${String(n).padStart(2, "0")}-${what}.png`) }); console.log(n, what); };
const must = (ok, what) => { if (!ok) throw new Error(what); };
const REF = /^[A-Z]+-[\w-]*\d/;

const sign = async (ws) => {
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  const people = (await (await page.request.get(`${base}/w/${ws}/api/config`)).json()).people.filter((p) => p.kind === "human");
  const person = (people.find((p) => p.id === "du") ?? people[0]).id;
  must((await page.request.post(`${base}/w/${ws}/api/session`, { data: { person } })).ok(), `cannot sign in as ${person}`);
  await page.request.post(`${base}/w/${ws}/api/session/lang`, { data: { lang: "de" } });
};
// every row of a tab: its reference beside the kind, and the title above it
const rows = async (ws, tab) => {
  await page.goto(`${base}/w/${ws}/group/${tab}`, { waitUntil: "networkidle" });
  await page.locator(".q-list").waitFor({ timeout: 5000 });
  const all = page.locator(".q-list .q");
  const count = await all.count();
  for (let i = 0; i < count; i++) {
    const row = all.nth(i);
    const ref = ((await row.locator(".qn .cref").textContent().catch(() => "")) ?? "").trim();
    must(REF.test(ref), `${ws} ${tab}: row ${i + 1} shows the reference "${ref}"`);
    const title = await row.locator(".qt").boundingBox();
    const sub = await row.locator(".qn").boundingBox();
    must(title && sub && title.y < sub.y, `${ws} ${tab}: row ${i + 1} does not read the title first`);
  }
  return count;
};
const head = async (ws, id, ref) => {
  await page.goto(`${base}/w/${ws}/case/${encodeURIComponent(id)}`, { waitUntil: "networkidle" });
  await page.locator(".c-head").waitFor({ timeout: 5000 });
  const got = ((await page.locator(".c-head .hkind .cref").textContent()) ?? "").trim();
  must(got === ref, `${ws}: the case head shows "${got}", not ${ref}`);
};
const board = async (ws) => {
  await page.goto(`${base}/w/${ws}/board`, { waitUntil: "networkidle" });
  const cards = page.locator(".wb-card");
  const count = await cards.count();
  must(count > 0, `${ws}: the board shows no card`);
  must(await page.locator(".wb-card .wb-m .cref").count() === count, `${ws}: not every board card shows its reference`);
};

try {
  at = "Shipyard list at phone width";
  await sign(ship);
  let total = 0;
  for (const tab of ["you", "others", "done"]) { total += await rows(ship, tab); await shot(`shipyard-${tab}`); }
  must(total >= 3, `the three tabs show ${total} rows, not every sample case`);

  at = "Shipyard case head at phone width";
  await head(ship, "SW-2026-002-another-sample", "SW-2026-002");
  must((await page.locator(".c-head .hkind").textContent())?.startsWith("Änderung"), "the reference does not stand beside the kind");
  await shot("shipyard-head-phone");

  at = "Shipyard at desktop width: head, board, search";
  await page.setViewportSize({ width: 1440, height: 900 });
  await head(ship, "SW-2026-002-another-sample", "SW-2026-002");
  await shot("shipyard-head-desktop");
  await board(ship);
  await shot("shipyard-board");
  for (const q of ["SW-2026-002", "sw-2026-002", "002"]) {
    await page.goto(`${base}/w/${ship}/`, { waitUntil: "networkidle" });
    const input = page.locator(".rail-search input");
    await input.click();
    await input.fill(q);
    const hits = page.locator(".search-pop button");
    await hits.first().waitFor({ timeout: 5000 });
    must((await hits.allTextContents()).some((t) => t.includes("Another sample")), `the search for "${q}" does not find SW-2026-002`);
  }
  await shot("shipyard-search");

  at = "a second application: list, board, head";
  await page.setViewportSize({ width: 390, height: 844 });
  await sign(other);
  const seen = await rows(other, "you") + await rows(other, "others");
  must(seen > 0, `${other}: no row to look at`);
  await shot("second-list-phone");
  const first = await page.request.get(`${base}/w/${other}/api/cases`).then((r) => r.json());
  const card = first.flatMap((g) => g.cases)[0];
  await head(other, card.id, card.ref);
  await shot("second-head-phone");
  await page.setViewportSize({ width: 1440, height: 900 });
  await board(other);
  await shot("second-board");

} catch (e) {
  issues.push(`${at}: ${e.message.split("\n")[0]}`);
  await page.screenshot({ path: join(out, "broken.png") }).catch(() => undefined);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
