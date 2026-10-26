// The end of a working day, Duolingo's lesson-complete: nothing waits for you, and what you brought through a gate today
// waits to be collected. One press: the day's seals stack up, each with its stamp, then the reward tone. Counted from the
// step journals, never invented; collected once a day, then it stays as a quiet line.
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { chime, thud } from "../moments";
import type { words } from "../words";

export function DayDone({ w, me }: { w: ReturnType<typeof words>; me: string }) {
  const r = useQuery({ queryKey: ["rhythm"], queryFn: api.rhythm, refetchInterval: 60_000 });
  const key = `cf.collected.${new Date().toISOString().slice(0, 10)}.${me}`;
  const [collected, setCollected] = useState(() => { try { return localStorage.getItem(key) === "1"; } catch { return false; } });
  const [playing, setPlaying] = useState(false);
  const d = r.data;
  if (!d) return null;
  const seals = d.today_seals;
  const collect = () => {
    setPlaying(true);
    seals.slice(0, 6).forEach((_, i) => thud(0.35 + i * 0.32));
    chime(0.5 + Math.min(seals.length, 6) * 0.32);
    try { localStorage.setItem(key, "1"); } catch { /* private window */ }
    setTimeout(() => setCollected(true), 400);
  };
  return (
    <div className="daydone" data-help="cf.daydone">
      {seals.length > 0 && !collected && !playing ? (
        <>
          <p className="daydone-lead">{w.dayLead(seals.length)}</p>
          <button type="button" className="btn seal collect" onClick={collect}>{w.collect}</button>
        </>
      ) : seals.length > 0 ? (
        <>
          <div className="seal-stack" aria-hidden={!playing}>
            {seals.slice(0, 6).map((s, i) => (
              <div key={i} className="seal-slip" style={{ animationDelay: playing ? `${0.35 + i * 0.32}s` : "0s" }}>
                <span className="slip-stamp" style={{ animationDelay: playing ? `${0.35 + i * 0.32}s` : "0s" }}>{w.sealed}</span>
                <b>{s.title}</b><small>{s.action}</small>
              </div>
            ))}
          </div>
          <p className="daydone-sum" style={{ animationDelay: playing ? `${0.6 + Math.min(seals.length, 6) * 0.32}s` : "0s" }}>{w.daySum(seals.length, d.today_steps)}</p>
        </>
      ) : null}
      {d.week_seals > 0 && <p className="week-line">{w.weekLine(d.week_seals)}</p>}
    </div>
  );
}
