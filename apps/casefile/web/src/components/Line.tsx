// Where the case stands: a line with stations, the marker glides to the next one after a step — and clicks past each
// station it crosses (the sound of progress, moments.ts).
import { useEffect, useRef } from "react";
import { tick } from "../moments";

export function Line({ stations, mine, label, caseId }: { stations: { key: string; word: string; state: string }[]; mine: boolean; label: string; caseId?: string }) {
  const cur = Math.max(0, stations.findIndex((s) => s.state === "current"));
  const n = Math.max(1, stations.length - 1);
  const pct = (cur / n) * 100;
  const prev = useRef<{ id?: string; cur: number } | null>(null);
  useEffect(() => {
    const p = prev.current;
    if (p && p.id === caseId && cur > p.cur) for (let i = 0; i < cur - p.cur; i++) tick(0.12 + i * 0.11);
    prev.current = { id: caseId, cur };
  }, [cur, caseId]);
  return (
    <div className="line" aria-label={label} role="img">
      <div className="rail" />
      <div className="fill" style={{ width: `calc((100% - 2 * var(--line-pad, 0px)) * ${pct / 100})` }} />
      {stations.map((s, i) => (
        <div key={s.key} className={`st ${s.state}`} style={{ left: `calc(var(--line-pad, 0px) + (100% - 2 * var(--line-pad, 0px)) * ${i / n})` }}>
          <i />
          <span>{s.word}</span>
        </div>
      ))}
      <div className={`here${mine ? " mine" : ""}`} style={{ left: `calc(var(--line-pad, 0px) + (100% - 2 * var(--line-pad, 0px)) * ${pct / 100})` }} />
    </div>
  );
}
