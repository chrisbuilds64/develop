// The stacked list: every case as one row, stacked by stage, dense — the third view. A filter box narrows it; a row opens the case.
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, BASE, type ConfigView } from "../api";
import { Cover } from "../components/Cover";
import { ago, dateWords, type words } from "../words";

export function Stacked({ config, go, w }: { config: ConfigView; go: (p: string) => void; w: ReturnType<typeof words> }) {
  const stages = useQuery({ queryKey: ["stages"], queryFn: api.stages, refetchInterval: 25_000 });
  const [q, setQ] = useState("");
  const lang = config.lang;
  const roleWord = (actor: string) => actor === "claude" ? (config.people.find((p) => p.kind === "agent")?.name ?? actor)
    : actor.startsWith("role:") ? (((config.words as { roles?: Record<string, string> }).roles?.[actor.slice(5)]) ?? actor.slice(5)) : (config.people.find((p) => p.id === actor)?.name ?? actor);
  const needle = q.trim().toLowerCase();
  const hit = (c: { id: string; title: string; external_id: string; label_word: string }) => !needle || [c.id, c.title, c.external_id, c.label_word].some((x) => x.toLowerCase().includes(needle));
  const total = (stages.data ?? []).reduce((n, s) => n + s.cases.filter(hit).length, 0);
  return (
    <main className="main view-stack">
      <header className="view-head">
        <h1>{w.stacked}</h1>
        <label className="filter"><span className="sr">{w.filter}</span><input value={q} onChange={(e) => setQ(e.target.value)} placeholder={w.filter} /></label>
        <span className="hint">{total} · {config.product}</span>
      </header>
      <div className="stack-scroll">
        <table className="stack">
          <thead><tr><th></th><th>{w.colNumber}</th><th>{w.colTitle}</th><th>{w.colTurn}</th><th>{w.colSince}</th><th>{w.colDate}</th></tr></thead>
          {(stages.data ?? []).map((s) => {
            const rows = s.cases.filter(hit);
            if (rows.length === 0) return null;
            return (
              <tbody key={s.folder}>
                <tr className="group"><th colSpan={6}><span>{s.word}</span><span className="n">{rows.length}</span></th></tr>
                {rows.map((c) => (
                  <tr key={c.id} className={c.mine ? "mine" : ""} onClick={() => go(`/case/${encodeURIComponent(c.id)}`)} tabIndex={0}
                      onKeyDown={(e) => { if (e.key === "Enter") go(`/case/${encodeURIComponent(c.id)}`); }}>
                    <td className="cv"><Cover label={c.label} number={c.number || c.id.split("-")[1] || ""} tint={c.tint} /></td>
                    <td className="num"><a href={`${BASE}/case/${encodeURIComponent(c.id)}`} onClick={(e) => e.preventDefault()}>{c.external_id || (c.number ? `${c.label}-${c.number}` : c.id)}</a><small>{c.label_word}</small></td>
                    <td className="ttl" title={c.title}>{c.title}</td>
                    <td className="turn">{c.turn ? <><b className={c.mine ? "you" : ""}>{c.mine ? w.yourMove : roleWord(c.turn.actor)}</b><small>{c.turn.label}</small></> : <span className="hint">—</span>}</td>
                    <td className="since">{c.since ? ago(c.since, lang) : ""}</td>
                    <td className="date">{c.date ? dateWords(c.date, lang) : ""}</td>
                  </tr>
                ))}
              </tbody>
            );
          })}
        </table>
      </div>
    </main>
  );
}
