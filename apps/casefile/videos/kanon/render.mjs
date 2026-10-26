// Renders scene.html into ../../config/gatehouse/videos/kanon.mp4 and a poster. usage: node render.mjs  (needs playwright and ffmpeg)
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";
const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, "../../config/gatehouse/videos");
const tmp = mkdtempSync(join(tmpdir(), "kanon-"));
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: tmp, size: { width: 1280, height: 720 } }, deviceScaleFactor: 1 });
const p = await ctx.newPage();
await p.goto("file://" + join(here, "scene.html"));
await p.waitForFunction(() => document.title === "done", null, { timeout: 110000, polling: 500 });
await ctx.close(); await b.close();
const webm = join(tmp, readdirSync(tmp).find((f) => f.endsWith(".webm")));
// the stamp lands at 38.9 s in the scene (0.5 s are cut at the start) and the accept click at 34.3 s: the surface's own sound under both
const thud = join(tmp, "thud.wav");
execFileSync("python3", [join(here, "thud.py"), thud]);
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-ss", "0.5", "-i", webm, "-i", thud, "-i", thud,
  "-filter_complex", "[1]adelay=38400|38400,volume=1.0[a];[2]adelay=33800|33800,volume=0.35[b];[a][b]amix=inputs=2:normalize=0:duration=longest,apad=whole_dur=120[s]",
  "-map", "0:v", "-map", "[s]", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", "-preset", "slow", "-c:a", "aac", "-b:a", "96k",
  "-movflags", "+faststart", join(out, "kanon.mp4")]);
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-ss", "70", "-i", webm, "-frames:v", "1", "-q:v", "3", join(out, "kanon.jpg")]);
console.log("written", join(out, "kanon.mp4"));
