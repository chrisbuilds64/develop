// A document over the case: text rendered, PDF embedded, image large. The person stays in the case. Escape or the × closes it.
import { useEffect, useRef, useState } from "react";
import { BASE } from "../api";
import { Close } from "./Icons";
import type { words } from "../words";

export type Doc = { name: string; word: string; version: number; url: string; shape: string };

export function Viewer({ doc, caseId, onClose, w }: { doc: Doc | null; caseId: string; onClose: () => void; w: ReturnType<typeof words> }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [html, setHtml] = useState<string | null>(null);
  const ext = doc?.name.split(".").pop()?.toLowerCase() ?? "";
  const isText = ["md", "txt", "json"].includes(ext);
  const isPdf = ext === "pdf";
  const isImage = ["png", "jpg", "jpeg", "webp", "gif"].includes(ext);
  const isVideo = ["mp4", "mov", "webm"].includes(ext);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (doc && !d.open) d.showModal();
    if (!doc && d.open) d.close();
  }, [doc]);
  useEffect(() => {
    setHtml(null);
    if (!doc || !isText) return;
    let alive = true;
    fetch(`${BASE}/api/cases/${encodeURIComponent(caseId)}/read/${encodeURIComponent(doc.name)}`, { credentials: "same-origin" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((j: { html: string }) => { if (alive) setHtml(j.html); })
      .catch(() => { if (alive) setHtml(`<p>${w.unreachable}</p>`); });
    return () => { alive = false; };
  }, [doc, caseId, isText, w.unreachable]);
  return (
    <dialog ref={ref} className="viewer" onClose={onClose} onClick={(e) => { if (e.target === ref.current) onClose(); }}>
      {doc && (
        <div className="viewer-in">
          <header className="viewer-head">
            <div>
              <b>{doc.word}</b>
              <span className="mono hint"> · {w.version(Math.max(1, doc.version))} · {doc.name}</span>
            </div>
            <div className="viewer-acts">
              <a className="quiet" href={BASE + doc.url} target="_blank" rel="noreferrer">{w.openTab}</a>
              <button type="button" className="swap" onClick={onClose} aria-label={w.close}><Close /></button>
            </div>
          </header>
          <div className="viewer-body">
            {isImage && <img src={BASE + doc.url} alt={doc.word} />}
            {isVideo && <video src={BASE + doc.url} controls playsInline />}
            {isPdf && <iframe src={BASE + doc.url} title={doc.word} />}
            {isText && (html === null ? <p className="hint">…</p> : <article className="prose" dangerouslySetInnerHTML={{ __html: html }} />)}
            {!isImage && !isVideo && !isPdf && !isText && <p className="hint"><a href={BASE + doc.url} target="_blank" rel="noreferrer">{w.openTab}</a></p>}
          </div>
        </div>
      )}
    </dialog>
  );
}
