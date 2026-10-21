// Twenty visitors at once: each gets a sandbox, opens the claims file, puts the sample invoice in, waits for the
// reconciliation, approves with an amount. Pure HTTP, no browser. usage: node load.mjs <base-url> [n]
const [base, nArg] = process.argv.slice(2);
const n = Number(nArg ?? 20);
const CASE = "HR-2026-0417-wasserschaden-badezimmer";

async function visitor(i) {
  const jar = new Map();
  const cookie = () => [...jar.entries()].map(([k, v]) => `${k}=${v}`).join("; ");
  const call = async (method, path, body) => {
    const res = await fetch(base + path, { method, headers: { "Content-Type": "application/json", Cookie: cookie() }, body: body ? JSON.stringify(body) : undefined });
    for (const sc of res.headers.getSetCookie?.() ?? []) { const [kv] = sc.split(";"); const [k, v] = kv.split("="); jar.set(k, v); }
    return { status: res.status, body: await res.json().catch(() => null) };
  };
  const t0 = Date.now();
  const me = await call("POST", "/api/demo/session", { world: "claims" });
  if (me.status !== 200) return { i, ok: false, at: "session", status: me.status };
  const s = await call("POST", `/api/cases/${CASE}/samples`, { slot: "rechnung.pdf", step_id: `load-${i}-s` });
  if (s.status !== 200) return { i, ok: false, at: "sample", status: s.status };
  let group = "claude";
  for (let k = 0; k < 40 && group === "claude"; k++) {
    await new Promise((r) => setTimeout(r, 500));
    const v = await call("GET", `/api/cases/${CASE}`);
    group = v.body?.group ?? "?";
  }
  const a = await call("POST", `/api/cases/${CASE}/steps`, { action: "approve_settlement", step_id: `load-${i}-a`, payload: { amount: "4.370 €" } });
  return { i, ok: a.status === 200 && a.body?.to === "40-regulierung", at: "approve", status: a.status, ms: Date.now() - t0 };
}

const results = await Promise.all(Array.from({ length: n }, (_, i) => visitor(i)));
const ok = results.filter((r) => r.ok).length;
console.log(`${ok}/${n} visitors completed the path`);
for (const r of results.filter((r) => !r.ok)) console.log("failed:", r);
const ms = results.filter((r) => r.ms).map((r) => r.ms).sort((a, b) => a - b);
if (ms.length) console.log(`time per visitor: median ${ms[Math.floor(ms.length / 2)]} ms, max ${ms[ms.length - 1]} ms`);
process.exit(ok === n ? 0 : 1);
