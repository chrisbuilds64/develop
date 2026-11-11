// The case's conversation (design hand-back, 2026-11-05): one card per entry. The AI's are violet (actor "ai", request 5),
// yours sit to the right, an open question for you carries Answer and Done, a sealed decision shows its seal, and an
// undone or corrected decision says so (ADR-025). A decision you may correct offers "Open a correction".
import { Md } from "./Md";
import { useState } from "react";
import type { Entry } from "../api";
import { ago, type words } from "../words";
import { Send, Seal } from "./Icons";

type Props = {
  entries: Entry[]; meName: string; lang: string; w: ReturnType<typeof words>; busy: boolean; stageWord: (folder: string) => string;
  onAnswer: (e: Entry, text: string) => void; onDone: (e: Entry) => void; onFile: (name: string) => void; fileUrl: (name: string) => string;
  canCorrect: (e: Entry) => boolean; onCorrect: (e: Entry, text: string, amount: string) => void;
};

export function Conversation({ entries, meName, lang, w, busy, stageWord, onAnswer, onDone, onFile, fileUrl, canCorrect, onCorrect }: Props) {
  const resolved = new Set(entries.filter((e) => e.resolves).map((e) => e.resolves));
  const [answering, setAnswering] = useState<string | null>(null);
  const [correcting, setCorrecting] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [amount, setAmount] = useState("");
  if (entries.length === 0) return <p className="conv-empty">{w.threadEmpty}</p>;
  return (
    <>
      {entries.map((e) => {
        const mine = e.author === meName;
        const ai = e.actor === "ai";
        const open = e.status === "open" && e.for === meName && !resolved.has(e.id);
        const sealed = e.status === "approved";
        const undone = (e.corrected_by ?? []).some((id) => entries.find((x) => x.id === id)?.status === "undone");
        const corrected = (e.corrected_by ?? []).some((id) => entries.find((x) => x.id === id)?.status === "correction");
        const cls = ["msg", ai ? "ai" : "", mine ? "mine" : "", open ? "oq" : "", sealed ? "sealed" : "", e.status === "undone" || e.status === "correction" ? "note" : "", undone ? "gone" : ""].filter(Boolean).join(" ");
        return (
          <div key={e.id} className={cls}>
            <div className="mh">
              {sealed && <i className="m-seal"><Seal /></i>}
              <b>{ai ? `✦ ${e.author}` : mine ? w.you : e.author}</b>
              <span>{[e.for && !mine && !open ? `→ ${e.for}` : "", open ? w.youOnIt : "", ago(e.date, lang)].filter(Boolean).join(" · ")}</span>
            </div>
            {e.title && e.title !== e.text && <p className="m-title">{e.title}{undone ? ` · ${w.undoneWord}` : corrected ? ` · ${w.corrected}` : ""}</p>}
            {e.text && <Md text={e.text} img={(n) => (e.files?.includes(n) ? fileUrl(n) : undefined)} />}
            {(e.amount || e.to) && <p className="m-fact">{[e.amount, e.to ? `→ ${stageWord(e.to)}` : ""].filter(Boolean).join(" · ")}</p>}
            {e.files && e.files.length > 0 && <span className="m-files">{e.files.map((f) => <button key={f} type="button" onClick={() => onFile(f)}>{f}</button>)}</span>}
            {open && answering !== e.id && (
              <span className="mq">
                <button type="button" className="mbtn" onClick={() => { setAnswering(e.id); setText(""); }}>{w.answer}</button>
                <button type="button" className="mbtn" disabled={busy} onClick={() => onDone(e)}>{w.done}</button>
              </span>
            )}
            {answering === e.id && (
              <form className="m-form" onSubmit={(ev) => { ev.preventDefault(); if (text.trim()) { onAnswer(e, text.trim()); setAnswering(null); setText(""); } }}>
                <input autoFocus value={text} onChange={(ev) => setText(ev.target.value)} placeholder={w.answer} />
                <button type="submit" disabled={busy} aria-label={w.answer}><Send /></button>
              </form>
            )}
            {!undone && canCorrect(e) && correcting !== e.id && (
              <button type="button" className="tlink" data-help="cf.correct" onClick={() => { setCorrecting(e.id); setText(""); setAmount(""); }}><u>{w.correct}</u></button>
            )}
            {correcting === e.id && (
              <form className="m-form col" onSubmit={(ev) => { ev.preventDefault(); if (text.trim()) { onCorrect(e, text.trim(), amount.trim()); setCorrecting(null); } }}>
                <input autoFocus value={text} onChange={(ev) => setText(ev.target.value)} placeholder={w.correctPh} />
                {e.amount && <input value={amount} onChange={(ev) => setAmount(ev.target.value)} placeholder={w.correctAmount} inputMode="decimal" />}
                <span className="mq"><button type="submit" className="mbtn" disabled={busy || !text.trim()}>{w.correctSend}</button>
                  <button type="button" className="mbtn" onClick={() => setCorrecting(null)}>{w.cancel}</button></span>
              </form>
            )}
          </div>
        );
      })}
    </>
  );
}
