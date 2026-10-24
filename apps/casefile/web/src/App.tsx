// The shell: menu and one of three views on the same folders — the cases (list + case), the board, the stacked list.
// Routes, read from the location: /, /case/<id>, /group/<key> (cases), /board, /list, and /doc/<id>/<name> as the reader in its own window.
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, BASE } from "./api";
import { Gate } from "./screens/Gate";
import { Menu } from "./components/Menu";
import { List } from "./screens/List";
import { CaseScreen } from "./screens/Case";
import { Board } from "./screens/Board";
import { Stacked } from "./screens/Stacked";
import { Rules } from "./screens/Rules";
import { Signals } from "./screens/Signals";
import { DocWindow } from "./screens/DocWindow";
import { words } from "./words";

export type Route = { name: "home" } | { name: "case"; id: string } | { name: "board" } | { name: "list" } | { name: "rules" } | { name: "signals" } | { name: "group"; key: string } | { name: "doc"; id: string; file: string };

export function parse(full: string): Route {
  const path = full.startsWith(BASE) ? full.slice(BASE.length) || "/" : full;
  const d = path.match(/^\/doc\/([^/]+)\/([^/]+)/);
  if (d) return { name: "doc", id: decodeURIComponent(d[1]), file: decodeURIComponent(d[2]) };
  const m = path.match(/^\/case\/([^/]+)/);
  if (m) return { name: "case", id: decodeURIComponent(m[1]) };
  if (path.startsWith("/board") || path.startsWith("/workshop")) return { name: "board" };
  if (path.startsWith("/list")) return { name: "list" };
  if (path.startsWith("/rules")) return { name: "rules" };
  if (path.startsWith("/signals")) return { name: "signals" };
  const g = path.match(/^\/group\/([^/]+)/);
  if (g) return { name: "group", key: g[1] };
  return { name: "home" };
}

export function useRoute(): [Route, (path: string) => void] {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const on = () => setPath(window.location.pathname);
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
  const [theme, setTheme] = useState<"light" | "dark" | "system">(() => {
    try { return (localStorage.getItem("cf.theme") as "light" | "dark" | "system") || "system"; } catch { return "system"; }
  });
  useEffect(() => {
    try { localStorage.setItem("cf.theme", theme); } catch { /* private window */ }
    if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme;
  }, [theme]);
  const [side, setSide] = useState<"left" | "right">(() => {
    try { return (localStorage.getItem("cf.side") as "left" | "right") || "left"; } catch { return "left"; }
  });
  useEffect(() => { try { localStorage.setItem("cf.side", side); } catch { /* private window */ } }, [side]);
  useEffect(() => { if (config.data) { document.title = config.data.product; document.documentElement.lang = config.data.lang; } }, [config.data]);

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
  const w = words(lang);
  const first = route.name === "group" ? groups.data?.find((g) => g.key === route.key)?.cases[0]?.id : groups.data?.find((g) => g.key === "you")?.cases[0]?.id;
  const isPhone = window.matchMedia("(max-width: 900px)").matches;
  const showList = !isPhone || route.name === "home" || route.name === "group";
  const showMain = !isPhone || route.name !== "home";

  if (route.name === "doc") return <div className="shell"><DocWindow id={route.id} name={route.file} config={config.data} w={w} /></div>;

  return (
    <div className={`shell ${side}`}>
      <Menu config={config.data} me={me.data} route={route} go={go} side={side} onSwap={() => setSide(side === "left" ? "right" : "left")} w={w}
            onSignOut={async () => { await api.signOut(); qc.invalidateQueries(); }} onFresh={onFresh} onPerson={onPerson}
            theme={theme} onTheme={setTheme} onLang={onLang} />
      {route.name === "board" ? (
        <Board config={config.data} go={go} w={w} />
      ) : route.name === "list" ? (
        <Stacked config={config.data} go={go} w={w} />
      ) : route.name === "rules" ? (
        <Rules config={config.data} w={w} />
      ) : route.name === "signals" ? (
        <Signals config={config.data} go={go} w={w} />
      ) : (
        <>
          {showList && <List config={config.data} route={route} go={go} w={w} />}
          {showMain && route.name === "case" && <CaseScreen id={route.id} config={config.data} me={me.data} go={go} w={w} />}
          {showMain && route.name !== "case" && !isPhone && (first ? <CaseScreen id={first} config={config.data} me={me.data} go={go} w={w} /> : <main className="main" />)}
        </>
      )}
    </div>
  );
}
