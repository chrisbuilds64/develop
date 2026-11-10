// Two versions of a text document, line by line (SYS-162): what the newer one added, what it removed, and the unchanged
// stretches folded to a line of context on each side. A longest-common-subsequence diff — documents in a case are
// short; above a size where that gets slow, the two versions are shown one after the other instead.
import { useEffect, useState } from "react";
import { BASE } from "../api";
import type { words } from "../words";

type W = ReturnType<typeof words>;
type Line = { kind: "same" | "add" | "del"; text: string };
const LIMIT = 4_000_000;          // n × m cells of the table
const CONTEXT = 2;

export function diffLines(a: string[], b: string[]): Line[] | null {
  const n = a.length, m = b.length;
  if (n * m > LIMIT) return null;
  const t: Uint32Array[] = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) t[i][j] = a[i] === b[j] ? t[i + 1][j + 1] + 1 : Math.max(t[i + 1][j], t[i][j + 1]);
  const out: Line[] = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { out.push({ kind: "same", text: a[i] }); i++; j++; }
    else if (t[i + 1][j] >= t[i][j + 1]) out.push({ kind: "del", text: a[i++] });
    else out.push({ kind: "add", text: b[j++] });
  }
  while (i < n) out.push({ kind: "del", text: a[i++] });
  while (j < m) out.push({ kind: "add", text: b[j++] });
  return out;
}

type Row = Line | { kind: "fold"; count: number };

function folded(lines: Line[]): Row[] {
  const out: Row[] = [];
  let k = 0;
  while (k < lines.length) {
    if (lines[k].kind !== "same") { out.push(lines[k++]); continue; }
    let e = k;
    while (e < lines.length && lines[e].kind === "same") e++;
    const run = lines.slice(k, e), head = k === 0 ? 0 : CONTEXT, tail = e === lines.length ? 0 : CONTEXT;
    if (run.length > head + tail + 1) { out.push(...run.slice(0, head), { kind: "fold", count: run.length - head - tail }, ...run.slice(run.length - tail)); }
    else out.push(...run);
    k = e;
  }
  return out;
}

export function VersionDiff({ older, newer, w }: { older: { url: string; version: number }; newer: { url: string; version: number }; w: W }) {
  const [texts, setTexts] = useState<[string, string] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    setTexts(null); setFailed(false);
    Promise.all([older.url, newer.url].map((u) => fetch(BASE + u, { credentials: "same-origin" }).then((r) => (r.ok ? r.text() : Promise.reject(r.status)))))
      .then(([a, b]) => { if (alive) setTexts([a, b]); })
      .catch(() => { if (alive) setFailed(true); });
    return () => { alive = false; };
  }, [older.url, newer.url]);
  if (failed) return <p className="hint">{w.unreachable}</p>;
  if (!texts) return <p className="hint">…</p>;
  const lines = diffLines(texts[0].replace(/\r\n/g, "\n").split("\n"), texts[1].replace(/\r\n/g, "\n").split("\n"));
  if (!lines) return <p className="hint">{w.diffTooLong}</p>;
  const added = lines.filter((l) => l.kind === "add").length, removed = lines.filter((l) => l.kind === "del").length;
  return (
    <div className="diff" aria-label={w.diffTitle(older.version, newer.version)}>
      <p className="diff-sum">
        <b>{w.diffTitle(older.version, newer.version)}</b>
        {added + removed === 0 ? <span> · {w.diffSame}</span> : <><span className="diff-n add"> +{added}</span><span className="diff-n del"> −{removed}</span></>}
      </p>
      <pre className="diff-body">{folded(lines).map((r, i) => r.kind === "fold"
        ? <span key={i} className="diff-fold">{w.diffFolded(r.count)}</span>
        : <span key={i} className={`diff-line ${r.kind}`}><i aria-hidden="true">{r.kind === "add" ? "+" : r.kind === "del" ? "−" : " "}</i>{r.text || " "}</span>)}</pre>
    </div>
  );
}
