// The canon as the finished product: the house's own rules, each with the words it rests on. Built from the case's data
// (draft, decisions, pack), never from the compiled file — that file is the export, this is the reading (ADR-021).
import { useQuery } from "@tanstack/react-query";
import { ApiError, BASE, talk, type CanonMap, type ConfigView, type Line } from "../api";
import { Back } from "../components/Icons";
import { Explain } from "../components/Explain";
import { dateWords, type words } from "../words";

type W = ReturnType<typeof words>;

// Where this canon stands (canonical-hierarchy, depth): the layers above it and the other areas beside it. An area's rules
// are one part of the canon, never the whole; the brand stays open until it has had its own conversation.
function CanonMapView({ map, w, go }: { map: CanonMap; w: W; go: (p: string) => void }) {
  const areas = map.areas ?? [];
  const layer = (name: string, l?: { present: boolean; title: string; rules: number }) => (
    <li className={`map-layer ${l?.present ? "" : "open"}`}>
      <span className="map-name">{name}</span>
      <span className="map-what">{l?.present ? <>{l.title}{l.rules ? <small>{w.mapRules(l.rules)}</small> : null}</> : w.mapOpen}</span>
    </li>
  );
  return (
    <section className="canon-map" aria-label={w.mapTitle} data-help="cf.canon-map">
      <h2>{w.mapTitle}</h2>
      <ol className="map-stack">
        {layer(w.mapBasis, map.basis)}
        {layer(w.mapMarke, map.marke)}
        <li className="map-layer">
          <span className="map-name">{w.mapAreas}</span>
          <span className="map-areas">
            {areas.map((a) => (
              <button key={a.case} type="button" className={`map-area ${a.current ? "here" : ""} ${a.version ? "" : "work"}`} disabled={a.current}
                onClick={() => go(`/case/${encodeURIComponent(a.case)}${a.version ? "/kanon" : ""}`)}>
                {a.title}<small>{a.current ? w.mapHere : a.version ? `v0.${a.version}` : w.mapInWork}</small>
              </button>
            ))}
          </span>
        </li>
      </ol>
      <p className="map-rule">{w.mapRule}</p>
    </section>
  );
}

export function CanonScreen({ id, config, go, w }: { id: string; config: ConfigView; go: (p: string) => void; w: W }) {
  const q = useQuery({ queryKey: ["outcome", id], queryFn: () => talk.outcome(id), retry: false });
  if (q.isLoading) return <main className="main canon-main"><p className="empty">…</p></main>;
  if (!q.data) return <main className="main canon-main"><p className="empty">{q.error instanceof ApiError ? q.error.message : w.unreachable}</p></main>;
  const v = q.data;
  const markerWord = (m?: string) => (m ? ((config.words as { markers?: Record<string, string> }).markers?.[m]) ?? m : "");
  const kept = v.lines.filter((l) => l.decision.verdict === "accept" || l.decision.verdict === "edit");
  const sources = kept.flatMap((l) => l.sources ?? []);
  const voices = [...new Set(sources.map((s) => s.person))];
  const chapter = (qid: string) => { const [bid, n] = qid.split("."); const b = v.blocks.find((x) => x.id === bid); return b ? `${b.title.replace(/^Block \d+ — /, "")}, ${w.questionN(n)}` : qid; };
  const groups = v.blocks.map((b) => ({ b, lines: kept.filter((l) => l.block === b.id) })).filter((g) => g.lines.length);
  const sealed = !!v.canon;
  const text = (l: Line) => (l.decision.verdict === "edit" ? l.decision.text : l.text) ?? "";

  return (
    <main className="main canon-main">
      <header className="talk-head canon-tools">
        <button type="button" className="btn link small talk-back" onClick={() => go(`/case/${encodeURIComponent(id)}/ergebnis`)}><Back /> {w.outcomeOpen}</button>
        <span className="talk-title" />
        <Explain where="canon" config={config} />
        <button type="button" className="btn ghost small" onClick={() => window.print()} data-help="cf.canon-print">{w.printPdf}</button>
        {v.canon_url && <a className="btn link small" href={BASE + v.canon_url} download>{w.asFile}</a>}
      </header>
      <div className="canon-scroll">
        <article className="canon-doc" data-help="cf.canon-doc">
          <header className="canon-cover">
            <div className="canon-seal" aria-hidden="true"><span><b>v0.{v.version || 1}</b><small>{sealed ? w.sealed : w.draftWord}</small></span></div>
            <p className="canon-kind">{w.canonKind}</p>
            <h1>{v.title}</h1>
            {v.subtitle && <p className="canon-sub">{v.subtitle}</p>}
            <dl className="canon-facts">
              <div><dt>{w.factRules}</dt><dd>{kept.length}</dd></div>
              <div><dt>{w.factVoices}</dt><dd>{voices.length}</dd></div>
              <div><dt>{w.factQuotes}</dt><dd>{sources.length}</dd></div>
              {sealed && v.approved_at && <div><dt>{w.factApproved}</dt><dd className="small">{dateWords(v.approved_at, config.lang)}<span>{v.approved_by}</span></dd></div>}
            </dl>
            <nav className="canon-toc" aria-label={w.chapters}>
              {groups.map((g) => <a key={g.b.id} href={`#k-${g.b.id}`} onClick={(e) => { e.preventDefault(); document.getElementById(`k-${g.b.id}`)?.scrollIntoView({ behavior: "smooth" }); }}>{g.b.canon || g.b.title}<span>{g.lines.length}</span></a>)}
            </nav>
          </header>

          <CanonMapView map={v.canon_map} w={w} go={go} />

          {groups.map((g) => (
            <section key={g.b.id} id={`k-${g.b.id}`} className="canon-chapter">
              <h2>{g.b.canon || g.b.title}</h2>
              <ol className="canon-rules">
                {g.lines.map((l) => (
                  <li key={l.id} className={`canon-rule ${l.marker ?? ""}`}>
                    <div className="rule-head">
                      <span className="rule-id">{l.id}</span>
                      <span className={`rule-tag ${l.marker ?? ""}`}>{markerWord(l.marker)}</span>
                    </div>
                    <p className="rule-text">{text(l)}</p>
                    {!!l.sources?.length && (
                      <div className="rule-voices">
                        {l.sources.map((s, i) => (
                          <figure key={i} className="voice">
                            <span className="avatar small" aria-hidden="true">{(v.people[s.person] ?? s.person).slice(0, 2).toUpperCase()}</span>
                            <div>
                              <blockquote>„{s.quote}“</blockquote>
                              <figcaption>{v.people[s.person] ?? s.person} · {chapter(s.question)}</figcaption>
                            </div>
                          </figure>
                        ))}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            </section>
          ))}

          <section className="canon-machine" data-help="cf.canon-machine">
            <h2>{w.machineTitle}</h2>
            <p>{w.machineText}</p>
            <div className="machine-row" aria-hidden="true">
              <span className="machine-doc">{w.canonKind.split(" · ")[0]} v0.{v.version || 1}</span>
              <span className="machine-lines" />
              <span className="machine-agents">{["Claude", "Codex", "Grok", "API"].map((a) => <span key={a}>{a}</span>)}</span>
            </div>
            <p className="machine-rule">{w.machineRule}</p>
          </section>

          <footer className="canon-foot">
            <p>{w.canonFoot}</p>
          </footer>
        </article>
      </div>
    </main>
  );
}
