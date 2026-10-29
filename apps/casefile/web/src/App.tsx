// The shell: menu and one of three views on the same folders — the cases (list + case), the board, the stacked list.
// Routes, read from the location: /, /case/<id>, /group/<key> (cases), /board, /list, and /doc/<id>/<name> as the reader in its own window.
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, BASE } from "./api";
import { Gate } from "./screens/Gate";
import { Menu } from "./components/Menu";
import { TopBar } from "./components/TopBar";
import { List } from "./screens/List";
import { CaseScreen } from "./screens/Case";
import { Board } from "./screens/Board";
import { Stacked } from "./screens/Stacked";
import { Rules } from "./screens/Rules";
import { Lists } from "./screens/Lists";
import { Signals } from "./screens/Signals";
import { DocWindow } from "./screens/DocWindow";
import { InterviewScreen } from "./screens/Interview";
import { OutcomeScreen } from "./screens/Outcome";
import { OnSiteScreen } from "./screens/OnSite";
import { CanonScreen } from "./screens/Canon";
import { HouseScreen } from "./screens/House";
import { words } from "./words";
import { presenting, setPresenting } from "./moments";

export type Route = { name: "home" } | { name: "case"; id: string; group?: string } | { name: "talk"; id: string } | { name: "outcome"; id: string } | { name: "onsite"; id: string } | { name: "canon"; id: string } | { name: "board" } | { name: "list" } | { name: "rules" } | { name: "lists" } | { name: "signals" } | { name: "house" } | { name: "group"; key: string } | { name: "doc"; id: string; file: string };

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
  if (path === "/lists" || path.startsWith("/lists/")) return { name: "lists" };     // before "/list", which it starts with
  if (path.startsWith("/list")) return { name: "list" };
  if (path.startsWith("/rules")) return { name: "rules" };
  if (path.startsWith("/signals")) return { name: "signals" };
  if (path === "/kanon" || path.startsWith("/kanon/")) return { name: "house" };
  const g = path.match(/^\/group\/([^/]+)/);
  if (g) return { name: "group", key: g[1] };
  return { name: "home" };
}

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
  // one choice for the whole shell: the cockpit keeps it as `cockpit-theme` (light | dark | auto), same origin; the app reads
  // that first, writes both, and follows a change made in another tab
  const readTheme = (): "light" | "dark" | "system" => {
    try {
      const shell = localStorage.getItem("cockpit-theme");
      if (shell) return shell === "auto" ? "system" : (shell as "light" | "dark");
      return (localStorage.getItem("cf.theme") as "light" | "dark" | "system") || "system";
    } catch { return "system"; }
  };
  const [theme, setTheme] = useState<"light" | "dark" | "system">(readTheme);
  useEffect(() => {
    try { localStorage.setItem("cf.theme", theme); localStorage.setItem("cockpit-theme", theme === "system" ? "auto" : theme); } catch { /* private window */ }
    if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme;
  }, [theme]);
  useEffect(() => {
    const on = (e: StorageEvent) => { if (e.key === "cockpit-theme" || e.key === "cf.theme") setTheme(readTheme()); };
    window.addEventListener("storage", on);
    return () => window.removeEventListener("storage", on);
  }, []);
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

  if (me.isLoading || config.isLoading) return null;
  if (!config.data) return <div className="gate"><p className="empty">The core is not reachable.</p></div>;
  const lang = config.data.lang;
  if (!me.data?.person) {
    return <Gate config={config.data} me={me.data} onSignedIn={() => qc.invalidateQueries()} />;
  }
  // a fresh sandbox or the other world: the cookie changes, then every live query reloads against it (removing them instead left the observers on the old world for one round)
  const onFresh = async (world?: string) => { await api.demoSession(world); go("/"); qc.removeQueries({ queryKey: ["case"] }); await Promise.all([qc.resetQueries({ queryKey: ["groups"] }), qc.resetQueries({ queryKey: ["turns"] }), qc.invalidateQueries({ queryKey: ["me"] }), qc.invalidateQueries({ queryKey: ["config"] })]); };
  const onPerson = async (person: string) => { await api.signIn(person); qc.invalidateQueries(); };
  const onLang = async (l: string) => { await api.setLang(l); await qc.invalidateQueries(); };
  const w = words(lang, ((config.data?.theme as Record<string, unknown> | undefined)?.words as Record<string, Record<string, unknown>> | undefined)?.[lang]);
  const first = route.name === "group" ? groups.data?.find((g) => g.key === route.key)?.cases[0]?.id : groups.data?.find((g) => g.key === "you")?.cases[0]?.id;
  const isPhone = window.matchMedia("(max-width: 900px)").matches;
  const showList = !isPhone || route.name === "home" || route.name === "group";
  const showMain = !isPhone || route.name !== "home";

  if (route.name === "doc") return <div className="shell"><DocWindow id={route.id} name={route.file} config={config.data} w={w} /></div>;

  return (
    <>
    <TopBar config={config.data} me={me.data} w={w} onSwap={() => setSide(side === "left" ? "right" : "left")} onFresh={() => onFresh()} />
    <div className={`shell ${side}`} style={{ viewTransitionName: (/\/w\/([^/]+)/.exec(BASE)?.[1] ? `ws-${/\/w\/([^/]+)/.exec(BASE)![1]}` : undefined) }}>
      <Menu config={config.data} me={me.data} route={route} go={go} side={side} onSwap={() => setSide(side === "left" ? "right" : "left")} w={w}
            onSignOut={async () => { await api.signOut(); if (me.data?.shell) { window.location.href = `${me.data.shell.replace(/\/?$/, "/")}logout`; return; } qc.invalidateQueries(); }} onFresh={onFresh} onPerson={onPerson}
            theme={theme} onTheme={setTheme} onLang={onLang} />
      {route.name === "talk" ? (
        <InterviewScreen id={route.id} config={config.data} go={go} w={w} />
      ) : route.name === "canon" ? (
        <CanonScreen id={route.id} config={config.data} go={go} w={w} />
      ) : route.name === "outcome" ? (
        <OutcomeScreen id={route.id} config={config.data} go={go} w={w} />
      ) : route.name === "onsite" ? (
        <OnSiteScreen id={route.id} config={config.data} go={go} w={w} />
      ) : route.name === "board" ? (
        <Board config={config.data} go={go} w={w} />
      ) : route.name === "list" ? (
        <Stacked config={config.data} go={go} w={w} />
      ) : route.name === "rules" ? (
        <Rules config={config.data} w={w} />
      ) : route.name === "lists" ? (
        <Lists config={config.data} w={w} />
      ) : route.name === "house" ? (
        <HouseScreen config={config.data} go={go} w={w} />
      ) : route.name === "signals" ? (
        <Signals config={config.data} go={go} w={w} />
      ) : (
        <>
          {showList && <List config={config.data} route={route} go={go} w={w} me={me.data.person ?? ""} />}
          {showMain && route.name === "case" && <CaseScreen id={route.id} config={config.data} me={me.data} go={go} w={w} />}
          {showMain && route.name !== "case" && !isPhone && (first ? <CaseScreen id={first} config={config.data} me={me.data} go={go} w={w} /> : <main className="main" />)}
        </>
      )}
    </div>
    </>
  );
}
