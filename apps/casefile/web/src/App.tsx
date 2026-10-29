// The surface: a bar and one column (ADR-024, step 2 — the shell fell). Routes, read from the location: / (the stack of this
// workspace), /case/<id> (one gate of it), /group/<key> (a group as rows), the ways into a case (/case/<id>/gespraech|ergebnis|
// vorort|kanon), the second views (/board, /list), /rules, /signals, /kanon, and /doc/<id>/<name> as the reader in its own window.
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, BASE } from "./api";
import { Gate } from "./screens/Gate";
import { TopBar, type Side, type Theme } from "./components/TopBar";
import { GroupScreen, Place, Stack, ident } from "./screens/Stack";
import { Board } from "./screens/Board";
import { Stacked } from "./screens/Stacked";
import { Rules } from "./screens/Rules";
import { Signals } from "./screens/Signals";
import { DocWindow } from "./screens/DocWindow";
import { InterviewScreen } from "./screens/Interview";
import { OutcomeScreen } from "./screens/Outcome";
import { OnSiteScreen } from "./screens/OnSite";
import { CanonScreen } from "./screens/Canon";
import { HouseScreen } from "./screens/House";
import { words } from "./words";
import { presenting, setPresenting } from "./moments";

export type Route = { name: "home" } | { name: "case"; id: string; group?: string } | { name: "talk"; id: string } | { name: "outcome"; id: string } | { name: "onsite"; id: string } | { name: "canon"; id: string } | { name: "board" } | { name: "list" } | { name: "rules" } | { name: "signals" } | { name: "house" } | { name: "group"; key: string } | { name: "doc"; id: string; file: string };

export function parse(full: string): Route {
  const [bare, search = ""] = full.split("?");
  const path = bare.startsWith(BASE) ? bare.slice(BASE.length) || "/" : bare;
  const group = new URLSearchParams(search).get("g") || undefined;     // the group the case was opened from (older links keep working)
  const d = path.match(/^\/doc\/([^/]+)\/([^/]+)/);
  if (d) return { name: "doc", id: decodeURIComponent(d[1]), file: decodeURIComponent(d[2]) };
  const t = path.match(/^\/case\/([^/]+)\/(gespraech|ergebnis|kanon|vorort)/);
  if (t) return { name: t[2] === "gespraech" ? "talk" : t[2] === "kanon" ? "canon" : t[2] === "vorort" ? "onsite" : "outcome", id: decodeURIComponent(t[1]) };
  const m = path.match(/^\/case\/([^/]+)/);
  if (m) return { name: "case", id: decodeURIComponent(m[1]), ...(group ? { group } : {}) };
  if (path.startsWith("/board") || path.startsWith("/workshop")) return { name: "board" };
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
    document.querySelector(".stack-main")?.scrollTo({ top: 0 });
  };
  return [parse(path), go];
}

export function App() {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, refetchInterval: false });
  const groups = useQuery({ queryKey: ["groups"], queryFn: api.groups, enabled: !!me.data?.person });
  const turns = useQuery({ queryKey: ["turns"], queryFn: api.turns, enabled: !!me.data?.person });
  const config = useQuery({ queryKey: ["config"], queryFn: api.config, refetchInterval: false });
  const [route, go] = useRoute();
  const [theme, setTheme] = useState<Theme>(() => {
    try { return (localStorage.getItem("cf.theme") as Theme) || "system"; } catch { return "system"; }
  });
  useEffect(() => {
    try { localStorage.setItem("cf.theme", theme); } catch { /* private window */ }
    if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme;
  }, [theme]);
  const [side, setSide] = useState<Side>(() => {
    try { return (localStorage.getItem("cf.side") as Side) || "right"; } catch { return "right"; }
  });
  useEffect(() => { try { localStorage.setItem("cf.side", side); } catch { /* private window */ } }, [side]);
  useEffect(() => { if (config.data) { document.title = config.data.product; document.documentElement.lang = config.data.lang; } }, [config.data]);

  // What is open right now, for whoever stands beside the person (the cockpit's side panel, ADR-020): the case on the screen —
  // chosen in the URL or, on the stack, its first gate — and the document if one is open.
  const cards = groups.data?.flatMap((g) => g.cases) ?? [];
  const cardOf = (id: string) => cards.find((c) => c.id === id);
  const firstGate = turns.data?.find((t) => t.turn.kind !== "nudge")?.case.id;
  const focusId = "id" in route && route.name !== "doc" ? route.id : route.name === "doc" ? route.id
    : route.name === "home" ? firstGate : route.name === "group" ? groups.data?.find((g) => g.key === route.key)?.cases[0]?.id : undefined;
  const focusCard = focusId ? cardOf(focusId) : undefined;
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
  const onSignOut = async () => { await api.signOut(); if (me.data?.shell) { window.location.href = `${me.data.shell.replace(/\/?$/, "/")}logout`; return; } qc.invalidateQueries(); };
  const w = words(lang, ((config.data?.theme as Record<string, unknown> | undefined)?.words as Record<string, Record<string, unknown>> | undefined)?.[lang]);
  const cfg = config.data, who = me.data;

  if (route.name === "doc") return <div className="shell"><DocWindow id={route.id} name={route.file} config={cfg} w={w} /></div>;

  // the place line over a screen that is not the stack: workspace › (case ›) here (rule 6)
  const inCase = (id: string, word: string) => [{ text: cardOf(id) ? ident(cardOf(id)!) : id, to: `/case/${encodeURIComponent(id)}` }, { text: word }];
  const column = (parts: { text: string; to?: string }[], screen: React.ReactNode) => (
    <div className="col"><Place config={cfg} go={go} parts={parts} />{screen}</div>
  );

  return (
    <>
    <TopBar config={cfg} me={who} w={w} side={side} onSide={setSide} onFresh={onFresh} onPerson={onPerson} onLang={onLang} theme={theme} onTheme={setTheme} onSignOut={onSignOut} />
    <div className="shell" style={{ viewTransitionName: (/\/w\/([^/]+)/.exec(BASE)?.[1] ? `ws-${/\/w\/([^/]+)/.exec(BASE)![1]}` : undefined) }}>
      {route.name === "home" ? (
        <Stack config={cfg} me={who} go={go} w={w} onFresh={onFresh} />
      ) : route.name === "case" ? (
        <Stack config={cfg} me={who} go={go} w={w} id={route.id} onFresh={onFresh} />
      ) : route.name === "group" ? (
        <GroupScreen config={cfg} go={go} w={w} groupKey={route.key} />
      ) : route.name === "talk" ? (
        column(inCase(route.id, w.talkOpen), <InterviewScreen id={route.id} config={cfg} go={go} w={w} />)
      ) : route.name === "canon" ? (
        column(inCase(route.id, w.house), <CanonScreen id={route.id} config={cfg} go={go} w={w} />)
      ) : route.name === "outcome" ? (
        column(inCase(route.id, w.outcomeOpen), <OutcomeScreen id={route.id} config={cfg} go={go} w={w} />)
      ) : route.name === "onsite" ? (
        column(inCase(route.id, w.onsite), <OnSiteScreen id={route.id} config={cfg} go={go} w={w} />)
      ) : route.name === "board" ? (
        column([{ text: w.board }], <Board config={cfg} go={go} w={w} />)
      ) : route.name === "list" ? (
        column([{ text: w.stacked }], <Stacked config={cfg} go={go} w={w} />)
      ) : route.name === "rules" ? (
        column([{ text: w.rules }], <Rules config={cfg} w={w} />)
      ) : route.name === "house" ? (
        column([{ text: w.house }], <HouseScreen config={cfg} go={go} w={w} />)
      ) : (
        column([{ text: w.signals }], <Signals config={cfg} go={go} w={w} />)
      )}
    </div>
    </>
  );
}
