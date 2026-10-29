// The gate (ADR-024): one case in full depth. The place line, the headline as a sentence, the path with its dates, the
// situation in four lines, the evidence — what is missing first, then what is present, every line with its origin —
// exactly one filled button, a locked gate as a sentence with a lock, the second way as a text link. Behind it, folded in
// place: the ways into a conversation, the outcome or the site; the thread; every file; the record.
// Everything comes from CaseView and the vocabulary; nothing here names a domain.
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, BASE, sample as putSample, stepId, type CaseView, type ConfigView, type Entry, type MeOut, type SlotView, type Turn } from "../api";
import { DropLine } from "../components/Frames";
import { Thread } from "../components/Thread";
import { Cover } from "../components/Cover";
import { Arrow, Check, Chev, Lock, Send, Wait, You } from "../components/Icons";
import { Reader, type Doc } from "../components/Reader";
import { dateMon, dateRange, dateShort, type words } from "../words";
import { paper, thud } from "../moments";
import { MailTriage } from "../components/MailTriage";
import { MetaSheet } from "../components/MetaSheet";

type Vocabulary = Record<string, Record<string, string> | undefined>;
const HIDDEN = ["meta.json", "review.md"];
const isDoc = (s: SlotView) => !HIDDEN.includes(s.file) && !["interview", "data"].includes(s.shape);
const seriesOf = (f: string) => /^(.+)-\d+\.(\w+)$/.exec(f)?.slice(1).join(".");
const fill = (s: string, ctx: Record<string, string>) => Object.entries(ctx).reduce((t, [k, val]) => t.split(`{${k}}`).join(val), s).trim();

/** The documents in the case, newest version each, the primary first — the order the reader walks. */
export function docsOf(v: CaseView): Doc[] {
  const present = v.slots.filter((s) => s.present && isDoc(s));
  const ordered = v.primary ? [...present.filter((s) => s.file === v.primary), ...present.filter((s) => s.file !== v.primary)] : present;
  return ordered.map((s) => ({ word: s.word, shape: s.shape, versions: s.versions.map((v) => ({ name: v.name, version: v.version, url: v.url })) }));
}

type Gap = { key: string; word: string; slot?: SlotView; who: string; mine: boolean };

export function CaseScreen({ id, config, me, go, w }: { id: string; config: ConfigView; me: MeOut; go: (p: string) => void; w: ReturnType<typeof words> }) {
  const qc = useQueryClient();
  const lang = config.lang;
  const q = useQuery({ queryKey: ["case", id], queryFn: () => api.case(id), retry: false, refetchInterval: (query) => (query.state.data?.group === "claude" ? 2500 : 25_000) });
  const stagesQ = useQuery({ queryKey: ["stages"], queryFn: api.stages, staleTime: 60_000 });
  const samples = ((config.theme as { samples?: string[] }).samples ?? []);
  const voc = (config.words ?? {}) as Vocabulary;
  const extWord = voc.words?.external_id ?? "";
  const [refused, setRefused] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; undo?: () => void; sealed?: boolean } | null>(null);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [ask, setAsk] = useState("");
  const [pending, setPending] = useState<Turn | null>(null);
  const [reading, setReading] = useState<string | null>(null);
  const [landed, setLanded] = useState<string | null>(null);         // the slot that just received a file: its line lights up once
  const [threadOpen, setThreadOpen] = useState(false);
  const [filesOpen, setFilesOpen] = useState(false);
  const askRef = useRef<HTMLInputElement>(null);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["case", id] }); qc.invalidateQueries({ queryKey: ["groups"] }); qc.invalidateQueries({ queryKey: ["turns"] }); };
  const fail = (e: unknown) => setRefused(e instanceof ApiError ? e.message : String(e));
  const stageWord = (f: string) => voc.stages?.[f] ?? f.replace(/^\d+-/, "");
  const step = useMutation({ mutationFn: (p: { action: string; payload?: Record<string, unknown> }) => api.step(id, p.action, stepId(p.action), p.payload ?? {}), onSuccess: (r, p) => {
    setRefused(null); refresh();
    const gate = q.data?.my_turns.find((t) => t.action === p.action)?.seal && !r.replayed;
    if (gate) { thud(); setToast({ text: `${q.data?.my_turns.find((t) => t.action === p.action)?.label ?? ""}${r.to ? ` · ${stageWord(r.to)}` : ""}`, sealed: true }); }
    else if (r.to) setToast({ text: w.doneMoved(stageWord(r.to)) });
  }, onError: fail });
  const entry = useMutation({ mutationFn: (b: Parameters<typeof api.entry>[1]) => api.entry(id, b), onSuccess: () => { setRefused(null); refresh(); }, onError: fail });
  const run = useMutation({ mutationFn: (text: string) => api.run(id, { note: text, request_id: stepId("ask") }), onSuccess: () => { setRefused(null); setAsk(""); refresh(); }, onError: fail });
  const upload = useMutation({ mutationFn: (p: { slot: string; file: File }) => api.asset(id, p.slot, stepId("up"), p.file), onSuccess: (_r, p) => { setRefused(null); setLanded(p.slot); paper(); refresh(); }, onError: fail });
  const sampleIn = useMutation({ mutationFn: (slot: string) => putSample(id, slot, stepId("sample")), onSuccess: (_r, slot) => { setRefused(null); setLanded(slot); paper(); refresh(); }, onError: fail });
  useEffect(() => { if (!landed) return; const t = setTimeout(() => setLanded(null), 1600); return () => clearTimeout(t); }, [landed]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 6000); return () => clearTimeout(t); }, [toast]);
  useEffect(() => { setReading(null); setPending(null); setThreadOpen(false); setFilesOpen(false); }, [id]);
  // an open question for the viewer unfolds the thread; the thread is where it is answered
  const answerForMe = q.data?.my_turns.some((t) => t.action === "answer") ?? false;
  useEffect(() => { if (answerForMe) setThreadOpen(true); }, [answerForMe, id]);
  const openAsk = () => { setThreadOpen(true); setTimeout(() => askRef.current?.focus(), 50); };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openAsk(); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (q.isLoading) return <main className="main gate-main"><p className="empty">…</p></main>;
  if (!q.data) return <main className="main gate-main"><p className="empty">{q.error instanceof ApiError && q.error.status === 404 ? w.notHere : q.error ? w.unreachable : "…"}</p></main>;
  const v = q.data;
  const busy = step.isPending || entry.isPending || run.isPending || upload.isPending || sampleIn.isPending;

  // ---- who is who: a person by id, a role by the people who hold it (one name) or by its word, the agent by its name
  const actorWord = (actor: string): string => {
    if (actor === "claude") return v.agent;
    if (actor.startsWith("role:")) {
      const role = actor.slice(5);
      const holders = config.people.filter((p) => p.kind === "human" && p.roles.includes(role));
      return holders.length === 1 ? holders[0].name : (voc.roles?.[role] ?? role);
    }
    return config.people.find((p) => p.id === actor)?.name ?? actor;
  };
  const roleWord = (actor: string) => (actor.startsWith("role:") ? (voc.roles?.[actor.slice(5)] ?? actor.slice(5)) : "");
  const isAgent = (name: string) => !!name && name === v.agent;

  // ---- the moves: the viewer's first, else the case's; free before locked; exactly one button
  const mine = v.my_turns.length > 0;
  const mainTurn: Turn | undefined = v.my_turns[0] ?? v.turns[0];
  const actionTurns = v.my_turns.filter((t) => !["answer", "wait"].includes(t.action));
  const free = actionTurns.filter((t) => t.blocked_by.length === 0);
  const locked = actionTurns.filter((t) => t.blocked_by.length > 0 && t.action !== "deliver");
  const deliverTurn = actionTurns.find((t) => t.action === "deliver");
  const primaryTurn: Turn | undefined = free[0];
  const secondary = free.slice(1);
  const asks = primaryTurn?.payload ?? [];
  const needsAmount = asks.includes("amount");
  const needsDate = asks.includes("date");
  const needsUrl = asks.includes("url");
  const needsNote = asks.includes("note");
  const canPress = !!primaryTurn && (!needsAmount || amount.trim()) && (!needsDate || date) && (!needsNote || note.trim()) && !busy;
  const payload: Record<string, unknown> = {};
  if (needsAmount) payload.amount = amount.trim();
  if (needsDate) payload.date = date;
  if (needsUrl) payload.url = note.trim() || "https://example.invalid/";
  if (note.trim() && !needsUrl) payload.note = note.trim();
  const press = (t: Turn) => t.action === "interview" ? go(`/case/${encodeURIComponent(id)}/gespraech`) : t.action === "approve_canon" ? go(`/case/${encodeURIComponent(id)}/ergebnis`) : step.mutate({ action: t.action, payload });

  // ---- what is missing: the tokens of the moves that wait (the viewer's, else the case's); the core has already put them into
  // words (`Turn.missing`, in the viewer's language), here each token also finds its slots
  const waiting = mine ? v.my_turns : v.turns.slice(0, 1);
  const wordOf = new Map<string, string>();
  for (const t of [...waiting, ...v.turns]) t.blocked_by.filter((b) => !b.startsWith("four eyes:")).forEach((b, i) => { if (!wordOf.has(b) && t.missing?.[i]) wordOf.set(b, t.missing[i]); });
  const missingWord = (b: string): string => wordOf.get(b) ?? v.slots.find((s) => s.file === b.split("|")[0])?.word ?? voc.files?.[b.split("|")[0]] ?? b;
  const slotsFor = (b: string): SlotView[] => b.startsWith("shape:") ? v.slots.filter((s) => !s.present && isDoc(s) && s.shape.startsWith(b.slice(6)))
    : v.slots.filter((s) => !s.present && b.split("|").includes(s.file));
  const myTokens = new Set(v.my_turns.flatMap((t) => t.blocked_by));
  const gapTokens = [...new Set(waiting.flatMap((t) => t.blocked_by))].filter((b) => !b.startsWith("four eyes:"));
  const fourEyes = waiting.flatMap((t) => t.blocked_by).filter((b) => b.startsWith("four eyes:")).map((b) => b.slice(10).trim());
  const byHelper = (s: SlotView) => s.by === "claude" || isAgent(s.by_word);
  const firstOfSeries = new Set<string>();
  const nextOfSeries = (s: SlotView) => { const k = seriesOf(s.file); if (!k) return true; if (firstOfSeries.has(k)) return false; firstOfSeries.add(k); return true; };
  const seen = new Set<string>();
  const gaps: Gap[] = [];
  for (const b of gapTokens) {
    const slots = slotsFor(b).filter(nextOfSeries).filter((s) => !seen.has(s.file));
    if (slots.length === 0) {
      const who = b === "answered" ? v.turns.filter((t) => t.action.startsWith("interview")).map((t) => actorWord(t.actor)).join(", ")
        : b.startsWith("decided:") ? (myTokens.has(b) ? w.you : actorWord(mainTurn?.actor ?? "")) : "";
      gaps.push({ key: b, word: missingWord(b), who, mine: false });
      continue;
    }
    for (const s of slots) { seen.add(s.file); gaps.push({ key: s.file, word: s.word, slot: s, who: s.by_word, mine: mine && myTokens.has(b) }); }
  }
  // and the frames the station asks for anyway: required, or due here, not made by a helper, one place per series
  for (const s of v.slots.filter((s) => !s.present && isDoc(s) && !byHelper(s) && (s.required || s.due_station === v.station) && !seen.has(s.file)).filter(nextOfSeries)) {
    seen.add(s.file); gaps.push({ key: s.file, word: s.word, slot: s, who: s.by_word, mine: false });
  }
  const gapWords = [...new Set(gapTokens.map(missingWord))];          // the situation names the condition ("ein Bild"), the evidence lists the frames

  // ---- what is present: newest version each, the primary first, who made it from the slot or the entry that delivered it
  const present = v.slots.filter((s) => s.present && isDoc(s));
  const ordered = v.primary ? [...present.filter((s) => s.file === v.primary), ...present.filter((s) => s.file !== v.primary)] : present;
  // a numbered series (fotos-1 … fotos-5) is one line with its members, not five
  const groups: { head: SlotView; members: SlotView[] }[] = [];
  for (const s of ordered) {
    const k = seriesOf(s.file);
    const g = k ? groups.find((x) => seriesOf(x.head.file) === k) : undefined;
    if (g) g.members.push(s); else groups.push({ head: s, members: [s] });
  }
  const entryFor = (name: string): Entry | undefined => [...v.entries].reverse().find((e) => e.files?.includes(name));
  const docs = docsOf(v);
  const readingIndex = reading === null ? -1 : docs.findIndex((d) => d.versions.some((x) => x.name === reading));
  const talkSlot = v.slots.find((s) => s.shape === "interview");
  const talkOpen = !!talkSlot && (talkSlot.present || v.turns.some((t) => t.action.startsWith("interview")));
  const outcomeReady = v.slots.some((s) => s.shape === "data" && s.present);
  const draftHere = v.slots.some((s) => s.file === ((config.theme as { interview?: { draft?: string } }).interview?.draft) && s.present);
  const onsiteHere = ((config.theme as { onsite?: { stages?: string[] } }).onsite?.stages ?? []).includes(v.stage);
  const last = v.entries[v.entries.length - 1];

  // ---- the path: every station with its dates, from the entries that moved the case (from → to), the current one bold
  const stationKey = (folder: string) => stagesQ.data?.find((s) => s.folder === folder)?.key ?? "";
  const sorted = [...v.entries].sort((a, b) => a.date.localeCompare(b.date));
  const starts: Record<string, string> = {};
  if (v.stations.length) starts[v.stations[0].key] = sorted[0]?.date ?? String(v.meta?.created ?? "");
  for (const e of sorted) { const k = e.to ? stationKey(e.to) : ""; if (k && !starts[k]) starts[k] = e.date; }
  const current = v.stations.find((s) => s.state === "current");
  if (current && !starts[current.key] && v.since) starts[current.key] = v.since;
  const endOf = (i: number) => { for (let j = i + 1; j < v.stations.length; j++) { const d = starts[v.stations[j].key]; if (d) return d; } return ""; };
  const stationWord = current?.word ?? v.stage_word;

  // ---- the headline: the viewer's move as a sentence, else whom the case waits for
  const t0 = v.turns[0];
  const headline = v.my_turns[0]?.headline || (t0 ? (t0.actor === "claude" ? w.workingHeadline(v.agent, v.title) : w.waitingHeadline(actorWord(t0.actor), v.title)) : `${v.stage_word}: ${v.title}`);
  const ident = v.external_id ? (v.external_url ? <a href={v.external_url} target="_blank" rel="noreferrer" title={extWord || undefined}>{v.external_id}</a> : <span title={extWord || undefined}>{v.external_id}</span>) : <span>{v.number ? `${v.label}-${v.number}` : v.id}</span>;
  const whoLine = mainTurn
    ? `${mine ? `${w.withYou}${roleWord(mainTurn.actor) ? ` (${roleWord(mainTurn.actor)})` : ""}` : actorWord(mainTurn.actor)}${mainTurn.since ? `, ${w.sinceDate(dateShort(mainTurn.since, lang))}` : ""}`
    : w.nobody;
  const noTurnText = !t0 ? w.noTurnAtAll : t0.actor === "claude" ? w.isWorking(v.agent)
    : (voc.texts?.no_turn && gapWords.length ? fill(voc.texts.no_turn, { actor: actorWord(t0.actor), missing: gapWords.join(", ") }) : w.noTurn(actorWord(t0.actor), gapWords.join(", ")));
  const lockText = (t: Turn) => t.lock || `${t.label}; ${fourEyes.join("; ")}`;
  const bold = (s: string) => { const m = /^(.*?[.;])\s(.*)$/s.exec(s); return m ? <><b>{m[1]}</b> {m[2]}</> : <b>{s}</b>; };
  const fileCount = v.slots.reduce((n, s) => n + s.versions.length, 0);
  const missingCount = v.slots.filter((s) => !s.present && isDoc(s)).length;
  const chip = (t: Turn) => (
    <button key={t.action} type="button" className={`link${pending?.action === t.action ? " on" : ""}`} disabled={busy} data-action={t.action}
            onClick={() => { if (!(t.payload ?? []).includes("note")) { press(t); return; } setPending(t); setAsk(""); openAsk(); }}>{t.label}</button>
  );

  return (
    <main className="main gate-main">
      <article className={`tor${mine ? " du" : ""}`} aria-labelledby="tor-h1">
        <header className="tor-head" data-help="cf.case-head">
          <p className="wo">
            <Cover label={v.label} number={v.number || v.id.split("-")[1] || ""} tint={v.tint} />
            <b>{v.label_word}</b>
            <span className="mono">{ident}</span>
            {v.meta?.series ? <span>{String(v.meta.series)}</span> : null}
            {v.date ? <span>{w.date} · {dateShort(v.date, lang)}</span> : null}
          </p>
          <h1 id="tor-h1" tabIndex={-1}>{headline}</h1>
          <p className="lauf" data-help="cf.stations" aria-label={stationWord}>
            {v.stations.map((s, i) => {
              const from = starts[s.key];
              const text = s.state === "current" ? (from ? `${s.word} · ${w.sinceDate(dateMon(from, lang))}` : s.word)
                : s.state === "done" ? (from ? `${s.word} · ${dateRange(from, endOf(i), lang)}` : s.word) : s.word;
              return (
                <span key={s.key} className={`st ${s.state}`}>
                  {i > 0 && <span className="pfeil" aria-hidden="true">→</span>}
                  {s.state === "current" ? <b aria-current="step">{text}</b> : <span>{text}</span>}
                  {s.state === "current" && mainTurn && (
                    <span className={`wer${mine ? " du" : ""}${!mine && mainTurn.actor === "claude" ? " ki" : ""}`}>{mine ? <You /> : <Wait />}{mine ? w.you : actorWord(mainTurn.actor)}</span>
                  )}
                </span>
              );
            })}
          </p>
        </header>

        <dl className="lage">
          <dt>{w.place}</dt><dd>{config.product} · {stationWord}</dd>
          <dt>{w.withWhom}</dt><dd>{whoLine}</dd>
          <dt>{w.missingPos}</dt><dd className="fehl">{gapWords.join(", ") || w.nothingMissing}</dd>
          <dt>{w.lastPos}</dt><dd>{last ? `${last.title} · ${last.author} · ${dateShort(last.date, lang)}` : w.noEntry}</dd>
        </dl>

        {refused && <div className="refused">{refused}</div>}

        <div className="desk" data-help="cf.desk">
          {readingIndex >= 0 ? (
            <Reader docs={docs} index={readingIndex} caseId={id} onIndex={(i) => setReading(docs[i].versions[docs[i].versions.length - 1].name)} onClose={() => setReading(null)} w={w} />
          ) : (
            <>
              <MailTriage data={(v as unknown as { data?: Record<string, unknown> }).data ?? {}} w={w} />
              <ul className="belege" aria-label={`${w.missingPos} · ${w.presentPos}`}>
                <li className="pos">{w.missingPos} <span className="c">{gaps.length}</span>{gaps.length === 0 && <span className="satz">{w.missingNone}</span>}</li>
                {gaps.map((g) => g.slot ? (
                  <DropLine key={g.key} slot={g.slot} mine={g.mine} who={g.who} w={w} busy={busy} onFile={(f) => upload.mutate({ slot: g.slot!.file, file: f })}
                            sample={samples.includes(g.slot.file)} onSample={() => sampleIn.mutate(g.slot!.file)} />
                ) : (
                  <li key={g.key} className="fehlt"><span className="zust"><Wait /><span className="sr">{w.missingPos}</span></span>
                    <span className="was"><b>{g.word}</b>{g.who && <span className="wer">{g.who}</span>}</span></li>
                ))}
                <li className="pos">{w.presentPos} <span className="c">{groups.length}</span>{groups.length === 0 && <span className="satz">{w.presentNone}</span>}</li>
                {groups.map(({ head: s, members }) => {
                  const newest = s.versions[s.versions.length - 1];
                  const e = entryFor(newest.name);
                  const who = s.by_word || e?.author || "";
                  const lastM = members[members.length - 1];
                  return (
                    <li key={s.file} className={`ok${members.some((m) => landed === m.file) ? " landed" : ""}`}>
                      <span className="zust"><Check /><span className="sr">{w.presentPos}</span></span>
                      <span className="was">
                        {members.length > 1 ? (
                          <span className="thumbs">{members.map((m) => { const n = m.versions[m.versions.length - 1]; return m.shape.startsWith("image")
                            ? <button key={m.file} type="button" className="thumbbtn" data-file={m.file} aria-label={`${m.word} · ${w.open}`} onClick={() => setReading(n.name)}><img className="thumb" src={BASE + n.url} alt="" /></button>
                            : <button key={m.file} type="button" className="link" data-file={m.file} onClick={() => setReading(n.name)}>{m.word}</button>; })}</span>
                        ) : s.shape.startsWith("image") && <img className="thumb" src={BASE + newest.url} alt="" />}
                        <b>{members.length > 1 ? `${s.word} … ${lastM.word}` : s.word}</b>
                        <span className="meta"><span className="v">{members.length > 1 ? `${newest.name} … ${lastM.versions[lastM.versions.length - 1].name}` : newest.name}</span> · {w.version(Math.max(1, newest.version))}{s.versions.length > 1 ? ` · ${w.earlierVersions(s.versions.length - 1)}` : ""}</span>
                        <span className={`wer${isAgent(who) || s.by === "claude" ? " ki" : who ? "" : " ne"}`}>{who || w.originUnknown}</span>
                        {e?.date && <span className="meta">{dateShort(e.date, lang)}</span>}
                        <button type="button" className="link open" data-file={members.length > 1 ? undefined : s.file} onClick={() => setReading(newest.name)}>{w.open}</button>
                      </span>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>

        <div className="tun foot" data-help="cf.your-move">
          <p className="pos">{w.yourTurn}</p>
          {primaryTurn && (
            <div className="zug">
              {needsAmount && <label className="money"><span>{w.amount}</span><input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="€" inputMode="decimal" /></label>}
              {needsDate && <label className="date"><span>{w.date}</span><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>}
              {(needsUrl || needsNote) && <label className="ask"><span className="sr">{needsUrl ? w.link : primaryTurn.label}</span><input value={note} onChange={(e) => setNote(e.target.value)} placeholder={needsUrl ? `${w.link} …` : `${primaryTurn.label} …`} /></label>}
              <button type="button" className={`btn${primaryTurn.seal ? " seal" : ""}`} disabled={!canPress} data-action={primaryTurn.action} onClick={() => press(primaryTurn)}>{primaryTurn.label} <Arrow /></button>
            </div>
          )}
          {deliverTurn && <p className="ziel du"><You /><span>{w.fillFrames(deliverTurn.blocked_by.map(missingWord).join(", "))}</span></p>}
          {locked.map((t) => <p key={t.action} className={`ziel${t.seal ? " seal" : ""}`} data-lock={t.action}><Lock /><span>{bold(lockText(t))}</span></p>)}
          {secondary.length > 0 && <span className="chips">{secondary.map(chip)}</span>}
          {!mine && <p className="keiner" role="status">{noTurnText}</p>}
        </div>
      </article>

      <section className="dahinter" aria-label={w.behind}>
        <h2>{w.behind}</h2>
        {(talkOpen || (talkSlot && outcomeReady) || (!talkSlot && draftHere) || onsiteHere) && (
          <ul className="zeilen">
            {talkOpen && (
              <li><button type="button" className={`row${v.my_turns.some((t) => t.action.startsWith("interview")) ? " mine" : ""}`} data-talk="1" data-help="cf.talk-tile" onClick={() => go(`/case/${encodeURIComponent(id)}/gespraech`)}>
                <span className="t">{w.talkOpen}</span><span className="s">{w.talkOpenHint}</span><span className="act"><Chev />{w.open}</span></button></li>
            )}
            {((talkSlot && outcomeReady) || (!talkSlot && draftHere)) && (
              <li><button type="button" className={`row${v.my_turns.some((t) => t.action === "approve_canon") ? " mine" : ""}`} data-outcome="1" data-help="cf.outcome-tile" onClick={() => go(`/case/${encodeURIComponent(id)}/ergebnis`)}>
                <span className="t">{w.outcomeOpen}</span><span className="s">{w.outcomeOpenHint}</span><span className="act"><Chev />{w.open}</span></button></li>
            )}
            {onsiteHere && (
              <li><button type="button" className={`row${mine ? " mine" : ""}`} data-onsite="1" onClick={() => go(`/case/${encodeURIComponent(id)}/vorort`)}>
                <span className="t">{w.onsite}</span><span className="s">{w.onsiteHint}</span><span className="act"><Chev />{w.open}</span></button></li>
            )}
          </ul>
        )}
        <details className="d thread" data-help="cf.thread" open={threadOpen} onToggle={(e) => setThreadOpen((e.currentTarget as HTMLDetailsElement).open)}>
          <summary><Chev />{w.conversation} <span className="c">{w.entriesCount(v.entries.length)}</span>{last && <span className="hint">{w.lastBy(last.author, dateShort(last.date, lang))}</span>}</summary>
          <div className="body">
            <div className="verlauf">
              <Thread entries={v.entries} meName={me.name ?? ""} agentName={v.agent} lang={lang} w={w} busy={busy} stageWord={stageWord}
                      onAnswer={(e, text) => entry.mutate({ kind: "answer", step_id: stepId("answer"), resolves: e.id, text })}
                      onDone={(e) => entry.mutate({ kind: "done", step_id: stepId("done"), resolves: e.id })} />
              {v.entries.length === 0 && <p className="prosa-klein">{w.noEntry}</p>}
            </div>
            <form className="ask" onSubmit={(e) => { e.preventDefault(); if (!ask.trim()) return; if (pending) { step.mutate({ action: pending.action, payload: { note: ask.trim(), text: ask.trim() } }); setPending(null); setAsk(""); } else run.mutate(ask.trim()); }}>
              <span className="sr">{pending ? pending.label : w.notePlaceholder(v.agent)}</span>
              {pending && <button type="button" className="chip on small" onClick={() => setPending(null)}>{pending.label} ×</button>}
              <input ref={askRef} value={ask} onChange={(e) => setAsk(e.target.value)} placeholder={pending ? `${pending.label} …` : w.notePlaceholder(v.agent)} />
              <button type="submit" className="send" disabled={busy || !ask.trim()} aria-label={pending ? pending.label : w.askClaude(v.agent)}><Send /></button>
            </form>
          </div>
        </details>
        <details className="d" open={filesOpen} onToggle={(e) => setFilesOpen((e.currentTarget as HTMLDetailsElement).open)}>
          <summary><Chev />{w.allFiles} <span className="c">{fileCount}</span>{missingCount > 0 && <span className="hint">{missingCount} {w.missingCount(missingCount)}</span>}</summary>
          <div className="body"><ul className="dateien">
            {v.slots.map((s) => s.present ? [...s.versions].reverse().map((ver, i) => {
              const e = entryFor(ver.name);
              const who = (i === 0 && s.by_word) || e?.author || "";
              return (
                <li key={ver.name}><span className="n">{ver.name}</span><span className="l">{s.word}, {w.version(Math.max(1, ver.version))}</span>
                  <span className="w">{who ? `${who}${e?.date ? ` · ${dateShort(e.date, lang)}` : ""}` : w.originUnknown}</span>
                  {isDoc(s) && <button type="button" className="link open" onClick={() => setReading(ver.name)}>{w.open}</button>}</li>
              );
            }) : (
              <li key={s.file} className="miss"><span className="n">{s.file}</span><span className="l">{s.word}</span><span className="w">{w.missingPos}{s.by_word ? ` · ${s.by_word}` : ""}</span></li>
            ))}
          </ul></div>
        </details>
        <div className="d row">
          <MetaSheet meta={(v.meta ?? {}) as Record<string, unknown>} words={(config.words ?? {}) as Record<string, unknown>} lang={lang} title={w.metaTitle} table={w.metaTable} />
        </div>
      </section>
      {toast && <div className={`toast${toast.sealed ? " sealed" : ""}`} role="status">{toast.sealed && <span className="stampmark">{w.sealed}</span>}<span>{toast.text}</span>{toast.undo && <button type="button" onClick={toast.undo}>{w.undo}</button>}<button type="button" onClick={() => go("/")}>{w.yourMove} →</button></div>}
    </main>
  );
}
