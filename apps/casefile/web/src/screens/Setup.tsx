// Setup (design hand-back, 2026-11-06): what this workspace is built from, in six tabs: the cockpit's plugins, where new
// cases come from, the workspaces, the roles and who holds them, the kinds of case and what each collects, and the value
// lists. Everything is read from the configuration (GET /api/setup); only the lists are edited here, as before (SYS-105).
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, stepId, ApiError, type MeOut, type SetupItem } from "../api";
import { EntryForm, Status, STATUSES } from "./Lists";
import type { words } from "../words";

type W = ReturnType<typeof words>;
export type SetupTab = "plugins" | "sources" | "modules" | "roles" | "schemas" | "lists";
export const SETUP_TABS: SetupTab[] = ["plugins", "sources", "modules", "roles", "schemas", "lists"];

function Rows({ items, open, setOpen, fallback, empty }: { items: SetupItem[]; open: string | null; setOpen: (k: string | null) => void; fallback: string; empty: string }) {
  if (!items.length) return <p className="su-empty">{empty}</p>;
  return (
    <>
      {items.map((it) => {
        const o = open === it.id;
        return (
          <button key={it.id} type="button" className={`su-row${o ? " open" : ""}`} aria-expanded={o} data-help-skip="opens the details" onClick={() => setOpen(o ? null : it.id)}>
            <span className="su-n">
              <b>{it.name}</b>
              {o && <span className="su-t">{it.text || fallback}</span>}
              {o && it.items && it.items.length > 0 && <span className="su-items">{it.items.map((x) => <i key={x}>{x}</i>)}</span>}
            </span>
            <span className="su-side">{it.side}</span>
            <span className="su-go" aria-hidden="true">{o ? "⌄" : "›"}</span>
          </button>
        );
      })}
    </>
  );
}

function ListsTab({ w }: { w: W }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["lists"], queryFn: api.lists, refetchInterval: false });
  const [adding, setAdding] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);            // "<list>/<key>": the entry whose details are open
  const [error, setError] = useState<string | null>(null);
  const refresh = () => { setAdding(null); qc.invalidateQueries({ queryKey: ["lists"] }); qc.invalidateQueries({ queryKey: ["config"] }); qc.invalidateQueries({ queryKey: ["groups"] }); };
  if (!q.data) return null;
  const { lists, may_edit } = q.data;
  const setStatus = async (list: string, key: string, status: string) => {
    try { setError(null); await api.putEntry(list, { key, status, step_id: stepId("list") }); refresh(); }
    catch (err) { setError(err instanceof ApiError ? err.message : String(err)); }
  };
  if (!lists.length) return <p className="su-empty">{w.listsEmpty}</p>;
  return (
    <>
      {error && <p className="rb-err" role="alert">{error}</p>}
      {lists.map((l) => {
        const pick = l.entries.find((e) => picked === `${l.id}/${e.key}`);
        return (
          <section key={l.id} className="su-card su-list" aria-label={l.word} data-help="cf.lists">
            <h3>{l.word}</h3>
            <div className="su-lents">
              {l.entries.map((e) => (
                <button key={e.key} type="button" className={`su-lent${e.status === "retired" ? " retired" : ""}${pick === e ? " on" : ""}`} data-help-skip="shows the entry"
                        onClick={() => setPicked(pick === e ? null : `${l.id}/${e.key}`)}>
                  <i style={{ background: e.color || undefined }} className={e.color ? "" : "none"} />{e.word}
                </button>
              ))}
              {may_edit && adding !== l.id && <button type="button" className="su-lent su-add" data-help="cf.lists-entry" onClick={() => { setAdding(l.id); setPicked(null); }}>{w.suAdd}</button>}
            </div>
            {pick && (
              <div className="su-pick">
                <span className="su-key">{pick.key}</span>
                {pick.description && <span className="su-desc">{pick.description}</span>}
                <span className="su-cases">{w.suInCases(pick.cases)}</span>
                {may_edit ? (
                  <label className="status-pick"><Status s={pick.status} w={w} bare />
                    <select value={pick.status} aria-label={`${w.setStatus}: ${pick.key}`} onChange={(ev) => setStatus(l.id, pick.key, ev.target.value)}>
                      {STATUSES.map((s) => <option key={s} value={s}>{w.entryStatus(s)}</option>)}
                    </select>
                  </label>
                ) : <Status s={pick.status} w={w} />}
              </div>
            )}
            {adding === l.id && <div className="su-form"><EntryForm list={l} w={w} done={refresh} /><button type="button" className="btn link small" onClick={() => setAdding(null)}>{w.cancel}</button></div>}
          </section>
        );
      })}
    </>
  );
}

export function Setup({ me, tab, go, w }: { me: MeOut; tab: SetupTab; go: (p: string) => void; w: W }) {
  const q = useQuery({ queryKey: ["setup", me.lang, me.world], queryFn: api.setup });
  const [open, setOpen] = useState<string | null>(null);
  const label: Record<SetupTab, string> = { plugins: w.suPlugins, sources: w.suSources, modules: w.suModules, roles: w.suRoles, schemas: w.suSchemas, lists: w.suLists };
  const modules: SetupItem[] = (me.places ?? []).map((p) => ({ id: p.id, name: p.name, side: p.current ? w.suHere : (p.count ? w.suCases(p.count) : ""), text: "", items: [] }));
  const d = q.data;
  return (
    <main className="main view-setup rb" data-help="cf.setup">
      <div className="rb-page">
        <header className="tm-head su-head">
          <div>
            <h1>{w.setup}</h1>
            <p className="rb-lead quiet">{tab === "lists" ? w.suListsLead : w.suLead}</p>
          </div>
        </header>
        <div className="su-seg" role="tablist" aria-label={w.setup}>
          {SETUP_TABS.map((t) => (
            <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? "on" : ""} data-help-skip="explained by cf.setup"
                    onClick={() => { setOpen(null); go(t === "plugins" ? "/setup" : `/setup/${t}`); }}>{label[t]}</button>
          ))}
        </div>
        {tab === "lists" ? <ListsTab w={w} /> : (
          <section className="su-card">
            {tab === "modules" ? <Rows items={modules} open={open} setOpen={setOpen} fallback={w.suModulesText} empty={w.suNone} />
              : d ? (
                tab === "plugins" ? <Rows items={d.plugins} open={open} setOpen={setOpen} fallback={w.suPluginsText} empty={w.suNone} />
                : tab === "sources" ? <Rows items={d.sources} open={open} setOpen={setOpen} fallback="" empty={w.suNoSources} />
                : tab === "roles" ? <Rows items={d.roles} open={open} setOpen={setOpen} fallback="" empty={w.suNone} />
                : <Rows items={d.schemas} open={open} setOpen={setOpen} fallback="" empty={w.suNone} />
              ) : null}
          </section>
        )}
      </div>
    </main>
  );
}

