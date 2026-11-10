// Facets: filter, sort and card chips for every application, built only from what /api/config declares (domain/facets.py).
// Nothing here names a domain. The choice lives in the address (?q=…&f.label=SYS,INF&sort=due&mine=1&late=1), so a
// view survives a reload and can be sent as a link.
import { useEffect, useMemo, useState } from "react";
import type { CaseCard, ConfigView } from "../api";
import type { words } from "../words";

type W = ReturnType<typeof words>;
export type Facet = ConfigView["facets"][number];
export type FacetState = { q: string; pick: Record<string, string[]>; sort: string; mine: boolean; late: boolean };

const today = () => new Date().toISOString().slice(0, 10);

function read(): FacetState {
  const p = new URLSearchParams(window.location.search);
  const pick: Record<string, string[]> = {};
  p.forEach((v, k) => { if (k.startsWith("f.") && v) pick[k.slice(2)] = v.split(","); });
  return { q: p.get("q") ?? "", pick, sort: p.get("sort") ?? "", mine: p.get("mine") === "1", late: p.get("late") === "1" };
}

function write(s: FacetState) {
  const p = new URLSearchParams(window.location.search);
  [...p.keys()].filter((k) => k.startsWith("f.") || ["q", "sort", "mine", "late"].includes(k)).forEach((k) => p.delete(k));
  if (s.q) p.set("q", s.q);
  Object.entries(s.pick).forEach(([k, v]) => { if (v.length) p.set(`f.${k}`, v.join(",")); });
  if (s.sort) p.set("sort", s.sort);
  if (s.mine) p.set("mine", "1");
  if (s.late) p.set("late", "1");
  const qs = p.toString();
  window.history.replaceState(window.history.state, "", window.location.pathname + (qs ? `?${qs}` : ""));
}

export function useFacets(): [FacetState, (s: FacetState) => void] {
  const [s, set] = useState<FacetState>(read);
  useEffect(() => { write(s); }, [s]);
  return [s, set];
}

const dateFacet = (facets: Facet[]) => facets.find((f) => f.kind === "date" && (f.sort || f.card));

/** The cards that pass the choice, in the chosen order. Without a sort they keep the order they came in. */
export function apply(cards: CaseCard[], facets: Facet[], s: FacetState, extra: (c: CaseCard) => string = () => ""): CaseCard[] {
  const needle = s.q.trim().toLowerCase();
  const due = dateFacet(facets);
  const now = today();
  const out = cards.filter((c) => {
    const v = c.values ?? {};
    if (needle && ![c.id, c.external_id, c.title, c.party, extra(c)].join(" ").toLowerCase().includes(needle)) return false;
    for (const [k, picked] of Object.entries(s.pick)) if (picked.length && !picked.includes(v[k] ?? "")) return false;
    if (s.mine && !c.mine) return false;
    if (s.late && !(due && v[due.key] && v[due.key] < now && c.turn)) return false;
    return true;
  });
  const f = facets.find((x) => x.key === s.sort && x.sort);
  if (!f) return out;
  const rank = (c: CaseCard): string | number => {
    const v = (c.values ?? {})[f.key];
    if (!v) return "￿";                                         // the empty last
    if (f.kind === "list") { const i = f.values.findIndex((x) => x.key === v); return i < 0 ? 9999 : i; }
    if (f.kind === "person") return f.values.find((x) => x.key === v)?.word ?? v;
    return v;
  };
  return [...out].sort((a, b) => {
    const x = rank(a), y = rank(b);
    if (typeof x === "number" && typeof y === "number") return x - y;
    return String(x).localeCompare(String(y));
  });
}

function Pick({ f, picked, onChange }: { f: Facet; picked: string[]; onChange: (v: string[]) => void }) {
  const [open, setOpen] = useState(false);
  const label = picked.length === 0 ? f.word : picked.length === 1 ? (f.values.find((x) => x.key === picked[0])?.word ?? picked[0]) : `${f.word} · ${picked.length}`;
  return (
    <span className={`fc-pick${picked.length ? " on" : ""}`}>
      <button type="button" className="fc-btn" aria-expanded={open} onClick={() => setOpen(!open)}>{label}<i aria-hidden="true">▾</i></button>
      {open && (
        <span className="fc-menu" role="listbox" aria-label={f.word} onMouseLeave={() => setOpen(false)}>
          {f.values.map((x) => {
            const on = picked.includes(x.key);
            return (
              <label key={x.key} className="fc-opt">
                <input type="checkbox" checked={on} onChange={() => onChange(on ? picked.filter((k) => k !== x.key) : [...picked, x.key])} />
                {x.color && <i className="fc-dot" style={{ background: x.color }} />}{x.word}
              </label>
            );
          })}
          {picked.length > 0 && <button type="button" className="fc-clear" onClick={() => onChange([])}>×</button>}
        </span>
      )}
    </span>
  );
}

/** The bar: search, one choice per filter facet, mine / overdue, the order, how many show. */
export function FacetBar({ facets, s, set, w, shown, total }: { facets: Facet[]; s: FacetState; set: (s: FacetState) => void; w: W; shown: number; total: number }) {
  const filters = facets.filter((f) => f.filter && f.values.length > 0);
  const sorts = facets.filter((f) => f.sort);
  const due = dateFacet(facets);
  const busy = !!(s.q || s.mine || s.late || Object.values(s.pick).some((v) => v.length));
  return (
    <div className="fc-bar">
      <input className="wb-filter" value={s.q} onChange={(e) => set({ ...s, q: e.target.value })} placeholder={w.tblFilter} aria-label={w.filter} autoComplete="off" />
      {filters.map((f) => <Pick key={f.key} f={f} picked={s.pick[f.key] ?? []} onChange={(v) => set({ ...s, pick: { ...s.pick, [f.key]: v } })} />)}
      <button type="button" className={`fc-btn${s.mine ? " on" : ""}`} aria-pressed={s.mine} onClick={() => set({ ...s, mine: !s.mine })}>{w.fcMine}</button>
      {due && <button type="button" className={`fc-btn${s.late ? " on" : ""}`} aria-pressed={s.late} onClick={() => set({ ...s, late: !s.late })}>{w.fcLate}</button>}
      {sorts.length > 0 && (
        <select className="fc-sort" value={s.sort} onChange={(e) => set({ ...s, sort: e.target.value })} aria-label={w.fcSort}>
          <option value="">{w.fcSortNone}</option>
          {sorts.map((f) => <option key={f.key} value={f.key}>{w.fcSortBy(f.word)}</option>)}
        </select>
      )}
      {busy && <button type="button" className="fc-btn fc-reset" onClick={() => set({ q: "", pick: {}, sort: s.sort, mine: false, late: false })}>{w.fcReset}</button>}
      {busy && <span className="fc-count">{w.fcCount(shown, total)}</span>}
    </div>
  );
}

/** What a card shows of its facets: a coloured chip per list value, the person, the date (red when it is past). */
export function Chips({ c, facets, lang }: { c: CaseCard; facets: Facet[]; lang: string }) {
  const v = c.values ?? {};
  const now = useMemo(today, []);
  const chips = facets.filter((f) => f.card && v[f.key]).map((f) => {
    const raw = v[f.key];
    const known = f.values.find((x) => x.key === raw);
    if (f.kind === "date") {
      const late = raw < now && !!c.turn;
      const d = new Date(`${raw}T00:00:00`);
      return <span key={f.key} className={`fc-chip fc-k-date${late ? " late" : ""}`} title={f.word}>{isNaN(d.getTime()) ? raw : d.toLocaleDateString(lang, { day: "numeric", month: "short" })}</span>;
    }
    return (
      <span key={f.key} className={`fc-chip fc-k-${f.kind}`} title={f.word}>
        {known?.color && <i className="fc-dot" style={{ background: known.color }} />}{known?.word ?? raw}
      </span>
    );
  });
  return chips.length ? <span className="fc-chips">{chips}</span> : null;
}
