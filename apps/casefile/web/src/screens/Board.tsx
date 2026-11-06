// The board and the table (design hand-back, 2026-11-06): the two wide views on the same folders, under the workspace's own
// bar (Home / the workspace, the view switch, and on the table a filter). The board: a column per stage, a quiet card per
// case (title, who it is from, whose move, how long). The table: number, case, customer, stage, status, age. A click opens
// the case in the list beside it.
import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type CaseCard, type ConfigView, type MeOut } from "../api";
import { short } from "./Queue";
import type { words } from "../words";

type W = ReturnType<typeof words>;

/** Whose move it is, in the words of the design: for you, with someone, the AI, or where it ended up. */
export function statusOf(c: CaseCard, config: ConfigView, w: W): { text: string; you: boolean } {
  const actor = c.turn?.actor ?? "";
  if (c.turn && c.mine) return { text: w.forYou, you: true };
  if (actor === "claude") return { text: w.aiReading, you: false };
  if (c.turn && actor) {
    const name = actor.startsWith("role:") ? (((config.words as { roles?: Record<string, string> }).roles?.[actor.slice(5)]) ?? actor.slice(5))
      : (config.people.find((p) => p.id === actor)?.name ?? actor);
    return { text: w.withName(name), you: false };
  }
  return { text: c.group_word || c.stage_word, you: false };
}

export function WideBar({ me, w, go, views, children }: { me?: MeOut; w: W; go: (p: string) => void; views?: ReactNode; children?: ReactNode }) {
  const here = me?.places?.find((p) => p.current);
  return (
    <div className="q-bar wide-bar">
      <span className="wide-l">
        <button type="button" className="q-crumb" data-help-skip="explained by cf.groups" onClick={() => go("/")}>{w.home}</button>
        <span className="q-sep">/</span>
        <span className="q-place"><span className="sq" style={{ background: here?.color || undefined }} />{here?.name}</span>
        <span className="wide-views">{views}</span>
      </span>
      {children}
    </div>
  );
}

export function Board({ config, go, w, views }: { config: ConfigView; go: (p: string) => void; w: W; views?: ReactNode }) {
  const stages = useQuery({ queryKey: ["stages"], queryFn: api.stages, refetchInterval: 25_000 });
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const lang = config.lang;
  return (
    <main className="main view-board wide" data-help="cf.views">
      <WideBar me={me.data} w={w} go={go} views={views} />
      <div className="wb-board">
        {(stages.data ?? []).map((s, _i, all) => {
          const shared = !!s.station && all.filter((x) => x.station === s.station).length > 1;
          const head = shared ? s.word : (s.station || s.word);
          return (
            <section key={s.folder} className="wb-col" aria-label={head}>
              <div className="wb-ch"><span>{head}</span><em>{s.cases.length || ""}</em></div>
              {s.cases.length === 0 ? <div className="wb-empty">{w.nothingHere}</div> : s.cases.map((c) => {
                const st = statusOf(c, config, w);
                const done = !c.turn;
                return (
                  <button key={c.id} type="button" className={`wb-card${done ? " fade" : ""}`} data-help-skip="opens the case" onClick={() => go(`/case/${encodeURIComponent(c.id)}`)}>
                    <b>{c.unread && c.mine && <span className="wb-dot" aria-label={w.isNew} />}{c.title}</b>
                    {(c.party || c.external_id) && <span className="wb-m">{c.party || c.external_id}</span>}
                    <span className="wb-f"><span className={`wb-w${st.you ? " you" : ""}`}>{st.text}</span><span>{c.since ? short(c.since, lang) : ""}</span></span>
                  </button>
                );
              })}
            </section>
          );
        })}
      </div>
    </main>
  );
}

export function Table({ config, go, w, views }: { config: ConfigView; go: (p: string) => void; w: W; views?: ReactNode }) {
  const stages = useQuery({ queryKey: ["stages"], queryFn: api.stages, refetchInterval: 25_000 });
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const [q, setQ] = useState("");
  const lang = config.lang;
  const rows = (stages.data ?? []).flatMap((s) => s.cases.map((c) => ({ c, stage: s.station || s.word, st: statusOf(c, config, w) })));
  const needle = q.trim().toLowerCase();
  const shown = rows.filter(({ c, stage, st }) => !needle || [c.external_id, c.title, c.party, stage, st.text].join(" ").toLowerCase().includes(needle));
  return (
    <main className="main view-stack wide" data-help="cf.views">
      <WideBar me={me.data} w={w} go={go} views={views}>
        <input className="wb-filter" value={q} onChange={(e) => setQ(e.target.value)} placeholder={w.tblFilter} aria-label={w.filter} autoComplete="off" />
      </WideBar>
      <div className="wb-tblw">
        <table className="wb-tbl">
          <thead><tr><th>{w.colNumber}</th><th>{w.colCase}</th><th>{w.colCustomer}</th><th>{w.colStage}</th><th>{w.colStatus}</th><th className="ta">{w.colAge}</th></tr></thead>
          <tbody>
            {shown.map(({ c, stage, st }) => (
              <tr key={c.id} onClick={() => go(`/case/${encodeURIComponent(c.id)}`)} className={c.turn ? "" : "fade"}>
                <td className="tn">{c.external_id}</td>
                <td><b>{c.title}</b></td>
                <td>{c.party}</td>
                <td>{stage}</td>
                <td><span className={`wb-w${st.you ? " you" : ""}`}>{st.text}</span></td>
                <td className="ta">{c.since ? short(c.since, lang) : ""}</td>
              </tr>
            ))}
            {stages.data && shown.length === 0 && <tr><td colSpan={6} className="tnone">{w.noMatch(q)}</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
