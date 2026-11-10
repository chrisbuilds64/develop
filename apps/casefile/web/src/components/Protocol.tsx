// A gate protocol in the case (ADR-029, REQ-003 G2): the items of this gate, each answered by its type — yes/no, a number, a
// choice, evidence — with what was seen; nothing is preset. Before the first verdict an item can be struck with a reason.
// When nothing is open the person seals it; the gate reads the sealed protocol. An agent's observations sit under the item.
import { useState } from "react";
import { ApiError, gate, stepId } from "../api";
import type { words } from "../words";

type W = ReturnType<typeof words>;
// what the case view carries per protocol (views.protocols): typed here, the API types it as plain objects
export type ProtocolEntry = { template: string; title: string; opens: string[]; here: boolean; doc?: unknown; state?: unknown };
type P = ProtocolEntry;
type Item = { id: string; question?: Record<string, string>; type: string; must?: boolean; role?: string; agent?: boolean;
  options?: string[]; criterion?: { eq?: number; min?: number; max?: number; allowed?: string[] }; origin?: string;
  struck?: { by: string; reason: string } | null };
type Answer = { verdict: "pass" | "fail" | "na"; value?: unknown; note?: string; evidence?: string[]; by: string; at: string };
type Doc = { template: string; version?: number; items: Item[]; answers: Record<string, Answer>;
  observations?: Record<string, { by: string; note?: string; value?: unknown; suggests?: string; evidence?: string[] }[]>;
  sealed?: { by: string; at: string } | null };

const mark = { pass: "✓", fail: "✗", na: "–" } as const;

function criterionText(it: Item, w: W): string {
  const c = it.criterion ?? {};
  if (it.type === "number") return [c.eq !== undefined && `= ${c.eq}`, c.min !== undefined && `≥ ${c.min}`, c.max !== undefined && `≤ ${c.max}`].filter(Boolean).join(" · ");
  if (it.type === "choice") return (c.allowed ?? []).join(" / ");
  if (it.type === "evidence") return w.pcEvidence;
  return "";
}

function Row({ it, a, obs, lang, sealed, shaping, w, onAnswer, onStrike }: {
  it: Item; a?: Answer; obs?: Doc["observations"] extends infer O ? O extends Record<string, infer V> ? V : never : never; lang: string; sealed: boolean; shaping: boolean; w: W;
  onAnswer: (body: { value?: boolean | number | string | null; na?: boolean; note?: string; evidence?: string[] }) => Promise<void>;
  onStrike: (reason: string) => Promise<void>;
}) {
  const q = it.question?.[lang] ?? it.question?.en ?? it.id;
  const [val, setVal] = useState<string>("");
  const [note, setNote] = useState("");
  const [mode, setMode] = useState<"" | "na" | "strike">("");
  const open = !a && !it.struck && !sealed;
  const send = (value?: boolean | number | string | null) => onAnswer({ value, note: note.trim() || undefined }).then(() => { setVal(""); setNote(""); });
  return (
    <li className={`pc-item${it.struck ? " struck" : ""}${a ? ` ${a.verdict}` : ""}`}>
      <div className="pc-q">
        <span className="pc-mark" aria-hidden="true">{it.struck ? "~" : a ? mark[a.verdict] : "·"}</span>
        <span className="pc-text">{q}</span>
        <span className={`pc-badge ${it.must === false ? "should" : "must"}`}>{it.must === false ? w.pcShould : w.pcMust}</span>
        {criterionText(it, w) && <span className="pc-crit">{criterionText(it, w)}</span>}
      </div>
      {it.origin && <div className="pc-origin">{w.pcOrigin(it.origin)}{it.role ? ` · ${w.pcRole(it.role)}` : ""}{it.agent ? ` · ${w.pcAgent}` : ""}</div>}
      {it.struck && <div className="pc-said">{w.pcStruck(it.struck.reason, it.struck.by)}</div>}
      {a && <div className="pc-said">{a.verdict === "na" ? w.pcNa : ""}{a.value !== undefined && a.value !== null && a.verdict !== "na" ? String(a.value === true ? w.yes : a.value === false ? w.no : a.value) : ""}{a.note ? ` — ${a.note}` : ""} <span className="pc-by">· {a.by}</span></div>}
      {(obs ?? []).map((o, i) => <div key={i} className="pc-obs">{w.pcObserved(o.by)}: {o.note || String(o.value ?? "")}{o.suggests ? ` (${o.suggests})` : ""}</div>)}
      {open && (
        <div className="pc-answer">
          {mode === "" && it.type === "yesno" && (
            <><button type="button" className="ghost pc-yes" onClick={() => send(true)}>{w.yes}</button>
              <button type="button" className="ghost pc-no" onClick={() => send(false)} title={w.pcNoNeedsNote}>{w.no}</button></>
          )}
          {mode === "" && it.type === "number" && (
            <><input className="pc-in" type="number" inputMode="decimal" value={val} onChange={(e) => setVal(e.target.value)} aria-label={q} />
              <button type="button" className="ghost" disabled={val === ""} onClick={() => send(Number(val))}>{w.pcSet}</button></>
          )}
          {mode === "" && it.type === "choice" && (
            <select className="pc-in" value={val} onChange={(e) => { setVal(e.target.value); if (e.target.value) send(e.target.value); }} aria-label={q}>
              <option value="">{w.pick}</option>
              {(it.options ?? it.criterion?.allowed ?? []).map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          )}
          {mode === "" && it.type === "evidence" && (
            <><input className="pc-in wide" value={val} onChange={(e) => setVal(e.target.value)} placeholder={w.pcEvidencePh} aria-label={q} />
              <button type="button" className="ghost" disabled={!val.trim()} onClick={() => onAnswer({ value: val.trim(), evidence: [val.trim()], note: note.trim() || undefined }).then(() => setVal(""))}>{w.pcSet}</button></>
          )}
          {mode === "" && <input className="pc-in wide pc-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder={w.pcNotePh} aria-label={w.pcNotePh} />}
          {mode === "" && <button type="button" className="quiet" onClick={() => setMode("na")}>{w.pcNa}</button>}
          {mode === "" && shaping && <button type="button" className="quiet" onClick={() => setMode("strike")}>{w.pcStrike}</button>}
          {mode !== "" && (
            <><input className="pc-in wide" autoFocus value={note} onChange={(e) => setNote(e.target.value)} placeholder={mode === "strike" ? w.pcStrikeWhy : w.pcWhy} />
              <button type="button" className="ghost" disabled={!note.trim()} onClick={() => (mode === "strike" ? onStrike(note.trim()) : onAnswer({ na: true, note: note.trim() })).then(() => { setMode(""); setNote(""); })}>{mode === "strike" ? w.pcStrike : w.pcNa}</button>
              <button type="button" className="quiet" onClick={() => setMode("")}>{w.cancel}</button></>
          )}
        </div>
      )}
    </li>
  );
}

export function ProtocolCard({ p, caseId, lang, w, onChanged }: { p: P; caseId: string; lang: string; w: W; onChanged: () => void }) {
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const doc = p.doc as Doc | null | undefined;
  const run = async (f: () => Promise<unknown>) => {
    setBusy(true); setErr(null);
    try { await f(); onChanged(); } catch (e) { setErr(e instanceof ApiError ? e.message : String(e)); } finally { setBusy(false); }
  };
  if (!doc) {
    return (
      <section className="pc" data-help="cf.protocol">
        <header className="pc-head"><b>{p.title}</b>{p.opens.length > 0 && <span className="hint">{w.pcOpens(p.opens.join(", "))}</span>}</header>
        <p className="hint">{w.pcNotStarted}</p>
        <button type="button" className="primary" disabled={busy} onClick={() => run(() => gate.start(caseId, p.template))}>{w.pcStart}</button>
        {err && <p className="c-refused">{err}</p>}
      </section>
    );
  }
  const st = p.state as { open: string[]; failed_must: string[]; failed_should: string[]; passed: string[]; complete: boolean; gate_open: boolean } | null;
  const sealed = !!doc.sealed;
  const shaping = !sealed && Object.keys(doc.answers ?? {}).length === 0;
  const live = doc.items.filter((i) => !i.struck);
  const done = live.length - (st?.open.length ?? 0);
  return (
    <section className={`pc${sealed ? " sealed" : ""}`} data-help="cf.protocol">
      <header className="pc-head">
        <b>{p.title}{(doc.version ?? 1) > 1 ? ` · v${doc.version}` : ""}</b>
        <span className="pc-progress">{w.pcProgress(done, live.length)}</span>
        {sealed ? <span className={`pc-badge ${st?.gate_open ? "pass" : "fail"}`}>{st?.gate_open ? w.pcGateOpen : w.pcGateClosed}</span>
          : p.opens.length > 0 && <span className="hint">{w.pcOpens(p.opens.join(", "))}</span>}
      </header>
      {sealed && <p className="hint">{w.pcSealed(doc.sealed!.by, doc.sealed!.at.slice(0, 16).replace("T", " "))}</p>}
      <ol className="pc-list">
        {doc.items.map((it) => (
          <Row key={it.id} it={it} a={doc.answers?.[it.id]} obs={doc.observations?.[it.id]} lang={lang} sealed={sealed} shaping={shaping} w={w}
               onAnswer={(body) => run(() => gate.answer(caseId, p.template, { item: it.id, step_id: stepId("pc"), ...body }))}
               onStrike={(reason) => run(() => gate.strike(caseId, p.template, it.id, reason, stepId("pc")))} />
        ))}
      </ol>
      {!sealed && (
        <div className="pc-foot">
          {st && st.failed_must.length > 0 && <span className="pc-warn">{w.pcFailedMust(st.failed_must.length)}</span>}
          <button type="button" className="primary" disabled={busy || !st?.complete} onClick={() => run(() => gate.seal(caseId, p.template, stepId("seal")))}
                  title={st?.complete ? "" : w.pcStillOpen(st?.open.length ?? 0)}>{w.pcSeal}</button>
          {!st?.complete && <span className="hint">{w.pcStillOpen(st?.open.length ?? 0)}</span>}
        </div>
      )}
      {err && <p className="c-refused">{err}</p>}
    </section>
  );
}
