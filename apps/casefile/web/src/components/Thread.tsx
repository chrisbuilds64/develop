// The conversation: the thread as speech bubbles, the agent and others on the left, you on the right, a stamp when something was approved.
import { useState } from "react";
import type { Entry } from "../api";
import { ago, type words } from "../words";
import { Send } from "./Icons";

export function Thread({ entries, meName, agentName, lang, w, onAnswer, onDone, busy, stageWord }:
  { entries: Entry[]; meName: string; agentName: string; lang: string; w: ReturnType<typeof words>; onAnswer: (e: Entry, text: string) => void; onDone: (e: Entry) => void; busy: boolean; stageWord: (folder: string) => string }) {
  const resolved = new Set(entries.filter((e) => e.resolves).map((e) => e.resolves));
  const [answering, setAnswering] = useState<string | null>(null);
  const [text, setText] = useState("");
  return (
    <>
      {entries.map((e) => {
        const you = e.author === meName;
        const openForMe = e.status === "open" && e.for === meName && !resolved.has(e.id);
        if (e.status === "approved") {
          return (
            <div key={e.id} className="stamp">
              <b>{e.title.toUpperCase()} · {e.author.toUpperCase()} · {ago(e.date, lang).toUpperCase()}</b>
              {e.to && <span>{w.moved} → {stageWord(e.to)}</span>}
            </div>
          );
        }
        return (
          <div key={e.id} className={`bubble${you ? " you" : ""}${openForMe ? " open" : ""}`}>
            <span className="who"><b>{you ? w.you : e.author}</b> · {ago(e.date, lang)}{e.for && !you ? ` → ${e.for}` : ""}</span>
            <span className="text">{e.title && e.title !== e.text ? <b>{e.title}</b> : null}{e.title && e.title !== e.text ? "\n" : ""}{e.text}</span>
            {e.files && e.files.length > 0 && <span className="chips">{e.files.map((f) => <span key={f}>{f}</span>)}</span>}
            {openForMe && answering !== e.id && (
              <span className="acts">
                <button type="button" className="chip" onClick={() => { setAnswering(e.id); setText(""); }}>{w.answer}</button>
                <button type="button" className="chip" disabled={busy} onClick={() => onDone(e)}>{w.done}</button>
              </span>
            )}
            {answering === e.id && (
              <form className="ask" style={{ marginTop: 6 }} onSubmit={(ev) => { ev.preventDefault(); if (text.trim()) { onAnswer(e, text.trim()); setAnswering(null); setText(""); } }}>
                <input autoFocus value={text} onChange={(ev) => setText(ev.target.value)} placeholder={w.answer} />
                <button type="submit" className="send" disabled={busy} aria-label={w.answer}><Send /></button>
              </form>
            )}
          </div>
        );
      })}
      {entries.length === 0 && <p className="empty" aria-label={agentName}></p>}
    </>
  );
}
