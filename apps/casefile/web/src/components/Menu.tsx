// The rail (design hand-back, 2026-11-05): the mark and name, search, Home, the workspaces, the admin pages, and the
// person at the bottom with everything that is about you (theme, language, sound, side, the demo's people and reset).
// It carries what the old menu carried; only the places changed. On a phone it slides in over the page.
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, BASE, type ConfigView, type MeOut, type CaseCard } from "../api";
import { createSpec, newCaseWord, openNewCase } from "./NewCase";
import type { Route } from "../App";
import type { words } from "../words";
import { Book, TeamIcon, SetupIcon, RulebookIcon, Pulse, SearchIcon, HomeIcon, Updown, Globe, Swap, Restart, Close, Speaker } from "./Icons";
import { setSound, soundOn, chime, paper as paperSound } from "../moments";

type Props = {
  config: ConfigView; me: MeOut; route: Route; go: (p: string) => void; side: "left" | "right"; onSwap: () => void; onSignOut: () => void;
  onFresh: (world?: string) => void; onPerson: (person: string) => void; onLang: (lang: string) => void; w: ReturnType<typeof words>;
  theme: "light" | "dark" | "system"; onTheme: (t: "light" | "dark" | "system") => void; open: boolean; onClose: () => void;
};

/** Two letters for a name of two words or a long one ("Chris Moser" → CM, "designer" → DE); a short word gets its first ("You" → Y). */
const initials = (name?: string | null) => {
  const parts = (name ?? "?").trim().split(/\s+/);
  if (parts.length > 1) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (parts[0].length <= 3 ? parts[0][0] : parts[0].slice(0, 2)).toUpperCase();
};

type Place = NonNullable<MeOut["places"]>[number];

/** The rail's places by workspace (ADR-032), in the order they come; one group without a name when none carries one. */
function groupsOf(places: Place[]): { key: string; label: string; places: Place[] }[] {
  const out: { key: string; label: string; places: Place[] }[] = [];
  for (const p of places) {
    const key = p.workspace ?? "";
    let g = out.find((x) => x.key === key);
    if (!g) { g = { key, label: p.workspace_label || key, places: [] }; out.push(g); }
    g.places.push(p);
  }
  return out;
}

export function Menu({ config, me, route, go, side, onSwap, onSignOut, onFresh, onPerson, onLang, w, theme, onTheme, open, onClose }: Props) {
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups });
  const counts = new Map((groups.data ?? []).map((g) => [g.key, g.cases.length]));
  const mine = counts.get("you") ?? 0;
  const everywhere = mine + (me.places ?? []).filter((p) => !p.current).reduce((n, p) => n + (p.count ?? 0), 0);   // Home gathers every workspace
  const [pop, setPop] = useState(false);
  const [sound, setSoundState] = useState(soundOn());
  const goClose = (p: string) => { setPop(false); onClose(); go(p); };

  // a new case: the rail opens the same editor as the bar's button (REQ-001 S-18), one way in
  const mayCreate = !!createSpec(config, me);
  const [madeError, setMadeError] = useState<string | null>(null);
  const mailDrop = !!(config.theme as { mail_drop?: boolean }).mail_drop && me.roles.includes("operator");
  const dropMail = async (f: File | undefined) => {
    if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try {
      const res = await fetch(BASE + "/api/mail", { method: "POST", body: fd, credentials: "same-origin" });
      const j = await res.json();
      if (!res.ok) throw new Error(j.reason ?? j.detail ?? `HTTP ${res.status}`);
      paperSound(); goClose(`/case/${encodeURIComponent(j.id)}`);
    } catch (e) { setMadeError(String((e as Error).message)); }
  };

  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  const humans = config.people.filter((p) => p.kind === "human");
  const places = me.places ?? [];
  const here = places.find((p) => p.current)?.workspace_label ?? "";     // the workspace you are in (ADR-032), named at the top
  const [opened, setOpened] = useState<string[]>([]);      // workspaces the person opened in the rail; the current one is always open
  const inWorkspace = route.name === "group" || route.name === "case" || route.name === "board" || route.name === "list";
  const roleWord = (r: string) => ((config.words as { roles?: Record<string, string> }).roles?.[r] ?? r);
  const resettable = !!(config.theme as { resettable?: boolean }).resettable;
  const reset = async () => {
    setPop(false);
    if (!resettable) { onFresh(); return; }
    if (!window.confirm(w.resetConfirm)) return;
    const r = await fetch(BASE + "/api/demo/reset", { method: "POST", credentials: "same-origin" });
    if (r.ok) window.location.href = BASE + "/"; else window.alert(`${w.resetFailed} (${r.status})`);
  };

  return (
    <>
    <nav className={`cf-rail${open ? " open" : ""}`} aria-label={w.menu}>
      {me.shell && <a className="rail-back" data-help="cf.back" href={me.shell}><span aria-hidden="true">←</span> {w.allWorkspaces}</a>}
      <div className="rail-brand">
        <button type="button" className="rail-home" data-help-skip="explained by cf.groups" onClick={() => goClose("/")} aria-label={`${here || w.brand}, ${w.home}`}>
          <span className="rail-mark" aria-hidden="true"><i /></span>
          <span className="rail-name"><b>{here || w.brand}</b>{here && <small>{w.brand}</small>}</span>
        </button>
        {me.demo && <span className="rail-tag" title={w.fictional}>{w.demoTag}</span>}
      </div>
      <Search w={w} cases={(groups.data ?? []).flatMap((g) => g.cases)} go={goClose} />
      <button type="button" className={`nav${route.name === "home" ? " on" : ""}`} data-help="cf.groups" onClick={() => goClose("/")}>
        <HomeIcon /><span className="tx">{w.home}</span>{everywhere > 0 ? <span className="badge">{everywhere}</span> : null}
      </button>

      <div className="rail-groups" data-help="cf.workspaces">
      {groupsOf(places).map((g) => {
        const shut = g.key !== "" && !g.places.some((p) => p.current) && !opened.includes(g.key);
        return (
          <div key={g.key || "all"} className="rail-group">
            {g.key === "" ? (
              <div className="rail-cap" data-help-skip="explained by cf.workspaces">{w.workspaces}</div>
            ) : (
              <button type="button" className="rail-cap rail-cap-toggle" aria-expanded={!shut} data-help-skip="explained by cf.workspaces"
                      onClick={() => setOpened(shut ? [...opened, g.key] : opened.filter((k) => k !== g.key))}>
                {g.label}<i aria-hidden="true">{shut ? "▸" : "▾"}</i>
              </button>
            )}
            {!shut && g.places.map((p) => (
              <button key={p.id} type="button" className={`nav${p.current && inWorkspace ? " on" : ""}`} data-help-skip="explained by cf.workspaces"
                      onClick={() => (p.current ? goClose("/group/you") : p.url ? window.location.assign(p.url) : onFresh(p.id))}>
                <span className="sq" style={{ background: p.color || undefined }} />
                <span className="tx">{p.name}</span>
                {(p.current ? mine : p.count) > 0 ? <span className="n">{p.current ? mine : p.count}</span> : null}
              </button>
            ))}
          </div>
        );
      })}
      </div>
      {me.shell && <a className="nav quiet" data-help="cf.new-workspace" href={`${me.shell.replace(/\/?$/, "/")}workspaces/new`}><span className="tx">{w.newWorkspace}</span></a>}
      {mailDrop ? (
        <label className="nav quiet rail-drop" data-help="cf.drop-in"><span className="tx">{w.dropMail}</span>
          <input type="file" accept=".eml,message/rfc822" hidden onChange={(e) => dropMail(e.target.files?.[0])} /></label>
      ) : mayCreate ? (
        <button type="button" className="nav quiet" data-help="cf.new-case" onClick={() => { onClose(); openNewCase(); }}><span className="tx">+ {newCaseWord(config, w)}</span></button>
      ) : null}
      {madeError && <span className="talk-error">{madeError}</span>}

      <div className="rail-cap">{w.admin}</div>
      {me.team && <button type="button" className={`nav${route.name === "team" || route.name === "teamSession" ? " on" : ""}`} data-help="cf.team" onClick={() => goClose("/team")}><TeamIcon /><span className="tx">{w.team}</span></button>}
      <button type="button" className={`nav${route.name === "rules" ? " on" : ""}`} data-help="cf.rules" onClick={() => goClose("/rules")}><RulebookIcon /><span className="tx">{w.rules}</span>{me.waiting_rules > 0 && <span className="ndot" title={w.ndotRules(me.waiting_rules)} aria-label={w.ndotRules(me.waiting_rules)} />}</button>
      <button type="button" className={`nav${route.name === "signals" ? " on" : ""}`} data-help="cf.patterns" onClick={() => goClose("/signals")}><Pulse /><span className="tx">{w.flagged}</span>{me.waiting_signals > 0 && <span className="ndot" title={w.ndotSignals(me.waiting_signals)} aria-label={w.ndotSignals(me.waiting_signals)} />}</button>
      {(config.theme as { canon?: boolean }).canon && (
        <button type="button" className={`nav${route.name === "house" ? " on" : ""}`} data-help="cf.house" onClick={() => goClose("/kanon")}><Book /><span className="tx">{w.house}</span></button>
      )}
      <button type="button" className={`nav${route.name === "setup" ? " on" : ""}`} data-help="cf.setup" onClick={() => goClose("/setup")}><SetupIcon /><span className="tx">{w.setup}</span></button>

      <button type="button" className={`me${pop ? " on" : ""}`} data-help="cf.person" aria-haspopup="true" aria-expanded={pop} onClick={() => setPop(!pop)}>
        <span className="av">{initials(me.name)}</span>
        <span className="me-tx"><span className="me-name">{me.name}</span><span className="me-role">{me.roles.map(roleWord).join(", ")}</span></span>
        <Updown />
      </button>
    </nav>
    {open && <button type="button" className="rail-scrim" aria-label={w.close} onClick={onClose} />}
    {pop && (
      <>
        <button type="button" className="pop-scrim" aria-label={w.close} onClick={() => setPop(false)} />
        <div className={`me-pop ${side}`} role="menu">
          <div className="me-head"><span className="av lg">{initials(me.name)}</span>
            <span><b>{me.name}</b><small>{me.roles.map(roleWord).join(", ")}</small></span></div>
          {me.demo && humans.length > 1 && (
            <label className="pop-field"><span>{w.signIn}</span>
              <select value={me.person ?? ""} onChange={(e) => { setPop(false); onPerson(e.target.value); }}>
                {humans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select></label>
          )}
          <div className="pop-label">{w.theme}</div>
          <div className="seg" role="group" aria-label={w.theme} data-help="cf.theme">
            {(["light", "dark", "system"] as const).map((t) => (
              <button key={t} type="button" className={theme === t ? "on" : ""} onClick={() => onTheme(t)}>{t === "light" ? w.light : t === "dark" ? w.dark : "System"}</button>
            ))}
          </div>
          <hr />
          <button type="button" className="pop-row" data-help="cf.language" lang={config.lang === "de" ? "en" : "de"} onClick={() => { setPop(false); onLang(config.lang === "de" ? "en" : "de"); }}><Globe /><span>{w.otherLang}</span></button>
          <button type="button" className="pop-row" data-help="cf.sound" aria-pressed={sound} onClick={() => { setSound(!sound); setSoundState(!sound); if (!sound) setTimeout(() => chime(), 30); }}>
            <Speaker on={sound} /><span>{sound ? w.soundOn : w.soundOff}</span></button>
          <button type="button" className="pop-row" data-help-skip="explained by cf.person" onClick={() => { setPop(false); onSwap(); }}><Swap /><span>{side === "left" ? w.sideRight : w.sideLeft}</span></button>
          {me.demo && <button type="button" className="pop-row" data-help-skip="public demo only" onClick={reset}><Restart /><span>{resettable ? w.resetData : w.startOver}</span></button>}
          {me.shell && <a className="pop-row" data-help-skip="explained by cf.back" href={me.shell}><Close /><span>{w.backToShell}</span></a>}
          {!me.demo && <button type="button" className="pop-row" data-help-skip="explained by cf.person" onClick={() => { setPop(false); onSignOut(); }}><Close /><span>{w.signOut}</span></button>}
        </div>
      </>
    )}
    </>
  );
}

// Search: the cases this person can see, by title, number, sender or reference. Ctrl/Cmd+K opens it from anywhere.
function Search({ w, cases, go }: { w: ReturnType<typeof words>; cases: CaseCard[]; go: (p: string) => void }) {
  const [q, setQ] = useState("");
  const [on, setOn] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k" && !document.querySelector(".ask input:focus")) { e.preventDefault(); setOn(true); setTimeout(() => ref.current?.focus(), 0); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const hits = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (!t) return [];
    const seen = new Set<string>();
    return cases.filter((c) => !seen.has(c.id) && seen.add(c.id) && [c.title, c.ref, c.number, c.party, c.external_id, c.label_word].some((x) => (x ?? "").toLowerCase().includes(t))).slice(0, 8);
  }, [q, cases]);
  const mac = /Mac|iPhone|iPad/.test(navigator.platform);
  return (
    <div className="rail-search" data-help="cf.search">
      <SearchIcon />
      <input ref={ref} value={q} placeholder={w.search} onFocus={() => setOn(true)} onBlur={() => setTimeout(() => setOn(false), 150)}
             onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Escape") { setQ(""); ref.current?.blur(); } if (e.key === "Enter" && hits[0]) { setQ(""); go(`/case/${encodeURIComponent(hits[0].id)}`); } }} />
      {!q && <span className="kbd">{mac ? "⌘K" : "Ctrl K"}</span>}
      {on && q.trim() && (
        <div className="search-pop" role="listbox">
          {hits.length === 0 ? <p className="search-none">{w.searchNone}</p> : hits.map((c) => (
            <button key={c.id} type="button" role="option" onMouseDown={(e) => e.preventDefault()} onClick={() => { setQ(""); go(`/case/${encodeURIComponent(c.id)}`); }}>
              <span className="sq" style={{ background: c.tint || undefined }} /><b>{c.title}</b><small>{c.party || c.ref}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
