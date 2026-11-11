// The typed client over the core's API. Types come from the core (scripts/types.sh → api.d.ts), never from here.
import type { components } from "./api-types";

export type CaseCard = components["schemas"]["CaseCard"];
export type CaseView = components["schemas"]["CaseView"];
export type Turn = components["schemas"]["Turn"];
export type TurnOut = components["schemas"]["TurnOut"];
export type GroupOut = components["schemas"]["GroupOut"];
export type StageOut = components["schemas"]["StageOut"];
export type RulesOut = components["schemas"]["RulesOut"];
export type RuleModule = components["schemas"]["RuleModule"];
export type RuleArea = components["schemas"]["RuleArea"];
export type ModuleHistory = components["schemas"]["ModuleHistory"];
export type SignalOut = components["schemas"]["SignalOut"];
export type StepResult = components["schemas"]["StepResult"];
export type MeOut = components["schemas"]["MeOut"];
export type ConfigView = components["schemas"]["ConfigView"];
export type Entry = components["schemas"]["Entry"];
export type SlotView = components["schemas"]["SlotView"];
export type RhythmOut = components["schemas"]["RhythmOut"];
export type ListView = components["schemas"]["ListView"];
export type ListEntryView = components["schemas"]["ListEntryView"];
export type ListsOut = components["schemas"]["ListsOut"];
export type ListChangeOut = components["schemas"]["ListChangeOut"];
export type PlaceOut = components["schemas"]["PlaceOut"];
export type SetupOut = components["schemas"]["SetupOut"];
export type HomePlace = components["schemas"]["HomePlace"];
export type SetupItem = components["schemas"]["SetupItem"];
export type PreviewOut = components["schemas"]["PreviewOut"];

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(typeof body === "object" && body && "reason" in body ? String((body as { reason: string }).reason) : `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

// Where this surface is served: the core writes it into index.html per mount (one build, many prefixes);
// without the tag, the build-time BASE_URL.
const metaBase = typeof document !== "undefined" ? document.querySelector<HTMLMetaElement>('meta[name="cf-base"]')?.content : undefined;
export const BASE = (metaBase ?? import.meta.env.BASE_URL ?? "/").replace(/\/$/, "");

async function call<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
    credentials: "same-origin",
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

export const api = {
  me: () => call<MeOut>("GET", "/api/me"),
  signIn: (person: string) => call<MeOut>("POST", "/api/session", { person }),
  signOut: () => call<{ ok: boolean }>("DELETE", "/api/session"),
  setLang: (lang: string) => call<{ ok: boolean; lang: string }>("POST", "/api/session/lang", { lang }),
  demoSession: (world?: string) => call<MeOut>("POST", "/api/demo/session", { world: world ?? null }),
  config: () => call<ConfigView>("GET", "/api/config"),
  turns: () => call<TurnOut[]>("GET", "/api/me/turns"),
  home: () => call<HomePlace[]>("GET", "/api/home"),
  /** Inside a shell, another workspace's part of Home, at its own address (same origin, the shell's login). */
  homeAt: async (url: string): Promise<HomePlace[]> => {
    const res = await fetch(`${url.replace(/\/?$/, "/")}api/home`, { credentials: "same-origin" });
    if (!res.ok) return [];
    const parts = (await res.json()) as HomePlace[];
    return parts.map((p) => ({ ...p, place: { ...p.place, url: url.replace(/\/?$/, "/"), current: false } }));
  },
  groups: () => call<GroupOut[]>("GET", "/api/cases"),
  stages: () => call<StageOut[]>("GET", "/api/stages"),
  rules: () => call<RulesOut>("GET", "/api/rules"),
  module: (id: string) => call<ModuleHistory>("GET", `/api/rulebook/${encodeURIComponent(id)}`),
  moduleDraft: (id: string, body: { text: string; title?: string; kind?: string; areas?: string[] | null; note?: string }) =>
    call<ModuleHistory>("POST", `/api/rulebook/${encodeURIComponent(id)}/draft`, body),
  moduleApprove: (id: string) => call<ModuleHistory>("POST", `/api/rulebook/${encodeURIComponent(id)}/approve`),
  moduleReject: (id: string, reason: string) => call<ModuleHistory>("POST", `/api/rulebook/${encodeURIComponent(id)}/reject`, { reason }),
  moduleRetire: (id: string, note: string) => call<ModuleHistory>("POST", `/api/rulebook/${encodeURIComponent(id)}/retire`, { note }),
  rhythm: () => call<RhythmOut>("GET", "/api/me/rhythm"),
  signals: () => call<SignalOut[]>("GET", "/api/signals"),
  setup: () => call<SetupOut>("GET", "/api/setup"),
  addSchema: (body: { key: string; word: Record<string, string>; based_on: string; step_id: string }) => call<SetupOut>("POST", "/api/setup/schemas", body),
  signalStatus: (id: string, status: "offen" | "in_pruefung" | "erledigt") => call<SignalOut>("POST", `/api/signals/${encodeURIComponent(id)}/status`, { status }),
  case: (id: string) => call<CaseView>("GET", `/api/cases/${encodeURIComponent(id)}`),
  step: (id: string, action: string, step_id: string, payload: Record<string, unknown> = {}) =>
    call<StepResult>("POST", `/api/cases/${encodeURIComponent(id)}/steps`, { action, step_id, payload }),
  entry: (id: string, body: { kind: "note" | "answer" | "done"; step_id: string; text?: string; for?: string; resolves?: string; title?: string }) =>
    call<StepResult>("POST", `/api/cases/${encodeURIComponent(id)}/entries`, body),
  run: (id: string, body: { skill?: string; note: string; request_id: string }) =>
    call<StepResult>("POST", `/api/cases/${encodeURIComponent(id)}/runs`, body),
  seen: (id: string, unread = false) => call<{ case: string; unread: boolean }>("POST", `/api/cases/${encodeURIComponent(id)}/seen`, { unread }),
  lists: () => call<ListsOut>("GET", "/api/lists"),
  putList: (body: { id: string; word: Record<string, string>; field?: string; on_create?: boolean; step_id: string }) => call<ListChangeOut>("POST", "/api/lists", body),
  putEntry: (list: string, body: { key: string; word?: Record<string, string>; color?: string; description?: string; status?: string; step_id: string }) =>
    call<ListChangeOut>("POST", `/api/lists/${encodeURIComponent(list)}/entries`, body),
  asset: (id: string, slot: string, step_id: string, file: File) => {
    const fd = new FormData();
    fd.append("slot", slot);
    fd.append("step_id", step_id);
    fd.append("file", file);
    return call<{ name: string; slot: string; step: StepResult }>("POST", `/api/cases/${encodeURIComponent(id)}/assets`, undefined, fd);
  },
  editPreview: (id: string, file: string, text: string) => call<PreviewOut>("POST", `/api/cases/${encodeURIComponent(id)}/edit/preview`, { file, text }),
  editSave: (id: string, file: string, text: string, step_id: string) =>
    call<{ name: string; slot: string; step: StepResult }>("POST", `/api/cases/${encodeURIComponent(id)}/edit`, { file, text, step_id }),
};

// A conversation (Gatehouse): the pack, my answers, the helper's file for me, how far everyone is.
export type Question = { id: string; text: string; why: string };
export type Block = { id: string; title: string; canon: string; lead: string; questions: Question[] };
export type Trigger = { cue: string; ask: string; match: string[] };
export type Pack = { id: string; name: string; version: string; anchor: { ask?: string; placeholder?: string; why?: string }; blocks: Block[]; triggers: Trigger[] };
export type Answer = { text: string; marker: "is" | "should" | "open"; at?: string };
export type Helper = {
  followups?: { id: string; question: string; ask: string }[];
  tensions?: { id: string; questions: string[]; text: string }[];
  drafts?: { block: string; text: string; marker?: string; source?: string }[];
};
export type Interview = {
  case: string; title: string; pack: Pack; me: string; can_answer: boolean; anchor: string;
  answers: Record<string, Answer>; followup_answers: Record<string, { text: string }>; helper: Helper; helper_running: boolean; done: boolean;
  respondents: { id: string; name: string; answered: number; total: number; done: boolean; me: boolean }[];
  sees_all: boolean; others: number; others_done: number;
};
export type Source = { person: string; question: string; quote: string };
export type Line = { id: string; block: string; text: string; marker?: string; sources?: Source[]; decision: { verdict?: "accept" | "edit" | "reject"; text?: string; by?: string; at?: string } };
export type Findings = {
  summary?: string;
  path?: { step: string; gate?: string | null; missing_gate?: boolean; note?: string; source?: Source }[];
  roles?: { name: string; decides: string; single_point?: boolean; source?: Source }[];
  tensions?: { title: string; said: Source; done: Source }[];
  divergences?: { topic: string; views: Source[] }[];
  limits?: string;
};
export type Outcome = {
  case: string; title: string; stage_word: string; blocks: { id: string; title: string; canon: string }[]; findings: Findings; lines: Line[];
  can_decide: boolean; open_lines: number; canon: string | null; canon_url: string | null; running: boolean; people: Record<string, string>;
  subtitle: string; version: number; approved_by: string; approved_at: string; canon_map: CanonMap;
};
export type CanonLayer = { present: boolean; title: string; rules: number };
export type Trail = { step: string; date?: string; who?: string; text?: string; quotes?: { who: string; quote: string }[] };
export type HouseDoc = { file?: string; case?: string; title: string; layer: string; area?: string; depth?: number; kind?: string; scope?: string; status?: string;
  evidence?: string; open?: string; owner?: string; implements?: string[]; lead?: string; note?: string; version?: number; uses?: string[];
  origin?: { kind: string; text?: string; trail?: Trail[] } };
export type HouseView = { house: string; lead: string; updated: string; areas: { id: string; title: string; lead?: string }[]; docs: HouseDoc[];
  gaps: { layer: string; area?: string; depth: number; title: string; lead?: string }[]; records: HouseDoc[] };
export const canon = {
  house: () => call<HouseView>("GET", "/api/canon"),
  doc: (file: string) => call<{ file: string; html: string }>("GET", `/api/canon/doc?file=${encodeURIComponent(file)}`),
};
export type CanonMap = { basis?: CanonLayer; marke?: CanonLayer; areas?: { case: string; title: string; current: boolean; version: number }[] };

const cid = (id: string) => encodeURIComponent(id);
export const talk = {
  get: (id: string) => call<Interview>("GET", `/api/cases/${cid(id)}/interview`),
  answer: (id: string, question: string, text: string, marker: string, step_id: string) => call<{ ok: boolean; answer: Answer }>("POST", `/api/cases/${cid(id)}/interview/answer`, { question, text, marker, step_id }),
  anchor: (id: string, text: string) => call<{ ok: boolean; anchor: string }>("POST", `/api/cases/${cid(id)}/interview/anchor`, { text }),
  followup: (id: string, followup: string, text: string, step_id: string) => call<{ ok: boolean }>("POST", `/api/cases/${cid(id)}/interview/followup`, { followup, text, step_id }),
  chapter: (id: string, block: string, step_id: string) => call<{ ok: boolean; run: string | null }>("POST", `/api/cases/${cid(id)}/interview/chapter`, { block, step_id }),
  finish: (id: string, step_id: string) => call<{ ok: boolean; first: boolean }>("POST", `/api/cases/${cid(id)}/interview/finish`, { step_id }),
  outcome: (id: string) => call<Outcome>("GET", `/api/cases/${cid(id)}/outcome`),
  decide: (id: string, line: string, verdict: string, text: string, step_id: string) => call<{ ok: boolean }>("POST", `/api/cases/${cid(id)}/outcome/decide`, { line, verdict, text, step_id }),
  create: (title: string, step_id: string, values: Record<string, string> = {}) => call<{ id: string; stage: string }>("POST", "/api/cases", { title, step_id, values }),
};

// gate protocols (ADR-029): start, answer, shape (strike/add), seal — every write carries a step id, replayed safely
export const gate = {
  start: (id: string, template: string) => call<{ ok: boolean; file: string }>("POST", `/api/cases/${cid(id)}/protocols/start`, { template }),
  answer: (id: string, tid: string, body: { item: string; step_id: string; value?: boolean | number | string | null; na?: boolean; note?: string; evidence?: string[] }) =>
    call<{ ok: boolean }>("POST", `/api/cases/${cid(id)}/protocols/${encodeURIComponent(tid)}/answer`, body),
  strike: (id: string, tid: string, item: string, reason: string, step_id: string) =>
    call<{ ok: boolean }>("POST", `/api/cases/${cid(id)}/protocols/${encodeURIComponent(tid)}/shape`, { strike: item, reason, step_id }),
  seal: (id: string, tid: string, step_id: string) => call<{ ok: boolean }>("POST", `/api/cases/${cid(id)}/protocols/${encodeURIComponent(tid)}/seal`, { step_id }),
};

export const sample = (id: string, slot: string, step_id: string, source?: string) =>
  call<{ name: string; slot: string; step: StepResult }>("POST", `/api/cases/${encodeURIComponent(id)}/samples`, { slot, step_id, source: source ?? null });

// At the car (theme.onsite): which view each photo shows, what of the AI's hints is settled.
export type OnsiteHint = { id: string; text: string; why?: string; view?: string; photo?: string };
export type OnsiteHints = { round?: number; summary?: string; photograph?: OnsiteHint[]; clarify?: OnsiteHint[]; notice?: OnsiteHint[] };
export type OnsiteState = { photos?: Record<string, string>; hints?: Record<string, { done: boolean; text: string; by?: string; at?: string }> };
export type OnsiteConf = { stages: string[]; series: string; note: string; helper: string; hints: string; state: string; close: string;
  views: { id: string; word: string; required?: boolean }[] };
export const onsite = {
  put: (id: string, body: { photos?: Record<string, string>; hints?: Record<string, { done: boolean; text?: string }> }) =>
    call<{ ok: boolean; state: OnsiteState }>("PUT", `/api/cases/${encodeURIComponent(id)}/vorort`, body),
};

export function stepId(prefix: string): string {
  const r = (globalThis.crypto?.randomUUID?.() ?? Math.random().toString(16).slice(2)).replace(/-/g, "").slice(0, 12);
  return `${prefix}-${Date.now().toString(36)}-${r}`.slice(0, 80);
}

// The AI team (ADR-020): helpers belong to the person. Inside the cockpit the page works on the person's own team through the
// shell (`<shell>api/cf-team`, same origin, the shell's csrf cookie); in the public demo on the visitor's team here.
export type TeamAgent = { id: string; label: string; role: string; model?: string | null; session?: string | null };
export type TeamTemplate = { id: string; label: string; role: string; taken: boolean };
export type TeamSessionHead = { id: string; agent: string; label: string; topic: string; note: string; started?: string | null; ended?: string | null };
export type TeamView = { source: "demo" | "cockpit"; agents: TeamAgent[]; hireable: TeamTemplate[]; models: { id: string; label: string }[]; sessions: TeamSessionHead[]; logs_dir: string };
export type TeamTurn = { who: "you" | "ai"; text: string; thinking?: boolean };
export type TeamSession = TeamSessionHead & { role: string; does: string; status: "open" | "closed"; turns: TeamTurn[]; suggestions: string[] };

export function teamApi(me: MeOut) {
  const shell = me.team === "cockpit" && me.shell ? me.shell.replace(/\/?$/, "/") : null;
  const root = shell ? `${shell}api/cf-team` : `${BASE}/api/team`;
  const csrf = () => (document.cookie.split("; ").find((c) => c.startsWith("csrf=")) ?? "").slice(5);
  async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (shell && method !== "GET") headers["X-CSRF"] = csrf();
    const res = await fetch(root + path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined, credentials: "same-origin" });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) throw new ApiError(res.status, data && typeof data === "object" && "detail" in data ? { reason: (data as { detail: string }).detail } : data);
    return data as T;
  }
  return {
    view: () => req<TeamView>("GET", ""),
    hire: (template: string, model: string) => req<TeamView>("POST", "", { what: "hire", template, model }),
    dismiss: (agent: string) => req<TeamView>("POST", "", { what: "dismiss", agent }),
    logs: (logs_dir: string) => req<TeamView>("POST", "", { what: "logs_dir", logs_dir }),
    start: (agent: string, topic: string, place?: Record<string, string>) => req<{ id: string }>("POST", "/sessions", { agent, topic, place }),
    session: (id: string) => req<TeamSession>("GET", `/sessions/${encodeURIComponent(id)}`),
    say: (id: string, text: string) => req<TeamSession>("POST", `/sessions/${encodeURIComponent(id)}/say`, { text }),
    end: (id: string, note: string) => req<TeamSession>("POST", `/sessions/${encodeURIComponent(id)}/end`, { note }),
  };
}
