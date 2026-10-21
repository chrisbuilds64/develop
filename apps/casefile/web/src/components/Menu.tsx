// The menu: groups by urgency, the workshop behind a rule, drop-in and the person at the bottom. Left or right.
import { useQuery } from "@tanstack/react-query";
import { api, type ConfigView, type MeOut } from "../api";
import type { Route } from "../App";
import type { words } from "../words";
import { Restart, Swap, Worlds } from "./Icons";

export function Menu({ config, me, route, go, side, onSwap, onSignOut, onFresh, onPerson, w }:
  { config: ConfigView; me: MeOut; route: Route; go: (p: string) => void; side: "left" | "right"; onSwap: () => void; onSignOut: () => void;
    onFresh: (world?: string) => void; onPerson: (person: string) => void; w: ReturnType<typeof words> }) {
  const humans = config.people.filter((p) => p.kind === "human");
  const otherWorld = me.worlds.find((x) => x !== me.world);
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const counts = new Map((groups.data ?? []).map((g) => [g.key, g.cases.length]));
  const agent = config.people.find((p) => p.kind === "agent")?.name ?? "Claude";
  const current = route.name === "group" ? route.key : route.name === "home" ? "you" : null;
  return (
    <nav className="menu" aria-label={w.menu}>
      <div className="menu-head">
        <div className="brand">
          <svg width="26" height="22" viewBox="0 0 26 22" aria-hidden="true"><path d="M1 4h8l2 3h14v14H1z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
          <span>{config.product}</span>
        </div>
        <button type="button" className="swap" onClick={onSwap} aria-label={w.switchHand} title={w.switchHand}><Swap /></button>
      </div>
      {config.groups.map((g) => {
        const n = counts.get(g.key) ?? 0;
        if (n === 0 && !["you", "claude", "others", "out"].includes(g.key)) return null;
        const phone = g.key === "you";
        return (
          <button key={g.key} type="button" className={`nav-row${current === g.key ? " on" : ""}${phone ? " phone" : ""}`}
                  onClick={() => go(g.key === "you" ? "/" : `/group/${g.key}`)}>
            <span>{g.word}</span>
            {g.key === "you" ? (n > 0 ? <span className="badge">{n}</span> : <span className="n">0</span>) : <span className="n">{n}</span>}
          </button>
        );
      })}
      <div className="rule" />
      <button type="button" className={`nav-row quiet${route.name === "workshop" ? " on" : ""}`} onClick={() => go("/workshop")}>
        <span>{w.workshop}</span><span className="mono n">{w.stages}</span>
      </button>
      <div className="spacer" />
      <button type="button" className="drop-in" onClick={() => go("/")} aria-label={w.dropIn}>{window.matchMedia("(max-width: 900px)").matches ? "+" : w.dropIn}</button>
      <button type="button" className="nav-row quiet ask-row" onClick={() => document.querySelector<HTMLInputElement>(".ask input")?.focus()}>
        <span>{w.askClaude(agent)}</span><span className="mono n">⌘K</span>
      </button>
      <button type="button" className="nav-row phone-only" onClick={() => go(route.name === "workshop" ? "/" : "/workshop")}>{route.name === "workshop" ? w.yourMove : w.workshop}</button>
      {me.demo && (
        <div className="demo-row">
          {otherWorld && <button type="button" className="nav-row quiet" onClick={() => onFresh(otherWorld)}><span>{w.world(otherWorld)}</span><span className="n"><Worlds /></span></button>}
          <button type="button" className="nav-row quiet" onClick={() => onFresh()}><span>{w.startOver}</span><span className="n"><Restart /></span></button>
        </div>
      )}
      <div className="who">
        <span className="avatar">{(me.name ?? "?").slice(0, 2).toUpperCase()}</span>
        {me.demo && humans.length > 1 ? (
          <select className="person-switch" value={me.person ?? ""} onChange={(e) => onPerson(e.target.value)} aria-label={w.signIn}>
            {humans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        ) : <span>{me.name}</span>}
        {!me.demo && <button type="button" className="btn link small" style={{ marginLeft: "auto", padding: 0 }} onClick={onSignOut}>{w.signOut}</button>}
      </div>
    </nav>
  );
}
