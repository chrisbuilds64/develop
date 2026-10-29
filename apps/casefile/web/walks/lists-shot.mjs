// The value lists page at one look: sign in as the operator, open /lists, screenshot at 1440 light; with "form", open the
// first list's entry form first; with "phone", also a 390 px shot.
// usage: node walks/lists-shot.mjs <base> <outdir> <workspace> <person> <name> [form] [phone]
import { chromium } from "playwright";
import { mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ws, person, name, ...flags] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const browser = await chromium.launch({ executablePath: join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell") });
const sizes = [["", { width: 1440, height: 1000 }], ...(flags.includes("phone") ? [["-390", { width: 390, height: 844 }]] : [])];
for (const [suffix, viewport] of sizes) {
  const page = await (await browser.newContext({ viewport, locale: "de-DE", colorScheme: "light" })).newPage();
  await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
  await page.request.post(`${base}/w/${ws}/api/session`, { data: { person } });
  await page.goto(`${base}/w/${ws}/lists`, { waitUntil: "networkidle" });
  await page.waitForSelector(".view-lists .list-head");
  if (flags.includes("form")) { await page.click(".list-head .btn >> nth=0"); await page.waitForSelector(".list-form"); }
  await page.screenshot({ path: join(out, `${name}${suffix}.png`) });
}
await browser.close();
console.log("ok");
