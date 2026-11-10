// The loading state when entering a workspace (REQ-001 S-13, SW-2026-003): with the API slowed, the frame stands at once
// (rail column and main column, busy) while `me` and `config` wait; the queue shows five placeholder rows and Home three
// under a placeholder headline while their lists wait; the region is busy and says so to a screen reader; once the list
// is there the placeholders are gone. Once in light with motion, once with reduced motion (the bars stand still), once in
// dark (screenshot). A screenshot per step; exit 1 on the first thing that does not hold.
// usage: node walks/loading-state-shot.mjs <base> <outdir> [workspace]
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
const issues = [];
const must = (ok, what) => { if (!ok) throw new Error(what); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SLOW = 1500;
let at = "start";

// one visitor per pass: signed in, the theme set before the first paint, the lists (and once the configuration) slowed
async function visitor(name, { reducedMotion = "no-preference", theme = "light" } = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "de-DE", reducedMotion });
  await ctx.addInitScript((t) => { try { localStorage.setItem("shell-theme", t); } catch { /* none */ } }, theme);
  const page = await ctx.newPage();
  page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`${name} pageerror: ${e.message}`); });
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  await page.request.post(`${base}/w/${ws}/api/session`, { data: { person: "du" } });
  await page.request.post(`${base}/w/${ws}/api/session/lang`, { data: { lang: "de" } });
  for (const p of ["cases", "home"]) await page.route(new RegExp(`/w/${ws}/api/${p}(\\?|$)`), async (r) => { await sleep(SLOW); await r.continue(); });
  return page;
}

const bars = (page, scope) => page.evaluate((s) => [...document.querySelectorAll(`${s} .skel-bar`)].map((b) => {
  const c = getComputedStyle(b);
  return { name: c.animationName, hidden: b.closest("[aria-hidden=true]") !== null, w: b.getBoundingClientRect().width };
}), scope);

async function pass(name, opts) {
  const page = await visitor(name, opts);
  const shot = (what) => page.screenshot({ path: join(out, `${name}-${what}.png`) });

  // the frame, before the configuration is there
  at = `${name}: frame`;
  await page.route(new RegExp(`/w/${ws}/api/config(\\?|$)`), async (r) => { await sleep(800); await r.continue(); });
  const t0 = Date.now();
  await page.goto(`${base}/w/${ws}/group/you`, { waitUntil: "commit" });
  await page.locator(".app .main-col").waitFor({ timeout: 600 });
  must(await page.locator(".app .cf-rail").count() === 1, "the frame has no rail column");
  must(await page.locator(".app[aria-busy=true]").count() === 1, "the frame is not marked busy");
  must(Date.now() - t0 < 800, "the frame came only with the configuration");
  await shot("1-frame");
  await page.unroute(new RegExp(`/w/${ws}/api/config(\\?|$)`));

  // the queue: five placeholder rows, then the list
  at = `${name}: queue`;
  await page.locator(".q-list .q.skel").first().waitFor({ timeout: SLOW });
  must(await page.locator("a.q").count() === 0, "a real row came before the placeholders");
  must(await page.locator(".q-list .q.skel").count() === 5, `the queue shows ${await page.locator(".q-list .q.skel").count()} placeholder rows, not 5`);
  must(await page.locator(".q-list[aria-busy=true]").count() === 1, "the list is not marked busy while it loads");
  must(/geladen/.test(await page.locator(".q-list .sr").textContent() ?? ""), "the list does not say it is loading");
  const qb = await bars(page, ".q-list");
  must(qb.length >= 15 && qb.every((b) => b.hidden && b.w > 0), "a placeholder bar is missing, empty or not hidden from screen readers");
  if (opts?.reducedMotion === "reduce") must(qb.every((b) => b.name === "none"), "a bar still moves under reduced motion");
  else must(qb.every((b) => b.name !== "none"), "the bars do not pulse");
  await shot("2-queue-loading");
  await page.locator("a.q").first().waitFor({ timeout: SLOW * 3 });
  must(await page.locator(".q.skel").count() === 0, "placeholders stay beside the list");
  must(await page.locator(".q-list[aria-busy=true]").count() === 0, "the list stays busy");
  await shot("3-queue-loaded");

  // Home: a placeholder headline and three rows, then the real page
  at = `${name}: home`;
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "commit" });
  await page.locator(".home-wrap .row.skel").first().waitFor({ timeout: SLOW });
  must(await page.locator(".home-wrap .row.skel").count() === 3, `Home shows ${await page.locator(".home-wrap .row.skel").count()} placeholder rows, not 3`);
  must(await page.locator(".home-wrap .h1 .skel-bar").count() === 1, "Home has no placeholder headline");
  must(await page.locator(".home-wrap[aria-busy=true]").count() === 1, "Home is not marked busy while it loads");
  await shot("4-home-loading");
  await page.locator(".home-wrap .h1:not(:has(.skel-bar))").waitFor({ timeout: SLOW * 3 });
  must(await page.locator(".skel").count() === 0, "placeholders stay on Home");
  must(await page.locator(".home-wrap[aria-busy=true]").count() === 0, "Home stays busy");
  await shot("5-home-loaded");
  console.log(name, "· frame, queue and Home held");

  // a fast load goes straight to the list (no added delay): reported, not held — a slow machine is not a defect
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await page.addInitScript(() => {
    window.__skel = false;
    new MutationObserver(() => { if (document.querySelector(".skel")) window.__skel = true; }).observe(document, { subtree: true, childList: true });
  });
  await page.goto(`${base}/w/${ws}/group/you`, { waitUntil: "networkidle" });
  console.log(name, "· fast load showed placeholders:", await page.evaluate(() => window.__skel));
  await page.context().close();
}

try {
  await pass("light");
  await pass("reduced", { reducedMotion: "reduce" });
  await pass("dark", { theme: "dark" });
} catch (e) {
  issues.push(`${at}: ${e.message.split("\n")[0]}`);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
