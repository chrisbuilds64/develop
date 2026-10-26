// The surface's few moments: presenting mode and the one sound. Sound only while presenting — never in the office by default.

export function presenting(): boolean {
  return typeof document !== "undefined" && document.documentElement.dataset.present !== undefined;
}

export function setPresenting(on: boolean): void {
  if (on) document.documentElement.dataset.present = ""; else delete document.documentElement.dataset.present;
  try { localStorage.setItem("cf.present", on ? "1" : "0"); } catch { /* private window */ }
}

export function initPresenting(): void {
  let on = new URLSearchParams(window.location.search).get("present");
  if (on === null) { try { on = localStorage.getItem("cf.present"); } catch { on = null; } }
  setPresenting(on === "1");
}

let ctx: AudioContext | null = null;

/** A stamp on paper: a short low thud with a dry top. Synthesised, no file. */
export function thud(): void {
  if (!presenting() || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  try {
    ctx = ctx ?? new AudioContext();
    const t = ctx.currentTime;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = "sine"; o.frequency.setValueAtTime(140, t); o.frequency.exponentialRampToValueAtTime(48, t + 0.18);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.55, t + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.28);
    o.connect(g).connect(ctx.destination); o.start(t); o.stop(t + 0.3);
    const n = ctx.createBufferSource(), buf = ctx.createBuffer(1, ctx.sampleRate * 0.06, ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length) ** 3;
    const ng = ctx.createGain(); ng.gain.value = 0.18; n.buffer = buf; n.connect(ng).connect(ctx.destination); n.start(t);
  } catch { /* no audio: the moment is still visible */ }
}
