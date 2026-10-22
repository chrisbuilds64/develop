// The typed client over the core's API. Types come from the core (scripts/types.sh → api.d.ts), never from here.
import type { components } from "./api-types";

export type CaseCard = components["schemas"]["CaseCard"];
export type CaseView = components["schemas"]["CaseView"];
export type Turn = components["schemas"]["Turn"];
export type TurnOut = components["schemas"]["TurnOut"];
export type GroupOut = components["schemas"]["GroupOut"];
export type StageOut = components["schemas"]["StageOut"];
export type RulesOut = components["schemas"]["RulesOut"];
export type StepResult = components["schemas"]["StepResult"];
export type MeOut = components["schemas"]["MeOut"];
export type ConfigView = components["schemas"]["ConfigView"];
export type Entry = components["schemas"]["Entry"];
export type SlotView = components["schemas"]["SlotView"];

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(typeof body === "object" && body && "reason" in body ? String((body as { reason: string }).reason) : `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

export const BASE = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");

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

export const sample = (id: string, slot: string, step_id: string) =>
  call<{ name: string; slot: string; step: StepResult }>("POST", `/api/cases/${encodeURIComponent(id)}/samples`, { slot, step_id });

export function stepId(prefix: string): string {
  const r = (globalThis.crypto?.randomUUID?.() ?? Math.random().toString(16).slice(2)).replace(/-/g, "").slice(0, 12);
  return `${prefix}-${Date.now().toString(36)}-${r}`.slice(0, 80);
}
