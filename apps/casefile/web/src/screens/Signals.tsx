// Patterns across files: what the pattern helper noticed over the whole world — duplicates, repeats, deviations — each as a
// hint with its reasoning and the files it rests on. Never a finding; a person decides whether anything follows.
import { useQuery } from "@tanstack/react-query";
import { api, BASE, type ConfigView } from "../api";
import { Cover } from "../components/Cover";
import type { words } from "../words";

export function Signals({ config, go, w }: { config: ConfigView; go: (p: string) => void; w: ReturnType<typeof words> }) {
  const q = useQuery({ queryKey: ["signals"], queryFn: api.signals, refetchInterval: 25_000 });
  const stages = useQuery({ queryKey: ["stages"], queryFn: api.stages, refetchInterval: false });
  const cards = new Map((stages.data ?? []).flatMap((s) => s.cases).map((c) => [c.id, c]));
  const agent = config.people.find((p) => p.kind === "agent")?.name ?? "KI";
  return (
    <main className="main view-signals">
      <header className="view-head">
        <h1>{w.signals}</h1>
        <span className="hint">{config.product} · {w.signalsHint(agent)}</span>
      </header>
      <div className="rules-scroll">
        {q.data?.length === 0 && <p className="empty">{w.signalsNone}</p>}
        {(q.data ?? []).map((s) => (
          <article key={s.id} className="signal">
            <div className="signal-head">
              <span className="chip small on">{s.kind}</span>
              <h2>{s.title}</h2>
              <span className="hint">{s.id} · {s.date} · {s.status}</span>
            </div>
            <div className="signal-cases">
              {s.cases.map((c) => {
                const card = cards.get(c.id);
                return (
                  <a key={c.id} className="card quiet" href={`${BASE}/case/${encodeURIComponent(c.id)}`} onClick={(e) => { e.preventDefault(); go(`/case/${encodeURIComponent(c.id)}`); }}>
                    <Cover label={card?.label ?? c.id.split("-")[0]} number={card?.number || c.id.split("-")[1] || ""} tint={card?.tint ?? ""} />
                    <span className="card-body">
                      <span className="num">{c.external_id || c.id}</span>
                      <span className="title">{c.title}</span>
                      <span className="state">{c.stage_word}</span>
                    </span>
                  </a>
                );
              })}
            </div>
            <div className="signal-text prose" dangerouslySetInnerHTML={{ __html: toHtml(s.text) }} />
          </article>
        ))}
      </div>
    </main>
  );
}

/** The signal's text is a few paragraphs of plain prose with *emphasis*; nothing else is rendered. */
function toHtml(text: string): string {
  const esc = text.replace(/&/g, "&amp;").replace(/</g, "&lt;");
  return esc.split(/\n\s*\n/).map((p) => `<p>${p.replace(/\*([^*]+)\*/g, "<em>$1</em>").replace(/\n/g, "<br>")}</p>`).join("");
}
