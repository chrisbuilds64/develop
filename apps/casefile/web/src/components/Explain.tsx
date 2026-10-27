// An explainer video at the place it explains: a chip with its length, the player over the page. The catalog is the
// application's videos.json; a place names itself by key ("canon", "outcome", "interview" …).
import { useEffect, useState } from "react";
import { BASE, type ConfigView } from "../api";
import { Close } from "./Icons";

export type Video = { key: string; where: string[]; title: string; url: string; poster: string; seconds: number };

export function Explain({ where, config }: { where: string; config: ConfigView }) {
  const videos = ((config as unknown as { videos?: Video[] }).videos ?? []).filter((v) => v.where.includes(where));
  const [open, setOpen] = useState<Video | null>(null);
  if (!videos.length) return null;
  const len = (s: number) => (s >= 60 ? `${Math.round(s / 60)} Min.` : `${s} s`);
  return (
    <>
      {videos.map((v) => (
        <button key={v.key} type="button" className="explain" data-help="cf.explain" onClick={() => setOpen(v)}>
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 1.8v10.4L12 7z" fill="currentColor" /></svg>
          <span>{v.title}</span>{v.seconds > 0 && <span className="explain-len">{len(v.seconds)}</span>}
        </button>
      ))}
      {open && <VideoStage video={open} onClose={() => setOpen(null)} />}
    </>
  );
}

/** The player over the page — at its place (Explain) or from the bar's support. */
export function VideoStage({ video, onClose }: { video: Video; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="explain-stage" role="dialog" aria-modal="true" aria-label={video.title} onClick={onClose}>
      <div className="explain-frame" onClick={(e) => e.stopPropagation()}>
        <video src={BASE + video.url} poster={video.poster ? BASE + video.poster : undefined} controls autoPlay playsInline />
        <button type="button" className="explain-close" aria-label="×" onClick={onClose}><Close /></button>
      </div>
    </div>
  );
}
