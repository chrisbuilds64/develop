// The bar over every page: where you are (the way back to the cockpit, the workspace's whole name, the stage) and the support
// beside the work — the demonstrations, help for this page, the application's videos, putting a sample workspace back, the
// person's agents — and one menu button. The menu is a sheet (ADR-024, step 2): language, light/dark/system, sound, hand, who
// you are (sample worlds), start over, sign out; on a phone the support folds into it. It traps the focus, Esc closes it and
// gives the focus back to the button, and it leaves as soon as something is chosen.
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BASE, type ConfigView, type MeOut } from "../api";
import { VideoStage, type Video } from "./Explain";
import { Close, Globe, MenuIcon, Restart, Worlds } from "./Icons";
import { chime, setSound, soundOn } from "../moments";
import type { words } from "../words";

type Panel = { dock: (host: HTMLElement) => void; help: () => void };
const panel = () => (window as unknown as { agentPanel?: Panel }).agentPanel;
export type Theme = "light" | "dark" | "system";
export type Side = "left" | "right";

export function TopBar({ config, me, w, side, onSide, onFresh, onPerson, onLang, theme, onTheme, onSignOut }:
  { config: ConfigView; me: MeOut; w: ReturnType<typeof words>; side: Side; onSide: (s: Side) => void; onFresh: (world?: string) => void;
    onPerson: (person: string) => void; onLang: (lang: string) => void; theme: Theme; onTheme: (t: Theme) => void; onSignOut: () => void }) {
  const stage = document.querySelector<HTMLMetaElement>('meta[name="cf-stage"]')?.content ?? "";
  const t = config.theme as { demo?: boolean; resettable?: boolean };
  const videos = ((config as unknown as { videos?: Video[] }).videos ?? []);
  const flows = useQuery({ queryKey: ["flows"], queryFn: () => fetch(BASE + "/api/demo/ablaeufe", { credentials: "same-origin" }).then((r) => (r.ok ? r.json() : { flows: [] })), enabled: !!t.demo, staleTime: Infinity });
  const hasFlows = (flows.data?.flows?.length ?? 0) > 0;
  const [hasPanel, setHasPanel] = useState(!!panel());
  const [open, setOpen] = useState(false);
  const [videoList, setVideoList] = useState(false);
  const [playing, setPlaying] = useState<Video | null>(null);
  const [resetting, setResetting] = useState(false);
  const [sound, setSoundState] = useState(soundOn());
  const agents = useRef<HTMLSpanElement>(null);
  const sheet = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLButtonElement>(null);

  // the cockpit's panel script may arrive before or after this bar; whichever comes second docks the agents here
  useEffect(() => {
    const dock = () => { const p = panel(); if (p && agents.current) { p.dock(agents.current); setHasPanel(true); } };
    dock();
    window.addEventListener("agent-panel:ready", dock);
    return () => window.removeEventListener("agent-panel:ready", dock);
  }, []);
  useEffect(() => { document.body.classList.add("has-bar"); return () => document.body.classList.remove("has-bar"); }, []);

  const close = () => { setOpen(false); setTimeout(() => opener.current?.focus(), 0); };
  // the sheet holds the focus: the first control takes it, Tab stays inside, Esc closes (rule 20)
  useEffect(() => {
    if (!open) return;
    const el = sheet.current;
    if (!el) return;
    const focusables = () => [...el.querySelectorAll<HTMLElement>("button:not([disabled]), a[href], select, input:not([hidden]), [tabindex]:not([tabindex='-1'])")];
    focusables()[0]?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); e.stopImmediatePropagation(); close(); return; }
      if (e.key !== "Tab") return;
      const f = focusables();
      if (!f.length) return;
      const i = f.indexOf(document.activeElement as HTMLElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [open]);

  const reset = async () => {
    close();
    if (!t.resettable) { onFresh(); return; }                 // the public demo: a fresh sandbox
    if (!window.confirm(w.resetConfirm)) return;
    setResetting(true);
    const r = await fetch(BASE + "/api/demo/reset", { method: "POST", credentials: "same-origin" });
    if (r.ok) window.location.href = BASE + "/"; else { setResetting(false); window.alert(`${w.resetFailed} (${r.status})`); }
  };
  const video = () => { close(); if (videos.length === 1) setPlaying(videos[0]); else setVideoList(!videoList); };
  const support = (
    <>
      {hasFlows && <button type="button" className="bar-btn" onClick={() => { close(); window.dispatchEvent(new CustomEvent("cf:director")); }} title="Shift+Alt+D"><span className="i">▷</span><span>{w.flows}</span></button>}
      {hasPanel && <button type="button" className="bar-btn" onClick={() => { close(); panel()?.help(); }} title={w.helpHint}><span className="i">?</span><span>{w.help}</span></button>}
      {videos.length > 0 && <button type="button" className="bar-btn" onClick={video}><span className="i">▶</span><span>{videos.length === 1 ? w.video : w.videos(videos.length)}</span></button>}
      {t.demo && <button type="button" className="bar-btn" disabled={resetting} onClick={reset}><span className="i">↺</span><span>{resetting ? "…" : w.resetData}</span></button>}
    </>
  );
  const humans = config.people.filter((p) => p.kind === "human");
  const otherWorlds = me.worlds.filter((x) => x !== me.world);
  const themes: Theme[] = ["light", "dark", "system"];
  const themeWord = (k: Theme) => (k === "light" ? w.light : k === "dark" ? w.dark : w.themeSystem);

  return (
    <header className={`topbar hand-${side}`} data-help="cf.topbar">
      {me.shell ? <a className="bar-back" data-help="cf.back" href={me.shell} title={w.backToShell}><span aria-hidden="true">←</span><span className="wide-only">{w.backToShell}</span></a> : null}
      <span className="bar-name" title={config.product}>
        <svg width="20" height="17" viewBox="0 0 26 22" aria-hidden="true"><path d="M1 4h8l2 3h14v14H1z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
        <span className="t">{config.product}</span>
        {stage && <span className={`bar-stage ${stage}`}>{stage.toUpperCase()}</span>}
      </span>
      <span className="bar-support" data-help="cf.support">
        <span className="bar-items">{support}</span>
        <span ref={agents} className="bar-agents" />
        <button ref={opener} type="button" className="bar-btn bar-menu" data-help="cf.menu" onClick={() => (open ? close() : setOpen(true))} aria-expanded={open} aria-haspopup="dialog">
          <span className="i">{open ? <Close /> : <MenuIcon />}</span><span className="wide-only">{w.menu}</span>
        </button>
      </span>
      {videoList && videos.length > 1 && (
        <div className="bar-pop" role="menu">
          {videos.map((v) => <button key={v.key} type="button" onClick={() => { setVideoList(false); setPlaying(v); }}>▶ {v.title}</button>)}
        </div>
      )}
      {open && (
        <>
          <button type="button" className="bar-scrim" aria-label={w.close} tabIndex={-1} onClick={close} />
          <div ref={sheet} className="bar-sheet" role="dialog" aria-modal="true" aria-label={w.menu}>
            <div className="sheet-head"><b>{w.menu}</b><button type="button" className="sheet-close" aria-label={w.close} onClick={close}><Close /></button></div>
            {(hasFlows || hasPanel || videos.length > 0 || t.demo) && (
              <div className="sheet-support" aria-label={w.support}><span className="kicker">{w.support}</span>{support}</div>
            )}
            <button type="button" className="nav-row" data-help="cf.language" onClick={() => { onLang(config.lang === "de" ? "en" : "de"); close(); }} lang={config.lang === "de" ? "en" : "de"}>
              <span>{w.language}</span><span className="n">{w.otherLang} <Globe /></span>
            </button>
            <div className="nav-row" data-help="cf.theme" role="radiogroup" aria-label={w.theme}>
              <span>{w.theme}</span>
              <span className="seg">{themes.map((k) => <button key={k} type="button" role="radio" aria-checked={theme === k} className={`seg-btn${theme === k ? " on" : ""}`} onClick={() => onTheme(k)}>{themeWord(k)}</button>)}</span>
            </div>
            <button type="button" className="nav-row" data-help="cf.sound" aria-pressed={sound} onClick={() => { setSound(!sound); setSoundState(!sound); if (!sound) setTimeout(() => chime(), 30); }}>
              <span>{w.sound}</span><span className="n">{sound ? w.soundOn : w.soundOff}</span>
            </button>
            <div className="nav-row" data-help="cf.hand" role="radiogroup" aria-label={w.hand}>
              <span>{w.hand}</span>
              <span className="seg">{(["left", "right"] as Side[]).map((k) => <button key={k} type="button" role="radio" aria-checked={side === k} className={`seg-btn${side === k ? " on" : ""}`} onClick={() => onSide(k)}>{k === "left" ? w.handLeft : w.handRight}</button>)}</span>
            </div>
            {me.demo && humans.length > 1 && (
              <label className="nav-row" data-help-skip="public demo only"><span>{w.signInAs}</span>
                <select className="person-switch" value={me.person ?? ""} onChange={(e) => { onPerson(e.target.value); close(); }} aria-label={w.signInAs}>
                  {humans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </label>
            )}
            {me.demo && otherWorlds.map((x) => <button key={x} type="button" className="nav-row" data-help-skip="public demo only" onClick={() => { close(); onFresh(x); }}><span>{w.world(x)}</span><span className="n"><Worlds /></span></button>)}
            {me.demo && <button type="button" className="nav-row" data-help-skip="public demo only" onClick={() => { close(); onFresh(); }}><span>{w.startOver}</span><span className="n"><Restart /></span></button>}
            {!me.demo && <button type="button" className="nav-row" data-help="cf.sign-out" onClick={onSignOut}><span>{w.signOut}</span><span className="n">{me.name}</span></button>}
            <div className="who"><span className="avatar">{(me.name ?? "?").slice(0, 2).toUpperCase()}</span><span>{me.name}</span></div>
          </div>
        </>
      )}
      {playing && <VideoStage video={playing} onClose={() => setPlaying(null)} />}
    </header>
  );
}
