// A conversation, not a form: one question at a time, the chapters as a map, the canon growing beside it.
// No answer is finished without the person's own word on how it stands — nothing is preselected (ADR-021).
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, stepId, talk, type Answer, type Block, type ConfigView, type Interview as Talk } from "../api";
import { Back, Check } from "../components/Icons";
import { Explain } from "../components/Explain";
import { chime } from "../moments";
import type { words } from "../words";

type W = ReturnType<typeof words>;
const MARKERS = ["is", "should", "open"] as const;

function cuesIn(text: string, triggers: Talk["pack"]["triggers"]) {
  const t = ` ${text.toLowerCase()} `;
  return triggers.filter((tr) => tr.match.some((m) => t.includes(m.toLowerCase())));
}

export function InterviewScreen({ id, config, go, w }: { id: string; config: ConfigView; go: (p: string) => void; w: W }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["talk", id], queryFn: () => talk.get(id), retry: false, refetchInterval: (query) => (query.state.data?.helper_running ? 3000 : 20_000) });
  const agent = config.people.find((p) => p.kind === "agent")?.name ?? "KI";
  const markerWord = (m: string) => ((config.words as { markers?: Record<string, string> }).markers?.[m]) ?? m;
  const storeKey = `cf.talk.${id}.${q.data?.me ?? ""}`;
  const [current, setCurrent] = useState<string | null>(() => { try { return localStorage.getItem(storeKey); } catch { return null; } });
  const [drafts, setDrafts] = useState<Record<string, { text: string; marker: string }>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fresh, setFresh] = useState<string | null>(null);          // the compartment that just received an answer
  const [anchorText, setAnchorText] = useState("");
  const [fu, setFu] = useState<Record<string, string>>({});
  const [showFinish, setShowFinish] = useState(false);
  const [whyOpen, setWhyOpen] = useState(false);
  const [gotChapter, setGotChapter] = useState(false);              // the chapter's reward picked up
  const [finishedNow, setFinishedNow] = useState(false);           // "I am done" just pressed: the quotes go into the canon
  const [triedNext, setTriedNext] = useState(false);
  const [moment, setMoment] = useState<{ done: Block; next: Block; target: string } | null>(null);   // a chapter just clicked shut
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const sent = useRef<Set<string>>(new Set());

  const v = q.data;
  const order = useMemo(() => (v ? v.pack.blocks.flatMap((b) => b.questions.map((qq) => ({ block: b, q: qq }))) : []), [v]);
  const total = order.length;
  const firstOpen = order.find((x) => !v?.answers[x.q.id])?.q.id ?? order[0]?.q.id ?? null;
  const qid = current && order.some((x) => x.q.id === current) ? current : firstOpen;
  const at = order.findIndex((x) => x.q.id === qid);
  const here = at >= 0 ? order[at] : undefined;
  useEffect(() => { if (qid) { try { localStorage.setItem(storeKey, qid); } catch { /* private window */ } } }, [qid, storeKey]);
  useEffect(() => { if (!fresh) return; const t = setTimeout(() => setFresh(null), 1400); return () => clearTimeout(t); }, [fresh]);
  useEffect(() => { areaRef.current?.focus({ preventScroll: true }); setWhyOpen(false); setTriedNext(false); }, [qid]);

  if (q.isLoading) return <main className="main talk-main"><p className="empty">…</p></main>;
  if (!v) return <main className="main talk-main"><p className="empty">{q.error instanceof ApiError ? q.error.message : w.unreachable}</p></main>;

  const saved: Answer | undefined = qid ? v.answers[qid] : undefined;
  const draft = qid ? drafts[qid] ?? { text: saved?.text ?? "", marker: saved?.marker ?? "" } : { text: "", marker: "" };
  const dirty = !!qid && (draft.text.trim() !== (saved?.text ?? "") || draft.marker !== (saved?.marker ?? ""));
  const needsMarker = draft.text.trim() !== "" && !MARKERS.includes(draft.marker as typeof MARKERS[number]);
  const answeredCount = Object.keys(v.answers).length;
  const refresh = () => qc.invalidateQueries({ queryKey: ["talk", id] });
  const setDraft = (patch: Partial<{ text: string; marker: string }>) => qid && setDrafts({ ...drafts, [qid]: { ...draft, ...patch } });

  const blockAnswered = (b: Block) => b.questions.filter((qq) => v.answers[qq.id]).length;
  const chapterDone = async (b: Block) => {
    const n = blockAnswered(b) + (dirty && here?.block.id === b.id && !saved ? 1 : 0);
    const key = `ch-${b.id}-${n}`;
    if (n === 0 || sent.current.has(key)) return;
    sent.current.add(key);
    try { await talk.chapter(id, b.id, `${key}-${v.me}`.slice(0, 80)); refresh(); } catch { /* follow-ups are a bonus, never a blocker */ }
  };

  // the answer flies from the field into its compartment — the one authored moment of the conversation
  const fly = (text: string, blockId: string) => {
    const from = areaRef.current?.getBoundingClientRect();
    const to = document.querySelector<HTMLElement>(`.fach[data-block="${blockId}"]`)?.getBoundingClientRect();
    if (!from || !to || window.matchMedia("(prefers-reduced-motion: reduce)").matches || to.width === 0) return;
    const el = document.createElement("div");
    el.className = "flight";
    el.textContent = `„${text.length > 90 ? text.slice(0, 88) + "…" : text}“`;
    el.style.left = `${from.left + 16}px`; el.style.top = `${from.top + 12}px`;
    document.body.appendChild(el);
    const dx = to.left + 12 - (from.left + 16), dy = to.top + 30 - (from.top + 12);
    el.animate([{ transform: "translate(0,0) scale(1)", opacity: 1 }, { transform: `translate(${dx * 0.6}px, ${dy * 0.6 - 40}px) scale(.85)`, opacity: 1, offset: 0.6 },
                { transform: `translate(${dx}px, ${dy}px) scale(.6)`, opacity: 0 }], { duration: 650, easing: "cubic-bezier(.2,.8,.2,1)" }).onfinish = () => el.remove();
  };

  const save = async (): Promise<boolean> => {
    if (!qid || !dirty) return true;
    if (needsMarker) { setTriedNext(true); return false; }
    setSaving(true); setError(null);
    try {
      await talk.answer(id, qid, draft.text, draft.marker, stepId("ans"));
      if (draft.text.trim() && here) { fly(draft.text.trim(), here.block.id); setTimeout(() => setFresh(here.block.id), 520); }
      const next = { ...drafts }; delete next[qid]; setDrafts(next);
      await refresh();
      return true;
    } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); return false; }
    finally { setSaving(false); }
  };

  const goTo = async (target: string | null, opts: { save?: boolean } = { save: true }) => {
    const landed = !!qid && dirty && !saved && draft.text.trim() !== "";
    if (opts.save && !(await save())) return;
    const from = here?.block;
    const to = order.find((x) => x.q.id === target)?.block;
    if (from && to && from.id !== to.id) {
      void chapterDone(from);
      const full = blockAnswered(from) + (landed ? 1 : 0) >= from.questions.length;
      if (full && landed && target) { setGotChapter(false); setMoment({ done: from, next: to, target }); setCurrent(target); return; }
    }
    setMoment(null);
    setShowFinish(false);
    setCurrent(target);
  };
  const next = async () => {
    if (at === total - 1) { if (await save()) { if (here) void chapterDone(here.block); setShowFinish(true); } return; }
    await goTo(order[at + 1].q.id);
  };

  // ---------------------------------------------------------------- not asked, or closed: how far everyone is
  if (!v.can_answer) {
    return (
      <main className="main talk-main">
        <TalkHead v={v} go={go} w={w} />
        <section className="talk-solo">
          <p className="talk-lead">{v.respondents.some((r) => r.me) ? w.closedTalk : w.notAsked}</p>
          <People v={v} w={w} />
        </section>
      </main>
    );
  }

  // ---------------------------------------------------------------- the anchor: one real piece, before anything else
  if (!v.anchor && answeredCount === 0) {
    return (
      <main className="main talk-main">
        <TalkHead v={v} go={go} w={w} />
        <section className="talk-anchor" data-help="cf.talk-anchor">
          <h1>{v.pack.anchor.ask ?? w.anchorPlaceholder}</h1>
          {v.pack.anchor.why && <p className="talk-why">{v.pack.anchor.why}</p>}
          <p className="talk-scope">{w.scope(total, v.pack.blocks.length)}</p>
          <div><Explain where="interview" config={config} /></div>
          <form onSubmit={async (e) => { e.preventDefault(); if (!anchorText.trim()) return; try { await talk.anchor(id, anchorText); refresh(); } catch (err) { setError(err instanceof ApiError ? err.message : String(err)); } }}>
            <input autoFocus value={anchorText} onChange={(e) => setAnchorText(e.target.value)} placeholder={v.pack.anchor.placeholder ?? w.anchorPlaceholder} maxLength={200} />
            <button type="submit" className="btn" disabled={!anchorText.trim()}>{w.anchorGo} →</button>
          </form>
          {error && <p className="talk-error" role="alert">{error}</p>}
        </section>
      </main>
    );
  }

  const cues = cuesIn(draft.text, v.pack.triggers);
  const helperHere = (v.helper.followups ?? []).filter((f) => f.question === qid);
  const tensions = (v.helper.tensions ?? []).filter((t) => t.questions.every((x) => v.answers[x]));

  return (
    <main className="main talk-main">
      <TalkHead v={v} go={go} w={w} />
      <div className="talk">
        {/* the map: seven chapters, a dot per question */}
        <nav className="talk-map" aria-label={w.chapters} data-help="cf.talk-map">
          {v.pack.blocks.map((b) => {
            const n = blockAnswered(b);
            const on = here?.block.id === b.id;
            return (
              <div key={b.id} className={`chapter${on ? " on" : ""}${n === b.questions.length ? " full" : ""}`}>
                <button type="button" className="chapter-head" onClick={() => goTo(b.questions.find((qq) => !v.answers[qq.id])?.id ?? b.questions[0].id)}>
                  <span className="chapter-title">{b.title.replace(/^Block \d+ — /, "")}</span>
                  <span className="chapter-n">{n}/{b.questions.length}</span>
                </button>
                <div className="dots">
                  {b.questions.map((qq) => (
                    <button key={qq.id} type="button" aria-label={qq.text} title={qq.text} onClick={() => goTo(qq.id)}
                            className={`qdot${v.answers[qq.id] ? ` filled ${v.answers[qq.id].marker}` : ""}${qq.id === qid ? " here" : ""}${(v.helper.followups ?? []).some((f) => f.question === qq.id && !v.followup_answers[f.id]) ? " asks" : ""}`} />
                  ))}
                </div>
              </div>
            );
          })}
          <div className="talk-map-foot">
            <People v={v} w={w} compact />
          </div>
        </nav>

        {/* the question */}
        <section className="talk-q" aria-live="polite">
          {moment ? (
            <div className="chapter-done" data-help="cf.talk-chapter">
              <span className={`mark${gotChapter ? " got" : ""}`} aria-hidden="true"><Check /></span>
              <h1>{w.chapterDone(moment.done.title.replace(/^Block \d+ — /, ""))}</h1>
              <p className="talk-why">{w.chapterFilled(moment.done.canon || moment.done.title, moment.done.questions.filter((qq) => v.answers[qq.id]).length)}</p>
              {(() => { const last = [...moment.done.questions].reverse().find((qq) => v.answers[qq.id]); return last ? <blockquote>„{v.answers[last.id].text}“</blockquote> : null; })()}
              <div className="talk-actions">
                <button type="button" className="btn link" onClick={() => go(`/case/${encodeURIComponent(id)}`)}>{w.pauseHere}</button>
                <span className="talk-state" />
                {gotChapter
                  ? <button type="button" className="btn arrive" autoFocus onClick={() => setMoment(null)}>{w.nextChapter(moment.next.title.replace(/^Block \d+ — /, ""))} →</button>
                  : <button type="button" className="btn collect-chapter" autoFocus onClick={() => { chime(); setGotChapter(true); setFresh(moment.done.id); }}>{w.collect}</button>}
              </div>
            </div>
          ) : showFinish || !here ? (
            <div className="talk-finish" data-help="cf.talk-finish">
              {v.done ? (<>
                {finishedNow && (
                  <div className="quote-fall" aria-hidden="true">
                    {Object.values(v.answers).slice(-8).map((a, i) => <span key={i} className="slip" style={{ animationDelay: `${i * 0.12}s`, left: `${8 + (i % 4) * 22}%` }}>„{a.text.length > 48 ? a.text.slice(0, 46) + "…" : a.text}“</span>)}
                    <span className="into">{w.canonGrows}</span>
                  </div>
                )}
                <h1>{finishedNow ? w.carried(answeredCount) : w.finished}</h1><p className="talk-why">{w.finishedHint}</p></>) : (<>
                <h1>{w.finishTitle}</h1>
                <p className="talk-why">{w.finishText(answeredCount, total)}</p>
                <div className="talk-actions">
                  <button type="button" className="btn ghost" onClick={() => goTo(firstOpen, { save: false })}>{w.back}</button>
                  <button type="button" className="btn" disabled={answeredCount === 0} onClick={async () => { try { await talk.finish(id, stepId("fin")); setFinishedNow(true); chime(0.9); await refresh(); qc.invalidateQueries({ queryKey: ["case", id] }); qc.invalidateQueries({ queryKey: ["groups"] }); } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); } }}>{w.finishBtn}</button>
                </div>
              </>)}
              {error && <p className="talk-error" role="alert">{error}</p>}
            </div>
          ) : (
            <>
              <p className="talk-where"><span>{here.block.title.replace(/^Block \d+ — /, "")}</span><span className="mono">{w.questionOf(at + 1, total)}</span></p>
              {(() => {
                // the first sentence is the question; what follows only explains it — set smaller, read second
                const m = /^(.+?[?.!])\s+(.+)$/s.exec(here.q.text);
                return <>
                  <h1 className="talk-question">{m ? m[1] : here.q.text}</h1>
                  {m && <p className="talk-detail">{m[2]}</p>}
                </>;
              })()}
              <div className="talk-meta">
                {v.anchor && <span className="talk-anchor-chip">{w.atExample(v.anchor)}</span>}
                {here.q.why && <button type="button" className={`why-toggle${whyOpen ? " on" : ""}`} aria-expanded={whyOpen} onClick={() => setWhyOpen(!whyOpen)}>{w.whyAsk}</button>}
              </div>
              {whyOpen && here.q.why && <p className="talk-why why-open">{here.q.why}</p>}
              <textarea ref={areaRef} className="talk-area" value={draft.text} onChange={(e) => setDraft({ text: e.target.value })} placeholder={w.answerPlaceholder} rows={6}
                        onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); void next(); } }} data-help="cf.talk-answer" />
              {cues.length > 0 && (
                <div className="talk-nudge" role="note">
                  <b>{w.nudge}</b>
                  {cues.slice(0, 2).map((c) => <span key={c.cue}>{c.ask}</span>)}
                </div>
              )}
              {(draft.text.trim() !== "" || saved) && <fieldset className={`markers${needsMarker && triedNext ? " ask" : ""}`} data-help="cf.talk-markers">
                <legend>{w.howStands}</legend>
                <div className="marker-row" role="radiogroup" aria-label={w.howStands}>
                  {MARKERS.map((m) => (
                    <button key={m} type="button" role="radio" aria-checked={draft.marker === m} className={`marker ${m}${draft.marker === m ? " on" : ""}`}
                            onClick={() => setDraft({ marker: draft.marker === m ? "" : m })}>
                      <i aria-hidden="true">{draft.marker === m ? <Check /> : null}</i>{markerWord(m)}
                    </button>
                  ))}
                </div>
                {needsMarker && triedNext && <p className="talk-hint">{w.howStandsHint}</p>}
              </fieldset>}

              {helperHere.length > 0 && (
                <div className="talk-followups" data-help="cf.talk-followups">
                  <p className="talk-sub">{w.followups(agent)}</p>
                  {helperHere.map((f) => {
                    const val = fu[f.id] ?? v.followup_answers[f.id]?.text ?? "";
                    const changed = val.trim() !== (v.followup_answers[f.id]?.text ?? "");
                    return (
                      <div key={f.id} className="followup">
                        <p>{f.ask}</p>
                        <textarea rows={2} value={val} onChange={(e) => setFu({ ...fu, [f.id]: e.target.value })} placeholder={w.followupPlaceholder}
                                  onBlur={async () => { if (changed) { try { await talk.followup(id, f.id, val, stepId("fu")); refresh(); } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); } } }} />
                      </div>
                    );
                  })}
                </div>
              )}

              {error && <p className="talk-error" role="alert">{error}</p>}
              <div className="talk-actions">
                <button type="button" className="btn link" disabled={at <= 0 || saving} onClick={() => goTo(order[at - 1].q.id)}>{w.back}</button>
                <span className="talk-state">{saving ? w.saving : saved && !dirty ? w.saved : ""}</span>
                {!saved && !draft.text.trim() && <button type="button" className="btn link" onClick={() => goTo(at < total - 1 ? order[at + 1].q.id : null, { save: false })}>{w.later}</button>}
                <button type="button" className="btn" disabled={saving} onClick={next}>{w.goOn} →</button>
              </div>
            </>
          )}
        </section>

        {/* the canon, growing */}
        <aside className="talk-canon" aria-label={w.canonGrows} data-help="cf.talk-canon">
          <h2>{w.canonGrows}</h2>
          {answeredCount === 0 && <p className="talk-hint">{w.canonGrowsHint}</p>}
          {v.helper_running && <p className="talk-reading"><i aria-hidden="true" />{w.reading(agent)}</p>}
          {tensions.map((t) => (
            <div key={t.id} className="tension">
              <b>{w.tension}</b>
              <p>{t.text}</p>
              <small>{w.tensionHint}</small>
            </div>
          ))}
          {v.pack.blocks.map((b) => {
            const mine = b.questions.filter((qq) => v.answers[qq.id]);
            const drafts2 = (v.helper.drafts ?? []).filter((d) => d.block === b.id);
            const fill = mine.length / b.questions.length;
            return (
              <div key={b.id} data-block={b.id} className={`fach${mine.length === 0 ? " empty" : ""}${fresh === b.id ? " fresh" : ""}${here?.block.id === b.id ? " on" : ""}`}>
                <div className="fach-head"><b>{b.canon || b.title}</b><span className="fach-bar" aria-hidden="true"><i style={{ width: `${Math.round(fill * 100)}%` }} /></span></div>
                {mine.length === 0 && drafts2.length === 0 ? <span className="fach-empty">{w.emptyFach}</span> : null}
                {drafts2.map((d, i) => <p key={i} className="fach-draft"><span>{d.text}</span><small>{w.drafted(agent)}</small></p>)}
                {drafts2.length === 0 && mine.slice(-2).map((qq) => <p key={qq.id} className="fach-quote">„{v.answers[qq.id].text.length > 110 ? v.answers[qq.id].text.slice(0, 108) + "…" : v.answers[qq.id].text}“</p>)}
              </div>
            );
          })}
        </aside>
      </div>
    </main>
  );
}

function TalkHead({ v, go, w }: { v: Talk; go: (p: string) => void; w: W }) {
  return (
    <header className="talk-head">
      <button type="button" className="btn link small talk-back" onClick={() => go(`/case/${encodeURIComponent(v.case)}`)}><Back /> {w.backToCase}</button>
      <div className="talk-title"><b>{v.title}</b><span className="pack-tag">{v.pack.name}{v.pack.version ? ` · v${v.pack.version}` : ""}</span></div>
    </header>
  );
}

function People({ v, w, compact = false }: { v: Talk; w: W; compact?: boolean }) {
  return (
    <div className={`talk-people${compact ? " compact" : ""}`}>
      <p className="talk-sub">{w.people}</p>
      <ul>
        {v.respondents.filter((r) => v.sees_all || r.me).map((r) => (
          <li key={r.id} className={r.me ? "me" : ""}>
            <span className="avatar small">{r.name.slice(0, 2).toUpperCase()}</span>
            <span className="talk-person">{r.name}</span>
            <span className="talk-pbar" aria-hidden="true"><i style={{ width: `${r.total ? Math.round((r.answered / r.total) * 100) : 0}%` }} /></span>
            <span className="mono talk-pn">{r.done ? w.doneMark : w.answered(r.answered, r.total)}</span>
          </li>
        ))}
      </ul>
      {!v.sees_all && v.others > 0 && <p className="others">{w.othersDone(v.others_done, v.others)}</p>}
    </div>
  );
}
