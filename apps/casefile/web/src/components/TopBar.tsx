// The bar over the page (design hand-back, 2026-11-05): where you are on the left; on the right the support beside the
// work — Guides (the application's videos), help for this page when the cockpit's panel is there, the demo's flows,
// Ask AI where a case is open, and light or dark. The person's agents dock here as before. Reset and the person's own
// settings moved to the person menu at the bottom of the rail.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { BASE, type ConfigView, type MeOut } from "../api";
import { VideoStage, type Video } from "./Explain";
import { MenuIcon, Play, Contrast } from "./Icons";
import type { words } from "../words";

type Panel = { dock: (host: HTMLElement) => void; help: () => void };
const panel = () => (window as unknown as { agentPanel?: Panel }).agentPanel;

export function TopBar({ config, w, crumb, canAsk, dark, onTheme, onMenu, views }: { config: ConfigView; me: MeOut; w: ReturnType<typeof words>; crumb: string; canAsk: boolean;
  dark: boolean; onTheme: () => void; onMenu: () => void; views?: ReactNode }) {
  const stage = document.querySelector<HTMLMetaElement>('meta[name="cf-stage"]')?.content ?? "";
  const theme = config.theme as { demo?: boolean };
  const videos = ((config as unknown as { videos?: Video[] }).videos ?? []);
  const flows = useQuery({ queryKey: ["flows"], queryFn: () => fetch(BASE + "/api/demo/ablaeufe", { credentials: "same-origin" }).then((r) => (r.ok ? r.json() : { flows: [] })), enabled: !!theme.demo, staleTime: Infinity });
  const hasFlows = (flows.data?.flows?.length ?? 0) > 0;
  const [hasPanel, setHasPanel] = useState(!!panel());
  const [videoList, setVideoList] = useState(false);
  const [playing, setPlaying] = useState<Video | null>(null);
  const agents = useRef<HTMLSpanElement>(null);
  const mac = /Mac|iPhone|iPad/.test(navigator.platform);

  useEffect(() => {
    const dock = () => { const p = panel(); if (p && agents.current) { p.dock(agents.current); setHasPanel(true); } };
    dock();
    window.addEventListener("agent-panel:ready", dock);
    return () => window.removeEventListener("agent-panel:ready", dock);
  }, []);
  useEffect(() => { document.body.classList.add("has-bar"); return () => document.body.classList.remove("has-bar"); }, []);
  const guides = () => { if (videos.length === 1) setPlaying(videos[0]); else setVideoList(!videoList); };
  const ask = () => document.querySelector<HTMLInputElement>(".i-ask input, .ask input, .ask textarea")?.focus();

  return (
    <header className="cf-bar" data-help="cf.topbar">
      <button type="button" className="bar-menu" data-help-skip="opens the rail on a phone" aria-label={w.menu} onClick={onMenu}><MenuIcon /></button>
      <span className="bar-crumb">{crumb}{stage && <span className={`bar-stage ${stage}`}>{stage.toUpperCase()}</span>}</span>
      {views}
      <span className="bar-right" data-help="cf.support">
        {videos.length > 0 && <button type="button" className="btn" onClick={guides} aria-expanded={videoList}><Play /><span>{w.guides}</span></button>}
        {hasPanel && <button type="button" className="btn" onClick={() => panel()?.help()} title={w.helpHint}><span className="i">?</span><span>{w.help}</span></button>}
        {hasFlows && <button type="button" className="btn" onClick={() => window.dispatchEvent(new CustomEvent("cf:director"))} title="Shift+Alt+D"><span>{w.flows}</span></button>}
        {canAsk && <button type="button" className="btn ai" data-help="cf.ask" onClick={ask}>✦ <span>{w.askAi}</span> <span className="kbd">{mac ? "⌘J" : "Ctrl J"}</span></button>}
        <button type="button" className="theme" data-help-skip="explained by cf.theme" aria-label={w.theme} title={dark ? w.light : w.dark} onClick={onTheme}><Contrast /></button>
        <span ref={agents} className="bar-agents" />
      </span>
      {videoList && videos.length > 1 && (
        <>
          <button type="button" className="pop-scrim" aria-label={w.close} onClick={() => setVideoList(false)} />
          <div className="cf-bar-pop" role="menu">
            {videos.map((v) => (
              <button key={v.key} type="button" onClick={() => { setVideoList(false); setPlaying(v); }}>
                {v.poster ? <img src={BASE + v.poster} alt="" /> : <span className="poster" />}
                <span><b>{v.title}</b><small>{v.seconds ? `${v.seconds} s` : ""}</small></span>
              </button>
            ))}
          </div>
        </>
      )}
      {playing && <VideoStage video={playing} onClose={() => setPlaying(null)} />}
    </header>
  );
}
