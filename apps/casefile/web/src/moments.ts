// The surface's few moments: presenting mode and one family of sounds. Sound is on by default and switched off in the
// menu (Chris, 2026-10-26); the family: a low stamp for decisions, a dry click for progress, a rising tone for collecting,
// a paper swish for something put in. All synthesised, no files; reduced motion silences them too.

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

export function soundOn(): boolean {
  try { return localStorage.getItem("cf.sound") !== "0"; } catch { return true; }
}

export function setSound(on: boolean): void {
  try { localStorage.setItem("cf.sound", on ? "1" : "0"); } catch { /* private window */ }
}

function audio(): AudioContext | null {
  if (!soundOn() || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return null;
  try { ctx = ctx ?? new AudioContext(); if (ctx.state === "suspended") void ctx.resume(); return ctx; } catch { return null; }
}

function tone(c: AudioContext, at: number, from: number, to: number, dur: number, gain: number, type: OscillatorType = "sine"): void {
  const o = c.createOscillator(), g = c.createGain();
  o.type = type; o.frequency.setValueAtTime(from, at); o.frequency.exponentialRampToValueAtTime(to, at + dur * 0.6);
  g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(gain, at + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
  o.connect(g).connect(c.destination); o.start(at); o.stop(at + dur + 0.02);
}

function noise(c: AudioContext, at: number, dur: number, gain: number, lowpass?: number): void {
  const n = c.createBufferSource(), buf = c.createBuffer(1, Math.max(1, Math.floor(c.sampleRate * dur)), c.sampleRate), d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length) ** 2;
  const g = c.createGain(); g.gain.value = gain; n.buffer = buf;
  if (lowpass) { const f = c.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = lowpass; n.connect(f).connect(g).connect(c.destination); }
  else n.connect(g).connect(c.destination);
  n.start(at);
}

/** Progress: a dry click, the marker passing a station. */
export function tick(delay = 0): void {
  const c = audio(); if (!c) return;
  const t = c.currentTime + delay;
  tone(c, t, 1900, 1400, 0.035, 0.18, "triangle"); noise(c, t, 0.012, 0.08);
}

/** Collecting: two rising notes, warm, the reward picked up. Same low root as the stamp, an octave and a fifth above. */
export function chime(delay = 0): void {
  const c = audio(); if (!c) return;
  const t = c.currentTime + delay;
  tone(c, t, 523, 523, 0.22, 0.22); tone(c, t + 0.11, 784, 784, 0.42, 0.24); tone(c, t + 0.11, 1568, 1568, 0.3, 0.05);
}

/** Something put in: a short paper swish. */
export function paper(delay = 0): void {
  const c = audio(); if (!c) return;
  noise(c, c.currentTime + delay, 0.14, 0.22, 2600);
}

/** A stamp on paper: a short low thud with a dry top. Synthesised, no file. */
export function thud(delay = 0): void {
  const c0 = audio(); if (!c0) return;
  try {
    ctx = c0;
    const t = ctx.currentTime + delay;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = "sine"; o.frequency.setValueAtTime(140, t); o.frequency.exponentialRampToValueAtTime(48, t + 0.18);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.55, t + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.28);
    o.connect(g).connect(ctx.destination); o.start(t); o.stop(t + 0.3);
    noise(ctx, t, 0.06, 0.18);
  } catch { /* no audio: the moment is still visible */ }
}
