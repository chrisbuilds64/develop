// What is missing, as a line: a dashed circle, the word, who owes it — and, when the viewer may deliver it, the place to drop
// or choose the file. Three forms (ADR-024, step 2): "button" — the drop is the viewer's move, the line carries the one filled
// button; "zone" — the viewer may deliver, a dashed line with a quiet button; "compact" — somebody else owes it, one line with
// a small link to put it in oneself. Tap or drop: the file becomes the next version, nothing is overwritten.
import { useRef, useState } from "react";
import type { SlotView } from "../api";
import type { words } from "../words";
import { Arrow, Miss, You } from "./Icons";

export type DropMode = "button" | "zone" | "compact";

export function DropLine({ slot, mode, who, detail, onFile, w, busy, sample, onSample }:
  { slot: SlotView; mode: DropMode; who: string; detail?: string; onFile: (f: File) => void; w: ReturnType<typeof words>; busy: boolean; sample?: boolean; onSample?: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const accept = slot.shape.startsWith("image") ? "image/*" : slot.shape.startsWith("video") ? "video/*" : slot.shape === "pdf" ? "application/pdf" : undefined;
  const agent = !who || who === w.originUnknown || who === w.whoDelivers ? "ne" : "";
  const mine = mode === "button";
  return (
    <li className={`fehlt${mine ? " du" : ""}${mode === "compact" ? " kompakt" : ""}${over ? " over" : ""}`} data-slot={slot.file}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}>
      <span className="zust">{mine ? <You /> : <Miss />}<span className="sr">{w.missingPos}{mine ? ` · ${w.waitingForYou}` : ""}</span></span>
      <span className="was">
        <b>{slot.word}</b>
        <span className="meta"><span className="v">{slot.file}</span>{slot.required ? ` · ${w.requiredWord}` : ""}</span>
        <span className={`wer ${agent}`}>{who || w.whoDelivers}</span>
        {mode === "compact" && <button type="button" className="link selbst" disabled={busy} onClick={() => input.current?.click()}>{w.selfDrop}</button>}
      </span>
      {detail && <span className="detail">{detail}</span>}
      {mode !== "compact" && (
        <span className="drop">
          <button type="button" className="droptext" disabled={busy} onClick={() => input.current?.click()}>{over ? w.dropHere : `${slot.word} · ${w.dropHere}`}</button>
          <span className="dropacts">
            {sample && onSample && <button type="button" className="link" disabled={busy} onClick={onSample}>{w.sample(slot.word)}</button>}
            {mine
              ? <button type="button" className="btn" disabled={busy} data-drop={slot.file} onClick={() => input.current?.click()}>{w.dropVerb(slot.word)} <Arrow /></button>
              : <button type="button" className="btn still klein" disabled={busy} data-drop={slot.file} onClick={() => input.current?.click()}>{w.chooseFile}</button>}
          </span>
        </span>
      )}
      <input ref={input} type="file" accept={accept} hidden aria-label={`${slot.word} · ${w.dropHere}`} onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
    </li>
  );
}
