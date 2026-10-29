// The board: every case as a card in the column of its stage — the second view on the same folders. Click a card, the case opens.
import { useQuery } from "@tanstack/react-query";
import { api, type ConfigView } from "../api";
import { Card } from "./List";
import type { words } from "../words";

export function Board({ config, go, w }: { config: ConfigView; go: (p: string) => void; w: ReturnType<typeof words> }) {
  const stages = useQuery({ queryKey: ["stages"], queryFn: api.stages, refetchInterval: 25_000 });
  const lang = config.lang;
  const total = (stages.data ?? []).reduce((n, s) => n + s.cases.length, 0);
  return (
    <main className="main view-board">
      <header className="view-head">
        <h1>{w.board}</h1>
        <span className="hint">{total} · {config.product}</span>
      </header>
      <div className="kanban">
        {(stages.data ?? []).map((s) => (
          <section key={s.folder} className={`col${s.cases.length === 0 ? " empty" : ""}`} aria-label={s.word}>
            <h3><span>{s.station || s.word}</span><span className="n">{s.cases.length}</span></h3>
            {s.station && s.cases.length > 0 && <span className="folder">{s.word}</span>}
            <div className="col-cards">
              {s.cases.map((c) => <Card key={c.id} c={c} go={go} w={w} lang={lang} quiet={!c.mine} />)}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
