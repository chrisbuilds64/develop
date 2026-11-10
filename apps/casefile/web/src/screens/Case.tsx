// One case (design hand-back, 2026-11-05): a slim bar with the number and the place in the queue; the head (photo or
// initials, title, who it is from, urgent); the line of stations; one card with what the core proposes and the one
// button for it — the AI's reading of a mail with its facts and suggestion, or the plain sentence of the move — and, when
// the case lies elsewhere or is closed, remind, take back or move back; what is on the desk; the keys. Beside it the
// conversation, the documents and the details. Every action is a step of the core; Undo follows the core's undo_step.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, BASE, sample as putSample, stepId, type CaseView, type ConfigView, type MeOut, type Turn, type Entry } from "../api";
import { Conversation } from "../components/Conversation";
import { Seal, DocIcon, PenIcon, PhotoIcon } from "../components/Icons";
import { NoteField, openNote } from "../components/NoteField";
import { Reader, type Doc } from "../components/Reader";
import { MetaList } from "../components/MetaSheet";
import { casesOf, type Tab } from "./Queue";
import { ago, dateWords, type words } from "../words";
import { paper, thud, tick } from "../moments";

type W = ReturnType<typeof words>;

/** The documents on the desk, newest version each, the primary first — the order the reader walks. */
export function docsOf(v: CaseView): Doc[] {
  const present = v.slots.filter((s) => s.present && !["meta.json", "review.md"].includes(s.file) && !["interview", "data"].includes(s.shape));
  const ordered = v.primary ? [...present.filter((s) => s.file === v.primary), ...present.filter((s) => s.file !== v.primary)] : present;
  return ordered.map((s) => ({ word: s.word, shape: s.shape, versions: s.versions.map((v) => ({ name: v.name, version: v.version, url: v.url })) }));
}

type Reading = { kind?: string; rule?: string; urgency?: string; summary?: string; fields?: Record<string, string>; labels?: Record<string, string>; reasons?: string[] };
type Done = { case?: string; title?: string; url?: string; target_label?: string };

// Every station has a column of its own, so no two words touch at any width (SW-2026-002): the columns share the line
// equally, except that the current station's column never gets narrower than its word; a word that does not fit its
// column is cut with an ellipsis and keeps the full word in its title. Each column draws its own piece of the track, so
// the track meets the dots however wide the columns end up.
function Stations({ stations, caseId }: { stations: { key: string; word: string; state: string }[]; caseId: string }) {
  const cur = Math.max(0, stations.findIndex((s) => s.state === "current"));
  const prev = useRef<{ id: string; cur: number } | null>(null);
  useEffect(() => {
    const p = prev.current;
    if (p && p.id === caseId && cur > p.cur) for (let i = 0; i < cur - p.cur; i++) tick(0.12 + i * 0.11);
    prev.current = { id: caseId, cur };
  }, [cur, caseId]);
  const columns = stations.map((_, i) => (i === cur ? "minmax(max-content, 1fr)" : "minmax(0, 1fr)")).join(" ");
  return (
    <div className="sline" role="img" aria-label={`${stations[cur]?.word ?? ""} · ${stations.map((s) => s.word).join(", ")}`} data-help="cf.stations">
      <div className="sst" style={{ gridTemplateColumns: columns }}>
        {stations.map((s) => (
          <span key={s.key} title={s.word} className={s.state === "done" ? "past" : s.state === "current" ? "now" : ""}><b /><em>{s.word}</em></span>
        ))}
      </div>
    </div>
  );
}

function Missing({ slot, mine, busy, sample, w, onFile, onSample }: { slot: CaseView["slots"][number]; mine: boolean; busy: boolean; sample: boolean; w: W; onFile: (f: File) => void; onSample: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const accept = slot.shape.startsWith("image") ? "image/*" : slot.shape.startsWith("video") ? "video/*" : slot.shape === "pdf" ? "application/pdf" : undefined;
  return (
    <div className={`doc missing${mine ? " mine" : ""}${over ? " over" : ""}`} role="button" tabIndex={0} aria-label={`${slot.word} · ${w.dropHere}`}
         onClick={() => !busy && input.current?.click()} onKeyDown={(e) => { if (e.key === "Enter") input.current?.click(); }}
         onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
         onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}>
      <span className="dn">{slot.word}</span>
      <span className="dm">{over ? w.dropHere : slot.by_word ? w.delivers(slot.by_word) : w.missingDrop}</span>
      {sample && <button type="button" className="d-sample" disabled={busy} onClick={(e) => { e.stopPropagation(); onSample(); }}>{w.useSample}</button>}
      <input ref={input} type="file" accept={accept} hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
    </div>
  );
}

export function CaseScreen({ id, config, me, go, w, tab = "you" }: { id: string; config: ConfigView; me: MeOut; go: (p: string) => void; w: W; tab?: Tab }) {
  const qc = useQueryClient();
  const lang = config.lang;
  const q = useQuery({ queryKey: ["case", id], queryFn: () => api.case(id), retry: false, refetchInterval: (query) => (query.state.data?.group === "claude" ? 2500 : 25_000) });
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const rules = useQuery({ queryKey: ["rules"], queryFn: api.rules, staleTime: 60_000 });
  const samples = ((config.theme as { samples?: string[] }).samples ?? []);
  const [refused, setRefused] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; undo?: boolean; sealed?: boolean } | null>(null);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [pending, setPending] = useState<Turn | null>(null);
  const [reading, setReading] = useState<string | null>(null);
  const [side, setSide] = useState<"conv" | "docs" | "details">("conv");
  const threadRef = useRef<HTMLDivElement>(null);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["case", id] }); qc.invalidateQueries({ queryKey: ["groups"] }); qc.invalidateQueries({ queryKey: ["turns"] }); qc.invalidateQueries({ queryKey: ["rhythm"] }); };
  const fail = (e: unknown) => setRefused(e instanceof ApiError ? e.message : String(e));
  const stageWord = (f: string) => ((config.words as { stages?: Record<string, string> }).stages?.[f]) ?? f.replace(/^\d+-/, "");
  const actionWord = (a: string) => ((config.words as { actions?: Record<string, string> }).actions?.[a]) ?? a;
  const roleWord = (actor: string) => actor.startsWith("role:") ? (((config.words as { roles?: Record<string, string> }).roles?.[actor.slice(5)]) ?? actor.slice(5)) : (config.people.find((p) => p.id === actor)?.name ?? actor);

  const step = useMutation({ mutationFn: (p: { action: string; payload?: Record<string, unknown>; label?: string }) => api.step(id, p.action, stepId(p.action), p.payload ?? {}), onSuccess: (r, p) => {
    setRefused(null); refresh(); setAmount(""); setDate(""); setNote("");
    if (p.action === "undo") { setToast({ text: w.undone }); return; }
    if (p.action === "remind") { setToast({ text: w.reminded((q.data?.held_by ?? []).join(", ")) }); return; }
    const t = q.data?.my_turns.find((x) => x.action === p.action);
    if (t?.seal && !r.replayed) thud();
    const text = `${p.label ?? t?.label ?? actionWord(p.action)}${r.to ? ` · ${stageWord(r.to)}` : ""}`;
    setToast({ text, sealed: !!t?.seal, undo: !!r.to && !["take_back", "reopen", "correct"].includes(p.action) });
  }, onError: fail });
  const entry = useMutation({ mutationFn: (b: Parameters<typeof api.entry>[1]) => api.entry(id, b), onSuccess: () => { setRefused(null); refresh(); }, onError: fail });
  const run = useMutation({ mutationFn: (text: string) => api.run(id, { note: text, request_id: stepId("ask") }), onSuccess: () => { setRefused(null); refresh(); }, onError: fail });
  const upload = useMutation({ mutationFn: (p: { slot: string; file: File }) => api.asset(id, p.slot, stepId("up"), p.file), onSuccess: () => { setRefused(null); paper(); refresh(); }, onError: fail });
  const sampleIn = useMutation({ mutationFn: (slot: string) => putSample(id, slot, stepId("sample")), onSuccess: () => { setRefused(null); paper(); refresh(); }, onError: fail });

  const entryCount = q.data?.entries.length ?? 0;
  useEffect(() => { const el = threadRef.current; if (el) el.scrollTop = el.scrollHeight; }, [entryCount, id, side]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 7000); return () => clearTimeout(t); }, [toast]);
  useEffect(() => { setReading(null); setPending(null); setRefused(null); }, [id]);

  const v = q.data;
  const list = casesOf(groups.data, tab);
  const at = list.findIndex((c) => c.id === id);
  const neighbour = (d: number) => (at >= 0 ? list[at + d] : undefined);
  const busy = step.isPending || entry.isPending || run.isPending || upload.isPending || sampleIn.isPending;
  const actionTurns = (v?.my_turns ?? []).filter((t) => !["answer", "wait"].includes(t.action));
  const primaryTurn: Turn | undefined = actionTurns[0];
  const asks = primaryTurn?.payload ?? [];
  const needsAmount = asks.includes("amount"), needsDate = asks.includes("date"), needsUrl = asks.includes("url"), needsNote = asks.includes("note");
  const blocked = primaryTurn?.blocked_by ?? [];
  const special = primaryTurn && ["interview", "approve_canon", "deliver"].includes(primaryTurn.action);
  const canPress = !!primaryTurn && blocked.length === 0 && (!needsAmount || !!amount.trim()) && (!needsDate || !!date) && (!needsNote || !!note.trim()) && !busy;
  const payload: Record<string, unknown> = {};
  if (needsAmount) payload.amount = amount.trim();
  if (needsDate) payload.date = date;
  if (needsUrl) payload.url = note.trim() || "https://example.invalid/";
  if (note.trim() && !needsUrl) payload.note = note.trim();
  const press = () => {
    if (!primaryTurn || !canPress) return;
    if (primaryTurn.action === "interview") return go(`/case/${encodeURIComponent(id)}/gespraech`);
    if (primaryTurn.action === "approve_canon") return go(`/case/${encodeURIComponent(id)}/ergebnis`);
    step.mutate({ action: primaryTurn.action, payload, label: primaryTurn.label });
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) || t.isContentEditable;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") { e.preventDefault(); setSide("conv"); openNote(); return; }
      if (typing || e.metaKey || e.ctrlKey || e.altKey || reading) return;
      if (e.key === "j" && neighbour(1)) go(`/case/${encodeURIComponent(neighbour(1)!.id)}?g=${tab}`);
      else if (e.key === "k" && neighbour(-1)) go(`/case/${encodeURIComponent(neighbour(-1)!.id)}?g=${tab}`);
      else if (e.key === "Escape") go("/");
      else if (e.key === "Enter" && t.tagName !== "BUTTON" && t.tagName !== "A") { e.preventDefault(); press(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (q.isLoading) return <div className="ws-case"><main className="center" /></div>;
  if (!v) return <div className="ws-case"><main className="center"><p className="c-empty">{q.error instanceof ApiError && q.error.status === 404 ? w.notHere : q.error ? w.unreachable : "…"}</p></main></div>;

  const mine = v.mine;
  const main: Turn | undefined = v.my_turns[0] ?? v.turns[0];
  const docs = docsOf(v);
  const readingIndex = reading === null ? -1 : docs.findIndex((d) => d.versions.some((x) => x.name === reading));
  const openFile = (name: string) => { const d = docs.find((x) => x.versions.some((y) => y.name === name || name.endsWith(y.name))); if (d) setReading(d.versions[d.versions.length - 1].name); };
  const data = ((v as unknown as { data?: Record<string, unknown> }).data ?? {});
  const r = data["einordnung.json"] as Reading | undefined;
  const done = data["aktion.json"] as Done | undefined;
  const row = r ? rules.data?.matrix?.find((m) => m.id === r.rule) : undefined;
  const blockedWord = (b: string) => {
    const slot = v.slots.find((s) => s.file === b);
    if (slot) return slot.word;
    if (b.startsWith("shape:")) { const want = b.slice(6); const first = v.slots.find((s) => !s.present && s.shape.startsWith(want)); return first ? first.word : w.shape(want); }
    return ((config.words as { files?: Record<string, string> }).files?.[b]) ?? b;
  };
  const byHelper = (s: { by: string; by_word: string }) => s.by === "claude" || (!!s.by_word && s.by_word === v.agent);
  const seriesOf = (f: string) => /^(.+)-\d+\.(\w+)$/.exec(f)?.slice(1).join(".");
  const firstFree = new Set<string>();
  const nextOfSeries = (s: { file: string }) => { const k = seriesOf(s.file); if (!k) return true; if (firstFree.has(k)) return false; firstFree.add(k); return true; };
  const desk = v.slots.filter((s) => s.present && !["meta.json", "review.md"].includes(s.file) && !["interview", "data"].includes(s.shape));
  const blocksMe = (s: { file: string; shape: string }) => blocked.includes(s.file) || (blocked.some((b) => b.startsWith("shape:")) && blocked.some((b) => s.shape.startsWith(b.slice(6))));
  const othersDeliver = (s: { by: string; by_word: string }) => !!s.by && s.by !== "human" && !byHelper(s) && !(me.roles ?? []).some((r) => s.by === `role:${r}` || s.by === r);
  const missing = v.slots.filter((s) => !s.present && s.file !== "meta.json" && s.file !== "review.md" && !["interview", "data"].includes(s.shape) && !byHelper(s)
    && (blocksMe(s) || (mine && (s.required || s.due_station === v.station) && !othersDeliver(s)))).filter(nextOfSeries);
  const talkSlot = v.slots.find((s) => s.shape === "interview");
  const outcomeReady = v.slots.some((s) => s.shape === "data" && s.present);
  const draftHere = v.slots.some((s) => s.file === ((config.theme as { interview?: { draft?: string } }).interview?.draft) && s.present);
  const onsiteHere = ((config.theme as { onsite?: { stages?: string[] } }).onsite?.stages ?? []).includes(v.stage);
  const party = v.party || "";
  const initials = (party || v.title).split(/[\s,]+/).filter(Boolean).slice(0, 2).map((x) => x[0]).join("").toUpperCase();
  const urgent = main?.kind === "date" || r?.urgency === "high";
  const stub = main
    ? mine ? `${w.forYou} · ${primaryTurn?.reason && primaryTurn.reason !== v.stage_word ? primaryTurn.reason : v.stage_word}`
      : main.actor === "claude" ? `${w.isWorking(v.agent)}${v.since ? ` · ${w.since} ${ago(v.since, lang)}` : ""}`
      : `${v.stage_word} · ${w.waitingFor(roleWord(main.actor))}`
    : `${v.stage_word}${v.date ? ` · ${dateWords(v.date, lang)}` : ""}`;
  // the core's sentence for the move, without the case's own title, which the head already shows
  const headline = (primaryTurn?.headline ?? "").split(`${v.title}: `).join("").split(`: ${v.title}`).join("").trim();
  const secondary = actionTurns.slice(1);
  const cap = (x: string) => (x ? x.charAt(0).toUpperCase() + x.slice(1) : x);
  const canCorrect = (e: Entry) => !!e.step && !!(e.to || e.amount) && e.actor === "person" && !["undone", "correction"].includes(e.status) && e.step !== v.undo_step;

  const button = primaryTurn && !special && (
    <span className="tipw">
      <button type="button" className="primary" disabled={!canPress} data-action={primaryTurn.action} onClick={press}>
        {primaryTurn.seal && <span className="p-seal"><Seal /></span>}{r && !done ? w.confirmCarry : primaryTurn.label} <span className="k">⏎</span>
      </button>
    </span>
  );
  const inputs = primaryTurn && blocked.length === 0 && (
    <>
      {needsAmount && <label className="c-field"><span>{w.amount}</span><input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="€" inputMode="decimal" /></label>}
      {needsDate && <label className="c-field"><span>{w.date}</span><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>}
      {(needsUrl || needsNote) && <label className="c-field wide"><span>{needsUrl ? w.link : primaryTurn.label}</span><input value={note} onChange={(e) => setNote(e.target.value)} placeholder="…" /></label>}
    </>
  );
  const otherActs = (
    <>
      {secondary.map((t) => (
        <button key={t.action} type="button" className="ghost" disabled={busy || t.blocked_by.length > 0} data-action={t.action}
                onClick={() => { if (!(t.payload ?? []).includes("note")) { step.mutate({ action: t.action, label: t.label }); return; } setPending(t); setSide("conv"); openNote(); }}>{t.label}</button>
      ))}
      {special && primaryTurn && (
        <button type="button" className="ghost" onClick={() => primaryTurn.action === "interview" ? go(`/case/${encodeURIComponent(id)}/gespraech`) : primaryTurn.action === "approve_canon" ? go(`/case/${encodeURIComponent(id)}/ergebnis`) : undefined}>{primaryTurn.label} →</button>
      )}
    </>
  );

  return (
    <div className="ws-case">
      <main className="center">
        <div className="c-bar">
          <span className="cid" title={v.id}>{v.external_id ? (v.external_url ? <a href={v.external_url} target="_blank" rel="noreferrer">{v.external_id}</a> : v.external_id) : v.number ? `${v.label}-${v.number}` : v.id}</span>
          <span className="c-meta">· {v.label_word}{v.meta?.created ? ` · ${dateWords(String(v.meta.created), lang)}` : ""}</span>
          {at >= 0 && <span className="c-of">{w.ofN(at + 1, list.length)}</span>}
        </div>
        {readingIndex >= 0 ? (
          <div className="c-reader"><Reader docs={docs} index={readingIndex} caseId={id} onIndex={(i) => setReading(docs[i].versions[docs[i].versions.length - 1].name)} onClose={() => setReading(null)} w={w} /></div>
        ) : (
        <div className="case">
          <header className="c-head" data-help="cf.case-head">
            <span className="hav" aria-hidden="true">{initials}</span>
            <div className="hmain">
              <h1 className="title">{v.title}</h1>
              <div className="hsub">{party && <span>{party}</span>}{urgent && <span className="hurg">{w.urgent}</span>}</div>
            </div>
          </header>
          <Stations stations={v.stations} caseId={v.id} />
          <p className="c-stub"><i className={mine ? "you" : main?.actor === "claude" ? "ai" : ""} />{stub}</p>

          {refused && <div className="c-refused">{refused}</div>}

          {r ? (
            <div className="aicard" data-help="cf.triage"><div>
              <div className="ai-head"><span className="plab"><span>✦</span> {w.aiSummary}</span>{(row?.word || r.kind) && <span className="rdas">{w.readAs}: <b>{row?.word ?? r.kind}</b></span>}</div>
              {r.summary && <p className="ai-lead">{r.summary}</p>}
              {r.fields && Object.keys(r.fields).filter((k) => r.fields![k] && !k.endsWith("_short") && k !== "title").length > 0 && (
                <dl className="facts2">{Object.entries(r.fields).filter(([k, x]) => x && !k.endsWith("_short") && k !== "title").map(([k, x]) => <div key={k}><dt>{r.labels?.[k] ?? k.replace(/_/g, " ")}</dt><dd>{x}</dd></div>)}</dl>
              )}
              {!!r.reasons?.length && (
                <div className="src"><div className="srch">{w.fromMail}</div>{r.reasons.slice(0, 3).map((x, i) => <div key={i} className="srcq"><span>{x}</span></div>)}</div>
              )}
              {done ? (
                <div className="proposal done triage-done"><span className="plab"><Seal /> {w.sealed}</span>
                  <b>{done.case ? <>{w.triageDone(done.target_label ?? "")} {done.url ? <a href={new URL(done.url, window.location.origin + BASE + "/").pathname}>{done.title ?? done.case}</a> : (done.title ?? done.case)}</> : w.triageFiled}</b></div>
              ) : primaryTurn ? (
                <div className="proposal">
                  <div className="p-what"><span className="plab"><span>✦</span> {w.aiSuggestion}</span>
                    <b>{row ? `${row.action_word}${row.target_word ? ` · ${row.target_word}` : ""}` : primaryTurn.label}</b></div>
                  <div className="pacts">{inputs}{button}{blocked.length > 0 && <span className="p-wait">{primaryTurn.lock || w.waitingOn(blocked.map(blockedWord).join(", "))}</span>}</div>
                </div>
              ) : null}
              <div className="acts2">{otherActs}</div>
            </div></div>
          ) : (
            <div className="card plain">
              {v.reopen_to ? (
                <><p>{w.closedNote}</p><div className="pacts"><button type="button" className="primary" data-help="cf.move-back" disabled={busy} onClick={() => step.mutate({ action: "reopen", label: w.moveBack })}>{w.moveBack} · {v.reopen_word}</button></div></>
              ) : (v.held_by ?? []).length > 0 ? (
                <><p>{w.heldBy((v.held_by ?? []).join(", "))}</p>
                  {primaryTurn && <div className="pacts">{inputs}{button}{blocked.length > 0 && <span className="p-wait">{w.waitingOn(blocked.map(blockedWord).join(", "))}</span>}</div>}
                  <div className="pacts" data-help="cf.held">
                    <button type="button" className={primaryTurn ? "ghost" : "primary"} disabled={busy} onClick={() => step.mutate({ action: "remind" })}>{w.remind}</button>
                    {v.take_back_to && <button type="button" className="ghost" disabled={busy} onClick={() => step.mutate({ action: "take_back", label: w.takeBack })}>{w.takeBack} · {v.take_back_word}</button>}
                  </div>
                  {primaryTurn && (secondary.length > 0 || special) && <div className="acts2">{otherActs}</div>}</>
              ) : primaryTurn ? (
                <><p>{cap(headline || primaryTurn.reason || primaryTurn.label)}</p>
                  <div className="pacts">{inputs}{button}{blocked.length > 0 && <span className="p-wait">{w.waitingOn(blocked.map(blockedWord).join(", "))}</span>}</div>
                  {(secondary.length > 0 || special) && <div className="acts2">{otherActs}</div>}</>
              ) : mine && main?.action === "answer" ? (
                <><p>{cap(main.reason)}</p>
                  <div className="pacts"><button type="button" className="primary" onClick={() => { setSide("conv"); setTimeout(() => document.querySelector<HTMLButtonElement>(".msg.oq .mbtn")?.click(), 0); }}>{w.answer}</button></div></>
              ) : (
                <p>{main ? (main.actor === "claude" ? w.isWorking(v.agent) : w.waitingFor(roleWord(main.actor))) : v.stage_word}</p>
              )}
            </div>
          )}

          <div className="c-desk" data-help="cf.desk">
            <div className="deskh">{w.onDesk}</div>
            <div className="docs">
              {talkSlot && v.station !== "prepare" && <button type="button" className="doc tile" data-help="cf.talk-tile" onClick={() => go(`/case/${encodeURIComponent(id)}/gespraech`)}><span className="dn">{w.talkOpen}</span><span className="dm">{w.talkOpenHint}</span></button>}
              {((talkSlot && outcomeReady) || (!talkSlot && draftHere)) && <button type="button" className="doc tile" data-help="cf.outcome-tile" data-outcome="1" onClick={() => go(`/case/${encodeURIComponent(id)}/ergebnis`)}><span className="dn">{w.outcomeOpen}</span><span className="dm">{w.outcomeOpenHint}</span></button>}
              {onsiteHere && <button type="button" className="doc tile" data-onsite="1" data-help-skip="explained by cf.desk" onClick={() => go(`/case/${encodeURIComponent(id)}/vorort`)}><span className="dn">{w.onsite} →</span><span className="dm">{w.onsiteHint}</span></button>}
              {(() => {
                const photos = desk.filter((s) => s.shape.startsWith("image"));
                const rest = desk.filter((s) => !s.shape.startsWith("image"));
                const tile = (key: string, word: string, meta: string, open: () => void, icon: ReactNode) => (
                  <button key={key} type="button" className="doc" data-file={key} onClick={open}>
                    <span className="dn">{icon}{word}</span><span className="dm">{meta}</span>
                  </button>
                );
                const metaOf = (s: CaseView["slots"][number]) => { const n = s.versions[s.versions.length - 1]; return `${w.version(Math.max(1, n.version))}${s.by_word ? ` · ${s.by_word}` : ""}`; };
                return <>
                  {rest.map((s) => tile(s.file, s.word, metaOf(s), () => setReading(s.versions[s.versions.length - 1].name), s.shape === "pdf" ? <DocIcon /> : s.shape === "money" ? <DocIcon /> : <PenIcon />))}
                  {photos.length === 1 && tile(photos[0].file, photos[0].word, metaOf(photos[0]), () => setReading(photos[0].versions[photos[0].versions.length - 1].name), <PhotoIcon />)}
                  {photos.length > 1 && tile("photos", `${w.photos} (${photos.length})`, metaOf(photos[0]), () => setReading(photos[0].versions[photos[0].versions.length - 1].name), <PhotoIcon />)}
                </>;
              })()}
              {missing.map((s) => <Missing key={s.file} slot={s} mine={mine && blocked.includes(s.file)} busy={busy} sample={samples.includes(s.file)} w={w}
                                           onFile={(f) => upload.mutate({ slot: s.file, file: f })} onSample={() => sampleIn.mutate(s.file)} />)}
              {desk.length === 0 && missing.length === 0 && !talkSlot && <span className="c-empty">{w.deskEmpty}</span>}
            </div>
          </div>
        </div>
        )}
        <div className="c-keys" aria-hidden="true">
          <span><span className="kbd">J</span> {w.keyNext}</span><span><span className="kbd">K</span> {w.keyPrev}</span>
          <span><span className="kbd">⏎</span> {w.keyConfirm}</span><span><span className="kbd">Esc</span> {w.keyHome}</span>
        </div>
      </main>

      <aside className="insp" aria-label={w.conversation}>
        <div className="tabs" role="tablist">
          {(["conv", "docs", "details"] as const).map((t) => (
            <button key={t} type="button" role="tab" aria-selected={side === t} className={side === t ? "on" : ""} onClick={() => setSide(t)}>{t === "conv" ? w.conversation : t === "docs" ? w.documents : w.details}</button>
          ))}
        </div>
        {side === "conv" ? (
          <div className="i-thread" ref={threadRef} data-help="cf.thread">
            <Conversation entries={v.entries} meName={me.name ?? ""} lang={lang} w={w} busy={busy} stageWord={stageWord} onFile={openFile}
                          onAnswer={(e, text) => entry.mutate({ kind: "answer", step_id: stepId("answer"), resolves: e.id, text })}
                          onDone={(e) => entry.mutate({ kind: "done", step_id: stepId("done"), resolves: e.id })}
                          canCorrect={canCorrect} onCorrect={(e, text, amt) => step.mutate({ action: "correct", label: w.correct, payload: { corrects: e.id, text, ...(amt ? { amount: amt } : {}) } })} />
          </div>
        ) : side === "docs" ? (
          <div className="i-thread">
            {docs.length === 0 ? <p className="conv-empty">{w.noDocs}</p> : docs.map((d) => (
              <button key={d.word} type="button" className="i-doc" onClick={() => setReading(d.versions[d.versions.length - 1].name)}>
                <b>{d.word}</b><small>{w.versionsN(d.versions.length)} · {d.versions[d.versions.length - 1].name}</small>
              </button>
            ))}
          </div>
        ) : (
          <div className="i-thread"><MetaList meta={(v.meta ?? {}) as Record<string, unknown>} words={(config.words ?? {}) as Record<string, unknown>} lang={lang} lists={config.lists ?? []} /></div>
        )}
        <NoteField caseId={id} chip={pending?.label} onChip={() => setPending(null)} placeholder={pending ? `${pending.label} …` : w.askAiPh} busy={busy} w={w}
                   onSend={(text) => pending
                     ? step.mutateAsync({ action: pending.action, label: pending.label, payload: { note: text, text } }).then(() => setPending(null))
                     : run.mutateAsync(text)} />
      </aside>

      {toast && (
        <div className={`c-toast${toast.sealed ? " sealed" : ""}`} role="status">
          {toast.sealed && <span className="t-seal"><Seal /></span>}<span>{toast.text}</span>
          {toast.undo && v.undo_step && <button type="button" data-help="cf.undo" onClick={() => { setToast(null); step.mutate({ action: "undo" }); }}>{w.undo}</button>}
          {neighbour(1) && <button type="button" onClick={() => { setToast(null); go(`/case/${encodeURIComponent(neighbour(1)!.id)}?g=${tab}`); }}>{w.keyNext} →</button>}
        </div>
      )}
    </div>
  );
}
