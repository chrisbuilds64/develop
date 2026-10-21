// One case: head, the line, what is on the desk, what is missing, the conversation, and the one button in the thumb zone.
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, sample as putSample, stepId, type ConfigView, type MeOut, type Turn } from "../api";
import { Line } from "../components/Line";
import { Frame } from "../components/Frames";
import { Thread } from "../components/Thread";
import { ago, dateWords, type words } from "../words";

export function CaseScreen({ id, config, me, go, w }: { id: string; config: ConfigView; me: MeOut; go: (p: string) => void; w: ReturnType<typeof words> }) {
  const qc = useQueryClient();
  const lang = config.lang;
  const q = useQuery({ queryKey: ["case", id], queryFn: () => api.case(id), refetchInterval: (query) => (query.state.data?.group === "claude" ? 2500 : 25_000) });
  const samples = ((config.theme as { samples?: string[] }).samples ?? []);
  const [refused, setRefused] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; undo?: () => void } | null>(null);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [ask, setAsk] = useState("");
  const askRef = useRef<HTMLInputElement>(null);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["case", id] }); qc.invalidateQueries({ queryKey: ["groups"] }); qc.invalidateQueries({ queryKey: ["turns"] }); };
  const fail = (e: unknown) => setRefused(e instanceof ApiError ? e.message : String(e));
  const stageWord = (f: string) => ((config.words as { stages?: Record<string, string> }).stages?.[f]) ?? f.replace(/^\d+-/, "");
  const roleWord = (actor: string) => actor.startsWith("role:") ? (((config.words as { roles?: Record<string, string> }).roles?.[actor.slice(5)]) ?? actor.slice(5)) : (config.people.find((p) => p.id === actor)?.name ?? actor);
  const step = useMutation({ mutationFn: (p: { action: string; payload?: Record<string, unknown> }) => api.step(id, p.action, stepId(p.action), p.payload ?? {}), onSuccess: (r) => { setRefused(null); refresh(); if (r.to) setToast({ text: w.doneMoved(stageWord(r.to)) }); }, onError: fail });
  const entry = useMutation({ mutationFn: (b: Parameters<typeof api.entry>[1]) => api.entry(id, b), onSuccess: () => { setRefused(null); refresh(); }, onError: fail });
  const run = useMutation({ mutationFn: (text: string) => api.run(id, { note: text, request_id: stepId("ask") }), onSuccess: () => { setRefused(null); setAsk(""); refresh(); }, onError: fail });
  const upload = useMutation({ mutationFn: (p: { slot: string; file: File }) => api.asset(id, p.slot, stepId("up"), p.file), onSuccess: () => { setRefused(null); refresh(); }, onError: fail });
  const sampleIn = useMutation({ mutationFn: (slot: string) => putSample(id, slot, stepId("sample")), onSuccess: () => { setRefused(null); refresh(); }, onError: fail });
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 6000); return () => clearTimeout(t); }, [toast]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); askRef.current?.focus(); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (q.isLoading) return <main className="main"><p className="empty">…</p></main>;
  if (!q.data) return <main className="main"><p className="empty">{String(q.error ?? "—")}</p></main>;
  const v = q.data;
  const busy = step.isPending || entry.isPending || run.isPending || upload.isPending || sampleIn.isPending;
  const main: Turn | undefined = v.my_turns[0] ?? v.turns[0];
  const mine = v.mine;
  const actionTurns = v.my_turns.filter((t) => !["answer", "wait"].includes(t.action));
  const primaryTurn: Turn | undefined = actionTurns[0];
  const secondary = actionTurns.slice(1);
  const asks = primaryTurn?.payload ?? [];
  const needsAmount = asks.includes("amount");
  const needsDate = asks.includes("date");
  const needsUrl = asks.includes("url");
  const needsNote = asks.includes("note");
  const blocked = primaryTurn?.blocked_by ?? [];
  const canPress = primaryTurn && blocked.length === 0 && (!needsAmount || amount.trim()) && (!needsDate || date) && (!needsNote || note.trim()) && !busy;
  const desk = v.slots.filter((s) => s.present && !["meta.json", "review.md"].includes(s.file));
  const missing = v.slots.filter((s) => !s.present && s.file !== "meta.json" && s.file !== "review.md" && (s.required || s.due_station === v.station || blocked.includes(s.file)));
  const primary = v.primary ? v.slots.find((s) => s.file === v.primary) : undefined;
  const stub = main
    ? mine ? `${v.stage_word} · ${w.waitingForYou}${v.since ? ` ${w.since} ${ago(v.since, lang)}` : ""}`
      : main.actor === "claude" ? `${w.isWorking(v.agent)}${v.since ? ` · ${w.since} ${ago(v.since, lang)}` : ""}`
      : `${v.stage_word} · ${w.waitingFor(roleWord(main.actor))}`
    : `${v.stage_word}${v.date ? ` · ${dateWords(v.date, lang)}` : ""}`;
  const payload: Record<string, unknown> = {};
  if (needsAmount) payload.amount = amount.trim();
  if (needsDate) payload.date = date;
  if (needsUrl) payload.url = note.trim() || "https://example.invalid/";
  if (note.trim() && !needsUrl) payload.note = note.trim();

  return (
    <main className="main">
      <header className="case-head">
        <span className="ref">{v.label_word}{v.meta?.series ? ` · ${v.meta.series}` : ""} · {v.id.split("-").slice(0, 2).join("-")}{v.meta?.created ? ` · ${dateWords(String(v.meta.created), lang)}` : ""}</span>
        <h1>{v.title}</h1>
        <p className="stub"><span className={`dot${mine ? " mine" : ""}`} /><span>{stub}</span></p>
      </header>

      <Line stations={v.stations} mine={mine} label={v.stage_word} />

      {refused && <div className="refused">{refused}</div>}

      <div className="body">
        <div className="desk">
          <p className="kicker">{w.onDesk}</p>
          <div className="desk-grid">
            {primary?.present && (
              <a className="file wide stack" href={primary.versions[primary.versions.length - 1].url} target="_blank" rel="noreferrer">
                <span className="head"><span className="name">{primary.word}</span><span className="meta">{w.version(Math.max(1, primary.versions[primary.versions.length - 1].version))}{primary.by_word ? ` · ${primary.by_word}` : ""}</span></span>
                {primary.versions.length > 1 && <span className="hint">{w.keeps}</span>}
              </a>
            )}
            {desk.filter((s) => s.file !== v.primary).map((s) => {
              const newest = s.versions[s.versions.length - 1];
              return (
                <a key={s.file} className={`file${s.versions.length > 1 ? " stack" : ""}`} href={newest.url} target="_blank" rel="noreferrer">
                  {s.shape.startsWith("image") && <img src={newest.url} alt="" />}
                  <span className="name">{s.word}</span>
                  <span className="meta">{w.version(Math.max(1, newest.version))}{s.by_word ? ` · ${s.by_word}` : ""}</span>
                </a>
              );
            })}
            {desk.length === 0 && !primary?.present && <span className="empty">—</span>}
          </div>

          {missing.length > 0 && (
            <>
              <p className="kicker" style={{ marginTop: 10 }}>{w.missing}</p>
              <div className="frames">
                {missing.map((s) => <Frame key={s.file} slot={s} mine={mine && blocked.includes(s.file)} w={w} busy={busy} onFile={(f) => upload.mutate({ slot: s.file, file: f })}
                                           sample={samples.includes(s.file)} onSample={() => sampleIn.mutate(s.file)} />)}
                {needsAmount && (
                  <div className="frame"><div className="box mine" style={{ width: 260, height: 120, alignItems: "flex-start", textAlign: "left" }}>
                    <span style={{ fontSize: 15, fontWeight: 600, color: "var(--ink)" }}>{primaryTurn?.label}</span>
                    <label className="money">{w.amount}<input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="€" inputMode="decimal" /></label>
                  </div></div>
                )}
              </div>
            </>
          )}
          {missing.length === 0 && needsAmount && (
            <label className="money" style={{ marginTop: 10 }}>{w.amount}<input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="€" inputMode="decimal" /></label>
          )}
          {needsDate && <label className="date" style={{ marginTop: 10, display: "inline-flex", gap: 10, alignItems: "center" }}>{w.date}<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>}
          {(needsUrl || needsNote) && <label className="ask" style={{ marginTop: 10, maxWidth: 480 }}><span className="sr">{needsUrl ? w.link : primaryTurn?.label}</span><input value={note} onChange={(e) => setNote(e.target.value)} placeholder={needsUrl ? `${w.link} …` : `${primaryTurn?.label} …`} /></label>}
        </div>

        <aside className="thread" aria-label={w.conversation}>
          <p className="kicker">{w.conversation}</p>
          <Thread entries={v.entries} meName={me.name ?? ""} agentName={v.agent} lang={lang} w={w} busy={busy}
                  stageWord={stageWord}
                  onAnswer={(e, text) => entry.mutate({ kind: "answer", step_id: stepId("answer"), resolves: e.id, text })}
                  onDone={(e) => entry.mutate({ kind: "done", step_id: stepId("done"), resolves: e.id })} />
          <div className="grow" />
          {secondary.length > 0 && (
            <div className="chips">
              {secondary.map((t) => <button key={t.action} type="button" className="chip" disabled={busy || t.blocked_by.length > 0} title={t.blocked_by.join(", ")}
                                            onClick={() => { const text = window.prompt(t.label) ?? ""; if (text.trim()) step.mutate({ action: t.action, payload: { note: text.trim(), text: text.trim() } }); }}>{t.label}</button>)}
            </div>
          )}
          <form className="ask" onSubmit={(e) => { e.preventDefault(); if (ask.trim()) run.mutate(ask.trim()); }}>
            <span className="sr">{w.notePlaceholder(v.agent)}</span>
            <input ref={askRef} value={ask} onChange={(e) => setAsk(e.target.value)} placeholder={w.notePlaceholder(v.agent)} />
            <button type="submit" className="send" disabled={busy || !ask.trim()}>↵</button>
          </form>
        </aside>
      </div>

      <footer className="foot">
        {primaryTurn ? (
          <>
            {blocked.length > 0 && <span className="says">{w.firstHere}: {blocked.map((b) => v.slots.find((s) => s.file === b)?.word ?? b).join(", ")}</span>}
            {!blocked.length && primaryTurn.reason && !mine && <span className="says">{primaryTurn.reason}</span>}
            <button type="button" className="btn" disabled={!canPress} onClick={() => step.mutate({ action: primaryTurn.action, payload })}>{primaryTurn.label} →</button>
          </>
        ) : main ? (
          <span className="says">{main.actor === "claude" ? w.isWorking(v.agent) : `${w.waitingFor(roleWord(main.actor))}`}</span>
        ) : (
          <span className="says">{v.stage_word}</span>
        )}
      </footer>
      {toast && <div className="toast" role="status"><span>{toast.text}</span>{toast.undo && <button type="button" onClick={toast.undo}>{w.undo}</button>}<button type="button" onClick={() => go("/")}>{w.yourMove} →</button></div>}
    </main>
  );
}
