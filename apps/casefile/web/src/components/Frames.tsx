// Empty frames in real shape. Tap or drop a file: it becomes the next version, nothing is overwritten.
import { useRef, useState } from "react";
import { BASE, type SlotView } from "../api";
import type { words } from "../words";

const SIZE: Record<string, [number, number]> = { "image-16x9": [208, 117], "image-4x5": [94, 117], image: [160, 117], "video-9x16": [66, 117], video: [160, 117], pdf: [124, 160], money: [200, 120], text: [170, 110] };

export function Frame({ slot, mine, onFile, w, busy, sample, onSample, onOpen }: { slot: SlotView; mine: boolean; onFile: (f: File) => void; w: ReturnType<typeof words>; busy: boolean; sample?: boolean; onSample?: () => void; onOpen?: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [wd, ht] = SIZE[slot.shape] ?? SIZE.text;
  const newest = slot.versions[slot.versions.length - 1];
  const accept = slot.shape.startsWith("image") ? "image/*" : slot.shape.startsWith("video") ? "video/*" : slot.shape === "pdf" ? "application/pdf" : undefined;
  const ratio = slot.shape.replace(/^(image|video)-/, "").replace("x", " : ");
  return (
    <div className="frame">
      <button type="button" className={`box${slot.present ? " filled" : ""}${mine && !slot.present ? " mine" : ""}${over ? " over" : ""}`}
              style={{ width: wd, height: ht }} disabled={busy}
              onClick={() => { if (slot.present && onOpen) onOpen(); else input.current?.click(); }}
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}
              aria-label={`${slot.word}${slot.present ? "" : ` · ${w.dropHere}`}`}>
        {slot.present && newest && slot.shape.startsWith("image") ? <img src={BASE + newest.url} alt="" /> :
         slot.present ? <span className="tick">✓ {slot.word}</span> :
         <>{/^(image|video)/.test(slot.shape) ? <span>{ratio}</span> : <span>{slot.word}</span>}<span style={{ fontSize: 12 }}>{over ? w.dropHere : slot.shape === "pdf" ? "PDF" : w.tapToAdd}</span></>}
      </button>
      <input ref={input} type="file" accept={accept} hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
      <span className="cap">{slot.word}{newest ? <small>{newest.name} · {w.version(Math.max(1, newest.version))}</small> : <small>{w.tapToAdd}</small>}</span>
      {sample && !slot.present && onSample && <button type="button" className="chip" disabled={busy} onClick={onSample}>{w.sample(slot.word)}</button>}
    </div>
  );
}
