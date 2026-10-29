// The restyle, photographed: start page, a claims case, board, list, a PressRoom case with many files — 1440 light and dark,
// 390 light. Measures what the rules demand: targets ≥ 24 px (the line's pins, chips), the focus never under a fixed bar or
// the foot, no horizontal overflow at 390. usage: node walks/restyle-shot.mjs <base> <outdir> [claims ws] [claims case] [press ws] [press case]
import { chromium } from "playwright";
import { mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, cws = "schadenakte-muster", ccase = "HR-2026-0417-wasserschaden-badezimmer", pws = "pressroom-muster", pcase = "POD-SIM-01-i-build-the-kind-of-thing"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const browser = await chromium.launch({ executablePath: join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell") });
const issues = [];
const shots = [["start", `/w/${cws}/`, cws, "du"], ["case", `/w/${cws}/case/${ccase}`, cws, "du"], ["board", `/w/${cws}/board`, cws, "du"], ["list", `/w/${cws}/list`, cws, "du"], ["press", `/w/${pws}/case/${pcase}`, pws, "chris"]];
// one session cookie per host: sign in to the workspace right before its shot
const signIn = async (page, ws, person) => { await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" }); await page.request.post(`${base}/w/${ws}/api/session`, { data: { person } }); };

for (const [tag, width, height, scheme] of [["1440-light", 1440, 900, "light"], ["1440-dark", 1440, 900, "dark"], ["390-light", 390, 844, "light"]]) {
  const page = await (await browser.newContext({ viewport: { width, height }, locale: "de-DE", colorScheme: scheme })).newPage();
  page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`${tag} pageerror: ${e.message}`); });
  for (const [name, path, ws, person] of shots) {
    await signIn(page, ws, person);
    await page.goto(`${base}${path}`, { waitUntil: "networkidle" });
    await page.waitForSelector(".case-head, .view-head, .list h2", { timeout: 15000 }).catch(() => issues.push(`${tag} ${name}: nothing rendered`));
    await page.waitForTimeout(700);
    await page.screenshot({ path: join(out, `${name}-${tag}.png`) });
    // targets: the line's pins and every chip carry at least 24 px in both directions
    const small = await page.evaluate(() => [...document.querySelectorAll(".line .st i, .chip, .foot .btn, .nav-row, .card")].map((el) => {
      const r = el.getBoundingClientRect(); return r.width > 0 && (r.width < 24 || r.height < 24) ? `${el.className} ${Math.round(r.width)}×${Math.round(r.height)}` : null;
    }).filter(Boolean));
    for (const s of small) issues.push(`${tag} ${name}: target < 24 px: ${s}`);
    // overflow: nothing wider than the phone
    const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (over > 0) issues.push(`${tag} ${name}: horizontal overflow ${over} px`);
  }
  // focus: tab through the case; the focused element is never under the fixed foot, the bottom menu or the top bar
  await signIn(page, cws, "du");
  await page.goto(`${base}/w/${cws}/case/${ccase}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".case-head", { timeout: 15000 }).catch(() => issues.push(`${tag} focus walk: nothing rendered`));
  await page.waitForTimeout(500);
  let hidden = 0;
  for (let n = 0; n < 40; n++) {
    await page.keyboard.press("Tab");
    const r = await page.evaluate(() => {
      const a = document.activeElement; if (!a || a === document.body) return null;
      const b = a.getBoundingClientRect();
      const covers = [...document.querySelectorAll(".foot, .menu, .cf-bar, .topbar")].filter((el) => ["fixed", "sticky"].includes(getComputedStyle(el).position)).map((el) => el.getBoundingClientRect());
      const under = covers.some((c) => c.width > 0 && b.bottom > c.top && b.top < c.bottom && b.right > c.left && b.left < c.right && !a.closest(".foot, .menu, .cf-bar, .topbar"));
      return { under, tag: a.tagName + "." + a.className, top: Math.round(b.top), bottom: Math.round(b.bottom), vh: innerHeight };
    });
    if (r?.under) { hidden++; issues.push(`${tag} focus under a bar: ${r.tag} ${r.top}–${r.bottom} of ${r.vh}`); }
    if (n === 6) await page.screenshot({ path: join(out, `focus-${tag}.png`) });
  }
  console.log(tag, "focus hidden:", hidden);
  await page.context().close();
}
await browser.close();
console.log(issues.length ? issues.join("\n") : "clean");
process.exit(issues.length ? 1 : 0);
