// A document, read inside the case: text rendered, PDF embedded, image large. Chips above switch between the documents on the desk,
// ← → walk them, Escape returns to the desk. Every version of a document stays; small chips below the tabs leaf through them.
// "Pop out" opens the same reader as its own window, next to the case.
import { useEffect, useRef, useState } from "react";
import { BASE } from "../api";
import { Back, Close, Next, PopOut, Prev } from "./Icons";
import type { words } from "../words";

export type Version = { name: string; version: number; url: string };
export type Doc = { word: string; shape: string; versions: Version[] };   // versions oldest → newest

function kindOf(name: string) {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (["md", "txt", "json"].includes(ext)) return "text";
  if (ext === "pdf") return "pdf";
  if (["png", "jpg", "jpeg", "webp", "gif"].includes(ext)) return "image";
  if (["mp4", "mov", "webm"].includes(ext)) return "video";
  return "other";
}

export function Reader({ docs, index, caseId, onIndex, onClose, standalone, startAt, w }: {
  docs: Doc[]; index: number; caseId: string; onIndex: (i: number) => void; onClose: () => void; standalone?: boolean; startAt?: string; w: ReturnType<typeof words>;
}) {
  const doc = docs[index];
  const [vi, setVi] = useState(() => Math.max(0, doc ? (startAt ? doc.versions.findIndex((v) => v.name === startAt) : -1) : -1));
  const ver = doc ? doc.versions[Math.min(vi < 0 ? doc.versions.length - 1 : vi, doc.versions.length - 1)] : undefined;
  const kind = ver ? kindOf(ver.name) : "other";
  const [html, setHtml] = useState<string | null>(null);
  const tabs = useRef<HTMLDivElement>(null);
  useEffect(() => { tabs.current?.querySelector<HTMLElement>('[aria-selected="true"]')?.scrollIntoView({ block: "nearest", inline: "center" }); }, [index]);
  const prev = () => onIndex((index - 1 + docs.length) % docs.length);
  const next = () => onIndex((index + 1) % docs.length);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement | null)?.tagName === "INPUT") return;
      if (e.key === "ArrowLeft" && docs.length > 1) { e.preventDefault(); prev(); }
      if (e.key === "ArrowRight" && docs.length > 1) { e.preventDefault(); next(); }
      if (e.key === "Escape" && !standalone) { e.preventDefault(); onClose(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  useEffect(() => { setVi(-1); }, [index]);     // a new document opens on its newest version
  useEffect(() => {
    setHtml(null);
    if (!ver || kind !== "text") return;
    let alive = true;
    fetch(`${BASE}/api/cases/${encodeURIComponent(caseId)}/read/${encodeURIComponent(ver.name)}`, { credentials: "same-origin" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((j: { html: string }) => { if (alive) setHtml(j.html); })
      .catch(() => { if (alive) setHtml(`<p>${w.unreachable}</p>`); });
    return () => { alive = false; };
  }, [ver, caseId, kind, w.unreachable]);
  if (!doc || !ver) return null;
  const popOut = () => {
    const url = `${BASE}/doc/${encodeURIComponent(caseId)}/${encodeURIComponent(ver.name)}`;
    const win = window.open(url, `casefile-${caseId}`, "popup,width=880,height=1000");
    if (win) onClose(); else window.open(url, "_blank");
  };
  return (
    <section className={`reader${standalone ? " full" : ""}`} aria-label={doc.word}>
      <header className="reader-head">
        {!standalone && <button type="button" className="swap" onClick={onClose} aria-label={w.backToDesk} title={`${w.backToDesk} · Esc`}><Back /></button>}
        <div className="reader-tabs" role="tablist" ref={tabs}>
          {docs.map((d, i) => (
            <button key={d.word + i} type="button" role="tab" aria-selected={i === index} className={`chip${i === index ? " on" : ""}`} onClick={() => onIndex(i)}>{d.word}</button>
          ))}
        </div>
        <div className="reader-acts">
          {docs.length > 1 && <button type="button" className="swap" onClick={prev} aria-label={w.prev} title={`${w.prev} · ←`}><Prev /></button>}
          {docs.length > 1 && <button type="button" className="swap" onClick={next} aria-label={w.next} title={`${w.next} · →`}><Next /></button>}
          {!standalone && <button type="button" className="swap" onClick={popOut} aria-label={w.popOut} title={w.popOut}><PopOut /></button>}
          {standalone && <button type="button" className="swap" onClick={() => window.close()} aria-label={w.close} title={w.close}><Close /></button>}
        </div>
      </header>
      <p className="reader-meta hint">
        {doc.versions.length > 1 ? (
          <span className="versions" role="tablist" aria-label={w.versions}>
            {doc.versions.map((v, i) => <button key={v.name} type="button" role="tab" aria-selected={v === ver} className={`chip small${v === ver ? " on" : ""}`} onClick={() => setVi(i)}>{w.version(Math.max(1, v.version))}</button>)}
          </span>
        ) : <span className="mono">{w.version(Math.max(1, ver.version))}</span>}
        <span className="mono"> · {ver.name} · <a className="quiet" href={BASE + ver.url} target="_blank" rel="noreferrer">{w.openTab}</a></span>
      </p>
      <div className="reader-body">
        {kind === "image" && <img src={BASE + ver.url} alt={doc.word} />}
        {kind === "video" && <video src={BASE + ver.url} controls playsInline />}
        {kind === "pdf" && <iframe src={BASE + ver.url} title={doc.word} />}
        {kind === "text" && (html === null ? <p className="hint">…</p> : <article className="prose" dangerouslySetInnerHTML={{ __html: html }} />)}
        {kind === "other" && <p className="hint"><a href={BASE + ver.url} target="_blank" rel="noreferrer">{w.openTab}</a></p>}
      </div>
    </section>
  );
}
