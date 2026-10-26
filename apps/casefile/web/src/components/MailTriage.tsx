// A mail's reading, as a card on the desk: what the AI recognised, the data it found (with the words it found them in),
// the row of the rule matrix it proposes — and, once a person confirmed, what was done and where it now lives.
import { useQuery } from "@tanstack/react-query";
import { api, BASE } from "../api";
import type { words } from "../words";

type Reading = { kind?: string; rule?: string; urgency?: string; summary?: string; fields?: Record<string, string>; labels?: Record<string, string>; reasons?: string[]; confidence?: string };
type Done = { rule?: string; action?: string; case?: string; title?: string; url?: string; target_label?: string; note?: string; at?: string };

export function MailTriage({ data, w }: { data: Record<string, unknown>; w: ReturnType<typeof words> }) {
  const r = data["einordnung.json"] as Reading | undefined;
  const done = data["aktion.json"] as Done | undefined;
  const rules = useQuery({ queryKey: ["rules"], queryFn: api.rules, staleTime: 60_000 });
  if (!r) return null;
  const row = rules.data?.matrix?.find((m) => m.id === r.rule);
  const href = done?.url ? new URL(done.url, window.location.origin + BASE + "/").pathname : "";
  return (
    <div className={`triage${done ? " done" : ""}`} data-help="cf.triage">
      <div className="triage-head">
        <span className="triage-kind">{row?.word ?? r.kind}</span>
        {r.urgency && <span className={`triage-urgency ${r.urgency}`}>{w.urgency(r.urgency)}</span>}
      </div>
      {r.summary && <p className="triage-sum">{r.summary}</p>}
      {r.fields && Object.keys(r.fields).length > 0 && (
        <dl className="triage-fields">
          {Object.entries(r.fields).filter(([k, v]) => v && !k.endsWith("_short") && k !== "title").map(([k, v]) => (
            <div key={k}><dt>{r.labels?.[k] ?? k.replace(/_/g, " ")}</dt><dd>{v}</dd></div>
          ))}
        </dl>
      )}
      {!!r.reasons?.length && <ul className="triage-reasons">{r.reasons.slice(0, 3).map((x, i) => <li key={i}>{x}</li>)}</ul>}
      {done ? (
        <p className="triage-done">
          <span className="stampmark">{w.sealed}</span>
          {done.case ? <>{w.triageDone(done.target_label ?? "")} {href ? <a href={href}>{done.title ?? done.case}</a> : <b>{done.title ?? done.case}</b>}</> : w.triageFiled}
        </p>
      ) : row ? (
        <p className="triage-proposal"><span className="mono">{row.id}</span> {w.triagePropose} <b>{row.action_word}</b>{row.target_word ? ` · ${row.target_word}` : ""}{!row.connected && <em> · {w.notConnected}</em>}</p>
      ) : null}
    </div>
  );
}
