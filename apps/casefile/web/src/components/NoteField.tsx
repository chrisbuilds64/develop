// The note field at the foot of a case and the large editor it opens (REQ-001 S-09): a click or ⌘J opens it, Enter is a
// new line, ⌘Enter sends, Esc closes and keeps the draft. A task or an idea does not fit in one line. The draft is kept
// per case in local storage, so switching cases does not mix drafts and a reload does not lose one. Every application's
// case screen uses this one component.
import { useEffect, useRef, useState } from "react";
import { BASE } from "../api";
import { Send } from "./Icons";
import type { words } from "../words";

type W = ReturnType<typeof words>;

const mac = /Mac|iPhone|iPad/.test(navigator.platform);
const slot = (caseId: string) => `cf.note:${BASE}:${caseId}`;
const load = (caseId: string) => { try { return localStorage.getItem(slot(caseId)) ?? ""; } catch { return ""; } };
const keep = (caseId: string, text: string) => {
  try { if (text) localStorage.setItem(slot(caseId), text); else localStorage.removeItem(slot(caseId)); } catch { /* storage off: the draft lives until the page is left */ }
};

/** What ⌘J and the top bar's ask button do on a case screen. */
export const openNote = () => window.dispatchEvent(new CustomEvent("cf:note"));

export function NoteField({ caseId, chip, onChip, placeholder, busy, onSend, w }: {
  caseId: string; chip?: string; onChip: () => void; placeholder: string; busy: boolean; onSend: (text: string) => Promise<unknown>; w: W;
}) {
  const [draft, setDraft] = useState(() => load(caseId));
  const [open, setOpen] = useState(false);
  const area = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { setDraft(load(caseId)); setOpen(false); }, [caseId]);
  useEffect(() => { const on = () => setOpen(true); window.addEventListener("cf:note", on); return () => window.removeEventListener("cf:note", on); }, []);
  useEffect(() => { if (open) { const a = area.current; if (a) { a.focus(); a.setSelectionRange(a.value.length, a.value.length); } } }, [open]);

  const current = useRef(caseId);
  current.current = caseId;
  const latest = useRef(draft);
  latest.current = draft;
  const write = (text: string) => { setDraft(text); keep(caseId, text); };
  // the draft goes only once the send went through: a refused note stays to be corrected, a draft written meanwhile stays
  const send = () => {
    const text = draft.trim(), sent = draft, id = caseId;
    if (!text || busy) return;
    setOpen(false);
    onSend(text).then(() => {
      const here = current.current === id;
      if ((here ? latest.current : load(id)) !== sent) return;
      keep(id, "");
      if (here) setDraft("");
    }, () => undefined);
  };
  const mod = mac ? "⌘" : "Ctrl ";

  return (
    <>
      <div className="i-ask">
        <span className="ask-i">✦</span>
        {chip && <button type="button" className="ask-chip" onClick={onChip}>{chip} ×</button>}
        <button type="button" className={`ask-open${draft.trim() ? " has" : ""}`} aria-label={placeholder} onClick={() => setOpen(true)}>{draft.trim() ? draft.trim().split("\n")[0] : placeholder}</button>
        {draft.trim() ? <button type="button" className="ask-send" disabled={busy} aria-label={w.noteSend} onClick={send}><Send /></button> : <span className="kbd">{mac ? "⌘J" : "Ctrl J"}</span>}
      </div>
      {open && (
        <div className="nf-scrim" role="presentation" onClick={() => setOpen(false)}>
          <div className="nf-sheet" role="dialog" aria-modal="true" aria-label={w.noteTitle} onClick={(e) => e.stopPropagation()}>
            <div className="nf-head"><span className="ask-i">✦</span><b>{w.noteTitle}</b>{chip && <button type="button" className="ask-chip" onClick={onChip}>{chip} ×</button>}</div>
            <textarea ref={area} value={draft} placeholder={placeholder} rows={12} onChange={(e) => write(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); setOpen(false); }   // not the case screen's Esc: that goes to the desk
                        else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); e.stopPropagation(); send(); }
                      }} />
            <div className="nf-foot">
              <span className="nf-hint">{w.noteHint(mod)}</span>
              <button type="button" className="primary" disabled={!draft.trim() || busy} onClick={send}>{w.noteSend} <span className="k">{mod}⏎</span></button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
