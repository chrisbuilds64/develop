// A case's meta.json at one press, for every application: what the case says about itself (published when, where, from what).
// The attributes are the domain's own; their words come from the vocabulary's `meta` section, else the key stands as it is.
// Keys the domain names come first, in its order; the rest follows alphabetically. Read only: meta changes through steps.
import { useState } from "react";
import { createPortal } from "react-dom";
import { dateWords } from "../words";

const ISO = /^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?([+-]\d{2}:?\d{2}|Z)?)?$/;

function Value({ v, lang }: { v: unknown; lang: string }) {
  if (v === null || v === undefined || v === "") return <span className="meta-empty">—</span>;
  if (typeof v === "boolean") return <>{v ? "✓" : "—"}</>;
  if (typeof v === "string") {
    if (/^https?:\/\//.test(v)) return <a href={v} target="_blank" rel="noreferrer">{v}</a>;
    if (ISO.test(v)) return <span title={v}>{dateWords(v.slice(0, 10), lang)}{v.length > 10 ? ` · ${v.slice(11, 16)}` : ""}</span>;
    return <>{v}</>;
  }
  if (typeof v === "number") return <>{v}</>;
  if (Array.isArray(v) && v.every((x) => typeof x !== "object" || x === null)) return <>{v.join(", ")}</>;
  return <code className="meta-json">{JSON.stringify(v, null, 1)}</code>;
}

export function MetaSheet({ meta, words, lang, title, table }: { meta: Record<string, unknown>; words: Record<string, unknown>; lang: string; title: string; table: string }) {
  const [open, setOpen] = useState(false);
  const [raw, setRaw] = useState(false);
  const named = (words.meta ?? {}) as Record<string, string>;
  const keys = Object.keys(meta).filter((k) => !k.startsWith("$"));
  const order = [...Object.keys(named).filter((k) => keys.includes(k)), ...keys.filter((k) => !(k in named)).sort()];
  return (
    <>
      <button type="button" className="meta-open" data-meta="open" onClick={() => setOpen(true)}>{title} · {keys.length}</button>
      {open && createPortal(
        <div className="meta-sheet" role="dialog" aria-label={title} onClick={(e) => e.target === e.currentTarget && setOpen(false)}>
          <div className="meta-card">
            <header>
              <h2>{title}</h2>
              <button type="button" onClick={() => setRaw(!raw)}>{raw ? table : "meta.json"}</button>
              <button type="button" data-meta="close" aria-label="×" onClick={() => setOpen(false)}>×</button>
            </header>
            {raw ? <pre className="meta-raw">{JSON.stringify(meta, null, 2)}</pre> : (
              <dl>
                {order.map((k) => (
                  <div key={k} className="meta-row"><dt title={k}>{named[k] || k}</dt><dd><Value v={meta[k]} lang={lang} /></dd></div>
                ))}
              </dl>
            )}
          </div>
        </div>, document.body                       // above the bar: the case's own layers would hold it below
      )}
    </>
  );
}
