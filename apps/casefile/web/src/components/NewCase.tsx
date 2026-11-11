// A new case (REQ-001 S-18, SW-2026-007): one visible button in the bar of every application that says how a case starts
// (`theme.create`), for the roles it names, worded by the application (vocabulary `texts.new_case`). It opens one editor —
// the same from the bar and from the rail: a title, the value lists a new case asks for, a Markdown description with the
// editors' toolbar and a preview, and files dropped or pasted (⌘V). An image becomes `![](name)` at the cursor and shows in
// the preview as it will in the thread. The case is made in the application the person is in — nothing picks another —
// and opens; what it offers first is the application's (`theme.create.next`).
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, createCase, stepId, type ConfigView, type MeOut } from "../api";
import { Close } from "./Icons";
import { Md } from "./Md";
import { mdTools, MdToolbar } from "./MdTools";
import { paper } from "../moments";
import type { words } from "../words";

type W = ReturnType<typeof words>;
type Create = { label?: string; roles?: string[]; meta?: Record<string, unknown> };

const OPEN = "cf:new-case";
export const openNewCase = () => window.dispatchEvent(new CustomEvent(OPEN));

/** How a case starts here, when this person may start one; else null. A mail inbox starts cases from mail instead. */
export function createSpec(config: ConfigView, me: MeOut): Create | null {
  const theme = config.theme as { create?: Create; mail_drop?: boolean };
  if (!theme.create || theme.mail_drop) return null;
  return (theme.create.roles ?? []).some((r) => me.roles.includes(r)) ? theme.create : null;
}

/** The application's word for a new case, without the "+" the generic word carries. */
export const newCaseWord = (config: ConfigView, w: W) =>
  (config.words as { texts?: Record<string, string> }).texts?.new_case || w.newCaseShort.replace(/^\+\s*/, "");

export function NewCaseButton({ config, me, w }: { config: ConfigView; me: MeOut; w: W }) {
  if (!createSpec(config, me)) return null;
  const word = newCaseWord(config, w);
  return (
    <button type="button" className="nc-open" data-help="cf.new-case" onClick={openNewCase} title={word} aria-label={word}>
      <span aria-hidden="true">+</span><span className="tx">{word}</span>
    </button>
  );
}

// the same rule as the core's (domain/assets.py free_name): what the case will call the file
const FREE = ["png", "jpg", "jpeg", "webp", "gif", "pdf", "txt", "md", "mp4", "mov", "webm"];
const EXT: Record<string, string> = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif", "application/pdf": "pdf" };
function nameFor(f: File, taken: string[]): string | null {
  const base = (f.name || "").split(/[\\/]/).pop() ?? "";
  const dot = base.lastIndexOf(".");
  let stem = dot > -1 ? base.slice(0, dot) : base;
  const ext = (dot > -1 ? base.slice(dot + 1) : EXT[f.type] ?? "").toLowerCase();
  if (!FREE.includes(ext)) return null;
  if (!stem || /^image$/i.test(stem)) stem = "screenshot";                 // what a browser calls a pasted picture
  stem = stem.replace(/[^A-Za-z0-9_-]+/g, "-").replace(/^[-_]+|[-_]+$/g, "").slice(0, 60) || "file";
  let name = `${stem}.${ext}`;
  for (let n = 2; taken.includes(name); n++) name = `${stem}-${n}.${ext}`;
  return name;
}
const isImage = (name: string) => /\.(png|jpe?g|webp|gif)$/i.test(name);

export function NewCase({ config, me, w, go }: { config: ConfigView; me: MeOut; w: W; go: (p: string) => void }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const on = () => setOpen(true);
    window.addEventListener(OPEN, on);
    return () => window.removeEventListener(OPEN, on);
  }, []);
  const spec = createSpec(config, me);
  if (!open || !spec) return null;
  return <Sheet config={config} spec={spec} w={w} onClose={() => setOpen(false)} onMade={(id) => { setOpen(false); paper(); go(`/case/${encodeURIComponent(id)}`); }} />;
}

function Sheet({ config, spec, w, onClose, onMade }: { config: ConfigView; spec: Create; w: W; onClose: () => void; onMade: (id: string) => void }) {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [files, setFiles] = useState<{ file: File; url: string }[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [pane, setPane] = useState<"write" | "preview">("write");
  const [asking, setAsking] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step] = useState(() => stepId("new"));                         // one request, however often it is sent
  const area = useRef<HTMLTextAreaElement>(null);
  const titleRef = useRef<HTMLInputElement>(null);
  const { insert, wrap, link, tools, mod } = mdTools(area, setText, w);
  const word = newCaseWord(config, w);
  const asks = (config.lists ?? []).filter((l) => l.on_create && l.entries.some((e) => e.status !== "retired"));
  const defaults: Record<string, string> = { ...Object.fromEntries(Object.entries(spec.meta ?? {}).map(([k, v]) => [k, String(v)])), ...(spec.label ? { label: spec.label } : {}) };
  const urls = useMemo(() => Object.fromEntries(files.map((f) => [f.file.name, f.url])), [files]);
  const dirty = !!(title.trim() || text.trim() || files.length);

  useLayoutEffect(() => { titleRef.current?.focus(); }, []);
  const kept = useRef(files);
  kept.current = files;
  useEffect(() => () => kept.current.forEach((f) => URL.revokeObjectURL(f.url)), []);

  const attach = (list: FileList | File[] | null | undefined, refer: boolean) => {
    const add: { file: File; url: string }[] = [];
    const taken = files.map((f) => f.file.name);
    let refused: string | null = null;
    for (const f of Array.from(list ?? [])) {
      const name = nameFor(f, [...taken, ...add.map((a) => a.file.name)]);
      if (!name) { refused = f.name || f.type; continue; }
      const file = new File([f], name, { type: f.type });
      add.push({ file, url: URL.createObjectURL(file) });
    }
    setError(refused ? w.ncRefused(refused) : null);
    if (!add.length) return;
    setFiles([...files, ...add]);
    const refs = add.filter((a) => isImage(a.file.name)).map((a) => `![](${a.file.name})`);
    if (refer && refs.length) insert(refs.join("\n") + "\n");
  };
  const remove = (name: string) => {
    const f = files.find((x) => x.file.name === name);
    if (f) URL.revokeObjectURL(f.url);
    setFiles(files.filter((x) => x.file.name !== name));
  };

  const make = async () => {
    if (!title.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      const r = await createCase({ title: title.trim(), step_id: step, values, description: text }, files.map((f) => f.file));
      qc.invalidateQueries({ queryKey: ["groups"] });
      onMade(r.id);
    } catch (e) {
      setBusy(false);
      setError(e instanceof ApiError ? e.message : String(e));
    }
  };
  const leave = () => { if (dirty) setAsking(true); else onClose(); };

  // While the sheet is open every key is its own (as in the editor over a file): nothing behind it hears it.
  const keys = useRef({ make, leave, wrap, link, asking });
  keys.current = { make, leave, wrap, link, asking };
  useLayoutEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      e.stopPropagation();
      const k = keys.current, m = e.metaKey || e.ctrlKey;
      if (e.key === "Escape") { e.preventDefault(); if (k.asking) setAsking(false); else k.leave(); return; }
      if (!m || e.altKey) return;
      const key = e.key.toLowerCase();
      if (key === "enter") { e.preventDefault(); k.make(); return; }
      if (document.activeElement !== area.current) { if (key === "k" || key === "j") e.preventDefault(); return; }
      if (key === "b") { e.preventDefault(); k.wrap("**", "**", w.edBold.toLowerCase()); }
      else if (key === "i") { e.preventDefault(); k.wrap("_", "_", w.edItalic.toLowerCase()); }
      else if (key === "k") { e.preventDefault(); k.link(); }
      else if (key === "j") e.preventDefault();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [w]);

  return (
    <div className="nf-scrim" role="presentation" onClick={leave}>
      <div className={`nf-sheet ed-sheet nc-sheet${dragging ? " dragging" : ""}`} role="dialog" aria-modal="true" aria-label={word} data-help="cf.new-case"
           onClick={(e) => e.stopPropagation()}
           onPaste={(e) => { if (e.clipboardData.files.length) { e.preventDefault(); attach(e.clipboardData.files, true); } }}
           onDragOver={(e) => { if (e.dataTransfer.types.includes("Files")) { e.preventDefault(); setDragging(true); } }}
           onDragLeave={(e) => { if (e.currentTarget === e.target) setDragging(false); }}
           onDrop={(e) => { if (e.dataTransfer.files.length) { e.preventDefault(); setDragging(false); attach(e.dataTransfer.files, true); } }}>
        <div className="nf-head">
          <b>{word}</b>
          <span className="ed-panes" role="tablist">
            <button type="button" role="tab" aria-selected={pane === "write"} className={`chip small${pane === "write" ? " on" : ""}`} onClick={() => setPane("write")}>{w.edWrite}</button>
            <button type="button" role="tab" aria-selected={pane === "preview"} className={`chip small${pane === "preview" ? " on" : ""}`} onClick={() => setPane("preview")}>{w.edPreview}</button>
          </span>
          <button type="button" className="swap ed-close" onClick={leave} aria-label={w.close} title={`${w.close} · Esc`}><Close /></button>
        </div>
        <div className="nc-fields">
          <input ref={titleRef} className="nc-title" value={title} maxLength={120} placeholder={w.ncTitlePh} aria-label={w.ncTitlePh} onChange={(e) => setTitle(e.target.value)} />
          {asks.map((l) => (
            <label key={l.id} className="nc-list"><span>{l.word}</span>
              <select value={values[l.field] ?? defaults[l.field] ?? ""} onChange={(e) => setValues({ ...values, [l.field]: e.target.value })}>
                {!defaults[l.field] && <option value="">{w.pick}</option>}
                {l.entries.filter((x) => x.status !== "retired").map((x) => <option key={x.key} value={x.key}>{x.word}{x.status === "planned" ? ` · ${w.entryStatus("planned")}` : ""}</option>)}
              </select>
            </label>
          ))}
        </div>
        <MdToolbar tools={tools} w={w} />
        <div className={`ed-body show-${pane}`}>
          <div className="ed-write">
            <textarea ref={area} value={text} spellCheck placeholder={w.ncDescPh} aria-label={w.edWrite} onChange={(e) => setText(e.target.value)} />
          </div>
          <div className="ed-preview reader-body" aria-label={w.edPreview}>
            {text.trim() ? <Md text={text} img={(n) => urls[n]} /> : <p className="hint">{w.ncDescPh}</p>}
          </div>
        </div>
        <div className="nc-files">
          {files.map((f) => (
            <span key={f.file.name} className="nc-file">
              {isImage(f.file.name) && <img src={f.url} alt="" />}
              <span className="mono">{f.file.name}</span>
              <button type="button" aria-label={w.ncRemove(f.file.name)} title={w.ncRemove(f.file.name)} onClick={() => remove(f.file.name)}><Close /></button>
            </span>
          ))}
          <label className="nc-attach">{w.ncAttach}
            <input type="file" multiple hidden accept={FREE.map((x) => `.${x}`).join(",")} onChange={(e) => { attach(e.target.files, true); e.target.value = ""; }} />
          </label>
        </div>
        {dragging && <div className="nc-drop" aria-hidden="true">{w.ncDrop}</div>}
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
            <span className={`nf-hint${error ? " nc-error" : ""}`} role={error ? "alert" : undefined}>{error ?? w.ncHint(mod)}</span>
            <button type="button" className="primary nc-make" disabled={!title.trim() || busy} onClick={make}>{w.create} <span className="k">{mod}↵</span></button>
          </div>
        )}
      </div>
    </div>
  );
}
