// AI team (design hand-back, 2026-11-06; ADR-020): the person's helpers, where they work. A helper has a job profile, works
// only in sessions the person starts, and every session is logged. Inside the cockpit this page works on the person's own
// team through the shell; in the public demo on the visitor's team, with prepared answers. One page, two sources (teamApi).
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, teamApi, type ConfigView, type MeOut, type TeamSession, type TeamTurn, type TeamView } from "../api";
import { VideoStage, type Video } from "../components/Explain";
import type { words } from "../words";

type W = ReturnType<typeof words>;
const MIN_THINK = 1200;          // a prepared answer still takes a breath, so it reads as an answer and not as a lookup

function useToast(): [string | null, (t: string) => void] {
  const [toast, setToast] = useState<string | null>(null);
  const say = (t: string) => { setToast(t); window.setTimeout(() => setToast((x) => (x === t ? null : x)), 3000); };
  return [toast, say];
}

export function Team({ config, me, go, w }: { config: ConfigView; me: MeOut; go: (p: string) => void; w: W }) {
  const tapi = useMemo(() => teamApi(me), [me]);
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["team", me.lang], queryFn: tapi.view });
  const [toast, say] = useToast();
  const [error, setError] = useState<string | null>(null);
  const [hiring, setHiring] = useState(false);
  const [playing, setPlaying] = useState<Video | null>(null);
  const [logs, setLogs] = useState<string | null>(null);
  const videos = ((config as unknown as { videos?: Video[] }).videos ?? []);
  const video = videos.find((v) => (v.where ?? []).includes("ai-team")) ?? videos.find((v) => v.key === "ch09");
  const here = me.places?.find((p) => p.current)?.name ?? config.product;

  const run = async (fn: () => Promise<unknown>, done?: string) => {
    try { await fn(); setError(null); await qc.invalidateQueries({ queryKey: ["team"] }); if (done) say(done); }
    catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
  };
  const start = async (agent: string) => {
    try { const r = await tapi.start(agent, here, { url: window.location.pathname }); await qc.invalidateQueries({ queryKey: ["team"] }); go(`/team/${encodeURIComponent(r.id)}`); }
    catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
  };

  const v = q.data;
  return (
    <main className="main view-team rb" data-help="cf.team">
      <div className="rb-page">
        <header className="tm-head">
          <div>
            <h1>{w.team}</h1>
            <p className="rb-lead quiet">{w.tmLead}</p>
            {video && <button type="button" className="rb-watch" data-help-skip="a video about this page" onClick={() => setPlaying(video)}><span className="rb-play" aria-hidden="true" />{w.rbWatch} · {video.seconds} s</button>}
          </div>
          <button type="button" className="primary" data-help="cf.team-add" onClick={() => (v && v.hireable.every((t) => t.taken) ? say(w.tmAllHired) : setHiring(true))}>{w.tmAdd}</button>
        </header>
        {error && <p className="rb-err">{error}</p>}
        {v && (
          <>
            <section className="tm-card">
              <h3>{w.tmOnTeam}</h3>
              {v.agents.length ? v.agents.map((a) => (
                <div key={a.id} className="tm-row">
                  <span className="tm-av" aria-hidden="true">✦</span>
                  <span className="tm-n"><b>{a.label}</b><span>{a.role}</span></span>
                  <span className={`tm-st${a.session ? " busy" : ""}`}><i />{a.session ? w.tmBusy : w.tmReady}</span>
                  <button type="button" className="tm-btn" data-help="cf.team-session" onClick={() => (a.session ? go(`/team/${encodeURIComponent(a.session)}`) : start(a.id))}>{a.session ? w.tmOpen : w.tmStart}</button>
                  <button type="button" className="tm-rm" data-help-skip="explained by cf.team" onClick={() => run(() => tapi.dismiss(a.id), w.tmRemoved(a.label))}>{w.tmRemove}</button>
                </div>
              )) : <p className="tm-empty">{w.tmEmpty}</p>}
            </section>
            <section className="tm-card">
              <h3>{w.tmHistory}</h3>
              {v.sessions.length ? v.sessions.map((s) => (
                <button key={s.id} type="button" className="tm-row tm-srow" data-help-skip="opens the session" onClick={() => go(`/team/${encodeURIComponent(s.id)}`)}>
                  <span className="tm-tm">{s.ended}</span>
                  <span className="tm-n"><b>{s.note || s.topic}</b><span>{s.label}{s.topic && s.note ? ` · ${s.topic}` : ""}</span></span>
                  <span className="tm-go" aria-hidden="true">›</span>
                </button>
              )) : <p className="tm-empty">{w.tmNoHistory}</p>}
            </section>
            <section className="tm-card">
              <h3>{w.tmLogs}</h3>
              <form className="tm-logf" onSubmit={(e) => { e.preventDefault(); if (logs !== null) run(() => tapi.logs(logs), w.tmSaved); }}>
                <input className="tm-fin" value={logs ?? v.logs_dir} onChange={(e) => setLogs(e.target.value)} aria-label={w.tmLogsLabel} spellCheck={false} />
                <button type="submit" className="tm-btn big" data-help="cf.team-logs">{w.save}</button>
              </form>
              <p className="tm-hint">{w.tmLogsHint}</p>
            </section>
          </>
        )}
      </div>
      {hiring && v && <Hire w={w} v={v} onClose={() => setHiring(false)} onHire={(t, m, label) => { setHiring(false); run(() => tapi.hire(t, m), w.tmHired(label)); }} />}
      {toast && <div className="rb-toast" role="status">{toast}</div>}
      {playing && <VideoStage video={playing} onClose={() => setPlaying(null)} />}
    </main>
  );
}

function Hire({ w, v, onClose, onHire }: { w: W; v: TeamView;
  onClose: () => void; onHire: (template: string, model: string, label: string) => void }) {
  const [pick, setPick] = useState<string | null>(v.hireable.find((t) => !t.taken)?.id ?? null);
  const [model, setModel] = useState(v.models[0]?.id ?? "");
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  const chosen = v.hireable.find((t) => t.id === pick);
  return (
    <div className="tm-scrim" role="presentation" onClick={onClose}>
      <div className="tm-sheet" role="dialog" aria-label={w.tmAdd} onClick={(e) => e.stopPropagation()}>
        <div className="tm-sh"><b>{w.tmAdd}</b><span>{w.tmAddLead}</span></div>
        <div className="tm-opts">
          {v.hireable.map((t) => (
            <button key={t.id} type="button" className={`tm-opt${pick === t.id ? " sel" : ""}${t.taken ? " dis" : ""}`} disabled={t.taken} data-help-skip="picks a job profile" onClick={() => setPick(t.id)}>
              <i />
              <span><span className="tm-ot">{t.label}</span><span className="tm-od">{t.taken ? w.tmAlready : t.role}</span></span>
              {pick === t.id && <span className="tm-ck">✓</span>}
            </button>
          ))}
        </div>
        {v.models.length > 0 && (
          <div className="tm-hb">
            <div className="tm-fl">{w.tmModel}</div>
            <div className="tm-seg" role="radiogroup" aria-label={w.tmModel}>
              {v.models.map((m) => <button key={m.id} type="button" role="radio" aria-checked={model === m.id} className={model === m.id ? "on" : ""} data-help-skip="picks the model" onClick={() => setModel(m.id)}>{m.label}</button>)}
            </div>
          </div>
        )}
        <div className="tm-sf">
          <button type="button" className="tm-btn big" data-help-skip="closes the sheet" onClick={onClose}>{w.cancel}</button>
          <button type="button" className="primary tm-p" disabled={!chosen} data-help-skip="explained by cf.team-add" onClick={() => chosen && onHire(chosen.id, model, chosen.label)}>{w.tmAddTo}</button>
        </div>
      </div>
    </div>
  );
}

export function TeamSessionScreen({ id, me, go, w }: { id: string; me: MeOut; go: (p: string) => void; w: W }) {
  const tapi = useMemo(() => teamApi(me), [me]);
  const qc = useQueryClient();
  const [s, setS] = useState<TeamSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [ending, setEnding] = useState(false);
  const [toast, say] = useToast();
  const input = useRef<HTMLInputElement>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const load = async () => {
    try { setS(await tapi.session(id)); setError(null); }
    catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
  };
  useEffect(() => { setS(null); load(); }, [id, me.lang]);                   // eslint-disable-line react-hooks/exhaustive-deps
  const thinking = !!s?.turns.some((t) => t.thinking);
  useEffect(() => {                                                          // inside the cockpit a real helper answers later: look again
    if (!thinking || busy) return;
    const t = window.setInterval(load, 2000);
    return () => window.clearInterval(t);
  }, [thinking, busy]);                                                      // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { bottom.current?.scrollIntoView({ block: "end" }); }, [s?.turns.length, thinking]);
  useEffect(() => { if (s?.status === "open" && !ending) input.current?.focus(); }, [s?.status, ending]);

  const send = async (raw: string) => {
    const t = raw.trim();
    if (!t || !s || busy) return;
    setText(""); setBusy(true);
    const mine: TeamTurn[] = [...s.turns, { who: "you", text: t }, { who: "ai", text: "", thinking: true }];
    setS({ ...s, turns: mine, suggestions: [] });
    const t0 = Date.now();
    try {
      const next = await tapi.say(s.id, t);
      await new Promise((r) => window.setTimeout(r, Math.max(0, MIN_THINK - (Date.now() - t0))));
      setS(next); setError(null);
    } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); await load(); }
    finally { setBusy(false); input.current?.focus(); }
  };
  const end = async (note: string) => {
    if (!s) return;
    if (!note.trim()) { say(w.tmNeedNote); return; }
    try { setS(await tapi.end(s.id, note)); setEnding(false); setError(null); say(w.tmEndedToast); await qc.invalidateQueries({ queryKey: ["team"] }); }
    catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
  };

  const open = s?.status === "open";
  return (
    <main className="main view-team-session" data-help="cf.team-session">
      <div className="q-bar tm-bar">
        <button type="button" className="q-crumb" data-help-skip="back to the AI team" onClick={() => go("/team")}>{w.team}</button>
        <span className="q-sep">/</span>
        <span className="tm-bt">{s?.label ?? ""}</span>
        {s && <span className="tm-crt">{s.started}{s.ended ? ` – ${s.ended}` : ""}</span>}
        {s && (open
          ? <button type="button" className="tm-btn" data-help="cf.team-end" onClick={() => setEnding(true)}>{w.tmEnd}</button>
          : <span className="tm-tag">{w.tmEnded}</span>)}
      </div>
      <div className="tm-sess">
        <div className="tm-col">
          {error && <p className="rb-err">{error}</p>}
          {s && (s.turns.length || !open ? (
            <div className="tm-thread">
              {s.turns.map((t, i) => (
                <div key={i} className={`tm-m ${t.who === "ai" ? "ai" : "me"}`}>
                  {t.who === "ai" && <span className="tm-av sm" aria-hidden="true">✦</span>}
                  <div>
                    <div className="tm-mh">{t.who === "ai" ? s.label : w.tmYou}</div>
                    <p className={t.thinking ? "tm-shimmer" : ""}>{t.thinking ? w.tmThinking : t.text}</p>
                  </div>
                </div>
              ))}
              {!open && s.note && <div className="tm-close"><b>{w.tmClosing}</b>{s.note}</div>}
              <div ref={bottom} />
            </div>
          ) : (
            <div className="tm-hello">
              <span className="tm-av lg" aria-hidden="true">✦</span>
              <h2>{s.label}</h2>
              <p><span>{s.role}</span>{s.does && <> <span>{s.does}</span></>}</p>
            </div>
          ))}
        </div>
        {s && open && (
          <div className="tm-foot">
            {s.turns.length === 0 && s.suggestions.length > 0 && (
              <div className="tm-sugg">
                {s.suggestions.map((x) => <button key={x} type="button" className="tm-q" data-help-skip="sends this question" onClick={() => send(x)}>{x}</button>)}
              </div>
            )}
            <form className="tm-ask" onSubmit={(e) => { e.preventDefault(); send(text); }}>
              <input ref={input} value={text} onChange={(e) => setText(e.target.value)} placeholder={w.tmMessage(s.label)} aria-label={w.tmMessage(s.label)} autoComplete="off" disabled={busy || thinking} />
              <button type="submit" className={`tm-send${text.trim() ? " on" : ""}`} aria-label={w.tmSend} data-help-skip="sends the message" disabled={busy || thinking}>↑</button>
            </form>
          </div>
        )}
      </div>
      {ending && <EndSheet w={w} onClose={() => setEnding(false)} onEnd={end} />}
      {toast && <div className="rb-toast" role="status">{toast}</div>}
    </main>
  );
}

function EndSheet({ w, onClose, onEnd }: { w: W; onClose: () => void; onEnd: (note: string) => void }) {
  const [note, setNote] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    ref.current?.focus();
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  return (
    <div className="tm-scrim" role="presentation" onClick={onClose}>
      <div className="tm-sheet" role="dialog" aria-label={w.tmEndTitle} onClick={(e) => e.stopPropagation()}>
        <div className="tm-sh"><b>{w.tmEndTitle}</b><span>{w.tmEndLead}</span></div>
        <textarea ref={ref} className="tm-ta" rows={3} value={note} placeholder={w.tmEndPh} onChange={(e) => setNote(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onEnd(note); }} />
        <div className="tm-sf">
          <button type="button" className="tm-btn big" data-help-skip="closes the sheet" onClick={onClose}>{w.cancel}</button>
          <button type="button" className="primary tm-p" data-help-skip="explained by cf.team-end" onClick={() => onEnd(note)}>{w.tmEnd}</button>
        </div>
      </div>
    </div>
  );
}

