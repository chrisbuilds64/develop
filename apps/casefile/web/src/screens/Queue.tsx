// The queue beside a case (design hand-back, 2026-11-05): three tabs over the workspace's groups — for you, with others
// (the AI, other people, a date, planned), done (out and the archive) — and one quiet row per case: the blue dot for new
// to you, the title, who it is from, how long it has waited, and a line while the AI reads.
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type CaseCard, type GroupOut } from "../api";
import { ago, type words } from "../words";

export type Tab = "you" | "others" | "done";
const OTHERS = ["claude", "others", "date", "planned", "ideas"];
const DONE = ["out", "archive"];

export function tabOf(key: string | undefined): Tab {
  if (!key || key === "you") return "you";
  return DONE.includes(key) ? "done" : OTHERS.includes(key) ? "others" : key === "done" ? "done" : "others";
}

export function casesOf(groups: GroupOut[] | undefined, tab: Tab): CaseCard[] {
  const keys = tab === "you" ? ["you"] : tab === "done" ? DONE : OTHERS;
  const seen = new Set<string>();
  return (groups ?? []).filter((g) => keys.includes(g.key)).flatMap((g) => g.cases).filter((c) => !seen.has(c.id) && !!seen.add(c.id));
}

function short(iso: string, lang: string): string {
  return ago(iso, lang).replace(/ (Min\.|min)$/, "m").replace(/ (Std\.|h)$/, "h").replace(/ Tage?n?$| days?$/, "d");
}

export function Queue({ tab, openId, go, w, lang, place, views, onMenu }: { tab: Tab; openId?: string; go: (p: string) => void; w: ReturnType<typeof words>; lang: string;
  place: string; views?: ReactNode; onMenu?: () => void }) {
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const color = me.data?.places?.find((p) => p.current)?.color;
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const n = (t: Tab) => casesOf(groups.data, t).length;
  const list = casesOf(groups.data, tab);
  const open = (c: CaseCard) => go(`/case/${encodeURIComponent(c.id)}?g=${tab}`);
  return (
    <section className="queue" aria-label={w.yourMove} data-help="cf.list">
      <div className="q-bar">
        <button type="button" className="bar-menu" data-help-skip="opens the rail on a phone" aria-label={w.menu} onClick={onMenu}>☰</button>
        <button type="button" className="q-crumb" data-help-skip="explained by cf.groups" onClick={() => go("/")}>{w.home}</button>
        <span className="q-sep">/</span>
        <span className="q-place"><span className="sq" style={{ background: color || undefined }} />{place}</span>
        {views}
      </div>
      <div className="q-tabs" role="tablist">
        {(["you", "others", "done"] as Tab[]).map((t) => (
          <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? "on" : ""} onClick={() => go(`/group/${t}`)}>
            {t === "you" ? w.forYou : t === "others" ? w.withOthers : w.doneTab}<span className="sc">{n(t) || ""}</span>
          </button>
        ))}
      </div>
      <div className="q-list">
        {!groups.data ? null : list.length === 0 ? <p className="q-empty">{tab === "you" ? w.nothing : "—"}</p> : list.map((c) => {
          const working = c.turn?.actor === "claude";
          return (
            <a key={c.id} className={`q${c.id === openId ? " on" : ""}`} href={`?`} aria-current={c.id === openId ? "true" : undefined}
               onClick={(e) => { e.preventDefault(); open(c); }}>
              {c.unread && <i className="q-dot" aria-label={w.isNew} />}
              <span className="qtop"><span className="qt">{c.title}</span><span className="qa">{c.since ? short(c.since, lang) : ""}</span></span>
              <span className="qn">{c.party || c.external_id || c.label_word}</span>
              {working && <span className="qp q-working">{c.turn?.reason}</span>}
              {tab === "others" && !working && c.turn && <span className="qp">{c.stage_word}</span>}
            </a>
          );
        })}
      </div>
    </section>
  );
}
