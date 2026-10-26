// The house canon at one glance (canonical-hierarchy: Depth, Every rule carries). Columns are the layers — who wins, left
// before right; rows are the depths — how concrete. Depth is no second precedence. Every document is a chip that says its
// status; a click opens what makes it usable: scope, status, owner, origin, what carries it out, and the text itself.
// Records stay below the line: they show the canon at work and are never canon themselves.
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { canon, type HouseDoc, type HouseView } from "../api";
import { Close } from "../components/Icons";
import { Explain } from "../components/Explain";
import type { ConfigView } from "../api";
import type { words } from "../words";

type W = ReturnType<typeof words>;
const DEPTHS = [1, 2, 3, 4, 0];

function mark(d: HouseDoc) {
  if (d.status === "freigegeben") return d.open ? "approved unproven" : "approved";
  if (d.status === "nachweis" || d.status === "referenz" || d.status === "historie") return "record";
  return "candidate";
}

export function HouseScreen({ config, go, w }: { config: ConfigView; go: (p: string) => void; w: W }) {
  const q = useQuery({ queryKey: ["canon-house"], queryFn: canon.house, refetchInterval: false });
  const [open, setOpen] = useState<HouseDoc | null>(null);
  if (!q.data) return <main className="main view-house"><p className="empty">…</p></main>;
  const v: HouseView = q.data;
  const cols = [{ key: "basis", title: w.layerBasis, lead: w.layerBasisLead }, { key: "marke", title: w.layerMarke, lead: w.layerMarkeLead },
    ...v.areas.map((a) => ({ key: `bereich:${a.id}`, title: a.title, lead: a.lead ?? "" }))];
  const colOf = (d: { layer: string; area?: string }) => (d.layer === "bereich" ? `bereich:${d.area ?? ""}` : d.layer);
  const canonDocs = v.docs.filter((d) => (d.depth ?? 1) !== 5);
  const records = v.docs.filter((d) => d.depth === 5);
  const approved = canonDocs.filter((d) => d.status === "freigegeben");
  const unproven = approved.filter((d) => d.open).length;
  const areaCount = v.areas.length;

  return (
    <main className="main view-house">
      <header className="view-head">
        <h1>{w.houseTitle}{v.house && <span className="house-name"> · {v.house}</span>}</h1>
        <span className="hint">{v.lead || w.houseHint}</span>
        <Explain where="house" config={config} />
      </header>
      <div className="house-scroll">
        <section className="house-intro" data-help="cf.house-intro">
          <div><b>{w.houseOne}</b><p>{w.houseOneText}</p></div>
          <div><b>{w.houseBinding}</b><p>{w.houseBindingText}</p></div>
          <div><b>{w.houseMachine}</b><p>{w.houseMachineText}</p></div>
        </section>

        <p className="house-count">{w.houseCount(canonDocs.length, approved.length, unproven, v.gaps.length)}</p>

        <section className="house-matrix-wrap" data-help="cf.house-matrix">
          <div className="house-matrix" style={{ gridTemplateColumns: `minmax(150px, 190px) repeat(${cols.length}, minmax(170px, 1fr))` }}>
            <div className="hm-corner"><span className="hm-arrow">{w.houseWins}</span></div>
            <div className="hm-band basis-marke" style={{ gridColumn: "2 / span 2" }}>{w.houseAbove}</div>
            {areaCount > 0 && <div className="hm-band areas" style={{ gridColumn: `4 / span ${areaCount}` }}>{w.houseAreas}</div>}
            <div className="hm-corner small">{w.houseDepth}</div>
            {cols.map((c) => <div key={c.key} className="hm-col"><b>{c.title}</b>{c.lead && <small>{c.lead}</small>}</div>)}
            {DEPTHS.filter((depth) => depth !== 0 || canonDocs.some((d) => d.depth === 0)).map((depth) => (
              <Row key={depth} depth={depth} cols={cols.map((c) => c.key)} docs={canonDocs.filter((d) => (d.depth ?? 1) === depth)}
                   gaps={v.gaps.filter((g) => g.depth === depth)} colOf={colOf} onOpen={setOpen} w={w} />
            ))}
            <div className="hm-line" style={{ gridColumn: `1 / span ${cols.length + 1}` }}><span>{w.houseLine}</span></div>
            <div className="hm-depth record"><b>{w.depthWord(5)}</b><small>{w.depthLead(5)}</small></div>
            {cols.map((c) => (
              <div key={c.key} className="hm-cell record">
                {records.filter((d) => colOf(d) === c.key).map((d) => <Chip key={d.file ?? d.case} d={d} onOpen={setOpen} w={w} />)}
                {v.records.filter((r) => colOf(r) === c.key).map((r) => (
                  <button key={r.title} type="button" className="hm-chip record" onClick={() => setOpen({ ...r, layer: r.layer, depth: 5, status: "nachweis", kind: w.recordWord })}>
                    {r.title}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </section>

        <section className="house-legend" aria-label={w.legend}>
          <span><i className="hm-chip approved" />{w.legApproved}</span>
          <span><i className="hm-chip approved unproven" />{w.legUnproven}</span>
          <span><i className="hm-chip candidate" />{w.legCandidate}</span>
          <span><i className="hm-chip gap" />{w.legGap}</span>
          <span><i className="hm-chip record" />{w.legRecord}</span>
          <span className="rule">{w.houseRule}</span>
        </section>
      </div>
      {open && <DocPanel d={open} docs={v.docs} onClose={() => setOpen(null)} onOpen={setOpen} go={go} w={w} />}
    </main>
  );
}

function Row({ depth, cols, docs, gaps, colOf, onOpen, w }: { depth: number; cols: string[]; docs: HouseDoc[]; gaps: HouseView["gaps"];
  colOf: (d: { layer: string; area?: string }) => string; onOpen: (d: HouseDoc) => void; w: W }) {
  return (
    <>
      <div className={`hm-depth d${depth}`}><b>{w.depthWord(depth)}</b><small>{w.depthLead(depth)}</small></div>
      {cols.map((k) => (
        <div key={k} className={`hm-cell d${depth}`}>
          {docs.filter((d) => colOf(d) === k).map((d) => <Chip key={d.file ?? d.case} d={d} onOpen={onOpen} w={w} />)}
          {gaps.filter((g) => colOf(g) === k).map((g) => (
            <button key={g.title} type="button" className="hm-chip gap" onClick={() => onOpen({ ...g, status: "luecke", kind: w.gapWord })}>{w.gapPrefix} {g.title}</button>
          ))}
        </div>
      ))}
    </>
  );
}

function Chip({ d, onOpen, w }: { d: HouseDoc; onOpen: (d: HouseDoc) => void; w: W }) {
  return (
    <button type="button" className={`hm-chip ${mark(d)}`} onClick={() => onOpen(d)} title={d.lead ?? ""}>
      {d.title}{d.open && <span className="hm-q" aria-label={w.legUnproven}>?</span>}
    </button>
  );
}

function DocPanel({ d, docs, onClose, onOpen, go, w }: { d: HouseDoc; docs: HouseDoc[]; onClose: () => void; onOpen: (d: HouseDoc) => void; go: (p: string) => void; w: W }) {
  const [html, setHtml] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    setHtml(null);
    if (d.file) canon.doc(d.file).then((r) => { if (alive) setHtml(r.html); }).catch(() => { if (alive) setHtml(""); });
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => { alive = false; window.removeEventListener("keydown", onKey); };
  }, [d.file, d.title]);
  const used = (d.uses ?? []).map((f) => docs.find((x) => x.file === f)).filter(Boolean) as HouseDoc[];
  return (
    <aside className="house-panel" role="dialog" aria-label={d.title} data-help="cf.house-doc">
      <header>
        <div><p className="kicker">{d.kind}</p><h2>{d.title}</h2>{d.lead && <p className="lead">{d.lead}</p>}</div>
        <button type="button" className="btn link small" onClick={onClose} aria-label={w.close}><Close /></button>
      </header>
      <dl className="house-facts">
        <div><dt>{w.factLayer}</dt><dd>{d.layer === "basis" ? w.layerBasis : d.layer === "marke" ? w.layerMarke : w.houseAreas}{d.depth !== undefined && ` · ${w.depthWord(d.depth)}`}</dd></div>
        {d.scope && <div><dt>{w.factScope}</dt><dd>{d.scope}</dd></div>}
        <div><dt>{w.factStatus}</dt><dd className={`st ${mark(d)}`}>{w.statusWord(d.status ?? "")}{d.version ? (d.case ? ` · v0.${d.version}` : ` · v${d.version}`) : ""}
          {d.evidence && <small>{w.evidenceWord}: {d.evidence}</small>}{d.open && <small className="warn">{d.open}</small>}</dd></div>
        {d.owner && <div><dt>{w.factOwner}</dt><dd>{d.owner}</dd></div>}
        {!!d.implements?.length && <div><dt>{w.factImplements}</dt><dd>{d.implements.join(" · ")}</dd></div>}
        {d.note && <div><dt>{w.factNote}</dt><dd className="warn">{d.note}</dd></div>}
      </dl>
      {d.origin && (
        <section className="house-origin">
          <h3>{w.originTitle(d.origin.kind)}</h3>
          {d.origin.text && <p>{d.origin.text}</p>}
          {!!d.origin.trail?.length && (
            <ol className="house-trail">
              {d.origin.trail.map((t, i) => (
                <li key={i} className={t.step}><b>{w.trailWord(t.step)}</b><span>{t.date}{t.who && ` · ${t.who}`}</span><p>{t.text}</p>
                  {t.quotes?.map((q, j) => <blockquote key={j}>„{q.quote}“ <cite>— {q.who}</cite></blockquote>)}</li>
              ))}
            </ol>
          )}
        </section>
      )}
      {!!used.length && (
        <section className="house-origin">
          <h3>{w.usesTitle}</h3>
          <p className="house-uses">{used.map((u) => <button key={u.file} type="button" className="hm-chip approved" onClick={() => onOpen(u)}>{u.title}</button>)}</p>
        </section>
      )}
      {d.case && <p><button type="button" className="btn small" onClick={() => go(`/case/${encodeURIComponent(d.case!)}${d.depth === 5 ? "" : d.status === "freigegeben" ? "/kanon" : "/ergebnis"}`)}>{d.depth === 5 ? w.openCase : w.openAreaCanon}</button></p>}
      {d.file && (html === null ? <p className="empty">…</p> : html ? <div className="prose house-text" dangerouslySetInnerHTML={{ __html: html }} /> : null)}
    </aside>
  );
}
