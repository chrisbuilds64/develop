// The value lists (SYS-105): every list the domain keeps, its entries with colour, key, name, description, status and how
// many cases carry them. Nothing here knows a particular list: which lists exist, the field each fills and whether a new
// case asks for it come from lists.json. Whoever runs the place (role operator) adds lists and entries and changes a
// status, in forms on the page; everyone else reads. An entry's colour appears only as its swatch.
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, stepId, ApiError, type ConfigView, type ListView } from "../api";
import type { words } from "../words";

type W = ReturnType<typeof words>;
const STATUSES = ["planned", "active", "retired"] as const;

function Status({ s, w, bare }: { s: string; w: W; bare?: boolean }) {
  // the shape carries the state as much as the word: a ring planned, a disc active, a struck ring retired
  return (
    <span className={`entry-status ${s}`}>
      <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
        <circle cx="7" cy="7" r="5" fill={s === "active" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.6" />
        {s === "retired" && <path d="M2.5 11.5l9-9" stroke="currentColor" strokeWidth="1.6" />}
      </svg>
      {!bare && w.entryStatus(s)}
    </span>
  );
}

export function Swatch({ color, label }: { color: string; label: string }) {
  return color ? <span className="swatch" style={{ background: color }} title={color} aria-label={`${label} ${color}`} role="img" />
    : <span className="swatch none" aria-label={label} role="img" />;
}

function errorOf(e: unknown): string {
  return e instanceof ApiError ? e.message : String((e as Error)?.message ?? e);
}

function EntryForm({ list, w, done }: { list: ListView; w: W; done: () => void }) {
  const [key, setKey] = useState("");
  const [de, setDe] = useState("");
  const [en, setEn] = useState("");
  const [withColor, setWithColor] = useState(list.entries.some((e) => e.color));
  const [color, setColor] = useState("#5a6270");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("active");
  const [error, setError] = useState<string | null>(null);
  const id = `ef-${list.id}`;
  return (
    <form className="list-form" data-help="cf.lists-entry" onSubmit={async (e) => {
      e.preventDefault();
      try {
        await api.putEntry(list.id, { key: key.trim(), word: { de: de.trim(), en: en.trim() }, ...(withColor ? { color } : {}),
                                      ...(description.trim() ? { description: description.trim() } : {}), status, step_id: stepId("list") });
        done();
      } catch (err) { setError(errorOf(err)); }
    }}>
      <label htmlFor={`${id}-key`}>{w.colKey}<input id={`${id}-key`} className="mono" value={key} maxLength={16} required autoFocus
        onChange={(e) => setKey(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))} /></label>
      <label htmlFor={`${id}-de`}>{w.nameDe}<input id={`${id}-de`} value={de} maxLength={80} required onChange={(e) => setDe(e.target.value)} /></label>
      <label htmlFor={`${id}-en`}>{w.nameEn}<input id={`${id}-en`} value={en} maxLength={80} required onChange={(e) => setEn(e.target.value)} /></label>
      <label className="color-field">
        <span><input type="checkbox" checked={withColor} onChange={(e) => setWithColor(e.target.checked)} /> {w.colColor}</span>
        <input type="color" value={color} disabled={!withColor} onChange={(e) => setColor(e.target.value)} aria-label={w.colColor} />
      </label>
      <label htmlFor={`${id}-desc`} className="wide">{w.colDescription}<input id={`${id}-desc`} value={description} maxLength={300} onChange={(e) => setDescription(e.target.value)} /></label>
      <label htmlFor={`${id}-status`}>{w.colStatus}
        <select id={`${id}-status`} value={status} onChange={(e) => setStatus(e.target.value)}>{STATUSES.map((s) => <option key={s} value={s}>{w.entryStatus(s)}</option>)}</select>
      </label>
      <div className="list-form-do">
        <button type="submit" className="btn small" disabled={!key || !de.trim() || !en.trim()}>{w.save}</button>
        <button type="button" className="btn link small" onClick={done}>{w.cancel}</button>
      </div>
      {error && <p className="talk-error" role="alert">{error}</p>}
    </form>
  );
}

function ListForm({ w, done }: { w: W; done: () => void }) {
  const [id, setId] = useState("");
  const [de, setDe] = useState("");
  const [en, setEn] = useState("");
  const [field, setField] = useState("");
  const [ask, setAsk] = useState(true);
  const [error, setError] = useState<string | null>(null);
  return (
    <form className="list-form" data-help="cf.lists-new" onSubmit={async (e) => {
      e.preventDefault();
      try { await api.putList({ id: id.trim(), word: { de: de.trim(), en: en.trim() }, field: field.trim() || id.trim(), on_create: ask, step_id: stepId("list") }); done(); }
      catch (err) { setError(errorOf(err)); }
    }}>
      <label htmlFor="lf-id">{w.listId}<input id="lf-id" className="mono" value={id} maxLength={32} required autoFocus
        onChange={(e) => { const v = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""); if (field === id) setField(v); setId(v); }} /></label>
      <label htmlFor="lf-de">{w.nameDe}<input id="lf-de" value={de} maxLength={80} required onChange={(e) => setDe(e.target.value)} /></label>
      <label htmlFor="lf-en">{w.nameEn}<input id="lf-en" value={en} maxLength={80} required onChange={(e) => setEn(e.target.value)} /></label>
      <label htmlFor="lf-field">{w.listFieldLabel}<input id="lf-field" className="mono" value={field} maxLength={40} onChange={(e) => setField(e.target.value.replace(/[^A-Za-z0-9_]/g, ""))} /></label>
      <label className="check"><input type="checkbox" checked={ask} onChange={(e) => setAsk(e.target.checked)} /> {w.askOnCreate}</label>
      <div className="list-form-do">
        <button type="submit" className="btn small" disabled={!id || !de.trim() || !en.trim()}>{w.save}</button>
        <button type="button" className="btn link small" onClick={done}>{w.cancel}</button>
      </div>
      {error && <p className="talk-error" role="alert">{error}</p>}
    </form>
  );
}

export function Lists({ config, w }: { config: ConfigView; w: W }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["lists"], queryFn: api.lists, refetchInterval: false });
  const [adding, setAdding] = useState<string | null>(null);          // the list whose entry form is open, or "" for a new list
  const [error, setError] = useState<string | null>(null);
  const refresh = () => { setAdding(null); qc.invalidateQueries({ queryKey: ["lists"] }); qc.invalidateQueries({ queryKey: ["config"] }); qc.invalidateQueries({ queryKey: ["groups"] }); };
  if (!q.data) return <main className="main view-rules view-lists"><p className="empty">…</p></main>;
  const { lists, may_edit } = q.data;
  const setStatus = async (list: string, key: string, status: string) => {
    try { setError(null); await api.putEntry(list, { key, status, step_id: stepId("list") }); refresh(); } catch (err) { setError(errorOf(err)); }
  };
  return (
    <main className="main view-rules view-lists">
      <header className="view-head">
        <h1>{w.lists}</h1>
        <span className="hint">{config.product} · {w.listsHint}</span>
      </header>
      <div className="rules-scroll">
        {!may_edit && <p className="hint">{w.listsReadOnly}</p>}
        {may_edit && (adding === "" ? <section className="rules-block"><p className="kicker">{w.addList}</p><ListForm w={w} done={refresh} /></section>
          : <div><button type="button" className="btn ghost small" onClick={() => setAdding("")}>+ {w.addList}</button></div>)}
        {error && <p className="talk-error" role="alert">{error}</p>}
        {lists.length === 0 && <p className="empty">{w.listsEmpty}</p>}
        {lists.map((l) => (
          <section key={l.id} className="rules-block" aria-labelledby={`list-${l.id}`}>
            <div className="list-head">
              <h2 id={`list-${l.id}`}>{l.word}</h2>
              <span className="hint"><span className="mono">{l.id}</span> · {w.listField(l.field)} · {l.on_create ? w.listAsks : w.listAsksNot}</span>
              {may_edit && adding !== l.id && <button type="button" className="btn ghost small" onClick={() => setAdding(l.id)}>+ {w.addEntry}</button>}
            </div>
            {adding === l.id && <EntryForm list={l} w={w} done={refresh} />}
            {l.entries.length === 0 ? <p className="empty">{w.listEmpty}</p> : (
              <div className="table-scroll">
                <table className="rules-table list-table">
                  <thead><tr><th>{w.colColor}</th><th>{w.colKey}</th><th>{w.colName}</th><th className="desc">{w.colDescription}</th><th>{w.colStatus}</th><th className="n">{w.colCases}</th></tr></thead>
                  <tbody>
                    {l.entries.map((e) => (
                      <tr key={e.key} className={e.status === "retired" ? "retired" : ""}>
                        <td><Swatch color={e.color} label={e.color ? w.colColor : w.noColor} /></td>
                        <td className="mono">{e.key}</td>
                        <td><b>{e.word}</b></td>
                        <td className="desc">{e.description || "—"}</td>
                        <td>{may_edit ? (
                          <label className="status-pick"><Status s={e.status} w={w} bare />
                            <select value={e.status} aria-label={`${w.setStatus}: ${e.key}`} onChange={(ev) => setStatus(l.id, e.key, ev.target.value)}>
                              {STATUSES.map((s) => <option key={s} value={s}>{w.entryStatus(s)}</option>)}
                            </select>
                          </label>) : <Status s={e.status} w={w} />}</td>
                        <td className="n">{e.cases}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        ))}
      </div>
    </main>
  );
}
