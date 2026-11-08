// Home (design hand-back, 2026-11-05; across workspaces 2026-11-06): what needs you in every workspace, grouped the way a
// clerk reads a morning — urgent first, then what is ready to confirm, then what waits for something; each row carries its
// workspace's colour. Beside it what the AI is doing right now and what you sealed today. From the core: /api/home (in a
// shell each workspace answers at its own address); today's seals come with each part.
import { useEffect } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { openKeys } from "../components/Keys";
import { api, type ConfigView, type MeOut, type TurnOut, type CaseCard, type PlaceOut } from "../api";
import { ago, type words } from "../words";
import { Seal } from "../components/Icons";

type W = ReturnType<typeof words>;

function short(iso: string, lang: string): string {
  const a = ago(iso, lang);
  return a.replace(/ (Min\.|min)$/, "m").replace(/ (Std\.|h)$/, "h").replace(/ Tage?n?$| days?$/, "d");
}

type Item = { card: CaseCard; action: string; since: string; place: PlaceOut; group: string };
type Open = (place: PlaceOut, path: string) => void;

function Row({ card, action, since, place, group, lang, open }: Item & { lang: string; open: Open }) {
  const go = () => open(place, `/case/${encodeURIComponent(card.id)}?g=${group}`);
  return (
    <div className={`row${card.unread ? " unread" : ""}`} role="link" tabIndex={0} onClick={go} onKeyDown={(e) => { if (e.key === "Enter") go(); }} title={place.name}>
      <span className="sq" style={{ background: place.color || card.tint || undefined }} aria-label={place.name} />
      <span className="r-party">{card.party || card.external_id || card.label_word}</span>
      <span className="r-title">{card.title}</span>
      <span className="r-action">{action}</span>
      <span className="r-age">{since ? short(since, lang) : ""}</span>
      <span className="kbd rk">⏎</span>
    </div>
  );
}

function Section({ dot, title, rows, lang, open }: { dot: string; title: string; rows: Item[]; lang: string; open: Open }) {
  if (rows.length === 0) return null;
  return (
    <>
      <div className="grph"><span className={`gdot ${dot}`} />{title}<span className="gn">{rows.length}</span></div>
      <div className="rgrp">{rows.map((r) => <Row key={r.place.id + r.card.id + r.action} {...r} lang={lang} open={open} />)}</div>
    </>
  );
}

export function Home({ config, me, go, open, w }: { config: ConfigView; me: MeOut; go: (p: string) => void; open: Open; w: W }) {
  const lang = config.lang;
  const home = useQuery({ queryKey: ["home", lang, me.world], queryFn: api.home, refetchInterval: 25_000 });
  // inside a shell, every other workspace answers for itself at its own address
  const peers = (me.shell ? (me.places ?? []).filter((p) => !p.current && p.url) : []);
  const others = useQueries({ queries: peers.map((p) => ({ queryKey: ["home-at", p.url, lang], queryFn: () => api.homeAt(p.url), refetchInterval: 25_000 })) });
  const parts = [...(home.data ?? []), ...others.flatMap((q) => q.data ?? [])];

  // the action without the case's own title, which the row already shows ("Approve: Hail damage" → "Approve")
  const bare = (text: string, title: string) => text.split(`${title}: `).join("").split(`: ${title}`).join("").split(title).join("").replace(/^[\s:·–-]+|[\s:·–-]+$/g, "");
  const cap = (x: string) => x.charAt(0).toUpperCase() + x.slice(1);
  const byAge = (a: Item, b: Item) => (a.since || "").localeCompare(b.since || "");
  // one row per case: its main move is the one that counts (the core ranks them; the first per case wins)
  const mine: { t: TurnOut; place: PlaceOut }[] = [];
  for (const part of parts) {
    const seen = new Set<string>();
    for (const t of part.turns) if (!seen.has(t.case.id)) { seen.add(t.case.id); mine.push({ t, place: part.place }); }
  }
  const item = ({ t, place }: { t: TurnOut; place: PlaceOut }): Item => ({ card: t.case, place, group: "you", since: t.turn.since || t.case.since,
    action: t.turn.blocked_by.length ? bare(t.turn.headline || t.turn.label, t.case.title) || t.turn.label : t.turn.label });
  const urgent = mine.filter(({ t }) => t.turn.kind === "date").map(item).sort(byAge);
  const blocked = mine.filter(({ t }) => t.turn.kind !== "date" && t.turn.blocked_by.length > 0).map(item).sort(byAge);
  const ready = mine.filter(({ t }) => t.turn.kind !== "date" && t.turn.blocked_by.length === 0).map(item).sort(byAge);
  const working: Item[] = parts.flatMap((part) => part.working.map((c) => ({ card: c, place: part.place, group: "claude", since: c.since, action: cap(c.turn?.reason || c.stage_word) })));
  const sealed = parts.flatMap((part) => (part.seals ?? []).map((x) => ({ ...x, place: part.place }))).sort((a, b) => a.at.localeCompare(b.at));   // today, across workspaces
  const next = [...urgent, ...ready, ...blocked][0];
  const n = mine.length;
  const openNext = () => next && open(next.place, `/case/${encodeURIComponent(next.card.id)}?g=you`);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (e.key !== "Enter" || e.metaKey || e.ctrlKey || e.altKey || ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(t.tagName) || t.getAttribute("role") === "link") return;
      if (next) { e.preventDefault(); openNext(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next?.place.id, next?.card.id]);                                        // eslint-disable-line react-hooks/exhaustive-deps

  if (home.isLoading) return <main className="home-wrap" />;
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
              <button type="button" className="primary" data-help="cf.next" onClick={openNext}>
                {w.openNext} <span className="k">⏎</span>
              </button>
            )}
          </div>
          <Section dot="urgent" title={w.urgent} rows={urgent} lang={lang} open={open} />
          <Section dot="you" title={w.ready} rows={ready} lang={lang} open={open} />
          <Section dot="quiet" title={w.waitingSomething} rows={blocked} lang={lang} open={open} />
          <Section dot="ai" title={w.aiWorking} rows={working} lang={lang} open={open} />
        </section>
        <aside className="home-side">
          {ai && (
            <div className="card aiw">
              <div className="aiw-k">✦ {w.aiCard}</div>
              <button type="button" className="aw" data-help-skip="explained by cf.groups" onClick={() => open(ai.place, `/case/${encodeURIComponent(ai.card.id)}?g=claude`)}>
                <span className="aw-k">{ai.action}</span>
                <span className="aw-t">{ai.card.title}</span>
                <span className="aw-m">{[ai.card.party || ai.card.label_word, ai.since ? ago(ai.since, lang) : ""].filter(Boolean).join(" · ")}</span>
                <span className="prog"><i /></span>
                <span className="aw-n">{w.aiCardNote}</span>
              </button>
            </div>
          )}
          <div className="card">
            <div className="card-k">{w.doneToday}</div>
            {sealed.length === 0 ? <p className="card-none">{w.doneNone}</p> : sealed.map((x) => (
              <button key={x.place.id + x.case + x.at} type="button" className="sealrow" data-help-skip="explained by cf.daydone" title={x.place.name} onClick={() => open(x.place, `/case/${encodeURIComponent(x.case)}`)}>
                <span className="seal-i"><Seal /></span>
                <span className="seal-t">{x.title}</span>
                <span className="seal-at">{x.at.slice(11, 16)}</span>
              </button>
            ))}
          </div>
          <button type="button" className="kbhint" data-help-skip="opens the keyboard shortcuts" onClick={openKeys}><span className="gd-ic kb" aria-hidden="true" />{w.keysTitle}<span className="kbd">?</span></button>
        </aside>
      </div>
    </main>
  );
}
