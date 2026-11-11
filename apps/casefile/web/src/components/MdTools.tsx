// The Markdown toolbar of the editors (REQ-001 S-15): bold, italic, heading, list, checklist, link, code over a textarea.
// Shared by the editor over a file and the editor of a new case (S-18). No editor library: insertText, so the browser's
// own undo keeps working.
import type { RefObject } from "react";
import type { words } from "../words";

type W = ReturnType<typeof words>;
export const mac = /Mac|iPhone|iPad/.test(navigator.platform);
export type Tool = [string, string, () => void];

export function mdTools(area: RefObject<HTMLTextAreaElement | null>, setText: (t: string) => void, w: W) {
  // Replace the selection the way typing would: the browser's undo stack keeps it, and React hears the input event.
  const replace = (s: number, e: number, insert: string, selFrom: number, selTo: number) => {
    const a = area.current;
    if (!a) return;
    a.focus();
    a.setSelectionRange(s, e);
    if (!document.execCommand("insertText", false, insert)) setText(a.value.slice(0, s) + insert + a.value.slice(e));
    requestAnimationFrame(() => a.setSelectionRange(selFrom, selTo));
  };
  const insert = (text: string) => {
    const a = area.current; if (!a) return;
    const s = a.selectionStart, e = a.selectionEnd;
    replace(s, e, text, s + text.length, s + text.length);
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
  const mod = mac ? "⌘" : "Ctrl ";
  const tools: Tool[] = [
    ["B", `${w.edBold} · ${mod}B`, () => wrap("**", "**", w.edBold.toLowerCase())],
    ["I", `${w.edItalic} · ${mod}I`, () => wrap("_", "_", w.edItalic.toLowerCase())],
    ["H", w.edHeading, () => lines("## ")],
    ["•", w.edList, () => lines("- ")],
    ["☐", w.edCheck, () => lines("- [ ] ")],
    ["↗", `${w.edLink} · ${mod}K`, link],
    ["</>", w.edCode, code],
  ];
  return { insert, wrap, link, tools, mod };
}

export function MdToolbar({ tools, w }: { tools: Tool[]; w: W }) {
  return (
    <div className="ed-tools" role="toolbar" aria-label={w.edEdit}>
      {tools.map(([label, title, act]) => (
        <button key={title} type="button" className="ed-tool" title={title} aria-label={title} onMouseDown={(e) => e.preventDefault()} onClick={act}>{label}</button>
      ))}
    </div>
  );
}
