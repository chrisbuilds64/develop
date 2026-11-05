// Home (design hand-back, 2026-11-05): what needs you, in the order the core ranks it, grouped the way a clerk reads a
// morning — urgent first, then what is ready to confirm, then what waits for something; beside it what the AI is doing
// right now and what you sealed today. Everything comes from the core: /api/me/turns, /api/cases, /api/me/rhythm.
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { openKeys } from "../components/Keys";
import { api, type ConfigView, type TurnOut, type CaseCard } from "../api";
import { ago, type words } from "../words";
import { Seal } from "../components/Icons";

type W = ReturnType<typeof words>;

function short(iso: string, lang: string): string {
  const a = ago(iso, lang);
  return a.replace(/ (Min\.|min)$/, "m").replace(/ (Std\.|h)$/, "h").replace(/ Tage?n?$| days?$/, "d");
}

function Row({ card, action, since, lang, w, go }: { card: CaseCard; action: string; since: string; lang: string; w: W; go: (p: string) => void }) {
  const open = () => go(`/case/${encodeURIComponent(card.id)}?g=you`);
  return (
    <div className={`row${card.unread ? " unread" : ""}`} role="link" tabIndex={0} onClick={open} onKeyDown={(e) => { if (e.key === "Enter") open(); }}>
      <span className="sq" style={{ background: card.tint || undefined }} />
      <span className="r-party">{card.party || card.external_id || card.label_word}</span>
      <span className="r-title">{card.title}</span>
      <span className="r-action">{action}</span>
      <span className="r-age">{since ? short(since, lang) : ""}</span>
      <span className="kbd rk">⏎</span>
    </div>
  );
}

function Section({ dot, title, rows, lang, w, go }: { dot: string; title: string; rows: { card: CaseCard; action: string; since: string }[]; lang: string; w: W; go: (p: string) => void }) {
  if (rows.length === 0) return null;
  return (
    <>
      <div className="grph"><span className={`gdot ${dot}`} />{title}<span className="gn">{rows.length}</span></div>
      <div className="rgrp">{rows.map((r) => <Row key={r.card.id + r.action} {...r} lang={lang} w={w} go={go} />)}</div>
    </>
  );
}

export function Home({ config, go, w }: { config: ConfigView; go: (p: string) => void; w: W }) {
  const lang = config.lang;
  const turns = useQuery({ queryKey: ["turns"], queryFn: api.turns });
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const rhythm = useQuery({ queryKey: ["rhythm"], queryFn: api.rhythm });

  // one row per case: its main move is the one that counts (the core ranks them; the first per case wins)
  const seen = new Set<string>();
  const mine: TurnOut[] = (turns.data ?? []).filter((t) => !seen.has(t.case.id) && !!seen.add(t.case.id));
  const urgent = mine.filter((t) => t.turn.kind === "date");
  const blocked = mine.filter((t) => t.turn.kind !== "date" && t.turn.blocked_by.length > 0);
  const ready = mine.filter((t) => t.turn.kind !== "date" && t.turn.blocked_by.length === 0);
  const working = groups.data?.find((g) => g.key === "claude")?.cases ?? [];
  const next = [...urgent, ...ready, ...blocked][0];
  const n = mine.length;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (e.key !== "Enter" || e.metaKey || e.ctrlKey || e.altKey || ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(t.tagName) || t.getAttribute("role") === "link") return;
      if (next) { e.preventDefault(); go(`/case/${encodeURIComponent(next.case.id)}?g=you`); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next?.case.id]);

  if (turns.isLoading || groups.isLoading) return <main className="home-wrap" />;
  // the action without the case's own title, which the row already shows ("Approve: Hail damage" → "Approve")
  const bare = (text: string, title: string) => text.split(`${title}: `).join("").split(`: ${title}`).join("").split(title).join("").replace(/^[\s:·–-]+|[\s:·–-]+$/g, "");
  const row = (t: TurnOut) => ({ card: t.case, action: t.turn.blocked_by.length ? bare(t.turn.headline || t.turn.label, t.case.title) || t.turn.label : t.turn.label, since: t.turn.since || t.case.since });
  const cap = (x: string) => x.charAt(0).toUpperCase() + x.slice(1);
  const today = new Date().toLocaleDateString(lang === "de" ? "de-DE" : "en-GB", { weekday: "long", day: "numeric", month: "long" });
  const ai = working[0];

  return (
    <main className="home-wrap">
      <div className="home">
        <section className="home-main">
          <div className="home-date">{today}</div>
          <div className="home-head">
            <div>
              <h1 className="h1">{w.needYou(n)}</h1>
              <p className="home-lead">{w.homeLead(n)}</p>
            </div>
            {next && (
              <button type="button" className="primary" data-help="cf.next" onClick={() => go(`/case/${encodeURIComponent(next.case.id)}?g=you`)}>
                {w.openNext} <span className="k">⏎</span>
              </button>
            )}
          </div>
          <Section dot="urgent" title={w.urgent} rows={urgent.map(row)} lang={lang} w={w} go={go} />
          <Section dot="you" title={w.ready} rows={ready.map(row)} lang={lang} w={w} go={go} />
          <Section dot="quiet" title={w.waitingSomething} rows={blocked.map(row)} lang={lang} w={w} go={go} />
          <Section dot="ai" title={w.aiWorking} rows={working.map((c) => ({ card: c, action: cap(c.turn?.reason || c.stage_word), since: c.since }))} lang={lang} w={w} go={go} />
        </section>
        <aside className="home-side">
          {ai && (
            <div className="card aiw">
              <div className="aiw-k">✦ {w.aiCard}</div>
              <button type="button" className="aw" data-help-skip="explained by cf.groups" onClick={() => go(`/case/${encodeURIComponent(ai.id)}?g=claude`)}>
                <span className="aw-k">{cap(ai.turn?.reason || ai.stage_word)}</span>
                <span className="aw-t">{ai.title}</span>
                <span className="aw-m">{[ai.party || ai.label_word, ai.since ? ago(ai.since, lang) : ""].filter(Boolean).join(" · ")}</span>
                <span className="prog"><i /></span>
                <span className="aw-n">{w.aiCardNote}</span>
              </button>
            </div>
          )}
          <div className="card">
            <div className="card-k">{w.doneToday}</div>
            {(rhythm.data?.today_seals ?? []).length === 0 ? <p className="card-none">{w.doneNone}</p> : (rhythm.data?.today_seals ?? []).map((s) => (
              <button key={s.case + s.at} type="button" className="sealrow" data-help-skip="explained by cf.daydone" onClick={() => go(`/case/${encodeURIComponent(s.case)}`)}>
                <span className="seal-i"><Seal /></span>
                <span className="seal-t">{s.title}</span>
                <span className="seal-at">{s.at.slice(11, 16)}</span>
              </button>
            ))}
          </div>
          <button type="button" className="kbhint" data-help-skip="opens the keyboard shortcuts" onClick={openKeys}><span className="gd-ic kb" aria-hidden="true" />{w.keysTitle}<span className="kbd">?</span></button>
        </aside>
      </div>
    </main>
  );
}
