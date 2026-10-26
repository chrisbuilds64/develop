// The outcome of a conversation: the operation on one page, and the canon draft that a person decides line by line.
// Every claim carries the words it rests on; what the AI proposes holds only once somebody has accepted it (ADR-021).
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, BASE, stepId, talk, type ConfigView, type Line, type Outcome, type Source } from "../api";
import { Back, Check, Cross, Pen } from "../components/Icons";
import { dateWords, type words } from "../words";
import { thud } from "../moments";

type W = ReturnType<typeof words>;

export function OutcomeScreen({ id, config, go, w }: { id: string; config: ConfigView; go: (p: string) => void; w: W }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["outcome", id], queryFn: () => talk.outcome(id), retry: false, refetchInterval: (query) => (query.state.data?.running ? 3000 : 30_000) });
  const c = useQuery({ queryKey: ["case", id], queryFn: () => api.case(id), retry: false });
  const agent = config.people.find((p) => p.kind === "agent")?.name ?? "KI";
  const [error, setError] = useState<string | null>(null);
  const [sealing, setSealing] = useState<{ lines: string[]; rules: number; voices: number; quotes: number } | null>(null);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["outcome", id] }); qc.invalidateQueries({ queryKey: ["case", id] }); qc.invalidateQueries({ queryKey: ["groups"] }); };
  const decide = useMutation({ mutationFn: (p: { line: string; verdict: string; text?: string }) => talk.decide(id, p.line, p.verdict, p.text ?? "", stepId("dec")),
                               onSuccess: () => { setError(null); refresh(); }, onError: (e) => setError(e instanceof ApiError ? e.message : String(e)) });
  const approve = useMutation({ mutationFn: () => api.step(id, "approve_canon", stepId("approve")), onSuccess: () => {
                                  setError(null);
                                  // the numbers on the seal are the case's own: lines kept, people whose words they rest on, quotes behind them
                                  const kept = (q.data?.lines ?? []).filter((l) => l.decision.verdict === "accept" || l.decision.verdict === "edit");
                                  const sources = kept.flatMap((l) => l.sources ?? []);
                                  setSealing({ lines: kept.slice(0, 6).map((l) => (l.decision.verdict === "edit" ? l.decision.text : l.text) ?? ""), rules: kept.length,
                                               voices: new Set(sources.map((s) => s.person)).size, quotes: sources.length });
                                  setTimeout(thud, 420);
                                  refresh();
                                },
                                onError: (e) => setError(e instanceof ApiError ? e.message : String(e)) });

  if (q.isLoading) return <main className="main talk-main"><p className="empty">…</p></main>;
  if (!q.data) return <main className="main talk-main"><p className="empty">{q.error instanceof ApiError ? q.error.message : w.unreachable}</p></main>;
  const v: Outcome = q.data;
  const f = v.findings;
  const who = (pid: string) => v.people[pid] ?? pid;
  // "weg.3" → "Der Weg, Frage 3": the person's words, never the pack's codes
  const where = (qid: string) => { const [bid, n] = qid.split("."); const b = v.blocks.find((x) => x.id === bid); return b ? `${b.title.replace(/^Block \d+ — /, "")}, ${w.questionN(n)}` : qid; };
  const approveTurn = c.data?.my_turns.find((t) => t.action === "approve_canon");
  const hasFindings = !!(f.path?.length || f.roles?.length || f.tensions?.length || f.divergences?.length || f.summary);
  const titleOf = (bid: string) => { const b = v.blocks.find((x) => x.id === bid); return b ? (b.canon || b.title) : bid; };
  const groups = [...v.blocks.map((b) => b.id), ...[...new Set(v.lines.map((l) => l.block))].filter((b) => !v.blocks.some((x) => x.id === b))]
    .map((bid) => ({ bid, lines: v.lines.filter((l) => l.block === bid) })).filter((g) => g.lines.length);

  return (
    <main className="main talk-main">
      <header className="talk-head">
        <button type="button" className="btn link small talk-back" onClick={() => go(`/case/${encodeURIComponent(id)}`)}><Back /> {w.backToCase}</button>
        <div className="talk-title"><b>{v.title}</b><span>{v.stage_word}</span></div>
      </header>

      {v.canon && !approveTurn && (
        <div className="sealed-band" data-help="cf.outcome-sealed"><b>{w.sealed}</b><span>{w.sealedBand(dateWords(c.data?.entries.filter((e) => e.status === "approved").slice(-1)[0]?.date ?? "", config.lang) || "")}</span>
          {v.canon_url && <a href={BASE + v.canon_url} target="_blank" rel="noreferrer">{w.openCanon}</a>}</div>
      )}
      <div className="outcome-scroll">
        {v.running && <p className="talk-reading"><i aria-hidden="true" />{w.evaluating(agent)}</p>}
        {!hasFindings && !v.lines.length && !v.running && <p className="talk-lead">{w.noOutcome}</p>}

        {hasFindings && (
          <section className="mirror" aria-label={w.findings} data-help="cf.outcome-findings">
            <h1>{w.mirror}</h1>
            {f.summary && <p className="mirror-lead">{f.summary}</p>}

            {!!f.path?.length && (
              <div className="mirror-block">
                <h2>{w.pathTitle}</h2>
                <ol className="way">
                  {f.path.map((s, i) => (
                    <li key={i} className={s.missing_gate ? "missing" : s.gate ? "gated" : ""}>
                      <span className="way-step">{s.step}</span>
                      {s.gate ? <span className="way-gate"><b>{w.gate}</b> {s.gate}</span> : s.missing_gate ? <span className="way-gate open"><b>{w.noGate}</b>{s.note ? ` · ${s.note}` : ""}</span> : null}
                      {s.source && <Quote s={s.source} who={who} where={where} w={w} />}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {!!f.roles?.length && (
              <div className="mirror-block">
                <h2>{w.rolesTitle}</h2>
                <ul className="roles">
                  {f.roles.map((r, i) => (
                    <li key={i}>
                      <div><b>{r.name}</b> {r.decides}</div>
                      {r.single_point && <span className="flag">{w.singlePoint}</span>}
                      {r.source && <Quote s={r.source} who={who} where={where} w={w} />}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {!!f.tensions?.length && (
              <div className="mirror-block">
                <h2>{w.saidDone}</h2>
                {f.tensions.map((t, i) => (
                  <div key={i} className="said-done">
                    <b>{t.title}</b>
                    <div className="pair">
                      <div><small>{w.said}</small><Quote s={t.said} who={who} where={where} w={w} /></div>
                      <div><small>{w.done2}</small><Quote s={t.done} who={who} where={where} w={w} /></div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!!f.divergences?.length && (
              <div className="mirror-block">
                <h2>{w.divergences}</h2>
                {f.divergences.map((d, i) => (
                  <div key={i} className="divergence">
                    <b>{d.topic}</b>
                    <div className="voices">{d.views.map((s, j) => <Quote key={j} s={s} who={who} where={where} w={w} />)}</div>
                  </div>
                ))}
              </div>
            )}

            {f.limits && <div className="mirror-block limits"><h2>{w.limits}</h2><p>{f.limits}</p></div>}
          </section>
        )}

        {!!v.lines.length && (
          <section className="draft" aria-label={w.draftTitle} data-help="cf.outcome-draft">
            <h1>{w.draftTitle}</h1>
            <p className="talk-why">{w.draftHint}</p>
            {!v.can_decide && <p className="talk-hint">{w.onlyDecider}</p>}
            {groups.map((g) => (
              <div key={g.bid} className="draft-group">
                <h2>{titleOf(g.bid)}</h2>
                {g.lines.map((l) => <LineRow key={l.id} l={l} can={v.can_decide && !!approveTurn} busy={decide.isPending} who={who} where={where} w={w}
                                               onDecide={(verdict, text) => decide.mutate({ line: l.id, verdict, text })} />)}
              </div>
            ))}
          </section>
        )}
        {error && <p className="talk-error" role="alert">{error}</p>}
      </div>

      {!!v.lines.length && (approveTurn || v.canon) && (
        <footer className="foot" data-help="cf.outcome-approve">
          <span className="says">{v.canon && !approveTurn ? w.canonReady : v.open_lines ? w.draftHint : w.allDecided}</span>
          {approveTurn && (v.open_lines > 0
            ? <span className="gate-count" aria-live="polite"><b>{v.open_lines}</b> {w.openLinesShort(v.open_lines)} {w.stillOpen}</span>
            : <button type="button" className="btn arrive" disabled={approve.isPending} onClick={() => approve.mutate()}>{w.approve} →</button>)}
        </footer>
      )}
      {sealing && (
        <div className="seal-stage" role="dialog" aria-modal="true" aria-label={w.sealed} onClick={() => setSealing(null)}>
          <div className="seal-sheet" onClick={(e) => e.stopPropagation()}>
            <span className="seal-stamp" style={{ animationDelay: "380ms" }} aria-hidden="true"><span><b>v0.1</b><small>{w.sealed}</small></span></span>
            <h2>{w.sealTitle(v.title)}</h2>
            <ul className="seal-lines">{sealing.lines.map((t, i) => <li key={i} style={{ animationDelay: `${60 + i * 50}ms` }}>{t}</li>)}</ul>
            <p className="seal-sum" style={{ animationDelay: "900ms" }}>{w.sealSum(sealing.rules, sealing.voices, sealing.quotes).map((x, i) => <span key={i}>{i ? ", " : ""}<em>{x}</em></span>)}. {w.sealNow}</p>
            <div className="seal-acts" style={{ animationDelay: "1150ms" }}>
              <button type="button" className="btn link" onClick={() => setSealing(null)}>{w.close}</button>
              {v.canon_url && <a className="btn seal" href={BASE + v.canon_url} target="_blank" rel="noreferrer">{w.openCanon}</a>}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function Quote({ s, who, where, w }: { s: Source; who: (p: string) => string; where: (q: string) => string; w: W }) {
  return (
    <blockquote className="quote">
      <p>„{s.quote}“</p>
      <cite>{w.sourceOf(who(s.person), where(s.question))}</cite>
    </blockquote>
  );
}

function LineRow({ l, can, busy, who, where, w, onDecide }: { l: Line; can: boolean; busy: boolean; who: (p: string) => string; where: (q: string) => string; w: W; onDecide: (verdict: string, text?: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(l.decision.text ?? l.text);
  const [open, setOpen] = useState(false);
  const verdict = l.decision.verdict;
  const shown = verdict === "edit" ? l.decision.text : l.text;
  return (
    <div className={`kline${verdict ? ` ${verdict}` : ""}`}>
      <div className="kline-main">
        <span className="mono kline-id">{l.id}</span>
        {editing ? (
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} autoFocus />
        ) : (
          <p className="kline-text">{shown}{verdict === "edit" && <del>{l.text}</del>}</p>
        )}
        <span className="kline-marker">{l.marker ? w.markerWord(l.marker) : ""}</span>
      </div>
      <div className="kline-foot">
        {!!l.sources?.length && <button type="button" className="btn link small" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? "−" : "+"} {l.sources.length === 1 ? who(l.sources[0].person) : w.sources(l.sources.length)}</button>}
        <span className="kline-state">{verdict === "accept" ? w.accepted : verdict === "edit" ? w.edited : verdict === "reject" ? w.rejected : ""}</span>
        {can && (editing ? (
          <>
            <button type="button" className="btn link small" onClick={() => { setEditing(false); setText(l.decision.text ?? l.text); }}>{w.cancel}</button>
            <button type="button" className="btn small" disabled={busy || !text.trim()} onClick={() => { onDecide("edit", text); setEditing(false); }}>{w.takeOver}</button>
          </>
        ) : verdict ? (
          <button type="button" className="btn link small" disabled={busy} onClick={() => onDecide("undo")}>{w.undoDecision}</button>
        ) : (
          <div className="kline-acts">
            <button type="button" className="chip act accept" disabled={busy} onClick={() => onDecide("accept")}><Check /> {w.accept}</button>
            <button type="button" className="chip act" disabled={busy} onClick={() => setEditing(true)}><Pen /> {w.edit}</button>
            <button type="button" className="chip act reject" disabled={busy} onClick={() => onDecide("reject")}><Cross /> {w.reject}</button>
          </div>
        ))}
      </div>
      {open && <div className="kline-sources">{l.sources?.map((s, i) => <Quote key={i} s={s} who={who} where={where} w={w} />)}</div>}
    </div>
  );
}
