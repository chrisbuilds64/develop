// A helper at work, as far as anybody can know (REQ-001 W-08): the phases its skill declares, the one it reached, what it
// does this second and just did, and how long such a run usually takes. Nothing here is guessed from a clock alone: a phase
// fills when the runner saw a tool call of its kind; without declared phases the bar follows the usual duration and stops
// short of the end until the run is really done.
import { useEffect, useState } from "react";
import type { CaseView } from "../api";
import type { words } from "../words";

type W = ReturnType<typeof words>;
type Helper = NonNullable<CaseView["helper"]>;

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export function RunProgress({ h, agent, w }: { h: Helper; agent: string; w: W }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(t); }, []);
  const from = Date.parse(h.started || h.created || "");
  const elapsed = Number.isFinite(from) ? Math.max(0, (now - from) / 1000) : 0;
  const queued = h.status === "queued";
  const usual = h.expected_s ? Math.max(1, Math.round(h.expected_s / 60)) : 0;
  const share = h.expected_s ? Math.min(elapsed / h.expected_s, 0.95) : 0;
  const phases = h.phases ?? [];
  const phase = h.phase ?? -1;
  const steps = h.steps ?? 0;
  const earlier = (h.recent ?? []).filter((x) => x !== h.now).slice(-3).reverse();
  return (
    <div className="rp" role="status" aria-live="polite" data-help="cf.run-progress">
      <div className="rp-head">
        <span className="rp-who"><span aria-hidden="true">✦</span> {agent} · {h.skill_word}</span>
        <span className="rp-time">
          {queued ? w.rpQueued : mmss(elapsed)}
          {usual > 0 && !queued && <span className="rp-usual"> · {w.rpUsual(usual)}</span>}
        </span>
      </div>
      {phases.length > 0 ? (
        <ol className="rp-phases" aria-label={w.rpPhases}>
          {phases.map((p, i) => {
            const state = queued ? "" : i < phase ? "done" : i === phase || (phase < 0 && i === 0) ? "now" : "";
            return (
              <li key={p.key} className={state} aria-current={state === "now" ? "step" : undefined}>
                <span className="rp-bar"><i /></span>
                <span className="rp-word">{p.word}</span>
              </li>
            );
          })}
        </ol>
      ) : (
        <div className={`rp-single${queued ? " waiting" : ""}`}><i style={{ width: `${Math.round(share * 100)}%` }} /></div>
      )}
      <p className="rp-now" key={h.now || "start"}>{queued ? w.rpQueuedHint : h.now ? <code>{h.now}</code> : w.isWorking(agent)}</p>
      {earlier.length > 0 && (
        <ul className="rp-recent">{earlier.map((x, i) => <li key={`${i}-${x}`}><code>{x}</code></li>)}</ul>
      )}
      {steps > 0 && <p className="rp-steps">{w.rpSteps(steps)}</p>}
    </div>
  );
}
