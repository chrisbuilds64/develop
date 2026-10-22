// The rulebook: what this world runs on — the stages and their gates, what each helper does and never does, and the
// approved text modules and rules with their versions. Read-only; a change is a new version, approved by a person.
import { useQuery } from "@tanstack/react-query";
import { api, type ConfigView } from "../api";
import type { words } from "../words";

export function Rules({ config, w }: { config: ConfigView; w: ReturnType<typeof words> }) {
  const q = useQuery({ queryKey: ["rules"], queryFn: api.rules, refetchInterval: false });
  if (!q.data) return <main className="main view-rules"><p className="empty">…</p></main>;
  const r = q.data;
  const modules = r.modules.filter((m) => m.kind !== "Regel");
  const rules = r.modules.filter((m) => m.kind === "Regel");
  return (
    <main className="main view-rules">
      <header className="view-head">
        <h1>{w.rules}</h1>
        <span className="hint">{config.product} · {w.rulesHint}</span>
      </header>
      <div className="rules-scroll">
        <section className="rules-block">
          <p className="kicker">{w.rulesStages}</p>
          <ol className="rule-stages">
            {r.stages.map((s) => (
              <li key={s.folder}>
                <div className="rs-head"><b>{s.station || s.word}</b><span className="mono hint">{s.folder}</span><span className="hint">{s.turn_word}</span></div>
                <div className="rs-body">
                  {s.actions.map((a) => <span key={a.id} className="chip small">{a.word}{a.to_word ? ` → ${a.to_word}` : ""}{a.run ? ` · ${w.rulesOrders} ${a.run}` : ""}{a.requires.length ? ` · ${w.rulesNeeds} ${a.requires.join(", ")}` : ""}</span>)}
                  {s.auto.map((a, i) => <span key={i} className="chip small auto">{w.rulesAuto} {a.on_file} → {a.skill}</span>)}
                </div>
              </li>
            ))}
          </ol>
        </section>
        <section className="rules-block">
          <p className="kicker">{w.rulesSkills}</p>
          <table className="rules-table">
            <thead><tr><th>{w.rulesSkill}</th><th>{w.rulesDoes}</th><th className="never">{w.rulesNever}</th><th>{w.rulesBy}</th></tr></thead>
            <tbody>
              {r.skills.map((s) => (
                <tr key={s.name}>
                  <td><b>{s.name}</b>{s.rules.length > 0 && <small>{s.rules.join(" · ")}</small>}</td>
                  <td>{s.does}</td>
                  <td className="never">{s.never}</td>
                  <td className="hint">{s.orderable_by.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        {r.connectors.length > 0 && (
          <section className="rules-block">
            <p className="kicker">{w.rulesConnectors}</p>
            <table className="rules-table">
              <thead><tr><th>{w.rulesSystem}</th><th>{w.rulesStandard}</th><th>{w.rulesCarries}</th></tr></thead>
              <tbody>
                {r.connectors.map((k) => (
                  <tr key={k.id}><td><b>{k.name}</b><small>{k.direction}</small></td><td>{k.standard}</td><td>{k.carries}{k.note && <small>{k.note}</small>}</td></tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
        {rules.length > 0 && (
          <section className="rules-block">
            <p className="kicker">{w.rulesRules}</p>
            <div className="modules">{rules.map((m) => <Module key={m.id} m={m} w={w} />)}</div>
          </section>
        )}
        {modules.length > 0 && (
          <section className="rules-block">
            <p className="kicker">{w.rulesModules}</p>
            <div className="modules">{modules.map((m) => <Module key={m.id} m={m} w={w} />)}</div>
          </section>
        )}
      </div>
    </main>
  );
}

function Module({ m, w }: { m: { id: string; title: string; version: number; status: string; approved_by: string; date: string; text: string }; w: ReturnType<typeof words> }) {
  return (
    <article className="module">
      <div className="module-head"><b>{m.id} · {m.title}</b><span className="chip small on">{w.version(m.version)}</span></div>
      <p className="module-text">{m.text}</p>
      <p className="hint">{m.status} · {m.approved_by} · {m.date}</p>
    </article>
  );
}
