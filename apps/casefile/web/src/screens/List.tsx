// The list: one sentence, the cases that wait for you with a blue border, then the others in grey, then what is coming up.
import { useQuery } from "@tanstack/react-query";
import { api, type CaseCard, type ConfigView } from "../api";
import { BASE } from "../api";
import type { Route } from "../App";
import { Cover } from "../components/Cover";
import { DayDone } from "../components/DayDone";
import { ago, dateWords, type words } from "../words";

export function Card({ c, go, w, lang, quiet, on, from }: { c: CaseCard; go: (p: string) => void; w: ReturnType<typeof words>; lang: string; quiet?: boolean; on?: boolean; from?: string }) {
  const to = `/case/${encodeURIComponent(c.id)}${from ? `?g=${encodeURIComponent(from)}` : ""}`;
  const t = c.turn;
  const running = t?.actor === "claude";
  const state = t ? (c.mine ? c.stage_word : t.actor === "claude" ? `${t.reason}${c.since ? ` · ${w.since} ${ago(c.since, lang)}` : ""}` : `${c.stage_word}`) : c.stage_word;
  return (
    <a className={`card${c.mine ? " mine" : ""}${quiet ? " quiet" : ""}${on ? " on" : ""}`} aria-current={on ? "true" : undefined} href={`${BASE}${to}`} onClick={(e) => { e.preventDefault(); go(to); }}>
      <Cover label={c.label} number={c.number || c.id.split("-")[1] || ""} tint={c.tint} />
      <span className="card-body">
        {!quiet && <span className="ref">{c.label_word}</span>}
        <span className="num">{c.external_id || (c.number ? `${c.label}-${c.number}` : c.id)}</span>
        <span className="title">{c.title}</span>
        <span className="state">{state}</span>
        {c.mine && <span className="yours">{w.yourMove}</span>}
        {running && <span className="bar"><i /></span>}
      </span>
    </a>
  );
}

export function List({ config, route, go, w, me }: { config: ConfigView; route: Route; go: (p: string) => void; w: ReturnType<typeof words>; me?: string }) {
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const lang = config.lang;
  if (!groups.data) return <section className="list" aria-label={w.yourMove}><p className="empty">…</p></section>;
  const byKey = new Map(groups.data.map((g) => [g.key, g]));
  // the case open beside the list: the one chosen in the URL, or on the start page the first that waits for you
  const openId = route.name === "case" ? route.id : (route.name === "group" ? byKey.get(route.key)?.cases[0]?.id : byKey.get("you")?.cases[0]?.id);
  const isClaims = !config.words?.labels || Object.keys(config.words.labels as object).some((k) => ["HR", "WG", "KFZ"].includes(k));
  const shown = route.name === "group" ? route.key : route.name === "case" ? route.group : undefined;    // a case opened from a group keeps its group beside it
  if (shown) {
    const g = byKey.get(shown);
    return (
      <section className="list" aria-label={g?.word ?? shown}>
        <h2>{g?.word ?? shown}</h2>
        {g?.cases.length ? g.cases.map((c) => <Card key={c.id} c={c} go={go} w={w} lang={lang} quiet={shown !== "you"} on={c.id === openId} from={shown} />) : <p className="empty">—</p>}
      </section>
    );
  }
  const mine = byKey.get("you")?.cases ?? [];
  const others = [...(byKey.get("claude")?.cases ?? []), ...(byKey.get("others")?.cases ?? []), ...(byKey.get("date")?.cases ?? [])];
  const coming = (byKey.get("planned")?.cases ?? []).slice(0, 3);
  const headline = mine.length === 0 ? `${w.nothing} ${w.nice}` : mine.length === 1 ? (isClaims ? w.oneCase : w.one) : isClaims ? w.manyCases(mine.length) : w.many(mine.length);
  return (
    <section className="list" aria-label={w.yourMove} data-help="cf.list">
      <h2>{headline}</h2>
      {mine.length === 0 && <DayDone w={w} me={me ?? ""} />}
      {mine.map((c) => <Card key={c.id} c={c} go={go} w={w} lang={lang} on={c.id === openId} />)}
      {others.length > 0 && <p className="kicker" style={{ marginTop: 10 }}>{w.others}</p>}
      {others.slice(0, 6).map((c) => <Card key={c.id} c={c} go={go} w={w} lang={lang} quiet on={c.id === openId} />)}
      {coming.length > 0 && (
        <div className="coming">
          <span className="kicker">{w.coming}</span>
          {coming.map((c) => <span key={c.id}>{dateWords(c.date, lang)} · <a href={`${BASE}/case/${c.id}`} onClick={(e) => { e.preventDefault(); go(`/case/${c.id}`); }}>{c.title}</a></span>)}
        </div>
      )}
    </section>
  );
}
