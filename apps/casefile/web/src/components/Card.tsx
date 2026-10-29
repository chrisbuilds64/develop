// The card: a case on the board and under a signal — the second views keep it (ADR-024); the stack itself shows rows, never cards.
import { type CaseCard } from "../api";
import { BASE } from "../api";
import { Cover } from "./Cover";
import { ago, type words } from "../words";

export function Card({ c, go, w, lang, quiet, on, from }: { c: CaseCard; go: (p: string) => void; w: ReturnType<typeof words>; lang: string; quiet?: boolean; on?: boolean; from?: string }) {
  const to = `/case/${encodeURIComponent(c.id)}${from ? `?g=${encodeURIComponent(from)}` : ""}`;
  const t = c.turn;
  const running = t?.actor === "claude";
  const state = t ? (c.mine ? c.stage_word : t.actor === "claude" ? `${t.reason}${c.since ? ` · ${w.since} ${ago(c.since, lang)}` : ""}` : `${c.stage_word}`) : c.stage_word;
  return (
    <a className={`card${c.mine ? " mine" : ""}${quiet ? " quiet" : ""}${on ? " on" : ""}`} aria-current={on ? "true" : undefined} href={`${BASE}${to}`} onClick={(e) => { e.preventDefault(); go(to); }}>
      <Cover label={c.label} number={c.number || c.id.split("-")[1] || ""} tint={c.tint} />
      <span className="card-body">
        {!quiet && <span className="ref">{c.label_word}</span>}
        <span className="num">{c.external_id || (c.number ? `${c.label}-${c.number}` : c.id)}</span>
        <span className="title">{c.title}</span>
        <span className="state">{state}</span>
        {c.mine && <span className="yours">{w.yourMove}</span>}
        {running && <span className="bar"><i /></span>}
      </span>
    </a>
  );
}
