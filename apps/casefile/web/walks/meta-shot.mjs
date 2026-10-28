// A case's details at one press: open a case, press "Kopfdaten", screenshot table and raw view.
// usage: node walks/meta-shot.mjs <base> <outdir> <workspace> <case id>
import { chromium } from "playwright";
import { mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ws, cid] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const browser = await chromium.launch({ executablePath: join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell") });
for (const scheme of ["light", "dark"]) {
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 820 }, locale: "de-DE", colorScheme: scheme })).newPage();
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  await page.request.post(`${base}/w/${ws}/api/session`, { data: { person: "du" } });
  await page.goto(`${base}/w/${ws}/case/${cid}`, { waitUntil: "networkidle" });
  await page.click('[data-meta="open"]');
  await page.waitForSelector(".meta-card");
  await page.screenshot({ path: join(out, `meta-${scheme}.png`) });
  if (scheme === "light") { await page.click(".meta-card header button >> nth=0"); await page.screenshot({ path: join(out, "meta-raw.png") }); }
}
await browser.close();
console.log("ok");
