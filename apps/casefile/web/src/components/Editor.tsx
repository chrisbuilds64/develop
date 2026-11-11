// The editor over a text file of the case (REQ-001 S-14 – S-16): the note's sheet with a Markdown toolbar, ⌘B ⌘I ⌘K, and a
// preview from the reader's own renderer beside it (or behind a switch on a narrow screen). Saving writes the next version;
// the older ones stay. Esc with unsaved text asks first. In the file that carries the acceptance criteria, the lines the
// gate could not read are listed under the text with their line and reason, before anything is saved. No editor library:
// a textarea, and insertText so the browser's own undo keeps working. A new note (REQ-001 S-17) opens it empty, without a url.
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { api, ApiError, BASE, stepId, type PreviewOut } from "../api";
import { Close } from "./Icons";
import type { words } from "../words";

type W = ReturnType<typeof words>;
const mac = /Mac|iPhone|iPad/.test(navigator.platform);

export function Editor({ caseId, file, word, url, onClose, onSaved, w }: {
  caseId: string; file: string; word: string; url?: string; onClose: () => void; onSaved: (name: string) => void; w: W;   // no url: a new note, empty
}) {
  const [base, setBase] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<PreviewOut | null>(null);
  const [pane, setPane] = useState<"write" | "preview">("write");
  const [asking, setAsking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const area = useRef<HTMLTextAreaElement>(null);
  const dirty = base !== null && text !== base;

  useEffect(() => {
    if (!url) { setBase(""); setText(""); return; }
    let alive = true;
    fetch(BASE + url, { credentials: "same-origin" }).then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
      .then((t) => { if (alive) { setBase(t); setText(t); } })
      .catch(() => { if (alive) setError(w.unreachable); });
    return () => { alive = false; };
  }, [url, w.unreachable]);
  useLayoutEffect(() => { if (base !== null) { const a = area.current; if (a) { a.focus(); a.setSelectionRange(0, 0); } } }, [base]);
  // the preview follows the text a moment after typing stops: the reader's renderer, and the criteria the gate would refuse
  useEffect(() => {
    if (base === null) return;
    let alive = true;
    const t = setTimeout(() => { api.editPreview(caseId, file, text).then((p) => { if (alive) setPreview(p); }, () => undefined); }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [text, base, caseId, file]);

  // Replace the selection the way typing would: the browser's undo stack keeps it, and React hears the input event.
  const replace = (s: number, e: number, insert: string, selFrom: number, selTo: number) => {
    const a = area.current;
    if (!a) return;
    a.focus();
    a.setSelectionRange(s, e);
    if (!document.execCommand("insertText", false, insert)) setText(a.value.slice(0, s) + insert + a.value.slice(e));
    requestAnimationFrame(() => a.setSelectionRange(selFrom, selTo));
  };
  const wrap = (before: string, after: string, empty: string) => {
    const a = area.current; if (!a) return;
    const s = a.selectionStart, e = a.selectionEnd, sel = a.value.slice(s, e) || empty;
    replace(s, e, before + sel + after, s + before.length, s + before.length + sel.length);
  };
  const link = () => {
    const a = area.current; if (!a) return;
    const s = a.selectionStart, e = a.selectionEnd, sel = a.value.slice(s, e) || w.edLink, href = "https://";
    replace(s, e, `[${sel}](${href})`, s + sel.length + 3, s + sel.length + 3 + href.length);   // the address is selected, ready to be typed over
  };
  const lines = (prefix: string) => {
    const a = area.current; if (!a) return;
    const v = a.value, s0 = a.selectionStart, e0 = a.selectionEnd;
    const s = s0 > 0 ? v.lastIndexOf("\n", s0 - 1) + 1 : 0;                      // from the start of the first selected line
    const end = v.indexOf("\n", e0 > s0 && v[e0 - 1] === "\n" ? e0 - 1 : e0);    // to the end of the last (a selection ending on a line break stops before it)
    const e = end < 0 ? v.length : end;
    const out = v.slice(s, e).split("\n").map((l) => (l.startsWith(prefix) ? l : prefix + l)).join("\n");
    replace(s, e, out, s, s + out.length);
  };
  const code = () => {
    const a = area.current; if (!a) return;
    if (a.value.slice(a.selectionStart, a.selectionEnd).includes("\n")) wrap("```\n", "\n```", "");
    else wrap("`", "`", w.edCode.toLowerCase());
  };
  const jump = (line: number) => {
    const a = area.current; if (!a) return;
    const at = a.value.split("\n").slice(0, line - 1).reduce((n, l) => n + l.length + 1, 0);
    const len = (a.value.split("\n")[line - 1] ?? "").length;
    setPane("write");
    a.focus(); a.setSelectionRange(at, at + len);
  };

  const save = () => {
    if (!dirty || saving) return;
    setSaving(true); setError(null);
    api.editSave(caseId, file, text, stepId("edit")).then((r) => { setSaving(false); onSaved(r.name); },
      (e) => { setSaving(false); setError(e instanceof ApiError ? e.message : String(e)); });
  };
  const leave = () => { if (dirty) setAsking(true); else onClose(); };

  // While the editor is open every key is its own: nothing behind it — the reader's arrows and Esc, the case's ⌘J, the
  // command menu's ⌘K — hears it. A capture listener on window runs first and ends the event there; typing is the
  // browser's default action and goes on. ⌘K here means a link (AC-3).
  const keys = useRef({ save, leave, wrap, link, asking });
  keys.current = { save, leave, wrap, link, asking };
  useLayoutEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      e.stopPropagation();
      const k = keys.current, mod = e.metaKey || e.ctrlKey;
      if (e.key === "Escape") { e.preventDefault(); if (k.asking) setAsking(false); else k.leave(); return; }
      if (!mod || e.altKey) return;
      const key = e.key.toLowerCase();
      if (key === "b") { e.preventDefault(); k.wrap("**", "**", w.edBold.toLowerCase()); }
      else if (key === "i") { e.preventDefault(); k.wrap("_", "_", w.edItalic.toLowerCase()); }
      else if (key === "k") { e.preventDefault(); k.link(); }
      else if (key === "s") { e.preventDefault(); k.save(); }
      else if (key === "j") e.preventDefault();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [w]);

  const mod = mac ? "⌘" : "Ctrl ";
  const bad = preview?.unreadable ?? [];
  const tools: [string, string, () => void][] = [
    ["B", `${w.edBold} · ${mod}B`, () => wrap("**", "**", w.edBold.toLowerCase())],
    ["I", `${w.edItalic} · ${mod}I`, () => wrap("_", "_", w.edItalic.toLowerCase())],
    ["H", w.edHeading, () => lines("## ")],
    ["•", w.edList, () => lines("- ")],
    ["☐", w.edCheck, () => lines("- [ ] ")],
    ["↗", `${w.edLink} · ${mod}K`, link],
    ["</>", w.edCode, code],
  ];
  return (
    <div className="nf-scrim" role="presentation" onClick={leave}>
      <div className="nf-sheet ed-sheet" role="dialog" aria-modal="true" aria-label={w.edTitle(word)} onClick={(e) => e.stopPropagation()}>
        <div className="nf-head">
          <b>{w.edTitle(word)}</b><span className="mono ed-file">{file}</span>
          <span className="ed-panes" role="tablist">
            <button type="button" role="tab" aria-selected={pane === "write"} className={`chip small${pane === "write" ? " on" : ""}`} onClick={() => setPane("write")}>{w.edWrite}</button>
            <button type="button" role="tab" aria-selected={pane === "preview"} className={`chip small${pane === "preview" ? " on" : ""}`} onClick={() => setPane("preview")}>{w.edPreview}</button>
          </span>
          <button type="button" className="swap ed-close" onClick={leave} aria-label={w.close} title={`${w.close} · Esc`}><Close /></button>
        </div>
        <div className="ed-tools" role="toolbar" aria-label={w.edEdit}>
          {tools.map(([label, title, act]) => (
            <button key={title} type="button" className="ed-tool" title={title} aria-label={title} onMouseDown={(e) => e.preventDefault()} onClick={act}>{label}</button>
          ))}
        </div>
        <div className={`ed-body show-${pane}`}>
          <div className="ed-write">
            <textarea ref={area} value={text} disabled={base === null} spellCheck onChange={(e) => setText(e.target.value)} aria-label={w.edWrite} />
            {bad.length > 0 && (
              <div className="ed-bad" role="status">
                <b>{w.edBad(bad.length)}</b>
                {bad.map((b) => (
                  <button key={b.line} type="button" className="ed-bad-line" onClick={() => jump(b.line)}>
                    <span className="mono">{w.edLine(b.line)}</span> {b.reason}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="ed-preview reader-body" aria-label={w.edPreview}>
            {preview ? <article className="prose" dangerouslySetInnerHTML={{ __html: preview.html }} /> : <p className="hint">…</p>}
          </div>
        </div>
        {asking ? (
          <div className="nf-foot ed-ask" role="alertdialog" aria-label={w.edDiscardQ}>
            <span>{w.edDiscardQ}</span>
            <span className="ed-ask-acts">
              <button type="button" className="ghost" autoFocus onClick={() => setAsking(false)}>{w.edKeep}</button>
              <button type="button" className="ghost ed-discard" onClick={onClose}>{w.edDiscard}</button>
            </span>
          </div>
        ) : (
          <div className="nf-foot">
            <span className="nf-hint">{error ?? w.edHint(mod)}</span>
            <button type="button" className="primary" disabled={!dirty || saving} onClick={save}>{w.edSave} <span className="k">{mod}S</span></button>
          </div>
        )}
      </div>
    </div>
  );
}
