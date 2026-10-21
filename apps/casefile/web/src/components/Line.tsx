// Where the case stands: a line with stations, the marker glides to the next one after a step.
export function Line({ stations, mine, label }: { stations: { key: string; word: string; state: string }[]; mine: boolean; label: string }) {
  const cur = Math.max(0, stations.findIndex((s) => s.state === "current"));
  const n = Math.max(1, stations.length - 1);
  const pct = (cur / n) * 100;
  return (
    <div className="line" aria-label={label} role="img">
      <div className="rail" />
      <div className="done" style={{ width: `${pct}%` }} />
      {stations.map((s, i) => (
        <div key={s.key} className={`st ${s.state}`} style={{ left: `${(i / n) * 100}%` }}>
          <i />
          <span>{s.word}</span>
        </div>
      ))}
      <div className={`marker${mine ? " mine" : ""}`} style={{ left: `${pct}%` }} />
    </div>
  );
}
