// The board: every case as a card in the column of its stage — the second view on the same folders. Click a card, the case opens.
import { useQuery } from "@tanstack/react-query";
import { api, type ConfigView } from "../api";
import { Card } from "./List";
import type { words } from "../words";

export function Board({ config, go, w }: { config: ConfigView; go: (p: string) => void; w: ReturnType<typeof words> }) {
  const stages = useQuery({ queryKey: ["stages"], queryFn: api.stages, refetchInterval: 25_000 });
  // one label for every case: the tag says nothing, so it is left out (design, 2026-11-01)
  const bare = new Set((stages.data ?? []).flatMap((s: { cases: { label: string }[] }) => s.cases.map((c) => c.label))).size <= 1;
  const lang = config.lang;
  const total = (stages.data ?? []).reduce((n, s) => n + s.cases.length, 0);
  return (
    <main className="main view-board">
      <header className="view-head">
        <h1>{w.board}</h1>
        <span className="hint">{total} · {config.product}</span>
      </header>
      <div className="kanban">
        {(stages.data ?? []).map((s, _i, all) => {
          // two stages of one station (inspection, then the AI's reconciliation): the stage's own word heads the column
          const shared = !!s.station && all.filter((x) => x.station === s.station).length > 1;
          const head = shared ? s.word : (s.station || s.word);
          return (
          <section key={s.folder} className={`col${s.cases.length === 0 ? " empty" : ""}`} aria-label={s.word}>
            <h3><span>{head}</span><span className="n">{s.cases.length}</span></h3>
            {s.station && s.cases.length > 0 && <span className="folder">{shared ? s.station : s.word}</span>}
            <div className="col-cards">
              {s.cases.map((c) => <Card key={c.id} c={c} go={go} w={w} lang={lang} quiet={!c.mine} bare={bare} />)}
            </div>
          </section>
          );
        })}
      </div>
    </main>
  );
}
