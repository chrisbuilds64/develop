// The rulebook (design hand-back, 2026-11-05): everything the office and the AI work by, in four tabs. Rules: what the
// AI proposes waits for you, grouped by the area it applies to; what is in force can be changed (a new version, four
// eyes) or retired with a reason. Case steps, AI limits and letter templates read from the configuration and the
// `_bausteine/`; a template is changed the same way a rule is. Connections (the hand-off matrix and the systems) when
// this place has them. Nothing is deleted: a rejected or retired version stays on record with its reason.
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type ConfigView, type RuleArea, type RuleModule, type RulesOut, type ModuleHistory } from "../api";
import { VideoStage, type Video } from "../components/Explain";
import { PenIcon } from "../components/Icons";
import type { words } from "../words";

type W = ReturnType<typeof words>;
type Tab = "rules" | "steps" | "limits" | "letters" | "links";
const OFFICE = "__office";

function day(iso: string, lang: string): string {
  if (!iso) return "";
  const d = new Date(iso.length <= 10 ? iso + "T12:00:00" : iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString(lang === "de" ? "de-DE" : "en-GB", { day: "numeric", month: "short" });
}
const sources = (note: string) => note.split("¶").map((x) => x.trim()).filter(Boolean).map((x) => {
  const i = x.indexOf(":");
  return i > 0 ? [x.slice(0, i).trim(), x.slice(i + 1).trim()] : ["", x];
});
const isRule = (m: RuleModule) => m.kind === "Regel" || m.kind.toLowerCase() === "rule";

export function Rules({ config, w, lang }: { config: ConfigView; w: W; lang: string }) {
  const q = useQuery({ queryKey: ["rules"], queryFn: api.rules, refetchInterval: false });
  const [tab, setTab] = useState<Tab>("rules");
  const [toast, setToast] = useState<string | null>(null);
  const [playing, setPlaying] = useState<Video | null>(null);
  const videos = ((config as unknown as { videos?: Video[] }).videos ?? []);
  const video = videos.find((v) => (v.where ?? []).includes("rules")) ?? videos.find((v) => v.key === "ch07");
  if (!q.data) return <main className="main view-rules rb"><p className="empty">…</p></main>;
  const r = q.data;
  const say = (t: string) => { setToast(t); window.setTimeout(() => setToast((x) => (x === t ? null : x)), 3200); };
  const hasLinks = (r.matrix?.length ?? 0) > 0 || r.connectors.length > 0;
  const tabs: [Tab, string][] = [["rules", w.rbTabRules], ["steps", w.rbTabSteps], ["limits", w.rbTabLimits], ["letters", w.rbTabLetters], ...(hasLinks ? [["links", w.rbTabLinks] as [Tab, string]] : [])];
  const intro: Record<Tab, [string, string]> = {
    rules: [w.rbIntroRules, w.rbExRules], steps: [w.rbIntroSteps, w.rbExSteps], limits: [w.rbIntroLimits, w.rbExLimits],
    letters: [w.rbIntroLetters, w.rbExLetters], links: [w.rbIntroLinks, w.rbExLinks],
  };
  return (
    <main className="main view-rules rb" data-help="cf.rules">
      <div className="rb-page">
        <header className="rb-head">
          <h1>{w.rules}</h1>
          <p className="rb-lead">{w.rbLead}</p>
          {video && <button type="button" className="rb-watch" data-help-skip="a video about this page" onClick={() => setPlaying(video)}><span className="rb-play" aria-hidden="true" />{w.rbWatch} · {video.seconds} s</button>}
        </header>
        <div className="rb-tabs" role="tablist">
          {tabs.map(([k, label]) => (
            <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} data-help-skip="a tab of the rulebook" onClick={() => setTab(k)}>{label}</button>
          ))}
        </div>
        <div className="rb-intro"><p>{intro[tab][0]}</p><p className="rb-ex">{intro[tab][1]}</p></div>
        {tab === "rules" && <RulesTab r={r} w={w} lang={lang} say={say} />}
        {tab === "steps" && <StepsTab r={r} w={w} product={config.product} />}
        {tab === "limits" && <LimitsTab r={r} w={w} />}
        {tab === "letters" && <LettersTab r={r} w={w} lang={lang} say={say} />}
        {tab === "links" && <LinksTab r={r} w={w} />}
      </div>
      {toast && <div className="rb-toast" role="status">{toast}</div>}
      {playing && <VideoStage video={playing} onClose={() => setPlaying(null)} />}
    </main>
  );
}

// ------------------------------------------------------------------ rules: waiting for you, in force

function useAct(say: (t: string) => void) {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const run = async (f: () => Promise<unknown>, done: string) => {
    try { await f(); setError(null); await qc.invalidateQueries({ queryKey: ["rules"] }); say(done); return true; }
    catch (e) { setError(e instanceof ApiError ? e.message : String(e)); return false; }
  };
  return { run, error, setError };
}

function groupByArea(list: RuleModule[], areas: RuleArea[], pick: (m: RuleModule) => string[]) {
  const order = [OFFICE, ...areas.map((a) => a.key)];
  const first = (m: RuleModule) => pick(m)[0] ?? OFFICE;
  return order.filter((k) => list.some((m) => first(m) === k)).map((k) => ({ key: k, items: list.filter((m) => first(m) === k) }))
    .concat(list.some((m) => !order.includes(first(m))) ? [{ key: "?", items: list.filter((m) => !order.includes(first(m))) }] : []);
}

function AreaHead({ k, areas, w }: { k: string; areas: RuleArea[]; w: W }) {
  const a = areas.find((x) => x.key === k);
  return <div className="rb-gh">{k === OFFICE ? <><b className="rb-go">◎</b>{w.rbOffice}</> : <><i style={{ background: a?.color || undefined }} />{a?.word ?? k}</>}</div>;
}

function RulesTab({ r, w, lang, say }: { r: RulesOut; w: W; lang: string; say: (t: string) => void }) {
  const rules = r.modules.filter(isRule).filter((m) => m.status !== "zurückgezogen" || m.draft);
  const draftAreas = (m: RuleModule) => (m.draft ? m.draft_areas : m.areas);
  const waiting = rules.filter((m) => m.draft && r.may_decide && m.draft_by !== r.me);
  const mine = rules.filter((m) => m.draft && m.draft_by === r.me);
  const inForce = rules.filter((m) => m.in_force && m.status !== "zurückgezogen");
  if (!rules.length) return <p className="rb-none">{w.rbNoRules}</p>;
  return (
    <>
      {waiting.length > 0 && (
        <>
          <h3 className="rb-h"><span className="rb-dot" />{w.rbWaiting}<em>{waiting.length}</em></h3>
          <section className="rb-card" data-help="cf.rb-waiting">
            {groupByArea(waiting, r.areas, draftAreas).map((g) => (
              <div key={g.key}><AreaHead k={g.key} areas={r.areas} w={w} />{g.items.map((m) => <Proposal key={m.id} m={m} r={r} k={g.key} w={w} lang={lang} say={say} />)}</div>
            ))}
          </section>
        </>
      )}
      {mine.length > 0 && (
        <>
          <h3 className="rb-h"><span className="rb-dot quiet" />{w.rbWaitingOthers}<em>{mine.length}</em></h3>
          <section className="rb-card">
            {mine.map((m) => (
              <div key={m.id} className="rb-rule in">
                <div className="rb-main"><p className="rb-t">{m.draft_text}</p><div className="rb-m"><span>{w.rbYouWrote}</span><span className="rb-sep">·</span><span>{day(m.draft_date, lang)}</span></div></div>
              </div>
            ))}
          </section>
        </>
      )}
      <h3 className="rb-h"><span className="rb-dot ok" />{w.rbInForce}<em>{inForce.length}</em></h3>
      <section className="rb-card" data-help="cf.rb-in-force">
        {groupByArea(inForce, r.areas, (m) => m.areas).map((g) => (
          <div key={g.key}><AreaHead k={g.key} areas={r.areas} w={w} />{g.items.map((m) => <InForce key={m.id} m={m} r={r} k={g.key} w={w} lang={lang} say={say} />)}</div>
        ))}
      </section>
    </>
  );
}

function also(areasOfIt: string[], k: string, all: RuleArea[], w: W) {
  const other = areasOfIt.filter((x) => x !== k).map((x) => all.find((a) => a.key === x)?.word ?? x);
  return other.length ? <><span className="rb-also">{w.rbAlso(other.join(", "))}</span><span className="rb-sep">·</span></> : null;
}

function ScopePick({ value, onChange, areas, w }: { value: string[]; onChange: (v: string[]) => void; areas: RuleArea[]; w: W }) {
  const toggle = (k: string) => onChange(value.includes(k) ? value.filter((x) => x !== k) : [...value, k]);
  return (
    <div className="rb-scope">
      <div className="rb-fl">{w.rbApplies}</div>
      <div className="rb-sc">
        <button type="button" className={value.length === 0 ? "on" : ""} data-help-skip="scope: the whole office" onClick={() => onChange([])}>{w.rbOffice}</button>
        {areas.map((a) => (
          <button key={a.key} type="button" className={value.includes(a.key) ? "on" : ""} data-help-skip="scope: one area" onClick={() => toggle(a.key)}>
            <i style={{ background: a.color || undefined }} />{a.word}
          </button>
        ))}
      </div>
    </div>
  );
}

function Proposal({ m, r, k, w, lang, say }: { m: RuleModule; r: RulesOut; k: string; w: W; lang: string; say: (t: string) => void }) {
  const [mode, setMode] = useState<"" | "edit" | "reject" | "why">("");
  const [text, setText] = useState(m.draft_text);
  const [scope, setScope] = useState<string[]>(m.draft_areas);
  const [reason, setReason] = useState("");
  const { run, error, setError } = useAct(say);
  const src = sources(m.draft_note);
  const close = () => { setMode(""); setError(null); };
  return (
    <div className="rb-rule">
      {mode === "edit" ? (
        <div className="rb-main">
          <textarea className="rb-in rb-ta" rows={2} value={text} autoFocus onChange={(e) => setText(e.target.value)} />
          <ScopePick value={scope} onChange={setScope} areas={r.areas} w={w} />
          <p className="rb-note">{w.rbChangeNote}</p>
          {error && <p className="rb-err">{error}</p>}
          <div className="rb-acts">
            <button type="button" className="rb-btn" data-help-skip="cancel" onClick={close}>{w.rbCancel}</button>
            <button type="button" className="rb-btn ok" data-help-skip="explained by cf.rb-waiting" disabled={!r.may_edit}
                    onClick={async () => { if (!text.trim()) return setError(w.rbEmpty); if (await run(() => api.moduleDraft(m.id, { text, areas: scope, note: m.draft_note }), w.rbDoneDraft)) close(); }}>{w.rbSaveChange}</button>
          </div>
        </div>
      ) : mode === "reject" ? (
        <div className="rb-main">
          <p className="rb-t">{m.draft_text}</p>
          {error && <p className="rb-err">{error}</p>}
          <div className="rb-acts">
            <input className="rb-in" autoFocus value={reason} placeholder={w.rbRejectPh} onChange={(e) => setReason(e.target.value)} />
            <button type="button" className="rb-btn" data-help-skip="cancel" onClick={close}>{w.rbCancel}</button>
            <button type="button" className="rb-btn bad" data-help-skip="explained by cf.rb-waiting"
                    onClick={async () => { if (!reason.trim()) return setError(w.rbNeedReason); if (await run(() => api.moduleReject(m.id, reason), w.rbDoneReject)) close(); }}>{w.rbReject}</button>
          </div>
        </div>
      ) : (
        <>
          <div className="rb-main">
            <p className="rb-t">{m.draft_text}</p>
            <div className="rb-m">
              {also(m.draft_areas, k, r.areas, w)}
              <span>{m.in_force ? w.rbWaitsVersion(m.draft ?? 0, m.draft_by) : (m.source || w.rbProposedBy(m.draft_by, day(m.draft_date, lang)))}</span>
              {src.length > 0 && <><span className="rb-sep">·</span>
                <button type="button" className="rb-why" data-help-skip="shows where the proposal comes from" onClick={() => setMode(mode === "why" ? "" : "why")}>{mode === "why" ? w.rbHideSources : w.rbSources(src.length)}</button></>}
            </div>
            {mode === "why" && <div className="rb-src">{src.map(([a, b], i) => <div key={i}>{a && <span>{a}</span>}{b}</div>)}</div>}
            {error && <p className="rb-err">{error}</p>}
          </div>
          <div className="rb-side">
            <button type="button" className="rb-acc" data-help-skip="explained by cf.rb-waiting" onClick={() => run(() => api.moduleApprove(m.id), w.rbDoneAccept)}>{w.rbAccept}</button>
            {r.may_edit && <button type="button" className="rb-ic" data-help-skip="change the proposal" aria-label={w.rbChange} title={w.rbChange} onClick={() => setMode("edit")}><PenIcon /></button>}
            <button type="button" className="rb-ic no" data-help-skip="reject the proposal" aria-label={w.rbReject} title={w.rbReject} onClick={() => setMode("reject")}>✕</button>
          </div>
        </>
      )}
    </div>
  );
}

function InForce({ m, r, k, w, lang, say }: { m: RuleModule; r: RulesOut; k: string; w: W; lang: string; say: (t: string) => void }) {
  const [mode, setMode] = useState<"" | "edit" | "retire" | "history">("");
  const [text, setText] = useState(m.text);
  const [scope, setScope] = useState<string[]>(m.areas);
  const [reason, setReason] = useState("");
  const { run, error, setError } = useAct(say);
  const hist = useQuery({ queryKey: ["module", m.id], queryFn: () => api.module(m.id), enabled: mode === "history" });
  const close = () => { setMode(""); setError(null); };
  const next = m.versions + 1;
  const editable = r.may_edit && !m.draft;
  return (
    <div className="rb-rule in">
      {mode === "edit" ? (
        <div className="rb-main">
          <textarea className="rb-in rb-ta" rows={2} value={text} autoFocus onChange={(e) => setText(e.target.value)} />
          <ScopePick value={scope} onChange={setScope} areas={r.areas} w={w} />
          <p className="rb-note">{w.rbVersionNote(next)}</p>
          {error && <p className="rb-err">{error}</p>}
          <div className="rb-acts">
            <button type="button" className="rb-btn" data-help-skip="cancel" onClick={close}>{w.rbCancel}</button>
            <button type="button" className="rb-btn ok" data-help-skip="explained by cf.rb-in-force"
                    onClick={async () => { if (!text.trim()) return setError(w.rbEmpty); if (await run(() => api.moduleDraft(m.id, { text, areas: scope }), w.rbDoneDraft)) close(); }}>{w.rbSaveVersion(next)}</button>
          </div>
        </div>
      ) : mode === "retire" ? (
        <div className="rb-main">
          <p className="rb-t">{m.text}</p>
          {error && <p className="rb-err">{error}</p>}
          <div className="rb-acts">
            <input className="rb-in" autoFocus value={reason} placeholder={w.rbRetirePh} onChange={(e) => setReason(e.target.value)} />
            <button type="button" className="rb-btn" data-help-skip="cancel" onClick={close}>{w.rbCancel}</button>
            <button type="button" className="rb-btn bad" data-help-skip="explained by cf.rb-in-force"
                    onClick={async () => { if (!reason.trim()) return setError(w.rbNeedReason); if (await run(() => api.moduleRetire(m.id, reason), w.rbDoneRetire)) close(); }}>{w.rbRetireRule}</button>
          </div>
        </div>
      ) : (
        <>
          <div className="rb-main">
            <p className="rb-t">{m.text}</p>
            <div className="rb-m">
              {also(m.areas, k, r.areas, w)}
              <span>{w.rbAccepted(m.approved_by, day(m.date, lang), m.version)}</span>
              {m.versions > 1 && <><span className="rb-sep">·</span>
                <button type="button" className="rb-why" data-help-skip="shows earlier versions" onClick={() => setMode(mode === "history" ? "" : "history")}>{mode === "history" ? w.rbHideHistory : w.rbHistory}</button></>}
            </div>
            {mode === "history" && <History h={hist.data} w={w} lang={lang} />}
            {error && <p className="rb-err">{error}</p>}
          </div>
          {editable && (
            <div className="rb-side">
              <button type="button" className="rb-ic" data-help-skip="change the rule" aria-label={w.rbChange} title={w.rbChange} onClick={() => setMode("edit")}><PenIcon /></button>
              <button type="button" className="rb-ic no" data-help-skip="retire the rule" aria-label={w.rbRetire} title={w.rbRetire} onClick={() => setMode("retire")}>✕</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function History({ h, w, lang }: { h?: ModuleHistory; w: W; lang: string }) {
  if (!h) return <div className="rb-src">…</div>;
  return (
    <div className="rb-src">
      {[...h.versions].reverse().map((v) => (
        <div key={v.version}>
          <span>{w.version(v.version)} · {v.approved_by || v.drafted_by} · {day(v.date, lang)}{v.status !== "freigegeben" ? ` · ${v.status}` : ""}</span>
          {v.text}{v.reason || (v.status !== "freigegeben" && v.note) ? <em className="rb-reason"> {v.reason || v.note}</em> : null}
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ case steps, AI limits, connections: read from the configuration

function StepsTab({ r, w, product }: { r: RulesOut; w: W; product: string }) {
  return (
    <section className="rb-card" data-help="cf.rb-steps">
      <div className="rb-sth"><h3>{product}</h3><span>{w.rbStepCount(r.stages.length)}</span></div>
      {r.stages.map((s, i) => {
        const how = s.actions.map((a) => a.word + (a.to_word ? ` → ${a.to_word}` : "")).join(" · ");
        const auto = s.auto.map((a) => w.rbAuto(a.on_file, a.skill)).join(" · ");
        const sub = [how, auto].filter(Boolean).join(" · ");
        const same = i > 0 && (r.stages[i - 1].station || r.stages[i - 1].word) === (s.station || s.word);
        const name = same ? s.word.charAt(0).toUpperCase() + s.word.slice(1) : s.station || s.word;
        return (
          <div key={s.folder} className="rb-row">
            <span className="rb-n">{i + 1}</span>
            <span className="rb-an"><b>{name}</b>{sub && <span>{sub}</span>}</span>
            {s.turn_word && <span className="rb-who" title={w.rbWho}>{s.turn_word}</span>}
          </div>
        );
      })}
    </section>
  );
}

function LimitsTab({ r, w }: { r: RulesOut; w: W }) {
  return (
    <>
      {r.skills.map((s) => (
        <section key={s.name} className="rb-card" data-help="cf.rb-limits">
          <h3 className="rb-hdt"><span>✦</span>{s.name}</h3>
          <div className="rb-hdo">
            <div><b className="y">{w.rbCanDo}</b><p><i className="y">✓</i>{s.does}</p></div>
            <div><b className="n">{w.rbNeverDoes}</b><p><i className="n">✕</i>{s.never}</p></div>
          </div>
          {s.orderable_by.length > 0 && <p className="rb-by">{w.rbOrderedBy(s.orderable_by.join(", "))}</p>}
        </section>
      ))}
    </>
  );
}

function LinksTab({ r, w }: { r: RulesOut; w: W }) {
  return (
    <>
      {(r.matrix?.length ?? 0) > 0 && (
        <section className="rb-card" data-help="cf.matrix">
          <h3 className="rb-ch">{w.rulesMatrix}</h3>
          {r.matrix!.map((m) => (
            <div key={m.id} className={`rb-row${m.connected ? "" : " off"}`}>
              <span className="rb-an"><b>{m.word}</b><span>{[m.when, `${m.action_word}${m.target_word ? ` · ${m.target_word}` : ""}`].filter(Boolean).join(" · ")}</span></span>
              <span className="rb-who">{!m.connected ? w.notConnected : m.approval === "auto" ? w.rbAutoOk : w.rbHuman}</span>
            </div>
          ))}
        </section>
      )}
      {r.connectors.length > 0 && (
        <section className="rb-card">
          <h3 className="rb-ch">{w.rulesConnectors}</h3>
          {r.connectors.map((k) => (
            <div key={k.id} className="rb-row">
              <span className="rb-an"><b>{k.name}</b><span>{[k.carries, k.note].filter(Boolean).join(" · ")}</span></span>
              <span className="rb-who">{[k.standard, k.direction].filter(Boolean).join(" · ")}</span>
            </div>
          ))}
        </section>
      )}
    </>
  );
}

// ------------------------------------------------------------------ letter templates

function LettersTab({ r, w, lang, say }: { r: RulesOut; w: W; lang: string; say: (t: string) => void }) {
  const list = r.modules.filter((m) => !isRule(m) && m.in_force && m.status !== "zurückgezogen");
  const [open, setOpen] = useState<string | null>(null);
  if (!list.length) return <p className="rb-none">—</p>;
  return (
    <section className="rb-card" data-help="cf.rb-letters">
      {list.map((m) => <Template key={m.id} m={m} r={r} w={w} lang={lang} say={say} open={open === m.id} onToggle={() => setOpen(open === m.id ? null : m.id)} />)}
    </section>
  );
}

function Template({ m, r, w, lang, say, open, onToggle }: { m: RuleModule; r: RulesOut; w: W; lang: string; say: (t: string) => void; open: boolean; onToggle: () => void }) {
  const [edit, setEdit] = useState(false);
  const [text, setText] = useState(m.text);
  const { run, error, setError } = useAct(say);
  const next = m.versions + 1;
  const mayDecide = !!m.draft && r.may_decide && m.draft_by !== r.me;
  const marked = (t: string) => t.split(/(\{[^}]+\})/g).map((p, i) => (p.startsWith("{") && p.endsWith("}") ? <span key={i} className="rb-ph">{p.slice(1, -1)}</span> : p));
  return (
    <div className={`rb-tb${open ? " open" : ""}`}>
      <button type="button" className="rb-tbh" data-help-skip="opens the template" aria-expanded={open} onClick={onToggle}>
        <span className="rb-an"><b>{m.title}</b><span>{w.rbUsedIn(m.use, m.version)}{m.draft ? ` · ${w.rbWaitsVersion(m.draft, m.draft_by)}` : ""}</span></span>
        <span className="rb-go-ic" aria-hidden="true">{open ? "⌄" : "›"}</span>
      </button>
      {open && (edit ? (
        <>
          <textarea className="rb-in rb-ta" rows={6} value={text} autoFocus onChange={(e) => setText(e.target.value)} />
          <p className="rb-note">{w.rbPlaceholderNote(next)}</p>
          {error && <p className="rb-err">{error}</p>}
          <div className="rb-acts">
            <button type="button" className="rb-btn" data-help-skip="cancel" onClick={() => { setEdit(false); setError(null); }}>{w.rbCancel}</button>
            <button type="button" className="rb-btn ok" data-help-skip="explained by cf.rb-letters"
                    onClick={async () => { if (!text.trim()) return setError(w.rbEmpty); if (await run(() => api.moduleDraft(m.id, { text }), w.rbDoneDraft)) setEdit(false); }}>{w.rbSaveVersion(next)}</button>
          </div>
        </>
      ) : (
        <>
          <div className="rb-tbtx">{marked(m.draft && mayDecide ? m.draft_text : m.text)}</div>
          {error && <p className="rb-err">{error}</p>}
          <div className="rb-acts start">
            {mayDecide ? (
              <>
                <button type="button" className="rb-btn ok" data-help-skip="explained by cf.rb-letters" onClick={() => run(() => api.moduleApprove(m.id), w.rbDoneAccept)}>{w.rbAccept}</button>
                <span className="rb-note">{w.rbProposedBy(m.draft_by, day(m.draft_date, lang))}</span>
              </>
            ) : r.may_edit && !m.draft ? (
              <button type="button" className="rb-btn" data-help-skip="explained by cf.rb-letters" onClick={() => setEdit(true)}>{w.rbEditTemplate}</button>
            ) : m.draft ? <span className="rb-note">{w.rbYouWrote}</span> : null}
          </div>
        </>
      ))}
    </div>
  );
}
