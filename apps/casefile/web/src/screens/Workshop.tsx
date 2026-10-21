// The workshop: the kanban by stage, for the operator. Stage names in mono, nothing hidden.
import { useQuery } from "@tanstack/react-query";
import { api, type ConfigView } from "../api";
import type { words } from "../words";

export function Workshop({ config, go, w }: { config: ConfigView; go: (p: string) => void; w: ReturnType<typeof words> }) {
  const stages = useQuery({ queryKey: ["stages"], queryFn: api.stages });
  return (
    <main className="main">
      <header className="case-head">
        <span className="ref">{config.product}</span>
        <h1>{w.workshop}</h1>
      </header>
      <div className="kanban">
        {(stages.data ?? []).map((s) => (
          <div key={s.folder} className="col">
            <h3>{s.folder} <span style={{ opacity: .6 }}>· {s.cases.length}</span></h3>
            {s.cases.map((c) => (
              <a key={c.id} className={`card${c.mine ? " mine" : ""}`} href={`/case/${c.id}`} onClick={(e) => { e.preventDefault(); go(`/case/${encodeURIComponent(c.id)}`); }}>
                <span className="ref">{c.id}</span>
                <span className="title">{c.title}</span>
                {c.turn && <span className="state">{c.turn.actor.replace(/^role:/, "")} → {c.turn.label}</span>}
              </a>
            ))}
          </div>
        ))}
      </div>
    </main>
  );
}
