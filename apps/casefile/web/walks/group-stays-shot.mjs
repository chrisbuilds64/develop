// A case opened from a group keeps the group beside it: pick "others" in the menu, open a case, the list stays.
// usage: node walks/group-stays-shot.mjs <base> <outdir> <workspace> <group key>
import { chromium } from "playwright";
import { mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const [base, out, ws, key] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const cache = join(homedir(), "Library/Caches/ms-playwright");
const shell = readdirSync(cache).find((d) => d.startsWith("chromium_headless_shell"));
const browser = await chromium.launch({ executablePath: join(cache, shell, "chrome-headless-shell-mac-arm64", "chrome-headless-shell") });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "de-DE" })).newPage();
await page.goto(`${base}/w/${ws}/`, { waitUntil: "networkidle" });
await page.request.post(`${base}/w/${ws}/api/session`, { data: { person: "du" } });
await page.goto(`${base}/w/${ws}/group/${key}`, { waitUntil: "networkidle" });
const head = await page.locator("section.list h2").textContent();
await page.locator("section.list a.card").nth(1).click();
await page.waitForTimeout(1200);
const after = await page.locator("section.list h2").textContent().catch(() => "(no group heading)");
const menuOn = await page.locator(".nav-row.on").first().textContent();
await page.screenshot({ path: join(out, "after-click.png") });
console.log(JSON.stringify({ url: page.url(), head, after, menuOn }));
await browser.close();
process.exit(head === after ? 0 : 1);
