// The shell: menu and one of three views on the same folders — the cases (list + case), the board, the stacked list.
// Routes, read from the location: /, /case/<id>, /group/<key> (cases), /board, /list, and /doc/<id>/<name> as the reader in its own window.
import { HomeSkeleton, RailSkeleton } from "./components/Skeleton";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, BASE, type PlaceOut } from "./api";
import { Keys } from "./components/Keys";
import { Gate } from "./screens/Gate";
import { Menu } from "./components/Menu";
import { TopBar } from "./components/TopBar";
import { CaseScreen } from "./screens/Case";
import { Setup, SETUP_TABS, type SetupTab } from "./screens/Setup";
import { Team, TeamSessionScreen } from "./screens/Team";
import { Board, Table } from "./screens/Board";
import { Rules } from "./screens/Rules";
import { Signals } from "./screens/Signals";
import { DocWindow } from "./screens/DocWindow";
import { InterviewScreen } from "./screens/Interview";
import { OutcomeScreen } from "./screens/Outcome";
import { OnSiteScreen } from "./screens/OnSite";
import { CanonScreen } from "./screens/Canon";
import { HouseScreen } from "./screens/House";
import { Home } from "./screens/Home";
import { Queue, tabOf, casesOf } from "./screens/Queue";
import { ViewCases, ViewBoard, ViewList } from "./components/Icons";
import { words } from "./words";
import { presenting, setPresenting } from "./moments";

export type Route = { name: "home" } | { name: "case"; id: string; group?: string } | { name: "talk"; id: string } | { name: "outcome"; id: string } | { name: "onsite"; id: string } | { name: "canon"; id: string } | { name: "board" } | { name: "list" } | { name: "rules" } | { name: "signals" } | { name: "team" } | { name: "setup"; tab: SetupTab } | { name: "teamSession"; id: string } | { name: "house" } | { name: "group"; key: string } | { name: "doc"; id: string; file: string };

export function parse(full: string): Route {
  const [bare, search = ""] = full.split("?");
  const path = bare.startsWith(BASE) ? bare.slice(BASE.length) || "/" : bare;
  const group = new URLSearchParams(search).get("g") || undefined;     // the group the case was opened from: the list stays there
  const d = path.match(/^\/doc\/([^/]+)\/([^/]+)/);
  if (d) return { name: "doc", id: decodeURIComponent(d[1]), file: decodeURIComponent(d[2]) };
  const t = path.match(/^\/case\/([^/]+)\/(gespraech|ergebnis|kanon|vorort)/);
  if (t) return { name: t[2] === "gespraech" ? "talk" : t[2] === "kanon" ? "canon" : t[2] === "vorort" ? "onsite" : "outcome", id: decodeURIComponent(t[1]) };
  const m = path.match(/^\/case\/([^/]+)/);
  if (m) return { name: "case", id: decodeURIComponent(m[1]), ...(group ? { group } : {}) };
  if (path.startsWith("/board") || path.startsWith("/workshop")) return { name: "board" };
  if (path === "/lists" || path.startsWith("/lists/")) return { name: "setup", tab: "lists" };     // the value lists live in Setup now; before "/list", which it starts with
  const su = path.match(/^\/setup(?:\/([a-z]+))?/);
  if (su) return { name: "setup", tab: (SETUP_TABS as string[]).includes(su[1] ?? "") ? su[1] as SetupTab : "plugins" };
  if (path.startsWith("/list")) return { name: "list" };
  if (path.startsWith("/rules")) return { name: "rules" };
  if (path.startsWith("/signals")) return { name: "signals" };
  const ts = path.match(/^\/team\/([^/]+)/);
  if (ts) return { name: "teamSession", id: decodeURIComponent(ts[1]) };
  if (path === "/team") return { name: "team" };
  if (path === "/kanon" || path.startsWith("/kanon/")) return { name: "house" };
  const g = path.match(/^\/group\/([^/]+)/);
  if (g) return { name: "group", key: g[1] };
  return { name: "home" };
}

// Inside the cockpit, its Casefile entry opens the workspace you were last in: note it, on the shared origin.
try { if (BASE) localStorage.setItem("casefile-last", BASE + "/"); } catch { /* storage off: the cockpit opens the first workspace */ }

export function useRoute(): [Route, (path: string) => void] {
  const [path, setPath] = useState(window.location.pathname + window.location.search);
  useEffect(() => {
    const on = () => setPath(window.location.pathname + window.location.search);
    window.addEventListener("popstate", on);
    return () => window.removeEventListener("popstate", on);
  }, []);
  const go = (p: string) => {
    window.history.pushState(null, "", BASE + p);
    setPath(p);
    window.scrollTo({ top: 0 });
  };
  return [parse(path), go];
}

export function App() {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, refetchInterval: false });
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups, enabled: !!me.data?.person });
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, refetchInterval: false });
  const [route, go] = useRoute();
  // one choice for the whole shell, kept as `shell-theme` (light | dark | auto) on the shared origin and written only when
  // the person picks one. Until then it is light, whatever the computer is set to (design hand-back, 2026-11-05).
  const readTheme = (): "light" | "dark" | "system" => {
    try {
      const v = localStorage.getItem("shell-theme");
      return v === "dark" ? "dark" : v === "auto" ? "system" : "light";
    } catch { return "light"; }
  };
  const [theme, setThemeState] = useState<"light" | "dark" | "system">(readTheme);
  const setTheme = (t: "light" | "dark" | "system") => {
    setThemeState(t);
    try { localStorage.setItem("shell-theme", t === "system" ? "auto" : t); } catch { /* private window: this visit only */ }
  };
  useEffect(() => {
    if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme;
  }, [theme]);
  useEffect(() => {
    const on = (e: StorageEvent) => { if (e.key === "shell-theme") setThemeState(readTheme()); };
    window.addEventListener("storage", on);
    return () => window.removeEventListener("storage", on);
  }, []);
  const [railOpen, setRailOpen] = useState(false);
  // opening a case reads it: the blue dot goes (request 7); the lists learn it on their next look
  const openedId = route.name === "case" ? route.id : null;
  useEffect(() => {
    if (!openedId || !me.data?.person) return;
    api.seen(openedId).then(() => { qc.invalidateQueries({ queryKey: ["groups"] }); qc.invalidateQueries({ queryKey: ["turns"] }); }).catch(() => { /* a case that is gone */ });
  }, [openedId, me.data?.person]);
  const [side, setSide] = useState<"left" | "right">(() => {
    try { return (localStorage.getItem("cf.side") as "left" | "right") || "left"; } catch { return "left"; }
  });
  useEffect(() => { try { localStorage.setItem("cf.side", side); } catch { /* private window */ } }, [side]);
  useEffect(() => { if (config.data) { document.title = config.data.product; document.documentElement.lang = config.data.lang; } }, [config.data]);

  // What is open right now, for whoever stands beside the person (the cockpit's side panel, ADR-020): the case on
  // the screen — chosen in the URL or, on the start page, the first one of the group — and the document if one is open.
  const wide = !window.matchMedia("(max-width: 900px)").matches;
  const focusId = route.name === "case" || route.name === "doc" || route.name === "talk" || route.name === "outcome" || route.name === "onsite" || route.name === "canon" ? route.id
    : (route.name === "home" || route.name === "group") && wide
      ? (route.name === "group" ? groups.data?.find((g) => g.key === route.key)?.cases[0]?.id : groups.data?.find((g) => g.key === "you")?.cases[0]?.id)
      : undefined;
  const focusCard = focusId ? groups.data?.flatMap((g) => g.cases).find((c) => c.id === focusId) : undefined;
  useEffect(() => {
    const detail = focusCard
      ? { case: focusCard.id, item: `${focusCard.stage}/${focusCard.id}`, title: focusCard.title, stage: focusCard.stage_word,
          label: focusCard.label_word, view: route.name, document: route.name === "doc" ? route.file : undefined, application: config.data?.product }
      : { view: route.name, application: config.data?.product };
    (window as unknown as { casefileFocus?: unknown }).casefileFocus = detail;
    window.dispatchEvent(new CustomEvent("casefile:focus", { detail }));
  }, [focusCard?.id, focusCard?.stage, focusCard?.title, route.name, route.name === "doc" ? route.file : "", config.data?.product]);

  // the director (components/Director) asks for fresh data after the AI finished a step it waited for
  useEffect(() => {
    const on = () => { qc.invalidateQueries(); };
    window.addEventListener("casefile:refresh", on);
    return () => window.removeEventListener("casefile:refresh", on);
  }, [qc]);

  // presenting: Shift+Alt+P hides the demo's furniture; Shift+Alt+1…9 switches to the n-th person of a sample world
  useEffect(() => {
    const onKey = async (e: KeyboardEvent) => {
      if (!e.shiftKey || !e.altKey) return;
      if (e.code === "KeyP") { e.preventDefault(); setPresenting(!presenting()); return; }
      const n = /^Digit([1-9])$/.exec(e.code)?.[1];
      const humans = config.data?.people.filter((p) => p.kind === "human") ?? [];
      if (n && me.data?.open_identity && humans[Number(n) - 1]) { e.preventDefault(); await api.signIn(humans[Number(n) - 1].id); qc.invalidateQueries(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [config.data, me.data?.open_identity, qc]);

  // the frame at once, in its final place, while the shell waits for who you are and how this workspace is set up; the
  // rail's content and the words follow with the configuration (SW-2026-003)
  if (me.isLoading || config.isLoading) {
    if (route.name === "doc") return null;
    return (
      <div className={`app ${side}`} aria-busy="true">
        <nav className="cf-rail" aria-hidden="true"><RailSkeleton /></nav>
        <div className="main-col">
          <span className="sr">{words(navigator.language.slice(0, 2)).loading}</span>
          {route.name === "home" && <main className="home-wrap"><div className="home"><section className="home-main"><HomeSkeleton /></section></div></main>}
        </div>
      </div>
    );
  }
  if (!config.data) return <div className="gate"><p className="empty">The core is not reachable.</p></div>;
  const lang = config.data.lang;
  if (!me.data?.person) {
    return <Gate config={config.data} me={me.data} onSignedIn={() => qc.invalidateQueries()} />;
  }
  // a fresh sandbox or the other world: the cookie changes, then every live query reloads against it (removing them instead left the observers on the old world for one round)
  // Home across workspaces: a row in another workspace opens there (inside a shell at its address; in the demo the visitor's sandbox of that world)
  const onPlace = async (place: PlaceOut, path: string) => {
    if (place.current) { go(path); return; }
    if (place.url) { window.location.assign(place.url.replace(/\/?$/, "/") + path.replace(/^\//, "")); return; }
    await api.demoSession(place.id);
    qc.removeQueries({ queryKey: ["case"] });
    await Promise.all([qc.resetQueries({ queryKey: ["groups"] }), qc.resetQueries({ queryKey: ["turns"] }), qc.invalidateQueries({ queryKey: ["me"] }), qc.invalidateQueries({ queryKey: ["config"] })]);
    go(path);
  };
  const onFresh = async (world?: string) => { await api.demoSession(world); go("/"); qc.removeQueries({ queryKey: ["case"] }); await Promise.all([qc.resetQueries({ queryKey: ["groups"] }), qc.resetQueries({ queryKey: ["turns"] }), qc.invalidateQueries({ queryKey: ["me"] }), qc.invalidateQueries({ queryKey: ["config"] })]); };
  const onPerson = async (person: string) => { await api.signIn(person); qc.invalidateQueries(); };
  const onLang = async (l: string) => { await api.setLang(l); await qc.invalidateQueries(); };
  const w = words(lang, ((config.data?.theme as Record<string, unknown> | undefined)?.words as Record<string, Record<string, unknown>> | undefined)?.[lang]);
  const tab = tabOf(route.name === "group" ? route.key : route.name === "case" ? route.group : undefined);
  const first = route.name === "group" ? casesOf(groups.data, tab)[0]?.id : undefined;
  const isPhone = window.matchMedia("(max-width: 900px)").matches;
  const showList = !isPhone || route.name === "group";
  const showMain = !isPhone || route.name !== "group";

  if (route.name === "doc") return <div className="shell"><DocWindow id={route.id} name={route.file} config={config.data} w={w} /></div>;

  const here = me.data.places?.find((p) => p.current)?.name ?? config.data.product;
  const inWorkspace = route.name === "group" || route.name === "case" || route.name === "board" || route.name === "list";
  const crumb = route.name === "home" ? w.home : route.name === "rules" ? w.rules : route.name === "signals" ? w.flagged : route.name === "team" ? w.team : route.name === "setup" ? w.setup
    : route.name === "house" ? w.house : here;
  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  const view = route.name === "board" ? "board" : route.name === "list" ? "list" : "cases";
  const views = inWorkspace ? (
    <span className="bar-views" role="tablist" aria-label={w.views} data-help="cf.views">
      <button type="button" role="tab" aria-selected={view === "cases"} className={view === "cases" ? "on" : ""} onClick={() => go("/group/you")} title={w.casesView}><ViewList /></button>
      <button type="button" role="tab" aria-selected={view === "board"} className={view === "board" ? "on" : ""} onClick={() => go("/board")} title={w.board}><ViewBoard /></button>
      <button type="button" role="tab" aria-selected={view === "list"} className={view === "list" ? "on" : ""} onClick={() => go("/list")} title={w.stacked}><ViewCases /></button>
    </span>
  ) : null;

  return (
    <div className={`app ${side}`} style={{ viewTransitionName: (/\/w\/([^/]+)/.exec(BASE)?.[1] ? `ws-${/\/w\/([^/]+)/.exec(BASE)![1]}` : undefined) }}>
      <Menu config={config.data} me={me.data} route={route} go={go} side={side} onSwap={() => setSide(side === "left" ? "right" : "left")} w={w}
            onSignOut={async () => { await api.signOut(); if (me.data?.shell) { window.location.href = `${me.data.shell.replace(/\/?$/, "/")}logout`; return; } qc.invalidateQueries(); }} onFresh={onFresh} onPerson={onPerson}
            theme={theme} onTheme={setTheme} onLang={onLang} open={railOpen} onClose={() => setRailOpen(false)} />
      <Keys w={w} onTheme={() => setTheme(dark ? "light" : "dark")} />
      <div className="main-col">
        {!(route.name === "group" || route.name === "board" || route.name === "list" || route.name === "teamSession" || (route.name === "case" && !isPhone)) && <TopBar config={config.data} me={me.data} w={w} crumb={crumb} canAsk={route.name === "case"} dark={dark}
                onTheme={() => setTheme(dark ? "light" : "dark")} onMenu={() => setRailOpen(true)} views={views} />}
        {route.name === "home" ? (
          <Home config={config.data} me={me.data} go={go} open={onPlace} w={w} />
        ) : (
        <div className="shell">
          {route.name === "talk" ? (
            <InterviewScreen id={route.id} config={config.data} go={go} w={w} />
          ) : route.name === "canon" ? (
            <CanonScreen id={route.id} config={config.data} go={go} w={w} />
          ) : route.name === "outcome" ? (
            <OutcomeScreen id={route.id} config={config.data} go={go} w={w} />
          ) : route.name === "onsite" ? (
            <OnSiteScreen id={route.id} config={config.data} go={go} w={w} />
          ) : route.name === "board" ? (
            <Board config={config.data} go={go} w={w} views={views} />
          ) : route.name === "list" ? (
            <Table config={config.data} go={go} w={w} views={views} />
          ) : route.name === "rules" ? (
            <Rules config={config.data} w={w} lang={lang} />
          ) : route.name === "house" ? (
            <HouseScreen config={config.data} go={go} w={w} />
          ) : route.name === "signals" ? (
            <Signals config={config.data} go={go} w={w} lang={lang} />
          ) : route.name === "setup" ? (
            <Setup me={me.data} tab={route.tab} go={go} w={w} />
          ) : route.name === "team" ? (
            <Team config={config.data} me={me.data} go={go} w={w} />
          ) : route.name === "teamSession" ? (
            <TeamSessionScreen id={route.id} me={me.data} go={go} w={w} />
          ) : (
            <div className="ws">
              {showList && <Queue tab={tab} openId={route.name === "case" ? route.id : first} go={go} w={w} lang={lang} place={here} views={views} onMenu={() => setRailOpen(true)} />}
              {showMain && route.name === "case" && <CaseScreen id={route.id} config={config.data} me={me.data} go={go} w={w} tab={tab} />}
              {showMain && route.name !== "case" && !isPhone && (first ? <CaseScreen id={first} config={config.data} me={me.data} go={go} w={w} tab={tab} /> : <div className="ws-case"><main className="center" /></div>)}
            </div>
          )}
        </div>
        )}
      </div>
    </div>
  );
}
