// The menu: the three views under the name, groups by urgency, drop-in and the person at the bottom. Left or right.
import { useQuery } from "@tanstack/react-query";
import { api, type ConfigView, type MeOut } from "../api";
import type { Route } from "../App";
import type { words } from "../words";
import { Close, Globe, MenuIcon, Moon, Restart, Sun, Swap, Worlds, ViewCases, ViewBoard, ViewList } from "./Icons";
import { useState } from "react";

export function Menu({ config, me, route, go, side, onSwap, onSignOut, onFresh, onPerson, onLang, w, theme, onTheme }:
  { config: ConfigView; me: MeOut; route: Route; go: (p: string) => void; side: "left" | "right"; onSwap: () => void; onSignOut: () => void;
    onFresh: (world?: string) => void; onPerson: (person: string) => void; onLang: (lang: string) => void; w: ReturnType<typeof words>; theme: "light" | "dark" | "system"; onTheme: (t: "light" | "dark" | "system") => void }) {
  const [open, setOpen] = useState(false);
  const goClose = (p: string) => { setOpen(false); go(p); };
  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  const humans = config.people.filter((p) => p.kind === "human");
  const otherWorld = me.worlds.find((x) => x !== me.world);
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const counts = new Map((groups.data ?? []).map((g) => [g.key, g.cases.length]));
  const agent = config.people.find((p) => p.kind === "agent")?.name ?? "Claude";
  const current = route.name === "group" ? route.key : route.name === "home" ? "you" : null;
  const view = route.name === "board" ? "board" : route.name === "list" ? "list" : "cases";
  return (
    <nav className={`menu${open ? " open" : ""}`} aria-label={w.menu}>
      <button type="button" className={`nav-row phone-only${route.name === "home" ? " on" : ""}`} onClick={() => goClose("/")}>
        <span>{(config.groups.find((g) => g.key === "you")?.word) ?? w.yourMove}</span>
        {(counts.get("you") ?? 0) > 0 ? <span className="badge">{counts.get("you")}</span> : null}
      </button>
      <button type="button" className="drop-in phone-only" onClick={() => goClose("/")} aria-label={w.dropIn}>+</button>
      <button type="button" className="nav-row phone-only" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? <Close /> : <MenuIcon />}<span style={{ marginLeft: 8 }}>{w.menu}</span></button>
      <div className="sheet">
      <div className="menu-head">
        <div className="brand">
          <svg width="26" height="22" viewBox="0 0 26 22" aria-hidden="true"><path d="M1 4h8l2 3h14v14H1z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
          <span>{config.product}</span>
        </div>
        <button type="button" className="swap" onClick={onSwap} aria-label={w.switchHand} title={w.switchHand}><Swap /></button>
      </div>
      <div className="views" role="tablist" aria-label={w.views}>
        <button type="button" role="tab" aria-selected={view === "cases"} className={`view${view === "cases" ? " on" : ""}`} onClick={() => goClose("/")} title={w.casesView}><ViewCases /><span>{w.casesView}</span></button>
        <button type="button" role="tab" aria-selected={view === "board"} className={`view${view === "board" ? " on" : ""}`} onClick={() => goClose("/board")} title={w.board}><ViewBoard /><span>{w.board}</span></button>
        <button type="button" role="tab" aria-selected={view === "list"} className={`view${view === "list" ? " on" : ""}`} onClick={() => goClose("/list")} title={w.stacked}><ViewList /><span>{w.stacked}</span></button>
      </div>
      {config.groups.map((g) => {
        const n = counts.get(g.key) ?? 0;
        if (n === 0 && !["you", "claude", "others", "out"].includes(g.key)) return null;
        const phone = g.key === "you";
        return (
          <button key={g.key} type="button" className={`nav-row${current === g.key ? " on" : ""}${phone ? " phone" : ""}`}
                  onClick={() => goClose(g.key === "you" ? "/" : `/group/${g.key}`)}>
            <span>{g.word}</span>
            {g.key === "you" ? (n > 0 ? <span className="badge">{n}</span> : <span className="n">0</span>) : <span className="n">{n}</span>}
          </button>
        );
      })}
      <div className="spacer" />
      <button type="button" className="drop-in" onClick={() => goClose("/")} aria-label={w.dropIn}>{w.dropIn}</button>
      <button type="button" className="nav-row quiet ask-row" onClick={() => document.querySelector<HTMLInputElement>(".ask input")?.focus()}>
        <span>{w.askClaude(agent)}</span><span className="mono n">⌘K</span>
      </button>

      {me.demo && (
        <div className="demo-row">
          {otherWorld && <button type="button" className="nav-row quiet" onClick={() => onFresh(otherWorld)}><span>{w.world(otherWorld)}</span><span className="n"><Worlds /></span></button>}
          <button type="button" className="nav-row quiet" onClick={() => onFresh()}><span>{w.startOver}</span><span className="n"><Restart /></span></button>
        </div>
      )}
      <button type="button" className="nav-row quiet" onClick={() => onLang(config.lang === "de" ? "en" : "de")} title={w.language} lang={config.lang === "de" ? "en" : "de"}>
        <span>{w.otherLang}</span><span className="n"><Globe /></span>
      </button>
      <button type="button" className="nav-row quiet" onClick={() => onTheme(dark ? "light" : "dark")} aria-label={w.theme}>
        <span>{dark ? w.light : w.dark}</span><span className="n">{dark ? <Sun /> : <Moon />}</span>
      </button>
      <div className="who">
        <span className="avatar">{(me.name ?? "?").slice(0, 2).toUpperCase()}</span>
        {me.demo && humans.length > 1 ? (
          <select className="person-switch" value={me.person ?? ""} onChange={(e) => onPerson(e.target.value)} aria-label={w.signIn}>
            {humans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        ) : <span>{me.name}</span>}
        {!me.demo && <button type="button" className="btn link small" style={{ marginLeft: "auto", padding: 0 }} onClick={onSignOut}>{w.signOut}</button>}
      </div>
      </div>
      {open && <button type="button" className="scrim" aria-label={w.menu} onClick={() => setOpen(false)} />}
    </nav>
  );
}
