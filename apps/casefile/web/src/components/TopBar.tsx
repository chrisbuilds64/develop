// The bar over every page: where you are (the way back to the cockpit, the workspace's whole name, the stage) and the
// support beside the work — help for this page, the application's videos, the demonstrations, putting a sample workspace
// back, and the person's agents. On a phone the support folds into one button and opens as a sheet.
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BASE, type ConfigView, type MeOut } from "../api";
import { VideoStage, type Video } from "./Explain";
import { Swap } from "./Icons";
import type { words } from "../words";

type Panel = { dock: (host: HTMLElement) => void; help: () => void };
const panel = () => (window as unknown as { agentPanel?: Panel }).agentPanel;

export function TopBar({ config, me, w, onSwap, onFresh }: { config: ConfigView; me: MeOut; w: ReturnType<typeof words>; onSwap: () => void; onFresh: () => void }) {
  const stage = document.querySelector<HTMLMetaElement>('meta[name="cf-stage"]')?.content ?? "";
  const theme = config.theme as { demo?: boolean; resettable?: boolean };
  const videos = ((config as unknown as { videos?: Video[] }).videos ?? []);
  const flows = useQuery({ queryKey: ["flows"], queryFn: () => fetch(BASE + "/api/demo/ablaeufe", { credentials: "same-origin" }).then((r) => (r.ok ? r.json() : { flows: [] })), enabled: !!theme.demo, staleTime: Infinity });
  const hasFlows = (flows.data?.flows?.length ?? 0) > 0;
  const [hasPanel, setHasPanel] = useState(!!panel());
  const [sheet, setSheet] = useState(false);
  const [videoList, setVideoList] = useState(false);
  const [playing, setPlaying] = useState<Video | null>(null);
  const [resetting, setResetting] = useState(false);
  const agents = useRef<HTMLSpanElement>(null);

  // the cockpit's panel script may arrive before or after this bar; whichever comes second docks the agents here
  useEffect(() => {
    const dock = () => { const p = panel(); if (p && agents.current) { p.dock(agents.current); setHasPanel(true); } };
    dock();
    window.addEventListener("agent-panel:ready", dock);
    return () => window.removeEventListener("agent-panel:ready", dock);
  }, []);
  useEffect(() => { document.body.classList.add("has-bar"); return () => document.body.classList.remove("has-bar"); }, []);

  const reset = async () => {
    setSheet(false);
    if (!theme.resettable) { onFresh(); return; }                 // the public demo: a fresh sandbox
    if (!window.confirm(w.resetConfirm)) return;
    setResetting(true);
    const r = await fetch(BASE + "/api/demo/reset", { method: "POST", credentials: "same-origin" });
    if (r.ok) window.location.href = BASE + "/"; else { setResetting(false); window.alert(`${w.resetFailed} (${r.status})`); }
  };
  const video = () => { setSheet(false); if (videos.length === 1) setPlaying(videos[0]); else setVideoList(!videoList); };
  const items = (
    <>
      {hasPanel && <button type="button" className="bar-btn" onClick={() => { setSheet(false); panel()?.help(); }} title={w.helpHint}><span className="i">?</span><span>{w.help}</span></button>}
      {videos.length > 0 && <button type="button" className="bar-btn" onClick={video}><span className="i">▶</span><span>{videos.length === 1 ? w.video : w.videos(videos.length)}</span></button>}
      {hasFlows && <button type="button" className="bar-btn" onClick={() => { setSheet(false); window.dispatchEvent(new CustomEvent("cf:director")); }} title="Shift+Alt+D"><span className="i">▷</span><span>{w.flows}</span></button>}
      {theme.demo && <button type="button" className="bar-btn" disabled={resetting} onClick={reset}><span className="i">↺</span><span>{resetting ? "…" : w.resetData}</span></button>}
    </>
  );

  return (
    <header className="topbar" data-help="cf.topbar">
      {me.shell ? <a className="bar-back" data-help="cf.back" href={me.shell} title={w.backToShell}><span aria-hidden="true">←</span><span className="wide-only">{w.backToShell}</span></a> : null}
      <span className="bar-name" title={config.product}>
        <svg width="20" height="17" viewBox="0 0 26 22" aria-hidden="true"><path d="M1 4h8l2 3h14v14H1z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
        <span className="t">{config.product}</span>
        {stage && <span className={`bar-stage ${stage}`}>{stage.toUpperCase()}</span>}
      </span>
      <span className="bar-support" data-help="cf.support">
        <span className="bar-items">{items}</span>
        {(hasPanel || videos.length > 0 || hasFlows || theme.demo) && (
          <button type="button" className="bar-btn bar-more" onClick={() => setSheet(!sheet)} aria-expanded={sheet}><span className="i">?</span><span>{w.support}</span></button>
        )}
        <button type="button" className="bar-btn bar-swap wide-only" onClick={onSwap} aria-label={w.switchHand} title={w.switchHand}><Swap /></button>
        <span ref={agents} className="bar-agents" />
      </span>
      {videoList && videos.length > 1 && (
        <div className="bar-pop" role="menu">
          {videos.map((v) => <button key={v.key} type="button" onClick={() => { setVideoList(false); setPlaying(v); }}>▶ {v.title}</button>)}
        </div>
      )}
      {sheet && (
        <>
          <button type="button" className="bar-scrim" aria-label="×" onClick={() => setSheet(false)} />
          <div className="bar-sheet" role="menu" aria-label={w.support}>{items}</div>
        </>
      )}
      {playing && <VideoStage video={playing} onClose={() => setPlaying(null)} />}
    </header>
  );
}
