// What is missing, as a line: a dashed circle, the word, who owes it — and the place to drop or choose the file.
// Tap or drop: the file becomes the next version, nothing is overwritten. The line, not a tile (ADR-024, rule 3).
import { useRef, useState } from "react";
import type { SlotView } from "../api";
import type { words } from "../words";
import { Miss, You } from "./Icons";

export function DropLine({ slot, mine, who, detail, onFile, w, busy, sample, onSample }:
  { slot: SlotView; mine: boolean; who: string; detail?: string; onFile: (f: File) => void; w: ReturnType<typeof words>; busy: boolean; sample?: boolean; onSample?: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const accept = slot.shape.startsWith("image") ? "image/*" : slot.shape.startsWith("video") ? "video/*" : slot.shape === "pdf" ? "application/pdf" : undefined;
  const agent = !who || who === w.originUnknown || who === w.whoDelivers ? "ne" : "";
  return (
    <li className={`fehlt${mine ? " du" : ""}${over ? " over" : ""}`} data-slot={slot.file}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}>
      <span className="zust">{mine ? <You /> : <Miss />}<span className="sr">{w.missingPos}{mine ? ` · ${w.waitingForYou}` : ""}</span></span>
      <span className="was">
        <b>{slot.word}</b>
        <span className="meta"><span className="v">{slot.file}</span>{slot.required ? ` · ${w.requiredWord}` : ""}</span>
        <span className={`wer ${agent}`}>{who || w.whoDelivers}</span>
      </span>
      {detail && <span className="detail">{detail}</span>}
      <span className="drop">
        <button type="button" className="droptext" disabled={busy} onClick={() => input.current?.click()}>{over ? w.dropHere : `${slot.word} · ${w.dropHere}`}</button>
        <span className="dropacts">
          {sample && onSample && <button type="button" className="link" disabled={busy} onClick={onSample}>{w.sample(slot.word)}</button>}
          <button type="button" className="btn still klein" disabled={busy} onClick={() => input.current?.click()}>{w.chooseFile}</button>
        </span>
        <input ref={input} type="file" accept={accept} hidden aria-label={`${slot.word} · ${w.dropHere}`} onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
      </span>
    </li>
  );
}
