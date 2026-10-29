// The gate (ADR-024) photographed: a case in each sample world, at 1440 light and dark and at 390, plus a measurement of
// what a design rule demands — targets ≥ 24 px, nothing hidden under the bar, no horizontal scroll at 390, the keyboard
// walking the whole gate. usage: node walks/gate-shot.mjs <base> <outdir> <workspace>:<case id>:<person> …
// Stage: control/demo/stage.py <worlds> <trees> <port> schadenakte-muster=claims pressroom-muster=pressroom …
import { chromium } from "playwright";
import { mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ...targets] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const browser = await chromium.launch({ executablePath: join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell") });
const issues = [];
const report = [];

async function open(ctx, ws, cid, person) {
  const page = await ctx.newPage();
  page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`${ws}/${cid}: pageerror ${e.message}`); });
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  await page.request.post(`${base}/w/${ws}/api/session`, { data: { person } });
  await page.request.post(`${base}/w/${ws}/api/session/lang`, { data: { lang: process.env.LANG_UI || "de" } });
  await page.goto(`${base}/w/${ws}/case/${encodeURIComponent(cid)}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".tor", { timeout: 20000 });
  await page.waitForTimeout(600);
  return page;
}

for (const t of targets) {
  const [ws, cid, person = "du"] = t.split(":");
  const tag = `${ws}-${cid.split("-").slice(0, 3).join("-")}`;
  for (const [scheme, width] of [["light", 1440], ["dark", 1440], ["light", 390]]) {
    const ctx = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 }, locale: "de-DE", colorScheme: scheme, isMobile: width === 390, hasTouch: width === 390 });
    const page = await open(ctx, ws, cid, person);
    // the phone's fixed menu bar and sheet are the shell, not the gate; a full-page photo would paint them mid-page
    if (width === 390) await page.addStyleTag({ content: ".menu, .scrim { display: none !important; }" });
    // on a desktop the main scrolls for itself: the photo takes the whole gate by growing the viewport to its height
    if (width === 1440) { const h = await page.evaluate(() => Math.min(4000, (document.querySelector(".gate-main")?.scrollHeight ?? 900) + 60)); await page.setViewportSize({ width, height: Math.max(900, h) }); await page.waitForTimeout(200); }
    await page.screenshot({ path: join(out, `${tag}-${width}-${scheme}.png`), fullPage: true });
    if (width === 1440) { await page.setViewportSize({ width, height: 900 }); await page.waitForTimeout(200); }
    if (width === 1440 && scheme === "light") {
      // measured, not claimed: every interactive element of the gate ≥ 24 px, the keyboard reaches it, nothing hides under the bar
      const m = await page.evaluate(() => {
        const bar = document.querySelector(".topbar")?.getBoundingClientRect().bottom ?? 0;
        const els = [...document.querySelectorAll(".gate-main button, .gate-main a[href], .gate-main input, .gate-main summary, .gate-main [tabindex='-1']")];
        const small = [], hidden = [];
        for (const el of els) {
          const r = el.getBoundingClientRect();
          if (r.width === 0 && r.height === 0) continue;
          if ((r.width < 24 || r.height < 24) && !el.matches("[tabindex='-1'], input[hidden]")) small.push(`${el.tagName.toLowerCase()}.${el.className} "${(el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 30)}" ${Math.round(r.width)}×${Math.round(r.height)}`);
        }
        return { bar, count: els.length, small, hidden, scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth };
      });
      report.push(`${tag}: ${m.count} targets, ${m.small.length} under 24 px${m.small.length ? ": " + m.small.join(" | ") : ""}`);
      // the keyboard walks the gate: Tab from the headline until focus leaves the main; every stop must be inside the viewport and below the bar
      await page.focus("#tor-h1");
      const stops = [];
      for (let i = 0; i < 80; i++) {
        await page.keyboard.press("Tab");
        const f = await page.evaluate(() => {
          const el = document.activeElement; if (!el || el === document.body) return null;
          const r = el.getBoundingClientRect(); const bar = document.querySelector(".topbar")?.getBoundingClientRect().bottom ?? 0;
          const main = document.querySelector(".gate-main");
          return { inMain: !!main && main.contains(el), tag: el.tagName.toLowerCase(), text: (el.textContent || el.getAttribute("aria-label") || el.getAttribute("placeholder") || "").trim().slice(0, 28), top: Math.round(r.top), bottom: Math.round(r.bottom), bar, vh: window.innerHeight, visible: r.height > 0 };
        });
        if (!f || !f.inMain) break;
        stops.push(f);
      }
      const covered = stops.filter((s) => s.visible && (s.top < s.bar || s.bottom > s.vh)).map((s) => `${s.tag} "${s.text}" ${s.top}–${s.bottom}`);
      report.push(`${tag}: keyboard ${stops.length} stops; under bar or off screen: ${covered.length}${covered.length ? " → " + covered.join(" | ") : ""}`);
      report.push(`${tag}: stops → ${stops.map((s) => `${s.tag}(${s.text})`).join(", ")}`);
    }
    if (width === 390) {
      const m = await page.evaluate(() => ({ scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth, torW: Math.round(document.querySelector(".tor")?.getBoundingClientRect().width ?? 0),
        wide: [...document.querySelectorAll(".gate-main *")].filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1).slice(0, 5).map((el) => `${el.tagName.toLowerCase()}.${el.className}`) }));
      report.push(`${tag} @390: scrollWidth ${m.scrollW} / viewport ${m.innerW}, gate ${m.torW} px wide${m.wide.length ? "; over the edge: " + m.wide.join(", ") : ""}`);
      if (m.scrollW > m.innerW) issues.push(`${tag}: horizontal scroll at 390 (${m.scrollW})`);
    }
    await ctx.close();
  }
}
writeFileSync(join(out, "measure.txt"), report.join("\n") + "\n");
console.log(report.join("\n"));
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
