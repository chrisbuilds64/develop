// The director: a whole flow played in the real surface, step by step — a visible pointer moves to the button and presses it.
// Flows belong to a demo suite and travel with its worlds (GET /api/demo/ablaeufe, only in sample workspaces). Starting one puts every workspace it touches
// back to its world (POST /api/demo/reset), signs the flow's person in, and opens the first page. The flow's place survives a
// page change (sessionStorage), so a flow walks from one application into the next. → / Space / PageDown: next step (the
// presenter's clicker); the bar's "Abläufe" or Shift+Alt+D: the list; Shift+Alt+C: captions on or off. There is no step back: the steps are real.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, BASE } from "../api";

type Step = { do: "go" | "open" | "press" | "type" | "read" | "close" | "follow" | "wait" | "show" | "say"; say: string;
  ws?: string; path?: string; case?: string; action?: string; text?: string; file?: string; target?: string; until?: "idle"; ms?: number;
  date?: number; amount?: string };                // press: a date (days from today) or an amount the action asks for, entered first
type Flow = { id: string; title: string; summary: string; person: string; workspaces: Record<string, string>; suite?: { id: string; title: string }; steps: Step[] };
type State = { flow: string; i: number; auto: boolean; captions: boolean };

const KEY = "cf.director";
const ROOT = BASE.replace(/\/w\/[^/]+$/, "");
const HERE = /\/w\/([^/]+)$/.exec(BASE)?.[1] ?? "";
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function load(): State | null {
  try { return JSON.parse(sessionStorage.getItem(KEY) || "null"); } catch { return null; }
}
function save(s: State | null) {
  try { if (s) sessionStorage.setItem(KEY, JSON.stringify(s)); else sessionStorage.removeItem(KEY); } catch { /* private window */ }
}

async function find(selector: string, ms = 20_000): Promise<HTMLElement> {
  const until = Date.now() + ms;
  while (Date.now() < until) {
    const el = document.querySelector<HTMLElement>(selector);
    if (el && !(el as HTMLButtonElement).disabled && el.getClientRects().length > 0) return el;
    await sleep(200);
  }
  throw new Error(`nicht gefunden: ${selector}`);
}

function caseInPath(): string | undefined {
  const m = /\/case\/([^/]+)/.exec(window.location.pathname);
  return m ? decodeURIComponent(m[1]) : undefined;
}

function navigate(path: string) {                   // inside this application: the router listens to popstate
  window.history.pushState(null, "", BASE + path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

async function fill(input: HTMLElement, value: string) {      // React reads the native setter, not .value
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  input.scrollIntoView({ block: "center" });
  setter.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(500);
}

export function Director() {
  const [flows, setFlows] = useState<Flow[] | null>(null);
  const [state, setState] = useState<State | null>(load);
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pointer = useRef<HTMLDivElement>(null);
  const running = useRef(false);

  useEffect(() => {                                   // the bar's "Abläufe" opens the list
    const on = () => setPicking(true);
    window.addEventListener("cf:director", on);
    return () => window.removeEventListener("cf:director", on);
  }, []);
  useEffect(() => {
    fetch(BASE + "/api/demo/ablaeufe", { credentials: "same-origin" }).then((r) => (r.ok ? r.json() : { flows: [] })).then((d) => setFlows(d.flows ?? [])).catch(() => setFlows([]));
  }, []);
  const flow = flows?.find((f) => f.id === state?.flow);
  const step = flow && state ? flow.steps[state.i] : undefined;
  const set = (s: State | null) => { save(s); setState(s); };

  const aim = async (el: HTMLElement, click = true) => {
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    await sleep(350);
    const r = el.getBoundingClientRect();
    const p = pointer.current;
    if (p) { p.style.opacity = "1"; p.style.transform = `translate(${r.left + r.width / 2}px, ${r.top + r.height / 2}px)`; }
    await sleep(750);
    el.classList.add("cf-dir-hit");
    setTimeout(() => el.classList.remove("cf-dir-hit"), 1200);
    if (click) { await sleep(250); el.click(); }
  };

  const perform = useCallback(async (s: Step, st: State): Promise<"next" | "away"> => {
    const away = (url: string) => { save({ ...st, i: st.i + 1 }); window.location.href = url; return "away" as const; };
    switch (s.do) {
      case "say":
        return "next";
      case "go":
        if (s.ws && s.ws !== HERE) return away(`${ROOT}/w/${s.ws}${s.path ?? "/"}`);
        navigate(s.path ?? "/");
        await sleep(600);
        return "next";
      case "open": {
        const card = await find(`a.card[href*="/case/${s.case}"]`).catch(() => null);
        if (card) await aim(card);
        else {
          const all = (await api.groups()).flatMap((g) => g.cases);
          const hit = all.find((c) => c.id.startsWith(s.case ?? "\u0000"));
          if (!hit) throw new Error(`keine Akte ${s.case}`);
          navigate(`/case/${encodeURIComponent(hit.id)}`);
        }
        await sleep(700);
        return "next";
      }
      case "press":
        if (s.date !== undefined) await fill(await find(".desk input[type=date]"), new Date(Date.now() + s.date * 86_400_000).toISOString().slice(0, 10));
        if (s.amount !== undefined) await fill(await find(".foot label.money input"), s.amount);
        await aim(await find(`[data-action="${s.action}"]`));
        await sleep(900);
        return "next";
      case "type": {
        // a secondary move is a chip that opens the thread's field; the case's main move carries its own field on the desk
        const chip = document.querySelector<HTMLElement>(`.chips [data-action="${s.action}"]`);
        if (chip) await aim(chip);
        const input = await find(chip ? ".thread form.ask input" : ".desk label.ask input");
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
        await aim(input, false);
        input.focus();
        for (let n = 1; n <= (s.text ?? "").length; n++) {
          setter.call(input, (s.text ?? "").slice(0, n));
          input.dispatchEvent(new Event("input", { bubbles: true }));
          await sleep(35);
        }
        await sleep(300);
        await aim(await find(chip ? ".thread form.ask button.send" : `.foot [data-action="${s.action}"]`));
        await sleep(900);
        return "next";
      }
      case "read":
        await aim(await find(`[data-file="${s.file}"]`));
        await sleep(500);
        return "next";
      case "close":
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
        await sleep(400);
        return "next";
      case "follow": {
        const link = await find(s.target ?? ".triage-done a");
        await aim(link, false);
        return away((link as HTMLAnchorElement).href);
      }
      case "show": {
        const el = await find(s.target ?? "main");
        await aim(el, false);
        return "next";
      }
      case "wait": {
        const id = caseInPath();
        const until = Date.now() + (s.ms ?? 60_000);
        while (id && Date.now() < until) {
          const v = await api.case(id);
          const files = new Set(v.slots.filter((x) => x.present).map((x) => x.file));
          if ((s.until !== "idle" || v.group !== "claude") && (!s.file || files.has(s.file))) break;
          await sleep(800);
        }
        window.dispatchEvent(new CustomEvent("casefile:refresh"));
        await sleep(900);
        return "next";
      }
    }
    return "next";
  }, []);

  const next = useCallback(async () => {
    const st = load();
    if (!st || !flow || running.current) return;
    const s = flow.steps[st.i];
    if (!s) { set(null); return; }
    running.current = true; setBusy(true); setError(null);
    try {
      const how = await perform(s, st);
      if (how === "away") return;
      const after = { ...st, i: st.i + 1 };
      set(after.i >= flow.steps.length ? { ...after, auto: false } : after);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      set({ ...st, auto: false });
    } finally {
      running.current = false; setBusy(false);
    }
  }, [flow, perform]);

  // auto: the next step after a pause; "wait" steps follow at once
  useEffect(() => {
    if (!state?.auto || busy || !flow || state.i >= flow.steps.length) return;
    const t = setTimeout(() => { next(); }, flow.steps[state.i]?.do === "wait" ? 300 : 3200);
    return () => clearTimeout(t);
  }, [state?.auto, state?.i, busy, flow, next]);

  const start = async (f: Flow) => {
    setPicking(false); setBusy(true); setError(null);
    try {
      for (const ws of Object.keys(f.workspaces)) {
        const r = await fetch(`${ROOT}/w/${ws}/api/demo/reset`, { method: "POST", credentials: "same-origin" });
        if (!r.ok) throw new Error(`${ws} lässt sich nicht zurücksetzen (${r.status})`);
        await fetch(`${ROOT}/w/${ws}/api/session`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ person: f.person }) });
      }
      const first = f.steps[0];
      const ws = first?.do === "go" && first.ws ? first.ws : HERE;
      save({ flow: f.id, i: first?.do === "go" ? 1 : 0, auto: false, captions: state?.captions ?? true });
      window.location.href = `${ROOT}/w/${ws}${first?.do === "go" ? first.path ?? "/" : "/"}`;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); setBusy(false);
    }
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.shiftKey && e.altKey && e.code === "KeyD") { e.preventDefault(); setPicking((p) => !p); return; }
      const st = load();
      if (e.shiftKey && e.altKey && e.code === "KeyC" && st) { e.preventDefault(); set({ ...st, captions: !st.captions }); return; }
      if (!st || !flow) return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") { e.preventDefault(); e.stopImmediatePropagation(); next(); }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [flow, next]);

  if (!flows || flows.length === 0) return null;
  const done = !!flow && !!state && state.i >= flow.steps.length;
  return (
    <>
      <div ref={pointer} className="cf-dir-pointer" aria-hidden="true"><svg viewBox="0 0 24 24" width="28" height="28"><path d="M4 2l16 10-7 1.5L9.5 21z" /></svg></div>
      {picking && (
        <div className="cf-dir-pick" role="dialog" aria-label="Abläufe">
          <div className="cf-dir-pick-head"><b>Ablauf vorführen</b><button type="button" onClick={() => setPicking(false)} aria-label="Schließen">×</button></div>
          <p className="cf-dir-note">Die beteiligten Muster-Workspaces werden dabei auf ihren Ausgangsstand gesetzt.</p>
          {flows.map((f, n) => (
            <div key={f.id}>
              {f.suite && f.suite.id !== flows[n - 1]?.suite?.id && <p className="cf-dir-suite">Suite · {f.suite.title}</p>}
              <button type="button" className="cf-dir-flow" data-flow={f.id} disabled={busy} onClick={() => start(f)}>
                <span className="t">{f.title}</span><span className="s">{f.summary}</span><span className="n">{f.steps.length} Schritte</span>
              </button>
            </div>
          ))}
          {error && <p className="cf-dir-error">{error}</p>}
        </div>
      )}
      {state && flow && (
        <div className={`cf-dir-panel${state.captions ? "" : " small"}`} role="region" aria-label="Vorführung">
          <div className="cf-dir-row">
            <span className="cf-dir-count">{flow.title} · {done ? "fertig" : `${state.i + 1}/${flow.steps.length}`}</span>
            <span className="cf-dir-tools">
              <button type="button" onClick={() => set({ ...state, captions: !state.captions })} title="Untertitel · Shift+Alt+C">{state.captions ? "Text aus" : "Text an"}</button>
              {!done && <button type="button" onClick={() => set({ ...state, auto: !state.auto })}>{state.auto ? "❚❚ Pause" : "▶ Automatisch"}</button>}
              <button type="button" onClick={() => set(null)} title="Beenden">×</button>
            </span>
          </div>
          {state.captions && <p className="cf-dir-say">{done ? "Ende des Ablaufs." : step?.say}</p>}
          {error && <p className="cf-dir-error">{error} — Schritt wiederholen mit Weiter.</p>}
          {!done ? <button type="button" className="cf-dir-next" disabled={busy} onClick={() => next()}>{busy ? (step?.do === "wait" ? "KI arbeitet …" : "…") : "Weiter →"}</button>
            : <button type="button" className="cf-dir-next" onClick={() => { set(null); setPicking(true); }}>Nächster Ablauf</button>}
        </div>
      )}
    </>
  );
}
