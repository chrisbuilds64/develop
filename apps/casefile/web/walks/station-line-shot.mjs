// The station line under a case's title (REQ-001 S-08, SW-2026-002): a Shipyard case in German, nine stations, at a line
// width of 480 and 780 px. No two station words touch; a word that does not fit its column is cut with an ellipsis and
// keeps the full word in its title; the current station's word is never cut; the line names every station. Once for the
// last station (Abgeschlossen beside PROD) and once for an early one. A screenshot per case and width; exit 1 on the first
// thing that does not hold.
// usage: node walks/station-line-shot.mjs <base> <outdir> [workspace]
import { chromium } from "playwright";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ws = "shipyard-muster"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = existsSync(cache) && readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const pinned = shell && join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell");
const browser = await chromium.launch(pinned && existsSync(pinned) ? { executablePath: pinned } : {});
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "de-DE" })).newPage();
const issues = [];
page.on("pageerror", (e) => { if (!/ViewTransition/.test(e.message)) issues.push(`pageerror: ${e.message}`); });
const must = (ok, what) => { if (!ok) throw new Error(what); };
const WORDS = ["Auftrag", "Umsetzung", "Prüfung", "Freigabe", "Release", "ENTW", "TEST", "PROD", "Abgeschlossen"];
const CASES = [["SW-2026-001-sample-change", "Abgeschlossen"], ["SW-2026-002-another-sample", "Umsetzung"]];
let at = "start";

// what the line shows, measured in the page: per station its word, title, box, its column's box and whether it is cut
const measure = () => page.evaluate(() => {
  const box = (el) => { const r = el.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom }; };
  const line = document.querySelector(".sline");
  return {
    width: line.getBoundingClientRect().width, label: line.getAttribute("aria-label") ?? "", line: box(line),
    st: [...line.querySelectorAll(".sst > span")].map((s) => {
      const em = s.querySelector("em");
      return { word: em.textContent, title: s.getAttribute("title") ?? "", now: s.classList.contains("now"), cell: box(s), em: box(em), cut: em.scrollWidth > em.clientWidth + 0.5 };
    }),
  };
});

try {
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  await page.request.post(`${base}/w/${ws}/api/session`, { data: { person: "du" } });
  await page.request.post(`${base}/w/${ws}/api/session/lang`, { data: { lang: "de" } });
  for (const [id, current] of CASES) {
    for (const width of [480, 780]) {
      at = `${id} at ${width} px`;
      await page.goto(`${base}/w/${ws}/case/${encodeURIComponent(id)}`, { waitUntil: "networkidle" });
      await page.locator(".sline").waitFor({ timeout: 5000 });
      await page.addStyleTag({ content: `.sline { width: ${width}px; max-width: ${width}px; }` });
      const m = await measure();
      must(Math.abs(m.width - width) < 1, `the line is ${m.width} px wide, not ${width}`);
      must(m.st.map((s) => s.word).join(",") === WORDS.join(","), `the stations read ${m.st.map((s) => s.word).join(", ")}`);
      const now = m.st.filter((s) => s.now);
      must(now.length === 1 && now[0].word === current, `the current station is ${now.map((s) => s.word).join(", ") || "none"}, not ${current}`);
      must(!now[0].cut, `the current station's word ${current} is cut`);
      for (const w of WORDS) must(m.label.includes(w), `the line's label "${m.label}" does not name ${w}`);
      m.st.forEach((s, i) => {
        must(s.title === s.word, `${s.word} carries the title "${s.title}"`);
        must(s.em.l >= m.line.l - 0.5 && s.em.r <= m.line.r + 0.5, `${s.word} leaves the line`);
        if (!s.now) must(s.em.l >= s.cell.l - 0.5 && s.em.r <= s.cell.r + 0.5, `${s.word} leaves its column`);
        for (const o of m.st.slice(i + 1)) {
          const apart = s.em.r <= o.em.l + 0.5 || o.em.r <= s.em.l + 0.5 || s.em.b <= o.em.t + 0.5 || o.em.b <= s.em.t + 0.5;
          must(apart, `${s.word} and ${o.word} overlap`);
        }
      });
      await page.locator(".sline").screenshot({ path: join(out, `${id}-${width}.png`) });
      console.log(at, "·", m.st.map((s) => `${s.word}${s.cut ? "…" : ""}`).join(" · "));
    }
  }
} catch (e) {
  issues.push(`${at}: ${e.message.split("\n")[0]}`);
  await page.screenshot({ path: join(out, "broken.png") }).catch(() => undefined);
}
console.log(issues.length ? issues.join("\n") : "clean");
await browser.close();
process.exit(issues.length ? 1 : 0);
