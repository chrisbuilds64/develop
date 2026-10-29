// The stack (ADR-024, step 2): the workspace is one column. The place line, how many gates wait, the rule of the order, the
// first gate in full depth (screens/Case), the rest as rows ("after"), what has no gate as one row per group, and behind it,
// folded: the second views, the rulebook, the signals, the house canon, the sample worlds, the way to put something in and the
// question to the AI. /case/<id> is the same screen with that case as the gate; /group/<key> is one group as rows.
// Everything comes from /api/me/turns (already in the engine's order), /api/cases and the vocabulary; nothing here names a domain.
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError, BASE, stepId, talk, type CaseCard, type ConfigView, type MeOut, type Turn, type TurnOut } from "../api";
import { CaseScreen } from "./Case";
import { DayDone } from "../components/DayDone";
import { paper } from "../moments";
import { Calendar, Chev, Dot, Lock, Seal } from "../components/Icons";
import { dateShort, type words } from "../words";

type W = ReturnType<typeof words>;
type Go = (p: string) => void;
const GROUPS = ["claude", "others", "date", "planned", "out", "ideas", "archive"];   // every group but "you": the stack is "you"

export const ident = (c: CaseCard) => c.external_id || (c.number ? `${c.label}-${c.number}` : c.id);

export function actorName(config: ConfigView, actor: string): string {
  if (actor === "claude") return config.people.find((p) => p.kind === "agent")?.name ?? actor;
  if (actor.startsWith("role:")) {
    const role = actor.slice(5);
    const holders = config.people.filter((p) => p.kind === "human" && p.roles.includes(role));
    return holders.length === 1 ? holders[0].name : (((config.words as { roles?: Record<string, string> }).roles?.[role]) ?? role);
  }
  return config.people.find((p) => p.id === actor)?.name ?? actor;
}

/** The place as a sentence (rule 6): workspace › … › here; the last member is no link. */
export function Place({ config, go, parts, tail }: { config: ConfigView; go: Go; parts: { text: string; to?: string }[]; tail?: string }) {
  return (
    <p className="ort">
      <a href={`${BASE}/`} onClick={(e) => { e.preventDefault(); go("/"); }}>{config.product}</a>
      {parts.map((p, i) => (
        <span key={i}> <span className="sep" aria-hidden="true">›</span> {p.to ? <a href={BASE + p.to} onClick={(e) => { e.preventDefault(); go(p.to!); }}>{p.text}</a> : <b>{p.text}</b>}</span>
      ))}
      {tail && <span> <span className="sep" aria-hidden="true">·</span> {tail}</span>}
    </p>
  );
}

/** One move as a row: number · title · station · since · who, and on the right the verb with its form (rule 15):
 *  a lock when it waits for something, the seal mark when it stamps, a calendar when a date puts it first, else a dot. */
export function TurnRow({ c, t, config, go, w, lang, mine }: { c: CaseCard; t: Turn | null | undefined; config: ConfigView; go: Go; w: W; lang: string; mine?: boolean }) {
  const to = `/case/${encodeURIComponent(c.id)}`;
  const locked = !!t && t.blocked_by.some((b) => !b.startsWith("four eyes:"));
  const form = !t ? "" : locked ? "lock" : t.seal ? "seal" : t.date ? "date" : "punkt";
  const who = t && !mine && t.actor ? actorName(config, t.actor) : "";
  const since = t?.since || c.since;
  return (
    <li>
      <a className={`row${mine ? " du" : ""}`} href={BASE + to} onClick={(e) => { e.preventDefault(); go(to); }}>
        <span className="t"><span className="id mono">{ident(c)}</span>{c.title}</span>
        <span className="s">{c.stage_word}{since ? ` · ${w.sinceDate(dateShort(since, lang))}` : ""}{who ? ` · ${who}` : ""}</span>
        {t && <span className={`act ${form}${t.seal ? " seal" : ""}`}>{form === "lock" ? <Lock /> : form === "seal" ? <Seal /> : form === "date" ? <Calendar /> : <Dot />}{t.label}</span>}
      </a>
    </li>
  );
}

export function Stack({ config, me, go, w, id, onFresh }: { config: ConfigView; me: MeOut; go: Go; w: W; id?: string; onFresh: (world?: string) => void }) {
  const lang = config.lang;
  const turnsQ = useQuery({ queryKey: ["turns"], queryFn: api.turns });
  const groupsQ = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const turns = turnsQ.data ?? [];
  const cards = (groupsQ.data ?? []).flatMap((g) => g.cases);
  // the stack: one entry per case — its first move in the engine's order is the case's gate; nudges stand in the reserve
  const gates: TurnOut[] = [], nudges: TurnOut[] = [];
  const seen = new Set<string>();
  for (const t of turns) { if (seen.has(t.case.id)) continue; seen.add(t.case.id); (t.turn.kind === "nudge" ? nudges : gates).push(t); }
  const shownId = id ?? gates[0]?.case.id;
  const stackIds = gates.map((g) => g.case.id);
  const at = shownId ? stackIds.indexOf(shownId) : -1;
  const after = gates.filter((g) => g.case.id !== shownId);
  const byLabel = new Map<string, TurnOut[]>();
  for (const n of nudges.filter((g) => g.case.id !== shownId)) byLabel.set(n.turn.label, [...(byLabel.get(n.turn.label) ?? []), n]);
  const groupsByKey = new Map((groupsQ.data ?? []).map((g) => [g.key, g]));
  const count = (k: string) => groupsByKey.get(k)?.cases.length ?? 0;
  const groupWord = (k: string) => config.groups.find((g) => g.key === k)?.word ?? groupsByKey.get(k)?.word ?? k;
  const card = shownId ? (cards.find((c) => c.id === shownId) ?? gates.find((g) => g.case.id === shownId)?.case) : undefined;
  const n = gates.length;
  const loading = turnsQ.isLoading || groupsQ.isLoading;

  // the keyboard without a mode (rule 19): J/K the next and the previous gate of the stack, Esc back to the stack — never while a
  // field, the reader, a sheet or the director's list has the keys
  const ids = stackIds.join(",");
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (document.querySelector(".reader, .meta-sheet, .explain-stage, .bar-sheet, .cf-dir-pick, .house-panel")) return;
      const list = ids ? ids.split(",") : [];
      if (e.key === "j" || e.key === "J") { const next = list[at + 1]; if (next) { e.preventDefault(); go(`/case/${encodeURIComponent(next)}`); } }
      else if (e.key === "k" || e.key === "K") { if (at > 0) { e.preventDefault(); go(`/case/${encodeURIComponent(list[at - 1])}`); } }
      else if (e.key === "Escape" && id) { e.preventDefault(); go("/"); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [at, id, ids, go]);

  const chips = ["you", "others", "out"];
  const present = GROUPS.filter((k) => count(k) > 0);
  return (
    <main className="main gate-main stack-main" aria-label={config.product}>
      {id ? <Place config={config} go={go} parts={[{ text: card ? ident(card) : id }]} tail={card?.stage_word} />
        : <p className="ort"><b>{config.product}</b> <span className="sep" aria-hidden="true">·</span> {w.atYou}</p>}

      <div className="stapel" data-help="cf.stack">
        <p className="zahl" id="stapel" tabIndex={-1}>{loading ? "…" : w.stackHead(n)}</p>
        <span className="filt" role="group" aria-label={w.groupsLabel} data-help="cf.groups">
          {chips.map((k) => {
            const to = k === "you" ? "/" : `/group/${k}`;
            return <a key={k} className="chip" href={BASE + to} aria-current={!id && k === "you" ? "page" : undefined} onClick={(e) => { e.preventDefault(); go(to); }}>{groupWord(k)} <span className="c">{count(k)}</span></a>;
          })}
        </span>
      </div>
      <div className="rangzeile" data-help="cf.order">
        <span>{w.orderWord}: <span className="regel">{(config.order ?? []).map((k) => w.kindWord(k)).join(" → ")}</span></span>
        <details className="rang"><summary>{w.orderWhy}</summary><div className="body">{w.orderText} {w.keys}.</div></details>
      </div>

      {shownId ? <CaseScreen id={shownId} config={config} me={me} go={go} w={w} stack={at >= 0 ? { i: at + 1, n } : undefined} />
        : !loading && <Empty config={config} me={me} go={go} w={w} cards={cards} groupWord={groupWord} ideas={count("ideas")} />}

      <section className="danach" aria-labelledby="h-danach" data-help="cf.after">
        <h2 id="h-danach">{w.after}</h2>
        {after.length === 0 && byLabel.size === 0 ? <p className="prosa-klein">{loading ? "…" : w.nothingAfter}</p> : (
          <ul className="zeilen">
            {after.map((g) => <TurnRow key={g.case.id} c={g.case} t={g.turn} config={config} go={go} w={w} lang={lang} mine />)}
            {[...byLabel].map(([label, rows]) => (
              <li key={label}>
                <details className="d">
                  <summary><Chev />{w.moreNudges(rows.length, label)}</summary>
                  <ul className="zeilen">{rows.map((g) => <TurnRow key={g.case.id} c={g.case} t={g.turn} config={config} go={go} w={w} lang={lang} mine />)}</ul>
                </details>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="vorrat" aria-labelledby="h-vorrat" data-help="cf.no-gate">
        <h2 id="h-vorrat">{w.noGateHead}</h2>
        {present.length === 0 ? <p className="prosa-klein">{loading ? "…" : w.noGateNone}</p> : (
          <ul className="gruppen">
            {present.map((k) => {
              const g = groupsByKey.get(k)!;
              return (
                <li key={k}>
                  <b>{groupWord(k)}</b> <span className="c">{g.cases.length}</span>
                  <span className="ex">{g.cases.slice(0, 3).map(ident).join(", ")}{g.cases.length > 3 ? " …" : ""}</span>
                  <a href={`${BASE}/group/${k}`} onClick={(e) => { e.preventDefault(); go(`/group/${k}`); }}>{w.open}</a>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <Behind config={config} me={me} go={go} w={w} onFresh={onFresh} />
    </main>
  );
}

/** Nothing waits for you: a sentence with what lies with others (rule 17), the reserve, and the day's seals to collect. */
function Empty({ config, me, go, w, cards, groupWord, ideas }: { config: ConfigView; me: MeOut; go: Go; w: W; cards: CaseCard[]; groupWord: (k: string) => string; ideas: number }) {
  const others = cards.filter((c) => c.group === "others" || c.group === "claude");
  const items = others.slice(0, 3).map((c) => `${ident(c)} (${c.turn ? `${actorName(config, c.turn.actor)}: ${c.turn.label}` : groupWord(c.group)})`).join(", ");
  return (
    <div className="leer" role="status">
      <h1 id="tor-h1" tabIndex={-1}>{w.stackHead(0)}</h1>
      <p>{others.length ? w.nextFromOthers(items + (others.length > 3 ? " …" : "")) : w.othersNone}</p>
      {ideas > 0 && <p><a className="btn still klein" href={`${BASE}/group/ideas`} onClick={(e) => { e.preventDefault(); go("/group/ideas"); }}>{w.openReserve} · {ideas}</a></p>}
      <DayDone w={w} me={me.person ?? ""} />
    </div>
  );
}

/** Behind the stack, folded (rule 5): the second views, the rulebook, the signals, the house canon, the sample worlds,
 *  the way to put something in, the question to the AI. Rows, never a panel. */
function Behind({ config, me, go, w, onFresh }: { config: ConfigView; me: MeOut; go: Go; w: W; onFresh: (world?: string) => void }) {
  const theme = config.theme as { canon?: boolean; create?: { label?: string; roles?: string[] }; mail_drop?: boolean };
  const create = theme.create;
  const mayCreate = !!create && (create.roles ?? []).some((r) => me.roles.includes(r));
  const mailDrop = !!theme.mail_drop && me.roles.includes("operator");
  const labelWord = create?.label ? ((config.words as { labels?: Record<string, string> }).labels?.[create.label] ?? create.label) : "";
  const [making, setMaking] = useState(false);
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const agent = config.people.find((p) => p.kind === "agent")?.name ?? "Claude";
  const otherWorlds = me.worlds.filter((x) => x !== me.world);
  const dropMail = async (f: File | undefined) => {
    if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try {
      const res = await fetch(BASE + "/api/mail", { method: "POST", body: fd, credentials: "same-origin" });
      const j = await res.json();
      if (!res.ok) throw new Error(j.reason ?? j.detail ?? `HTTP ${res.status}`);
      paper(); go(`/case/${encodeURIComponent(j.id)}`);
    } catch (e) { setErr(String((e as Error).message)); }
  };
  const link = (text: string, to: string) => (
    <a className="row" href={BASE + to} onClick={(e) => { e.preventDefault(); go(to); }}><span className="t">{text}</span><span className="act"><Chev /></span></a>
  );
  return (
    <section className="dahinter" aria-label={w.behind}>
      <details className="d" data-help="cf.behind">
        <summary><Chev />{w.behind}</summary>
        <ul className="zeilen">
          <li data-help="cf.views">{link(w.board, "/board")}</li>
          <li>{link(w.stacked, "/list")}</li>
          <li data-help="cf.rules">{link(w.rules, "/rules")}</li>
          <li data-help="cf.patterns">{link(w.signals, "/signals")}</li>
          {theme.canon && <li data-help="cf.house">{link(w.house, "/kanon")}</li>}
          {me.demo && otherWorlds.map((x) => (
            <li key={x} data-help-skip="public demo only"><button type="button" className="row" onClick={() => onFresh(x)}><span className="t">{w.world(x)}</span><span className="s">{w.sampleWorlds}</span><span className="act"><Chev /></span></button></li>
          ))}
          {mailDrop ? (
            <li data-help="cf.drop-in"><label className="row drop-row">{w.dropMail}<input type="file" accept=".eml,message/rfc822" hidden onChange={(e) => dropMail(e.target.files?.[0])} />
              {err && <span className="talk-error">{err}</span>}</label></li>
          ) : mayCreate ? (making ? (
            <li><form className="new-case row" data-help="cf.new-case" onSubmit={async (e) => { e.preventDefault(); if (!name.trim()) return; try { const r = await talk.create(name.trim(), stepId("new")); setMaking(false); setName(""); setErr(null); go(`/case/${encodeURIComponent(r.id)}`); } catch (x) { setErr(x instanceof ApiError ? x.message : String(x)); } }}>
              <input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder={w.newCasePlaceholder} maxLength={120} onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); setMaking(false); } }} />
              <button type="submit" className="btn small" disabled={!name.trim()}>{w.create}</button>
              {err && <span className="talk-error">{err}</span>}
            </form></li>
          ) : (
            <li data-help="cf.drop-in"><button type="button" className="row" onClick={() => setMaking(true)}><span className="t">{w.newCase(labelWord)}</span><span className="act"><Chev /></span></button></li>
          )) : create ? null : (
            <li data-help="cf.drop-in"><button type="button" className="row" onClick={() => document.querySelector<HTMLElement>(".belege .drop .btn, .belege .drop .droptext, .belege .selbst")?.focus()}><span className="t">{w.dropIn}</span><span className="s">{w.tapToAdd}</span><span className="act"><Chev /></span></button></li>
          )}
          <li data-help="cf.ask"><button type="button" className="row" onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))}><span className="t">{w.askClaude(agent)}</span><span className="act mono">⌘K</span></button></li>
        </ul>
      </details>
    </section>
  );
}

/** One group as rows (the existing /group/<key>): the place, the word with its count, every case with its main move. */
export function GroupScreen({ config, go, w, groupKey }: { config: ConfigView; go: Go; w: W; groupKey: string }) {
  const groupsQ = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const g = groupsQ.data?.find((x) => x.key === groupKey);
  const word = config.groups.find((x) => x.key === groupKey)?.word ?? g?.word ?? groupKey;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (e.key === "Escape" && tag !== "INPUT" && !document.querySelector(".bar-sheet, .explain-stage, .cf-dir-pick")) { e.preventDefault(); go("/"); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);
  return (
    <main className="main gate-main stack-main" aria-label={word}>
      <Place config={config} go={go} parts={[{ text: word }]} />
      <section className="gruppe" data-help="cf.list" aria-labelledby="h-gruppe">
        <h1 id="h-gruppe" tabIndex={-1}>{word} <span className="c">{g ? w.casesCount(g.cases.length) : "…"}</span></h1>
        {g && g.cases.length === 0 ? <p className="prosa-klein">{w.groupEmpty}</p> : (
          <ul className="zeilen">{g?.cases.map((c) => <TurnRow key={c.id} c={c} t={c.turn} config={config} go={go} w={w} lang={config.lang} mine={c.mine} />)}</ul>
        )}
      </section>
      <p className="prosa-klein"><a href={`${BASE}/`} onClick={(e) => { e.preventDefault(); go("/"); }}>← {w.toStack}</a></p>
    </main>
  );
}
