// The menu: the three views under the name, groups by urgency, drop-in and the person at the bottom. Left or right.
import { useQuery } from "@tanstack/react-query";
import { api, stepId, talk, ApiError, type ConfigView, type MeOut } from "../api";
import type { Route } from "../App";
import type { words } from "../words";
import { Book, Close, Spark, Globe, MenuIcon, Moon, Restart, Sun, Swap, Worlds, ViewCases, ViewBoard, ViewList } from "./Icons";
import { useState } from "react";

export function Menu({ config, me, route, go, side, onSwap, onSignOut, onFresh, onPerson, onLang, w, theme, onTheme }:
  { config: ConfigView; me: MeOut; route: Route; go: (p: string) => void; side: "left" | "right"; onSwap: () => void; onSignOut: () => void;
    onFresh: (world?: string) => void; onPerson: (person: string) => void; onLang: (lang: string) => void; w: ReturnType<typeof words>; theme: "light" | "dark" | "system"; onTheme: (t: "light" | "dark" | "system") => void }) {
  const [open, setOpen] = useState(false);
  const create = (config.theme as { create?: { label?: string; roles?: string[] } }).create;
  const mayCreate = !!create && (create.roles ?? []).some((r) => me.roles.includes(r));
  const [making, setMaking] = useState(false);
  const [name, setName] = useState("");
  const [madeError, setMadeError] = useState<string | null>(null);
  const labelWord = create?.label ? ((config.words as { labels?: Record<string, string> }).labels?.[create.label] ?? create.label) : "";
  const goClose = (p: string) => { setOpen(false); go(p); };
  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  const humans = config.people.filter((p) => p.kind === "human");
  const otherWorlds = me.worlds.filter((x) => x !== me.world);
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const counts = new Map((groups.data ?? []).map((g) => [g.key, g.cases.length]));
  const agent = config.people.find((p) => p.kind === "agent")?.name ?? "Claude";
  const current = route.name === "group" ? route.key : route.name === "home" ? "you" : null;
  const view = route.name === "board" ? "board" : route.name === "list" ? "list" : "cases";
  return (
    <nav className={`menu${open ? " open" : ""}`} aria-label={w.menu}>
      <button type="button" className={`nav-row phone-only${route.name === "home" ? " on" : ""}`} data-help-skip="phone copy of cf.groups" onClick={() => goClose("/")}>
        <span>{(config.groups.find((g) => g.key === "you")?.word) ?? w.yourMove}</span>
        {(counts.get("you") ?? 0) > 0 ? <span className="badge">{counts.get("you")}</span> : null}
      </button>
      <button type="button" className="drop-in phone-only" data-help-skip="phone copy of cf.drop-in" onClick={() => { if (mayCreate) { setOpen(true); setMaking(true); } else goClose("/"); }} aria-label={mayCreate ? w.newCase(labelWord) : w.dropIn}>+</button>
      <button type="button" className="nav-row phone-only" data-help-skip="opens this menu on a phone" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? <Close /> : <MenuIcon />}<span style={{ marginLeft: 8 }}>{w.menu}</span></button>
      <div className="sheet">
      {me.shell && (
        <a className="nav-row quiet shell-row" data-help="cf.back" href={me.shell} title={w.backToShell}><span>← {w.backToShell}</span></a>
      )}
      <div className="menu-head">
        <div className={`brand${config.product.length > 11 ? " long" : ""}`}>
          <svg width="26" height="22" viewBox="0 0 26 22" aria-hidden="true"><path d="M1 4h8l2 3h14v14H1z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
          <span>{config.product}</span>
        </div>
        <button type="button" className="swap" onClick={onSwap} aria-label={w.switchHand} title={w.switchHand}><Swap /></button>
      </div>
      <div className="views" role="tablist" aria-label={w.views} data-help="cf.views">
        <button type="button" role="tab" aria-selected={view === "cases"} className={`view${view === "cases" ? " on" : ""}`} onClick={() => goClose("/")} title={w.casesView}><ViewCases /><span>{w.casesView}</span></button>
        <button type="button" role="tab" aria-selected={view === "board"} className={`view${view === "board" ? " on" : ""}`} onClick={() => goClose("/board")} title={w.board}><ViewBoard /><span>{w.board}</span></button>
        <button type="button" role="tab" aria-selected={view === "list"} className={`view${view === "list" ? " on" : ""}`} onClick={() => goClose("/list")} title={w.stacked}><ViewList /><span>{w.stacked}</span></button>
      </div>
      {config.groups.map((g) => {
        const n = counts.get(g.key) ?? 0;
        if (n === 0 && !["you", "claude", "others", "out"].includes(g.key)) return null;
        const phone = g.key === "you";
        return (
          <button key={g.key} type="button" className={`nav-row${current === g.key ? " on" : ""}${phone ? " phone" : ""}`} {...(g.key === "you" ? { "data-help": "cf.groups" } : {})}
                  onClick={() => goClose(g.key === "you" ? "/" : `/group/${g.key}`)}>
            <span>{g.word}</span>
            {g.key === "you" ? (n > 0 ? <span className="badge">{n}</span> : <span className="n">0</span>) : <span className="n">{n}</span>}
          </button>
        );
      })}
      <div className="rule" />
      <button type="button" className={`nav-row quiet${route.name === "signals" ? " on" : ""}`} onClick={() => goClose("/signals")} data-help="cf.patterns">
        <span>{w.signals}</span><span className="n"><Spark /></span>
      </button>
      <button type="button" className={`nav-row quiet${route.name === "rules" ? " on" : ""}`} onClick={() => goClose("/rules")} data-help="cf.rules">
        <span>{w.rules}</span><span className="n"><Book /></span>
      </button>
      <div className="spacer" />
      {mayCreate ? (making ? (
        <form className="new-case" data-help="cf.new-case" onSubmit={async (e) => { e.preventDefault(); if (!name.trim()) return; try { const r = await talk.create(name.trim(), stepId("new")); setMaking(false); setName(""); setMadeError(null); goClose(`/case/${encodeURIComponent(r.id)}`); } catch (err) { setMadeError(err instanceof ApiError ? err.message : String(err)); } }}>
          <input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder={w.newCasePlaceholder} maxLength={120} onKeyDown={(e) => { if (e.key === "Escape") setMaking(false); }} />
          <button type="submit" className="btn small" disabled={!name.trim()}>{w.create}</button>
          {madeError && <span className="talk-error">{madeError}</span>}
        </form>
      ) : (
        <button type="button" className="drop-in" onClick={() => setMaking(true)} data-help="cf.drop-in">{w.newCase(labelWord)}</button>
      )) : create ? null : (
        <button type="button" className="drop-in" onClick={() => goClose("/")} aria-label={w.dropIn} data-help="cf.drop-in">{w.dropIn}</button>
      )}
      <button type="button" className="nav-row quiet ask-row" data-help="cf.ask" onClick={() => document.querySelector<HTMLInputElement>(".ask input")?.focus()}>
        <span>{w.askClaude(agent)}</span><span className="mono n">⌘K</span>
      </button>

      {me.demo && (
        <div className="demo-row">
          {otherWorlds.map((x) => <button key={x} type="button" className="nav-row quiet" data-help-skip="public demo only" onClick={() => onFresh(x)}><span>{w.world(x)}</span><span className="n"><Worlds /></span></button>)}
          <button type="button" className="nav-row quiet" data-help-skip="public demo only" onClick={() => onFresh()}><span>{w.startOver}</span><span className="n"><Restart /></span></button>
        </div>
      )}
      <button type="button" className="nav-row quiet" data-help="cf.language" onClick={() => onLang(config.lang === "de" ? "en" : "de")} title={w.language} lang={config.lang === "de" ? "en" : "de"}>
        <span>{w.otherLang}</span><span className="n"><Globe /></span>
      </button>
      <button type="button" className="nav-row quiet" data-help="cf.theme" onClick={() => onTheme(dark ? "light" : "dark")} aria-label={w.theme}>
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
