// The stack (ADR-024, step 2) photographed: the workspace's start page in each sample world at 1440 light and dark and at 390,
// plus named cases as the gate — and a measurement of what the design rules demand: targets ≥ 24 px, nothing hidden under the
// bar, no horizontal scroll at 390, the keyboard walking the whole column, exactly one surface framed in --your-move.
// usage: node walks/stack-shot.mjs <base> <outdir> <workspace>:<person>[:<case id>,<case id>] …
// Stage: control/demo/stage.py <worlds> <trees> <port> schadenakte-muster=claims pressroom-muster=pressroom gatehouse-muster=gatehouse
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

async function open(ctx, ws, person, path) {
  const page = await ctx.newPage();
  page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`${ws}${path}: pageerror ${e.message}`); });
  page.on("console", (m) => { if (m.type() === "error" && process.env.DEBUG) console.log(`console ${ws}${path}: ${m.text().slice(0, 200)}`); });
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  await page.request.post(`${base}/w/${ws}/api/session`, { data: { person } });
  await page.request.post(`${base}/w/${ws}/api/session/lang`, { data: { lang: process.env.LANG_UI || "de" } });
  await page.goto(`${base}/w/${ws}${path}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".stack-main .tor, .stack-main .leer", { timeout: 30000 }).catch(async (e) => {
    const seen = await page.evaluate(() => ({ gate: !!document.querySelector(".gate"), text: document.body.innerText.slice(0, 300) }));
    throw new Error(`${ws}${path}: ${e.message.split("\n")[0]} — sign-in screen: ${seen.gate}; text: ${seen.text}`);
  });
  await page.waitForTimeout(600);
  return page;
}

// measured, not claimed (rules 14, 20, 22)
async function measure(page, tag, width) {
  const m = await page.evaluate(() => {
    const bar = document.querySelector(".topbar")?.getBoundingClientRect().bottom ?? 0;
    const els = [...document.querySelectorAll(".stack-main button, .stack-main a[href], .stack-main input, .stack-main select, .stack-main summary")];
    const small = [];
    for (const el of els) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      if ((r.width < 24 || r.height < 24) && !el.matches("input[hidden]")) small.push(`${el.tagName.toLowerCase()}.${el.className} "${(el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 30)}" ${Math.round(r.width)}×${Math.round(r.height)}`);
    }
    // exactly one surface carries --your-move as its frame: the piece that waits for you
    const accent = getComputedStyle(document.documentElement).getPropertyValue("--your-move").trim();
    const probe = document.createElement("i"); probe.style.borderColor = accent; document.body.appendChild(probe);
    const want = getComputedStyle(probe).borderTopColor; probe.remove();
    const framed = [...document.querySelectorAll("*")].filter((el) => {
      const r = el.getBoundingClientRect(); if (r.width === 0 || r.height === 0) return false;
      const cs = getComputedStyle(el);
      return ["Top", "Left", "Right", "Bottom"].some((s) => cs[`border${s}Color`] === want && cs[`border${s}Style`] !== "none" && parseFloat(cs[`border${s}Width`]) > 0) || (cs.outlineColor === want && cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0);
    }).map((el) => `${el.tagName.toLowerCase()}.${el.className}`);
    const wide = [...document.querySelectorAll(".stack-main *")].filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1).slice(0, 5).map((el) => `${el.tagName.toLowerCase()}.${el.className}`);
    return { bar, count: els.length, small, framed, scrollW: document.documentElement.scrollWidth, mainW: document.querySelector(".stack-main")?.scrollWidth ?? 0, innerW: window.innerWidth, wide };
  });
  report.push(`${tag} @${width}: ${m.count} targets, ${m.small.length} under 24 px${m.small.length ? ": " + m.small.join(" | ") : ""}`);
  report.push(`${tag} @${width}: framed in --your-move: ${m.framed.length} → ${m.framed.join(", ") || "none"}`);
  // one frame at most, and exactly the piece when a move waits for the viewer; none when nothing does (POD-012 for Chris lies with Akhil)
  if (m.framed.length > 1 || (m.framed.length === 1 && m.framed[0] !== "article.tor du")) issues.push(`${tag} @${width}: ${m.framed.length} surfaces framed in --your-move (${m.framed.join(", ")})`);
  if (m.small.length) issues.push(`${tag} @${width}: ${m.small.length} targets under 24 px`);
  if (width === 390) {
    report.push(`${tag} @390: scrollWidth ${m.scrollW} / main ${m.mainW} / viewport ${m.innerW}${m.wide.length ? "; over the edge: " + m.wide.join(", ") : ""}`);
    if (m.scrollW > m.innerW || m.mainW > m.innerW) issues.push(`${tag}: horizontal scroll at 390 (${m.scrollW}/${m.mainW})`);
  }
  if (width === 1440) {
    // the keyboard walks the column: Tab from the head of the stack until the focus leaves the main; every stop inside the viewport and below the bar
    await page.focus("#stapel, #h-gruppe");
    const stops = [];
    for (let i = 0; i < 120; i++) {
      await page.keyboard.press("Tab");
      const f = await page.evaluate(() => {
        const el = document.activeElement; if (!el || el === document.body) return null;
        const r = el.getBoundingClientRect(); const bar = document.querySelector(".topbar")?.getBoundingClientRect().bottom ?? 0;
        const main = document.querySelector(".stack-main");
        return { inMain: !!main && main.contains(el), tag: el.tagName.toLowerCase(), text: (el.textContent || el.getAttribute("aria-label") || el.getAttribute("placeholder") || "").trim().slice(0, 24), top: Math.round(r.top), bottom: Math.round(r.bottom), bar, vh: window.innerHeight, visible: r.height > 0 };
      });
      if (!f || !f.inMain) break;
      stops.push(f);
    }
    const covered = stops.filter((s) => s.visible && (s.top < s.bar || s.bottom > s.vh)).map((s) => `${s.tag} "${s.text}" ${s.top}–${s.bottom}`);
    report.push(`${tag} @1440: keyboard ${stops.length} stops; under bar or off screen: ${covered.length}${covered.length ? " → " + covered.join(" | ") : ""}`);
    report.push(`${tag} @1440: stops → ${stops.map((s) => `${s.tag}(${s.text})`).join(", ")}`);
    if (covered.length) issues.push(`${tag}: ${covered.length} focus stops under the bar or off screen`);
  }
}

async function shoot(ws, person, path, tag, variants) {
  for (const [scheme, width] of variants) {
    const ctx = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 }, locale: "de-DE", colorScheme: scheme, isMobile: width === 390, hasTouch: width === 390 });
    const page = await open(ctx, ws, person, path);
    // on a desktop the column scrolls for itself: the photo takes the whole column by growing the viewport to its height
    if (width === 1440) { const h = await page.evaluate(() => Math.min(5000, (document.querySelector(".stack-main")?.scrollHeight ?? 900) + 60)); await page.setViewportSize({ width, height: Math.max(900, h) }); await page.waitForTimeout(200); }
    await page.screenshot({ path: join(out, `${tag}-${width}-${scheme}.png`), fullPage: true });
    if (width === 1440) { await page.setViewportSize({ width, height: 900 }); await page.waitForTimeout(200); }
    if (scheme === "light") await measure(page, tag, width);
    await ctx.close();
  }
}

for (const t of targets) {
  const [ws, person = "du", cases = ""] = t.split(":");
  await shoot(ws, person, "/", `${ws}-stack`, [["light", 1440], ["dark", 1440], ["light", 390]]);
  for (const cid of cases.split(",").filter(Boolean)) {
    await shoot(ws, person, `/case/${encodeURIComponent(cid)}`, `${ws}-${cid.split("-").slice(0, 3).join("-")}`, [["light", 1440], ["light", 390]]);
  }
}
writeFileSync(join(out, "measure.txt"), report.join("\n") + "\n");
console.log(report.join("\n"));
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
