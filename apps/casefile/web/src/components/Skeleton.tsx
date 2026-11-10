// Placeholder rows while a list loads (SW-2026-003, REQ-001 S-13): each has the shape of the real row it stands for, so
// nothing jumps when the data arrives. They come only after a short wait — a fast load goes straight to the list — and
// the bars are hidden from screen readers; the busy region says "loading" once instead.
import { useEffect, useState } from "react";

// true once `on` has held for `ms`: placeholders for a slow load, nothing for a fast one
export function useLate(on: boolean, ms = 150): boolean {
  const [late, setLate] = useState(false);
  useEffect(() => {
    if (!on) { setLate(false); return; }
    const t = setTimeout(() => setLate(true), ms);
    return () => clearTimeout(t);
  }, [on, ms]);
  return on && late;
}

const Bar = ({ w }: { w: string }) => <i className="skel-bar" style={{ width: w }} />;

// the queue beside a case: title, age on the right, the party below (Queue.tsx `.q`)
const QUEUE = [["78%", "62%"], ["64%", "48%"], ["84%", "56%"], ["58%", "40%"], ["72%", "52%"]];
export function QueueSkeleton() {
  return (
    <>
      {QUEUE.map(([title, party], i) => (
        <div key={i} className="q skel" aria-hidden="true">
          <span className="qtop"><span className="qt"><Bar w={title} /></span><span className="qa"><Bar w="22px" /></span></span>
          <span className="qn"><Bar w={party} /></span>
        </div>
      ))}
    </>
  );
}

// Home: the headline, one group's caption and three rows (Home.tsx `Row`)
const HOME = [["70%", "64%", "60px"], ["56%", "72%", "84px"], ["82%", "50%", "70px"]];
export function HomeSkeleton() {
  return (
    <>
      <div className="home-head" aria-hidden="true"><div><h1 className="h1"><Bar w="320px" /></h1></div></div>
      <div className="grph skel" aria-hidden="true"><Bar w="120px" /></div>
      <div className="rgrp" aria-hidden="true">
        {HOME.map(([party, title, action], i) => (
          <div key={i} className="row skel">
            <span className="sq" />
            <span className="r-party"><Bar w={party} /></span>
            <span className="r-title"><Bar w={title} /></span>
            <span className="r-action"><Bar w={action} /></span>
            <span className="r-age"><Bar w="22px" /></span>
            <span />
          </div>
        ))}
      </div>
    </>
  );
}
