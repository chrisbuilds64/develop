// The typed client over the core's API. Types come from the core (scripts/types.sh → api.d.ts), never from here.
import type { components } from "./api-types";

export type CaseCard = components["schemas"]["CaseCard"];
export type CaseView = components["schemas"]["CaseView"];
export type Turn = components["schemas"]["Turn"];
export type TurnOut = components["schemas"]["TurnOut"];
export type GroupOut = components["schemas"]["GroupOut"];
export type StageOut = components["schemas"]["StageOut"];
export type RulesOut = components["schemas"]["RulesOut"];
export type SignalOut = components["schemas"]["SignalOut"];
export type StepResult = components["schemas"]["StepResult"];
export type MeOut = components["schemas"]["MeOut"];
export type ConfigView = components["schemas"]["ConfigView"];
export type Entry = components["schemas"]["Entry"];
export type SlotView = components["schemas"]["SlotView"];
export type RhythmOut = components["schemas"]["RhythmOut"];

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
  groups: () => call<GroupOut[]>("GET", "/api/cases"),
  stages: () => call<StageOut[]>("GET", "/api/stages"),
  rules: () => call<RulesOut>("GET", "/api/rules"),
  rhythm: () => call<RhythmOut>("GET", "/api/me/rhythm"),
  signals: () => call<SignalOut[]>("GET", "/api/signals"),
  case: (id: string) => call<CaseView>("GET", `/api/cases/${encodeURIComponent(id)}`),
  step: (id: string, action: string, step_id: string, payload: Record<string, unknown> = {}) =>
    call<StepResult>("POST", `/api/cases/${encodeURIComponent(id)}/steps`, { action, step_id, payload }),
  entry: (id: string, body: { kind: "note" | "answer" | "done"; step_id: string; text?: string; for?: string; resolves?: string; title?: string }) =>
    call<StepResult>("POST", `/api/cases/${encodeURIComponent(id)}/entries`, body),
  run: (id: string, body: { skill?: string; note: string; request_id: string }) =>
    call<StepResult>("POST", `/api/cases/${encodeURIComponent(id)}/runs`, body),
  asset: (id: string, slot: string, step_id: string, file: File) => {
    const fd = new FormData();
    fd.append("slot", slot);
    fd.append("step_id", step_id);
    fd.append("file", file);
    return call<{ name: string; slot: string; step: StepResult }>("POST", `/api/cases/${encodeURIComponent(id)}/assets`, undefined, fd);
  },
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
  create: (title: string, step_id: string) => call<{ id: string; stage: string }>("POST", "/api/cases", { title, step_id }),
};

export const sample = (id: string, slot: string, step_id: string) =>
  call<{ name: string; slot: string; step: StepResult }>("POST", `/api/cases/${encodeURIComponent(id)}/samples`, { slot, step_id });

export function stepId(prefix: string): string {
  const r = (globalThis.crypto?.randomUUID?.() ?? Math.random().toString(16).slice(2)).replace(/-/g, "").slice(0, 12);
  return `${prefix}-${Date.now().toString(36)}-${r}`.slice(0, 80);
}
