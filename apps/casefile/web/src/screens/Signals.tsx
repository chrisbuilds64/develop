// Flagged (design hand-back, 2026-11-05): what the pattern helper noticed across the cases, as hints. Three groups: to check,
// looking into it, done. Each hint says what kind it is (a possible duplicate, a repeat, an unusual amount), why, and the
// cases it rests on. A person moves it: look into it, nothing to do, mark as done, move back. The hint is never changed or
// deleted; only its status, with who and when (POST /api/signals/{id}/status).
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type ConfigView, type SignalOut } from "../api";
import { VideoStage, type Video } from "../components/Explain";
import type { words } from "../words";

type W = ReturnType<typeof words>;
type Kind = "dup" | "rep" | "dev";
const ORDER: Kind[] = ["dup", "rep", "dev"];

export function kindOf(kind: string): Kind {
  if (/dubl|doppel|duplic/i.test(kind)) return "dup";
  if (/abweich|deviat|betrag|amount|ungewöhn|unusual/i.test(kind)) return "dev";
  return "rep";
}
/** The reasoning without the closing line every hint carries ("a hint, not a finding"): the page says that once, on top. */
const why = (text: string) => text.split(/\n\s*\n/).map((p) => p.trim()).filter((p) => p && !/^\*.*\*$/.test(p)).join("\n\n");

function Icon({ k }: { k: Kind }) {
  const path = k === "dup"
    ? <><rect x="8" y="8" width="12" height="12" rx="2.5" /><path d="M16 8V6.5A2.5 2.5 0 0 0 13.5 4h-7A2.5 2.5 0 0 0 4 6.5v7A2.5 2.5 0 0 0 6.5 16H8" /></>
    : k === "rep"
      ? <><path d="M17 2l3 3-3 3" /><path d="M4 11V9a4 4 0 0 1 4-4h12" /><path d="M7 22l-3-3 3-3" /><path d="M20 13v2a4 4 0 0 1-4 4H4" /></>
      : <><path d="M3 17l6-6 4 4 8-8" /><path d="M15 7h6v6" /></>;
  return <span className={`sg-i ${k}`} aria-hidden="true"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{path}</svg></span>;
}

export function Signals({ config, go, w, lang }: { config: ConfigView; go: (p: string) => void; w: W; lang: string }) {
  const q = useQuery({ queryKey: ["signals"], queryFn: api.signals, refetchInterval: 25_000 });
  const qc = useQueryClient();
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState<Video | null>(null);
  const videos = ((config as unknown as { videos?: Video[] }).videos ?? []);
  const video = videos.find((v) => (v.where ?? []).includes("signals")) ?? videos.find((v) => v.key === "ch08");
  const say = (t: string) => { setToast(t); window.setTimeout(() => setToast((x) => (x === t ? null : x)), 3000); };
  const move = async (s: SignalOut, status: "offen" | "in_pruefung" | "erledigt", done: string) => {
    try { await api.signalStatus(s.id, status); setError(null); await qc.invalidateQueries({ queryKey: ["signals"] }); say(done); }
    catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
  };
  const all = q.data ?? [];
  const sorted = (list: SignalOut[]) => [...list].sort((a, b) => ORDER.indexOf(kindOf(a.kind)) - ORDER.indexOf(kindOf(b.kind)));
  const open = sorted(all.filter((s) => s.status !== "in_pruefung" && s.status !== "erledigt"));
  const looking = sorted(all.filter((s) => s.status === "in_pruefung"));
  const done = sorted(all.filter((s) => s.status === "erledigt"));
  const label: Record<Kind, string> = { dup: w.sgDup, rep: w.sgRep, dev: w.sgDev };
  const when = (iso: string) => {
    const d = new Date(iso);
    return isNaN(d.getTime()) ? "" : d.toLocaleDateString(lang === "de" ? "de-DE" : "en-GB", { day: "numeric", month: "short" });
  };

  const row = (s: SignalOut) => {
    const k = kindOf(s.kind);
    return (
      <div key={s.id} className={`rb-rule sg-row${s.status === "erledigt" ? " in" : ""}`}>
        <Icon k={k} />
        <div className="rb-main">
          <p className="rb-t">{s.title}</p>
          <p className={`sg-k ${k}`}>{label[k]}</p>
          <p className="sg-why">{why(s.text)}</p>
          <div className="sg-cs">
            {s.cases.map((c) => (
              <button key={c.id} type="button" className="sg-c" data-help-skip="opens the case" onClick={() => go(`/case/${encodeURIComponent(c.id)}`)}>
                <i style={{ background: c.color || undefined }} />{c.title}<span className="sg-a">›</span>
              </button>
            ))}
          </div>
          {s.decided_by && s.status !== "offen" && <p className="sg-by">{w.sgBy(s.decided_by, when(s.decided_at))}</p>}
        </div>
        <div className="rb-side">
          {s.status === "erledigt" ? (
            <button type="button" className="sg-back" data-help-skip="explained by cf.signals" onClick={() => move(s, "offen", w.sgDoneBack)}>{w.sgMoveBack}</button>
          ) : s.status === "in_pruefung" ? (
            <>
              <button type="button" className="rb-acc" data-help-skip="explained by cf.signals" onClick={() => move(s, "erledigt", w.sgDoneDone)}>{w.sgMarkDone}</button>
              <button type="button" className="sg-back" data-help-skip="explained by cf.signals" onClick={() => move(s, "offen", w.sgDoneBack)}>{w.sgMoveBack}</button>
            </>
          ) : (
            <>
              <button type="button" className="rb-acc" data-help-skip="explained by cf.signals" onClick={() => move(s, "in_pruefung", w.sgDoneLook)}>{w.sgLook}</button>
              <button type="button" className="rb-ic no" data-help-skip="nothing to do: marks it as done" aria-label={w.sgNothing} title={w.sgNothing} onClick={() => move(s, "erledigt", w.sgDoneNothing)}>✕</button>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <main className="main view-signals rb" data-help="cf.signals">
      <div className="rb-page">
        <header className="rb-head">
          <h1>{w.flagged}</h1>
          <p className="rb-lead">{w.sgLead}</p>
          {video && <button type="button" className="rb-watch" data-help-skip="a video about this page" onClick={() => setPlaying(video)}><span className="rb-play" aria-hidden="true" />{w.rbWatch} · {video.seconds} s</button>}
        </header>
        {error && <p className="rb-err">{error}</p>}
        {q.data && (
          <>
            <h3 className="rb-h"><span className="rb-dot" />{w.sgToCheck}<em>{open.length}</em></h3>
            {open.length ? <section className="rb-card">{open.map(row)}</section> : <p className="rb-none">{w.sgNone}</p>}
            {looking.length > 0 && <><h3 className="rb-h"><span className="rb-dot urgent" />{w.sgLooking}<em>{looking.length}</em></h3><section className="rb-card">{looking.map(row)}</section></>}
            {done.length > 0 && <><h3 className="rb-h"><span className="rb-dot quiet" />{w.sgDone}<em>{done.length}</em></h3><section className="rb-card">{done.map(row)}</section></>}
          </>
        )}
      </div>
      {toast && <div className="rb-toast" role="status">{toast}</div>}
      {playing && <VideoStage video={playing} onClose={() => setPlaying(null)} />}
    </main>
  );
}
