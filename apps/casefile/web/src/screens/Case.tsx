// One case: head, the line, what is on the desk, what is missing, the conversation, and the one button in the thumb zone.
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, BASE, sample as putSample, stepId, type CaseView, type ConfigView, type MeOut, type Turn } from "../api";
import { Line } from "../components/Line";
import { Frame } from "../components/Frames";
import { Thread } from "../components/Thread";
import { Cover } from "../components/Cover";
import { Send } from "../components/Icons";
import { Reader, type Doc } from "../components/Reader";
import { ago, dateWords, type words } from "../words";

/** The documents on the desk, newest version each, the primary first — the order the reader walks. */
export function docsOf(v: CaseView): Doc[] {
  const present = v.slots.filter((s) => s.present && !["meta.json", "review.md"].includes(s.file) && !["interview", "data"].includes(s.shape));
  const ordered = v.primary ? [...present.filter((s) => s.file === v.primary), ...present.filter((s) => s.file !== v.primary)] : present;
  return ordered.map((s) => ({ word: s.word, shape: s.shape, versions: s.versions.map((v) => ({ name: v.name, version: v.version, url: v.url })) }));
}

export function CaseScreen({ id, config, me, go, w }: { id: string; config: ConfigView; me: MeOut; go: (p: string) => void; w: ReturnType<typeof words> }) {
  const qc = useQueryClient();
  const lang = config.lang;
  const q = useQuery({ queryKey: ["case", id], queryFn: () => api.case(id), retry: false, refetchInterval: (query) => (query.state.data?.group === "claude" ? 2500 : 25_000) });
  const samples = ((config.theme as { samples?: string[] }).samples ?? []);
  const extWord = ((config.words as { words?: Record<string, string> }).words?.external_id) ?? "";
  const [refused, setRefused] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; undo?: () => void } | null>(null);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [ask, setAsk] = useState("");
  const [pending, setPending] = useState<Turn | null>(null);
  const [reading, setReading] = useState<string | null>(null);
  const askRef = useRef<HTMLInputElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["case", id] }); qc.invalidateQueries({ queryKey: ["groups"] }); qc.invalidateQueries({ queryKey: ["turns"] }); };
  const fail = (e: unknown) => setRefused(e instanceof ApiError ? e.message : String(e));
  const stageWord = (f: string) => ((config.words as { stages?: Record<string, string> }).stages?.[f]) ?? f.replace(/^\d+-/, "");
  const roleWord = (actor: string) => actor.startsWith("role:") ? (((config.words as { roles?: Record<string, string> }).roles?.[actor.slice(5)]) ?? actor.slice(5)) : (config.people.find((p) => p.id === actor)?.name ?? actor);
  const step = useMutation({ mutationFn: (p: { action: string; payload?: Record<string, unknown> }) => api.step(id, p.action, stepId(p.action), p.payload ?? {}), onSuccess: (r) => { setRefused(null); refresh(); if (r.to) setToast({ text: w.doneMoved(stageWord(r.to)) }); }, onError: fail });
  const entry = useMutation({ mutationFn: (b: Parameters<typeof api.entry>[1]) => api.entry(id, b), onSuccess: () => { setRefused(null); refresh(); }, onError: fail });
  const run = useMutation({ mutationFn: (text: string) => api.run(id, { note: text, request_id: stepId("ask") }), onSuccess: () => { setRefused(null); setAsk(""); refresh(); }, onError: fail });
  const upload = useMutation({ mutationFn: (p: { slot: string; file: File }) => api.asset(id, p.slot, stepId("up"), p.file), onSuccess: () => { setRefused(null); refresh(); }, onError: fail });
  const sampleIn = useMutation({ mutationFn: (slot: string) => putSample(id, slot, stepId("sample")), onSuccess: () => { setRefused(null); refresh(); }, onError: fail });
  const entryCount = q.data?.entries.length ?? 0;
  useEffect(() => { const down = () => { const el = threadRef.current; if (el) el.scrollTop = el.scrollHeight; }; down(); document.fonts?.ready.then(down); const t = setTimeout(down, 250); return () => clearTimeout(t); }, [entryCount, id]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 6000); return () => clearTimeout(t); }, [toast]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); askRef.current?.focus(); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (q.isLoading) return <main className="main"><p className="empty">…</p></main>;
  if (!q.data) return <main className="main"><p className="empty">{q.error instanceof ApiError && q.error.status === 404 ? w.notHere : q.error ? w.unreachable : "…"}</p></main>;
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
  const blockedWord = (b: string) => {
    const slot = v.slots.find((s) => s.file === b);
    if (slot) return slot.word;
    if (b.startsWith("shape:")) { const want = b.slice(6); const first = v.slots.find((s) => !s.present && s.shape.startsWith(want)); return first ? first.word : w.shape(want); }
    return b;
  };
  const framesAreTheMove = primaryTurn?.action === "deliver";
  const canPress = primaryTurn && blocked.length === 0 && (!needsAmount || amount.trim()) && (!needsDate || date) && (!needsNote || note.trim()) && !busy;
  const desk = v.slots.filter((s) => s.present && !["meta.json", "review.md"].includes(s.file) && !["interview", "data"].includes(s.shape));
  const talkSlot = v.slots.find((s) => s.shape === "interview");
  const outcomeReady = v.slots.some((s) => s.shape === "data" && s.present);
  const missing = v.slots.filter((s) => !s.present && s.file !== "meta.json" && s.file !== "review.md" && !["interview", "data"].includes(s.shape) && (s.required || s.due_station === v.station || blocked.includes(s.file) || (blocked.some((b) => b.startsWith("shape:")) && blocked.some((b) => s.shape.startsWith(b.slice(6))))));
  const primary = v.primary ? v.slots.find((s) => s.file === v.primary) : undefined;
  const docs = docsOf(v);
  const readingIndex = reading === null ? -1 : docs.findIndex((d) => d.versions.some((v) => v.name === reading));
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
      <header className="case-head" data-help="cf.case-head">
        <Cover label={v.label} number={v.number || v.id.split("-")[1] || ""} tint={v.tint} size="m" />
        <span className="ref">{v.label_word}{v.meta?.series ? ` · ${v.meta.series}` : ""}{v.meta?.created ? ` · ${dateWords(String(v.meta.created), lang)}` : ""}</span>
        <h1 className="num" title={extWord || undefined}>{v.external_id ? (v.external_url ? <a href={v.external_url} target="_blank" rel="noreferrer">{v.external_id}</a> : v.external_id) : v.number ? `${v.label}-${v.number}` : v.id}</h1>
        <p className="title">{v.title}</p>
        <p className="stub"><span className={`dot${mine ? " mine" : ""}`} /><span>{stub}</span></p>
      </header>

      <div data-help="cf.stations"><Line stations={v.stations} mine={mine} label={v.stage_word} /></div>

      {refused && <div className="refused">{refused}</div>}

      <div className={`body${readingIndex >= 0 ? " reading" : ""}`}>
        <div className="desk" data-help="cf.desk">
          {readingIndex >= 0 ? (
            <Reader docs={docs} index={readingIndex} caseId={id} onIndex={(i) => setReading(docs[i].versions[docs[i].versions.length - 1].name)} onClose={() => setReading(null)} w={w} />
          ) : (<>
          <p className="kicker">{w.onDesk}</p>
          <div className="desk-grid">
            {talkSlot && v.station !== "prepare" && (
              <button type="button" className={`file wide talk-tile${v.my_turns.some((t) => t.action === "interview") ? " mine" : ""}`} data-help="cf.talk-tile" onClick={() => go(`/case/${encodeURIComponent(id)}/gespraech`)}>
                <span className="head"><span className="name">{w.talkOpen}</span></span>
                <span className="hint">{w.talkOpenHint}</span>
              </button>
            )}
            {talkSlot && outcomeReady && (
              <button type="button" className={`file wide talk-tile${v.my_turns.some((t) => t.action === "approve_canon") ? " mine" : ""}`} data-help="cf.outcome-tile" onClick={() => go(`/case/${encodeURIComponent(id)}/ergebnis`)}>
                <span className="head"><span className="name">{w.outcomeOpen}</span></span>
                <span className="hint">{w.outcomeOpenHint}</span>
              </button>
            )}
            {primary?.present && (
              <button type="button" className="file wide stack" onClick={() => setReading(primary.versions[primary.versions.length - 1].name)}>
                <span className="head"><span className="name">{primary.word}</span><span className="meta">{w.version(Math.max(1, primary.versions[primary.versions.length - 1].version))}{primary.by_word ? ` · ${primary.by_word}` : ""}</span></span>
                {primary.versions.length > 1 && <span className="hint">{w.keeps}</span>}
              </button>
            )}
            {desk.filter((s) => s.file !== v.primary).map((s) => {
              const newest = s.versions[s.versions.length - 1];
              return (
                <button key={s.file} type="button" className={`file${s.versions.length > 1 ? " stack" : ""}`} onClick={() => setReading(newest.name)}>
                  {s.shape.startsWith("image") && <img src={BASE + newest.url} alt="" />}
                  <span className="name">{s.word}</span>
                  <span className="meta">{w.version(Math.max(1, newest.version))}{s.by_word ? ` · ${s.by_word}` : ""}</span>
                </button>
              );
            })}
            {desk.length === 0 && !primary?.present && !talkSlot && <span className="empty">—</span>}
          </div>

          {missing.length > 0 && (
            <>
              <p className="kicker" style={{ marginTop: 10 }}>{w.missing}</p>
              <div className="frames">
                {missing.map((s) => <Frame key={s.file} slot={s} mine={mine && blocked.includes(s.file)} w={w} busy={busy} onFile={(f) => upload.mutate({ slot: s.file, file: f })}
                                           sample={samples.includes(s.file)} onSample={() => sampleIn.mutate(s.file)} />)}

              </div>
            </>
          )}
          {needsDate && <label className="date" style={{ marginTop: 10, display: "inline-flex", gap: 10, alignItems: "center" }}>{w.date}<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>}
          {(needsUrl || needsNote) && <label className="ask" style={{ marginTop: 10, maxWidth: 480 }}><span className="sr">{needsUrl ? w.link : primaryTurn?.label}</span><input value={note} onChange={(e) => setNote(e.target.value)} placeholder={needsUrl ? `${w.link} …` : `${primaryTurn?.label} …`} /></label>}
          </>)}
        </div>

        <aside className="thread" aria-label={w.conversation} data-help="cf.thread">
          <p className="kicker">{w.conversation}</p>
          <div className="thread-scroll" ref={threadRef}>
          <Thread entries={v.entries} meName={me.name ?? ""} agentName={v.agent} lang={lang} w={w} busy={busy}
                  stageWord={stageWord}
                  onAnswer={(e, text) => entry.mutate({ kind: "answer", step_id: stepId("answer"), resolves: e.id, text })}
                  onDone={(e) => entry.mutate({ kind: "done", step_id: stepId("done"), resolves: e.id })} />
          </div>
          {secondary.length > 0 && (
            <div className="chips">
              {secondary.map((t) => <button key={t.action} type="button" className={`chip${pending?.action === t.action ? " on" : ""}`} disabled={busy || t.blocked_by.length > 0} title={t.blocked_by.join(", ")}
                                            onClick={() => { setPending(t); setAsk(""); askRef.current?.focus(); }}>{t.label}</button>)}
            </div>
          )}
          <form className="ask" onSubmit={(e) => { e.preventDefault(); if (!ask.trim()) return; if (pending) { step.mutate({ action: pending.action, payload: { note: ask.trim(), text: ask.trim() } }); setPending(null); setAsk(""); } else run.mutate(ask.trim()); }}>
            <span className="sr">{pending ? pending.label : w.notePlaceholder(v.agent)}</span>
            {pending && <span className="chip on small" onClick={() => setPending(null)} role="button" tabIndex={0}>{pending.label} ×</span>}
            <input ref={askRef} value={ask} onChange={(e) => setAsk(e.target.value)} placeholder={pending ? `${pending.label} …` : w.notePlaceholder(v.agent)} />
            <button type="submit" className="send" disabled={busy || !ask.trim()} aria-label="↵"><Send /></button>
          </form>
        </aside>
      </div>

      <footer className="foot">
        {primaryTurn && framesAreTheMove ? (
          <span className="says">{w.fillFrames(blocked.map(blockedWord).join(", "))}</span>
        ) : primaryTurn ? (
          <>
            {blocked.length > 0 && <span className="says">{w.firstHere}: {blocked.map(blockedWord).join(", ")}</span>}
            {blocked.length === 0 && needsAmount && <label className="money says-input"><span>{w.amount}</span><input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="€" inputMode="decimal" autoFocus /></label>}
            {blocked.length === 0 && needsDate && !date && <span className="says">{w.firstHere}: {w.date}</span>}
            {!blocked.length && primaryTurn.reason && !mine && <span className="says">{primaryTurn.reason}</span>}
            <button type="button" className="btn" disabled={!canPress} onClick={() => primaryTurn.action === "interview" ? go(`/case/${encodeURIComponent(id)}/gespraech`) : primaryTurn.action === "approve_canon" ? go(`/case/${encodeURIComponent(id)}/ergebnis`) : step.mutate({ action: primaryTurn.action, payload })}>{primaryTurn.label} →</button>
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
